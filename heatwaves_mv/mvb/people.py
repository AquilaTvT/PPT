"""Where the people are, for the print. print2 only lets its skin treatment (faces and hands on one warm cream ink,
a lighter screen) land on people, so a sunset cloud, the sea, a seawall in dusk light, a lantern, a firework or a
wooden floor -- all "skin coloured" -- keep their own inks.

Three models, all small and CPU-fast, in work/models/ (`python3 -m mvb.people` fetches them):
  - anime person and face detection, YOLOv8 (deepghs/anime_person_detection person_detect_v1.3_s and
    deepghs/anime_face_detection face_detect_v1.4_s, MIT);
  - anime character segmentation, ISNet (skytnt/anime-seg isnetis.onnx, Apache-2.0).
The gate is the segmentation of a crop around each main figure (the model was trained on character pictures: on a
whole wide frame it sometimes takes a seawall or a lantern-lit street for "character", on the figure's own crop it is
clean), kept inside the figure's box, plus the face boxes. The faces also anchor the skin colour (print2). A frame
with no person and no face detected has no skin at all (and skips the segmentation).

A gate is computed every STEP-th frame of a shot and holds for the frames up to the next one (people move a few pixels
in 1/8 s; the gate is a coarse, slightly grown region), cached on disk per printer (its name carries the footage's
identity) and frame, so re-renders and parallel workers reuse it. Without a frame index (a single still), the cache
is keyed by the frame's content instead.
"""
import hashlib
import math
import os
import threading

import cv2
import numpy as np

from .atomic import load_json, save_img, save_json

ROOT = os.path.join(os.path.dirname(__file__), '..')
MODELS = os.path.join(ROOT, 'work', 'models')
FILES = {
    'seg': ('isnetis.onnx', 'https://huggingface.co/skytnt/anime-seg/resolve/main/isnetis.onnx'),
    'person': ('person_detect_v1.3_s/model.onnx',
               'https://huggingface.co/deepghs/anime_person_detection/resolve/main/person_detect_v1.3_s/model.onnx'),
    'face': ('face_detect_v1.4_s/model.onnx',
             'https://huggingface.co/deepghs/anime_face_detection/resolve/main/face_detect_v1.4_s/model.onnx'),
}
CONF = {'person': 0.45, 'face': 0.40}     # above the models' F1 thresholds (0.31 / 0.32): the main figures, steadily
VERSION = 'g2'
CACHE = os.path.join(ROOT, 'work', 'B2', 'people')
S = 1024                      # the segmentation model's fixed input (square; the 16:9 frame is letterboxed into it)
OUT = (480, 270)              # cached gate resolution: a gate, not a matte
STEP = 3                      # a fresh gate every 3rd frame (8 per second)
FRAME = None                  # (shot id, frame index) being rendered -- set by timeline.render
_SESS = {}
_MEM = {}
_LOCK = threading.Lock()
_WARNED = False


def _path(k):
    return os.path.join(MODELS, FILES[k][0])


def available():
    return all(os.path.exists(_path(k)) for k in FILES)


def _session(k):
    s = _SESS.get(k)
    if s is None:
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = int(os.environ.get('HW_SEG_THREADS', '0') or 0) or (os.cpu_count() or 4)
        so.inter_op_num_threads = 1
        s = _SESS[k] = ort.InferenceSession(_path(k), so, providers=['CPUExecutionProvider'])
    return s


def _u8(rgb):
    return rgb if rgb.dtype == np.uint8 else (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def segment(rgb, size=None):
    """character segmentation, float32 0..1, at `size` (w, h; default: the input's)"""
    u8 = _u8(rgb)
    h0, w0 = u8.shape[:2]
    h, w = (S, int(round(S * w0 / h0))) if h0 > w0 else (int(round(S * h0 / w0)), S)
    ph, pw = (S - h) // 2, (S - w) // 2
    x = np.zeros((S, S, 3), np.float32)
    x[ph:ph + h, pw:pw + w] = cv2.resize(u8, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    sess = _session('seg')
    with _LOCK:
        m = sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0][0, 0]
    return cv2.resize(np.clip(m[ph:ph + h, pw:pw + w], 0, 1).astype(np.float32), size or (w0, h0),
                      interpolation=cv2.INTER_AREA)


def _nms(b, s, thr=0.6):
    x0, y0, x1, y1 = b.T
    ar = (x1 - x0) * (y1 - y0)
    o = s.argsort()[::-1]
    keep = []
    while o.size:
        i = o[0]
        keep.append(i)
        r = o[1:]
        inter = (np.clip(np.minimum(x1[i], x1[r]) - np.maximum(x0[i], x0[r]), 0, None) *
                 np.clip(np.minimum(y1[i], y1[r]) - np.maximum(y0[i], y0[r]), 0, None))
        o = r[inter / (ar[i] + ar[r] - inter + 1e-9) < thr]
    return keep


def detect(rgb, kind, conf=None, size=640):
    """[(x0, y0, x1, y1, score)] in the input's pixels (YOLOv8: resize to a multiple of 32, xywh + class scores)"""
    u8 = _u8(rgb)
    h0, w0 = u8.shape[:2]
    r = min(1.0, size / max(h0, w0))
    nw, nh = int(math.ceil(w0 * r / 32) * 32), int(math.ceil(h0 * r / 32) * 32)
    x = cv2.resize(u8, (nw, nh), interpolation=cv2.INTER_AREA).astype(np.float32).transpose(2, 0, 1)[None] / 255.0
    sess = _session(kind)
    with _LOCK:
        out = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]
    sc = out[4:].max(0)
    out = out[:, sc > (CONF[kind] if conf is None else conf)].T
    if not len(out):
        return []
    cx, cy, w, h = out[:, 0], out[:, 1], out[:, 2], out[:, 3]
    b = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 1) * np.array([w0 / nw, h0 / nh, w0 / nw, h0 / nh])
    s = out[:, 4:].max(1)
    return [(*b[i], float(s[i])) for i in _nms(b, s)]


def _boxes(shape, boxes, grow):
    h, w = shape
    m = np.zeros((h, w), np.float32)
    for x0, y0, x1, y1, _ in boxes:
        gx, gy = (x1 - x0) * grow, (y1 - y0) * grow
        m[max(0, int(y0 - gy)):min(h, int(math.ceil(y1 + gy))), max(0, int(x0 - gx)):min(w, int(math.ceil(x1 + gx)))] = 1
    return m


def compute(rgb):
    """(gate float32 0..1 at OUT, faces [(x0, y0, x1, y1, score)] in OUT pixels)"""
    u8 = _u8(rgb)
    h0, w0 = u8.shape[:2]
    persons = detect(u8, 'person')
    faces = detect(u8, 'face')
    sx, sy = OUT[0] / w0, OUT[1] / h0
    g = np.zeros(OUT[::-1], np.float32)
    big = [p for p in persons if (p[2] - p[0]) * (p[3] - p[1]) >= 0.012 * w0 * h0]
    for x0, y0, x1, y1, _ in sorted(big, key=lambda p: (p[2] - p[0]) * (p[3] - p[1]), reverse=True)[:3]:
        gx, gy = 0.12 * (x1 - x0), 0.12 * (y1 - y0)
        cx0, cy0 = max(0, int(x0 - gx)), max(0, int(y0 - gy))
        cx1, cy1 = min(w0, int(math.ceil(x1 + gx))), min(h0, int(math.ceil(y1 + gy)))
        ox0, oy0 = int(round(cx0 * sx)), int(round(cy0 * sy))
        ox1, oy1 = max(ox0 + 1, int(round(cx1 * sx))), max(oy0 + 1, int(round(cy1 * sy)))
        m = segment(u8[cy0:cy1, cx0:cx1], (ox1 - ox0, oy1 - oy0))
        box = np.zeros_like(m)                                   # the figure's own box (+4%), inside its crop
        bx0, by0 = int((x0 - 0.04 * (x1 - x0)) * sx) - ox0, int((y0 - 0.04 * (y1 - y0)) * sy) - oy0
        bx1, by1 = int(math.ceil((x1 + 0.04 * (x1 - x0)) * sx)) - ox0, int(math.ceil((y1 + 0.04 * (y1 - y0)) * sy)) - oy0
        box[max(0, by0):max(0, by1), max(0, bx0):max(0, bx1)] = 1
        g[oy0:oy1, ox0:ox1] = np.maximum(g[oy0:oy1, ox0:ox1], m * box)
    fo = [(x0 * sx, y0 * sy, x1 * sx, y1 * sy, sc) for x0, y0, x1, y1, sc in faces]
    return np.maximum(g, _boxes(OUT[::-1], fo, 0.12)), fo


def key(rgb):
    th = cv2.resize(_u8(rgb), (192, 108), interpolation=cv2.INTER_AREA)
    return hashlib.md5(np.ascontiguousarray(th).tobytes() + VERSION.encode()).hexdigest()


def mask(rgb, name=None):
    """{'gate': float32 0..1 at OUT, 'faces': [(x0, y0, x1, y1, score)] in OUT pixels} for this frame (cached),
    or None when the models are not installed. name: the printer's name (footage + settings) -> the gate of this
    frame's STEP group; without it, or without a frame index, the cache is keyed by the frame's content."""
    global _WARNED
    if not available():
        if not _WARNED:
            print('people: models missing (python3 -m mvb.people) -- skin is not gated', flush=True)
            _WARNED = True
        return None
    if name and FRAME is not None:
        fi = int(FRAME[1])
        path = os.path.join(CACHE, name, f'{fi - fi % STEP:05d}.png')
    else:
        k = key(rgb)
        path = os.path.join(CACHE, k[:2], f'{k}.png')
    hit = _MEM.get(path)
    if hit is not None:
        return hit
    m = cv2.imread(path, cv2.IMREAD_GRAYSCALE) if os.path.exists(path) else None
    meta = load_json(path[:-4] + '.json') if m is not None else None
    if m is not None and meta is not None and m.shape[::-1] == OUT:
        out = {'gate': m.astype(np.float32) / 255.0, 'faces': [tuple(f) for f in meta['faces']]}
    else:
        g, faces = compute(rgb)
        save_json(path[:-4] + '.json', {'faces': [[float(v) for v in f] for f in faces]})
        save_img(path, (g * 255 + 0.5).astype(np.uint8))
        out = {'gate': g, 'faces': faces}
    if len(_MEM) > 64:
        _MEM.clear()
    _MEM[path] = out
    return out


def gate(m, shape, grow=0.02, thr=0.7):
    """boolean gate at `shape` (h, w): the mask, thresholded and grown a little (a hair's width of slack at the
    character's edge, so the skin there is not clipped by a soft matte)"""
    h, w = shape
    g = (cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR) > thr).astype(np.uint8)
    r = max(1, int(round(h * grow)))
    return cv2.dilate(g, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0


def download():
    import subprocess
    for k, (rel, url) in FILES.items():
        p = _path(k)
        if os.path.exists(p):
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        subprocess.run(['curl', '-sSL', '--retry', '4', '-o', p + '.part', url], check=True)
        os.replace(p + '.part', p)
        print('downloaded', rel, os.path.getsize(p))


if __name__ == '__main__':
    download()
    print('models ready' if available() else 'models missing')

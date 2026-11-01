"""MV-B v2 devices that live inside the generated footage (raw stage, before the print).

Detection works on plates (1920x1080 float RGB) so it follows the camera when the clip moves:
  detect_mirrors(rgb)   orange curve-mirror rings -> the glass inside each, as ellipses (largest first)
  detect_screen(rgb)    the lit CRT face -> 4-point quad
  detect_led(rgb)       the red seven-segment clock digits -> bounding box
  detect_paper(rgb)     the pale card on the table / floor -> 4-point quad
Tracks are computed once per clip (every frame, smoothed over time) and cached next to the clip.

Inserts:
  mirror_insert(img, ell, src)   a convex-mirror view of src inside the glass: barrel warp, cool tint,
                                 darker edge, a specular arc
  quad_paste(img, content, quad) perspective paste with a soft edge, lit by the plate underneath
  crt(content, t)                scanlines, bloom, slight barrel, phosphor tint
"""
import functools
import json
import math
import os

import cv2
import numpy as np

from .print_fx import hexc as H

W, H_ = 1920, 1080


# ------------------------------------------------------------------ detection
def _hsv(rgb, scale=0.5):
    small = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor((np.clip(small, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    return hsv, scale


def detect_mirrors(rgb, min_r=28, max_n=12):
    """glass ellipses inside orange rings: [((cx, cy), (w, h), angle), ...] in plate px, largest first"""
    hsv, sc = _hsv(rgb)
    h, s, v = hsv[..., 0].astype(np.int16), hsv[..., 1], hsv[..., 2]
    ring = (((h >= 2) & (h <= 16)) & (s > 120) & (v > 90)).astype(np.uint8)
    ring = cv2.morphologyEx(ring, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(ring, 8)
    out = []
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if max(w, hh) < 2 * min_r * sc or a < 60:
            continue
        comp = (lab[y:y + hh, x:x + w] == i).astype(np.uint8)
        filled = comp.copy()
        ff = np.zeros((hh + 2, w + 2), np.uint8)
        pad = cv2.copyMakeBorder(filled, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
        ff = pad.copy()
        cv2.floodFill(ff, None, (0, 0), 1)
        holes = (ff[1:-1, 1:-1] == 0).astype(np.uint8)       # pixels not reachable from outside = inside the ring
        if holes.sum() < (min_r * sc) ** 2 * 1.5:
            continue
        cs, _ = cv2.findContours(holes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=cv2.contourArea)
        if len(c) < 6:
            continue
        (ex, ey), (ew, eh), ang = cv2.fitEllipse(c)
        area = math.pi * ew * eh / 4
        fill = cv2.contourArea(c) / max(area, 1)
        if fill < 0.75 or min(ew, eh) / max(ew, eh) < 0.45:
            continue
        out.append((((ex + x) / sc, (ey + y) / sc), (ew / sc, eh / sc), ang))
    out.sort(key=lambda e: -e[1][0] * e[1][1])
    return out[:max_n]


def detect_screen(rgb, min_area=2500):
    """the lit CRT face: the largest bright, low-saturation blob -> 4 corners (TL, TR, BR, BL)"""
    hsv, sc = _hsv(rgb)
    m = ((hsv[..., 2] > 200) & (hsv[..., 1] < 110)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cs = [c for c in cs if cv2.contourArea(c) > min_area * sc * sc]
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    return _quad(c) / sc


def detect_led(rgb):
    """bounding box (x0, y0, x1, y1) of red glowing seven-segment digits"""
    hsv, sc = _hsv(rgb)
    h = hsv[..., 0].astype(np.int16)
    m = (((h <= 8) | (h >= 170)) & (hsv[..., 1] > 120) & (hsv[..., 2] > 150)).astype(np.uint8)
    m = cv2.dilate(m, np.ones((5, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, hh, _ = st[i]
    return np.array([x, y, x + w, y + hh], np.float32) / sc


def detect_paper(rgb, y_min=0.45):
    """the pale card lying in the lower part of the frame -> 4 corners"""
    hsv, sc = _hsv(rgb)
    v = hsv[..., 2].astype(np.float32)
    loc = cv2.GaussianBlur(v, (0, 0), 25)
    m = ((v > loc + 25) & (hsv[..., 1] < 90) & (v > 60)).astype(np.uint8)
    m[:int(m.shape[0] * y_min)] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    if cv2.contourArea(c) < 400:
        return None
    return _quad(c) / sc


def _quad(c):
    hull = cv2.convexHull(c)
    peri = cv2.arcLength(hull, True)
    for eps in (0.02, 0.04, 0.06, 0.09, 0.12):
        ap = cv2.approxPolyDP(hull, eps * peri, True)
        if len(ap) == 4:
            return order(ap.reshape(4, 2).astype(np.float32))
    r = cv2.minAreaRect(c)
    return order(cv2.boxPoints(r).astype(np.float32))


def order(p):
    """TL, TR, BR, BL"""
    p = np.asarray(p, np.float32)
    s, d = p.sum(1), p[:, 1] - p[:, 0]
    return np.array([p[np.argmin(s)], p[np.argmin(d)], p[np.argmax(s)], p[np.argmax(d)]], np.float32)


# ------------------------------------------------------------------ tracks (per clip, cached)
def track(sid2, kind, frames_fn, n, fps, smooth=2.0):
    """run detector `kind` on every frame of a clip once; cache; temporal smoothing of the numbers"""
    from . import v2
    d = os.path.join(v2.WORK2, sid2)
    src = v2.clip_path(sid2) or v2.kf_path(sid2) or ''
    key = os.path.join(d, f'track_{kind}_{int(os.path.getmtime(src)) if src else 0}.json')
    if os.path.exists(key):
        return json.load(open(key))
    det = {'mirrors': detect_mirrors, 'screen': detect_screen, 'led': detect_led, 'paper': detect_paper}[kind]
    raw = []
    for i in range(n):
        r = det(frames_fn(i / fps))
        if r is None:
            raw.append(None)
        elif kind == 'mirrors':
            raw.append([[e[0][0], e[0][1], e[1][0], e[1][1], e[2]] for e in r])
        else:
            raw.append(np.asarray(r, np.float32).ravel().tolist())
    out = _smooth_track(raw, kind, smooth)
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(key, 'w'))
    return out


def _smooth_track(raw, kind, sigma):
    n = len(raw)
    if kind != 'mirrors':
        good = [r for r in raw if r is not None]
        if not good:
            return [None] * n
        last = good[0]
        filled = []
        for r in raw:
            last = r if r is not None else last
            filled.append(last)
        a = np.array(filled, np.float32)
        if n > 2 and sigma > 0:
            a = cv2.GaussianBlur(a, (1, 0), sigmaX=0, sigmaY=sigma) if False else _gauss1d(a, sigma)
        return a.tolist()
    # mirrors: follow each mirror of the first frame by nearest centre
    first = next((r for r in raw if r), [])
    tracks = []
    for e0 in first:
        cur = e0
        seq = []
        for r in raw:
            if r:
                j = int(np.argmin([math.hypot(e[0] - cur[0], e[1] - cur[1]) for e in r]))
                if math.hypot(r[j][0] - cur[0], r[j][1] - cur[1]) < 0.6 * max(cur[2], cur[3]):
                    cur = r[j]
            seq.append(list(cur))
        a = np.array(seq, np.float32)
        ang = a[:, 4].copy()
        a = _gauss1d(a, sigma)
        a[:, 4] = ang
        tracks.append(a.tolist())
    return [[tr[i] for tr in tracks] for i in range(n)]


def _gauss1d(a, sigma):
    if len(a) < 3:
        return a
    k = np.exp(-0.5 * (np.arange(-int(3 * sigma), int(3 * sigma) + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.pad(a, ((len(k) // 2, len(k) // 2), (0, 0)), mode='edge')
    return np.stack([np.convolve(pad[:, j], k, mode='valid') for j in range(a.shape[1])], 1)


# ------------------------------------------------------------------ inserts
@functools.lru_cache(maxsize=8)
def _barrel_maps(size, k):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    u, v = (xs - size / 2) / (size / 2), (ys - size / 2) / (size / 2)
    r = np.sqrt(u * u + v * v)
    f = 1 + k * r * r
    return (u * f * size / 2 + size / 2 - 0.5).astype(np.float32), (v * f * size / 2 + size / 2 - 0.5).astype(np.float32)


def mirror_insert(img, ell, src, alpha=1.0, k=0.35, tint='#BFD4E6', edge=0.45, glare=0.5):
    """a convex-mirror view of `src` (float RGB, any size, already framed: the subject in the middle) inside the
    glass ellipse `ell` = ((cx, cy), (w, h), angle)"""
    (cx, cy), (ew, eh), ang = ell
    size = int(max(ew, eh) * 1.1) + 4
    if size < 8:
        return img
    sq = cv2.resize(src, (size, size), interpolation=cv2.INTER_AREA if src.shape[0] > size else cv2.INTER_CUBIC)
    mx, my = _barrel_maps(size, k)
    sq = cv2.remap(sq, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt(((xs - size / 2) / (size / 2)) ** 2 + ((ys - size / 2) / (size / 2)) ** 2)
    sq = sq * (1 - edge * np.clip((r - 0.55) / 0.45, 0, 1) ** 1.5)[..., None]
    sq = sq * 0.82 + H(tint)[None, None] * 0.18 * sq.mean(axis=2, keepdims=True) * 1.2
    # glare: a soft arc at the upper left of the glass
    gl = np.exp(-((r - 0.78) / 0.07) ** 2) * np.clip(-((xs - size / 2) + (ys - size / 2)) / size * 2.2, 0, 1)
    sq = sq + gl[..., None] * glare
    # place: the picture stays upright, scaled to the ellipse's bounding box; the rotated ellipse is only the mask
    t = math.radians(ang)
    bw = math.sqrt((ew / 2 * math.cos(t)) ** 2 + (eh / 2 * math.sin(t)) ** 2) * 2
    bh = math.sqrt((ew / 2 * math.sin(t)) ** 2 + (eh / 2 * math.cos(t)) ** 2) * 2
    Mf = np.array([[bw / size, 0, cx - bw / 2], [0, bh / size, cy - bh / 2]], np.float32)
    x0, y0 = int(max(0, cx - size)), int(max(0, cy - size))
    x1, y1 = int(min(W, cx + size)), int(min(H_, cy + size))
    if x1 <= x0 or y1 <= y0:
        return img
    Ml = Mf.copy()
    Ml[:, 2] -= [x0, y0]
    patch = cv2.warpAffine(sq, Ml, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.ellipse(m, ((cx - x0, cy - y0), (ew * 0.97, eh * 0.97), ang), 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), max(0.8, min(ew, eh) * 0.012)) * alpha
    roi = img[y0:y1, x0:x1]
    roi += (patch - roi) * m[..., None]
    return img


def quad_paste(img, content, quad, alpha=1.0, light=None, feather=1.2, blur=0.0, ref=None):
    """perspective-paste `content` onto the plate quad (TL, TR, BR, BL); `light` multiplies by the plate's own
    shading (0 = flat, 1 = fully lit by the plate)"""
    h, w = content.shape[:2]
    q = np.asarray(quad, np.float32).reshape(4, 2)
    Hm = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), q)
    x0, y0 = [int(max(0, math.floor(v - 4))) for v in q.min(0)]
    x1, y1 = int(min(W, math.ceil(q[:, 0].max() + 4))), int(min(H_, math.ceil(q[:, 1].max() + 4)))
    if x1 <= x0 or y1 <= y0:
        return img
    T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], np.float64)
    Hl = T @ Hm
    patch = cv2.warpPerspective(content, Hl, (x1 - x0, y1 - y0), flags=cv2.INTER_AREA if w > (x1 - x0) * 1.5 else cv2.INTER_LINEAR)
    m = cv2.warpPerspective(np.ones((h, w), np.float32), Hl, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
    if feather:
        m = cv2.GaussianBlur(m, (0, 0), feather)
    if blur > 0:
        patch = cv2.GaussianBlur(patch, (0, 0), blur)
    roi = img[y0:y1, x0:x1]
    if light:
        lum = roi @ np.float32([0.2126, 0.7152, 0.0722])
        if ref is None:                  # normalise to the brightest part under the quad, or to a fixed paper white
            ref = np.percentile(lum[m > 0.5], 90) if (m > 0.5).any() else 1.0
        shade = np.clip(lum / max(ref, 1e-3), 0.0, 1.4)
        shade = cv2.GaussianBlur(shade, (0, 0), 6)
        patch = patch * (1 - light + light * shade[..., None])
    roi += (patch - roi) * (m * alpha)[..., None]
    return img


def crt(content, t, tint='#CFE8FF', lines=True, bloom=0.35, curve=0.06):
    """a picture as it looks on a 1985 CRT: barrel, scanlines, phosphor tint, bloom, a rolling bright band"""
    h, w = content.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = (xs / w - 0.5) * 2, (ys / h - 0.5) * 2
    f = 1 + curve * (u * u + v * v)
    img = cv2.remap(content, ((u * f) / 2 + 0.5) * w, ((v * f) / 2 + 0.5) * h, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    img = img * 0.85 + H(tint)[None, None] * 0.15 * img.mean(axis=2, keepdims=True)
    if lines:
        sl = 0.78 + 0.22 * (np.sin(ys * math.pi * 2 / max(3.0, h / 120)) * 0.5 + 0.5)
        img = img * sl[..., None]
    band = np.exp(-(((ys / h) - ((t * 0.35) % 1.4 - 0.2)) / 0.08) ** 2) * 0.10
    img = img * (1 + band[..., None])
    if bloom:
        b = cv2.GaussianBlur(img, (0, 0), max(2.0, w / 60))
        img = img + b * bloom
    vig = np.clip(1 - 0.35 * (u * u + v * v) ** 1.5, 0, 1)
    return np.clip(img * vig[..., None], 0, 1.4)


def led_face(txt, w, h, on='#FF3B2A', off='#3A0E0C', bg='#140504', glow=0.6):
    """a red seven-segment clock face rendered to (h, w): digits from mvb.print_fx.clock_grid"""
    from . import print_fx as pf
    g = pf.clock_grid(txt)
    gh, gw = g.shape
    cell = min((w * 0.86) / gw, (h * 0.78) / gh)
    img = np.empty((h, w, 3), np.float32)
    img[:] = H(bg)
    ox, oy = (w - gw * cell) / 2, (h - gh * cell) / 2
    m_on = np.zeros((h, w), np.float32)
    m_off = np.zeros((h, w), np.float32)
    for yy in range(gh):
        for xx in range(gw):
            c = (int((ox + (xx + 0.5) * cell) * 4), int((oy + (yy + 0.5) * cell) * 4))
            r = int(cell * 0.42 * 4)
            cv2.circle(m_on if g[yy, xx] else m_off, c, r, 1.0, -1, cv2.LINE_AA, shift=2)
    img += (H(off) - img) * m_off[..., None] * 0.6
    img += (H(on) - img) * m_on[..., None]
    if glow:
        img += H(on)[None, None] * cv2.GaussianBlur(m_on, (0, 0), cell * 0.9)[..., None] * glow
    return img


# ------------------------------------------------------------------ planar tracking of a device region
def _gray(rgb):
    return cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)


def track_region(frame_at, n, box, pad=70, min_feat=12):
    """follow a (roughly planar, rigid) region through a clip: frame_at(i) -> float RGB plate; box = (x0, y0, x1, y1)
    on frame 0. Frame-to-frame homographies from LK-tracked corners (re-detected every frame inside the region as it
    moves), accumulated, applied to the box corners, smoothed in time. Returns [[4 corners] per frame] (plate px)."""
    x0, y0, x1, y1 = box
    B = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    Hacc = np.eye(3)
    prev = _gray(frame_at(0))
    corners = [B.copy()]
    for i in range(1, n):
        cur = _gray(frame_at(i))
        reg = cv2.perspectiveTransform(B[None], Hacc)[0]
        m = np.zeros(prev.shape, np.uint8)
        rx0, ry0 = np.maximum(reg.min(0) - pad, 0).astype(int)
        rx1, ry1 = np.minimum(reg.max(0) + pad, [W - 1, H_ - 1]).astype(int)
        m[ry0:ry1, rx0:rx1] = 255
        p0 = cv2.goodFeaturesToTrack(prev, 500, 0.01, 6, mask=m)
        Hstep = np.eye(3)
        if p0 is not None and len(p0) >= min_feat:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, p0, None, winSize=(21, 21), maxLevel=3,
                                                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
            ok = st.ravel() == 1
            if ok.sum() >= min_feat:
                Hm, inl = cv2.findHomography(p0[ok], p1[ok], cv2.RANSAC, 2.5)
                if Hm is not None and inl is not None and inl.sum() >= min_feat:
                    Hstep = Hm
        Hacc = Hstep @ Hacc
        corners.append(cv2.perspectiveTransform(B[None], Hacc)[0])
        prev = cur
    C = np.array(corners, np.float32).reshape(n, 8)
    if np.abs(C - C[0]).max() < 1.5:                      # a locked-off shot: do not add tracking jitter
        C[:] = C[0]
    elif n > 3:
        C = _gauss1d(C, 1.5)
    return C.reshape(n, 4, 2).tolist()


# ------------------------------------------------------------------ mirror tracking by masked multi-scale template match
def track_mirror_tm(frame_at, n, hint, half=True):
    """follow one curve mirror through a clip: frame_at(i) -> float RGB plate (zoom 1); hint = ((cx, cy), (w, h),
    ang) = its glass on frame 0. The ring + hood annulus of frame 0 (the glass masked out: its reflection changes) is
    matched in every frame around the predicted position, at three scales round the previous one.
    Returns [[cx, cy, scale, conf]] per frame in plate px; conf ~ match score, 0 once the mirror has left the frame."""
    (cx0, cy0), (ew, eh), ang = hint
    k = 0.5 if half else 1.0
    R = max(ew, eh) / 2 * k
    f0 = cv2.resize(frame_at(0), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    hh = int(math.ceil(R * 1.32))
    pad = hh + 4
    big = cv2.copyMakeBorder(f0, pad, pad, pad, pad, cv2.BORDER_REFLECT)
    tx, ty = int(round(cx0 * k)) + pad, int(round(cy0 * k)) + pad
    T = big[ty - hh:ty + hh + 1, tx - hh:tx + hh + 1].copy()
    ys, xs = np.mgrid[-hh:hh + 1, -hh:hh + 1].astype(np.float32)
    t = math.radians(ang)
    u = (xs * math.cos(t) + ys * math.sin(t)) / (ew / 2 * k)
    v = (-xs * math.sin(t) + ys * math.cos(t)) / (eh / 2 * k)
    e = np.sqrt(u * u + v * v)
    M = ((e > 0.93) & (e < 1.30)).astype(np.float32)
    M3 = np.repeat(M[..., None], 3, 2)
    out = [[float(cx0), float(cy0), 1.0, 1.0]]
    c = np.float32([cx0 * k, cy0 * k])
    vel = np.zeros(2, np.float32)
    s_prev = 1.0
    gone = False
    for i in range(1, n):
        if gone:
            out.append([float(c[0] / k), float(c[1] / k), s_prev, 0.0])
            continue
        fr = cv2.resize(frame_at(i), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        Hf, Wf = fr.shape[:2]
        pred = c + vel * 0.7
        best = (-2.0, pred, s_prev)
        for sc in (s_prev * 0.965, s_prev, s_prev * 1.035):
            Ts = cv2.resize(T, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)
            Ms = cv2.resize(M3, (Ts.shape[1], Ts.shape[0]), interpolation=cv2.INTER_NEAREST)
            th, tw_ = Ts.shape[:2]
            sr = int(0.22 * R * sc + 10)
            x0, y0 = int(round(pred[0] - tw_ / 2 - sr)), int(round(pred[1] - th / 2 - sr))
            x1, y1 = x0 + tw_ + 2 * sr, y0 + th + 2 * sr
            p = max(0, -x0, -y0, x1 - Wf, y1 - Hf)
            if p > tw_:                                     # mostly outside the frame
                continue
            win = cv2.copyMakeBorder(fr, p, p, p, p, cv2.BORDER_REFLECT) if p else fr
            win = win[y0 + p:y1 + p, x0 + p:x1 + p]
            if win.shape[0] < th or win.shape[1] < tw_:
                continue
            res = cv2.matchTemplate(win, Ts, cv2.TM_CCOEFF_NORMED, mask=Ms)
            res = np.nan_to_num(res, nan=-1.0, posinf=-1.0, neginf=-1.0)
            _, mv, _, ml = cv2.minMaxLoc(res)
            if mv > best[0]:
                best = (mv, np.float32([x0 + ml[0] + tw_ / 2, y0 + ml[1] + th / 2]), sc)
        score, cn, sn = best
        if score < -1.5:
            gone = True
            out.append([float(c[0] / k), float(c[1] / k), s_prev, 0.0])
            continue
        vel = cn - c
        c, s_prev = cn, float(sn)
        r_now = R * s_prev
        if c[0] < -r_now or c[0] > Wf + r_now or c[1] < -r_now or c[1] > Hf + r_now:
            gone = True
        out.append([float(c[0] / k), float(c[1] / k), s_prev, float(max(0.0, score))])
    a = np.array(out, np.float32)
    if n > 3:
        a[:, :3] = _gauss1d(a[:, :3], 1.2)
    return a.tolist()

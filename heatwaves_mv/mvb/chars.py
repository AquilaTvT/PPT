"""MV-B character cut-outs (design/mv_b/shots.json render_rules.cutout).

Green key (spill suppression, 1 px erode, matte smoothing; anime-seg ISNet when the plate is not green) ->
x3 Lanczos when the clip is not already upscaled -> PrintStyle in the shot's world inks (8 px 45-degree dots,
XDoG line in #1A1416) -> sticker rim (2 px warm-black + 5 px cream + 1.5 px vermilion hairline).
Processed frames are cached as RGBA PNG in work/B/cut/<sid>_<hash>/, so the slow steps run once per frame.

  cl = CharLayer('B-chorus1-01')
  if cl.ok:
      rgb, a = cl.frame(local_t, zoom=1.0, cx=0.5, cy=0.55)     # 1920x1080 screen-space layer
      img = over(img, rgb, a, shadow='#1E2550')

  python3 -m mvb.chars --all [--workers 3]      # pre-cut every clip that has arrived
"""
import argparse
import hashlib
import json
import os
import re

import cv2
import numpy as np

from .halftone import PrintStyle, hexc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WORK = os.path.join(ROOT, 'work', 'B')
CUT = os.path.join(WORK, 'cut')
SPEC = json.load(open(os.path.join(ROOT, 'design', 'mv_b', 'shots.json')))
BY_ID = {s['id']: s for s in SPEC['shots']}
W, H = 1920, 1080
VERSION = 8          # bump to invalidate cached cut-outs after changing the processing below

WORLDS = {k: [c.split()[0] for c in v] for k, v in SPEC['colour_worlds'].items()}
SECTION_WORLD = {'intro': '夜刷り Night Print', 'hook': '正午刷り Noon Print', 'chorus1': '正午刷り Noon Print',
                 'verse': 'ブラウン管 CRT Glow', 'chorus2': '月刷り Moon Print', 'bridge1': '夕焼け刷り Dusk Print',
                 'chorus3': '祭 Festival', 'bridge2': '二色夢刷り Two-ink Dream', 'chorus4': '黎明前 Blue Hour',
                 'outro': '夜明け刷り Dawn Print', 'outro_hook': '正午刷り Noon Print'}


def world_inks(sid):
    """the shot's inks: every hex code in its world line, else its section's colour world"""
    s = BY_ID[sid]
    hx = re.findall(r'#[0-9A-Fa-f]{6}', s.get('world', ''))
    if len(hx) < 4:
        hx = WORLDS[SECTION_WORLD[s['section']]]
    out = []
    for h in hx + ['#1A1416', '#EDE3CF']:
        if h.upper() not in out:
            out.append(h.upper())
    return out


def media_path(sid):
    d = os.path.join(WORK, sid)
    for name in ('final_up.mp4', 'v_0_up.mp4', 'final.mp4', 'v_0_24.mp4', 'v_0.mp4'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return 'video', p
    man = os.path.join(WORK, 'manifest.json')
    if os.path.exists(man):
        kf = ((json.load(open(man)).get(sid) or {}).get('pick') or {}).get('kf')
        if kf and os.path.exists(os.path.join(d, os.path.basename(kf))):
            return 'still', os.path.join(d, os.path.basename(kf))
    for name in ('kf_0.png', 'kf_1.png'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return 'still', p
    return None, None


# ------------------------------------------------------------------ matte
def green_key(rgb):
    """soft background probability for a flat green plate; returns (alpha, green_fraction)"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ex = g - np.maximum(r, b)
    bg = np.clip((ex - 0.05) / 0.10, 0, 1)
    frac = float((bg > 0.5).mean())
    a = 1.0 - bg
    a = cv2.erode(a, np.ones((3, 3), np.uint8))                      # 1 px erode
    a = cv2.GaussianBlur(a, (0, 0), 0.8)
    a = np.clip((a - 0.5) * 1.8 + 0.5, 0, 1)
    # drop specks: keep components larger than 1.5% of the biggest one
    n, lab, st, _ = cv2.connectedComponentsWithStats((a > 0.5).astype(np.uint8), 8)
    if n > 2:
        big = st[1:, cv2.CC_STAT_AREA].max()
        keep = np.zeros(n, np.float32)
        keep[1:] = (st[1:, cv2.CC_STAT_AREA] >= 0.015 * big).astype(np.float32)
        a = a * cv2.dilate(keep[lab], np.ones((5, 5), np.uint8))
    return a.astype(np.float32), frac


def despill(rgb, a):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lim = np.maximum(r, b) + 0.015
    g2 = np.where(g > lim, lim + (g - lim) * 0.15, g)
    out = rgb.copy()
    out[..., 1] = g2
    return out


_matter = None


def isnet(rgb):
    global _matter
    if _matter is None:
        from .matte import Matter
        _matter = Matter()
    return _matter(rgb)


# ------------------------------------------------------------------ rim
def sticker(rgb, a, line='#1A1416', cream='#EDE3CF', hair='#D9402B', w_line=2.0, w_cream=5.0, w_hair=1.5, scale=1.0):
    """rim rings outside the matte by distance: warm-black line, cream band, vermilion hairline"""
    d = cv2.distanceTransform((a < 0.5).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
    e1, e2, e3 = w_line * scale, (w_line + w_cream) * scale, (w_line + w_cream + w_hair) * scale
    m_line = np.clip(e1 + 0.5 - d, 0, 1)
    m_cream = np.clip(e2 + 0.5 - d, 0, 1)
    m_hair = np.clip(e3 + 0.5 - d, 0, 1) if w_hair > 0 else m_cream
    col = np.broadcast_to(hexc(hair), rgb.shape).copy()
    col += (hexc(cream)[None, None] - col) * m_cream[..., None]
    col += (hexc(line)[None, None] - col) * m_line[..., None]
    col += (rgb - col) * a[..., None]
    return col, np.maximum(a, m_hair)


# ------------------------------------------------------------------ layer
class CharLayer:
    def __init__(self, sid, inks=None, period=8.0, in_t=0.15, speed=1.0, loop=False, pingpong=False, rim=True,
                 rim_cream='#EDE3CF', rim_hair='#D9402B', rim_w=(2.0, 5.0, 1.5), shade=0.85, dot_gain=1.0,
                 line_w=1.0, max_cov=None, src=None, dead=0.07, skin='#EDE3CF'):
        self.sid = sid
        self.kind, self.path = (('video', src) if src and src.endswith('.mp4') else ('still', src)) if src else media_path(sid)
        if self.kind is None and os.environ.get('HW_CHAR_STANDIN'):      # preview only: a stand-in figure
            self.kind, self.path = 'still', os.environ['HW_CHAR_STANDIN']
        self.ok = self.kind is not None
        self.inks = inks or world_inks(sid)
        self.in_t, self.speed, self.loop, self.pingpong = in_t, speed, loop, pingpong
        self.rim, self.rim_cream, self.rim_hair, self.rim_w = rim, rim_cream, rim_hair, rim_w
        self.style = dict(period=period, shade_strength=shade, dot_gain=dot_gain, line_w=line_w, dead=dead, skin=skin)
        self.max_cov = max_cov
        self._ps = None
        self._mem = {}
        if not self.ok:
            return
        key = json.dumps([VERSION, self.path, os.path.getmtime(self.path), self.inks, self.style, rim, rim_cream, rim_hair,
                          list(rim_w)], sort_keys=True)
        self.dir = os.path.join(CUT, f'{sid}_{hashlib.md5(key.encode()).hexdigest()[:10]}')
        if self.kind == 'video':
            cap = cv2.VideoCapture(self.path)
            self.fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            self.n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
        else:
            self.fps, self.n = 24.0, 1
        self._cap, self._ci = None, -1

    # --- source
    def index(self, local_t):
        if self.kind != 'video':
            return 0
        i = int((self.in_t + max(0.0, local_t) * self.speed) * self.fps + 1e-6)
        if self.pingpong and self.n > 1:
            per = 2 * (self.n - 1)
            i %= per
            return i if i < self.n else per - i
        if self.loop:
            return i % self.n
        return min(i, self.n - 1)

    def _read(self, i):
        if self.kind != 'video':
            im = cv2.imread(self.path)
        else:
            if self._cap is None or i <= self._ci - 1 or i > self._ci + 60:
                if self._cap is not None:
                    self._cap.release()
                self._cap = cv2.VideoCapture(self.path)
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                self._ci = i - 1
            im = None
            while self._ci < i:
                ok, im = self._cap.read()
                if not ok:
                    break
                self._ci += 1
            if im is None:
                cap = cv2.VideoCapture(self.path)
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                _, im = cap.read()
                cap.release()
        return cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

    # --- processing
    def process(self, i):
        rgb = self._read(i)
        if rgb.shape[1] < 1200:
            rgb = np.clip(cv2.resize(rgb, (rgb.shape[1] * 3, rgb.shape[0] * 3), interpolation=cv2.INTER_LANCZOS4), 0, 1)
        a, frac = green_key(rgb)
        if frac < 0.15:
            a = isnet(rgb)
        rgb = despill(rgb, a)
        if self._ps is None:
            self._ps = PrintStyle(self.inks, ink_line='#1A1416', paper='#EDE3CF', grain=0.0, **self.style)
        pr = self._ps(rgb)
        if self.max_cov is not None:          # under-inked look: pull the print back toward its flat base
            pr = pr * self.max_cov + hexc('#EDE3CF')[None, None] * (1 - self.max_cov)
        if self.rim:
            pr, a = sticker(pr, a, cream=self.rim_cream, hair=self.rim_hair, w_line=self.rim_w[0], w_cream=self.rim_w[1],
                            w_hair=self.rim_w[2])
        return pr.astype(np.float32), a.astype(np.float32)

    def rgba(self, i):
        """cut-out at source resolution: (rgb, alpha) float32"""
        if i in self._mem:
            return self._mem[i]
        p = os.path.join(self.dir, f'c_{i:05d}.png')
        if os.path.exists(p):
            im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            rgb = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            a = im[..., 3].astype(np.float32) / 255.0
        else:
            rgb, a = self.process(i)
            os.makedirs(self.dir, exist_ok=True)
            out = np.dstack([cv2.cvtColor((rgb * 255 + 0.5).clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                             (a * 255 + 0.5).clip(0, 255).astype(np.uint8)])
            cv2.imwrite(p + '.tmp.png', out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            os.replace(p + '.tmp.png', p)
        if len(self._mem) > 4:
            self._mem.clear()
        self._mem[i] = (rgb, a)
        return rgb, a

    def precompute(self):
        for i in range(self.n):
            if not os.path.exists(os.path.join(self.dir, f'c_{i:05d}.png')):
                self.rgba(i)

    def frame(self, local_t, zoom=1.0, cx=0.5, cy=0.5, rot=0.0, x=None, y=None, flip=False, height=None):
        """screen-space layer. Default: cover-fit the source frame (like the footage), scaled by zoom about the
        source point (cx, cy). With x/y the source point (cx, cy) lands on screen (x, y); height = source frame
        height in screen px (overrides the cover-fit scale)."""
        rgb, a = self.rgba(self.index(local_t))
        ih, iw = a.shape
        s = (height / ih) if height else max(W / iw, H / ih) * zoom
        M = cv2.getRotationMatrix2D((cx * iw, cy * ih), rot, s)
        M[0, 2] += (W / 2 if x is None else x) - cx * iw
        M[1, 2] += (H / 2 if y is None else y) - cy * ih
        if flip:
            M = np.array([[-1, 0, W - 1], [0, 1, 0]], np.float64) @ np.vstack([M, [0, 0, 1]])
        four = np.dstack([rgb, a])
        o = cv2.warpAffine(four, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        o = np.clip(o, 0, 1)
        return o[..., :3], o[..., 3]


def over(img, rgb, a, shadow=None, shadow_off=(8, 8), shadow_amt=0.6, alpha=1.0):
    """composite a cut-out layer; optional flat drop shadow in a world ink"""
    if shadow:
        M = np.float32([[1, 0, shadow_off[0]], [0, 1, shadow_off[1]]])
        sa = cv2.warpAffine(a, M, (a.shape[1], a.shape[0])) * shadow_amt * alpha
        img = img + (hexc(shadow)[None, None] - img) * sa[..., None]
    return img + (rgb - img) * (a * alpha)[..., None]


def available():
    return [sid for sid in BY_ID if media_path(sid)[0]]


def _work(sid):
    cl = CharLayer(sid)
    if cl.ok:
        cl.precompute()
    return sid


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--shots', default='')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    ids = available() if a.all else [s for s in a.shots.split(',') if s]
    if a.workers > 1 and len(ids) > 1:
        import multiprocessing as mp
        with mp.get_context('fork').Pool(a.workers) as pool:
            for sid in pool.imap_unordered(_work, ids):
                print('cut', sid, flush=True)
    else:
        for sid in ids:
            print('cut', _work(sid), flush=True)


def raw_matte(sid, src=None):
    """(rgb, alpha, parts) of a shot's still at >= 1056 px tall: anime-seg matte (white or green plate), and the
    connected figures sorted left to right as separate alphas (two-person stills split into print plates)."""
    kind, path = ('still', src) if src else media_path(sid)
    if kind is None and os.environ.get('HW_CHAR_STANDIN'):
        kind, path = 'still', os.environ['HW_CHAR_STANDIN']
    if kind is None:
        return None
    key = hashlib.md5(json.dumps([VERSION, path, os.path.getmtime(path)]).encode()).hexdigest()[:10]
    d = os.path.join(CUT, f'{sid}_raw_{key}')
    fp = os.path.join(d, 'rgba.png')
    if os.path.exists(fp):
        im = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
        rgb = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        a = im[..., 3].astype(np.float32) / 255.0
    else:
        if kind == 'video':
            cap = cv2.VideoCapture(path)
            _, im = cap.read()
            cap.release()
        else:
            im = cv2.imread(path)
        rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        if rgb.shape[0] < 1000:
            k = 1056 / rgb.shape[0]
            rgb = np.clip(cv2.resize(rgb, (int(rgb.shape[1] * k), 1056), interpolation=cv2.INTER_LANCZOS4), 0, 1)
        a, frac = green_key(rgb)
        if frac < 0.15:
            a = isnet(rgb)
        rgb = despill(rgb, a)
        os.makedirs(d, exist_ok=True)
        out = np.dstack([cv2.cvtColor((rgb * 255 + 0.5).clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                         (a * 255 + 0.5).clip(0, 255).astype(np.uint8)])
        cv2.imwrite(fp, out)
    n, lab, st, cen = cv2.connectedComponentsWithStats((a > 0.5).astype(np.uint8), 8)
    comps = sorted([i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.04 * (a > 0.5).sum()], key=lambda i: cen[i][0])
    parts = []
    for i in comps:
        m = cv2.dilate((lab == i).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
        parts.append((a * m, tuple(st[i, :4])))
    if len(parts) == 1:
        # the two figures touch: split the blob at its narrowest column between 30% and 70% of its width
        x, y, w, h = parts[0][1]
        cols = (a[y:y + h, x:x + w] > 0.5).sum(0).astype(np.float32)
        lo, hi = int(w * 0.3), int(w * 0.7)
        if hi > lo + 2:
            cut = x + lo + int(np.argmin(cv2.GaussianBlur(cols[lo:hi][None], (1, 31), 0)[0]))
            ramp = np.clip((np.arange(a.shape[1], dtype=np.float32) - cut) / 6.0 + 0.5, 0, 1)[None, :]
            left, right = a * (1 - ramp), a * ramp
            parts = [(left, (x, y, cut - x, h)), (right, (cut, y, x + w - cut, h))]
    return rgb, a, parts

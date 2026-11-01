"""MV-B v2: the stamp-card shots (pure graphics, mvb/card2.py).

  intro-04  11.05-16.98  night, the card on the chabudai in CRT light; five stamps slam onto the cells on the
                         beats, the English line types itself into the footer; then the sun rises in the sixth
                         cell, its warmth floods the card and the camera dives into it (-> hook-01, noon).
  outro-07  179.94-182.91 dawn, the card on the lighthouse's wooden stamp stand: the sixth stamp lands (lighthouse
                         and sun), dots burst, the camera pulls back to the whole card, all six stamps pulse once,
                         the old line fades and HEAT WAVES BEEN FAKIN' ME OUT is typed; the sea wind lifts the edge.
"""
import functools
import math

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import BEAT
from . import card2 as C
from .print_fx import hexc as H

W, H_ = 1920, 1080
_YS, _XS = np.mgrid[0:H_, 0:W].astype(np.float32)
LINE_IN = "YOU KNOW THAT I'M NEVER GONNA LOSE"
LINE_OUT = ['HEAT', 'WAVES', 'BEEN', "FAKIN'", 'ME', 'OUT']


def ease_io(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_in(x):
    return x ** 3


def smooth(x):
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ camera helpers
def scr_scale(zoom):
    return W / C.CW * zoom                       # screen px per design unit


def to_screen(cam, x, y):
    cx, cy, z, rot = cam
    s = scr_scale(z)
    dx, dy = (x - cx) * s, (y - cy) * s
    a = math.radians(-rot)
    return W / 2 + dx * math.cos(a) - dy * math.sin(a), H_ / 2 + dx * math.sin(a) + dy * math.cos(a)


@functools.lru_cache(maxsize=4)
def table_tex(kind):
    """the surface under the card, in design units at 1/4 scale over (-1600..4800) x (-1200..3000)"""
    tw_, th_ = 1600, 1050
    rng = np.random.default_rng(5 if kind == 'night' else 6)
    ys, xs = np.mgrid[0:th_, 0:tw_].astype(np.float32)
    warp = cv2.resize(rng.standard_normal((th_ // 40 + 2, tw_ // 40 + 2)).astype(np.float32), (tw_, th_), interpolation=cv2.INTER_CUBIC)
    grain = 0.5 + 0.5 * np.sin(ys / 3.4 + 2.2 * warp + 0.5 * np.sin(xs / 90.0))
    streak = cv2.resize(cv2.GaussianBlur(rng.standard_normal((th_ // 2, tw_ // 24)).astype(np.float32), (0, 0), 1.0),
                        (tw_, th_), interpolation=cv2.INTER_CUBIC)
    fine = cv2.GaussianBlur(rng.standard_normal((th_, tw_)).astype(np.float32), (0, 0), 0.8)
    if kind == 'night':
        a, b = H('#1B1412'), H('#33241C')
    else:
        a, b = H('#86512C'), H('#A9683A')
    plank = np.repeat(rng.uniform(-0.06, 0.06, 4), th_ // 4 + 1)[:th_, None, None]
    img = a[None, None] + (b - a)[None, None] * (grain[..., None] * 0.35 + 0.35 + 0.12 * streak[..., None])
    img *= (1 + plank + 0.04 * fine[..., None])
    for k in range(1, 4):                          # plank seams
        img[int(th_ * k / 4) - 1:int(th_ * k / 4) + 1] *= 0.55
    return img.astype(np.float32)


def table_view(kind, cam):
    tex = table_tex(kind)
    cx, cy, z, rot = cam
    s = scr_scale(z) * 4.0                          # screen px per texture px (texture = 1/4 design scale)
    tcx, tcy = (cx + 1600) / 4.0, (cy + 1200) / 4.0
    M = cv2.getRotationMatrix2D((tcx, tcy), rot, s)
    M[0, 2] += W / 2 - tcx
    M[1, 2] += H_ / 2 - tcy
    return cv2.warpAffine(tex, M, (W, H_), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def card_mask(cam, lift=0.0):
    pts = np.float32([to_screen(cam, x, y) for x, y in ((0, 0), (C.CW, 0), (C.CW, C.CH), (0, C.CH))])
    m = np.zeros((H_, W), np.uint8)
    cv2.fillPoly(m, [np.round(pts * 4).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
    return m.astype(np.float32) / 255.0


def on_table(card, cam, kind, shadow=(14, 18, 16, 0.55)):
    cx, cy, z, rot = cam
    img = C.view(card, cx, cy, z, rot)
    m = card_mask(cam)
    if m.min() > 0.999:
        return img, m
    tab = table_view(kind, cam)
    dx, dy, blur, amt = shadow
    sh = cv2.GaussianBlur(np.roll(m, (int(dy * z), int(dx * z)), (0, 1)), (0, 0), blur * z) * amt
    base = tab * (1 - sh[..., None])
    return base * (1 - m[..., None]) + img * m[..., None], m


# ------------------------------------------------------------------ card states (cached per key)
_CACHE = {}


def _cached(key, fn, keep=3):
    if key not in _CACHE:
        ks = [k for k in _CACHE if k[0] == key[0]]
        for k in ks[:max(0, len(ks) - keep + 1)]:
            del _CACHE[k]
        _CACHE[key] = fn()
    return _CACHE[key]


def _typed(img, s, x, y, size, col, alpha=1.0, name='garamond', tracking=0.3, press=True):
    """letterpress: a dark bite lower-right, a light lip upper-left, then the ink"""
    layers = ((2.5, 2.5, '#9E8F74', 0.55), (-1.5, -1.5, '#FFF8EA', 0.5), (0, 0, col, 1.0)) if press else ((0, 0, col, 1.0),)
    for dx, dy, c, al in layers:
        surf, cv = C._a8()
        C.T(cv, s, x + dx, y + dy, size, name, align='left', tracking=tracking)
        cov = C._cov(surf) * al * alpha
        if c == col:
            img *= 1 - cov[..., None] * (1 - H(c))[None, None]
        else:
            img += (H(c)[None, None] - img) * cov[..., None]
    return img


def _wet(img, i, wet):
    """the first frames of a fresh stamp: ink spreads a little, then settles"""
    if wet <= 0:
        return img
    cov, x0, y0 = C.stamp_patch(i)
    spread = cv2.dilate(cov, np.ones((3, 3), np.uint8), iterations=max(1, int(round(3 * wet))))
    extra = np.clip(spread - cov, 0, 1) * 0.8 * wet
    h, w = cov.shape
    roi = img[y0:y0 + h, x0:x0 + w]
    roi *= 1 - extra[..., None] * (1 - H(C.STAMP_INK))[None, None]
    return img


# ------------------------------------------------------------------ intro-04
STAMP_T = [11.79, 12.53, 13.27, 14.02, 14.76]
CAM_IN = [  # t, cx, cy, zoom
    (11.05, 1600, 900, 0.93), (11.79, 1760, 880, 1.10), (13.27, 2150, 930, 1.36), (14.76, 2440, 1060, 1.58),
    (16.24, 2875, 1312, 3.30), (16.98, 2875, 1286, 11.0)]


def _cam_in(t):
    ks = CAM_IN
    if t <= ks[0][0]:
        return ks[0][1:]
    for a, b in zip(ks, ks[1:]):
        if t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0])
            e = ease_in(u) if b[0] == 16.98 else (ease_io(u) if a[0] >= 14.76 else smooth(u))
            z = math.exp(math.log(a[3]) + (math.log(b[3]) - math.log(a[3])) * e)
            return a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e, z
    return ks[-1][1:]


def intro04(s, t, local, fi):
    stamp_k = tuple(round(clamp((t - r) / (2 / 24)), 2) for r in STAMP_T)
    wet = [clamp(1 - (t - r) / (4 / 24)) if t >= r else 0.0 for r in STAMP_T]
    sun_k = ease_io(clamp((t - 14.76) / (16.24 - 14.76)))
    glow_k = 0.35 * sun_k + 0.65 * clamp((t - 15.50) / (16.98 - 15.50))
    ray = 3.0 * max(0.0, t - 14.76) / BEAT
    n = int(clamp((t - 11.39) / (14.02 - 11.39)) * len(LINE_IN))
    key = ('in', stamp_k, tuple(round(w, 2) for w in wet), round(sun_k, 3), round(glow_k, 3), round(ray, 1), n)

    def build():
        card = C.render_card(stamp_k=stamp_k, sun_k=sun_k, glow_k=glow_k, ray_rot=ray)
        for i, w in enumerate(wet):
            card = _wet(card, i, w)
        if n:
            card = _typed(card, LINE_IN[:n], 1240, 1688, 30, C.VERM)
        return card
    card = _cached(key, build)
    cx, cy, z = _cam_in(t)
    # the slam: a two-frame jolt of the camera on every stamp
    jx = jy = 0.0
    for r in STAMP_T:
        if 0 <= t - r < 0.25:
            d = math.exp(-(t - r) / 0.06)
            jx += 5.0 * d * math.sin((t - r) * 2 * math.pi * 14)
            jy += 7.0 * d * math.cos((t - r) * 2 * math.pi * 11)
    cam = (cx - jx / scr_scale(z), cy - jy / scr_scale(z), z, 0.0)
    img, m = on_table(card, cam, 'night')
    # map pins answer their stamp: a vermilion ring opens on the pin as the stamp lands
    from .shiomi_map import STAMPS
    ring = np.zeros((H_, W), np.float32)
    for i, r in enumerate(STAMP_T):
        if 0 <= t - r < 0.6:
            k = (t - r) / 0.6
            px, py = to_screen(cam, *C.m2d(*STAMPS[i][2:]))
            rr = scr_scale(z) * (26 + 70 * (1 - (1 - k) ** 2))
            cv2.circle(ring, (int(px), int(py)), int(rr), 1.0, max(1, int(4 * (1 - k) + 1)), cv2.LINE_AA)
    img += (H(C.VERM)[None, None] - img) * (ring * 0.85)[..., None]
    # light: night CRT (mint, from the left), then the sun's warmth spreading from the sixth cell
    xs, ys = _XS / W, _YS / H_
    crt = np.clip(1.08 - 0.75 * xs - 0.22 * ys, 0, 1)
    night = (0.36 + 0.50 * crt)[..., None] * (H('#B8D8D4') * 0.55 + H('#C3CCE6') * 0.45)[None, None] * 1.12
    sx, sy = to_screen(cam, *C.CELL_C[5])
    d = np.sqrt((_XS - sx) ** 2 + (_YS - sy) ** 2) / (scr_scale(z) * C.R0)
    warm_r = 1.2 + 9.0 * sun_k ** 1.5
    warm = np.clip(np.exp(-(d / warm_r) ** 2) * (0.25 + 0.75 * sun_k), 0, 1) * clamp(sun_k * 1.6)
    day = H('#FFE7B8')[None, None] * 1.06
    light = night * (1 - warm[..., None]) + day * warm[..., None]
    img = img * light
    # heat shimmer over the rising sun (dreamcore): the air above the cell wobbles
    if sun_k > 0.05:
        amp = 2.5 * sun_k * scr_scale(z) / 1.2
        wob = np.exp(-(d / (2.0 + 2.0 * sun_k)) ** 2)
        dxm = (amp * wob * np.sin(_YS / 9.0 + t * 7.0)).astype(np.float32)
        img = cv2.remap(img, _XS + dxm, _YS, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    # the dive: blown out to warm white as the camera enters the sun
    if t > 16.45:
        k = clamp((t - 16.45) / (16.98 - 16.45)) ** 2
        img += (H('#FFF4DC')[None, None] - img) * k
    return img


# ------------------------------------------------------------------ outro-07
def _sun_disc(card, k):
    """the sixth stamp is a two-colour impression: a yellow sun under the vermilion lighthouse"""
    x6, y6 = C.CELL_C[5]
    half = int((C.R0 + 6) * C.SC)
    ys, xs = np.mgrid[-half:half, -half:half].astype(np.float32) / C.SC
    d = np.sqrt(xs ** 2 + (ys + 8) ** 2)
    disc = np.clip((C.R0 * 0.50 - d) * C.SC * 0.7, 0, 1)
    ang = np.degrees(np.arctan2(ys + 8, xs))
    rays = ((np.mod(ang + 7.5, 30) < 15) & (d > C.R0 * 0.56) & (d < C.R0 * 0.70)).astype(np.float32)
    cov = np.clip(disc + rays * 0.85, 0, 1) * k
    rng = np.random.default_rng(66)
    cov *= np.clip(0.85 + 0.15 * cv2.GaussianBlur(rng.standard_normal(cov.shape).astype(np.float32), (0, 0), 3) * 3, 0.5, 1)
    x0, y0 = int(x6 * C.SC) - half, int(y6 * C.SC) - half
    roi = card[y0:y0 + 2 * half, x0:x0 + 2 * half]
    roi *= 1 - cov[..., None] * (1 - H('#F2C23A'))[None, None]
    return card


def outro07(s, t, local, fi):
    from .recipes import _map_gt
    x6, y6 = C.CELL_C[5]
    slam = clamp(local / (3 / 24))
    gt = _map_gt(61)
    new = ''
    for i, w_ in enumerate(LINE_OUT):
        if t >= gt[i]:
            nl = min(len(w_), int((t - gt[i]) / (BEAT / 8)) + 1)      # letters within a word on 32nds
            new += (' ' if new else '') + w_[:nl]
    old_a = round(1.0 - clamp((t - 180.15) / (181.6 - 180.15)), 2)
    key = ('out', round(slam, 2), new, old_a)

    def build():
        card = C.render_card(stamp_k=(1, 1, 1, 1, 1))
        card = _sun_disc(card, 1.0)
        cov, x0, y0 = C.stamp_patch(5)
        C._press(card, cov, x0, y0)
        if slam < 1:
            card = _wet(card, 5, 1 - slam)
        if old_a > 0:
            card = _typed(card, LINE_IN, 1240, 1688, 30, C.VERM, alpha=old_a, press=False)
        if new:
            card = _typed(card, new, 1240, 1688, 30, C.NAVY)
        return card
    card = _cached(key, build)
    # camera: hold on the sixth cell at x2.4 (the relay lands there), pull back from 180.68 to the whole card
    k = ease_io(clamp((t - 180.68) / (181.95 - 180.68)))
    z = math.exp(math.log(2.4) + (math.log(0.90) - math.log(2.4)) * k)
    cx, cy = x6 + (1600 - x6) * k, y6 + (900 - y6) * k
    if slam < 1:
        z *= 1.0 + 0.05 * (1 - slam)
    cam = (cx, cy, z, -1.5 * k)
    img, m = on_table(card, cam, 'day', shadow=(22, 26, 14, 0.5))
    # the sea wind lifts the free (right) edge from 182.17
    lift = clamp((t - 182.17) / 0.6)
    lx, _ = to_screen(cam, 0, C.CH / 2)
    rx, _ = to_screen(cam, C.CW, C.CH / 2)
    u = np.clip((_XS - lx) / max(1.0, rx - lx), 0, 1)
    wgt = np.clip((u - 0.6) / 0.4, 0, 1) ** 2
    amp = (3.0 + 26.0 * lift) * wgt
    dy = amp * np.sin(2 * np.pi * (u * 1.6 - 2.2 * t)) - 22.0 * lift * wgt
    if amp.max() > 0.3:
        img = cv2.remap(img, _XS, (_YS - dy).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        shade = np.clip(1.0 + 0.08 * np.gradient(dy, axis=1), 0.85, 1.12)
        img *= shade[..., None]
    # morning light from the upper right, a halftone glare, motes in the air
    xs, ys = _XS / W, _YS / H_
    warm = np.clip(0.58 + 0.55 * xs - 0.35 * ys, 0, 1.15)[..., None]
    img = img * (0.74 + 0.30 * warm) * np.array([1.05, 0.99, 0.90], np.float32)
    from mva import fx
    img = fx.motes(img, t, n=28, seed=11, amount=0.22)
    # impact: a burst of dots out of the circle (vermilion + sun yellow)
    sx, sy = to_screen(cam, x6, y6)
    rp = scr_scale(z) * C.R0
    if local < 0.5:
        kb = local / 0.5
        rng = np.random.default_rng(7)
        m1 = np.zeros((H_, W), np.float32)
        m2 = np.zeros((H_, W), np.float32)
        for j in range(80):
            a = rng.uniform(0, 2 * np.pi)
            d = rp * (1.0 + rng.uniform(0.15, 1.4) * (1 - (1 - kb) ** 3))
            rr = max(1, int(rng.uniform(5, 15) * (1 - kb)))
            cv2.circle(m1 if j % 3 else m2, (int(sx + np.cos(a) * d), int(sy + np.sin(a) * d)), rr, 1.0, -1, cv2.LINE_AA)
        img += (H(C.VERM)[None, None] - img) * m1[..., None]
        img += (H('#F5C842')[None, None] - img) * m2[..., None]
    if local < 2 / 24:                              # the relay's sun is still there for two frames
        mm = np.zeros((H_, W), np.float32)
        cv2.circle(mm, (int(sx), int(sy)), int(rp * 0.98), 1.0, -1, cv2.LINE_AA)
        img += (H('#FFF2C8')[None, None] - img) * (mm * (1 - local * 12))[..., None]
    # all six stamps pulse once on 181.43
    if 181.43 <= t < 181.85:
        pk = (t - 181.43) / 0.42
        mm = np.zeros((H_, W), np.float32)
        for (x, y, _) in C.CIRCLES:
            px, py = to_screen(cam, x, y)
            cv2.circle(mm, (int(px), int(py)), int(rp * (1.0 + 0.35 * pk)), 1.0, max(1, int(6 * (1 - pk))), cv2.LINE_AA)
        img += (H(C.VERM)[None, None] - img) * (mm * (1 - pk))[..., None]
    return img


GRAPHIC = {'B-intro-04': intro04, 'B-outro-07': outro07}
OWN_TYPE = {'B-intro-04', 'B-outro-07'}

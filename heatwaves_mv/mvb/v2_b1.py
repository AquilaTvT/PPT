"""MV-B v2, bridge 1 (88.09-111.79): the drowned street, last summer's chalk umbrella, the long shadows, her
print starting to come apart, the swelling moon.

  bridge1-01  the line in bubbles that pop on each mora (lyric column replaced)
  bridge1-02  the chalk umbrella draws itself on the seawall beside her: a sun and a moon under it
  bridge1-03  the line cast as long sunset shadows along the seawall between her and him
  bridge1-04  top-down: under the umbrella a sun and a moon; the wave takes his half; a halftone '?' rises
  bridge1-06  her print's edges begin to scatter into dots
  bridge1-07  the moon swells and its halo pulses faster and faster
"""
import functools
import math

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import BEAT, BEAT0
from . import v2
from . import v2_fx as fx
from .print_fx import hexc as H

W, H_ = 1920, 1080
RAW, OVER, OWN, LYRIC = {}, {}, set(), {}


@functools.lru_cache(maxsize=1)
def _grid():
    return np.mgrid[0:H_, 0:W].astype(np.float32)


def _dream(img, s, t, local):
    from .v2_shots import dream
    return dream(img, s, t, local)


# ------------------------------------------------------------------ chalk
def _chalk(mask, seed=0):
    """chalk on concrete: grainy, broken, slightly soft"""
    rng = np.random.default_rng(seed)
    g = cv2.GaussianBlur(rng.random(mask.shape).astype(np.float32), (0, 0), 0.7)
    g = (g - g.min()) / (g.max() - g.min() + 1e-6)
    m = mask * np.clip((g - 0.22) * 2.2, 0, 1)
    return cv2.GaussianBlur(m, (0, 0), 0.6)


def _stroke(canvas, pts, w, upto=1.0):
    """draw the first `upto` fraction (by length) of a polyline"""
    pts = np.asarray(pts, np.float32)
    if len(pts) < 2 or upto <= 0:
        return canvas
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1] * min(1.0, upto)
    n = int(np.searchsorted(cum, L))
    part = list(pts[:n])
    if n < len(pts):
        a = (L - cum[n - 1]) / max(1e-6, seg[n - 1])
        part.append(pts[n - 1] + (pts[n] - pts[n - 1]) * a)
    if len(part) >= 2:
        cv2.polylines(canvas, [np.round(np.asarray(part) * 4).astype(np.int32)], False, 1.0, w, cv2.LINE_AA, shift=2)
    return canvas


def _circle_pts(cx, cy, r, a0=0.0, a1=360.0, n=60):
    a = np.radians(np.linspace(a0, a1, n))
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], 1)


def sun_moon_strokes(cx, cy, s):
    """chalk strokes for a sun (left) and a moon (right) centred about (cx, cy), scale s; each a list of polylines"""
    sun = [_circle_pts(cx - 1.0 * s, cy, 0.42 * s)]
    for k in range(8):
        a = math.radians(k * 45)
        sun.append(np.float32([[cx - s + math.cos(a) * 0.58 * s, cy + math.sin(a) * 0.58 * s],
                               [cx - s + math.cos(a) * 0.80 * s, cy + math.sin(a) * 0.80 * s]]))
    moon = [np.concatenate([_circle_pts(cx + 1.0 * s, cy, 0.48 * s, 60, 300, 40),
                            _circle_pts(cx + 1.22 * s, cy, 0.40 * s, 290, 70, 40)[::-1]])]
    return sun, moon


def _inpaint_strokes(img, box, v_min=0.80, s_max=0.35, grow=5):
    """remove the generated chalk scribble inside box (x0, y0, x1, y1): bright, pale strokes -> inpaint"""
    x0, y0, x1, y1 = box
    roi = (np.clip(img[y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 2] > v_min * 255) & (hsv[..., 1] < s_max * 255)).astype(np.uint8)
    loc = cv2.GaussianBlur(hsv[..., 2].astype(np.float32), (0, 0), 9)
    dark = (hsv[..., 2].astype(np.float32) < loc - 40).astype(np.uint8)           # their dark outlines
    near = cv2.dilate(m, np.ones((grow * 2 + 1, grow * 2 + 1), np.uint8))
    m = cv2.dilate(np.maximum(m, dark & near), np.ones((grow, grow), np.uint8))
    fixed = cv2.inpaint(roi, m * 255, 5, cv2.INPAINT_TELEA)
    out = img.copy()
    out[y0:y1, x0:x1] = fixed.astype(np.float32) / 255.0
    return out


# ---- bridge1-02: the umbrella draws itself beside her
B102_SURF = [(1430, 826), (1920, 874), (1920, 1012), (1352, 974)]     # the sunlit top of the seawall (plate)
B102_QUAD = [(1505, 852), (1905, 880), (1912, 990), (1478, 972)]      # where the new chalk drawing goes


def _strip_chalk(img, surf_q):
    """remove the chalk the model drew on the seawall: thin strokes brighter than the surface around them (white in
    the sun, pale blue in her shadow), found by a top-hat inside the surface, then inpainted"""
    q = np.asarray(surf_q, np.float32)
    x0, y0 = [int(max(0, v - 8)) for v in q.min(0)]
    x1, y1 = int(min(W, q[:, 0].max() + 8)), int(min(H_, q[:, 1].max() + 8))
    roi = (np.clip(img[y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8)
    g = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    th = cv2.morphologyEx(g, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    inside = np.zeros(g.shape, np.uint8)
    cv2.fillPoly(inside, [np.round((q - [x0, y0]) * 4).astype(np.int32)], 255, cv2.LINE_8, shift=2)
    m = ((th > 22) & (inside > 0)).astype(np.uint8)
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    fixed = cv2.inpaint(roi, m * 255, 4, cv2.INPAINT_TELEA)
    out = img.copy()
    out[y0:y1, x0:x1] = fixed.astype(np.float32) / 255.0
    return out


def bridge1_02(s, t, local):
    img = v2.plate(s, local)
    img = _strip_chalk(img, v2.tracked(s, B102_SURF, local))
    return _dream(img, s, t, local)


def _aiaigasa_canvas(k, cw=560, chh=300):
    """the aiaigasa drawn up to fraction k: canopy, shaft, a little heart, the sun on the left, the moon on the right"""
    canvas = np.zeros((chh, cw), np.float32)
    ax, ay = cw / 2, 26
    canopy = np.float32([[ax - 230, 150], [ax - 120, 70], [ax, ay + 20], [ax + 120, 70], [ax + 230, 150]])
    shaft = np.float32([[ax, ay + 20], [ax, chh - 20]])
    heart = np.concatenate([_circle_pts(ax - 9, ay + 6, 10, 180, 360, 12), np.float32([[ax, ay + 24]]),
                            _circle_pts(ax + 9, ay + 6, 10, 180, 360, 12)[::-1]])
    sun, moon = sun_moon_strokes(ax, 220, 92)
    parts = [(canopy, 0.00, 0.22), (shaft, 0.20, 0.34), (heart, 0.34, 0.42)]
    for j, p in enumerate(sun):
        parts.append((p, 0.44 + j * 0.025, 0.52 + j * 0.025))
    parts.append((moon[0], 0.70, 0.92))
    for p, a0, a1 in parts:
        _stroke(canvas, p, 13, clamp((k - a0) / (a1 - a0)))
    return _chalk(canvas, 2)


def bridge1_02_over(img, s, t, local):
    """the chalk drawn over the print, crisp, lit by the plate (bright in the sun, dim in her shadow)"""
    d = s['end'] - s['start']
    k = clamp((local - 0.25) / (d - 0.6))
    if k <= 0:
        return img
    chalk = _aiaigasa_canvas(k)
    tq = v2.tracked(s, B102_QUAD, local, box=(1360, 830, 1920, 1002))
    mk = fx.quad_paste(np.zeros_like(img), np.repeat(chalk[..., None], 3, 2), tq, feather=0.8)[..., 0]
    plate = v2.plate(s, local)
    lum = cv2.GaussianBlur(plate @ np.float32([0.2126, 0.7152, 0.0722]), (0, 0), 3)
    light = np.clip(lum / 0.55, 0.42, 1.05)[..., None]
    col = H('#F4F0E6')[None, None] * light + H('#AFC3E8')[None, None] * (1 - light) * 0.35
    return img + (col - img) * (mk * 0.95)[..., None]


RAW['B-bridge1-02'] = bridge1_02
OVER['B-bridge1-02'] = bridge1_02_over


# ---- bridge1-04: top-down -- the wave takes his half, a halftone question mark rises in its place
B104_BOX = (330, 585, 650, 790)
B104_SUN, B104_MOON = (430, 690), (565, 690)


def bridge1_04(s, t, local):
    img = v2.plate(s, local)
    dx, dy = v2.tracked(s, [(497, 688)], local, box=B104_BOX)[0] - np.float32([497, 688])     # follow the drawing
    bx = B104_BOX
    img = _inpaint_strokes(img, (int(bx[0] + dx), int(bx[1] + dy), int(bx[2] + dx), int(bx[3] + dy)), v_min=0.70, s_max=0.45, grow=9)
    c = np.zeros((H_, W), np.float32)
    sun, moon = sun_moon_strokes(497 + dx, 688 + dy, 84)
    for p in sun:
        _stroke(c, p, 12)
    wash = clamp((local - 1.05) / 0.55)                       # the wave runs in from the sea (right)
    mc = np.zeros((H_, W), np.float32)
    _stroke(mc, moon[0], 12)
    ys, xs = _grid()
    front = 680 - 260 * wash
    gone = np.clip((xs - front) / 40.0, 0, 1) * (wash > 0)
    mc *= 1 - gone
    chalk = _chalk(np.clip(c + mc, 0, 1), 4)
    img = img + (H('#F7F3EA')[None, None] - img) * (chalk * 0.97)[..., None]
    if wash > 0:                                               # the wet sheen the wave leaves on the right half
        wet = np.clip((xs - front) / 120.0, 0, 1) * np.clip(1 - np.abs(ys - 690) / 260, 0, 1) * (xs < 900) * 0.22
        img = img * (1 - wet[..., None] * 0.6) + H('#FFE2B8')[None, None] * (wet * 0.4)[..., None]
    q = clamp((local - 1.75) / 0.9)                            # the halftone question mark rises
    if q > 0:
        from .v2_typo import glyph_mask
        g = glyph_mask('?', 280, 'garamond')
        gh, gw = g.shape
        per = 9.0
        gx, gy = int(B104_MOON[0] + dx + 40 - gw / 2), int(B104_MOON[1] + dy - gh * 0.62 + 40 * (1 - q))
        yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
        u, v = (xx + yy) / (per * 1.4142), (xx - yy) / (per * 1.4142)
        dd = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
        tone = cv2.GaussianBlur(g, (0, 0), 3) * q
        dots = np.clip((np.sqrt(tone) * 0.7 - dd) * 6 + 0.5, 0, 1) * (tone > 0.03)
        roi = img[gy:gy + gh, gx:gx + gw]
        roi += (H('#1E1418')[None, None] - roi) * (dots[:roi.shape[0], :roi.shape[1]] * 0.95)[..., None]
    return _dream(img, s, t, local)


RAW['B-bridge1-04'] = bridge1_04


# ---- bridge1-01: bubbles; bridge1-03: long shadows; bridge1-06: her edges scatter; bridge1-07: the moon swells
def bridge1_01_over(img, s, t, local):
    from .v2_typo import bubbles
    return bubbles(img, 30, t, x0=1600, y0=160)


B103_QUAD = [(1300, 945), (1690, 945), (1760, 1065), (1240, 1065)]     # on the walkway floor (kf_3)


def bridge1_03_over(img, s, t, local):
    from .v2_typo import long_shadow
    return long_shadow(img, 32, t, v2.tracked(s, B103_QUAD, local), size=150, alpha=0.75)


def bridge1_06_over(img, s, t, local):
    """the print breaks up from the frame edges inward: dots lift off and drift away, the cream paper shows"""
    d = s['end'] - s['start']
    k = clamp((local - 0.3) / (d - 0.3))
    if k <= 0:
        return img
    ys, xs = _grid()
    edge = np.minimum(np.minimum(xs, W - xs) / W, np.minimum(ys, H_ - ys) / H_ * 1.2)
    rng = np.random.default_rng(6)
    nz = cv2.resize(cv2.GaussianBlur(rng.random((H_ // 8, W // 8)).astype(np.float32), (0, 0), 2.0), (W, H_))
    nz = (nz - nz.min()) / (nz.max() - nz.min() + 1e-6)
    front = 0.16 * k ** 1.2
    gone = np.clip((front - edge - 0.06 * nz) / 0.03, 0, 1)
    per = 11.0
    gw, gh = int(W / per) + 1, int(H_ / per) + 1
    cells = cv2.resize(img, (gw, gh), interpolation=cv2.INTER_AREA)
    cg = cv2.resize(gone, (gw, gh), interpolation=cv2.INTER_AREA)
    out = img * (1 - gone[..., None]) + H('#EDE3CF')[None, None] * gone[..., None]
    m = np.zeros((H_, W, 3), np.float32)
    a = np.zeros((H_, W), np.float32)
    cyx = np.argwhere((cg > 0.05) & (cg < 0.98))
    for (cy, cx) in cyx:
        g = cg[cy, cx]
        x, y = (cx + 0.5) * per, (cy + 0.5) * per
        vx, vy = (x - W / 2) / W, (y - H_ / 2) / H_
        drift = 60 * g
        px, py = x + vx * drift + 6 * math.sin(t * 3 + cx), y + vy * drift - 20 * g
        r = per * 0.42 * (1 - 0.6 * g)
        col = cells[cy, cx]
        cv2.circle(m, (int(px * 4), int(py * 4)), int(r * 4), tuple(float(c) for c in col), -1, cv2.LINE_AA, shift=2)
        cv2.circle(a, (int(px * 4), int(py * 4)), int(r * 4), 1.0, -1, cv2.LINE_AA, shift=2)
    return out * (1 - a[..., None]) + m * a[..., None]


def b107_moon():
    return find_moon('B2-bridge1-07')


@functools.lru_cache(maxsize=8)
def find_moon(sid2):
    """the moon on the clip's first frame: the largest bright round blob in the upper half (zoom-1 plate px)"""
    f = v2.footage(sid2)
    rgb = f.at(0.0) if hasattr(f, 'c') else f.img
    y = rgb @ np.float32([0.2126, 0.7152, 0.0722])
    m = (y > 0.55).astype(np.uint8)
    m[H_ // 2:] = 0
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        return (1100.0, 285.0, 165.0)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    cs, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    (cx, cy), r = cv2.minEnclosingCircle(max(cs, key=cv2.contourArea))
    return (float(cx), float(cy), float(r))


def bridge1_07(s, t, local):
    img = v2.plate(s, local)
    d = s['end'] - s['start']
    k = clamp(local / d)
    cx, cy, R = b107_moon()
    m = v2.frame_map(s, local)
    (cx, cy), R = m([(cx, cy)])[0], R * m.scale
    sc = 1.0 + 0.30 * k * k
    # pulses: once a beat at first, then twice, then four times
    nb = (t - BEAT0) / BEAT
    div = 1 if k < 0.4 else (2 if k < 0.75 else 4)
    ph = (nb * div) % 1.0
    pulse = math.exp(-ph * 5.0)
    ys, xs = _grid()
    r = np.hypot(xs - cx, ys - cy)
    inside = np.clip((R * sc * 1.25 - r) / 30.0, 0, 1)
    M = np.float32([[1 / sc, 0, cx * (1 - 1 / sc)], [0, 1 / sc, cy * (1 - 1 / sc)]])
    mx = (xs * M[0, 0] + M[0, 2]).astype(np.float32)
    my = (ys * M[1, 1] + M[1, 2]).astype(np.float32)
    big = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img = img * (1 - inside[..., None]) + big * inside[..., None]
    moon = np.clip((R * sc - r) / 6.0, 0, 1)
    img = img * (1 + moon[..., None] * (0.10 + 0.35 * pulse))
    halo = np.exp(-((r - R * sc) / (60 + 80 * pulse)) ** 2) * (r > R * sc) * (0.10 + 0.30 * pulse)
    img = img + H('#F7E7B8')[None, None] * halo[..., None]
    return _dream(img, s, t, local)


RAW['B-bridge1-07'] = bridge1_07
OVER.update({'B-bridge1-01': bridge1_01_over, 'B-bridge1-03': bridge1_03_over, 'B-bridge1-06': bridge1_06_over})
OWN.update({'B-bridge1-01', 'B-bridge1-03'})
LYRIC.update({'B-bridge1-02': dict(x=200, y=150), 'B-bridge1-05': dict(x=1760), 'B-bridge1-06': dict(x=1780, y=200),
              'B-bridge1-07': dict(x=200, y=150)})


def install():
    v2.RAW.update(RAW)
    v2.OVER.update(OVER)
    v2.V2_OWN_TYPE.update(OWN)
    v2.LYRIC_POS.update(LYRIC)

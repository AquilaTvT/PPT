"""Halftone fireworks for MV-B (dots instead of bloom, like the reference).

  img = burst(img, t, t0, cx, cy, R, kind='chrysanthemum'|'peony'|'ring'|'willow', color, seed)
  img = glyph_burst(img, t, t0, cx, cy, height, ch='君', color)
A burst is a set of sparks flying out on ballistic paths (gravity, drag); every spark is drawn as a round dot
plus an AM-halftone halo (dot screen whose radius falls off from the spark); trails are dotted lines.
"""
import math

import cv2
import numpy as np

from .print_fx import hexc

W, H = 1920, 1080


def _screen_dots(tone, period=12.0, angle=45.0):
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    u = (xs * c + ys * s) / period
    v = (-xs * s + ys * c) / period
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    return np.clip((np.sqrt(np.clip(tone, 0, 1)) * 0.68 - d) * period * 0.6, 0, 1)


_DOT_CACHE = {}


def halo_dots(tone):
    return _screen_dots(tone)


def _sparks(kind, n, seed):
    rng = np.random.default_rng(seed)
    if kind == 'ring':
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        el = np.zeros(n)
    else:
        a = rng.uniform(0, 2 * np.pi, n)
        el = np.arccos(rng.uniform(-1, 1, n)) - np.pi / 2
    sp = np.cos(el) * (0.9 + 0.2 * rng.random(n))
    return a, sp


def burst(img, t, t0, cx, cy, R=420, kind='chrysanthemum', color='#F5C842', color2=None, seed=0, life=2.4,
          n=None, glow=0.55):
    dt = t - t0
    if dt < 0 or dt > life + 0.5:
        return img
    n = n or {'chrysanthemum': 140, 'peony': 90, 'ring': 64, 'willow': 110}.get(kind, 100)
    a, sp = _sparks(kind, n, seed)
    k = 1 - math.exp(-dt * 3.2)          # expansion with drag
    grav = (90 if kind != 'willow' else 220) * dt * dt
    fade = max(0.0, 1 - dt / life)
    xs = cx + np.cos(a) * sp * R * k
    ys = cy + np.sin(a) * sp * R * k * 0.92 + grav
    cov = np.zeros((H, W), np.float32)
    halo = np.zeros((H, W), np.float32)
    tail = 6 if kind in ('chrysanthemum', 'willow') else 2
    for i in range(n):
        x, y = xs[i], ys[i]
        if not (-50 < x < W + 50 and -50 < y < H + 50):
            continue
        r = 5.0 * fade + 1.5
        cv2.circle(cov, (int(x), int(y)), max(1, int(r)), 1.0, -1, cv2.LINE_AA)
        for j in range(1, tail):
            kk = 1 - math.exp(-(dt - j * 0.04) * 3.2) if dt > j * 0.04 else 0
            px = cx + math.cos(a[i]) * sp[i] * R * kk
            py = cy + math.sin(a[i]) * sp[i] * R * kk * 0.92 + (90 if kind != 'willow' else 220) * max(0, dt - j * 0.04) ** 2
            cv2.circle(cov, (int(px), int(py)), max(1, int(r * (1 - j / tail))), 0.8 * (1 - j / tail), -1, cv2.LINE_AA)
        cv2.circle(halo, (int(x), int(y)), int(16 + 6 * fade), 1.0, -1, cv2.LINE_AA)
    flash = math.exp(-dt * 6.0)
    if flash > 0.02:
        cv2.circle(halo, (int(cx), int(cy)), int(R * 0.35 * k + 20), flash, -1, cv2.LINE_AA)
    halo = cv2.GaussianBlur(halo, (0, 0), 10) * fade * glow * 0.8
    dots = halo_dots(halo)
    col = hexc(color)
    out = img + (col[None, None] - img) * (dots * 0.85)[..., None]
    c2 = hexc(color2) if color2 else np.minimum(1.0, col * 1.15 + 0.1)
    out = out + (c2[None, None] - out) * (np.clip(cov * fade * 1.4, 0, 1))[..., None]
    return out


def rocket(img, t, t0, t1, x0, y0, x1, y1, color='#F5C842'):
    """dotted trail from (x0, y0) rising to (x1, y1) between t0 and t1"""
    if t < t0:
        return img
    k = min(1.0, (t - t0) / max(1e-3, t1 - t0))
    e = 1 - (1 - k) ** 2
    hx, hy = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e
    cov = np.zeros((H, W), np.float32)
    n = 24
    for i in range(n):
        f = i / n
        if f > e:
            break
        px, py = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        cv2.circle(cov, (int(px + 3 * math.sin(f * 40)), int(py)), 3, 0.7 * (f / max(e, 1e-3)), -1, cv2.LINE_AA)
    if k < 1:
        cv2.circle(cov, (int(hx), int(hy)), 7, 1.0, -1, cv2.LINE_AA)
    return img + (hexc(color)[None, None] - img) * cov[..., None]


def glyph_burst(img, t, t0, cx, cy, height=600, ch='君', color='#F5C842', hold=0.74, life=2.2, grid=16):
    """sparks fly out from the centre and settle on a grid x grid glyph mask, hold, then drift down"""
    dt = t - t0
    if dt < 0 or dt > life + hold:
        return img
    from mv import text
    key = (ch, grid)
    if key not in _DOT_CACHE:
        import skia
        f = skia.Font(text.typeface('dot'), grid)
        surf = skia.Surface.MakeRaster(skia.ImageInfo.MakeA8(grid, grid))
        c = surf.getCanvas()
        c.clear(0)
        w = f.measureText(ch)
        c.drawString(ch, (grid - w) / 2, grid * 0.88, f, skia.Paint(AntiAlias=False))
        arr = np.empty((grid, grid), np.uint8)
        surf.readPixels(skia.ImageInfo.MakeA8(grid, grid), arr, grid)
        _DOT_CACHE[key] = np.argwhere(arr > 96)
    pts = _DOT_CACHE[key]
    cell = height / grid
    k = min(1.0, 1 - math.exp(-dt * 5.0))
    drift = max(0.0, dt - hold - 0.4) ** 2 * 120
    fade = 1.0 if dt < hold + 0.4 else max(0.0, 1 - (dt - hold - 0.4) / (life - 0.4))
    cov = np.zeros((H, W), np.float32)
    halo = np.zeros((H, W), np.float32)
    for (r, c) in pts:
        tx, ty = cx + (c - grid / 2 + 0.5) * cell, cy + (r - grid / 2 + 0.5) * cell + drift
        x, y = cx + (tx - cx) * k, cy + (ty - cy) * k
        cv2.circle(cov, (int(x), int(y)), int(cell * 0.22) + 1, 1.0, -1, cv2.LINE_AA)
        cv2.circle(halo, (int(x), int(y)), int(cell * 0.9), 1.0, -1, cv2.LINE_AA)
    halo = cv2.GaussianBlur(halo, (0, 0), cell * 0.5) * 0.5 * fade
    out = img + (hexc(color)[None, None] - img) * (halo_dots(halo) * 0.8)[..., None]
    return out + (np.minimum(1, hexc(color) * 1.15 + 0.1)[None, None] - out) * (cov * fade)[..., None]

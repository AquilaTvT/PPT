"""Core rendering primitives for the Heat Waves MV.

Everything is drawn in a virtual 1920x1080 coordinate space.  Vector shapes are
rasterised with Skia into coverage masks, then composited in numpy as "ink"
layers.  Gradients and glows go through an AM halftone screen so that every
frame reads like a riso / screen print — the dot texture is the look.
"""
import functools
import math

import cv2
import numpy as np
import skia

VW, VH = 1920, 1080          # virtual canvas
W, H = 1920, 1080            # output resolution (set_resolution for previews)
S = 1.0                      # W / VW


def set_resolution(w, h):
    global W, H, S
    W, H, S = int(w), int(h), w / VW


class resolution:
    """with resolution(320, 180): ...   temporarily render at another size"""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def __enter__(self):
        self.prev = (W, H)
        set_resolution(self.w, self.h)
        return self

    def __exit__(self, *a):
        set_resolution(*self.prev)
        return False


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------
def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


PAL = {k: hexc(v) for k, v in {
    'paper':  '#F4EAD6',   # cream stock
    'paper2': '#EADCC0',
    'ink':    '#141B3D',   # deep navy key ink
    'navy':   '#1E2A5E',
    'blue':   '#2F5DC4',   # sky ink
    'sky':    '#6FB6E8',
    'teal':   '#2BB3B1',   # mirage / tv glow
    'aqua':   '#7FE3DE',
    'yellow': '#FFCB45',
    'sun':    '#FFE7A3',
    'coral':  '#FF6A55',
    'red':    '#E8383D',
    'pink':   '#FF5C9E',
    'lime':   '#B8E35A',
    'night':  '#0B1030',
    'dusk':   '#5B3C8C',
    'white':  '#FFFDF6',
    'black':  '#06081A',
}.items()}


def mix(a, b, t):
    return a + (b - a) * np.float32(t)


# --------------------------------------------------------------------------
# easing / timing helpers
# --------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lin(t, t0, t1):
    if t1 == t0:
        return 1.0 if t >= t1 else 0.0
    return clamp((t - t0) / (t1 - t0))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    x = clamp(x)
    return 1 - (1 - x) ** p


def ease_in(x, p=3):
    return clamp(x) ** p


def ease_io(x, p=3):
    x = clamp(x)
    return 4 * x ** 3 if (p == 3 and x < 0.5) else (1 - (-2 * x + 2) ** p / 2 if x >= 0.5 else (2 ** (p - 1)) * x ** p)


def back_out(x, s=1.70158):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def elastic_out(x):
    x = clamp(x)
    if x in (0.0, 1.0):
        return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi / 3)) + 1


def hash01(*a):
    """deterministic pseudo random in [0,1) from ints/floats"""
    h = 0
    for v in a:
        h = (h * 1000003) ^ int(v * 9973 + 0.5)
        h &= 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 0x45d9f3b) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF) / float(0x1000000)


# --------------------------------------------------------------------------
# skia coverage masks
# --------------------------------------------------------------------------
class View:
    """2D camera over the 1920x1080 design space: zoom about (cx, cy), rotate."""

    def __init__(self, zoom=1.0, cx=VW / 2, cy=VH / 2, rot=0.0):
        self.zoom, self.cx, self.cy, self.rot = float(zoom), float(cx), float(cy), float(rot)

    def apply(self, c):
        c.translate(VW / 2, VH / 2)
        if self.rot:
            c.rotate(self.rot)
        c.scale(self.zoom, self.zoom)
        c.translate(-self.cx, -self.cy)

    def pt(self, x, y):
        dx, dy = (x - self.cx) * self.zoom, (y - self.cy) * self.zoom
        if self.rot:
            r = math.radians(self.rot)
            dx, dy = dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)
        return VW / 2 + dx, VH / 2 + dy

    def d(self, v):
        return v * self.zoom


IDENT = View()


class Mask:
    """Draw into an A8 surface using 1920x1080 coordinates.

    with Mask() as (c, m): c.drawCircle(...)
    cov = m.cov        # float32 (H, W) in [0, 1]
    """

    def __init__(self, view=None):
        self.info = skia.ImageInfo.MakeA8(W, H)
        self.surf = skia.Surface.MakeRaster(self.info)
        self.c = self.surf.getCanvas()
        self.c.clear(0)
        self.c.scale(S, S)
        if view is not None:
            view.apply(self.c)
        self.cov = None

    def __enter__(self):
        return self.c, self

    def __exit__(self, *a):
        arr = np.empty((H, W), np.uint8)
        self.surf.readPixels(self.info, arr, W)
        self.cov = arr.astype(np.float32) * (1.0 / 255.0)
        return False


def mask(fn, view=None):
    """mask(lambda c: c.drawRect(...)) -> coverage"""
    with Mask(view) as (c, m):
        fn(c)
    return m.cov


def P(alpha=1.0, stroke=None, cap='round', join='round', aa=True, blur=0.0):
    p = skia.Paint(AntiAlias=aa)
    p.setColor4f(skia.Color4f(1, 1, 1, float(alpha)))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(float(stroke))
        p.setStrokeCap({'round': skia.Paint.kRound_Cap, 'butt': skia.Paint.kButt_Cap,
                        'square': skia.Paint.kSquare_Cap}[cap])
        p.setStrokeJoin({'round': skia.Paint.kRound_Join, 'miter': skia.Paint.kMiter_Join,
                         'bevel': skia.Paint.kBevel_Join}[join])
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, float(blur)))
    return p


def path(points, close=True):
    pth = skia.Path()
    pts = list(points)
    if not pts:
        return pth
    pth.moveTo(float(pts[0][0]), float(pts[0][1]))
    for x, y in pts[1:]:
        pth.lineTo(float(x), float(y))
    if close:
        pth.close()
    return pth


def smooth_path(points, close=True, tension=0.5):
    """Catmull-Rom through points -> cubic path"""
    pts = [np.asarray(p, np.float64) for p in points]
    n = len(pts)
    pth = skia.Path()
    if n < 2:
        return pth
    pth.moveTo(*map(float, pts[0]))
    rng = range(n) if close else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (close or i > 0) else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (close or i + 2 < n) else pts[(i + 1) % n]
        c1 = p1 + (p2 - p0) * tension / 3
        c2 = p2 - (p3 - p1) * tension / 3
        pth.cubicTo(float(c1[0]), float(c1[1]), float(c2[0]), float(c2[1]), float(p2[0]), float(p2[1]))
    if close:
        pth.close()
    return pth


# --------------------------------------------------------------------------
# frame & compositing
# --------------------------------------------------------------------------
def _col(color):
    if isinstance(color, str):
        return PAL[color] if color in PAL else hexc(color)
    return np.asarray(color, np.float32)


class Frame:
    def __init__(self, bg='paper'):
        self.a = np.empty((H, W, 3), np.float32)
        self.a[:] = _col(bg)

    # cov: (H, W) float32 coverage ; color: rgb or (H,W,3)
    def over(self, color, cov, alpha=1.0):
        if cov is None:
            return self
        bb = bbox(cov)
        if bb is None:
            return self
        ys, xs = bb
        k = cov[ys, xs]
        if alpha != 1.0:
            k = k * np.float32(alpha)
        c = _col(color)
        if c.ndim == 3:
            c = c[ys, xs]
        sub = self.a[ys, xs]
        sub += (c - sub) * k[..., None]
        return self

    def mul(self, color, cov, alpha=1.0):
        """overprint (multiply) like riso ink"""
        bb = bbox(cov)
        if bb is None:
            return self
        ys, xs = bb
        c = _col(color)
        if c.ndim == 3:
            c = c[ys, xs]
        k = (cov[ys, xs] * np.float32(alpha))[..., None]
        sub = self.a[ys, xs]
        sub *= 1.0 - k * (1.0 - c)
        return self

    def add(self, color, cov, alpha=1.0):
        bb = bbox(cov)
        if bb is None:
            return self
        ys, xs = bb
        c = _col(color)
        if c.ndim == 3:
            c = c[ys, xs]
        sub = self.a[ys, xs]
        sub += c * (cov[ys, xs] * np.float32(alpha))[..., None]
        return self

    def screen(self, color, cov, alpha=1.0):
        bb = bbox(cov)
        if bb is None:
            return self
        ys, xs = bb
        c = _col(color)
        if c.ndim == 3:
            c = c[ys, xs]
        k = (cov[ys, xs] * np.float32(alpha))[..., None]
        sub = self.a[ys, xs]
        sub[:] = 1.0 - (1.0 - sub) * (1.0 - c * k)
        return self

    def image(self, rgb, alpha=None, opacity=1.0):
        """composite a full-frame rgb (H,W,3) with optional alpha (H,W)"""
        if alpha is None:
            if opacity >= 1.0:
                self.a[:] = rgb
            else:
                self.a += (rgb - self.a) * np.float32(opacity)
        else:
            bb = bbox(alpha)
            if bb is None:
                return self
            ys, xs = bb
            k = alpha[ys, xs]
            if opacity < 1.0:
                k = k * np.float32(opacity)
            sub = self.a[ys, xs]
            sub += (rgb[ys, xs] - sub) * k[..., None]
        return self

    def layer(self, L, opacity=1.0):
        return self.image(L.rgb, L.alpha, opacity)

    def copy(self):
        f = Frame.__new__(Frame)
        f.a = self.a.copy()
        return f

    def clip(self):
        np.clip(self.a, 0, 1, out=self.a)
        return self


def bbox(cov, thresh=0.0):
    """(row slice, col slice) of the region where cov > thresh, or None"""
    rows = cov.max(axis=1) > thresh
    if not rows.any():
        return None
    r = np.flatnonzero(rows)
    cols = cov[r[0]:r[-1] + 1].max(axis=0) > thresh
    c = np.flatnonzero(cols)
    return slice(r[0], r[-1] + 1), slice(c[0], c[-1] + 1)


@functools.lru_cache(maxsize=24)
def _screen(cell, angle, w, h):
    th = math.radians(angle)
    cs, sn = math.cos(th), math.sin(th)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xs * cs + ys * sn
    v = -xs * sn + ys * cs
    cu = (np.floor(u / cell) + 0.5) * cell
    cv_ = (np.floor(v / cell) + 0.5) * cell
    du, dv = u - cu, v - cv_
    dist = np.sqrt(du * du + dv * dv).astype(np.float32)
    cx = cu * cs - cv_ * sn
    cy = cu * sn + cv_ * cs
    iy = np.clip(np.round(cy), 0, h - 1).astype(np.int32)
    ix = np.clip(np.round(cx), 0, w - 1).astype(np.int32)
    flat = (iy * w + ix).astype(np.int32)
    return dist, flat


def _dot_radius(c):
    # area-faithful AM dot: r = sqrt(c/pi) until the dots touch, then fill corners
    r = np.sqrt(np.clip(c, 0, 1) * (1.0 / math.pi))
    k = 0.785398
    r = np.where(c > k, 0.5 + (np.clip(c, 0, 1) - k) * (0.2071 / (1 - k)), r)
    return r


def halftone(cov, cell=7.0, angle=45.0, soft=0.9, gain=1.0, center=True, minc=0.0):
    """Convert a continuous coverage map into AM halftone dots (screen space)."""
    cs = cell * S
    dist, flat = _screen(round(cs, 3), float(angle), W, H)
    c = cov
    if gain != 1.0:
        c = c * np.float32(gain)
    if center:
        k = max(1, int(round(cs * 0.75)))
        cb = cv2.blur(c, (k, k)) if k > 1 else c
        c = cb.reshape(-1)[flat].reshape(H, W)
    if minc > 0:
        c = np.where(c < minc, 0, c)
    r = _dot_radius(c) * cs
    out = (r - dist) * (1.0 / max(0.35, soft * S)) + 0.5
    np.clip(out, 0, 1, out=out)
    out[c <= 0.002] = 0
    return out


def ramp(field, colors, cell=7.0, angle=45.0, soft=0.9, presmooth=True):
    """Posterised colour ramp: field in [0,1] picks between adjacent inks of
    `colors`, the in-between values are rendered as AM halftone dots of the next
    ink.  This is the 'limited inks + dot screen' look; returns (H,W,3)."""
    cols = np.stack([_col(c) for c in colors]).astype(np.float32)
    n = len(cols)
    cs = cell * S
    dist, flat = _screen(round(cs, 3), float(angle), W, H)
    v = field
    if presmooth:
        k = max(1, int(round(cs * 0.75)))
        v = cv2.blur(field, (k, k)) if k > 1 else field
    vc = np.clip(v.reshape(-1)[flat].reshape(H, W), 0, 1) * (n - 1)
    lo = np.clip(np.floor(vc), 0, n - 2).astype(np.int32)
    fr = vc - lo
    r = _dot_radius(fr) * cs
    ins = np.clip((r - dist) * (1.0 / max(0.35, soft * S)) + 0.5, 0, 1)
    ins[fr <= 0.002] = 0
    c0 = cols[lo]
    c1 = cols[lo + 1]
    return c0 + (c1 - c0) * ins[..., None]


class Layer:
    """Skia RGBA layer in virtual coords; use for multi-colour vector art.

    with Layer() as (c, L): c.drawCircle(x, y, r, paint(color))
    L.rgb (H,W,3) float, L.alpha (H,W) float  (straight, un-premultiplied)
    """

    def __init__(self, w=None, h=None, scale=None, view=None):
        self.w = w or W
        self.h = h or H
        self.info = skia.ImageInfo.Make(self.w, self.h, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
        self.surf = skia.Surface.MakeRaster(self.info)
        self.c = self.surf.getCanvas()
        self.c.clear(skia.ColorTRANSPARENT)
        self.c.scale(scale or S, scale or S)
        if view is not None:
            view.apply(self.c)

    def __enter__(self):
        return self.c, self

    def __exit__(self, *a):
        arr = np.empty((self.h, self.w, 4), np.uint8)
        self.surf.readPixels(self.info, arr, self.w * 4)
        a = arr[..., 3].astype(np.float32) * (1 / 255.0)
        rgb = arr[..., :3].astype(np.float32) * (1 / 255.0)
        self.alpha = a
        self.rgb = rgb / np.maximum(a[..., None], 1e-4)  # un-premultiply
        np.clip(self.rgb, 0, 1, out=self.rgb)
        return False


def paint(color, alpha=1.0, stroke=None, cap='round', join='round', blur=0.0, aa=True):
    p = P(alpha=alpha, stroke=stroke, cap=cap, join=join, blur=blur, aa=aa)
    c = _col(color)
    p.setColor4f(skia.Color4f(float(c[0]), float(c[1]), float(c[2]), float(alpha)))
    return p


def linescreen(cov, period=6.0, angle=0.0, soft=0.9, phase=0.0):
    """Line halftone (thickness ~ coverage) — used for water, scanlines, rain."""
    ps = period * S
    th = math.radians(angle)
    ys, xs = _grid()
    v = -xs * math.sin(th) + ys * math.cos(th) + phase * S
    d = np.abs((v / ps) % 1.0 - 0.5) * ps
    half = np.clip(cov, 0, 1) * ps * 0.5
    out = (half - d) / max(0.35, soft * S) + 0.5
    return np.clip(out, 0, 1)


@functools.lru_cache(maxsize=6)
def _grid_k(w, h):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return ys, xs


def _grid():
    return _grid_k(W, H)


def coords():
    """virtual-space coordinate grids (y, x) in 1920x1080 units"""
    ys, xs = _grid()
    return ys / S, xs / S


BAYER8 = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
                   [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
                   [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                   [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]], np.float32) / 64.0


def dither(cov, px=3):
    """ordered (Bayer) dither with chunky pixels — the 'pixel' screen"""
    p = max(1, int(round(px * S)))
    small = cv2.resize(cov, (max(1, W // p), max(1, H // p)), interpolation=cv2.INTER_AREA)
    h, w = small.shape
    th = np.tile(BAYER8, (h // 8 + 1, w // 8 + 1))[:h, :w] + 1 / 128
    out = (small > th).astype(np.float32)
    return cv2.resize(out, (W, H), interpolation=cv2.INTER_NEAREST)


def radial(cx, cy, r, falloff=2.0, inner=0.0, view=None, sx=1.0, sy=1.0):
    """coverage 1 at centre -> 0 at radius r (virtual units)"""
    if view is not None:
        cx, cy = view.pt(cx, cy)
        r = view.d(r)
    ys, xs = coords()
    if sx != 1.0 or sy != 1.0:
        d = np.sqrt(((xs - cx) / sx) ** 2 + ((ys - cy) / sy) ** 2) / max(r, 1e-3)
        v = np.clip(1 - (d - inner) / max(1e-3, 1 - inner), 0, 1)
        return (v ** falloff).astype(np.float32)
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / max(r, 1e-3)
    v = np.clip(1 - (d - inner) / max(1e-3, 1 - inner), 0, 1)
    return (v ** falloff).astype(np.float32)


def vgrad(y0, y1, v0=1.0, v1=0.0, ease=None):
    ys, _ = coords()
    t = np.clip((ys - y0) / (y1 - y0), 0, 1)
    if ease == 'smooth':
        t = t * t * (3 - 2 * t)
    elif isinstance(ease, (int, float)):
        t = t ** ease
    return (v0 + (v1 - v0) * t).astype(np.float32)


def hgrad(x0, x1, v0=1.0, v1=0.0):
    _, xs = coords()
    t = np.clip((xs - x0) / (x1 - x0), 0, 1)
    return (v0 + (v1 - v0) * t).astype(np.float32)


def value_noise(shape, scale, seed=0, octaves=4, persistence=0.5):
    """fBm value noise at output resolution, scale in output pixels"""
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot, sc = 1.0, 0.0, scale
    for _ in range(octaves):
        gh, gw = max(2, int(h / sc) + 2), max(2, int(w / sc) + 2)
        g = rng.random((gh, gw)).astype(np.float32)
        out += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= persistence
        sc /= 2
    return out / tot


@functools.lru_cache(maxsize=3)
def _paper_k(w, h):
    s = w / VW
    n1 = value_noise((h, w), 220 * s, seed=11, octaves=5)
    rng = np.random.default_rng(5)
    fib = rng.random((h, w)).astype(np.float32)
    fib = cv2.GaussianBlur(fib, (0, 0), sigmaX=6 * s, sigmaY=0.6 * s)
    fib = (fib - fib.mean()) / (fib.std() + 1e-6)
    p = (n1 - 0.5) * 0.6 + fib * 0.12
    return p.astype(np.float32)


def _paper():
    return _paper_k(W, H)


@functools.lru_cache(maxsize=3)
def _grain_k(w, h):
    rng = np.random.default_rng(7)
    bank = []
    for _ in range(6):
        g = rng.standard_normal((h, w)).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 0.7 * w / VW)
        bank.append(g / (g.std() + 1e-6))
    return bank


def _grain_bank():
    return _grain_k(W, H)


def _vignette(strength_key):
    return _vignette_k(strength_key, W, H)


@functools.lru_cache(maxsize=8)
def _vignette_k(strength_key, w, h):
    ys, xs = _grid_k(w, h)
    nx = (xs / w - 0.5) * 2
    ny = (ys / h - 0.5) * 2
    d = np.sqrt(nx * nx * 0.8 + ny * ny)
    return np.clip(1 - strength_key / 100.0 * np.clip(d - 0.35, 0, None) ** 1.6, 0, 1).astype(np.float32)


def finish(img, frame_idx=0, paper=0.06, grain=0.035, vignette=28, dark_grain=None):
    """Global print finishing: paper fibres, film grain (on twos), vignette."""
    a = img
    if paper:
        a = a * (1.0 + _paper()[..., None] * np.float32(paper))
    if grain:
        g = _grain_bank()[(frame_idx // 2) % 6]
        lum = a.mean(axis=2, keepdims=True)
        # grain strongest in midtones
        wgt = 4 * lum * (1 - lum) + 0.25
        a = a + g[..., None] * np.float32(grain) * wgt
    if vignette:
        a = a * _vignette(int(vignette))[..., None]
    return np.clip(a, 0, 1)


# --------------------------------------------------------------------------
# image-space effects
# --------------------------------------------------------------------------
def heat_haze(img, t, amp=6.0, wavelength=38.0, speed=1.6, region=None, vamp=1.5, seed=0):
    """Vertical-wavelength shimmer (the signature heat-wave distortion).

    region: optional (H,W) weight map for where the haze acts.
    """
    ys, xs = _grid()
    wl = wavelength * S
    ph = t * speed * 2 * math.pi
    dx = (np.sin(ys / wl * 2 * math.pi - ph + seed) * 0.65 +
          np.sin(ys / (wl * 0.43) * 2 * math.pi - ph * 1.7 + 1.3 + seed) * 0.35) * amp * S
    dy = np.sin(xs / (wl * 3.1) * 2 * math.pi + ph * 0.8 + seed) * vamp * S
    if region is not None:
        dx = dx * region
        dy = dy * region
    mx = (xs + dx).astype(np.float32)
    my = (ys + dy).astype(np.float32)
    return cv2.remap(img, mx, my, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def displace(img, dx, dy):
    ys, xs = _grid()
    return cv2.remap(img, (xs + dx).astype(np.float32), (ys + dy).astype(np.float32),
                     interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def blur(img, sigma):
    if sigma <= 0.05:
        return img
    return cv2.GaussianBlur(img, (0, 0), sigma * S)


def motion_blur(img, dx, dy=0.0, taps=9):
    """directional blur along (dx,dy) virtual px"""
    if abs(dx) + abs(dy) < 0.5:
        return img
    acc = np.zeros_like(img)
    for i in range(taps):
        f = i / (taps - 1) - 0.5
        M = np.float32([[1, 0, dx * f * S], [0, 1, dy * f * S]])
        acc += cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / taps


def zoom_blur(img, amount, cx=VW / 2, cy=VH / 2, taps=10):
    if amount < 0.002:
        return img
    acc = np.zeros_like(img)
    for i in range(taps):
        s = 1 + amount * i / (taps - 1)
        M = np.float32([[s, 0, (1 - s) * cx * S], [0, s, (1 - s) * cy * S]])
        acc += cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / taps


def affine(img, scale=1.0, rot=0.0, tx=0.0, ty=0.0, cx=VW / 2, cy=VH / 2, border=cv2.BORDER_REFLECT):
    """scale/rotate around (cx,cy) then translate (virtual units)"""
    M = cv2.getRotationMatrix2D((cx * S, cy * S), rot, scale)
    M[0, 2] += tx * S
    M[1, 2] += ty * S
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border)


def chroma_shift(img, dx=3.0, dy=0.0):
    out = img.copy()
    M1 = np.float32([[1, 0, dx * S], [0, 1, dy * S]])
    M2 = np.float32([[1, 0, -dx * S], [0, 1, -dy * S]])
    out[..., 0] = cv2.warpAffine(img[..., 0], M1, (W, H), borderMode=cv2.BORDER_REFLECT)
    out[..., 2] = cv2.warpAffine(img[..., 2], M2, (W, H), borderMode=cv2.BORDER_REFLECT)
    return out


def lum(img):
    return (img[..., 0] * 0.299 + img[..., 1] * 0.587 + img[..., 2] * 0.114).astype(np.float32)


def flash(img, amount, color='white'):
    if amount <= 0:
        return img
    return img + (_col(color) - img) * np.float32(clamp(amount))

"""Reusable 2D pieces for MV-B recipes (all operate on float32 RGB 1920x1080)."""
import math

import cv2
import numpy as np

from mva import fx
from .print_fx import hexc

W, H = 1920, 1080
_YS, _XS = np.mgrid[0:H, 0:W].astype(np.float32)


def mirage_band(img, t, y, x0=0, x1=W, height=26.0, amp=3.0, pulse=0.0, tint='#C9D3DC', strength=0.85):
    """silver mirage: the strip above horizon y is mirrored into a band below it, rippling"""
    hgt = height * (1 + 0.35 * pulse)
    yy = np.clip(2 * y - _YS + np.sin(_XS / 23.0 + t * 7.0) * amp * 0.4, 0, H - 1)
    xx = _XS + np.sin(_YS / 3.0 + t * 11.0) * amp
    refl = cv2.remap(img, xx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    m = ((_YS >= y) & (_YS < y + hgt) & (_XS >= x0) & (_XS < x1)).astype(np.float32)
    m *= np.clip(1 - (_YS - y) / max(1, hgt), 0, 1) ** 0.6
    m = cv2.GaussianBlur(m, (0, 0), 1.2)
    refl = refl * 0.75 + hexc(tint)[None, None] * 0.25
    return img + (refl - img) * (m * strength)[..., None]


def dot_person(img, x, y, h, t, colors=('#1E2550', '#F6F2E7', '#D9402B', '#1A1416'), run=True, reflect_y=None, alpha=1.0):
    """tiny printed figure (body navy, white top, red dot, black head) at foot position (x, y), height h px"""
    bob = abs(math.sin(t * 9.0)) * h * 0.04 if run else 0.0
    layer = np.zeros((H, W), np.float32)
    cols = []

    def blob(fn, col):
        m = np.zeros((H, W), np.uint8)
        fn(m)
        cols.append((col, m.astype(np.float32) / 255.0))
    yb = y - bob
    blob(lambda m: cv2.ellipse(m, (int(x), int(yb - h * 0.33)), (int(h * 0.16), int(h * 0.3)), 0, 0, 360, 255, -1, cv2.LINE_AA), colors[0])
    blob(lambda m: cv2.ellipse(m, (int(x), int(yb - h * 0.55)), (int(h * 0.15), int(h * 0.14)), 0, 0, 360, 255, -1, cv2.LINE_AA), colors[1])
    blob(lambda m: cv2.circle(m, (int(x), int(yb - h * 0.52)), max(1, int(h * 0.05)), 255, -1, cv2.LINE_AA), colors[2])
    blob(lambda m: cv2.circle(m, (int(x), int(yb - h * 0.82)), max(2, int(h * 0.15)), 255, -1, cv2.LINE_AA), colors[3])
    out = img
    for col, m in cols:
        out = out + (hexc(col)[None, None] - out) * (m * alpha)[..., None]
        if reflect_y is not None:
            mr = cv2.flip(m, 0)
            shift = int(2 * reflect_y - H)
            mr = np.roll(mr, shift, axis=0) * 0.45 * alpha
            mr *= (_YS > reflect_y).astype(np.float32)
            out = out + (hexc(col)[None, None] - out) * mr[..., None]
    return out


def dir_blur(img, dx, dy=0.0, taps=9):
    if abs(dx) < 0.5 and abs(dy) < 0.5:
        return img
    acc = np.zeros_like(img)
    for i in range(taps):
        k = (i / (taps - 1) - 0.5)
        M = np.float32([[1, 0, dx * k], [0, 1, dy * k]])
        acc += cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / taps


def haze_lower(img, t, amp=0.006, y0=520):
    reg = np.clip((_YS - y0) / 200.0, 0, 1)
    return fx.heat_haze(img, t, amp=amp, region=reg)


def beat_pulse(t, beats, decay=0.12):
    return fx.pulse(t, beats, decay)


def dot_flash(img, k, color='#F5C842', period=24.0):
    """網点フラッシュ: full-frame dots shrinking to 0 (k: 1 = start .. 0 = gone)"""
    if k <= 0:
        return img
    c, s = math.cos(math.radians(45)), math.sin(math.radians(45))
    u = (_XS * c + _YS * s) / period
    v = (-_XS * s + _YS * c) / period
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    m = np.clip((0.7 * k - d) * period * 0.5, 0, 1)
    return img + (hexc(color)[None, None] - img) * m[..., None]


_GP = {}


def glyph_patch(ch, size=70, font='mincho', stroke=7.0):
    """rasterised single glyph (fill, stroke) coverage patches, (2*size)^2, glyph centred"""
    key = (ch, size, font, stroke)
    if key not in _GP:
        from mv import text
        n = int(size * 2)
        g = dict(ch=ch, cx=n / 2, cy=n / 2, rot=90.0 if ch in text.ROTATE_V else 0.0, size=size, font=font, i=0, col=0)
        f, s = text.render_glyphs([g], stroke=stroke)
        _GP[key] = (f[:n, :n].copy(), s[:n, :n].copy())
    return _GP[key]


def map_glyph(img, ch, x, y, size=70, angle=0.0, scale=1.0, fill='#F6F2E7', stroke='#1E2550', sw=7.0, font='mincho', alpha=1.0,
              sx=1.0):
    """map-label glyph (cream fill, ink outline) centred at (x, y), rotated by angle degrees (ccw). Draws in place."""
    if scale <= 0.01 or alpha <= 0.003:
        return img
    f, s = glyph_patch(ch, size, font, sw)
    n = f.shape[0]
    m = int(n * max(1.0, scale) * 1.5) + 2
    xi, yi = int(round(x)), int(round(y))
    x0, y0 = xi - m // 2, yi - m // 2
    M = cv2.getRotationMatrix2D((n / 2, n / 2), angle, scale)
    if sx != 1.0:                                   # horizontal flip / squeeze about the glyph centre
        M[:, 0] *= sx
        M[:, 2] += (1 - sx) * (M[:, 0] / sx * n / 2) if sx != 0 else 0
    M[0, 2] += m / 2 - n / 2 + (x - xi) - (m / 2 - m // 2)
    M[1, 2] += m / 2 - n / 2 + (y - yi) - (m / 2 - m // 2)
    ax0, ay0, ax1, ay1 = max(0, x0), max(0, y0), min(W, x0 + m), min(H, y0 + m)
    if ax0 >= ax1 or ay0 >= ay1:
        return img
    for cov, col in ((s, stroke), (f, fill)):
        w = cv2.warpAffine(cov, M, (m, m))[ay0 - y0: ay1 - y0, ax0 - x0: ax1 - x0] * alpha
        roi = img[ay0:ay1, ax0:ax1]
        roi += (hexc(col)[None, None] - roi) * w[..., None]
    return img


def halo(img, x, y, r=40.0, color='#7FC8B8', strength=0.9, period=9.0):
    """printed halftone halo around (x, y): dots shrink with distance (screen-locked 45 deg screen)"""
    x0, y0, x1, y1 = int(max(0, x - r - 2)), int(max(0, y - r - 2)), int(min(W, x + r + 3)), int(min(H, y + r + 3))
    if x0 >= x1 or y0 >= y1:
        return img
    ys, xs = _YS[y0:y1, x0:x1], _XS[y0:y1, x0:x1]
    tone = np.clip(1.0 - np.sqrt((xs - x) ** 2 + (ys - y) ** 2) / r, 0, 1) ** 1.3 * strength
    c, s = math.cos(math.radians(45)), math.sin(math.radians(45))
    u = (xs * c + ys * s) / period
    v = (-xs * s + ys * c) / period
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    m = np.clip((np.sqrt(tone) * 0.62 - d) * period * 0.7, 0, 1)
    roi = img[y0:y1, x0:x1]
    roi += (hexc(color)[None, None] - roi) * m[..., None]
    return img


def dot_walker(img, x, y, h, phase, colors=('#1A1416', '#F6F2E7', '#1E2550', '#1A1416'), pitch=None, alpha=1.0, run=False):
    """a pedestrian-signal style figure made of round LED dots, walking (phase in cycles). (x, y) = feet.
    colors: head, shirt, trousers, shoes. The figure is built from capsules then sampled onto a dot grid."""
    p = pitch or max(3.0, h / 15.0)
    s = 4                                          # supersample for the capsule masks
    W_, H_ = int(h * 1.2), int(h * 1.15)
    ox, oy = W_ / 2, H_ - h * 0.04
    layers = {k: np.zeros((H_ * s // 4 * 4 // 4 * 1, W_), np.float32) for k in ()}
    m = {k: np.zeros((H_, W_), np.uint8) for k in ('head', 'shirt', 'trousers', 'shoes')}
    a = 2 * np.pi * phase
    sw = (0.55 if run else 0.38) * np.sin(a)
    def cap(name, x0, y0, x1, y1, w):
        cv2.line(m[name], (int(ox + x0 * h), int(oy - y0 * h)), (int(ox + x1 * h), int(oy - y1 * h)), 255, max(1, int(w * h)), cv2.LINE_AA)
    hip, sh = 0.50, 0.80
    bob = 0.012 * np.cos(2 * a)
    # legs (thigh + shin), opposite phase
    for sg in (1, -1):
        th = sg * sw
        kx, ky = np.sin(th) * 0.24, hip - np.cos(th) * 0.24
        sh_a = th - (0.35 if sg * np.sin(a) < 0 else 0.05)
        fx, fy = kx + np.sin(sh_a) * 0.24, ky - np.cos(sh_a) * 0.24
        cap('trousers', 0, hip + bob, kx, ky + bob, 0.14)
        cap('trousers', kx, ky + bob, fx, max(0.03, fy + bob), 0.12)
        cap('shoes', fx - 0.01, max(0.03, fy + bob), fx + 0.08, max(0.03, fy + bob), 0.08)
    cap('shirt', 0, hip + 0.02 + bob, 0, sh + bob, 0.25)
    for sg in (1, -1):                              # arms swing against the legs
        th = -sg * sw * 0.9
        ex, ey = np.sin(th) * 0.16, sh - 0.02 - np.cos(th) * 0.16
        hx, hy = ex + np.sin(th + 0.3) * 0.15, ey - np.cos(th + 0.3) * 0.15
        cap('shirt', 0, sh - 0.02 + bob, ex, ey + bob, 0.10)
        cap('head', ex, ey + bob, hx, hy + bob, 0.075)
    cv2.circle(m['head'], (int(ox), int(oy - (0.91 + bob) * h)), int(0.105 * h), 255, -1, cv2.LINE_AA)
    # sample onto a dot grid (screen-locked so the dots don't swim)
    x0, y0 = int(x - ox), int(y - oy)
    out = img
    for name, col in zip(('trousers', 'shoes', 'shirt', 'head'), (colors[2], colors[3], colors[1], colors[0])):
        mm = m[name].astype(np.float32) / 255.0
        ys_, xs_ = np.mgrid[0:H_, 0:W_].astype(np.float32)
        gx, gy = (xs_ + x0) / p, (ys_ + y0) / p
        cxs, cys = (np.floor(gx) + 0.5) * p - x0, (np.floor(gy) + 0.5) * p - y0
        cov = cv2.remap(cv2.GaussianBlur(mm, (0, 0), p * 0.35), cxs.astype(np.float32), cys.astype(np.float32), cv2.INTER_LINEAR)
        d = np.sqrt((gx - np.floor(gx) - 0.5) ** 2 + (gy - np.floor(gy) - 0.5) ** 2)
        dots = np.clip((0.44 * np.sqrt(np.clip(cov * 1.6, 0, 1)) - d) * p * 0.9, 0, 1) * alpha
        ax0, ay0, ax1, ay1 = max(0, x0), max(0, y0), min(W, x0 + W_), min(H, y0 + H_)
        if ax0 >= ax1 or ay0 >= ay1:
            continue
        dd = dots[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0]
        roi = out[ay0:ay1, ax0:ax1]
        roi += (hexc(col)[None, None] - roi) * dd[..., None]
    return out


def gull(img, x, y, span, flap, color='#1A1416', alpha=0.85):
    """a printed gull: two arcs, wings flapping (flap 0..1)"""
    m = np.zeros((H, W), np.float32)
    lift = (0.5 - abs(flap % 1.0 - 0.5)) * 2
    hy = span * (0.12 + 0.28 * lift)
    for sg in (-1, 1):
        pts = np.array([[x, y], [x + sg * span * 0.25, y - hy], [x + sg * span * 0.5, y - hy * 0.4]], np.float32)
        curve = [(1 - u) ** 2 * pts[0] + 2 * (1 - u) * u * pts[1] + u ** 2 * pts[2] for u in np.linspace(0, 1, 10)]
        cv2.polylines(m, [np.array(curve, np.int32)], False, 1.0, max(2, int(span * 0.06)), cv2.LINE_AA)
    img += (hexc(color)[None, None] - img) * (m * alpha)[..., None]
    return img

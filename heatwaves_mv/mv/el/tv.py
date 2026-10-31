"""CRT television: low-res dithered pictures, scanlines, phosphor mask, static."""
import functools
import math

import cv2
import numpy as np

from .. import core
from ..core import BAYER8

# 16-colour "TV" palette drawn from the MV inks
TV_PAL = ['#06081A', '#141B3D', '#1E2A5E', '#2F5DC4', '#6FB6E8', '#DDEFF4', '#FFFDF6', '#F4EAD6',
          '#FFCB45', '#FF6A55', '#E8383D', '#2BB3B1', '#7FE3DE', '#5FA746', '#B9C3EA', '#5B3C8C']


@functools.lru_cache(maxsize=8)
def _pal(key):
    return np.stack([core._col(c) for c in key]).astype(np.float32)


def ordered_dither(img, palette=tuple(TV_PAL), spread=0.18):
    """nearest-palette quantisation with an 8x8 Bayer offset (chunky retro look)"""
    h, w = img.shape[:2]
    pal = _pal(tuple(palette))
    th = np.tile(BAYER8, (h // 8 + 1, w // 8 + 1))[:h, :w] - 0.5
    x = img + th[..., None] * spread
    d = ((x[:, :, None, :] - pal[None, None]) ** 2).sum(-1)
    return pal[d.argmin(-1)]


def lowres(fn, t, w=320, h=180, dither=True, palette=tuple(TV_PAL), spread=0.18):
    """render fn(t) -> rgb at a tiny resolution, dither, then nearest-upscale to the frame"""
    with core.resolution(w, h):
        img = fn(t)
        if hasattr(img, 'a'):
            img = img.a
        img = np.clip(img, 0, 1)
        if dither:
            img = ordered_dither(img, palette, spread)
    return img


def upscale_nearest(img, w=None, h=None):
    return cv2.resize(img, (w or core.W, h or core.H), interpolation=cv2.INTER_NEAREST)


def static(t, w=240, h=135, seed=0, bars=True):
    rng = np.random.default_rng(int(t * 30) + seed * 7919)
    n = rng.random((h, w)).astype(np.float32)
    if bars:
        y = (np.arange(h)[:, None] / h + t * 0.7) % 1.0
        n = n * (0.75 + 0.25 * np.sin(y * math.pi * 2) ** 8)
    img = np.repeat(n[..., None], 3, 2)
    img = img * core._col('#DDEFF4')[None, None] * 0.9 + core._col('#141B3D') * (1 - img) * 0.6
    return img


@functools.lru_cache(maxsize=4)
def _barrel(w, h, k):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = xs / w * 2 - 1
    ny = ys / h * 2 - 1
    r2 = nx * nx + ny * ny
    f = 1 + k * r2
    mx = ((nx * f + 1) * 0.5 * w).astype(np.float32)
    my = ((ny * f + 1) * 0.5 * h).astype(np.float32)
    inside = ((np.abs(nx * f) <= 1) & (np.abs(ny * f) <= 1)).astype(np.float32)
    # rounded corner falloff
    edge = np.clip((1 - np.maximum(np.abs(nx * f), np.abs(ny * f))) * 40, 0, 1)
    return mx, my, inside * edge


@functools.lru_cache(maxsize=4)
def _mask_pattern(w, h, period):
    xs = np.arange(w)
    ys = np.arange(h)
    ph = (xs // max(1, period)) % 3
    m = np.ones((h, w, 3), np.float32) * 0.78
    for c in range(3):
        m[:, ph == c, c] = 1.08
    scan = 0.8 + 0.2 * (np.cos((ys / max(1, period * 1.3)) * 2 * math.pi) * 0.5 + 0.5)
    return m * scan[:, None, None]


def crt(img, t=0.0, curve=0.06, scan=1.0, glow=0.45, vignette=0.55, flicker=0.03, roll=0.0, noise=0.03,
        bright=1.0, chroma=1.5):
    """full-frame CRT treatment"""
    h, w = img.shape[:2]
    out = img * bright
    if chroma:
        out = core.chroma_shift(out, chroma, 0)
    if glow:
        out = out + core.blur(np.clip(out - 0.45, 0, 1), 10) * glow * 1.6
    period = max(1, int(round(3 * core.S)))
    out = out * (1 - scan + scan * _mask_pattern(w, h, period))
    if roll:
        ys = np.arange(h)[:, None, None] / h
        band = np.exp(-(((ys - (t * roll) % 1.3 + 0.15)) / 0.06) ** 2) * 0.12
        out = out + band
    if noise:
        rng = np.random.default_rng(int(t * 30))
        out = out + rng.standard_normal((h, w, 1)).astype(np.float32) * noise
    if flicker:
        out = out * (1 + flicker * math.sin(t * 120.0))
    if curve:
        mx, my, inside = _barrel(w, h, curve)
        out = cv2.remap(out.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        out = out * inside[..., None]
    if vignette:
        ys, xs = core._grid_k(w, h)
        nx = xs / w * 2 - 1
        ny = ys / h * 2 - 1
        v = np.clip(1 - vignette * (nx * nx * 0.6 + ny * ny * 0.8) ** 1.5, 0, 1)
        out = out * v[..., None]
    return np.clip(out, 0, 1.2)


def power_on(img, p):
    """p 0 -> 1 : dot -> line -> full picture"""
    h, w = img.shape[:2]
    out = np.zeros_like(img)
    if p <= 0:
        return out
    sx = core.ease_out(core.clamp(p / 0.35), 3)
    sy = core.ease_out(core.clamp((p - 0.3) / 0.7), 4)
    w2 = max(2, int(w * sx))
    h2 = max(2, int(h * max(0.004, sy)))
    small = cv2.resize(img, (w2, h2), interpolation=cv2.INTER_AREA)
    bright = 1 + (1 - sy) * 3
    y0, x0 = (h - h2) // 2, (w - w2) // 2
    out[y0:y0 + h2, x0:x0 + w2] = np.clip(small * bright, 0, 1)
    out = out + core.blur(out, 8) * (1 - sy) * 1.5
    return np.clip(out, 0, 1)


def power_off(img, p):
    return power_on(img, 1 - p)


def place_screen(f, content, quad, glow=0.6, glass='#7FE3DE', glass_amt=0.0):
    """map a full-res content image into a quad (4 virtual-space points, TL TR BR BL)"""
    h, w = content.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[x * core.S, y * core.S] for x, y in quad])
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(content.astype(np.float32), M, (core.W, core.H), flags=cv2.INTER_LINEAR)
    m = cv2.warpPerspective(np.ones((h, w), np.float32), M, (core.W, core.H), flags=cv2.INTER_LINEAR)
    f.image(warped, m)
    if glass_amt:
        f.screen(glass, m * 0.0 + m, alpha=glass_amt)
    return m

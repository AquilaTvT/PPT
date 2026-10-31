"""MV-B print finish + LED dot-matrix boards.

finish(img, frame_idx): fixed paper texture (multiply), registration jitter (whole frame jumps ~1 px every
3 frames, like the reference), corner darkening to ~77%, fine grain.
led_board(text, ...): dot-matrix LED rendering of any text (Japanese via DotGothic16) -> (rgb, alpha).
"""
import functools

import cv2
import numpy as np

from mv import text as mtext

W, H = 1920, 1080


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


@functools.lru_cache(maxsize=1)
def paper(seed=11):
    r = np.random.default_rng(seed)
    n = r.standard_normal((H // 2, W // 2)).astype(np.float32)
    n = cv2.resize(cv2.GaussianBlur(n, (0, 0), 0.8), (W, H))
    fib = np.zeros((H, W), np.float32)
    for _ in range(1600):
        x, y = r.uniform(0, W), r.uniform(0, H)
        a = r.uniform(0, np.pi)
        l = r.uniform(6, 26)
        cv2.line(fib, (int(x), int(y)), (int(x + np.cos(a) * l), int(y + np.sin(a) * l)), float(r.uniform(0.3, 1.0)), 1, cv2.LINE_AA)
    fib = cv2.GaussianBlur(fib, (0, 0), 0.6)
    tex = 1.0 - 0.035 * np.clip(n, -2, 2) * 0.5 - 0.05 * fib
    blot = cv2.resize(r.standard_normal((9, 16)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    tex *= 1.0 - 0.025 * blot
    return np.clip(tex, 0.85, 1.05).astype(np.float32)


@functools.lru_cache(maxsize=1)
def corner_mask(strength=0.23):
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xs - W / 2) / (W / 2)) ** 2 + ((ys - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
    return (1.0 - strength * np.clip(d, 0, 1) ** 2.4).astype(np.float32)


def jitter_offset(frame_idx, every=3):
    k = frame_idx // every
    h = np.sin(k * 12.9898) * 43758.5453
    fx = h - np.floor(h)
    h2 = np.sin(k * 78.233) * 12345.678
    fy = h2 - np.floor(h2)
    return int(round(fx * 2 - 1)), int(round(fy * 2 - 1))


def finish(img, frame_idx, paper_amt=1.0, grain=0.018, jitter=True, corners=True):
    out = img
    if jitter:
        dx, dy = jitter_offset(frame_idx)
        if dx or dy:
            out = np.roll(out, (dy, dx), axis=(0, 1))
    if paper_amt:
        p = paper()
        out = out * (1 + (p - 1) * paper_amt)[..., None]
    if corners:
        out = out * corner_mask()[..., None]
    if grain:
        r = np.random.default_rng(frame_idx // 2 + 7)
        g = r.standard_normal((H // 2, W // 2)).astype(np.float32)
        out = out + cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)[..., None] * grain
    return out


def led_board(txt, cols=None, rows=16, dot=10, on='#7FC8B8', off='#16302E', bg='#0B1414', font='dot',
              scroll=0.0, glow=0.55):
    """dot-matrix board: text rasterised to a `rows`-tall grid, each cell drawn as a round LED.
    scroll (cells) shifts the text left (marquee). Returns rgb (h, w, 3), alpha (h, w)."""
    size = rows * 1.0
    glyphs, width = mtext.layout_h(txt, 0, rows / 2, size, font, tracking=0.05, align='left')
    gw = int(np.ceil(width)) + 4
    ncols = cols or gw
    # rasterise at grid resolution (each glyph unit = one LED)
    from mv.core import Mask
    import skia
    surf = skia.Surface.MakeRaster(skia.ImageInfo.MakeA8(max(gw, ncols) + int(abs(scroll)) + 4, rows))
    c = surf.getCanvas()
    c.clear(0)
    c.translate(2 - scroll, 0)
    for g in glyphs:
        f = mtext.font(g['font'], g['size'])
        w, b = mtext.char_box(f, g['ch'])
        c.drawString(g['ch'], g['cx'] - w / 2, g['base'] if 'base' in g else rows * 0.85, f, skia.Paint(AntiAlias=False))
    arr = np.empty((rows, surf.width()), np.uint8)
    surf.readPixels(skia.ImageInfo.MakeA8(surf.width(), rows), arr, surf.width())
    grid = (arr[:, :ncols] > 96).astype(np.float32)
    h, w = rows * dot, ncols * dot
    lit = cv2.resize(grid, (w, h), interpolation=cv2.INTER_NEAREST)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    cell = np.sqrt(((xs % dot) - dot / 2 + 0.5) ** 2 + ((ys % dot) - dot / 2 + 0.5) ** 2)
    disc = np.clip((dot * 0.36 - cell) * 1.5, 0, 1)
    rgb = np.empty((h, w, 3), np.float32)
    rgb[:] = hexc(bg)
    rgb = rgb + (hexc(off) - rgb) * disc[..., None]
    on_m = (disc * lit)[..., None]
    rgb = rgb + (hexc(on) - rgb) * on_m
    if glow:
        gl = cv2.GaussianBlur(lit * 1.0, (0, 0), dot * 0.9)
        rgb = rgb + hexc(on)[None, None] * gl[..., None] * glow * 0.6
    return np.clip(rgb, 0, 1), np.ones((h, w), np.float32)

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
    tex = 1.0 - 0.02 * np.clip(n, -2, 2) * 0.5 - 0.035 * fib
    blot = cv2.resize(r.standard_normal((9, 16)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    tex *= 1.0 - 0.012 * blot
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


# ---------------------------------------------------------------- generic dot matrices (clocks, scoreboards)
SEG = {  # seven-segment map per digit: a b c d e f g
    '0': 'abcdef', '1': 'bc', '2': 'abdeg', '3': 'abcdg', '4': 'bcfg', '5': 'acdfg', '6': 'acdefg', '7': 'abc',
    '8': 'abcdefg', '9': 'abcdfg', ' ': '', '-': 'g'}


def seg_digit(ch, w=7, h=13):
    g = np.zeros((h, w), bool)
    m = h // 2
    on = SEG.get(ch, '')
    if 'a' in on: g[0, 1:w - 1] = True
    if 'g' in on: g[m, 1:w - 1] = True
    if 'd' in on: g[h - 1, 1:w - 1] = True
    if 'f' in on: g[1:m, 0] = True
    if 'b' in on: g[1:m, w - 1] = True
    if 'e' in on: g[m + 1:h - 1, 0] = True
    if 'c' in on: g[m + 1:h - 1, w - 1] = True
    return g


def clock_grid(s, colon_on=True, w=7, h=13, gap=2):
    cols = []
    for ch in s:
        if ch == ':':
            c = np.zeros((h, 3), bool)
            if colon_on:
                c[h // 3, 1] = c[2 * h // 3, 1] = True
            cols.append(c)
        else:
            cols.append(seg_digit(ch, w, h))
        cols.append(np.zeros((h, gap), bool))
    return np.concatenate(cols[:-1], 1)


def dot_matrix(grid, pitch=18, on='#7FC8B8', off_alpha=0.12, bg='#0B1414', glow=0.5):
    h, w = grid.shape
    H2, W2 = h * pitch, w * pitch
    lit = cv2.resize(grid.astype(np.float32), (W2, H2), interpolation=cv2.INTER_NEAREST)
    ys, xs = np.mgrid[0:H2, 0:W2].astype(np.float32)
    cell = np.sqrt(((xs % pitch) - pitch / 2 + 0.5) ** 2 + ((ys % pitch) - pitch / 2 + 0.5) ** 2)
    core = np.clip((pitch * 0.34 - cell) * 1.4, 0, 1)
    ring = np.clip((pitch * 0.42 - cell) * 1.4, 0, 1) - core
    rgb = np.empty((H2, W2, 3), np.float32)
    rgb[:] = hexc(bg)
    c = hexc(on)
    rgb = rgb + (c * off_alpha + hexc(bg) * (1 - off_alpha) - rgb) * core[..., None]
    rgb = rgb - ring[..., None] * 0.04
    rgb = rgb + (c - rgb) * (core * lit)[..., None]
    if glow:
        g = cv2.GaussianBlur(lit, (0, 0), pitch * 0.7)
        rgb = rgb + c[None, None] * g[..., None] * glow * 0.5
    return np.clip(rgb, 0, 1)


# ---------------------------------------------------------------- 二色夢刷り: riso two-ink separation
_TWO = {}


def _lab(rgb):
    from .halftone import to_lab
    return to_lab(rgb)


def _screen(tone, period, angle, off=(0.0, 0.0)):
    """AM halftone coverage for a tone map on a screen-locked grid (round dots, full solid at tone 1)"""
    h, w = tone.shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    xs += off[0]
    ys += off[1]
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    u = (xs * c + ys * s) / period
    v = (-xs * s + ys * c) / period
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    r = 0.7071 * np.sqrt(np.clip(tone, 0, 1))
    return np.clip((r - d) * period + 0.5, 0, 1) * (tone > 0.02)


def two_ink(img, cobalt='#2C4C9A', orange='#F08A3C', paper='#EDE3CF', over='#292924', period=8.0, ang_c=15.0,
            ang_o=75.0, mis=(2.0, -1.0), gain=1.0, solid=0.93):
    """re-print any frame in two inks: each pixel is unmixed into cobalt / orange coverage (4-primary Neugebauer
    model fitted in Lab through a 32^3 LUT), then each plate gets its own halftone screen (15 / 75 degrees) with
    a slight misregistration. Near-solid areas print solid so flats stay flat."""
    key = (cobalt, orange, paper, over)
    if key not in _TWO:
        P_, C_, O_, X_ = [hexc(h) for h in (paper, cobalt, orange, over)]
        cs = np.linspace(0, 1, 33).astype(np.float32)
        cc, oo = [a.ravel() for a in np.meshgrid(cs, cs, indexing='ij')]
        cols = (P_[None] * ((1 - cc) * (1 - oo))[:, None] + C_[None] * (cc * (1 - oo))[:, None]
                + O_[None] * (oo * (1 - cc))[:, None] + X_[None] * (cc * oo)[:, None])
        lab_g = _lab(cols[None].astype(np.float32))[0]
        q = ((np.arange(32) + 0.5) / 32).astype(np.float32)
        bins = np.stack(np.meshgrid(q, q, q, indexing='ij'), -1).reshape(-1, 3)
        lab_b = _lab(bins[None])[0]
        best = np.empty(len(bins), np.int64)
        for i in range(0, len(bins), 2048):
            best[i:i + 2048] = ((lab_b[i:i + 2048, None, :] - lab_g[None]) ** 2).sum(-1).argmin(1)
        _TWO[key] = (cc[best].reshape(32, 32, 32), oo[best].reshape(32, 32, 32), P_, C_, O_, X_)
    lc, lo, P_, C_, O_, X_ = _TWO[key]
    idx = np.clip((np.clip(img, 0, 1) * 31.999).astype(np.int32), 0, 31)
    c = lc[idx[..., 0], idx[..., 1], idx[..., 2]]
    o = lo[idx[..., 0], idx[..., 1], idx[..., 2]]
    c = cv2.GaussianBlur(c, (0, 0), 0.9) * gain
    o = cv2.GaussianBlur(o, (0, 0), 0.9) * gain
    cd = np.where(c > solid, 1.0, _screen(c, period, ang_c)).astype(np.float32)
    od = np.where(o > solid, 1.0, _screen(o, period, ang_o, mis)).astype(np.float32)
    if mis != (0.0, 0.0):      # the orange plate's solids are misregistered too
        M = np.float32([[1, 0, mis[0]], [0, 1, mis[1]]])
        od = np.maximum(od * (o <= solid), cv2.warpAffine((o > solid).astype(np.float32), M, (od.shape[1], od.shape[0])))
    cd, od = cd[..., None], od[..., None]
    return (P_ * (1 - cd) * (1 - od) + C_ * cd * (1 - od) + O_ * od * (1 - cd) + X_ * cd * od).astype(np.float32)

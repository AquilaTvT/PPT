"""MV-B v2: lyric devices that replace the column for single shots (original Japanese lines only).

  tanzaku(img, idx, t)       each glyph on its own paper strip, dropping in on its sung syllable and swaying
                             like the strips under the wind chimes
  moon_path(img, idx, t)     glyphs set down the moon's path on the sea, sliced and displaced by the waves,
                             glittering
"""
import functools
import json
import math
import os

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import LYRICS
from .print_fx import hexc as H

W, H_ = 1920, 1080
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


@functools.lru_cache(maxsize=1)
def glyph_times():
    return json.load(open(os.path.join(ROOT, 'assets', 'glyph_times.json')))


@functools.lru_cache(maxsize=256)
def glyph_mask(ch, size, name='mincho'):
    import skia
    from mv import text
    f = text.font(name, size)
    w = int(max(size, f.measureText(ch)) + size * 0.4)
    h = int(size * 1.5)
    info = skia.ImageInfo.Make(w, h, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType)
    surf = skia.Surface.MakeRaster(info)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    c.drawString(ch, (w - f.measureText(ch)) / 2, size * 1.08, f, skia.Paint(AntiAlias=True, Color=skia.Color4f(1, 1, 1, 1)))
    a = np.empty((h, w), np.uint8)
    surf.readPixels(info, a, w)
    return a.astype(np.float32) / 255.0


def _blend(img, m, x0, y0, col, alpha=1.0):
    h, w = m.shape
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H_, y0 + h)
    if xb <= xa or yb <= ya:
        return img
    sub = m[ya - y0:yb - y0, xa - x0:xb - x0] * alpha
    roi = img[ya:yb, xa:xb]
    roi += (H(col)[None, None] - roi) * sub[..., None]
    return img


def _rot(m, ang):
    h, w = m.shape
    pad = int(max(h, w) * 0.3)
    big = cv2.copyMakeBorder(m, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    M = cv2.getRotationMatrix2D((big.shape[1] / 2, pad + 2), ang, 1.0)       # pivot: top centre (the string)
    return cv2.warpAffine(big, M, (big.shape[1], big.shape[0]), flags=cv2.INTER_LINEAR), pad


TANZAKU_COLS = ['#F3EBD9', '#BFD8E8', '#F2C6C2', '#F5DE8A', '#CFE3C4']


def tanzaku(img, idx, t, x0=1840, y_top=26, step=-104, size=58):
    ln = LYRICS[idx]
    gt = glyph_times()[str(idx)]
    chars = [c for c in ln['text'] if not c.isspace()]
    out_a = 1 - clamp((t - ln['end'] - 0.1) / 0.4)
    if out_a <= 0:
        return img
    for i, ch in enumerate(chars[:len(gt)]):
        k = (t - gt[i]) / 0.35
        if k <= 0:
            continue
        drop = (1 - clamp(k)) ** 3 * 60
        sw = math.sin(t * 2.3 + i * 0.9) * 4.0 * (0.6 + 0.4 * math.sin(t * 0.7 + i))
        sw += 14 * math.exp(-k * 2.5) * math.sin(k * 9)
        sw_deg = sw
        sh, swd = int(size * 3.1), int(size * 1.25)
        slip = np.zeros((sh, swd), np.float32)
        slip[int(size * 0.35):, :] = 1.0
        slip[:int(size * 0.35), swd // 2 - 1:swd // 2 + 1] = 1.0                  # the string
        g = glyph_mask(ch, size)
        gy = int(size * 0.75)
        gx = (swd - g.shape[1]) // 2
        gl = np.zeros_like(slip)
        gl[gy:gy + g.shape[0], max(0, gx):max(0, gx) + g.shape[1]] = g[:, :min(g.shape[1], swd - max(0, gx))]
        rs, pad = _rot(slip, sw_deg)
        rg, _ = _rot(gl, sw_deg)
        x = int(x0 + i * step - rs.shape[1] / 2)
        y = int(y_top - drop - pad)
        a = clamp(k * 3) * out_a
        shadow = cv2.GaussianBlur(rs, (0, 0), 5) * 0.35
        img = _blend(img, shadow, x + 8, y + 10, '#0A0C18', a)
        paper = rs.copy()
        paper[:pad + int(size * 0.35)] *= 0
        img = _blend(img, paper, x, y, TANZAKU_COLS[i % len(TANZAKU_COLS)], a * 0.96)
        string = rs.copy()
        string[pad + int(size * 0.35):] *= 0
        img = _blend(img, string, x, y, '#C9C2B4', a * 0.8)
        img = _blend(img, rg, x, y, '#1A1416', a)
    return img


def moon_path(img, idx, t, x=990, y0=330, size=74, lead=1.18):
    ln = LYRICS[idx]
    gt = glyph_times()[str(idx)]
    chars = [c for c in ln['text'] if not c.isspace()]
    out_a = 1 - clamp((t - ln['end'] - 0.1) / 0.5)
    if out_a <= 0:
        return img
    for i, ch in enumerate(chars[:len(gt)]):
        k = (t - gt[i]) / 0.3
        if k <= 0:
            continue
        g = glyph_mask(ch, size)
        h, w = g.shape
        yy = int(y0 + i * size * lead * (0.86 + 0.14 * i / max(1, len(chars))))
        persp = 0.8 + 0.5 * (yy - y0) / 700.0                                  # nearer = bigger
        g = cv2.resize(g, (int(w * persp), int(h * persp)), interpolation=cv2.INTER_AREA)
        h, w = g.shape
        # broken by the waves: horizontal slices shifted by the swell, more so nearer the shore
        rows = np.arange(h, dtype=np.float32)
        amp = (3 + 9 * persp) * (1.0 + 0.6 * math.sin(t * 1.3 + i))
        shift = amp * np.sin(rows / (5.0 + persp * 3) + t * 5.0 + i * 1.7)
        shift = np.round(shift / 2) * 2
        broken = np.zeros_like(g)
        for r in range(h):
            broken[r] = np.roll(g[r], int(shift[r]))
        gaps = (np.sin(rows * 0.9 + t * 7 + i) > 0.62).astype(np.float32)[:, None]
        broken *= 1 - gaps * 0.85
        a = clamp(k) * out_a
        glow = cv2.GaussianBlur(broken, (0, 0), 6) * 0.8
        img = _blend(img, glow, int(x - w / 2), yy, '#9FB8E0', a * 0.6)
        img = _blend(img, broken, int(x - w / 2), yy, '#F3EBD9', a)
        tw = np.clip(np.sin(rows[:, None] * 2.1 + np.arange(w)[None, :] * 0.7 + t * 11) - 0.93, 0, 1) * 12 * broken
        img = _blend(img, np.clip(tw, 0, 1), int(x - w / 2), yy, '#FFFFFF', a)
    return img

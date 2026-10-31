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

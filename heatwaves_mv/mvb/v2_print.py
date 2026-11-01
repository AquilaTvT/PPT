"""MV-B v2: alternative presses for single shots.

  two_ink(raw, masks, ...)   a riso duotone: each figure on its own plate (orange / cobalt), halftone on its own
                             screen angle, key lines in the plate's dark tone, laid by multiplication on cream stock,
                             each plate shifted by its own registration offset
  peel(top, under, p, ...)   the top print peels away like a thin sheet along a moving diagonal fold, showing its
                             paper back and casting a soft shadow on what is revealed
"""
import functools
import math

import cv2
import numpy as np

from .print_fx import hexc as H
from .print2 import screen, dots, CREAM

W, H_ = 1920, 1080


def _lines(raw, sigma=1.0):
    y = raw @ np.float32([0.2126, 0.7152, 0.0722])
    g1 = cv2.GaussianBlur(y, (0, 0), sigma)
    g2 = cv2.GaussianBlur(y, (0, 0), 1.6 * sigma)
    xd = g1 - 0.985 * g2
    ln = 1 - np.clip(1 - np.tanh(np.maximum(0, -xd - 0.007) * 70), 0, 1)
    return cv2.GaussianBlur(ln, (0, 0), 0.6)


def _shift(a, dx, dy):
    if abs(dx) < 0.01 and abs(dy) < 0.01:
        return a
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def two_ink(raw, masks, inks=('#F08A3C', '#2C4C9A'), keys=('#A8401C', '#1E2550'), offsets=((0, 0), (0, 0)),
            angles=(15.0, 75.0), period=6.5, bg=0.45, gamma=1.25, paper='#EDE3CF'):
    """masks: one soft mask per plate (her / him); outside its mask a plate still prints the scene at `bg`"""
    y = np.clip(raw @ np.float32([0.2126, 0.7152, 0.0722]), 0, 1)
    flat = cv2.bilateralFilter((y * 255).astype(np.uint8), 7, 30, 5).astype(np.float32) / 255
    tone = np.clip((1 - flat) ** gamma * 1.15 - 0.04, 0, 1)
    ln = _lines(raw)
    img = np.empty((H_, W, 3), np.float32)
    img[:] = H(paper)
    rng = np.random.default_rng(3)
    grain = 1 - 0.08 * np.abs(cv2.GaussianBlur(rng.standard_normal((H_, W)).astype(np.float32), (0, 0), 0.8))
    for m, ink, key, (dx, dy), ang in zip(masks, inks, keys, offsets, angles):
        w = m + (1 - m) * bg
        cov = dots(np.clip(tone * w, 0, 1), screen(period, ang), period) * grain
        cov = _shift(cov, dx, dy)
        img *= 1 - cov[..., None] * (1 - H(ink))[None, None]
        kl = _shift(np.clip(ln * m * 1.1, 0, 1), dx, dy)
        img *= 1 - kl[..., None] * (1 - H(key))[None, None] * 0.9
    return np.clip(img, 0, 1)


def split_masks(x_split, soft=70.0, left_first=True):
    xs = np.arange(W, dtype=np.float32)
    a = np.clip((x_split - xs) / soft + 0.5, 0, 1)[None, :].repeat(H_, 0)
    return (a, 1 - a) if left_first else (1 - a, a)


def peel(top, under, p, angle=-35.0, curl=90.0, back='#E4D7BC'):
    """p in 0..1: the fold travels across the frame along `angle` (degrees); past the fold the under image shows,
    the curled sheet (its paper back, shaded) lies just behind the fold, a soft shadow falls on the revealed side"""
    ys, xs = _grid()
    a = math.radians(angle)
    d = xs * math.cos(a) + ys * math.sin(a)
    lo, hi = float(d.min()) - curl * 2, float(d.max()) + curl
    f = lo + (hi - lo) * p                                   # fold position along d
    rel = d - f                                              # < 0: already peeled (revealed)
    revealed = np.clip(-rel / 1.5, 0, 1)
    out = top * (1 - revealed[..., None]) + under * revealed[..., None]
    # the shadow of the lifted sheet on the revealed side
    sh = np.exp(-np.clip(-rel, 0, None) / (curl * 0.9)) * (rel < 0) * 0.45
    out = out * (1 - sh[..., None])
    # the curl: the sheet's back, a band just on the revealed side of the fold
    band = (rel < 0) & (rel > -curl)
    u = np.clip(-rel / curl, 0, 1)
    shade = 0.70 + 0.30 * np.sin(u * math.pi)
    backc = H(back)[None, None] * shade[..., None]
    bm = band.astype(np.float32)
    bm = cv2.GaussianBlur(bm, (0, 0), 0.8)
    out = out * (1 - bm[..., None]) + backc * bm[..., None]
    edge = np.exp(-(rel / 1.6) ** 2) * 0.5
    return np.clip(out * (1 - edge[..., None] * 0.6), 0, 1)


@functools.lru_cache(maxsize=1)
def _grid():
    return np.mgrid[0:H_, 0:W].astype(np.float32)

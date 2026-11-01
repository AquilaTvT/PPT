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


def peel(top, under, p, angle=-35.0, curl=90.0, back='#E4D7BC', mode='paper'):
    """p in 0..1: a sheet is peeled back along a fold that travels across the frame (direction `angle`, degrees).
    Behind the fold (already peeled) the under image shows; the peeled part is folded back over the rest as a flap
    of width <= curl showing its back, with a soft shadow beyond its edge.
      mode='paper': the flap is the sheet's paper back (colour `back`, shaded, the print faintly showing through)
      mode='film' : the sheet is a transparent screentone film -- the flap carries the mirrored dots of the top
                    print (top / under), with a sheen"""
    ys, xs = _grid()
    a = math.radians(angle)
    nx, ny = math.cos(a), math.sin(a)
    d = xs * nx + ys * ny
    lo, hi = float(d.min()), float(d.max())
    f = lo - 4 + (hi - lo + curl + 8) * p                    # fold position along d
    rel = d - f                                              # < 0: peeled (revealed), > 0: still on the paper
    peeled_len = max(0.0, f - lo)
    wf = min(curl, peeled_len)
    revealed = np.clip(-rel / 1.2 + 0.5, 0, 1)
    out = top * (1 - revealed[..., None]) + under * revealed[..., None]
    # a little lift shadow on the revealed side next to the fold
    out = out * (1 - (np.exp(np.clip(rel, None, 0) / 18.0) * (rel < 0) * 0.25)[..., None])
    if wf > 1:
        flap = (rel > 0) & (rel < wf)
        u = np.clip(rel / wf, 0, 1)                          # 0 at the fold, 1 at the flap's free edge
        mx = (xs - 2 * rel * nx).astype(np.float32)
        my = (ys - 2 * rel * ny).astype(np.float32)
        fm = flap.astype(np.float32)
        fm = cv2.GaussianBlur(fm, (0, 0), 0.8)
        if mode == 'film':
            ratio = np.clip(top / np.maximum(under, 1e-3), 0, 1)
            rm = cv2.remap(ratio, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            sheen = 1.0 + 0.10 * np.sin(u * math.pi)[..., None]
            film = top * rm * sheen + 0.05 * (1 - u)[..., None]
            out = out * (1 - fm[..., None]) + film * fm[..., None]
        else:
            mt = cv2.remap(top, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            shade = (0.78 + 0.22 * np.sin(u * math.pi * 0.9 + 0.2))[..., None]
            paper = H(back)[None, None] * shade
            show = paper * 0.86 + (1 - mt) * -0.10 + mt * 0.10      # the print faintly through the paper
            out = out * (1 - fm[..., None]) + np.clip(show, 0, 1) * fm[..., None]
        edge = np.exp(-((rel - wf) / 1.4) ** 2) * 0.35 + np.exp(-(rel / 1.4) ** 2) * 0.25
        sh = np.exp(-np.clip(rel - wf, 0, None) / 16.0) * (rel > wf) * 0.32
        out = out * (1 - (edge + sh)[..., None])
    return np.clip(out, 0, 1)


@functools.lru_cache(maxsize=1)
def _grid():
    return np.mgrid[0:H_, 0:W].astype(np.float32)

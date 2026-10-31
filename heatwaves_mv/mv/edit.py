"""Timeline: shots + transitions -> one frame."""
import math

import numpy as np

from . import core
from .core import clamp, smooth, ease_io, ease_out, ease_in


class Shot:
    def __init__(self, name, t0, t1, fn, pre=0.0, post=0.0, **params):
        self.name, self.t0, self.t1, self.fn = name, t0, t1, fn
        self.params = params
        self.pre, self.post = pre, post

    @property
    def dur(self):
        return self.t1 - self.t0

    def local(self, t):
        return t - self.t0

    def prog(self, t):
        return (t - self.t0) / max(1e-6, self.t1 - self.t0)

    def render(self, t):
        out = self.fn(t, self)
        if hasattr(out, 'a'):
            out = out.a
        return out

    def __getitem__(self, k):
        return self.params[k]

    def get(self, k, d=None):
        return self.params.get(k, d)


class Tr:
    """transition at the boundary between two consecutive shots.

    kind: cut | dissolve | dots | heat | crt | flash | whip | iris | wipe | cloud | white | black
    dur:  seconds; align 0 -> starts at boundary, 1 -> ends at boundary, 0.5 centred
    """

    def __init__(self, kind='cut', dur=0.0, align=0.5, **params):
        self.kind, self.dur, self.align, self.params = kind, dur, align, params

    def window(self, tb):
        return tb - self.dur * self.align, tb + self.dur * (1 - self.align)


def _dots(a, b, p, cell=22.0, angle=45.0, grow='radial', cx=960, cy=540, invert=False):
    """halftone dot dissolve: B shows through dots that grow from nothing"""
    ys, xs = core.coords()
    if grow == 'radial':
        d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / 1100.0
        field = np.clip(p * 1.6 - d * 0.6, 0, 1)
    elif grow == 'left':
        field = np.clip(p * 1.7 - (xs / 1920.0) * 0.7, 0, 1)
    elif grow == 'right':
        field = np.clip(p * 1.7 - (1 - xs / 1920.0) * 0.7, 0, 1)
    elif grow == 'down':
        field = np.clip(p * 1.7 - (ys / 1080.0) * 0.7, 0, 1)
    elif grow == 'up':
        field = np.clip(p * 1.7 - (1 - ys / 1080.0) * 0.7, 0, 1)
    else:
        field = np.full(xs.shape, p, np.float32)
    field = field.astype(np.float32)
    m = core.halftone(field, cell=cell, angle=angle, center=True)
    return a + (b - a) * m[..., None]


def _heat(a, b, p, t):
    amp = math.sin(p * math.pi) * 26.0
    aa = core.heat_haze(a, t, amp=amp, wavelength=30, speed=2.5) if amp > 0.5 else a
    bb = core.heat_haze(b, t + 1.7, amp=amp, wavelength=30, speed=2.5) if amp > 0.5 else b
    m = smooth(clamp((p - 0.3) / 0.4))
    # dissolve through a horizontal ripple mask so it reads as shimmer
    ys, xs = core.coords()
    rip = (np.sin(ys / 9.0 + t * 20) * 0.5 + 0.5) * 0.35
    k = np.clip(m * 1.35 - rip, 0, 1)
    return aa + (bb - aa) * k[..., None]


def _crt(a, b, p):
    """A collapses to a line then a dot, B expands back (TV channel change)"""
    out = np.zeros_like(a)
    H, W = core.H, core.W
    src, q = (a, p * 2) if p < 0.5 else (b, (1 - p) * 2)
    # q: 0 = full picture, 1 = collapsed
    sy = max(0.003, 1 - ease_in(clamp(q / 0.7), 2))
    sx = 1 - ease_in(clamp((q - 0.6) / 0.4), 2) * 0.995
    img = core.affine(src, scale=1.0, border=0)
    import cv2
    h2 = max(1, int(H * sy))
    w2 = max(1, int(W * sx))
    small = cv2.resize(img, (w2, h2), interpolation=cv2.INTER_AREA)
    bright = 1 + q * 2.5
    small = np.clip(small * bright, 0, 1)
    y0, x0 = (H - h2) // 2, (W - w2) // 2
    out[y0:y0 + h2, x0:x0 + w2] = small
    glow = core.blur(out, 6) * (q * 1.2)
    return np.clip(out + glow, 0, 1)


def _whip(a, b, p, direction=1):
    off = 1920 * direction
    if p < 0.5:
        q = ease_in(p * 2, 2)
        img = core.affine(a, tx=-off * q * 0.35)
        return core.motion_blur(img, 220 * q * direction)
    q = 1 - ease_out((p - 0.5) * 2, 2)
    img = core.affine(b, tx=off * q * 0.35)
    return core.motion_blur(img, 220 * q * direction)


def _iris(a, b, p, cx=960, cy=540, close_first=True):
    ys, xs = core.coords()
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    if p < 0.5:
        r = (1 - ease_in(p * 2, 2)) * 1150
        m = np.clip((r - d) / 2 + 0.5, 0, 1)
        return a * m[..., None] + core._col('night') * (1 - m[..., None])
    r = ease_out((p - 0.5) * 2, 2) * 1150
    m = np.clip((r - d) / 2 + 0.5, 0, 1)
    return b * m[..., None] + core._col('night') * (1 - m[..., None])


def _wipe(a, b, p, angle=20.0, soft=60.0, color=None):
    ys, xs = core.coords()
    th = math.radians(angle)
    u = xs * math.cos(th) + ys * math.sin(th)
    lo, hi = -400, 1920 * math.cos(th) + 1080 * abs(math.sin(th)) + 400
    pos = lo + (hi - lo) * ease_io(p)
    m = np.clip((pos - u) / soft + 0.5, 0, 1)
    out = a + (b - a) * m[..., None]
    if color is not None:
        band = np.exp(-((u - pos) / 40.0) ** 2)
        out = out + (core._col(color) - out) * band[..., None]
    return out


def compose(tr, a, b, p, t):
    k = tr.kind
    if k == 'dissolve':
        return a + (b - a) * np.float32(smooth(p))
    if k == 'dots':
        return _dots(a, b, ease_io(p), **tr.params)
    if k == 'heat':
        return _heat(a, b, p, t)
    if k == 'crt':
        return _crt(a, b, p)
    if k == 'whip':
        return _whip(a, b, p, tr.params.get('direction', 1))
    if k == 'iris':
        return _iris(a, b, p, **tr.params)
    if k == 'wipe':
        return _wipe(a, b, p, **tr.params)
    if k in ('flash', 'white', 'black'):
        col = core._col(tr.params.get('color', 'white' if k != 'black' else 'night'))
        base = a if p < 0.5 else b
        amt = 1 - abs(p - 0.5) * 2
        amt = amt ** tr.params.get('power', 1.5)
        return base + (col - base) * np.float32(amt)
    return b if p >= 0.5 else a


class Edit:
    def __init__(self, shots, transitions=None, post=None):
        self.shots = shots
        self.trans = transitions or {}
        self.post = post

    def shot_at(self, t):
        for i, s in enumerate(self.shots):
            if s.t0 <= t < s.t1:
                return i
        return len(self.shots) - 1 if t >= self.shots[-1].t0 else 0

    def render(self, t, frame_idx=0):
        i = self.shot_at(t)
        img = None
        # boundary with next
        for j in (i, i - 1):
            if j < 0 or j + 1 >= len(self.shots):
                continue
            tr = self.trans.get(j)
            if tr is None or tr.kind == 'cut' or tr.dur <= 0:
                continue
            tb = self.shots[j].t1
            w0, w1 = tr.window(tb)
            if w0 <= t < w1:
                p = (t - w0) / (w1 - w0)
                a = self.shots[j].render(t)
                b = self.shots[j + 1].render(t)
                img = compose(tr, a, b, p, t)
                break
        if img is None:
            img = self.shots[i].render(t)
        if self.post:
            img = self.post(img, t, frame_idx)
        return img

"""Generated video clips as compositor layers.

  r = Clip('work/A/A-hook-01/final.mp4', speed=1.0)
  img = r.frame(t_local)                       # (H, W, 3) float32 at output size, cover-fit
  img = r.frame(t_local, zoom=1.08, cx=0.5, cy=0.45)

Frames are decoded sequentially (each render worker walks forward in time), so a
reader keeps one VideoCapture open and only re-opens on a backwards seek.
"""
import functools
import os
import weakref

import cv2
import numpy as np

from . import core


_LIVE = weakref.WeakSet()       # every Clip, so a forked render worker can drop the parent's decoders
_ORPHANS = []                   # inherited VideoCaptures: never touched (or garbage-collected) in the child


def _after_fork_in_child():
    """a decoder opened in the parent carries its threads' locks across fork() and hangs on the first read in the
    child: forget it (kept referenced so its destructor never runs here) and let the worker open its own"""
    for c in list(_LIVE):
        if c._cap is not None:
            _ORPHANS.append(c._cap)
        c._cap, c._idx, c._last = None, -1, None


os.register_at_fork(after_in_child=_after_fork_in_child)


class Clip:
    def __init__(self, path, speed=1.0, loop=False, pingpong=False, start=0.0, alpha=None):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.path, self.speed, self.loop, self.pingpong, self.start = path, speed, loop, pingpong, start
        cap = cv2.VideoCapture(path)
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        self._cap = None
        self._idx = -1
        self._last = None
        self.alpha = Clip(alpha, speed, loop, pingpong, start) if alpha else None
        _LIVE.add(self)

    @property
    def duration(self):
        return self.n / self.fps / self.speed

    def _index(self, t):
        f = (self.start + max(0.0, t) * self.speed) * self.fps
        i = int(f)
        if self.pingpong and self.n > 1:
            period = 2 * (self.n - 1)
            i = i % period
            return i if i < self.n else period - i
        if self.loop:
            return i % self.n
        return min(i, self.n - 1)

    def raw(self, t):
        """source frame (uint8 BGR) nearest to local time t"""
        i = self._index(t)
        if i == self._idx and self._last is not None:
            return self._last
        if self._cap is None or i < self._idx or i > self._idx + 90:
            if self._cap is not None:
                self._cap.release()
            self._cap = cv2.VideoCapture(self.path)
            if i > 0:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            self._idx = i - 1
        fr = self._last
        while self._idx < i:
            ok, nxt = self._cap.read()
            if not ok:
                break
            fr = nxt
            self._idx += 1
        self._last = fr
        return fr

    def frame(self, t, zoom=1.0, cx=0.5, cy=0.5, rot=0.0):
        """cover-fit to the output frame, then zoom/pan around (cx, cy) in source-relative coordinates"""
        src = self.raw(t)
        if src is None:
            return np.zeros((core.H, core.W, 3), np.float32)
        rgb = cv2.cvtColor(src, cv2.COLOR_BGR2RGB).astype(np.float32) * (1 / 255.0)
        return fit(rgb, zoom, cx, cy, rot)

    def matte(self, t, zoom=1.0, cx=0.5, cy=0.5, rot=0.0):
        if self.alpha is None:
            return None
        a = self.alpha.raw(t)
        if a is None:
            return None
        g = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32) * (1 / 255.0)
        return fit(g[..., None].repeat(3, 2), zoom, cx, cy, rot)[..., 0]


def fit(img, zoom=1.0, cx=0.5, cy=0.5, rot=0.0):
    h, w = img.shape[:2]
    s = max(core.W / w, core.H / h) * zoom
    # source point (cx, cy) goes to the frame centre, clamped so the frame stays covered
    px, py = cx * w, cy * h
    half_w, half_h = core.W / (2 * s), core.H / (2 * s)
    px = min(max(px, half_w), w - half_w) if w > 2 * half_w else w / 2
    py = min(max(py, half_h), h - half_h) if h > 2 * half_h else h / 2
    M = cv2.getRotationMatrix2D((px, py), rot, s)
    M[0, 2] += core.W / 2 - px
    M[1, 2] += core.H / 2 - py
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    return cv2.warpAffine(img, M, (core.W, core.H), flags=interp, borderMode=cv2.BORDER_REFLECT)


@functools.lru_cache(maxsize=64)
def clip(path, speed=1.0, loop=False, pingpong=False, start=0.0, alpha=None):
    """per-process cache so shots can call clip(...) every frame"""
    return Clip(path, speed, loop, pingpong, start, alpha)

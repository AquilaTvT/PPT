"""Pixel-art conversion for MV-B (works on stills and on video, temporally stable).

  px = Pixelizer(grid=(480, 270), palette=PAL_DAY, dither='bayer4', strength=0.6)
  out = px(frame_rgb_float)            # (H, W, 3) float at output resolution

- the picture is area-resampled onto a fixed low-res grid locked to the screen,
- quantised to a limited palette (fixed list of inks, or an adaptive palette learnt once
  per shot and then frozen),
- optional ordered dithering, optional 1-px dark outline on luminance edges,
- temporal hysteresis: a pixel keeps last frame's ink unless the new best ink is clearly
  better, which removes the shimmer that plain per-frame quantisation produces on AI video,
- nearest-neighbour upscale to the output size.
"""
import numpy as np
import cv2

from . import core

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16.0


def hexes(*hs):
    return np.stack([core.hexc(h) for h in hs]).astype(np.float32)


def srgb_to_lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2Lab)


def learn_palette(img, k=24, seed=0):
    """k-means palette in Lab from one representative frame"""
    lab = srgb_to_lab(img).reshape(-1, 3)
    rng = np.random.default_rng(seed)
    sub = lab[rng.choice(len(lab), min(len(lab), 40000), replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
    _, _, centers = cv2.kmeans(sub, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    rgb = cv2.cvtColor(centers.reshape(1, -1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3)
    return np.clip(rgb, 0, 1).astype(np.float32)


class Pixelizer:
    def __init__(self, grid=(480, 270), palette=None, dither='none', strength=0.5, outline=0.0,
                 outline_color='#141B3D', hysteresis=0.15, k=24, pre_sharpen=0.4):
        self.gw, self.gh = grid
        self.palette = palette
        self.k = k
        self.dither = dither
        self.strength = strength
        self.outline = outline
        self.outline_color = core.hexc(outline_color)
        self.hyst = hysteresis
        self.pre_sharpen = pre_sharpen
        self._prev_idx = None
        self._pal_lab = None

    def reset(self):
        self._prev_idx = None

    def _ensure_palette(self, small):
        if self.palette is None:
            self.palette = learn_palette(small, self.k)
        if self._pal_lab is None:
            self._pal_lab = srgb_to_lab(self.palette.reshape(1, -1, 3)).reshape(-1, 3)

    def __call__(self, img):
        small = cv2.resize(img, (self.gw, self.gh), interpolation=cv2.INTER_AREA)
        if self.pre_sharpen:
            blur = cv2.GaussianBlur(small, (0, 0), 1.0)
            small = np.clip(small + (small - blur) * self.pre_sharpen, 0, 1)
        self._ensure_palette(small)
        work = small
        if self.dither == 'bayer4':
            th = np.tile(BAYER4, (self.gh // 4 + 1, self.gw // 4 + 1))[:self.gh, :self.gw] - 0.5
            work = np.clip(small + th[..., None] * (self.strength * 0.18), 0, 1)
        lab = srgb_to_lab(work).reshape(-1, 3)
        d = ((lab[:, None, :] - self._pal_lab[None, :, :]) ** 2).sum(-1)
        idx = d.argmin(1)
        if self._prev_idx is not None and self._prev_idx.shape == idx.shape and self.hyst > 0:
            best = d[np.arange(len(idx)), idx]
            prev = d[np.arange(len(idx)), self._prev_idx]
            keep = prev <= best * (1.0 + self.hyst) + 4.0
            idx = np.where(keep, self._prev_idx, idx)
        self._prev_idx = idx
        q = self.palette[idx].reshape(self.gh, self.gw, 3)
        if self.outline > 0:
            L = cv2.cvtColor(q, cv2.COLOR_RGB2GRAY)
            e = np.maximum(np.abs(np.diff(L, axis=0, prepend=L[:1])), np.abs(np.diff(L, axis=1, prepend=L[:, :1])))
            m = (e > 0.18).astype(np.float32) * self.outline
            q = q * (1 - m[..., None]) + self.outline_color * m[..., None]
        return cv2.resize(q, (core.W, core.H), interpolation=cv2.INTER_NEAREST)

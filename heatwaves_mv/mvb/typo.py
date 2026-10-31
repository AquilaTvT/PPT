"""MV-B lyric type (reference-style print lettering).

Style A: cream #EDE3CF fill, 3 px warm-black line, offset shadow (+7,+7) in the world's accent ink.
Style B (busy plates): warm-black glyph with an 8 px cream outline.
Entrance: 見当合わせ: each glyph arrives as two misregistered plates (fill + shadow 24 px apart) that lock
together within 2 frames on its sung onset. Exit: the glyph breaks into its halftone dots, shrinking over 6 frames.
Chinese: Noto Serif SC 32 px cream 85% in a thin column left of the Japanese column.
"""
import json
import math
import os

import cv2
import numpy as np

from mv import text, lyrics
from mv.core import clamp
from mv.timing import LYRICS

GT = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'assets', 'glyph_times.json')))
W, H = 1920, 1080
CREAM, INK = '#EDE3CF', '#1A1416'
_YS, _XS = np.mgrid[0:H, 0:W].astype(np.float32)


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def _over(img, color, cov):
    return img + (hexc(color)[None, None] - img) * cov[..., None]


def dots_mask(k, period=8.0, angle=45.0):
    """screen of round dots whose radius shrinks with k (0 = full coverage, 1 = gone)"""
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    u = (_XS * c + _YS * s) / period
    v = (-_XS * s + _YS * c) / period
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    r = 0.72 * (1 - k)
    return np.clip((r - d) * period, 0, 1)


class VLyric:
    def __init__(self, idx, x=1720, y=160, size=100, accent='#D9402B', style='A', out_t=None, zh=True,
                 times=None, color=None, en_led=False, max_glyphs=None):
        self.ln = LYRICS[idx]
        self.idx = idx
        self.size, self.accent, self.style = size, accent, style
        self.fill = color or (CREAM if style == 'A' else INK)
        self.times = times or GT[str(idx)]
        self.out_t = out_t if out_t is not None else self.ln['end']
        s = self.ln['text'].replace(' ', '　')
        if max_glyphs:
            s = ''.join([c for c in s if not c.isspace()][:max_glyphs])
        n = len([c for c in s if not c.isspace()])
        size = min(size, (H - y - 60) / max(1, n * 1.08))
        self.size = size
        self.glyphs = text.layout_v(s, x, y, size, 'mincho', tracking=0.08)
        self.x, self.y = x, y
        self.zh = zh and idx in lyrics.ZH

    def _anim(self, t, dx=0.0, dy=0.0):
        def anim(g):
            tc = self.times[min(g['i'], len(self.times) - 1)]
            if t < tc:
                return None
            k = clamp((t - tc) / (2.0 / 24))          # 2-frame lock
            return dict(alpha=1.0, dx=dx * (1 - k), dy=dy * (1 - k))
        return anim

    def draw(self, img, t):
        if t < self.times[0] - 0.05 or t > self.out_t + 0.3:
            return img
        exit_k = clamp((t - self.out_t) / (6.0 / 24)) if t > self.out_t else 0.0
        fill, _ = text.render_glyphs(self.glyphs, anim=self._anim(t))
        if fill is None:
            return img
        shadow, _ = text.render_glyphs(self.glyphs, anim=self._anim(t, dx=24, dy=24))
        sh = np.roll(np.roll(shadow, 7, axis=0), 7, axis=1)
        line = cv2.dilate(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        if exit_k > 0:
            dm = dots_mask(exit_k)
            fill, sh, line = fill * dm, sh * dm, line * dm
        out = img
        if self.style == 'A':
            out = _over(out, self.accent, sh)
            out = _over(out, INK, line)
            out = _over(out, self.fill, fill)
        else:
            halo = cv2.dilate(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
            out = _over(out, CREAM, halo)
            out = _over(out, self.fill, fill)
        if self.zh:
            k = clamp((t - self.times[0]) / 0.25) * (1 - exit_k)
            if k > 0:
                gl = text.layout_v(lyrics.ZH[self.idx].replace(' ', '　'), self.x - self.size * 0.95, self.y + 8, 32, 'zh', tracking=0.14)
                zf, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=0.85 * k))
                if zf is not None:
                    halo = cv2.GaussianBlur(cv2.dilate(zf, np.ones((3, 3), np.uint8), iterations=2), (0, 0), 1.2)
                    out = _over(out, INK, halo * 0.7)
                    out = _over(out, CREAM, zf)
        return out

"""MV-A lyric typography: vertical Japanese with per-glyph ink-bleed reveals at the sung onsets,
Chinese translation, English lines in Cormorant Garamond Italic in the lower letterbox bar.

  ly = Lyric(10, slot='left', world='memory')        # line index from mv.timing.LYRICS
  img = ly.draw(img, t)
"""
import json
import math
import os

import cv2
import numpy as np

from mv import text, lyrics
from mv.core import clamp, ease_out
from mv.timing import LYRICS
from . import fx

GT = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'assets', 'glyph_times.json')))
BAR = fx.letterbox_bar(2.39)        # 138 px

WORLD = {
    'memory': dict(color='#14203F', halo='#FFF3D6', halo_px=3.0, split=0.0),
    'present': dict(color='#F2F6F8', halo='#0B1026', halo_px=2.0, split=1.0),
    'mirror': dict(color='#D9E1E8', halo='#1A2440', halo_px=2.0, split=0.0),
    'dawn': dict(color='#FFF6E8', halo='#3A2A3E', halo_px=2.0, split=0.0),
    'film': dict(color='#FFF1D6', halo='#2A120C', halo_px=2.0, split=0.0),
}
WARM = '#FFF3D6'
LED_RED = '#FF3B30'


def _cov_rgb(cov, color):
    return fx.hexc(color)[None, None] * cov[..., None]


_SCRIM = None


def _foot_scrim():
    """0..1 mask: a soft band along the bottom of the frame, densest under the English line"""
    global _SCRIM
    if _SCRIM is None:
        y = np.arange(1080, dtype=np.float32)[:, None]
        band = np.clip((y - 820.0) / 140.0, 0, 1) ** 1.6
        _SCRIM = np.ascontiguousarray(np.broadcast_to(band, (1080, 1920))).astype(np.float32)
    return _SCRIM


class Lyric:
    def __init__(self, idx, slot='right', world='memory', font=None, size=None, out_t=None, letterboxed=False,
                 zh='foot', color=None, halo=None, special=(), x=None, y=None, fade_out=0.35, colors=None,
                 wobble=0.0, stop70=None):
        self.ln = LYRICS[idx]
        self.idx = idx
        self.en = self.ln['lang'] == 'en'
        self.world = WORLD[world]
        self.color = color or self.world['color']
        self.halo = halo or self.world['halo']
        self.slot, self.letterboxed, self.zh = slot, letterboxed, zh
        self.special = set(special)
        self.out_t = out_t if out_t is not None else self.ln['end']
        self.fade_out = fade_out
        self.colors = colors or {}          # glyph -> colour (e.g. {'君': WARM})
        self.wobble = wobble
        self.stop70 = stop70 if stop70 is not None else ('幸せ' in self.ln['text'] and 'complete70' not in self.special)
        self.times = GT[str(idx)]
        if self.en:
            self._layout_en(size or 54)
        else:
            self._layout_jp(font or 'mincho', size or 70, x, y)

    # ---------------------------------------------------------------- layout
    def _layout_jp(self, fname, size, x, y):
        s = self.ln['text'].replace(' ', '　')
        n = len([c for c in s if not c.isspace()])
        top = (BAR + 52) if self.letterboxed else 118
        bottom = (1080 - BAR - 40) if self.letterboxed else 980
        if self.zh == 'foot':
            bottom -= 40
        size = min(size, (bottom - top) / max(1, n * 1.1 + 0.6))
        if x is None:
            x = {'right': 1450, 'left': 470, 'center': 960, 'far_right': 1690, 'far_left': 230}.get(self.slot, 1450)
        if y is None:
            y = top if self.slot != 'center' else top + 10
        self.size = size
        self.glyphs = text.layout_v(s, x, y, size, fname, tracking=0.1)
        self.x = x
        self.foot = max(g['cy'] for g in self.glyphs) + size * 0.75 if self.glyphs else y
        # mark glyph runs for keyword treatments
        txt = ''.join(g['ch'] for g in self.glyphs)
        self.kw = {}
        for word in ('幸せ', '零時', '君', 'ミラー', '逃げ水', '投影', '僕', 'さよなら'):
            k = txt.find(word)
            while k >= 0:
                for j in range(k, k + len(word)):
                    self.kw.setdefault(j, set()).add(word)
                k = txt.find(word, k + 1)

    def _layout_en(self, size):
        self.size = size
        y = (1080 - BAR / 2 - 14) if self.letterboxed else 960
        s = self.ln['text'].lower()
        self.glyphs, self.width = text.layout_h(s, 960, y, size, 'corm_i', tracking=0.08, align='center')
        # map glyph -> word index for word-by-word reveal
        wi, out = 0, []
        prev_space = False
        k = 0
        for ch in s:
            if ch == ' ':
                wi += 1
                continue
            out.append(wi)
            k += 1
        for g, w in zip(self.glyphs, out):
            g['w'] = w
        self.y = y

    # ---------------------------------------------------------------- per-glyph state
    def _t_of(self, g):
        if self.en:
            return self.times[min(g['w'], len(self.times) - 1)]
        return self.times[min(g['i'], len(self.times) - 1)]

    def _anim(self, t):
        fade_k = clamp((t - self.out_t) / self.fade_out) if t > self.out_t else 0.0
        dur = 0.25   # 6 frames ink bleed

        def anim(g):
            tc = self._t_of(g)
            k = clamp((t - tc) / dur)
            if k <= 0:
                return None
            e = ease_out(k, 2)
            a = e
            bl = (1 - e) * 5.0
            dy = (1 - e) * 2.0
            if not self.en and self.stop70 and '幸せ' in self.kw.get(g['i'], ()):
                a = min(a, 0.62)
                bl = max(bl, 1.6)
            if self.wobble:
                dy += math.sin(t * 5.0 + g['i'] * 0.9) * self.wobble
            if fade_k > 0:
                a *= 1 - fade_k
                dy -= fade_k * 14          # evaporates upward
                bl += fade_k * 6
            st = dict(alpha=a, blur=bl, dy=dy)
            if not self.en and 'mirror_flip' in self.special and 'ミラー' in self.kw.get(g['i'], ()):
                last = self.times[min(max(j for j in self.kw if 'ミラー' in self.kw[j]), len(self.times) - 1)]
                fk = clamp((t - last) / 0.18)
                st['scale'] = 1.0
                st['sx'] = -1.0 + 2.0 * ease_out(fk, 2)
            return st
        return anim

    # ---------------------------------------------------------------- draw
    def draw(self, img, t):
        if t < self.times[0] - 0.05 or t > self.out_t + self.fade_out + 0.05:
            return img
        anim = self._anim(t)
        if self.en:
            return self._draw_en(img, t, anim)
        # split glyphs by colour group
        groups = {}
        for g in self.glyphs:
            col = self.color
            kws = self.kw.get(g['i'], ())
            for w in kws:
                if w in self.colors:
                    col = self.colors[w]
            if '零時' in kws and 'led_zero' in self.special:
                col = LED_RED
            if '君' in kws and 'warm_kimi' in self.special:
                col = WARM if self.color != WARM else '#FFFFFF'
            groups.setdefault(col, []).append(g)
        out = img
        for col, gl in groups.items():
            out = self._draw_group(out, gl, anim, col)
        if self.zh and self.idx in lyrics.ZH:
            out = self._draw_zh(out, t)
        return out

    def _flip_glyphs(self, glyphs, anim):
        """horizontal mirror per glyph via skia scale: emulate by drawing mirrored copies"""
        return glyphs

    def _draw_group(self, img, glyphs, anim, color):
        # mirrored glyphs (ミラー) are drawn with negative x-scale through 'rot' trick: render separately
        normal = [g for g in glyphs]
        fill, _ = text.render_glyphs(normal, anim=lambda g: self._sx_anim(g, anim))
        if fill is None:
            return img
        halo = cv2.GaussianBlur(cv2.dilate(fill, np.ones((3, 3), np.uint8), iterations=int(self.world['halo_px'])),
                                (0, 0), self.world['halo_px'] * 0.8)
        out = fx.over(img, np.broadcast_to(fx.hexc(self.halo), img.shape), halo * 0.85)
        if self.world['split']:
            sp = self.world['split']
            r = np.roll(fill, int(sp), axis=1)
            b = np.roll(fill, -int(sp), axis=1)
            out = out + np.stack([r * 0.25, np.zeros_like(r), b * 0.25], -1)
        return fx.over(out, np.broadcast_to(fx.hexc(color), img.shape), fill)

    def _sx_anim(self, g, anim):
        st = anim(g)
        if st is None:
            return None
        if 'sx' in st:
            sx = st.pop('sx')
            # emulate a horizontal flip with a squash through zero (skia path in text._draw_glyph uses uniform
            # scale; a negative scale mirrors both axes, so rotate 180 deg to undo the vertical mirror)
            if sx < 0:
                st['scale'] = max(0.05, -sx)
                st['rot'] = st.get('rot', 0.0) + 180.0
                st['flipv'] = True
            else:
                st['scale'] = max(0.05, sx)
        return st

    def _draw_zh(self, img, t):
        zh = lyrics.ZH[self.idx]
        k = clamp((t - (self.times[0] + 0.25)) / 0.3)
        if t > self.out_t:
            k *= 1 - clamp((t - self.out_t) / self.fade_out)
        if k <= 0:
            return img
        if self.letterboxed or self.zh == 'bar':
            gl, _ = text.layout_h(zh, 960, 1080 - BAR / 2, 26, 'zh', tracking=0.18, align='center')
        else:
            zs = max(22, self.size * 0.4)
            gl = text.layout_v(zh.replace(' ', '　'), self.x, self.foot + 8, zs, 'zh', tracking=0.12)
            if gl and max(g['cy'] for g in gl) > 1050:
                gl = text.layout_v(zh.replace(' ', '　'), self.x - self.size * 0.95, 140, zs, 'zh', tracking=0.12)
        fill, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=0.75 * k))
        if fill is None:
            return img
        col = self.color if not (self.letterboxed or self.zh == 'bar') else '#DCE3EA'
        halo = cv2.GaussianBlur(fill, (0, 0), 2.0)
        out = fx.over(img, np.broadcast_to(fx.hexc(self.halo), img.shape), halo * 0.6)
        return fx.over(out, np.broadcast_to(fx.hexc(col), img.shape), fill)

    def _draw_en(self, img, t, anim):
        fill, _ = text.render_glyphs(self.glyphs, anim=anim)
        out = img
        if not self.letterboxed:      # full frame: a soft foot scrim so the thin italic reads over bright footage
            k = clamp((t - (self.times[0] - 0.1)) / 0.3)
            if t > self.out_t:
                k *= 1 - clamp((t - self.out_t) / self.fade_out)
            if k > 0:
                out = out * (1 - _foot_scrim()[..., None] * np.float32(0.42 * k))
        if fill is not None:
            halo = cv2.GaussianBlur(fill, (0, 0), 3.5)
            out = fx.over(out, np.broadcast_to(fx.hexc('#000000'), img.shape), np.clip(halo * 0.75, 0, 1))
            col = self.colors.get('_all', '#F2EDE4')
            out = fx.over(out, np.broadcast_to(fx.hexc(col), img.shape), fill)
        if self.zh and self.idx in lyrics.ZH:
            k = clamp((t - (self.times[0] + 0.25)) / 0.3)
            if t > self.out_t:
                k *= 1 - clamp((t - self.out_t) / self.fade_out)
            if k > 0:
                gl, _ = text.layout_h(lyrics.ZH[self.idx], 960, self.y + 46, 24, 'zh', tracking=0.2, align='center')
                f2, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=0.75 * k))
                if f2 is not None:
                    out = fx.over(out, np.broadcast_to(fx.hexc('#C9D0D8'), img.shape), f2)
        return out

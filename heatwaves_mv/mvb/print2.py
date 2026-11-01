"""print2 -- generated anime footage -> a reference-grade screen print.

What the reference does (design/ref_study/forensics.md): native 1080p, flat designed colours (~24 per frame),
soft 45-degree halftone screens of ~7 px carrying the shading, AM halftone halos around lights, warm-purple
blacks and cream highlights (never pure black / white), ink linework (gold / cream on the dark night
architecture), paper fibre, grain, vignette and a 2-3 frame gate weave.

  pr = Printer(world_inks, name='B2-hook-01')    # palette fitted once per shot (cached) -> no colour flicker
  pr.fit(frames)                                 # a few frames of the shot (composited raw RGB, float 0..1)
  out = pr(rgb)                                  # float RGB 1080p
"""
import hashlib
import json
import math
import os

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, 'work', 'B2', 'print2')
W, H = 1920, 1080
_YS, _XS = np.mgrid[0:H, 0:W].astype(np.float32)
BLACK, CREAM = (24, 16, 15), (231, 218, 195)


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def to_lab(rgb):
    return cv2.cvtColor(np.ascontiguousarray(np.clip(rgb, 0, 1), np.float32), cv2.COLOR_RGB2LAB)


def from_lab(lab):
    return np.clip(cv2.cvtColor(np.ascontiguousarray(lab, np.float32), cv2.COLOR_LAB2RGB), 0, 1)


_SCREENS = {}


def screen(period=7.0, angle=45.0):
    """distance (cell units) to the nearest dot centre of a screen-locked grid: 0 .. 0.707"""
    key = (round(period, 3), round(angle, 3))
    if key not in _SCREENS:
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        u = (_XS * c + _YS * s) / period
        v = (-_XS * s + _YS * c) / period
        _SCREENS[key] = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2).astype(np.float32)
    return _SCREENS[key]


def dots(tone, d, period=7.0, soft=1.15):
    """soft AM dots: area ~ tone; edge softness ~1 px like the reference's 3-4 px soft dots"""
    r = np.sqrt(np.clip(tone, 0, 1)) * 0.64
    return np.clip((r - d) * period / soft + 0.5, 0, 1) * (tone > 0.015)


def flatten(rgb):
    """edge-preserving cel flattening (mean shift at half resolution + bilateral at full)"""
    u8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    half = cv2.resize(u8, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    f = cv2.pyrMeanShiftFiltering(half, 5, 16)
    f = cv2.resize(f, (W, H), interpolation=cv2.INTER_LINEAR)
    f = cv2.bilateralFilter(f, 7, 26, 5)
    return f.astype(np.float32) / 255.0


class Printer:
    def __init__(self, inks, name=None, k=22, period=7.0, harmonize=0.38, line='#1A1110', gold='#D2B06E',
                 night=False, lines=1.0, shade=1.0, glow=1.0, sat=1.0, dot_dark=0.5):
        self.inks_lab = to_lab(np.stack([hexc(h) for h in inks])[None])[0]
        self.name, self.k, self.period = name, k, period
        self.harmonize, self.night, self.lines_amt, self.shade_amt, self.glow_amt, self.sat = harmonize, night, lines, shade, glow, sat
        self.line, self.gold = hexc(line), hexc(gold)
        self.dot_dark = dot_dark
        self.pal = self.pal_g = None
        if name:
            p = os.path.join(CACHE, f'{name}.json')
            from .atomic import load_json
            d = load_json(p) if os.path.exists(p) else None
            if d is not None:
                self.pal, self.pal_g = np.float32(d['pal']), np.float32(d['pal_g'])

    # ---------------------------------------------------------------- palette
    def fit(self, frames, seed=0):
        rng = np.random.default_rng(seed)
        samp = []
        for fr in frames:
            lab = to_lab(flatten(fr)).reshape(-1, 3)
            samp.append(lab[rng.choice(len(lab), 50000, replace=False)])
        samp = np.concatenate(samp).astype(np.float32)
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 80, 0.2)
        _, _, cen = cv2.kmeans(samp, self.k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
        self.pal = cen.astype(np.float32)
        self.pal_g = self.grade(self.pal)
        if self.name:
            os.makedirs(CACHE, exist_ok=True)
            from .atomic import save_json
            save_json(os.path.join(CACHE, f'{self.name}.json'), {'pal': self.pal.tolist(), 'pal_g': self.pal_g.tolist()})
        return self

    def grade(self, pal):
        """harmonise the footage palette with the section's inks; tonal ends to warm black / cream"""
        out = pal.copy()
        d = ((pal[:, None, :] - self.inks_lab[None]) ** 2).sum(-1)
        near = self.inks_lab[d.argmin(1)]
        # pull hue / chroma (a, b) more than lightness so the footage keeps its modelling
        out[:, 1:] += (near[:, 1:] - out[:, 1:]) * self.harmonize
        out[:, 0] += (near[:, 0] - out[:, 0]) * self.harmonize * 0.35
        out[:, 1:] *= self.sat
        rgb = from_lab(out[None])[0]
        bl, cr = np.float32(BLACK) / 255, np.float32(CREAM) / 255
        rgb = bl + (cr - bl) * rgb
        return to_lab(rgb[None])[0]

    # ---------------------------------------------------------------- print one frame
    def _assign(self, lab_h):
        """soft two-nearest palette assignment (half resolution): flat inks, anti-aliased borders"""
        x = lab_h.reshape(-1, 3)
        pal = self.pal
        d = (x * x).sum(1, keepdims=True) - 2.0 * (x @ pal.T) + (pal * pal).sum(1)[None]
        i1 = d.argmin(1)
        r = np.arange(len(x))
        d1 = d[r, i1].copy()
        d[r, i1] = 1e9
        i2 = d.argmin(1)
        d2 = d[r, i2]
        a = np.clip((np.sqrt(np.maximum(d2, 0)) - np.sqrt(np.maximum(d1, 0))) / 5.0, 0, 1) * 0.5 + 0.5
        base = self.pal_g[i1] * a[:, None] + self.pal_g[i2] * (1 - a[:, None])
        refL = pal[i1][:, 0] * a + pal[i2][:, 0] * (1 - a)
        h, w = lab_h.shape[:2]
        self._i1 = i1.reshape(h, w)
        return base.reshape(h, w, 3), refL.reshape(h, w)

    def __call__(self, rgb, light_mask=None, skin=True, stage=None):
        """stage (optional) runs the press part-way: {'inks': k} lays the palette inks light -> dark, the k-th one
        still being rolled across left -> right; 'dots', 'lines', 'halo' in 0..1 fade those plates"""
        assert self.pal is not None, 'fit() the printer on a few frames of the shot first'
        hw, hh = W // 2, H // 2
        u8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
        half = cv2.resize(u8, (hw, hh), interpolation=cv2.INTER_AREA)
        flat_h = cv2.bilateralFilter(cv2.pyrMeanShiftFiltering(half, 5, 16), 5, 24, 4).astype(np.float32) / 255.0
        base_lab_h, refL_h = self._assign(to_lab(flat_h))
        skin_h = None
        if skin:          # faces and hands print on a warm cream; the screen carries their shading (manga print)
            sk = skin_regions(flat_h)
            if sk is not None:
                sm, skin_lab_map, ref_map = sk
                sm3 = sm[..., None]
                base_lab_h = base_lab_h * (1 - sm3) + skin_lab_map * sm3
                refL_h = refL_h * (1 - sm) + ref_map * sm
                skin_h = sm
        if stage is not None and stage.get('inks', 1e9) < len(self.pal):
            k = max(0.0, float(stage['inks']))
            order = np.argsort(-self.pal_g[:, 0])                 # lightest ink first
            rank = np.empty(len(order), np.int32)
            rank[order] = np.arange(len(order))
            r = rank[self._i1] // max(1, int(stage.get('group', 1)))
            xs = np.linspace(0, 1, r.shape[1], dtype=np.float32)[None, :]
            frac = k - math.floor(k)
            vis = (r < math.floor(k)).astype(np.float32) + (r == math.floor(k)) * np.clip((frac * 1.15 - xs) / 0.06, 0, 1)
            paper = to_lab((np.float32(CREAM) / 255)[None, None])[0, 0]
            vis = cv2.GaussianBlur(vis.astype(np.float32), (0, 0), 0.8)[..., None]
            base_lab_h = paper[None, None] + (base_lab_h - paper[None, None]) * vis
        base_lab = cv2.resize(base_lab_h, (W, H), interpolation=cv2.INTER_LINEAR)
        ref_L = cv2.resize(refL_h, (W, H), interpolation=cv2.INTER_LINEAR)
        base = from_lab(base_lab)
        st = stage or {}
        # shading: the real image darker / lighter than its flat ink -> halftone
        L = to_lab(rgb)[..., 0]
        dark = np.clip((ref_L - L - 3.0) / 26.0, 0, 1) * self.shade_amt
        if skin_h is not None:                                 # faces stay mostly clean: lighter screen on skin
            sk = cv2.resize(skin_h, (W, H), interpolation=cv2.INTER_LINEAR)
            dark = dark * (1 - 0.45 * sk) - 0.06 * sk
            dark = np.clip(dark, 0, 1)
        light = np.clip((L - ref_L - 4.0) / 28.0, 0, 1) * self.shade_amt
        p = self.period
        dk = dots(dark, screen(p, 45.0), p) * st.get('dots', 1.0)
        shade_col = base * (1 - self.dot_dark) + np.float32(BLACK) / 255 * self.dot_dark
        out = base + (shade_col - base) * dk[..., None]
        lt = dots(light * 0.85, screen(p, 15.0), p) * st.get('dots', 1.0)
        out = out + (np.float32(CREAM) / 255 - out) * (lt[..., None] * 0.6)
        # AM halos around light sources (lamps, windows, sun, moon, fireworks)
        if self.glow_amt > 0 and st.get('halo', 1.0) > 0:
            bright = np.clip((L - 78.0) / 18.0, 0, 1) if light_mask is None else light_mask
            bq = cv2.resize(bright, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
            halo = cv2.GaussianBlur(bq, (0, 0), 5.5) * 1.6 + cv2.GaussianBlur(bq, (0, 0), 1.8) * 0.6
            halo = np.clip(cv2.resize(halo, (W, H), interpolation=cv2.INTER_LINEAR), 0, 1) * self.glow_amt
            hp = p * 1.35
            hd = dots(halo * 0.8, screen(hp, 45.0), hp)
            gcol = hexc('#F5C842') * 0.55 + np.float32(CREAM) / 255 * 0.45
            out = out + (gcol - out) * (hd[..., None] * 0.55 * st.get('halo', 1.0))
        # ink linework (XDoG); gold / cream on dark inks (the reference's night architecture)
        if self.lines_amt > 0 and st.get('lines', 1.0) > 0:
            y = cv2.cvtColor(u8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
            g1 = cv2.GaussianBlur(y, (0, 0), 0.95)
            g2 = cv2.GaussianBlur(y, (0, 0), 1.6 * 0.95)
            xd = g1 - 0.985 * g2
            ln = 1 - np.clip(1 - np.tanh(np.maximum(0, -xd - 0.007) * 70), 0, 1)
            ln = cv2.GaussianBlur(ln, (0, 0), 0.55) * self.lines_amt
            if skin_h is not None:                         # faces keep their outline; creases inside the skin fade
                sk_in = cv2.erode(cv2.resize(skin_h, (W, H), interpolation=cv2.INTER_LINEAR), np.ones((7, 7), np.uint8))
                ln = ln * (1 - 0.6 * sk_in)
            on_dark = np.clip((34.0 - base_lab[..., 0]) / 14.0, 0, 1)[..., None]
            lcol = self.line[None, None] * (1 - on_dark) + self.gold[None, None] * on_dark
            la = ln[..., None] * (0.92 - 0.25 * on_dark) * st.get('lines', 1.0)
            out = out + (lcol - out) * la
        return np.clip(out, 0, 1)


def skin_regions(flat, grow_de=24.0, cream_mix=0.58):
    """whole faces / hands as consistent regions, so a face half in lantern light does not print half cream, half tan:
    strict skin cores (skin_mask_scene) are grown into neighbouring pixels of similar colour (Lab distance to the
    core's median), within a radius of the core. Each region gets ONE ink -- its median colour pulled toward the
    paper's warm cream -- and one reference lightness (its lit side), so the halftone carries its shading.
    Returns (soft mask, ink Lab map, reference L map) at the input's resolution, or None."""
    sm, core = skin_mask_scene(flat)
    if not core.any():
        return None
    h, w = core.shape
    lab = to_lab(flat)
    n, lab_c, st, _ = cv2.connectedComponentsWithStats(core.astype(np.uint8), 8)
    region = np.zeros((h, w), np.float32)
    ink = np.zeros((h, w, 3), np.float32)
    ref = np.zeros((h, w), np.float32)
    cream = to_lab((np.float32(CREAM) / 255 * 0.82 + hexc('#E8A890') * 0.18)[None, None])[0, 0]
    r = max(4, int(h * 0.05))
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < max(30, int(h * w * 0.0002)):
            continue
        x, y, ww, hh = st[i, :4]
        x0, y0, x1, y1 = max(0, x - r), max(0, y - r), min(w, x + ww + r), min(h, y + hh + r)
        comp = (lab_c[y0:y1, x0:x1] == i).astype(np.uint8)
        m = np.median(lab[y0:y1, x0:x1][comp > 0], axis=0)
        near = cv2.dilate(comp, ker) > 0
        win = lab[y0:y1, x0:x1]
        d = np.sqrt(((win - m) ** 2).sum(-1))
        chroma = np.sqrt(win[..., 1] ** 2 + win[..., 2] ** 2)
        hue = np.degrees(np.arctan2(win[..., 2], win[..., 1]))
        # skin keeps its warm chroma in any light; grey asphalt or a motion-blurred edge next to a leg does not
        warm = (chroma >= max(7.0, 0.45 * float(np.hypot(m[1], m[2])))) & (hue > -5) & (hue < 105)
        cand = ((d < grow_de) & near & warm & (win[..., 0] > 22)).astype(np.uint8) | comp
        nn, lab_g = cv2.connectedComponents(cand, 8)
        keep = np.unique(lab_g[comp > 0])
        keep = keep[keep > 0]
        grown = np.isin(lab_g, keep).astype(np.uint8)
        grown = cv2.morphologyEx(grown, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        Lr = lab[y0:y1, x0:x1, 0][grown > 0]
        lit = float(np.percentile(Lr, 75)) if Lr.size > 20 else float(m[0])
        tgt = m * (1 - cream_mix) + cream * cream_mix
        tgt[0] = max(tgt[0], min(90.0, lit * 0.25 + cream[0] * 0.75))
        g = grown.astype(np.float32)
        sub = region[y0:y1, x0:x1]
        newer = g > sub
        sub[newer] = g[newer]
        ink[y0:y1, x0:x1][newer] = tgt
        ref[y0:y1, x0:x1][newer] = min(lit + 3.0, 92.0)
    if region.max() <= 0:
        return None
    soft = cv2.GaussianBlur(region, (0, 0), 1.2)
    ink = cv2.GaussianBlur(ink, (0, 0), 1.2) / np.maximum(cv2.GaussianBlur(region, (0, 0), 1.2), 1e-3)[..., None]
    ref = cv2.GaussianBlur(ref, (0, 0), 1.2) / np.maximum(cv2.GaussianBlur(region, (0, 0), 1.2), 1e-3)
    return soft, ink, ref


def skin_mask_scene(flat):
    """(soft mask, core) of anime skin in a full scene: warm hue, MODERATE saturation (an orange curve mirror or a
    lantern is far more saturated), reasonably bright; enclosed reddish holes (an open mouth) filled; blush near skin
    only"""
    f8 = (np.clip(flat, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(f8, cv2.COLOR_RGB2HSV)
    Hh, S, V = hsv[..., 0].astype(np.int16), hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
    R, G, B = f8[..., 0].astype(np.int16), f8[..., 1].astype(np.int16), f8[..., 2].astype(np.int16)
    core = ((Hh <= 22) & (S >= 22) & (S <= 140) & (V >= 95) & (R > G) & (G * 100 >= B * 92) & (R - B >= 14)).astype(np.uint8)
    core = cv2.morphologyEx(core, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    h, w = core.shape
    n, lab, stats, _ = cv2.connectedComponentsWithStats(core, 8)
    keep = np.zeros(n, bool)
    if n > 1:
        areas = stats[1:, cv2.CC_STAT_AREA]
        keep[1:] = areas >= max(40, int(h * w * 0.0003))
    core = keep[lab].astype(np.uint8)
    r = max(3, int(h * 0.012))
    near = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    blush = (((Hh <= 12) | (Hh >= 165)) & (S >= 40) & (S <= 150) & (V >= 80)).astype(np.uint8)
    m = np.maximum(core, near & blush)
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2), core.astype(bool)


def light_mask_from(rgb, thresh=0.82):
    """explicit light sources for the halos: very bright, smallish regions"""
    y = rgb @ np.float32([0.2126, 0.7152, 0.0722])
    return np.clip((y - thresh) / (1 - thresh), 0, 1)

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


def moon_path(img, idx, t, x=990, y0=330, size=74, lead=1.18, slant=0.0):
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
        xc = x + slant * (yy - y0)                                             # the column opens out toward us
        # broken by the waves: horizontal slices shifted by the swell, more so nearer the shore
        rows = np.arange(h, dtype=np.float32)
        amp = (3 + 9 * persp) * (1.0 + 0.6 * math.sin(t * 1.3 + i)) * min(1.0, size / 74.0)   # stays legible small
        shift = amp * np.sin(rows / (5.0 + persp * 3) + t * 5.0 + i * 1.7)
        shift = np.round(shift / 2) * 2
        broken = np.zeros_like(g)
        for r in range(h):
            broken[r] = np.roll(g[r], int(shift[r]))
        gaps = (np.sin(rows * 0.9 + t * 7 + i) > 0.62).astype(np.float32)[:, None]
        broken *= 1 - gaps * 0.85
        a = clamp(k) * out_a
        glow = cv2.GaussianBlur(broken, (0, 0), 6) * 0.8
        img = _blend(img, glow, int(xc - w / 2), yy, '#9FB8E0', a * 0.6)
        img = _blend(img, broken, int(xc - w / 2), yy, '#F3EBD9', a)
        tw = np.clip(np.sin(rows[:, None] * 2.1 + np.arange(w)[None, :] * 0.7 + t * 11) - 0.93, 0, 1) * 12 * broken
        img = _blend(img, np.clip(tw, 0, 1), int(xc - w / 2), yy, '#FFFFFF', a)
    return img


# ------------------------------------------------------------------ bubbles (bridge1-01): one glyph per bubble, popped on its mora
def bubbles(img, idx, t, x0=1560, y0=190, size=70, lead=1.55, seed=4):
    ln = LYRICS[idx]
    gt = glyph_times()[str(idx)]
    chars = [c for c in ln['text'] if not c.isspace()]
    rng = np.random.default_rng(seed)
    jit = rng.uniform(-1, 1, (len(chars), 3))
    t_in = ln['t'] - 0.6
    out_a = 1 - clamp((t - ln['end'] - 0.2) / 0.4)
    if t < t_in or out_a <= 0:
        return img
    for i, ch in enumerate(chars[:len(gt)]):
        rise = (t - t_in) * 26
        cx = x0 + (i % 2) * 130 + 16 * math.sin(t * 1.6 + i * 1.3) + jit[i, 0] * 14
        cy = y0 + i * size * lead + 60 - rise * (0.6 + 0.4 * jit[i, 1]) + 18 * jit[i, 2]
        r = size * 0.78
        k = (t - gt[i]) / 0.22                       # >0 once sung: the bubble pops
        g = glyph_mask(ch, size)
        gh, gw = g.shape
        a = clamp((t - t_in - i * 0.04) / 0.3) * out_a
        if k < 1:
            # the bubble: thin bright rim, a highlight, a faint fill; it swells as it is about to pop
            sc = 1 + 0.18 * clamp(k * 2)
            ring = np.zeros((int(2 * r * sc) + 8, int(2 * r * sc) + 8), np.float32)
            c0 = ring.shape[0] / 2
            cv2.circle(ring, (int(c0 * 4), int(c0 * 4)), int(r * sc * 4), 1.0, 2, cv2.LINE_AA, shift=2)
            hl = np.zeros_like(ring)
            cv2.ellipse(hl, (int((c0 - r * 0.42) * 4), int((c0 - r * 0.45) * 4)), (int(r * 0.22 * 4), int(r * 0.12 * 4)), -35, 0, 360,
                        1.0, -1, cv2.LINE_AA, shift=2)
            fill = np.zeros_like(ring)
            cv2.circle(fill, (int(c0 * 4), int(c0 * 4)), int(r * sc * 4), 1.0, -1, cv2.LINE_AA, shift=2)
            img = _blend(img, fill, int(cx - c0), int(cy - c0), '#9FC4E8', a * 0.16 * (1 - clamp(k)))
            img = _blend(img, ring, int(cx - c0), int(cy - c0), '#DDEBF7', a * 0.9 * (1 - clamp(k)))
            img = _blend(img, hl, int(cx - c0), int(cy - c0), '#FFFFFF', a * 0.85 * (1 - clamp(k)))
        if k >= 0 and k < 1.6:                       # the pop: a burst of droplets
            m = np.zeros((int(r * 4), int(r * 4)), np.float32)
            c0 = m.shape[0] / 2
            for j in range(10):
                ang = j / 10 * 2 * math.pi + i
                dd = r * (0.9 + 0.9 * clamp(k / 1.6))
                cv2.circle(m, (int((c0 + math.cos(ang) * dd) * 4), int((c0 + math.sin(ang) * dd) * 4)),
                           int(max(1, 5 * (1 - k / 1.6)) * 4), 1.0, -1, cv2.LINE_AA, shift=2)
            img = _blend(img, m, int(cx - c0), int(cy - c0), '#E6F2FF', a * (1 - clamp(k / 1.6)))
        # the glyph: pale inside its bubble, flashing to full cream when its bubble breaks
        ga = a * (0.55 + 0.45 * clamp(k * 3)) if k > 0 else a * 0.55
        glow = cv2.GaussianBlur(g, (0, 0), 5) * (0.9 * math.exp(-max(0.0, k) * 1.5) if k > 0 else 0)
        img = _blend(img, glow, int(cx - gw / 2), int(cy - gh * 0.62), '#BFE0FF', a)
        img = _blend(img, g, int(cx - gw / 2), int(cy - gh * 0.62), '#F3EBD9', ga)
    return img


# ------------------------------------------------------------------ willow (chorus3-08): glyphs hang like willow strands and drip
def willow(img, idx, t, x0=1680, y0=90, size=70, lead=1.12, col='#F5D27A'):
    ln = LYRICS[idx]
    gt = glyph_times()[str(idx)]
    chars = [c for c in ln['text'] if not c.isspace()]
    out_a = 1 - clamp((t - ln['end'] - 0.6) / 0.8)
    if out_a <= 0:
        return img
    for i, ch in enumerate(chars[:len(gt)]):
        k = t - gt[i]
        if k <= 0:
            continue
        g = glyph_mask(ch, size)
        gh, gw = g.shape
        sag = 22 * (1 - math.exp(-k * 0.9)) + 6 * k                       # the strand droops as the sparks fall
        x = x0 - (i // 6) * size * 1.25 + 4 * math.sin(t * 1.1 + i * 0.7)
        y = y0 + (i % 6) * size * lead + sag + 3 * (i % 6) ** 1.4
        a = clamp(k / 0.25) * out_a
        drip = clamp((k - 0.4) / 1.6)
        if drip > 0:                                                         # a drop runs down from the glyph
            m = np.zeros((int(size * 3.5), gw), np.float32)
            dy = int(drip * size * 2.8)
            cv2.line(m, (gw // 2, int(gh * 0.9)), (gw // 2, int(gh * 0.9) + dy), 1.0, 2, cv2.LINE_AA)
            cv2.circle(m, (gw // 2, int(gh * 0.9) + dy), 4, 1.0, -1, cv2.LINE_AA)
            img = _blend(img, m, int(x - gw / 2), int(y - gh * 0.62), col, a * 0.8 * (1 - clamp((k - 2.0) / 1.0)))
        sp = cv2.GaussianBlur(g, (0, 0), 4) * 0.9
        img = _blend(img, sp, int(x - gw / 2), int(y - gh * 0.62), '#F08A3C', a * 0.7)
        img = _blend(img, g, int(x - gw / 2), int(y - gh * 0.62), col, a)
    return img


# ------------------------------------------------------------------ long shadows (bridge1-03): the line cast across the concrete
def long_shadow(img, idx, t, quad, size=150, col='#2A1A22', alpha=0.62):
    """the line as a horizontal run of glyphs, projected onto the ground quad (TL, TR, BR, BL) like a shadow cast by
    the low sun; glyphs fall in on their syllables"""
    ln = LYRICS[idx]
    gt = glyph_times()[str(idx)]
    chars = [c for c in ln['text'] if not c.isspace()]
    out_a = 1 - clamp((t - ln['end'] - 0.2) / 0.5)
    if out_a <= 0:
        return img
    n = len(chars[:len(gt)])
    cw, ch_ = int(size * 1.05), int(size * 1.5)
    pad = int(size)
    sheet = np.zeros((ch_, cw * n + 2 * pad), np.float32)
    for i, c in enumerate(chars[:n]):
        k = clamp((t - gt[i]) / 0.25)
        if k <= 0:
            continue
        g = glyph_mask(c, size)
        gh, gw = g.shape
        x = pad + i * cw + (cw - gw) // 2
        hh = min(ch_, gh)
        sheet[:hh, x:x + gw] = np.maximum(sheet[:hh, x:x + gw], g[:hh] * k)
    sheet = cv2.GaussianBlur(sheet, (0, 0), 2.0)
    q = np.asarray(quad, np.float32)
    Hm = cv2.getPerspectiveTransform(np.float32([[0, 0], [sheet.shape[1], 0], [sheet.shape[1], sheet.shape[0]], [0, sheet.shape[0]]]), q)
    m = cv2.warpPerspective(sheet, Hm, (W, H_), flags=cv2.INTER_LINEAR)
    m = cv2.GaussianBlur(m, (0, 0), 1.5) * alpha * out_a
    return img * (1 - m[..., None] * (1 - H(col))[None, None])


# ------------------------------------------------------------------ firework glyphs (chorus3-05, chorus3-06)
@functools.lru_cache(maxsize=16)
def glyph_points(txt, size=300, n=1500, name='kaku', seed=1):
    import skia
    from mv import text
    f = text.font(name, size)
    w = int(f.measureText(txt) + size * 0.4)
    h = int(size * 1.4)
    info = skia.ImageInfo.Make(w, h, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType)
    surf = skia.Surface.MakeRaster(info)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    c.drawString(txt, size * 0.2, size * 1.05, f, skia.Paint(AntiAlias=True, Color=skia.Color4f(1, 1, 1, 1)))
    a = np.empty((h, w), np.uint8)
    surf.readPixels(info, a, w)
    ys, xs = np.nonzero(a > 128)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(xs), size=min(n, len(xs)), replace=False)
    pts = np.stack([xs[idx] - w / 2, ys[idx] - h / 2], 1).astype(np.float32)
    return pts


def firework(img, t, t0, cx, cy, radius=260, n=1500, col='#F5C842', col2='#FF7A3C', glyph=None, gsize=300, seed=0,
             dur=2.2):
    """a halftone-spark burst at (cx, cy) launched at t0; with `glyph` the sparks settle into its letterform"""
    k = t - t0
    if k < 0 or k > dur:
        return img
    rng = np.random.default_rng(seed)
    if glyph is not None:
        tgt = glyph_points(glyph, gsize, n)
        n = len(tgt)
    ang = rng.uniform(0, 2 * math.pi, n)
    spd = rng.uniform(0.55, 1.0, n)
    e = 1 - math.exp(-k * 4.0)
    if glyph is None:
        px = cx + np.cos(ang) * radius * spd * e
        py = cy + np.sin(ang) * radius * spd * e + 60 * k * k
    else:
        bx = cx + np.cos(ang) * radius * 0.35 * spd * min(1.0, k * 6)
        by = cy + np.sin(ang) * radius * 0.35 * spd * min(1.0, k * 6)
        s2 = clamp((k - 0.10) / 0.45)
        s2 = s2 * s2 * (3 - 2 * s2)
        px = bx + (cx + tgt[:, 0] - bx) * s2
        py = by + (cy + tgt[:, 1] - by) * s2 + 30 * max(0.0, k - 1.1) ** 2
    fade = 1 - clamp((k - dur * 0.55) / (dur * 0.45))
    m = np.zeros((H_, W), np.float32)
    twinkle = (rng.random(n) + k * 3) % 1.0 > 0.25
    r = max(1, int(round(4 * (1 - 0.4 * clamp(k / dur)))))
    for x, y, on in zip(px, py, twinkle):
        if on and 0 <= x < W and 0 <= y < H_:
            cv2.circle(m, (int(x * 4), int(y * 4)), r * 4, 1.0, -1, cv2.LINE_AA, shift=2)
    glow = cv2.GaussianBlur(m, (0, 0), 7) * 1.4
    img = img + H(col2)[None, None] * (glow * fade * 0.8)[..., None]
    img = img + (H(col)[None, None] - img) * (np.clip(m, 0, 1) * fade)[..., None]
    if k < 0.12:                                                              # the flash of the burst
        fl = np.exp(-((_xs() - cx) ** 2 + (_ys() - cy) ** 2) / (2 * 120.0 ** 2)) * (1 - k / 0.12)
        img = img + H('#FFF2C8')[None, None] * fl[..., None] * 0.8
    return img


@functools.lru_cache(maxsize=1)
def _grid():
    return np.mgrid[0:H_, 0:W].astype(np.float32)


def _xs():
    return _grid()[1]


def _ys():
    return _grid()[0]


# ------------------------------------------------------------------ road text (outro_hook-01): the line painted on the road
ROAD_CW, ROAD_CH = 1000, 2200          # the road rectangle as a canvas: x = across (edge to edge), y = far (0) .. near


@functools.lru_cache(maxsize=16)
def road_word(word, height=300, max_w=820, name='kaku'):
    """one word as road paint: heavy gothic, stretched along the road (x2.6) so it reads under the foreshortening;
    worn (grain of the asphalt showing through)"""
    g = glyph_mask_line(word, 120, name)
    h, w = g.shape
    out_w = min(max_w, int(w * height / (h * 2.6)))
    m = cv2.resize(g, (out_w, height), interpolation=cv2.INTER_AREA)
    rng = np.random.default_rng(abs(hash(word)) % 1000)
    wear = cv2.GaussianBlur(rng.random(m.shape).astype(np.float32), (0, 0), 2.0)
    wear = (wear - wear.min()) / (wear.max() - wear.min() + 1e-6)
    return m * np.clip(0.55 + 0.7 * wear, 0, 1)


@functools.lru_cache(maxsize=32)
def glyph_mask_line(txt, size, name='kaku'):
    import skia
    from mv import text
    f = text.font(name, size)
    w = int(f.measureText(txt) + size * 0.3)
    h = int(size * 1.25)
    info = skia.ImageInfo.Make(w, h, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType)
    surf = skia.Surface.MakeRaster(info)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    c.drawString(txt, size * 0.15, size * 0.98, f, skia.Paint(AntiAlias=True, Color=skia.Color4f(1, 1, 1, 1)))
    a = np.empty((h, w), np.uint8)
    surf.readPixels(info, a, w)
    a = a.astype(np.float32) / 255.0
    ys, xs = np.nonzero(a > 0.05)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else a


def road_text(img, words, times, t, quad, v_slots=(0.20, 0.36, 0.52, 0.68, 0.84), col='#F2B23A'):
    """paint words on a road: quad = the road rectangle's image corners (near-left, near-right, far-right, far-left);
    word i sits at v_slots[i] (0 near .. 1 far) and appears on times[i] (a quick press-in)"""
    canvas = np.zeros((ROAD_CH, ROAD_CW), np.float32)
    any_on = False
    for i, (wd, t0) in enumerate(zip(words, times)):
        k = (t - t0) / 0.14
        if k <= 0:
            continue
        any_on = True
        m = road_word(wd)
        h, w = m.shape
        cy = int((1 - v_slots[i]) * ROAD_CH)
        y0, x0 = cy - h // 2, (ROAD_CW - w) // 2
        canvas[y0:y0 + h, x0:x0 + w] = np.maximum(canvas[y0:y0 + h, x0:x0 + w], m * clamp(k))
    if not any_on:
        return img
    q = np.asarray(quad, np.float32)
    src = np.float32([[0, ROAD_CH], [ROAD_CW, ROAD_CH], [ROAD_CW, 0], [0, 0]])
    Hm = cv2.getPerspectiveTransform(src, q)
    a = cv2.warpPerspective(canvas, Hm, (W, H_), flags=cv2.INTER_AREA)
    a = cv2.GaussianBlur(a, (0, 0), 0.6) * 0.97
    ys, xs = np.mgrid[0:H_, 0:W].astype(np.float32)               # printed paint: a fine 45-degree screen in the ink
    u, v = (xs + ys) / (5.0 * 1.4142), (xs - ys) / (5.0 * 1.4142)
    dd = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    a = a * np.clip(0.78 + (0.62 - dd) * 0.6, 0.6, 1.0)
    lum = img @ np.float32([0.2126, 0.7152, 0.0722])
    paint = H(col)[None, None] * np.clip(0.45 + 0.6 * lum, 0.6, 1.05)[..., None]      # yellow road paint, lit like the asphalt
    return img + (paint - img) * a[..., None]

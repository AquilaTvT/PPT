"""Japanese / English kinetic typography (vertical 縦書き and horizontal)."""
import functools
import math
import os

import numpy as np
import skia

from . import core
from .core import Mask, clamp, ease_out, back_out

FONT_DIR = os.environ.get('HW_FONT_DIR', os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts'))

FONTS = {
    'mincho': 'ShipporiMincho-ExtraBold.ttf',
    'mincho_sb': 'ShipporiMincho-SemiBold.ttf',
    'mincho_r': 'ShipporiMincho-Regular.ttf',
    'old': 'ZenOldMincho-Black.ttf',
    'old_b': 'ZenOldMincho-Bold.ttf',
    'dot': 'DotGothic16-Regular.ttf',
    'dela': 'DelaGothicOne-Regular.ttf',
    'brush': 'YujiSyuku-Regular.ttf',
    'kaku': 'ZenKakuGothicNew-Black.ttf',
    'kaku_m': 'ZenKakuGothicNew-Medium.ttf',
    'hina': 'HinaMincho-Regular.ttf',
    'klee': 'KleeOne-SemiBold.ttf',
    'vt': 'VT323-Regular.ttf',
    'silk': 'Silkscreen-Regular.ttf',
    'garamond': 'EBGaramond[wght].ttf',
    'garamond_i': 'EBGaramond-Italic[wght].ttf',
    'corm_i': 'CormorantGaramond-Italic[wght].ttf',
    'pixelify': 'PixelifySans[wght].ttf',
    'zh': ('NotoSerifSC[wght].ttf', 600),
    'zh_b': ('NotoSerifSC[wght].ttf', 800),
}


@functools.lru_cache(maxsize=64)
def typeface(name):
    spec = FONTS.get(name, name)
    wght = None
    if isinstance(spec, tuple):
        spec, wght = spec
    p = os.path.join(FONT_DIR, spec)
    tf = skia.Typeface.MakeFromFile(p)
    if tf is None:
        raise FileNotFoundError(p)
    if wght is not None:
        tag = (ord('w') << 24) | (ord('g') << 16) | (ord('h') << 8) | ord('t')
        coord = skia.FontArguments.VariationPosition.Coordinate(tag, float(wght))
        pos = skia.FontArguments.VariationPosition(skia.FontArguments.VariationPosition.Coordinates([coord]))
        args = skia.FontArguments()
        args.setVariationDesignPosition(pos)
        tf = tf.makeClone(args)
    return tf


@functools.lru_cache(maxsize=256)
def font(name, size):
    f = skia.Font(typeface(name), float(size))
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


ROTATE_V = set('ー－—―〜～…‥()（）[]［］「」『』【】<>〈〉《》-=~:：;；')
SMALL_KANA = set('ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ')
PUNCT_TR = set('、。，．,.')


def char_box(fnt, ch):
    """returns (advance, glyph_bounds Rect) for one char"""
    g = fnt.textToGlyphs(ch)
    w = fnt.getWidths(g)[0] if len(g) else fnt.getSize()
    b = fnt.getBounds(g)[0] if len(g) else skia.Rect(0, 0, 0, 0)
    return w, b


def layout_v(text, x, y, size, fname='mincho', tracking=0.06, col_gap=1.25):
    """Vertical layout. Returns list of glyph dicts with centre positions.

    '\n' starts a new column to the LEFT (Japanese reading order).
    x is the column centre of the first (rightmost) column, y the top.
    """
    out = []
    cx, cy = x, y
    col = 0
    idx = 0
    for ch in text:
        if ch == '\n':
            col += 1
            cx = x - col * size * col_gap
            cy = y
            continue
        if ch == ' ' or ch == '　':
            cy += size * 0.6
            continue
        adv = size * (1 + tracking)
        g = dict(ch=ch, cx=cx, cy=cy + size * 0.5, rot=0.0, size=size, font=fname, i=idx, col=col)
        if ch in ROTATE_V:
            g['rot'] = 90.0
        if ch in SMALL_KANA:
            g['cx'] += size * 0.1
            g['cy'] -= size * 0.08
            adv = size * (0.92 + tracking)
        if ch in PUNCT_TR:
            g['cx'] += size * 0.55
            g['cy'] -= size * 0.55
            adv = size * 0.55
        out.append(g)
        cy += adv
        idx += 1
    return out


def layout_h(text, x, y, size, fname='mincho', tracking=0.0, align='left'):
    """Horizontal layout on a baseline-centred line. x,y = anchor (y is visual centre)."""
    fnt = font(fname, size)
    glyphs = []
    pen = 0.0
    idx = 0
    for ch in text:
        w, b = char_box(fnt, ch)
        glyphs.append(dict(ch=ch, adv=w, b=b))
        pen += w + tracking * size
    total = pen - tracking * size if glyphs else 0
    if align == 'center':
        pen0 = x - total / 2
    elif align == 'right':
        pen0 = x - total
    else:
        pen0 = x
    out = []
    pen = pen0
    m = fnt.getMetrics()
    # visual centre of the line ~ between ascent and descent
    base = y + (-(m.fAscent) - m.fDescent) / 2 * 0.9
    for g in glyphs:
        if g['ch'] != ' ':
            out.append(dict(ch=g['ch'], cx=pen + g['adv'] / 2, cy=y, base=base, rot=0.0, size=size,
                            font=fname, i=idx, adv=g['adv'], col=0))
            idx += 1
        pen += g['adv'] + tracking * size
    return out, total


def _draw_glyph(c, g, paint, extra_scale=1.0, dx=0.0, dy=0.0, rot=0.0):
    fnt = font(g['font'], g['size'])
    ch = g['ch']
    w, b = char_box(fnt, ch)
    c.save()
    c.translate(g['cx'] + dx, g['cy'] + dy)
    r = g['rot'] + rot
    if r:
        c.rotate(r)
    s = extra_scale * g.get('scale', 1.0)
    if s != 1.0:
        c.scale(s, s)
    # centre glyph bounds on origin (ideographic centring)
    if 'base' in g and not g['rot']:
        ox = -w / 2
        oy = g['base'] - g['cy']
    else:
        ox = -w / 2
        oy = -(b.top() + b.bottom()) / 2 if ch not in SMALL_KANA else -(b.top() + b.bottom()) / 2
        if g['rot']:
            oy = -(b.top() + b.bottom()) / 2
    c.drawString(ch, ox, oy, fnt, paint)
    c.restore()


def render_glyphs(glyphs, stroke=0.0, fill=True, anim=None, blur_fill=0.0):
    """Rasterise glyphs. anim(g) -> dict(alpha, scale, dx, dy, rot, blur) or None to skip.

    returns (fill_cov, stroke_cov)
    """
    fill_cov = stroke_cov = None
    states = []
    for g in glyphs:
        st = anim(g) if anim else dict(alpha=1.0)
        if st is None or st.get('alpha', 1.0) <= 0.003:
            continue
        states.append((g, st))
    if not states:
        return None, None
    if fill:
        with Mask() as (c, m):
            for g, st in states:
                p = core.P(alpha=st.get('alpha', 1.0), blur=st.get('blur', 0.0) + blur_fill)
                _draw_glyph(c, g, p, st.get('scale', 1.0), st.get('dx', 0.0), st.get('dy', 0.0), st.get('rot', 0.0))
        fill_cov = m.cov
    if stroke > 0:
        with Mask() as (c, m):
            for g, st in states:
                p = core.P(alpha=st.get('alpha', 1.0), stroke=stroke * st.get('stroke_k', 1.0), blur=st.get('blur', 0.0))
                _draw_glyph(c, g, p, st.get('scale', 1.0), st.get('dx', 0.0), st.get('dy', 0.0), st.get('rot', 0.0))
                # stroke paint also fills interior for a solid backing
                p2 = core.P(alpha=st.get('alpha', 1.0), blur=st.get('blur', 0.0))
                _draw_glyph(c, g, p2, st.get('scale', 1.0), st.get('dx', 0.0), st.get('dy', 0.0), st.get('rot', 0.0))
        stroke_cov = m.cov
    return fill_cov, stroke_cov


# --------------------------------------------------------------------------
# reveal animations
# --------------------------------------------------------------------------
def char_times(n, t0, t1, lead=0.0):
    """spread n char onsets across [t0, t1]"""
    if n <= 1:
        return [t0]
    return [t0 + (t1 - t0) * i / (n - 1) + lead for i in range(n)]


def reveal_drop(times, t, dur=0.28, drop=26.0, out_t=None, out_dur=0.35, blur=6.0):
    """per-char: fade in while dropping into place with a blur->sharp settle"""
    def anim(g):
        tc = times[min(g['i'], len(times) - 1)]
        k = clamp((t - tc) / dur)
        if k <= 0:
            return None
        e = ease_out(k, 3)
        a = e
        dy = -(1 - e) * drop
        bl = (1 - e) * blur
        sc = 1.0 + (1 - e) * 0.12
        if out_t is not None and t > out_t:
            ko = clamp((t - out_t - g['i'] * 0.02) / out_dur)
            a *= 1 - ko
            dy += ko * drop * 0.6
            bl += ko * blur
        return dict(alpha=a, dy=dy, blur=bl, scale=sc)
    return anim


def reveal_pop(times, t, dur=0.22, out_t=None, out_dur=0.3):
    def anim(g):
        tc = times[min(g['i'], len(times) - 1)]
        k = clamp((t - tc) / dur)
        if k <= 0:
            return None
        a = clamp(k * 2.5)
        sc = 0.35 + 0.65 * back_out(k, 2.4)
        if out_t is not None and t > out_t:
            ko = clamp((t - out_t) / out_dur)
            a *= 1 - ko
            sc *= 1 + ko * 0.3
        return dict(alpha=a, scale=sc)
    return anim


def reveal_type(times, t, out_t=None):
    """hard on/off — typewriter / LED"""
    def anim(g):
        tc = times[min(g['i'], len(times) - 1)]
        if t < tc:
            return None
        if out_t is not None and t > out_t:
            return None
        return dict(alpha=1.0)
    return anim


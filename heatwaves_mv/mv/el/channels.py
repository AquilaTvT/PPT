"""Tiny TV programmes, drawn at whatever resolution is active (used via tv.lowres)."""
import math

import numpy as np
import skia

from .. import core, text
from ..core import Frame, Layer, Mask, P, paint, path, halftone, smooth_path


def colour_bars(t):
    f = Frame('black')
    cols = ['#FFFDF6', '#FFCB45', '#7FE3DE', '#5FA746', '#FF5C9E', '#E8383D', '#2F5DC4']
    with Layer() as (c, L):
        for k, col in enumerate(cols):
            c.drawRect(skia.Rect.MakeXYWH(k * 1920 / 7, 0, 1920 / 7 + 2, 760), paint(col))
        for k, col in enumerate(['#2F5DC4', '#141B3D', '#FF5C9E', '#141B3D', '#7FE3DE', '#141B3D', '#FFFDF6']):
            c.drawRect(skia.Rect.MakeXYWH(k * 1920 / 7, 760, 1920 / 7 + 2, 110), paint(col))
        c.drawRect(skia.Rect.MakeXYWH(0, 870, 1920, 210), paint('#141B3D'))
    f.layer(L)
    return f.a


def weather(t):
    f = Frame('#2F5DC4')
    # simplified Japanese archipelago
    isl = [[(1180, 120), (1300, 90), (1380, 170), (1330, 260), (1220, 250)],
           [(1150, 300), (1250, 290), (1260, 420), (1180, 560), (1060, 640), (900, 700), (760, 760), (700, 720),
            (860, 640), (1000, 560), (1100, 450)],
           [(620, 760), (720, 760), (700, 840), (610, 830)],
           [(500, 800), (590, 790), (600, 900), (520, 960), (470, 880)]]
    with Layer() as (c, L):
        for poly in isl:
            c.drawPath(smooth_path(poly, close=True, tension=0.4), paint('#5FA746'))
            c.drawPath(smooth_path(poly, close=True, tension=0.4), paint('#FFFDF6', stroke=6))
        for (x, y) in ((1240, 180), (1130, 420), (900, 650), (560, 860)):
            c.drawCircle(x, y, 46, paint('#FFCB45'))
            for k in range(8):
                a = k * math.pi / 4 + t
                c.drawLine(x + math.cos(a) * 58, y + math.sin(a) * 58, x + math.cos(a) * 80, y + math.sin(a) * 80,
                           paint('#FFCB45', stroke=10))
    f.layer(L)
    gl, _ = text.layout_h('明日 34℃ 晴れ', 120, 120, 120, 'dot', align='left')
    fc, sc = text.render_glyphs(gl, stroke=14)
    f.over('#141B3D', sc)
    f.over('#FFFDF6', fc)
    return f.a


def baseball(t):
    f = Frame('#5FA746')
    with Layer() as (c, L):
        for k in range(12):
            c.drawRect(skia.Rect.MakeXYWH(0, k * 90, 1920, 45), paint('#4E9A3E'))
        dia = path([(960, 980), (1260, 680), (960, 380), (660, 680)])
        c.drawPath(dia, paint('#C98F3E'))
        c.drawPath(path([(960, 900), (1180, 680), (960, 460), (740, 680)]), paint('#5FA746'))
        for (x, y) in ((960, 980), (1260, 680), (960, 380), (660, 680)):
            c.drawRect(skia.Rect.MakeXYWH(x - 18, y - 18, 36, 36), paint('#FFFDF6'))
        c.drawCircle(960, 680, 40, paint('#C98F3E'))
        bx = 960 + math.sin(t * 6) * 120
        c.drawCircle(bx, 600 - abs(math.sin(t * 6)) * 200, 14, paint('#FFFDF6'))
    f.layer(L)
    gl, _ = text.layout_h('9回裏  2-3', 1800, 100, 90, 'dot', align='right')
    fc, sc = text.render_glyphs(gl, stroke=12)
    f.over('#141B3D', sc)
    f.over('#FFCB45', fc)
    return f.a


def hollywood(t, couple_k=0.0):
    """a sunset 'roadshow' movie: palms, a convertible on a coastal road, letterboxed"""
    f = Frame('#FF9A74')
    ys, xs = core.coords()
    field = np.clip(1 - ys / 640, 0, 1).astype(np.float32)
    f.a[:] = core.ramp(field, ['#FFE7B8', '#FFC489', '#FF9A74', '#F0686A', '#B8457A', '#5B3C8C'], cell=12, angle=45)
    f.over('#FFF1D6', core.mask(lambda c: c.drawCircle(960, 600, 170, P())))
    # sea
    sea = (ys > 640).astype(np.float32)
    f.over('#B8457A', sea)
    with Mask() as (c, m):
        for k in range(14):
            yy = 660 + k * 16
            w = 260 - k * 12
            c.drawLine(960 - w, yy, 960 + w, yy, P(stroke=5))
    f.over('#FFE7B8', m.cov * sea, alpha=0.8)
    # coastal road + car silhouette moving
    with Layer() as (c, L):
        c.drawRect(skia.Rect.MakeXYWH(-10, 760, 1940, 60), paint('#3B2E6E'))
        x = -450 + ((t * 420) % 2500)
        car = path([(x, 760), (x + 30, 712), (x + 120, 700), (x + 170, 660), (x + 260, 660), (x + 300, 700),
                    (x + 380, 708), (x + 400, 760)])
        c.drawPath(car, paint('#141B3D'))
        c.drawCircle(x + 80, 762, 26, paint('#141B3D'))
        c.drawCircle(x + 320, 762, 26, paint('#141B3D'))
        # two heads
        c.drawCircle(x + 200, 640, 22, paint('#141B3D'))
        c.drawCircle(x + 250, 636, 20, paint('#141B3D'))
        # hair blowing (one has a hat when couple_k grows -> "us")
        if couple_k > 0.5:
            c.drawOval(skia.Rect.MakeXYWH(x + 214, 612, 74, 16), paint('#141B3D'))
        # palms
        for px in (180, 1700, 1560):
            c.drawLine(px, 820, px + 30, 330, paint('#141B3D', stroke=24))
            for k in range(7):
                a = -math.pi / 2 + (k - 3) * 0.5 + math.sin(t * 2 + k) * 0.05
                pth = skia.Path()
                pth.moveTo(px + 30, 330)
                pth.quadTo(px + 30 + math.cos(a) * 160, 330 + math.sin(a) * 160 - 40, px + 30 + math.cos(a) * 260,
                           330 + math.sin(a) * 260 + 60)
                c.drawPath(pth, paint('#141B3D', stroke=20, cap='round'))
    f.layer(L)
    # letterbox + subtitle
    lb = ((ys < 150) | (ys > 930)).astype(np.float32)
    f.over('black', lb)
    return f.a


def osd(f, label, x=1700, y=110, size=86, color='#7FE3DE'):
    gl, _ = text.layout_h(label, x, y, size, 'dot', align='right')
    fc, sc = text.render_glyphs(gl, stroke=14)
    f.over('black', sc)
    f.over(color, fc)

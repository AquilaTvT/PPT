"""Midnight town: house with the TV-lit window, street lamp & moths, block wall,
power lines, vending machine."""
import math

import numpy as np
import skia

from .. import core
from ..core import Layer, Mask, P, paint, path, smooth_path, halftone, View


def sky(f, v, horizon=760, moon=(380, 200, 70), stars=True, t=0.0, cols=None):
    ys, xs = core.coords()
    hz = v.pt(0, horizon)[1]
    field = np.clip(1 - ys / max(1, hz), 0, 1).astype(np.float32)
    f.a[:] = core.ramp(field, cols or ['#2A3570', '#1E2A5E', '#141B3D', '#0B1030', '#06081A'], cell=7, angle=45)
    if stars:
        rng = np.random.default_rng(12)
        with Mask(v) as (c, m):
            for i in range(120):
                x, y = rng.uniform(-200, 2120), rng.uniform(-200, horizon - 120)
                a = 0.45 + 0.55 * math.sin(t * rng.uniform(1, 3) + i)
                c.drawCircle(x, y, rng.uniform(0.9, 2.3), P(alpha=a))
        f.over('#F4EAD6', m.cov)
    if moon:
        mx, my, mr = moon
        g = core.radial(mx, my, mr * 3.4, falloff=2.2, view=v)
        f.over('#F4EAD6', halftone(g * 0.5, cell=7, angle=45), alpha=0.7)
        mc = core.mask(lambda c: c.drawCircle(mx, my, mr, P()), v)
        f.over('#FFF6DA', mc)
        with Mask(v) as (c, m):
            for (ax, ay, ar) in ((-20, -12, 20), (16, 18, 16), (24, -22, 11), (-8, 28, 10)):
                c.drawCircle(mx + ax * mr / 60, my + ay * mr / 60, ar * mr / 60, P(blur=4))
        f.mul('#E2CFA6', halftone(m.cov * mc * 0.8, cell=4, angle=45))


def house(f, v, t, x=520, ground=900, tv_glow=1.0, flicker=1.0, porch=True):
    """two-storey wooden house, gable roof, the boy's window upstairs"""
    with Layer(view=v) as (c, L):
        # body
        c.drawRect(skia.Rect.MakeLTRB(x, ground - 520, x + 760, ground), paint('#1E2A5E'))
        # siding lines
        for k in range(26):
            yy = ground - 520 + k * 20
            c.drawLine(x, yy, x + 760, yy, paint('#18224F', stroke=2))
        # first-floor eave
        c.drawPath(path([(x - 50, ground - 262), (x + 810, ground - 262), (x + 770, ground - 236), (x - 10, ground - 236)]),
                   paint('#0B1030'))
        # gable roof
        c.drawPath(path([(x - 70, ground - 512), (x + 380, ground - 760), (x + 830, ground - 512)]), paint('#0E1436'))
        for k in range(1, 12):
            u = k / 12
            c.drawLine(x - 70 + u * 450, ground - 512 - u * 248, x + 380 + u * 450, ground - 760 + u * 248,
                       paint('#141B3D', stroke=2))
        c.drawPath(path([(x - 70, ground - 512), (x + 380, ground - 760), (x + 830, ground - 512)], close=False),
                   paint('#2A3570', stroke=8))
        # air-con outdoor unit
        c.drawRect(skia.Rect.MakeXYWH(x + 600, ground - 150, 130, 100), paint('#3B4A8C'))
        c.drawCircle(x + 650, ground - 100, 34, paint('#1E2A5E'))
        # entrance (sliding door) + porch light
        c.drawRect(skia.Rect.MakeXYWH(x + 90, ground - 210, 180, 210), paint('#141B3D'))
        for k in range(1, 6):
            c.drawLine(x + 90 + k * 30, ground - 205, x + 90 + k * 30, ground - 5, paint('#1E2A5E', stroke=2))
        # downstairs window (dark)
        c.drawRect(skia.Rect.MakeXYWH(x + 370, ground - 200, 190, 120), paint('#0B1030'))
        # balcony rail
        c.drawRect(skia.Rect.MakeXYWH(x + 60, ground - 300, 640, 10), paint('#2A3570'))
        for k in range(17):
            c.drawLine(x + 70 + k * 38, ground - 300, x + 70 + k * 38, ground - 262, paint('#2A3570', stroke=3))
        # laundry pole with a hanging t-shirt
        c.drawLine(x + 80, ground - 470, x + 700, ground - 470, paint('#3B4A8C', stroke=4))
    f.layer(L)
    # the window upstairs: TV glow flickering
    wx0, wy0, wx1, wy1 = x + 300, ground - 470, x + 560, ground - 330
    win = core.mask(lambda c: c.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), P()), v)
    glow = tv_glow * (0.75 + 0.25 * flicker)
    f.over('#2BB3B1', win, alpha=0.85 * glow + 0.1)
    f.over('#7FE3DE', halftone(win * core.radial((wx0 + wx1) / 2, (wy0 + wy1) / 2, 160, 1.0, view=v), cell=5),
           alpha=0.8 * glow)
    with Mask(v) as (c, m):
        c.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), P(stroke=10))
        c.drawLine((wx0 + wx1) / 2, wy0, (wx0 + wx1) / 2, wy1, P(stroke=8))
    f.over('#0B1030', m.cov)
    # light spill on the wall and night air around the window
    g = core.radial((wx0 + wx1) / 2, (wy0 + wy1) / 2, 420, falloff=1.6, view=v)
    f.over('#2BB3B1', halftone(g * 0.45 * glow, cell=7, angle=45), alpha=0.5)
    # curtain silhouette + flicker shadow
    with Mask(v) as (c, m):
        c.drawPath(path([(wx0 + 6, wy0 + 6), (wx0 + 60, wy0 + 6), (wx0 + 40, wy1 - 6), (wx0 + 6, wy1 - 6)]), P())
    f.over('#1D7F8C', m.cov)
    if porch:
        px, py = x + 300, ground - 230
        f.over('#FFCB45', core.mask(lambda c: c.drawCircle(px, py, 9, P()), v))
        f.over('#FFCB45', halftone(core.radial(px, py, 120, 1.8, view=v) * 0.6, cell=5), alpha=0.6)


def block_wall(f, v, y_top=820, ground=930, x0=-200, x1=2200, gate=(980, 1120)):
    with Layer(view=v) as (c, L):
        c.drawRect(skia.Rect.MakeLTRB(x0, y_top, x1, ground), paint('#2A3570'))
        for r in range(int((ground - y_top) / 34) + 1):
            yy = y_top + r * 34
            c.drawLine(x0, yy, x1, yy, paint('#1E2A5E', stroke=2))
            off = 0 if r % 2 == 0 else 60
            for k in range(int((x1 - x0) / 120) + 2):
                xx = x0 + k * 120 + off
                c.drawLine(xx, yy, xx, yy + 34, paint('#1E2A5E', stroke=2))
        c.drawRect(skia.Rect.MakeLTRB(x0, y_top - 10, x1, y_top + 4), paint('#3B4A8C'))
        if gate:
            g0, g1 = gate
            c.drawRect(skia.Rect.MakeLTRB(g0, y_top - 20, g1, ground), paint('#0B1030'))
            for k in range(8):
                xx = g0 + 10 + k * (g1 - g0 - 20) / 7
                c.drawLine(xx, y_top - 10, xx, ground - 5, paint('#3B4A8C', stroke=4))
    f.layer(L)


def street_lamp(f, v, t, x=1560, ground=960, height=660, on=1.0, moths=True, cone=True, color='#F4F7E8'):
    with Layer(view=v) as (c, L):
        c.drawRect(skia.Rect.MakeLTRB(x - 14, ground - height - 300, x + 14, ground), paint('#06081A'))
        for (hh, arm) in ((height + 260, 170), (height + 190, 130)):
            c.drawRect(skia.Rect.MakeXYWH(x - arm / 2, ground - hh, arm, 12), paint('#06081A'))
        c.drawLine(x, ground - height - 20, x - 130, ground - height + 10, paint('#06081A', stroke=8))
        c.drawRoundRect(skia.Rect.MakeXYWH(x - 190, ground - height, 90, 28), 10, 10, paint('#06081A'))
        # sign plate on the pole
        c.drawRect(skia.Rect.MakeXYWH(x - 26, ground - 420, 52, 150), paint('#2F5DC4'))
        c.drawRect(skia.Rect.MakeXYWH(x - 22, ground - 416, 44, 142), paint('#DDEFF4', stroke=2))
    f.layer(L)
    lx, ly = x - 145, ground - height + 26
    if on > 0:
        f.over(color, core.mask(lambda c: c.drawRoundRect(skia.Rect.MakeXYWH(lx - 40, ly - 4, 80, 10), 5, 5, P()), v),
               alpha=on)
        if cone:
            with Mask(v) as (c, m):
                c.drawPath(path([(lx - 40, ly), (lx + 40, ly), (lx + 330, ground + 40), (lx - 330, ground + 40)]),
                           P(blur=30))
            g = m.cov * core.radial(lx, ly, height * 1.25, falloff=0.9, view=v)
            f.over(color, halftone(np.clip(g * 0.85 * on, 0, 1), cell=7, angle=45), alpha=0.55)
        f.add(color, core.radial(lx, ly, 120, 2.2, view=v), alpha=0.5 * on)
        if moths:
            rng = np.random.default_rng(3)
            with Mask(v) as (c, m):
                for i in range(9):
                    a = t * rng.uniform(2, 5) + i
                    rr = rng.uniform(20, 70)
                    mx = lx + math.cos(a) * rr * 1.4
                    my = ly + 30 + math.sin(a * 1.3) * rr * 0.7
                    flap = abs(math.sin(t * 30 + i)) * 4 + 2
                    c.drawOval(skia.Rect.MakeXYWH(mx - flap, my - 2, flap * 2, 4), P())
            f.over('#F4EAD6', m.cov, alpha=on)
    return (lx, ly)


def wires(f, v, pts_list, color='#06081A', width=2.2):
    with Mask(v) as (c, m):
        for (x0, y0, x1, y1, sag) in pts_list:
            pth = skia.Path()
            pth.moveTo(x0, y0)
            pth.quadTo((x0 + x1) / 2, (y0 + y1) / 2 + sag, x1, y1)
            c.drawPath(pth, P(stroke=width))
    f.over(color, m.cov)


def far_town(f, v, ground=800, seed=5, color='#0B1030', lit='#FFCB45'):
    rng = np.random.default_rng(seed)
    with Mask(v) as (c, m):
        x = -300
        pts = [(-300, ground + 10)]
        while x < 2300:
            w = rng.uniform(90, 220)
            h = rng.uniform(60, 170)
            pts += [(x, ground - h), (x + w * 0.5, ground - h - rng.uniform(0, 40)), (x + w, ground - h)]
            x += w
        pts += [(2300, ground + 10)]
        c.drawPath(path(pts), P())
    f.over(color, m.cov)
    with Mask(v) as (c, m):
        for i in range(30):
            c.drawRect(skia.Rect.MakeXYWH(rng.uniform(-200, 2200), ground - rng.uniform(30, 140), 9, 11), P())
    f.over(lit, m.cov, alpha=0.75)


def vending_machine(f, v, t, x=1180, ground=960, on=1.0, scale=1.0):
    s = scale
    w, h = 260 * s, 480 * s
    x0, y0 = x - w / 2, ground - h
    with Layer(view=v) as (c, L):
        c.drawRoundRect(skia.Rect.MakeXYWH(x0, y0, w, h), 10 * s, 10 * s, paint('#E8383D'))
        c.drawRect(skia.Rect.MakeXYWH(x0 + 14 * s, y0 + 20 * s, w - 28 * s, 230 * s), paint('#FFFDF6'))
        # rows of drinks
        cols = ['#2F5DC4', '#FFCB45', '#5FA746', '#E8383D', '#7FE3DE', '#FF9A74', '#141B3D']
        for r in range(3):
            for k in range(6):
                cx = x0 + 34 * s + k * 38 * s
                cy = y0 + 48 * s + r * 72 * s
                c.drawRoundRect(skia.Rect.MakeXYWH(cx - 12 * s, cy - 24 * s, 24 * s, 48 * s), 6 * s, 6 * s,
                                paint(cols[(r * 6 + k) % len(cols)]))
                c.drawRect(skia.Rect.MakeXYWH(cx - 12 * s, cy + 28 * s, 24 * s, 8 * s), paint('#141B3D'))
                c.drawCircle(cx, cy + 32 * s, 3 * s, paint('#FF6A55'))
        c.drawRect(skia.Rect.MakeXYWH(x0 + 14 * s, y0 + 270 * s, w - 28 * s, 60 * s), paint('#141B3D'))
        c.drawRect(skia.Rect.MakeXYWH(x0 + 40 * s, y0 + 380 * s, w - 80 * s, 56 * s), paint('#141B3D'))
        c.drawRect(skia.Rect.MakeXYWH(x0 + w - 70 * s, y0 + 290 * s, 34 * s, 22 * s), paint('#7FE3DE'))
    f.layer(L)
    # glow onto the ground
    if on > 0:
        g = core.radial(x, y0 + 140 * s, 520 * s, falloff=1.3, view=v)
        f.over('#FFFDF6', halftone(g * 0.6 * on, cell=7, angle=45), alpha=0.45)
        with Mask(v) as (c, m):
            c.drawPath(path([(x0, ground), (x0 + w, ground), (x0 + w + 260 * s, ground + 140 * s),
                             (x0 - 260 * s, ground + 140 * s)]), P(blur=20))
        f.over('#FFFDF6', halftone(m.cov * 0.55 * on, cell=6, angle=15), alpha=0.6)

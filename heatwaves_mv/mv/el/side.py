"""Side-on parallax landscapes (paddies, poles, sea, train)."""
import math

import numpy as np
import skia

from .. import core
from ..core import Mask, Layer, P, paint, path, smooth_path, halftone
from . import road as rd


def far_mountains(f, y, x_off, color='#9FB0E0', height=120, seed=1, cov=0.55, shade='#6FB6E8'):
    rng = np.random.default_rng(seed)
    xs = np.linspace(-400, 2400, 36)
    hs = height * (0.45 + 0.55 * np.abs(np.sin(xs / 380 + seed))) * (0.7 + 0.3 * rng.random(36))
    pts = [(-400 + 0, y + 4)] + [(x - (x_off % 2800) + 0, y - h) for x, h in zip(xs, hs)] + [(2400, y + 4)]
    pts2 = [(p[0] + 2800, p[1]) for p in pts]
    def draw(c):
        for pp in (pts, pts2):
            c.drawPath(smooth_path(pp, close=True, tension=0.35), P())
    m = core.mask(draw)
    f.over(color, m)
    f.mul(shade, halftone(m * cov, cell=6, angle=45))
    return m


def tree_line(f, y, x_off, color='#2B6E3E', seed=4, h=46, dark='#1E4F33'):
    rng = np.random.default_rng(seed)
    with Mask() as (c, m):
        period = 2400
        for k in range(70):
            x = (k * 37 + rng.uniform(0, 30) - x_off) % period - 200
            r = rng.uniform(0.5, 1.0) * h
            for rep in (0, period):
                c.drawCircle(x + rep, y - r * 0.6, r, P())
        c.drawRect(skia.Rect.MakeLTRB(-10, y - h * 0.4, 1940, y + 6), P())
        # a few farmhouse roofs
        for k in range(5):
            x = (k * 470 + 140 - x_off * 1.0) % period - 200
            c.drawPath(path([(x, y - 30), (x + 40, y - 62), (x + 120, y - 62), (x + 160, y - 30)]), P())
    f.over(color, m.cov)
    f.mul(dark, halftone(m.cov * core.vgrad(y - h * 2, y, 0.1, 0.8), cell=5, angle=45))


def paddies(f, y0, y1, x_off, tod='noon', t=0.0):
    """horizontal paddy strips; water strips reflect the sky"""
    pal = rd.TOD[tod]
    ys, xs = core.coords()
    band = ((ys >= y0) & (ys < y1)).astype(np.float32)
    v = np.clip((ys - y0) / (y1 - y0), 0, 1) ** 0.7
    f.image(core.ramp(v.astype(np.float32), pal['ground'], cell=7, angle=15), band)
    # strips (levees) as thin lines, spacing grows toward the camera
    with Mask() as (c, m):
        yy = y0
        k = 0
        while yy < y1:
            gap = 6 + (yy - y0) * 0.16
            c.drawLine(-10, yy, 1930, yy, P(stroke=max(1.0, gap * 0.12)))
            yy += gap
            k += 1
    f.over(pal['rows'], m.cov * band, alpha=0.45)
    # rice rows as short vertical ticks that stream past
    with Mask() as (c, m):
        rng = np.random.default_rng(3)
        for k in range(220):
            yy = y0 + (y1 - y0) * (rng.random() ** 0.6)
            sp = 0.3 + (yy - y0) / (y1 - y0) * 1.7
            x = (rng.uniform(0, 2200) - x_off * sp) % 2200 - 140
            hh = 3 + (yy - y0) * 0.05
            c.drawLine(x, yy, x + hh * 0.2, yy - hh, P(stroke=1.4))
    f.over(pal['rows'], m.cov, alpha=0.6)


def poles_side(f, x_off, y_ground=1000, spacing=760, height=900, color='#141B3D', wires=True, sag=40):
    with Mask() as (c, m):
        xs = []
        for k in range(-1, 5):
            x = k * spacing - (x_off % spacing)
            xs.append(x)
            c.drawPath(path([(x - 13, y_ground), (x + 13, y_ground), (x + 9, y_ground - height),
                             (x - 9, y_ground - height)]), P())
            for (hh, arm) in ((height - 40, 120), (height - 120, 90)):
                c.drawRect(skia.Rect.MakeXYWH(x - arm / 2, y_ground - hh - 6, arm, 12), P())
            c.drawRoundRect(skia.Rect.MakeXYWH(x + 12, y_ground - height + 240, 46, 80), 8, 8, P())
        if wires:
            for w in range(4):
                yy = y_ground - height + 34 + w * 26 + (40 if w == 3 else 0)
                for a, b in zip(xs[:-1], xs[1:]):
                    pth = skia.Path()
                    pth.moveTo(a, yy)
                    pth.quadTo((a + b) / 2, yy + sag * 2, b, yy)
                    c.drawPath(pth, P(stroke=2.6))
    f.over(color, m.cov)
    return m.cov


def sea(f, y0, y1, x_off, t, tod='noon'):
    ys, xs = core.coords()
    band = ((ys >= y0) & (ys < y1)).astype(np.float32)
    v = np.clip((ys - y0) / (y1 - y0), 0, 1)
    cols = {'noon': ['#A9D8EF', '#6FB6E8', '#3F86D6', '#2A5FBF', '#1E4FA8'],
            'sunset': ['#FFC489', '#F0686A', '#B8457A', '#7A2E6B', '#4A2360'],
            'dawn': ['#FFE0B8', '#F9C9B6', '#C9C6E6', '#8E98D8', '#5D66B0'],
            'dusk': ['#F0A090', '#C86A88', '#7A4A88', '#4A3570', '#2A2457']}[tod]
    f.image(core.ramp(v.astype(np.float32), cols, cell=6, angle=45), band)
    # sparkles: short horizontal dashes twinkling
    rng = np.random.default_rng(5)
    with Mask() as (c, m):
        for k in range(260):
            yy = y0 + (y1 - y0) * rng.random() ** 1.4
            sp = 0.2 + (yy - y0) / (y1 - y0)
            x = (rng.uniform(0, 2100) - x_off * sp * 0.3) % 2100 - 90
            a = max(0.0, math.sin(t * rng.uniform(2, 6) + k))
            ln = 4 + (yy - y0) * 0.06
            c.drawLine(x, yy, x + ln, yy, P(stroke=1.6, alpha=a))
    f.over('#FFFDF6', m.cov * band)

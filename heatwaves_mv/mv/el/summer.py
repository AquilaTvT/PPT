"""Summer props: sunflowers, the coastal railcar, seawall, bus stop, station."""
import math

import numpy as np
import skia

from .. import core
from ..core import Layer, Mask, P, paint, path, smooth_path, halftone


def sunflower(c, x, y, s, face=0.0, sway=0.0, stem_len=600, leaf=True, petal_col='#FFCB45', petal_dark='#E89A2A',
              disk='#6B3A2E', stem='#3B8740'):
    """draw one sunflower on a Layer canvas. face: -1..1 head yaw (foreshortens the disk)"""
    hx, hy = x + sway, y
    # stem
    pth = skia.Path()
    pth.moveTo(x, y + stem_len)
    pth.quadTo(x + sway * 0.2, y + stem_len * 0.5, hx, hy + 30 * s)
    c.drawPath(pth, paint(stem, stroke=14 * s, cap='round'))
    if leaf:
        for k, (ly, side) in enumerate(((0.35, 1), (0.6, -1), (0.82, 1))):
            yy = y + stem_len * ly
            xx = x + sway * (1 - ly) * 0.3
            lf = skia.Path()
            lf.moveTo(xx, yy)
            lf.cubicTo(xx + side * 60 * s, yy - 50 * s, xx + side * 130 * s, yy - 10 * s, xx + side * 150 * s, yy + 30 * s)
            lf.cubicTo(xx + side * 100 * s, yy + 40 * s, xx + side * 40 * s, yy + 30 * s, xx, yy)
            c.drawPath(lf, paint(stem))
            c.drawLine(xx, yy, xx + side * 120 * s, yy + 18 * s, paint('#2B6E3E', stroke=2 * s))
    sx = 0.55 + 0.45 * math.cos(face * 1.2)
    c.save()
    c.translate(hx, hy)
    c.scale(sx, 1.0)
    n = 22
    for layer, (r0, r1, col) in enumerate(((52, 110, petal_dark), (48, 100, petal_col))):
        for k in range(n):
            a = (k + 0.5 * layer) / n * 360
            c.save()
            c.rotate(a)
            pp = skia.Path()
            pp.moveTo(r0 * s * 0.8, 0)
            pp.quadTo((r0 + r1) * 0.5 * s, -12 * s, r1 * s, 0)
            pp.quadTo((r0 + r1) * 0.5 * s, 12 * s, r0 * s * 0.8, 0)
            c.drawPath(pp, paint(col))
            c.restore()
    c.drawCircle(0, 0, 54 * s, paint(disk))
    c.drawCircle(0, 0, 54 * s, paint('#3D2418', stroke=4 * s))
    c.restore()


def sunflower_field(f, t, horizon=700, seed=3, wind=1.0, view=None, n_far=34, n_mid=12, n_near=4):
    """low camera in a sunflower field: tiny heads at the horizon, giants in front"""
    rng = np.random.default_rng(seed)
    flowers = []
    def add(n, d0, d1):
        for _ in range(n):
            d = rng.uniform(d0, d1)               # 1 far .. 0 near
            s = 0.18 + 1.9 * (1 - d) ** 2.6
            x = rng.uniform(-150, 2070)
            y = horizon - 10 - (1 - d) ** 1.8 * 520 + rng.uniform(-14, 14) * (1 - d)
            face = rng.choice([-0.9, -0.5, 0.0, 0.4, 0.8])
            flowers.append((d, x, y, s, face, rng.uniform(0, 6.28)))
    add(n_far, 0.62, 1.0)
    add(n_mid, 0.3, 0.62)
    add(n_near, 0.0, 0.18)
    flowers.sort(key=lambda q: -q[0])
    with Layer(view=view) as (c, L):
        for (d, x, y, s, face, ph) in flowers:
            sw = (math.sin(t * 1.3 + ph + x * 0.002) * 16 + 10) * s * wind
            sunflower(c, x, y, s, face=face + math.sin(t * 0.6 + ph) * 0.08, sway=sw, stem_len=1400)
    f.layer(L)
    return L.alpha


def railcar(c, x, y, s=1.0, length=1500, t=0.0, livery=('#F4EAD6', '#2F5DC4', '#E8383D'), lit=False):
    """1-car diesel (キハ) seen from the side, x = rear end, y = rail level"""
    body_h = 300 * s
    top = y - 70 * s - body_h
    L_ = length * s
    cream, blue, red = livery
    # bogies
    for bx in (0.18, 0.82):
        cx = x + L_ * bx
        c.drawRect(skia.Rect.MakeXYWH(cx - 110 * s, y - 80 * s, 220 * s, 50 * s), paint('#141B3D'))
        for wx in (-62, 62):
            c.drawCircle(cx + wx * s, y - 30 * s, 30 * s, paint('#1E2A5E'))
            c.drawCircle(cx + wx * s, y - 30 * s, 10 * s, paint('#8E98D8'))
    # body
    body = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, top, L_, body_h), 26 * s, 26 * s)
    c.drawRRect(body, paint(cream))
    c.drawRect(skia.Rect.MakeXYWH(x, top + body_h * 0.62, L_, body_h * 0.12), paint(blue))
    c.drawRect(skia.Rect.MakeXYWH(x, top + body_h * 0.77, L_, body_h * 0.05), paint(red))
    c.drawRect(skia.Rect.MakeXYWH(x, top + body_h * 0.9, L_, body_h * 0.1), paint('#3B4A8C'))
    # roof equipment
    for k in range(3):
        c.drawRoundRect(skia.Rect.MakeXYWH(x + L_ * (0.2 + 0.25 * k), top - 34 * s, 180 * s, 36 * s), 10 * s, 10 * s,
                        paint('#B9C3EA'))
    # windows + doors
    wy = top + body_h * 0.16
    wh = body_h * 0.36
    for k in range(9):
        wx = x + L_ * 0.08 + k * L_ * 0.094
        if k in (1, 7):
            c.drawRect(skia.Rect.MakeXYWH(wx, top + body_h * 0.08, L_ * 0.06, body_h * 0.82), paint('#DDE3F4'))
            c.drawRect(skia.Rect.MakeXYWH(wx + L_ * 0.006, wy, L_ * 0.048, wh), paint('#6FB6E8' if not lit else '#FFCB45'))
            continue
        c.drawRoundRect(skia.Rect.MakeXYWH(wx, wy, L_ * 0.07, wh), 8 * s, 8 * s,
                        paint('#6FB6E8' if not lit else '#FFE7A3'))
        c.drawLine(wx + L_ * 0.012, wy + wh * 0.8, wx + L_ * 0.05, wy + wh * 0.15, paint('#DDEFF4', stroke=5 * s, alpha=0.7))
    # front windows at the right end
    c.drawRoundRect(skia.Rect.MakeXYWH(x + L_ - 70 * s, wy, 50 * s, wh), 8 * s, 8 * s, paint('#2F5DC4'))
    c.drawCircle(x + L_ - 30 * s, top + body_h * 0.82, 12 * s, paint('#FFFBEA'))
    c.drawRRect(body, paint('#141B3D', stroke=4 * s))


def railway(f, y, x_off=0.0, view=None, color='#3B2E6E'):
    with Mask(view) as (c, m):
        c.drawRect(skia.Rect.MakeLTRB(-2000, y - 6, 4000, y + 6), P())
        c.drawRect(skia.Rect.MakeLTRB(-2000, y + 14, 4000, y + 40), P(alpha=0.6))
        for k in range(-20, 60):
            sx = k * 60 - (x_off % 60)
            c.drawRect(skia.Rect.MakeXYWH(sx, y + 4, 30, 14), P())
    f.over(color, m.cov)


def seawall(f, y_top, y_bot, view=None, color='#B9C3EA', shade='#5D66B0'):
    with Mask(view) as (c, m):
        c.drawRect(skia.Rect.MakeLTRB(-2000, y_top, 4000, y_bot), P())
    f.over(color, m.cov)
    f.mul(shade, halftone(m.cov * core.vgrad(y_top, y_bot, 0.15, 0.6), cell=6, angle=45))
    with Mask(view) as (c, m2):
        c.drawLine(-2000, y_top + 3, 4000, y_top + 3, P(stroke=6))
    f.over('#FFFDF6', m2.cov)


def station_sign(c, x, y, s=1.0, name='かげろう', roman='KAGERŌ', prev='にげみず', nxt='しんきろう'):
    """駅名標 — fictional stations: 逃げ水 ← 陽炎 → 蜃気楼"""
    from .. import text as tx
    w, h = 620 * s, 200 * s
    c.drawRect(skia.Rect.MakeXYWH(x - 10 * s, y + h, 20 * s, 300 * s), paint('#141B3D'))
    c.drawRect(skia.Rect.MakeXYWH(x + w - 10 * s, y + h, 20 * s, 300 * s), paint('#141B3D'))
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), paint('#FFFDF6'))
    c.drawRect(skia.Rect.MakeXYWH(x, y + h * 0.62, w, h * 0.14), paint('#2F5DC4'))
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), paint('#141B3D', stroke=5 * s))
    f1 = tx.font('kaku', 74 * s)
    tw = f1.measureText(name)
    c.drawString(name, x + w / 2 - tw / 2, y + 92 * s, f1, paint('#141B3D'))
    f2 = tx.font('kaku_m', 24 * s)
    tw = f2.measureText(roman)
    c.drawString(roman, x + w / 2 - tw / 2, y + 120 * s, f2, paint('#141B3D'))
    f3 = tx.font('kaku_m', 26 * s)
    c.drawString(prev, x + 16 * s, y + h * 0.73, f3, paint('#FFFDF6'))
    tw = f3.measureText(nxt)
    c.drawString(nxt, x + w - 16 * s - tw, y + h * 0.73, f3, paint('#FFFDF6'))
    c.drawString('◀', x + 16 * s, y + h * 0.95, f3, paint('#141B3D'))
    c.drawString('▶', x + w - 40 * s, y + h * 0.95, f3, paint('#141B3D'))


def platform(c, y_edge, color='#B9C3EA', edge='#FFCB45', x0=-200, x1=2200, depth=260):
    c.drawRect(skia.Rect.MakeLTRB(x0, y_edge, x1, y_edge + depth), paint(color))
    c.drawRect(skia.Rect.MakeLTRB(x0, y_edge, x1, y_edge + 14), paint('#FFFDF6'))
    for k in range(int((x1 - x0) / 60)):
        c.drawRect(skia.Rect.MakeXYWH(x0 + k * 60 + 4, y_edge + 30, 52, 22), paint(edge))

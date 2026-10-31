"""The boy's room at midnight: tatami, window with moon & wind chime, electric
fan, CRT on a stand, mosquito coil, digital clock, the boy lying in TV light."""
import functools
import math

import numpy as np
import skia

from .. import core
from ..core import Layer, Mask, P, paint, path, smooth_path, halftone, View

TV_QUAD = [(1312, 476), (1628, 470), (1634, 708), (1306, 714)]   # screen corners (design space)
TV_CENTER = (1470, 592)
WINDOW = (170, 110, 790, 560)
CHIME = (650, 128)
FAN = (300, 640)
CLOCK = (1340, 968)


def _wall(f, v, tv_on):
    # wall: dark navy with a fine dot texture; TV light grades it
    ys, xs = core.coords()
    floor_y = v.pt(0, 650)[1]
    wall = (ys < floor_y).astype(np.float32)
    f.over('#141B3D', wall)
    f.over('#1E2A5E', halftone(wall * 0.45, cell=6, angle=45))
    # skirting board
    k = core.mask(lambda c: c.drawRect(skia.Rect.MakeLTRB(-2000, 628, 4000, 652), P()), v)
    f.over('#0B1030', k)
    if tv_on > 0:
        g = core.radial(TV_CENTER[0], TV_CENTER[1], 1100, falloff=1.7, view=v) * wall
        f.over('#2BB3B1', halftone(g * 0.75 * tv_on, cell=7, angle=45), alpha=0.55)


def _floor(f, v, tv_on, moon_amt=1.0):
    ys, xs = core.coords()
    floor_y = v.pt(0, 650)[1]
    fl = (ys >= floor_y).astype(np.float32)
    f.over('#1A2350', fl)
    # tatami mats in perspective: vanishing point high above the TV
    vp = (1060, -900)
    with Mask(v) as (c, m):
        for k in range(-14, 22):
            x0 = 960 + k * 150
            # line from floor front to vanishing point
            yb = 1500
            xb = vp[0] + (x0 - vp[0]) * (yb - vp[1]) / (650 - vp[1])
            c.drawLine(x0, 650, xb, yb, P(stroke=1.2, alpha=0.5))
        for yy in (650, 745, 880, 1060):
            c.drawLine(-2000, yy, 4000, yy, P(stroke=1.0, alpha=0.4))
    f.over('#2A3570', m.cov * fl)
    # heri (mat borders)
    with Mask(v) as (c, m):
        c.drawPath(path([(-400, 862), (2400, 862), (2400, 884), (-400, 884)]), P())
        c.drawPath(path([(980, 650), (1004, 650), (1130, 1300), (1090, 1300)]), P())
    f.over('#0E1436', m.cov * fl)
    # weave texture as linescreen
    f.over('#26306A', core.linescreen(fl * 0.5, period=5, angle=0) * fl, alpha=0.5)
    if tv_on > 0:
        # TV light pool on the floor (trapezoid fan toward camera)
        with Mask(v) as (c, m):
            c.drawPath(path([(1250, 760), (1700, 760), (2100, 1150), (520, 1150)]), P(blur=60))
        pool = m.cov * fl * core.radial(1470, 760, 900, falloff=1.2, view=v)
        f.over('#7FE3DE', halftone(np.clip(pool * 1.1 * tv_on, 0, 1), cell=7, angle=45), alpha=0.7)
    if moon_amt > 0:
        # moonlight parallelogram from the window with the frame cross
        with Mask(v) as (c, m):
            c.drawPath(path([(260, 690), (700, 690), (980, 1000), (420, 1000)]), P(blur=8))
        with Mask(v) as (c, m2):
            c.drawLine(480, 690, 700, 1000, P(stroke=14))
            c.drawLine(300, 820, 860, 820, P(stroke=12))
        mm = np.clip(m.cov - m2.cov, 0, 1) * fl
        f.over('#F4EAD6', halftone(mm * 0.42 * moon_amt, cell=6, angle=15), alpha=0.45)


def _window(f, v, t, moon=True, chime=True, curtain=True, gust=0.0):
    x0, y0, x1, y1 = WINDOW
    # night sky inside
    with Mask(v) as (c, m):
        c.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), P())
    win = m.cov
    ys, xs = core.coords()
    top = v.pt(0, y0)[1]
    bot = v.pt(0, y1)[1]
    field = np.clip(1 - (ys - top) / max(1, bot - top), 0, 1) ** 0.9
    sky = core.ramp(field.astype(np.float32), ['#2A3570', '#1E2A5E', '#141B3D', '#0B1030'], cell=6, angle=45)
    f.image(sky, win)
    # stars
    rng = np.random.default_rng(9)
    with Mask(v) as (c, m):
        for i in range(40):
            sx, sy = rng.uniform(x0, x1), rng.uniform(y0, y1 - 160)
            a = 0.5 + 0.5 * math.sin(t * 2 + i)
            c.drawCircle(sx, sy, rng.uniform(1.0, 2.2), P(alpha=a))
    f.over('#F4EAD6', m.cov * win)
    if moon:
        mx, my, mr = 560, 230, 58
        g = core.radial(mx, my, mr * 3, falloff=2.0, view=v) * win
        f.over('#F4EAD6', halftone(g * 0.45, cell=6, angle=45), alpha=0.7)
        mc = core.mask(lambda c: c.drawCircle(mx, my, mr, P()), v) * win
        f.over('#FFF6DA', mc)
        with Mask(v) as (c, m):
            for (ax, ay, ar) in ((-18, -10, 18), (14, 16, 14), (20, -20, 10), (-6, 24, 9)):
                c.drawCircle(mx + ax, my + ay, ar, P(blur=4))
        f.mul('#E2CFA6', halftone(m.cov * mc * 0.8, cell=4, angle=45))
    # town silhouette: roofs, a utility pole and wires
    with Mask(v) as (c, m):
        pts = [(x0, y1), (x0, 470), (250, 470), (290, 440), (360, 440), (400, 470), (470, 470), (470, 420),
               (540, 395), (610, 420), (610, 480), (700, 480), (730, 455), (x1, 455), (x1, y1)]
        c.drawPath(path(pts), P())
        c.drawRect(skia.Rect.MakeLTRB(330, 200, 342, 470), P())
        c.drawRect(skia.Rect.MakeLTRB(300, 228, 372, 236), P())
        c.drawRect(skia.Rect.MakeLTRB(308, 252, 364, 258), P())
        for k in range(3):
            pth = skia.Path()
            pth.moveTo(x0 - 10, 250 + k * 9)
            pth.quadTo(250, 262 + k * 9, 336, 232 + k * 10)
            pth.quadTo(560, 280 + k * 9, x1 + 10, 240 + k * 11)
            c.drawPath(pth, P(stroke=1.6))
    f.over('#06081A', m.cov * win)
    with Mask(v) as (c, m):
        for (wx, wy) in ((500, 430), (520, 430), (650, 492), (740, 470)):
            c.drawRect(skia.Rect.MakeXYWH(wx, wy, 10, 12), P())
    f.over('#FFCB45', m.cov * win, alpha=0.9)
    # window frame (aluminium sash) and mosquito screen half
    with Mask(v) as (c, m):
        c.drawRect(skia.Rect.MakeLTRB(x0 - 22, y0 - 22, x1 + 22, y1 + 22), P(stroke=26, join='miter'))
        c.drawRect(skia.Rect.MakeLTRB(470, y0, 486, y1), P())
        c.drawRect(skia.Rect.MakeLTRB(x0, 330, 470, 340), P())
    f.over('#0B1030', m.cov)
    with Mask(v) as (c, m):
        c.drawRect(skia.Rect.MakeLTRB(x0 - 12, y0 - 12, x1 + 12, y1 + 12), P(stroke=3))
    f.over('#3B4A8C', m.cov)
    # screen mesh on the right pane
    with Mask(v) as (c, m):
        c.drawRect(skia.Rect.MakeLTRB(486, y0, x1, y1), P())
    f.over('#0B1030', core.linescreen(m.cov * 0.25, period=4, angle=0) * m.cov, alpha=0.6)
    if curtain:
        sw = math.sin(t * 0.9) * 10 + gust * 30
        with Mask(v) as (c, m):
            pts = [(x0 - 60, y0 - 50), (x0 + 70, y0 - 50)]
            for k in range(11):
                yy = y0 - 50 + k * 66
                pts.append((x0 + 70 + sw * (k / 10) ** 1.5 + math.sin(k * 1.3 + t * 2) * 6, yy))
            pts += [(x0 - 60, y1 + 70)]
            c.drawPath(smooth_path(pts, close=True, tension=0.3), P())
        cur = m.cov
        f.over('#2A3570', cur)
        f.over('#3B4A8C', core.linescreen(cur, period=26, angle=88) * cur, alpha=0.5)
    if chime:
        _chime(f, v, t, gust)


def _chime(f, v, t, gust=0.0):
    cx, cy = CHIME
    ang = math.sin(t * 1.9) * 7 + math.sin(t * 3.7 + 1) * 3 + gust * 18
    strip = math.sin(t * 2.3 + 0.6) * 14 + gust * 30
    with Layer(view=v) as (c, L):
        c.save()
        c.translate(cx, cy)
        c.rotate(ang)
        c.drawLine(0, 0, 0, 52, paint('#B9C3EA', stroke=2))
        bell = skia.Path()
        bell.moveTo(-34, 110)
        bell.cubicTo(-36, 60, -20, 50, 0, 50)
        bell.cubicTo(20, 50, 36, 60, 34, 110)
        bell.close()
        c.drawPath(bell, paint('#7FE3DE', alpha=0.75))
        c.drawPath(bell, paint('#DDEFF4', stroke=2.5))
        # painted goldfish on the glass
        c.drawOval(skia.Rect.MakeXYWH(-14, 78, 16, 9), paint('#E8383D'))
        c.drawPath(path([(2, 82), (10, 76), (10, 90)]), paint('#E8383D'))
        c.drawLine(0, 110, 0, 150, paint('#DDEFF4', stroke=1.5))
        c.save()
        c.translate(0, 150)
        c.rotate(strip - ang)
        c.drawRect(skia.Rect.MakeXYWH(-13, 0, 26, 110), paint('#F4EAD6'))
        c.drawRect(skia.Rect.MakeXYWH(-13, 0, 26, 110), paint('#B9C3EA', stroke=1.5))
        c.drawLine(-6, 20, -6, 90, paint('#1E2A5E', stroke=2))
        c.restore()
        c.restore()
    f.layer(L)


def _fan(f, v, t, speed=1.0, on=True):
    x, y = FAN
    osc = math.sin(t * 0.55) * 0.75          # head yaw
    sx = 0.45 + 0.55 * abs(math.cos(osc))
    with Layer(view=v) as (c, L):
        # base + pole
        c.drawOval(skia.Rect.MakeXYWH(x - 95, y + 270, 190, 46), paint('#0B1030'))
        c.drawOval(skia.Rect.MakeXYWH(x - 90, y + 262, 180, 40), paint('#2A3570'))
        c.drawRect(skia.Rect.MakeXYWH(x - 9, y + 70, 18, 200), paint('#1E2A5E'))
        c.drawRect(skia.Rect.MakeXYWH(x - 3, y + 70, 5, 200), paint('#3B4A8C'))
        c.save()
        c.translate(x + math.sin(osc) * 30, y)
        c.scale(sx, 1.0)
        # motor housing behind
        c.drawCircle(math.sin(osc) * 60 / sx, 8, 46, paint('#1E2A5E'))
        # blades: translucent spinning disc + faint blade shapes
        c.drawCircle(0, 0, 118, paint('#2BB3B1', alpha=0.18))
        if on:
            ang = (t * 360 * 4.5 * speed) % 360
            for k in range(3):
                c.save()
                c.rotate(ang + k * 120)
                bl = skia.Path()
                bl.moveTo(0, 0)
                bl.cubicTo(30, -30, 100, -60, 104, -10)
                bl.cubicTo(100, 20, 40, 20, 0, 0)
                c.drawPath(bl, paint('#7FE3DE', alpha=0.35))
                c.restore()
        # guard
        c.drawCircle(0, 0, 122, paint('#DDEFF4', stroke=3, alpha=0.9))
        c.drawCircle(0, 0, 80, paint('#DDEFF4', stroke=1.5, alpha=0.5))
        for k in range(24):
            a = k * math.pi / 12
            c.drawLine(math.cos(a) * 20, math.sin(a) * 20, math.cos(a) * 122, math.sin(a) * 122,
                       paint('#DDEFF4', stroke=1.2, alpha=0.55))
        c.drawCircle(0, 0, 20, paint('#B9C3EA'))
        c.drawCircle(0, 0, 9, paint('#E8383D'))
        c.restore()
    f.layer(L)


def _tv(f, v, content=None, tv_on=1.0, t=0.0):
    with Layer(view=v) as (c, L):
        # stand
        c.drawRect(skia.Rect.MakeLTRB(1200, 772, 1760, 790), paint('#3B2E6E'))
        c.drawRect(skia.Rect.MakeLTRB(1214, 790, 1746, 900), paint('#22204F'))
        c.drawRect(skia.Rect.MakeLTRB(1236, 806, 1476, 884), paint('#141B3D'))
        c.drawRect(skia.Rect.MakeLTRB(1486, 806, 1724, 884), paint('#141B3D'))
        c.drawCircle(1456, 845, 5, paint('#FFCB45'))
        c.drawCircle(1506, 845, 5, paint('#FFCB45'))
        # body
        body = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(1262, 420, 1700, 772), 26, 26)
        c.drawRRect(body, paint('#1E2A5E'))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(1270, 428, 1692, 764), 22, 22),
                    paint('#2A3570', stroke=4))
        # bezel
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(1290, 452, 1652, 728), 30, 30), paint('#0B1030'))
        # control strip
        c.drawRect(skia.Rect.MakeLTRB(1300, 734, 1652, 756), paint('#141B3D'))
        for k in range(5):
            c.drawCircle(1580 + k * 14, 745, 4, paint('#3B4A8C'))
        c.drawCircle(1320, 745, 4, paint('#E8383D' if tv_on > 0 else '#FF6A55'))
        # antenna
        c.drawLine(1480, 420, 1400, 300, paint('#B9C3EA', stroke=3))
        c.drawLine(1480, 420, 1580, 310, paint('#B9C3EA', stroke=3))
        c.drawCircle(1480, 420, 14, paint('#1E2A5E'))
    f.layer(L)
    if content is not None and tv_on > 0:
        from . import tv
        quad = [v.pt(*p) for p in TV_QUAD]
        tv.place_screen(f, content * tv_on, quad)
    else:
        q = [v.pt(*p) for p in TV_QUAD]
        f.over('#0E1436', core.mask(lambda c: c.drawPath(path(q), P()), None))
    # glass reflection highlight
    with Mask(v) as (c, m):
        c.drawPath(path([(1330, 488), (1420, 484), (1360, 560), (1320, 600)]), P(alpha=0.25, blur=3))
    f.add('#DDEFF4', m.cov, alpha=0.35)


def _boy(f, v, t, tv_on=1.0, breathe=True):
    br = math.sin(t * 1.4) * 2.5 if breathe else 0.0
    sw1 = math.sin(t * 1.15) * 10          # lower legs swing (deg)
    sw2 = math.sin(t * 1.15 + 1.9) * 9
    with Mask(v) as (c, m):
        def limb(x0, y0, x1, y1, w):
            c.drawLine(x0, y0, x1, y1, P(stroke=w, cap='round'))
        # torso: chest propped up on elbows, back sloping down to the hips
        torso = [(1062, 806 - br), (1010, 818 - br), (930, 846 - br * 0.6), (860, 866), (800, 860), (760, 874),
                 (752, 902), (800, 914), (900, 912), (990, 906), (1040, 884), (1072, 846)]
        c.drawPath(smooth_path(torso, close=True, tension=0.5), P())
        # arms: shoulder -> elbow on the floor -> hands under the chin
        limb(1018, 834 - br, 1046, 902, 34)
        limb(1046, 902, 1104, 822, 26)
        limb(990, 842 - br, 1004, 906, 30)
        limb(1004, 906, 1088, 830, 22)
        c.drawOval(skia.Rect.MakeXYWH(1084, 806, 50, 30), P())
        # neck + head + hair
        limb(1066, 812 - br, 1094, 792, 26)
        c.drawCircle(1112, 768 - br * 0.3, 40, P())
        hair = [(1072, 760), (1078, 730), (1102, 716), (1132, 720), (1152, 744), (1156, 770), (1146, 748),
                (1128, 742), (1096, 748)]
        c.drawPath(smooth_path(hair, close=True, tension=0.5), P())
        # thighs along the floor
        limb(790, 892, 600, 904, 50)
        limb(800, 900, 610, 912, 44)
        # lower legs raised and crossed, swinging
        for (kx, ky, ang, w) in ((604, 900, -62 + sw1, 36), (614, 908, -76 + sw2, 34)):
            r = math.radians(ang)
            ex, ey = kx + math.cos(r) * 170, ky + math.sin(r) * 170
            limb(kx, ky, ex, ey, w)
            fr = math.radians(ang - 80)
            limb(ex, ey, ex + math.cos(fr) * 40, ey + math.sin(fr) * 40, 22)
    body = m.cov
    f.over('#06081A', body)
    # t-shirt / shorts separation (subtle)
    with Mask(v) as (c, m2):
        c.drawLine(805, 866, 820, 916, P(stroke=3))
        c.drawLine(1032, 860, 1050, 866, P(stroke=2.5))
    f.over('#1E2A5E', m2.cov * body, alpha=0.9)
    if tv_on > 0:
        import cv2
        M = np.float32([[1, 0, -8 * core.S * v.zoom], [0, 1, 7 * core.S * v.zoom]])
        sh = cv2.warpAffine(body, M, (core.W, core.H))
        rim = np.clip(body - sh, 0, 1)
        f.over('#7FE3DE', rim, alpha=0.95 * tv_on)
        # soft TV light on the face side
        g = core.radial(1150, 770, 70, falloff=1.5, view=v) * body
        f.over('#2BB3B1', halftone(g * 0.8 * tv_on, cell=5, angle=45), alpha=0.8)


def _calendar(f, v, t, flutter=0.0):
    from .. import text as tx
    x, y, w, h = 905, 170, 210, 270
    rot = math.sin(t * 1.3) * 1.2 + flutter
    with Layer(view=v) as (c, L):
        c.save()
        c.translate(x + w / 2, y)
        c.rotate(rot)
        c.translate(-(x + w / 2), -y)
        c.drawCircle(x + w / 2, y - 8, 5, paint('#B9C3EA'))
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), paint('#9FB4D8'))
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, 26), paint('#3B4A8C'))
        for r in range(5):
            for k in range(7):
                cx = x + 18 + k * 29
                cy = y + 118 + r * 30
                c.drawRect(skia.Rect.MakeXYWH(cx - 9, cy - 9, 18, 18), paint('#5D66B0', alpha=0.55))
        # days crossed out up to the 15th
        for d in range(15):
            r, k = divmod(d + 1, 7)
            cx = x + 18 + k * 29
            cy = y + 118 + r * 30
            c.drawLine(cx - 9, cy - 9, cx + 9, cy + 9, paint('#E8383D', stroke=2.2))
        c.restore()
    f.layer(L)
    # horizontal big "6" instead of vertical text
    gl2, _ = tx.layout_h('6', x + w * 0.5, y + 70, 64, 'old', align='center')
    fc, _ = tx.render_glyphs(gl2)
    if fc is not None and v.zoom == 1.0 and not rot:
        f.over('#141B3D', fc)
    else:
        with Mask(v) as (c, m):
            c.save()
            c.translate(x + w / 2, y)
            c.rotate(rot)
            c.translate(-(x + w / 2), -y)
            fnt = tx.font('old', 64)
            c.drawString('6', x + w * 0.5 - 18, y + 92, fnt, P())
            fnt2 = tx.font('mincho_sb', 15)
            c.drawString('JUNE', x + w * 0.5 + 22, y + 92, fnt2, P())
            c.restore()
        f.over('#141B3D', m.cov)


def _cord(f, v, t):
    sw = math.sin(t * 0.8) * 6
    with Mask(v) as (c, m):
        c.drawLine(760, -20, 760 + sw, 300, P(stroke=2.2))
        c.drawOval(skia.Rect.MakeXYWH(760 + sw - 7, 300, 14, 26), P())
    f.over('#3B4A8C', m.cov)


def _props(f, v, t, clock_text='23:59', clock_on=True):
    with Layer(view=v) as (c, L):
        # glass of barley tea with ice
        c.drawRect(skia.Rect.MakeLTRB(1176, 942, 1214, 1010), paint('#B9C3EA', alpha=0.35))
        c.drawRect(skia.Rect.MakeLTRB(1178, 962, 1212, 1008), paint('#C98F3E', alpha=0.75))
        c.drawRect(skia.Rect.MakeLTRB(1184, 964, 1198, 976), paint('#DDEFF4', alpha=0.8))
        c.drawRect(skia.Rect.MakeLTRB(1176, 942, 1214, 1010), paint('#DDEFF4', stroke=2, alpha=0.8))
        # mosquito coil on its stand
        c.drawOval(skia.Rect.MakeXYWH(560, 990, 110, 30), paint('#3B4A8C'))
        pth = skia.Path()
        for k in range(120):
            a = k * 0.18
            r = 6 + a * 3.2
            px, py = 615 + math.cos(a) * r, 995 + math.sin(a) * r * 0.28
            if k == 0:
                pth.moveTo(px, py)
            else:
                pth.lineTo(px, py)
        c.drawPath(pth, paint('#2BB3B1', stroke=4))
        c.drawCircle(615 + math.cos(21.4) * 74, 995 + math.sin(21.4) * 21, 4, paint('#FF6A55'))
    f.layer(L)
    # smoke curl (thin, wavy, fades)
    sx0, sy0 = 615 + math.cos(21.4) * 74, 995 + math.sin(21.4) * 21
    with Mask(v) as (c, m):
        pth = skia.Path()
        pth.moveTo(sx0, sy0)
        for k in range(1, 40):
            yy = sy0 - k * 9
            xx = sx0 + math.sin(k * 0.35 - t * 1.6) * (4 + k * 0.9) + k * 1.4
            pth.lineTo(xx, yy)
        c.drawPath(pth, P(stroke=2.4, alpha=0.6, blur=1.2))
    sm = m.cov * core.vgrad(v.pt(0, sy0 - 360)[1], v.pt(0, sy0)[1], 0.0, 1.0)
    f.over('#B9C3EA', sm, alpha=0.7)
    if clock_on:
        clock(f, v, clock_text, t)


def clock(f, v, txt, t, x=None, y=None, scale=1.0, color='#FF6A55', body=True):
    """small digital alarm clock with LED digits (dot-matrix)"""
    from .. import text as tx
    x = CLOCK[0] if x is None else x
    y = CLOCK[1] if y is None else y
    if body:
        with Layer(view=v) as (c, L):
            c.drawRoundRect(skia.Rect.MakeXYWH(x - 92 * scale, y - 34 * scale, 184 * scale, 76 * scale),
                            14 * scale, 14 * scale, paint('#0B1030'))
            c.drawRoundRect(skia.Rect.MakeXYWH(x - 80 * scale, y - 24 * scale, 160 * scale, 54 * scale),
                            8 * scale, 8 * scale, paint('#06081A'))
        f.layer(L)
    led(f, v, txt, x, y + 3 * scale, 40 * scale, color, t)


def led(f, v, txt, x, y, size, color='#FF6A55', t=0.0, glow=True, ghost=True):
    """seven-segment-ish dot matrix text using a 5x7 font grid"""
    cov = led_mask(txt, x, y, size, v)
    if ghost:
        cg = led_mask('88:88' if ':' in txt else '8' * len(txt), x, y, size, v)
        f.over(color, cg, alpha=0.08)
    if glow:
        f.add(color, core.blur(cov, 6 * size / 40), alpha=0.7)
    f.over(color, cov)
    return cov


_FONT5x7 = {
    '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
    '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
    '3': ['11111', '00010', '00100', '00010', '00001', '10001', '01110'],
    '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
    '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
    '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
    '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
    '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
    ':': ['00000', '00100', '00100', '00000', '00100', '00100', '00000'],
    ' ': ['00000'] * 7,
    'C': ['01110', '10001', '10000', '10000', '10000', '10001', '01110'],
    'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001'],
    'A': ['01110', '10001', '10001', '11111', '10001', '10001', '10001'],
    'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001'],
    'P': ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
    '-': ['00000', '00000', '00000', '11111', '00000', '00000', '00000'],
}


def led_mask(txt, x, y, size, v=None, gap=0.18, align='center'):
    cell = size / 7.0
    n = len(txt)
    wch = 5 * cell + 1.6 * cell
    total = n * wch - 1.6 * cell
    x0 = x - total / 2 if align == 'center' else x
    with Mask(v) as (c, m):
        for i, ch in enumerate(txt):
            g = _FONT5x7.get(ch, _FONT5x7[' '])
            for r, row in enumerate(g):
                for k, bit in enumerate(row):
                    if bit == '1':
                        cx = x0 + i * wch + k * cell + cell / 2
                        cy = y - size / 2 + r * cell + cell / 2
                        c.drawRoundRect(skia.Rect.MakeXYWH(cx - cell * (0.5 - gap / 2), cy - cell * (0.5 - gap / 2),
                                                           cell * (1 - gap), cell * (1 - gap)),
                                        cell * 0.2, cell * 0.2, P())
    return m.cov


def room(f, t, v=None, tv_content=None, tv_on=1.0, clock_text='23:59', fan=True, boy=True, moon=True,
         gust=0.0, props=True):
    v = v or View()
    f.a[:] = core._col('#0B1030')
    _wall(f, v, tv_on)
    _window(f, v, t, moon=moon, gust=gust)
    _calendar(f, v, t)
    _cord(f, v, t)
    _floor(f, v, tv_on, moon_amt=1.0 if moon else 0.0)
    if fan:
        _fan(f, v, t)
    _tv(f, v, tv_content, tv_on, t)
    if boy:
        _boy(f, v, t, tv_on)
    if props:
        _props(f, v, t, clock_text)
    return f

"""Summer festival: fireworks (halftone bursts), lantern rows, goldfish pool."""
import math

import numpy as np
import skia

from .. import core, text
from ..core import Layer, Mask, P, paint, path, smooth_path, halftone

FW_COLS = [('#FF5C9E', '#FFD1E3'), ('#FFCB45', '#FFF3C4'), ('#7FE3DE', '#E6FFFB'), ('#FF6A55', '#FFE0D6'),
           ('#B8E35A', '#F1FFD6'), ('#B9C3EA', '#FFFFFF')]


def burst(f, t, t0, x, y, R=260, n=72, col=0, kind='peony', seed=0, view=None, life=2.2, alpha=1.0, glow=True):
    """one firework shell bursting at (x, y) at time t0 (launch trail before)"""
    dt = t - t0
    if dt < -0.6 or dt > life:
        return
    c1, c2 = FW_COLS[col % len(FW_COLS)]
    rng = np.random.default_rng(seed)
    if dt < 0:
        # rising trail
        u = (dt + 0.6) / 0.6
        yy = y + (1 - core.ease_out(u, 2)) * 520
        with Mask(view) as (c, m):
            c.drawLine(x, yy, x + math.sin(u * 9) * 3, yy + 60, P(stroke=3, alpha=0.8))
            c.drawCircle(x, yy, 4, P())
        f.over(c2, m.cov, alpha=alpha)
        return
    k = 1 - math.exp(-dt * 3.2)
    fade = max(0.0, 1 - dt / life) ** 1.3
    grav = 70 * dt * dt
    with Mask(view) as (c, m):
        for i in range(n):
            a = i / n * 2 * math.pi + rng.uniform(-0.05, 0.05)
            sp = rng.uniform(0.85, 1.0)
            if kind == 'ring':
                sp = 1.0
            r = R * sp * k
            px, py = x + math.cos(a) * r, y + math.sin(a) * r + grav
            tr = (0.35 if kind != 'willow' else 0.9) * R * k * (1 - k * 0.6)
            qx, qy = x + math.cos(a) * max(0, r - tr), y + math.sin(a) * max(0, r - tr) + grav * 0.6
            tw = 1.0 if dt < life * 0.55 else (0.3 + 0.7 * (math.sin(dt * 40 + i * 2.3) > 0))
            c.drawLine(qx, qy, px, py, P(stroke=2.2 if kind != 'willow' else 1.6, alpha=0.45 * fade))
            c.drawCircle(px, py, 3.6 * (1 - k * 0.3), P(alpha=fade * tw))
            if kind == 'peony' and i % 2 == 0:
                r2 = r * 0.55
                c.drawCircle(x + math.cos(a + 0.1) * r2, y + math.sin(a + 0.1) * r2 + grav, 2.6, P(alpha=fade * tw))
    cov = m.cov
    if glow:
        g = core.blur(cov, 16)
        f.add(c1, halftone(np.clip(g * 3.0, 0, 1), cell=6, angle=45), alpha=0.55 * alpha)
    f.over(c1, np.clip(cov * 1.4, 0, 1), alpha=alpha)
    f.over(c2, np.clip(cov * 2 - 1, 0, 1), alpha=alpha)
    # flash at the moment of bursting lights up the sky
    if dt < 0.25:
        f.add(c1, core.radial(x, y, R * 2.2, 1.6, view=view), alpha=(1 - dt / 0.25) * 0.35 * alpha)


def schedule(t0, t1, beats_from, every=1.0, seed=3, area=(250, 120, 1670, 520), start_beat=0.0):
    """burst list (time, x, y, R, col, kind, seed) on a beat grid"""
    from ..timing import BEAT, BEAT0
    rng = np.random.default_rng(seed)
    out = []
    b = math.ceil((t0 - BEAT0) / BEAT) + start_beat
    tt = BEAT0 + b * BEAT
    kinds = ['peony', 'ring', 'peony', 'willow', 'chrys']
    i = 0
    while tt < t1:
        x0, y0, x1, y1 = area
        out.append((tt, rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(230, 420), int(rng.integers(0, 6)),
                    kinds[i % len(kinds)], int(rng.integers(0, 1 << 30))))
        tt += BEAT * every
        i += 1
    return out


def sky_fireworks(f, t, sched, view=None, alpha=1.0):
    for (tb, x, y, R, col, kind, sd) in sched:
        burst(f, t, tb, x, y, R=R, col=col, kind=kind, seed=sd, view=view, alpha=alpha)


def lantern(c, x, y, s, col='#FF6A55', mark='祭', lit=1.0):
    """paper lantern (chochin)"""
    w, h = 70 * s, 96 * s
    c.drawRect(skia.Rect.MakeXYWH(x - w * 0.36, y - h * 0.5 - 10 * s, w * 0.72, 12 * s), paint('#141B3D'))
    c.drawRect(skia.Rect.MakeXYWH(x - w * 0.36, y + h * 0.5 - 2 * s, w * 0.72, 12 * s), paint('#141B3D'))
    c.drawOval(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), paint(col))
    for k in range(1, 6):
        yy = y - h / 2 + k * h / 6
        ww = w * math.sqrt(max(0.0, 1 - ((yy - y) / (h / 2)) ** 2))
        c.drawLine(x - ww / 2, yy, x + ww / 2, yy, paint('#B23A3A', stroke=1.2 * s, alpha=0.5))
    c.drawOval(skia.Rect.MakeXYWH(x - w * 0.22, y - h * 0.3, w * 0.44, h * 0.6), paint('#FFF3C4', alpha=0.55 * lit))


def goldfish(c, x, y, s, ang, t, col='#FF6A55', fin='#FFB08A', ph=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(math.degrees(ang))
    c.scale(s, s)
    tail = math.sin(t * 9 + ph) * 0.45
    tp = skia.Path()
    tp.moveTo(-30, 0)
    tp.cubicTo(-60, -10 + tail * 20, -90, -40 + tail * 30, -96, -30 + tail * 34)
    tp.cubicTo(-80, -6 + tail * 20, -80, 6 + tail * 20, -96, 30 + tail * 34)
    tp.cubicTo(-90, 40 + tail * 30, -60, 10 + tail * 20, -30, 0)
    c.drawPath(tp, paint(fin, alpha=0.9))
    c.drawOval(skia.Rect.MakeXYWH(-40, -22, 80, 44), paint(col))
    c.drawCircle(26, -10, 4, paint('#141B3D'))
    c.drawCircle(26, 10, 4, paint('#141B3D'))
    c.restore()


def goldfish_pool(f, t, view=None, n=11, seed=4, poi=None):
    """top-down kingyo-sukui tank. poi = (x, y, depth 0..1, torn 0..1)"""
    ys, xs = core.coords()
    field = (0.5 + 0.5 * np.sin(xs / 140.0 + t * 0.6) * np.sin(ys / 170.0 - t * 0.4)).astype(np.float32)
    f.a[:] = core.ramp(field, ['#1E4FA8', '#2F5DC4', '#3F86D6', '#5FA0E0'], cell=9, angle=45)
    # lantern reflections
    with Mask(view) as (c, m):
        for k in range(6):
            c.drawCircle(220 + k * 300, 140 + math.sin(t + k) * 8, 46, P(blur=6))
    f.over('#FFCB45', halftone(m.cov * 0.8, cell=6), alpha=0.7)
    rng = np.random.default_rng(seed)
    with Layer(view=view) as (c, L):
        for i in range(n):
            cx, cy = rng.uniform(300, 1620), rng.uniform(250, 830)
            r = rng.uniform(120, 300)
            sp = rng.uniform(0.25, 0.6) * (1 if i % 2 else -1)
            a = t * sp + i
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.6
            heading = a + (math.pi / 2 if sp > 0 else -math.pi / 2)
            col = ['#FF6A55', '#E8383D', '#FFF3D6', '#FF9A4D'][i % 4]
            goldfish(c, x, y, rng.uniform(0.9, 1.5), math.atan2(math.sin(heading) * 0.6, math.cos(heading)), t,
                     col=col, ph=i)
    f.layer(L)
    # ripples
    with Mask(view) as (c, m):
        for k in range(5):
            rr = ((t * 60 + k * 90) % 450)
            c.drawCircle(960 + math.sin(k) * 300, 540 + math.cos(k * 1.7) * 200, rr, P(stroke=3, alpha=1 - rr / 450))
    f.over('#B9E0F5', m.cov, alpha=0.5)
    if poi is not None:
        px, py, depth, torn = poi
        with Layer(view=view) as (c, L):
            c.drawLine(px + 170, py + 170, px + 420, py + 420, paint('#E8383D', stroke=26))
            c.drawCircle(px, py, 170, paint('#E8383D', stroke=22))
            paper = skia.Path()
            paper.addCircle(px, py, 160)
            if torn > 0:
                hole = skia.Path()
                rng2 = np.random.default_rng(7)
                pts = []
                for k in range(18):
                    a = k / 18 * 2 * math.pi
                    rr = 150 * torn * rng2.uniform(0.55, 1.0)
                    pts.append((px + 20 + math.cos(a) * rr, py - 10 + math.sin(a) * rr))
                hole = path(pts)
                paper = skia.Op(paper, hole, skia.PathOp.kDifference_PathOp)
            c.drawPath(paper, paint('#FFFDF6', alpha=0.55 + 0.25 * (1 - depth)))
        f.layer(L)

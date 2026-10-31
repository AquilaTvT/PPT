"""Particles and overlays: drifting petals, light motes, fireflies, lens flare, dust."""
import math

import numpy as np
import skia

from .. import core
from ..core import Mask, Layer, P, paint, halftone


def petals(f, t, n=40, seed=1, colors=('#FFCB45', '#F7DC8A'), wind=(260, 40), size=(10, 22), area=(0, 0, 1920, 1080),
           spin=3.0, alpha=1.0, view=None):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = area
    W_, H_ = x1 - x0 + 400, y1 - y0 + 300
    with Layer(view=view) as (c, L):
        for i in range(n):
            px = rng.uniform(0, W_)
            py = rng.uniform(0, H_)
            sp = rng.uniform(0.6, 1.4)
            s = rng.uniform(*size)
            ph = rng.uniform(0, 6.28)
            col = colors[i % len(colors)]
            x = (px + wind[0] * sp * t + math.sin(t * 1.3 + ph) * 40) % W_ + x0 - 200
            y = (py + wind[1] * sp * t + math.sin(t * 2.1 + ph) * 30) % H_ + y0 - 150
            ang = (t * spin * 60 * sp + ph * 57) % 360
            flat = abs(math.cos(t * spin * sp + ph))
            c.save()
            c.translate(x, y)
            c.rotate(ang)
            c.scale(1.0, 0.25 + 0.75 * flat)
            c.drawOval(skia.Rect.MakeXYWH(-s, -s * 0.42, 2 * s, s * 0.84), paint(col, alpha=alpha))
            c.restore()
    f.layer(L)


def motes(f, t, n=60, seed=2, color='#FFFBEA', area=(0, 0, 1920, 1080), rise=12.0, r=(1.5, 4.0), alpha=0.8,
          twinkle=2.0, glow=True):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = area
    with Mask() as (c, m):
        for i in range(n):
            x = rng.uniform(x0, x1) + math.sin(t * 0.7 + i) * 20
            y = (rng.uniform(y0, y1) - rise * t * rng.uniform(0.5, 1.5)) % (y1 - y0) + y0
            a = 0.5 + 0.5 * math.sin(t * twinkle * rng.uniform(0.6, 1.4) + i * 1.7)
            c.drawCircle(x, y, rng.uniform(*r), P(alpha=a * alpha))
    if glow:
        f.add(color, core.blur(m.cov, 6), alpha=0.6)
    f.over(color, m.cov)


def fireflies(f, t, n=40, seed=5, area=(0, 300, 1920, 1080), color='#D9F27A', alpha=1.0):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = area
    with Mask() as (c, m):
        for i in range(n):
            bx, by = rng.uniform(x0, x1), rng.uniform(y0, y1)
            fx, fy = rng.uniform(0.2, 0.6), rng.uniform(0.2, 0.6)
            x = bx + math.sin(t * fx + i) * 80 + math.sin(t * fx * 2.3 + i * 2) * 30
            y = by + math.sin(t * fy + i * 1.3) * 50
            pulse = max(0.0, math.sin(t * rng.uniform(1.5, 3.0) + i * 2.1)) ** 2
            c.drawCircle(x, y, 3.2, P(alpha=pulse * alpha))
    g = core.blur(m.cov, 10)
    f.over(color, halftone(np.clip(g * 2.2, 0, 1), cell=5, angle=45), alpha=0.8)
    f.over('#FFFDF6', m.cov)


def flare(f, t, sx, sy, amount=1.0, color='#FFF3C4', axis=(960, 540), n=6):
    """hexagon ghosts along the line through the frame centre"""
    if amount <= 0:
        return
    ax, ay = axis
    with Mask() as (c, m):
        for k in range(n):
            u = -0.3 - k * 0.32
            x = ax + (sx - ax) * u
            y = ay + (sy - ay) * u
            r = 14 + (k % 3) * 18
            pth = skia.Path()
            for j in range(6):
                a = j * math.pi / 3 + 0.3
                px, py = x + math.cos(a) * r, y + math.sin(a) * r
                if j == 0:
                    pth.moveTo(px, py)
                else:
                    pth.lineTo(px, py)
            pth.close()
            c.drawPath(pth, P(alpha=0.35 + 0.15 * (k % 2)))
    f.over(color, halftone(m.cov * amount, cell=5, angle=30), alpha=0.8)


def speedlines(f, t, cx=960, cy=540, n=70, color='#FFFDF6', alpha=0.6, seed=4, inner=380, length=900):
    rng = np.random.default_rng(seed + int(t * 15))
    with Mask() as (c, m):
        for i in range(n):
            a = rng.uniform(0, 2 * math.pi)
            r0 = inner + rng.uniform(0, 300)
            r1 = r0 + rng.uniform(0.3, 1.0) * length
            c.drawLine(cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * r1, cy + math.sin(a) * r1,
                       P(stroke=rng.uniform(1.5, 4.5), alpha=rng.uniform(0.4, 1.0)))
    f.over(color, m.cov, alpha=alpha)


def straw_hat(f, x, y, s, rot=0.0, t=0.0, view=None, tilt=0.35):
    """procedural straw hat with red ribbon (for the flying-hat shots)"""
    with Layer(view=view) as (c, L):
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        # brim (ellipse, foreshortened by tilt)
        c.drawOval(skia.Rect.MakeXYWH(-160, -160 * tilt, 320, 320 * tilt), paint('#E9B65A'))
        c.drawOval(skia.Rect.MakeXYWH(-160, -160 * tilt, 320, 320 * tilt), paint('#B9843A', stroke=4))
        for k in range(1, 4):
            r = 160 - k * 24
            c.drawOval(skia.Rect.MakeXYWH(-r, -r * tilt, 2 * r, 2 * r * tilt), paint('#C9963F', stroke=2, alpha=0.6))
        # crown
        crown = skia.Path()
        crown.moveTo(-78, -6)
        crown.cubicTo(-80, -110, 80, -110, 78, -6)
        crown.close()
        c.drawPath(crown, paint('#F2C46B'))
        c.drawPath(crown, paint('#B9843A', stroke=3))
        # ribbon band + tails fluttering
        c.drawRect(skia.Rect.MakeLTRB(-79, -40, 79, -10), paint('#E8383D'))
        for sgn in (1, -1):
            tail = skia.Path()
            tail.moveTo(60 * sgn, -26)
            wv = math.sin(t * 9 + sgn) * 18
            tail.cubicTo(120 * sgn, -30 + wv, 170 * sgn, 10 - wv, 230 * sgn, -10 + wv)
            tail.lineTo(222 * sgn, 12 + wv)
            tail.cubicTo(160 * sgn, 34 - wv, 110 * sgn, 0 + wv, 56 * sgn, -6)
            tail.close()
            c.drawPath(tail, paint('#E8383D' if sgn > 0 else '#C42F3A'))
        c.restore()
    f.layer(L)


def disintegrate(f, rgb, alpha, k, t, cell=14.0, rise=520.0, seed=3, front='down', spread=60.0, bg=None):
    """Turn an image into its own halftone dots that peel away and float off.

    k 0..1: progress. Dots detach in a sweep (front) and rise with jitter; the
    still-attached part of the picture is drawn as a normal halftone of itself.
    """
    import cv2
    cs = cell * core.S
    gw, gh = int(core.W / cs) + 1, int(core.H / cs) + 1
    small = cv2.resize(rgb, (gw, gh), interpolation=cv2.INTER_AREA)
    sa = cv2.resize(alpha, (gw, gh), interpolation=cv2.INTER_AREA)
    lum = small[..., 0] * 0.299 + small[..., 1] * 0.587 + small[..., 2] * 0.114
    rng = np.random.default_rng(seed)
    jit = rng.random((gh, gw)).astype(np.float32)
    ys, xs = np.mgrid[0:gh, 0:gw].astype(np.float32)
    if front == 'down':
        order = ys / gh
    elif front == 'up':
        order = 1 - ys / gh
    else:
        order = np.sqrt((xs / gw - 0.5) ** 2 + (ys / gh - 0.5) ** 2) * 1.4
    start = order * 0.6 + jit * 0.35            # detach time in 0..~1
    local = np.clip((k * 1.15 - start) / 0.45, 0, 1)
    with Layer() as (c, L):
        for j in range(gh):
            for i in range(gw):
                a = sa[j, i]
                if a < 0.1:
                    continue
                q = local[j, i]
                if q >= 0.999:
                    continue
                r = (0.25 + 0.75 * np.sqrt(max(0.0, 1.05 - lum[j, i]))) * cell * 0.62
                x = (i + 0.5) * cell + math.sin(t * 2 + jit[j, i] * 9) * spread * q
                y = (j + 0.5) * cell - (q ** 1.6) * rise * (0.6 + jit[j, i])
                r *= (1 - q * 0.7)
                col = small[j, i]
                p = skia.Paint(AntiAlias=True)
                p.setColor4f(skia.Color4f(float(col[0]), float(col[1]), float(col[2]), float(a * (1 - q ** 2))))
                c.drawCircle(float(x), float(y), float(r), p)
    f.layer(L)

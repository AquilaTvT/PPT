"""カーブミラー (convex traffic mirror) with a fisheye reflection inside."""
import functools
import math

import cv2
import numpy as np
import skia

from .. import core
from ..core import Layer, Mask, P, paint, path, halftone


@functools.lru_cache(maxsize=6)
def _fisheye_maps(n, k):
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    nx = xs / n * 2 - 1
    ny = ys / n * 2 - 1
    r = np.sqrt(nx * nx + ny * ny)
    # convex mirror: strong compression toward the rim
    rr = np.tan(np.clip(r, 0, 0.999) * k) / math.tan(k)
    s = np.where(r > 1e-6, rr / np.maximum(r, 1e-6), 1.0)
    mx = ((-nx * s * 0.62 + 1) * 0.5).astype(np.float32)   # mirrored horizontally
    my = ((ny * s * 0.62 + 1) * 0.5).astype(np.float32)
    return mx, my


def fisheye(img, n=None, k=1.25):
    """img (any res) -> square n x n convex-mirror view"""
    h, w = img.shape[:2]
    n = n or int(min(h, w))
    mx, my = _fisheye_maps(n, k)
    # sample a central square-ish region of the source (wider than tall)
    sx = mx * w
    sy = (my - 0.5) * w + h / 2
    return cv2.remap(img.astype(np.float32), sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def curve_mirror(f, v, cx, cy, r, reflection, t, wobble=0.0, pole_color='#FF7A3D', hood=True,
                 sign=True, rim_w=None, glare=True):
    """draw the mirror (in design space through view v); reflection = square image"""
    rim_w = rim_w or r * 0.16
    with Layer(view=v) as (c, L):
        # pole
        c.drawRect(skia.Rect.MakeLTRB(cx - r * 0.09, cy + r * 0.9, cx + r * 0.09, cy + r * 9), paint(pole_color))
        c.drawRect(skia.Rect.MakeLTRB(cx - r * 0.09, cy + r * 0.9, cx - r * 0.03, cy + r * 9), paint('#C24A2A'))
        # bracket
        c.drawRect(skia.Rect.MakeLTRB(cx - r * 0.25, cy + r * 0.85, cx + r * 0.25, cy + r * 1.05), paint('#C24A2A'))
        if sign:
            sy0 = cy + r * 1.9
            c.drawRect(skia.Rect.MakeXYWH(cx - r * 0.55, sy0, r * 1.1, r * 0.55), paint('#FFFDF6'))
            c.drawRect(skia.Rect.MakeXYWH(cx - r * 0.55, sy0, r * 1.1, r * 0.55), paint('#141B3D', stroke=r * 0.03))
        # rim ring
        c.drawCircle(cx, cy, r + rim_w, paint(pole_color))
        c.drawCircle(cx, cy, r + rim_w * 0.35, paint('#C24A2A'))
        if hood:
            hp = skia.Path()
            hp.addArc(skia.Rect.MakeXYWH(cx - r - rim_w * 1.1, cy - r - rim_w * 1.1, 2 * (r + rim_w * 1.1),
                                         2 * (r + rim_w * 1.1)), 200, 140)
            c.drawPath(hp, paint('#141B3D', stroke=rim_w * 0.9, cap='butt'))
    f.layer(L)
    if sign:
        from .. import text as tx
        sy0 = cy + r * 1.9
        with Mask(v) as (c, m):
            fnt = tx.font('kaku', r * 0.26)
            w = fnt.measureText('安全確認')
            c.drawString('安全確認', cx - w / 2, sy0 + r * 0.37, fnt, P())
        f.over('#E8383D', m.cov)
    # reflection
    n = reflection.shape[0]
    sx, sy = v.pt(cx, cy)
    rr = v.d(r)
    dst_n = max(4, int(2 * rr * core.S))
    refl = cv2.resize(reflection, (dst_n, dst_n), interpolation=cv2.INTER_AREA if dst_n < n else cv2.INTER_LINEAR)
    if wobble > 0:
        yy, xx = np.mgrid[0:dst_n, 0:dst_n].astype(np.float32)
        dx = np.sin(yy / (dst_n / 18.0) - t * 6.0) * wobble * dst_n / 300
        refl = cv2.remap(refl, xx + dx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    canvas = np.zeros((core.H, core.W, 3), np.float32)
    x0 = int(round(sx * core.S - dst_n / 2))
    y0 = int(round(sy * core.S - dst_n / 2))
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(core.W, x0 + dst_n), min(core.H, y0 + dst_n)
    if xb > xa and yb > ya:
        canvas[ya:yb, xa:xb] = refl[ya - y0:yb - y0, xa - x0:xb - x0]
    disc = core.mask(lambda c: c.drawCircle(cx, cy, r, P()), v)
    f.image(canvas, disc)
    # convex glass shading + glare streak
    ring = core.radial(cx, cy, r, falloff=0.6, view=v)
    f.mul('#8E98D8', halftone(np.clip((1 - ring) * disc * 0.55, 0, 1), cell=5, angle=45))
    if glare:
        with Mask(v) as (c, m):
            pth = skia.Path()
            pth.addArc(skia.Rect.MakeXYWH(cx - r * 0.8, cy - r * 0.8, r * 1.6, r * 1.6), 200, 50)
            c.drawPath(pth, P(stroke=r * 0.07, alpha=0.8))
        f.over('#FFFDF6', m.cov * disc, alpha=0.7)
    return disc

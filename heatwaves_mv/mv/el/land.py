"""Country road in perspective: asphalt, paddies, utility poles & wires, mirage."""
import math

import numpy as np
import skia

from .. import core
from ..core import Mask, P, halftone, path


class Cam:
    """pinhole camera over a flat world. X right, Y up, Z forward (metres)."""

    def __init__(self, f=1100.0, x=0.0, h=1.6, z=0.0, horizon=560.0, cx=960.0, roll=0.0):
        self.f, self.x, self.h, self.z, self.horizon, self.cx, self.roll = f, x, h, z, horizon, cx, roll

    def proj(self, X, Y, Z):
        z = Z - self.z
        z = np.maximum(z, 0.05) if isinstance(z, np.ndarray) else max(z, 0.05)
        sx = self.cx + self.f * (X - self.x) / z
        sy = self.horizon - self.f * (Y - self.h) / z
        if self.roll:
            r = math.radians(self.roll)
            dx, dy = sx - 960, sy - 540
            sx = 960 + dx * math.cos(r) - dy * math.sin(r)
            sy = 540 + dx * math.sin(r) + dy * math.cos(r)
        return sx, sy

    def scale(self, Z):
        return self.f / max(Z - self.z, 0.05)


def pole_positions(cam, side=1, X=4.6, spacing=32.0, phase=0.0, n=40):
    z0 = math.floor((cam.z - phase) / spacing) * spacing + phase
    return [(side * X, z0 + k * spacing) for k in range(1, n + 1)]


def utility_poles(f, cam, sides=(1,), X=4.6, spacing=32.0, height=10.5, color='ink', wires=3, sag=0.9,
                  max_z=900.0, alpha=1.0, t=0.0, transformer=True):
    """電柱: tapered poles + crossarms + catenary wires converging to the vanishing point"""
    with Mask() as (c, m):
        for side in sides:
            poles = [(x, z) for x, z in pole_positions(cam, side, X, spacing) if z - cam.z < max_z and z - cam.z > 0.5]
            tops = []
            for (x, z) in poles:
                b = cam.proj(x, 0, z)
                tp = cam.proj(x, height, z)
                s = cam.scale(z)
                w = max(0.6, 0.32 * s)
                wt = max(0.5, 0.22 * s)
                c.drawPath(path([(b[0] - w / 2, b[1]), (b[0] + w / 2, b[1]), (tp[0] + wt / 2, tp[1]), (tp[0] - wt / 2, tp[1])]), P())
                # crossarm
                for hh, arm in ((height - 0.6, 1.5), (height - 1.6, 1.1)):
                    a1 = cam.proj(x - arm * side * 0.2 - arm / 2, hh, z)
                    a2 = cam.proj(x + arm / 2, hh, z)
                    c.drawLine(float(a1[0]), float(a1[1]), float(a2[0]), float(a2[1]), P(stroke=max(0.6, 0.12 * s), cap='butt'))
                if transformer and int(z / spacing) % 3 == 0:
                    tc = cam.proj(x + side * 0.35, height - 3.2, z)
                    c.drawRoundRect(skia.Rect.MakeXYWH(tc[0] - 0.28 * s, tc[1] - 0.6 * s, 0.56 * s, 1.1 * s), 0.1 * s, 0.1 * s, P())
                tops.append((x, z, s))
            # wires
            for wi in range(wires):
                off = (wi - (wires - 1) / 2) * 0.55
                hh = height - 0.6 - (0.0 if wi < 2 else 1.0)
                for (x1, z1, s1), (x2, z2, s2) in zip(tops[:-1], tops[1:]):
                    pth = skia.Path()
                    nseg = 10
                    for k in range(nseg + 1):
                        u = k / nseg
                        zz = z1 + (z2 - z1) * u
                        yy = hh - sag * 4 * u * (1 - u)
                        px, py = cam.proj(x1 + off, yy, zz)
                        if k == 0:
                            pth.moveTo(float(px), float(py))
                        else:
                            pth.lineTo(float(px), float(py))
                    c.drawPath(pth, P(stroke=max(0.5, 0.025 * s1), alpha=0.9))
                # wire to camera (nearest pole) — heading off-screen
                if tops:
                    x1, z1, s1 = tops[0]
                    a = cam.proj(x1 + off, hh, z1)
                    b = cam.proj(x1 + off, hh - 0.6, cam.z + 0.6)
                    c.drawLine(float(a[0]), float(a[1]), float(b[0]), float(b[1]), P(stroke=2.0))
    f.over(color, m.cov, alpha=alpha)
    return m.cov


def far_hills(f, horizon, color='sky', seed=4, height=60, alpha=1.0, cell=6, cov=0.6):
    rng = np.random.default_rng(seed)
    xs = np.linspace(-20, 1940, 40)
    ys = horizon - height * (0.4 + 0.6 * np.abs(np.sin(xs / 300 + seed))) * (0.6 + 0.4 * rng.random(40))
    pts = [(-20, horizon + 2)] + list(zip(xs, ys)) + [(1940, horizon + 2)]
    m = core.mask(lambda c: c.drawPath(core.smooth_path(pts, close=True, tension=0.4), P()))
    f.over('paper', m)
    f.mul(color, halftone(m * cov, cell=cell, angle=45), alpha=alpha)
    return m


def mirage(f, horizon, road_cov, t, depth=34.0, strength=1.0, src_rows=None):
    """逃げ水: the far road turns into a mirror of the sky just above the horizon."""
    hz = int(horizon * core.S)
    d = int(depth * core.S)
    if hz - d < 0 or hz + d >= core.H:
        return
    src = f.a[hz - d:hz][::-1].copy() if src_rows is None else src_rows
    # wobble the reflection
    ys, xs = np.mgrid[0:src.shape[0], 0:core.W].astype(np.float32)
    dx = np.sin(ys * 0.9 / core.S + t * 9) * 2.5 * core.S + np.sin(xs * 0.02 / core.S + t * 3) * 1.5 * core.S
    import cv2
    src = cv2.remap(src, xs + dx, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    band = np.zeros((core.H, core.W), np.float32)
    k = np.linspace(1, 0, d, dtype=np.float32) ** 0.8
    band[hz:hz + d] = k[:, None]
    # ragged shimmering lower edge
    _, xs2 = core._grid()
    edge = (np.sin(xs2[0] * 0.035 / core.S + t * 5) * 0.5 + 0.5) * 0.35
    band[hz:hz + d] *= np.clip(1 - edge[None, :] * np.linspace(0, 1, d)[:, None] * 2, 0, 1)
    m = band * road_cov * strength
    region = f.a[hz:hz + d]
    region += (src - region) * m[hz:hz + d][..., None]

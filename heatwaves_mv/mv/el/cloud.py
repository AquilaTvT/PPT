"""Anime-style cumulonimbus (入道雲).

The cloud is a union of spheres.  For every pixel we keep the front-most
sphere and its analytic normal, light it, then posterise the shading into a
handful of inks with halftone transitions.  Each puff therefore gets a crisp
terminator arc and nearer puffs occlude farther ones — the painted
cauliflower look — while the cloud base fades into a dotted shadow.
"""
import math

import numpy as np

from .. import core


def make_cloud(seed, x, base, width, height, towers=1, lean=0.0, puffiness=1.0):
    """list of puffs (cx, cy, r, zbias) — a cumulonimbus with flat base"""
    rng = np.random.default_rng(seed)
    puffs = []
    for tw in range(towers):
        if towers == 1:
            tx, th, tww = x, height, width
        else:
            off = (tw - (towers - 1) / 2) / max(1, towers - 1)
            tx = x + off * width * 0.55 + rng.uniform(-20, 20)
            th = height * (1.0 if tw == towers // 2 else rng.uniform(0.5, 0.78))
            tww = width * 0.6
        levels = 7
        for j in range(levels):
            v = j / (levels - 1)
            lw = tww * (0.92 - 0.5 * v ** 0.9)
            cy = base - th * (0.12 + 0.74 * v)
            k = max(2, int(round((5.5 - 3 * v) * puffiness)))
            for i in range(k):
                u = (i + 0.5) / k
                cx = tx - lw / 2 + lw * u + rng.uniform(-0.25, 0.25) * lw / k + lean * v * th
                r = th * (0.2 - 0.07 * v) * rng.uniform(0.75, 1.2) / max(1.0, puffiness ** 0.5)
                zb = (1 - v) * th * 0.25 + rng.uniform(-0.04, 0.04) * th
                puffs.append((cx, cy, r, zb))
        # crown
        puffs.append((tx + lean * th + rng.uniform(-10, 10), base - th * 0.9, th * 0.13, -0.05 * th))
        # small bumps on the silhouette for detail
        for _ in range(int(10 * puffiness)):
            a = rng.uniform(math.pi * 1.05, math.pi * 1.95)
            v = rng.uniform(0.15, 0.95)
            lw = tww * (0.92 - 0.5 * v ** 0.9)
            cx = tx + math.cos(a) * lw * 0.5 + lean * v * th
            cy = base - th * (0.12 + 0.74 * v) + math.sin(a) * th * 0.06
            puffs.append((cx, cy, th * rng.uniform(0.04, 0.075), (1 - v) * th * 0.25 + th * 0.06))
    # skirt along the base
    n = int(9 * max(1, width / 600))
    for i in range(n):
        u = (i + 0.5) / n
        cx = x - width * 0.55 + width * 1.1 * u + rng.uniform(-12, 12)
        r = height * rng.uniform(0.06, 0.1)
        puffs.append((cx, base - r * 0.6, r, height * 0.3))
    return puffs


def shade_cloud(puffs, light=(0.55, -0.6, 0.58), dx=0.0, dy=0.0, scale=1.0, origin=(960, 540), base=None):
    """returns (coverage, diffuse, height_rel) at output resolution"""
    Wd, Hd, S = core.W, core.H, core.S
    ox, oy = origin
    cov = np.zeros((Hd, Wd), np.float32)
    z = np.full((Hd, Wd), -1e9, np.float32)
    nx = np.zeros((Hd, Wd), np.float32)
    ny = np.zeros((Hd, Wd), np.float32)
    nz = np.ones((Hd, Wd), np.float32)
    for cx, cy, r, zb in puffs:
        X = ((cx - ox) * scale + ox + dx) * S
        Y = ((cy - oy) * scale + oy + dy) * S
        R = r * scale * S
        Z = zb * scale * S
        x0, x1 = int(max(0, X - R - 2)), int(min(Wd, X + R + 2))
        y0, y1 = int(max(0, Y - R - 2)), int(min(Hd, Y + R + 2))
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        ddx, ddy = xx - X, yy - Y
        d2 = ddx * ddx + ddy * ddy
        inside = R * R - d2
        c = np.clip(R - np.sqrt(d2) + 0.5, 0, 1)
        h = np.sqrt(np.maximum(inside, 0)) + Z
        sub_z = z[y0:y1, x0:x1]
        win = (inside > 0) & (h > sub_z)
        sub_z[win] = h[win]
        nx[y0:y1, x0:x1][win] = ddx[win] / R
        ny[y0:y1, x0:x1][win] = ddy[win] / R
        nz[y0:y1, x0:x1][win] = np.sqrt(np.maximum(inside[win], 0)) / R
        np.maximum(cov[y0:y1, x0:x1], c, out=cov[y0:y1, x0:x1])
    lx, ly, lz = light
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    dif = (nx * lx + ny * ly + nz * lz) / ln
    dif = np.clip(dif, -1, 1)
    if base is not None:
        b = ((base - oy) * scale + oy + dy)
        ys, _ = core.coords()
        cut = np.clip((b - ys) * S / 1.5 + 0.5, 0, 1)
        cov = cov * cut
    return cov, dif, z


def draw_cloud(f, puffs, light=(0.55, -0.6, 0.58), inks=('#7D86C9', '#AEB5E6', '#DCDDF5', '#FFFDF6', '#FFFDF6'),
               dx=0.0, dy=0.0, scale=1.0, origin=(960, 540), base=None, base_h=150, cell=6.0, angle=45,
               opacity=1.0, bias=0.0, base_ink='#7D86C9', rim=None, rim_amt=0.0):
    cov, dif, _ = shade_cloud(puffs, light, dx, dy, scale, origin, base)
    v = np.clip(dif * 0.62 + 0.42 + bias, 0, 1).astype(np.float32)
    if base is not None:
        b = (base - origin[1]) * scale + origin[1] + dy
        g = core.vgrad(b - base_h * scale, b, 0.0, 1.0, ease=1.2)
        v = v * (1 - 0.75 * g)
    rgb = core.ramp(v, list(inks), cell=cell, angle=angle)
    if rim is not None and rim_amt > 0:
        edge = cov * (1 - core.blur(cov, 3)) * 2.0
        rgb = rgb + (core._col(rim) - rgb) * np.clip(edge * rim_amt, 0, 1)[..., None]
    f.image(rgb, cov, opacity)
    return cov


def cloud_bank(f, horizon, seed=1, height=40, n=26, inks=('#9FB0E0', '#C9D3F0', '#EEF2FA'), light=(0.5, -0.7, 0.5),
               dy=0.0, opacity=1.0, cell=5.0):
    rng = np.random.default_rng(seed)
    puffs = []
    for i in range(n):
        cx = rng.uniform(-60, 1980)
        r = rng.uniform(0.35, 1.0) * height
        puffs.append((cx, horizon - r * 0.25, r, rng.uniform(0, 1) * height))
    cov, dif, _ = shade_cloud(puffs, light, dy=dy, base=horizon + dy)
    v = np.clip(dif * 0.6 + 0.45, 0, 1).astype(np.float32)
    rgb = core.ramp(v, list(inks), cell=cell, angle=45)
    f.image(rgb, cov, opacity)
    return cov

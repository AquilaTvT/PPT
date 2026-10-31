"""The long country road under cumulonimbus, in four lights."""
import math

import cv2
import numpy as np
import skia

from .. import core
from ..core import Mask, P, path, halftone
from . import cloud, land, sprite

TOD = {
    'noon': dict(sky=['#DDEFF4', '#A9D8EF', '#6FB6E8', '#3F86D6', '#2A5FBF'],
                 cloud=('#7D86C9', '#AEB5E6', '#DCDDF5', '#FFFDF6', '#FFFDF6'), cloud_base='#7D86C9',
                 bank=('#9FB0E0', '#C9D3F0', '#EEF2FA'),
                 ground=['#D9E8A8', '#A8D06A', '#6DB04C', '#43904A', '#2B6E3E'], rows='#2E6B3A',
                 road=['#8E95B8', '#6B739B', '#4A5282', '#363E6B'], line='#FFFDF6', dash='#FFCB45',
                 pole='#141B3D', hills='#6FB6E8', sun='#FFFBEA', glow='#FFF3C4', sun_pos=(1540, 120)),
    'sunset': dict(sky=['#FFE7B8', '#FFC489', '#FF9A74', '#F0686A', '#B8457A', '#5B3C8C'],
                   cloud=('#5B2E6B', '#B23A5E', '#F0686A', '#FFB37A', '#FFE2B0'), cloud_base='#5B2E6B',
                   bank=('#8A3A6E', '#D9606E', '#FFB08A'),
                   ground=['#C26A7A', '#8E4A78', '#62366E', '#41275C', '#2B1D47'], rows='#22204F',
                   road=['#B87A92', '#8A5A85', '#5E3F72', '#3D2B5C'], line='#FFD6A0', dash='#FFCB45',
                   pole='#1A1438', hills='#8A4A88', sun='#FFF1D6', glow='#FFB37A', sun_pos=(1180, 470)),
    'dawn': dict(sky=['#FFF6E2', '#FFE0B8', '#F9C9B6', '#C9C6E6', '#8E98D8', '#5D66B0'],
                 cloud=('#7A7FC0', '#C3B3D9', '#F6C9B0', '#FFE7CF', '#FFF8EE'), cloud_base='#7A7FC0',
                 bank=('#B8A9D6', '#F2C9C0', '#FFEADB'),
                 ground=['#E8D9B0', '#B8C98A', '#7FA86A', '#55805A', '#37604A'], rows='#37604A',
                 road=['#B8B2C9', '#8E8AAE', '#676A93', '#474D78'], line='#FFF8EE', dash='#FFCB45',
                 pole='#22204F', hills='#B8A9D6', sun='#FFFBEA', glow='#FFE0B8', sun_pos=(700, 500)),
    'night': dict(sky=['#2A3570', '#1E2A5E', '#141B3D', '#0B1030', '#06081A'],
                  cloud=('#0B1030', '#141B3D', '#1E2A5E', '#2A3570', '#3B4A8C'), cloud_base='#0B1030',
                  bank=('#0B1030', '#141B3D', '#1E2A5E'),
                  ground=['#1E2A5E', '#18224F', '#141B3D', '#0E1436', '#0B1030'], rows='#06081A',
                  road=['#3B4A8C', '#2A3570', '#1E2A5E', '#141B3D'], line='#8E98D8', dash='#B38A3E',
                  pole='#06081A', hills='#141B3D', sun=None, glow=None, sun_pos=(0, 0)),
}

_cache = {}


def memo(key, fn):
    k = (key, core.W, core.H)
    if k not in _cache:
        if len(_cache) > 40:
            _cache.clear()
        _cache[k] = fn()
    return _cache[k]


def sky(f, tod, horizon):
    pal = TOD[tod]
    ys, xs = core.coords()
    field = np.clip(1 - (ys / max(horizon, 1)) ** 1.15, 0, 1).astype(np.float32)
    f.a[:] = core.ramp(field, pal['sky'], cell=8, angle=45)


def sun(f, tod, x=None, y=None, r=50, glow_r=420, amt=1.0):
    pal = TOD[tod]
    if pal['sun'] is None:
        return
    sx, sy = pal['sun_pos']
    x = sx if x is None else x
    y = sy if y is None else y
    g = core.radial(x, y, glow_r, falloff=1.4)
    f.over(pal['glow'], halftone(g * amt, cell=9, angle=30), alpha=0.9)
    f.over(pal['sun'], core.mask(lambda c: c.drawCircle(x, y, r, P())), alpha=amt)


def clouds_layer(tod, horizon, seed=11, specs=None, light=None):
    """cached cloud layer (rgb, alpha) for a given time of day / horizon"""
    pal = TOD[tod]
    if specs is None:
        specs = [(seed, 600, 900, 560, 3), (seed - 6, 1500, 480, 300, 1)]
    if light is None:
        light = (0.55, -0.6, 0.58) if tod != 'sunset' else (0.2, -0.3, 0.9)

    def build():
        fl = core.Frame('paper')
        fl.a[:] = 0
        alpha = np.zeros((core.H, core.W), np.float32)
        for (sd, x, w, h, towers) in specs:
            pf = cloud.make_cloud(sd, x, horizon - 4, w, h, towers=towers)
            cov = cloud.draw_cloud(fl, pf, light=light, inks=pal['cloud'], base=horizon - 4,
                                   base_h=h * 0.3, base_ink=pal['cloud_base'])
            alpha = np.maximum(alpha, cov)
        bk = cloud.cloud_bank(fl, horizon, seed=3, height=24, n=40, inks=pal['bank'])
        alpha = np.maximum(alpha, bk)
        rgb = fl.a / np.maximum(alpha[..., None], 1e-4)
        return np.clip(rgb, 0, 1), alpha
    return memo(('clouds', tod, horizon, seed, str(specs)), build)


def put_layer(f, layer, dx=0.0, dy=0.0, scale=1.0, opacity=1.0, cx=960, cy=540):
    rgb, a = layer
    if dx or dy or scale != 1.0:
        M = cv2.getRotationMatrix2D((cx * core.S, cy * core.S), 0, scale)
        M[0, 2] += dx * core.S
        M[1, 2] += dy * core.S
        rgb = cv2.warpAffine(rgb, M, (core.W, core.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        a = cv2.warpAffine(a, M, (core.W, core.H), flags=cv2.INTER_LINEAR)
    f.image(rgb, a, opacity)


def ground(f, tod, cam, rows=True):
    pal = TOD[tod]
    hz = cam.horizon
    ys, xs = core.coords()
    gm = np.clip((ys - hz) * core.S + 0.5, 0, 1).astype(np.float32)
    gf = (np.clip((ys - hz) / max(1, 1080 - hz), 0, 1) ** 0.55).astype(np.float32)
    f.image(core.ramp(gf, pal['ground'], cell=7, angle=15), gm)
    if rows:
        with Mask() as (c, m):
            for k in range(-70, 71):
                if abs(k) < 2:
                    continue
                X = k * 2.4 + cam.x * 0
                x0, y0 = cam.proj(X, 0, cam.z + 1.0)
                x1, y1 = cam.proj(X, 0, cam.z + 1600)
                c.drawLine(float(x0), float(y0), float(x1), float(y1), P(stroke=1.1))
            # levees (あぜ道) across the fields
            for zz in range(0, 400, 40):
                z = math.floor(cam.z / 40) * 40 + zz + 40
                a = cam.proj(-80, 0, z)
                b = cam.proj(80, 0, z)
                w = max(0.6, cam.scale(z) * 0.25)
                c.drawLine(float(a[0]), float(a[1]), float(b[0]), float(b[1]), P(stroke=w, cap='butt'))
        f.over(pal['rows'], m.cov * gm, alpha=0.35)
    return gm


def road_surface(f, tod, cam, half_w=3.2, far=1600.0, glare=0.0, t=0.0):
    pal = TOD[tod]
    near = cam.z + 0.6
    pts = [cam.proj(-half_w, 0, near), cam.proj(half_w, 0, near), cam.proj(half_w, 0, far),
           cam.proj(-half_w, 0, far)]
    rc = core.mask(lambda c: c.drawPath(path(pts), P()))
    ys, xs = core.coords()
    hz = cam.horizon
    rf = (np.clip((ys - hz) / max(1, 1080 - hz), 0, 1) ** 0.6).astype(np.float32)
    f.image(core.ramp(rf, pal['road'], cell=6, angle=45), rc)
    # edge lines
    with Mask() as (c, m):
        for s in (-1, 1):
            X = s * (half_w - 0.18)
            a1, a2 = cam.proj(X - 0.08, 0, near), cam.proj(X + 0.08, 0, near)
            b1, b2 = cam.proj(X + 0.08, 0, far), cam.proj(X - 0.08, 0, far)
            c.drawPath(path([a1, a2, b1, b2]), P())
    f.over(pal['line'], m.cov * rc)
    # centre dashes
    with Mask() as (c, m):
        period, dl = 10.0, 5.0
        z0 = math.floor(cam.z / period) * period
        for k in range(0, 170):
            za, zb = z0 + k * period, z0 + k * period + dl
            if zb < near:
                continue
            za = max(za, near)
            if za > far:
                break
            q = [cam.proj(-0.07, 0, za), cam.proj(0.07, 0, za), cam.proj(0.07, 0, zb), cam.proj(-0.07, 0, zb)]
            c.drawPath(path(q), P())
    f.over(pal['dash'], m.cov * rc)
    if glare > 0:
        # 光りだすロード: a hot specular sheen racing along the far road
        sx = cam.proj(0, 0, cam.z + 200)[0]
        g = core.radial(sx, hz + 18, 520, falloff=1.2, sx=2.4, sy=0.35) * rc
        f.over('#FFFBEA', halftone(np.clip(g * glare * 1.4, 0, 1), cell=6, angle=15))
    return rc


def kimi_far(f, cam, Z, X=0.6, t=0.0, name='kimi_back', h_m=1.62, haze=4.0, reflect=0.55, flip=False,
             mul=None, mul_amt=0.0, opacity=1.0, wind=3.0):
    """君 standing on the road at distance Z, with her mirage reflection beneath"""
    fx, fy = cam.proj(X, 0, Z)
    hpx = cam.f * h_m / max(0.5, Z - cam.z) * 1.03
    if hpx < 6:
        return
    L = sprite.warp(name, fx, fy, hpx, anchor=(0.5, 0.97), flip=flip, wind=wind, t=t)
    L = sprite.shade_print(L, cell=max(3.0, min(6.0, hpx / 60)), shade_k=0.5, light_k=0.25)
    if mul is not None:
        L = sprite.grade(L, mul=mul, mul_amt=mul_amt)
    rgb, a = L['rgb'], L['a'] * opacity
    if haze:
        ys, _ = core._grid()
        rgb = core.heat_haze(rgb, t, amp=haze * min(1.0, hpx / 200 + 0.3), wavelength=14)
        a = core.heat_haze(a, t, amp=haze * min(1.0, hpx / 200 + 0.3), wavelength=14)
    if reflect > 0:
        # mirror below the feet line, wobbling, fading with depth
        yline = fy * core.S
        ys, xs = core._grid()
        my = (2 * yline - ys).astype(np.float32)
        mx = (xs + np.sin(ys / (5 * core.S) + t * 11) * 2.2 * core.S).astype(np.float32)
        rr = cv2.remap(rgb, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        ra = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        fade = np.clip(1 - (ys - yline) / (hpx * core.S * 0.6), 0, 1) * (ys > yline)
        f.image(rr, ra * fade * reflect)
    f.image(rgb, a)


def world(f, t, cam, tod='noon', clouds=True, cloud_dx=0.0, cloud_dy=0.0, cloud_scale=1.0, sun_amt=1.0,
          poles=(1,), mirage=1.0, mirage_depth=34, haze=4.5, glare=0.0, hills=True, figure=None,
          seed=11, specs=None, rows=True, pole_X=4.6, guard=False, haze_region=None):
    hz = cam.horizon
    sky(f, tod, hz)
    if sun_amt > 0:
        sun(f, tod, amt=sun_amt)
    if clouds:
        layer = clouds_layer(tod, int(hz), seed=seed, specs=specs)
        put_layer(f, layer, dx=cloud_dx, dy=cloud_dy, scale=cloud_scale, cy=hz)
    if hills:
        land.far_hills(f, hz, color=TOD[tod]['hills'], seed=2, height=26, cov=0.5)
    ground(f, tod, cam, rows=rows)
    rc = road_surface(f, tod, cam, glare=glare, t=t)
    if poles:
        land.utility_poles(f, cam, sides=poles, X=pole_X, color=TOD[tod]['pole'])
    if mirage > 0:
        land.mirage(f, hz, rc, t, depth=mirage_depth, strength=mirage)
    if figure is not None:
        figure(f)
    if haze > 0:
        ys, xs = core.coords()
        if haze_region is None:
            reg = np.exp(-((ys - hz - 10) / 80.0) ** 2)
        else:
            reg = haze_region
        f.a = core.heat_haze(f.a, t, amp=haze, wavelength=26, region=reg.astype(np.float32))
    return rc

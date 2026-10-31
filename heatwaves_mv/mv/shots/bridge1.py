"""Bridge 1 — goodbye — 88.10 – 111.80 s"""
import math
import os

import cv2
import numpy as np
import skia

from .. import core, lyrics
from ..core import Frame, View, Mask, Layer, P, paint, path, clamp, smooth, ease_io, ease_out, ease_in, lin, halftone
from ..edit import Shot, Tr
from ..el import sprite, fx, people, side, summer, night
from ..timing import bar, BEAT, beat_pulse
from .common import lerp


def has(name):
    return os.path.exists(os.path.join(sprite.ASSET_DIR, name + '.png'))


def pick(*names):
    for n in names:
        if has(n):
            return n
    return names[-1]


def s30_underwater(t, sh):
    u = lin(t, bar(29), bar(30))
    f = Frame('#1E2A5E')
    ys, xs = core.coords()
    field = np.clip(1 - ys / 1080, 0, 1).astype(np.float32)
    f.a[:] = core.ramp(field, ['#0B1030', '#141B3D', '#1E4FA8', '#2F5DC4', '#6FB6E8'], cell=8, angle=45)
    # caustics: wobbling light net near the surface
    n1 = np.sin(xs / 37.0 + np.sin(ys / 23.0 + t * 1.7) * 2 + t * 1.3)
    n2 = np.sin(ys / 29.0 + np.sin(xs / 31.0 - t * 1.1) * 2 - t * 0.9)
    caust = np.clip((np.abs(n1 + n2) < 0.35).astype(np.float32) * np.clip(1 - ys / 700, 0, 1), 0, 1)
    f.over('#B9E0F5', core.blur(caust, 1.2), alpha=0.55)
    # light shafts from the surface
    with Mask() as (c, m):
        for k in range(6):
            x = 300 + k * 280 + math.sin(t * 0.5 + k) * 40
            c.drawPath(path([(x - 30, -20), (x + 30, -20), (x + 220, 1100), (x + 60, 1100)]), P(alpha=0.5, blur=20))
    f.over('#B9E0F5', halftone(m.cov * core.vgrad(0, 1080, 0.6, 0.0), cell=7, angle=60), alpha=0.5)
    # the boy sinking, one hand up toward the light
    y = lerp(520, 700, ease_out(u, 2))
    with Mask() as (c, m):
        c.save()
        c.translate(960, y)
        c.rotate(170 + math.sin(t * 0.8) * 6)
        people.boy_back(c, 0, 380, 560)
        c.restore()
    body = core.heat_haze(m.cov, t, amp=4, wavelength=40, speed=0.8)
    f.over('#06081A', body)
    # bubbles rising
    rng = np.random.default_rng(3)
    with Mask() as (c, m):
        for i in range(40):
            bx = 960 + rng.normal(0, 160) + math.sin(t * 2 + i) * 14
            by = (rng.uniform(0, 1080) - t * rng.uniform(90, 220)) % 1180 - 50
            r = rng.uniform(3, 12)
            c.drawCircle(bx, by, r, P(stroke=2.0))
            c.drawCircle(bx - r * 0.3, by - r * 0.3, r * 0.25, P())
    f.over('#DDEFF4', m.cov, alpha=0.8)
    f.a = core.heat_haze(f.a, t, amp=5, wavelength=60, speed=0.7)
    lyrics.draw_v(f, t, 30, x=1770, y=110, size=82, fill='#DDEFF4', edge='#0B1030', zh_color='#7FE3DE', haze=3.0)
    return f.a


def _dusk_sky(f, hz, cols=('#FFE7B8', '#FFC489', '#FF9A74', '#E85A7A', '#7A2E6B', '#3B2E6E')):
    ys, xs = core.coords()
    field = np.clip(1 - (ys / hz) ** 1.1, 0, 1).astype(np.float32)
    f.a[:] = core.ramp(field, list(cols), cell=8, angle=45)


def s31_seawall(t, sh):
    u = lin(t, bar(30), bar(31))
    f = Frame('paper')
    hz = 600
    _dusk_sky(f, hz)
    sx, sy = 1260, hz + 10 - u * 14
    g = core.radial(sx, sy, 600, falloff=1.3)
    f.over('#FFE7B8', halftone(g, cell=9, angle=30), alpha=0.8)
    f.over('#FFF1D6', core.mask(lambda c: c.drawCircle(sx, sy, 90, P())))
    side.sea(f, hz, 860, u * 60, t, tod='dusk')
    # sun path glitter on the sea
    with Mask() as (c, m):
        rng = np.random.default_rng(2)
        for k in range(90):
            yy = hz + 6 + (860 - hz) * rng.random() ** 1.6
            ww = 20 + (yy - hz) * 0.5
            a = max(0.0, math.sin(t * rng.uniform(2, 5) + k))
            c.drawLine(sx - ww * rng.random(), yy, sx + ww * rng.random(), yy, P(stroke=2.5, alpha=a))
    f.over('#FFE7B8', m.cov)
    summer.seawall(f, 860, 1080, color='#3B2E6E', shade='#22204F')
    with Mask() as (c, m):
        people.sitting_pair(c, 760, 868, 330, t=t)
    f.over('#22204F', m.cov)
    # gulls
    with Mask() as (c, m):
        for k in range(4):
            bx = (300 + k * 180 + t * 40) % 2100 - 100
            by = 200 + k * 40 + math.sin(t * 2 + k) * 10
            flap = math.sin(t * 7 + k) * 10
            c.drawPath(path([(bx - 26, by - flap), (bx, by), (bx + 26, by - flap)], close=False), P(stroke=4))
    f.over('#3B2E6E', m.cov)
    lyrics.draw_v(f, t, 31, x=360, y=110, size=82, fill='#FFF1D6', edge='#3B2E6E', zh_color='#FFF1D6')
    return f.a


def s32_station(t, sh):
    u = lin(t, bar(31), bar(32))
    f = Frame('paper')
    hz = 640
    _dusk_sky(f, hz)
    side.sea(f, hz, 700, 0, t, tod='dusk')
    with Layer() as (c, L):
        # roof + pillars
        c.drawRect(skia.Rect.MakeLTRB(-100, 40, 2100, 96), paint('#22204F'))
        for k in range(5):
            c.drawRect(skia.Rect.MakeXYWH(120 + k * 420, 96, 26, 720), paint('#22204F'))
        summer.station_sign(c, 1150, 300, s=0.95)
    f.layer(L)
    # train arriving from the left, decelerating
    x = lerp(-3600, -260, ease_out(lin(u, 0.0, 0.85), 2.4))
    with Layer() as (c, L):
        summer.railcar(c, x, 860, s=1.0, length=1800, t=t, livery=('#F4EAD6', '#2F5DC4', '#E8383D'), lit=True)
    f.layer(L)
    with Layer() as (c, L):
        summer.platform(c, 860, color='#5B3C8C', edge='#FFCB45')
    f.layer(L)
    lyrics.draw_v(f, t, 32, x=1770, y=150, size=80, fill='#FFF1D6', edge='#22204F', zh_color='#FFF1D6')
    return f.a


def s33_door(t, sh):
    u = lin(t, bar(32), bar(33))
    name = pick('kimi_platform', 'kimi_back')
    f = Frame('paper')
    if name == 'kimi_platform':
        sprite.scene_par(f, name, zoom=1.07, cx=0.5, cy=0.45, u=u, par=0.03, t=t)
    else:
        _dusk_sky(f, 700)
        sprite.place(f, name, 960, 600, 980, t=t, wind=3, mul='#FF9A74', mul_amt=0.3)
    lyrics.draw_v(f, t, 33, x=1770, y=110, size=80, fill='#FFF1D6', edge='#3B2E6E', zh_color='#FFF1D6')
    return f.a


def s34_doors_close(t, sh):
    u = lin(t, bar(33), bar(34))
    f = Frame('paper')
    _dusk_sky(f, 1000)
    # her silhouette behind the door glass
    with Mask() as (c, m):
        people.girl_hat(c, 960, 1180, 980, t=t)
    f.over('#3B2E6E', m.cov, alpha=0.8)
    close = ease_io(lin(u, 0.25, 0.7), 3)
    gap = lerp(560, 0, close)
    with Layer() as (c, L):
        for sgn in (-1, 1):
            x_in = 960 + sgn * gap / 2
            x_out = x_in + sgn * 900
            r = skia.Rect.MakeLTRB(min(x_in, x_out), -20, max(x_in, x_out), 1100)
            c.drawRect(r, paint('#DDE3F4'))
            gx0 = x_in + sgn * 110
            gx1 = x_in + sgn * 520
            c.drawRoundRect(skia.Rect.MakeLTRB(min(gx0, gx1), 140, max(gx0, gx1), 720), 20, 20, paint('#6FB6E8', alpha=0.25))
            c.drawRoundRect(skia.Rect.MakeLTRB(min(gx0, gx1), 140, max(gx0, gx1), 720), 20, 20, paint('#8E98D8', stroke=8))
            c.drawRect(skia.Rect.MakeLTRB(min(x_in, x_in + sgn * 26), -20, max(x_in, x_in + sgn * 26), 1100), paint('#141B3D'))
    f.layer(L)
    lyrics.draw_v(f, t, 34, x=1770, y=110, size=80, fill='#141B3D', edge='#FFF1D6', zh_color='#141B3D')
    return f.a


def s35_eyes(t, sh):
    u = lin(t, bar(34), bar(35))
    f = Frame('#141B3D')
    if has('kimi_crying'):
        # the eyes first: tears welling, slow push
        sprite.scene_par(f, 'kimi_crying', zoom=2.1, cx=0.5, cy=0.37, u=u, par=0.015, t=t)
    else:
        sprite.scene_par(f, 'kimi_portrait', zoom=2.45, cx=0.66, cy=0.36, u=u, par=0.04, t=t)
    lyrics.draw_v(f, t, 35, x=1770, y=110, size=80, fill='#DDEFF4', edge='#0B1030', zh_color='#B9C3EA')
    return f.a


def s36_breaking(t, sh):
    u = lin(t, bar(35), bar(36))
    name = pick('kimi_crying', 'kimi_portrait')
    f = Frame('#0B1030')
    k = smooth(lin(u, 0.3, 1.0))
    fr = Frame('#0B1030')
    sprite.scene_par(fr, name, zoom=1.08, cx=0.5, cy=0.45, u=u, par=0.05, t=t)
    if k <= 0:
        f.a = fr.a
    else:
        # the picture peels off into its own dots, which rise like bubbles into the dark
        ones = np.ones((core.H, core.W), np.float32)
        dots = Frame('#0B1030')
        fx.disintegrate(dots, fr.a, ones, k, t, cell=13, rise=640, front='down', spread=50)
        m = smooth(clamp(k / 0.14))
        f.a = fr.a * (1 - m) + dots.a * m
    lyrics.draw_v(f, t, 36, x=1770, y=110, size=80, fill='#DDEFF4', edge='#0B1030', zh_color='#B9C3EA')
    return f.a


def s37_depart(t, sh):
    u = lin(t, bar(36), bar(37))
    f = Frame('paper')
    hz = 640
    _dusk_sky(f, hz, cols=('#F6C9B0', '#E8A0A8', '#B87AA8', '#7A5A9E', '#3B3C7A', '#22204F'))
    side.sea(f, hz, 700, 0, t, tod='dusk')
    with Layer() as (c, L):
        c.drawRect(skia.Rect.MakeLTRB(-100, 40, 2100, 96), paint('#22204F'))
        for k in range(5):
            c.drawRect(skia.Rect.MakeXYWH(120 + k * 420, 96, 26, 720), paint('#22204F'))
    f.layer(L)
    x = lerp(-260, 2600, ease_in(lin(u, 0.05, 0.9), 2.2))
    with Layer() as (c, L):
        summer.railcar(c, x, 860, s=1.0, length=1800, t=t, lit=True)
    rgb, a = L.rgb, L.alpha
    speed = ease_in(lin(u, 0.05, 0.9), 1.2) * 120
    if speed > 2:
        pm = core.motion_blur(rgb * a[..., None], speed, taps=9)
        am = core.motion_blur(np.repeat(a[..., None], 3, 2), speed, taps=9)[..., 0]
        rgb, a = pm / np.maximum(am[..., None], 1e-3), am
    f.image(np.clip(rgb, 0, 1), a)
    with Layer() as (c, L):
        summer.platform(c, 860, color='#5B3C8C', edge='#FFCB45')
    f.layer(L)
    # him, alone on the platform
    with Mask() as (c, m):
        people.boy_back(c, 520, 1060, 520)
    f.over('#141B3D', m.cov)
    lyrics.draw_v(f, t, 37, x=1770, y=110, size=82, fill='#FFF1D6', edge='#22204F', zh_color='#FFF1D6')
    # build into the chorus: white bloom
    f.a = core.flash(f.a, ease_in(lin(t, bar(37) - 0.9, bar(37)), 3), '#FFFDF6')
    return f.a


def shots():
    return [
        (Shot('s30_underwater', bar(29), bar(30), s30_underwater), Tr('heat', 0.6)),
        (Shot('s31_seawall', bar(30), bar(31), s31_seawall), Tr('dissolve', 0.5)),
        (Shot('s32_station', bar(31), bar(32), s32_station), Tr('cut')),
        (Shot('s33_door', bar(32), bar(33), s33_door), Tr('cut')),
        (Shot('s34_doors_close', bar(33), bar(34), s34_doors_close), Tr('dissolve', 0.4)),
        (Shot('s35_eyes', bar(34), bar(35), s35_eyes), Tr('dissolve', 0.5)),
        (Shot('s36_breaking', bar(35), bar(36), s36_breaking), Tr('dots', 0.6, grow='up', cell=24)),
        (Shot('s37_depart', bar(36), bar(37), s37_depart), Tr('cut')),
    ]

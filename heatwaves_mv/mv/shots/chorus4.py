"""Chorus 4 — quiet night walk, then the build — 147.36 – 162.18 s"""
import math
import os

import cv2
import numpy as np
import skia

from .. import core, lyrics
from ..core import Frame, View, Mask, Layer, P, paint, path, clamp, smooth, ease_io, ease_out, ease_in, lin, halftone
from ..edit import Shot, Tr
from ..el import road as rd, land, sprite, fx, people, night
from ..timing import bar, BEAT, beat_pulse, beat_index
from .common import lerp


def s50_walk(t, sh):
    u = t - bar(49)
    scroll = u * 160
    f = Frame('night')
    v = View()
    night.sky(f, v, horizon=900, moon=(1500, 200, 64), t=t)
    vs = View(1.0, 960 + scroll * 0.15, 540)
    night.far_town(f, vs, ground=820, seed=11)
    vw = View(1.0, 960 + scroll, 540)
    night.block_wall(f, vw, y_top=700, ground=900, x0=-2000, x1=6000, gate=None)
    for k in range(-1, 4):
        lx = 700 + k * 1300
        night.street_lamp(f, vw, t, x=lx, ground=930, height=640, moths=True)
    ys, xs = core.coords()
    f.over('#141B3D', np.clip((ys - 900) * core.S + 0.5, 0, 1).astype(np.float32))
    with Mask() as (c, m):
        people.boy_walk(c, 760, 960, 420, u * 6.5)
    f.over('#06081A', m.cov)
    # long shadow on the road from the lamps
    sh_ = cv2.warpAffine(m.cov, np.float32([[1, 1.2, -960 * core.S * 1.2 * 0.8], [0, 0.18, 960 * core.S * 0.82]]),
                         (core.W, core.H))
    f.over('#06081A', sh_ * 0.5)
    lyrics.draw_v(f, t, 50, x=1770, y=110, size=78, fill='#F4EAD6', edge='#06081A', zh_color='#B9C3EA')
    return f.a


def s51_vending(t, sh):
    u = lin(t, bar(50), bar(51))
    v = View(1.0 + 0.1 * ease_io(u, 2), 1000, 600)
    f = Frame('night')
    night.sky(f, v, horizon=900, moon=None, t=t)
    night.far_town(f, v, ground=760, seed=13)
    night.block_wall(f, v, y_top=640, ground=960, gate=None)
    night.vending_machine(f, v, t, x=1240, ground=960, scale=1.25)
    ys, xs = core.coords()
    gy = v.pt(0, 960)[1]
    f.over('#141B3D', np.clip((ys - gy) * core.S + 0.5, 0, 1).astype(np.float32))
    with Mask(v) as (c, m):
        people.boy_back(c, 880, 1000, 560, sway=-3)
    f.over('#06081A', m.cov)
    M = np.float32([[1, 0, -6 * core.S], [0, 1, 0]])
    rim = np.clip(m.cov - cv2.warpAffine(m.cov, M, (core.W, core.H)), 0, 1)
    f.over('#FFFDF6', rim, alpha=0.8)
    fx.motes(f, t, n=14, seed=8, color='#F4EAD6', area=(1000, 300, 1500, 700), rise=-6, r=(1.5, 3), alpha=0.8,
             glow=False)
    lyrics.draw_v(f, t, 51, x=380, y=110, size=78, fill='#F4EAD6', edge='#06081A', zh_color='#B9C3EA')
    return f.a


def _night_road(t, f, cam, her=1.0, haze=4.0):
    rd.world(f, t, cam, tod='night', clouds=False, mirage=0.5, mirage_depth=20, haze=0.0, poles=(1, -1), pole_X=4.6)
    # lamps along the road
    for (X, Z) in ((-4.6, cam.z + 30), (4.6, cam.z + 75), (-4.6, cam.z + 150)):
        x, y = cam.proj(X * 0.8, 6.0, Z)
        r = cam.scale(Z) * 6
        f.over('#F4F7E8', halftone(core.radial(x, y + r * 0.8, r * 1.4, 1.2, sy=1.6), cell=6), alpha=0.6)
        f.over('#F4F7E8', core.mask(lambda c: c.drawCircle(x, y, max(2.0, r * 0.06), P())))
    if her > 0:
        x, y = cam.proj(0.6, 0, cam.z + 75)
        hh = cam.scale(cam.z + 75) * 1.6
        with Mask() as (c, m):
            people.girl_hat(c, x, y, hh, t=t)
        cov = core.heat_haze(m.cov, t, amp=haze, wavelength=8)
        f.over('#B9C3EA', cov, alpha=0.75 * her)
        # her reflection on the warm night asphalt
        ys, xs = core._grid()
        yl = y * core.S
        my = (2 * yl - ys).astype(np.float32)
        refl = cv2.remap(cov, xs, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        refl = core.heat_haze(refl, t, amp=haze * 1.5, wavelength=6)
        f.over('#8E98D8', refl * (ys > yl) * 0.35 * her)
    ys, xs = core.coords()
    reg = np.exp(-((ys - cam.horizon - 20) / 120.0) ** 2).astype(np.float32)
    f.a = core.heat_haze(f.a, t, amp=2.0, wavelength=26, region=reg)


def s52_nightmirage(t, sh):
    u = lin(t, bar(51), bar(52))
    cam = land.Cam(f=1500, x=-0.3, h=1.55, z=40 + u * 2.5, horizon=560)
    f = Frame('night')
    _night_road(t, f, cam, her=smooth(lin(u, 0.1, 0.4)), haze=4 + 3 * u)
    lyrics.draw_v(f, t, 52, x=1770, y=110, size=80, fill='#F4EAD6', edge='#06081A', zh_color='#B9C3EA')
    return f.a


def s53_stop(t, sh):
    u = lin(t, bar(52), bar(53))
    cam = land.Cam(f=1500, x=-0.3, h=1.55, z=42.5, horizon=560)
    f = Frame('night')
    _night_road(t, f, cam, her=1 - smooth(lin(u, 0.25, 0.8)), haze=7)
    with Mask() as (c, m):
        people.boy_back(c, 620, 1240, 980)
    f.over('#06081A', m.cov)
    lyrics.draw_v(f, t, 53, x=1770, y=110, size=80, fill='#F4EAD6', edge='#06081A', zh_color='#B9C3EA')
    return f.a


def s54_rise(t, sh):
    u = lin(t, bar(53), bar(54))
    f = Frame('night')
    # tilt up from the night town into the sky; the horizon starts to burn toward dawn
    tilt = ease_in(u, 2) * 700
    v = View(1.0, 960, 540 + tilt * -1)
    dawn = smooth(lin(u, 0.35, 1.0))
    ys, xs = core.coords()
    hz = v.pt(0, 900)[1]
    field = np.clip(1 - (ys - (hz - 1600)) / 1600, 0, 1).astype(np.float32)
    cols = ['#5D66B0', '#3B4A8C', '#1E2A5E', '#141B3D', '#0B1030']
    f.a[:] = core.ramp(field, cols, cell=7, angle=45)
    g = core.vgrad(hz - 500, hz, 0.0, 1.0, ease=1.6)
    f.over('#FFB37A', halftone(g * dawn, cell=8, angle=30), alpha=0.9)
    rng = np.random.default_rng(4)
    with Mask() as (c, m):
        for i in range(160):
            x = rng.uniform(0, 1920)
            y = rng.uniform(-1600, 900) + tilt
            ln = 2 + ease_in(u, 3) * 40
            c.drawLine(x, y, x, y - ln, P(stroke=2, alpha=rng.uniform(0.4, 1)))
    f.over('#F4EAD6', m.cov * (1 - dawn * 0.6))
    night.far_town(f, v, ground=900, seed=5)
    lyrics.draw_v(f, t, 54, x=1770, y=110, size=84, fill='#F4EAD6', edge='#06081A', zh_color='#FFB37A')
    f.a = core.flash(f.a, ease_in(lin(t, bar(54) - 0.5, bar(54)), 3), '#FFF6E2')
    return f.a


def shots():
    return [
        (Shot('s50_walk', bar(49), bar(50), s50_walk), Tr('dissolve', 0.5)),
        (Shot('s51_vending', bar(50), bar(51), s51_vending), Tr('dissolve', 0.5)),
        (Shot('s52_nightmirage', bar(51), bar(52), s52_nightmirage), Tr('cut')),
        (Shot('s53_stop', bar(52), bar(53), s53_stop), Tr('dissolve', 0.5)),
        (Shot('s54_rise', bar(53), bar(54), s54_rise), Tr('cut')),
    ]

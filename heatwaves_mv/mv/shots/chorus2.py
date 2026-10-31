"""Chorus 2 — festival — 76.24 – 88.10 s"""
import math
import os

import numpy as np
import skia

from .. import core, lyrics
from ..core import Frame, View, Mask, Layer, P, paint, clamp, smooth, ease_io, ease_out, ease_in, lin, halftone
from ..edit import Shot, Tr
from ..el import fest, sprite, fx, night, people, side
from ..timing import bar, BEAT
from .common import lerp


def has(name):
    return os.path.exists(os.path.join(sprite.ASSET_DIR, name + '.png'))


def s26_yukata(t, sh):
    u = lin(t, bar(25), bar(26))
    f = Frame('night')
    sprite.scene_par(f, 'kimi_yukata', zoom=1.36, cx=0.46, cy=0.4, u=u, par=0.06, drift=(0.02, 0.0), t=t)
    fx.motes(f, t, n=50, seed=4, color='#FFCB45', area=(0, 300, 1920, 1080), rise=10, r=(2, 6), alpha=0.7)
    lyrics.draw_v(f, t, 26, x=1760, y=110, size=82, fill='#FFF3D6', edge='#141B3D', zh_color='#FFCB45')
    return f.a


def s27_goldfish(t, sh):
    u = lin(t, bar(26), bar(27))
    v = View(1.05 + 0.05 * u, 960, 540, rot=-3 + 4 * u)
    f = Frame('#2F5DC4')
    dip = smooth(lin(u, 0.15, 0.45)) - smooth(lin(u, 0.7, 0.85))
    torn = smooth(lin(u, 0.62, 0.72))
    px = lerp(1250, 980, ease_io(u, 2))
    py = lerp(420, 520, ease_io(u, 2))
    fest.goldfish_pool(f, t, view=v, poi=(px, py, dip, torn))
    lyrics.draw_v(f, t, 27, x=300, y=110, size=82, fill='#FFF3D6', edge='#141B3D', zh_color='#FFCB45')
    return f.a


def s28_riverbank(t, sh):
    u = lin(t, bar(27), bar(28))
    f = Frame('night')
    v = View(1.0 + 0.04 * u, 960, 540)
    night.sky(f, v, horizon=700, moon=None, stars=True, t=t)
    sched = fest.schedule(bar(27) - 1.0, bar(28) + 0.5, None, every=0.5, seed=11, area=(260, 120, 1660, 420))
    fest.sky_fireworks(f, t, sched, view=v)
    # far bank + river with the fireworks reflected
    night.far_town(f, v, ground=700, seed=3)
    ys, xs = core.coords()
    river = ((ys > v.pt(0, 700)[1]) & (ys < v.pt(0, 880)[1])).astype(np.float32)
    f.over('#0B1030', river)
    refl = np.flip(f.a, 0)
    import cv2
    shift = int((2 * v.pt(0, 700)[1] - core.H / core.S) * core.S)
    refl = np.roll(refl, shift, 0)
    refl = core.heat_haze(refl, t, amp=6, wavelength=10, speed=2.0)
    f.image(refl, river * 0.45)
    f.over('#B9C3EA', core.linescreen(river * 0.3, period=6, phase=t * 20) * river, alpha=0.3)
    # grassy bank in front + the two of them sitting, seen from behind
    with Mask(v) as (c, m):
        c.drawPath(core.smooth_path([(-100, 1100), (-100, 900), (500, 870), (1100, 890), (2100, 860), (2100, 1100)],
                                    close=True), P())
    f.over('#06081A', m.cov)
    with Mask(v) as (c, m):
        people.sitting_pair(c, 860, 1010, 420, t=t)
    f.over('#0B1030', m.cov)
    from ..timing import beat_index
    col = fest.FW_COLS[int(beat_index(t) * 2) % len(fest.FW_COLS)][0]
    import cv2
    M = np.float32([[1, 0, 0], [0, 1, 5 * core.S]])
    rim = np.clip(m.cov - cv2.warpAffine(m.cov, M, (core.W, core.H)), 0, 1)
    f.over(col, rim, alpha=0.85)
    lyrics.draw_v(f, t, 28, x=1770, y=110, size=80, fill='#FFF3D6', edge='#141B3D', zh_color='#FF5C9E')
    return f.a


def s29_profile(t, sh):
    u = lin(t, bar(28), bar(29))
    name = 'kimi_fireworks_profile' if has('kimi_fireworks_profile') else 'kimi_yukata'
    f = Frame('night')
    sprite.scene_par(f, name, zoom=1.09, cx=0.55, cy=0.45, u=u, par=0.06, drift=(-0.02, 0.0), t=t)
    # firework light flickering over her face, colour changing every beat
    from ..timing import beat_index, beat_pulse
    b = int(beat_index(t))
    col = fest.FW_COLS[b % len(fest.FW_COLS)][0]
    k = beat_pulse(t, decay=2.5)
    f.screen(col, np.full((core.H, core.W), 0.35 * k, np.float32))
    lyrics.draw_v(f, t, 29, x=1770, y=110, size=80, fill='#FFF3D6', edge='#141B3D', zh_color='#FF5C9E')
    return f.a


def shots():
    return [
        (Shot('s26_yukata', bar(25), bar(26), s26_yukata), Tr('dots', 0.5, grow='radial', cell=26)),
        (Shot('s27_goldfish', bar(26), bar(27), s27_goldfish), Tr('wipe', 0.45, angle=-30, color='#FFCB45')),
        (Shot('s28_riverbank', bar(27), bar(28), s28_riverbank), Tr('flash', 0.3)),
        (Shot('s29_profile', bar(28), bar(29), s29_profile), Tr('white', 0.6)),
    ]

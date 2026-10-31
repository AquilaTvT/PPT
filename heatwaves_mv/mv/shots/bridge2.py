"""Bridge 2 — quiet — 135.51 – 147.36 s: 君はどんな夢のなかに …"""
import math
import os

import numpy as np
import skia

from .. import core, lyrics
from ..core import Frame, View, Mask, Layer, P, paint, path, clamp, smooth, ease_io, ease_out, ease_in, lin, halftone
from ..edit import Shot, Tr
from ..el import sprite, fx, people, room
from ..timing import bar, BEAT, beat_pulse, beat_index
from .common import lerp


def has(name):
    return os.path.exists(os.path.join(sprite.ASSET_DIR, name + '.png'))


def pick(*names):
    for n in names:
        if has(n):
            return n
    return names[-1]


def _passing_light(f, t, strength=0.35, period=0.62, angle=18):
    """shadows of poles sweeping through a train window"""
    ys, xs = core.coords()
    th = math.radians(angle)
    u = (xs * math.cos(th) + ys * math.sin(th)) / 1920.0 - t / period
    band = (np.sin(u * 2 * math.pi * 1.0) > 0.82).astype(np.float32)
    f.mul('#3B4A8C', core.blur(band, 18) * strength)


def s46_sleep(t, sh):
    u = lin(t, bar(45), bar(46))
    name = pick('kimi_sleep_train', 'kimi_portrait')
    f = Frame('paper')
    sprite.scene_par(f, name, zoom=1.08, cx=0.5, cy=0.5, u=u, par=0.04, drift=(0.03, 0.0), t=t)
    _passing_light(f, t)
    fx.motes(f, t, n=40, seed=6, area=(0, 0, 1920, 1080), rise=6, r=(1.5, 3.5), alpha=0.6)
    lyrics.draw_v(f, t, 46, x=1770, y=110, size=80, fill='#FFFDF6', edge='#3B4A8C', zh_color='#FFFDF6')
    return f.a


def s47_smile(t, sh):
    u = lin(t, bar(46), bar(47))
    name = pick('kimi_sleep_train', 'kimi_portrait')
    f = Frame('paper')
    if name == 'kimi_sleep_train':
        sprite.scene_par(f, name, zoom=2.3, cx=0.6, cy=0.3, u=u, par=0.015, t=t)
    else:
        sprite.scene_par(f, name, zoom=2.25, cx=0.68, cy=0.35, u=u, par=0.015, t=t)
    _passing_light(f, t, strength=0.25, period=0.9)
    # warm light leak from the window side
    g = core.radial(1900, 100, 1300, falloff=1.4)
    f.screen('#FFCB45', g * 0.45)
    lyrics.draw_v(f, t, 47, x=360, y=110, size=80, fill='#FFFDF6', edge='#3B4A8C', zh_color='#FFFDF6')
    return f.a


def s48_hands(t, sh):
    u = lin(t, bar(47), bar(48))
    f = Frame('#0B1030')
    f.over('#141B3D', halftone(core.radial(960, 300, 1300, 1.2), cell=7))
    g = core.radial(960, 120, 1100, falloff=1.4)
    f.over('#2BB3B1', halftone(g * 0.6, cell=7), alpha=0.5)
    with Mask() as (c, m):
        for sg in (-1, 1):
            c.save()
            c.translate(960 + sg * 250, 760 + math.sin(t * 0.8 + sg) * 6)
            c.scale(sg, 1)
            c.rotate(-12)
            c.drawRoundRect(skia.Rect.MakeXYWH(-130, -120, 260, 260), 110, 110, P())   # palm
            for k, (fx_, fl, w) in enumerate(((-100, 210, 46), (-38, 260, 48), (24, 270, 48), (86, 230, 44))):
                c.drawLine(fx_, -60, fx_ + k * 6 - 10, -60 - fl, P(stroke=w))
            c.drawLine(120, 20, 250, -110, P(stroke=56))
            c.drawRoundRect(skia.Rect.MakeXYWH(-120, 100, 240, 500), 60, 60, P())     # wrist/arm
            c.restore()
    f.over('#06081A', m.cov)
    import cv2
    M = np.float32([[1, 0, 0], [0, 1, 7 * core.S]])
    rim = np.clip(m.cov - cv2.warpAffine(m.cov, M, (core.W, core.H)), 0, 1)
    flick = 0.7 + 0.3 * math.sin(t * 11) * math.sin(t * 5.7)
    f.over('#7FE3DE', rim, alpha=0.9 * flick)
    f.over('#2BB3B1', halftone(core.radial(960, 600, 500, 1.4) * m.cov * 0.6, cell=5), alpha=0.6 * flick)
    lyrics.draw_v(f, t, 48, x=1770, y=110, size=80, fill='#F4EAD6', edge='#06081A', zh_color='#7FE3DE')
    return f.a


def s49_noshadow(t, sh):
    u = lin(t, bar(48), bar(49))
    f = Frame('paper')
    sprite.scene_par(f, 'kimi_portrait', zoom=2.0, cx=0.68, cy=0.36, u=u, par=0.02, t=t)
    # light floods in until nothing is left in shadow
    k = smooth(lin(u, 0.3, 1.0))
    g = core.radial(1500, 200, 1600, falloff=1.0)
    f.screen('#FFFBEA', np.clip(g * (0.3 + 0.7 * k), 0, 1))
    f.over('#FFFDF6', halftone(np.full((core.H, core.W), k * 0.9, np.float32), cell=10), alpha=k)
    lyrics.draw_v(f, t, 49, x=380, y=110, size=80, fill='#FFFDF6', edge='#C77B6A', zh_color='#FFFDF6')
    return f.a


def shots():
    return [
        (Shot('s46_sleep', bar(45), bar(46), s46_sleep), Tr('dissolve', 0.8)),
        (Shot('s47_smile', bar(46), bar(47), s47_smile), Tr('dissolve', 0.8)),
        (Shot('s48_hands', bar(47), bar(48), s48_hands), Tr('dissolve', 0.8)),
        (Shot('s49_noshadow', bar(48), bar(49), s49_noshadow), Tr('white', 0.8)),
    ]

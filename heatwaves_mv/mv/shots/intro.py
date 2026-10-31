"""Intro 0 – 16.98 s: CRT on, the dithered memory, title, the midnight room, back into the TV."""
import math

import numpy as np

from .. import core, lyrics, text
from ..core import Frame, View, clamp, smooth, ease_io, ease_out, ease_in, lin
from ..edit import Shot, Tr
from ..el import room, tv
from ..timing import bar
from .common import tv_pixel_road, crt_full, lerp

TV_ZOOM = 1920 / (1628 - 1312) * 1.02      # zoom at which the screen fills the frame
TVC = room.TV_CENTER


def _title_lowres(t, w=320, h=180):
    """pixel title card: sun disc + HEAT WAVES wobbling"""
    def scene(tt):
        f = Frame('#FFF3D6')
        ys, xs = core.coords()
        field = np.clip(1 - ys / 1080, 0, 1).astype(np.float32)
        f.a[:] = core.ramp(field, ['#FFCB45', '#FF9A74', '#F0686A', '#B8457A', '#5B3C8C'], cell=40, angle=45)
        f.over('#FFF3D6', core.mask(lambda c: c.drawCircle(960, 600, 300, core.P())))
        f.mul('#FFCB45', core.halftone(core.radial(960, 600, 300, 1.0), cell=40))
        gl, _ = text.layout_h('HEAT WAVES', 960, 560, 230, 'silk', tracking=0.02, align='center')
        fc, sc = text.render_glyphs(gl, stroke=40)
        f.over('#141B3D', sc)
        f.over('#FFFDF6', fc)
        gl2, _ = text.layout_h('JAPANESE VERSION  /  LIME', 960, 800, 64, 'silk', tracking=0.1, align='center')
        fc2, sc2 = text.render_glyphs(gl2, stroke=16)
        f.over('#141B3D', sc2)
        f.over('#FFFDF6', fc2)
        f.a = core.heat_haze(f.a, tt, amp=9, wavelength=110, speed=1.2)
        return f.a
    return tv.lowres(scene, t, w, h)


def tv_content(t):
    """what the CRT shows during the intro, full-res with CRT treatment"""
    if t < 2.16:
        img = tv.upscale_nearest(tv.static(t))
    elif t < bar(2):
        k = smooth(lin(t, 2.16, 3.4))
        road = tv.upscale_nearest(tv_pixel_road(t - 2.16, z0=40))
        st = tv.upscale_nearest(tv.static(t))
        if k < 1:
            ys = np.arange(core.H)[:, None, None] / core.H
            band = (np.sin(ys * 40 + t * 30) * 0.5 + 0.5) < (1 - k)
            img = np.where(band, st, road)
        else:
            img = road
    elif t < 13.6:
        img = tv.upscale_nearest(_title_lowres(t))
    else:
        img = tv.upscale_nearest(tv_pixel_road(t - 2.16, z0=40, speed=7 + max(0, t - 13.6) * 6))
    return tv.crt(img, t, curve=0.07, glow=0.5, roll=0.25)


def s01_power(t, sh):
    f = Frame('#06081A')
    f.over('#0B1030', core.halftone(np.full((core.H, core.W), 0.35, np.float32), cell=7))
    # standby LED
    if t < 1.15:
        a = 0.6 + 0.4 * math.sin(t * 9)
        f.over('#E8383D', core.mask(lambda c: c.drawCircle(960, 990, 6, core.P(blur=1))), alpha=a)
        f.add('#E8383D', core.radial(960, 990, 60, 2.0), alpha=0.4 * a)
        return f.a
    p = lin(t, 1.15, 2.0)
    img = tv.power_on(tv_content(t), p)
    return img


def s02_tvroad(t, sh):
    f = Frame('#06081A')
    f.a = tv_content(t)
    lyrics.draw_tv(f, t, 0, y=930, size=42)
    lyrics.draw_tv(f, t, 1, y=930, size=42)
    lyrics.draw_tv(f, t, 2, y=930, size=42)
    return f.a


def s03_pullback(t, sh):
    """title on the TV, then the camera pulls back to reveal the room"""
    k = ease_io(lin(t, 9.2, 11.05), 3)
    zoom = math.exp(lerp(math.log(TV_ZOOM), math.log(1.0), k))
    cx = lerp(TVC[0], 960, k)
    cy = lerp(TVC[1], 540, k)
    v = View(zoom, cx, cy)
    content = tv_content(t)
    f = Frame('night')
    room.room(f, t, v, tv_content=content, clock_text='23:59')
    lyrics.draw_tv(f, t, 2, y=930, size=42, alpha=1 - k)
    return f.a


def s04_details(t, sh):
    f = Frame('night')
    content = tv_content(t)
    if t < bar(3) + 1.5:
        # wind chime against the moon, a gust passes
        u = lin(t, bar(3), bar(3) + 1.5)
        v = View(2.7 + 0.15 * u, 610, 300 - 10 * u)
        gust = math.sin(lin(t, bar(3) + 0.2, bar(3) + 1.4) * math.pi) * 0.6
        room.room(f, t, v, tv_content=content, gust=gust)
    else:
        u = lin(t, bar(3) + 1.5, bar(4))
        v = View(2.3 + 0.2 * u, 330 + 20 * u, 650)
        room.room(f, t, v, tv_content=content)
    lyrics.draw_h(f, t, 3, x=960, y=935, size=60, fill='#F4EAD6', edge='#06081A', fname='corm_i', stroke=6)
    return f.a


def s05_intotv(t, sh):
    u = lin(t, bar(4), bar(5))
    k = ease_in(u, 3)
    zoom = math.exp(lerp(math.log(1.0), math.log(TV_ZOOM * 1.15), k))
    cx = lerp(960, TVC[0], ease_io(u, 2))
    cy = lerp(540, TVC[1], ease_io(u, 2))
    v = View(zoom, cx, cy)
    f = Frame('night')
    room.room(f, t, v, tv_content=tv_content(t), clock_text='23:59')
    # heat starts to ripple through the room
    amp = ease_in(lin(t, bar(4) + 1.0, bar(5)), 2) * 18
    if amp > 0.3:
        f.a = core.heat_haze(f.a, t, amp=amp, wavelength=34, speed=2.0)
    fl = ease_in(lin(t, bar(5) - 0.45, bar(5)), 2)
    f.a = core.flash(f.a, fl, '#FFFBEA')
    return f.a


def shots():
    return [
        (Shot('s01_power', 0.0, bar(0), s01_power), Tr('cut')),
        (Shot('s02_tvroad', bar(0), bar(2), s02_tvroad), Tr('cut')),
        (Shot('s03_pullback', bar(2), bar(3), s03_pullback), Tr('cut')),
        (Shot('s04_details', bar(3), bar(4), s04_details), Tr('dissolve', 0.4)),
        (Shot('s05_intotv', bar(4), bar(5), s05_intotv), Tr('cut')),
    ]

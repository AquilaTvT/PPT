"""Chorus 1 — 28.83 – 52.54 s"""
import math
import os

import numpy as np
import skia

from .. import core, lyrics, text
from ..core import Frame, View, Mask, Layer, P, paint, clamp, smooth, ease_io, ease_out, ease_in, lin, halftone
from ..edit import Shot, Tr
from ..el import road as rd, land, side, sprite, fx, room, summer, cloud
from ..timing import bar, BEAT, beat_pulse
from .common import lerp


def has(name):
    return os.path.exists(os.path.join(sprite.ASSET_DIR, name + '.png'))


def s10_portrait(t, sh):
    u = lin(t, bar(9), bar(10))
    f = Frame('paper')
    sprite.scene_par(f, 'kimi_portrait', zoom=1.1, cx=0.6, cy=0.42, u=ease_io(u, 2), par=0.07, drift=(0.025, 0.0),
                     t=t)
    fx.petals(f, t, n=26, seed=3, wind=(320, 60), size=(8, 18))
    fx.motes(f, t, n=40, seed=9, area=(0, 0, 1920, 700), rise=8, alpha=0.7)
    lyrics.draw_v(f, t, 10, x=300, y=110, size=86)
    f.a = core.flash(f.a, 1 - ease_out(lin(t, bar(9), bar(9) + 0.35), 2), '#FFFDF6')
    return f.a


def s11_clock(t, sh):
    u = lin(t, bar(10), bar(11))
    flip = t >= bar(10) + 0.42
    txt = ' 0:00' if flip else '23:59'
    k = ease_io(lin(t, bar(10) + 1.2, bar(11)), 3)
    zoom = lerp(5.2, 2.0, k)
    cx = lerp(room.CLOCK[0], 1250, k)
    cy = lerp(room.CLOCK[1] - 8, 820, k)
    v = View(zoom, cx, cy)
    f = Frame('night')
    from .intro import tv_content
    room.room(f, t, v, tv_content=tv_content(13.7 + (t - bar(10)) * 0.3), clock_text=txt)
    if abs(t - (bar(10) + 0.42)) < 0.12:
        f.a = core.chroma_shift(f.a, 14, 0)
    lyrics.draw_v(f, t, 11, x=1770, y=110, size=80, fill='#F4EAD6', edge='#06081A', zh_color='#7FE3DE')
    return f.a


def s12_type(t, sh):
    u = t - bar(11)
    f = Frame('#FF9A74')
    ys, xs = core.coords()
    field = np.clip(1 - ys / 1080, 0, 1).astype(np.float32)
    f.a[:] = core.ramp(field, ['#FFE7B8', '#FFC489', '#FF9A74', '#F0686A', '#B8457A'], cell=9, angle=45)
    # rows of HEAT WAVE marquees, alternating solid / outline and direction
    fill_m = np.zeros((core.H, core.W), np.float32)
    line_m = np.zeros((core.H, core.W), np.float32)
    _, period = text.layout_h('HEAT WAVES ', 0, 0, 170, 'dela')
    for r in range(6):
        y = 90 + r * 182
        sp = (260 if r % 2 == 0 else -260) * (1 + 0.15 * r)
        x = -period + (u * sp + r * 137) % period
        gl, _ = text.layout_h('HEAT WAVES ' * 4, x, y, 170, 'dela')
        if r % 2 == 0:
            fc, _ = text.render_glyphs(gl)
            if fc is not None:
                fill_m = np.maximum(fill_m, fc)
        else:
            fc, sc = text.render_glyphs(gl, stroke=6)
            if sc is not None:
                line_m = np.maximum(line_m, np.clip(sc - fc, 0, 1))
    wav = core.heat_haze(np.dstack([fill_m, line_m, fill_m * 0]), t, amp=26, wavelength=120, speed=1.0)
    f.over('#FFF3D6', wav[..., 0], alpha=0.9)
    f.mul('#B8457A', halftone(wav[..., 0] * core.vgrad(0, 1080, 0.0, 0.6), cell=6, angle=45))
    f.over('#5B3C8C', wav[..., 1])
    # the boy walking into the haze (small silhouette, centre)
    walk = math.sin(u * 7.0)
    with Mask() as (c, m):
        x, y = 960, 860
        c.drawCircle(x, y - 150, 22, P())
        c.drawRoundRect(skia.Rect.MakeXYWH(x - 26, y - 128, 52, 100), 18, 18, P())
        c.drawLine(x - 10, y - 30, x - 10 - walk * 22, y + 40, P(stroke=18))
        c.drawLine(x + 10, y - 30, x + 10 + walk * 22, y + 40, P(stroke=18))
        c.drawLine(x - 24, y - 110, x - 30 + walk * 18, y - 40, P(stroke=13))
        c.drawLine(x + 24, y - 110, x + 30 - walk * 18, y - 40, P(stroke=13))
    body = core.heat_haze(m.cov, t, amp=8, wavelength=20)
    f.over('#141B3D', body)
    lyrics.draw_v(f, t, 12, x=1100, y=150, size=104, fill='#141B3D', edge='#FFF3D6', stroke=12, zh_color='#141B3D',
                  haze=4.0)
    f.a = core.heat_haze(f.a, t, amp=3, wavelength=30)
    return f.a


def s13_walkaway(t, sh):
    u = lin(t, bar(12), bar(13))
    cam = land.Cam(f=1500, x=-0.3, h=1.35, z=20 + u * 3, horizon=600)
    zk = cam.z + 7 + ease_in(u, 1.4) * 34
    fade = 1 - smooth(lin(u, 0.62, 0.95))

    def fig(f):
        if fade <= 0:
            return
        bob = abs(math.sin(u * 14)) * 0.03
        fx_, fy_ = cam.proj(0.35, bob, zk)
        hpx = cam.f * 1.62 / (zk - cam.z)
        L = sprite.warp('kimi_back', fx_, fy_, hpx, anchor=(0.5, 0.97), wind=5, t=t)
        L = sprite.shade_print(L, cell=6, shade_k=0.55, light_k=0.3)
        L = sprite.rim(L, '#FFFBEA', 0.9, dx=6, dy=4)
        a = L['a']
        if fade < 1:
            dots = halftone(np.full_like(a, fade), cell=7, angle=45)
            a = a * dots
        f.image(L['rgb'], a)

    f = Frame('paper')
    rd.world(f, t, cam, tod='noon', haze=4.0 + 6 * u, mirage=1.0, mirage_depth=40, figure=fig, seed=11,
             poles=(1,), cloud_dx=-u * 10)
    lyrics.draw_v(f, t, 13, x=1770, y=110, size=82)
    return f.a


def s14_sunflowers(t, sh):
    u = lin(t, bar(13), bar(14))
    v = View(1.0 + 0.06 * u, 960, 540 - 20 * u)
    f = Frame('paper')
    hz = 760
    rd.sky(f, 'noon', hz)
    rd.sun(f, 'noon', x=1450, y=170, amt=1.0)
    layer = rd.clouds_layer('noon', hz, seed=51, specs=[(51, 520, 1100, 600, 2), (52, 1500, 640, 420, 1)])
    rd.put_layer(f, layer, dy=-60, dx=-u * 20)
    ys, xs = core.coords()
    gm = np.clip((ys - (hz - 40)) * core.S + 0.5, 0, 1).astype(np.float32)
    gf = np.clip((ys - hz + 40) / 400, 0, 1).astype(np.float32)
    f.image(core.ramp(gf, ['#9CCB5E', '#5FA746', '#3B8740', '#2A6B3C'], cell=7, angle=15), gm)
    summer.sunflower_field(f, t, horizon=hz, seed=3, wind=1.2, view=v)
    # the hat sails across the sky
    hx = lerp(-260, 2150, ease_io(u, 1.6))
    hy = 380 - math.sin(u * math.pi) * 180 + math.sin(t * 3) * 14
    fx.straw_hat(f, hx, hy, 0.75, rot=-15 + u * 220 * 0.3 + math.sin(t * 2.5) * 12, t=t, tilt=0.42 + 0.2 * math.sin(t * 2))
    fx.petals(f, t, n=30, seed=7, wind=(380, -20), size=(8, 16))
    fx.flare(f, t, 1450, 170, amount=0.8)
    lyrics.draw_v(f, t, 14, x=340, y=110, size=86)
    return f.a


def _topdown(f, t, v, tv_flicker=1.0):
    # tatami from above: six mats in a classic layout
    f.a[:] = core._col('#141B3D')
    mats = [(0, 0, 2, 1), (0, 1, 1, 2), (1, 1, 1, 2), (2, 0, 1, 2), (0, 3, 2, 1), (2, 2, 1, 2)]
    unit = 300
    ox, oy = 960 - 1.5 * unit, 540 - 2 * unit
    with Layer(view=v) as (c, L):
        for (mx, my, w, h) in mats:
            r = skia.Rect.MakeXYWH(ox + mx * unit + 4, oy + my * unit + 4, w * unit - 8, h * unit - 8)
            c.drawRect(r, paint('#2A3570'))
            c.drawRect(r, paint('#0E1436', stroke=14))
            for k in range(1, 30):
                if w > h:
                    xx = r.left() + k * r.width() / 30
                    c.drawLine(xx, r.top() + 10, xx, r.bottom() - 10, paint('#26306A', stroke=1.4))
                else:
                    yy = r.top() + k * r.height() / 30
                    c.drawLine(r.left() + 10, yy, r.right() - 10, yy, paint('#26306A', stroke=1.4))
    f.layer(L)
    # TV light from the right edge
    g = core.radial(2000, 540, 1400, falloff=1.4, view=v)
    f.over('#2BB3B1', halftone(g * (0.55 + 0.25 * tv_flicker), cell=7, angle=45), alpha=0.6)
    # the boy on his back, arms spread
    with Mask(v) as (c, m):
        cx, cy = 900, 560
        c.drawCircle(cx + 250, cy, 44, P())
        c.drawPath(core.smooth_path([(cx + 200, cy - 60), (cx + 120, cy - 75), (cx - 60, cy - 62), (cx - 90, cy),
                                     (cx - 60, cy + 62), (cx + 120, cy + 75), (cx + 200, cy + 60), (cx + 215, cy)],
                                    close=True), P())
        c.drawLine(cx + 160, cy - 60, cx + 230, cy - 210, P(stroke=30))
        c.drawLine(cx + 230, cy - 210, cx + 330, cy - 260, P(stroke=26))
        c.drawLine(cx + 160, cy + 60, cx + 120, cy + 240, P(stroke=30))
        c.drawLine(cx + 120, cy + 240, cx + 180, cy + 340, P(stroke=26))
        c.drawLine(cx - 80, cy - 30, cx - 360, cy - 70, P(stroke=46))
        c.drawLine(cx - 80, cy + 30, cx - 360, cy + 90, P(stroke=46))
    f.over('#06081A', m.cov)
    import cv2
    M = np.float32([[1, 0, -6 * core.S * v.zoom], [0, 1, 0]])
    rim = np.clip(m.cov - cv2.warpAffine(m.cov, M, (core.W, core.H)), 0, 1)
    f.over('#7FE3DE', rim, alpha=0.8 * tv_flicker)
    # electric fan from above: rotating blade shadow sweeping the floor
    ang = t * 50
    with Mask(v) as (c, m):
        c.save()
        c.translate(420, 300)
        c.rotate(math.sin(t * 0.55) * 35)
        for k in range(3):
            c.save()
            c.rotate(ang * 9 + k * 120)
            c.drawOval(skia.Rect.MakeXYWH(10, -30, 120, 60), P(alpha=0.35))
            c.restore()
        c.drawCircle(0, 0, 140, P(stroke=4, alpha=0.6))
        c.restore()
    f.over('#B9C3EA', m.cov, alpha=0.6)


def night_house(f, t, v, glow=1.0):
    from ..el import night
    night.sky(f, v, horizon=900, moon=(330, 190, 66), t=t)
    night.far_town(f, v, ground=880, seed=5)
    night.wires(f, v, [(-200, 180, 2200, 260, 70), (-200, 205, 2200, 290, 80), (-200, 230, 2200, 320, 85)])
    flick = 0.65 + 0.35 * math.sin(t * 13) * math.sin(t * 7.3 + 1)
    night.house(f, v, t, x=470, ground=980, tv_glow=glow, flicker=flick)
    night.block_wall(f, v, y_top=880, ground=1000, gate=(1310, 1430))
    night.street_lamp(f, v, t, x=1640, ground=1010, height=640)
    ys, xs = core.coords()
    road = np.clip((ys - v.pt(0, 1000)[1]) * core.S + 0.5, 0, 1).astype(np.float32)
    f.over('#141B3D', road)


def s15_house(t, sh):
    u = lin(t, bar(14), bar(15))
    v = View(1.0 + 0.16 * ease_io(u, 2), 900, 560 - 30 * u)
    f = Frame('night')
    night_house(f, t, v)
    lyrics.draw_v(f, t, 15, x=1770, y=110, size=80, fill='#F4EAD6', edge='#06081A', zh_color='#7FE3DE')
    return f.a


def s16_train(t, sh):
    u = t - bar(15)
    f = Frame('paper')
    hz = 560
    rd.sky(f, 'noon', hz)
    rd.sun(f, 'noon', x=380, y=140, amt=0.9)
    layer = rd.clouds_layer('noon', hz, seed=61, specs=[(61, 1250, 1200, 480, 2), (62, 300, 500, 300, 1)])
    rd.put_layer(f, layer, dx=-u * 6)
    side.sea(f, hz, 760, u * 100, t)
    summer.seawall(f, 760, 860)
    summer.railway(f, 900, x_off=0)
    with Layer() as (c, L):
        x = lerp(-2300, 2300, u / 2.96) - 300
        summer.railcar(c, x, 900, s=0.95, length=1700, t=t)
        # second car coupled
        summer.railcar(c, x - 1700 * 0.95 - 20, 900, s=0.95, length=1700, t=t)
    f.layer(L)
    # embankment grass below
    ys, xs = core.coords()
    g = (ys > 920).astype(np.float32)
    f.over('#43904A', g)
    f.mul('#2B6E3E', halftone(g * core.vgrad(920, 1080, 0.2, 0.7), cell=7, angle=15))
    f.a = core.heat_haze(f.a, t, amp=3.5, wavelength=24,
                         region=(np.exp(-((ys - 900) / 60.0) ** 2)).astype(np.float32))
    lyrics.draw_v(f, t, 16, x=1770, y=110, size=82)
    return f.a


def s17_busstop(t, sh):
    u = lin(t, bar(16), bar(17))
    f = Frame('paper')
    name = 'kimi_busstop' if has('kimi_busstop') else 'kimi_portrait'
    sprite.scene_par(f, name, zoom=1.08, cx=0.5, cy=0.5, u=u, par=0.06, drift=(-0.03, 0.0), t=t)
    # late-afternoon tint creeping in toward the verse (night)
    k = smooth(lin(u, 0.55, 1.0))
    f.mul('#5B3C8C', np.full((core.H, core.W), 0.55 * k, np.float32))
    lyrics.draw_v(f, t, 17, x=1770, y=110, size=82)
    return f.a


def shots():
    return [
        (Shot('s10_portrait', bar(9), bar(10), s10_portrait), Tr('cut')),
        (Shot('s11_clock', bar(10), bar(11), s11_clock), Tr('heat', 0.5)),
        (Shot('s12_type', bar(11), bar(12), s12_type), Tr('dots', 0.45, grow='down', cell=24)),
        (Shot('s13_walkaway', bar(12), bar(13), s13_walkaway), Tr('flash', 0.35)),
        (Shot('s14_sunflowers', bar(13), bar(14), s14_sunflowers), Tr('crt', 0.5)),
        (Shot('s15_house', bar(14), bar(15), s15_house), Tr('dissolve', 0.5)),
        (Shot('s16_train', bar(15), bar(16), s16_train), Tr('wipe', 0.5, angle=0, color='#FFFDF6')),
        (Shot('s17_busstop', bar(16), bar(17), s17_busstop), Tr('cut')),
    ]

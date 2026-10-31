"""Outro — dawn — 162.18 – 198.74 s"""
import math
import os

import cv2
import numpy as np
import skia

from .. import core, lyrics, text
from ..core import Frame, View, Mask, Layer, P, paint, path, clamp, smooth, ease_io, ease_out, ease_in, lin, halftone
from ..edit import Shot, Tr
from ..el import road as rd, land, sprite, fx, people, room, tv, side, summer
from ..timing import bar, BEAT, beat_pulse, beat_index, DURATION
from .common import lerp
from .chorus3 import crt_wall, mirror_shot


def has(name):
    return os.path.exists(os.path.join(sprite.ASSET_DIR, name + '.png'))


def pick(*names):
    for n in names:
        if has(n):
            return n
    return names[-1]


EN = dict(fill='#FFFDF6', edge='#3B3C7A', fname='corm_i', stroke=7, zh_gap=74)


def s55_sunrise(t, sh):
    u = lin(t, bar(54), bar(55))
    f = Frame('paper')
    hz = 680
    rd.sky(f, 'dawn', hz)
    sy = lerp(720, 560, ease_out(u, 2))
    g = core.radial(960, sy, 900, falloff=1.2)
    f.over('#FFE0B8', halftone(g, cell=10, angle=30), alpha=0.9)
    f.over('#FFFBEA', core.mask(lambda c: c.drawCircle(960, sy, 130, P())))
    layer = rd.clouds_layer('dawn', hz, seed=81, specs=[(81, 380, 700, 380, 2), (82, 1560, 640, 320, 1)])
    rd.put_layer(f, layer, dx=-u * 20)
    side.sea(f, hz, 1080, u * 50, t, tod='dawn')
    with Mask() as (c, m):
        rng = np.random.default_rng(2)
        for k in range(120):
            yy = hz + 6 + (1080 - hz) * rng.random() ** 1.5
            ww = 30 + (yy - hz) * 0.7
            a = max(0.0, math.sin(t * rng.uniform(2, 5) + k))
            c.drawLine(960 - ww * rng.random(), yy, 960 + ww * rng.random(), yy, P(stroke=3, alpha=a))
    f.over('#FFFBEA', m.cov)
    f.a = core.flash(f.a, 1 - ease_out(lin(t, bar(54), bar(54) + 0.8), 2), '#FFF6E2')
    lyrics.draw_h(f, t, 55, x=960, y=880, size=88, **EN)
    return f.a


def s56_calendar(t, sh):
    """tear-off calendar: a day flies off on every beat"""
    u = t - bar(55)
    f = Frame('#F4EAD6')
    ys, xs = core.coords()
    f.mul('#E2CFA6', halftone(core.radial(960, 540, 1300, 1.0), cell=8), alpha=0.6)
    b = beat_index(t) - beat_index(bar(55))
    day = 13 + int(max(0, b))
    frac = b - int(max(0, b)) if b >= 0 else 0.0
    def page(c, d, dx=0.0, dy=0.0, rot=0.0, curl=0.0):
        c.save()
        c.translate(960 + dx, 200 + dy)
        c.rotate(rot)
        c.drawRect(skia.Rect.MakeXYWH(-330, 0, 660, 760), paint('#FFFDF6'))
        c.drawRect(skia.Rect.MakeXYWH(-330, 0, 660, 760), paint('#B9C3EA', stroke=3))
        c.drawRect(skia.Rect.MakeXYWH(-330, 0, 660, 110), paint('#E8383D' if d % 7 == 0 else '#2F5DC4'))
        fnt = text.font('old', 430)
        s = str(d)
        w = fnt.measureText(s)
        c.drawString(s, -w / 2, 560, fnt, paint('#E8383D' if d % 7 == 0 else '#141B3D'))
        f2 = text.font('mincho_sb', 54)
        c.drawString('六月', -300, 80, f2, paint('#FFFDF6'))
        f3 = text.font('corm_i', 60)
        lab = 'June'
        w3 = f3.measureText(lab)
        c.drawString(lab, 300 - w3, 80, f3, paint('#FFFDF6'))
        f4 = text.font('mincho_sb', 46)
        wd = '日月火水木金土'[d % 7] + '曜日'
        w4 = f4.measureText(wd)
        c.drawString(wd, -w4 / 2, 690, f4, paint('#141B3D'))
        c.restore()
    with Layer() as (c, L):
        # binding + the stack
        c.drawRect(skia.Rect.MakeXYWH(620, 160, 680, 60), paint('#141B3D'))
        page(c, day + 1)
        if frac < 0.65:
            k = ease_in(frac / 0.65, 2)
            page(c, day, dx=k * 900, dy=-k * 260 + k * k * 500, rot=k * 70)
    f.layer(L)
    lyrics.draw_h(f, t, 56, x=960, y=1000, size=70, fill='#141B3D', edge='#F4EAD6', fname='corm_i', stroke=6, zh_gap=0,
                  zh=False)
    return f.a


def s57_ghosts(t, sh):
    u = t - bar(56)
    cam = land.Cam(f=1900, x=-0.2, h=1.4, z=60 + u * 6, horizon=580)
    b = beat_index(t)

    def figs(f):
        for k, (X, dz) in enumerate(((0.8, 26), (-1.6, 48), (1.9, 80), (-0.6, 130), (0.4, 200))):
            ph = (b * 0.5 + k * 0.37) % 1.0
            a = math.sin(ph * math.pi) ** 2
            if a < 0.05:
                continue
            rd.kimi_far(f, cam, cam.z + dz, X=X, t=t + k, haze=5.0, reflect=0.5, opacity=a,
                        mul='#F6C9B0', mul_amt=0.25)

    f = Frame('paper')
    rd.world(f, t, cam, tod='dawn', haze=5.0, mirage=1.0, mirage_depth=50, figure=figs, seed=31,
             specs=[(31, 700, 1300, 420, 2), (32, 1600, 520, 300, 1)], poles=(1,))
    lyrics.draw_h(f, t, 57, x=960, y=900, size=84, **EN)
    return f.a


def s58_burn(t, sh):
    u = lin(t, bar(57), bar(58))
    f = Frame('paper')
    name = pick('kimi_laugh_cutout', 'kimi_portrait')
    if name == 'kimi_laugh_cutout':
        hz = 760
        rd.sky(f, 'noon', hz)
        layer = rd.clouds_layer('noon', hz, seed=51, specs=[(51, 520, 1100, 600, 2), (52, 1500, 640, 420, 1)])
        rd.put_layer(f, layer, dy=-60)
        from ..el import summer as sm
        sm.sunflower_field(f, t, horizon=hz + 40, seed=5, wind=1.0)
        sprite.place(f, name, 960, 600, 1150 + 60 * u, t=t, wind=6, rim_color='#FFFBEA', rim_amt=0.9, rim_dir=(-6, 4))
    else:
        sprite.scene_par(f, name, zoom=1.18, cx=0.62, cy=0.4, u=u, par=0.06, t=t)
    # film burn from the corner
    k = ease_in(lin(u, 0.45, 1.0), 2)
    if k > 0:
        ys, xs = core.coords()
        d = np.sqrt((xs - 1700) ** 2 + (ys - 900) ** 2)
        n = core.value_noise((core.H, core.W), 90 * core.S, seed=4, octaves=3) * 300
        front = k * 2600
        burn = np.clip((front - d + n) / 140, 0, 1)
        edge = np.clip(1 - np.abs(front - d + n) / 70, 0, 1)
        f.over('#FF9A4D', edge, alpha=0.9)
        f.over('#FFE7A3', halftone(np.clip(edge * 1.5, 0, 1), cell=6))
        f.over('#FFFBEA', burn)
    lyrics.draw_h(f, t, 58, x=960, y=900, size=84, **EN)
    return f.a


def s59_wall(t, sh):
    u = lin(t, bar(58), bar(59))
    v = View(lerp(1.0, 1.25, ease_io(u, 2)), 960, 540)
    f = Frame('#06081A')
    crt_wall(f, t, v, cols=5, rows=3, seed=7, static_rate=0.15 + 0.5 * u)
    lyrics.draw_h(f, t, 59, x=960, y=900, size=84, **EN)
    return f.a


def s60_off(t, sh):
    u = lin(t, bar(59), bar(60))
    t_off = bar(59) + 1.3
    p = lin(t, t_off, t_off + 0.45)
    from .intro import tv_content
    content = tv.crt(tv.upscale_nearest(tv.static(t)), t, curve=0.07)
    if p > 0:
        content = tv.power_off(content, p)
    v = View(1.25, 1100, 600)
    f = Frame('night')
    room.room(f, t, v, tv_content=content, tv_on=1 - smooth(p), clock_text=' 4:52')
    # dawn creeping in through the window afterwards
    if p >= 1:
        k = smooth(lin(t, t_off + 0.5, bar(60)))
        x0, y0, x1, y1 = room.WINDOW
        g = core.radial(480, 330, 900, 1.3, view=v)
        f.over('#FFB37A', halftone(g * 0.5 * k, cell=8), alpha=0.5)
    lyrics.draw_h(f, t, 60, x=960, y=900, size=80, fill='#F4EAD6', edge='#06081A', fname='corm_i', stroke=6, zh_gap=72)
    return f.a


def s61_morningwalk(t, sh):
    u = t - bar(60)
    scroll = u * 520
    f = Frame('paper')
    hz = 640
    rd.sky(f, 'dawn', hz)
    rd.sun(f, 'dawn', x=420, y=380, r=70, glow_r=600)
    layer = rd.clouds_layer('dawn', hz, seed=91, specs=[(91, 1100, 1300, 460, 3)])
    rd.put_layer(f, layer, dx=-u * 10)
    side.far_mountains(f, hz, scroll * 0.05, color='#C9C6E6', height=70, seed=4, cov=0.4, shade='#8E98D8')
    side.tree_line(f, hz + 20, scroll * 0.2, color='#55805A', dark='#37604A')
    side.paddies(f, hz + 18, 1080, scroll * 0.6, tod='dawn', t=t)
    with Mask() as (c, m):
        people.boy_walk(c, 900, 1000, 420, u * 6.6)
    f.over('#22204F', m.cov)
    side.poles_side(f, scroll * 1.5, y_ground=1120, spacing=900, height=1050, color='#22204F')
    lyrics.draw_h(f, t, 61, x=960, y=180, size=80, **EN)
    return f.a


def s62_crane(t, sh):
    u = lin(t, bar(61), bar(62))
    k = ease_io(u, 2)
    cam = land.Cam(f=1300, x=0.0, h=lerp(1.6, 9.0, k), z=120 + u * 4, horizon=lerp(560, 420, k))
    zb = cam.z + 18 + u * 4

    def fig(f):
        x, y = cam.proj(0.3, 0, zb)
        hh = cam.scale(zb) * 1.7
        with Mask() as (c, m):
            people.boy_back(c, x, y, hh)
        f.over('#22204F', m.cov)

    f = Frame('paper')
    rd.world(f, t, cam, tod='dawn', figure=fig, haze=3.5, mirage=1.0, seed=31,
             specs=[(31, 700, 1300, 420, 2), (32, 1600, 520, 300, 1)], poles=(1,), cloud_dy=0)
    lyrics.draw_h(f, t, 62, x=960, y=900, size=84, **EN)
    return f.a


def s63_mirror(t, sh):
    both = 1.0 - smooth(lin(t, bar(63) + 1.0, bar(64) - 0.5))
    f = mirror_shot(t, bar(62), bar(64), tod='dawn', both=both, zoom0=1.2, zoom1=2.6, lyric=None)
    lyrics.draw_h(f, t, 63, x=760, y=930, size=72, fill='#FFFDF6', edge='#3B3C7A', fname='corm_i', stroke=6, zh_gap=64)
    lyrics.draw_h(f, t, 64, x=760, y=930, size=72, fill='#FFFDF6', edge='#3B3C7A', fname='corm_i', stroke=6, zh_gap=64)
    return f.a


def s64_title(t, sh):
    u = lin(t, bar(64), DURATION)
    f = Frame('paper')
    hz = 780
    rd.sky(f, 'noon', hz)
    rd.sun(f, 'noon', x=1520, y=150, amt=1.0)
    layer = rd.clouds_layer('noon', hz, seed=11, specs=[(11, 820, 1200, 640, 3), (5, 1600, 420, 280, 1)])
    rd.put_layer(f, layer, dx=-u * 30)
    ys, xs = core.coords()
    g = np.clip((ys - hz) * core.S + 0.5, 0, 1).astype(np.float32)
    gf = np.clip((ys - hz) / (1080 - hz), 0, 1).astype(np.float32) ** 0.6
    f.image(core.ramp(gf, rd.TOD['noon']['ground'], cell=7, angle=15), g)
    # title
    k = ease_out(lin(t, bar(64) + 0.2, bar(64) + 1.6), 3)
    gl, _ = text.layout_h('HEAT WAVES', 960, 500, 190, 'dela', tracking=0.04, align='center')
    fc, sc = text.render_glyphs(gl, stroke=18, anim=lambda g: dict(alpha=k, dy=(1 - k) * 30))
    if fc is not None:
        amp = lerp(10, 0.5, ease_io(u, 2))
        fc = core.heat_haze(fc, t, amp=amp, wavelength=40)
        sc = core.heat_haze(sc, t, amp=amp, wavelength=40)
        sh_ = np.roll(np.roll(sc, int(8 * core.S), 1), int(9 * core.S), 0)
        f.over('#141B3D', halftone(sh_, cell=5), alpha=0.7)
        f.over('#141B3D', sc)
        f.over('#FFFDF6', fc)
    k2 = ease_out(lin(t, bar(64) + 1.0, bar(64) + 2.4), 3)
    gl2, _ = text.layout_h('陽炎の向こうの君', 960, 650, 64, 'mincho', tracking=0.3, align='center')
    fc2, sc2 = text.render_glyphs(gl2, stroke=7, anim=lambda g: dict(alpha=k2))
    if fc2 is not None:
        f.over('#141B3D', sc2)
        f.over('#FFFDF6', fc2)
    k3 = ease_out(lin(t, bar(64) + 2.0, bar(64) + 3.2), 3)
    credits = ['Glass Animals「Heat Waves」 Japanese Version — Lime', 'fan-made music video  ·  非公式ファンメイド']
    for i, line in enumerate(credits):
        gl3, _ = text.layout_h(line, 960, 900 + i * 50, 30, 'mincho_sb', tracking=0.08, align='center')
        fc3, sc3 = text.render_glyphs(gl3, stroke=4, anim=lambda g: dict(alpha=k3))
        if fc3 is not None:
            f.over('#141B3D', sc3, alpha=0.8)
            f.over('#FFFDF6', fc3)
    lyrics.draw_h(f, t, 65, x=960, y=780, size=46, fill='#FFFDF6', edge='#141B3D', fname='corm_i', stroke=5, zh=False)
    lyrics.draw_h(f, t, 66, x=960, y=780, size=46, fill='#FFFDF6', edge='#141B3D', fname='corm_i', stroke=5, zh=False)
    f.a = core.heat_haze(f.a, t, amp=lerp(4, 0.0, ease_io(u, 2)), wavelength=30)
    # fade out
    fo = smooth(lin(t, DURATION - 1.4, DURATION - 0.2))
    f.a = core.flash(f.a, fo, '#06081A')
    return f.a


def shots():
    return [
        (Shot('s55_sunrise', bar(54), bar(55), s55_sunrise), Tr('cut')),
        (Shot('s56_calendar', bar(55), bar(56), s56_calendar), Tr('flash', 0.3)),
        (Shot('s57_ghosts', bar(56), bar(57), s57_ghosts), Tr('heat', 0.5)),
        (Shot('s58_burn', bar(57), bar(58), s58_burn), Tr('white', 0.4)),
        (Shot('s59_wall', bar(58), bar(59), s59_wall), Tr('crt', 0.4)),
        (Shot('s60_off', bar(59), bar(60), s60_off), Tr('dissolve', 0.5)),
        (Shot('s61_morningwalk', bar(60), bar(61), s61_morningwalk), Tr('dots', 0.5, grow='right', cell=24)),
        (Shot('s62_crane', bar(61), bar(62), s62_crane), Tr('dissolve', 0.6)),
        (Shot('s63_mirror', bar(62), bar(64), s63_mirror), Tr('dots', 0.8, grow='radial', cell=26)),
        (Shot('s64_title', bar(64), DURATION + 0.5, s64_title), Tr('cut')),
    ]

"""Verse 52.54 – 76.24 s: TV on, channel surfing, a Hollywood movie that is us,
the level crossing, the mirage spreading, darkness."""
import math
import os

import cv2
import numpy as np
import skia

from .. import core, lyrics, text
from ..core import Frame, View, Mask, Layer, P, paint, path, clamp, smooth, ease_io, ease_out, ease_in, lin, halftone
from ..edit import Shot, Tr
from ..el import road as rd, land, sprite, fx, room, tv, channels, night, people, summer
from ..timing import bar, BEAT, beat_pulse, beat_index
from .common import lerp
from .intro import TV_ZOOM


def has(name):
    return os.path.exists(os.path.join(sprite.ASSET_DIR, name + '.png'))


def _crt(img_lowres, t, **kw):
    return tv.crt(tv.upscale_nearest(img_lowres), t, curve=0.07, glow=0.5, roll=0.2, **kw)


def s18_tvon(t, sh):
    t_click = bar(17) + 0.55
    p = lin(t, t_click, t_click + 0.55)
    content = _crt(tv.lowres(lambda tt: channels.colour_bars(tt), t), t)
    content = tv.power_on(content, p) if p < 1 else content
    u = lin(t, bar(17), bar(18))
    v = View(1.25 + 0.25 * ease_io(u, 2), 1220, 640)
    f = Frame('night')
    room.room(f, t, v, tv_content=content if p > 0 else None, tv_on=smooth(p), clock_text=' 0:03')
    # the click: a quick white pop at the screen
    if 0 < p < 0.4:
        f.add('#FFFDF6', core.radial(*room.TV_CENTER, 300 * (1 - p), 2.0, view=v), alpha=1 - p / 0.4)
    lyrics.draw_v(f, t, 18, x=360, y=110, size=78, fill='#F4EAD6', edge='#06081A', zh_color='#7FE3DE')
    return f.a


CH = [('CH 1', channels.colour_bars), ('CH 3', channels.weather), ('CH 6', channels.baseball),
      ('CH 8', lambda tt: channels.hollywood(tt))]


def s19_surf(t, sh):
    b = beat_index(t) - beat_index(bar(18))
    k = int(max(0, b)) % len(CH)
    frac = b - int(b)
    label, fn = CH[k]
    img = tv.lowres(fn, t)
    content = _crt(img, t)
    f = Frame('night')
    v = View(2.25, 1470, 600)
    room.room(f, t, v, tv_content=content, clock_text=' 0:03')
    if frac < 0.18:
        st = tv.crt(tv.upscale_nearest(tv.static(t)), t, curve=0.07)
        quad = [v.pt(*q) for q in room.TV_QUAD]
        tv.place_screen(f, st, quad)
    # OSD channel number on the TV
    channels.osd(f, label, x=v.pt(1610, 500)[0], y=v.pt(1610, 500)[1], size=70)
    lyrics.draw_v(f, t, 19, x=330, y=110, size=78, fill='#F4EAD6', edge='#06081A', zh_color='#7FE3DE')
    return f.a


def _movie(t, couple):
    img = tv.lowres(lambda tt: channels.hollywood(tt, couple), t, 320, 180)
    return img


def s20_hollywood(t, sh):
    u = lin(t, bar(19), bar(20))
    f = Frame('black')
    f.a = _crt(_movie(t, 0.0), t, chroma=2.0)
    channels.osd(f, 'ロードショー', x=1780, y=120, size=64, color='#FFCB45')
    lyrics.draw_h(f, t, 20, x=960, y=992, size=54, fill='#FFFDF6', edge='black', zh_gap=56)
    return f.a


def s21_projection(t, sh):
    u = lin(t, bar(20), bar(21))
    # the movie couple becomes us: cross-fade to the dithered memory, then pull back
    mem = 'two_bicycle' if has('two_bicycle') else 'kimi_portrait'

    def memory(tt):
        L = sprite.scene(mem, zoom=1.0)
        fr = Frame('paper')
        sprite.put(fr, L)
        return fr.a
    k = smooth(lin(u, 0.05, 0.4))
    a = _movie(t, 1.0)
    b = tv.lowres(memory, t, 320, 180)
    rng = np.random.default_rng(int(t * 30))
    mix = np.where((rng.random(a.shape[:2]) < k)[..., None], b, a)
    content = _crt(mix, t)
    pk = ease_io(lin(u, 0.45, 1.0), 3)
    zoom = math.exp(lerp(math.log(TV_ZOOM), math.log(1.15), pk))
    v = View(zoom, lerp(room.TV_CENTER[0], 1080, pk), lerp(room.TV_CENTER[1], 600, pk))
    f = Frame('night')
    room.room(f, t, v, tv_content=content, clock_text=' 0:04')
    lyrics.draw_v(f, t, 21, x=360, y=110, size=78, fill='#F4EAD6', edge='#06081A', zh_color='#7FE3DE')
    return f.a


def s22_happy(t, sh):
    u = lin(t, bar(21), bar(22))
    f = Frame('paper')
    ys, xs = core.coords()
    field = np.clip(1 - ys / 1080, 0, 1).astype(np.float32)
    f.a[:] = core.ramp(field, ['#FFF6E2', '#FFE7A3', '#FFCB45', '#FF9A74'], cell=9, angle=45)
    g = core.radial(1250, 360, 900, falloff=1.2)
    f.over('#FFFBEA', halftone(g, cell=10, angle=30))
    name = 'kimi_laugh_cutout' if has('kimi_laugh_cutout') else ('kimi_back' if has('kimi_back') else None)
    if name:
        sprite.place(f, name, 1180, 640 + 10 * math.sin(t * 1.5), 1250 + 40 * u, t=t, wind=7, rim_color='#FFFBEA',
                     rim_amt=1.0, rim_dir=(-7, 5), shade_ink='#FF9A74', light_k=0.5)
    fx.petals(f, t, n=24, seed=4, colors=('#FFFDF6', '#FFE7A3'), wind=(200, -40), size=(6, 12))
    # his reflection on the TV glass laid over everything
    with Mask() as (c, m):
        people.boy_back(c, 520, 1150, 900)
    f.over('#141B3D', core.blur(m.cov, 3), alpha=0.28)
    # scanlines: we are still looking at a screen
    f.mul('#B9C3EA', core.linescreen(np.full((core.H, core.W), 0.35, np.float32), period=4), alpha=0.35)
    lyrics.draw_v(f, t, 22, x=420, y=110, size=82, fill='#FFFDF6', edge='#B8457A', zh_color='#FFFDF6')
    return f.a


def s23_crossing(t, sh):
    u = lin(t, bar(22), bar(23))
    v = View(1.0 + 0.05 * u, 960, 540)
    f = Frame('night')
    night.sky(f, v, horizon=640, moon=None, t=t)
    night.far_town(f, v, ground=640, seed=8)
    night.street_lamp(f, v, t, x=1380, ground=690, height=440, moths=True)
    # her silhouette across the tracks under the lamp
    with Mask(v) as (c, m):
        people.girl_hat(c, 1230, 690, 260, wind=0.4, t=t)
    her = m.cov
    # ground + rails
    ys, xs = core.coords()
    gy = v.pt(0, 690)[1]
    f.over('#141B3D', np.clip((ys - gy) * core.S + 0.5, 0, 1).astype(np.float32))
    summer.railway(f, 760, view=v, color='#3B4A8C')
    # train passing (lit windows streaming), strobing her in and out
    t_in, t_out = bar(22) + 0.3, bar(23) - 0.55
    train_on = t_in < t < t_out
    if train_on:
        x_off = (t - t_in) * 2600
        with Layer(view=v) as (c, L):
            for car in range(-1, 3):
                x0 = car * 1260 - (x_off % 1260)
                c.drawRect(skia.Rect.MakeXYWH(x0 + 6, 470, 1248, 280), paint('#1E2A5E'))
                for k in range(8):
                    c.drawRect(skia.Rect.MakeXYWH(x0 + 70 + k * 145, 520, 100, 90), paint('#FFE7A3'))
                c.drawRect(skia.Rect.MakeXYWH(x0 + 6, 690, 1248, 14), paint('#E8383D'))
        mb = core.motion_blur(L.rgb * L.alpha[..., None], 90, taps=7)
        ma = core.motion_blur(L.alpha[..., None].repeat(3, 2), 90, taps=7)[..., 0]
        gap = 1 - np.clip(ma, 0, 1)
        f.over('#F4EAD6', her * gap, alpha=0.9)
        f.image(mb / np.maximum(ma[..., None], 1e-3), ma)
    elif t <= t_in:
        f.over('#F4EAD6', her, alpha=0.9)
    # crossing: gates down, crossbuck, alternating red lamps (on the beat)
    blink = int(beat_index(t) * 2) % 2
    with Layer(view=v) as (c, L):
        for gx, sgn in ((520, 1), (1460, -1)):
            c.drawRect(skia.Rect.MakeLTRB(gx - 10, 560, gx + 10, 900), paint('#06081A'))
            c.drawLine(gx - 90, 600, gx + 90, 660, paint('#FFCB45', stroke=26))
            c.drawLine(gx - 90, 660, gx + 90, 600, paint('#FFCB45', stroke=26))
            for k, lx in enumerate((gx - 60, gx + 60)):
                on = (k == blink)
                c.drawCircle(lx, 720, 30, paint('#06081A'))
                c.drawCircle(lx, 720, 24, paint('#FF3B3B' if on else '#4A1828'))
            # gate arm
            c.drawLine(gx, 860, gx + sgn * 520, 860, paint('#FFCB45', stroke=18, cap='butt'))
            for k in range(6):
                xx = gx + sgn * (40 + k * 85)
                c.drawLine(xx, 860, xx + sgn * 42, 860, paint('#141B3D', stroke=18, cap='butt'))
    f.layer(L)
    for gx in (520, 1460):
        lx = gx - 60 if blink == 0 else gx + 60
        f.add('#FF3B3B', core.radial(lx, 720, 160, 2.0, view=v), alpha=0.6)
    # the boy in the foreground, from behind
    with Mask(v) as (c, m):
        people.boy_back(c, 760, 1180, 760)
    f.over('#06081A', m.cov)
    blinkcol = '#FF3B3B'
    import cv2
    M = np.float32([[1, 0, 0], [0, 1, 5 * core.S]])
    rim = np.clip(m.cov - cv2.warpAffine(m.cov, M, (core.W, core.H)), 0, 1)
    f.over(blinkcol, rim, alpha=0.5 + 0.5 * blink)
    lyrics.draw_v(f, t, 23, x=1770, y=110, size=80, fill='#F4EAD6', edge='#06081A', zh_color='#FF8A7A')
    return f.a


def s24_nigemizu(t, sh):
    u = lin(t, bar(23), bar(24))
    cam = land.Cam(f=2400, x=0.0, h=0.42, z=50 + u * 2.0, horizon=470)
    depth = lerp(40, 320, ease_io(u, 2))
    zk = cam.z + 60

    def fig(f):
        # only her reflection lives in the water — she herself is not there
        fx_, fy_ = cam.proj(0.4, 0, zk)
        hpx = cam.f * 1.62 / (zk - cam.z)
        L = sprite.warp('kimi_back', fx_, fy_, hpx, anchor=(0.5, 0.97), wind=4, t=t)
        L = sprite.shade_print(L, cell=5, shade_k=0.5, light_k=0.3)
        rgb, a = L['rgb'], L['a']
        ys, xs = core._grid()
        yl = fy_ * core.S
        my = (2 * yl - ys).astype(np.float32)
        mx = (xs + np.sin(ys / (4 * core.S) + t * 12) * 3.0 * core.S).astype(np.float32)
        rr = cv2.remap(rgb, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        ra = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        fade = np.clip(1 - (ys - yl) / (hpx * core.S * 0.9), 0, 1) * (ys > yl)
        f.image(rr, ra * fade * 0.75 * smooth(lin(u, 0.15, 0.5)))

    f = Frame('paper')
    rd.world(f, t, cam, tod='noon', mirage=1.0, mirage_depth=depth, haze=5.5, figure=fig, seed=71,
             specs=[(71, 760, 1500, 440, 3)], poles=(1, -1), pole_X=4.4, sun_amt=0.0)
    lyrics.draw_v(f, t, 24, x=1770, y=110, size=82, haze=2.0)
    return f.a


def s25_dark(t, sh):
    u = lin(t, bar(24), bar(25))
    cam = land.Cam(f=1300, x=0.0, h=1.5, z=80, horizon=600)
    f = Frame('night')
    rd.world(f, t, cam, tod='night', clouds=False, mirage=0.0, haze=1.2, glare=0.0, hills=True, poles=(1,))
    # the boy alone, small, under a single lamp that dies
    with Mask() as (c, m):
        people.boy_back(c, 930, 960, 300)
    f.over('#06081A', m.cov)
    fx.fireflies(f, t, n=46, seed=5, area=(0, 420, 1920, 1080), alpha=smooth(lin(u, 0.05, 0.4)))
    # iris down to darkness, fireflies stay
    r = lerp(1300, 0, ease_in(lin(u, 0.35, 0.92), 2))
    ys, xs = core.coords()
    d = np.sqrt((xs - 930) ** 2 + (ys - 820) ** 2)
    m = np.clip((r - d) / 3 + 0.5, 0, 1)
    dark = core._col('#06081A')
    f.a = f.a * m[..., None] + dark * (1 - m[..., None])
    fx.fireflies(f, t, n=30, seed=9, area=(0, 200, 1920, 1080), alpha=smooth(lin(u, 0.5, 0.9)))
    lyrics.draw_v(f, t, 25, x=1770, y=110, size=80, fill='#F4EAD6', edge='#06081A', zh_color='#D9F27A')
    return f.a


def shots():
    return [
        (Shot('s18_tvon', bar(17), bar(18), s18_tvon), Tr('cut')),
        (Shot('s19_surf', bar(18), bar(19), s19_surf), Tr('crt', 0.4)),
        (Shot('s20_hollywood', bar(19), bar(20), s20_hollywood), Tr('cut')),
        (Shot('s21_projection', bar(20), bar(21), s21_projection), Tr('flash', 0.4)),
        (Shot('s22_happy', bar(21), bar(22), s22_happy), Tr('dots', 0.5, grow='left', cell=24)),
        (Shot('s23_crossing', bar(22), bar(23), s23_crossing), Tr('heat', 0.6)),
        (Shot('s24_nigemizu', bar(23), bar(24), s24_nigemizu), Tr('dissolve', 0.6)),
        (Shot('s25_dark', bar(24), bar(25), s25_dark), Tr('cut')),
    ]

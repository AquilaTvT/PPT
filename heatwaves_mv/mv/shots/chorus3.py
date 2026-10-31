"""Chorus 3 — climax — 111.80 – 135.51 s"""
import math
import os

import cv2
import numpy as np
import skia

from .. import core, lyrics, text
from ..core import Frame, View, Mask, Layer, P, paint, path, clamp, smooth, ease_io, ease_out, ease_in, lin, halftone
from ..edit import Shot, Tr
from ..el import road as rd, land, sprite, fx, room, tv, fest, people, mirror, night
from ..timing import bar, BEAT, beat_pulse, beat_index
from .common import lerp

_still = {}


def has(name):
    return os.path.exists(os.path.join(sprite.ASSET_DIR, name + '.png'))


def pick(*names):
    for n in names:
        if has(n):
            return n
    return names[-1]


def still(key, fn, w=320, h=180):
    """cached dithered thumbnail for the CRT wall"""
    k = (key, w, h)
    if k not in _still:
        _still[k] = tv.lowres(lambda tt: fn(), 0.0, w, h)
    return _still[k]


def _asset_still(name, zoom=1.0, cx=0.5, cy=0.5):
    def fn():
        fr = Frame('paper')
        sprite.put(fr, sprite.scene(name, zoom=zoom, cx=cx, cy=cy))
        return fr.a
    return fn


def _road_still(tod='noon', seed=11):
    def fn():
        fr = Frame('paper')
        cam = land.Cam(f=1150, x=-0.9, h=1.55, z=60, horizon=560)
        rd.world(fr, 3.0, cam, tod=tod, haze=0, mirage=1.0, seed=seed)
        return fr.a
    return fn


def wall_items():
    items = [('portrait', _asset_still('kimi_portrait', 1.2, 0.62, 0.4)),
             ('road', _road_still('noon')),
             ('yukata', _asset_still('kimi_yukata', 1.3, 0.46, 0.4)),
             ('sunset', _road_still('sunset', 21)),
             ('fw', _asset_still(pick('kimi_fireworks_profile', 'kimi_yukata'), 1.1, 0.5, 0.4)),
             ('back', _asset_still('kimi_portrait', 2.2, 0.68, 0.33)),
             ('dawn', _road_still('dawn', 31))]
    for extra in ('kimi_busstop', 'kimi_platform', 'kimi_sleep_train', 'two_bicycle', 'kimi_crying'):
        if has(extra):
            items.append((extra, _asset_still(extra, 1.05)))
    return items


def crt_wall(f, t, v, cols=5, rows=3, seed=0, static_rate=0.25, tint=None):
    items = wall_items()
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(items) * 4) % len(items)
    cw, chh = 420, 330
    x0 = 960 - cols * cw / 2
    y0 = 540 - rows * chh / 2
    b = int(beat_index(t) * 2)
    with Layer(view=v) as (c, L):
        for r in range(rows):
            for k in range(cols):
                x, y = x0 + k * cw, y0 + r * chh
                c.drawRoundRect(skia.Rect.MakeXYWH(x + 8, y + 8, cw - 16, chh - 16), 22, 22, paint('#1E2A5E'))
                c.drawRoundRect(skia.Rect.MakeXYWH(x + 26, y + 26, cw - 52, chh - 80), 26, 26, paint('#0B1030'))
                c.drawCircle(x + cw - 50, y + chh - 34, 6, paint('#E8383D'))
    f.layer(L)
    for r in range(rows):
        for k in range(cols):
            x, y = x0 + k * cw, y0 + r * chh
            idx = order[(r * cols + k) % len(order)]
            key, fn = items[idx]
            hsh = core.hash01(r, k, b)
            if hsh < static_rate:
                img = tv.static(t + r + k, 160, 90)
            else:
                img = still(key, fn)
            img = tv.upscale_nearest(img, 640, 360)
            img = tv.crt(img, t, curve=0.1, scan=0.8, glow=0.4, vignette=0.6, noise=0.02, chroma=0)
            quad = [v.pt(x + 40, y + 40), v.pt(x + cw - 40, y + 40), v.pt(x + cw - 40, y + chh - 66),
                    v.pt(x + 40, y + chh - 66)]
            tv.place_screen(f, img, quad)
    # the wall glows into the room
    g = core.radial(960, 540, 1300, falloff=1.2, view=v)
    f.add('#2BB3B1', halftone(g * 0.3, cell=8), alpha=0.25)


def s38_wall(t, sh):
    u = lin(t, bar(37), bar(38))
    v = View(lerp(1.9, 1.0, ease_out(u, 2.5)), 960, 540)
    f = Frame('#06081A')
    crt_wall(f, t, v, cols=5, rows=3, seed=1)
    f.a = core.flash(f.a, 1 - ease_out(lin(t, bar(37), bar(37) + 0.6), 2), '#FFFDF6')
    lyrics.draw_v(f, t, 38, x=1060, y=120, size=110, fill='#FFFDF6', edge='#06081A', stroke=12, zh_color='#7FE3DE')
    return f.a


def s39_melt(t, sh):
    u = lin(t, bar(38), bar(39))
    f = Frame('#0B1030')
    night.sky(f, View(), horizon=1080, moon=(1500, 220, 90), t=t)
    from ..el.room import _FONT5x7
    txt = ' 0:00'
    size = 380
    cell = size / 7.0
    n = len(txt)
    wch = 5 * cell + 1.6 * cell
    x0 = 960 - (n * wch - 1.6 * cell) / 2
    melt = ease_in(lin(u, 0.2, 1.0), 1.6)
    with Mask() as (c, m), Mask() as (c2, m2):
        for i, ch in enumerate(txt):
            g = _FONT5x7.get(ch, _FONT5x7[' '])
            for r, row in enumerate(g):
                for k, bit in enumerate(row):
                    cx = x0 + i * wch + k * cell + cell / 2
                    cy = 560 - size / 2 + r * cell + cell / 2
                    if bit == '1':
                        h = core.hash01(i, r, k)
                        drop = max(0.0, melt * 1.6 - h * 0.8) ** 2 * 700 * (0.4 + h)
                        stretch = 1 + max(0.0, melt - h * 0.5) * 2.5
                        c.drawRoundRect(skia.Rect.MakeXYWH(cx - cell * 0.4, cy - cell * 0.4 + drop,
                                                           cell * 0.8, cell * 0.8 * stretch), cell * 0.35, cell * 0.35, P())
                    else:
                        c2.drawRoundRect(skia.Rect.MakeXYWH(cx - cell * 0.4, cy - cell * 0.4, cell * 0.8, cell * 0.8),
                                         cell * 0.3, cell * 0.3, P())
    f.over('#FF6A55', m2.cov, alpha=0.07)
    f.add('#FF6A55', core.blur(m.cov, 18), alpha=0.6)
    f.over('#FF6A55', m.cov)
    f.a = core.heat_haze(f.a, t, amp=3 + 10 * melt, wavelength=40)
    lyrics.draw_v(f, t, 39, x=1800, y=110, size=78, fill='#F4EAD6', edge='#06081A', zh_color='#FF8A7A')
    return f.a


def s40_chase(t, sh):
    u = t - bar(39)
    cam = land.Cam(f=1150, x=-0.4 + math.sin(u * 7) * 0.08, h=1.55 + abs(math.sin(u * 7)) * 0.06,
                   z=200 + u * 22, horizon=600, roll=math.sin(u * 3.5) * 1.2)
    zk = cam.z + 40          # she stays the same distance away, however fast he runs

    def fig(f):
        rd.kimi_far(f, cam, zk, X=0.4, t=t, haze=6.0, reflect=0.6, mul='#FF9A74', mul_amt=0.25)

    f = Frame('paper')
    rd.world(f, t, cam, tod='sunset', haze=6.5, mirage=1.0, mirage_depth=60, figure=fig, seed=21,
             specs=[(21, 1150, 1500, 480, 3)], poles=(1, -1), sun_amt=1.0, glare=0.5 + 0.5 * beat_pulse(t, 3.0))
    fx.speedlines(f, t, cx=960, cy=600, n=40, color='#FFE7B8', alpha=0.35, inner=500, length=700)
    lyrics.draw_v(f, t, 40, x=1770, y=110, size=84, fill='#FFF1D6', edge='#5B2E6B', zh_color='#FFF1D6')
    return f.a


def s41_embers(t, sh):
    u = lin(t, bar(40), bar(41))
    f = Frame('paper')
    hz = 820
    rd.sky(f, 'sunset', hz)
    rd.sun(f, 'sunset', x=960, y=430, r=150, glow_r=800)
    ys, xs = core.coords()
    g = (ys > hz).astype(np.float32)
    f.over('#41275C', g)
    name = pick('kimi_front_cutout', 'kimi_back')
    L = sprite.warp(name, 960, 1060, 900, anchor=(0.5, 0.98), wind=5, t=t)
    L = sprite.shade_print(L, shade_ink='#7A2E6B', cell=6)
    L = sprite.grade(L, mul='#FF9A74', mul_amt=0.35)
    L = sprite.rim(L, '#FFE7B8', 1.0, dx=0, dy=6)
    k = smooth(lin(u, 0.2, 0.95))
    a = L['a']
    if k > 0:
        # she burns away bottom-up into rising dots
        front = lerp(1100, 100, k)
        prog = np.clip((ys - front) / 120.0 + 0.5, 0, 1)
        dots = halftone(np.clip(1 - prog, 0, 1), cell=8)
        a = a * dots
        with Mask() as (c, m):
            rng = np.random.default_rng(5)
            for i in range(160):
                bx = 960 + rng.normal(0, 140)
                by0 = rng.uniform(front - 50, 1060)
                by = by0 - (t - bar(40)) * rng.uniform(60, 240) * k
                c.drawCircle(bx + math.sin(t * 3 + i) * 10, by, rng.uniform(2, 5), P(alpha=rng.uniform(0.4, 1.0)))
        f.add('#FFCB45', core.blur(m.cov, 4), alpha=0.8)
        f.over('#FFE7B8', m.cov)
    f.image(L['rgb'], a)
    lyrics.draw_v(f, t, 41, x=1770, y=110, size=84, fill='#FFF1D6', edge='#5B2E6B', zh_color='#FFF1D6')
    return f.a


def s42_finale(t, sh):
    u = lin(t, bar(41), bar(42))
    f = Frame('night')
    v = View(1.0 + 0.05 * u, 960, 540)
    night.sky(f, v, horizon=800, moon=None, t=t)
    sched = fest.schedule(bar(41) - 1.2, bar(42) + 0.4, None, every=0.5, seed=23, area=(150, 100, 1770, 520))
    fest.sky_fireworks(f, t, sched, view=v)
    with Mask(v) as (c, m):
        c.drawPath(core.smooth_path([(-100, 1100), (-100, 860), (600, 820), (1300, 850), (2100, 820), (2100, 1100)],
                                    close=True), P())
    f.over('#06081A', m.cov)
    with Mask(v) as (c, m):
        people.sitting_pair(c, 960, 930, 560, t=t)
    f.over('#0B1030', m.cov)
    # fireworks light rims the two of them
    b = int(beat_index(t) * 2)
    col = fest.FW_COLS[b % len(fest.FW_COLS)][0]
    M = np.float32([[1, 0, 0], [0, 1, 6 * core.S]])
    rim = np.clip(m.cov - cv2.warpAffine(m.cov, M, (core.W, core.H)), 0, 1)
    f.over(col, rim, alpha=0.9)
    lyrics.draw_v(f, t, 42, x=1770, y=110, size=84, fill='#FFF3D6', edge='#141B3D', zh_color=col)
    return f.a


def s43_house_fw(t, sh):
    """the midnight house again — but memory-fireworks are bursting over it"""
    from .chorus1 import night_house
    u = lin(t, bar(42), bar(43))
    v = View(1.05 + 0.12 * ease_io(u, 2), 900, 520)
    f = Frame('night')
    night_house(f, t, v, glow=0.6 + 0.4 * beat_pulse(t, 4.0))
    sched = fest.schedule(bar(42) - 0.8, bar(43) + 0.3, None, every=0.5, seed=31, area=(200, 60, 1720, 360))
    fx_layer = Frame('night')
    fx_layer.a[:] = 0
    fest.sky_fireworks(f, t, sched, view=v, alpha=0.9)
    lyrics.draw_v(f, t, 43, x=1770, y=110, size=80, fill='#F4EAD6', edge='#06081A', zh_color='#FF5C9E')
    return f.a


def s44_kaleido(t, sh):
    u = t - bar(43)
    cam = land.Cam(f=1150, x=0.0, h=1.4, z=300 + u * 18, horizon=540)
    fr = Frame('paper')
    rd.world(fr, t, cam, tod='sunset', haze=4.0, mirage=1.0, seed=21, specs=[(21, 960, 1600, 460, 3)], poles=(1, -1))
    img = fr.a
    # four-way mirror around the centre, slowly rotating
    rot = u * 14
    img = core.affine(img, rot=rot, scale=1.25)
    left = img[:, : core.W // 2]
    top = np.concatenate([left, left[:, ::-1]], axis=1)
    if top.shape[1] < core.W:
        top = np.concatenate([top, top[:, -1:]], axis=1)
    half = top[: core.H // 2]
    full = np.concatenate([half, half[::-1]], axis=0)
    if full.shape[0] < core.H:
        full = np.concatenate([full, full[-1:]], axis=0)
    f = Frame('paper')
    f.a = core.heat_haze(full, t, amp=5, wavelength=40)
    lyrics.draw_v(f, t, 44, x=1770, y=110, size=84, fill='#FFF1D6', edge='#5B2E6B', zh_color='#FFF1D6')
    return f.a


def _mirror_alone(t, n=420, tod='sunset', both=0.0):
    def scene():
        fr = Frame('paper')
        cam = land.Cam(f=900, x=0.3, h=1.6, z=10, horizon=300)

        def fig(ff):
            with Mask() as (c, m):
                x, y = cam.proj(-0.2, 0, cam.z + 9)
                hh = cam.f * 1.7 / 9
                people.boy_back(c, x, y, hh)
                if both > 0:
                    x2, y2 = cam.proj(0.6, 0, cam.z + 9.5)
                    people.girl_hat(c, x2, y2, cam.f * 1.6 / 9.5, t=t)
            ff.over(rd.TOD[tod]['pole'], m.cov)
        rd.world(fr, t, cam, tod=tod, mirage=0.6, mirage_depth=20, haze=2.5, figure=fig, seed=41,
                 specs=[(41, 900, 1300, 280, 2)], poles=(-1,), hills=True, sun_amt=0.6)
        return fr.a
    with core.resolution(n * 16 // 9, n):
        img = scene()
    return mirror.fisheye(img, n=n, k=1.15)


def mirror_shot(t, t0, t1, tod='sunset', both=0.0, zoom0=1.3, zoom1=2.2, lyric=None, fill='#FFF1D6',
                edge='#5B2E6B'):
    u = lin(t, t0, t1)
    mcx, mcy, mr = 1180, 380, 200
    v = View(lerp(zoom0, zoom1, ease_io(u, 2)), lerp(1060, mcx, ease_io(u, 2)), lerp(560, mcy, ease_io(u, 2)))
    f = Frame('paper')
    hz = 650
    rd.sky(f, tod, hz)
    rd.sun(f, tod)
    layer = rd.clouds_layer(tod, hz, seed=11)
    p0 = v.pt(960, hz)
    rd.put_layer(f, layer, scale=v.zoom ** 0.5, cx=p0[0], cy=p0[1], dy=p0[1] - hz)
    ys, xs = core.coords()
    gy = v.pt(0, hz)[1]
    gm = np.clip((ys - gy) * core.S + 0.5, 0, 1).astype(np.float32)
    gf = np.clip((ys - gy) / max(1, 1080 - gy), 0, 1).astype(np.float32) ** 0.6
    f.image(core.ramp(gf, rd.TOD[tod]['ground'], cell=7, angle=15), gm)
    refl = _mirror_alone(t, tod=tod, both=both)
    mirror.curve_mirror(f, v, mcx, mcy, mr, refl, t, wobble=3.0)
    if lyric is not None:
        for idx in (lyric if isinstance(lyric, (list, tuple)) else [lyric]):
            lyrics.draw_v(f, t, idx, x=1770, y=110, size=82, fill=fill, edge=edge, zh_color=fill)
    reg = np.exp(-((ys - gy) / 90.0) ** 2).astype(np.float32)
    f.a = core.heat_haze(f.a, t, amp=3.0, wavelength=30, region=reg)
    return f


def s45_mirror(t, sh):
    f = mirror_shot(t, bar(44), bar(45), tod='sunset', both=0.0, lyric=45)
    f.a = core.flash(f.a, ease_in(lin(t, bar(45) - 0.6, bar(45)), 2) * 0.85, '#141B3D')
    return f.a


def shots():
    return [
        (Shot('s38_wall', bar(37), bar(38), s38_wall), Tr('crt', 0.4)),
        (Shot('s39_melt', bar(38), bar(39), s39_melt), Tr('flash', 0.3)),
        (Shot('s40_chase', bar(39), bar(40), s40_chase), Tr('heat', 0.5)),
        (Shot('s41_embers', bar(40), bar(41), s41_embers), Tr('dots', 0.45, grow='up', cell=26)),
        (Shot('s42_finale', bar(41), bar(42), s42_finale), Tr('whip', 0.36, direction=-1)),
        (Shot('s43_house_fw', bar(42), bar(43), s43_house_fw), Tr('flash', 0.3)),
        (Shot('s44_kaleido', bar(43), bar(44), s44_kaleido), Tr('heat', 0.5)),
        (Shot('s45_mirror', bar(44), bar(45), s45_mirror), Tr('cut')),
    ]

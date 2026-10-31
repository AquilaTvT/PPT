"""Hook 16.98 – 28.83 s: 光りだすロード / 揺らいでくビジョン / 熱波ゆらり 泳いでくミラー"""
import math

import numpy as np

from .. import core, lyrics
from ..core import Frame, View, clamp, smooth, ease_io, ease_out, ease_in, lin
from ..edit import Shot, Tr
from ..el import road as rd, land, side, mirror, sprite, cloud
from ..timing import bar, BEAT, beat_pulse
from .common import lerp


def s06_road(t, sh):
    u = t - bar(5)
    # surge forward on the drop, settle into a steady glide
    z = 120 + 26 * u - 14 * (1 - math.exp(-u * 1.5))
    sway = math.sin(u * 1.3) * 0.25
    cam = land.Cam(f=1100, x=-0.9 + sway, h=1.45 + 0.05 * math.sin(u * 2.6), z=z, horizon=590,
                   roll=math.sin(u * 0.9) * 0.6)
    f = Frame('paper')
    glare = 0.35 + 0.65 * beat_pulse(t, decay=3.0)
    rd.world(f, t, cam, tod='noon', glare=glare, haze=4.5, mirage=1.0, cloud_dx=-u * 4)
    lyrics.draw_v(f, t, 4, x=1770, y=96, size=84, hold_to=bar(6) - 0.05)
    lyrics.draw_v(f, t, 5, x=1560, y=196, size=84)
    # drop impact: flash fades out
    f.a = core.flash(f.a, 1 - ease_out(lin(t, bar(5), bar(5) + 0.5), 2), '#FFFBEA')
    return f.a


def s07_mirage(t, sh):
    u = t - bar(6)
    cam = land.Cam(f=5200, x=-0.4, h=0.55, z=40 + u * 1.2, horizon=520)
    zk = cam.z + 72

    def fig(f):
        rd.kimi_far(f, cam, zk, X=0.5, t=t, haze=5.0, reflect=0.6)

    f = Frame('paper')
    specs = [(21, 820, 1500, 620, 3)]
    rd.world(f, t, cam, tod='noon', mirage=1.0, mirage_depth=120, haze=6.5, figure=fig, specs=specs, seed=21,
             poles=(1, -1), pole_X=5.2, hills=False, sun_amt=0.0,
             haze_region=None)
    lyrics.draw_v(f, t, 6, x=1760, y=120, size=78, haze=2.5)
    return f.a


def s08_side(t, sh):
    u = t - bar(7)
    x_off = u * 900 + 300
    f = Frame('paper')
    hz = 640
    rd.sky(f, 'noon', hz)
    rd.sun(f, 'noon', x=1600, y=150, amt=1.0)
    layer = rd.clouds_layer('noon', hz, seed=31, specs=[(31, 700, 1300, 560, 3), (25, 1650, 520, 330, 1)])
    rd.put_layer(f, layer, dx=-u * 12)
    side.far_mountains(f, hz, x_off * 0.04, color='#B9D6F0', height=70, seed=2, cov=0.45)
    side.tree_line(f, hz + 26, x_off * 0.15)
    side.paddies(f, hz + 24, 1080, x_off * 0.6, t=t)
    side.poles_side(f, x_off * 1.6, y_ground=1120, spacing=820, height=1060)
    lyrics.draw_v(f, t, 7, x=1770, y=96, size=80, hold_to=bar(8) - 0.05)
    lyrics.draw_v(f, t, 8, x=1570, y=196, size=80)
    return f.a


def _mirror_reflection(t, n=420):
    """render the road behind us small, then bend it into a convex mirror"""
    def scene():
        f = Frame('paper')
        cam = land.Cam(f=900, x=0.3, h=1.6, z=10 + (t - bar(8)) * 0.8, horizon=300)
        zk = cam.z + 12

        def fig(ff):
            rd.kimi_far(ff, cam, zk, X=-0.4, t=t, haze=2.0, reflect=0.3, wind=4)
        rd.world(f, t, cam, tod='noon', mirage=0.6, mirage_depth=20, haze=2.5, figure=fig, seed=41,
                 specs=[(41, 900, 1300, 280, 2)], poles=(-1,), hills=True, sun_amt=0.6)
        return f.a
    with core.resolution(n * 16 // 9, n):
        img = scene()
    return mirror.fisheye(img, n=n, k=1.15)


def s09_curvemirror(t, sh):
    u = lin(t, bar(8), bar(9))
    k = ease_in(u, 2.2)
    zoom = math.exp(lerp(math.log(1.0), math.log(4.6), k))
    mcx, mcy, mr = 1250, 360, 190
    v = View(zoom, lerp(1060, mcx, ease_io(u, 2)), lerp(560, mcy, ease_io(u, 2)))
    f = Frame('paper')
    # background: junction, paddies, clouds (drawn through the view)
    hz = 640
    rd.sky(f, 'noon', hz)
    layer = rd.clouds_layer('noon', hz, seed=11)
    rd.put_layer(f, layer, scale=zoom ** 0.5, cx=v.pt(960, hz)[0], cy=v.pt(960, hz)[1],
                 dy=(v.pt(960, hz)[1] - hz))
    # flat junction ground under the view
    ys, xs = core.coords()
    gy = v.pt(0, hz)[1]
    gmask = np.clip((ys - gy) * core.S + 0.5, 0, 1).astype(np.float32)
    gf = np.clip((ys - gy) / max(1, 1080 - gy), 0, 1).astype(np.float32) ** 0.6
    f.image(core.ramp(gf, rd.TOD['noon']['ground'], cell=7, angle=15), gmask)
    # cross road band
    with core.Mask(v) as (c, m):
        c.drawPath(core.path([(-2000, 700), (4000, 700), (4000, 790), (-2000, 790)]), core.P())
    f.over('#6B739B', m.cov)
    with core.Mask(v) as (c, m):
        c.drawLine(-2000, 745, 4000, 745, core.P(stroke=4))
    f.over('#FFFDF6', m.cov)
    refl = _mirror_reflection(t)
    mirror.curve_mirror(f, v, mcx, mcy, mr, refl, t, wobble=3.0 + 4 * u)
    if u < 0.75:
        a = 1 - lin(u, 0.6, 0.75)
        lyrics.draw_v(f, t, 9, x=1770, y=110, size=80, haze=2.0, alpha=a)
    ys, xs = core.coords()
    reg = np.exp(-((ys - v.pt(0, 640)[1]) / 90.0) ** 2).astype(np.float32)
    f.a = core.heat_haze(f.a, t, amp=3.0, wavelength=30, region=reg)
    return f.a


def shots():
    return [
        (Shot('s06_road', bar(5), bar(6), s06_road), Tr('heat', 0.5)),
        (Shot('s07_mirage', bar(6), bar(7), s07_mirage), Tr('whip', 0.36, direction=1)),
        (Shot('s08_side', bar(7), bar(8), s08_side), Tr('dots', 0.5, grow='right', cell=26)),
        (Shot('s09_curvemirror', bar(8), bar(9), s09_curvemirror), Tr('flash', 0.3)),
    ]

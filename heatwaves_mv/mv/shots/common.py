"""Helpers shared by shot modules."""
import math

import numpy as np

from .. import core, lyrics
from ..core import Frame, View, clamp, smooth, ease_io, ease_out, ease_in, lin
from ..timing import bar, BEAT, BAR, beat_pulse, beat_phase


def tv_pixel_road(t, z0=60.0, speed=7.0, tod='noon', w=320, h=180, figure_z=None):
    """the summer road rendered tiny and dithered (what the TV shows)"""
    from ..el import road as rd, land, tv

    def scene(tt):
        f = Frame('paper')
        cam = land.Cam(f=1150, x=-0.9, h=1.55, z=z0 + speed * tt, horizon=560)
        rd.world(f, tt, cam, tod=tod, haze=2.0, mirage=1.0, seed=11)
        return f.a
    return tv.lowres(scene, t, w, h)


def crt_full(content_lowres, t, **kw):
    from ..el import tv
    img = tv.upscale_nearest(content_lowres)
    return tv.crt(img, t, **kw)


def lerp(a, b, k):
    return a + (b - a) * k

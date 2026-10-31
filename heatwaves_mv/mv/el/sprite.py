"""Stylised character / scene images placed in screen space.

Assets come from tools/stylize.py: <name>.png (flat colours + lines, RGBA) and
<name>_sl.png (G = light, R = shade).  Shading is turned into halftone *after*
the image is transformed, so its dot screen always matches the backgrounds.
"""
import functools
import math
import os

import cv2
import numpy as np

from .. import core

ASSET_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'chars')


@functools.lru_cache(maxsize=48)
def load(name):
    p = os.path.join(ASSET_DIR, name + '.png')
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(p)
    im = im.astype(np.float32) / 255.0
    rgb = im[..., :3][..., ::-1].copy()
    a = im[..., 3].copy() if im.shape[2] == 4 else np.ones(im.shape[:2], np.float32)
    slp = p.replace('.png', '_sl.png')
    if os.path.exists(slp):
        sl = cv2.imread(slp, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
        shade, light = sl[..., 2].copy(), sl[..., 1].copy()
    else:
        shade = np.zeros(a.shape, np.float32)
        light = np.zeros(a.shape, np.float32)
    # premultiply for clean resampling
    pack = np.dstack([rgb * a[..., None], a, shade * a, light * a]).astype(np.float32)
    return pack


def size(name):
    p = load(name)
    return p.shape[1], p.shape[0]


def _matrix(name, cx, cy, height, rot=0.0, flip=False, anchor=(0.5, 0.5)):
    w, h = size(name)
    s = height * core.S / h
    ax, ay = anchor
    # source anchor -> dest (cx, cy)
    M = cv2.getRotationMatrix2D((ax * w, ay * h), rot, s)
    if flip:
        F = np.float32([[-1, 0, w], [0, 1, 0], [0, 0, 1]])
        M = (np.vstack([M, [0, 0, 1]]) @ F)[:2]
    M[0, 2] += cx * core.S - ax * w
    M[1, 2] += cy * core.S - ay * h
    return M.astype(np.float32)


def warp(name, cx, cy, height, rot=0.0, flip=False, anchor=(0.5, 0.5), wind=0.0, t=0.0, wind_top=0.45,
         sway=0.0):
    """returns dict rgb, a, shade, light at output resolution"""
    pack = load(name)
    M = _matrix(name, cx, cy, height, rot, flip, anchor)
    o1 = cv2.warpAffine(pack[..., :4], M, (core.W, core.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                        borderValue=(0, 0, 0, 0))
    o2 = cv2.warpAffine(pack[..., 4:6], M, (core.W, core.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                        borderValue=(0, 0, 0, 0))
    out = np.dstack([o1, o2])
    if wind > 0 or sway:
        # displace the upper part (hair, hat, hem) with a travelling wave
        ys, xs = core._grid()
        top = cy * core.S - height * core.S * 0.5
        rel = np.clip(1 - (ys - top) / (height * core.S * wind_top), 0, 1)
        dx = (np.sin(ys / (40 * core.S) - t * 5.0) * wind + sway) * core.S * rel
        mx = xs - dx.astype(np.float32)
        out = np.dstack([cv2.remap(out[..., :4], mx, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT),
                         cv2.remap(out[..., 4:6], mx, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)])
    a = out[..., 3]
    inv = 1.0 / np.maximum(a, 1e-4)
    rgb = out[..., :3] * inv[..., None]
    return dict(rgb=np.clip(rgb, 0, 1), a=np.clip(a, 0, 1), shade=np.clip(out[..., 4] * inv, 0, 1),
                light=np.clip(out[..., 5] * inv, 0, 1))


def shade_print(L, shade_ink='#5D66B0', light_ink='white', cell=6.0, shade_k=0.6, light_k=0.4, angle=45):
    rgb = L['rgb']
    if shade_k > 0:
        ht = core.halftone(L['shade'], cell=cell, angle=angle) * shade_k
        ink = core._col(shade_ink)
        rgb = rgb * (1 - ht[..., None]) + rgb * ink * ht[..., None]
    if light_k > 0:
        hl = core.halftone(L['light'], cell=cell, angle=angle - 30) * light_k
        rgb = rgb + (core._col(light_ink) - rgb) * hl[..., None]
    L['rgb'] = rgb
    return L


def grade(L, mul=None, mul_amt=1.0, add=None, add_amt=0.0, sat=1.0, lift=None, lift_amt=0.0):
    rgb = L['rgb']
    if sat != 1.0:
        g = core.lum(rgb)[..., None]
        rgb = g + (rgb - g) * sat
    if mul is not None:
        m = core._col(mul)
        rgb = rgb * (1 - mul_amt + m * mul_amt)
    if lift is not None and lift_amt:
        rgb = rgb + (core._col(lift) - rgb) * lift_amt * (1 - core.lum(rgb))[..., None]
    if add is not None and add_amt:
        rgb = rgb + core._col(add) * add_amt
    L['rgb'] = np.clip(rgb, 0, 1)
    return L


def rim(L, color='sun', amount=1.0, dx=-6.0, dy=-4.0, width=1.0):
    """rim light on the edge facing the light (offset alpha difference)"""
    a = L['a']
    M = np.float32([[1, 0, dx * core.S * width], [0, 1, dy * core.S * width]])
    sh = cv2.warpAffine(a, M, (core.W, core.H))
    edge = np.clip(a - sh, 0, 1) * amount
    L['rgb'] = L['rgb'] + (core._col(color) - L['rgb']) * edge[..., None]
    return L


def put(f, L, opacity=1.0):
    f.image(L['rgb'], L['a'], opacity)


def drop_shadow(f, L, dx=18, dy=10, color='ink', opacity=0.35, blur=6, cell=5):
    a = L['a']
    M = np.float32([[1, 0, dx * core.S], [0, 1, dy * core.S]])
    sh = cv2.warpAffine(a, M, (core.W, core.H))
    if blur:
        sh = core.blur(sh, blur)
    f.over(color, core.halftone(sh, cell=cell, angle=45), alpha=opacity)


def place(f, name, cx, cy, height, t=0.0, rot=0.0, flip=False, anchor=(0.5, 0.5), wind=0.0, sway=0.0,
          shade_ink='#5D66B0', cell=6.0, shade_k=0.6, light_k=0.35, mul=None, mul_amt=1.0, rim_color=None,
          rim_amt=0.0, rim_dir=(-6, -4), opacity=1.0, shadow=None, sat=1.0, lift=None, lift_amt=0.0,
          add=None, add_amt=0.0, ret=False):
    L = warp(name, cx, cy, height, rot, flip, anchor, wind, t, sway=sway)
    L = shade_print(L, shade_ink, cell=cell, shade_k=shade_k, light_k=light_k)
    if mul is not None or sat != 1.0 or lift is not None or add is not None:
        L = grade(L, mul, mul_amt, add, add_amt, sat, lift, lift_amt)
    if rim_color is not None and rim_amt > 0:
        L = rim(L, rim_color, rim_amt, rim_dir[0], rim_dir[1])
    if shadow:
        drop_shadow(f, L, **shadow)
    if ret:
        return L
    put(f, L, opacity)
    return L


def has_layers(name):
    return os.path.exists(os.path.join(ASSET_DIR, name + '_fg.png'))


def scene_par(f, name, zoom=1.0, cx=0.5, cy=0.5, u=0.0, par=0.035, drift=(0.0, 0.0), t=0.0, wind=0.0,
              shade_ink='#5D66B0', cell=6.0, shade_k=0.6, light_k=0.35, fg_grade=None):
    """2.5D Ken Burns: background and the cut-out character move at different rates.

    u: shot progress 0..1. The foreground gets an extra push-in of `par` and its own drift.
    """
    if not has_layers(name):
        L = scene(name, zoom, cx, cy, t=t, shade_ink=shade_ink, cell=cell, shade_k=shade_k, light_k=light_k)
        put(f, L)
        return L
    w, h = size(name)
    cover = max(1920 / w, 1080 / h)
    k = u - 0.5
    zb = zoom * (1 - par * 0.35 * k)
    zf = zoom * (1 + par * k)
    Lb = scene(name + '_bg', zb, cx - drift[0] * 0.4 * k, cy - drift[1] * 0.4 * k, t=t, shade_ink=shade_ink,
               cell=cell, shade_k=shade_k, light_k=light_k)
    put(f, Lb)
    # foreground placed with the same framing maths, but its own zoom/drift (no cover clamp)
    wd, hd = w * cover * zf, h * cover * zf
    px = 960 - (cx + drift[0] * k - 0.5) * wd
    py = 540 - (cy + drift[1] * k - 0.5) * hd
    wb, hb = w * cover * zb, h * cover * zb
    pxb = min(max(960 - (cx - 0.5) * wb, 1920 - wb / 2 + 1), wb / 2 - 1)
    pyb = min(max(540 - (cy - 0.5) * hb, 1080 - hb / 2 + 1), hb / 2 - 1)
    px += pxb - (960 - (cx - 0.5) * wb)
    py += pyb - (540 - (cy - 0.5) * hb)
    Lf = warp(name + '_fg', px, py, hd, wind=wind, t=t)
    Lf = shade_print(Lf, shade_ink, cell=cell, shade_k=shade_k, light_k=light_k)
    if fg_grade:
        Lf = grade(Lf, **fg_grade)
    put(f, Lf)
    return Lf


def scene(name, zoom=1.0, cx=0.5, cy=0.5, rot=0.0, t=0.0, shade_ink='#5D66B0', cell=6.0, shade_k=0.6,
          light_k=0.35):
    """full-frame scene image with Ken-Burns framing; zoom=1 fits the frame (cover)"""
    w, h = size(name)
    cover = max(1920 / w, 1080 / h)
    height = h * cover * zoom
    wd, hd = w * cover * zoom, h * cover * zoom
    px = 960 - (cx - 0.5) * wd
    py = 540 - (cy - 0.5) * hd
    # keep the picture covering the frame
    px = min(max(px, 1920 - wd / 2 + 1), wd / 2 - 1)
    py = min(max(py, 1080 - hd / 2 + 1), hd / 2 - 1)
    L = warp(name, px, py, height, rot)
    L = shade_print(L, shade_ink, cell=cell, shade_k=shade_k, light_k=light_k)
    return L

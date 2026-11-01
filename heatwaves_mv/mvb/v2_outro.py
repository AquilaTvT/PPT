"""MV-B v2: devices for the dream and the morning.

  bridge2-04       the halftone shadow on her face is lifted off like a sheet of screentone: her face clean
  outro-02         the night's indigo print peels off the waking town, the dawn print underneath
  outro-08         the wind lifts the stamp card from beside him; it flies off like a kite toward the sun
  outro_hook-01    the card crosses the town from above while the light goes from dawn to noon
"""
import functools
import math

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import BEAT, BEAT0
from . import v2
from . import v2_fx as fx
from .print_fx import hexc as H

W, H_ = 1920, 1080
GRAPHIC = {}


def _dream(img, s, t, local):
    from .v2_shots import dream
    return dream(img, s, t, local)


# ------------------------------------------------------------------ two presses on one shot
_PR = {}


def printer2(s, key, world_from, raw_fn, **kw):
    """a second printer for shot s with another world's inks (fitted on the same raw frames)"""
    from .print2 import Printer
    from .chars import world_inks, SECTION_WORLD
    name = v2.b2_id(s) + '_' + key
    if name not in _PR:
        world = SECTION_WORLD.get(tl_section(world_from), '')
        args = dict(v2.WORLD_PRINT.get(world, {}))
        args.update(kw)
        pr = Printer(world_inks(world_from), name=name, **args)
        if pr.pal is None:
            d = s['end'] - s['start']
            pr.fit([raw_fn(s, s['start'] + d * f, d * f) for f in (0.15, 0.5, 0.85)])
        _PR[name] = pr
    return _PR[name]


def day_for_night(raw):
    """the night plate of the same view: darker, cooler, the sky deep indigo, sunlit surfaces fall to moonlight"""
    y = np.clip(raw @ np.float32([0.2126, 0.7152, 0.0722]), 0, 1)
    lum = 0.10 + 0.50 * y ** 1.35
    tint = np.float32([0.42, 0.52, 0.95])
    out = lum[..., None] * tint[None, None] + np.float32([0.02, 0.03, 0.08])[None, None]
    return np.clip(out, 0, 1)


def tl_section(sid):
    return v2.tl.BY_ID[sid]['section']


def _raw(s, t, local):
    return _dream(v2.plate(s, local), s, t, local)


def bridge2_04(s, t, local, fi):
    from .v2_print import peel
    raw = _raw(s, t, local)
    pr = v2.printer_for(s, _raw)
    p = clamp((t - 145.05) / 1.55)
    if p <= 0:
        return pr(raw)
    clean = pr(raw, stage={'dots': 0.0})
    if p >= 1:
        return clean
    top = pr(raw)
    return peel(top, clean, p, angle=-30.0, curl=150.0, mode='film')


def outro_02(s, t, local, fi):
    from .v2_print import peel
    raw = _raw(s, t, local)
    night = printer2(s, 'night', 'B-chorus2-04', lambda s_, t_, l_: day_for_night(_raw(s_, t_, l_)), glow=1.1, night=True)
    dawn = v2.printer_for(s, _raw)
    nraw = day_for_night(raw)
    p = clamp((t - 165.7) / 1.9)
    if p <= 0:
        img = night(nraw)
    elif p >= 1:
        img = dawn(raw)
    else:
        img = peel(night(nraw), dawn(raw), p, angle=-24.0, curl=170.0, back='#E4D7BC', mode='paper')
    return v2.english_lines(img, s, t)


# ------------------------------------------------------------------ the flying card
@functools.lru_cache(maxsize=2)
def card_faces(w=960):
    from . import card2 as C
    from .v2_card import _sun_disc
    card = C.render_card(stamp_k=(1, 1, 1, 1, 1))
    card = _sun_disc(card, 1.0)
    cov, x0, y0 = C.stamp_patch(5)
    C._press(card, cov, x0, y0)
    front = cv2.resize(card, (w, int(w * C.CH / C.CW)), interpolation=cv2.INTER_AREA)
    back = np.empty_like(front)
    back[:] = H('#E9DFC9')
    rng = np.random.default_rng(9)
    fib = cv2.GaussianBlur(rng.standard_normal(back.shape[:2]).astype(np.float32), (0, 0), 1.0)
    back *= (1 + 0.02 * fib)[..., None]
    import skia
    from mv import text
    surf = skia.Surface(back.shape[1], back.shape[0])
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    f = text.font('old', 40)
    c.drawString('潮見線', back.shape[1] / 2 - f.measureText('潮見線') / 2, back.shape[0] / 2 + 14, f,
                 skia.Paint(AntiAlias=True, Color=skia.Color4f(*H('#2C4C9A'), 0.7)))
    arr = np.empty((back.shape[0], back.shape[1], 4), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(back.shape[1], back.shape[0], skia.ColorType.kRGBA_8888_ColorType,
                                        skia.AlphaType.kUnpremul_AlphaType), arr, back.shape[1] * 4)
    a = arr[..., 3:4].astype(np.float32) / 255
    back = back * (1 - a) + arr[..., :3].astype(np.float32) / 255 * a
    return front.astype(np.float32), back.astype(np.float32)


def card_quad(x, y, z, yaw, pitch, roll, size=520.0, f=1400.0):
    """screen quad of a 16:9 card of width `size` (world units) centred at (x, y, z) (camera at origin, +z forward,
    screen centre at (W/2, H/2)); returns (quad, facing) -- facing > 0 when the front is toward the camera"""
    hw, hh = size / 2, size * 9 / 32
    P = np.float32([[-hw, -hh, 0], [hw, -hh, 0], [hw, hh, 0], [-hw, hh, 0]])
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    Ry = np.float32([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.float32([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.float32([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    R = Rz @ Rx @ Ry
    Q = P @ R.T + np.float32([x, y, z])
    q = np.stack([W / 2 + f * Q[:, 0] / Q[:, 2], H_ / 2 + f * Q[:, 1] / Q[:, 2]], 1)
    n = R @ np.float32([0, 0, -1])
    return q, float(n[2] * -1)


def draw_card(img, x, y, z, yaw, pitch, roll, sun_dir=(0.6, -0.6, -0.5), alpha=1.0, shadow=0.0):
    front, back = card_faces()
    q, facing = card_quad(x, y, z, yaw, pitch, roll)
    if not np.isfinite(q).all() or z <= 50:
        return img
    tex = front if facing >= 0 else back[:, ::-1]
    # light: brighter when the face turns to the sun; a glint near edge-on
    _, _ = sun_dir, None
    lit = 0.78 + 0.32 * abs(facing)
    tex = tex * lit
    if abs(facing) < 0.25:
        tex = tex + (1 - abs(facing) / 0.25) * 0.25
    if shadow > 0:
        sh = np.zeros((H_, W), np.float32)
        cv2.fillPoly(sh, [np.round((q + [18, 26]) * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
        sh = cv2.GaussianBlur(sh, (0, 0), 14) * shadow
        img = img * (1 - sh[..., None])
    return fx.quad_paste(img, tex, q, alpha=alpha, feather=0.8)


O08_PATH = [(0.0, 1830, 1290), (0.25, 1805, 990), (0.5, 1745, 795), (0.72, 1790, 600), (0.9, 1910, 470),
            (1.0, 2090, 400)]    # screen points (e, x, y): up his right side -- right of his ear and hair, right of the
                                 # LED strip -- and off the right edge (the next shot picks the card up from the left)


def _o08_screen(e):
    """Catmull-Rom through O08_PATH"""
    ps = O08_PATH
    i = max(0, min(len(ps) - 2, next((j for j in range(len(ps) - 1) if e <= ps[j + 1][0]), len(ps) - 2)))
    u = (e - ps[i][0]) / max(1e-6, ps[i + 1][0] - ps[i][0])
    p0, p1, p2, p3 = (np.float32(ps[max(0, min(len(ps) - 1, j))][1:]) for j in (i - 1, i, i + 1, i + 2))
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def outro_08_over(img, s, t, local):
    """the card blows in from below, rises past his shoulder on the wind and flies off to the right -- never across
    his face"""
    t0 = 183.35
    k = (t - t0) / (185.87 - t0)
    if k <= 0:
        return img
    e = clamp(k)
    sx, sy = _o08_screen(e)
    sx += 18 * math.sin(e * 11.0)
    sy += 14 * math.sin(e * 9.0 + 1)
    z = 1300 + 5200 * e ** 1.4
    x, y = (sx - 960) * z / 1400.0, (sy - 540) * z / 1400.0
    yaw = 35 * math.sin(t * 2.9) + 20
    pitch = 50 * math.sin(t * 3.7 + 0.4) - 25
    roll = -25 + 40 * math.sin(t * 2.1)
    img = draw_card(img, x, y, z, yaw, pitch, roll, shadow=0.25 * (1 - e))
    if e > 0.75:                                            # it becomes a spark against the sun
        q, _ = card_quad(x, y, z, yaw, pitch, roll)
        cx, cy = q.mean(0)
        g = np.exp(-(((_xs() - cx) ** 2 + (_ys() - cy) ** 2) / (2 * 22.0 ** 2))) * (e - 0.75) * 4 * 0.8
        img = img + H('#FFF2C8')[None, None] * g[..., None]
    return img


OH1_ROAD = [(460, 1080), (1510, 1080), (1162, 640), (847, 640)]      # the near road as a rectangle (keyframe)


def outro_hook_01(s, t, local, fi):
    """aerial: the card crosses the town; the light turns from dawn to noon in a few beats; the English line is painted
    on the road below, one word on each sung word"""
    from .v2_typo import road_text, glyph_times
    raw = v2.plate(s, local)
    quad = v2.tracked(s, OH1_ROAD, local, box=(460, 640, 1510, 1080))
    d = s['end'] - s['start']
    k = clamp(local / d)
    day = clamp((local - 0.4) / 1.6)
    warm = np.float32([1.06, 0.92, 0.80])
    noon = np.float32([1.02, 1.03, 1.06])
    raw = raw * (warm * (1 - day) + noon * day) + 0.04 * day
    if day > 0.5:
        from .v2_shots import MIRAGE, _mirage_mask
        raw = v2.heat(raw, t, 0.004 * day)
        raw = v2.heat(raw, t * 1.6 + 3.7, MIRAGE['B-outro_hook-01'][4] * (day - 0.5) * 2, region=_mirage_mask('B-outro_hook-01'))
    img = v2.printer_for(s, lambda s_, t_, l_: v2.plate(s_, l_))(raw)
    img = road_text(img, ['ROAD', 'SHIMMER', "WIGGLIN'", 'THE', 'VISION'], glyph_times()['63'], t, quad)   # paint on the print
    e = k
    img = draw_card(img, -900 + 1900 * e, -60 + 90 * math.sin(e * 4), 1700 - 300 * e, 30 * math.sin(t * 2.4), 60 + 20 * math.sin(t * 3.1),
                    -15 + 25 * math.sin(t * 1.7), shadow=0.0)
    return v2.english_lines(img, s, t)


@functools.lru_cache(maxsize=1)
def _grid():
    return np.mgrid[0:H_, 0:W].astype(np.float32)


def _xs():
    return _grid()[1]


def _ys():
    return _grid()[0]


def install():
    for sid, fn in (('B-bridge2-04', bridge2_04), ('B-outro-02', outro_02), ('B-outro_hook-01', outro_hook_01)):
        s = v2.tl.BY_ID[sid]
        if v2.clip_path(v2.b2_id(s)) or (v2.STANDIN and v2.kf_path(v2.b2_id(s))):
            v2.GRAPHIC[sid] = fn
    v2.OVER['B-outro-08'] = outro_08_over

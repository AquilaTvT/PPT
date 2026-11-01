"""MV-B v2: per-shot devices composited into the generated footage (raw stage), registered into mvb.v2.RAW.

Mirrors are tracked through each clip (scale + translation of a hand-placed hint ellipse, fitted every frame
to the inner edge of the orange ring below the hood), then her moments from other shots play inside them.
Screens, clocks and the stamp card are pasted on quads placed on the keyframe (the shots are static).
"""
import functools
import json
import math
import os

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import BEAT, BEAT0, LYRICS
from . import v2
from . import v2_fx as fx
from .print_fx import hexc as H

W, H_ = 1920, 1080

# her moments: (shot, crop centre x, y, half size) on that shot's plate
HER = {
    'turn': ('B2-hook-02', 930, 380, 380),
    'run': ('B2-hook-03', 960, 650, 330),
    'stand': ('B2-chorus1-03', 950, 560, 420),
    'pool': ('B2-chorus1-05', 1190, 420, 420),
}


def her(name, t_src):
    sid2, cx, cy, hs = HER[name]
    f = v2.footage(sid2)
    if f is None:
        return None
    img = f.at(t_src % max(0.5, f.dur - 0.1))
    x0, y0 = int(cx - hs), int(cy - hs)
    pad = cv2.copyMakeBorder(img, hs, hs, hs, hs, cv2.BORDER_REFLECT)
    return pad[y0 + hs:y0 + 3 * hs, x0 + hs:x0 + 3 * hs]


# ------------------------------------------------------------------ mirror tracking
def _ringmask(rgb):
    hsv = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    h = hsv[..., 0]
    return ((h <= 22) | (h >= 160)) & (hsv[..., 1] > 70) & (hsv[..., 2] > 35)


def _ell_dir(ew, eh, ang, a):
    """radius of an axis-aligned-then-rotated ellipse along direction a (radians, image coords)"""
    t = a - math.radians(ang)
    return 1.0 / math.sqrt((math.cos(t) / (ew / 2)) ** 2 + (math.sin(t) / (eh / 2)) ** 2)


def fit_mirror(rgb, est, hint):
    """refine (cx, cy, s) of the hint ellipse on this frame: rays from the centre to the inner ring edge,
    lower 220 degrees only (the hood hangs over the top); least squares for centre + scale"""
    cx, cy, s = est
    (_, _), (ew, eh), ang = hint
    R = max(ew, eh) / 2 * s
    x0, y0 = int(max(0, cx - 1.7 * R)), int(max(0, cy - 1.7 * R))
    x1, y1 = int(min(W, cx + 1.7 * R)), int(min(H_, cy + 1.7 * R))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return est, 0.0
    ring = _ringmask(rgb[y0:y1, x0:x1])
    rows, cols, ps = [], [], []
    for a in np.radians(np.arange(-30, 211, 4)):           # 0 = right, 90 = down (image coords)
        rho = _ell_dir(ew, eh, ang, a) * s
        ds = np.arange(0.55 * rho, 1.45 * rho, 1.0)
        xs = (cx + ds * math.cos(a) - x0).astype(int)
        ys = (cy + ds * math.sin(a) - y0).astype(int)
        ok = (xs >= 0) & (xs < x1 - x0) & (ys >= 0) & (ys < y1 - y0)
        hit = np.zeros_like(ok)
        hit[ok] = ring[ys[ok], xs[ok]]
        if not hit.any():
            continue
        d = ds[int(np.argmax(hit))]
        u = _ell_dir(ew, eh, ang, a)
        rows.append([1, 0, u * math.cos(a)])
        rows.append([0, 1, u * math.sin(a)])
        ps += [cx + d * math.cos(a), cy + d * math.sin(a)]
    if len(rows) < 24:
        return est, len(rows) / 120.0
    A, b = np.array(rows), np.array(ps)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    res = np.abs(A @ sol - b).reshape(-1, 2).max(1)
    keep = np.repeat(res < max(3.0, 0.08 * R), 2)
    if keep.sum() >= 24:
        sol = np.linalg.lstsq(A[keep], b[keep], rcond=None)[0]
    return (float(sol[0]), float(sol[1]), float(sol[2])), keep.sum() / max(1, len(rows))


def mirror_track(sid2, hints):
    """per-frame [(cx, cy, s, conf), ...] for each hint, cached beside the clip"""
    f = v2.footage(sid2)
    src = v2.clip_path(sid2) or v2.kf_path(sid2)
    key = os.path.join(v2.WORK2, sid2, f'track_mirrors_{abs(hash(json.dumps(hints))) % 10**8}_{int(os.path.getmtime(src))}.json')
    if os.path.exists(key):
        return json.load(open(key))
    fps = getattr(getattr(f, 'c', None), 'fps', 16.0)
    n = max(1, int(round(f.dur * fps))) if hasattr(f, 'c') else 1
    est = [(h[0][0], h[0][1], 1.0) for h in hints]
    out = []
    for i in range(n):
        rgb = f.at(i / fps) if hasattr(f, 'c') else f.img
        row = []
        for j, h in enumerate(hints):
            e, conf = fit_mirror(rgb, est[j], h)
            if conf > 0.5 and abs(e[2] - est[j][2]) < 0.25:
                est[j] = e
            row.append([est[j][0], est[j][1], est[j][2], conf])
        out.append(row)
    a = np.array(out, np.float32)                              # (n, m, 4)
    if n > 2:
        for j in range(a.shape[1]):
            a[:, j, :3] = fx._gauss1d(a[:, j, :3], 1.5)
    res = a.tolist()
    json.dump(res, open(key, 'w'))
    return res


def mirrors_at(sid2, hints, s, local, speed=None):
    tr = mirror_track(sid2, hints)
    f = v2.footage(sid2)
    if not hasattr(f, 'c'):
        row = tr[0]
    else:
        d = s['end'] - s['start']
        sp = speed if speed is not None else min(1.0, max(0.55, (f.dur - 0.13) / d))
        i = int(round((0.08 + local * sp) * f.c.fps))
        row = tr[min(len(tr) - 1, max(0, i))]
    out = []
    for (cx, cy, sc, conf), h in zip(row, hints):
        out.append((((cx, cy), (h[1][0] * sc, h[1][1] * sc), h[2]), conf))
    return out


def insert_in(img, plate, ell, src, alpha=1.0, k=0.35):
    """her moment inside one mirror; the hood and ring in the plate stay in front"""
    if src is None or alpha <= 0:
        return img
    (cx, cy), (ew, eh), ang = ell
    pad = int(max(ew, eh) * 0.6) + 4
    x0, y0, x1, y1 = int(max(0, cx - pad)), int(max(0, cy - pad)), int(min(W, cx + pad)), int(min(H_, cy + pad))
    if x1 <= x0 or y1 <= y0:
        return img
    before = img[y0:y1, x0:x1].copy()
    fx.mirror_insert(img, ell, src, alpha=alpha, k=k)
    ring = _ringmask(plate[y0:y1, x0:x1]).astype(np.float32)
    ring = cv2.GaussianBlur(cv2.dilate(ring, np.ones((3, 3), np.uint8)), (0, 0), 1.0)
    roi = img[y0:y1, x0:x1]
    roi += (before - roi) * ring[..., None]
    return img


# ------------------------------------------------------------------ shots
RAW = {}
LYRIC = {}


def base(s, t, local):
    return v2.plate(s, local)


def dream(img, s, t, local):
    """the dreamcore light after the devices: noon heat shimmer, night glow (as v2.default_raw)"""
    from .chars import SECTION_WORLD
    world = SECTION_WORLD.get(s['section'], '')
    if world in ('正午刷り Noon Print',):
        img = v2.heat(img, t, 0.005)
    if world in ('夜刷り Night Print', 'ブラウン管 CRT Glow', '月刷り Moon Print', '祭 Festival', '黎明前 Blue Hour'):
        img = v2.glow(img, 0.22)
    return img


# ---- intro-01: the station prints itself plate by plate; the train's sign is a real LED board
INTRO01_SIGN = [(704, 410), (835, 411), (834, 457), (705, 456)]


@functools.lru_cache(maxsize=1)
def _intro01_board():
    from . import print_fx as pf
    rgb, _ = pf.led_board('潮見', rows=12, dot=12, on='#FF9A3C', off='#3A1A10', bg='#140A06', font='dot', glow=0.7)
    return rgb


def intro01(s, t, local):
    img = base(s, t, local)
    img = fx.quad_paste(img, _intro01_board(), INTRO01_SIGN, feather=1.2)
    return dream(img, s, t, local)


def intro01_stage(s, t, local):
    """paper, then four passes of ink (light -> dark) rolled across on the beats, the halftone, the key line as
    the voice comes in at 2.45"""
    if t >= 2.6:
        return None
    passes = [(0.10, 0.62), (0.70, 1.36), (1.44, 2.08), (2.16, 2.40)]
    k = 0.0
    for i, (a, b) in enumerate(passes):
        if t >= b:
            k = i + 1.0
        elif t > a:
            k = i + (t - a) / (b - a)
            break
    return {'inks': k, 'group': 6, 'dots': clamp((t - 2.10) / 0.3), 'lines': clamp((t - 2.38) / 0.12),
            'halo': clamp((t - 2.2) / 0.4)}


RAW['B-intro-01'] = intro01
STAGE = {'B-intro-01': intro01_stage}


# ---- intro-03: the clock says 23:59, the card waits on the table with its sixth cell empty
INTRO03_LED = (741, 300, 957, 384)
INTRO03_CARD = [(891, 607), (1063, 649), (920, 691), (749, 640)]


@functools.lru_cache(maxsize=4)
def card_tex(stamps=5, sun=0.0, w=960):
    from . import card2
    c = card2.render_card(stamp_k=tuple([1] * stamps + [0] * (5 - stamps)), sun_k=sun)
    return cv2.resize(c, (w, int(w * card2.CH / card2.CW)), interpolation=cv2.INTER_AREA)


def intro03(s, t, local):
    img = base(s, t, local)
    plate = img.copy()
    x0, y0, x1, y1 = INTRO03_LED
    colon = (t * 2) % 2 < 1
    face = fx.led_face('23:59' if colon else '23 59', x1 - x0, y1 - y0)
    img = fx.quad_paste(img, face, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], feather=2.0)
    img = fx.quad_paste(img, card_tex(), INTRO03_CARD, light=0.8, feather=1.0, blur=0.6)
    return dream(img, s, t, local)


RAW['B-intro-03'] = intro03


# ---- hook-01: her walk inside the curve mirror
HOOK01_M = [((580, 290), (176, 176), 0.0)]


def hook01(s, t, local):
    img = base(s, t, local)
    plate = img.copy()
    for ell, conf in mirrors_at('B2-hook-01', HOOK01_M, s, local):
        a = clamp((conf - 0.35) / 0.3)
        img = insert_in(img, plate, ell, her('run', 0.4 + local * 0.8), alpha=a)
    return dream(img, s, t, local)


RAW['B-hook-01'] = hook01


# ---- hook-02: seen through the mirror (fisheye + the orange rim at the frame edge)
def through_mirror(img, k=0.22):
    """raw stage: the shot as seen in a convex curve mirror -- barrel warp, edge darkening, specular streak"""
    ys, xs = fx_grid()
    u, v = (xs - W / 2) / (W / 2), (ys - H_ / 2) / (H_ / 2)
    e = (u / 0.985) ** 2 + (v / 1.06) ** 2
    f = 1 + k * e
    mx = (u / f * 1.04 * (W / 2) + W / 2).astype(np.float32)
    my = (v / f * 1.04 * (H_ / 2) + H_ / 2).astype(np.float32)
    out = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = out * np.clip(1.0 - 0.55 * np.clip((e - 0.62) / 0.38, 0, 1) ** 1.6, 0.4, 1.0)[..., None]
    streak = np.exp(-((e - 0.86) / 0.035) ** 2) * np.clip((-u - v * 1.4 - 0.55) * 2.0, 0, 1)
    return out + streak[..., None] * 0.45


@functools.lru_cache(maxsize=1)
def mirror_frame_layers():
    """over stage: ring, hood and the sky beyond as flat ink layers with a halftone shade (masks + colours)"""
    ys, xs = fx_grid()
    u, v = (xs - W / 2) / (W / 2), (ys - H_ / 2) / (H_ / 2)
    e = (u / 0.985) ** 2 + (v / 1.06) ** 2
    hood_in = (u / 1.0) ** 2 + ((v + 0.05) / 0.78) ** 2
    hood = np.clip((hood_in - 1.0) / 0.015, 0, 1) * np.clip((1.0 - e) / 0.012, 0, 1) * (v < 0.1)
    ring = np.clip((e - 1.0) / 0.012, 0, 1) * (1 - np.clip((e - 1.17) / 0.012, 0, 1))
    outside = np.clip((e - 1.17) / 0.012, 0, 1)
    per = 9.0
    uu, vv = (xs + ys) / (per * 1.4142), (xs - ys) / (per * 1.4142)
    dd = np.sqrt((uu - np.round(uu)) ** 2 + (vv - np.round(vv)) ** 2)
    def screen(tone):
        return np.clip((np.sqrt(np.clip(tone, 0, 1)) * 0.66 - dd) * 5 + 0.5, 0, 1) * (tone > 0.02)
    ring_shadow = screen(np.clip((u * 0.6 + v * 0.8 + 0.2) * 0.55, 0, 0.6)) * ring
    hood_shadow = screen(np.clip((v + 0.9) * 0.9, 0, 0.7)) * hood
    hl = np.exp(-((e - 1.05) / 0.02) ** 2) * np.clip(-(u * 0.7 + v * 0.7) - 0.3, 0, 1) * ring
    return [(outside, '#2C4C9A'), (ring, '#E8742C'), (ring_shadow, '#9E3A22'), (hood, '#B5402C'), (hood_shadow, '#5E1E1A'),
            (hl, '#F6E7C8'), (np.clip(np.exp(-((e - 1.0) / 0.006) ** 2) + np.exp(-((e - 1.17) / 0.006) ** 2), 0, 1) * 0.9, '#1A1110')]


def mirror_frame_over(img, s, t, local):
    for m, col in mirror_frame_layers():
        img += (H(col)[None, None] - img) * m[..., None]
    return img


@functools.lru_cache(maxsize=1)
def fx_grid():
    return np.mgrid[0:H_, 0:W].astype(np.float32)


def hook02(s, t, local):
    img = base(s, t, local)
    img = dream(img, s, t, local)
    return through_mirror(img)


RAW['B-hook-02'] = hook02


# ---- hook-04: the title swims out of the mirage inside the giant mirror
HOOK04_M = [((981, 575), (864, 808), 0.0)]
TITLE = 'Heat Waves'


@functools.lru_cache(maxsize=2)
def title_mask(size=150):
    """the title set in EB Garamond italic, with a key line (stroke) mask for contrast; (fill, line)"""
    import skia
    from mv import text
    f = text.font('garamond_i', size)
    w = int(f.measureText(TITLE) + size)
    h = int(size * 1.5)
    info = skia.ImageInfo.Make(w, h, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType)
    out = []
    for stroke in (0.0, size * 0.045):
        surf = skia.Surface.MakeRaster(info)
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 0))
        p = skia.Paint(AntiAlias=True, Color=skia.Color4f(1, 1, 1, 1))
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style)
            p.setStrokeWidth(stroke)
        c.drawString(TITLE, size * 0.5, size * 1.05, f, p)
        a = np.empty((h, w), np.uint8)
        surf.readPixels(info, a, w)
        out.append(a.astype(np.float32) / 255.0)
    return out[0], out[1]


def _wavy(m, amp, t, freq=0.045, speed=6.0):
    h, w = m.shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = amp * np.sin(ys * freq * 2 * math.pi / 6 + t * speed) + amp * 0.4 * np.sin(ys * 0.31 + t * 9.0)
    return cv2.remap(m, xs + dx.astype(np.float32), ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


def hook04_over(img, s, t, local):
    """the title hovers over the hot road inside the mirror with its mirage underneath; it rises out of the
    shimmer and snaps into register on the second downbeat"""
    snap = 26.61
    p = clamp((t - 25.95) / (snap - 25.95))
    e = 1 - (1 - p) ** 3
    if p <= 0:
        return img
    plate = v2.plate(s, local)
    (ell, conf), = mirrors_at('B2-hook-04', HOOK04_M, s, local)
    (cx, cy), (ew, eh), ang = ell
    glass = np.zeros((H_, W), np.float32)
    cv2.ellipse(glass, ((cx, cy), (ew * 0.97, eh * 0.97), ang), 1.0, -1, cv2.LINE_AA)
    glass *= 1 - cv2.GaussianBlur(_ringmask(plate).astype(np.float32), (0, 0), 1.5)
    fill, line = title_mask()
    late = clamp((t - 28.25) / 0.55)
    amp = 20 * (1 - e) + 1.0 + 8 * late
    blur = 0.3 + 4 * (1 - e)
    fw, lw = _wavy(fill, amp, t), _wavy(line, amp, t)
    if blur > 0.4:
        fw, lw = cv2.GaussianBlur(fw, (0, 0), blur), cv2.GaussianBlur(lw, (0, 0), blur)
    h, w = fw.shape
    horizon = cy - eh * 0.085
    base = horizon + 160 + 60 * (1 - e)                  # baseline over the road; rises from below the horizon line
    x0, y0 = int(cx - w / 2), int(base - h * 0.70)
    alpha = e ** 0.7 * (1 - 0.5 * late)

    def put(src, x, y):
        lay = np.zeros((H_, W), np.float32)
        xa, ya, xb, yb = max(0, x), max(0, y), min(W, x + src.shape[1]), min(H_, y + src.shape[0])
        if xb > xa and yb > ya:
            lay[ya:yb, xa:xb] = src[ya - y:yb - y, xa - x:xb - x]
        return lay
    # the mirage first (under the title): upside down from the baseline, squashed, rippling, sky-coloured
    ref = cv2.resize(fill[::-1], (w, int(h * 0.55)), interpolation=cv2.INTER_AREA)
    ref = _wavy(ref, 7 + 6 * (1 - e), t * 1.4, freq=0.14)
    fade = np.linspace(1, 0, ref.shape[0], dtype=np.float32)[:, None] ** 1.3
    lay = put(ref * fade, x0, int(base - h * 0.30 * 0.55) + 6)
    img += (H('#DCE8F2')[None, None] - img) * (lay * glass * alpha * 0.5)[..., None]
    off = 12 * (1 - e) + 1.2
    for src, dx, dy, col, k in ((lw, 0, 0, '#141A33', 0.85), (fill, -off, off * 0.6, '#D9402B', 0.85),
                                (fill, off, -off * 0.6, '#2C4C9A', 0.75), (fill, 0, 0, '#F3EBD9', 1.0)):
        srcw = fw if src is fill else lw
        lay = put(srcw, x0 + int(dx), y0 + int(dy))
        img += (H(col)[None, None] - img) * (lay * glass * alpha * k)[..., None]
    return img


# ---- chorus1-01: her peek-and-laugh in each mirror of the junction
C101_M = [((403, 315), (152, 160), 0.0), ((1609, 236), (276, 236), 0.0), ((1260, 517), (74, 74), 0.0)]
C101_SRC = ['turn', 'stand', 'run']


def chorus1_01(s, t, local):
    img = base(s, t, local)
    plate = img.copy()
    for j, (ell, conf) in enumerate(mirrors_at('B2-chorus1-01', C101_M, s, local)):
        a = clamp((conf - 0.35) / 0.3) * clamp((local - 0.15 - j * BEAT) / 0.12)
        img = insert_in(img, plate, ell, her(C101_SRC[j], 0.3 + local * 0.7), alpha=a)
    return dream(img, s, t, local)


RAW['B-chorus1-01'] = chorus1_01


# ---- chorus1-02: the far CRT shows her laughing face; the clock reads 0:00
C102_TV = [(1391, 177), (1644, 177), (1644, 387), (1391, 387)]
C102_LED = (247, 901, 440, 980)


def chorus1_02(s, t, local):
    img = base(s, t, local)
    face = her('turn', 0.5 + local * 0.6)
    if face is not None:
        q = np.asarray(C102_TV, np.float32)
        w, h = int(q[1, 0] - q[0, 0]), int(q[3, 1] - q[0, 1])
        tv = cv2.resize(face[int(face.shape[0] * 0.05):int(face.shape[0] * 0.80), int(face.shape[1] * 0.12):int(face.shape[1] * 0.88)],
                        (w * 2, h * 2), interpolation=cv2.INTER_AREA)
        img = fx.quad_paste(img, fx.crt(tv, t, tint='#FFF1C8', curve=0.08), C102_TV, feather=3.0)
    x0, y0, x1, y1 = C102_LED
    face = fx.led_face('0:00' if (t * 2) % 2 < 1 else '0 00', x1 - x0, y1 - y0)
    img = fx.quad_paste(img, face, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], feather=2.0)
    return dream(img, s, t, local)


RAW['B-chorus1-02'] = chorus1_02


# ---- chorus1-06: a different moment of her in every mirror, lighting up one per beat
C106_SRC = ['turn', 'stand', 'run', 'pool', 'turn', 'stand', 'run', 'pool']


@functools.lru_cache(maxsize=1)
def c106_hints():
    f = v2.footage('B2-chorus1-06')
    rgb = f.at(0.0) if hasattr(f, 'c') else f.img
    found = fx.detect_mirrors(rgb, min_r=40, max_n=8)
    return [((float(e[0][0]), float(e[0][1])), (float(e[1][0]), float(e[1][1])), float(e[2])) for e in found]


def chorus1_06(s, t, local):
    img = base(s, t, local)
    plate = img.copy()
    hints = c106_hints()
    nb0 = (s['start'] - BEAT0) / BEAT
    for j, (ell, conf) in enumerate(mirrors_at('B2-chorus1-06', hints, s, local)):
        on = BEAT0 + (math.floor(nb0) + 1 + j * 0.5) * BEAT
        a = clamp((conf - 0.35) / 0.3) * clamp((t - on) / 0.1)
        if a > 0:
            img = insert_in(img, plate, ell, her(C106_SRC[j % len(C106_SRC)], 0.2 + local * 0.7 + j * 0.37), alpha=a)
    return dream(img, s, t, local)


RAW['B-chorus1-06'] = chorus1_06


# ---- chorus1-07: the card on the floor -- five stamps, a paper sun that cannot rise in the sixth
C107_CARD = [(687, 807), (1057, 729), (1320, 940), (804, 1067)]


def chorus1_07(s, t, local):
    img = base(s, t, local)

    def bump(t0, peak, up=0.30, down=0.42):
        if t < t0:
            return 0.0
        if t < t0 + up:
            return peak * clamp((t - t0) / up) ** 2
        return peak * (1 - clamp((t - t0 - up) / down))
    sun = max(bump(50.31, 0.42), bump(51.05, 0.47))
    if 51.79 <= t < 52.05:
        sun = 0.38 if int((t - 51.79) * 24) % 2 == 0 else 0.0
    img = fx.quad_paste(img, card_tex(5, round(sun, 2)), C107_CARD, light=0.85, feather=1.0, blur=0.4)
    return dream(img, s, t, local)


RAW['B-chorus1-07'] = chorus1_07


# ------------------------------------------------------------------ lyric column placement (off faces)
LYRIC.update({
    'B-hook-02': dict(x=330, y=230),
    'B-hook-04': dict(x=1760, y=150),
    'B-chorus1-02': dict(x=1820, y=470, size=86),
    'B-chorus1-04': dict(x=1840),
    'B-chorus1-05': dict(x=150, y=150),
    'B-chorus1-03': dict(x=1500),
})


OVER = {'B-hook-02': mirror_frame_over, 'B-hook-04': hook04_over}


def install():
    v2.RAW.update(RAW)
    v2.OVER.update(OVER)
    v2.STAGE.update(STAGE)
    v2.LYRIC_POS.update(LYRIC)

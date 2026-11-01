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
    os.makedirs(os.path.dirname(key), exist_ok=True)
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


def ripple(src, amp, t, wl=0.09, speed=7.0):
    """water rings from the centre of a picture: 'the swimming mirror'; amp in px"""
    if src is None or amp < 0.2:
        return src
    h, w = src.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2
    dx, dy = xs - cx, ys - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    disp = amp * np.sin(r / (wl * max(w, h)) * 2 * math.pi - t * speed)
    return cv2.remap(src, (xs + disp * dx / r).astype(np.float32), (ys + disp * dy / r).astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)


def insert_in(img, plate, ell, src, alpha=1.0, k=0.35, rip=0.0, t=0.0):
    """her moment inside one mirror; the hood and ring in the plate stay in front; rip > 0 sets her swimming in"""
    if src is None or alpha <= 0:
        return img
    if rip > 0:
        src = ripple(src, rip * src.shape[0] / 300.0, t)
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
    img = fx.quad_paste(img, _intro01_board(), v2.tracked(s, INTRO01_SIGN, local), feather=1.2)
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


def as_quad(q):
    q = np.asarray(q, np.float32)
    if q.size == 4:
        x0, y0, x1, y1 = q
        q = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    return q.reshape(4, 2)


def led_over(img, q, txt, on='#FF3B2A', glow=0.6):
    """a red LED face drawn over the print (the print's palette has no room for its red): box or quad"""
    q = as_quad(q)
    w = max(8, int(round(np.hypot(*(q[1] - q[0])))))
    h = max(8, int(round(np.hypot(*(q[3] - q[0])))))
    face = fx.led_face(txt, w, h, on=on, glow=glow)
    img = fx.quad_paste(img, face, q, feather=2.0)
    ys, xs = fx_grid()
    (cx, cy), rx, ry = q.mean(0), w * 0.9, h * 1.6
    g = np.exp(-(((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2)) * 0.12
    return img + H(on)[None, None] * g[..., None]


def intro03(s, t, local):
    return dream(base(s, t, local), s, t, local)


def intro03_over(img, s, t, local):
    """the card (its own riso inks, kept out of the scene's palette) lit by the room, then the clock"""
    img = fx.quad_paste(img, card_tex(), v2.tracked(s, INTRO03_CARD, local), light=0.8, feather=1.0, blur=0.5)
    return led_over(img, v2.tracked_box(s, INTRO03_LED, local), '23:59' if (t * 2) % 2 < 1 else '23 59')


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


def swim_env(idx, a=5, b=None, tail=0.5):
    """0..1 envelope over the sung '泳いでくミラー' of lyric line idx (glyph a .. b)"""
    from .v2_typo import glyph_times
    g = glyph_times()[str(idx)]
    b = len(g) - 1 if b is None else b

    def env(t):
        return clamp((t - g[a] + 0.1) / 0.25) * (1 - clamp((t - g[b] - tail) / 0.6))
    return env


def hook02(s, t, local):
    img = base(s, t, local)
    img = dream(img, s, t, local)
    e = swim_env(6)(t)                                     # 泳いでくミラー: the mirror swims
    if e > 0:
        img = ripple(img, 7.0 * e, t, wl=0.07, speed=6.0)
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
        img = fx.quad_paste(img, fx.crt(tv, t, tint='#FFF1C8', curve=0.08), v2.tracked(s, C102_TV, local), feather=3.0)
    return dream(img, s, t, local)


def chorus1_02_over(img, s, t, local):
    return led_over(img, v2.tracked_box(s, C102_LED, local), '0:00' if (t * 2) % 2 < 1 else '0 00')


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
            rip = 6.0 * math.exp(-max(0.0, t - on) * 3.0)
            img = insert_in(img, plate, ell, her(C106_SRC[j % len(C106_SRC)], 0.2 + local * 0.7 + j * 0.37), alpha=a,
                            rip=rip, t=t)
    return dream(img, s, t, local)


RAW['B-chorus1-06'] = chorus1_06


# ---- chorus1-07: the card on the floor -- five stamps, a paper sun that cannot rise in the sixth
C107_CARD = [(687, 807), (1057, 729), (1320, 940), (804, 1067)]


def _c107_cam(s, local):
    d = s['end'] - s['start']
    k = clamp(local / d)
    e = k * k * (3 - 2 * k)
    z = 1.0 + 1.25 * e
    q = np.asarray(C107_CARD, np.float32)
    from . import card2
    u, v = card2.CELL_C[5][0] / card2.CW, card2.CELL_C[5][1] / card2.CH
    top = q[0] + (q[1] - q[0]) * u
    bot = q[3] + (q[2] - q[3]) * u
    c6 = top + (bot - top) * v                              # the sixth cell on the plate
    return z, 0.5 + (c6[0] / W - 0.5) * e, 0.5 + (c6[1] / H_ - 0.5) * e


def chorus1_07(s, t, local):
    """a slow push from the room to the card: the sixth cell, where a paper sun tries twice to rise and fails"""
    z, cx, cy = _c107_cam(s, local)
    return dream(v2.plate(s, local, zoom=z, cx=cx, cy=cy), s, t, local)


def chorus1_07_over(img, s, t, local):
    z, cx, cy = _c107_cam(s, local)
    sid2 = v2.b2_id(s)
    f = v2.footage(sid2)
    d = s['end'] - s['start']
    sp = min(1.0, max(0.55, (f.dur - 0.13) / d))
    qz = v2.zoom_map(sid2, z, cx, cy, t_src=0.08 + local * sp)(v2.tracked(s, C107_CARD, local))

    def bump(t0, peak, up=0.30, down=0.42):
        if t < t0:
            return 0.0
        if t < t0 + up:
            return peak * clamp((t - t0) / up) ** 2
        return peak * (1 - clamp((t - t0 - up) / down))
    sun = max(bump(50.31, 0.42), bump(51.05, 0.47))
    if 51.79 <= t < 52.05:
        sun = 0.38 if int((t - 51.79) * 24) % 2 == 0 else 0.0
    return fx.quad_paste(img, card_tex(5, round(sun, 2), w=960 if z < 1.4 else 1920), qz, light=0.85, feather=1.0, blur=0.4)


RAW['B-chorus1-07'] = chorus1_07


# ---- chorus1-04: two-ink riso -- her on the orange plate, him on the cobalt; the plates drift apart on 幸せ
def chorus1_04(s, t, local, fi):
    from . import v2_print as vp
    from .v2_typo import glyph_times
    raw = dream(base(s, t, local), s, t, local)
    gt = glyph_times()['13']
    k = clamp((t - gt[2]) / (gt[3] + 0.18 - gt[2]))
    e = 1 - (1 - k) ** 3
    off = 1.5 + 30.0 * e
    img = vp.two_ink(raw, vp.split_masks(990), offsets=((-off, off * 0.35), (off, -off * 0.35)))
    return img


GRAPHIC_FOOT = {'B-chorus1-04': chorus1_04}


# ---- chorus2-01: the line hangs on tanzaku strips under the wind chimes
def chorus2_01_over(img, s, t, local):
    from .v2_typo import tanzaku
    return tanzaku(img, 26, t, x0=1830, y_top=34, step=-112, size=64)


# ---- chorus2-02: the vending machine's ticker and its lottery roulette stopping on 0012
C202_TICKER = (1012, 706, 1632, 750)
C202_ROUL = (1306, 868, 1494, 936)


@functools.lru_cache(maxsize=1)
def _ticker_board():
    from . import print_fx as pf
    rgb, _ = pf.led_board('　ただいま 0:12　つめた〜い　あたりが出たらもう一本　', rows=12, dot=4, on='#FF8A3A',
                          off='#2A1208', bg='#100804', font='dot', glow=0.5)
    return rgb


def chorus2_02(s, t, local):
    return dream(base(s, t, local), s, t, local)


def chorus2_02_over(img, s, t, local):
    x0, y0, x1, y1 = C202_TICKER
    board = _ticker_board()
    bh, bw = board.shape[:2]
    win = int((x1 - x0) * bh / (y1 - y0))
    off = int(local * 160) % max(1, bw - win)
    crop = board[:, off:off + win]
    img = fx.quad_paste(img, crop, v2.tracked_box(s, C202_TICKER, local), feather=1.0)
    x0, y0, x1, y1 = C202_ROUL
    stop = [79.95, 80.35, 80.75, 81.15]
    digs = ''
    for j, ts in enumerate(stop):
        digs += '0012'[j] if t >= ts else str(int(t * 31 + j * 3) % 10)
    return led_over(img, v2.tracked_box(s, C202_ROUL, local), digs, glow=0.5)


RAW['B-chorus2-02'] = chorus2_02


# ---- chorus2-04: the line set down the moon's path on the sea, broken by the waves
def chorus2_04_over(img, s, t, local):
    from .v2_typo import moon_path
    return moon_path(img, 29, t, x=1190, y0=360)


# ---- verse-06: nigemizu -- the print's dots grow into rippling LED dots, then silver water floods to the lens
V06_VP = (955.0, 688.0)


def verse06_over(img, s, t, local):
    d = s['end'] - s['start']
    ys, xs = fx_grid()
    led_k = clamp((local - 0.55) / 1.5)
    led_k = led_k * led_k * (3 - 2 * led_k)
    if led_k > 0:
        per = 8.0 + 13.0 * led_k
        gw, gh = int(math.ceil(W / per)), int(math.ceil(H_ / per))
        small = cv2.resize(img, (gw, gh), interpolation=cv2.INTER_AREA)
        cell = cv2.resize(small, (int(gw * per), int(gh * per)), interpolation=cv2.INTER_NEAREST)[:H_, :W]
        lum = cell @ np.float32([0.2126, 0.7152, 0.0722])
        u, v = (xs % per) - per / 2, (ys % per) - per / 2
        dist = np.sqrt(u * u + v * v)
        rr = np.hypot(xs - V06_VP[0], ys - V06_VP[1])
        ripple = 0.5 + 0.5 * np.sin(rr / 34.0 - t * 7.5)
        rad = per * 0.46 * (0.30 + 0.70 * lum) * (0.80 + 0.35 * ripple)
        disc = np.clip(rad - dist + 0.5, 0, 1)
        col = cell * 0.45 + H('#DCEBFF')[None, None] * 0.55
        led = H('#0B1430')[None, None] + (col - H('#0B1430')[None, None]) * disc[..., None]
        led += cv2.GaussianBlur(disc * lum, (0, 0), per * 0.6)[..., None] * H('#9FC4FF')[None, None] * 0.35
        img = img * (1 - led_k * 0.85) + led * (led_k * 0.85)
    fk = clamp((local - (d - 1.25)) / 1.18)
    if fk > 0:
        fk = fk * fk * (3 - 2 * fk)
        yw = H_ - fk * (H_ + 60)
        src = img.copy()
        wob = 6.0 * np.sin(xs * 0.021 + t * 5.0) + 3.0 * np.sin(xs * 0.07 - t * 3.1)
        ym = 2 * yw - ys + wob
        ym = np.abs(ym)                                          # past the top edge the mirror folds back down
        ym = np.where(ym > H_ - 1, 2 * (H_ - 1) - ym, ym)
        xm = (xs + 7.0 * np.sin(ys * 0.09 + t * 6.0)).astype(np.float32)
        refl = cv2.remap(src, xm, np.clip(ym, 0, H_ - 1).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        refl = cv2.GaussianBlur(refl, (0, 0), 7)                     # a calm silver mirror, not more dots
        depth = np.clip((ys - yw) / 500.0, 0, 1)[..., None]
        water = refl * (0.40 - 0.15 * depth) + H('#E3EAF0')[None, None] * (0.60 + 0.15 * depth)
        water *= (0.97 + 0.03 * np.sin(ys * 0.10 + 2.0 * np.sin(xs * 0.008 + t * 1.1) + t * 3.0))[..., None]
        rng = np.random.default_rng(int(t * 24))
        sp = (rng.random((H_ // 8, W // 8)) > 0.9975).astype(np.float32)
        sp = cv2.GaussianBlur(cv2.resize(sp, (W, H_), interpolation=cv2.INTER_NEAREST), (0, 0), 2.0) * 2.0
        water += sp[..., None] * H('#FFFFFF')[None, None] * 0.6
        line = np.exp(-((ys - yw) / 3.0) ** 2) * 0.9
        a = np.clip((ys - yw) / 4.0, 0, 1)
        img = img * (1 - a[..., None]) + water * a[..., None]
        img += line[..., None] * H('#FFFFFF')[None, None] * 0.6
    return img


# ------------------------------------------------------------------ lyric column placement (off faces)
LYRIC.update({
    'B-hook-02': dict(x=330, y=230),
    'B-hook-04': dict(x=1760, y=150),
    'B-chorus1-01': dict(x=1080, y=140),
    'B-chorus1-02': dict(x=1850, y=130, size=86),
    'B-chorus1-04': dict(x=1820, y=140),
    'B-chorus2-02': dict(x=160, y=150),
    'B-chorus1-05': dict(x=150, y=150),
    'B-chorus1-03': dict(x=1500),
})


OVER = {'B-hook-02': mirror_frame_over, 'B-hook-04': hook04_over, 'B-chorus2-01': chorus2_01_over,
        'B-chorus2-04': chorus2_04_over, 'B-verse-06': verse06_over, 'B-intro-03': intro03_over,
        'B-chorus1-02': chorus1_02_over, 'B-chorus2-02': chorus2_02_over, 'B-chorus1-07': chorus1_07_over}
OWN = {'B-chorus2-01', 'B-chorus2-04'}


def install():
    v2.RAW.update(RAW)
    v2.OVER.update(OVER)
    v2.STAGE.update(STAGE)
    v2.V2_OWN_TYPE.update(OWN)
    v2.ENGLISH.update(ENGLISH_OVR)
    for sid, fn in GRAPHIC_FOOT.items():
        if v2.clip_path(v2.b2_id(v2.tl.BY_ID[sid])) or (v2.STANDIN and v2.kf_path(v2.b2_id(v2.tl.BY_ID[sid]))):
            v2.GRAPHIC[sid] = fn
    v2.LYRIC_POS.update(LYRIC)


# ================================================================== the ending: outro_hook-03
# the title rises out of the mirage once more, then the press runs backwards -- key line, halftone, inks dark
# to light rolled off on the beats -- until only cream paper, the registration marks and the sun stamp remain;
# the LED strip's dots go out one by one, the last one on the final beat.
OH3_BEATS = [BEAT0 + k * BEAT for k in range(258, 270)]       # 191.80, 192.54, ...


def oh3_stage(s, t, local):
    b = OH3_BEATS
    if t < b[3]:
        return None
    passes = [(b[4], b[4] + 0.62), (b[5], b[5] + 0.62), (b[6], b[6] + 0.62), (b[7], b[7] + 0.58)]
    k = 4.0
    for i, (a0, a1) in enumerate(passes):
        if t >= a1:
            k = 3.0 - i
        elif t > a0:
            k = 4.0 - i - (t - a0) / (a1 - a0)
            break
    return {'inks': max(0.0, k), 'group': 6, 'lines': 1 - clamp((t - b[3]) / 0.35),
            'dots': 1 - clamp((t - b[3] - 0.3) / 0.45), 'halo': 1 - clamp((t - b[3]) / 0.6)}


@functools.lru_cache(maxsize=1)
def proof_marks():
    """printer's proof furniture: crop marks, registration targets, a colour bar"""
    import skia
    from .card2 import INK
    surf = skia.Surface(W, H_)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    k = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.10, 0.07, 0.07, 1.0), StrokeWidth=2.0, Style=skia.Paint.kStroke_Style)
    m = 70
    for (x, y, sx, sy) in ((m, m, -1, -1), (W - m, m, 1, -1), (m, H_ - m, -1, 1), (W - m, H_ - m, 1, 1)):
        c.drawLine(x, y + sy * 14, x, y + sy * 52, k)
        c.drawLine(x + sx * 14, y, x + sx * 52, y, k)
    for (x, y) in ((W / 2, 40), (W / 2, H_ - 40), (36, H_ / 2), (W - 36, H_ / 2)):
        c.drawCircle(x, y, 14, k)
        c.drawLine(x - 24, y, x + 24, y, k)
        c.drawLine(x, y - 24, x, y + 24, k)
    cols = ['#F2C23A', '#F08A3C', INK['verm'], '#2D6BE0', INK['cobalt'], INK['navy'], '#1A1110']
    for i, col in enumerate(cols):
        h = H(col)
        c.drawRect(skia.Rect.MakeXYWH(W - 470 + i * 52, H_ - 66, 44, 22), skia.Paint(AntiAlias=True, Color=skia.Color4f(*h, 1.0)))
    from mv import text
    c.drawString('潮見観光協会　昭和六十年夏　第一刷', 110, H_ - 48, text.font('mincho_sb', 22),
                 skia.Paint(AntiAlias=True, Color=skia.Color4f(0.10, 0.07, 0.07, 1.0)))
    arr = np.empty((H_, W, 4), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(W, H_, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kUnpremul_AlphaType), arr, W * 4)
    return arr.astype(np.float32) / 255.0


@functools.lru_cache(maxsize=1)
def sun_hanko(R=170):
    """the sun stamp at screen scale: vermilion double ring and lettering, a yellow sun with rays (two pads)"""
    import skia
    from . import card2 as C
    n = int(R * 2 + 20)
    info = skia.ImageInfo.Make(n, n, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType)

    def layer(draw):
        surf = skia.Surface.MakeRaster(info)
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 0))
        c.translate(n / 2, n / 2)
        draw(c)
        a = np.empty((n, n), np.uint8)
        surf.readPixels(info, a, n)
        return a.astype(np.float32) / 255.0

    def red(c):
        c.drawCircle(0, 0, R * 0.97, C.P(1.0, stroke=R * 0.07))
        c.drawCircle(0, 0, R * 0.74, C.P(1.0, stroke=R * 0.028))
        C.ring_text(c, '潮見線夏休みスタンプラリー', 0, 0, R * 0.855, R * 0.13, 'old', mid=-90)
        C.ring_text(c, '六〇・八・三一　日の出', 0, 0, R * 0.855, R * 0.11, 'mincho', mid=90, bottom=True)
        c.drawCircle(0, R * 0.05, R * 0.36, C.P(1.0, stroke=R * 0.035))
        for k in range(12):
            a = math.radians(k * 30 - 90)
            c.drawLine(math.cos(a) * R * 0.44, R * 0.05 + math.sin(a) * R * 0.44, math.cos(a) * R * 0.62,
                       R * 0.05 + math.sin(a) * R * 0.62, C.P(1.0, stroke=R * 0.04))

    def yel(c):
        c.drawCircle(0, R * 0.05, R * 0.33, C.P(1.0))
    r = C._rubber(layer(red), 77, 30.0)
    y = C._rubber(layer(yel), 78, 200.0)
    return r, y


def oh3_over(img, s, t, local):
    b = OH3_BEATS
    # the title out of the mirage, as in hook-04, then its plates come apart and lift as the press runs back
    p = clamp((t - (b[0] + 0.1)) / (b[1] - b[0] - 0.1))
    if p > 0 and t < b[6]:
        e = 1 - (1 - p) ** 3
        fill, line = title_mask(180)
        amp = 18 * (1 - e) + 1.0
        fw, lw = _wavy(fill, amp, t), _wavy(line, amp, t)
        h, w = fw.shape
        cx, base = W / 2, OH3_BASE + 70 * (1 - e)
        x0, y0 = int(cx - w / 2), int(base - h * 0.70)
        apart = clamp((t - b[3]) / (b[5] - b[3]))
        gone = clamp((t - b[5]) / (b[6] - b[5]))
        off = 10 * (1 - e) + 1.2 + 40 * apart
        alpha = e ** 0.7

        def put(src, x, y):
            lay = np.zeros((H_, W), np.float32)
            xa, ya, xb, yb = max(0, x), max(0, y), min(W, x + src.shape[1]), min(H_, y + src.shape[0])
            if xb > xa and yb > ya:
                lay[ya:yb, xa:xb] = src[ya - y:yb - y, xa - x:xb - x]
            return lay
        ref = cv2.resize(fill[::-1], (w, int(h * 0.55)), interpolation=cv2.INTER_AREA)
        ref = _wavy(ref, 7 + 6 * (1 - e), t * 1.4, freq=0.14)
        fade = np.linspace(1, 0, ref.shape[0], dtype=np.float32)[:, None] ** 1.3
        lay = put(ref * fade, x0, int(base - h * 0.30 * 0.55) + 6)
        img += (H('#DCE8F2')[None, None] - img) * (lay * alpha * 0.45 * (1 - apart))[..., None]
        for src, dx, dy, col, k in ((lw, 0, 0, '#141A33', 0.85 * (1 - clamp((t - b[3]) / 0.35))),
                                    (fill, -off, off * 0.6, '#D9402B', 0.85 * (1 - gone)),
                                    (fill, off, -off * 0.6, '#2C4C9A', 0.75 * (1 - clamp((t - b[5]) / 0.6))),
                                    (fill, 0, 0, '#F3EBD9', 1.0 * (1 - gone))):
            if k <= 0:
                continue
            srcw = fw if src is fill else lw
            lay = put(srcw, x0 + int(dx), y0 + int(dy))
            img += (H(col)[None, None] - img) * (lay * alpha * k)[..., None]
    # bare paper: the proof marks surface, then the sun stamp lands on the last downbeat but one
    pm = clamp((t - b[6] - 0.3) / 0.8)
    if pm > 0:
        mk = proof_marks()
        img = img * (1 - mk[..., 3:4] * pm) + mk[..., :3] * (mk[..., 3:4] * pm)
    if t >= b[8]:
        red, yel = sun_hanko()
        n = red.shape[0]
        x0, y0 = int(W / 2 - n / 2), int(H_ / 2 - n / 2 - 20)
        slam = clamp((t - b[8]) / (3 / 24))
        k = 1.0
        if slam < 1:
            k = slam
        roi = img[y0:y0 + n, x0:x0 + n]
        roi *= 1 - (yel * k)[..., None] * (1 - H('#F2C23A'))[None, None]
        wet = 1 - clamp((t - b[8]) / 0.25)
        spread = cv2.dilate(red, np.ones((3, 3), np.uint8), iterations=max(1, int(round(2 * wet)))) if wet > 0 else red
        roi *= 1 - (spread * k)[..., None] * (1 - H(C_STAMP))[None, None]
    return img


C_STAMP = '#C3342A'
OH3_BASE = 610


def oh3_english(img, s, t):
    """the English lines on the strip; from 197.9 its dots go out one by one, the last on the final beat"""
    b = OH3_BEATS
    if t < 197.9:
        return v2.english_lines(img, s, t)
    key = (66, '#F5C842', 10, 6)
    if key not in v2._LEDCACHE:
        v2.led_caption(img.copy(), 196.0, 66)
    board = v2._LEDCACHE[key]
    bh, bw = board.shape[:2]
    strip_w = min(W - 240, bw)
    crop = board[:, max(0, bw - strip_w):]
    x0 = (W - strip_w) // 2
    y0 = int(1004 - bh / 2)
    dot = 6
    gh, gw = bh // dot, crop.shape[1] // dot
    lum = cv2.resize(crop @ np.float32([0.2126, 0.7152, 0.0722]), (gw, gh), interpolation=cv2.INTER_AREA)
    lit = np.argwhere(lum > lum.max() * 0.45)
    if len(lit) == 0:
        return img
    rng = np.random.default_rng(66)
    order = rng.permutation(len(lit))
    last = order[len(order) // 2]
    f = 1 - clamp((t - 197.9) / (b[9] - 0.25 - 197.9))
    keep = np.zeros((gh, gw), np.float32)
    nkeep = int(round(f * (len(lit) - 1)))
    for j in order[:nkeep]:
        keep[lit[j][0], lit[j][1]] = 1
    if t < b[9]:
        keep[lit[last][0], lit[last][1]] = 1
    on = cv2.resize(keep, (gw * dot, gh * dot), interpolation=cv2.INTER_NEAREST)
    frame = crop[:gh * dot, :gw * dot] * on[..., None] + crop[:gh * dot, :gw * dot] * (1 - on[..., None]) * 0.12
    bg_a = clamp(1 - (t - 197.9) / 0.6) * 0.92
    roi = img[y0:y0 + frame.shape[0], x0:x0 + frame.shape[1]]
    lit_m = on[..., None] * 1.0
    roi += (frame - roi) * np.maximum(lit_m, bg_a)
    return img


RAW['B-outro_hook-03'] = lambda s, t, local: dream(base(s, t, local), s, t, local)
STAGE['B-outro_hook-03'] = oh3_stage
OVER['B-outro_hook-03'] = oh3_over
ENGLISH_OVR = {'B-outro_hook-03': oh3_english}

"""MV-B v2: devices for the remaining shots (raw stage unless noted).

  intro-02      a teletext ticker crawls along the bottom of the CRT
  chorus1-05    the pool scoreboard: 君 lights in each of the eight lanes, one per beat; the timer reads 0:00.00
                and melts in the heat at the end of the shot
  verse-05      riso two-ink photo; his cobalt plate is lifted off like a screen, only she remains, brighter
  chorus3-01    the ten big lanterns light one by one on the sung syllables (a front sweeping left to right)
  chorus3-04    goldfish gather into 幸せ; the paper poi dips in and tears; the fish scatter
  chorus3-05/06 fireworks on the beats; the fourth spells 君, then 0:00 (sparks drawn over the print, the flash
                of each burst lights the scene before the print)
  chorus3-08    the line hangs like willow strands and drips (lyric column replaced)
  bridge2-01..04 the dream in two inks (cobalt + coral): a true duotone press with its own screen angles
  bridge2-01    the train's destination board reads 夢 行, then scrolls the question
  bridge2-02    zoetrope: the train passes one window per frame, so it seems to stand still while she moves
                from window to window
  chorus4-02    the night flies by on a big red LED clock: 0:00 -> 4:52
  chorus4-05    the board flips 夢 -> 日の出; the headlight's halo swells beat by beat into the sunrise
  outro-05      each curve mirror flashes one of her moments in turn, then only the sun
  outro_hook-02 in the mirror she walks into the heat haze and looks back once
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
RAW, OVER, GRAPHIC_FOOT, OWN, LYRIC, ENGLISH_OVR = {}, {}, {}, set(), {}, {}


@functools.lru_cache(maxsize=1)
def _grid():
    return np.mgrid[0:H_, 0:W].astype(np.float32)


def _dream(img, s, t, local):
    from .v2_shots import dream
    return dream(img, s, t, local)


def base(s, t, local):
    return v2.plate(s, local)


def gt(idx):
    from .v2_typo import glyph_times
    return glyph_times()[str(idx)]


def _skia(draw, w, h):
    import skia
    surf = skia.Surface(w, h)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    draw(c)
    arr = np.empty((h, w, 4), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kUnpremul_AlphaType), arr, w * 4)
    return arr.astype(np.float32) / 255.0


def _paint(col, alpha=1.0):
    import skia
    c = H(col)
    return skia.Paint(AntiAlias=True, Color=skia.Color4f(float(c[0]), float(c[1]), float(c[2]), float(alpha)))


def sub_quad(q, u0, v0, u1, v1):
    """the part (u0..u1, v0..v1) of a quad (TL, TR, BR, BL), bilinear"""
    q = np.asarray(q, np.float32)

    def at(u, v):
        top = q[0] + (q[1] - q[0]) * u
        bot = q[3] + (q[2] - q[3]) * u
        return top + (bot - top) * v
    return np.float32([at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1)])


# ------------------------------------------------------------------ intro-02: teletext on the CRT
I02_SCREEN = [(1177, 137), (1442, 132), (1440, 330), (1177, 340)]
I02_TEXT = ('文字放送　◆天気　潮見地方は今夜も熱帯夜　最低気温二十六度　◆交通　潮見線の上り最終電車は'
            '発車しました　◆あすも晴れ　海は穏やかでしょう　◆')


@functools.lru_cache(maxsize=1)
def _i02_strip():
    from mv import text
    f = text.font('kaku_m', 64)
    w = int(f.measureText(I02_TEXT) + 200)

    def draw(c):
        c.drawString(I02_TEXT, 100, 76, f, _paint('#FFFFFF'))
    return _skia(draw, w, 100)


def intro02(s, t, local):
    img = base(s, t, local)
    strip = _i02_strip()
    tw, th = 820, 100
    off = int(local * 150) % max(1, strip.shape[1] - tw)
    tex = np.empty((th, tw, 3), np.float32)
    tex[:] = H('#173A8A')
    a = strip[:, off:off + tw, 3:4]
    tex = tex * (1 - a) + strip[:, off:off + tw, :3] * a
    tex = fx.crt(tex, t, tint='#DDEEFF', curve=0.0, bloom=0.25)
    img = fx.quad_paste(img, tex, sub_quad(v2.tracked(s, I02_SCREEN, local), 0.04, 0.80, 0.96, 0.95), alpha=0.92, feather=1.0)
    return _dream(img, s, t, local)


RAW['B-intro-02'] = intro02


# ------------------------------------------------------------------ chorus1-05: the scoreboard
C105_PANEL = [(684, 369), (1115, 393), (1115, 598), (684, 592)]
C105_TIMER = [(849, 294), (984, 299), (983, 373), (849, 370)]


@functools.lru_cache(maxsize=16)
def _lane_row(lane, lit):
    from . import print_fx as pf
    txt = f'{lane}　{"君" if lit else "　"}'
    rgb, _ = pf.led_board(txt, cols=60, rows=14, dot=6, on='#FF9A3C', off='#2A1A10', bg='#0A0C14', font='dot', glow=0.6)
    return rgb


def _scoreboard(n_lit):
    rows = [_lane_row(i + 1, i < n_lit) for i in range(8)]
    w = max(r.shape[1] for r in rows)
    gap = 10
    h = sum(r.shape[0] for r in rows) + gap * 9
    img = np.empty((h, w + 2 * gap, 3), np.float32)
    img[:] = H('#0A0C14')
    y = gap
    for r in rows:
        img[y:y + r.shape[0], gap:gap + r.shape[1]] = r
        y += r.shape[0] + gap
    return img


def _lcd_timer(w=540, h=300, melt=0.0, t=0.0):
    from . import print_fx as pf
    g = pf.clock_grid('0:0000', colon_on=True)
    gh, gw = g.shape
    # a decimal point between the seconds and the hundredths: shift the last two digits right by 3 columns
    cut = gw - (7 * 2 + 2)
    g = np.concatenate([g[:, :cut], np.zeros((gh, 3), bool), g[:, cut:]], 1)
    g[gh - 1, cut + 1] = True
    gh, gw = g.shape
    cell = min(w * 0.88 / gw, h * 0.66 / gh)
    img = np.empty((h, w, 3), np.float32)
    img[:] = H('#DCE2D6')
    on = np.zeros((h, w), np.float32)
    ox, oy = (w - gw * cell) / 2, (h - gh * cell) / 2
    for yy in range(gh):
        for xx in range(gw):
            if g[yy, xx]:
                cv2.rectangle(on, (int((ox + xx * cell + cell * 0.08) * 4), int((oy + yy * cell + cell * 0.08) * 4)),
                              (int((ox + (xx + 1) * cell - cell * 0.08) * 4), int((oy + (yy + 1) * cell - cell * 0.08) * 4)),
                              1.0, -1, cv2.LINE_AA, shift=2)
    if melt > 0:                               # the digits run down in the heat
        rng = np.random.default_rng(3)
        dy = cv2.resize(rng.random((1, 24)).astype(np.float32), (w, 1), interpolation=cv2.INTER_CUBIC)[0]
        drop = (0.25 + 0.75 * dy) * melt * h * 0.9
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        acc = on.copy()
        for k in range(1, 9):
            sh = (drop * k / 8)[None, :]
            acc = np.maximum(acc, cv2.remap(on, xs, ys - sh, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) * (1 - k / 12))
        on = acc
        wob = (2.0 * melt * np.sin(ys / 7.0 + t * 9.0)).astype(np.float32)
        on = cv2.remap(on, xs + wob, ys, cv2.INTER_LINEAR)
    img += (H('#1A1C1E') - img) * on[..., None] * 0.92
    return img


def chorus1_05(s, t, local):
    img = base(s, t, local)
    melt = clamp((local - (s['end'] - s['start'] - 1.3)) / 1.2)
    img = fx.quad_paste(img, _lcd_timer(melt=melt, t=t), v2.tracked(s, C105_TIMER, local, box=(684, 294, 1115, 598)),
                        feather=1.0, light=0.5)
    return _dream(img, s, t, local)


def chorus1_05_over(img, s, t, local):
    """the LED lanes over the print; the starting block in front stays in front (keyed on the plate)"""
    nb0 = math.floor((s['start'] - BEAT0) / BEAT + 0.02)
    n_lit = int(clamp(math.floor((t - BEAT0) / BEAT) - nb0, 0, 8))
    board = _scoreboard(n_lit)
    plate = v2.plate(s, local)
    lum = plate @ np.float32([0.2126, 0.7152, 0.0722])
    keep = img.copy()
    pasted = fx.quad_paste(img.copy(), board, v2.tracked(s, C105_PANEL, local, box=(684, 294, 1115, 598)), feather=1.2)
    dark = cv2.GaussianBlur(np.clip((0.42 - lum) / 0.12, 0, 1), (0, 0), 1.2)
    return keep + (pasted - keep) * dark[..., None]


OVER['B-chorus1-05'] = chorus1_05_over
RAW['B-chorus1-05'] = chorus1_05


# ------------------------------------------------------------------ duotone press (the dream, verse-05)
def duotone(raw, inks=('#2C4C9A', '#E8664A'), dots=1.0, light_boost=1.0, skin_clean=False, period=6.5, paper='#EDE3CF',
            key='#1E2550', offsets=((0, 0), (2, -1))):
    """a true two-colour riso: the dark plate carries the tonal range on a 45-degree screen, the warm plate carries
    the warm colours on a 75-degree screen; key lines in the dark plate; laid by multiplication on cream.
    dots=0 replaces the screens by flat posterised solids (the clean print)."""
    from .print2 import screen, dots as hdots
    from .v2_print import _lines, _shift
    y = np.clip(raw @ np.float32([0.2126, 0.7152, 0.0722]), 0, 1)
    small = cv2.resize(raw, (W // 2, H_ // 2), interpolation=cv2.INTER_AREA)
    flat = cv2.bilateralFilter((np.clip(small, 0, 1) * 255).astype(np.uint8), 7, 30, 5).astype(np.float32) / 255
    flat = cv2.resize(flat, (W, H_), interpolation=cv2.INTER_LINEAR)
    fy = np.clip(flat @ np.float32([0.2126, 0.7152, 0.0722]), 0, 1)
    lo, hi = np.percentile(fy[::4, ::4], [2, 99.5])
    fy = np.clip((fy - lo) / max(0.15, hi - lo), 0, 1) ** 0.85            # auto-levels: a full range on every shot
    dark = np.clip((0.90 - fy) / 0.80, 0, 1) ** 1.25
    warm = np.clip((flat[..., 0] - flat[..., 2]) * 2.2 + 0.15 * (1 - fy), 0, 1) * np.clip((fy - 0.08) / 0.2, 0, 1)
    warm = np.clip(warm * light_boost, 0, 1)
    if skin_clean:
        from .print2 import skin_mask_scene
        sm, _ = skin_mask_scene(cv2.resize(flat, (W // 2, H_ // 2)))
        sm = cv2.resize(sm, (W, H_))
        dark = dark * (1 - sm * 0.85)
    rng = np.random.default_rng(5)
    grain = 1 - 0.07 * np.abs(cv2.GaussianBlur(rng.standard_normal((H_, W)).astype(np.float32), (0, 0), 0.8))
    img = np.empty((H_, W, 3), np.float32)
    img[:] = H(paper)
    covs = []
    for tone, ang in ((dark, 45.0), (warm, 75.0)):
        if dots >= 1:
            c = hdots(tone, screen(period, ang), period)
        elif dots <= 0:
            c = np.where(tone > 0.66, 1.0, np.where(tone > 0.33, 0.55, np.where(tone > 0.12, 0.22, 0.0)))
            c = cv2.GaussianBlur(c.astype(np.float32), (0, 0), 0.8)
        else:
            c = hdots(tone, screen(period, ang), period) * dots + np.clip(tone, 0, 1) * (1 - dots) * 0.8
        covs.append(c * grain)
    for c, ink, (dx, dy) in zip(covs, inks, offsets):
        c = _shift(c, dx, dy)
        img *= 1 - c[..., None] * (1 - H(ink))[None, None]
    ln = _lines(raw)
    img *= 1 - ln[..., None] * (1 - H(key))[None, None] * 0.9
    return np.clip(img, 0, 1)


DREAM = ('B-bridge2-01', 'B-bridge2-02', 'B-bridge2-03')


def dream_shot(raw_fn):
    def recipe(s, t, local, fi):
        raw = raw_fn(s, t, local)
        img = duotone(raw)
        fn = v2.OVER.get(s['id'])
        if fn is not None:
            img = fn(img, s, t, local)
        return v2.english_lines(img, s, t)
    return recipe


def bridge2_04_duo(s, t, local, fi):
    """the dream's last shot: the screen on her face is lifted off like a sheet of film; her face clean"""
    from .v2_print import peel
    raw = _dream(base(s, t, local), s, t, local)
    p = clamp((t - 145.05) / 1.55)
    top = duotone(raw)
    if p <= 0:
        return top
    clean = duotone(raw, dots=0.0, skin_clean=True)
    if p >= 1:
        return clean
    return peel(top, clean, p, angle=-30.0, curl=150.0, mode='film')


# ---- verse-05: his cobalt plate lifts off
def verse_05(s, t, local, fi):
    from . import v2_print as vp
    raw = _dream(base(s, t, local), s, t, local)
    masks = vp.split_masks(960)
    full = vp.two_ink(raw, masks)
    p = clamp((t - 68.55) / 1.4)
    if p <= 0:
        return full
    her_only = vp.two_ink(raw, (masks[0], masks[1] * 0.0), bg=0.0, gamma=1.05)
    if p >= 1:
        return her_only
    return vp.peel(full, her_only, p, angle=180.0, curl=160.0, mode='film')


# ------------------------------------------------------------------ chorus3-01: the lanterns light one by one
def lanterns_raw(s, t, local):
    img = base(s, t, local)
    g = gt(38)
    n = sum(1 for x in g if t >= x)
    front = W * n / len(g)
    hsv = cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    h = hsv[..., 0].astype(np.int16)
    m = (((h <= 18) | (h >= 165)) & (hsv[..., 1] > 110) & (hsv[..., 2] > 120)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    nlab, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    unlit = np.zeros((H_, W), np.float32)
    flash = np.zeros((H_, W), np.float32)
    for i in range(1, nlab):
        if st[i, cv2.CC_STAT_AREA] < 150:
            continue
        cx = cen[i][0]
        if cx > front:
            unlit[lab == i] = 1.0
        else:
            j = min(len(g) - 1, int(cx / W * len(g)))
            k = (t - g[j]) / 0.35
            if 0 <= k < 1:
                flash[lab == i] = 1 - k
    unlit = cv2.GaussianBlur(cv2.dilate(unlit, np.ones((9, 9), np.uint8)), (0, 0), 3)
    y = img @ np.float32([0.2126, 0.7152, 0.0722])
    dimmed = (y * 0.32)[..., None] * H('#6A4A52')[None, None] * 1.6
    img = img * (1 - unlit[..., None]) + dimmed * unlit[..., None]
    fl = cv2.GaussianBlur(flash, (0, 0), 14) * 1.2 + flash * 0.5
    img = img + H('#FFD9A0')[None, None] * fl[..., None] * 0.5
    return _dream(img, s, t, local)


RAW['B-chorus3-01'] = lanterns_raw


# ------------------------------------------------------------------ chorus3-04: goldfish
# a school of goldfish fry (hundreds of tiny fish among the big ones of the footage) gathers into 幸せ; the poi in
# the tank dips at 幸, the paper tears with a splash on あげ, and the fry scatter from it
C304_POI = (1530.0, 262.0)


@functools.lru_cache(maxsize=1)
def _fish_init(n=1300):
    from .v2_typo import glyph_points
    rng = np.random.default_rng(41)
    tgt = glyph_points('幸せ', 540, n, name='mincho', seed=4) + np.float32([900, 560])
    start = np.stack([rng.uniform(80, W - 80, n), rng.uniform(80, H_ - 80, n)], 1).astype(np.float32)
    phase = rng.uniform(0, 2 * math.pi, n)
    kind = rng.random(n)
    return tgt, start, phase, kind


def _fish_pos(t):
    tgt, start, phase, kind = _fish_init()
    g = gt(41)
    t_in, t_tear = g[2], g[7]
    wander = np.stack([np.sin(t * 0.9 + phase) * 90 + np.sin(t * 1.7 + phase * 2) * 30,
                       np.cos(t * 0.8 + phase * 1.3) * 70], 1).astype(np.float32)
    free = start + wander
    k = clamp((t - (t_in - 0.7)) / 1.0)
    k = k * k * (3 - 2 * k)
    p = free + (tgt + 3 * np.stack([np.sin(t * 4 + phase), np.cos(t * 3.4 + phase)], 1) - free) * k
    sc = clamp((t - t_tear) / 0.8)
    if sc > 0:
        d = p - np.float32(C304_POI)
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-3
        p = p + d * (sc ** 0.55) * 640
    return p


def _draw_fish(layer, alpha, p, prev, kind, outline=False):
    for (x, y), (px, py), kd in zip(p, prev, kind):
        a = math.degrees(math.atan2(y - py, x - px)) if (abs(x - px) + abs(y - py)) > 0.2 else (kd * 360.0)
        col = (0.97, 0.94, 0.86) if kd < 0.70 else ((0.98, 0.62, 0.22) if kd < 0.90 else (0.90, 0.20, 0.12))
        L, Wd = 13, 5
        if outline:
            cv2.ellipse(layer, ((float(x), float(y)), (L + 3, Wd + 3), a), (0.16, 0.08, 0.06), -1, cv2.LINE_AA)
            cv2.ellipse(alpha, ((float(x), float(y)), (L + 3, Wd + 3), a), 1.0, -1, cv2.LINE_AA)
        cv2.ellipse(layer, ((float(x), float(y)), (L, Wd), a), col, -1, cv2.LINE_AA)
        cv2.ellipse(alpha, ((float(x), float(y)), (L, Wd), a), 1.0, -1, cv2.LINE_AA)
        ar = math.radians(a)
        bx, by = x - math.cos(ar) * L * 0.45, y - math.sin(ar) * L * 0.45
        tail = np.float32([[bx, by], [bx - math.cos(ar - 0.7) * 8, by - math.sin(ar - 0.7) * 8],
                           [bx - math.cos(ar + 0.7) * 8, by - math.sin(ar + 0.7) * 8]])
        cv2.fillPoly(layer, [np.round(tail * 4).astype(np.int32)], col, cv2.LINE_AA, shift=2)
        cv2.fillPoly(alpha, [np.round(tail * 4).astype(np.int32)], 0.8, cv2.LINE_AA, shift=2)


def goldfish_raw(s, t, local):
    img = base(s, t, local)
    g = gt(41)
    # her face on the water (the one looking down into the tank), faint, rippling
    from .v2_shots import her
    face = her('turn', 0.4 + local * 0.5)
    if face is not None:
        f = cv2.resize(face, (760, 760), interpolation=cv2.INTER_AREA)[:, ::-1]
        ys, xs = np.mgrid[0:760, 0:760].astype(np.float32)
        f = cv2.remap(f, xs + 4 * np.sin(ys / 13 + t * 3), ys + 3 * np.sin(xs / 17 + t * 2.4), cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_REFLECT)
        m = np.clip(1 - np.hypot(xs - 380, ys - 380) / 380, 0, 1) ** 1.2 * 0.20
        x0, y0 = 930 - 380, 560 - 380
        roi = img[y0:y0 + 760, x0:x0 + 760]
        roi += (f * 1.1 - roi) * m[..., None] * np.float32([0.9, 1.0, 1.1])
    p, prev = _fish_pos(t), _fish_pos(t - 1 / 24)
    _, _, _, kind = _fish_init()
    sl = np.zeros((H_, W, 3), np.float32)
    sa = np.zeros((H_, W), np.float32)
    _draw_fish(sl, sa, p + np.float32([6, 10]), prev + np.float32([6, 10]), kind)
    img *= 1 - np.clip(cv2.GaussianBlur(sa, (0, 0), 7) * 1.6, 0, 1)[..., None] * 0.55   # the school's shadow (printed)
    # the poi dips on 幸 (rings spread from it) and tears with a splash on あげ
    ys, xs = _grid()
    px, py = C304_POI
    rr = np.hypot(xs - px, ys - py)
    for t0, amp in ((g[3], 0.18), (g[7], 0.32)):
        k = t - t0
        if 0 <= k < 1.4:
            ring = np.exp(-((rr - 40 - k * 420) / 7.0) ** 2) + 0.6 * np.exp(-((rr - 20 - k * 300) / 6.0) ** 2)
            img += ring[..., None] * H('#FFFFFF')[None, None] * amp * (1 - k / 1.4)
    k = t - g[7]
    if 0 <= k < 0.5:                                   # the splash: white droplets out of the torn paper
        rng = np.random.default_rng(12)
        m = np.zeros((H_, W), np.float32)
        for j in range(60):
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(20, 150) * (0.3 + k * 2.2)
            r = max(1, int(rng.uniform(2, 6) * (1 - k * 1.6)))
            cv2.circle(m, (int((px + math.cos(a) * d) * 4), int((py + math.sin(a) * d) * 4)), r * 4, 1.0, -1, cv2.LINE_AA, shift=2)
        img += (H('#F4FAFF')[None, None] - img) * (m * (1 - k / 0.5))[..., None]
    return _dream(img, s, t, local)


RAW['B-chorus3-04'] = goldfish_raw


def goldfish_over(img, s, t, local):
    """the fry themselves, crisp over the print (small enough that the press would melt them)"""
    p, prev = _fish_pos(t), _fish_pos(t - 1 / 24)
    _, _, _, kind = _fish_init()
    layer = np.zeros((H_, W, 3), np.float32)
    alpha = np.zeros((H_, W), np.float32)
    _draw_fish(layer, alpha, p, prev, kind, outline=True)
    return img * (1 - alpha[..., None]) + layer * alpha[..., None]


OVER['B-chorus3-04'] = goldfish_over


# ------------------------------------------------------------------ chorus3-05 / 06: fireworks
FW05 = [(0, 520, 300, '#F5C842', '#FF7A3C', None), (1, 1400, 260, '#9FE0FF', '#5FA0FF', None),
        (2, 900, 220, '#FF9AC2', '#E8506A', None)]
FW06 = [(1, 480, 260, '#F5C842', '#FF7A3C', None), (3, 1500, 300, '#FF9AC2', '#E8506A', None)]


def _bursts(sid):
    s = v2.tl.BY_ID[sid]
    nb0 = math.floor((s['start'] - BEAT0) / BEAT + 0.02)
    if sid == 'B-chorus3-05':
        out = [(BEAT0 + (nb0 + 1 + j) * BEAT, x, y, c1, c2, g) for j, x, y, c1, c2, g in FW05]
        out.append((gt(42)[6] - 0.42, 960, 400, '#FFE9A8', '#FF8A3C', '君'))
    else:
        out = [(BEAT0 + (nb0 + 1 + j) * BEAT, x, y, c1, c2, g) for j, x, y, c1, c2, g in FW06]
        out.append((gt(43)[2] - 0.40, 600, 300, '#BFF0FF', '#5FA0FF', '0:00'))
    return out


def fireworks_raw(s, t, local):
    img = base(s, t, local)
    for t0, x, y, c1, c2, g in _bursts(s['id']):
        k = t - t0
        if 0 <= k < 0.9:
            img = img + H(c2)[None, None] * (0.22 * math.exp(-k * 4.5))
    return _dream(img, s, t, local)


def fireworks_over(img, s, t, local):
    from .v2_typo import firework
    for i, (t0, x, y, c1, c2, g) in enumerate(_bursts(s['id'])):
        if g is None:
            img = firework(img, t, t0, x, y, radius=300, n=900, col=c1, col2=c2, seed=i + 11, dur=1.8)
        else:
            img = firework(img, t, t0, x, y, radius=360, col=c1, col2=c2, glyph=g, gsize=430 if g == '君' else 300,
                           seed=i + 21, dur=2.6)
    return img


for _sid in ('B-chorus3-05', 'B-chorus3-06'):
    RAW[_sid] = fireworks_raw
    OVER[_sid] = fireworks_over


# ------------------------------------------------------------------ chorus3-08: willow lyric
def willow_over(img, s, t, local):
    from .v2_typo import willow
    return willow(img, 45, t, x0=1700, y0=110, size=74)


OVER['B-chorus3-08'] = willow_over
OWN.add('B-chorus3-08')


# ------------------------------------------------------------------ boards on the train (bridge2-01, chorus4-05)
def detect_board(rgb, prev=None):
    """the orange dot-matrix destination board: bright orange glyph blobs on one line, merged; (x0, y0, x1, y1)"""
    hsv = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    h = hsv[..., 0].astype(np.int16)
    m = ((h >= 4) & (h <= 26) & (hsv[..., 1] > 120) & (hsv[..., 2] > 170)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 11), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    blobs = [tuple(st[i][:5]) for i in range(1, n) if st[i][4] >= 40 and st[i][4] >= 0.4 * st[i][2] * st[i][3]]
    best, score = None, 0.0
    for (x, y, w, hh, a) in blobs:
        # grow along the line: neighbours of similar height, vertically overlapping, close horizontally
        x0, y0, x1, y1, area = x, y, x + w, y + hh, a
        changed = True
        while changed:
            changed = False
            for (bx, by, bw, bh, ba) in blobs:
                if bx >= x0 and bx + bw <= x1:
                    continue
                ov = min(y1, by + bh) - max(y0, by)
                gap = max(bx - x1, x0 - (bx + bw))
                if ov > 0.5 * min(y1 - y0, bh) and gap < 1.6 * (y1 - y0) and 0.5 < bh / max(1, y1 - y0) < 2.0:
                    x0, y0, x1, y1 = min(x0, bx), min(y0, by), max(x1, bx + bw), max(y1, by + bh)
                    area += ba
                    changed = True
        w2, h2 = x1 - x0, y1 - y0
        if w2 < 1.8 * h2 or w2 < 30:
            continue
        sc = area * (1.0 if prev is None else math.exp(-math.hypot((x0 + x1) / 2 - prev[0], (y0 + y1) / 2 - prev[1]) / 200))
        if sc > score:
            best, score = (int(x0), int(y0), int(x1), int(y1)), sc
    return best


def board_track(sid2):
    f = v2.footage(sid2)
    src = v2.clip_path(sid2) or v2.kf_path(sid2)
    key = os.path.join(v2.WORK2, sid2, f'track_board_{int(os.path.getmtime(src))}.json')
    from .atomic import load_json, save_json
    got = load_json(key) if os.path.exists(key) else None
    if got is not None:
        return got
    fps = getattr(getattr(f, 'c', None), 'fps', 16.0)
    n = max(1, int(round(f.dur * fps))) if hasattr(f, 'c') else 1
    out, prev = [], None
    for i in range(n):
        rgb = f.at(i / fps) if hasattr(f, 'c') else f.img
        b = detect_board(rgb, prev)
        out.append(list(b) if b else None)
        if b:
            prev = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    good = [o for o in out if o]
    if good:
        last = good[0]
        for i in range(n):
            out[i] = out[i] or last
            last = out[i]
        a = fx._gauss1d(np.array(out, np.float32), 1.5)
        out = a.tolist()
    save_json(key, out)
    return out


def board_at(s, local):
    sid2 = v2.b2_id(s)
    tr = board_track(sid2)
    if not tr or tr[0] is None:
        return None
    f = v2.footage(sid2)
    if not hasattr(f, 'c'):
        return tr[0]
    d = s['end'] - s['start']
    sp = min(1.0, max(0.55, (f.dur - 0.13) / d))
    i = int(round((0.08 + local * sp) * f.c.fps))
    return tr[min(len(tr) - 1, max(0, i))]


@functools.lru_cache(maxsize=16)
def _board_img(txt):
    from . import print_fx as pf
    rgb, _ = pf.led_board(txt, rows=12, dot=8, on='#FF9A3C', off='#3A1A10', bg='#140A06', font='dot', glow=0.7)
    return rgb


def put_board(img, box, txt, scroll=None):
    if box is None:
        return img
    x0, y0, x1, y1 = box
    pad = 0.08 * (x1 - x0)
    board = _board_img(txt)
    bh, bw = board.shape[:2]
    aw = int(bh * (x1 - x0 + 2 * pad) / max(1.0, (y1 - y0)))
    if scroll is not None and bw > aw:
        off = int(scroll * (bw - aw))
        board = board[:, off:off + aw]
    elif bw < aw:
        padw = (aw - bw) // 2
        board = cv2.copyMakeBorder(board, 0, 0, padw, aw - bw - padw, cv2.BORDER_CONSTANT, value=tuple(float(c) for c in H('#140A06')))
    q = [(x0 - pad, y0 - 2), (x1 + pad, y0 - 2), (x1 + pad, y1 + 2), (x0 - pad, y1 + 2)]
    return fx.quad_paste(img, board, q, feather=1.2)


def strip_box(img, box):
    """inpaint a small region (fake captions / watermarks the model drew)"""
    x0, y0, x1, y1 = box
    pad = 12
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H_, y1 + pad)
    roi = (np.clip(img[Y0:Y1, X0:X1], 0, 1) * 255).astype(np.uint8)
    m = np.zeros(roi.shape[:2], np.uint8)
    m[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = 255
    fixed = cv2.inpaint(roi, m, 6, cv2.INPAINT_TELEA).astype(np.float32) / 255.0
    out = img.copy()
    out[Y0:Y1, X0:X1] = fixed
    return out


B201_CAPTION = (0, 1032, 475, 1072)


def bridge2_01_raw(s, t, local):
    img = strip_box(base(s, t, local), B201_CAPTION)
    box = board_at(s, local)
    if box is not None:                                        # into the frame (the shot's camera, a still's zoom)
        q = v2.frame_map(s, local)([(box[0], box[1]), (box[2], box[3])])
        box = (float(q[0, 0]), float(q[0, 1]), float(q[1, 0]), float(q[1, 1]))
    if local < 1.3:
        img = put_board(img, box, '夢　行')
    else:
        img = put_board(img, box, '　　君はどんな夢のなかに　　', scroll=clamp((local - 1.3) / 1.5))
    return _dream(img, s, t, local)


RAW['B-bridge2-01'] = bridge2_01_raw


C405_BOARD = (899, 208, 1041, 274)           # the destination board on the car's front (picked keyframe)


def chorus4_05_raw(s, t, local):
    img = base(s, t, local)
    q = v2.tracked_box(s, C405_BOARD, local)                         # the train approaches: the board grows
    box = (float(q[:, 0].min()), float(q[:, 1].min()), float(q[:, 0].max()), float(q[:, 1].max()))
    g = gt(54)
    flip = clamp((t - g[4]) / 0.25)
    if flip <= 0:
        img = put_board(img, box, '夢')
    elif flip < 1:
        if box is not None:
            x0, y0, x1, y1 = box
            k = abs(1 - 2 * flip)
            yc = (y0 + y1) / 2
            box2 = (x0, yc - (yc - y0) * k, x1, yc + (y1 - yc) * k)
            img = put_board(img, box2, '夢' if flip < 0.5 else '日の出')
    else:
        img = put_board(img, box, '日の出')
    return _dream(img, s, t, local)


def chorus4_05_over(img, s, t, local):
    """the headlight's halo swells on every beat until it floods the frame"""
    d = s['end'] - s['start']
    f = v2.footage(v2.b2_id(s))
    rgb = v2.plate(s, local)
    y = cv2.GaussianBlur(rgb @ np.float32([0.2126, 0.7152, 0.0722]), (0, 0), 9)
    _, mx, _, (lx, ly) = cv2.minMaxLoc(y)
    nb = (t - BEAT0) / BEAT
    ph = nb - math.floor(nb)
    k = clamp(local / d)
    R = 120 + 900 * k ** 2 + 90 * math.exp(-ph * 5)
    ys, xs = _grid()
    r = np.hypot(xs - lx, ys - ly)
    tone = np.clip(np.exp(-(r / R) ** 2) * (0.45 + 0.55 * k), 0, 1)
    per = 9.0 + 6 * k
    u, v = (xs + ys) / (per * 1.4142), (xs - ys) / (per * 1.4142)
    dd = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    m = np.clip((np.sqrt(tone) * 0.70 - dd) * 5 + 0.5, 0, 1) * (tone > 0.02)
    img = img + (H('#FFE7A8')[None, None] - img) * (m * 0.8)[..., None]
    wk = clamp((local - (d - 0.45)) / 0.45)
    if wk > 0:
        img = img + (H('#FFF4DC')[None, None] - img) * (wk ** 1.5)
    return img


RAW['B-chorus4-05'] = chorus4_05_raw
OVER['B-chorus4-05'] = chorus4_05_over


# ------------------------------------------------------------------ bridge2-02: the zoetrope train
ZW, ZH, ZP, ZY, ZR = 404, 330, 476, 286, 30            # window size, pitch, top, corner radius (px)
Z_X0 = (W - 4 * ZP) // 2 + (ZP - ZW) // 2


@functools.lru_cache(maxsize=1)
def zoetrope_body():
    """the side of the car, drawn once (it seems to stand still): RGBA with clear window openings"""
    import skia
    surf = skia.Surface(W, H_)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))

    def P(col, a=1.0, stroke=0.0):
        p = _paint(col, a)
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style)
            p.setStrokeWidth(stroke)
        return p
    top, belt0, belt1, bot = 150, 700, 732, 930
    # body: upper panel lighter, lower panel darker
    c.drawRect(skia.Rect.MakeLTRB(0, top, W, belt0), P('#4865B0'))
    c.drawRect(skia.Rect.MakeLTRB(0, belt1, W, bot), P('#2E4688'))
    c.drawRect(skia.Rect.MakeLTRB(0, belt0, W, belt1), P('#E9DEC6'))
    c.drawRect(skia.Rect.MakeLTRB(0, top - 26, W, top + 8), P('#1E2C5C'))
    c.drawLine(0, top + 12, W, top + 12, P('#7F9AD8', 1.0, 2.5))
    c.drawLine(0, bot - 4, W, bot - 4, P('#16204A', 1.0, 8))
    for k in range(-1, 6):                                 # panel seams + rivets between the windows
        x = Z_X0 - (ZP - ZW) / 2 + k * ZP
        c.drawLine(x, top + 20, x, bot - 10, P('#2B417F', 1.0, 3))
        for yy in range(top + 40, belt0 - 10, 34):
            c.drawCircle(x - 9, yy, 3.2, P('#8DA6E0'))
            c.drawCircle(x + 9, yy, 3.2, P('#8DA6E0'))
    c.drawRoundRect(skia.Rect.MakeXYWH(W / 2 - 92, belt1 + 40, 184, 56), 8, 8, P('#E9DEC6'))
    from mv import text
    f = text.font('mincho', 34)
    c.drawString('モハ 五〇一', W / 2 - f.measureText('モハ 五〇一') / 2, belt1 + 80, f, P('#1E2550'))
    # windows: chrome frame, then cut the openings
    for j in range(-1, 5):
        x0 = Z_X0 + j * ZP
        r = skia.Rect.MakeXYWH(x0 - 10, ZY - 10, ZW + 20, ZH + 20)
        c.drawRoundRect(r, ZR + 8, ZR + 8, P('#1A2550'))
        c.drawRoundRect(skia.Rect.MakeXYWH(x0 - 5, ZY - 5, ZW + 10, ZH + 10), ZR + 4, ZR + 4, P('#A9BCE6', 1.0, 3))
    clear = skia.Paint(AntiAlias=True)
    clear.setBlendMode(skia.BlendMode.kClear)
    for j in range(-1, 5):
        x0 = Z_X0 + j * ZP
        c.drawRoundRect(skia.Rect.MakeXYWH(x0, ZY, ZW, ZH), ZR, ZR, clear)
    for j in range(-1, 5):                                 # the sash bar across each window (two-part windows)
        x0 = Z_X0 + j * ZP
        c.drawRect(skia.Rect.MakeXYWH(x0, ZY + ZH * 0.42, ZW, 14), P('#1A2550'))
        c.drawLine(x0, ZY + ZH * 0.42 + 2, x0 + ZW, ZY + ZH * 0.42 + 2, P('#A9BCE6', 1.0, 2))
    # the platform edge in the foreground: dark, with the coral safety line
    c.drawRect(skia.Rect.MakeLTRB(0, 960, W, H_), P('#151B33'))
    c.drawRect(skia.Rect.MakeLTRB(0, 968, W, 986), P('#F2C23A'))
    for x in range(0, W, 46):
        c.drawCircle(x + 23, 977, 4, P('#B8901E'))
    arr = np.empty((H_, W, 4), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(W, H_, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kUnpremul_AlphaType), arr, W * 4)
    return arr.astype(np.float32) / 255.0


@functools.lru_cache(maxsize=1)
def zoetrope_back():
    ys, xs = _grid()
    img = np.empty((H_, W, 3), np.float32)
    sky = H('#0E1838')[None, None] + (H('#2A3C78') - H('#0E1838'))[None, None] * np.clip(1 - ys / 160, 0, 1)[..., None]
    img[:] = sky
    cv2.circle(img, (250, 70), 52, tuple(float(c) for c in H('#F3E7C2')), -1, cv2.LINE_AA)
    img[930:960] = H('#0B0F22')
    return img


def zoetrope_raw(s, t, local):
    src = v2.footage(v2.b2_id(s))
    fi = int(round(t * 24))
    img = zoetrope_back().copy()
    interior = np.zeros((H_, W, 3), np.float32)
    for j in range(-1, 5):
        x0 = Z_X0 + j * ZP
        xa, xb = max(0, x0), min(W, x0 + ZW)
        if xb <= xa:
            continue
        tt = (0.3 + local * 0.55 + (j + fi) * 0.11) % max(0.5, src.dur - 0.2)
        frame = src.at(tt)
        crop = frame[40:1000, 560:1740]                              # her face and the hand under her cheek
        win = cv2.resize(crop, (ZW, ZH), interpolation=cv2.INTER_AREA) * np.float32([1.10, 0.98, 0.82])
        sheen = np.clip(1 - np.abs((np.arange(ZW)[None, :] - np.arange(ZH)[:, None] * 0.8 - ZW * 0.28) / 36.0), 0, 1) * 0.14
        win = win + sheen[..., None]
        interior[ZY:ZY + ZH, xa:xb] = win[:, xa - x0:xb - x0]
    body = zoetrope_body()
    a = body[..., 3:4]
    img = img * (1 - a) + body[..., :3] * a
    hole = (1 - a)
    hole[:ZY - 12] = 0
    hole[ZY + ZH + 12:] = 0
    img = img * (1 - hole) + interior * hole
    # warm light from the windows on the platform edge and the lower body
    lit = np.zeros((H_, W), np.float32)
    for j in range(-1, 5):
        x0 = Z_X0 + j * ZP
        quad = np.float32([[x0 + 20, ZY + ZH + 20], [x0 + ZW - 20, ZY + ZH + 20], [x0 + ZW + 60, 1080], [x0 - 60, 1080]])
        cv2.fillPoly(lit, [np.round(quad * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
    lit = cv2.GaussianBlur(lit, (0, 0), 30) * 0.22 * (0.9 + 0.1 * math.sin(fi * 1.7))
    img = img + lit[..., None] * np.float32([1.0, 0.75, 0.45])
    jy = int(round(math.sin(fi * 2.1) * 1.2))              # the car rocks a little on the rail joints
    return np.roll(img, jy, axis=0)


RAW['B-bridge2-02'] = zoetrope_raw


# ------------------------------------------------------------------ chorus4-02: the night flies by
def chorus4_02_over(img, s, t, local):
    d = s['end'] - s['start']
    k = clamp((local - 0.25) / (d - 0.85))
    e = k * k * (3 - 2 * k)
    mins = int(round(292 * e))
    txt = f'{mins // 60}:{mins % 60:02d}'
    colon = (local * 2) % 2 < 1 or k >= 1
    face = fx.led_face(txt if colon else txt.replace(':', ' '), 500, 170, on='#FF3B2A', off='#2A0806', bg='#0B0404', glow=0.8)
    a = clamp(local / 0.25) * (1 - clamp((local - (d - 0.2)) / 0.2))
    q = [(1150, 190), (1650, 190), (1650, 360), (1150, 360)]
    img = fx.quad_paste(img, face, q, alpha=0.95 * a, feather=2.0)
    ys, xs = _grid()
    g = np.exp(-(((xs - 1400) / 360) ** 2 + ((ys - 275) / 150) ** 2)) * 0.18 * a
    return img + H('#FF3B2A')[None, None] * g[..., None]


OVER['B-chorus4-02'] = chorus4_02_over


# ------------------------------------------------------------------ outro-05: a moment of her in each mirror, one per beat
OUT05_SRC = ['turn', 'stand', 'run', 'pool', 'turn', 'stand']


@functools.lru_cache(maxsize=4)
def mirror_hints(sid2, n=6, min_r=30):
    f = v2.footage(sid2)
    rgb = f.at(0.0) if hasattr(f, 'c') else f.img
    found = fx.detect_mirrors(rgb, min_r=min_r, max_n=n)
    return [((float(e[0][0]), float(e[0][1])), (float(e[1][0]), float(e[1][1])), float(e[2])) for e in found]


OUT05_HINTS = [((475, 346), (359, 460), 0.0), ((890, 423), (255, 379), 0.0), ((1200, 477), (192, 300), 0.0),
               ((1393, 507), (147, 240), 0.0), ((1577, 540), (113, 214), 0.0), ((1728, 567), (90, 200), 0.0)]


def outro_05(s, t, local):
    from .v2_shots import mirrors_at, insert_in, her
    img = base(s, t, local)
    plate = img.copy()
    hints = OUT05_HINTS
    if not hints:
        return _dream(img, s, t, local)
    order = sorted(range(len(hints)), key=lambda j: hints[j][0][0])
    nb0 = math.floor((s['start'] - BEAT0) / BEAT + 0.02)
    for rank, (j, (ell, conf)) in enumerate(sorted(enumerate(mirrors_at(v2.b2_id(s), hints, s, local)),
                                                   key=lambda e: order.index(e[0]))):
        on = BEAT0 + (nb0 + 1 + rank) * BEAT
        k = t - on
        if k < 0 or k > BEAT * 1.2:
            continue
        a = clamp((conf - 0.35) / 0.3) * clamp(k / 0.06) * (1 - clamp((k - BEAT * 0.5) / (BEAT * 0.7)))
        img = insert_in(img, plate, ell, her(OUT05_SRC[rank % len(OUT05_SRC)], 0.5 + rank * 0.4), alpha=a,
                        rip=6.0 * math.exp(-k * 3.0), t=t)
    return _dream(img, s, t, local)


RAW['B-outro-05'] = outro_05


# ------------------------------------------------------------------ outro_hook-02: in the mirror she walks into the haze
def outro_hook_02(s, t, local):
    from .v2_shots import mirrors_at, insert_in, her
    img = base(s, t, local)
    plate = img.copy()
    hints = mirror_hints(v2.b2_id(s), n=1, min_r=80)
    if not hints:
        return _dream(img, s, t, local)
    d = s['end'] - s['start']
    (ell, conf), = mirrors_at(v2.b2_id(s), hints[:1], s, local)
    turn_t = d - 0.95
    src = her('run', 0.2 + local * 0.9) if local < turn_t else her('turn', 0.3 + (local - turn_t) * 0.8)
    if src is not None:
        ys, xs = np.mgrid[0:src.shape[0], 0:src.shape[1]].astype(np.float32)
        amp = 3 + 4 * clamp(local / d)
        src = cv2.remap(src, xs + amp * np.sin(ys / 11.0 + t * 7.0), ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    a = clamp((conf - 0.35) / 0.3) * clamp(local / 0.3) * (1 - clamp((local - (d - 0.25)) / 0.25))
    img = insert_in(img, plate, ell, src, alpha=a, k=0.3)
    return _dream(img, s, t, local)


RAW['B-outro_hook-02'] = outro_hook_02


LYRIC.update({'B-chorus3-02': dict(x=200, y=150), 'B-chorus3-03': dict(x=1760), 'B-chorus3-07': dict(x=200, y=150)})


def _moon_size(sid2):
    def fn(s, local):
        from .v2_b1 import find_moon
        cx, cy, r = find_moon(sid2)
        return cx, cy, 2 * r
    return fn


def install():
    from .v2_shots import pull_out
    v2.CAM['B-chorus2-01'] = pull_out(_moon_size('B2-chorus2-01'))   # out of the moon (from verse-07's test card)
    v2.RAW.update(RAW)
    v2.OVER.update(OVER)
    v2.V2_OWN_TYPE.update(OWN)
    v2.LYRIC_POS.update(LYRIC)
    v2.ENGLISH.update(ENGLISH_OVR)
    foot = {'B-verse-05': verse_05, 'B-bridge2-04': bridge2_04_duo}
    for sid in DREAM:
        foot[sid] = dream_shot(v2.RAW.get(sid, lambda s, t, l: _dream(base(s, t, l), s, t, l)))
    for sid, fn in foot.items():
        s = v2.tl.BY_ID[sid]
        if v2.clip_path(v2.b2_id(s)) or (v2.STANDIN and v2.kf_path(v2.b2_id(s))):
            v2.GRAPHIC[sid] = fn


# ------------------------------------------------------------------ outro-04: the morning pool -- the 君s go out, English scrolls
def detect_panel(rgb, y_max=0.62, min_area=12000):
    """the big dark scoreboard panel: the largest dark, low-saturation, roughly rectangular blob in the upper part"""
    hsv = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 2] < 80) & (hsv[..., 1] < 140)).astype(np.uint8)
    m[int(H_ * y_max):] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, ba = None, 0
    for c in cs:
        a = cv2.contourArea(c)
        if a < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if a < 0.6 * w * h or w < 1.2 * h:
            continue
        if a > ba:
            best, ba = c, a
    if best is None:
        return None
    return fx._quad(best)


O04_PANEL = [(694, 174), (1256, 174), (1256, 376), (694, 376)]       # measured on the picked keyframe


def o04_panel():
    return O04_PANEL


def outro_04_over(img, s, t, local):
    q = o04_panel()
    if q is None:
        return img
    from . import print_fx as pf
    nb0 = math.floor((s['start'] - BEAT0) / BEAT + 0.02)
    k = math.floor((t - BEAT0) / BEAT) - nb0
    n_lit = int(clamp(8 - k, 0, 8))
    if k < 4:
        board = _scoreboard(n_lit)
    else:
        txt = "CAN'T MAKE YOU HAPPIER NOW"
        rgb, _ = pf.led_board('   ' + txt + '   ', rows=14, dot=6, on='#FF9A3C', off='#2A1A10', bg='#0A0C14', font='silk', glow=0.6)
        ref = _scoreboard(0)
        bw = ref.shape[1]
        off = int(clamp((t - (BEAT0 + (nb0 + 4) * BEAT)) / (s['end'] - (BEAT0 + (nb0 + 4) * BEAT))) * max(1, rgb.shape[1] - bw))
        row = rgb[:, off:off + bw]
        board = ref.copy()
        y0 = (board.shape[0] - row.shape[0]) // 2
        board[y0:y0 + row.shape[0], :row.shape[1]] = row
    plate = v2.plate(s, local)
    lum = plate @ np.float32([0.2126, 0.7152, 0.0722])
    keep = img.copy()
    pasted = fx.quad_paste(img.copy(), board, v2.tracked(s, q, local), feather=1.2)
    dark = cv2.GaussianBlur(np.clip((0.42 - lum) / 0.12, 0, 1), (0, 0), 1.2)
    return keep + (pasted - keep) * dark[..., None]


OVER['B-outro-04'] = outro_04_over


# ------------------------------------------------------------------ chorus4-04: the machine at dawn
C404_PANEL = (1232, 662, 1376, 780)          # the light panel under the product window: roulette + ticker
C404_GLASS = (1225, 352, 1522, 628)          # the product window


@functools.lru_cache(maxsize=1)
def _c404_ticker():
    from . import print_fx as pf
    rgb, _ = pf.led_board('　　君に幸せあげられない　　ざんねん　　', rows=12, dot=4, on='#FF8A3A', off='#2A1208', bg='#100804',
                          font='dot', glow=0.5)
    return rgb


def chorus4_04_raw(s, t, local):
    """his reflection walks across the machine's glass (from his walk on the seawall), faint and cool"""
    img = base(s, t, local)
    f = v2.footage('B2-chorus4-03')
    if f is not None:
        fr = f.at(0.5 + local * 0.6)
        crop = fr[200:1080, 1150:1650][:, ::-1]                      # him, mirrored
        x0, y0, x1, y1 = C404_GLASS
        gw, gh = x1 - x0, y1 - y0
        k = clamp(local / (s['end'] - s['start']))
        h = int(gh * 1.25)
        w = int(h * crop.shape[1] / crop.shape[0])
        fig = cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA)
        fig = cv2.GaussianBlur(fig, (0, 0), 1.6)
        lum = fig @ np.float32([0.2126, 0.7152, 0.0722])
        px = int(x0 - w * 0.6 + (gw + w * 0.2) * k)
        py = y0 - int(h * 0.08)
        layer = np.zeros((H_, W), np.float32)
        xa, xb = max(x0, px), min(x1, px + w)
        ya, yb = max(y0, py), min(y1, py + h)
        if xb > xa and yb > ya:
            dark = 1 - lum[ya - py:yb - py, xa - px:xb - px]
            layer[ya:yb, xa:xb] = np.clip(dark - 0.35, 0, 1) * 0.55
            layer = cv2.GaussianBlur(layer, (0, 0), 1.2)
            img = img * (1 - layer[..., None] * 0.55) + H('#2A3A6A')[None, None] * (layer * 0.55)[..., None]
    return _dream(img, s, t, local)


def chorus4_04_over(img, s, t, local):
    x0, y0, x1, y1 = C404_PANEL
    ym = (y0 + y1) // 2
    g = gt(53)
    stops = [g[1], g[3], g[5], g[7]]
    digs = ''
    for j, ts in enumerate(stops):
        digs += '7776'[j] if t >= ts else str(int(t * 29 + j * 3) % 10)
    face = fx.led_face(digs, x1 - x0, ym - y0, on='#FF3B2A', glow=0.5)
    img = fx.quad_paste(img, face, v2.tracked(s, [(x0, y0), (x1, y0), (x1, ym), (x0, ym)], local, box=C404_PANEL), feather=1.0)
    board = _c404_ticker()
    bh, bw = board.shape[:2]
    win = int((x1 - x0) * bh / (y1 - ym))
    off = int(local * 120) % max(1, bw - win)
    img = fx.quad_paste(img, board[:, off:off + win], v2.tracked(s, [(x0, ym), (x1, ym), (x1, y1), (x0, y1)], local, box=C404_PANEL),
                        feather=1.0)
    return img


RAW['B-chorus4-04'] = chorus4_04_raw
OVER['B-chorus4-04'] = chorus4_04_over

"""MV-A per-shot composites (design/mv_a/shots.json `composite` / `transition_out`).

Regions inside the generated plates (glass, CRT screen, clock, calendar, window pane, puddle, feet, head ...)
come from design/mv_a/regions.json, filled after looking at the keyframes; the defaults below are placeholders.
Curve mirrors are found per frame by their orange rim (find_disc), so they need no hand tracking.

  from mva import timeline as tl, recipes        # importing registers the recipes into tl.RECIPES
  img = tl.render(t, frame_idx)
"""
import json
import math
import os

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import BEAT
from . import fx
from . import timeline as tl

W, H = fx.W, fx.H
REG_PATH = os.path.join(tl.ROOT, 'design', 'mv_a', 'regions.json')
_REG = None
_cache = {}


def REG(sid, key, default):
    """region lookup: design/mv_a/regions.json -> {shot: {key: value}}"""
    global _REG
    if _REG is None:
        _REG = json.load(open(REG_PATH)) if os.path.exists(REG_PATH) else {}
    v = _REG.get(sid, {}).get(key)
    return default if v is None else v


def once(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def plate(s, local, **kw):
    """this shot's footage per its `use` field (in-point, speed), cover-fit to 1920x1080"""
    t_in, speed = tl.parse_use(s)
    return tl.frame_of(s['id'], local, in_t=kw.pop('in_t', t_in), speed=kw.pop('speed', speed), dur=s['end'] - s['start'], **kw)


def other(sid, t_src, **kw):
    """another shot's footage at source time t_src (seconds into its clip)"""
    return tl.frame_of(sid, 0.0, in_t=t_src, speed=1.0, dur=3.0, **kw)


def shot_frame(sid, local, frame_idx=0):
    """a full composite of shot sid at its local time (for irises / wipes that reveal the next shot)"""
    s = tl.BY_ID[sid]
    fn = tl.RECIPES.get(sid, tl.default_recipe)
    return fn(s, s['start'] + local, local, frame_idx)


def beats_in(s):
    t0, t1 = s['start'], s['end']
    k = math.ceil((t0 - 0.682) / BEAT - 1e-6)
    out = []
    while 0.682 + k * BEAT < t1 - 1e-6:
        out.append(0.682 + k * BEAT)
        k += 1
    return out


def eighths_in(s):
    t0, t1 = s['start'], s['end']
    k = math.ceil((t0 - 0.682) / (BEAT / 2) - 1e-6)
    out = []
    while 0.682 + k * BEAT / 2 < t1 - 1e-6:
        out.append(0.682 + k * BEAT / 2)
        k += 1
    return out


def ev(img, stops):
    return img * np.float32(2.0 ** stops)


# ------------------------------------------------------------------ masks / inserts
def ellipse(e, feather=3.0):
    cx, cy, rx, ry = e[:4]
    rot = e[4] if len(e) > 4 else 0.0
    return fx.ellipse_mask(cx, cy, rx, ry, feather=feather, rot=rot)


def quad_mask(q, feather=1.5):
    return fx.poly_mask([tuple(p) for p in q], feather=feather)


def put_quad(img, content, quad, mode='over', amt=1.0, feather=1.5):
    """warp content (any size) onto a screen quad TL, TR, BR, BL; mode over | screen | add"""
    h, w = content.shape[:2]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    warped = cv2.warpPerspective(content, M, (W, H), flags=cv2.INTER_LINEAR)
    m = quad_mask(quad, feather) * amt
    if mode == 'screen':
        return img + (fx.screen(img, warped) - img) * m[..., None]
    if mode == 'add':
        return img + warped * m[..., None]
    return img + (warped - img) * m[..., None]


def put_ellipse(img, content, e, mode='over', amt=1.0, fisheye=0.0, mirror=False, feather=3.0):
    """content into an ellipse region (cx, cy, rx, ry[, rot]), optional convex fisheye + left-right mirror"""
    cx, cy, rx, ry = e[:4]
    rot = e[4] if len(e) > 4 else 0.0
    S = 512
    c = cv2.resize(content, (S, S), interpolation=cv2.INTER_AREA)
    if mirror:
        c = c[:, ::-1]
    if fisheye:
        c = fx.fisheye(c, fisheye)
    M = cv2.getRotationMatrix2D((S / 2, S / 2), -rot, 1.0)
    M[0] *= 2 * rx / S
    M[1] *= 2 * ry / S
    M[0, 2] += cx - rx
    M[1, 2] += cy - ry
    warped = cv2.warpAffine(c, M, (W, H), flags=cv2.INTER_LINEAR)
    m = ellipse(e, feather) * amt
    if mode == 'screen':
        return img + (fx.screen(img, warped) - img) * m[..., None]
    if mode == 'add':
        return img + warped * m[..., None]
    return img + (warped - img) * m[..., None]


def find_disc(img, default, hue=(4, 24), smin=110, vmin=70, inner=0.86):
    """curve mirror: orange rim -> largest component -> fitEllipse; returns the glass ellipse (cx, cy, rx, ry, rot)"""
    u8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 0] >= hue[0]) & (hsv[..., 0] <= hue[1]) & (hsv[..., 1] >= smin) & (hsv[..., 2] >= vmin)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    best = None
    for c in cs:
        a = cv2.contourArea(c)
        if a < 2500 or len(c) < 20:
            continue
        (x, y), (MA, ma), ang = cv2.fitEllipse(c)
        if min(MA, ma) < 30 or max(MA, ma) / max(1, min(MA, ma)) > 2.2:
            continue
        hull = cv2.contourArea(cv2.convexHull(c))
        score = hull * (min(MA, ma) / max(MA, ma))
        if best is None or score > best[0]:
            best = (score, (x, y, MA / 2 * inner, ma / 2 * inner, ang))
    return best[1] if best else tuple(default)


def disc_of(sid, local, img, default):
    key = ('disc', sid, int(round(local * 24)))
    if key not in _cache:
        if len([k for k in _cache if isinstance(k, tuple) and k[0] == 'disc']) > 400:
            for k in [k for k in _cache if isinstance(k, tuple) and k[0] == 'disc']:
                del _cache[k]
        _cache[key] = find_disc(img, default)
    return _cache[key]


# ------------------------------------------------------------------ transitions (each shot carries its own half)
def haze_in(img, t, local, frames=6, amp=0.02):
    """陽炎ディゾルブ, incoming half: the image refracts in and settles over `frames`"""
    k = clamp(local / (frames / 24))
    if k >= 1:
        return img
    return fx.heat_haze(img, t, amp=amp * (1 - k) ** 1.5)


def haze_out(img, t, s, beats=1.0, amp=0.02):
    """陽炎ディゾルブ, outgoing half: displacement ramps 0 -> amp over the last beat(s)"""
    k = clamp((t - (s['end'] - BEAT * beats)) / (BEAT * beats))
    if k <= 0:
        return img
    return fx.heat_haze(img, t, amp=amp * k * k)


def bloom_out(img, t, t_end, frames=4):
    """白飛び, outgoing: overexpose over the last `frames`"""
    k = clamp((t - (t_end - frames / 24)) / (frames / 24))
    return fx.white_bloom(img, k) if k > 0 else img


def bloom_in(img, local, frames=6):
    """白飛び, incoming: resolve from white"""
    k = 1.0 - clamp(local / (frames / 24))
    return fx.white_bloom(img, k) if k > 0 else img


def static_bleed(img, t, t0, t1, seed=0):
    """砂嵐: streaks sharpen into scanlines and channel noise that fill the frame by t1"""
    k = clamp((t - t0) / max(1e-6, t1 - t0))
    if k <= 0:
        return img
    noise = fx.tv_noise(t, seed=seed, level=0.8)
    lines = (np.sin(fx._YS * math.pi / 2.0) > 0).astype(np.float32)[..., None]
    out = img * (1 - 0.35 * k * lines)
    return out + (noise - out) * (k ** 2)


def wake_grade(img, warm=0.0):
    return fx.grade(img, warm=warm)


# ------------------------------------------------------------------ painted props
def seven_seg(txt, h=120, col='#FF3B30', glow=6.0):
    """7-segment LED digits (RGBA float) for clocks; ':' blinks are the caller's job"""
    segs = {'0': 'abcdef', '1': 'bc', '2': 'abdeg', '3': 'abcdg', '4': 'bcfg', '5': 'acdfg', '6': 'acdefg', '7': 'abc',
            '8': 'abcdefg', '9': 'abcdfg', ' ': ''}
    w = int(h * 0.55)
    th = max(3, int(h * 0.12))
    gap = int(h * 0.18)
    width = sum((w + gap) if ch != ':' else (th * 2 + gap) for ch in txt)
    m = np.zeros((h + 2 * th, width + 2 * th), np.float32)
    x = th
    for ch in txt:
        if ch == ':':
            for yy in (h * 0.32, h * 0.72):
                cv2.circle(m, (int(x + th), int(th + yy)), th // 2 + 1, 1.0, -1, cv2.LINE_AA)
            x += th * 2 + gap
            continue
        S = {'a': ((0.1, 0), (0.9, 0)), 'b': ((1, 0.08), (1, 0.46)), 'c': ((1, 0.54), (1, 0.92)), 'd': ((0.1, 1), (0.9, 1)),
             'e': ((0, 0.54), (0, 0.92)), 'f': ((0, 0.08), (0, 0.46)), 'g': ((0.1, 0.5), (0.9, 0.5))}
        for sg in segs.get(ch, ''):
            (x0, y0), (x1, y1) = S[sg]
            cv2.line(m, (int(x + x0 * w), int(th + y0 * h)), (int(x + x1 * w), int(th + y1 * h)), 1.0, th, cv2.LINE_AA)
        x += w + gap
    rgb = np.broadcast_to(fx.hexc(col), m.shape + (3,)).astype(np.float32).copy()
    g = cv2.GaussianBlur(m, (0, 0), glow)
    a = np.clip(m + g * 0.8, 0, 1)
    rgb = rgb * (0.7 + 0.3 * m[..., None]) + np.float32(0.25) * m[..., None]
    return np.clip(rgb, 0, 1), a


def put_rgba(img, rgb, a, quad):
    h, w = a.shape
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    wr = cv2.warpPerspective(rgb, M, (W, H))
    wa = cv2.warpPerspective(a, M, (W, H))
    return img + (wr - img) * wa[..., None]


def calendar_card(circle_k=0.0, note_k=0.0, tint=None):
    """a clean painted June calendar page; the 16 gets a red marker circle (circle_k) and a note 始発 4:52 (note_k)"""
    from mv import text
    key = ('cal', round(circle_k, 2), round(note_k, 2), tint)
    if key in _cache:
        return _cache[key]
    cw, ch = 600, 760
    im = np.empty((ch, cw, 3), np.float32)
    im[:] = fx.hexc('#F2EDE4')
    cv2.rectangle(im, (0, 0), (cw, 150), tuple(float(v) for v in fx.hexc('#3E5C8A')), -1)

    def put(txt, x, y, size, col, font='mincho'):
        nonlocal im
        gl, _ = text.layout_h(txt, x, y, size, font, align='center')
        f, _ = text.render_glyphs(gl)
        if f is not None:
            f = f[:ch, :cw] if f.shape[0] >= ch else np.pad(f, ((0, ch - f.shape[0]), (0, 0)))[:, :cw]
            im = im + (fx.hexc(col)[None, None] - im) * f[..., None]
    put('6', 300, 80, 96, '#F2EDE4', 'kaku')
    put('JUNE', 300, 132, 30, '#F2EDE4', 'mincho')
    days = '日月火水木金土'
    for i, dch in enumerate(days):
        put(dch, 50 + i * 83, 190, 26, '#D9402B' if i == 0 else '#20263A')
    # June: day 1 on a Thursday (as in many years); 16 sits on a Sunday-ish row -> keep it readable
    d0 = 4
    pos16 = None
    for dnum in range(1, 31):
        idx = d0 + dnum - 1
        r, c = divmod(idx, 7)
        x, y = 50 + c * 83, 260 + r * 92
        put(str(dnum), x, y, 34, '#D9402B' if c == 0 else '#20263A')
        if dnum == 16:
            pos16 = (x, y)
    if circle_k > 0 and pos16:
        m = np.zeros((ch, cw), np.float32)
        a1 = int(360 * circle_k)
        cv2.ellipse(m, pos16, (40, 32), -12, -80, -80 + a1, 1.0, 5, cv2.LINE_AA)
        im = im + (fx.hexc('#D9402B')[None, None] - im) * m[..., None]
    if note_k > 0 and pos16:
        from mv import text as T
        gl, _ = T.layout_h('始発 4:52', pos16[0] + 70, pos16[1] + 52, 26, 'klee', align='left')
        f, _ = T.render_glyphs(gl, anim=lambda g: dict(alpha=note_k))
        if f is not None:
            f = np.pad(f, ((0, max(0, ch - f.shape[0])), (0, 0)))[:ch, :cw]
            im = im + (fx.hexc('#D9402B')[None, None] - im) * f[..., None]
    if tint is not None:
        im = im * (0.55 + 0.45 * fx.hexc(tint)[None, None])
    _cache[key] = im
    return im


# ================================================================== intro
def a_intro_01(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, in_t=0.0, speed=5.04 / 5.13)
    g = REG(sid, 'glass', [600, 700, 110, 165])
    gm = ellipse(g, 6.0)
    # inside the glass: the noon sky of A-hook-01, upside down, squeezed at the rim (cylindrical refraction), hazy
    sky = other('A-hook-01', 1.0 + local * (3.0 / 5.13), zoom=1.3, cy=0.25)[::-1].copy()
    nx = (fx._XS - W / 2) / (W / 2)
    sq = (W / 2) + np.sign(nx) * (np.abs(nx) ** 0.7) * (W / 2)
    sky = cv2.remap(sky, sq.astype(np.float32), fx._YS, cv2.INTER_LINEAR)
    sky = fx.heat_haze(sky, t, amp=0.012)
    img = put_ellipse(img, sky, g, mode='screen', amt=0.85, feather=6.0)
    # rack focus: glass sharp, background soft -> flips to Haru on 2.16
    if local < 2.16:
        k = 1.0 - ease((local - 1.4) / 0.76)
        bg = fx.blur(img, 6.0 * k)
        img = img * gm[..., None] + bg * (1 - gm[..., None])
    else:
        k = ease((local - 2.16) / 0.5)
        gl = fx.blur(img, 4.0 * k)
        img = img * (1 - gm[..., None]) + gl * gm[..., None]
    # the ice cube clicks on 2.16: a 2-frame specular glint; it fades over beat 4 (4.39-5.13)
    if 2.16 <= local:
        gk = 1.0 if local < 2.16 + 2 / 24 else 0.35 * (1 - clamp((t - 4.39) / 0.74))
        gx, gy = g[0] + 0.3 * g[2], g[1] - 0.35 * g[3]
        m = fx.ellipse_mask(gx, gy, 12 + 10 * gk, 3 + 2 * gk, feather=4.0)
        img = img + np.float32(1.4 * gk) * m[..., None]
    # CRT key light +-8% on 8ths, dust motes in the TV beam
    p8 = ((t - 0.682) / (BEAT / 2)) % 1.0
    img = img * np.float32(1.0 + 0.08 * math.cos(p8 * 2 * math.pi))
    img = fx.motes(img, t, n=60, seed=1, amount=0.45)
    if local < 0.6:
        img = img * np.float32(ease(local / 0.6))
    return img


def a_intro_02(s, t, local, fi):
    sid = s['id']
    push = 1.0 + 0.025 * clamp(local / (s['end'] - s['start']))
    img = plate(s, local)
    q = np.float32(REG(sid, 'crt', [[760, 330], [1160, 330], [1160, 640], [760, 640]]))
    c = q.mean(0)
    q = (q - c) * push + c
    cont = other('A-hook-04', 0.2 + local)
    cont = fx.crt(cont, t, barrel_k=0.08, scan=0.22, mask=0.18, bloom_amt=0.3, hum=0.04)
    img = put_quad(img, cont, q, 'over')
    # his reflection on the convex glass (head-and-shoulders crop, mirrored, Fresnel brighter at the rim)
    hb = REG(sid, 'him_box', [1180, 260, 1700, 1000])
    crop = img[hb[1]:hb[3], hb[0]:hb[2]][:, ::-1]
    if crop.size:
        refl = cv2.resize(crop, (int(q[1][0] - q[0][0]), int(q[3][1] - q[0][1])))
        fres = np.clip(np.abs(np.linspace(-1, 1, refl.shape[1]))[None, :] ** 2 * 0.6 + 0.4, 0, 1)[..., None]
        img = put_quad(img, refl * fres, q, 'screen', amt=0.18)
    # 光の走査 out: the last train's first lit window crosses right -> left from 7.35 and wipes by 8.09
    img = fx.rect_sweep(img, t, 7.35, 10.0, n=1, w=900, h=420, speed=-2600.0, amount=0.55)
    if t > 8.09 - 3 / 24:
        img = fx.white_bloom(img, 0.5 * clamp((t - (8.09 - 3 / 24)) / (3 / 24)))
    return img


def a_intro_03(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    if local < 4 / 24:
        img = fx.white_bloom(img, 0.5 * (1 - local / (4 / 24)))
    # the window lights sweep the ceiling right -> left, one per beat, skewed by a homography; a streak on the CRT glass
    ceil = np.float32(REG(sid, 'ceiling', [[0, 0], [1920, 0], [1920, 420], [0, 520]]))
    lay = np.zeros((H, W, 3), np.float32)
    for b in (8.09, 8.83, 9.57, 10.31):
        lay = fx.rect_sweep(lay, t, b, 99.0, color='#FFB46B', n=1, w=320, h=200, y=200, speed=-2400.0, amount=1.0)
    Mh = cv2.getPerspectiveTransform(np.float32([[0, 0], [1920, 0], [1920, 1080], [0, 1080]]), ceil)
    lay = cv2.warpPerspective(lay, Mh, (W, H))
    img = img + lay * np.float32(0.35)
    crt = REG(sid, 'crt', None)
    if crt is not None:
        ph = ((t - 8.09) % BEAT) / BEAT
        streak = np.zeros((H, W, 3), np.float32)
        streak = fx.rect_sweep(streak, t, 8.09 + math.floor((t - 8.09) / BEAT) * BEAT, 99.0, color='#FFB46B', n=1, w=160,
                               h=900, y=0, speed=-2400.0, amount=1.0)
        img = img + streak * quad_mask(crt)[..., None] * np.float32(0.4)
    # the calendar: a clean painted card; 16 circled in red on beat 3 (9.57); note 始発 4:52
    cal = REG(sid, 'calendar', None)
    if cal is not None:
        ck = clamp((t - 9.57) / 0.35)
        card = calendar_card(ck, clamp((t - 9.9) / 0.3))
        img = put_quad(img, card, cal, 'over')
    return img


def a_intro_04(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, in_t=0.0, speed=0.85)
    d0 = REG(sid, 'mirror', [960, 470, 140, 140])
    e = disc_of(sid, local, img, d0)
    # inside the mirror: noon (A-hook-02 plate) through the convex glass, mirrored; brightens 0.3 EV per beat from 14.02
    noon = other('A-hook-02', 0.4 + local * 0.5)
    nb = sum(1 for b in (14.02, 14.76, 15.50, 16.24) if t >= b)
    noon = ev(noon, 0.3 * nb)
    img = put_ellipse(img, noon, e, 'over', fisheye=0.45, mirror=True)
    # the haze leaks past the rim, radius growing per beat
    if nb:
        r = max(e[2], e[3]) * (1.2 + 0.35 * nb)
        reg = fx.ellipse_mask(e[0], e[1], r, r, feather=r * 0.35)
        img = fx.heat_haze(img, t, amp=0.006 * nb, region=reg)
    # 16.24 drum pickup: full-frame haze warp
    if t >= 16.24:
        img = fx.heat_haze(img, t, amp=0.012 * clamp((t - 16.24) / 0.3))
    # 15.50-16.98 digital push into the mirror; fills the frame at 16.89, overexposes over 4 frames (鏡抜け + 白飛び)
    if t >= 15.50:
        k = clamp((t - 15.50) / (16.89 - 15.50))
        z = 1.0 + (W / (2 * max(10.0, e[2])) * 1.15 - 1.0) * (k ** 2.2)
        M = cv2.getRotationMatrix2D((e[0], e[1]), 0, z)
        M[0, 2] += (W / 2 - e[0]) * (k ** 2)
        M[1, 2] += (H / 2 - e[1]) * (k ** 2)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # present-day night: 2.39 bars, which slide open as the push passes through the glass into the noon memory
    img = fx.letterbox(img, open_k=ease((t - 15.50) / (16.89 - 15.50)))
    return bloom_out(img, t, s['end'], 4)


# ================================================================== hook
def _horizon(sid, default=520):
    return REG(sid, 'horizon', default)


def mirage_shimmer(img, t, hy, height=40, amp=3.0, strength=0.5):
    """extra vertical-mirror shimmer in the mirage band under the horizon"""
    yy = np.clip(2 * hy - fx._YS + np.sin(fx._XS / 23.0 + t * 7.0) * amp * 0.5, 0, H - 1).astype(np.float32)
    xx = (fx._XS + np.sin(fx._YS / 3.0 + t * 11.0) * amp).astype(np.float32)
    refl = cv2.remap(img, xx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    m = ((fx._YS >= hy) & (fx._YS < hy + height)).astype(np.float32) * np.clip(1 - (fx._YS - hy) / height, 0, 1)
    m = cv2.GaussianBlur(m, (0, 0), 1.5)
    return img + (refl - img) * (m * strength)[..., None]


def a_hook_01(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    kicks = (16.98, 17.72, 18.46, 19.20)
    img = ev(img, 0.25 * fx.pulse(t, kicks, decay=8 / 24 / 2.5))
    img = fx.heat_haze(img, t, amp=0.015)
    img = mirage_shimmer(img, t, _horizon(sid), 46, 4.0, 0.55)
    img = fx.halation(img, 0.22)
    img = fx.chroma(img, 1.2)
    img = fx.light_leak(img, t, 18.46, dur=0.9, color='#FFB46B', direction=1, amount=0.45)
    return bloom_in(img, local, 6)


def a_hook_02(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    e = disc_of(sid, local, img, REG(sid, 'mirror', [960, 430, 160, 160]))
    walk = other('A-hook-01', 1.0 + local)
    # the glass swims: 2 rings per beat
    ph = ((t - 0.682) / (BEAT / 2)) % 1.0
    S = 512
    ys, xs = np.mgrid[0:S, 0:S].astype(np.float32)
    rr = np.sqrt((xs - S / 2) ** 2 + (ys - S / 2) ** 2)
    d = np.sin(rr / 22.0 - ph * 2 * math.pi) * 4.0
    w2 = cv2.resize(walk, (S, S))
    w2 = cv2.remap(w2, xs + d * (xs - S / 2) / (rr + 1), ys + d * (ys - S / 2) / (rr + 1), cv2.INTER_LINEAR)
    img = put_ellipse(img, w2, e, 'over', fisheye=0.45, mirror=True)
    # rim glare pulsing on beats; one flash of the glass on ミラー (~21.9)
    pk = fx.pulse(t, beats_in(s), decay=0.12)
    rim = np.clip(ellipse((e[0], e[1], e[2] * 1.12, e[3] * 1.12) + tuple(e[4:]), 2.0) - ellipse(e, 2.0), 0, 1)
    img = img + np.float32(0.35 * pk) * rim[..., None]
    if 21.88 <= t < 21.88 + 3 / 24:
        img = img + np.float32(0.6 * (1 - (t - 21.88) / (3 / 24))) * ellipse(e, 3.0)[..., None]
    return img


def a_hook_03(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    hy = _horizon(sid, 600)
    img = mirage_shimmer(img, t, hy, 60, 3.0, 0.6)
    img = fx.heat_haze(img, t, amp=0.012)
    img = fx.light_leak(img, t, 24.15, dur=0.8, color='#FFC98A', direction=-1, amount=0.5)
    if 24.15 <= t < 24.15 + 6 / 24:
        img = fx.blur(img, 3.0 * math.sin(math.pi * (t - 24.15) / (6 / 24)))
    return img


def a_hook_04(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    fx_, fy = REG(sid, 'feet', [960, 860])
    hy = _horizon(sid, 620)
    if t >= 27.35:
        nb = int((t - 27.35) / (BEAT / 2)) + 1
        for k in range(nb):
            img = fx.ripple(img, fx_, fy, t, 27.35 + k * BEAT / 2, speed=420.0, wavelength=40.0, amp=7.0, decay=1.2)
        band = ((fx._YS >= hy) & (fx._YS < hy + 60)).astype(np.float32)
        img = img + np.float32(0.15 * clamp((t - 27.35) / 0.5)) * band[..., None]
    # 波紋カット: the outermost ring becomes an iris that reaches the frame edge exactly on 28.83
    if t >= 27.35:
        k = clamp((t - 27.35) / (28.83 - 27.35))
        rmax = math.hypot(max(fx_, W - fx_), max(fy, H - fy))
        r = rmax * (k ** 1.6)
        if r > 2:
            nxt = shot_frame('A-chorus1-01', 0.0, fi)
            m = fx.ellipse_mask(fx_, fy, r, r * 0.85, feather=10.0)
            img = img + (nxt - img) * m[..., None]
            ring = np.clip(fx.ellipse_mask(fx_, fy, r + 8, (r + 8) * 0.85, 3.0) - fx.ellipse_mask(fx_, fy, r - 4, (r - 4) * 0.85, 3.0), 0, 1)
            img = img + np.float32(0.35) * ring[..., None]
    return img


# ================================================================== chorus1
def a_chorus1_01(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    img = fx.grade(img, warm=0.02)
    img = fx.sparkles(img, t, n=140, seed=11, area=tuple(REG(sid, 'sea_box', [0, 520, 1920, 1080])), rate=8.0 / BEAT * 0.5)
    hx, hy = REG(sid, 'head', [900, 360])
    ghost = fx.ellipse_mask(W - hx, H - hy, 46, 46, feather=30.0)
    img = img + fx.hexc('#FFE2B0')[None, None] * (ghost * 0.25)[..., None]
    img = fx.halation(img, 0.22)
    img = fx.heat_haze(img, t, amp=0.008)
    if local < 2 / 24:                                   # the iris ring arriving at the frame edge
        img = img + np.float32(0.2 * (1 - local / (2 / 24)))
    return img


def a_chorus1_02(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    clk = REG(sid, 'clock', None)
    if clk is not None:
        txt = '23:59' if t < 31.95 else ' 0:00'
        rgb, a = seven_seg(txt, 110)
        img = put_rgba(img, rgb, a, clk)
        g = REG(sid, 'glass', None)
        if g is not None:                                 # the red bleeds into the glass; faint noon inside it
            img = img + fx.hexc('#FF3B30')[None, None] * (ellipse(g, 8.0) * 0.10)[..., None]
            sky = other('A-hook-01', 1.5 + local, zoom=1.4, cy=0.2)
            img = put_ellipse(img, sky, g, 'screen', amt=0.18)
    # the fan shadow, strengthened, on the half bar
    ang = (t - 31.79) / (2 * BEAT) * 2 * math.pi
    th = np.arctan2(fx._YS - 200, fx._XS - 1500)
    blades = (np.cos(3 * (th - ang)) > 0.55).astype(np.float32)
    img = img * (1 - cv2.GaussianBlur(blades, (0, 0), 30)[..., None] * 0.18)
    return haze_out(img, t, s)


def a_chorus1_03(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    img = haze_in(img, t, local)
    hx, hy = REG(sid, 'him', [960, 540])
    img = fx.swirl(img, hx, hy, 1.5 * local)
    img = fx.heat_haze(img, t, amp=0.018)
    if t >= 36.24:
        img = fx.chroma(img, 1.0 + 3.0 * clamp((t - 36.24) / 1.0))
    mir = REG(sid, 'mirror', None)
    if mir is not None:
        e = disc_of(sid, local, img, mir)
        hb = REG(sid, 'him_box', [760, 240, 1160, 1000])
        crop = img[hb[1]:hb[3], hb[0]:hb[2]]
        if crop.size:
            img = put_ellipse(img, crop, e, 'over', fisheye=0.4, mirror=True)
    return img


def a_chorus1_04(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    img = fx.heat_haze(img, t, amp=0.010)
    e = disc_of(sid, local, img, REG(sid, 'mirror', [960, 420, 150, 150]))
    # the mirror's kind lie: both figures side by side in the glass; her reflection runs one beat late
    hb = REG(sid, 'him_box', [300, 300, 700, 1000])
    nb_ = REG(sid, 'her_box', [1200, 300, 1600, 1000])
    late = plate(s, max(0.0, local - BEAT))
    S = 512
    glass = cv2.resize(img[0:H, 0:W], (S, S))
    hcrop = img[hb[1]:hb[3], hb[0]:hb[2]]
    ncrop = late[nb_[1]:nb_[3], nb_[0]:nb_[2]]
    if hcrop.size and ncrop.size:
        hc = cv2.resize(hcrop, (S // 2, S))
        nc = cv2.resize(ncrop, (S // 2, S))
        glass = np.concatenate([nc, hc], 1)
        melt = clamp((local - (s['end'] - s['start'] - 8 / 24)) / (8 / 24))
        if melt > 0:
            glass = fx.heat_haze(cv2.resize(glass, (W, H)), t, amp=0.04 * melt)
            glass = cv2.resize(glass, (S, S))
    img = put_ellipse(img, glass, e, 'over', fisheye=0.4, mirror=True)
    _cache['c104_disc'] = e
    return img


def a_chorus1_05(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    # circle match in: a ripple ring where the mirror disc was (chorus1-04's last frame, computed, not cached)
    s4 = tl.BY_ID['A-chorus1-04']
    l4 = s4['end'] - s4['start'] - 1 / 24
    e = disc_of('A-chorus1-04', l4, plate(s4, l4), REG('A-chorus1-04', 'mirror', [960, 420, 150, 150]))
    if local < 0.6:
        img = fx.ripple(img, e[0], e[1], t, s['start'], speed=600.0, wavelength=50.0, amp=10.0, decay=2.0)
    ca = fx.caustics(t, scale=120.0)
    img = img * (0.88 + 0.24 * ca[..., None])
    for b in (41.42, 42.16):
        img = fx.bubbles(img, t, n=24, seed=int(b * 10), amount=0.9 * math.exp(-max(0.0, t - b) * 2.0)) if t >= b else img
    return img


def a_chorus1_06(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    steps = sum(1 for b in (43.65, 44.39, 45.13, 45.87) if t >= b)
    ox, oy = REG(sid, 'spill_origin', [700, 760])
    r = 80 + 150 * steps + 40 * clamp(((t - 43.65) % BEAT) / BEAT)
    m = fx.noise_blob_mask(ox, oy + r * 0.3, r, t, seed=6, lobes=7, rough=0.22)
    pool = other('A-chorus1-05', 0.6 + local)[::-1]
    floor = np.float32(REG(sid, 'floor', [[300, 700], [1620, 700], [1920, 1080], [0, 1080]]))
    Mh = cv2.getPerspectiveTransform(np.float32([[0, 0], [W, 0], [W, H], [0, H]]), floor)
    spill = cv2.warpPerspective(pool, Mh, (W, H), borderMode=cv2.BORDER_REFLECT)
    img = img + (spill - img) * m[..., None]
    edge = np.clip(cv2.dilate(m, np.ones((5, 5), np.uint8)) - m, 0, 1)
    img = img + np.float32(0.6) * edge[..., None]
    fxx, fyy = REG(sid, 'face', [1200, 420])
    up = fx.ellipse_mask(fxx, fyy, 220, 260, feather=80.0) * (0.15 * steps / 4)
    img = img * (1 + up[..., None] * fx.hexc('#FFD9A0')[None, None])
    return haze_out(img, t, s)


def a_chorus1_07(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    ext = REG(sid, 'exterior', None)
    if ext is not None:
        m = quad_mask(ext, 12.0)
        hz = fx.heat_haze(img, t, amp=0.02)
        hz = fx.halation(hz, 0.5)
        img = img + (hz - img) * m[..., None]
    img = fx.motes(img, t, n=50, seed=7, amount=0.5)
    fxx, fyy = REG(sid, 'face', [960, 520])
    br = fx.pulse(t, (46.61, 47.35, 48.09), decay=0.3)
    img = img + np.float32(0.12 * br) * fx.ellipse_mask(fxx, fyy, 260, 300, feather=120.0)[..., None]
    return img


def a_chorus1_08(s, t, local, fi):
    img = plate(s, local)
    p8 = ((t - 0.682) / (BEAT / 2)) % 1.0
    img = img * np.float32(0.85 + 0.3 * (p8 < 0.45))
    return static_bleed(img, t, 51.79, 52.53, seed=8)


def register(*fns):
    """a_<section>_<NN> -> 'A-<section>-<NN>' (section may contain '_', e.g. outro_hook)"""
    for f in fns:
        sec, nn = f.__name__[2:].rsplit('_', 1)
        sid = f'A-{sec}-{nn}'
        assert sid in tl.BY_ID, sid
        tl.RECIPES[sid] = f


register(a_intro_01, a_intro_02, a_intro_03, a_intro_04, a_hook_01, a_hook_02, a_hook_03, a_hook_04,
         a_chorus1_01, a_chorus1_02, a_chorus1_03, a_chorus1_04, a_chorus1_05, a_chorus1_06, a_chorus1_07, a_chorus1_08)


# ================================================================== verse
def tv_hue(img, t, times, cols, mask_thr=0.55):
    """recolour the TV light on the lit side (highlight luma mask), luminance-preserving, hard 2-frame changes"""
    i = max([k for k, b in enumerate(times) if t >= b] or [0])
    col = fx.hexc(cols[i])
    l = fx.lum(img)
    m = np.clip((l - mask_thr) / 0.3, 0, 1)
    tinted = l[..., None] * col[None, None] / max(1e-3, float(col.mean())) * 0.9
    return img + (tinted - img) * (m * 0.55)[..., None]


def a_verse_01(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    img = tv_hue(img, t, (52.53, 53.27, 54.02, 54.76), ('#5FE3F0', '#FFB347', '#E85FD0', '#5FE3F0'))
    g = REG(sid, 'tv_glass', None)
    if g is not None:                                     # OSD volume bars climbing one notch per beat (no text)
        n = 4 + sum(1 for b in (52.53, 53.27, 54.02, 54.76) if t >= b) * 3
        x0, y0, x1, y1 = g
        bw = (x1 - x0) / 20
        for k in range(n):
            xa = int(x0 + k * bw)
            cv2.rectangle(img, (xa, int(y1 - 30)), (int(xa + bw * 0.7), int(y1 - 10)), (0.55, 0.95, 0.6), -1)
    if t >= s['end'] - 2 / 24:
        img = fx.tv_noise(t, seed=1, level=0.8)
    return img


def crt_full(img, t, k=0.12):
    return fx.crt(img, t, barrel_k=k, scan=0.25, mask=0.2, bloom_amt=0.35, hum=0.06, curve_vignette=True)


def a_verse_02(s, t, local, fi):
    flips = (55.50, 56.24, 56.98, 57.72)
    chans = [('A-hook-04', 0.2), ('A-chorus1-05', 1.0), ('A-chorus1-08', 0.5), ('A-chorus2-01', 0.4)]
    i = max([k for k, b in enumerate(flips) if t >= b] or [0])
    since = t - flips[i]
    sid, t0 = chans[i]
    cont = other(sid, t0 + since * 0.9)
    if since < 3 / 24:                                    # 3 frames of noise + vertical-hold roll
        roll = int(H * (since / (3 / 24)) * 0.6)
        cont = np.roll(fx.tv_noise(t, seed=i, level=0.7), roll, 0)
        cont = cont * 0.35                                # near-black noise frames: his reflection reads clearly
    img = crt_full(cont, t, 0.12)
    refl = other('A-verse-01', 2.0 + (local % 1.0))[:, ::-1]
    fres = np.clip(0.4 + 0.6 * ((fx._XS - W / 2) / (W / 2)) ** 2, 0, 1)[..., None]
    amt = 0.25 + (0.35 if since < 3 / 24 else 0.0) + (0.15 if i == 3 else 0.0)
    img = fx.screen(img, refl * fres, amt)
    # 鏡抜け into the CRT on 58.46: push through the scanlines with a horizontal flip
    k = clamp((t - (s['end'] - 0.37)) / 0.37)
    if k > 0:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1.0 + 2.0 * k * k)
        img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        if k > 0.5:
            img = img[:, ::-1]
        img = fx.white_bloom(img, 0.4 * k)
    return img


def technicolor(img, t, fi, flicker=0.02):
    g = fx.grade(img, sat=1.25, contrast=1.15)
    l = fx.lum(g)[..., None]
    g = g + (fx.hexc('#C2183C')[None, None] - g) * np.clip(g[..., 0:1] - g[..., 1:2] - 0.15, 0, 1) * 0.35
    g = g * (1 - 0.18 * (1 - l)) + fx.hexc('#0E6B6B')[None, None] * 0.18 * (1 - l)
    g = g * np.float32(1.0 + flicker * math.sin(fi * 2.7) * math.sin(fi * 0.9))
    return fx.halation(g, 0.25)


def film_window(img, t, fi, push):
    """4:3 movie inside the 16:9 frame, pillarboxed in the TV's warm black, 1 px gate weave"""
    w43 = int(H * 4 / 3)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, push)
    rng = np.random.default_rng(fi)
    M[0, 2] += rng.integers(-1, 2)
    M[1, 2] += rng.integers(-1, 2)
    inner = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    out = np.empty_like(img)
    out[:] = fx.hexc('#120C08')
    x0 = (W - w43) // 2
    out[:, x0:x0 + w43] = inner[:, x0:x0 + w43]
    return fx.grain(out, fi, 0.05, size=1.8)


def a_verse_03(s, t, local, fi):
    img = plate(s, local, in_t=0.0, speed=0.85)
    img = technicolor(img, t, fi)
    return film_window(img, t, fi, 1.0 + 0.06 * clamp(local / (s['end'] - s['start'])))


def a_verse_04(s, t, local, fi):
    sid = s['id']
    d = s['end'] - s['start']
    mov = other('A-verse-03', 2.5 + local * 0.85)
    mov = technicolor(mov, t, fi)
    if t >= 62.91:                                        # beat 3: the movie train's window light sweeps across both
        mov = fx.rect_sweep(mov, t, 62.91, 99.0, color='#FFD9A0', n=1, w=420, h=1080, y=0, speed=-2600.0, amount=0.5)
    refl = other('A-verse-01', 0.5 + local)[:, ::-1]
    hx, hy = REG(sid, 'movie_man', [1180, 520])
    ax, ay = REG('A-verse-01', 'face', [900, 480])
    k = ease((t - 61.42) / (62.16 - 61.42))
    M = np.float32([[1, 0, (hx - ax) * k], [0, 1, (hy - ay) * k]])
    refl = cv2.warpAffine(fx.barrel(refl, 0.06), M, (W, H), borderMode=cv2.BORDER_REFLECT)
    scr = crt_full(fx.screen(mov, refl, 0.30), t, 0.10)
    # pull back to reveal the rounded screen border and the bezel, speculars shifting
    pb = ease(local / d)
    z = 1.0 - 0.22 * pb
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
    out = np.empty_like(scr)
    out[:] = fx.hexc('#0E0D10')
    inner = cv2.warpAffine(scr, M, (W, H), borderValue=(0, 0, 0))
    rect = np.zeros((H, W), np.float32)
    rw, rh = W * z, H * z
    cv2.rectangle(rect, (int(W / 2 - rw / 2 + 30 * z), int(H / 2 - rh / 2 + 30 * z)),
                  (int(W / 2 + rw / 2 - 30 * z), int(H / 2 + rh / 2 - 30 * z)), 1.0, -1)
    rect = cv2.GaussianBlur(rect, (0, 0), 6.0)
    out = out + (inner - out) * rect[..., None]
    spec = np.exp(-((fx._XS - fx._YS * 0.8 - (300 + 700 * pb)) / 120.0) ** 2) * (1 - rect) * 0.25
    out = out + spec[..., None]
    return haze_out(out, t, s)


def cold_grade(img):
    g = fx.grade(img, warm=-0.25, sat=0.8, lift=0.06, contrast=0.92)
    return fx.bloom(g, 0.72, 16, 0.3)


def a_verse_05(s, t, local, fi):
    img = cold_grade(plate(s, local))
    # god rays: radial blur from the roof, slowly rotating
    cx, cy = 960 + 200 * math.sin(local * 0.3), -200
    acc = np.zeros_like(img)
    for k in range(8):
        sc = 1.0 + k * 0.025
        M = cv2.getRotationMatrix2D((cx, cy), 0.4 * k * math.sin(local * 0.5), sc)
        acc += cv2.warpAffine(np.clip(img - 0.7, 0, 1), M, (W, H))
    return np.clip(img + acc * 0.08, 0, 1)


def a_verse_06(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    pane = REG(sid, 'pane', [[620, 200], [1300, 200], [1300, 760], [620, 760]])
    fut = cold_grade(other('A-verse-05', 0.2 + local))
    leave = ease((local - 1.2) / 1.2)
    img = put_quad(img, fut, pane, 'screen', amt=0.7 + 0.2 * leave)
    # his reflection: difference matte against the empty end frame (clean plate), mirrored into the pane at 40%
    clean = plate(s, s['end'] - s['start'] - 0.05)
    diff = np.clip((np.abs(img - clean).max(-1) - 0.08) * 5.0, 0, 1)
    diff = cv2.GaussianBlur(diff, (0, 0), 3.0)
    him = (img * diff[..., None])[:, ::-1]
    slide = int(W * 0.25 * leave)
    him = np.roll(him, -slide, 1)
    img = put_quad(img, him, pane, 'screen', amt=0.4 * (1 - leave))
    return haze_out(img, t, s)


def a_verse_07(s, t, local, fi):
    sid = s['id']
    img = haze_in(plate(s, local), t, local)
    hy = _horizon(sid, 560)
    img = mirage_shimmer(img, t, hy, 70, 5.0, 0.65)
    img = fx.heat_haze(img, t, amp=0.015)
    return img


def a_verse_08(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    pud = REG(sid, 'puddle', [960, 900, 420, 90])
    if t < 75.13 + 0.5:
        wave = other('A-verse-07', 0.4 + local)[::-1]
        fade = 1.0 - clamp((t - 74.76) / 0.6)
        glow = 0.45 * fade
        if t >= 74.76:
            wave = fx.ripple(wave, W / 2, H / 2, t, 74.76, speed=500.0, wavelength=30.0, amp=10.0, decay=1.5)
        img = put_ellipse(img, wave, pud, 'screen', amt=glow)
    # the lamp flickers and dies on 75.13 -> near black
    if t >= 74.95:
        fl = 1.0 if t < 75.13 and int(t * 24) % 2 == 0 else 0.55
        if t >= 75.13:
            fl = 0.08 + 0.1 * math.exp(-(t - 75.13) * 6)
        img = img * np.float32(fl)
    # 75.50: a single spark with a trail rises from the horizon and bursts at 76.24 (circle match)
    if t >= 75.50:
        sx, sy0 = REG(sid, 'spark', [1240, 600])
        k = clamp((t - 75.50) / (76.24 - 75.50))
        sy = sy0 - 380 * (1 - (1 - k) ** 2)
        for j in range(12):
            kk = max(0.0, k - j * 0.02)
            yy = sy0 - 380 * (1 - (1 - kk) ** 2)
            m = fx.ellipse_mask(sx + 2 * math.sin(j), yy, 3.0, 3.0, feather=2.0)
            img = img + fx.hexc('#FFD166')[None, None] * (m * (1 - j / 12))[..., None]
        _cache['spark_pos'] = (sx, sy)
    return img


# ================================================================== chorus2
def firework_light(img, t, times, cols, decay=10 / 24, thr=0.45):
    """coloured firework flashes on the lit side (highlight luma mask)"""
    l = fx.lum(img)
    m = np.clip((l - thr) / 0.35, 0, 1)[..., None]
    out = img
    for i, b in enumerate(times):
        if t >= b:
            k = math.exp(-(t - b) / decay * 2.3)
            if k > 0.02:
                out = out + fx.hexc(cols[i % len(cols)])[None, None] * m * (0.45 * k)
    return out


def burst(img, t, t0, cx, cy, R=260, col='#FFD166', n=90, seed=0, life=1.4):
    dt = t - t0
    if dt < 0 or dt > life:
        return img
    rng = np.random.default_rng(seed)
    a = rng.uniform(0, 2 * math.pi, n)
    sp = rng.uniform(0.6, 1.0, n)
    r = R * (1 - math.exp(-dt * 3.0))
    m = np.zeros((H, W), np.float32)
    for ai, si in zip(a, sp):
        x = cx + math.cos(ai) * r * si
        y = cy + math.sin(ai) * r * si + 60 * dt * dt
        cv2.circle(m, (int(x), int(y)), 2, 1.0, -1, cv2.LINE_AA)
    m = m * (1 - dt / life)
    g = cv2.GaussianBlur(m, (0, 0), 6.0)
    return img + fx.hexc(col)[None, None] * np.clip(m + g * 1.5, 0, 1.5)[..., None]


def a_chorus2_01(s, t, local, fi):
    img = plate(s, local)
    sx, sy0 = REG('A-verse-08', 'spark', [1240, 600])
    sy = sy0 - 380                                         # where verse-08's rising spark ends (k = 1)
    img = burst(img, t, s['start'], sx, sy, 300, '#FFD166', seed=21)
    kicks = beats_in(s)
    img = firework_light(img, t, kicks, ('#FFD166', '#EF476F', '#2EC4B6'))
    img = fx.sparkles(img, t, n=80, seed=3, area=(0, 0, 1920, 700), color='#FFD166', rate=4.0)
    return img


def a_chorus2_02(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    pane = REG(sid, 'pane', [[1100, 180], [1700, 160], [1720, 820], [1110, 860]])
    mem = other('A-chorus1-01', 0.5 + local)
    img = put_quad(img, mem, pane, 'screen', amt=0.55)
    fxx, fyy = REG(sid, 'face', [760, 460])
    img = img + fx.hexc('#FFD9A0')[None, None] * (fx.ellipse_mask(fxx + 120, fyy, 140, 200, feather=90) * 0.12)[..., None]
    for b in (79.94, 81.42):                               # breath fog on beats 2 and 4
        if t >= b:
            k = math.sin(math.pi * clamp((t - b) / 0.9))
            q = np.float32(pane)
            c = q.mean(0)
            fog = fx.ellipse_mask(c[0] - 120, c[1] + 60, 260 * (0.6 + 0.4 * k), 170 * (0.6 + 0.4 * k), feather=90) * k
            bl = fx.blur(img, 8.0)
            img = img + (bl - img) * fog[..., None]
            img = img + np.float32(0.25) * fog[..., None]
    return haze_out(img, t, s)


def a_chorus2_03(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    hy = _horizon(sid, 560)
    yy = np.clip(2 * hy - fx._YS, 0, H - 1).astype(np.float32)
    refl = cv2.remap(img, fx._XS, yy, cv2.INTER_LINEAR)
    refl = fx.ripple(refl, W / 2, hy + 200, t, s['start'], speed=60.0, wavelength=24.0, amp=3.0, decay=0.0)
    sea = (fx._YS > hy).astype(np.float32)
    img = img + (refl - img) * (sea * 0.85)[..., None]
    img = firework_light(img, t, beats_in(s), ('#EF476F', '#FFD166'), thr=0.5)
    edge = np.clip(fx.lum(img) - fx.lum(fx.blur(img, 6.0)), 0, 1) * 4.0
    img = img + fx.hexc('#EF476F')[None, None] * np.clip(edge, 0, 1)[..., None] * 0.3
    roll = 12.0 * ease(local / (s['end'] - s['start']))
    M = cv2.getRotationMatrix2D((W / 2, H / 2), roll, 1.0 + 0.04 * roll / 12)
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)


def a_chorus2_04(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, speed=1.0)
    img = firework_light(img, t, beats_in(s), ('#FFD166', '#EF476F', '#2EC4B6'))
    if t >= 87.35:
        img = fx.sparkles(img, t, n=60, seed=9, area=(400, 200, 1500, 800), color='#FFD166', rate=6.0,
                          amount=1.0 - clamp((t - 87.35) / 0.74) * 0.5)
    # 水面割り: tilt down to the waterline 87.35-88.09; 4-frame split above / below; land underwater
    if t >= 87.35:
        k = ease((t - 87.35) / 0.74)
        hy = _horizon(sid, 640)
        M = np.float32([[1, 0, 0], [0, 1, -(hy - H / 2) * k - 300 * k * k]])
        img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        under = (fx._YS > H / 2 + 260 * (1 - k)).astype(np.float32)
        tint = img * fx.hexc('#3FA7C9')[None, None] * 1.1
        img = img + (tint - img) * (under * 0.7)[..., None]
        if k > 0.7:
            img = fx.bubbles(img, t, n=40, seed=12, amount=0.8)
    return img


# ================================================================== bridge1
def underwater(img, t, amt=1.0):
    ca = fx.caustics(t, 160.0)
    img = img * (1 - 0.25 * amt) + img * fx.hexc('#3FA7C9')[None, None] * (0.25 * amt) * 1.3
    img = img * (0.9 + 0.2 * ca[..., None] * amt)
    return fx.chroma(fx.blur(img, 0.8 * amt), 1.5 * amt)


def a_bridge1_01(s, t, local, fi):
    sid = s['id']
    img = underwater(plate(s, local), t)
    img = fx.bubbles(img, t, n=50, seed=13, rim='#BFF3FF', amount=0.9)
    crt = REG(sid, 'crt', None)
    if crt is not None:
        img = img + fx.hexc('#7FD6E8')[None, None] * (quad_mask(crt, 30.0) * 0.18)[..., None]
    return haze_out(img, t, s)


def a_bridge1_02(s, t, local, fi):
    img = haze_in(plate(s, local), t, local)
    amp = 9.0 * math.exp(-local * 1.2) + (6.0 * math.exp(-(t - 93.28) * 2.0) if t >= 93.28 else 0.0)
    img = fx.water_refract(img, t, amp=amp, scale=80.0)
    img = fx.grade(img, warm=0.15, tint='#E8A0B8', tint_amt=0.18)
    img = fx.bubbles(img, t, n=10, seed=14, amount=0.5)
    # 水面割り out: tear through the waterline into rain over the last 4 frames
    k = clamp((t - (s['end'] - 4 / 24)) / (4 / 24))
    if k > 0:
        line = H * (1 - k)
        above = (fx._YS < line).astype(np.float32)[..., None]
        img = img * (1 - above) + fx.rain(img * 0.6, t) * above
    return img


def slate(img):
    return fx.grade(img, warm=-0.12, sat=0.75, contrast=1.05, tint='#5E6E86', tint_amt=0.12)


def tube_flicker(img, t, t0, region=None):
    if t0 <= t < t0 + 0.25:
        k = 0.55 if int((t - t0) * 24) % 2 == 0 else 1.0
        if region is None:
            return img * np.float32(k)
        m = quad_mask(region, 40.0)
        return img * (1 - m[..., None] * (1 - k))
    return img


def a_bridge1_03(s, t, local, fi):
    sid = s['id']
    img = slate(plate(s, local))
    hy = REG(sid, 'ground_y', 760)
    refl = cv2.remap(img, fx._XS, np.clip(2 * hy - fx._YS, 0, H - 1).astype(np.float32), cv2.INTER_LINEAR)
    wet = (fx._YS > hy).astype(np.float32) * 0.3
    img = img + (refl - img) * wet[..., None]
    img = fx.rain(img, t)
    for b in beats_in(s):
        if t >= b:
            img = fx.bubbles(img, t - b, n=8, seed=int(b * 7), area=(0, int(hy), W, H), amount=0.4 * math.exp(-(t - b) * 4))
    return tube_flicker(img, t, 95.50, REG(sid, 'tube', None))


def a_bridge1_04(s, t, local, fi):
    sid = s['id']
    img = slate(plate(s, local))
    bg = np.float32(REG(sid, 'curtain', [[0, 0], [1920, 0], [1920, 760], [0, 760]]))
    m = quad_mask(bg, 20.0)
    dy = (np.sin(fx._XS / 7.0) * 6.0 + np.sin(fx._XS / 23.0 + t * 3.0) * 4.0).astype(np.float32)
    dx = (np.sin(fx._YS / 40.0 + fx._XS / 11.0 + t * 8.0) * 3.0).astype(np.float32)
    cur = cv2.remap(img, fx._XS + dx, fx._YS + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    streak = (np.sin(fx._XS / 3.1 + np.floor(fx._YS / 90.0) * 1.7) > 0.96).astype(np.float32) * 0.15
    img = img + (cur + streak[..., None] - img) * m[..., None]
    img = fx.rain(img, t)
    return tube_flicker(img, t, 98.46, REG(sid, 'tube', None))


def a_bridge1_05(s, t, local, fi):
    sid = s['id']
    img = slate(plate(s, local))
    img = fx.rain(img, t, layers=((0.35, 900, 22, 1.0), (0.22, 1500, 40, 1.4)))
    rng = np.random.default_rng(15)
    for _ in range(9):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(40, 110)
        img = img + np.float32(0.05) * fx.ellipse_mask(x, y, r, r, feather=r * 0.4)[..., None]
    cx, cy = REG(sid, 'cheek', [1000, 560])
    for j in range(3):
        yy = (cy - 120 + ((local * 90 + j * 70) % 260))
        img = img + np.float32(0.12) * fx.ellipse_mask(cx + j * 14 - 14, yy, 3, 9, feather=3)[..., None]
    return tube_flicker(img, t, 101.42, REG(sid, 'tube', None))


def a_bridge1_06(s, t, local, fi):
    img = slate(plate(s, local))
    sp = 1.0 if t < 104.0 else 1.0 - 0.5 * clamp((t - 104.0) / 0.8)
    img = fx.rain(img, 104.0 + (t - 104.0) * sp if t >= 104.0 else t)
    img = fx.selective_desat(img, 0.3 * clamp((t - 104.0) / 0.5))
    return img


def a_bridge1_07(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, in_t=0.0, speed=0.85)
    img = fx.selective_desat(img, 0.85)
    img = fx.rain(img, 105.87 + (t - 105.87) * 0.25)
    # 波紋カット insert on 107.35 (0.74 s): her tear lands on a mirror-flat sea and the rings break the surface
    if 107.35 <= t < 107.35 + BEAT:
        sea = other('A-bridge1-02', 1.2, cy=0.75, zoom=1.4)
        sea = cv2.GaussianBlur(sea, (1, 41), 0)
        sea = fx.ripple(sea, W / 2, H * 0.55, t, 107.35, speed=380.0, wavelength=34.0, amp=9.0, decay=1.0)
        img = fx.selective_desat(sea, 0.6)
    return img


def a_bridge1_08(s, t, local, fi):
    sid = s['id']
    img = slate(plate(s, local))
    img = fx.rain(img, t if t >= 111.06 else 108.83 + (t - 108.83) * 0.5)
    gx, gy = REG(sid, 'gap', [960, 560])
    img = img + fx.hexc('#FFE9C8')[None, None] * (fx.ellipse_mask(gx, gy, 40, 380, feather=40) * 0.18)[..., None]
    if t >= 111.42:                                         # the first train's headlight floods in from the right
        k = clamp((t - 111.42) / 0.37)
        img = fx.rect_sweep(img, t, 111.42, 99.0, color='#FFD9A0', n=1, w=900, h=1080, y=0, speed=-3200.0, amount=0.6)
        img = img + fx.hexc('#FFE9C8')[None, None] * (np.clip((fx._XS - W * (1 - k)) / 400, 0, 1) * 0.6 * k)[..., None]
    return bloom_out(img, t, s['end'], 4)


tl.NO_GRAIN.add('A-verse-05')
register(a_verse_01, a_verse_02, a_verse_03, a_verse_04, a_verse_05, a_verse_06, a_verse_07, a_verse_08,
         a_chorus2_01, a_chorus2_02, a_chorus2_03, a_chorus2_04,
         a_bridge1_01, a_bridge1_02, a_bridge1_03, a_bridge1_04, a_bridge1_05, a_bridge1_06, a_bridge1_07, a_bridge1_08)


# ================================================================== chorus3
def window_sweep(img, t, times, color='#FFD9A0', amount=0.35, w=300):
    for b in times:
        img = fx.rect_sweep(img, t, b, 99.0, color=color, n=1, w=w, h=1080, y=0, speed=-3000.0, amount=amount)
    return img


def clock_insert(img, sid, txt, dim=1.0):
    clk = REG(sid, 'clock', None)
    if clk is not None:
        rgb, a = seven_seg(txt, 110)
        img = put_rgba(img, rgb * dim, a * (0.6 + 0.4 * dim), clk)
    return img


def a_chorus3_01(s, t, local, fi):
    img = plate(s, local)
    img = window_sweep(img, t, eighths_in(s))
    img = clock_insert(img, s['id'], ' 4:41', 0.6)
    return bloom_in(img, local, 4)


def a_chorus3_02(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    crt = REG(sid, 'crt', None)
    if crt is not None:
        u = (local * 1.0) % 1.08
        u = u if u < 0.54 else 1.08 - u
        mov = technicolor(other('A-verse-03', 4.5 + u), t, fi) * np.float32(0.45)
        img = put_quad(img, fx.crt(mov, t, barrel_k=0.08), crt, 'over')
    img = clock_insert(img, sid, ' 4:42', 0.6)
    cal = REG(sid, 'calendar', None)
    if cal is not None:
        img = put_quad(img, calendar_card(1.0, 1.0, tint='#7F9CC8'), cal, 'over')
    return img


def a_chorus3_03(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    img = fx.grade(img, warm=-0.15, tint='#5F7FB0', tint_amt=0.12)
    lamps = REG(sid, 'lamps', [[400, 220], [1500, 200]])
    for (x, y), b in zip(lamps, (117.72, 118.46)):
        k = 1.0 if t < b else math.exp(-(t - b) * 5.0)
        img = img + fx.hexc('#FFD9A0')[None, None] * (fx.ellipse_mask(x, y, 160, 160, feather=110) * 0.45 * k)[..., None]
    return fx.halation(img, 0.15)


def a_chorus3_04(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, in_t=0.0)
    pud = REG(sid, 'puddle', [960, 880, 360, 90])
    mem = other('A-chorus1-01', 1.0 + local)[::-1]
    mem = fx.grade(mem, warm=0.3, gain=1.25)
    k = 1.0 if t < 119.94 else 1.0 - clamp((t - 119.94) / (6 / 24))
    if t >= 119.94:
        mem = fx.ripple(mem, W / 2, H / 2, t, 119.94, speed=700.0, wavelength=40.0, amp=14.0, decay=1.0)
    img = put_ellipse(img, mem, pud, 'screen', amt=0.8 * k)
    if 119.94 <= t < 119.94 + 4 / 24:
        img = fx.sparkles(img, t, n=40, seed=19, area=(int(pud[0] - pud[2]), int(pud[1] - 200), int(pud[0] + pud[2]), int(pud[1])),
                          color='#FFE7B0', rate=12.0)
    return img


def a_chorus3_05(s, t, local, fi):
    sid = s['id']
    # 1.6x speed ramp over the last half beat into his turn
    lt = local if t < 123.28 else (123.28 - s['start']) + (t - 123.28) * 1.6
    img = plate(s, lt)
    beats = (120.68, 121.42, 122.17, 122.91)
    i = max([k for k, b in enumerate(beats) if t >= b] or [0])
    L, R_ = REG(sid, 'lamp_l', [700, 300]), REG(sid, 'lamp_r', [1220, 300])
    on = L if i % 2 == 0 else R_
    img = img + fx.hexc('#FF3B30')[None, None] * (fx.ellipse_mask(on[0], on[1], 70, 70, feather=60) * 0.9)[..., None]
    fxx, fyy = REG(sid, 'face', [960, 520])
    side = fx.ellipse_mask(fxx + (-120 if i % 2 == 0 else 120), fyy, 220, 320, feather=120)
    img = img + fx.hexc('#FF3B30')[None, None] * (side * 0.18)[..., None]
    return img


def a_chorus3_06(s, t, local, fi):
    cuts = [('A-chorus3-03', 0.20, 'run'), ('A-chorus1-01', 1.20, 'mem'), ('A-chorus3-03', 0.60, 'run'),
            ('A-chorus1-05', 1.40, 'mem'), ('A-hook-01', 1.00, 'mem'), ('A-chorus2-01', 1.50, 'mem'),
            ('A-chorus3-01', 1.00, 'run'), ('A-bridge1-06', 2.00, 'mem')]
    i = min(7, int(local / (BEAT / 2)))
    sid, t0, kind = cuts[i]
    img = other(sid, t0 + (local - i * BEAT / 2))
    if kind == 'mem':
        img = fx.white_bloom(fx.grade(img, warm=0.35, gain=1.3), 0.25)
    else:
        img = fx.grade(img, warm=-0.25, tint='#5F7FB0', tint_amt=0.2)
        img = np.maximum(img, np.float32(0.18))          # mid-grey floor: caps the luminance jumps
        img = fx.letterbox(img, open_k=0.0, color=(0.2, 0.22, 0.27))
    for sn in (124.39, 125.87):
        if sn <= t < sn + 2 / 24:
            img = fx.chroma(img, 14.0)
            img = fx.screen(img, np.roll(img, 30, 1), 0.4)
    return img


def a_chorus3_07(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    hy = _horizon(sid, 600)
    nb = sum(1 for b in beats_in(s) if t >= b)
    img = img + fx.hexc('#FF9EC4')[None, None] * (np.exp(-((fx._YS - hy) / (40 + 25 * nb)) ** 2) * 0.25)[..., None]
    if t >= 128.09:
        k = clamp((t - 128.09) / 0.6)
        cone = np.clip(1 - np.abs(fx._XS - (-300 + 2600 * k)) / 500.0, 0, 1) * 0.45
        streak = np.exp(-((fx._YS - 520) / 10.0) ** 2) * np.clip(1 - np.abs(fx._XS - (-300 + 2600 * k)) / 1400, 0, 1)
        img = img + fx.hexc('#FFF4DE')[None, None] * (cone + streak * 0.8)[..., None]
    # 光の走査 wipe out
    img = fx.rect_sweep(img, t, s['end'] - 0.37, 99.0, color='#FFF4DE', n=1, w=1100, h=1080, y=0, speed=-5200.0, amount=0.7)
    return img


def a_chorus3_08(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    img = fx.heat_haze(img, t, amp=0.006, region=(fx._YS > 700).astype(np.float32))
    img = window_sweep(img, t, eighths_in(s), amount=0.4)
    hb = REG(sid, 'him_box', [700, 200, 1200, 1000])
    crop = img[hb[1]:hb[3], hb[0]:hb[2]][:, ::-1]
    if crop.size and int((t - 0.682) / (BEAT / 2)) % 2 == 0:
        off = int((local * 900) % 400)
        img = fx.screen(img, np.roll(cv2.resize(crop, (W, H)) * 0.6, off, 1), 0.18)
    return img


def a_chorus3_09(s, t, local, fi):
    d = s['end'] - s['start']
    lt = local * (1.0 - 0.1 * clamp(local / d))
    img = plate(s, lt)
    return window_sweep(img, t, eighths_in(s), amount=0.35)


def his_reflection(img, src_t, x_shift, amt):
    refl = other('A-chorus3-09', src_t)[:, ::-1]
    fres = np.clip(0.5 + 0.5 * ((fx._XS - W / 2) / (W / 2)) ** 2, 0, 1)[..., None]
    refl = np.roll(refl * fres, int(x_shift), 1)
    return fx.screen(img, refl, amt)


def a_chorus3_10(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    # his running reflection slides in from the edge and settles over her face by 134.39; slows during the fill
    k = ease((t - s['start']) / (134.39 - s['start']))
    fx_ = REG(sid, 'face', [960, 500])[0]
    shift = (W - fx_ + 400) * (1 - k)
    rate = 1.0 if t < 133.10 else 1.0 - 0.4 * clamp((t - 133.10) / (135.14 - 133.10))
    img = his_reflection(img, 0.1 + local * rate, shift, 0.35)
    img = img + fx.hexc('#FF9EC4')[None, None] * (np.exp(-((fx._XS - (W * ((local * 0.4) % 1.5) - 300)) / 200) ** 2) * 0.08)[..., None]
    return img


# ================================================================== bridge2
def a_bridge2_01(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, in_t=0.0, speed=0.85)
    img = his_reflection(img, 0.1 + local * 0.3, 0, 0.30)
    rng = np.random.default_rng(46)
    for _ in range(40):                                  # dust specks on the glass catching the light
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        img = img + np.float32(0.25) * fx.ellipse_mask(x, y, 1.6, 1.6, feather=1.2)[..., None]
    slide = 0.02 * W * ease(local / (s['end'] - s['start']))
    M = np.float32([[1, 0, -slide], [0, 1, 0]])
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)


def a_bridge2_02(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, in_t=0.0, speed=0.85)
    k = ease((t - 141.42) / (144.39 - 141.42))
    img = his_reflection(img, 0.1 + 0.3 * (t - 135.5), W * 0.6 * k, 0.30 * (1 - 0.6 * k))
    if t >= 144.39:                                       # the sun clears the horizon: a level beam sweeps left -> right
        kk = clamp((t - 144.39) / 1.2)
        beam = np.clip((W * kk * 1.4 - fx._XS) / 300.0, 0, 1)
        lit = fx.grade(img, warm=0.25, lift=0.12)
        blue = fx.grade(img, warm=-0.2, tint='#5F7FB0', tint_amt=0.15)
        img = blue + (lit - blue) * beam[..., None]
    if t >= 146.61:
        img = fx.white_bloom(fx.grade(img, warm=0.4), 0.6 * clamp((t - 146.61) / 0.74))
    return haze_out(img, t, s)


# ================================================================== chorus4
def a_chorus4_01(s, t, local, fi):
    sid = s['id']
    img = haze_in(plate(s, local), t, local)
    hy = _horizon(sid, 600)
    amp = 0.006 + 0.02 * clamp(local / 2.2)
    img = fx.heat_haze(img, t, amp=amp, region=np.clip((fx._YS - hy + 120) / 120.0, 0, 1))
    img = mirage_shimmer(img, t, hy, 60, 4.0, 0.6)
    tb = REG(sid, 'train_box', None)
    if tb is not None and t >= 148.6:
        k = clamp((t - 148.6) / (149.57 - 148.6))
        x0, y0, x1, y1 = tb
        reg = np.zeros((H, W), np.float32)
        reg[y0:y1, x0:x1] = 1
        img = fx.heat_haze(img, t, amp=0.03 * k, region=cv2.GaussianBlur(reg, (0, 0), 20))
    return img


def a_chorus4_02(s, t, local, fi):
    img = plate(s, local)
    img = clock_insert(img, s['id'], ' 5:02', 0.35)
    return fx.motes(img, t, n=90, seed=21, amount=0.6)


def a_chorus4_03(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    img = fx.sparkles(img, t, n=160, seed=23, area=tuple(REG(sid, 'sea_box', [0, 560, 1920, 1080])), rate=6.0)
    img = fx.bloom(img, 0.8, 18, 0.2)
    return fx.heat_haze(img, t, amp=0.003)


def a_chorus4_04(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    fxx, fyy = REG(sid, 'face', [960, 520])
    ca = fx.caustics(t, 90.0) * fx.ellipse_mask(fxx, fyy + 120, 360, 420, feather=160)
    img = img + fx.hexc('#FFF4D6')[None, None] * (ca * 0.18)[..., None]
    return fx.bloom(img, 0.85, 10, 0.25)


def a_chorus4_05(s, t, local, fi):
    from mv import text
    d = s['end'] - s['start']
    sun = other('A-chorus4-01', 1.0 + local * (2.0 / d), zoom=1.35, cx=REG('A-chorus4-01', 'sun_x', 0.5), cy=REG('A-chorus4-01', 'sun_y', 0.45))
    spk = other('A-chorus4-03', 0.5 + local * (2.0 / d))
    img = fx.screen(sun, spk, 0.35)
    nb = sum(1 for b in beats_in(s) if t >= b)
    img = ev(img, 0.4 * nb)
    if t >= 161.44:
        img = fx.bloom(img, 0.6, 30, 0.4 * clamp((t - 161.44) / 0.5))
    # the unsung L54 writes itself across the glare, one glyph per 1.5 beats; 幸せ completes (160.68) and glows
    word = '君に幸せあげられない'
    step = 1.5 * BEAT * (d - 0.9) / (len(word) * 1.5 * BEAT)
    n = int(clamp((t - s['start'] - 0.05) / step, 0, len(word)))
    if n > 0:
        gl, _ = text.layout_h(word[:n], 960, 300, 92, 'mincho', tracking=0.15, align='center')
        f, _ = text.render_glyphs(gl)
        if f is not None:
            dis = clamp((t - 161.6) / 0.5)
            if dis > 0:
                f = f * (np.random.default_rng(int(t * 24)).random(f.shape) > dis).astype(np.float32)
            halo = cv2.GaussianBlur(f, (0, 0), 6.0) * (0.6 if t >= 160.68 else 0.3)
            img = img + fx.hexc('#FFF6E8')[None, None] * halo[..., None]
            img = img + (fx.hexc('#FFF6E8')[None, None] - img) * f[..., None]
        gl, _ = text.layout_h('我给不了你幸福', 960, 380, 32, 'zh', tracking=0.2, align='center')
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=0.85))
        if f is not None:
            img = img + (fx.hexc('#FFF6E8')[None, None] - img) * f[..., None]
    # the letterbox bars thin over the build; a 4-frame white bloom to #FFFFFF lands on 162.17
    img = fx.letterbox(img, open_k=clamp(local / d))
    return bloom_out(img, t, s['end'], 4)


# ================================================================== outro
def a_outro_01(s, t, local, fi):
    img = plate(s, local, in_t=0.0, speed=0.85)
    img = fx.bloom(img, 0.82, 16, 0.2)
    img = fx.heat_haze(img, t, amp=0.002)
    img = fx.light_leak(img, t, 165.13, dur=1.0, color='#FFD9A0', direction=1, amount=0.45)
    return bloom_in(img, local, 8)


def luma_key(img, lo=0.35, hi=0.7):
    l = fx.lum(img)
    return np.clip((l - lo) / (hi - lo), 0, 1)


def a_outro_02(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    hb = REG(sid, 'her_box', [760, 300, 1160, 900])
    reg = np.zeros((H, W), np.float32)
    reg[hb[1]:hb[3], hb[0]:hb[2]] = 1
    reg = cv2.GaussianBlur(reg, (0, 0), 30)
    img = fx.heat_haze(img, t, amp=0.025, region=reg)
    hy = _horizon(sid, hb[3])
    return mirage_shimmer(img, t, hy, 80, 5.0, 0.6)


def a_outro_03(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, in_t=0.0, speed=0.85)
    img = fx.grade(img, sat=1.0 + 0.1 * clamp((t - 171.05) / 1.5))
    hy = _horizon(sid, 600)
    if t < 172.54:                                          # her mirage figure ahead of him in the band
        her = other('A-outro-02', 1.0)
        hb = REG('A-outro-02', 'her_box', [760, 300, 1160, 900])
        crop = her[hb[1]:hb[3], hb[0]:hb[2]]
        if crop.size:
            sc = 120 / max(1, crop.shape[0])
            cr = cv2.resize(crop, (max(2, int(crop.shape[1] * sc)), 120))
            a = luma_key(cr, 0.2, 0.6) * 0.7
            x0 = int(REG(sid, 'mirage_x', 960) - cr.shape[1] / 2)
            y0 = int(hy - 120)
            roi = img[y0:y0 + 120, x0:x0 + cr.shape[1]]
            if roi.shape[:2] == cr.shape[:2]:
                img[y0:y0 + 120, x0:x0 + cr.shape[1]] = roi + (cr - roi) * a[..., None]
    else:                                                   # it breaks like water
        k = t - 172.54
        img = fx.ripple(img, REG(sid, 'mirage_x', 960), hy - 60, t, 172.54, speed=900.0, wavelength=50.0, amp=12.0, decay=1.4)
        if k < 0.6:
            img = fx.sparkles(img, t, n=80, seed=31, area=(700, int(hy - 300), 1220, int(hy + 60)), color='#FFF0D8', rate=14.0)
            rb = np.exp(-((fx._XS - 960) ** 2 + (fx._YS - hy + 60) ** 2) / (2 * (200 + 600 * k) ** 2))
            rainbow = np.stack([np.sin(fx._XS / 40.0), np.sin(fx._XS / 40.0 + 2.1), np.sin(fx._XS / 40.0 + 4.2)], -1) * 0.5 + 0.5
            img = img + rainbow * (rb * 0.15 * (1 - k / 0.6))[..., None]
    amp = 0.012 if t < 174.02 else 0.003
    return fx.heat_haze(img, t, amp=amp)


def a_outro_04(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    e = disc_of(sid, local, img, REG(sid, 'mirror', [960, 420, 150, 150]))
    hb = REG(sid, 'him_box', [700, 200, 1200, 1000])
    crop = img[hb[1]:hb[3], hb[0]:hb[2]]
    if crop.size:
        img = put_ellipse(img, crop, e, 'over', fisheye=0.4, mirror=True)
    return img


def a_outro_05(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    crt = np.float32(REG(sid, 'crt', [[760, 330], [1160, 330], [1160, 640], [760, 640]]))
    P = crt.mean(0)
    if t < 181.42:
        u = local % 1.08
        u = u if u < 0.54 else 1.08 - u
        mov = technicolor(other('A-verse-03', 4.5 + u), t, fi) * np.float32(0.5)
        img = put_quad(img, fx.crt(mov, t, barrel_k=0.08), crt, 'over')
    else:                                                    # ブラウン管収束: squash to a line (6 f), then a dot (6 f)
        k1 = clamp((t - 181.42) / (6 / 24))
        k2 = clamp((t - 181.42 - 6 / 24) / (6 / 24))
        dark = np.zeros((H, W, 3), np.float32)
        img = put_quad(img, dark, crt, 'over')
        w2 = (crt[1][0] - crt[0][0]) / 2 * (1 - 0.97 * k2)
        h2 = max(2.0, (crt[3][1] - crt[0][1]) / 2 * (1 - k1))
        glow = fx.ellipse_mask(P[0], P[1], w2, h2 * 0.5 + 1, feather=6.0)
        bright = 1.4 + 1.2 * clamp((t - 181.92) / 1.0)
        img = img + np.float32(bright) * glow[..., None]
        img = img + fx.hexc('#E8F4FF')[None, None] * (fx.ellipse_mask(P[0], P[1], 60 + w2 * 0.3, 60, feather=50) * 0.4)[..., None]
    _cache['crt_P'] = (float(P[0]), float(P[1]))
    return img


def a_outro_06(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    img = fx.bloom(img, 0.8, 18, 0.28)
    img = fx.heat_haze(img, t, amp=0.002)
    if t >= 185.50:
        img = img * np.float32(1 - 0.3 * clamp((t - 185.50) / 0.2))
    return img


def a_outro_hook_01(s, t, local, fi):
    sid = s['id']
    img = plate(s, local, in_t=0.0, speed=0.85)
    ex, ey = REG(sid, 'eye', [960, 460])
    reg = fx.ellipse_mask(ex, ey, 360, 220, feather=140)
    img = fx.heat_haze(img, t, amp=0.006, region=reg)
    if t >= 188.83:
        pane = REG(sid, 'pane', [[0, 0], [1920, 0], [1920, 700], [0, 700]])
        img = put_quad(img, other('A-hook-03', 0.3 + (t - 188.83)), pane, 'screen', amt=0.30 * clamp((t - 188.83) / 0.5))
    if local < 0.2:
        img = img * np.float32(0.7 + 1.5 * local)
    return img


def a_outro_hook_02(s, t, local, fi):
    sid = s['id']
    img = plate(s, local)
    pane = REG(sid, 'pane', [[0, 0], [1920, 0], [1920, 700], [0, 700]])
    img = put_quad(img, other('A-hook-03', 2.0 + local), pane, 'screen', amt=0.30 * (1 - clamp(local / (4 * BEAT))))
    for b in beats_in(s):
        img = fx.rect_sweep(img, t, b, 99.0, color='#FFF4DE', n=1, w=160, h=1080, y=0, speed=-4200.0, amount=0.25)
    return haze_out(img, t, s)


def a_outro_hook_03(s, t, local, fi):
    from mv import text
    sid = s['id']
    img = other('A-verse-07', 0.0 + local * 0.9)
    hy = _horizon('A-verse-07', 560)
    hb = REG('A-verse-07', 'her_box', [860, 360, 1060, 700])
    reg = np.zeros((H, W), np.float32)
    reg[hb[1]:hb[3], hb[0]:hb[2]] = 1
    reg = cv2.GaussianBlur(reg, (0, 0), 40)
    amp = 0.015 + 0.045 * clamp((t - 194.76) / (196.24 - 194.76))
    img = fx.heat_haze(img, t, amp=amp, region=reg)
    twin = (fx._YS > hy).astype(np.float32) * clamp((t - 194.76) / 0.8)
    img = fx.heat_haze(img, t, amp=0.06 * clamp((t - 194.9) / 0.8), region=twin)
    # 196.24: the horizon flips; the frame rotates 180 deg about the horizon over two beats with motion blur
    if t >= 196.24:
        k = ease((t - 196.24) / (2 * BEAT))
        ang = 180.0 * k
        M = cv2.getRotationMatrix2D((W / 2, hy), ang, 1.0 + 0.08 * math.sin(math.pi * k))
        acc = np.zeros_like(img)
        for j in range(5):
            Mj = cv2.getRotationMatrix2D((W / 2, hy), ang - j * 2.0 * (1 - k), 1.0 + 0.08 * math.sin(math.pi * k))
            acc += cv2.warpAffine(img, Mj, (W, H), borderMode=cv2.BORDER_REFLECT)
        img = acc / 5
    # 197.0: the title 逃げ水 condenses in the reflected sky; 水 trails into shimmer
    if t >= 197.0:
        a = clamp((t - 197.0) / 0.5)
        gl, _ = text.layout_h('逃げ水', 960, 420, 200, 'mincho', tracking=0.1, align='center')
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a))
        if f is not None:
            sh = fx.heat_haze(np.repeat(f[..., None], 3, -1), t, amp=0.006, region=(fx._XS > 1060).astype(np.float32))[..., 0]
            img = img + (fx.hexc('#FFF8EC')[None, None] - img) * sh[..., None]
            refl = np.roll(sh[::-1], int(2 * 420 + 200 - H), 0) * 0.25
            img = img + (fx.hexc('#FFF8EC')[None, None] - img) * refl[..., None]
        gl, _ = text.layout_h('Heat Waves (Japanese ver.)', 960, 600, 46, 'corm_i', tracking=0.1, align='center')
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a))
        if f is not None:
            img = img + (fx.hexc('#FFF8EC')[None, None] - img) * f[..., None]
        gl, _ = text.layout_h('song: Lime  /  MV-A 逃げ水', 960, 660, 24, 'garamond', tracking=0.2, align='center')
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a * 0.8))
        if f is not None:
            img = img + (fx.hexc('#FFF8EC')[None, None] - img) * f[..., None]
    if t >= 197.72:
        k = clamp((t - 197.72) / (198.74 - 197.72))
        img = img + (fx.hexc('#FFF8EC')[None, None] - img) * np.float32(k ** 1.5)
    return img


tl.OWN_LYRICS.add('A-chorus4-05')
tl.GRAIN_FRAME['A-bridge2-01'] = lambda local, f: f if local >= 2 / 24 else int(round(135.5 * 24))
register(a_chorus3_01, a_chorus3_02, a_chorus3_03, a_chorus3_04, a_chorus3_05, a_chorus3_06, a_chorus3_07, a_chorus3_08,
         a_chorus3_09, a_chorus3_10, a_bridge2_01, a_bridge2_02, a_chorus4_01, a_chorus4_02, a_chorus4_03, a_chorus4_04,
         a_chorus4_05, a_outro_01, a_outro_02, a_outro_03, a_outro_04, a_outro_05, a_outro_06, a_outro_hook_01,
         a_outro_hook_02, a_outro_hook_03)

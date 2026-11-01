"""MV-B v2 ("Heat Waves"): generated full-scene footage printed by print2, with the film's devices on top.

Each shot is drawn in three stages:
  raw(s, t, local)          -> float RGB: the B2 footage (work/B2/B2-<id>), inserts (mirror worlds, CRT
                               pictures), dreamcore light (heat shimmer, mirage, glow) -- everything that should
                               be printed;
  print2                    -> the screen print (one palette per shot, fitted lazily on three raw frames);
  over(img, s, t, local)    -> graphics drawn on the print: LED boards, stamps, the vertical lyric column
                               (original lyrics only), English lines on a dot-matrix strip.
Shots without B2 footage yet fall back to their v1 recipe (mvb.recipes), so the film always renders whole.

  import mvb.v2   # registers the v2 recipes into mvb.timeline (render with tools/render_mvb.py --mv b2)
"""
import functools
import math
import os

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import LYRICS, BEAT
from . import timeline as tl
from . import recipes as v1              # noqa: F401  (v1 recipes register first; v2 overrides them)
from . import print_fx as pf
from .print2 import Printer
from .chars import world_inks, SECTION_WORLD

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WORK2 = os.path.join(ROOT, 'work', 'B2')
W, H = 1920, 1080
tl.ZH = False                            # original lyrics only (no translation column)
from mv import lyrics as _lyrics         # v1 fallback recipes that typeset translations directly get nothing
for _k in list(_lyrics.ZH):
    _lyrics.ZH[_k] = ''

# print2 settings per colour world
WORLD_PRINT = {
    '夜刷り Night Print': dict(glow=1.2, night=True),
    '正午刷り Noon Print': dict(shade=0.75, dot_dark=0.38, glow=0.6, sat=1.05, harmonize=0.32),
    'ブラウン管 CRT Glow': dict(glow=1.3, night=True),
    '月刷り Moon Print': dict(glow=1.1, night=True),
    '夕焼け刷り Dusk Print': dict(glow=1.0, sat=1.05),
    '祭 Festival': dict(glow=1.4, night=True),
    '二色夢刷り Two-ink Dream': dict(glow=0.9, night=True, harmonize=0.6),
    '黎明前 Blue Hour': dict(glow=1.0, night=True),
    '夜明け刷り Dawn Print': dict(glow=1.2, sat=1.05),
}


def b2_id(s):
    return 'B2-' + s['id'][2:]


# ------------------------------------------------------------------ footage
_CLIPS = {}


def clip_path(sid2):
    d = os.path.join(WORK2, sid2)
    for name in ('final_up.mp4', 'v_0_up.mp4', 'final.mp4', 'v_0.mp4'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


class Footage:
    """a B2 clip as raw frames (float RGB 1920x1080, cover-fit), sampled by shot-local time"""
    def __init__(self, path):
        from mv.clip import Clip
        self.c = Clip(path)
        self.dur = self.c.n / self.c.fps

    def at(self, t_src, zoom=1.0, cx=0.5, cy=0.5):
        from mv.clip import fit
        t_src = min(max(0.0, t_src), self.dur - 1.0 / self.c.fps)
        src = self.c.raw(t_src)
        rgb = cv2.cvtColor(src, cv2.COLOR_BGR2RGB).astype(np.float32) * (1 / 255.0)
        return fit(rgb, zoom, cx, cy)


class Still:
    """development stand-in while a shot's video is still being generated: the picked keyframe, framed exactly
    as the video will be (Wan's centre crop to 832x480, then the 1920-wide upscale cover-fitted to 1080)"""
    def __init__(self, path):
        im = cv2.imread(path)
        self.img = kf_frame(im)
        self.dur = 5.0

    def at(self, t_src, zoom=1.0, cx=0.5, cy=0.5):
        from mv.clip import fit
        return fit(self.img, zoom * (1.0 + 0.012 * t_src), cx, cy)


def kf_frame(im):
    h, w = im.shape[:2]
    cw = int(round(h * 832 / 480))
    x0 = (w - cw) // 2
    crop = im[:, x0:x0 + cw]
    up = cv2.resize(crop, (1920, int(round(1920 * h / cw))), interpolation=cv2.INTER_CUBIC)
    y0 = (up.shape[0] - 1080) // 2
    return cv2.cvtColor(up[y0:y0 + 1080], cv2.COLOR_BGR2RGB).astype(np.float32) * (1 / 255.0)


def kf2plate(pts, kw=1280, kh=704):
    """keyframe pixel coordinates -> plate (1920x1080) coordinates, for quads drawn on a keyframe"""
    cw = kh * 832 / 480
    s = 1920 / cw
    p = np.asarray(pts, np.float32).reshape(-1, 2)
    return np.stack([(p[:, 0] - (kw - cw) / 2) * s, p[:, 1] * s - (kh * s - 1080) / 2], 1)


@functools.lru_cache(maxsize=1)
def picks():
    import re
    out = {}
    p = os.path.join(ROOT, 'work', 'review', 'picks_B2.txt')
    if os.path.exists(p):
        for ln in open(p):
            m = re.match(r'(B2-\S+)\s+(kf_\d+)\.png', ln)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def kf_path(sid2):
    k = picks().get(sid2, 'kf_0')
    p = os.path.join(WORK2, sid2, k + '.png')
    return p if os.path.exists(p) else None


STANDIN = os.environ.get('HW_V2_STANDIN', '') == '1'


def zoom_map(sid2, zoom=1.0, cx=0.5, cy=0.5, t_src=0.0):
    """map points measured on the zoom-1 plate (1920x1080) to the frame of plate(..., zoom, cx, cy)"""
    f = footage(sid2)
    if isinstance(f, Still):
        w, h = W, H
        zoom = zoom * (1.0 + 0.012 * t_src)
        dy0 = 0.0
    else:
        w, h = f.c.w, f.c.h
        dy0 = (h * max(W / w, H / h) - H) / 2 / max(W / w, H / h)      # rows cropped off the top at zoom 1
    s0 = max(W / w, H / h)
    s = s0 * zoom
    px, py = cx * w, cy * h
    half_w, half_h = W / (2 * s), H / (2 * s)
    px = min(max(px, half_w), w - half_w) if w > 2 * half_w else w / 2
    py = min(max(py, half_h), h - half_h) if h > 2 * half_h else h / 2

    def m(pts):
        p = np.asarray(pts, np.float32).reshape(-1, 2)
        src = np.stack([p[:, 0] / s0, p[:, 1] / s0 + dy0], 1)       # plate px -> source px
        return np.stack([(src[:, 0] - px) * s + W / 2, (src[:, 1] - py) * s + H / 2], 1)
    return m


def footage(sid2):
    if sid2 not in _CLIPS:
        p = clip_path(sid2)
        if p:
            _CLIPS[sid2] = Footage(p)
        elif STANDIN and kf_path(sid2):
            _CLIPS[sid2] = Still(kf_path(sid2))
        else:
            _CLIPS[sid2] = None
    return _CLIPS[sid2]


def src_time(s, local, speed=None, in_t=0.08, sid2=None):
    """the clip time that plate() shows at shot-local time `local`"""
    f = footage(sid2 or b2_id(s))
    d = s['end'] - s['start']
    if speed is None:
        speed = min(1.0, max(0.55, (f.dur - in_t - 0.05) / d))
    return in_t + local * speed


def plate(s, local, speed=None, in_t=0.08, zoom=1.0, cx=0.5, cy=0.5, sid2=None):
    """this shot's footage at shot-local time; by default the clip is stretched to cover the shot"""
    f = footage(sid2 or b2_id(s))
    return f.at(src_time(s, local, speed, in_t, sid2), zoom, cx, cy)


_TRACKS = {}


def tracked(s, pts, local, box=None, sid2=None, pad=70):
    """points measured on the shot's first frame (the keyframe) -> where they are now, following the footage
    (planar track of the region round them, cached per clip); identity on a keyframe stand-in"""
    import json
    from . import v2_fx
    sid2 = sid2 or b2_id(s)
    p = np.asarray(pts, np.float32).reshape(-1, 2)
    f = footage(sid2)
    if f is None:
        return p
    if isinstance(f, Still):                     # a stand-in still zooms slowly about the centre (Still.at)
        z = 1.0 + 0.012 * src_time(s, local, sid2=sid2)
        c = np.float32([W / 2, H / 2])
        return (p - c) * z + c
    if box is None:
        box = (float(p[:, 0].min()), float(p[:, 1].min()), float(p[:, 0].max()), float(p[:, 1].max()))
    box = tuple(int(round(v)) for v in box)
    key = (sid2, box)
    if key not in _TRACKS:
        src = clip_path(sid2)
        fn = os.path.join(WORK2, sid2, f'track_q_{box[0]}_{box[1]}_{box[2]}_{box[3]}_{int(os.path.getmtime(src))}.json')
        if os.path.exists(fn):
            _TRACKS[key] = json.load(open(fn))
        else:
            n = max(1, int(f.c.n))
            tr = v2_fx.track_region(lambda i: f.at(i / f.c.fps), n, box, pad=pad)
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            json.dump(tr, open(fn, 'w'))
            _TRACKS[key] = tr
    tr = _TRACKS[key]
    i = int(round(src_time(s, local, sid2=sid2) * f.c.fps))
    C = np.float32(tr[min(len(tr) - 1, max(0, i))])
    x0, y0, x1, y1 = box
    B = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    Hm = cv2.getPerspectiveTransform(B, C)
    return cv2.perspectiveTransform(p[None], Hm)[0]


def tracked_box(s, box, local, **kw):
    """a box (x0, y0, x1, y1) on the first frame -> its tracked quad (TL, TR, BR, BL)"""
    x0, y0, x1, y1 = box
    return tracked(s, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], local, **kw)


# ------------------------------------------------------------------ dreamcore light (raw stage)
def heat(img, t, amp=0.006, region=None):
    from mva import fx
    return fx.heat_haze(img, t, amp=amp, region=region)


def glow(img, amt=0.25, thr=0.72, r=18):
    lum = img @ np.float32([0.2126, 0.7152, 0.0722])
    m = np.clip((lum - thr) / (1 - thr), 0, 1)
    b = cv2.GaussianBlur(img * m[..., None], (0, 0), r)
    return img + b * np.float32(amt)


def motes(img, t, n=40, seed=3, amount=0.35):
    from mva import fx
    return fx.motes(img, t, n=n, seed=seed, amount=amount)


# ------------------------------------------------------------------ printers
_PRINTERS = {}


def printer_for(s, raw_fn):
    sid2 = b2_id(s)
    pr = _PRINTERS.get(sid2)
    if pr is None:
        world = SECTION_WORLD.get(s['section'], '夜刷り Night Print')
        kw = dict(WORLD_PRINT.get(world, {}))
        kw.update(SHOT_PRINT.get(s['id'], {}))
        # the palette cache is keyed on the source (stand-in keyframe vs final footage) and the print settings
        import hashlib
        src = clip_path(sid2) or kf_path(sid2) or ''
        tag = hashlib.md5((src + str(int(os.path.getmtime(src)) if src else '') + repr(sorted(kw.items()))).encode()).hexdigest()[:8]
        pr = Printer(world_inks(s['id']), name=f'{sid2}_{tag}', **kw)
        if pr.pal is None:
            d = s['end'] - s['start']
            pr.fit([raw_fn(s, s['start'] + d * f, d * f) for f in (0.15, 0.5, 0.85)])
        _PRINTERS[sid2] = pr
    return pr


SHOT_PRINT = {}          # per-shot printer overrides (filled by the recipes below)


# ------------------------------------------------------------------ English lines on a dot-matrix strip
_LEDCACHE = {}


def led_caption(img, t, idx, y=1004, on='#F5C842', rows=10, dot=6):
    """the English line runs across a station-style LED strip at the foot of the frame"""
    ln = LYRICS[idx]
    if not (ln['t'] - 0.1 <= t <= ln['end'] + 0.3):
        return img
    key = (idx, on, rows, dot)
    if key not in _LEDCACHE:
        _LEDCACHE[key] = pf.led_board(ln['text'].upper(), rows=rows, dot=dot, on=on, off='#1A1A20', bg='#0C0C10', font='silk')[0]
    board = _LEDCACHE[key]
    bh, bw = board.shape[:2]
    k = clamp((t - ln['t']) / max(0.4, ln['end'] - ln['t']))
    a = clamp((t - ln['t'] + 0.1) / 0.15) * (1 - clamp((t - ln['end']) / 0.3))
    strip_w = min(W - 240, bw)
    x0 = (W - strip_w) // 2
    off = int(max(0, bw - strip_w) * k)
    crop = board[:, off:off + strip_w]
    y0 = int(y - bh / 2)
    frame = np.zeros((bh + 16, strip_w + 16, 3), np.float32)
    frame[:] = pf.hexc('#0C0C10')
    frame[8:8 + bh, 8:8 + crop.shape[1]] = crop
    out = img.copy()
    roi = out[y0 - 8:y0 - 8 + frame.shape[0], x0 - 8:x0 - 8 + frame.shape[1]]
    if roi.shape[:2] == frame.shape[:2]:
        out[y0 - 8:y0 - 8 + frame.shape[0], x0 - 8:x0 - 8 + frame.shape[1]] = roi + (frame - roi) * np.float32(a * 0.92)
    return out


# ------------------------------------------------------------------ the generic v2 recipe
RAW = {}                 # shot id -> raw(s, t, local) override
STAGE = {}               # shot id -> fn(s, t, local) -> print2 stage dict (press running part-way) or None
ENGLISH = {}             # shot id -> fn(img, s, t): a shot's own handling of its English lines
OVER = {}                # shot id -> over(img, s, t, local) override (graphics on the print)


def default_raw(s, t, local):
    img = plate(s, local)
    world = SECTION_WORLD.get(s['section'], '')
    if world in ('正午刷り Noon Print',):
        img = heat(img, t, 0.005)
    if world in ('夜刷り Night Print', 'ブラウン管 CRT Glow', '月刷り Moon Print', '祭 Festival', '黎明前 Blue Hour'):
        img = glow(img, 0.22)
    return img


def english_lines(img, s, t):
    for idx in s.get('lyric', []):
        if LYRICS[idx]['lang'] == 'en':
            img = led_caption(img, t, idx)
    return img


def make_recipe(s):
    raw_fn = RAW.get(s['id'], default_raw)

    def recipe(s, t, local, fi):
        raw = raw_fn(s, t, local)
        st = STAGE[s['id']](s, t, local) if s['id'] in STAGE else None
        img = printer_for(s, raw_fn)(raw, stage=st)
        fn = OVER.get(s['id'])
        if fn is not None:
            img = fn(img, s, t, local)
        return ENGLISH.get(s['id'], english_lines)(img, s, t)
    return recipe


def install():
    """override every shot that has B2 footage (or a v2-only recipe) with its v2 recipe"""
    from . import v2_card, v2_map, v2_shots, v2_tv, v2_b1
    GRAPHIC.update(v2_card.GRAPHIC)
    GRAPHIC.update(v2_map.GRAPHIC)
    v2_shots.install()
    v2_tv.install()
    v2_b1.install()
    from . import v2_outro, v2_more
    v2_outro.install()
    v2_more.install()                    # after v2_outro: the dream's duotone bridge2-04 replaces the print2 peel
    own = set(v2_card.OWN_TYPE) | V2_OWN_TYPE
    n = 0
    for s in tl.SHOTS:
        sid = s['id']
        if sid in GRAPHIC:
            tl.RECIPES[sid] = GRAPHIC[sid]
        elif clip_path(b2_id(s)) or (STANDIN and kf_path(b2_id(s))):
            tl.RECIPES[sid] = make_recipe(s)
        else:
            continue
        n += 1
        if sid in own:
            tl.OWN_TYPE.add(sid)
        else:
            tl.OWN_TYPE.discard(sid)           # v1 recipes typeset their own lines; v2 uses the default column
        if sid in FADE_IN or sid in FADE_OUT:
            tl.RECIPES[sid] = _with_fades(tl.RECIPES[sid], sid)
        if any(s['start'] - 0.01 <= h < s['end'] for h in HITS):
            tl.RECIPES[sid] = _with_hit(tl.RECIPES[sid])
    return n


# the press hits on the big downbeats (the choruses, the outro): the plates jump out of register and settle
HITS = [28.83, 76.24, 111.79, 147.35, 162.17]


def registration_hit(img, k):
    """a double impression: the sheet takes a second, misregistered hit of the same plates (ink multiplies on ink, the
    paper stays paper), offset by up to ~10 px and settling back as k -> 0"""
    if k <= 0.02:
        return img
    dx, dy = 10.0 * k, -5.0 * k
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    ghost = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    paper = pf.hexc('#EDE3CF')[None, None]
    ratio = np.clip(ghost / paper, 0, 1)
    w = 0.8 * min(1.0, k * 1.3)
    return img * (1 - w * (1 - ratio))


def _with_hit(fn):
    def recipe(s, t, local, fi):
        img = fn(s, t, local, fi)
        for h in HITS:
            if 0 <= t - h < 0.30:
                u = (t - h) / 0.30
                img = registration_hit(img, (1 - u) ** 2 * (1 if u > 0.03 else 0.6))
        return img
    return recipe


# the film's light relays: the cut happens inside a flash of light (the sun in the card -> noon; the moon bursting
# into the festival; the headlight's halo -> the sunrise); seconds and colour
FADE_IN = {'B-hook-01': (0.30, '#FFF4DC'), 'B-chorus3-01': (0.22, '#FFF2C8'), 'B-outro-01': (0.42, '#FFF4DC')}
FADE_OUT = {'B-bridge1-07': (0.16, '#FFF2C8')}


def _with_fades(fn, sid):
    def recipe(s, t, local, fi):
        img = fn(s, t, local, fi)
        if sid in FADE_IN:
            d, col = FADE_IN[sid]
            k = 1 - clamp(local / d)
            if k > 0:
                img = img + (pf.hexc(col)[None, None] - img) * np.float32(k * k)
        if sid in FADE_OUT:
            d, col = FADE_OUT[sid]
            k = clamp((local - (s['end'] - s['start'] - d)) / d)
            if k > 0:
                img = img + (pf.hexc(col)[None, None] - img) * np.float32(k * k)
        return img
    return recipe


V2_OWN_TYPE = set()      # v2 recipes that draw their own Japanese lines
LYRIC_POS = {}           # shot id -> VLyric kwargs (x, y, size): keep the column off faces


def _default_lyrics(s, img, t):
    from mv.timing import LYRICS as _L
    from .typo import VLyric
    for idx in s.get('lyric', []):
        ln = _L[idx]
        if ln['lang'] == 'en' or not (ln['t'] - 0.1 <= t <= ln['end'] + 0.4):
            continue
        key = (s['id'], idx)
        if key not in tl._LY:
            kw = dict(LYRIC_POS.get(s['id'], {}))
            tl._LY[key] = VLyric(idx, accent=tl.ACCENT.get(s['section'], '#D9402B'), zh=False, **kw)
        img = tl._LY[key].draw(img, t)
    return img


tl.default_lyrics = _default_lyrics
GRAPHIC = {}             # shot id -> full recipe for the pure-graphics shots (map, stamp card)

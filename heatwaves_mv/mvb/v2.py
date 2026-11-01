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


def footage(sid2):
    if sid2 not in _CLIPS:
        p = clip_path(sid2)
        _CLIPS[sid2] = Footage(p) if p else None
    return _CLIPS[sid2]


def plate(s, local, speed=None, in_t=0.08, zoom=1.0, cx=0.5, cy=0.5, sid2=None):
    """this shot's footage at shot-local time; by default the clip is stretched to cover the shot"""
    f = footage(sid2 or b2_id(s))
    d = s['end'] - s['start']
    if speed is None:
        speed = min(1.0, max(0.55, (f.dur - in_t - 0.05) / d))
    return f.at(in_t + local * speed, zoom, cx, cy)


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
        pr = Printer(world_inks(s['id']), name=sid2, **kw)
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
        _LEDCACHE[key] = pf.led_board(ln['text'].upper(), rows=rows, dot=dot, on=on, off='#1A1A20', bg='#0C0C10', font='silk')
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
        img = printer_for(s, raw_fn)(raw)
        fn = OVER.get(s['id'])
        if fn is not None:
            img = fn(img, s, t, local)
        return english_lines(img, s, t)
    return recipe


def install():
    """override every shot that has B2 footage (or a v2-only recipe) with its v2 recipe"""
    n = 0
    for s in tl.SHOTS:
        if s['id'] in GRAPHIC:
            tl.RECIPES[s['id']] = GRAPHIC[s['id']]
            n += 1
        elif clip_path(b2_id(s)):
            tl.RECIPES[s['id']] = make_recipe(s)
            n += 1
    return n


GRAPHIC = {}             # shot id -> full recipe for the pure-graphics shots (map, stamp card)

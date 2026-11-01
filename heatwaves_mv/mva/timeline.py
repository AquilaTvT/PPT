"""MV-A timeline: shots.json + per-shot recipes -> frames at 24 fps (1920x1080).

Media per shot (best available): work/A/<id>/final.mp4 (upscaled + retimed) > v_*_up.mp4 > keyframe
(kf picked) > a labelled card. Recipes in mva/recipes.py may override any shot; the default recipe plays
the clip per the spec's `use` field, grades it, adds haze/letterbox/typography from the spec text.
"""
import json
import math
import os
import re

import cv2
import numpy as np

from mv.clip import Clip
from mv import text
from . import fx
from .typo import Lyric

ROOT = os.path.join(os.path.dirname(__file__), '..')
SPEC = os.path.join(ROOT, 'design', 'mv_a', 'shots.json')
WORK = os.environ.get('HW_WORK_A', os.path.join(ROOT, 'work', 'A'))
FPS = 24
DUR = 198.74


def load_spec():
    d = json.load(open(SPEC))
    return d['shots']


SHOTS = load_spec()
BY_ID = {s['id']: s for s in SHOTS}


# ------------------------------------------------------------------ media
_clip_cache = {}
_still_cache = {}


def media_path(sid):
    d = os.path.join(WORK, sid)
    for name in ('final_up.mp4', 'v_0_up.mp4', 'final.mp4', 'v_0_24.mp4', 'v_0.mp4'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return 'video', p
    man = os.path.join(WORK, 'manifest.json')
    if os.path.exists(man):
        st = json.load(open(man)).get(sid, {})
        kf = (st.get('pick') or {}).get('kf')
        if kf:
            p = os.path.join(d, os.path.basename(kf))
            if os.path.exists(p):
                return 'still', p
    for name in ('kf_0.png', 'kf_1.png'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return 'still', p
    return None, None


def clip(sid):
    if sid not in _clip_cache:
        kind, p = media_path(sid)
        _clip_cache[sid] = (kind, Clip(p) if kind == 'video' else p)
    return _clip_cache[sid]


def card(sid, t):
    img = np.zeros((fx.H, fx.W, 3), np.float32)
    img[:] = fx.hexc('#20263A')
    s = BY_ID.get(sid, {})
    gl, _ = text.layout_h(sid, 960, 470, 64, 'kaku', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        img = fx.over(img, np.broadcast_to(fx.hexc('#F2EDE4'), img.shape), f)
    gl, _ = text.layout_h((s.get('beat') or '')[:40], 960, 560, 30, 'zh', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        img = fx.over(img, np.broadcast_to(fx.hexc('#AEB7C8'), img.shape), f)
    return img


def frame_of(sid, local_t, in_t=0.2, speed=1.0, zoom=1.0, cx=0.5, cy=0.5, pingpong=False, still_push=0.03, dur=3.0):
    """footage of shot `sid` at local time; stills (no video yet) get a slow push so timing can be judged"""
    kind, m = clip(sid)
    if kind == 'video':
        c = m
        tt = in_t + local_t * speed
        if pingpong and c.duration > 0:
            per = c.duration * 2
            tt = tt % per
            tt = per - tt if tt > c.duration else tt
        tt = min(max(0.0, tt), max(0.0, c.duration - 1.0 / FPS))
        raw = c.raw(tt)                                    # uint8 BGR from the decoder
        if raw is None:
            return card(sid, local_t)
        rgb = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB).astype(np.float32) * (1 / 255.0)
        return fx.fit(rgb, zoom=zoom, cx=cx, cy=cy)
    if kind == 'still':
        if m not in _still_cache:
            _still_cache[m] = cv2.cvtColor(cv2.imread(m), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        k = local_t / max(0.1, dur)
        return fx.fit(_still_cache[m], zoom=zoom * (1 + still_push * k), cx=cx, cy=cy)
    return card(sid, local_t)


# ------------------------------------------------------------------ spec parsing
def parse_use(s):
    """'0.20-3.16 s at 1.0x' -> (in, speed); 'retimed to 0.85x' etc."""
    u = s.get('use', '')
    m = re.search(r'(\d+\.\d+)\s*-\s*(\d+\.\d+)\s*s', u)
    sp = re.search(r'(\d+(?:\.\d+)?)x', u)
    t_in = float(m.group(1)) if m else 0.2
    speed = float(sp.group(1)) if sp else 1.0
    if 'All 121 frames' in u or 'one long held take' in u.lower():
        t_in = 0.0
    return t_in, speed


def is_present(s):
    c = s.get('composite', '') + s.get('use', '')
    return '2.39 letterbox' in c or 'letterbox (present' in c or 'letterbox is still on' in c


_REGIONS = None


def region_override(sid, key):
    """per-shot overrides from design/mv_a/regions.json (e.g. lyric_slot), read once"""
    global _REGIONS
    if _REGIONS is None:
        p = os.path.join(ROOT, 'design', 'mv_a', 'regions.json')
        _REGIONS = json.load(open(p)) if os.path.exists(p) else {}
    return _REGIONS.get(sid, {}).get(key)


def slot_for(s):
    low = (s.get('typography', '') or '').lower()
    slot = 'right'
    if 'left third' in low:
        slot = 'left'
    elif 'high center' in low or 'centred' in low or 'centered' in low:
        slot = 'center'
    return region_override(s['id'], 'lyric_slot') or slot      # moved off a face in the real footage


_SLOT_X = {'right': 1450, 'left': 470, 'center': 960, 'far_right': 1690, 'far_left': 230}


def _handover(idx):
    """True when line idx+1 starts as idx ends and is set in the same place (both English in the bar / at the foot,
    or both Japanese in the same column): idx must be gone by then, or the two overprint"""
    from mv.timing import LYRICS
    if idx + 1 >= len(LYRICS):
        return False
    a, b = LYRICS[idx], LYRICS[idx + 1]
    if b['t'] > a['end'] + 0.05:
        return False
    ha, hb = home_shot(idx), home_shot(idx + 1)
    if ha is None or hb is None:
        return False
    sa, sb = ha[0], hb[0]
    if a['lang'] == 'en' and b['lang'] == 'en':
        return True
    if is_present(sa) and is_present(sb):               # both translations sit centred in the bottom bar
        return True
    if a['lang'] != 'en' and b['lang'] != 'en':
        return abs(_SLOT_X.get(slot_for(sa), 1450) - _SLOT_X.get(slot_for(sb), 1450)) < 200
    return False


def lyric_for(s, idx):
    ty = s.get('typography', '') or ''
    low = ty.lower()
    slot = slot_for(s)
    font = 'hina' if 'hina' in low else 'mincho'
    world = 'memory'
    if 'moon white' in low or (is_present(s) and 'silver' not in low):
        world = 'present'
    if 'silver' in low:
        world = 'mirror'
    if s['section'] in ('outro', 'outro_hook', 'chorus4') and world == 'memory':
        world = 'dawn'
    if s['id'] in ('A-verse-03',):
        world = 'film'
    special = []
    if 'led red' in low:
        special.append('led_zero')
    if 'mirror-reversed' in low or '鏡文字' in ty:
        special.append('mirror_flip')
    if '君' in ty and ('warm' in low or 'bright' in low):
        special.append('warm_kimi')
    if 'completes' in low:
        special.append('complete70')
    lb = is_present(s)
    zh = 'bar' if lb else 'foot'
    if _handover(idx):        # the next line takes this place as this one ends: be gone by then
        from mv.timing import LYRICS
        return Lyric(idx, slot=slot, world=world, font=font, letterboxed=lb, zh=zh, special=special,
                     out_t=LYRICS[idx]['end'] - 0.15, fade_out=0.15)
    return Lyric(idx, slot=slot, world=world, font=font, letterboxed=lb, zh=zh, special=special)


# ------------------------------------------------------------------ default recipe
def default_recipe(s, t, local_t, frame_idx):
    t_in, speed = parse_use(s)
    img = frame_of(s['id'], local_t, in_t=t_in, speed=speed, dur=s['end'] - s['start'])
    comp = (s.get('composite') or '').lower()
    m = re.search(r'haze at (\d+(?:\.\d+)?)%', comp) or re.search(r'(\d+(?:\.\d+)?)% heat haze', comp)
    if m:
        img = fx.heat_haze(img, t, amp=float(m.group(1)) / 100.0)
    if 'halation' in comp:
        img = fx.halation(img, 0.25)
    if 'bloom' in comp:
        img = fx.bloom(img, 0.78, 14, 0.25)
    return img


RECIPES = {}       # filled by mva.recipes (shot id -> fn(s, t, local_t, frame_idx) -> img)
NO_GRAIN = set()   # shots printed without grain (A-verse-05: the over-perfect future)
OWN_LYRICS = set() # shots whose recipe typesets its own lines (the default lyric pass skips them)
GRAIN_FRAME = {}   # shot id -> fn(local_t, frame_idx) -> frame index for the grain (a time-stop freezes it)


def shot_at(t):
    for s in SHOTS:
        if s['start'] <= t < s['end']:
            return s
    return SHOTS[-1]


def letterbox_open(t):
    """present scenes are 2.39 until the bars slide open 171.05-172.54"""
    if t < 171.05:
        return 0.0
    return min(1.0, (t - 171.05) / (172.54 - 171.05))


LYRICS_CACHE = {}


_HOME = {}


def home_shot(idx):
    """the one shot that typesets line idx: of the shots listing it, the one it is sung over longest (a line
    listed by two shots used to switch columns at the second shot's window)"""
    if idx not in _HOME:
        from mv.timing import LYRICS
        ln = LYRICS[idx]
        cands = [x for x in SHOTS if idx in x.get('lyric', []) and x['id'] not in OWN_LYRICS]
        if not cands:
            _HOME[idx] = None
        else:
            ov = lambda x: min(x['end'], ln['end']) - max(x['start'], ln['t'])
            home = max(cands, key=ov)
            _HOME[idx] = (home, min(x['start'] for x in cands) - 0.3, max(x['end'] for x in cands) + 0.6)
    return _HOME[idx]


def lyrics_at(t):
    from mv.timing import LYRICS
    out = []
    for idx, ln in enumerate(LYRICS):
        if not (ln['t'] - 0.1 <= t <= ln['end'] + 0.5):
            continue
        h = home_shot(idx)
        if h is None:
            continue
        s, w0, w1 = h
        if w0 <= t < w1:
            key = (s['id'], idx)
            if key not in LYRICS_CACHE:
                LYRICS_CACHE[key] = lyric_for(s, idx)
            out.append(LYRICS_CACHE[key])
    return out


def render(t, frame_idx):
    s = shot_at(t)
    local = t - s['start']
    fn = RECIPES.get(s['id'], default_recipe)
    img = fn(s, t, local, frame_idx)
    if is_present(s):
        img = fx.letterbox(img, open_k=letterbox_open(t))
    for ly in lyrics_at(t):
        img = ly.draw(img, t)
    if s['id'] not in NO_GRAIN:
        gi = GRAIN_FRAME[s['id']](local, frame_idx) if s['id'] in GRAIN_FRAME else frame_idx
        img = fx.grain(img, gi, 0.022)
    return np.clip(img, 0, 1)

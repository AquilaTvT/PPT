"""Build an Edit straight from a designed shot list + the generation manifest.

Each shot shows the best media available — finished video > picked keyframe (animatic
placeholder with a slow push so timing can be judged) > a labelled card — plus its
lyric typography, and the cut into the next shot uses the transition named in the spec.

  from mv.assembly import build_from_spec
  ed = build_from_spec('design/mv_a_shots.json', 'work/A/manifest.json', post=...)
"""
import json
import os
import re

import cv2
import numpy as np

from . import core, lyrics
from .clip import clip as get_clip
from .core import Frame, smooth, lin
from .edit import Edit, Shot, Tr
from .timing import LYRICS

TRANSITIONS = [
    (r'match|hard cut|smash|^cut|straight cut', ('cut', 0.0, {})),
    (r'white|bloom|overexpos|flash', ('white', 0.35, {})),
    (r'black|fade to black|dip', ('black', 0.5, {})),
    (r'heat|haze|shimmer|mirage|ripple', ('heat', 0.6, {})),
    (r'crt|tv|channel|static', ('crt', 0.4, {})),
    (r'whip|swish|pan transition', ('whip', 0.36, {'direction': 1})),
    (r'iris', ('iris', 0.8, {})),
    (r'wipe|slide', ('wipe', 0.5, {'angle': 15})),
    (r'dot|halftone|pixel|dissolve into', ('dots', 0.6, {'grow': 'radial', 'cell': 24})),
    (r'dissolve|cross|fade|morph|blend', ('dissolve', 0.6, {})),
]


def transition_for(text):
    t = (text or '').lower()
    for pat, (kind, dur, params) in TRANSITIONS:
        if re.search(pat, t):
            return Tr(kind, dur, **params)
    return Tr('cut')


def load(path):
    d = json.load(open(path))
    if isinstance(d, dict) and 'sections' in d:
        return [s for sec in d['sections'] if sec for s in sec['shots']]
    return d.get('shots', d) if isinstance(d, dict) else d


def _media(st):
    if not st:
        return None, None
    if st.get('final') and os.path.exists(st['final']):
        return 'video', st['final']
    if st.get('video_pick') and os.path.exists(st['video_pick']):
        return 'video', st['video_pick']
    pick = (st.get('pick') or {}).get('kf')
    if pick and os.path.exists(pick):
        return 'still', pick
    return None, None


_img_cache = {}


def _still(path):
    if path not in _img_cache:
        im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        _img_cache[path] = im
    return _img_cache[path]


def _typo_params(spec):
    s = (spec or '').lower()
    vertical = not ('horizontal' in s or 'bottom' in s and 'vertical' not in s)
    x = 1750
    if 'left' in s:
        x = 330
    elif 'center' in s or 'centre' in s:
        x = 1000
    return vertical, x


def shot_fn(spec, st):
    kind, path = _media(st)
    lyr = [i for i in spec.get('lyric_ids', []) if 0 <= i < len(LYRICS)]
    vertical, x = _typo_params(spec.get('typography'))
    speed = float(spec.get('speed') or 1.0)

    def fn(t, sh):
        f = Frame('night')
        tl = t - sh.t0
        if kind == 'video':
            c = get_clip(path, speed)
            f.a = c.frame(tl)
        elif kind == 'still':
            u = lin(t, sh.t0, sh.t1)
            f.a = __import__('mv.clip', fromlist=['fit']).fit(_still(path), zoom=1.02 + 0.06 * smooth(u))
        else:
            f.a[:] = core._col('#1E2A5E')
        for i in lyr:
            ly = LYRICS[i]
            if ly['lang'] == 'en':
                lyrics.draw_h(f, t, i, x=960, y=930, size=64, fill='#FFFDF6', edge='#141B3D', zh_gap=66)
            elif vertical:
                lyrics.draw_v(f, t, i, x=x, y=110, size=78, fill='#FFFDF6', edge='#141B3D')
            else:
                lyrics.draw_h(f, t, i, x=960, y=930, size=60, fill='#FFFDF6', edge='#141B3D', zh_gap=62)
        if kind is None:
            from . import text
            gl, _ = text.layout_h(spec['id'], 960, 520, 54, 'dot', align='center')
            fc, sc = text.render_glyphs(gl, stroke=6)
            if fc is not None:
                f.over('#06081A', sc)
                f.over('#7FE3DE', fc)
        return f.a
    return fn


def build_from_spec(shots_path, manifest_path=None, post=None):
    shots = load(shots_path)
    man = json.load(open(manifest_path)) if manifest_path and os.path.exists(manifest_path) else {}
    shots = sorted(shots, key=lambda s: s['t0'])
    out, trans = [], {}
    for i, s in enumerate(shots):
        out.append(Shot(s['id'], s['t0'], s['t1'], shot_fn(s, man.get(s['id']))))
        trans[i] = transition_for(s.get('transition_out'))
    return Edit(out, trans, post=post)

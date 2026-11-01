"""MV-B timeline: design/mv_b/shots.json + per-shot recipes -> frames (1920x1080, 24 fps).

Recipes live in mvb/recipes.py: RECIPES[shot_id] = fn(s, t, local_t, frame_idx) -> img. A recipe that draws
its own lyrics adds the shot id to OWN_TYPE; otherwise the shot's lyric lines get the default style-A column.
Every frame ends with print_fx.finish (paper, gate jitter, corners, grain).
"""
import json
import os

import numpy as np

from mv import text
from mv.timing import LYRICS
from . import print_fx as pf
from .typo import VLyric

ROOT = os.path.join(os.path.dirname(__file__), '..')
SPEC = json.load(open(os.path.join(ROOT, 'design', 'mv_b', 'shots.json')))
SHOTS = SPEC['shots']
BY_ID = {s['id']: s for s in SHOTS}
RECIPES = {}
OWN_TYPE = set()
ZH = True                # translation column under the lyrics (MV-B v2 sets False: original lyrics only)
ACCENT = {'intro': '#D9402B', 'hook': '#2D6BE0', 'chorus1': '#2D6BE0', 'verse': '#D9402B', 'chorus2': '#F08A3C',
          'bridge1': '#D9402B', 'chorus3': '#D9402B', 'bridge2': '#F08A3C', 'chorus4': '#F08A3C', 'outro': '#D9402B',
          'outro_hook': '#2D6BE0'}


def shot_at(t):
    for s in SHOTS:
        if s['start'] <= t < s['end']:
            return s
    return SHOTS[-1]


def placeholder(s, t, local, fi):
    img = np.empty((1080, 1920, 3), np.float32)
    img[:] = pf.hexc('#141A33')
    gl, _ = text.layout_h(s['id'], 960, 480, 60, 'kaku', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        img += (pf.hexc('#EDE3CF') - img) * f[..., None]
    gl, _ = text.layout_h(s['beat'][:44], 960, 580, 28, 'zh', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        img += (pf.hexc('#7FC8B8') - img) * f[..., None]
    return img


_LY = {}


def default_lyrics(s, img, t):
    for idx in s.get('lyric', []):
        ln = LYRICS[idx]
        if ln['lang'] == 'en' or not (ln['t'] - 0.1 <= t <= ln['end'] + 0.4):
            continue
        key = (s['id'], idx)
        if key not in _LY:
            _LY[key] = VLyric(idx, accent=ACCENT.get(s['section'], '#D9402B'), zh=ZH)
        img = _LY[key].draw(img, t)
    return img


def render(t, frame_idx):
    s = shot_at(t)
    local = t - s['start']
    fn = RECIPES.get(s['id'], placeholder)
    img = fn(s, t, local, frame_idx)
    if s['id'] not in OWN_TYPE:
        img = default_lyrics(s, img, t)
    img = pf.finish(img, frame_idx)
    return np.clip(img, 0, 1)

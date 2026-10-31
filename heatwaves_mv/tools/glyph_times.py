"""Per-glyph (Japanese) / per-word (English) reveal times from the vocal stem.

For each lyric line, onsets are detected on the demucs vocal stem inside [t, end); the N glyphs of the
line are matched to onsets in order (the N strongest, re-sorted by time). If there are fewer onsets
than glyphs, the remaining glyphs are spread evenly between the onsets. Output: assets/glyph_times.json
  {"<line index>": [t_glyph0, t_glyph1, ...], ...}   (spaces and punctuation get the next glyph's time)
"""
import json
import os
import sys

import librosa
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mv.timing import LYRICS  # noqa: E402

VOC = os.environ.get('HW_VOCALS', '/tmp/claude-0/song/sep/htdemucs/hw/vocals.wav')
OUT = os.path.join(os.path.dirname(__file__), '..', 'assets', 'glyph_times.json')


def units(line):
    if line['lang'] == 'en':
        return line['text'].split()
    return [c for c in line['text'] if not c.isspace()]


def main():
    y, sr = librosa.load(VOC, sr=22050, mono=True)
    hop = 256
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop, backtrack=False, units='frames',
                                    pre_max=3, post_max=3, pre_avg=6, post_avg=6, delta=0.02, wait=2)
    t_on = librosa.frames_to_time(on, sr=sr, hop_length=hop)
    s_on = env[on]
    res = {}
    for ln in LYRICS:
        u = units(ln)
        n = len(u)
        a, b = ln['t'] - 0.05, ln['end'] - 0.05
        sel = (t_on >= a) & (t_on < b)
        ts, ss = t_on[sel], s_on[sel]
        if len(ts) >= n:
            idx = np.sort(np.argsort(-ss)[:n])
            times = list(ts[idx])
            times[0] = min(times[0], ln['t'])
        else:
            anchors = sorted(set([ln['t']] + list(ts)))
            times = list(anchors)
            span_end = ln['t'] + 0.75 * (ln['end'] - ln['t'])
            while len(times) < n:
                times.append(min(span_end, times[-1] + (span_end - ln['t']) / max(1, n)))
            times = sorted(times)[:n]
        res[str(ln['i'])] = [round(float(x), 3) for x in times]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=0)
    print('wrote', OUT, len(res), 'lines')


if __name__ == '__main__':
    main()

"""QA for a rendered film: duration / audio, flat frames, and a photosensitivity check.

  python3 tools/qa_video.py out/MV-B_full.mp4 [--expect 198.74]

Flash check (simplified W3C 2.3.1 general flash): the frame is split into a 4x4 grid; a cell 'flashes' when its
relative luminance changes by >= 0.10 between frames with the darker state below 0.80. A frame-to-frame transition
is a large-area flash event when cells covering >= 25% of the screen (4 of 16) change in the same direction. Two
opposing events form one flash; more than 3 flashes inside any 1-second window is reported as a FAIL window.
Flat frames (luma std < 0.015 at 320x180) are listed so intended blank frames can be told from mistakes.
"""
import argparse
import json
import subprocess
import sys

import numpy as np


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--expect', type=float, default=198.74)
    a = ap.parse_args()
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,r_frame_rate',
                                    '-of', 'json', a.video], capture_output=True, text=True).stdout)
    dur = float(pr['format']['duration'])
    kinds = [s['codec_type'] for s in pr['streams']]
    fr = [s['r_frame_rate'] for s in pr['streams'] if s['codec_type'] == 'video'][0]
    num, den = (int(x) for x in fr.split('/'))
    fps = num / den
    print(f'duration {dur:.2f}s (expected {a.expect:.2f}) streams {kinds} fps {fps:g}')
    w, h = 320, 180
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', a.video, '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE)
    lum_cells, flat = [], []
    i = 0
    while True:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        f = np.frombuffer(buf, np.uint8).reshape(h, w, 3).astype(np.float32) / 255.0
        lin = srgb_to_lin(f)
        L = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
        cells = L.reshape(4, h // 4, 4, w // 4).mean((1, 3)).ravel()
        lum_cells.append(cells)
        y = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
        if y.std() < 0.015:
            flat.append((i / fps, float(y.mean())))
        i += 1
    p.wait()
    C = np.stack(lum_cells)
    d = np.diff(C, axis=0)
    darker = np.minimum(C[:-1], C[1:])
    up = ((d >= 0.10) & (darker < 0.80)).sum(1) >= 4
    dn = ((d <= -0.10) & (darker < 0.80)).sum(1) >= 4
    ev = np.zeros(len(d), np.int8)
    ev[up] = 1
    ev[dn] = -1
    idx = np.nonzero(ev)[0]
    flashes = []                                      # time of each completed flash (an opposing pair)
    last = None
    for k in idx:
        if last is not None and ev[k] != ev[last]:
            flashes.append((k + 1) / fps)
            last = None
        else:
            last = k
    fails = []
    fl = np.array(flashes)
    for t0 in np.arange(0, dur, 0.25):
        n = int(((fl >= t0) & (fl < t0 + 1.0)).sum()) if len(fl) else 0
        if n > 3:
            fails.append((round(float(t0), 2), n))
    print(f'frames {i}  flash events {int(np.abs(ev).sum())}  flashes {len(flashes)}')
    if fails:
        merged = []
        for t0, n in fails:
            if merged and t0 <= merged[-1][1] + 0.25:
                merged[-1] = (merged[-1][0], t0 + 1.0, max(merged[-1][2], n))
            else:
                merged.append((t0, t0 + 1.0, n))
        for s, e, n in merged:
            print(f'FLASH FAIL {s:.2f}-{e:.2f}s  up to {n} flashes/s')
    else:
        print('flash check: pass')
    if flat:
        runs = []
        for t, m in flat:
            if runs and t - runs[-1][1] <= 1.5 / fps:
                runs[-1][1] = t
            else:
                runs.append([t, t, m])
        for s, e, m in runs:
            print(f'flat frames {s:.2f}-{e:.2f}s (mean luma {m:.2f})')
    ok = abs(dur - a.expect) < 0.1 and 'audio' in kinds and not fails
    print('QA', 'PASS' if ok else 'CHECK')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

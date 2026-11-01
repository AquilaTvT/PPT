"""Review sheets of every cut in a rendered film: for each shot boundary c, frames at c-2, c-1, c, c+1 (24 fps).

  python3 tools/cut_sheet.py out/mva.mp4 --mv a out_dir [--per 8] [--mid]

Frames are pulled from the rendered file (no re-render). --mid adds one row per shot at its midpoint instead.
Writes out_dir/cuts_<n>.jpg pages, 4 frames per row (320 px wide), labelled with the incoming shot id and time.
"""
import argparse
import json
import os
import subprocess

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def grab(video, t, w=320, h=180):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0.0, t):.4f}', '-i', video, '-frames:v', '1',
                        '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], capture_output=True)
    if len(r.stdout) < w * h * 3:
        return np.zeros((h, w, 3), np.uint8)
    return np.frombuffer(r.stdout[:w * h * 3], np.uint8).reshape(h, w, 3).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('out')
    ap.add_argument('--mv', default='a', choices=['a', 'b'])
    ap.add_argument('--per', type=int, default=8)
    ap.add_argument('--mid', action='store_true')
    a = ap.parse_args()
    d = json.load(open(os.path.join(ROOT, 'design', f'mv_{a.mv}', 'shots.json')))
    shots = d['shots'] if isinstance(d, dict) else d
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for i, s in enumerate(shots):
        if a.mid:
            ts = [s['start'] + (s['end'] - s['start']) * f for f in (0.2, 0.4, 0.6, 0.8)]
        else:
            if i == 0:
                continue
            c = s['start']
            ts = [c - 2 / 24, c - 1 / 24, c + 0.5 / 24, c + 1.5 / 24]
        tiles = [grab(a.video, t) for t in ts]
        row = np.concatenate(tiles, 1)
        cv2.line(row, (640, 0), (640, 179), (255, 0, 255), 1)
        label = f"{shots[i - 1]['id'][2:] if not a.mid else ''} | {s['id'][2:]}  {s['start']:.2f}"
        cv2.putText(row, label, (5, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(row, label, (5, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        rows.append(row)
    for k in range(0, len(rows), a.per):
        cv2.imwrite(os.path.join(a.out, f"{'mid' if a.mid else 'cuts'}_{k // a.per}.jpg"), np.concatenate(rows[k:k + a.per], 0),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(len(rows), 'rows')


if __name__ == '__main__':
    main()

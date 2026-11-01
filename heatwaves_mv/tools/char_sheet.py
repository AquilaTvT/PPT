"""Review sheet for the character shots of MV-B: three frames per shot (in / mid / out) with the real cut-outs.

  python3 tools/char_sheet.py out_dir [--ids B-hook-01,B-verse-03] [--per 8]

Writes out_dir/chars_<n>.jpg pages, 3 columns (in, mid, out) per row, one row per shot, labelled with the shot id,
the character source in use (video / still / stand-in / none) and the time of each frame.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--ids', default='')
    ap.add_argument('--per', type=int, default=8)
    a = ap.parse_args()
    from mvb import timeline as tl, recipes, chars  # noqa: F401  (recipes registers the shots)
    d = json.load(open(os.path.join(ROOT, 'design/mv_b/shots.json')))
    shots = d['shots'] if isinstance(d, dict) else d
    ids = [s['id'] for s in shots if (s.get('character') or {}).get('mode') in ('clip', 'still')]
    if a.ids:
        ids = [i for i in a.ids.split(',') if i]
    os.makedirs(a.out, exist_ok=True)
    rows, page = [], 0
    W, H = 512, 288

    def flush():
        nonlocal rows, page
        if rows:
            cv2.imwrite(os.path.join(a.out, f'chars_{page}.jpg'), cv2.cvtColor(np.concatenate(rows, 0), cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 86])
            print('page', page, len(rows), 'shots', flush=True)
            page += 1
            rows = []

    for sid in ids:
        s = tl.BY_ID[sid]
        kind_, src = chars.media_path(sid)
        kind = f'{kind_} {os.path.basename(src)}' if src else ('stand-in' if os.environ.get('HW_CHAR_STANDIN') else 'none')
        tiles = []
        for f in (0.12, 0.5, 0.88):
            t = s['start'] + (s['end'] - s['start']) * f
            try:
                im = tl.render(t, int(round(t * 24)))
            except Exception as e:                       # keep going: a broken shot shows as a red tile
                print('FAIL', sid, repr(e)[:160], flush=True)
                im = np.zeros((1080, 1920, 3), np.float32)
                im[:] = (0.6, 0.1, 0.1)
            im = (np.clip(cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA), 0, 1) * 255).astype(np.uint8).copy()
            cv2.putText(im, f'{t:.2f}', (6, H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1, cv2.LINE_AA)
            tiles.append(im)
        row = np.concatenate(tiles, 1)
        label = f'{sid[2:]}  [{kind}]'
        cv2.putText(row, label, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(row, label, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
        rows.append(row)
        if len(rows) >= a.per:
            flush()
    flush()


if __name__ == '__main__':
    main()

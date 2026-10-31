"""Render the final 1080p30 chunks in parallel (resumable).

  python tools/render_chunks.py --workers 3 --skip 64:68,96:100      # leave some ranges for later
  python tools/render_chunks.py --workers 4                           # fill everything that's missing
"""
import argparse
import multiprocessing as mp
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mv import render  # noqa: E402

FPS, RES, STEP, CRF = 30, 1920, 120, 12
TOTAL = int(round(198.74 * FPS))


def jobs(skip, only=()):
    out = []
    for a in range(0, TOTAL, STEP):
        b = min(TOTAL, a + STEP)
        if any(not (b / FPS <= s0 or a / FPS >= s1) for s0, s1 in skip):
            continue
        if only and not any(not (b / FPS <= s0 or a / FPS >= s1) for s0, s1 in only):
            continue
        path = os.path.join(render.OUT_DIR, f'full_{RES}_{FPS}_{a:06d}_{b:06d}.mp4')
        out.append((a, b, FPS, RES, path, CRF))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--skip', default='')
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    skip = [tuple(map(float, r.split(':'))) for r in a.skip.split(',') if r]
    only = [tuple(map(float, r.split(':'))) for r in a.only.split(',') if r]
    js = [j for j in jobs(skip, only) if not os.path.exists(j[4] + '.done')]
    print(f'{len(js)} chunks to render', flush=True)
    os.makedirs(render.OUT_DIR, exist_ok=True)
    with mp.get_context('fork').Pool(a.workers) as pool:
        for p in pool.imap_unordered(render._worker, js):
            print('done', os.path.basename(p), flush=True)

"""Render (and cache) three.js background plates for MV-B shots.

  pl = plate('B-hook-03', 's2_coast', {'world': 'noon', 'path': [...]}, t0=0.0, t1=2.96)
  img = pl.frame(local_t)          # float32 RGB 1920x1080
  pts = pl.anchor(local_t, 'tv')   # projected anchor points [(x, y, z), ...]
Plates are keyed by a hash of (scene, params, t0, t1, fps); re-rendered only when something changes.
"""
import hashlib
import json
import os
import subprocess

import cv2
import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), '..')
THREE = os.path.join(ROOT, 'three')
CACHE = os.environ.get('HW_PLATES', os.path.join(ROOT, 'work', 'B', 'plates'))
FPS = 24


class Plate:
    def __init__(self, d, n, t0):
        self.d, self.n, self.t0 = d, n, t0
        ap = os.path.join(d, 'anchors.json')
        self.anchors = json.load(open(ap)) if os.path.exists(ap) else None
        self._cache = {}

    def index(self, local_t):
        return int(min(self.n - 1, max(0, round(local_t * FPS))))

    def frame(self, local_t):
        i = self.index(local_t)
        if i not in self._cache:
            if len(self._cache) > 6:
                self._cache.clear()
            im = cv2.imread(os.path.join(self.d, f'f_{i:05d}.png'))
            self._cache[i] = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        return self._cache[i]

    def anchor(self, local_t, name):
        if not self.anchors:
            return None
        a = self.anchors[self.index(local_t)]
        return a.get(name) if a else None


def plate(shot_id, scene, params, t0, t1, fps=FPS, force=False):
    key = json.dumps([scene, params, round(t0, 4), round(t1, 4), fps], sort_keys=True)
    h = hashlib.md5(key.encode()).hexdigest()[:10]
    d = os.path.join(CACHE, f'{shot_id}_{h}')
    n = int(round((t1 - t0) * fps))
    done = os.path.join(d, 'DONE')
    if force or not os.path.exists(done):
        os.makedirs(d, exist_ok=True)
        cmd = ['node', os.path.join(THREE, 'engine', 'run.cjs'), '--scene', scene, '--t0', str(t0), '--t1', str(t1),
               '--fps', str(fps), '--out', d, '--params', json.dumps(params)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if r.returncode != 0:
            raise RuntimeError(f'plate {shot_id} failed: {r.stderr[-2000:]} {r.stdout[-500:]}')
        open(done, 'w').write(key)
    return Plate(d, n, t0)

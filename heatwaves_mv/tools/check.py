"""Render frames across the timeline at a tiny size and report any exceptions."""
import sys, traceback, time
sys.path.insert(0, '.')
import numpy as np
from mv import core
from mv.timeline import build

step = float(sys.argv[1]) if len(sys.argv) > 1 else 0.2
t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 198.7
core.set_resolution(320, 180)
ed = build()
errs = {}
t = t0
n = 0
start = time.time()
while t < t1:
    try:
        img = ed.render(t, int(t * 30))
        assert img.shape == (180, 320, 3), img.shape
        assert np.isfinite(img).all(), 'nan'
    except Exception as e:
        name = ed.shots[ed.shot_at(t)].name
        key = (name, type(e).__name__, str(e)[:120])
        if key not in errs:
            errs[key] = t
            print(f'ERR t={t:.2f} {name}: {type(e).__name__}: {e}')
            traceback.print_exc(limit=3)
    t += step
    n += 1
print(f'checked {n} frames in {time.time()-start:.0f}s, {len(errs)} distinct errors')

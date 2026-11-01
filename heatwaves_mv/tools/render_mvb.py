"""Render a time range of MV-B (or MV-A with --mv a) to an mp4 (parallel worker processes, then concat + audio).

  python3 tools/render_mvb.py --t0 0 --t1 28.83 --out /path/preview.mp4 [--workers 3] [--audio] [--mv a|b]
"""
import argparse
import multiprocessing as mp
import os
import subprocess
import time
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
FPS = 24
AUDIO = os.environ.get('HW_AUDIO', '/tmp/claude-0/song/hw.wav')
MV = os.environ.get('HW_MV', 'b')


def modules():
    if MV == 'a':
        from mva import timeline as tl, recipes  # noqa: F401
    elif MV == 'b2':
        from mvb import timeline as tl, recipes, v2  # noqa: F401
        v2.install()
    else:
        from mvb import timeline as tl, recipes  # noqa: F401
    return tl


RESUME = False


def frames_in(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                        'stream=nb_read_packets', '-of', 'csv=p=0', path], capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


def work(args):
    f0, f1, path = args
    if RESUME and os.path.exists(path) and frames_in(path) == f1 - f0:
        return path                       # --resume: this part is already complete (delete a part to re-render it)
    import numpy as np
    tl = modules()
    tmp = path[:-4] + '.tmp.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '15', '-preset', 'medium',
                          '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        img = tl.render(f / FPS, f)
        p.stdin.write((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f'ffmpeg failed on {path}')
    os.replace(tmp, path)
    return path


def warm(args):
    """warm one shot's disk caches (plates, palettes, skin verdicts, tracks): its first frame, and 70% in for MV-B v2
    (devices that start later in a shot)"""
    sid, u0, u1 = args
    tl = modules()
    s = tl.BY_ID[sid]
    tl.render(max(u0, s['start']) + 0.01, int(round((max(u0, s['start']) + 0.01) * FPS)))
    if MV == 'b2':
        tm = s['start'] + 0.7 * (s['end'] - s['start'])
        if u0 <= tm < u1:
            tl.render(tm, int(round(tm * FPS)))
    return sid


def drop_caches():
    """free the warm-up's per-shot objects (plates, cut-out layers, decoders, the ONNX matte) before fork()"""
    import gc
    for name in ('mvb.recipes', 'mva.recipes'):
        m = sys.modules.get(name)
        if m is not None and hasattr(m, '_cache'):
            m._cache.clear()
    for name, attrs in (('mvb.plates', ('_FRAMES',)), ('mvb.chars', ('_CUTS',)), ('mva.timeline', ('_clip_cache', '_still_cache'))):
        m = sys.modules.get(name)
        for at in attrs:
            if m is not None and hasattr(m, at):
                getattr(m, at).clear()
    m = sys.modules.get('mvb.chars')
    if m is not None and getattr(m, '_matter', None) is not None:
        m._matter = None
    m = sys.modules.get('mvb.v2')                 # MV-B v2: footage decoders are reopened per worker
    if m is not None:
        m._CLIPS.clear()
    m = sys.modules.get('mvb.people')             # ONNX sessions do not survive fork(): one per worker
    if m is not None:
        m._SESS = {}
    gc.collect()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--t0', type=float, default=0.0)
    ap.add_argument('--t1', type=float, default=198.74)
    ap.add_argument('--out', required=True)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--audio', action='store_true')
    ap.add_argument('--mv', default=MV, choices=['a', 'b', 'b2'])
    ap.add_argument('--jobs', type=int, default=0, help='parts to split the range into (default 2 per worker)')
    ap.add_argument('--resume', action='store_true', help='keep complete parts from an earlier run of the same range')
    a = ap.parse_args()
    globals()['RESUME'] = a.resume
    globals()['MV'] = a.mv
    os.environ['HW_MV'] = a.mv
    f0, f1 = int(round(a.t0 * FPS)), int(round(a.t1 * FPS))
    n = a.jobs or a.workers * 2
    step = max(1, (f1 - f0 + n - 1) // n)
    a.out = os.path.abspath(a.out)
    tmpd = a.out + '.parts'
    os.makedirs(tmpd, exist_ok=True)
    jobs = [(s, min(f1, s + step), os.path.join(tmpd, f'p{i:03d}.mp4')) for i, s in enumerate(range(f0, f1, step))]
    todo = [j for j in jobs if not (a.resume and os.path.exists(j[2]) and frames_in(j[2]) == j[1] - j[0])]
    print(f'parts: {len(jobs)}, to render: {len(todo)}', flush=True)
    spans = [(j0 / FPS, j1 / FPS) for j0, j1, _ in todo]
    # warm the per-shot disk caches once -- only for the shots the parts still to render touch. MV-B v1 renders its
    # plates through node (no parallel duplicates): one process; MV-B v2 (palettes, skin verdicts, tracks): one shot
    # per worker, in parallel
    tl = modules()
    shots = [s for s in tl.SHOTS if any(s['end'] > u0 and s['start'] < u1 for u0, u1 in spans)]
    os.environ.setdefault('HW_SEG_THREADS', str(max(1, (os.cpu_count() or 4) // a.workers)))
    if a.mv == 'b2' and shots:
        drop_caches()
        t_w = time.time()
        with mp.get_context('fork').Pool(a.workers, maxtasksperchild=4) as pool:
            pool.map(warm, [(s['id'], a.t0, a.t1) for s in shots], chunksize=1)
        print(f'warm-up {len(shots)} shots {time.time() - t_w:.0f}s', flush=True)
    else:
        for s in shots:
            tl.render(max(a.t0, s['start']) + 0.01, 0)
    drop_caches()            # the workers rebuild what they touch from disk; a fat parent is copied into every worker
    with mp.get_context('fork').Pool(a.workers, maxtasksperchild=1) as pool:
        parts = pool.map(work, jobs)
    lst = os.path.join(tmpd, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst]
    if a.audio:
        cmd += ['-ss', str(a.t0), '-t', str(a.t1 - a.t0), '-i', AUDIO, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '256k']
    cmd += ['-c:v', 'copy', '-movflags', '+faststart', a.out]
    subprocess.run(cmd, check=True)
    print('wrote', a.out)


if __name__ == '__main__':
    main()

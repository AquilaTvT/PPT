"""Render the MV.

  python -m mv.render sheet  --times 17,20.5,30 --res 960         contact sheet
  python -m mv.render preview --t0 16 --t1 30 --res 960 --fps 15   quick mp4
  python -m mv.render full --workers 4                              final 1080p30
"""
import argparse
import os
import subprocess
import sys
import time

import numpy as np

AUDIO = os.environ.get('HW_AUDIO', '/tmp/claude-0/song/hw.wav')
OUT_DIR = os.environ.get('HW_OUT', '/tmp/claude-0/out')


def _setup(res):
    import cv2
    cv2.setNumThreads(1)
    from . import core
    w = int(res)
    core.set_resolution(w, w * 9 // 16)


def _edit():
    from .timeline import build
    return build()


def to_u8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def sheet(times, res, out, cols=3):
    from PIL import Image, ImageDraw
    _setup(res)
    ed = _edit()
    ims = []
    for t in times:
        t0 = time.time()
        img = ed.render(t, int(t * 30))
        ims.append((t, Image.fromarray(to_u8(img)), time.time() - t0))
    w, h = ims[0][1].size
    rows = (len(ims) + cols - 1) // cols
    sh = Image.new('RGB', (cols * w, rows * (h + 18)), (16, 16, 16))
    d = ImageDraw.Draw(sh)
    for k, (t, im, dt) in enumerate(ims):
        c, r = k % cols, k // cols
        sh.paste(im, (c * w, r * (h + 18) + 18))
        d.text((c * w + 4, r * (h + 18) + 3), f't={t:.2f}s  ({dt:.1f}s)', fill=(255, 255, 0))
    sh.save(out, quality=90)
    print('wrote', out)


def encode_range(f0, f1, fps, res, path, crf=14, preset='medium'):
    _setup(res)
    ed = _edit()
    from . import core
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{core.W}x{core.H}',
           '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', preset, '-crf', str(crf),
           '-pix_fmt', 'yuv420p', '-threads', '1', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t_start = time.time()
    for fi in range(f0, f1):
        t = fi / fps
        img = ed.render(t, fi)
        p.stdin.write(to_u8(img).tobytes())
        if (fi - f0) % 30 == 0:
            el = time.time() - t_start
            print(f'[{os.getpid()}] frame {fi} ({fi - f0}/{f1 - f0}) {el:.0f}s', flush=True)
    p.stdin.close()
    p.wait()


def _worker(args):
    f0, f1, fps, res, path, crf = args
    if os.path.exists(path) and os.path.getsize(path) > 0 and os.path.exists(path + '.done'):
        return path
    encode_range(f0, f1, fps, res, path, crf)
    open(path + '.done', 'w').close()
    return path


def render_range(t0, t1, fps, res, out, workers=1, chunk_s=4.0, crf=14, tag='seg', audio=True):
    import multiprocessing as mp
    os.makedirs(OUT_DIR, exist_ok=True)
    f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
    step = max(1, int(chunk_s * fps))
    jobs = []
    for a in range(f0, f1, step):
        b = min(f1, a + step)
        jobs.append((a, b, fps, res, os.path.join(OUT_DIR, f'{tag}_{res}_{fps}_{a:06d}_{b:06d}.mp4'), crf))
    if workers > 1:
        with mp.get_context('fork').Pool(workers) as pool:
            paths = pool.map(_worker, jobs, chunksize=1)
    else:
        paths = [_worker(j) for j in jobs]
    lst = os.path.join(OUT_DIR, f'{tag}_list.txt')
    with open(lst, 'w') as fl:
        for pth in paths:
            fl.write(f"file '{pth}'\n")
    silent = out + '.silent.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', silent], check=True)
    if audio:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', silent, '-ss', str(t0), '-t', str(t1 - t0), '-i', AUDIO,
                        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest', out],
                       check=True)
        os.remove(silent)
    else:
        os.replace(silent, out)
    print('wrote', out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['sheet', 'preview', 'full', 'range'])
    ap.add_argument('--times', default='')
    ap.add_argument('--t0', type=float, default=0)
    ap.add_argument('--t1', type=float, default=198.74)
    ap.add_argument('--res', type=int, default=960)
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--cols', type=int, default=3)
    ap.add_argument('--crf', type=int, default=14)
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    if a.mode == 'sheet':
        times = [float(x) for x in a.times.split(',') if x]
        sheet(times, a.res, a.out or os.path.join(OUT_DIR, 'sheet.jpg'), a.cols)
    elif a.mode == 'preview':
        render_range(a.t0, a.t1, a.fps, a.res, a.out or os.path.join(OUT_DIR, f'preview_{a.t0:.0f}_{a.t1:.0f}.mp4'),
                     workers=a.workers, chunk_s=2.0, crf=20, tag=f'prev{a.t0:.0f}')
    elif a.mode in ('full', 'range'):
        render_range(a.t0, a.t1, a.fps, 1920, a.out or os.path.join(OUT_DIR, 'heatwaves_mv.mp4'), workers=a.workers,
                     chunk_s=4.0, crf=a.crf, tag='full')


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    main()

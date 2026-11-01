"""Upscale generated clips on the Mac GPU (MPS): Real-ESRGAN animevideov3 x4, then area-downscale to
1920 px wide. Frame by frame through ffmpeg pipes, so memory stays small (~0.5 GB).

  .hw/venv/bin/python gpu/upscale_clips.py work/A            # per shot: final.mp4 (RIFE) or v_*.mp4 -> *_up.mp4
  .hw/venv/bin/python gpu/upscale_clips.py work/A/A-hook-01/v_0.mp4

On the cloud CPU this model needs ~6.4 s per 832x480 frame; on the M4 GPU it is a few frames per
second, so this is one of the few post steps that runs on the Mac.
"""
import glob
import json
import os
import subprocess
import sys
import time

import numpy as np
import torch

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WEIGHTS = os.path.join(ROOT, 'gpu', 'weights', 'realesr-animevideov3.safetensors')
OUT_W = 1920


def ffmpeg_bin():
    for c in ('ffmpeg', os.path.join(ROOT, '.hw', 'bin', 'ffmpeg')):
        try:
            subprocess.run([c, '-version'], capture_output=True, check=True)
            return c
        except Exception:
            pass
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(ff, path):
    out = subprocess.run([ff, '-i', path], capture_output=True, text=True).stderr
    import re
    m = re.search(r', (\d+)x(\d+)[, ]', out)
    f = re.search(r', ([\d.]+) fps', out)
    return int(m.group(1)), int(m.group(2)), float(f.group(1)) if f else 16.0


def load_model(dev):
    import spandrel
    m = spandrel.ModelLoader().load_from_file(WEIGHTS)
    return m.model.eval().to(dev), m.scale


def upscale(path, net, scale, dev, ff):
    w, h, fps = probe(ff, path)
    keep = max(1, int(round(fps / 24.0))) if fps > 30 else 1      # 48 fps RIFE output -> every 2nd frame = 24 fps
    fps_out = fps / keep
    ow = OUT_W
    oh = int(round(h * OUT_W / w / 2)) * 2
    dst = path[:-4] + '_up.mp4'
    tmp = dst + '.tmp.mp4'
    rd = subprocess.Popen([ff, '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                          stdout=subprocess.PIPE)
    wr = subprocess.Popen([ff, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{ow}x{oh}',
                           '-r', f'{fps_out:g}', '-i', '-', '-c:v', 'libx264', '-crf', '14', '-preset', 'medium',
                           '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    import cv2
    n = 0
    k = -1
    t0 = time.time()
    with torch.inference_mode():
        while True:
            buf = rd.stdout.read(w * h * 3)
            if len(buf) < w * h * 3:
                break
            k += 1
            if k % keep:
                continue
            x = torch.from_numpy(np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy()).to(dev)
            x = x.permute(2, 0, 1)[None].float() / 255.0
            y = net(x).clamp_(0, 1)[0].permute(1, 2, 0)
            y = (y * 255.0).round().to(torch.uint8).cpu().numpy()
            y = cv2.resize(y, (ow, oh), interpolation=cv2.INTER_AREA)
            wr.stdin.write(y.tobytes())
            n += 1
    rd.wait()
    wr.stdin.close()
    wr.wait()
    os.replace(tmp, dst)
    return dst, n, time.time() - t0


def main():
    targets = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            for d in sorted({os.path.dirname(p) for p in glob.glob(os.path.join(a, '**', 'v_*.mp4'), recursive=True)}):
                fin = os.path.join(d, 'final.mp4')            # the RIFE'd clip when the finish stage has run
                srcs = [fin] if os.path.exists(fin) else sorted(p for p in glob.glob(os.path.join(d, 'v_*.mp4'))
                                                                if not p.endswith(('_up.mp4', '_24.mp4')))
                targets += [p for p in srcs if not os.path.exists(p[:-4] + '_up.mp4')]
        else:
            targets.append(a)
    dev = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
    net, scale = load_model(dev)
    ff = ffmpeg_bin()
    for p in targets:
        dst, n, secs = upscale(p, net, scale, dev, ff)
        print(json.dumps({'clip': p, 'out': dst, 'frames': n, 'secs': round(secs, 1)}), flush=True)


if __name__ == '__main__':
    main()

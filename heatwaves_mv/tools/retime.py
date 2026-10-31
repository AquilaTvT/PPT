"""Retime a clip to 24 fps with RIFE v4.26 (ComfyUI's IFNet) on the cloud CPU.

  python3 tools/retime.py in_16fps.mp4 out_24fps.mp4 [--fps 24] [--speed 1.0]

Output frame k shows source time k/fps*speed; source frames that land exactly are copied, the others
are synthesised by RIFE at the fractional timestep (16 -> 24 fps: t = 2/3, 1/3, 0 repeating).
"""
import argparse
import math
import os
import re
import subprocess
import sys
import time

import numpy as np
import torch

COMFY = os.environ.get('COMFY_DIR', '/tmp/claude-0/ComfyUI')
RIFE = os.environ.get('RIFE_WEIGHTS', '/tmp/claude-0/models/interp/rife_v4.26.safetensors')


def load_rife():
    sys.path.insert(0, COMFY)
    import comfy.cli_args
    comfy.cli_args.args.cpu = True
    import comfy.utils
    import safetensors.torch as st
    from comfy_extras.frame_interpolation_models.ifnet import IFNet, detect_rife_config
    sd = st.load_file(RIFE)
    sd = comfy.utils.state_dict_prefix_replace(sd, {'module.': '', 'flownet.': ''})
    km = {}
    for k in sd:
        for i in range(5):
            if k.startswith(f'block{i}.'):
                km[k] = f'blocks.{i}.{k[len(f"block{i}."):]}'
    sd = {km.get(k, k): v for k, v in sd.items() if not k.startswith(('teacher.', 'caltime.'))}
    head_ch, channels = detect_rife_config(sd)
    net = IFNet(head_ch=head_ch, channels=channels)
    net.load_state_dict(sd)
    return net.eval().float()


def probe(path):
    out = subprocess.run(['ffmpeg', '-i', path], capture_output=True, text=True).stderr
    m = re.search(r', (\d+)x(\d+)[, ]', out)
    f = re.search(r', ([\d.]+) fps', out)
    return int(m.group(1)), int(m.group(2)), float(f.group(1))


def read_all(path, w, h):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def to_t(fr, ph, pw):
    x = torch.from_numpy(fr.copy()).permute(2, 0, 1)[None].float() / 255.0
    return torch.nn.functional.pad(x, (0, pw, 0, ph), mode='replicate')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--fps', type=float, default=24.0)
    ap.add_argument('--speed', type=float, default=1.0, help='playback speed relative to the source fps')
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--crf', type=int, default=14)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    w, h, sfps = probe(a.src)
    frames = read_all(a.src, w, h)
    n_src = len(frames)
    dur = (n_src - 1) / sfps / a.speed
    n_out = int(math.floor(dur * a.fps + 1e-6)) + 1
    ph, pw = (-h) % 64, (-w) % 64
    net = load_rife()
    wr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
                           '-r', f'{a.fps:g}', '-i', '-', '-c:v', 'libx264', '-crf', str(a.crf), '-preset', 'medium',
                           '-pix_fmt', 'yuv420p', a.dst], stdin=subprocess.PIPE)
    t0 = time.time()
    cache = {}
    with torch.inference_mode():
        for k in range(n_out):
            p = k / a.fps * sfps * a.speed
            i = min(int(math.floor(p + 1e-6)), n_src - 1)
            t = p - i
            if t < 1e-3 or i >= n_src - 1:
                out = frames[i]
            else:
                if i not in cache:
                    cache.clear()
                    cache[i] = (to_t(frames[i], ph, pw), to_t(frames[i + 1], ph, pw))
                f0, f1 = cache[i]
                y = net(f0, f1, timestep=float(t))[:, :, :h, :w].clamp(0, 1)
                out = (y[0].permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
            wr.stdin.write(np.ascontiguousarray(out).tobytes())
    wr.stdin.close()
    wr.wait()
    print(f'{a.src}: {n_src} frames @{sfps:g} -> {n_out} @{a.fps:g} in {time.time() - t0:.1f}s', flush=True)


if __name__ == '__main__':
    main()

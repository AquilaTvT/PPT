"""Benchmark the generation stack on this machine (decides resolution / steps / shot budget).

  python gpu/bench.py --platform mac                      # Apple Silicon, 16 GB: 5B turbo path
  python gpu/bench.py --platform cuda --model 14b        # NVIDIA

5B path: Anima keyframes (turbo 10 steps / aesthetic 24 steps) at 1280x704, then the umt5 text
encoder alone (conditioning saved to disk and the encoder freed), then Wan 2.2 TI2V 5B Turbo
4-step clips (121 frames) at 832x480 (shift 5 and 8) and 1280x704; wall time + peak memory of
each step go to work/bench.json.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gpu import graphs as gr  # noqa: E402
from gpu.comfy import Comfy  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')


class MemWatch(threading.Thread):
    """samples used memory (macOS: vm_stat / NVIDIA: nvidia-smi) every second"""

    def __init__(self, platform):
        super().__init__(daemon=True)
        self.platform, self.peak, self.stop = platform, 0.0, False

    def used_gb(self):
        try:
            if self.platform == 'mac':
                out = subprocess.run(['vm_stat'], capture_output=True, text=True).stdout
                page = 16384
                vals = {}
                for line in out.splitlines()[1:]:
                    if ':' in line:
                        k, v = line.split(':', 1)
                        vals[k.strip()] = int(v.strip().rstrip('.') or 0)
                used = (vals.get('Pages active', 0) + vals.get('Pages wired down', 0) +
                        vals.get('Pages occupied by compressor', 0)) * page
                return used / 2 ** 30
            out = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                                 capture_output=True, text=True).stdout
            return float(out.split()[0]) / 1024
        except Exception:
            return 0.0

    def run(self):
        while not self.stop:
            self.peak = max(self.peak, self.used_gb())
            time.sleep(1.0)


def timed(c, graph, platform, label, results):
    w = MemWatch(platform)
    w.start()
    t0 = time.time()
    try:
        outs = c.outputs(c.run(graph))
        ok = True
    except Exception as e:  # keep benchmarking the other configs
        outs, ok = [], False
        print(label, 'FAILED', str(e)[:400], flush=True)
    w.stop = True
    w.join(2)
    r = {'label': label, 'ok': ok, 'secs': round(time.time() - t0, 1), 'peak_mem_gb': round(w.peak, 1)}
    results.append(r)
    print(json.dumps(r), flush=True)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--platform', choices=['mac', 'cuda'], required=True)
    ap.add_argument('--quant', default='Q5_K_M')
    ap.add_argument('--te', default='umt5-xxl-encoder-Q5_K_M.gguf')
    ap.add_argument('--url', default='http://127.0.0.1:8188')
    ap.add_argument('--root', default='')
    ap.add_argument('--with5b', action='store_true')
    ap.add_argument('--model', choices=['14b', '5b'], default='5b')
    ap.add_argument('--unet', default='Wan2.2-TI2V-5B-Q6_K.gguf')
    a = ap.parse_args()
    root = a.root or os.path.join(ROOT, '.hw', 'ComfyUI')
    c = Comfy(a.url, root if os.path.isdir(root) else None)
    res = []
    prompt = ('masterpiece, best quality, 1girl, solo, short black bob hair, straw hat with red ribbon, white sundress, '
              'standing on a country road in summer, cumulonimbus, blue sky, wind, looking back over shoulder, '
              'anime screencap, cinematic lighting')
    kw, kh = (1280, 704) if a.model == '5b' else (1536, 864)
    outs = timed(c, gr.t2i_anima(prompt, w=kw, h=kh, seed=7, prefix='bench_kf', model='anima-turbo-v1.1.safetensors',
                                 steps=10, cfg=1.0, sampler='euler'), a.platform, f'anima-turbo {kw}x{kh} 10 steps', res)
    c.free()
    timed(c, gr.t2i_anima(prompt, w=kw, h=kh, seed=8, prefix='bench_kf_aes', steps=24), a.platform,
          f'anima-aesthetic {kw}x{kh} 24 steps cfg 4.5', res)
    c.free()
    if not outs:
        return
    kf = os.path.join(ROOT, 'work', 'bench_kf.png')
    os.makedirs(os.path.dirname(kf), exist_ok=True)
    c.fetch(outs[0], kf)
    up = c.upload(kf, 'bench_kf.png')
    vp = 'the girl turns her head toward the camera and smiles, her hair and dress move in the warm wind, ' \
         'clouds drift slowly, the camera slowly pushes in'
    if a.model == '5b':
        # stage 1: text encoder alone, saved to disk, then freed -> sampling never holds the 4 GB encoder
        timed(c, gr.encode_texts([('bench_pos', vp), ('bench_neg', gr.NEG_WAN)], te=a.te), a.platform,
              'umt5 text encode (2 prompts)', res)
        cond = c.stash_conditioning(['bench_pos', 'bench_neg'])
        c.free()
        for (w, h, shift) in ((832, 480, 5.0), (832, 480, 8.0), (1280, 704, 8.0)):
            g = gr.ti2v_wan22_5b(up, None, w=w, h=h, frames=121, seed=3, steps=4, cfg=1.0, shift=shift,
                                 sampler='euler', unet_name=gr.TURBO_5B, pos_cond=cond['bench_pos'],
                                 neg_cond=cond['bench_neg'], prefix=f'video/bench_turbo_{w}x{h}_s{shift:g}')
            timed(c, g, a.platform, f'wan2.2 5B turbo {w}x{h} 121f 4 steps shift {shift:g}', res)
            c.free()
        json.dump(res, open(os.path.join(ROOT, 'work', 'bench.json'), 'w'), indent=1)
        return
    else:
        for (w, h) in ((832, 480), (1280, 720)):
            if a.platform == 'mac':
                g = gr.i2v_wan22_gguf(up, vp, w=w, h=h, frames=81, seed=3, quant=a.quant, te=a.te, lightning=True,
                                      prefix='video/bench')
            else:
                g = gr.i2v_wan22(up, vp, w=w, h=h, frames=81, seed=3, lightning=True, prefix='video/bench')
            timed(c, g, a.platform, f'wan2.2 A14B {w}x{h} 81f 4-step', res)
    if a.with5b:
        timed(c, gr.ti2v_wan22_5b(up, vp, frames=121, seed=3, te=a.te, prefix='video/bench5b'), a.platform,
              'wan2.2 5B 1280x704 121f 20 steps', res)
    json.dump(res, open(os.path.join(ROOT, 'work', 'bench.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

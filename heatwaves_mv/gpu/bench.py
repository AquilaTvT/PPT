"""Benchmark the generation stack on this machine (decides resolution / steps / shot budget).

  python gpu/bench.py --platform mac --quant Q5_K_M      # Apple Silicon
  python gpu/bench.py --platform cuda                    # NVIDIA

Runs: one Anima keyframe (1536x864, 30 steps), then Wan 2.2 I2V clips from it at
832x480 and 1280x720 with the 4-step distill LoRAs (and optionally the 5B model), and
records wall time + peak memory for each into work/bench.json.
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
    ap.add_argument('--te', default='umt5-xxl-encoder-Q8_0.gguf')
    ap.add_argument('--url', default='http://127.0.0.1:8188')
    ap.add_argument('--root', default='')
    ap.add_argument('--with5b', action='store_true')
    ap.add_argument('--model', choices=['14b', '5b'], default='14b')
    ap.add_argument('--unet', default='Wan2.2-TI2V-5B-Q6_K.gguf')
    a = ap.parse_args()
    c = Comfy(a.url, a.root or None)
    res = []
    prompt = ('masterpiece, best quality, 1girl, solo, short black bob hair, straw hat with red ribbon, white sundress, '
              'standing on a country road in summer, cumulonimbus, blue sky, wind, looking back over shoulder, '
              'anime screencap, cinematic lighting')
    outs = timed(c, gr.t2i_anima(prompt, seed=7, prefix='bench_kf', model='anima-turbo-v1.1.safetensors', steps=10,
                                 cfg=1.0, sampler='euler'), a.platform, 'anima-turbo 1536x864 10 steps', res)
    timed(c, gr.t2i_anima(prompt, seed=8, prefix='bench_kf_aes'), a.platform, 'anima-aesthetic 1536x864 30 steps', res)
    if not outs:
        return
    kf = os.path.join(ROOT, 'work', 'bench_kf.png')
    os.makedirs(os.path.dirname(kf), exist_ok=True)
    c.fetch(outs[0], kf)
    up = c.upload(kf, 'bench_kf.png')
    c.free()
    vp = 'the girl turns her head toward the camera and smiles, her hair and dress move in the warm wind, ' \
         'clouds drift slowly, the camera slowly pushes in'
    if a.model == '5b':
        for (w, h, steps) in ((640, 352, 20), (832, 480, 20)):
            g = gr.ti2v_wan22_5b(up, vp, w=w, h=h, frames=121, seed=3, steps=steps, te=a.te, unet_name=a.unet,
                                 prefix='video/bench5b')
            timed(c, g, a.platform, f'wan2.2 5B {w}x{h} 121f {steps} steps', res)
            c.free()
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

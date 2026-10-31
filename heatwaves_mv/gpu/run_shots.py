"""Shot generation runner (runs on the GPU machine next to ComfyUI).

  python gpu/run_shots.py keyframes --shots design/mv_a_shots.json --cfg gpu/config.json [--ids A-hook-01,...] [--n 4]
  python gpu/run_shots.py pick      --shots ... --id A-hook-01 --kf kf_3.png      # choose a keyframe candidate
  python gpu/run_shots.py videos    --shots ... --cfg ... [--ids ...] [--n 1]
  python gpu/run_shots.py finish    --shots ... --cfg ...                         # interpolate (+ optional SR)
  python gpu/run_shots.py status    --shots ...

Everything lands in work/<mv>/<shot_id>/ and is tracked in work/<mv>/manifest.json, so any
step can be interrupted and resumed. Model families are batched (all keyframes, then all
videos) and VRAM is freed between families.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gpu import graphs as gr  # noqa: E402
from gpu.comfy import Comfy  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')


def load_cfg(path):
    cfg = {
        'comfy_url': 'http://127.0.0.1:8188', 'comfy_root': os.path.expanduser('~/ComfyUI'),
        'keyframe': {'model': 'anima-aesthetic-v1.1.safetensors', 'steps': 30, 'cfg': 4.5, 'sampler': 'er_sde',
                     'w': 1536, 'h': 864, 'loras': []},
        'tokens': {},          # e.g. {"<kimi>": "kimi_hw, 1girl, black hair, bob cut, ...", "<boku>": "..."}
        'video': {'engine': 'wan22', 'w': 1280, 'h': 720, 'lightning': False, 'steps': 20, 'cfg': 3.5, 'split': 10,
                  'shift': 5.0},
        'finish': {'interp_model': 'rife_v4.26.safetensors', 'multiplier': 2},
    }
    if path and os.path.exists(path):
        user = json.load(open(path))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def load_shots(path):
    d = json.load(open(path))
    if isinstance(d, dict) and 'sections' in d:
        shots = [s for sec in d['sections'] if sec for s in sec['shots']]
    elif isinstance(d, dict) and 'shots' in d:
        shots = d['shots']
    else:
        shots = d
    return shots


class Manifest:
    def __init__(self, mv):
        self.dir = os.path.join(ROOT, 'work', mv)
        os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, 'manifest.json')
        self.d = json.load(open(self.path)) if os.path.exists(self.path) else {}

    def shot(self, sid):
        return self.d.setdefault(sid, {'keyframes': [], 'pick': None, 'videos': [], 'video_pick': None, 'final': None})

    def save(self):
        tmp = self.path + '.tmp'
        json.dump(self.d, open(tmp, 'w'), ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def shot_dir(self, sid):
        p = os.path.join(self.dir, sid)
        os.makedirs(p, exist_ok=True)
        return p


def stable_seed(*parts):
    return int(hashlib.md5('|'.join(map(str, parts)).encode()).hexdigest()[:10], 16)


def expand_tokens(prompt, tokens):
    for k, v in tokens.items():
        prompt = prompt.replace(k, v)
    return re.sub(r'\s+', ' ', prompt).strip()


def mv_of(shots):
    return shots[0]['id'].split('-')[0] if shots else 'X'


def select(shots, ids):
    if not ids:
        return shots
    want = set(ids.split(','))
    return [s for s in shots if s['id'] in want]


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


# ---------------------------------------------------------------------------------------
def do_keyframes(c, cfg, shots, man, n):
    k = cfg['keyframe']
    for s in shots:
        if s.get('video_mode') == 'composite' and not s.get('keyframe_prompt'):
            continue
        st = man.shot(s['id'])
        have = len(st['keyframes'])
        prompts = [('kf', s['keyframe_prompt'])]
        if s.get('video_mode') == 'flf' and s.get('end_keyframe_prompt'):
            prompts.append(('end', s['end_keyframe_prompt']))
        for tag, raw in prompts:
            existing = [x for x in st['keyframes'] if x['tag'] == tag]
            for i in range(len(existing), n):
                seed = stable_seed(s['id'], tag, i)
                prompt = expand_tokens(raw, cfg['tokens'])
                g = gr.t2i_anima(prompt, w=k['w'], h=k['h'], seed=seed, model=k['model'], steps=k['steps'],
                                 cfg=k['cfg'], sampler=k['sampler'], prefix=f"{s['id']}_{tag}",
                                 loras=[tuple(x) for x in k.get('loras', [])])
                t0 = time.time()
                outs = c.outputs(c.run(g))
                dst = os.path.join(man.shot_dir(s['id']), f'{tag}_{i}.png')
                c.fetch(outs[0], dst)
                st['keyframes'].append({'tag': tag, 'path': dst, 'seed': seed, 'prompt': prompt,
                                        'secs': round(time.time() - t0, 1)})
                man.save()
                log(f"{s['id']} {tag}_{i} {time.time() - t0:.0f}s")
        if have == 0 and st['pick'] is None and st['keyframes']:
            st['pick'] = {'kf': st['keyframes'][0]['path']}
            ends = [x for x in st['keyframes'] if x['tag'] == 'end']
            if ends:
                st['pick']['end'] = ends[0]['path']
            man.save()


def do_videos(c, cfg, shots, man, n):
    v = cfg['video']
    prev_last = None
    for s in shots:
        st = man.shot(s['id'])
        mode = s.get('video_mode', 'i2v')
        if mode == 'composite':
            continue
        if mode == 'chain' and prev_last:
            start = prev_last
        elif st.get('pick') and st['pick'].get('kf'):
            start = st['pick']['kf']
        else:
            log(f"{s['id']} skipped: no keyframe picked")
            continue
        end = st['pick'].get('end') if (mode == 'flf' and st.get('pick')) else None
        frames = int(round(min(5.0, s.get('clip_seconds', 5)) * 16)) // 4 * 4 + 1
        for i in range(len(st['videos']), n):
            seed = stable_seed(s['id'], 'v', i)
            up = c.upload(start, f"{s['id']}_start.png")
            upe = c.upload(end, f"{s['id']}_end.png") if end else None
            if v['engine'] == 'hy15':
                g = gr.i2v_hy15(up, s['video_prompt'], w=v['w'], h=v['h'], frames=int(frames * 1.5) // 4 * 4 + 1,
                                seed=seed, prefix=f"video/{s['id']}")
            else:
                g = gr.i2v_wan22(up, s['video_prompt'], w=v['w'], h=v['h'], frames=frames, seed=seed, end_image=upe,
                                 lightning=v['lightning'], steps=v['steps'], cfg=v['cfg'], split=v['split'],
                                 shift=v['shift'], prefix=f"video/{s['id']}")
            t0 = time.time()
            outs = c.outputs(c.run(g))
            vids = [o for o in outs if o['filename'].endswith(('.mp4', '.webm', '.mkv'))]
            dst = os.path.join(man.shot_dir(s['id']), f'v_{i}.mp4')
            c.fetch(vids[0], dst)
            st['videos'].append({'path': dst, 'seed': seed, 'engine': v['engine'], 'secs': round(time.time() - t0, 1)})
            if st['video_pick'] is None:
                st['video_pick'] = dst
            man.save()
            log(f"{s['id']} video {i} {time.time() - t0:.0f}s")
        if st['video_pick']:
            prev_last = last_frame(st['video_pick'], os.path.join(man.shot_dir(s['id']), 'last.png'))


def last_frame(video, dst):
    import subprocess
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-sseof', '-0.1', '-i', video, '-frames:v', '1', dst], check=False)
    return dst if os.path.exists(dst) else None


def do_finish(c, cfg, shots, man):
    f = cfg['finish']
    for s in shots:
        st = man.shot(s['id'])
        if not st.get('video_pick') or st.get('final'):
            continue
        up = c.upload(st['video_pick'], f"{s['id']}_raw.mp4")
        g = gr.interpolate(up, multiplier=f['multiplier'], fps_out=16 * f['multiplier'], model=f['interp_model'],
                           prefix=f"video/{s['id']}_interp")
        t0 = time.time()
        outs = c.outputs(c.run(g))
        vids = [o for o in outs if o['filename'].endswith(('.mp4', '.webm', '.mkv'))]
        dst = os.path.join(man.shot_dir(s['id']), 'final.mp4')
        c.fetch(vids[0], dst)
        st['final'] = dst
        man.save()
        log(f"{s['id']} finished {time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['keyframes', 'videos', 'finish', 'pick', 'status'])
    ap.add_argument('--shots', required=True)
    ap.add_argument('--cfg', default='')
    ap.add_argument('--ids', default='')
    ap.add_argument('--n', type=int, default=0)
    ap.add_argument('--id', default='')
    ap.add_argument('--kf', default='')
    ap.add_argument('--video', default='')
    a = ap.parse_args()
    cfg = load_cfg(a.cfg)
    shots = load_shots(a.shots)
    man = Manifest(mv_of(shots))
    if a.mode == 'status':
        for s in shots:
            st = man.shot(s['id'])
            print(f"{s['id']:18s} kf={len(st['keyframes'])} pick={'y' if st['pick'] else '-'} "
                  f"videos={len(st['videos'])} final={'y' if st['final'] else '-'}")
        return
    if a.mode == 'pick':
        st = man.shot(a.id)
        if a.kf:
            st['pick'] = st.get('pick') or {}
            st['pick']['kf'] = os.path.join(man.shot_dir(a.id), a.kf)
        if a.video:
            st['video_pick'] = os.path.join(man.shot_dir(a.id), a.video)
            st['final'] = None
        man.save()
        return
    c = Comfy(cfg['comfy_url'], cfg['comfy_root'])
    todo = select(shots, a.ids)
    if a.mode == 'keyframes':
        do_keyframes(c, cfg, todo, man, a.n or 4)
    elif a.mode == 'videos':
        c.free()
        do_videos(c, cfg, todo, man, a.n or 1)
    elif a.mode == 'finish':
        c.free()
        do_finish(c, cfg, todo, man)


if __name__ == '__main__':
    main()

"""Character consistency: reference-sheet generation -> curated dataset -> LoRA.

  python gpu/charsheet.py gen     --chars design/characters.json [--n 3]     # candidates per view/outfit
  python gpu/charsheet.py sheet   --char kimi                                 # contact sheet for review
  python gpu/charsheet.py dataset --char kimi --keep 3,7,12,...               # curate + caption
  python gpu/charsheet.py train   --char kimi [--steps 2000 --rank 32]        # native ComfyUI LoRA training

characters.json:
  {"kimi": {"trigger": "kimi_hw", "identity": "1girl, black hair, short bob, ...",
            "outfits": {"sundress": "white sundress, straw hat with red ribbon", "yukata": "..."},
            "negative": "..."}}

Identity tags go into every generation prompt but are LEFT OUT of the training captions, so
the identity binds to the trigger word while outfit/pose/expression stay promptable.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gpu import graphs as gr  # noqa: E402
from gpu.comfy import Comfy  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')

VIEWS = [
    ('front_full', 'full body, standing, facing viewer, arms at sides, simple background, white background', 832, 1216),
    ('34_full', 'full body, standing, three-quarter view, from side, simple background, white background', 832, 1216),
    ('back_full', 'full body, standing, from behind, looking back over shoulder, simple background, white background', 832, 1216),
    ('side_full', 'full body, walking, from side, profile, simple background, white background', 832, 1216),
    ('bust_smile', 'upper body, portrait, smile, looking at viewer, simple background', 1024, 1024),
    ('bust_sad', 'upper body, portrait, sad, downcast eyes, simple background', 1024, 1024),
    ('bust_laugh', 'upper body, laughing, closed eyes, open mouth, simple background', 1024, 1024),
    ('bust_tears', 'upper body, close-up, tears, crying, sad smile, simple background', 1024, 1024),
    ('face_34', 'close-up, face, three-quarter view, looking away, simple background', 1024, 1024),
    ('scene_wind', 'cowboy shot, wind, hair blowing, outdoors, summer, blue sky, cumulonimbus', 1216, 832),
    ('scene_night', 'cowboy shot, night, city lights, bokeh, looking at viewer', 1216, 832),
    ('scene_sit', 'sitting, full body, on a bench, outdoors, afternoon light', 1216, 832),
]


def seed_of(*parts):
    return int(hashlib.md5('|'.join(map(str, parts)).encode()).hexdigest()[:10], 16)


def char_dir(name, sub=''):
    p = os.path.join(ROOT, 'work', 'chars', name, sub)
    os.makedirs(p, exist_ok=True)
    return p


def do_gen(c, chars, n, only=None):
    for name, ch in chars.items():
        if only and name not in only:
            continue
        out = char_dir(name, 'raw')
        index_p = os.path.join(out, 'index.json')
        index = json.load(open(index_p)) if os.path.exists(index_p) else {}
        for outfit, otags in ch['outfits'].items():
            for view, vtags, w, h in VIEWS:
                for k in range(n):
                    fn = f'{outfit}__{view}__{k}.png'
                    if fn in index:
                        continue
                    prompt = f"{ch['identity']}, {otags}, {vtags}, anime screencap, highres"
                    g = gr.t2i_anima(prompt, neg=ch.get('negative', gr.NEG_ANIMA), w=w, h=h,
                                     seed=seed_of(name, outfit, view, k), prefix=f'char_{name}')
                    outs = c.outputs(c.run(g))
                    c.fetch(outs[0], os.path.join(out, fn))
                    index[fn] = {'outfit': outfit, 'view': view, 'k': k, 'prompt': prompt}
                    json.dump(index, open(index_p, 'w'), indent=1, ensure_ascii=False)
                    print(name, fn, flush=True)


def do_sheet(name):
    from gpu.sheet import grid
    from PIL import Image
    raw = char_dir(name, 'raw')
    index = json.load(open(os.path.join(raw, 'index.json')))
    rows = {}
    for i, (fn, meta) in enumerate(sorted(index.items())):
        rows.setdefault(f"{meta['outfit']}/{meta['view']}", []).append((f'#{i} {fn.split("__")[-1]}', Image.open(os.path.join(raw, fn))))
    out = os.path.join(char_dir(name), 'sheet.jpg')
    grid(list(rows.items()), out, tw=256)
    # numbered listing for --keep
    for i, fn in enumerate(sorted(index)):
        print(i, fn)
    print(out)


def do_dataset(name, chars, keep, comfy_root):
    ch = chars[name]
    raw = char_dir(name, 'raw')
    index = json.load(open(os.path.join(raw, 'index.json')))
    files = sorted(index)
    picked = [files[i] for i in keep]
    ds = os.path.join(comfy_root, 'input', f'ds_{name}')
    if os.path.exists(ds):
        shutil.rmtree(ds)
    os.makedirs(ds)
    for fn in picked:
        meta = index[fn]
        shutil.copy(os.path.join(raw, fn), os.path.join(ds, fn))
        view_tags = dict((v[0], v[1]) for v in VIEWS)[meta['view']]
        caption = f"{ch['trigger']}, {ch['outfits'][meta['outfit']]}, {view_tags}"
        open(os.path.join(ds, fn.replace('.png', '.txt')), 'w').write(caption)
    print(f'{len(picked)} images -> {ds}')


def do_train(c, name, chars, steps, rank, lr):
    g = gr.train_lora(f'ds_{name}', steps=steps, rank=rank, lr=lr, prefix=f'loras/{chars[name]["trigger"]}')
    print('training', name, steps, 'steps rank', rank, flush=True)
    c.run(g, timeout=24 * 3600)
    print('done', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['gen', 'sheet', 'dataset', 'train'])
    ap.add_argument('--chars', default=os.path.join(ROOT, 'design', 'characters.json'))
    ap.add_argument('--char', default='')
    ap.add_argument('--n', type=int, default=3)
    ap.add_argument('--keep', default='')
    ap.add_argument('--steps', type=int, default=2000)
    ap.add_argument('--rank', type=int, default=32)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--url', default='http://127.0.0.1:8188')
    ap.add_argument('--comfy_root', default=os.path.join(ROOT, '.hw', 'ComfyUI'))
    a = ap.parse_args()
    chars = json.load(open(a.chars))
    if a.mode == 'sheet':
        return do_sheet(a.char)
    if a.mode == 'dataset':
        return do_dataset(a.char, chars, [int(x) for x in a.keep.split(',') if x], a.comfy_root)
    c = Comfy(a.url, a.comfy_root)
    if a.mode == 'gen':
        do_gen(c, chars, a.n, {a.char} if a.char else None)
    else:
        do_train(c, a.char, chars, a.steps, a.rank, a.lr)


if __name__ == '__main__':
    main()

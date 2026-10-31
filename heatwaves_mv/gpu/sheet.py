"""Contact sheets for reviewing generated candidates.

  python gpu/sheet.py keyframes work/A out.jpg [--ids A-hook-01,...]   # every keyframe candidate per shot
  python gpu/sheet.py videos work/A out.jpg [--frames 6]               # frames sampled across each video candidate
"""
import argparse
import glob
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def font(size=18):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/System/Library/Fonts/Helvetica.ttc'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def grid(rows, out, tw=384, label_h=22):
    """rows = [(row_label, [(tile_label, PIL.Image), ...]), ...]"""
    th = tw * 9 // 16
    cols = max(len(r[1]) for r in rows) if rows else 1
    W = 200 + cols * tw
    H = len(rows) * (th + label_h)
    sheet = Image.new('RGB', (W, H), (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    f = font(16)
    for r, (rl, tiles) in enumerate(rows):
        y = r * (th + label_h)
        d.text((6, y + th // 2), rl, fill=(255, 230, 120), font=f)
        for c, (tl, im) in enumerate(tiles):
            x = 200 + c * tw
            sheet.paste(im.convert('RGB').resize((tw, th)), (x, y + label_h))
            d.text((x + 4, y + 3), tl, fill=(200, 220, 255), font=f)
    sheet.save(out, quality=90)
    return out


def video_frames(path, n=6):
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    ims = []
    for k in range(n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(k * (total - 1) / max(1, n - 1)))
        ok, fr = cap.read()
        if ok:
            ims.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
    return ims


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['keyframes', 'videos'])
    ap.add_argument('work')
    ap.add_argument('out')
    ap.add_argument('--ids', default='')
    ap.add_argument('--frames', type=int, default=6)
    a = ap.parse_args()
    man = json.load(open(os.path.join(a.work, 'manifest.json')))
    ids = a.ids.split(',') if a.ids else sorted(man)
    rows = []
    for sid in ids:
        st = man.get(sid)
        if not st:
            continue
        if a.mode == 'keyframes':
            tiles = [(f"{os.path.basename(k['path'])}", Image.open(k['path'])) for k in st['keyframes']
                     if os.path.exists(k['path'])]
            if tiles:
                rows.append((sid, tiles))
        else:
            for v in st['videos']:
                if os.path.exists(v['path']):
                    fr = video_frames(v['path'], a.frames)
                    rows.append((f"{sid}\n{os.path.basename(v['path'])}", [(f'{i}', im) for i, im in enumerate(fr)]))
    print(grid(rows, a.out))


if __name__ == '__main__':
    main()

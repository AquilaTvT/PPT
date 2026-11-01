"""Keyframe sheets with a pixel grid, for reading off MV-A regions (design/mv_a/regions.json).

  python3 tools/region_sheet.py --out /tmp/sheets [--ids A-intro-01,A-intro-02] [--frame mid]

For each shot: the picked keyframe (or the clip's frame at --frame in|mid|out) at 1920x1080 cover-fit exactly as
the compositor sees it, a 120 px grid with coordinate labels, and the region names the recipe reads, written to
<out>/<id>.jpg at 960x540 (coordinates labelled in full-HD units). Regions already in regions.json are drawn.
"""
import argparse
import json
import os
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mva import timeline as tl  # noqa: E402
from mva import recipes as rc   # noqa: E402


def keys_for(sid):
    src = open(os.path.join(tl.ROOT, 'mva', 'recipes.py')).read()
    fn = 'a_' + sid[2:].replace('-', '_')
    m = re.search(rf'def {fn}\(.*?(?=\ndef |\Z)', src, re.S)
    if not m:
        return []
    return sorted(set(re.findall(r"REG\((?:sid|'[^']+'), '([a-z_]+)'", m.group(0))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--ids', default='')
    ap.add_argument('--frame', default='mid')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ids = [x for x in a.ids.split(',') if x] or [s['id'] for s in tl.SHOTS]
    reg = json.load(open(rc.REG_PATH)) if os.path.exists(rc.REG_PATH) else {}
    for sid in ids:
        s = tl.BY_ID[sid]
        d = s['end'] - s['start']
        local = {'in': 0.05, 'mid': d / 2, 'out': d - 0.05}[a.frame]
        img = rc.plate(s, local)
        u8 = (np.clip(img, 0, 1) * 255).astype(np.uint8).copy()
        for x in range(0, 1920, 120):
            cv2.line(u8, (x, 0), (x, 1079), (255, 0, 255), 1)
            cv2.putText(u8, str(x), (x + 3, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        for y in range(0, 1080, 120):
            cv2.line(u8, (0, y), (1919, y), (255, 0, 255), 1)
            cv2.putText(u8, str(y), (3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        for k, v in reg.get(sid, {}).items():
            if isinstance(v, list) and v and isinstance(v[0], list):
                cv2.polylines(u8, [np.int32(v)], True, (0, 255, 0), 3)
                cv2.putText(u8, k, tuple(int(c) for c in v[0]), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            elif isinstance(v, list) and len(v) in (4, 5) and k not in ('him_box', 'her_box', 'sea_box', 'tv_glass', 'train_box'):
                cv2.ellipse(u8, (int(v[0]), int(v[1])), (int(v[2]), int(v[3])), v[4] if len(v) > 4 else 0, 0, 360, (0, 255, 0), 3)
                cv2.putText(u8, k, (int(v[0]), int(v[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            elif isinstance(v, list) and len(v) == 4:
                cv2.rectangle(u8, (int(v[0]), int(v[1])), (int(v[2]), int(v[3])), (0, 255, 0), 3)
                cv2.putText(u8, k, (int(v[0]), int(v[1]) + 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            elif isinstance(v, list) and len(v) == 2:
                cv2.circle(u8, (int(v[0]), int(v[1])), 12, (0, 255, 0), 3)
                cv2.putText(u8, k, (int(v[0]) + 14, int(v[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        need = ', '.join(keys_for(sid)) or '-'
        cv2.rectangle(u8, (0, 1040), (1919, 1079), (0, 0, 0), -1)
        cv2.putText(u8, f'{sid}  regions: {need}', (10, 1070), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        out = cv2.resize(u8, (960, 540), interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(a.out, f'{sid}.jpg'), cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(sid, need, flush=True)


if __name__ == '__main__':
    main()

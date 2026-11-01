"""Stage only what the cloud compositor needs into the media clone (used by push_media.sh for work/A, work/B):
per shot the best video (final_up > v_0_up > final > v_0), the picked keyframe, plus the manifest.

  .hw/venv/bin/python gpu/stage_media.py <dest-root> work/A work/B
"""
import json
import os
import shutil
import sys
import time

VIDEO_ORDER = ('final_up.mp4', 'v_0_up.mp4', 'final.mp4', 'v_0.mp4')
MAX_BYTES = 95 * 1000 * 1000


def stage(dest_root, wdir):
    man_p = os.path.join(wdir, 'manifest.json')
    man = json.load(open(man_p)) if os.path.exists(man_p) else {}
    n_files, n_bytes = 0, 0
    for sid in sorted(os.listdir(wdir)):
        sd = os.path.join(wdir, sid)
        if not os.path.isdir(sd):
            continue
        keep = []
        for name in VIDEO_ORDER:                       # best video that GitHub accepts (hard limit 100 MB per file)
            vp = os.path.join(sd, name)
            if os.path.exists(vp):
                if time.time() - os.path.getmtime(vp) < 45:   # still being written by the chain: next push takes it
                    print(f'  {sid}/{name}: just written, skipped this time')
                    continue
                if os.path.getsize(vp) > MAX_BYTES:
                    print(f'  {sid}/{name}: {os.path.getsize(vp) / 1e6:.0f} MB > limit, trying the next one')
                    continue
                keep.append(name)
                break
        kf = ((man.get(sid) or {}).get('pick') or {}).get('kf')
        if kf and os.path.exists(os.path.join(sd, os.path.basename(kf))):
            keep.append(os.path.basename(kf))
        elif os.path.exists(os.path.join(sd, 'kf_0.png')):
            keep.append('kf_0.png')
        dd = os.path.join(dest_root, wdir, sid)
        os.makedirs(dd, exist_ok=True)
        for name in keep:
            src, dst = os.path.join(sd, name), os.path.join(dd, name)
            if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
                shutil.copy2(src, dst)
            n_files += 1
            n_bytes += os.path.getsize(src)
        for old in os.listdir(dd):                      # drop superseded files (e.g. v_0.mp4 once final_up exists)
            if old not in keep:
                os.remove(os.path.join(dd, old))
    if os.path.exists(man_p):
        os.makedirs(os.path.join(dest_root, wdir), exist_ok=True)
        shutil.copy2(man_p, os.path.join(dest_root, wdir, 'manifest.json'))
    print(f'{wdir}: {n_files} files, {n_bytes / 1e6:.0f} MB')


if __name__ == '__main__':
    dest = sys.argv[1]
    for w in sys.argv[2:]:
        stage(dest, w.rstrip('/'))

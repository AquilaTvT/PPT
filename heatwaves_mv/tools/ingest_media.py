"""Fetch the Mac's generated media from the repo's `hw-media` branch into ./work (cloud side of gpu/push_media.sh).

  python3 tools/ingest_media.py [--branch hw-media] [--only work/B] [--dry]

The branch mirrors the Mac's work/ layout (work/A/<shot>/kf_*.png, v_0.mp4, v_0_up.mp4, manifest.json, ...).
Files are copied into work/ only when new or changed (size / mtime), so it can be re-run as more media arrives.
Manifest paths are rewritten from the Mac's absolute paths to this checkout. A summary of what arrived is printed.
"""
import argparse
import json
import os
import shutil
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.media_branch')


def git(*a, cwd=None):
    return subprocess.run(['git', *a], cwd=cwd or ROOT, check=True, capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--branch', default='hw-media')
    ap.add_argument('--only', default='work')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    url = git('remote', 'get-url', 'origin').strip()
    if not os.path.isdir(os.path.join(CACHE, '.git')):
        os.makedirs(CACHE, exist_ok=True)
        git('init', '-q', cwd=CACHE)
        git('remote', 'add', 'origin', url, cwd=CACHE)
    for i in range(4):
        try:
            git('fetch', '-q', '--depth', '1', 'origin', a.branch, cwd=CACHE)
            break
        except subprocess.CalledProcessError as e:
            if i == 3:
                raise SystemExit(f'fetch failed: {e.stderr.strip()}')
            import time
            time.sleep(2 ** (i + 1))
    git('checkout', '-q', '-f', 'FETCH_HEAD', cwd=CACHE)
    src_root = os.path.join(CACHE, a.only)
    new = []
    for dp, dn, fn in os.walk(src_root):
        for f in fn:
            sp = os.path.join(dp, f)
            rel = os.path.relpath(sp, CACHE)
            dp_ = os.path.join(ROOT, rel)
            if os.path.exists(dp_) and os.path.getsize(dp_) == os.path.getsize(sp) and not f.endswith('.json'):
                continue
            new.append(rel)
            if not a.dry:
                os.makedirs(os.path.dirname(dp_), exist_ok=True)
                shutil.copy2(sp, dp_)
    # manifests: rewrite Mac absolute paths to this checkout
    for m in ('work/A/manifest.json', 'work/B/manifest.json'):
        p = os.path.join(ROOT, m)
        if os.path.exists(p) and not a.dry:
            d = json.load(open(p))
            s = json.dumps(d)
            # robust rewrite: any "...heatwaves_mv/work/X" -> "<ROOT>/work/X"
            import re
            s = re.sub(r'"[^"]*?heatwaves_mv/(work/[^"]*)"', lambda mm: json.dumps(os.path.join(ROOT, mm.group(1))), s)
            open(p, 'w').write(s)
    kinds = {}
    for r in new:
        k = os.path.splitext(r)[1]
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{'would copy' if a.dry else 'copied'} {len(new)} files: {kinds}")
    shots = sorted({r.split('/')[2] for r in new if r.count('/') >= 3})
    print('shots:', ' '.join(shots))


if __name__ == '__main__':
    main()

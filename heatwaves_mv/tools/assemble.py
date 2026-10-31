"""Concatenate rendered chunks, mux the song, and encode the deliverables.

  python tools/assemble.py --audio song.wav --out HeatWaves_MV_1080p.mp4 --mb 92
"""
import argparse
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mv import render  # noqa: E402
from tools.render_chunks import jobs  # noqa: E402

DUR = 198.74


def run(cmd):
    print(' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--audio', default=render.AUDIO)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mb', type=float, default=92.0, help='target file size in MB (2-pass)')
    ap.add_argument('--abr', type=int, default=192)
    ap.add_argument('--hq', default='', help='optional extra high-quality encode path (CRF)')
    ap.add_argument('--hq_crf', type=int, default=18)
    a = ap.parse_args()
    js = jobs([])
    missing = [j[4] for j in js if not os.path.exists(j[4] + '.done')]
    if missing:
        sys.exit(f'{len(missing)} chunks missing, e.g. {missing[0]}')
    work = render.OUT_DIR
    lst = os.path.join(work, 'final_list.txt')
    with open(lst, 'w') as f:
        for j in js:
            f.write(f"file '{j[4]}'\n")
    master = os.path.join(work, 'master_silent.mp4')
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', master])
    # 2-pass to a size budget
    vk = int((a.mb * 8 * 1000) / DUR - a.abr)
    print('video bitrate kbps', vk, flush=True)
    common = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{vk}k', '-maxrate', f'{int(vk * 2.2)}k',
              '-bufsize', f'{int(vk * 4)}k', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-g', '60',
              '-x264-params', 'aq-mode=3:aq-strength=0.9:psy-rd=1.0,0.15:deblock=-1,-1']
    os.chdir(work)
    run(['ffmpeg', '-v', 'error', '-y', '-i', master] + common + ['-pass', '1', '-an', '-f', 'mp4', os.devnull])
    run(['ffmpeg', '-v', 'error', '-y', '-i', master, '-i', a.audio] + common +
        ['-pass', '2', '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', f'{a.abr}k', '-t', str(DUR),
         '-movflags', '+faststart', a.out])
    for f in glob.glob(os.path.join(work, 'ffmpeg2pass*')):
        os.remove(f)
    if a.hq:
        run(['ffmpeg', '-v', 'error', '-y', '-i', master, '-i', a.audio, '-map', '0:v', '-map', '1:a',
             '-c:v', 'libx264', '-preset', 'slow', '-crf', str(a.hq_crf), '-pix_fmt', 'yuv420p', '-profile:v', 'high',
             '-c:a', 'aac', '-b:a', '256k', '-t', str(DUR), '-movflags', '+faststart', a.hq])
    print('done', a.out, os.path.getsize(a.out) / 1e6, 'MB')


if __name__ == '__main__':
    main()

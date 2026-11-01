"""MV-B v2 media status: per shot, the picked keyframe and the best video present (with fps, frames, duration),
plus the shots still running on a keyframe stand-in or on their v1 fallback.

  python3 tools/v2_status.py
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                        'stream=width,height,r_frame_rate,nb_read_packets', '-of', 'json', p], capture_output=True, text=True)
    try:
        s = json.loads(r.stdout)['streams'][0]
        num, den = (int(x) for x in s['r_frame_rate'].split('/'))
        fps = num / den
        n = int(s['nb_read_packets'])
        return f"{s['width']}x{s['height']} {fps:g}fps {n}f {n / fps:.2f}s"
    except Exception:
        return 'unreadable'


def main():
    from mvb import timeline as tl
    from mvb import v2
    from mvb import v2_card, v2_map
    graphic = set(v2_card.GRAPHIC) | set(v2_map.GRAPHIC)
    have, stand, missing = 0, [], []
    for s in tl.SHOTS:
        sid2 = v2.b2_id(s)
        if s['id'] in graphic:
            print(f"{s['id']:18s} graphic")
            continue
        clip = v2.clip_path(sid2)
        kf = v2.picks().get(sid2, '-')
        if clip:
            have += 1
            print(f"{s['id']:18s} {kf:6s} {os.path.basename(clip):14s} {probe(clip)}")
        elif v2.kf_path(sid2):
            stand.append(s['id'])
            print(f"{s['id']:18s} {kf:6s} (keyframe only)")
        else:
            missing.append(s['id'])
            print(f"{s['id']:18s} -      (nothing: v1 fallback)")
    print(f'\nvideos {have} / {len(tl.SHOTS) - len(graphic)}; keyframe only {len(stand)}; nothing {len(missing)}')
    if missing:
        print('nothing yet:', ' '.join(missing))


if __name__ == '__main__':
    main()

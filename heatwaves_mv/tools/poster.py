"""Contact-sheet poster of key frames from the finished video.

  python tools/poster.py master.mp4 poster.jpg
"""
import subprocess
import sys

import numpy as np
from PIL import Image

TIMES = [3.4, 9.6, 14.6, 21.4, 27.2, 33.4, 43.0, 47.6, 55.2, 61.0, 66.2, 79.4,
         87.7, 93.6, 104.6, 116.2, 128.2, 146.2, 166.8, 193.4]     # MV-B v2 "Heat Waves"


def grab(path, t, w=480):
    h = w * 9 // 16
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1', '-vf',
                          f'scale={w}:{h}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    return Image.fromarray(np.frombuffer(raw, np.uint8).reshape(h, w, 3))


def main(src, out, cols=4, gap=6, w=480):
    ims = [grab(src, t, w) for t in TIMES]
    h = ims[0].height
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap), (11, 16, 48))
    for k, im in enumerate(ims):
        c, r = k % cols, k // cols
        sheet.paste(im, (gap + c * (w + gap), gap + r * (h + gap)))
    sheet.save(out, quality=88)
    print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

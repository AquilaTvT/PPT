"""Contact-sheet poster of key frames from the finished video.

  python tools/poster.py master.mp4 poster.jpg
"""
import subprocess
import sys

import numpy as np
from PIL import Image

TIMES = [6.0, 18.6, 21.2, 30.2, 45.6, 61.8, 68.6, 77.6, 84.2, 98.6, 104.4, 107.6,
         112.6, 116.4, 122.4, 137.6, 155.0, 164.0, 186.8, 194.8]


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

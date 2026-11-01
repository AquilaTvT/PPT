"""Cache files written by several render workers at once: write to a private temp file, then rename over the target
(atomic on POSIX), so a reader never sees a half-written file; readers treat an unreadable file as missing."""
import json
import os

import cv2


def _tmp(path):
    root, ext = os.path.splitext(path)
    return f'{root}.tmp{os.getpid()}{ext}'


def save_json(path, obj):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = _tmp(path)
    with open(tmp, 'w') as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_img(path, img):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = _tmp(path)
    if not cv2.imwrite(tmp, img):
        raise IOError(f'could not write {tmp}')
    os.replace(tmp, path)

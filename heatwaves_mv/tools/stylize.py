"""Turn Anima renders into print-style assets that sit in the MV's world.

  python tools/stylize.py cutout  in.png out.png      # alpha matte (anime-seg)
  python tools/stylize.py style   in.png out.png --pal day|night|fest|dusk

The style pass:
  1. edge-preserving flatten (mean shift) -> cel regions
  2. k-means in Lab, every cluster snapped toward the scene's ink palette
  3. shading inside regions re-expressed as halftone dots of a shade ink
  4. line art pulled from the original and re-inked in the key navy
"""
import argparse
import math
import os
import sys

import cv2
import numpy as np

MODEL = os.environ.get('ANIME_SEG', '/tmp/claude-0/models/isnetis.onnx')

PALETTES = {
    # inks a cluster may snap to (sRGB hex); listed light -> dark per family
    'day': ['#FFFDF6', '#F4EAD6', '#FFF1E6', '#FBE3D2', '#F8D3BD', '#F0B9A0', '#E2A08A',
            '#DCDDF5', '#B9C3EA', '#8E98D8', '#5D66B0',
            '#DDEFF4', '#A9D8EF', '#6FB6E8', '#3F86D6', '#2A5FBF',
            '#F7DC8A', '#F2C46B', '#C98F3E', '#8A5A2B',
            '#FF8A7A', '#E8383D', '#C42F3A', '#9E1F35', '#7A1A2E',
            '#CFE3A0', '#9CCB5E', '#5FA746', '#2A6B3C',
            '#6B3A2E', '#3B4A8C', '#1E2A5E', '#141B3D'],
    'night': ['#F4EAD6', '#E8D9C4', '#B9C3EA', '#7FE3DE', '#2BB3B1', '#1D7F8C',
              '#8E98D8', '#5D66B0', '#3B4A8C', '#2A3570', '#1E2A5E', '#141B3D', '#0B1030',
              '#F6C9B0', '#C77B6A', '#8A4F5E', '#E8383D', '#9E1F35', '#FFCB45'],
    'fest': ['#FFF3D6', '#FBE3D2', '#F6C9B0', '#E9A98F', '#C77B6A', '#FFCB45', '#FF9A4D',
             '#FF6A55', '#E8383D', '#9E1F35', '#5B1E3E', '#B9C3EA', '#5D66B0', '#3B4A8C',
             '#2A3570', '#1E2A5E', '#141B3D', '#0B1030', '#7FE3DE', '#FF5C9E'],
    'dusk': ['#FFF1D6', '#FFD6A0', '#FFB37A', '#FF8A6A', '#E85A5A', '#B23A5E', '#7A2E6B',
             '#5B3C8C', '#3B2E6E', '#22204F', '#141B3D', '#FBE3D2', '#F6C9B0', '#E9A98F',
             '#C77B6A', '#FFCB45', '#B9C3EA', '#8E98D8', '#F2C46B', '#D9A05A', '#B9843A', '#8A5A2B',
             '#E8383D', '#9E1F35'],
}


def hex2bgr(h):
    h = h.lstrip('#')
    return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.uint8)


def to_lab(bgr_u8):
    return cv2.cvtColor(bgr_u8.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)


# --------------------------------------------------------------------------
def anime_seg(img_bgr, size=1024):
    import onnxruntime as ort
    sess = ort.InferenceSession(MODEL, providers=['CPUExecutionProvider'])
    h, w = img_bgr.shape[:2]
    s = size / max(h, w)
    nh, nw = int(h * s), int(w * s)
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    pad = np.zeros((size, size, 3), np.float32)
    y0, x0 = (size - nh) // 2, (size - nw) // 2
    pad[y0:y0 + nh, x0:x0 + nw] = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)
    inp = pad.transpose(2, 0, 1)[None]
    m = sess.run(None, {'img': inp})[0][0, 0]
    m = m[y0:y0 + nh, x0:x0 + nw]
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(m, 0, 1)


def refine_alpha(alpha, img_bgr):
    """tighten the matte: guided-ish smoothing then a contrast curve"""
    a = alpha.astype(np.float32)
    a = cv2.GaussianBlur(a, (0, 0), 0.8)
    a = np.clip((a - 0.25) / 0.5, 0, 1)
    return a


# --------------------------------------------------------------------------
def style(img_bgr, pal='day', k=14, line_strength=1.0, dots=True, cell=6, flatten=12, alpha=None,
          shade_ink=None, snap=0.78, keep_detail=0.25):
    h, w = img_bgr.shape[:2]
    # 1. flatten
    flat = cv2.pyrMeanShiftFiltering(img_bgr, sp=flatten, sr=24, maxLevel=1)
    flat = cv2.bilateralFilter(flat, 9, 40, 9)
    # 2. k-means in Lab
    lab = cv2.cvtColor(flat, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    if alpha is not None:
        sel = alpha.reshape(-1) > 0.5
        train = lab[sel] if sel.sum() > 1000 else lab
    else:
        train = lab
    rng = np.random.default_rng(0)
    sub = train[rng.choice(len(train), min(len(train), 60000), replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    _, _, centers = cv2.kmeans(sub, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    d = ((lab[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
    labels = d.argmin(1)
    # snap centres toward palette inks (in Lab, weighted on chroma so hues survive)
    inks = np.stack([hex2bgr(c) for c in PALETTES[pal]])
    inks_lab = to_lab(inks)
    snapped = []
    for c in centers:
        dd = ((inks_lab - c) ** 2 * np.array([1.0, 1.6, 1.6])).sum(-1)
        j = int(dd.argmin())
        snapped.append(c * (1 - snap) + inks_lab[j] * snap)
    snapped = np.array(snapped, np.float32)
    out_lab = snapped[labels].reshape(h, w, 3)
    out = cv2.cvtColor(np.clip(out_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32) / 255.0
    # 3. shading -> halftone: compare original luminance with its cluster mean
    L0 = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) / 255.0
    Lc = (centers[labels, 0].reshape(h, w)) / 255.0
    dev = cv2.GaussianBlur(L0, (0, 0), 2.0) - cv2.GaussianBlur(Lc, (0, 0), 2.0)
    if dots:
        shade = np.clip(-dev * 3.0, 0, 1)
        light = np.clip(dev * 3.0, 0, 1)
        ht_s = halftone_np(shade, cell, 45)
        ht_l = halftone_np(light, cell, 15)
        sink = (hex2bgr(shade_ink or ('#5D66B0' if pal != 'night' else '#0B1030')).astype(np.float32) / 255.0)
        out = out * (1 - ht_s[..., None] * 0.55) + out * sink * ht_s[..., None] * 0.55
        out = out + (1 - out) * ht_l[..., None] * 0.35
    if keep_detail > 0:
        out = out + (L0 - Lc)[..., None] * keep_detail
    # 4. line art
    if line_strength > 0:
        g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        bh = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        lines = np.clip((bh - 0.06) * 6.0, 0, 1) * line_strength
        dark = np.clip((0.22 - g) * 5.0, 0, 1)
        lines = np.maximum(lines, dark * 0.9)
        ink = hex2bgr('#141B3D' if pal != 'dusk' else '#22204F').astype(np.float32) / 255.0
        out = out * (1 - lines[..., None]) + ink * lines[..., None]
    return np.clip(out, 0, 1)


def halftone_np(cov, cell, angle):
    h, w = cov.shape
    th = math.radians(angle)
    cs, sn = math.cos(th), math.sin(th)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xs * cs + ys * sn
    v = -xs * sn + ys * cs
    cu = (np.floor(u / cell) + 0.5) * cell
    cv_ = (np.floor(v / cell) + 0.5) * cell
    dist = np.sqrt((u - cu) ** 2 + (v - cv_) ** 2)
    cx = np.clip(np.round(cu * cs - cv_ * sn), 0, w - 1).astype(np.int32)
    cy = np.clip(np.round(cu * sn + cv_ * cs), 0, h - 1).astype(np.int32)
    c = cv2.blur(cov, (int(cell * 0.75) | 1, int(cell * 0.75) | 1))[cy, cx]
    r = np.sqrt(np.clip(c, 0, 1) / math.pi) * cell
    r = np.where(c > 0.785, (0.5 + (c - 0.785) * 0.2071 / 0.215) * cell, r)
    o = np.clip(r - dist + 0.5, 0, 1)
    o[c < 0.01] = 0
    return o


def style_layers(img_bgr, pal='day', k=14, alpha=None, flatten=10, snapL=0.2, snapAB=0.45, line_strength=1.0,
                 line_ink='#141B3D'):
    """cel-flat colours + line art, plus shade/light maps for screen-space halftone.

    returns rgb (float, RGB order), shade (0..1), light (0..1)
    """
    h, w = img_bgr.shape[:2]
    flat = cv2.pyrMeanShiftFiltering(img_bgr, sp=flatten, sr=22, maxLevel=1)
    flat = cv2.bilateralFilter(flat, 9, 35, 9)
    lab = cv2.cvtColor(flat, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    sel = alpha.reshape(-1) > 0.5 if alpha is not None else np.ones(len(lab), bool)
    train = lab[sel] if sel.sum() > 1000 else lab
    rng = np.random.default_rng(0)
    sub = train[rng.choice(len(train), min(len(train), 60000), replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    _, _, centers = cv2.kmeans(sub, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    labels = np.empty(len(lab), np.int32)
    for s0 in range(0, len(lab), 200000):
        blk = lab[s0:s0 + 200000]
        labels[s0:s0 + 200000] = ((blk[:, None, :] - centers[None]) ** 2).sum(-1).argmin(1)
    inks_lab = to_lab(np.stack([hex2bgr(c) for c in PALETTES[pal]]))
    snapped = []
    for c in centers:
        dd = ((inks_lab - c) ** 2 * np.array([1.0, 1.3, 1.3])).sum(-1)
        j = int(dd.argmin())
        s = np.array([snapL, snapAB, snapAB], np.float32)
        snapped.append(c * (1 - s) + inks_lab[j] * s)
    snapped = np.array(snapped, np.float32)
    out_lab = snapped[labels].reshape(h, w, 3)
    out = cv2.cvtColor(np.clip(out_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32) / 255.0
    L0 = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) / 255.0
    Lc = (centers[labels, 0].reshape(h, w)) / 255.0
    dev = cv2.GaussianBlur(L0, (0, 0), 1.5) - cv2.GaussianBlur(Lc, (0, 0), 1.5)
    shade = np.clip(-dev * 3.2, 0, 1)
    light = np.clip(dev * 3.2, 0, 1)
    if line_strength > 0:
        g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        ks = max(5, int(round(min(h, w) / 180)) | 1)
        bh = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks)))
        lines = np.clip((bh - 0.07) * 6.0, 0, 1) * line_strength
        dark = np.clip((0.2 - g) * 5.0, 0, 1)
        lines = np.maximum(lines, dark * 0.85)
        ink = hex2bgr(line_ink).astype(np.float32) / 255.0
        out = out * (1 - lines[..., None]) + ink * lines[..., None]
    out = np.clip(out, 0, 1)[..., ::-1].copy()
    return out, shade, light


def save_asset(path, rgb, alpha, shade, light):
    """asset = RGBA png + shade/light packed in a second png (R=shade, G=light)"""
    a = np.ones(rgb.shape[:2], np.float32) if alpha is None else alpha
    rgba = np.dstack([rgb[..., ::-1], a])
    cv2.imwrite(path, (np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8))
    sl = np.dstack([np.zeros_like(shade), light, shade])
    cv2.imwrite(path.replace('.png', '_sl.png'), (np.clip(sl, 0, 1) * 255 + 0.5).astype(np.uint8))


def _inpaint(rgb, hole, work=480):
    """fill the character's hole in the background (low-res Telea, composited back)"""
    h, w = rgb.shape[:2]
    s = work / max(h, w)
    small = cv2.resize((rgb * 255).astype(np.uint8), (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    hm = cv2.resize((hole * 255).astype(np.uint8), (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    hm = (hm > 20).astype(np.uint8) * 255
    fill = cv2.inpaint(small, hm, 9, cv2.INPAINT_TELEA)
    fill = cv2.GaussianBlur(fill, (0, 0), 2.0)
    fill = cv2.resize(fill, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255.0
    k = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 3.0)[..., None]
    return rgb * (1 - k) + fill * k


def build(inp, out, pal='day', cutout=True, k=14, scale=1.5, flatten=10, crop=None, line_ink='#141B3D',
          layers=True):
    img = cv2.imread(inp, cv2.IMREAD_COLOR)
    if crop:
        x0, y0, x1, y1 = crop
        img = img[y0:y1, x0:x1]
    seg = anime_seg(img) if (cutout or layers) else None
    alpha = refine_alpha(seg, img) if cutout else None
    if scale != 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        if alpha is not None:
            alpha = cv2.resize(alpha, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
        if seg is not None:
            seg = cv2.resize(seg, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    rgb, shade, light = style_layers(img, pal, k, alpha=alpha, flatten=flatten, line_ink=line_ink)
    save_asset(out, rgb, alpha, shade, light)
    if not cutout and layers and seg is not None:
        # 2.5D: foreground character + inpainted background for parallax
        fa = refine_alpha(seg, img)
        if fa.mean() > 0.02:
            save_asset(out.replace('.png', '_fg.png'), rgb, fa, shade, light)
            r = max(3, int(min(img.shape[:2]) * 0.025))
            hole = cv2.dilate((fa > 0.15).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r)))
            bg = _inpaint(rgb, hole.astype(np.float32))
            save_asset(out.replace('.png', '_bg.png'), bg, None, shade * (1 - hole), light * (1 - hole))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['cutout', 'style', 'both', 'asset', 'scene'])
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--pal', default='day')
    ap.add_argument('--k', type=int, default=14)
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--cell', type=float, default=6)
    ap.add_argument('--flatten', type=int, default=10)
    a = ap.parse_args()
    if a.mode in ('asset', 'scene'):
        build(a.inp, a.out, a.pal, cutout=(a.mode == 'asset'), k=a.k, scale=a.scale, flatten=a.flatten)
        return
    img = cv2.imread(a.inp, cv2.IMREAD_COLOR)
    if a.scale != 1.0:
        img = cv2.resize(img, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_CUBIC)
    alpha = None
    if a.mode in ('cutout', 'both'):
        alpha = refine_alpha(anime_seg(img), img)
    if a.mode in ('style', 'both'):
        out = style(img, a.pal, a.k, alpha=alpha, cell=a.cell)
        out8 = (out * 255).astype(np.uint8)
    else:
        out8 = img
    if alpha is not None:
        out8 = np.dstack([out8, (alpha * 255).astype(np.uint8)])
    cv2.imwrite(a.out, out8)


if __name__ == '__main__':
    main()

"""The stamp-rally card (MV-B's thread): riso-printed card art rendered procedurally at 3200x1800.

  img = render_card(stamp_k=[1,1,1,1,1], sun_k=0.0, glow_k=0.0, footer_n=0, sixth_stamp=0.0)
Six circles along a printed coastal route: カーブミラー / プール / 夏祭り / 駅 / 防波堤 / 灯台・日の出.
Stamps 1-5 are old vermilion hanko (stamp_k 0..1 = faded 55% .. full ink); the sixth is empty with a dashed
outline; sun_k raises a 3-layer paper-cut sun out of its horizon; sixth_stamp slams the final stamp.
"""
import functools
import math

import cv2
import numpy as np
import skia

from mv import text
from .print_fx import hexc

CW, CH = 3200, 1800
CREAM, PAPER2, NAVY, COBALT, VERM, INK, SILVER, ORANGE, SUN = ('#EDE3CF', '#E4D7BC', '#1E2550', '#2C4C9A', '#D9402B',
                                                              '#1A1416', '#C9D3DC', '#F08A3C', '#F5C842')
CIRCLES = [(520, 1060, 'カーブミラー'), (1000, 760, 'プール'), (1480, 1080, '夏祭り'), (1960, 760, '駅'), (2440, 1060, '防波堤'),
           (2860, 700, '灯台・日の出')]
R0 = 170


def _paint(col, alpha=1.0, stroke=0.0, aa=True):
    c = hexc(col)
    p = skia.Paint(AntiAlias=aa, Color=skia.Color4f(float(c[0]), float(c[1]), float(c[2]), float(alpha)))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
    return p


def _font(name, size):
    return skia.Font(text.typeface(name), size)


def _text(c, s, x, y, size, col, name='mincho', align='center', alpha=1.0, tracking=0.0):
    f = _font(name, size)
    w = f.measureText(s) + tracking * size * max(0, len(s) - 1)
    x0 = x - w / 2 if align == 'center' else x
    pen = x0
    for ch in s:
        c.drawString(ch, pen, y, f, _paint(col, alpha))
        pen += f.measureText(ch) + tracking * size


@functools.lru_cache(maxsize=1)
def base_layer():
    surf = skia.Surface(CW, CH)
    c = surf.getCanvas()
    c.clear(skia.Color4f(*hexc(CREAM), 1.0))
    # sea: halftone cobalt band along the top-right with a wobbly coastline
    path = skia.Path()
    path.moveTo(0, 0)
    pts = [(x, 420 + 90 * math.sin(x / 420.0) + 40 * math.sin(x / 130.0)) for x in range(0, CW + 40, 40)]
    for x, y in pts:
        path.lineTo(x, y)
    path.lineTo(CW, 0)
    path.close()
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    for yy in range(-20, 700, 22):
        for xx in range(-20, CW + 20, 22):
            off = 11 if (yy // 22) % 2 else 0
            r = 6.0 + 2.5 * math.sin(xx / 210.0 + yy / 90.0)
            c.drawCircle(xx + off, yy, r, _paint(COBALT, 0.95))
    c.restore()
    c.drawPath(path, _paint(NAVY, 1.0, stroke=6))
    # railway (navy line with ticks) following the coast below it
    rail = skia.Path()
    rp = [(x, y + 150) for x, y in pts]
    rail.moveTo(*rp[0])
    for x, y in rp[1:]:
        rail.lineTo(x, y)
    c.drawPath(rail, _paint(NAVY, 1.0, stroke=10))
    for x, y in rp[::2]:
        c.drawLine(x, y - 18, x, y + 18, _paint(NAVY, 1.0, stroke=5))
    # dotted route connecting the six circles
    route = skia.Path()
    route.moveTo(CIRCLES[0][0], CIRCLES[0][1])
    for (x0, y0, _), (x1, y1, _) in zip(CIRCLES, CIRCLES[1:]):
        route.cubicTo(x0 + 200, y0, x1 - 200, y1, x1, y1)
    p = _paint(VERM, 0.85, stroke=8)
    p.setPathEffect(skia.DashPathEffect.Make([30, 22], 0))
    c.drawPath(route, p)
    # header
    _text(c, '夏休み スタンプラリー', 1600, 236, 140, NAVY, 'mincho', tracking=0.08)
    _text(c, 'SUMMER STAMP RALLY  1984', 1600, 318, 46, VERM, 'mincho', tracking=0.35)
    # circles + labels
    for i, (x, y, lab) in enumerate(CIRCLES):
        cp = _paint(NAVY, 1.0, stroke=8)
        if i == 5:
            cp.setPathEffect(skia.DashPathEffect.Make([26, 18], 0))
        c.drawCircle(x, y, R0, cp)
        _text(c, lab, x, y + R0 + 90, 64, NAVY, 'mincho', tracking=0.05)
        _text(c, '①②③④⑤⑥'[i], x - R0 + 10, y - R0 + 30, 56, VERM, 'mincho')
    # name box with two doodles
    c.drawRect(skia.Rect.MakeXYWH(140, 1560, 900, 170), _paint(NAVY, 1.0, stroke=6))
    _text(c, 'なまえ', 230, 1665, 56, NAVY, 'mincho')
    c.drawCircle(520, 1645, 38, _paint(ORANGE, 1.0, stroke=6))
    for k in range(8):
        a = k * math.pi / 4
        c.drawLine(520 + 52 * math.cos(a), 1645 + 52 * math.sin(a), 520 + 72 * math.cos(a), 1645 + 72 * math.sin(a), _paint(ORANGE, 1.0, stroke=6))
    moon = skia.Path()
    moon.addCircle(700, 1645, 46)
    cut = skia.Path()
    cut.addCircle(722, 1630, 42)
    moon = skia.Op(moon, cut, skia.PathOp.kDifference_PathOp)
    c.drawPath(moon, _paint(COBALT, 1.0))
    c.drawLine(140, 1500, 3060, 1500, _paint(NAVY, 0.7, stroke=3))
    arr = np.empty((CH, CW, 4), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(CW, CH, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType), arr, CW * 4)
    return arr[..., :3].astype(np.float32) / 255.0


def _stamp_icon(c, i, x, y, r):
    p = _paint(VERM, 1.0, stroke=10)
    f = _paint(VERM, 1.0)
    c.drawCircle(x, y, r * 0.92, p)
    if i == 0:      # curve mirror
        c.drawCircle(x, y - r * 0.18, r * 0.34, p)
        c.drawLine(x, y + r * 0.16, x, y + r * 0.62, p)
    elif i == 1:    # pool lanes
        for k in range(-2, 3):
            c.drawLine(x - r * 0.55, y + k * r * 0.2, x + r * 0.55, y + k * r * 0.2, p)
    elif i == 2:    # lantern
        c.drawOval(skia.Rect.MakeXYWH(x - r * 0.3, y - r * 0.42, r * 0.6, r * 0.8), f)
        c.drawLine(x, y - r * 0.6, x, y - r * 0.42, p)
    elif i == 3:    # station roof
        path = skia.Path()
        path.moveTo(x - r * 0.6, y)
        path.lineTo(x, y - r * 0.45)
        path.lineTo(x + r * 0.6, y)
        c.drawPath(path, p)
        c.drawLine(x - r * 0.4, y, x - r * 0.4, y + r * 0.5, p)
        c.drawLine(x + r * 0.4, y, x + r * 0.4, y + r * 0.5, p)
    elif i == 4:    # seawall wave
        path = skia.Path()
        path.moveTo(x - r * 0.6, y + r * 0.1)
        for k in range(4):
            xx = x - r * 0.6 + (k + 0.5) * r * 0.3
            path.quadTo(xx, y - r * 0.3, x - r * 0.6 + (k + 1) * r * 0.3, y + r * 0.1)
        c.drawPath(path, p)
        c.drawLine(x - r * 0.6, y + r * 0.4, x + r * 0.6, y + r * 0.4, p)
    elif i == 5:    # lighthouse + sun
        c.drawRect(skia.Rect.MakeXYWH(x - r * 0.12, y - r * 0.4, r * 0.24, r * 0.8), f)
        c.drawCircle(x + r * 0.35, y - r * 0.35, r * 0.16, f)


def _layer(draw):
    surf = skia.Surface(CW, CH)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    draw(c)
    arr = np.empty((CH, CW, 4), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(CW, CH, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kUnpremul_AlphaType), arr, CW * 4)
    return arr.astype(np.float32) / 255.0


@functools.lru_cache(maxsize=8)
def stamp_layer(i):
    x, y, _ = CIRCLES[i]
    lay = _layer(lambda c: _stamp_icon(c, i, x + 9, y - 6, R0 * 0.9))
    # rubber texture: knock out speckles
    rng = np.random.default_rng(i + 3)
    sp = (rng.random((CH // 4, CW // 4)) > 0.18).astype(np.float32)
    sp = cv2.resize(sp, (CW, CH), interpolation=cv2.INTER_NEAREST)
    lay[..., 3] *= sp
    return lay


def render_card(stamp_k=(1, 1, 1, 1, 1), sun_k=0.0, glow_k=0.0, footer_n=0, footer='YOU KNOW THAT I\'M NEVER GONNA LOSE',
                sixth_stamp=0.0, ray_rot=0.0):
    img = base_layer().copy()
    for i, k in enumerate(stamp_k):
        lay = stamp_layer(i)
        a = lay[..., 3:4] * (0.55 + 0.45 * k)
        img = img * (1 - a) + lay[..., :3] * a
    x, y, _ = CIRCLES[5]
    if glow_k > 0:
        ys, xs = np.mgrid[0:CH:4, 0:CW:4].astype(np.float32)
        d = np.sqrt((xs - x) ** 2 + (ys - y) ** 2)
        tone = np.clip(0.8 * np.exp(-(d / (300 * (0.6 + glow_k))) ** 2) * glow_k, 0, 1)
        per = 16.0
        u, v = (xs + ys) / (per * 1.414), (xs - ys) / (per * 1.414)
        dd = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
        m = np.clip((np.sqrt(tone) * 0.66 - dd) * 6, 0, 1)
        m = cv2.resize(m, (CW, CH))
        img = img * (1 - m[..., None]) + hexc(SUN)[None, None] * m[..., None]
    if sun_k > 0:
        def draw_sun(c):
            c.save()
            clip = skia.Path()
            clip.addCircle(x, y, R0 - 8)
            c.clipPath(clip, skia.ClipOp.kIntersect, True)
            hy = y + R0 * 0.35
            cy = hy + R0 * 0.9 - R0 * 1.25 * sun_k
            for li, (col, rr, off) in enumerate(((ORANGE, R0 * 0.62, 9), (SUN, R0 * 0.5, 6), ('#FFF2C8', R0 * 0.34, 3))):
                c.drawCircle(x + off * 0.3, cy + off, rr, _paint(col, 1.0))
            for k in range(12):
                a = k * math.pi / 6 + math.radians(ray_rot)
                p0 = (x + math.cos(a) * R0 * 0.7, cy + math.sin(a) * R0 * 0.7)
                p1 = (x + math.cos(a) * R0 * 1.0, cy + math.sin(a) * R0 * 1.0)
                c.drawLine(p0[0], p0[1], p1[0], p1[1], _paint(ORANGE, 1.0, stroke=14))
            c.drawRect(skia.Rect.MakeXYWH(x - R0, hy, 2 * R0, R0), _paint(CREAM, 1.0))
            c.drawLine(x - R0, hy, x + R0, hy, _paint(NAVY, 1.0, stroke=6))
            c.restore()
        lay = _layer(draw_sun)
        a = lay[..., 3:4]
        img = img * (1 - a) + lay[..., :3] * a
    if sixth_stamp > 0:
        lay = stamp_layer(5)
        a = lay[..., 3:4] * min(1.0, sixth_stamp)
        img = img * (1 - a) + lay[..., :3] * a
    if footer_n > 0:
        s = footer[:footer_n]
        lay = _layer(lambda c: (_text(c, s, 1600, 1440, 64, NAVY, 'mincho', tracking=0.4)))
        lay2 = _layer(lambda c: (_text(c, s, 1601, 1441, 64, VERM, 'mincho', tracking=0.4, alpha=0.8)))
        for L in (lay2, lay):
            a = L[..., 3:4]
            img = img * (1 - a) + L[..., :3] * a
    return img


def view(card, cx, cy, zoom, rot=0.0, out=(1920, 1080)):
    """camera over the card: centre (cx, cy) in card px, zoom 1 = card width fills the frame"""
    s = out[0] / CW * zoom
    M = cv2.getRotationMatrix2D((cx, cy), rot, s)
    M[0, 2] += out[0] / 2 - cx
    M[1, 2] += out[1] / 2 - cy
    return cv2.warpAffine(card, M, out, flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)

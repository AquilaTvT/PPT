"""MV-B v2: the television shots of the verse (raw stage devices, registered into mvb.v2.RAW).

  verse-01  his hand turns the dial: one channel per beat behind the hand -- weather map (the real coast),
            night baseball on a dot-matrix board, the film he will remember (verse-03), a quiz show -- with
            two frames of static between them
  verse-02  he is pressed against the glass: scanlines, curvature, the window reflected in the glass
  verse-03  the 'Hollywood movie' at the sunset station (letterboxed, the train's sign fixed to an LED board);
            then the view pulls back out of the screen into his dark room
  verse-04  the perfect-life commercial: framed by the CRT, a channel bug, a slogan
  verse-07  sign-off, test card, the circle; the room dims a step on every beat
"""
import functools
import math

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import BEAT, BEAT0
from . import v2
from . import v2_fx as fx
from .print_fx import hexc as H

W, H_ = 1920, 1080
RAW = {}


def _skia_rgba(draw, w=W, h=H_):
    import skia
    surf = skia.Surface(w, h)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    draw(c)
    arr = np.empty((h, w, 4), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kUnpremul_AlphaType), arr, w * 4)
    return arr.astype(np.float32) / 255.0


def _over(img, rgba):
    a = rgba[..., 3:4]
    return img * (1 - a) + rgba[..., :3] * a


def _paint(col, alpha=1.0, stroke=0.0):
    import skia
    c = H(col)
    p = skia.Paint(AntiAlias=True, Color=skia.Color4f(float(c[0]), float(c[1]), float(c[2]), float(alpha)))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def _tv_text(c, s, x, y, size, col='#FFFFFF', name='kaku', align='left', outline='#101018', ow=0.16):
    """1985 telop: chunky gothic with a dark outline"""
    from mv import text
    f = text.font(name, size)
    w = f.measureText(s)
    x0 = x - w / 2 if align == 'center' else (x - w if align == 'right' else x)
    if outline:
        c.drawString(s, x0, y, f, _paint(outline, 1.0, stroke=size * ow))
    c.drawString(s, x0, y, f, _paint(col))


# ------------------------------------------------------------------ channels
@functools.lru_cache(maxsize=1)
def ch_weather():
    from . import v2_map
    img = v2_map.view('dawn', dict(cx=1550, cy=1050, rot=0, dist=3300, tilt=0), dof=False)
    img = img * 0.85 + 0.08

    def draw(c):
        import skia
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W, 150), _paint('#1E3C8C', 0.92))
        _tv_text(c, '天気予報', 70, 110, 84, '#FFFFFF', outline=None)
        _tv_text(c, '八月九日（金）', 1850, 108, 60, '#F5C842', align='right', outline=None)
        for (x, y, kind, temp) in ((560, 420, 'sun', '32°'), (1160, 360, 'sun', '33°'), (1580, 470, 'cloud', '30°'),
                                   (520, 820, 'sun', '31°')):
            if kind == 'sun':
                c.drawCircle(x, y, 62, _paint('#F5C842'))
                c.drawCircle(x, y, 62, _paint('#D9402B', stroke=6))
                for k in range(12):
                    a = k * math.pi / 6
                    c.drawLine(x + math.cos(a) * 78, y + math.sin(a) * 78, x + math.cos(a) * 104, y + math.sin(a) * 104,
                               _paint('#F08A3C', stroke=12))
            else:
                for dx, dy, r in ((-40, 10, 48), (10, -20, 60), (60, 12, 44)):
                    c.drawCircle(x + dx, y + dy, r, _paint('#F3F1EA'))
                c.drawRect(skia.Rect.MakeXYWH(x - 80, y + 10, 180, 50), _paint('#F3F1EA'))
            _tv_text(c, temp, x + 120, y + 30, 76, '#FFFFFF')
        _tv_text(c, '潮見', 400, 560, 58, '#FFFFFF')
        _tv_text(c, '汐見島', 330, 960, 52, '#FFFFFF')
        _tv_text(c, '浜町', 1060, 470, 52, '#FFFFFF')
        c.drawRect(skia.Rect.MakeXYWH(0, 990, W, 90), _paint('#101018', 0.75))
        _tv_text(c, '晴れ　日中は暑さが続くでしょう', 70, 1056, 56, '#FFFFFF', outline=None)
    return np.clip(_over(img, _skia_rgba(draw)), 0, 1)


@functools.lru_cache(maxsize=1)
def ch_baseball():
    from . import print_fx as pf
    img = np.empty((H_, W, 3), np.float32)
    img[:] = H('#0F2A1C')
    rows = ['ナイター中継', '潮見　010 020 010　４', '浜町　000 300 001　４', '九回裏　二死満塁']
    y = 110
    for i, r in enumerate(rows):
        rgb, _ = pf.led_board(r, rows=14, dot=14 if i else 12, on='#F5C842' if i in (0, 3) else '#FF8A3A', off='#173523',
                              bg='#0F2A1C', font='dot', glow=0.5)
        h, w = rgb.shape[:2]
        w = min(w, W - 120)
        img[y:y + h, 60:60 + w] = rgb[:, :w]
        y += h + 60
    return img


@functools.lru_cache(maxsize=1)
def ch_quiz():
    ys, xs = np.mgrid[0:H_, 0:W].astype(np.float32)
    g = np.clip(ys / H_, 0, 1)[..., None]
    img = H('#4B1E78')[None, None] * (1 - g) + H('#D9402B')[None, None] * g
    rays = (np.sin(np.arctan2(ys - 1180, xs - 960) * 18) > 0.3).astype(np.float32) * 0.18
    img = img + rays[..., None] * H('#F5C842')[None, None]

    def draw(c):
        for k in range(26):
            a = k / 26 * 2 * math.pi
            x, y = 960 + math.cos(a) * 780, 520 + math.sin(a) * 420
            c.drawCircle(x, y, 22, _paint('#FFF2C8' if k % 2 else '#F5C842'))
        _tv_text(c, 'クイズ', 960, 470, 260, '#F5C842', name='dela', align='center', outline='#2A0E3A', ow=0.12)
        _tv_text(c, '夏の夜 一〇〇問', 960, 680, 120, '#FFFFFF', name='dela', align='center', outline='#2A0E3A', ow=0.12)
    return np.clip(_over(img, _skia_rgba(draw)), 0, 1)


def ch_movie(t_src):
    f = v2.footage('B2-verse-03')
    if f is None:
        return ch_quiz()
    img = f.at(t_src % max(0.5, f.dur - 0.1))
    img = img.copy()
    img[:130] = 0.02
    img[-130:] = 0.02
    return img


def static(t, seed=0):
    rng = np.random.default_rng(int(t * 24) * 7 + seed)
    n = rng.random((H_ // 4, W // 4)).astype(np.float32)
    n = cv2.resize(n, (W, H_), interpolation=cv2.INTER_NEAREST)
    tear = np.roll(n, int(rng.integers(-60, 60)), axis=1)
    return np.repeat(np.clip(tear * 0.9 + 0.05, 0, 1)[..., None], 3, axis=2)


# ------------------------------------------------------------------ verse-01: the dial
V01_SCREEN = [(392, -24), (1602, -24), (1592, 652), (420, 658)]


def verse01(s, t, local):
    img = v2.plate(s, local)
    plate = img.copy()
    nb = (t - BEAT0) / BEAT
    k = int(math.floor(nb)) - int(math.floor((s['start'] - BEAT0) / BEAT + 0.02))
    ph = (nb - math.floor(nb)) * BEAT
    chans = [lambda: ch_weather(), lambda: ch_baseball(), lambda: ch_movie(1.0 + local), lambda: ch_quiz()]
    content = static(t) if (ph < 2 / 24 and k > 0) else chans[max(0, min(3, k))]()
    tv = fx.crt(content, t, tint='#DDF2FF', curve=0.05, bloom=0.3)
    lum = plate @ np.float32([0.2126, 0.7152, 0.0722])
    lit = cv2.GaussianBlur(np.clip((lum - 0.42) / 0.18, 0, 1), (0, 0), 1.5)       # the hand and knob stay in front
    q = np.asarray(V01_SCREEN, np.float32)
    keep = img.copy()
    img = fx.quad_paste(img, tv, q, feather=3.0)
    img = keep + (img - keep) * lit[..., None]
    return v2.glow(img, 0.25)


RAW['B-verse-01'] = verse01


# ------------------------------------------------------------------ verse-02: against the glass
@functools.lru_cache(maxsize=1)
def _glass_layers():
    ys, xs = np.mgrid[0:H_, 0:W].astype(np.float32)
    u, v = (xs - W / 2) / (W / 2), (ys - H_ / 2) / (H_ / 2)
    scan = 0.86 + 0.14 * (np.sin(ys * math.pi / 2.0) * 0.5 + 0.5)
    refl = np.exp(-(((u * 0.7 + v * 0.7) + 0.55) / 0.18) ** 2) * 0.22          # a soft diagonal sheen
    win = np.zeros((H_, W), np.float32)
    cv2.rectangle(win, (1300, 90), (1700, 420), 1.0, -1)
    cv2.line(win, (1500, 90), (1500, 420), 0.0, 14)
    cv2.line(win, (1300, 255), (1700, 255), 0.0, 14)
    win = cv2.GaussianBlur(win, (0, 0), 18) * 0.10
    vig = np.clip(1 - 0.45 * (u * u + v * v) ** 1.4, 0.3, 1)
    return scan, refl + win, vig


def verse02(s, t, local):
    img = v2.plate(s, local)
    k = 0.04
    ys, xs = np.mgrid[0:H_, 0:W].astype(np.float32)
    u, v = (xs - W / 2) / (W / 2), (ys - H_ / 2) / (H_ / 2)
    f = 1 + k * (u * u + v * v)
    img = cv2.remap(img, (u / f * W / 2 + W / 2).astype(np.float32), (v / f * H_ / 2 + H_ / 2).astype(np.float32),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    scan, refl, vig = _glass_layers()
    img = img * scan[..., None] * vig[..., None] + refl[..., None] * H('#CFE8FF')[None, None]
    return v2.glow(img, 0.3)


RAW['B-verse-02'] = verse02


# ------------------------------------------------------------------ verse-03: the film, then out of the screen
V03_SIGN = [(775, -6), (1185, -6), (1185, 54), (775, 54)]
V07_SCREEN = [(858, 298), (1032, 298), (1030, 448), (860, 450)]
PULL = (61.2, 64.39)


@functools.lru_cache(maxsize=1)
def _sign_board():
    from . import print_fx as pf
    rgb, _ = pf.led_board('潮見ゆき', rows=12, dot=10, on='#FF9A3C', off='#3A1A10', bg='#140A06', font='dot', glow=0.6)
    return rgb


def _film(s, t, local):
    img = v2.plate(s, local)
    img = fx.quad_paste(img, _sign_board(), V03_SIGN, feather=1.5)
    img = v2.glow(img, 0.18)
    return img


def verse03(s, t, local):
    film = _film(s, t, local)
    if t < PULL[0]:
        out = film.copy()
        out[:120] *= 0.04
        out[-120:] *= 0.04
        return out
    # pull back out of the screen into his room (the room of verse-07)
    k = clamp((t - PULL[0]) / (PULL[1] - PULL[0]))
    e = k * k * (3 - 2 * k)
    room_f = v2.footage('B2-verse-07')
    room = room_f.at(0.2 + (t - PULL[0]) * 0.3) if room_f is not None else np.zeros((H_, W, 3), np.float32)
    q = np.asarray(V07_SCREEN, np.float32)
    sc = q.mean(0)
    sw = q[1, 0] - q[0, 0]
    z0 = W / sw * 1.02
    z = math.exp(math.log(z0) * (1 - e))
    cx, cy = sc[0] + (W / 2 - sc[0]) * e, sc[1] + (H_ / 2 - sc[1]) * e
    M = np.float32([[z, 0, W / 2 - cx * z], [0, z, H_ / 2 - cy * z]])
    view = cv2.warpAffine(room * (0.55 + 0.45 * e), M, (W, H_), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    qs = np.hstack([q, np.ones((4, 1), np.float32)]) @ M.T
    tv = fx.crt(film, t, tint='#DDF2FF', curve=0.06 * e, bloom=0.25 * e, lines=e > 0.15)
    view = fx.quad_paste(view, tv, qs, feather=1.0 + 2 * e)
    # the TV's light falls into the room as it shrinks
    return v2.glow(view, 0.25 * e)


RAW['B-verse-03'] = verse03


# ------------------------------------------------------------------ verse-04: the commercial
@functools.lru_cache(maxsize=1)
def _bezel():
    ys, xs = np.mgrid[0:H_, 0:W].astype(np.float32)
    x0, y0, x1, y1, r = 110, 70, W - 110, H_ - 70, 110
    dx = np.maximum(np.maximum(x0 + r - xs, xs - (x1 - r)), 0)
    dy = np.maximum(np.maximum(y0 + r - ys, ys - (y1 - r)), 0)
    d = np.sqrt(dx * dx + dy * dy) - r
    inside = np.clip(-d / 3.0, 0, 1)
    edge = np.exp(-(d / 10.0) ** 2) * 0.35
    return inside, edge


def verse04(s, t, local):
    img = v2.plate(s, local)
    tv = fx.crt(img, t, tint='#FFF4DA', curve=0.05, bloom=0.22)
    inside, edge = _bezel()
    plastic = H('#24201E')[None, None] * (0.8 + 0.2 * (np.arange(H_, dtype=np.float32) / H_)[:, None, None])
    out = plastic * (1 - inside[..., None]) + tv * inside[..., None] + edge[..., None] * 0.25

    def draw(c):
        _tv_text(c, '潮見テレビ', 200, 160, 40, '#FFFFFF', align='left', outline='#101018', ow=0.12)
        if local > 0.9:
            a = clamp((local - 0.9) / 0.3)
            _tv_text(c, 'この夏を、もう一度。', 200, 930, 76, '#FFFFFF', name='mincho', outline='#101018', ow=0.10)
            _tv_text(c, '潮見観光協会', 205, 990, 36, '#F5C842', outline='#101018', ow=0.12)
    return _over(out, _skia_rgba(draw))


RAW['B-verse-04'] = verse04


# ------------------------------------------------------------------ verse-07: sign-off, test card, the room dims
def verse07(s, t, local):
    from .recipes import sign_off_card, test_card
    img = v2.plate(s, local)
    nb0 = math.floor((s['start'] - BEAT0) / BEAT + 0.02)
    k = int(math.floor((t - BEAT0) / BEAT)) - nb0
    dim = [1.0, 0.80, 0.62, 0.46, 0.34][max(0, min(4, k))]
    if t < 74.02:
        content = _cached_card('signoff', sign_off_card)
    elif t < 75.50:
        content = _cached_card('test', test_card)
    else:
        content = _cached_card('circle', lambda: test_card(True))
    tv = fx.crt(content, t, tint='#DDF2FF', curve=0.06, bloom=0.4)
    q = np.asarray(V07_SCREEN, np.float32)
    m = np.zeros((H_, W), np.float32)
    cv2.fillPoly(m, [np.round(q * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
    glow = cv2.GaussianBlur(m, (0, 0), 60) * 1.6
    keep = np.clip(m + glow * 0.35, 0, 1)
    img = img * (dim + (1 - dim) * keep)[..., None]
    img = fx.quad_paste(img, tv, q, feather=1.5)
    return v2.glow(img, 0.22)


_CARDS = {}


def _cached_card(key, fn):
    if key not in _CARDS:
        _CARDS[key] = np.clip(fn(), 0, 1).astype(np.float32)
    return _CARDS[key]


RAW['B-verse-07'] = verse07


LYRIC = {'B-verse-01': dict(x=1845, y=120, size=84), 'B-verse-03': dict(x=180), 'B-verse-04': dict(x=1700, y=200)}


def install():
    v2.RAW.update(RAW)
    v2.LYRIC_POS.update(LYRIC)

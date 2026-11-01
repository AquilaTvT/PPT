"""The stamp-rally card, v2: a 1985 four-ink riso card with the real Shiomi coast on it.

  card = render_card(stamp_k=(1, 1, 1, 1, 1), sun_k=0.0, glow_k=0.0)   # float RGB, PW x PH (design x SC)
  img = view(card, cx, cy, zoom, rot)                                   # 1920x1080; cx, cy in design units
  CIRCLES[i] = (x, y, label) in design units (3200 x 1800); R0 = stamp circle radius

Printing model: cream stock (mottling + fibres) and four inks laid down by multiplication, so overprints mix
the way ink does (yellow over cobalt = green woods, vermilion over cobalt = maroon). Each ink is a coverage
mask with its own grain and a slight misregistration. Cream type is knocked out of the plates, labels on the
map knock out a halo in the other inks.

Left: the map panel -- the real coast from OpenStreetMap (see mvb/shiomi_map.py): sea in a cobalt depth
screen with coastal hatching, every building as a light cobalt block, main roads yellow with cobalt casings,
the railway as the classic dashed band, woods green by overprint, beaches in yellow stipple, the route in
vermilion dashes along real streets with numbered pins. Right: six stamp cells. Stamps are pressed with
vermilion stamp-pad ink: double ring, lettering round the ring, an engraved illustration made from the film's
own keyframes (work/B2/<shot>/kf_*.png -> hatching + lines), the date, rubber speckle and uneven pressure.
"""
import functools
import math
import os

import cv2
import numpy as np
import skia

from mv import text
from .print_fx import hexc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, 'work', 'B2', 'card')
SC = 1.5                                     # px per design unit
CW, CH = 3200, 1800                          # design units
PW, PH = int(CW * SC), int(CH * SC)

PAPER = '#EDE3CF'
INK = {'yellow': '#F2C23A', 'cobalt': '#2C4C9A', 'verm': '#D9402B', 'navy': '#1E2550'}
SHIFT = {'yellow': (2.0, 3.0), 'cobalt': (3.0, -2.0), 'verm': (-2.0, 2.5), 'navy': (0.0, 0.0)}   # misregistration, px
STAMP_INK = '#C3342A'
CREAM, NAVY, COBALT, VERM, SUN, ORANGE = PAPER, INK['navy'], INK['cobalt'], INK['verm'], '#F5C842', '#F08A3C'

MAP_BOX = (420, 440, 2160, 1490)             # map panel (design units)
M0 = (-200.0, 330.0)                         # map metres at the panel's top-left
MAP_S = 0.553                                # design units per metre
R0 = 130
CELL_C = [(2445, 612), (2875, 612), (2445, 962), (2875, 962), (2445, 1312), (2875, 1312)]
LABELS = ['潮見駅', 'プール', 'カーブミラー', '自動販売機', '夏祭り', '灯台・日の出']
CIRCLES = [(x, y, LABELS[i]) for i, (x, y) in enumerate(CELL_C)]
NUM = '一二三四五六'
STAMP_RING = ['潮見線 潮見駅', '県立潮見高校 プール', '浜町三丁目 カーブミラー', '七里の浜 海岸通り', '潮見商店街 夏祭り',
              '汐見島灯台 日の出']
DATES = ['60.7.21', '60.7.28', '60.8.3', '60.8.9', '60.8.17', '60.8.31']
# engraved illustrations: (shot, keyframe, centre x, centre y, radius) in the 1280x704 keyframe
ART = {0: ('B2-intro-01', 0, 420, 380, 220), 1: ('B2-outro-04', 0, 640, 380, 300), 2: ('B2-hook-04', 0, 640, 330, 330),
       3: ('B2-chorus4-04', 0, 640, 380, 300), 4: ('B2-chorus3-01', 0, 640, 300, 300), 5: ('B2-outro-06', 0, 640, 330, 320)}


def m2d(xm, ym):
    """map metres -> card design units"""
    return MAP_BOX[0] + (xm - M0[0]) * MAP_S, MAP_BOX[1] + (ym - M0[1]) * MAP_S


# ------------------------------------------------------------------ skia helpers (draw in design units)
def _a8():
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(PW, PH, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType))
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    c.scale(SC, SC)
    return surf, c


def _cov(surf):
    a = np.empty((PH, PW), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(PW, PH, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType), a, PW)
    return a.astype(np.float32) * (1 / 255.0)


def P(alpha=1.0, stroke=0.0, clear=False, cap=None):
    p = skia.Paint(AntiAlias=True, Color=skia.Color4f(1, 1, 1, float(alpha)))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(float(stroke))
    if cap == 'round':
        p.setStrokeCap(skia.Paint.kRound_Cap)
    if clear:
        p.setBlendMode(skia.BlendMode.kClear)
    return p


def F(name, size):
    f = skia.Font(text.typeface(name), float(size))
    f.setSubpixel(True)
    return f


def tw(s, name, size, tracking=0.0):
    f = F(name, size)
    return sum(f.measureText(ch) for ch in s) + tracking * size * max(0, len(s) - 1)


def T(c, s, x, y, size, name='mincho', align='center', paint=None, tracking=0.0):
    f = F(name, size)
    w = tw(s, name, size, tracking)
    pen = x - w / 2 if align == 'center' else (x - w if align == 'right' else x)
    for ch in s:
        c.drawString(ch, pen, y, f, paint or P())
        pen += f.measureText(ch) + tracking * size


def TV(c, s, x, y, size, name='mincho', paint=None, lead=1.08):
    """vertical text, one glyph per line, centred on x"""
    f = F(name, size)
    for i, ch in enumerate(s):
        w = f.measureText(ch)
        c.drawString(ch, x - w / 2, y + i * size * lead, f, paint or P())


def ring_text(c, s, cx, cy, r, size, name='old', mid=-90.0, spread=1.0, paint=None, bottom=False):
    """glyphs round a circle centred on angle `mid`; bottom=True reads left-to-right along the lower arc, upright"""
    f = F(name, size)
    step = math.degrees(size * 1.12 * spread / r)
    n = len(s)
    for i, ch in enumerate(s):
        off = (i - (n - 1) / 2) * step
        a = mid - off if bottom else mid + off
        ar = math.radians(a)
        c.save()
        c.translate(cx + math.cos(ar) * r, cy + math.sin(ar) * r)
        c.rotate(a - 90 if bottom else a + 90)
        w = f.measureText(ch)
        c.drawString(ch, -w / 2, size * 0.36, f, paint or P())
        c.restore()


# ------------------------------------------------------------------ paper and inks
def _noise(shape, sigma, seed):
    rng = np.random.default_rng(seed)
    n = rng.standard_normal(shape).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), sigma)
    return n / (n.std() + 1e-6)


@functools.lru_cache(maxsize=1)
def paper():
    rng = np.random.default_rng(1985)
    img = np.empty((PH, PW, 3), np.float32)
    img[:] = hexc(PAPER)
    mot = cv2.resize(_noise((PH // 8, PW // 8), 2.0, 3), (PW, PH), interpolation=cv2.INTER_CUBIC)
    img *= (1 + 0.011 * mot)[..., None]
    fib = np.zeros((PH, PW), np.float32)
    for _ in range(int(3000 * SC)):
        x, y, a, ln = rng.uniform(0, PW), rng.uniform(0, PH), rng.uniform(0, math.pi), rng.uniform(10, 46) * SC
        cv2.line(fib, (int(x), int(y)), (int(x + math.cos(a) * ln), int(y + math.sin(a) * ln)), 1.0, 1, cv2.LINE_AA)
    img -= (cv2.GaussianBlur(fib, (0, 0), 0.6) * 0.045)[..., None]
    grain = _noise((PH, PW), 0.7, 4)
    img *= (1 + 0.012 * grain)[..., None]
    return img


def _grain(seed):
    return np.clip(1 - 0.09 * np.abs(_noise((PH, PW), 0.8, seed)) - 0.05 * cv2.resize(_noise((PH // 24, PW // 24), 1.5, seed + 1),
                                                                                      (PW, PH)), 0.55, 1)


def _shift(cov, d):
    if d == (0.0, 0.0):
        return cov
    M = np.float32([[1, 0, d[0]], [0, 1, d[1]]])
    return cv2.warpAffine(cov, M, (PW, PH), flags=cv2.INTER_LINEAR)


def lay_inks(img, covs, seed=10):
    for i, k in enumerate(('yellow', 'cobalt', 'verm', 'navy')):
        if k not in covs:
            continue
        cov = np.clip(_shift(covs[k], SHIFT[k]), 0, 1) * _grain(seed + i * 7)
        col = hexc(INK[k])
        img *= 1 - cov[..., None] * (1 - col)[None, None]
    return img


# ------------------------------------------------------------------ the map panel (cv2, px)
def _map_covs():
    from .shiomi_map import MapData, STAMPS
    D = MapData()
    L = D.L
    x0, y0, x1, y1 = [int(v * SC) for v in MAP_BOX]
    sh = 2

    def Pp(pts):
        q = np.stack([(MAP_BOX[0] + (pts[:, 0] - M0[0]) * MAP_S) * SC, (MAP_BOX[1] + (pts[:, 1] - M0[1]) * MAP_S) * SC], 1)
        return np.round(q * (1 << sh)).astype(np.int32)

    def lines(keys, w, closed=False):
        m = np.zeros((PH, PW), np.uint8)
        for k in keys:
            if L.get(k):
                cv2.polylines(m, [Pp(p) for p in L[k]], closed, 255, max(1, int(round(w))), cv2.LINE_AA, shift=sh)
        return m.astype(np.float32) / 255.0

    def fills(keys):
        m = np.zeros((PH, PW), np.uint8)
        for k in keys:
            if L.get(k):
                cv2.fillPoly(m, [Pp(p) for p in L[k] if len(p) > 2], 255, cv2.LINE_AA, shift=sh)
        return m.astype(np.float32) / 255.0

    inside = np.zeros((PH, PW), np.float32)
    inside[y0:y1, x0:x1] = 1
    # sea: flood from the open water; the data box edge (x < 0) is sea south of the western beach, land above
    bar = np.zeros((PH, PW), np.uint8)
    coast = [p for p in L['coast']]
    w0 = next(p for p in coast if not np.allclose(p[0], p[-1]) and p[0][0] < 0)     # the western beach enters at x < 0
    d = (w0[1] - w0[0]) / np.hypot(*(w0[1] - w0[0]))
    coast.append(np.stack([w0[0] - d * 900.0, w0[0]]).astype(np.float32))           # carry it on beyond the data box
    cv2.polylines(bar, [Pp(p) for p in coast], False, 255, 5, cv2.LINE_8, shift=sh)
    bar[:y0, :] = 255
    bar[y1:, :] = 255
    bar[:, :x0] = 255
    bar[:, x1:] = 255
    ff = bar.copy()
    sx, sy = m2d(2200.0, 2100.0)
    cv2.floodFill(ff, np.zeros((PH + 2, PW + 2), np.uint8), (int(sx * SC), int(sy * SC)), 128)
    sea = ((ff == 128) | ((bar == 255) & (cv2.dilate((ff == 128).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0))).astype(np.uint8)
    isl = fills(['coast']) > 0.5                  # closed coast rings (the island, rocks) are land
    sea[isl] = 0
    sea = sea * inside.astype(np.uint8)
    seaf = sea.astype(np.float32)
    dist = cv2.distanceTransform(sea, cv2.DIST_L2, 5)
    yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
    per = 6.5
    u, v = (xx + yy) / (per * 1.4142), (xx - yy) / (per * 1.4142)
    dd = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    tone = (0.10 + 0.42 * (1 - np.exp(-dist / (220 * SC)))) * seaf
    dots = np.clip((np.sqrt(tone) * 0.62 - dd) * 5.5 + 0.5, 0, 1) * (tone > 0.03)
    hatch = np.zeros_like(seaf)
    for k, d0 in enumerate((4, 9, 15, 22, 30)):
        d0 *= SC
        hatch = np.maximum(hatch, np.clip(1.15 - np.abs(dist - d0) / (0.85 * SC), 0, 1) * (1 - k * 0.13) * seaf)
    del xx, yy, u, v, dd
    rng = np.random.default_rng(7)
    waves = np.zeros((PH, PW), np.uint8)              # old-map wave marks in the open sea
    for _ in range(140):
        wx, wy = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if dist[int(wy), int(wx)] < 60 * SC:
            continue
        s = rng.uniform(9, 14) * SC
        pts = np.array([[wx - s, wy], [wx - s / 2, wy - s * 0.42], [wx, wy], [wx + s / 2, wy - s * 0.42], [wx + s, wy]], np.float32)
        cv2.polylines(waves, [np.round(pts * 4).astype(np.int32)], False, 255, max(1, int(1.6 * SC)), cv2.LINE_AA, shift=2)
    cob_sea = np.clip(dots * 0.9 + hatch + waves.astype(np.float32) / 255.0 * 0.85, 0, 1) * seaf
    land = inside * (1 - seaf)
    # land
    bld = fills(['building'])
    wood = fills(['wood']) * land
    park = fills(['park', 'grass', 'pitch', 'cemetery']) * land
    water = fills(['water', 'pool']) * land
    beach = fills(['beach']) * land
    major = lines(['road_major'], 5.0 * SC)
    major_in = lines(['road_major'], 2.6 * SC)
    minor = lines(['road_minor'], 1.4 * SC)
    small = lines(['road_small', 'path'], 0.9 * SC)
    river = lines(['river'], 3.0 * SC) + lines(['stream'], 1.2 * SC)
    pier = lines(['pier', 'breakwater'], 2.2 * SC)
    bridge = lines(['bridge'], 3.6 * SC)
    rng = np.random.default_rng(11)
    stip = (rng.random((PH, PW)) < 0.09).astype(np.float32)
    stip = cv2.GaussianBlur(stip, (0, 0), 0.7) * 3.0
    cobalt = np.maximum(cob_sea, bld * 0.40 * land)
    cobalt = np.maximum(cobalt, np.clip(major - major_in, 0, 1) * 0.95)
    cobalt = np.maximum(cobalt, minor * 0.85)
    cobalt = np.maximum(cobalt, small * 0.55)
    cobalt = np.maximum(cobalt, wood * 0.20 + park * 0.10)
    cobalt = np.maximum(cobalt, np.clip(water * 0.55 + river, 0, 1))
    yellow = np.clip(major_in * 0.85 + wood * 0.55 + park * 0.40 + np.clip(stip, 0, 1) * beach * 0.9, 0, 1)
    # trees: small cobalt crowns on the woods
    rng = np.random.default_rng(12)
    tr = np.zeros((PH, PW), np.uint8)
    st = int(9 * SC)
    wy, wx = np.nonzero(wood[::st, ::st] > 0.5)
    for yv, xv in zip(wy, wx):
        if rng.random() < 0.55:
            cx, cy = xv * st + rng.uniform(-3, 3) * SC, yv * st + rng.uniform(-3, 3) * SC
            cv2.ellipse(tr, (int(cx * 4), int(cy * 4)), (int(3.2 * SC * 4), int(2.6 * SC * 4)), 0, 180, 360, 255,
                        max(1, int(1.1 * SC)), cv2.LINE_AA, shift=2)
    cobalt = np.maximum(cobalt, tr.astype(np.float32) / 255.0 * 0.9 * land)
    # navy: rail band (ties knocked out), piers, bridges' parapets
    rail = lines(['rail'], 4.2 * SC)
    ties = np.zeros((PH, PW), np.uint8)
    for p in L['rail']:
        q = Pp(p).astype(np.float32) / 4.0
        seg = np.hypot(*np.diff(q, axis=0).T)
        cum = np.concatenate([[0], np.cumsum(seg)])
        s0 = 0.0
        while s0 < cum[-1]:
            ts = np.linspace(s0, min(cum[-1], s0 + 9 * SC), 3)
            pp = np.stack([np.interp(ts, cum, q[:, 0]), np.interp(ts, cum, q[:, 1])], 1)
            cv2.polylines(ties, [np.round(pp * 4).astype(np.int32)], False, 255, max(1, int(2.2 * SC)), cv2.LINE_AA, shift=2)
            s0 += 18 * SC
    navy = np.clip(rail * (1 - ties.astype(np.float32) / 255.0) + pier * 0.9 + np.clip(bridge - lines(['bridge'], 1.6 * SC), 0, 1),
                   0, 1)
    cobalt *= 1 - bridge * 0.8
    yellow *= 1 - bridge
    # the route along real streets, vermilion dashes
    route = np.zeros((PH, PW), np.uint8)
    pts_m = [(s[2], s[3]) for s in sorted(STAMPS)]
    for a_m, b_m in zip(pts_m, pts_m[1:]):
        path = D.path(a_m, b_m)
        q = Pp(path).astype(np.float32) / 4.0
        seg = np.hypot(*np.diff(q, axis=0).T)
        cum = np.concatenate([[0], np.cumsum(seg)])
        s0 = 0.0
        while s0 < cum[-1]:
            ts = np.linspace(s0, min(cum[-1], s0 + 11 * SC), 4)
            pp = np.stack([np.interp(ts, cum, q[:, 0]), np.interp(ts, cum, q[:, 1])], 1)
            cv2.polylines(route, [np.round(pp * 4).astype(np.int32)], False, 255, max(1, int(3.4 * SC)), cv2.LINE_AA, shift=2)
            s0 += 18 * SC
    verm = route.astype(np.float32) / 255.0 * inside
    return {'cobalt': cobalt * inside, 'yellow': yellow * inside, 'navy': navy * inside, 'verm': verm}


# ------------------------------------------------------------------ printed furniture (skia, design units)
def _wave_band(cob, x0, y0, x1, y1, r):
    """seigaiha (blue-wave) band: rows of scales, each clearing what is behind it before stroking its arcs"""
    cob.save()
    cob.clipRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), skia.ClipOp.kIntersect, True)
    y = y0 - r
    row = 0
    while y < y1 + r * 2:
        off = (row % 2) * r
        x = x0 - 2 * r + off
        while x < x1 + 2 * r:
            cob.drawCircle(x, y, r, P(clear=True))
            for rr in (r, r * 0.76, r * 0.52, r * 0.28):
                cob.drawCircle(x, y, rr - r * 0.05, P(1.0, stroke=r * 0.1))
            x += 2 * r
        y += r * 0.5
        row += 1
    cob.restore()


def _tram(nv, cb, ye, vm, x, y, s):
    """line-art single-car tram, front view, at (x, y) top-left, scale s"""
    body = skia.Path()
    body.moveTo(x + 20 * s, y + 40 * s)
    body.quadTo(x + 140 * s, y + 8 * s, x + 260 * s, y + 40 * s)
    body.lineTo(x + 268 * s, y + 170 * s)
    body.lineTo(x + 12 * s, y + 170 * s)
    body.close()
    ye.drawPath(body, P(0.85))
    cb.drawRect(skia.Rect.MakeLTRB(x + 14 * s, y + 112 * s, x + 266 * s, y + 170 * s), P(0.95))
    ye.drawRect(skia.Rect.MakeLTRB(x + 14 * s, y + 112 * s, x + 266 * s, y + 170 * s), P(clear=True))
    nv.drawPath(body, P(1.0, stroke=4.5 * s))
    for k in range(3):
        wr = skia.Rect.MakeXYWH(x + (38 + k * 72) * s, y + 50 * s, 58 * s, 50 * s)
        nv.drawRoundRect(wr, 6 * s, 6 * s, P(1.0, stroke=3.5 * s))
        ye.drawRoundRect(wr, 6 * s, 6 * s, P(clear=True))
        cb.drawRoundRect(skia.Rect.MakeXYWH(x + (42 + k * 72) * s, y + 54 * s, 50 * s, 42 * s), 4 * s, 4 * s, P(0.25))
    nv.drawRect(skia.Rect.MakeXYWH(x + 100 * s, y + 20 * s, 80 * s, 22 * s), P(1.0))
    T(nv, '潮見', x + 140 * s, y + 38 * s, 18 * s, 'mincho', paint=P(clear=True))
    for k in (0, 1):
        hx = x + (52 + k * 176) * s
        vm.drawCircle(hx, y + 138 * s, 11 * s, P(1.0))
        nv.drawCircle(hx, y + 138 * s, 11 * s, P(1.0, stroke=3 * s))
    nv.drawRect(skia.Rect.MakeXYWH(x + 6 * s, y + 166 * s, 268 * s, 14 * s), P(1.0))
    for k in (0, 1):
        nv.drawCircle(x + (70 + k * 140) * s, y + 192 * s, 14 * s, P(1.0, stroke=4 * s))
    pg = skia.Path()
    pg.moveTo(x + 110 * s, y + 24 * s)
    pg.lineTo(x + 140 * s, y - 26 * s)
    pg.lineTo(x + 170 * s, y + 24 * s)
    pg.moveTo(x + 110 * s, y - 26 * s)
    pg.lineTo(x + 170 * s, y - 26 * s)
    nv.drawPath(pg, P(1.0, stroke=3.5 * s))
    nv.drawLine(x - 40 * s, y - 34 * s, x + 330 * s, y - 34 * s, P(1.0, stroke=2.5 * s))


def _sun_emblem(vm, ye, x, y, r):
    ye.drawCircle(x, y, r * 0.55, P(1.0))
    vm.drawCircle(x, y, r * 0.55, P(1.0, stroke=r * 0.08))
    for k in range(16):
        a = k * math.pi / 8
        r1, r2 = r * 0.68, r * (1.0 if k % 2 == 0 else 0.86)
        p = skia.Path()
        p.moveTo(x + math.cos(a - 0.08) * r1, y + math.sin(a - 0.08) * r1)
        p.lineTo(x + math.cos(a) * r2, y + math.sin(a) * r2)
        p.lineTo(x + math.cos(a + 0.08) * r1, y + math.sin(a + 0.08) * r1)
        p.close()
        vm.drawPath(p, P(1.0))


def _furniture():
    """every printed element that is not map: returns {ink: coverage} and the label knockout"""
    nvS, nv = _a8()
    cbS, cb = _a8()
    vmS, vm = _a8()
    yeS, ye = _a8()
    koS, ko = _a8()                    # knockout of cobalt / yellow / vermilion map ink under labels
    # ---- tear-off stub: security pattern, perforation, texts
    cb.save()
    cb.clipRect(skia.Rect.MakeLTRB(70, 70, 280, CH - 70), skia.ClipOp.kIntersect, True)
    for k in range(0, 60):
        p = skia.Path()
        yb = 40 + k * 30
        p.moveTo(60, yb)
        for j in range(12):
            p.quadTo(60 + j * 20 + 10, yb + (8 if j % 2 == 0 else -8), 60 + (j + 1) * 20, yb)
        cb.drawPath(p, P(0.35, stroke=1.4))
    cb.restore()
    for y in range(78, CH - 70, 24):
        nv.drawCircle(300, y, 5.5, P(1.0))
    nv.drawRect(skia.Rect.MakeLTRB(84, 120, 266, 196), P(1.0))
    T(nv, '潮見線', 175, 178, 52, 'old', paint=P(clear=True))
    TV(nv, '夏休み乗車記念', 175, 300, 74, 'mincho', lead=1.06)
    T(nv, 'No.', 175, 1210, 40, 'garamond')
    T(vm, '0716', 175, 1286, 66, 'garamond', tracking=0.06)
    nv.drawLine(100, 1320, 250, 1320, P(1.0, stroke=2))
    T(nv, '大人・小人', 175, 1380, 30, 'mincho_sb')
    vm.drawCircle(175, 1530, 66, P(1.0, stroke=6))
    vm.drawCircle(175, 1530, 54, P(1.0, stroke=2))
    T(vm, '検', 175, 1556, 64, 'old')
    T(nv, '昭和60年', 175, 1660, 30, 'mincho_sb')
    # ---- border: navy rule, seigaiha band, thin navy rule; vermilion corner knots
    bx0, by0, bx1, by1 = 340, 56, CW - 56, CH - 56
    nv.drawRect(skia.Rect.MakeLTRB(bx0, by0, bx1, by1), P(1.0, stroke=9))
    band = 30
    _wave_band(cb, bx0 + 7, by0 + 7, bx1 - 7, by0 + 7 + band, 13)
    _wave_band(cb, bx0 + 7, by1 - 7 - band, bx1 - 7, by1 - 7, 13)
    _wave_band(cb, bx0 + 7, by0 + 7, bx0 + 7 + band, by1 - 7, 13)
    _wave_band(cb, bx1 - 7 - band, by0 + 7, bx1 - 7, by1 - 7, 13)
    ix0, iy0, ix1, iy1 = bx0 + 7 + band + 6, by0 + 7 + band + 6, bx1 - 7 - band - 6, by1 - 7 - band - 6
    nv.drawRect(skia.Rect.MakeLTRB(ix0, iy0, ix1, iy1), P(1.0, stroke=3))
    for (x, y) in ((bx0 + 22, by0 + 22), (bx1 - 22, by0 + 22), (bx0 + 22, by1 - 22), (bx1 - 22, by1 - 22)):
        cb.drawCircle(x, y, 26, P(clear=True))
        vm.drawCircle(x, y, 18, P(1.0))
        vm.drawCircle(x, y, 24, P(1.0, stroke=3))
        T(vm, '潮', x, y + 8, 22, 'old', paint=P(clear=True))
    # ---- header
    T(nv, '潮見線', 640, 290, 168, 'old', tracking=0.04)
    T(nv, '夏休み', 1150, 214, 76, 'mincho', align='left', tracking=0.08)
    T(nv, 'スタンプラリー', 1150, 316, 104, 'mincho', align='left', tracking=0.04)
    T(vm, 'SHIOMI LINE  ·  SUMMER STAMP RALLY  ·  1985', 1150, 372, 34, 'garamond', align='left', tracking=0.30)
    _sun_emblem(vm, ye, 2085, 250, 92)
    T(nv, '夏', 2085, 278, 74, 'old')
    _tram(nv, cb, ye, vm, 2420, 190, 0.96)
    T(nv, '六つの印を集めて、灯台の朝日を見に行こう。', 3050, 404, 30, 'mincho_sb', align='right')
    nv.drawLine(420, 414, 1560, 414, P(1.0, stroke=5))
    cb.drawLine(420, 426, 1560, 426, P(1.0, stroke=2))
    # ---- map panel: frame, labels, pins, compass, scale, credit
    x0, y0, x1, y1 = MAP_BOX
    nv.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), P(1.0, stroke=5))
    nv.drawRect(skia.Rect.MakeLTRB(x0 - 10, y0 - 10, x1 + 10, y1 + 10), P(1.0, stroke=1.6))
    labels = [('潮　見　湾', 1900, 1640, 64, 'old'), ('SHIOMI  BAY', 1900, 1730, 24, 'garamond'),
              ('汐見島', 760, 2075, 44, 'old'), ('潮見町', 1300, 420, 52, 'mincho'), ('浜　町', 2350, 470, 46, 'mincho'),
              ('灯明山', 1960, 395, 30, 'mincho_sb'), ('七里の浜', 2520, 1230, 32, 'mincho_sb'), ('潮見漁港', 400, 1330, 26, 'mincho_sb'),
              ('潮見川', 745, 700, 24, 'mincho_sb'), ('相 模 灘', 40, 1120, 34, 'old')]
    for s, xm, ym, size, fn in labels:
        x, y = m2d(xm, ym)
        T(ko, s, x, y, size, fn, paint=P(1.0, stroke=size * 0.34))
        T(ko, s, x, y, size, fn)
        T(nv, s, x, y, size, fn)
    for nm, xm, ym, dx, dy in (('潮見', 1049, 548, -70, -6), ('浜町', 1563, 842, 0, 46), ('高校前', 2245, 1026, 0, -34)):
        x, y = m2d(xm, ym)
        nv.drawRect(skia.Rect.MakeXYWH(x - 9, y - 6, 18, 12), P(1.0))
        w = tw(nm, 'mincho', 24)
        r = skia.Rect.MakeXYWH(x + dx - w / 2 - 8, y + dy - 22, w + 16, 30)
        ko.drawRect(r, P(1.0))
        nv.drawRect(r, P(1.0))
        T(nv, nm, x + dx, y + dy, 24, 'mincho', paint=P(clear=True))
    lx, ly = m2d(225, 1796)
    ko.drawCircle(lx, ly, 20, P(1.0))
    for k in range(8):
        a = k * math.pi / 4
        nv.drawLine(lx + math.cos(a) * 8, ly + math.sin(a) * 8, lx + math.cos(a) * 17, ly + math.sin(a) * 17, P(1.0, stroke=2.4))
    nv.drawCircle(lx, ly, 6, P(1.0))
    from .shiomi_map import STAMPS
    for n, _, xm, ym in STAMPS:
        x, y = m2d(xm, ym)
        ko.drawCircle(x, y, 27, P(1.0))
        vm.drawCircle(x, y, 22, P(1.0))
        vm.drawCircle(x, y, 26, P(1.0, stroke=2))
        T(vm, NUM[n - 1], x, y + 9, 26, 'old', paint=P(clear=True))
    ox, oy = x1 - 92, y0 + 104
    ko.drawCircle(ox, oy, 74, P(1.0))
    nv.drawCircle(ox, oy, 56, P(1.0, stroke=2.5))
    nv.drawCircle(ox, oy, 48, P(1.0, stroke=1))
    for k in range(4):
        a = k * math.pi / 2 - math.pi / 2
        p = skia.Path()
        p.moveTo(ox + math.cos(a) * 66, oy + math.sin(a) * 66)
        p.lineTo(ox + math.cos(a + 0.5) * 14, oy + math.sin(a + 0.5) * 14)
        p.lineTo(ox, oy)
        p.close()
        (vm if k == 0 else nv).drawPath(p, P(1.0))
        p2 = skia.Path()
        p2.moveTo(ox + math.cos(a) * 66, oy + math.sin(a) * 66)
        p2.lineTo(ox + math.cos(a - 0.5) * 14, oy + math.sin(a - 0.5) * 14)
        p2.lineTo(ox, oy)
        p2.close()
        nv.drawPath(p2, P(1.0, stroke=1.6))
    T(nv, '北', ox, oy - 78, 26, 'mincho')
    sx0, sy0 = x0 + 40, y1 - 52
    L500 = 500 * MAP_S
    ko.drawRect(skia.Rect.MakeXYWH(sx0 - 14, sy0 - 40, L500 + 70, 66), P(1.0))
    for k in range(5):
        r = skia.Rect.MakeXYWH(sx0 + k * L500 / 5, sy0, L500 / 5, 9)
        nv.drawRect(r, P(1.0) if k % 2 == 0 else P(1.0, stroke=1.6))
    for k, lab in ((0, '0'), (5, '500m')):
        T(nv, lab, sx0 + k * L500 / 5, sy0 - 8, 18, 'garamond')
    cw_ = tw('© OpenStreetMap contributors (ODbL)', 'garamond', 16)
    ko.drawRect(skia.Rect.MakeXYWH(x1 - cw_ - 120, y1 - 36, cw_ + 112, 28), P(1.0))
    T(nv, '© OpenStreetMap contributors (ODbL)', x1 - 14, y1 - 15, 16, 'garamond', align='right')
    T(nv, '地図データ', x1 - cw_ - 22, y1 - 15, 15, 'mincho_sb', align='right')
    # ---- stamp cells
    gx0, gy0, gx1, gy1 = 2210, 440, 3090, 1490
    nv.drawRect(skia.Rect.MakeLTRB(gx0, gy0, gx1, gy1), P(1.0, stroke=5))
    nv.drawLine((gx0 + gx1) / 2, gy0, (gx0 + gx1) / 2, gy1, P(1.0, stroke=1.6))
    for k in (1, 2):
        nv.drawLine(gx0, gy0 + k * 350, gx1, gy0 + k * 350, P(1.0, stroke=1.6))
    for i, (x, y) in enumerate(CELL_C):
        cp = P(1.0, stroke=3.2)
        cp.setPathEffect(skia.DashPathEffect.Make([14, 10], 0))
        cb.drawCircle(x, y, R0, cp)
        cb.drawCircle(x, y, R0 - 12, P(0.6, stroke=1.2))
        if i < 5:
            T(cb, 'スタンプ', x, y + 10, 28, 'mincho_sb', paint=P(0.16))
        lab = LABELS[i]
        w = tw(lab, 'mincho', 34)
        r = skia.Rect.MakeXYWH(x - w / 2 - 20, y + R0 - 22, w + 40, 46)
        cb.drawRect(r, P(clear=True))
        nv.drawRect(r, P(1.0))
        T(nv, lab, x, y + R0 + 13, 34, 'mincho', paint=P(clear=True))
        bx, by = x - R0 * 0.80, y - R0 * 0.80
        cb.drawCircle(bx, by, 30, P(clear=True))
        vm.drawCircle(bx, by, 25, P(1.0))
        T(vm, NUM[i], bx, by + 11, 30, 'old', paint=P(clear=True))
    x6, y6 = CELL_C[5]
    hy = y6 + R0 * 0.32
    cb.save()
    clip = skia.Path()
    clip.addCircle(x6, y6, R0 - 16)
    cb.clipPath(clip, skia.ClipOp.kIntersect, True)
    for k in range(5):
        cb.drawLine(x6 - R0, hy + 12 + k * 15, x6 + R0, hy + 12 + k * 15, P(0.85, stroke=4.2 - k * 0.5))
    cb.restore()
    nv.drawLine(x6 - R0 + 18, hy, x6 + R0 - 18, hy, P(1.0, stroke=3))
    # ---- footer: name box, rules, organiser
    fy = 1530
    nv.drawRect(skia.Rect.MakeXYWH(420, fy, 760, 140), P(1.0, stroke=3))
    T(nv, 'なまえ', 446, fy + 52, 34, 'mincho', align='left')
    nv.drawLine(446, fy + 112, 1150, fy + 112, P(1.0, stroke=1.4))
    T(nv, 'ねん　　くみ', 1150, fy + 52, 28, 'mincho_sb', align='right')
    T(vm, '◎', 1230, fy + 42, 30, 'mincho', align='left')
    T(nv, '六つのスタンプを集めて潮見駅の窓口へお持ちください。記念品をさしあげます。', 1274, fy + 42, 30, 'mincho_sb', align='left')
    T(vm, '◎', 1230, fy + 92, 30, 'mincho', align='left')
    T(nv, '期間　昭和六十年七月二十日（土）〜八月三十一日（土）', 1274, fy + 92, 30, 'mincho_sb', align='left')
    T(nv, '主催　潮見観光協会・潮見線', 3070, fy + 138, 26, 'mincho_sb', align='right')
    covs = {'navy': _cov(nvS), 'cobalt': _cov(cbS), 'verm': _cov(vmS), 'yellow': _cov(yeS)}
    return covs, _cov(koS)


@functools.lru_cache(maxsize=1)
def base_layer():
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f'base_v2_{PW}.png')
    if os.path.exists(path):
        b = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        return cv2.cvtColor(b, cv2.COLOR_BGR2RGB).astype(np.float32) * (1 / 255.0)
    mc = _map_covs()
    fc, ko = _furniture()
    covs = {}
    for k in ('yellow', 'cobalt', 'verm', 'navy'):
        m = mc.get(k, 0) * ((1 - ko) if k != 'navy' else 1.0)
        covs[k] = np.clip(1 - (1 - m) * (1 - fc[k]), 0, 1)
    img = np.clip(lay_inks(paper().copy(), covs), 0, 1)
    cv2.imwrite(path, cv2.cvtColor((img * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
    return img


# ------------------------------------------------------------------ stamps
def _art_src(i):
    shot, kf, cx, cy, r = ART[i]
    p = os.path.join(ROOT, 'work', 'B2', shot, f'kf_{kf}.png')
    return (p, cx, cy, r) if os.path.exists(p) else None


def engrave(img, cx, cy, r, out=520, sigma=1.3, k=1.6, tau=0.98, eps=-0.015, phi=70, smooth=8, solid_t=-0.13,
            hatch_t=-0.05, per=7.0, ang=45):
    """a keyframe region -> engraved line art (1 = ink): XDoG lines, local-contrast solids and 45-degree hatching"""
    pad = cv2.copyMakeBorder(img, 2 * r, 2 * r, 2 * r, 2 * r, cv2.BORDER_REFLECT)
    x0, y0 = int(cx - r) + 2 * r, int(cy - r) + 2 * r
    crop = cv2.resize(pad[y0:y0 + 2 * r, x0:x0 + 2 * r], (out, out), interpolation=cv2.INTER_AREA)
    flat = cv2.pyrMeanShiftFiltering(crop, smooth, 28)
    g = cv2.createCLAHE(2.0, (4, 4)).apply(cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY)).astype(np.float32) / 255.0
    D = cv2.GaussianBlur(g, (0, 0), sigma) - tau * cv2.GaussianBlur(g, (0, 0), sigma * k)
    E = np.where(D >= eps, 1.0, 1.0 + np.tanh(phi * (D - eps)))
    lines = (1 - np.clip(E, 0, 1)) > 0.5
    rel = cv2.GaussianBlur(g, (0, 0), 1.2) - cv2.GaussianBlur(g, (0, 0), out / 18)
    yy, xx = np.mgrid[0:out, 0:out].astype(np.float32)
    a = math.radians(ang)
    ph = ((xx * math.cos(a) + yy * math.sin(a)) / per) % 1.0
    hatch = (rel < hatch_t) & (np.abs(ph - 0.5) < 0.18 + 0.15 * np.clip((hatch_t - rel) / (hatch_t - solid_t), 0, 1))
    ink = (lines | (rel < solid_t) | hatch).astype(np.uint8)
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= 14
    return keep[lab].astype(np.float32)


@functools.lru_cache(maxsize=8)
def stamp_art(i):
    src = _art_src(i)
    if src is None:
        return None
    p, cx, cy, r = src
    key = os.path.join(CACHE, f'art_{i}_{os.path.basename(os.path.dirname(p))}_{int(os.path.getmtime(p))}.png')
    if os.path.exists(key):
        return cv2.imread(key, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
    art = engrave(cv2.imread(p), cx, cy, r)
    os.makedirs(CACHE, exist_ok=True)
    cv2.imwrite(key, (art * 255).astype(np.uint8))
    return art


def _icon(c, i, s):
    """vector fallback for a stamp whose keyframe is not generated yet (centred at 0, 0)"""
    thin = P(1.0, stroke=s * 0.07)
    if i == 1:      # pool: lanes and a diving board
        c.drawRect(skia.Rect.MakeXYWH(-s * 0.8, -s * 0.45, s * 1.6, s * 0.9), thin)
        for k in range(1, 4):
            yy = -s * 0.45 + k * s * 0.9 / 4
            for xx in np.linspace(-s * 0.7, s * 0.7, 9):
                c.drawCircle(float(xx), float(yy), s * 0.04, P(1.0))
    elif i == 3:    # vending machine
        c.drawRect(skia.Rect.MakeXYWH(-s * 0.35, -s * 0.7, s * 0.7, s * 1.1), thin)
        for k in range(3):
            c.drawRect(skia.Rect.MakeXYWH(-s * 0.27 + k * s * 0.19, -s * 0.58, s * 0.14, s * 0.26), thin)
        c.drawRect(skia.Rect.MakeXYWH(-s * 0.22, s * 0.12, s * 0.44, s * 0.1), P(1.0))
    elif i == 4:    # festival lantern
        c.drawOval(skia.Rect.MakeXYWH(-s * 0.35, -s * 0.55, s * 0.7, s * 1.0), P(1.0, stroke=s * 0.09))
        for k in range(-2, 3):
            c.drawLine(-s * 0.33 * math.cos(k * 0.45), -s * 0.05 + k * s * 0.18, s * 0.33 * math.cos(k * 0.45),
                       -s * 0.05 + k * s * 0.18, thin)
        T(c, '祭', 0, s * 0.1, s * 0.4, 'old')
    else:           # lighthouse
        p = skia.Path()
        p.moveTo(-s * 0.18, s * 0.7)
        p.lineTo(-s * 0.1, -s * 0.35)
        p.lineTo(s * 0.1, -s * 0.35)
        p.lineTo(s * 0.18, s * 0.7)
        c.drawPath(p, thin)
        c.drawRect(skia.Rect.MakeXYWH(-s * 0.13, -s * 0.56, s * 0.26, s * 0.21), P(1.0))


def _rubber(cov, seed, angle):
    """rubber stamp texture on a coverage patch: speckled voids, uneven pressure, ink spread"""
    h, w = cov.shape
    rng = np.random.default_rng(seed)
    fine = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 0.9)
    fine /= fine.std() + 1e-6
    blot = cv2.resize(cv2.GaussianBlur(rng.standard_normal((h // 16 + 2, w // 16 + 2)).astype(np.float32), (0, 0), 1.2), (w, h))
    blot /= blot.std() + 1e-6
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = math.radians(angle)
    grad = ((xx - w / 2) * math.cos(a) + (yy - h / 2) * math.sin(a)) / (w / 2)
    press = np.clip(0.86 + 0.10 * blot - 0.16 * grad, 0.35, 1.0)
    voids = np.clip((fine - 1.55) * 1.5, 0, 1)
    spread = cv2.GaussianBlur(cov, (0, 0), 0.7)
    return np.clip(spread * 1.25 - 0.12, 0, 1) * press * (1 - voids * 0.9)


STAMP_R = R0 * 0.93


@functools.lru_cache(maxsize=8)
def stamp_patch(i):
    """(coverage patch, x0, y0) in px for stamp i, pressed slightly off-centre and turned"""
    x, y = CELL_C[i]
    rot = [-7.0, 5.0, -3.0, 8.0, -5.0, 3.0][i]
    off = [(6, -4), (-5, 3), (4, 5), (-3, -6), (5, 2), (0, 0)][i]
    r = STAMP_R
    half = int((r + 14) * SC)
    pw = 2 * half
    info = skia.ImageInfo.Make(pw, pw, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType)
    surf = skia.Surface.MakeRaster(info)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    c.translate(half, half)
    c.scale(SC, SC)
    c.rotate(rot)
    c.drawCircle(0, 0, r * 0.97, P(1.0, stroke=r * 0.075))
    c.drawCircle(0, 0, r * 0.72, P(1.0, stroke=r * 0.03))
    top, *rest = STAMP_RING[i].split(' ')
    ring_text(c, top, 0, 0, r * 0.845, r * 0.155, 'old', mid=-90)
    ring_text(c, (rest[0] if rest else '') + '　' + DATES[i], 0, 0, r * 0.845, r * 0.12, 'mincho', mid=90, bottom=True)
    for a in (180.0, 0.0):
        ar = math.radians(a)
        c.drawCircle(math.cos(ar) * r * 0.845, math.sin(ar) * r * 0.845, r * 0.035, P(1.0))
    art = stamp_art(i)
    ri = r * 0.68
    if art is not None:
        n = art.shape[0]
        rgba = np.zeros((n, n, 4), np.uint8)
        yy, xx = np.mgrid[0:n, 0:n]
        circ = ((xx - n / 2) ** 2 + (yy - n / 2) ** 2) < (n / 2 - 2) ** 2
        rgba[..., 3] = (art * circ * 255).astype(np.uint8)
        rgba[..., :3] = rgba[..., 3:4]
        im = skia.Image.fromarray(rgba, colorType=skia.ColorType.kRGBA_8888_ColorType)
        c.drawImageRect(im, skia.Rect.MakeXYWH(-ri, -ri, 2 * ri, 2 * ri), skia.SamplingOptions(skia.FilterMode.kLinear))
    else:
        _icon(c, i, ri)
    cov = np.empty((pw, pw), np.uint8)
    surf.readPixels(info, cov, pw)
    cov = _rubber(cov.astype(np.float32) / 255.0, 30 + i, rot * 7 + 40)
    return cov, int((x + off[0]) * SC) - half, int((y + off[1]) * SC) - half


def _press(img, cov, x0, y0, col=STAMP_INK, k=1.0):
    h, w = cov.shape
    roi = img[y0:y0 + h, x0:x0 + w]
    roi *= 1 - (cov * k)[..., None] * (1 - hexc(col))[None, None]
    return img


# ------------------------------------------------------------------ the sixth circle: the sun
def _sun_patch(sun_k, ray_rot):
    """the paper-cut sun rising behind the printed horizon of the sixth cell: RGB multiply patch.
    Yellow disc with an orange halftone rim, twelve tapered orange rays; clipped to the cell above the horizon."""
    x6, y6 = CELL_C[5]
    half = int((R0 + 4) * SC)
    pw = 2 * half
    hy = R0 * 0.32
    cy = hy + R0 * 0.62 - R0 * 1.05 * sun_k
    info = skia.ImageInfo.Make(pw, pw, skia.ColorType.kAlpha_8_ColorType, skia.AlphaType.kPremul_AlphaType)

    def layer(draw):
        surf = skia.Surface.MakeRaster(info)
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 0))
        c.translate(half, half)
        c.scale(SC, SC)
        clip = skia.Path()
        clip.addCircle(0, 0, R0 - 16)
        c.clipPath(clip, skia.ClipOp.kIntersect, True)
        c.clipRect(skia.Rect.MakeLTRB(-R0, -R0, R0, hy), skia.ClipOp.kIntersect, True)
        draw(c)
        a = np.empty((pw, pw), np.uint8)
        surf.readPixels(info, a, pw)
        return a.astype(np.float32) / 255.0

    def rays(c):
        for k in range(12):
            a = math.radians(k * 30 + ray_rot)
            p = skia.Path()
            r1, r2 = R0 * 0.52, R0 * (0.86 if k % 2 == 0 else 0.74)
            p.moveTo(math.cos(a - 0.11) * r1, cy + math.sin(a - 0.11) * r1)
            p.lineTo(math.cos(a) * r2, cy + math.sin(a) * r2)
            p.lineTo(math.cos(a + 0.11) * r1, cy + math.sin(a + 0.11) * r1)
            p.close()
            c.drawPath(p, P(1.0))
    yel = layer(lambda c: c.drawCircle(0, cy, R0 * 0.44, P(1.0)))
    org = layer(rays)
    ring = layer(lambda c: c.drawCircle(0, cy, R0 * 0.44, P(1.0, stroke=R0 * 0.05)))
    # halftone shading on the disc: denser orange dots toward the lower rim
    ys, xs = np.mgrid[0:pw, 0:pw].astype(np.float32)
    Y = (ys - half) / SC
    tone = np.clip((Y - cy + R0 * 0.1) / (R0 * 0.5), 0, 1) * 0.45
    per = 7.0
    u, v = (xs + ys) / (per * 1.4142), (xs - ys) / (per * 1.4142)
    dd = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    dots = np.clip((np.sqrt(tone) * 0.66 - dd) * 6 + 0.5, 0, 1) * (tone > 0.02) * yel
    mul = np.ones((pw, pw, 3), np.float32)
    for m, col in ((yel, '#F7D36A'), (np.clip(org + ring + dots, 0, 1), ORANGE)):
        mul *= 1 - m[..., None] * (1 - hexc(col))[None, None]
    return mul, int(x6 * SC) - half, int(y6 * SC) - half


def _glow(img, glow_k):
    """halftone sun glow round the sixth cell (yellow screen), strength glow_k"""
    x6, y6 = CELL_C[5]
    half = int(R0 * 3.2 * SC)
    x0, y0 = max(0, int(x6 * SC) - half), max(0, int(y6 * SC) - half)
    x1, y1 = min(PW, int(x6 * SC) + half), min(PH, int(y6 * SC) + half)
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.sqrt((xs - x6 * SC) ** 2 + (ys - y6 * SC) ** 2) / SC
    tone = np.clip(0.85 * np.exp(-(d / (R0 * (1.2 + 1.6 * glow_k))) ** 2) * glow_k, 0, 1)
    per = 9.0
    u, v = (xs + ys) / (per * 1.4142), (xs - ys) / (per * 1.4142)
    dd = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    m = np.clip((np.sqrt(tone) * 0.66 - dd) * 6 + 0.5, 0, 1) * (tone > 0.02)
    roi = img[y0:y1, x0:x1]
    roi *= 1 - m[..., None] * (1 - hexc('#F5C842'))[None, None]
    return img


def render_card(stamp_k=(1, 1, 1, 1, 1), sun_k=0.0, glow_k=0.0, footer_n=0, footer="YOU KNOW THAT I'M NEVER GONNA LOSE",
                sixth_stamp=0.0, ray_rot=0.0):
    img = base_layer().copy()
    for i, k in enumerate(stamp_k):
        if k > 0:
            cov, x0, y0 = stamp_patch(i)
            _press(img, cov, x0, y0, k=min(1.0, k))
    if sun_k > 0:
        mul, x0, y0 = _sun_patch(sun_k, ray_rot)
        h, w = mul.shape[:2]
        img[y0:y0 + h, x0:x0 + w] *= mul
    if glow_k > 0:
        _glow(img, glow_k)
    if sixth_stamp > 0:
        cov, x0, y0 = stamp_patch(5)
        _press(img, cov, x0, y0, k=min(1.0, sixth_stamp))
    if footer_n > 0:
        surf, c = _a8()
        T(c, footer[:footer_n], 1640, 1712, 30, 'garamond', tracking=0.3)
        img *= 1 - _cov(surf)[..., None] * (1 - hexc(NAVY))[None, None]
    return img


def view(card, cx, cy, zoom, rot=0.0, out=(1920, 1080)):
    """camera over the card: centre (cx, cy) in design units, zoom 1 = the card's width fills the frame.
    Crops the visible region, area-resamples it (no moire on the screens), then rotates."""
    W, H = out
    s = W / CW * zoom / SC                          # output px per card px
    rad = math.hypot(W, H) / 2 / s + 8
    pcx, pcy = cx * SC, cy * SC
    x0, y0 = int(math.floor(pcx - rad)), int(math.floor(pcy - rad))
    x1, y1 = int(math.ceil(pcx + rad)), int(math.ceil(pcy + rad))
    pad = [max(0, -x0), max(0, -y0), max(0, x1 - PW), max(0, y1 - PH)]
    crop = card[max(0, y0):min(PH, y1), max(0, x0):min(PW, x1)]
    if any(pad):
        crop = cv2.copyMakeBorder(crop, pad[1], pad[3], pad[0], pad[2], cv2.BORDER_REPLICATE)
    cw_, ch_ = crop.shape[1], crop.shape[0]
    tw_, th_ = max(1, int(round(cw_ * s))), max(1, int(round(ch_ * s)))
    small = cv2.resize(crop, (tw_, th_), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    ccx, ccy = (pcx - x0) * tw_ / cw_, (pcy - y0) * th_ / ch_
    M = cv2.getRotationMatrix2D((ccx, ccy), rot, 1.0)
    M[0, 2] += W / 2 - ccx
    M[1, 2] += H / 2 - ccy
    return cv2.warpAffine(small, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

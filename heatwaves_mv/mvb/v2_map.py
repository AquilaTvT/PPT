"""MV-B v2: the two map shots, on the printed Shiomi sheet (real OpenStreetMap streets, mvb/shiomi_map.py).

  chorus2-03  82.16-85.13   night sheet, straight down: the town is a maze. The print turns a quarter on every
                            beat, the streets ripple like water, and he is a small light going round and round a
                            real block, a fading trail behind him; the curve mirrors on the corners catch a flash
                            of noon on the off-beats.
  chorus4-01  147.35-150.31 the sheet before dawn (blue hour over the dawn print): a headlight slides along the real
                            coast railway, the stamp route lights up like a fuse from the station to the lighthouse,
                            and place names pop up one by one on the sung syllables.
"""
import functools
import math

import cv2
import numpy as np

from mv.core import clamp
from mv.timing import BEAT, BEAT0
from .print_fx import hexc as H

W, H_ = 1920, 1080
_YS, _XS = np.mgrid[0:H_, 0:W].astype(np.float32)


def ease_io(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x, s=1.6):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


@functools.lru_cache(maxsize=2)
def sheet(v):
    from .shiomi_map import MapSheet
    sh = MapSheet(v)
    sh.master
    return sh


@functools.lru_cache(maxsize=8)
def mip(v, L):
    m = sheet(v).master
    for _ in range(L):
        m = cv2.pyrDown(m)
    return m


@functools.lru_cache(maxsize=1)
def data():
    from .shiomi_map import MapData
    return MapData()


def view(v, cam, dof=True, table='#0E0B12'):
    """MapSheet.view with a mip level chosen from the on-screen scale (no aliasing on the screens when far)"""
    sh = sheet(v)
    Hm = sh.homography(cam)
    inv = np.linalg.inv(Hm)

    def mp(x, y):
        q = inv @ np.array([x, y, 1.0])
        return q[:2] / q[2]
    spp = float(np.hypot(*(mp(W / 2 + 1, H_ * 0.4) - mp(W / 2, H_ * 0.4))))      # master px per screen px
    L = int(max(0, min(3, math.floor(math.log2(max(spp, 1e-6)) + 0.15))))
    HL = Hm @ np.diag([2.0 ** L, 2.0 ** L, 1.0])
    out = cv2.warpPerspective(mip(v, L), HL, (W, H_), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                              borderValue=tuple(int(c * 255) for c in H(table)))
    img = out.astype(np.float32) * (1 / 255.0)
    if dof and cam.get('tilt', 0) > 3:
        ys = np.arange(H_, dtype=np.float32)
        k = np.clip(np.abs(ys - cam.get('focus_y', H_ * 0.55)) / (H_ * 0.5), 0, 1) ** 1.4 * cam.get('dof', 1.0)
        b1 = cv2.GaussianBlur(img, (0, 0), 2.2)
        b2 = cv2.GaussianBlur(img, (0, 0), 5.5)
        a1 = np.clip(k * 2, 0, 1)[:, None, None]
        a2 = np.clip(k * 2 - 1, 0, 1)[:, None, None]
        img = img * (1 - a1) + b1 * a1
        img = img * (1 - a2) + b2 * a2
    return img


def project(v, cam, pts):
    return sheet(v).project(cam, np.atleast_2d(np.asarray(pts, np.float32)))


def arclen(P):
    seg = np.hypot(*np.diff(P, axis=0).T)
    return np.concatenate([[0.0], np.cumsum(seg)])


def at(P, cum, s):
    s = float(np.clip(s, 0, cum[-1]))
    return np.array([np.interp(s, cum, P[:, 0]), np.interp(s, cum, P[:, 1])], np.float32)


def glow_line(img, pts, col, width, alpha=1.0, glow=0.0, glow_col=None):
    if len(pts) < 2:
        return img
    m = np.zeros((H_, W), np.float32)
    cv2.polylines(m, [np.round(np.asarray(pts) * 4).astype(np.int32)], False, 1.0, max(1, int(round(width))), cv2.LINE_AA, shift=2)
    if glow > 0:
        g = cv2.GaussianBlur(m, (0, 0), width * 3.0) * glow
        img += H(glow_col or col)[None, None] * g[..., None]
    img += (H(col)[None, None] - img) * (m * alpha)[..., None]
    return img


def glow_dot(img, x, y, r, core='#FFF1C8', halo='#F08A3C', amt=1.0):
    m = np.zeros((H_, W), np.float32)
    cv2.circle(m, (int(x * 4), int(y * 4)), int(r * 4), 1.0, -1, cv2.LINE_AA, shift=2)
    g = cv2.GaussianBlur(m, (0, 0), r * 3.2) * 2.2 + cv2.GaussianBlur(m, (0, 0), r * 9) * 1.4
    img += H(halo)[None, None] * (g * amt)[..., None]
    img += (H(core)[None, None] - img) * (m * amt)[..., None]
    return img


# ------------------------------------------------------------------ chorus2-03: the maze at night
C203_LOOP = [(1395, 640), (1612, 606), (1655, 800), (1420, 832)]
C203_MIRRORS = [(1395, 640), (1612, 606), (1655, 800), (1420, 832), (1520, 720), (1300, 760)]


@functools.lru_cache(maxsize=1)
def c203_loop():
    D = data()
    parts = []
    for a, b in zip(C203_LOOP, C203_LOOP[1:] + C203_LOOP[:1]):
        p = D.path(a, b)
        parts.append(p if not parts else p[1:])
    P = np.concatenate(parts).astype(np.float32)
    return P, arclen(P)


def chorus2_03(s, t, local, fi):
    P, cum = c203_loop()
    L = cum[-1]
    d = s['end'] - s['start']
    speed = 1.35 * L / d
    pos = lambda tt: at(P, cum, (max(0.0, tt - s['start']) * speed) % L)
    me = pos(t)
    # a quarter turn on each beat (overshooting a little), on top of a slow drift
    b0 = math.floor((s['start'] - BEAT0) / BEAT + 0.5)
    rot = -12.0 + 5.0 * local
    for k in range(1, 5):
        tb = BEAT0 + (b0 + k) * BEAT
        if t >= tb:
            rot += 90.0 * back_out(clamp((t - tb) / 0.2))
    cx, cy = 1520 + (me[0] - 1520) * 0.25, 722 + (me[1] - 722) * 0.25
    cam = dict(cx=cx, cy=cy, rot=rot, dist=720 + 160 * local / d, tilt=0.0)
    img = view('night', cam, dof=False)
    # streets ripple like water
    dx = (3.2 * np.sin(_YS / 55.0 + t * 3.1) + 1.4 * np.sin(_XS / 23.0 - t * 5.2)).astype(np.float32)
    dy = (3.2 * np.cos(_XS / 66.0 + t * 2.6) + 1.2 * np.cos(_YS / 29.0 + t * 4.4)).astype(np.float32)
    img = cv2.remap(img, _XS + dx, _YS + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # curve mirrors on the corners: orange discs that flash noon on the off-beats
    nb = (t - BEAT0) / BEAT
    ob = (nb - math.floor(nb) - 0.5) * BEAT
    mk = project('night', cam, C203_MIRRORS)
    for j, (x, y) in enumerate(mk):
        m = np.zeros((H_, W), np.float32)
        cv2.circle(m, (int(x * 4), int(y * 4)), 9 * 4, 1.0, -1, cv2.LINE_AA, shift=2)
        ring = np.zeros((H_, W), np.float32)
        cv2.circle(ring, (int(x * 4), int(y * 4)), 9 * 4, 1.0, 3, cv2.LINE_AA, shift=2)
        img += (H('#F08A3C')[None, None] - img) * (m * 0.9)[..., None]
        img += (H('#1A1110')[None, None] - img) * ring[..., None]
        if 0 <= ob < 4 / 24 and (j + int(nb)) % 2 == 0:
            k = 1 - ob / (4 / 24)
            img = glow_dot(img, x, y, 7, core='#FFF6D8', halo='#F5C842', amt=k)
    # his light: a trail through the last second, then the dot
    ts = np.linspace(max(s['start'], t - 1.0), t, 26)
    tr = project('night', cam, [pos(tt) for tt in ts])
    for j in range(1, len(tr)):
        a = j / len(tr)
        img = glow_line(img, tr[j - 1:j + 1], '#F5C842', 4.0, alpha=0.7 * a, glow=0.45 * a, glow_col='#F08A3C')
    x, y = project('night', cam, [me])[0]
    pulse = 0.85 + 0.15 * math.sin(t * 9.0)
    img = glow_dot(img, x, y, 9.5, amt=pulse)
    # the print is a little darker at the edges: night
    v = np.clip(1.0 - 0.55 * (((_XS - W / 2) / W) ** 2 + ((_YS - H_ / 2) / H_) ** 2) * 2.2, 0.55, 1)
    return img * v[..., None]


# ------------------------------------------------------------------ chorus4-01: before dawn, the route lights up
C401_LABELS = [('潮見駅', 1046, 548), ('浜町', 1563, 842), ('高校前', 2245, 1026), ('七里の浜', 2900, 1150), ('潮見湾', 2050, 1600),
               ('潮見漁港', 420, 1180), ('汐見島', 520, 1980), ('灯台', 225, 1796), ('潮見町', 1250, 450), ('夏祭り', 1290, 810)]


@functools.lru_cache(maxsize=1)
def rail_path():
    """the coast railway as one polyline, 汐ヶ浜 (east) -> 潮見 station, by the same snapped graph as the streets"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    from scipy.spatial import cKDTree
    D = data()
    verts, rows, cols, w = [], [], [], []
    n = 0
    for line in D.L['rail']:
        seg = [line[0]]
        for a, b in zip(line[:-1], line[1:]):
            m = max(1, int(np.ceil(np.hypot(*(b - a)) / 6.0)))
            seg += [a + (b - a) * (j / m) for j in range(1, m + 1)]
        seg = np.asarray(seg, np.float32)
        idx = np.arange(n, n + len(seg))
        rows += list(idx[:-1])
        cols += list(idx[1:])
        w += list(np.hypot(*np.diff(seg, axis=0).T) + 1e-3)
        verts.append(seg)
        n += len(seg)
    V = np.concatenate(verts)
    tree = cKDTree(V)
    pr = tree.query_pairs(5.0, output_type='ndarray')
    rows += list(pr[:, 0])
    cols += list(pr[:, 1])
    w += list(np.hypot(*(V[pr[:, 0]] - V[pr[:, 1]]).T) + 0.5)
    G = coo_matrix((np.array(w + w), (np.array(rows + cols), np.array(cols + rows))), shape=(n, n)).tocsr()
    s_, t_ = int(tree.query([3099, 1074])[1]), int(tree.query([1049, 548])[1])
    _, pred = dijkstra(G, indices=s_, return_predecessors=True)
    out = [t_]
    while out[-1] != s_ and pred[out[-1]] >= 0:
        out.append(int(pred[out[-1]]))
    P = V[np.array(out[::-1])]
    return P, arclen(P)


@functools.lru_cache(maxsize=1)
def route_path():
    from .shiomi_map import STAMPS
    D = data()
    pts = [(st[2], st[3]) for st in sorted(STAMPS)]
    parts = []
    for a, b in zip(pts, pts[1:]):
        p = D.path(a, b)
        parts.append(p if not parts else p[1:])
    P = np.concatenate(parts).astype(np.float32)
    return P, arclen(P)


def _label_plate(img, x, y, txt, k):
    """a navy plate with cream type that pops (overshoot) at screen (x, y), with a vermilion tick to the place"""
    from mv import text
    import skia
    if k <= 0:
        return img
    sc = back_out(clamp(k), 2.2)
    size = 34 * sc
    if size < 2:
        return img
    tw_ = text.font('mincho', size).measureText(txt)
    bw, bh = tw_ + 26 * sc, 50 * sc
    bx, by = x - bw / 2, y - 64 * sc - bh
    surf = skia.Surface(W, H_)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    p = skia.Paint(AntiAlias=True, Color=skia.Color4f(*H('#1E2550'), 1.0))
    c.drawRect(skia.Rect.MakeXYWH(bx, by, bw, bh), p)
    p2 = skia.Paint(AntiAlias=True, Color=skia.Color4f(*H('#D9402B'), 1.0), StrokeWidth=3.0 * sc, Style=skia.Paint.kStroke_Style)
    c.drawLine(x, y - 64 * sc, x, y - 8 * sc, p2)
    c.drawCircle(x, y, 6 * sc, skia.Paint(AntiAlias=True, Color=skia.Color4f(*H('#D9402B'), 1.0)))
    f = text.font('mincho', size)
    c.drawString(txt, bx + 13 * sc, by + bh * 0.74, f, skia.Paint(AntiAlias=True, Color=skia.Color4f(*H('#EDE3CF'), 1.0)))
    arr = np.empty((H_, W, 4), np.uint8)
    surf.readPixels(skia.ImageInfo.Make(W, H_, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kUnpremul_AlphaType), arr, W * 4)
    a = arr[..., 3:4].astype(np.float32) / 255.0 * min(1.0, k * 3)
    return img * (1 - a) + arr[..., :3].astype(np.float32) / 255.0 * a


def chorus4_01(s, t, local, fi):
    from .recipes import _map_gt
    d = s['end'] - s['start']
    k = ease_io(clamp(local / d))
    A = dict(cx=2050, cy=1000, rot=-6, dist=3100, tilt=36, focus_y=620)
    B = dict(cx=930, cy=1330, rot=-15, dist=1650, tilt=44, focus_y=600)
    cam = {key: A[key] + (B[key] - A[key]) * k for key in A}
    cam['dist'] = math.exp(math.log(A['dist']) + (math.log(B['dist']) - math.log(A['dist'])) * k)
    img = view('dawn', cam)
    # blue hour over the dawn print; the east (right) begins to warm through the shot
    xs, ys = _XS / W, _YS / H_
    warm = np.clip((xs - 0.55) * 1.6 + (local / d) * 0.9 - 0.45 - ys * 0.3, 0, 1)[..., None]
    blue = np.array([0.46, 0.56, 0.88], np.float32)
    dawn = np.array([1.02, 0.86, 0.72], np.float32)
    img = img * (blue * (1 - warm) + dawn * warm) + np.array([0.02, 0.03, 0.07], np.float32) * (1 - warm)
    # the route lights up like a fuse, station -> lighthouse
    P, cum = route_path()
    prog = clamp((local - 0.2) / (d - 0.45))
    n = max(2, int(np.searchsorted(cum, prog * cum[-1])) + 1)
    lit = project('dawn', cam, P[:n])
    img = glow_line(img, lit, '#E8553A', 3.2, alpha=0.95, glow=0.55, glow_col='#F08A3C')
    if prog < 1:
        hx, hy = project('dawn', cam, [at(P, cum, prog * cum[-1])])[0]
        img = glow_dot(img, hx, hy, 5.0, core='#FFF6D8', halo='#F5A040', amt=1.0)
    # the headlight on the coast railway, east -> station
    R, rc = rail_path()
    rp = clamp(local / (d - 0.1))
    me = at(R, rc, rp * rc[-1])
    ahead = at(R, rc, min(rc[-1], rp * rc[-1] + 60))
    (x, y), (ax, ay) = project('dawn', cam, [me, ahead])
    ang = math.atan2(ay - y, ax - x)
    beam = np.zeros((H_, W), np.float32)
    L_ = 150.0
    tri = np.float32([[x, y], [x + math.cos(ang - 0.28) * L_, y + math.sin(ang - 0.28) * L_],
                      [x + math.cos(ang + 0.28) * L_, y + math.sin(ang + 0.28) * L_]])
    cv2.fillPoly(beam, [np.round(tri * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
    beam = cv2.GaussianBlur(beam, (0, 0), 14) * 0.55
    img += H('#FFE3A8')[None, None] * beam[..., None]
    img = glow_dot(img, x, y, 5.5, core='#FFFBEA', halo='#FFD27A', amt=1.0)
    # place names pop up on the sung syllables
    gt = _map_gt(50)
    for i, (txt, xm, ym) in enumerate(C401_LABELS[:len(gt)]):
        kk = (t - gt[i]) / 0.22
        if kk > 0:
            px, py = project('dawn', cam, [(xm, ym)])[0]
            if -100 < px < W + 100 and -50 < py < H_ + 120:
                img = _label_plate(img, px, py, txt, kk)
    return img


GRAPHIC = {'B-chorus2-03': chorus2_03, 'B-chorus4-01': chorus4_01}

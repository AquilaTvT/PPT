"""The Shiomi Line route map: a printed 1985 tourist map drawn from real OpenStreetMap data (the Enoden coast,
Koshigoe - Shichirigahama - Enoshima), relabelled with the film's fictional names.

  sheet = MapSheet('dawn')            # or 'night'
  img = sheet.view(t, cam)            # 1920x1080 float RGB: the sheet lying on a table, perspective + depth of field
  xy = sheet.project(cam, (x_m, y_m)) # screen position of a map point (metres) for overlays

The master sheet is rendered once per variant at 1.8 px/m (cached in work/B2/map/) with: coastal hatching and a
depth screen on the sea, every real building footprint, roads with casings, the railway as the classic dashed
band, wood / park tints with tree symbols, beach stipple, piers and breakwaters, landmark symbols, labels in
mincho, a neat-line frame with graticule ticks, title cartouche, legend, scale bar and compass rose.
Map data (c) OpenStreetMap contributors, ODbL 1.0.
"""
import gzip
import heapq
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'design', 'mv_b', 'map', 'shiomi_osm.json.gz')
CACHE = os.path.join(ROOT, 'work', 'B2', 'map')
FONT_DIR = os.path.join(ROOT, 'assets', 'fonts')
W, H = 1920, 1080
S = 1.8                      # master px per metre
MARGIN = 420                 # paper margin around the neat line (px)


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def font(name, size):
    files = {'title': 'ShipporiMincho-ExtraBold.ttf', 'label': 'ShipporiMincho-SemiBold.ttf', 'small': 'ShipporiMincho-Regular.ttf',
             'old': 'ZenOldMincho-Black.ttf', 'kaku': 'ZenKakuGothicNew-Medium.ttf', 'garamond': 'EBGaramond[wght].ttf'}
    return ImageFont.truetype(os.path.join(FONT_DIR, files[name]), int(size))


# fictional names for real places (metres from the top-left of the data box: x east, y south)
NAMES = {
    'stations': {'江ノ島': '潮見', '腰越': '浜町', '鎌倉高校前': '高校前', '七里ヶ浜': '汐ヶ浜', '稲村ヶ崎': '稲穂崎', '湘南海岸公園': '松原'},
    'labels': [  # (text, x_m, y_m, size, vertical, kind)
        ('潮 見 湾', 2150, 1720, 120, False, 'sea'),
        ('汐見島', 360, 1720, 64, False, 'island'),
        ('潮見漁港', 1200, 1160, 40, False, 'port'),
        ('潮見川', 600, 780, 38, True, 'river'),
        ('潮見町', 1250, 450, 92, False, 'town'),
        ('浜町', 2350, 560, 70, False, 'town'),
        ('汐ヶ浜', 3250, 820, 70, False, 'town'),
        ('灯明山', 2050, 140, 48, False, 'hill'),
        ('潮見商店街', 1000, 820, 34, False, 'street'),
        ('七里の浜', 3000, 1180, 44, False, 'beach'),
    ],
}
# the stamp rally route: (stamp no., title, x_m, y_m)
STAMPS = [(1, '潮見駅', 1046, 548), (2, 'プール', 2410, 600), (3, 'カーブミラー', 2010, 760), (4, '自動販売機', 2700, 1020),
          (5, '夏祭り', 1290, 810), (6, '灯台・日の出', 340, 1810)]


class MapData:
    def __init__(self):
        d = json.load(gzip.open(DATA, 'rt'))
        self.meta = d['meta']
        self.L = {k: [np.asarray(p, np.float32) / 10.0 for p in v] for k, v in d['layers'].items()}
        self.pois = [dict(p, xy=np.asarray(p['xy'], np.float32) / 10.0) for p in d['pois']]
        self.size = self.meta['size_m']

    # road graph for routes (nodes = shared vertices, metres)
    def graph(self):
        if hasattr(self, '_g'):
            return self._g
        adj = {}
        def key(p):
            return (round(float(p[0]), 1), round(float(p[1]), 1))
        for k in ('road_major', 'road_minor', 'road_small', 'path', 'steps', 'bridge'):
            for line in self.L[k]:
                for a, b in zip(line[:-1], line[1:]):
                    ka, kb = key(a), key(b)
                    w = float(np.hypot(*(b - a)))
                    adj.setdefault(ka, []).append((kb, w))
                    adj.setdefault(kb, []).append((ka, w))
        self._g = adj
        return adj

    def nearest_node(self, x, y):
        g = self.graph()
        ks = np.array(list(g.keys()), np.float32)
        i = int(np.argmin((ks[:, 0] - x) ** 2 + (ks[:, 1] - y) ** 2))
        return tuple(float(v) for v in ks[i])

    def path(self, a, b):
        """shortest street path between two points (metres) -> polyline (N, 2)"""
        g = self.graph()
        s, t = self.nearest_node(*a), self.nearest_node(*b)
        dist, prev = {s: 0.0}, {}
        q = [(0.0, s)]
        while q:
            d, u = heapq.heappop(q)
            if u == t:
                break
            if d > dist.get(u, 1e18):
                continue
            for v, w in g.get(u, ()):
                nd = d + w
                if nd < dist.get(v, 1e18):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(q, (nd, v))
        out = [t]
        while out[-1] != s and out[-1] in prev:
            out.append(prev[out[-1]])
        return np.array(out[::-1], np.float32)


VARIANTS = {
    # paper, land, sea (deep, shore), ink, building fill, building line, road fill, road major, casing, rail light,
    # wood, park, beach, label, accent (route / stamps), window lights
    'dawn': dict(paper='#E9DEC6', land='#E9DEC6', sea='#2C4C9A', shore='#5E86C8', ink='#1A1416', bfill='#C9805F',
                 bline='#5A2E22', road='#F6F0E2', major='#F5C842', casing='#3A2A26', rail_w='#F6F0E2', wood='#7E9F83',
                 park='#A8C09A', beach='#E7C98F', label='#1A1416', accent='#D9402B', light=None, gold='#B58A3A'),
    'night': dict(paper='#141A33', land='#1B2244', sea='#0B1026', shore='#22305E', ink='#0A0C18', bfill='#262E58',
                  bline='#C9A45A', road='#0F1430', major='#2A2F55', casing='#C9A45A', rail_w='#E9DEC6', wood='#1D2D3F',
                  park='#22344A', beach='#3A3550', label='#E9DEC6', accent='#F08A3C', light='#F5C842', gold='#C9A45A'),
}


class MapSheet:
    def __init__(self, variant='dawn'):
        self.v = variant
        self.c = {k: (hexc(v) if isinstance(v, str) else v) for k, v in VARIANTS[variant].items()}
        self.data = MapData()
        wm, hm = self.data.size
        self.mw, self.mh = int(wm * S), int(hm * S)
        self.Wt, self.Ht = self.mw + 2 * MARGIN, self.mh + 2 * MARGIN
        os.makedirs(CACHE, exist_ok=True)
        self.path_png = os.path.join(CACHE, f'sheet_{variant}_v4.png')
        self._master = None

    # metres -> master pixel
    def m2p(self, xy):
        xy = np.asarray(xy, np.float32)
        return xy * S + MARGIN

    @property
    def master(self):
        if self._master is None:
            if os.path.exists(self.path_png):
                self._master = cv2.cvtColor(cv2.imread(self.path_png), cv2.COLOR_BGR2RGB)
            else:
                self._master = self.render()
                cv2.imwrite(self.path_png, cv2.cvtColor(self._master, cv2.COLOR_RGB2BGR))
        return self._master

    # ------------------------------------------------------------------ master sheet
    def render(self):
        c = self.c
        Wt, Ht = self.Wt, self.Ht
        img = np.empty((Ht, Wt, 3), np.float32)
        img[:] = c['paper']
        L = self.data.L
        sh = 2                                       # cv2 subpixel shift (x4)
        P = lambda pts: np.round(self.m2p(pts) * 4).astype(np.int32)

        def fill(mask_polys, col, alpha=1.0, outline=None, ow=1):
            m = np.zeros((Ht, Wt), np.uint8)
            cv2.fillPoly(m, mask_polys, 255, cv2.LINE_AA, shift=sh)
            a = m.astype(np.float32)[..., None] / 255.0 * alpha
            np.multiply(img, 1 - a, out=img)
            img[:] += col * a
            if outline is not None:
                lm = np.zeros((Ht, Wt), np.uint8)
                cv2.polylines(lm, mask_polys, True, 255, ow, cv2.LINE_AA, shift=sh)
                la = lm.astype(np.float32)[..., None] / 255.0
                np.multiply(img, 1 - la, out=img)
                img[:] += outline * la
            return m

        def stroke(lines, col, w, closed=False, alpha=1.0):
            m = np.zeros((Ht, Wt), np.uint8)
            cv2.polylines(m, lines, closed, 255, max(1, int(round(w))), cv2.LINE_AA, shift=sh)
            a = m.astype(np.float32)[..., None] / 255.0 * alpha
            np.multiply(img, 1 - a, out=img)
            img[:] += col * a
            return m

        # --- land / sea ---------------------------------------------------------------------------------
        mx0, my0 = MARGIN, MARGIN
        coast = np.zeros((Ht, Wt), np.uint8)
        cv2.polylines(coast, [P(p) for p in L['coast']], False, 255, 6, cv2.LINE_8, shift=sh)
        ff = coast.copy()
        ff[:my0, :] = 255                            # the neat line is a barrier: the fill must not leak round the
        ff[my0 + self.mh:, :] = 255                  # ends of the coastline through the paper margin
        ff[:, :mx0] = 255
        ff[:, mx0 + self.mw:] = 255
        cv2.floodFill(ff, np.zeros((Ht + 2, Wt + 2), np.uint8), (mx0 + self.mw - 8, my0 + self.mh - 8), 128)
        sea = (ff == 128).astype(np.uint8)
        sea[:my0, :] = 0
        sea[my0 + self.mh:, :] = 0
        sea[:, :mx0] = 0
        sea[:, mx0 + self.mw:] = 0
        sea = cv2.dilate(sea, np.ones((5, 5), np.uint8))
        inside = np.zeros((Ht, Wt), np.uint8)
        inside[my0:my0 + self.mh, mx0:mx0 + self.mw] = 1
        sea &= inside
        land = inside & (1 - sea)
        img[land.astype(bool)] = c['land']
        # sea: shore tint -> deep, with coastal hatching (iso-distance lines) and a depth dot screen
        dist = cv2.distanceTransform((1 - sea).astype(np.uint8) ^ 1, cv2.DIST_L2, 5) if False else \
            cv2.distanceTransform(sea, cv2.DIST_L2, 5)
        depth = np.clip(dist / (420 * S / 1.8), 0, 1)
        seacol = c['shore'][None, None] + (c['sea'] - c['shore'])[None, None] * (depth[..., None] ** 0.6)
        sm = sea.astype(bool)
        img[sm] = seacol[sm]
        hatch = np.zeros((Ht, Wt), np.float32)
        for k, dd in enumerate((7, 16, 27, 40, 56, 75, 98)):
            band = np.clip(1.0 - np.abs(dist - dd * S / 1.8) / 1.1, 0, 1) * (1.0 - k / 9.0)
            hatch = np.maximum(hatch, band)
        lc = c['paper'] if self.v == 'night' else hexc('#E9DEC6')
        hatch *= sm
        img += (lc - img) * (hatch[..., None] * (0.55 if self.v == 'dawn' else 0.35))
        yy, xx = np.mgrid[0:Ht, 0:Wt].astype(np.float32)
        cs, sn = math.cos(math.radians(45)), math.sin(math.radians(45))
        per = 9.0
        u = (xx * cs + yy * sn) / per
        v = (-xx * sn + yy * cs) / per
        dd_ = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
        del u, v
        tone = (0.12 + 0.30 * depth) * sm
        dots = np.clip((np.sqrt(tone) * 0.62 - dd_) * per * 0.8 + 0.5, 0, 1) * (tone > 0.02)
        dark = c['sea'] * 0.62 + c['ink'] * 0.38
        img += (dark - img) * dots[..., None] * 0.55
        del dots, tone, depth
        # --- green areas, beach --------------------------------------------------------------------------
        woodm = fill([P(p) for p in L['wood'] if len(p) > 2], c['wood'], 0.85)
        parkm = fill([P(p) for p in L['park'] + L['grass'] if len(p) > 2], c['park'], 0.75)
        fill([P(p) for p in L['cemetery'] if len(p) > 2], c['park'], 0.6)
        beachm = fill([P(p) for p in L['beach'] if len(p) > 2], c['beach'], 0.9)
        # beach stipple, tree symbols on wood (deterministic)
        rng = np.random.default_rng(7)
        if beachm.any():
            ys, xs = np.nonzero(beachm[::6, ::6])
            sel = rng.random(len(ys)) < 0.35
            for y, x in zip(ys[sel] * 6, xs[sel] * 6):
                cv2.circle(img, (int(x), int(y)), 1, tuple(float(v) for v in (c['ink'] * 0.6 + c['beach'] * 0.4)), -1, cv2.LINE_AA)
        tm = (woodm > 0).astype(np.uint8)
        tm = cv2.erode(tm, np.ones((9, 9), np.uint8))
        ys, xs = np.nonzero(tm[::26, ::26])
        tc = tuple(float(v) for v in (c['wood'] * 0.45 + c['ink'] * 0.55))
        for y, x in zip(ys * 26, xs * 26):
            x2, y2 = int(x + rng.uniform(-6, 6)), int(y + rng.uniform(-6, 6))
            cv2.circle(img, (x2, y2), 5, tc, 1, cv2.LINE_AA)                       # broadleaf symbol
            cv2.line(img, (x2, y2 + 5), (x2, y2 + 9), tc, 1, cv2.LINE_AA)
        # --- water bodies, rivers, streams -----------------------------------------------------------------
        fill([P(p) for p in L['water'] if len(p) > 2], c['shore'], 1.0)
        stroke([P(p) for p in L['river']], c['shore'], 14 * S / 1.8)
        stroke([P(p) for p in L['stream']], c['shore'], 3)
        # --- piers, breakwaters, platforms -----------------------------------------------------------------
        for p in L['pier'] + L['breakwater']:
            closed = len(p) > 2 and np.hypot(*(p[0] - p[-1])) < 1.0
            if closed:
                fill([P(p)], c['land'], 1.0, outline=c['ink'] if self.v == 'dawn' else c['gold'], ow=2)
            else:
                stroke([P(p)], c['ink'] if self.v == 'dawn' else c['gold'], 9)
                stroke([P(p)], c['land'], 5)
        # --- roads (casing then fill) ----------------------------------------------------------------------
        cas = c['casing']
        for k, wf in (('path', 2.2), ('steps', 2.2), ('road_small', 5.0), ('road_minor', 8.5), ('road_major', 16.0)):
            lines = [P(p) for p in L[k]]
            if k in ('path', 'steps'):
                stroke(lines, cas, 2, alpha=0.75)
                continue
            stroke(lines, cas, wf * S / 1.8 + 3)
        for k, wf, col in (('road_small', 5.0, c['road']), ('road_minor', 8.5, c['road']), ('road_major', 16.0, c['major'])):
            stroke([P(p) for p in L[k]], col, wf * S / 1.8)
        # --- buildings ------------------------------------------------------------------------------------
        polys = [P(p) for p in L['building'] if len(p) > 2]
        fill(polys, c['bfill'], 1.0, outline=c['bline'], ow=1)
        if self.c['light'] is not None:                               # night: lit windows
            lit = self.c['light']
            for p in L['building']:
                if len(p) < 3:
                    continue
                q = self.m2p(p)
                x0, y0 = q.min(0)
                x1, y1 = q.max(0)
                area = (x1 - x0) * (y1 - y0)
                n = int(rng.poisson(min(4.0, area / 900.0)))
                for _ in range(n):
                    if rng.random() < 0.55:
                        continue
                    wx, wy = rng.uniform(x0 + 3, max(x0 + 4, x1 - 3)), rng.uniform(y0 + 3, max(y0 + 4, y1 - 3))
                    if cv2.pointPolygonTest(q.astype(np.float32), (float(wx), float(wy)), False) > 0:
                        col = lit if rng.random() < 0.8 else hexc('#F08A3C')
                        cv2.rectangle(img, (int(wx) - 2, int(wy) - 1), (int(wx) + 2, int(wy) + 1), tuple(float(v) for v in col), -1)
        # school grounds / pools / pitches
        fill([P(p) for p in L['pitch'] if len(p) > 2], c['park'], 0.8, outline=c['bline'], ow=1)
        poolc = hexc('#5EA9D6') if self.v == 'dawn' else hexc('#2C6E9A')
        for p in L['pool']:
            if len(p) < 3:
                continue
            fill([P(p)], poolc, 1.0, outline=c['ink'] if self.v == 'dawn' else c['gold'], ow=1)
        # --- railways -------------------------------------------------------------------------------------
        other = [P(p) for p in L['rail_other']]
        stroke(other, c['ink'] if self.v == 'dawn' else c['gold'], 4)
        rails = [P(p) for p in L['rail']]
        stroke(rails, c['ink'] if self.v == 'dawn' else c['gold'], 15)
        stroke(rails, c['rail_w'] if self.v == 'night' else hexc('#F6F0E2'), 9)
        # dashes (the band): alternate ink every 26 px along each line
        dashm = np.zeros((Ht, Wt), np.uint8)
        for p in L['rail']:
            q = self.m2p(p)
            seg = np.hypot(*np.diff(q, axis=0).T)
            cum = np.concatenate([[0], np.cumsum(seg)])
            total = cum[-1]
            s0 = 0.0
            while s0 < total:
                s1 = min(total, s0 + 26)
                ts = np.linspace(s0, s1, 6)
                pts = np.stack([np.interp(ts, cum, q[:, 0]), np.interp(ts, cum, q[:, 1])], 1)
                cv2.polylines(dashm, [np.round(pts * 4).astype(np.int32)], False, 255, 9, cv2.LINE_AA, shift=sh)
                s0 += 52
        a = dashm.astype(np.float32)[..., None] / 255.0
        dcol = c['ink'] if self.v == 'dawn' else hexc('#0A0C18')
        img[:] = img * (1 - a) + dcol * a
        img[~inside.astype(bool)] = c['paper']                      # print stops at the neat line
        self._labels_and_furniture(img)
        return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

    # ------------------------------------------------------------------ labels, symbols, frame
    def _labels_and_furniture(self, img):
        c = self.c
        pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        dr = ImageDraw.Draw(pil)
        lab = tuple(int(v * 255) for v in c['label'])
        halo = tuple(int(v * 255) for v in c['paper'])
        accent = tuple(int(v * 255) for v in c['accent'])
        gold = tuple(int(v * 255) for v in c['gold'])
        ink = tuple(int(v * 255) for v in (c['ink'] if self.v == 'dawn' else c['gold']))

        def text(s, x, y, size, fnt='label', fill=lab, stroke=halo, sw=None, anchor='mm', vertical=False, spacing=1.0):
            f = font(fnt, size)
            sw = int(max(2, size * 0.09)) if sw is None else sw
            if vertical:
                for i, ch in enumerate(s):
                    dr.text((x, y + i * size * spacing), ch, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)
            else:
                dr.text((x, y), s, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)

        # landmark symbols
        def sym_lighthouse(x, y, r):
            dr.ellipse([x - r, y - r, x + r, y + r], outline=ink, width=3)
            dr.ellipse([x - r * 0.35, y - r * 0.35, x + r * 0.35, y + r * 0.35], fill=ink)
            for k in range(8):
                a = k * math.pi / 4
                dr.line([x + math.cos(a) * r * 1.25, y + math.sin(a) * r * 1.25, x + math.cos(a) * r * 1.9, y + math.sin(a) * r * 1.9], fill=ink, width=3)

        def sym_torii(x, y, r):
            dr.line([x - r, y - r * 0.55, x + r, y - r * 0.55], fill=ink, width=4)
            dr.line([x - r * 0.8, y - r * 0.2, x + r * 0.8, y - r * 0.2], fill=ink, width=3)
            dr.line([x - r * 0.55, y - r * 0.55, x - r * 0.65, y + r * 0.8], fill=ink, width=3)
            dr.line([x + r * 0.55, y - r * 0.55, x + r * 0.65, y + r * 0.8], fill=ink, width=3)

        def sym_school(x, y, r):
            f = font('kaku', r * 1.6)
            dr.text((x, y), '文', font=f, fill=ink, anchor='mm', stroke_width=2, stroke_fill=halo)

        def sym_anchor(x, y, r):
            dr.line([x, y - r, x, y + r], fill=ink, width=3)
            dr.line([x - r * 0.5, y - r * 0.55, x + r * 0.5, y - r * 0.55], fill=ink, width=3)
            dr.arc([x - r, y - r * 0.2, x + r, y + r * 1.1], 20, 160, fill=ink, width=3)
            dr.ellipse([x - r * 0.18, y - r * 1.25, x + r * 0.18, y - r * 0.9], outline=ink, width=2)

        D = self.data
        for p in D.pois:
            x, y = self.m2p(p['xy'])
            if p['kind'] == 'lighthouse' and ('シーキャンドル' in p['name'] or 'Eno Shima' in p['name'] or p['name'] == ''):
                sym_lighthouse(x, y, 13)
            elif p['kind'] == 'shrine':
                sym_torii(x, y, 14)
        for p in D.L['school']:
            if len(p) > 2:
                x, y = self.m2p(p.mean(0))
                sym_school(x, y, 15)
        hx, hy = self.m2p((1215, 1105))
        sym_anchor(hx, hy, 18)
        # stations: name plates on the line
        for p in D.pois:
            if p['kind'] != 'station':
                continue
            nm = NAMES['stations'].get(p['name'])
            if not nm:
                continue
            x, y = self.m2p(p['xy'])
            dr.rectangle([x - 14, y - 9, x + 14, y + 9], fill=halo, outline=ink, width=3)
            f = font('label', 40)
            tw = dr.textlength(nm, font=f)
            bx, by = x + 26, y - 74
            dr.rectangle([bx - 10, by - 28, bx + tw + 10, by + 28], fill=halo, outline=ink, width=3)
            dr.text((bx, by), nm, font=f, fill=lab, anchor='lm')
            dr.line([x, y - 9, bx - 10, by + 20], fill=ink, width=2)
        # place labels
        for s, xm, ym, size, vert, kind in NAMES['labels']:
            x, y = self.m2p((xm, ym))
            if kind == 'sea':
                text(s, x, y, size, 'old', fill=tuple(int(v * 255) for v in (c['paper'] if self.v == 'dawn' else c['gold'])),
                     stroke=tuple(int(v * 255) for v in c['sea']), sw=0)
            else:
                text(s, x, y, size, 'title' if kind in ('town', 'island') else 'label', vertical=vert)
        # stamp rally route markers (numbered circles) -- the route line itself is drawn per frame
        for n, title, xm, ym in STAMPS:
            x, y = self.m2p((xm, ym))
            dr.ellipse([x - 30, y - 30, x + 30, y + 30], outline=accent, width=6)
            dr.text((x, y + 2), '①②③④⑤⑥'[n - 1], font=font('title', 46), fill=accent, anchor='mm')
            text(title, x + 44, y - 4, 32, 'label', anchor='lm')
        # --- frame: neat line, graticule ticks, cartouche, legend, scale, compass -------------------------
        x0, y0, x1, y1 = MARGIN, MARGIN, MARGIN + self.mw, MARGIN + self.mh
        for off, wdt in ((0, 6), (-22, 2), (-34, 10)):
            dr.rectangle([x0 + off, y0 + off, x1 - off, y1 - off], outline=ink, width=wdt)
        for k in range(0, 41):
            tx = x0 + (x1 - x0) * k / 40
            dr.line([tx, y0 - 34, tx, y0 - 22], fill=ink, width=2)
            dr.line([tx, y1 + 22, tx, y1 + 34], fill=ink, width=2)
        for k in range(0, 25):
            ty = y0 + (y1 - y0) * k / 24
            dr.line([x0 - 34, ty, x0 - 22, ty], fill=ink, width=2)
            dr.line([x1 + 22, ty, x1 + 34, ty], fill=ink, width=2)
        # title cartouche (top left, over the land)
        cx0, cy0 = x0 + 120, y0 + 110
        dr.rectangle([cx0, cy0, cx0 + 1240, cy0 + 360], fill=halo, outline=ink, width=6)
        dr.rectangle([cx0 + 16, cy0 + 16, cx0 + 1224, cy0 + 344], outline=ink, width=2)
        dr.text((cx0 + 620, cy0 + 120), '潮見線沿線案内図', font=font('old', 132), fill=lab, anchor='mm')
        dr.text((cx0 + 620, cy0 + 238), '夏のスタンプラリー　六つの印を集めよう', font=font('label', 50), fill=accent, anchor='mm')
        dr.text((cx0 + 620, cy0 + 306), '昭和六十年七月　潮見観光協会 発行', font=font('small', 34), fill=lab, anchor='mm')
        # legend (bottom right, over the sea)
        lx0, ly0 = x1 - 760, y1 - 560
        dr.rectangle([lx0, ly0, lx0 + 640, ly0 + 440], fill=halo, outline=ink, width=4)
        dr.text((lx0 + 320, ly0 + 46), '凡　例', font=font('title', 46), fill=lab, anchor='mm')
        rows = [('rail', '潮見線（電車）'), ('major', '主要道路'), ('road', '道路'), ('bld', '建物'), ('stamp', 'スタンプ設置所'), ('lh', '灯台')]
        for i, (k, s) in enumerate(rows):
            yy = ly0 + 110 + i * 54
            if k == 'rail':
                dr.rectangle([lx0 + 40, yy - 8, lx0 + 200, yy + 8], fill=halo, outline=ink, width=3)
                for j in range(3):
                    dr.rectangle([lx0 + 40 + j * 56, yy - 6, lx0 + 68 + j * 56, yy + 6], fill=ink)
            elif k == 'major':
                dr.rectangle([lx0 + 40, yy - 9, lx0 + 200, yy + 9], fill=tuple(int(v * 255) for v in c['major']), outline=ink, width=3)
            elif k == 'road':
                dr.rectangle([lx0 + 40, yy - 6, lx0 + 200, yy + 6], fill=tuple(int(v * 255) for v in c['road']), outline=ink, width=3)
            elif k == 'bld':
                dr.rectangle([lx0 + 90, yy - 14, lx0 + 150, yy + 14], fill=tuple(int(v * 255) for v in c['bfill']),
                             outline=tuple(int(v * 255) for v in c['bline']), width=2)
            elif k == 'stamp':
                dr.ellipse([lx0 + 98, yy - 20, lx0 + 142, yy + 20], outline=accent, width=5)
            elif k == 'lh':
                sym_lighthouse(lx0 + 120, yy, 11)
            dr.text((lx0 + 240, yy), s, font=font('label', 36), fill=lab, anchor='lm')
        # scale bar
        sx0, sy0 = x0 + 140, y1 - 150
        m500 = 500 * S
        for k in range(5):
            dr.rectangle([sx0 + k * m500 / 5, sy0, sx0 + (k + 1) * m500 / 5, sy0 + 18], fill=ink if k % 2 == 0 else halo, outline=ink, width=2)
        for k, s in ((0, '0'), (2.5, '250'), (5, '500m')):
            dr.text((sx0 + k * m500 / 5, sy0 - 26), s, font=font('small', 30), fill=lab, anchor='mm')
        # compass rose
        ox, oy, r = x1 - 300, y0 + 300, 150
        dr.ellipse([ox - r, oy - r, ox + r, oy + r], outline=ink, width=3)
        dr.ellipse([ox - r * 0.86, oy - r * 0.86, ox + r * 0.86, oy + r * 0.86], outline=ink, width=1)
        for k in range(32):
            a = k * math.pi / 16
            l = 0.12 if k % 4 else 0.22
            dr.line([ox + math.cos(a) * r * (0.86 - l), oy + math.sin(a) * r * (0.86 - l), ox + math.cos(a) * r * 0.86, oy + math.sin(a) * r * 0.86], fill=ink, width=2)
        for k in range(4):
            a = k * math.pi / 2 - math.pi / 2
            tip = (ox + math.cos(a) * r * 1.0, oy + math.sin(a) * r * 1.0)
            lft = (ox + math.cos(a + 0.5 * math.pi) * r * 0.16, oy + math.sin(a + 0.5 * math.pi) * r * 0.16)
            rgt = (ox + math.cos(a - 0.5 * math.pi) * r * 0.16, oy + math.sin(a - 0.5 * math.pi) * r * 0.16)
            dr.polygon([tip, lft, (ox, oy)], fill=ink if k == 0 else halo, outline=ink)
            dr.polygon([tip, rgt, (ox, oy)], fill=accent if k == 0 else ink, outline=ink)
        dr.text((ox, oy - r - 44), '北', font=font('title', 54), fill=lab, anchor='mm')
        # imprint line + attribution in the margin
        dr.text((x0, y1 + 90), '潮見観光協会 印刷　地図データ © OpenStreetMap contributors', font=font('small', 30), fill=lab, anchor='lm')
        dr.text((x1, y1 + 90), '縮尺 約 一万分の一', font=font('small', 30), fill=lab, anchor='rm')
        img[:] = np.asarray(pil, np.float32) / 255.0

    # ------------------------------------------------------------------ camera
    def homography(self, cam):
        """cam: dict(cx, cy [metres], rot [deg, map rotation on screen], dist [metres of sheet across the frame width],
        tilt [deg from straight down], fov=40) -> 3x3 mapping master px -> screen px"""
        cx, cy = self.m2p((cam['cx'], cam['cy']))
        rot = math.radians(cam.get('rot', 0.0))
        tilt = math.radians(cam.get('tilt', 0.0))
        span = cam['dist'] * S                         # master px visible across the frame (at the centre)
        f = W / 2 / math.tan(math.radians(cam.get('fov', 40) / 2))
        Z = f * span / W                               # camera height (master px units) so the centre spans `span`
        # camera looks at (cx, cy); orbit: tilt toward +y of the rotated frame
        R = np.array([[math.cos(rot), -math.sin(rot), 0], [math.sin(rot), math.cos(rot), 0], [0, 0, 1]])
        T = np.array([[1, 0, 0], [0, math.cos(tilt), -math.sin(tilt)], [0, math.sin(tilt), math.cos(tilt)]])
        Rc = T @ R
        cam_pos = np.array([cx, cy, 0.0]) + np.linalg.inv(Rc) @ np.array([0, 0, -Z])
        # plane point (x, y, 0) -> camera coords -> screen
        M = Rc @ np.array([[1, 0, -cam_pos[0]], [0, 1, -cam_pos[1]], [0, 0, -cam_pos[2]]])
        K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]])
        Hm = K @ M
        return Hm / Hm[2, 2]

    def project(self, cam, xy_m):
        Hm = self.homography(cam)
        p = self.m2p(np.atleast_2d(xy_m))
        q = np.hstack([p, np.ones((len(p), 1))]) @ Hm.T
        return q[:, :2] / q[:, 2:3]

    def view(self, cam, dof=True, table='#0E0B12'):
        Hm = self.homography(cam)
        out = cv2.warpPerspective(self.master, Hm, (W, H), flags=cv2.INTER_AREA if cam['dist'] * S > W * 1.3 else cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=tuple(int(v * 255) for v in hexc(table)))
        img = out.astype(np.float32) / 255.0
        if dof and cam.get('tilt', 0) > 3:
            # depth of field: blur grows away from the focus row (the plane recedes upward on screen)
            ys = np.arange(H, dtype=np.float32)
            focus = cam.get('focus_y', H * 0.55)
            k = np.clip(np.abs(ys - focus) / (H * 0.5), 0, 1) ** 1.4 * cam.get('dof', 1.0)
            b1 = cv2.GaussianBlur(img, (0, 0), 2.2)
            b2 = cv2.GaussianBlur(img, (0, 0), 5.5)
            a1 = np.clip(k * 2, 0, 1)[:, None, None]
            a2 = np.clip(k * 2 - 1, 0, 1)[:, None, None]
            img = img * (1 - a1) + b1 * a1
            img = img * (1 - a2) + b2 * a2
        return img

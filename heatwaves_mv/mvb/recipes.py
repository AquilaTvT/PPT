"""Per-shot MV-B recipes (registered into timeline.RECIPES)."""
import numpy as np

from mv.timing import BEAT
from . import timeline as tl
from . import kit
from .plates import plate
from .typo import VLyric

R = tl.RECIPES
_cache = {}


def once(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


# ---------------------------------------------------------------- B-hook-03: low flight over the noon road
def _hook03_plate():
    s = tl.BY_ID['B-hook-03']
    d = s['end'] - s['start']
    v = 22.0
    gt = tl.VLyric and __import__('json').load(open(tl.os.path.join(tl.ROOT, 'assets', 'glyph_times.json')))['7']
    decals = []
    for ch, tg in zip('光りだすロード', gt):
        tlc = max(0.12, tg - s['start'])
        decals.append({'ch': ch, 'z': v * tlc + 0.6, 'x': 0.0, 'size': 2.3, 'flashT': tlc})
    path = [{'t': 0.0, 'pos': [0.3, 0.8, 0.0], 'look': [0.2, 0.55, 40.0], 'fov': 52, 'ease': 'linear'},
            {'t': 1.40, 'pos': [0.3, 0.8, v * 1.40], 'look': [0.2, 0.55, v * 1.40 + 40], 'fov': 52, 'roll': 0, 'ease': 'linear'},
            {'t': 1.62, 'pos': [0.3, 0.8, v * 1.62], 'look': [0.2, 0.55, v * 1.62 + 40], 'fov': 52, 'roll': -3, 'ease': 'linear'},
            {'t': 2.10, 'pos': [0.3, 0.8, v * 2.10], 'look': [0.2, 0.55, v * 2.10 + 40], 'fov': 52, 'roll': 0, 'ease': 'linear'},
            {'t': 2.60, 'pos': [0.3, 0.8, v * 2.60], 'look': [0.2, 0.6, v * 2.60 + 40], 'fov': 52, 'ease': 'linear'},
            {'t': d, 'pos': [0.0, 2.8, v * 2.60 + 6], 'look': [-4.0, 2.9, v * 2.60 + 14], 'fov': 52, 'ease': 'in'}]
    return plate('B-hook-03', 's2_coast', {'world': 'noon', 'wallH': 0.5, 'poleSpacing': v * BEAT, 'poleZ0': 0.0,
                                           'mirrorEvery': 3, 'decals': decals, 'path': path}, 0.0, d, fps=24)


def hook03(s, t, local, fi):
    pl = once('hook03', _hook03_plate)
    img = pl.frame(local).copy()
    vp = pl.anchor(local, 'vp')
    hy = vp[0][1] if vp else 536.0
    beats = [s['start'] + k * BEAT for k in range(5)]
    p = kit.beat_pulse(t, beats, 0.15)
    if local < 2.55:
        img = kit.mirage_band(img, t, hy + 2, x0=760, x1=1160, height=22, pulse=p)
        img = kit.dot_person(img, 960 + 14 * np.sin(local * 0.7), hy + 14, 58, t, reflect_y=hy + 16)
        img = kit.haze_lower(img, t, 0.004, int(hy))
    if local > 2.55:
        k = (local - 2.55) / (s['end'] - s['start'] - 2.55)
        img = kit.dir_blur(img, 140 * k, 40 * k)
    ly = once('hook03_l8', lambda: VLyric(8, accent='#2D6BE0'))
    return ly.draw(img, t)


R['B-hook-03'] = hook03
tl.OWN_TYPE.add('B-hook-03')


# ---------------------------------------------------------------- B-intro-04: the stamp card, sun rises in the 6th circle
def _ease_in(x):
    return x * x * x


def _ease_io(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def intro04(s, t, local, fi):
    from . import card as C
    import math
    from mv.core import clamp
    re = [11.79, 12.53, 13.27, 14.02, 14.76]
    stamp_k = [clamp((t - r) / (4 / 24)) for r in re]
    sun_k = _ease_io(clamp((t - 14.02) / (16.24 - 14.02)))
    glow_k = 0.25 * sun_k + 0.75 * clamp((t - 15.50) / (16.98 - 15.50))
    beats_since = max(0.0, (t - 14.02) / BEAT)
    ray = 4 * beats_since + 4 * max(0.0, (t - 15.50) / BEAT)
    n = int(clamp((t - 11.39) / (14.02 - 11.39)) * len("YOU KNOW THAT I'M NEVER GONNA LOSE"))
    key = ('card', tuple(round(k, 2) for k in stamp_k), round(sun_k, 3), round(glow_k, 3), n, round(ray, 1))
    if key not in _cache:
        if len([k for k in _cache if isinstance(k, tuple) and k[0] == 'card']) > 4:
            for k in [k for k in _cache if isinstance(k, tuple) and k[0] == 'card']:
                del _cache[k]
        _cache[key] = C.render_card(stamp_k=stamp_k, sun_k=sun_k, glow_k=glow_k, footer_n=n, ray_rot=ray)
    card = _cache[key]
    x6, y6, _ = C.CIRCLES[5]
    if t < 14.02:
        k = (t - 11.05) / (14.02 - 11.05)
        cx, cy, z, rot = 900 + 1300 * k, 1000 - 80 * k, 1.6, 1.0 * math.sin(k * 3.0)
    elif t < 16.24:
        k = _ease_in((t - 14.02) / (16.24 - 14.02))
        cx, cy = 2200 + (x6 - 2200) * k, 920 + (y6 - 920) * k
        z, rot = 1.6 + (3.5 - 1.6) * k, 0.0
    else:
        k = _ease_in(clamp((t - 16.24) / (16.98 - 16.24)))
        cx, cy, z, rot = x6, y6 - 30 * k, 3.5 + (6.0 - 3.5) * k, 0.0
    img = C.view(card, cx, cy, z, rot)
    # CRT mint spill fading as the sun brightens
    spill = (1 - glow_k) * 0.18
    if spill > 0.01:
        ys, xs = kit._YS, kit._XS
        g = np.clip(1 - np.sqrt((xs / 1920) ** 2 + (ys / 1080) ** 2) / 1.2, 0, 1) * spill
        img = img * (1 - g[..., None]) + kit.hexc('#7FC8B8')[None, None] * g[..., None]
    if 'zh_l3' not in _cache:
        from mv import text, lyrics
        _cache['zh_l3'] = (text, lyrics)
    text, lyrics = _cache['zh_l3']
    if 11.6 < t < 14.6:
        a = clamp((t - 11.6) / 0.25) * (1 - clamp((t - 14.3) / 0.3))
        gl, _ = text.layout_h(lyrics.ZH[3], 960, 1010, 30, 'zh', tracking=0.2, align='center')
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a * 0.9))
        if f is not None:
            img = img + (kit.hexc('#1E2550')[None, None] - img) * f[..., None]
    if t >= 16.80:
        big = once('l4_pre', lambda: VLyric(4, x=960, y=420, size=230, accent='#D9402B',
                                             times=[16.80], out_t=99.0, zh=False, max_glyphs=1))
        img = big.draw(img, t)
    return img


R['B-intro-04'] = intro04
tl.OWN_TYPE.add('B-intro-04')


# ---------------------------------------------------------------- B-intro-01: LED destination board boot, town prints itself
def _intro01_plate():
    path = [{'t': 0.0, 'pos': [-420, 120, -560], 'look': [-150, 0, -260], 'fov': 34},
            {'t': 1.48, 'pos': [-520, 300, -680], 'look': [-80, 0, -120], 'fov': 34}]
    return plate('B-intro-01', 's5_map', {'world': 'night', 'path': path, 'route': [[0, 0], [2, 0]]}, 0.0, 1.50, fps=24)


def _print_passes(img, k_passes, wipe):
    """show the plate one ink family at a time (riso drums): k_passes[i] in 0..1 = wipe progress of pass i"""
    from .print_fx import hexc as H
    lab = __import__('cv2').cvtColor(np.clip(img, 0, 1).astype(np.float32), __import__('cv2').COLOR_RGB2Lab)
    L = lab[..., 0]
    hue_or = (img[..., 0] > img[..., 2] + 0.12)
    mint = (img[..., 1] > img[..., 0] + 0.08) & (img[..., 1] > 0.45)
    fam = np.full(img.shape[:2], 1, np.int8)          # cobalt-ish mids
    fam[L < 28] = 0                                   # darks: navy / warm black
    fam[hue_or] = 2                                   # orange windows / lamps
    fam[mint] = 3
    fam[L > 82] = 4                                   # paper
    out = np.empty_like(img)
    out[:] = H('#EDE3CF')
    xs = kit._XS / 1920.0
    for f in range(4):
        k = k_passes[f]
        if k <= 0:
            continue
        m = ((fam == f) & (xs <= k * 1.2 - 0.1 + 0.02 * np.sin(kit._YS / 40.0))).astype(np.float32)
        out = out * (1 - m[..., None]) + img * m[..., None]
    m = (fam == 4).astype(np.float32)
    return out * (1 - m[..., None]) + img * m[..., None]


def intro01(s, t, local, fi):
    from mv.core import clamp
    from .print_fx import led_board, hexc as H
    import cv2
    img = np.empty((1080, 1920, 3), np.float32)
    img[:] = H('#EDE3CF')
    # LED board (orange) state
    board_w, rows, dot = 96, 16, 18
    scroll_text = "LAST NIGHT, ALL I THINK ABOUT IS YOU"
    if local < 0.68:
        txt, scroll, lit = '', 0, 0.0
    elif local < 2.16:
        txt, scroll, lit = '', 0, 1.0
    elif local < 2.45:
        txt, scroll, lit = '回送', 0, 1.0
    else:
        fr = int((local - 2.45) * 24)
        # 'YOU' must reach the board centre on 4.39: scroll speed derived from that (dot-locked, whole dots/frame)
        txt_w = 8 * len(scroll_text)
        stop = txt_w - board_w // 2 - 12
        speed = max(2, int(round((stop + board_w) / ((4.39 - 2.45) * 24))))
        txt, scroll, lit = scroll_text, min(fr * speed - board_w, stop), 1.0
    key = ('led', txt, scroll)
    if key not in _cache:
        if txt:
            rgb, _ = led_board(txt, cols=board_w, rows=rows, dot=dot, on='#F08A3C', off='#3A2A20', bg='#120C0A',
                               font='dot', scroll=scroll if txt == scroll_text else -38)
        else:
            rgb, _ = led_board(' ', cols=board_w, rows=rows, dot=dot, on='#F08A3C', off='#3A2A20', bg='#120C0A', font='dot')
        _cache[key] = rgb
    board = _cache[key]
    bh, bw = board.shape[:2]
    # diagonal full-board dot flash at 1.42
    fk = clamp(1 - (local - 1.42) / 0.35) if local >= 1.42 else 0.0
    if fk > 0:
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        diag = ((xx + yy) / (bw + bh) < (local - 1.42) / 0.15)
        board = board + (H('#F08A3C')[None, None] - board) * (diag * fk * 0.8)[..., None]
    # pull back 3.65-5.13: plate prints itself under the shrinking board
    pk = clamp((local - 3.65) / (5.13 - 3.65))
    if pk > 0:
        pl = once('intro01', _intro01_plate)
        town = pl.frame(local - 3.65)
        passes = [clamp((local - tp) / 0.25) for tp in (3.65, 4.02, 4.39, 4.76)]
        img = _print_passes(town, passes, 0)
    scale = 1.0 - 0.82 * (pk * pk * (3 - 2 * pk))
    sw, sh = max(8, int(bw * scale)), max(4, int(bh * scale))
    b2 = cv2.resize(board, (sw, sh), interpolation=cv2.INTER_AREA)
    cx, cy = 960, int(540 - 300 * pk)
    x0, y0 = cx - sw // 2, cy - sh // 2
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(1920, x0 + sw), min(1080, y0 + sh)
    if xb > xa and yb > ya:
        img[ya:yb, xa:xb] = b2[ya - y0:yb - y0, xa - x0:xb - x0]
        # ink frame line-drawing reveal 0..0.68
        dk = clamp(local / 0.68)
        frame = np.zeros((1080, 1920), np.uint8)
        per = 2 * (sw + sh)
        L = int(per * dk)
        pts = [(x0 - 10, y0 - 10), (x0 + sw + 10, y0 - 10), (x0 + sw + 10, y0 + sh + 10), (x0 - 10, y0 + sh + 10), (x0 - 10, y0 - 10)]
        acc = 0
        for (a, b) in zip(pts, pts[1:]):
            seg = abs(b[0] - a[0]) + abs(b[1] - a[1])
            if acc >= L:
                break
            f = min(1.0, (L - acc) / max(1, seg))
            e = (int(a[0] + (b[0] - a[0]) * f), int(a[1] + (b[1] - a[1]) * f))
            cv2.line(frame, a, e, 255, max(2, int(6 * scale)), cv2.LINE_AA)
            acc += seg
        m = frame.astype(np.float32) / 255
        img = img + (H('#1A1416')[None, None] - img) * m[..., None]
    # registration marks + colour bar from 0.68, carried away by the crane
    if local >= 0.68:
        off = int(420 * pk)
        for (mx, my) in ((70, 70 - off), (1850, 70 - off), (70, 1010 + off), (1850, 1010 + off)):
            cv2.circle(img, (mx, my), 18, tuple(float(v) for v in H('#1A1416')), 2, cv2.LINE_AA)
            cv2.line(img, (mx - 30, my), (mx + 30, my), tuple(float(v) for v in H('#1A1416')), 2, cv2.LINE_AA)
            cv2.line(img, (mx, my - 30), (mx, my + 30), tuple(float(v) for v in H('#1A1416')), 2, cv2.LINE_AA)
        inks = ['#141A33', '#1E2550', '#2C4C9A', '#C9D3DC', '#EDE3CF', '#F08A3C', '#D9402B', '#7FC8B8', '#1A1416']
        for i, c in enumerate(inks):
            x = 560 + i * 90
            y = 1030 + off
            if y < 1080:
                cv2.rectangle(img, (x, y), (x + 80, min(1079, y + 30)), tuple(float(v) for v in H(c)), -1)
    # Chinese under the board from 2.45, dissolving to dots by 5.0
    if local >= 2.45:
        from mv import text, lyrics
        a = clamp((local - 2.45) / 0.25) * (1 - clamp((local - 4.6) / 0.4))
        gl, _ = text.layout_h(lyrics.ZH[0], cx, y0 + sh + 70 * max(scale, 0.3), 34, 'zh', tracking=0.2, align='center')
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a))
        if f is not None:
            img = img + (H('#1A1416')[None, None] - img) * f[..., None]
    return img


R['B-intro-01'] = intro01
tl.OWN_TYPE.add('B-intro-01')

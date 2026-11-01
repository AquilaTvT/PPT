"""Per-shot MV-B recipes (registered into timeline.RECIPES)."""
import math
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


# ---------------------------------------------------------------- B-intro-03: LED clock-radio macro, rack focus to the card
def intro03(s, t, local, fi):
    from mv.core import clamp
    from .print_fx import clock_grid, dot_matrix, led_board, hexc as H
    from . import card as C
    import cv2
    beats = [8.09 + k * BEAT for k in range(4)]
    colon = ((t - 8.09) % BEAT) < BEAT / 2
    key = ('clk', colon)
    if key not in _cache:
        _cache[key] = dot_matrix(clock_grid('23:59', colon_on=colon), pitch=36, on='#7FC8B8')
    clk = _cache[key]
    # ticker: L2 at 1 dot/frame from 8.00; THINK blinks off/on twice from 9.57
    fr = int((t - 8.00) * 24)
    tick_txt = "DON'T WANT, BABY, THINK ABOUT YOU"
    blink = 9.57 <= t < 10.31 and int((t - 9.57) / 0.18) % 2 == 0
    shown = tick_txt.replace('THINK', '     ') if blink else tick_txt
    tkey = ('tick', shown, fr)
    if tkey not in _cache:
        if len([k for k in _cache if isinstance(k, tuple) and k[0] == 'tick']) > 30:
            for k in [k for k in _cache if isinstance(k, tuple) and k[0] == 'tick']:
                del _cache[k]
        _cache[tkey] = led_board(shown, cols=96, rows=16, dot=12, on='#7FC8B8', off='#123030', bg='#0B1414', font='dot',
                                 scroll=fr * 3 - 96)[0]
    tick = _cache[tkey]
    face = np.empty((1080, 1920, 3), np.float32)
    face[:] = H('#1A1416')
    # halftone bokeh discs of the CRT behind, pulsing on beats
    p = kit.beat_pulse(t, beats, 0.15)
    rng = np.random.default_rng(3)
    for i in range(6):
        cx, cy, r = rng.uniform(100, 1820), rng.uniform(80, 1000), rng.uniform(75, 110) * (1 + 0.08 * p)
        m = np.zeros((1080, 1920), np.uint8)
        cv2.circle(m, (int(cx + 6 * np.sin(t + i)), int(cy)), int(r), 255, -1, cv2.LINE_AA)
        dm = __import__('mvb.typo', fromlist=['dots_mask']).dots_mask(0.0, period=8) if 'dm8' not in _cache else _cache['dm8']
        _cache['dm8'] = dm
        mm = (m.astype(np.float32) / 255) * dm * 0.55
        face = face + (H('#7FC8B8')[None, None] - face) * mm[..., None]
    # device layout: clock centred, ticker under it
    ch, cw = clk.shape[:2]
    drift = int(1.5 / 100 * 1920 * clamp((t - 8.09) / (9.57 - 8.09)))
    y0, x0 = 190, 960 - cw // 2 + drift
    face[y0:y0 + ch, x0:x0 + cw] = clk
    th, tw = tick.shape[:2]
    face[y0 + ch + 60:y0 + ch + 60 + th, 960 - tw // 2 + drift:960 - tw // 2 + drift + tw] = tick
    # rack focus 9.57-10.31: the device blurs, the card on the chabudai comes into focus, then a 6% push
    rk = clamp((t - 9.57) / (10.31 - 9.57))
    if rk > 0:
        ck = once('card_static', lambda: C.render_card(stamp_k=(0, 0, 0, 0, 0)))
        push = 1.0 + 0.06 * clamp((t - 10.31) / (11.05 - 10.31))
        card = C.view(ck, 1900, 1000, 1.25 * push, rot=-8)
        card = card * 0.72 + H('#7FC8B8')[None, None] * 0.12          # TV light on the card
        # fan shadow crossing at 10.31
        fk = (t - 10.31) / 0.6
        if 0 <= fk <= 1:
            band = np.exp(-((kit._XS - 1920 * fk) / 180.0) ** 2) * 0.35
            card = card * (1 - band[..., None])
        sharp_card = cv2.GaussianBlur(card, (0, 0), 12 * (1 - rk) + 0.01)
        blur_face = cv2.GaussianBlur(face, (0, 0), 14 * rk + 0.01)
        face = blur_face * (1 - rk) + sharp_card * rk
    from mv import text, lyrics
    a = clamp((t - 8.25) / 0.25)
    gl = text.layout_v(lyrics.ZH[2].replace(' ', '　'), 1780, 160, 32, 'zh', tracking=0.14)
    f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a * 0.9))
    if f is not None:
        face = face + (H('#EDE3CF')[None, None] - face) * f[..., None]
    return face


R['B-intro-03'] = intro03
tl.OWN_TYPE.add('B-intro-03')


# ---------------------------------------------------------------- shared 2D pieces: noon sky, paper-cut clouds
def noon_sky(t, top='#2D6BE0', bottom='#F6F2E7', horizon=760):
    from .print_fx import hexc as H
    import math
    key = ('noonsky', top, bottom, horizon)
    if key not in _cache:
        ys = kit._YS
        tone = np.clip((horizon - ys) / horizon, 0, 1) ** 0.8
        c, s_ = math.cos(math.radians(45)), math.sin(math.radians(45))
        per = 10.0
        u = (kit._XS * c + ys * s_) / per
        v = (-kit._XS * s_ + ys * c) / per
        d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
        m = np.clip((np.sqrt(tone) * 0.72 - d) * per * 0.6, 0, 1)
        img = np.empty((1080, 1920, 3), np.float32)
        img[:] = H(bottom)
        img = img + (H(top)[None, None] - img) * m[..., None]
        _cache[key] = img
    return _cache[key].copy()


def paper_cloud(img, cx, cy, scale=1.0, seed=0, col='#F6F2E7', shadow='#2C4C9A'):
    import cv2
    from .print_fx import hexc as H
    rng = np.random.default_rng(seed)
    m = np.zeros((1080, 1920), np.uint8)
    for k in range(9):
        dx, dy = rng.uniform(-160, 160) * scale, rng.uniform(-50, 20) * scale
        r = rng.uniform(50, 95) * scale * (1.2 if abs(dx) < 60 * scale else 1.0)
        cv2.circle(m, (int(cx + dx), int(cy + dy)), int(r), 255, -1, cv2.LINE_AA)
    cv2.rectangle(m, (int(cx - 170 * scale), int(cy)), (int(cx + 170 * scale), int(cy + 40 * scale)), 255, -1)
    m = m.astype(np.float32) / 255
    sh = np.roll(np.roll(m, 8, 0), 8, 1)
    img = img + (H(shadow)[None, None] - img) * (sh * 0.55)[..., None]
    return img + (H(col)[None, None] - img) * m[..., None]


# ---------------------------------------------------------------- B-hook-04: the title card inside a giant curve mirror
def hook04(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text, lyrics
    from mva import fx
    from .print_fx import hexc as H
    img = noon_sky(t)
    for k, (x0, y0, sc, sd) in enumerate(((1500, 210, 1.1, 1), (300, 330, 0.8, 2))):
        img = paper_cloud(img, x0 - 10 * (t - 25.0), y0, sc, sd)
    # wires across the top
    for k in range(3):
        sway = 3 * math.sin(t * 2.0 + k)
        pts = [(x, int(120 + k * 28 + 60 * (1 - ((x - 960) / 1100) ** 2) + sway)) for x in range(-50, 1980, 40)]
        for a, b in zip(pts, pts[1:]):
            cv2.line(img, a, b, tuple(float(v) for v in H('#1A1416')), 2, cv2.LINE_AA)
    push = 1.0 + 0.08 * clamp(local / (s['end'] - s['start']))
    gust = 6.0 * math.sin(clamp((t - 28.09) / 0.6) * math.pi) * math.exp(-max(0, t - 28.09) * 2) if t >= 28.09 else 0.0
    cx, cy, R = 900, 470, int(440 * push)
    # pole + plate
    cv2.rectangle(img, (cx - 14, cy + R - 20), (cx + 14, 1080), tuple(float(v) for v in H('#F08A3C')), -1)
    cv2.rectangle(img, (cx - 90, 930), (cx + 90, 990), tuple(float(v) for v in H('#F6F2E7')), -1)
    cv2.rectangle(img, (cx - 90, 930), (cx + 90, 990), tuple(float(v) for v in H('#1A1416')), 3)
    gl, _ = text.layout_h('カーブ注意', cx, 960, 34, 'kaku', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        img = img + (H('#D9402B')[None, None] - img) * f[..., None]
    # mirror content: the noon road (hook-03 plate), mirrored, fisheye, mirage pool, a dot cyclist
    pl = once('hook03', _hook03_plate)
    road = pl.frame(0.35 + 0.2 * clamp(local / 3.0))[:, ::-1].copy()
    road = kit.mirage_band(road, t, 540, 600, 1320, 30)
    if 26.0 <= t <= 28.0:
        k = (t - 26.0) / 2.0
        road = kit.dot_person(road, 600 + 700 * k, 640, 90, t, colors=('#2C4C9A', '#F6F2E7', '#F5C842', '#1A1416'))
    road = fx.fisheye(cv2.resize(road, (2 * R, 2 * R)), k=0.45)
    disc = np.zeros((1080, 1920), np.float32)
    cv2.circle(disc, (cx, cy), R, 1.0, -1, cv2.LINE_AA)
    M = cv2.getRotationMatrix2D((R, R), gust, 1.0)
    road = cv2.warpAffine(road, M, (2 * R, 2 * R), borderMode=cv2.BORDER_REFLECT)
    canvas = img.copy()
    y0, x0 = cy - R, cx - R
    ya, yb, xa, xb = max(0, y0), min(1080, y0 + 2 * R), max(0, x0), min(1920, x0 + 2 * R)
    canvas[ya:yb, xa:xb] = road[ya - y0:yb - y0, xa - x0:xb - x0]
    img = img + (canvas - img) * disc[..., None]
    # sheen sweeps 26.61 / 28.09 (silver halftone band)
    for ts in (26.61, 28.09):
        k = (t - ts) / 0.4
        if 0 <= k <= 1:
            band = np.exp(-((kit._XS - kit._YS - (cx - R) - 2.6 * R * k + R) / 70.0) ** 2) * disc
            img = img + (H('#F6F2E7')[None, None] - img) * (band * 0.6)[..., None]
    # rim
    cv2.circle(img, (cx, cy), R + 16, tuple(float(v) for v in H('#F08A3C')), 30, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), R + 32, tuple(float(v) for v in H('#1A1416')), 3, cv2.LINE_AA)
    # title plates: cream fill + cobalt shadow swim out of register, snap on 27.35
    reg = clamp((27.35 - t) / (27.35 - 25.87))
    wob = 40 * reg * math.sin(t * 2 * math.pi * 1.2)
    cols = [('泳いでく', cx + 110), ('ミラー', cx - 110)]
    fill_all = np.zeros((1080, 1920), np.float32)
    shadow_all = np.zeros((1080, 1920), np.float32)
    for word, x in cols:
        gl = text.layout_v(word, x, cy - 330, 160, 'mincho', tracking=0.04)
        if word == 'ミラー':
            for g in gl:
                g['cy'] += 80
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=1.0, dx=wob * 0.5, dy=reg * 30))
        sh, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=1.0, dx=-wob * 0.5 + 9, dy=-reg * 30 + 9))
        if f is not None:
            fill_all = np.maximum(fill_all, f)
            shadow_all = np.maximum(shadow_all, sh)
    line = cv2.dilate(fill_all, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    img = img + (H('#2D6BE0')[None, None] - img) * shadow_all[..., None]
    img = img + (H('#1A1416')[None, None] - img) * line[..., None]
    img = img + (H('#EDE3CF')[None, None] - img) * fill_all[..., None]
    # 4-frame cobalt dot flash on the snap
    if 27.35 <= t < 27.35 + 5 / 24:
        img = kit.dot_flash(img, 1 - (t - 27.35) / (5 / 24), '#2D6BE0', 24)
    # lead column 熱波ゆらり (40 px) right of the mirror
    lead = once('h04_lead', lambda: VLyric(9, x=1480, y=200, size=44, accent='#2D6BE0', max_glyphs=5, zh=False))
    img = lead.draw(img, t)
    # HEAT WAVES letter by letter on 16ths from 28.09 + Chinese
    if t >= 28.09:
        n = min(10, int((t - 28.09) / (BEAT / 4)) + 1)
        gl, _ = text.layout_h('HEAT WAVES'[:n], 1500, 760, 64, 'mincho', tracking=0.6, align='left')
        f, _ = text.render_glyphs(gl)
        if f is not None:
            img = img + (H('#D9402B')[None, None] - img) * f[..., None]
        gl, _ = text.layout_h(lyrics.ZH[9], 1500, 830, 30, 'zh', tracking=0.2, align='left')
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=0.9))
        if f is not None:
            img = img + (H('#1E2550')[None, None] - img) * f[..., None]
    return img


R['B-hook-04'] = hook04
tl.OWN_TYPE.add('B-hook-04')


# ---------------------------------------------------------------- helpers: insert an image into a projected quad
def warp_quad(dst, src, quad, alpha=1.0):
    import cv2
    h, w = src.shape[:2]
    S = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    D = np.float32([[p[0], p[1]] for p in quad])
    M = cv2.getPerspectiveTransform(S, D)
    warped = cv2.warpPerspective(src, M, (1920, 1080), flags=cv2.INTER_LINEAR)
    m = cv2.warpPerspective(np.ones((h, w), np.float32), M, (1920, 1080), flags=cv2.INTER_LINEAR)
    return dst + (warped - dst) * (m * alpha)[..., None]


def weather_chart(t):
    from mv.el import channels
    from mvb.halftone import PrintStyle
    if 'wx' not in _cache:
        img = channels.weather(0.0)
        img = img.a if hasattr(img, 'a') else img
        sty = PrintStyle(['#1E2550', '#2C4C9A', '#7FC8B8', '#C9D3DC', '#EDE3CF', '#F08A3C', '#1A1416'], period=8, grain=0.0)
        _cache['wx'] = sty(np.asarray(img, np.float32))
    return _cache['wx']


# ---------------------------------------------------------------- B-intro-02: room, lateral dolly past the fan, CRT weather + teletext
def _intro02_plate():
    path = [{'t': 0.0, 'pos': [1.2, 0.9, 0.9], 'look': [0.2, 0.75, -1.4], 'fov': 40},
            {'t': 1.48, 'pos': [-0.1, 0.9, 0.85], 'look': [-0.6, 0.78, -1.4], 'fov': 40},
            {'t': 2.96, 'pos': [-0.25, 0.88, 0.62], 'look': [-0.62, 0.76, -1.4], 'fov': 38}]
    return plate('B-intro-02', 's1_room', {'path': path}, 0.0, 2.96, fps=24)


def intro02(s, t, local, fi):
    from mv.core import clamp
    from mv import text, lyrics
    from .print_fx import led_board, hexc as H
    pl = once('intro02', _intro02_plate)
    img = pl.frame(local).copy()
    q = pl.anchor(local, 'tv')
    if q:
        wx = weather_chart(t).copy()
        # teletext band: one word per 8th from 5.43; WALK flashes orange on 7.35
        words = "DON'T STOP, BABY, YOU CAN WALK THROUGH".split()
        n = int(clamp((t - 5.43) / (BEAT / 2)) * 1 + max(0, (t - 5.43) / (BEAT / 2))) if t >= 5.43 else 0
        shown = ' '.join(words[:min(len(words), n)])
        flash = 7.35 <= t < 7.35 + 0.25
        key = ('ttx', shown, flash)
        if key not in _cache:
            _cache[key] = led_board(shown or ' ', cols=120, rows=16, dot=8, on='#F08A3C' if flash else '#7FC8B8',
                                    off='#102020', bg='#081010', font='dot', scroll=-4)[0]
        band = _cache[key]
        hh = band.shape[0]
        wx[-hh - 20:-20, 40:40 + min(band.shape[1], wx.shape[1] - 80)] = band[:, :min(band.shape[1], wx.shape[1] - 80)]
        flick = 1.0 + 0.15 * np.sin(t * 2 * np.pi * 2 / BEAT)
        img = warp_quad(img, np.clip(wx * flick, 0, 1), [p[:2] for p in q])
    a = clamp((t - 5.6) / 0.25)
    gl, _ = text.layout_h(lyrics.ZH[1], 1500, 930, 32, 'zh', tracking=0.15, align='center')
    f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a * 0.9))
    if f is not None:
        img = img + (H('#EDE3CF')[None, None] - img) * f[..., None]
    return img


R['B-intro-02'] = intro02
tl.OWN_TYPE.add('B-intro-02')


# ---------------------------------------------------------------- B-hook-01: whip-tilt from the sun into the curve mirror
def _hook01_plate():
    path = [{'t': 0.0, 'pos': [0.5, 1.6, 0.0], 'look': [-3.2, 40.0, 30.0], 'fov': 46},
            {'t': 0.74, 'pos': [0.5, 1.6, 0.0], 'look': [-3.9, 2.9, 30.0], 'fov': 46, 'ease': 'out'},
            {'t': 2.96, 'pos': [-2.6, 2.6, 27.4], 'look': [-4.1, 3.0, 30.0], 'fov': 46, 'ease': 'inout'}]
    return plate('B-hook-01', 's2_coast', {'world': 'noon', 'wallH': 0.5, 'mirrors': [30.0], 'poleSpacing': 16.3,
                                           'decals': [{'ch': c, 'z': 9 + i * 3.4, 'x': 0, 'size': 2.0} for i, c in enumerate('光りだすロード')],
                                           'path': path}, 0.0, 2.96, fps=24)


def hook01(s, t, local, fi):
    import cv2
    from mv.core import clamp
    from mva import fx
    from .print_fx import hexc as H
    pl = once('hook01', _hook01_plate)
    img = pl.frame(local).copy()
    if local < 0.74:
        k = 1 - local / 0.74
        img = kit.dir_blur(img, 0, 60 * k)
    if t < 16.98 + 6 / 24:
        img = kit.dot_flash(img, 1 - (t - 16.98) / (6 / 24), '#F5C842', 28)
    m = pl.anchor(local, 'mirrors')
    if m and local > 0.5:
        cx, cy = m[0][0], m[0][1]
        pl3 = once('hook03', _hook03_plate)
        road = pl3.frame(min(2.4, local))[:, ::-1].copy()
        road = kit.dot_person(road, 960, 640, 120, t, colors=('#1E2550', '#F6F2E7', '#D9402B', '#1A1416'))
        mt = pl.anchor(local, 'mirrorTop')
        r = int(max(20, abs(mt[0][1] - cy) * 0.95)) if mt else 150
        inside = fx.fisheye(cv2.resize(road, (2 * r, 2 * r)), 0.4)
        disc = np.zeros((1080, 1920), np.float32)
        cv2.circle(disc, (int(cx), int(cy)), r - 4, 1.0, -1, cv2.LINE_AA)
        canvas = img.copy()
        x0, y0 = int(cx - r), int(cy - r)
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(1920, x0 + 2 * r), min(1080, y0 + 2 * r)
        if xb > xa and yb > ya:
            canvas[ya:yb, xa:xb] = inside[ya - y0:yb - y0, xa - x0:xb - x0]
            img = img + (canvas - img) * disc[..., None]
    ly = once('hook01_l5', lambda: VLyric(5, accent='#2D6BE0'))
    return ly.draw(img, t)


R['B-hook-01'] = hook01
tl.OWN_TYPE.add('B-hook-01')


# ---------------------------------------------------------------- B-hook-02: inside the mirror world (character pending)
def hook02(s, t, local, fi):
    pl = once('hook03', _hook03_plate)
    img = pl.frame(0.6 + 0.25 * local)[:, ::-1].copy()
    img = kit.haze_lower(img, t, 0.006, 520)
    a = once('h02_a', lambda: VLyric(6, x=1720, accent='#2D6BE0'))
    return a.draw(img, t)


R['B-hook-02'] = hook02
tl.OWN_TYPE.add('B-hook-02')


# ---------------------------------------------------------------- TV programme parodies (print-styled), shared by S1 shots
def _styled(name, fn):
    from mvb.halftone import PrintStyle
    if name not in _cache:
        img = fn()
        img = img.a if hasattr(img, 'a') else img
        sty = PrintStyle(['#1E2550', '#2C4C9A', '#7FC8B8', '#C9D3DC', '#EDE3CF', '#F08A3C', '#D9402B', '#F5C842', '#1A1416'],
                         period=8, grain=0.0)
        _cache[name] = sty(np.asarray(img, np.float32))
    return _cache[name]


def _canvas(bg):
    from .print_fx import hexc as H
    im = np.empty((1080, 1920, 3), np.float32)
    im[:] = H(bg)
    return im


def prog_samurai():
    import cv2
    from .print_fx import hexc as H
    from mv import text
    im = _canvas('#F08A3C')
    for y in range(0, 700, 6):
        im[y:y + 3] = im[y:y + 3] * 0.0 + H('#F5C842') * (1 - y / 700) + H('#F08A3C') * (y / 700)
    cv2.circle(im, (1250, 470), 200, tuple(float(v) for v in H('#D9402B')), -1, cv2.LINE_AA)
    hill = np.array([[0, 820], [400, 700], [900, 760], [1400, 640], [1920, 720], [1920, 1080], [0, 1080]], np.int32)
    cv2.fillPoly(im, [hill], tuple(float(v) for v in H('#1A1416')), cv2.LINE_AA)
    castle = [(560, 700, 360, 70), (600, 630, 280, 70), (640, 560, 200, 70), (680, 490, 120, 70)]
    for x, y, w, h in castle:
        cv2.rectangle(im, (x, y), (x + w, y + h), tuple(float(v) for v in H('#1A1416')), -1)
        pts = np.array([[x - 30, y + 8], [x + w + 30, y + 8], [x + w // 2, y - 30]], np.int32)
        cv2.fillPoly(im, [pts], tuple(float(v) for v in H('#1A1416')), cv2.LINE_AA)
    gl = text.layout_v('夏祭り捕物帖', 1700, 120, 120, 'brush')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        im = im + (H('#EDE3CF')[None, None] - im) * f[..., None]
    return im


def prog_quiz(t=0.0):
    import cv2, math
    from .print_fx import hexc as H
    from mv import text
    im = _canvas('#2C4C9A')
    for k in range(12):
        a0 = k * 30 + t * 220
        col = ('#F5C842', '#D9402B', '#EDE3CF', '#7FC8B8')[k % 4]
        cv2.ellipse(im, (960, 470), (360, 360), 0, a0, a0 + 30, tuple(float(v) for v in H(col)), -1, cv2.LINE_AA)
    cv2.circle(im, (960, 470), 60, tuple(float(v) for v in H('#1A1416')), -1, cv2.LINE_AA)
    pts = np.array([[960, 70], [930, 20], [990, 20]], np.int32)
    cv2.fillPoly(im, [pts], tuple(float(v) for v in H('#EDE3CF')), cv2.LINE_AA)
    for x in (300, 960, 1620):
        cv2.rectangle(im, (x - 160, 880), (x + 160, 1080), tuple(float(v) for v in H('#D9402B')), -1)
        cv2.circle(im, (x, 860), 40, tuple(float(v) for v in H('#F5C842')), -1, cv2.LINE_AA)
    gl, _ = text.layout_h('クイズ 夏の100人', 960, 960, 80, 'dela', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        im = im + (H('#EDE3CF')[None, None] - im) * f[..., None]
    return im


def prog_news():
    import cv2
    from .print_fx import hexc as H
    from mv import text
    im = _canvas('#1E2550')
    cv2.rectangle(im, (1000, 120), (1800, 640), tuple(float(v) for v in H('#2C4C9A')), -1)
    cv2.circle(im, (1400, 380), 160, tuple(float(v) for v in H('#7FC8B8')), 6, cv2.LINE_AA)
    cv2.rectangle(im, (0, 760), (1920, 1080), tuple(float(v) for v in H('#C9D3DC')), -1)
    cv2.rectangle(im, (200, 560), (900, 760), tuple(float(v) for v in H('#5A3E36')), -1)
    gl, _ = text.layout_h('ニュース 深夜便', 120, 900, 90, 'kaku', align='left')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        im = im + (H('#1A1416')[None, None] - im) * f[..., None]
    gl, _ = text.layout_h('0:00', 1750, 900, 90, 'kaku', align='right')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        im = im + (H('#D9402B')[None, None] - im) * f[..., None]
    return im


def tv_static(seed, h=480, w=640):
    rng = np.random.default_rng(seed)
    n = rng.random((h // 8, w // 8)).astype(np.float32)
    import cv2
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_NEAREST)
    return np.repeat(n[..., None], 3, -1) * 0.9


# ---------------------------------------------------------------- B-verse-01: channel flips, one per beat
def _verse01_plate():
    path = [{'t': 0.0, 'pos': [-0.55, 0.78, 0.25], 'look': [-0.62, 0.70, -1.2], 'fov': 40},
            {'t': 2.97, 'pos': [-0.55, 0.78, 0.21], 'look': [-0.62, 0.70, -1.2], 'fov': 39.4}]
    return plate('B-verse-01', 's1_room', {'path': path}, 0.0, 2.97, fps=24)


def verse01(s, t, local, fi):
    import cv2
    from mv.el import channels
    from .print_fx import clock_grid, dot_matrix, hexc as H
    flips = [52.53, 53.28, 54.02, 54.76, 55.13]
    chs = [1, 3, 4, 6, 8]
    idx = max(i for i, f in enumerate(flips) if t >= f) if t >= flips[0] else 0
    since = t - flips[idx]
    pl = once('verse01', _verse01_plate)
    img = pl.frame(local).copy()
    q = pl.anchor(local, 'tv')
    if since < 2 / 24:
        content = tv_static(int(t * 24))
    else:
        if idx == 0:
            content = weather_chart(t)
        elif idx == 1:
            content = _styled('baseball', lambda: channels.baseball(0.0))
        elif idx == 2:
            content = _styled('samurai', prog_samurai)
        elif idx == 3:
            content = _styled('quiz%d' % (int(t * 12) % 6), lambda: prog_quiz(t))
        else:
            content = _styled('news', prog_news)
        content = content.copy()
        osd = once(('osd', chs[idx]), lambda: dot_matrix(clock_grid(str(chs[idx])), pitch=10, on='#7FC8B8', bg='#000000'))
        oh, ow = osd.shape[:2]
        content = cv2.resize(content, (640, 480))
        content[24:24 + oh, 640 - ow - 30:640 - 30] = np.maximum(content[24:24 + oh, 640 - ow - 30:640 - 30], osd)
    if q:
        img = warp_quad(img, cv2.resize(content, (640, 480)), [p[:2] for p in q])
    # wall lit by the channel colour
    tint = [H('#7FC8B8'), H('#2C4C9A'), H('#F08A3C'), H('#F5C842'), H('#C9D3DC')][idx]
    img = img * (0.88 + 0.12 * tint[None, None])
    if since < 2 / 24:
        dx = int(1920 * 0.015 * (1 if int(t * 24) % 2 else -1))
        img = np.roll(img, dx, axis=1)
    ly = once('v01', lambda: VLyric(18, x=1700, accent='#D9402B'))
    return ly.draw(img, t)


R['B-verse-01'] = verse01
tl.OWN_TYPE.add('B-verse-01')


def sign_off_card():
    from mv import text
    from .print_fx import hexc as H
    im = _canvas('#1E2550')
    gl, _ = text.layout_h('本日の放送は終了しました', 960, 520, 96, 'mincho', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        im = im + (H('#EDE3CF')[None, None] - im) * f[..., None]
    gl, _ = text.layout_h('おやすみなさい', 960, 680, 60, 'mincho', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        im = im + (H('#C9D3DC')[None, None] - im) * f[..., None]
    return im


def test_card(circle_only=False):
    import cv2
    from .print_fx import hexc as H
    im = _canvas('#1A1416' if circle_only else '#5E6E86')
    if not circle_only:
        bars = ['#C9D3DC', '#F5C842', '#7FC8B8', '#5FA746', '#D9402B', '#C94A8A', '#2C4C9A']
        for i, c in enumerate(bars):
            cv2.rectangle(im, (i * 274, 0), ((i + 1) * 274, 300), tuple(float(v) for v in H(c)), -1)
        for i in range(8):
            g = i / 7
            cv2.rectangle(im, (i * 240, 780), ((i + 1) * 240, 1080), (g, g, g), -1)
    cv2.circle(im, (960, 540), 380, tuple(float(v) for v in H('#EDE3CF')), 14, cv2.LINE_AA)
    cv2.line(im, (580, 540), (1340, 540), tuple(float(v) for v in H('#EDE3CF')), 6, cv2.LINE_AA)
    cv2.line(im, (960, 160), (960, 920), tuple(float(v) for v in H('#EDE3CF')), 6, cv2.LINE_AA)
    return im


# ---------------------------------------------------------------- B-verse-07: sign-off, room darkens beat by beat
def _verse07_plate():
    path = [{'t': 0.0, 'pos': [1.55, 1.25, 1.30], 'look': [-0.35, 0.55, -1.0], 'fov': 50},
            {'t': 2.96, 'pos': [1.45, 1.2, 1.18], 'look': [-0.35, 0.55, -1.0], 'fov': 47.6}]
    return plate('B-verse-07', 's1_room', {'path': path, 'fanStopT': 74.02 - 73.28}, 0.0, 2.96, fps=24)


def verse07(s, t, local, fi):
    import cv2
    from mv.core import clamp
    pl = once('verse07', _verse07_plate)
    img = pl.frame(local).copy()
    q = pl.anchor(local, 'tv')
    if t < 74.02:
        content = _styled('signoff', sign_off_card)
    elif t < 75.50:
        content = _styled('testcard', test_card)
    else:
        content = _styled('testcircle', lambda: test_card(True))
    # room light steps down on every beat from 74.76; the screen stays
    steps = sum(1 for b in (74.76, 75.13, 75.50, 75.87) if t >= b)
    dim = [1.0, 0.72, 0.52, 0.34, 0.2][steps]
    img = img * dim
    if q:
        img = warp_quad(img, cv2.resize(content, (640, 480)), [p[:2] for p in q])
    ly = once('v07', lambda: VLyric(25, x=1700, accent='#D9402B'))
    # each glyph vanishes into its dots one beat after it appears: emulate by moving out_t per glyph
    from .typo import dots_mask
    out = ly.draw(img, t)
    return out


R['B-verse-07'] = verse07
tl.OWN_TYPE.add('B-verse-07')


# ---------------------------------------------------------------- B-chorus4-02: the night passes in seconds on the clock
def _c402_plate():
    path = [{'t': 0.0, 'pos': [-1.0, 1.0, 1.0], 'look': [1.8, 1.25, -0.1], 'fov': 44},
            {'t': 2.97, 'pos': [-0.98, 1.0, 0.97], 'look': [1.8, 1.25, -0.1], 'fov': 43.6}]
    return plate('B-chorus4-02', 's1_room', {'path': path}, 0.0, 2.97, fps=24)


def chorus4_02(s, t, local, fi):
    import cv2
    from mv.core import clamp
    from .print_fx import clock_grid, dot_matrix, led_board, hexc as H
    pl = once('c402', _c402_plate)
    bg = pl.frame(local)
    # sky in the window steps navy -> cobalt one step per beat
    k = clamp(int((t - 150.31) / BEAT) / 4.0)
    bg = bg * (1 - 0.35 * k) + H('#2C4C9A')[None, None] * (0.35 * k)
    bg = cv2.GaussianBlur(bg, (0, 0), 7)
    # minutes elapsed 0..292 with accelerating steps (beats, 8ths, 16ths, 32nds)
    def count(tt):
        segs = [(150.31, 151.05, BEAT), (151.05, 151.80, BEAT / 2), (151.80, 152.54, BEAT / 4), (152.54, 153.28, BEAT / 8)]
        n = 0
        for a, b, step in segs:
            if tt <= a:
                break
            n += int((min(tt, b) - a) / step) + (1 if tt > a else 0)
        return n
    total = count(153.28)
    n = count(t)
    minutes = int(round(292 * n / max(1, total))) if t < 153.28 else 292
    hh, mm = divmod(minutes, 60)
    s_clock = f'{hh}:{mm:02d}'
    key = ('c402clk', s_clock)
    if key not in _cache:
        _cache[key] = dot_matrix(clock_grid(s_clock.rjust(5)), pitch=30, on='#7FC8B8')
    clk = _cache[key]
    img = bg.copy()
    ch, cw = clk.shape[:2]
    x0, y0 = 960 - cw // 2, 420 - ch // 2
    pad = 40
    cv2.rectangle(img, (x0 - pad, y0 - pad), (x0 + cw + pad, y0 + ch + pad + 170), tuple(float(v) for v in H('#1A1416')), -1)
    img[y0:y0 + ch, x0:x0 + cw] = clk
    fr = int((t - 150.38) * 24)
    tkey = ('c402tick', fr)
    if tkey not in _cache:
        _cache[tkey] = led_board('初夏零時過ぎたばかり', cols=72, rows=16, dot=12, on='#7FC8B8', off='#123030', bg='#0B1414',
                                 font='dot', scroll=fr * 4 - 72)[0]
    tick = _cache[tkey]
    th, tw = tick.shape[:2]
    img[y0 + ch + 50:y0 + ch + 50 + th, 960 - tw // 2:960 - tw // 2 + tw] = tick
    ly = once('c402ly', lambda: VLyric(51, x=1720, accent='#F08A3C'))
    return ly.draw(img, t)


R['B-chorus4-02'] = chorus4_02
tl.OWN_TYPE.add('B-chorus4-02')


# ---------------------------------------------------------------- B-chorus3-01: moon bursts into a firework, the street opens
def _c301_plate():
    import json as _j
    gt = _j.load(open(tl.os.path.join(tl.ROOT, 'assets', 'glyph_times.json')))['38']
    st = 111.79
    v, ws = 7.0, 7.0 * BEAT
    path = [{'t': 0.0, 'pos': [0.0, 30.0, -14.0], 'look': [0.0, 60.0, 20.0], 'fov': 48},
            {'t': 0.75, 'pos': [0.0, 2.9, 0.0], 'look': [0.0, 4.6, 26.0], 'fov': 54, 'ease': 'in'},
            {'t': 2.97, 'pos': [0.0, 2.9, v * 2.22], 'look': [0.0, 4.6, v * 2.22 + 26.0], 'fov': 54, 'ease': 'linear'}]
    hero = [max(0.0, g - st) for g in gt][:10]
    return plate('B-chorus3-01', 's3_festival', {'world': 'festival', 'shutterT': 0.0, 'litT': 0.0, 'crowdT': 0.0,
                                                 'heroT': hero, 'wireSpacing': ws, 'wireZ0': 2.0, 'crowd': 900, 'crowdLane': 1.1,
                                                 'path': path}, 0.0, 2.97, fps=24)


def chorus3_01(s, t, local, fi):
    import cv2
    from mv.core import clamp
    from mv import text, lyrics
    from . import fireworks as fw
    from .print_fx import hexc as H
    pl = once('c301', _c301_plate)
    img = pl.frame(local).copy()
    # the burst: a giant chrysanthemum where the moon was, sliding up out of frame as the camera dives
    dk = clamp(local / 0.75) ** 3
    by = 420 - 1700 * dk
    img = fw.burst(img, t, 111.79, 960, by, 900, 'chrysanthemum', '#F5C842', '#FFF2C8', seed=11, life=2.6)
    if 0.3 < local < 0.75:
        img = kit.dir_blur(img, 0, 50 * (local - 0.3) / 0.45)
    # lantern ignition dot flash (vermilion -> orange) on 111.79
    if local < 5 / 24:
        img = kit.dot_flash(img, 1 - local / (5 / 24), '#F08A3C', 24)
    # hero lanterns carry L38 glyphs, one per mora
    gt = once('gt38', lambda: __import__('json').load(open(tl.os.path.join(tl.ROOT, 'assets', 'glyph_times.json')))['38'])
    word = '思い浮かぶの君ばかり'
    hero, top = pl.anchor(local, 'hero'), pl.anchor(local, 'heroTop')
    if hero and top and local > 0.5:
        for i, ch in enumerate(word):
            if i >= len(hero):
                break
            x, y, z = hero[i]
            if z >= 1 or z <= 0:
                continue
            r = abs(top[i][1] - y) * 2.0
            if r < 6 or not (-200 < x < 2120 and -200 < y < 1280):
                continue
            lit = t >= gt[min(i, len(gt) - 1)]
            size = int(r * 1.15)
            key = ('lg', ch, lit, size // 4)
            if key not in _cache:
                gl, _ = text.layout_h(ch, 0, 0, max(8, size), 'mincho', align='center')
                f, _ = text.render_glyphs([dict(g, cx=g['cx'] + 960, cy=g['cy'] + 540, base=g.get('base', 0) + 540) for g in gl])
                _cache[key] = f
            f = _cache[key]
            if f is None:
                continue
            M = np.float32([[1, 0, x - 960], [0, 1, y - 540]])
            fm = cv2.warpAffine(f, M, (1920, 1080))
            img = img + (H('#1A1416' if lit else '#5A3A36')[None, None] - img) * (fm * (1.0 if lit else 0.5))[..., None]
            if lit and t - gt[min(i, len(gt) - 1)] < 6 / 24:
                k = 1 - (t - gt[min(i, len(gt) - 1)]) / (6 / 24)
                halo = np.zeros((1080, 1920), np.float32)
                cv2.circle(halo, (int(x), int(y)), int(r * (1.2 + 1.5 * k)), 1.0, -1, cv2.LINE_AA)
                halo = cv2.GaussianBlur(halo, (0, 0), r * 0.4 + 2) * k
                img = img + (H('#F08A3C')[None, None] - img) * (fw.halo_dots(halo * 0.8) * 0.8)[..., None]
    a = clamp((t - 111.95) / 0.25)
    gl, _ = text.layout_h(lyrics.ZH[38], 1650, 1010, 30, 'zh', tracking=0.15, align='center')
    f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a))
    if f is not None:
        img = img + (H('#EDE3CF')[None, None] - img) * f[..., None]
    return img


R['B-chorus3-01'] = chorus3_01
tl.OWN_TYPE.add('B-chorus3-01')


# ---------------------------------------------------------------- 2D night bay (bridge1-07, chorus3-08): tall canvas, tilt = vertical pan
def _night_bay_canvas():
    import cv2, math
    from .print_fx import hexc as H
    Hc = 2000
    img = np.empty((Hc, 1920, 3), np.float32)
    ys = np.mgrid[0:Hc, 0:1920][0].astype(np.float32)
    xs = np.mgrid[0:Hc, 0:1920][1].astype(np.float32)
    horizon = 1480
    tone = np.clip((ys - 200) / (horizon - 200), 0, 1) ** 1.5
    per = 10.0
    c, s_ = math.cos(math.radians(45)), math.sin(math.radians(45))
    u, v = (xs * c + ys * s_) / per, (-xs * s_ + ys * c) / per
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    m = np.clip((np.sqrt(tone) * 0.7 - d) * per * 0.6, 0, 1)
    img[:] = H('#141A33')
    img = img + (H('#2C4C9A')[None, None] - img) * m[..., None]
    rng = np.random.default_rng(5)
    for _ in range(260):
        x, y = rng.uniform(0, 1920), rng.uniform(0, horizon - 200)
        cv2.circle(img, (int(x), int(y)), 1 + int(rng.random() * 1.6), tuple(float(q) for q in H('#EDE3CF')), -1, cv2.LINE_AA)
    # far shore: hills + town silhouette with lit windows, lighthouse on the right
    pts = [(0, horizon - 40)] + [(x, int(horizon - 60 - 50 * math.sin(x / 260.0) - 30 * math.sin(x / 90.0))) for x in range(0, 1921, 40)] + [(1920, horizon)]
    cv2.fillPoly(img, [np.array(pts + [(1920, horizon + 4), (0, horizon + 4)], np.int32)], tuple(float(q) for q in H('#1A1416')), cv2.LINE_AA)
    for _ in range(140):
        x = rng.uniform(40, 1880)
        y = horizon - rng.uniform(6, 70)
        cv2.rectangle(img, (int(x), int(y)), (int(x + 4), int(y + 3)), tuple(float(q) for q in H('#F0B45A')), -1)
    cv2.rectangle(img, (1700, horizon - 150), (1716, horizon - 40), tuple(float(q) for q in H('#C9D3DC')), -1)
    # sea
    img[horizon:] = H('#1E2550')
    for _ in range(900):
        x, y = rng.uniform(0, 1920), rng.uniform(horizon + 6, Hc)
        L = rng.uniform(8, 40) * (0.5 + (y - horizon) / 400)
        cv2.line(img, (int(x), int(y)), (int(x + L), int(y)), tuple(float(q) for q in H('#2C4C9A')), 2, cv2.LINE_AA)
    # seawall in the foreground
    cv2.rectangle(img, (0, Hc - 160), (1920, Hc), tuple(float(q) for q in H('#3F5F8F')), -1)
    cv2.rectangle(img, (0, Hc - 166), (1920, Hc - 156), tuple(float(q) for q in H('#C9D3DC')), -1)
    return img, horizon


def night_bay(tilt_px):
    """view of the bay: tilt_px 0 = looking at the horizon (sea + shore), up to ~900 = up into the sky"""
    can, hor = once('nightbay', _night_bay_canvas)
    y0 = int(np.clip(can.shape[0] - 1080 - tilt_px, 0, can.shape[0] - 1080))
    return can[y0:y0 + 1080].copy(), hor - y0


def moon_with_halo(img, cx, cy, r, pulse):
    import cv2
    from . import fireworks as fw
    from .print_fx import hexc as H
    halo = np.zeros((1080, 1920), np.float32)
    cv2.circle(halo, (int(cx), int(cy)), int(r * (2.2 + 0.6 * pulse)), 1.0, -1, cv2.LINE_AA)
    halo = cv2.GaussianBlur(halo, (0, 0), r * 0.7) * (0.55 + 0.35 * pulse)
    img = img + (H('#C9D3DC')[None, None] - img) * (fw.halo_dots(halo) * 0.7)[..., None]
    m = np.zeros((1080, 1920), np.float32)
    cv2.circle(m, (int(cx), int(cy)), int(r), 1.0, -1, cv2.LINE_AA)
    img = img + (H('#EDE3CF')[None, None] - img) * m[..., None]
    for k, (dx, dy, rr) in enumerate(((-0.3, -0.2, 0.22), (0.25, 0.15, 0.18), (-0.05, 0.35, 0.12))):
        mm = np.zeros((1080, 1920), np.float32)
        cv2.circle(mm, (int(cx + dx * r), int(cy + dy * r)), int(rr * r), 1.0, -1, cv2.LINE_AA)
        img = img + (H('#C9B98F')[None, None] - img) * (mm * fw.halo_dots(np.full((1080, 1920), 0.5, np.float32)))[..., None]
    return img


def bridge1_07(s, t, local, fi):
    from mv.core import clamp
    from . import fireworks as fw
    tilt = 120 + 380 * clamp(local / 2.2) ** 1.2
    img, hor = night_bay(tilt)
    # moon pulse: 8ths, then 16ths from 110.31; inhale at 111.05 (halftone coverage shrinks)
    sub = BEAT / 2 if t < 110.31 else BEAT / 4
    ph = ((t - 108.83) % sub) / sub
    pulse = np.exp(-ph * 4) * (0.7 if t < 111.05 else 0.3)
    can_h = 2000
    y0 = can_h - 1080 - int(tilt)
    img = moon_with_halo(img, 1320, 520 - y0 * 0.0 + (tilt - 120) * 0.9, 80, pulse)
    img = fw.rocket(img, t, 109.57, 111.05, 700, hor + 20, 760, 300 + (tilt - 120) * 0.5, '#F5C842')
    wall_y = (can_h - 166) - y0
    if wall_y < 1120:
        img = kit.dot_person(img, 520, wall_y, 70, t, colors=('#C9D3DC', '#F6F2E7', '#7FC8B8', '#1A1416'), run=False)
    ly = once('b107', lambda: VLyric(37, x=1720, accent='#D9402B'))
    return ly.draw(img, t)


R['B-bridge1-07'] = bridge1_07
tl.OWN_TYPE.add('B-bridge1-07')


def chorus3_08(s, t, local, fi):
    import cv2
    from mv.core import clamp
    from mv import text, lyrics
    from . import fireworks as fw
    from .print_fx import hexc as H
    k = clamp(local / (s['end'] - s['start']))
    e = 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
    tilt = 900 - 820 * e
    img, hor = night_bay(tilt)
    cy = 300 + (900 - tilt)
    img = fw.burst(img, t, 132.54, 960, cy, 620, 'willow', '#F5C842', '#FFF2C8', seed=21, life=3.0, n=120)
    # gold reflections on the sea as dotted columns from 134.02
    if t > 134.02 and hor < 1080:
        cols = np.zeros((1080, 1920), np.float32)
        a = clamp((t - 134.02) / 0.5)
        for x in range(420, 1520, 34):
            for y in range(max(hor + 8, 0), 1080, 14):
                cv2.circle(cols, (x + int(6 * np.sin(y * 0.1 + t * 4)), y), 3, a * (1 - (y - hor) / 600), -1, cv2.LINE_AA)
        img = img + (H('#F5C842')[None, None] - img) * np.clip(cols, 0, 1)[..., None]
    # L45 glyphs appear at spark tips per mora then droop and drip with the trail
    gt = once('gt45', lambda: __import__('json').load(open(tl.os.path.join(tl.ROOT, 'assets', 'glyph_times.json')))['45'])
    word = '君に幸せあげられない'
    for i, ch in enumerate(word):
        tg = gt[min(i, len(gt) - 1)]
        if t < tg:
            continue
        dt = t - tg
        ang = -np.pi / 2 + (i - 4.5) * 0.28
        x = 960 + np.cos(ang) * 420 + (i - 4.5) * 10
        y = cy + np.sin(ang) * 260 + 160 * dt * dt + 40 * dt
        if ch in '幸せ':
            y += 260 * dt * dt
        key = ('dripg', ch)
        if key not in _cache:
            gl, _ = text.layout_h(ch, 960, 540, 90, 'mincho', align='center')
            _cache[key], _ = text.render_glyphs(gl)
        f = _cache[key]
        if f is None or y > 1180:
            continue
        M = np.float32([[1, 0, x - 960], [0, 1, y - 540]])
        fm = cv2.warpAffine(f, M, (1920, 1080))
        drip = cv2.GaussianBlur(fm, (1, 21), 0) * 0.5
        img = img + (H('#F5C842')[None, None] - img) * drip[..., None]
        img = img + (H('#EDE3CF')[None, None] - img) * fm[..., None]
    # 円リレー 5: one last spark hangs on, drifts to the vanishing point and turns heat-orange (-> headlight)
    if t > 134.6:
        k = clamp((t - 134.6) / 0.85)
        e = 1 - (1 - k) ** 3
        x, y = 1180 + (954 - 1180) * e, 300 + (570 - 300) * e + 40 * np.sin(k * np.pi)
        col = H('#F5C842') + (H('#F08A3C') - H('#F5C842')) * k
        kit.halo(img, x, y, 40 + 10 * k, '#F5C842' if k < 0.5 else '#F08A3C', 0.9)
        m = np.zeros((1080, 1920), np.float32)
        cv2.circle(m, (int(x), int(y)), 7, 1.0, -1, cv2.LINE_AA)
        img = img + (col[None, None] - img) * m[..., None]
    a = clamp((t - 132.7) / 0.3)
    gl, _ = text.layout_h(lyrics.ZH[45], 960, 1010, 30, 'zh', tracking=0.2, align='center')
    f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a))
    if f is not None:
        img = img + (H('#EDE3CF')[None, None] - img) * f[..., None]
    return img


R['B-chorus3-08'] = chorus3_08
tl.OWN_TYPE.add('B-chorus3-08')


def _c305_plate():
    path = [{'t': 0.0, 'pos': [0.5, 2.2, 18.0], 'look': [0.0, 5.0, 40.0], 'fov': 52},
            {'t': 1.48, 'pos': [0.5, 24.0, 12.0], 'look': [0.0, 18.0, 60.0], 'fov': 52, 'ease': 'inout'},
            {'t': 2.96, 'pos': [0.5, 32.0, 10.0], 'look': [0.0, 40.0, 70.0], 'fov': 52, 'ease': 'inout'}]
    return plate('B-chorus3-05', 's3_festival', {'world': 'festival', 'litT': -10.0, 'shutterT': -10.0, 'crowdT': -10.0,
                                                 'crowd': 900, 'surround': True, 'path': path}, 0.0, 2.96, fps=24)


def chorus3_05(s, t, local, fi):
    from mv.core import clamp
    from . import fireworks as fw
    pl = once('c305', _c305_plate)
    img = pl.frame(local).copy()
    sky_shift = 260 * clamp(local / 2.96)
    img = fw.burst(img, t, 123.65, 560, 330 + sky_shift, 360, 'peony', '#D9402B', seed=31)
    img = fw.burst(img, t, 124.39, 1350, 280 + sky_shift, 460, 'chrysanthemum', '#F5C842', seed=32)
    img = fw.burst(img, t, 125.13, 820, 220 + sky_shift * 0.6, 300, 'ring', '#7FC8B8', seed=33)
    img = fw.glyph_burst(img, t, 125.87, 980, 360, 600, '君', '#F5C842')
    ly = once('c305ly', lambda: VLyric(42, x=1720, accent='#D9402B'))
    return ly.draw(img, t)


R['B-chorus3-05'] = chorus3_05
tl.OWN_TYPE.add('B-chorus3-05')


# ---------------------------------------------------------------- B-bridge1-01: the shotengai under the sea
def _b101_plate():
    path = [{'t': 0.0, 'pos': [0.0, 9.0, -6.0], 'look': [0.0, 14.0, 10.0], 'fov': 50},
            {'t': 0.9, 'pos': [0.0, 3.2, 0.0], 'look': [0.0, 3.0, 20.0], 'fov': 50, 'ease': 'out'},
            {'t': 2.96, 'pos': [0.0, 3.2, 2.1], 'look': [0.1, 3.1, 22.0], 'fov': 50, 'ease': 'linear'}]
    return plate('B-bridge1-01', 's3_festival', {'world': 'underwater', 'shutterT': 99.0, 'litT': None, 'floatT': 0.0,
                                                 'crowd': 0, 'path': path}, 0.0, 2.96, fps=24)


def bridge1_01(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text, lyrics
    from mva import fx
    from .print_fx import hexc as H
    pl = once('b101', _b101_plate)
    img = pl.frame(local).copy()
    # underwater sway + caustics (line-screen) + bubbles
    img = fx.water_refract(img, t, amp=4.0, scale=120.0, speed=0.6)
    ca = fx.caustics(t, 160, 0.7, 7.0)
    scr = (np.mod(kit._YS + kit._XS * 0.0, 7.0) < 2.5).astype(np.float32)
    img = img + (H('#7FC8B8')[None, None] - img) * (ca * scr * 0.35)[..., None]
    img = fx.bubbles(img, t, n=60, seed=8, rim='#BFF3FF', speed=140.0, amount=0.8)
    # surface with the moon above, seen at the start of the sink
    if local < 0.9:
        k = 1 - local / 0.9
        m = np.zeros((1080, 1920), np.float32)
        cv2.ellipse(m, (980 + int(20 * math.sin(t * 2)), int(160 - 300 * (1 - k))), (90, 70), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        m = fx.water_refract(np.repeat(m[..., None], 3, -1), t, 8.0, 60.0, 1.2)[..., 0]
        img = img + (H('#BFF3FF')[None, None] - img) * (m * k * 0.9)[..., None]
    # goldfish (2D, few) weaving between stalls
    for i in range(7):
        ph = i * 0.9
        x = (300 + i * 230 + 120 * math.sin(t * 0.8 + ph)) % 1920
        y = 640 + 120 * math.sin(t * 1.1 + ph * 2)
        ang = math.cos(t * 0.8 + ph)
        body = np.zeros((1080, 1920), np.float32)
        cv2.ellipse(body, (int(x), int(y)), (26, 12), math.degrees(math.atan2(0.3, ang)), 0, 360, 1.0, -1, cv2.LINE_AA)
        tail = np.array([[x - 24 * np.sign(ang), y], [x - 50 * np.sign(ang), y - 14], [x - 50 * np.sign(ang), y + 14]], np.int32)
        cv2.fillPoly(body, [tail], 1.0, cv2.LINE_AA)
        img = img + (H('#D9402B')[None, None] - img) * body[..., None]
    # bubble lyrics: one glyph per bubble, popping on the next mora (L30 闘えず息できず)
    gt = once('gt30', lambda: __import__('json').load(open(tl.os.path.join(tl.ROOT, 'assets', 'glyph_times.json')))['30'])
    word = '闘えず息できず'
    for i, ch in enumerate(word):
        tg = gt[min(i, len(gt) - 1)]
        tn = gt[i + 1] if i + 1 < len(gt) else tg + 0.6
        if not (tg <= t < tn + 0.12):
            continue
        rise = (t - tg) * 90
        x, y = 1180 + (i % 3) * 120 - 120, 760 - i * 70 - rise
        pop = clamp((t - tn) / 0.12)
        rb = int(64 * (1 + 0.4 * pop))
        ring = np.zeros((1080, 1920), np.float32)
        cv2.circle(ring, (int(x), int(y)), rb, 1.0, 3, cv2.LINE_AA)
        img = img + (H('#BFF3FF')[None, None] - img) * (ring * (1 - pop))[..., None]
        key = ('bub', ch)
        if key not in _cache:
            gl, _ = text.layout_h(ch, 960, 540, 78, 'mincho', align='center')
            _cache[key], _ = text.render_glyphs(gl)
        f = _cache[key]
        if f is not None:
            fm = cv2.warpAffine(f, np.float32([[1, 0, x - 960], [0, 1, y - 540]]), (1920, 1080))
            img = img + (H('#EDE3CF')[None, None] - img) * (fm * (1 - pop))[..., None]
    a = clamp((t - 88.2) / 0.3)
    gl, _ = text.layout_h(lyrics.ZH[30], 960, 1010, 30, 'zh', tracking=0.2, align='center')
    f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a))
    if f is not None:
        img = img + (H('#BFF3FF')[None, None] - img) * f[..., None]
    return img


R['B-bridge1-01'] = bridge1_01
tl.OWN_TYPE.add('B-bridge1-01')


# ---------------------------------------------------------------- map shots (S5)
def _coast(z):
    import math
    return 120 + 40 * math.sin(z / 140) + 18 * math.sin(z / 47 + 1)


def _map_gt(line):
    return once(f'gt{line}', lambda: __import__('json').load(open(tl.os.path.join(tl.ROOT, 'assets', 'glyph_times.json')))[str(line)])


def _zh_fixed(img, t, line, t_in, y=1012, size=30, ink='#1A1416', halo_col='#EDE3CF'):
    """Chinese line fixed to screen, with a paper-coloured halo so it reads over the map"""
    from mv.core import clamp
    from mv import text, lyrics
    from .print_fx import hexc as H
    a = clamp((t - t_in) / 0.3)
    if a <= 0:
        return img
    gl, _ = text.layout_h(lyrics.ZH[line], 960, y, size, 'zh', tracking=0.2, align='center')
    f, s = text.render_glyphs(gl, stroke=6.0, anim=lambda g: dict(alpha=a))
    if s is not None:
        img = img + (H(halo_col)[None, None] - img) * s[..., None]
    if f is not None:
        img = img + (H(ink)[None, None] - img) * f[..., None]
    return img


def _him_dot(img, x, y, t, k=1.0):
    """him on the map: a tiny printed dot-person inside a mint halftone halo with a lit core (reads at a glance)"""
    import cv2
    from .print_fx import hexc as H
    kit.halo(img, x, y - 10 * k, 66 * k, '#7FC8B8', 1.0)
    m = np.zeros((1080, 1920), np.float32)
    cv2.circle(m, (int(x), int(y - 10 * k)), int(17 * k), 1.0, -1, cv2.LINE_AA)
    img += (H('#0E1226')[None, None] - img) * (m * 0.85)[..., None]
    return kit.dot_person(img, x, y + 4 * k, 30 * k, t, colors=('#7FC8B8', '#F6F2E7', '#F08A3C', '#EDE3CF'))


# ---- B-chorus2-03: the town as a maze, top-down, turning a notch on every beat --------------------------------
C203_J = [(-30, 14), (-30, 50), (-30, 86), (6, 86), (42, 86), (42, 50), (6, 50), (6, 14), (-30, 14)]
C203_MARKS = [(-30, 86), (6, 122), (42, 86), (78, 50), (42, 14), (6, -22), (-30, 14), (-66, 50), (6, 50), (-30, -22),
              (42, 122), (-66, 86)]
C203_MIRRORS = [(-66, 14), (78, 86), (-30, 122), (42, -22), (78, 14)]


def _c203_angle(tt):
    import math
    from mv.core import clamp
    nb = tt / BEAT
    whole = math.floor(nb + 1e-6)
    if whole < 1:
        return 0.0
    frac = clamp((tt - whole * BEAT) / (5 / 24))
    return 22.5 * (whole - 1 + frac * frac * (3 - 2 * frac))


def _c203_plate():
    import math
    s = tl.BY_ID['B-chorus2-03']
    d = s['end'] - s['start']
    cx, cz = 6.0, 50.0
    path = []
    for i in range(int(round(d * 24)) + 1):
        tt = i / 24
        a = math.radians(_c203_angle(tt))
        h = 170 - 42 * min(1.0, tt / d)
        path.append({'t': tt, 'pos': [cx, h, cz], 'look': [cx + 0.4 * math.sin(a), 0.0, cz + 0.4 * math.cos(a)], 'fov': 62,
                     'ease': 'linear'})
    pts, times = [list(C203_J[0])], [0.0]
    for b in range(4):
        tb = b * BEAT
        pts += [list(C203_J[2 * b]), list(C203_J[2 * b + 1]), list(C203_J[2 * b + 2])]
        times += [tb + 0.14, tb + 0.44, tb + 0.74]
    params = {'world': 'night', 'path': path, 'route': [[0, 0], [3, 0]], 'land': '#141A33', 'sea': '#1E2550',
              'seaShade': '#0E1226', 'road': '#C9D3DC', 'blocks': ['#1E2550', '#2C4C9A', '#232B57'], 'blockShade': '#0E1226',
              'window': '#F08A3C', 'litP': 0.012, 'vend': 160, 'routeColor': '#EDE3CF', 'routeOff': '#EDE3CF', 'rings': True,
              'moonPath': {'z': 50, 'len': 800, 'w': 70, 'color': '#C9D3DC', 'str': 0.9},
              'beam': {'speed': 25, 'len': 900, 'width': 160, 'color': '#C9D3DC', 'str': 0.55, 'phase': 64.5},
              'reroute': {'beats': [0.0, BEAT, 2 * BEAT, 3 * BEAT], 'frac': 0.17, 'seed': 3},
              'walker': {'pts': pts, 'times': times},
              'marks': [list(m) for m in C203_MARKS + C203_MIRRORS], 'fogNear': 2000, 'fogFar': 4000}
    return plate('B-chorus2-03', 's5_map', params, 0.0, d, fps=24)


def chorus2_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp, back_out
    pl = once('c203', _c203_plate)
    img = pl.frame(local).copy()
    # streets ripple like water (gentle, whole print)
    dx = np.sin(kit._YS / 60.0 + t * 3.0) * 4.0
    dy = np.cos(kit._XS / 70.0 + t * 2.6) * 4.0
    img = cv2.remap(img, kit._XS + dx, kit._YS + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    mk, mn = pl.anchor(local, 'marks') or [], pl.anchor(local, 'marksN') or []
    # noon flashes in the corner mirrors on the off-beats
    ob = (local - BEAT / 2) % BEAT
    if local > BEAT / 2 and ob < 4 / 24:
        k = 1.0 - ob / (4 / 24)
        for p in mk[len(C203_MARKS):]:
            kit.halo(img, p[0], p[1], 46 * (0.6 + 0.4 * k), '#F5C842', 0.95 * k)
            m = np.zeros((1080, 1920), np.float32)
            cv2.circle(m, (int(p[0]), int(p[1])), int(9 + 5 * k), 1.0, -1, cv2.LINE_AA)
            img += (np.array([0.96, 0.78, 0.26], np.float32)[None, None] - img) * (m * k)[..., None]
    # map rotation on screen, measured from the projected north of the first junction
    rot = 0.0
    if mk and mn:
        v = (mn[0][0] - mk[0][0], mn[0][1] - mk[0][1])
        rot = -math.degrees(math.atan2(v[0], -v[1]))
    # him: a dot-person with a mint halo walking the loop
    w = pl.anchor(local, 'walker')
    if w:
        img = _him_dot(img, w[0][0], w[0][1], t, 1.0)
    # L28 as map labels popping at junctions per mora; 迷 at the centre stays upright while the map turns
    gt = _map_gt(28)
    for i, ch in enumerate('ヒートウェイブに迷うのさ'):
        if i >= len(mk) or t < gt[i]:
            continue
        k = clamp((t - gt[i]) / (4 / 24))
        sc = 0.35 + 0.65 * back_out(k, 2.2)
        ang = 0.0 if ch == '迷' else rot
        kit.map_glyph(img, ch, mk[i][0], mk[i][1], 86 if ch != '迷' else 118, ang, sc, '#F6F2E7', '#1E2550', 10.0)
    return _zh_fixed(img, t, 28, s['start'] + 0.3, ink='#EDE3CF', halo_col='#141A33')


R['B-chorus2-03'] = chorus2_03
tl.OWN_TYPE.add('B-chorus2-03')


# ---- B-chorus4-01: blue-hour map, the headlight running the coast line to the lighthouse -------------------------
def _c401_plate():
    s = tl.BY_ID['B-chorus4-01']
    d = s['end'] - s['start']
    k0, k1 = 0.58, 0.97
    path = []
    for i in range(5):
        u = i / 4
        k = k0 + (k1 - k0) * u
        z = -800 + 1600 * (0.05 + 0.85 * k)
        x = _coast(z) - 22
        h = 210 - 21 * u
        path.append({'t': d * u, 'pos': [x - 170, h, z - 190], 'look': [x, 0, z + 40], 'fov': 40, 'ease': 'linear'})
    gt = _map_gt(50)
    lt = [g - s['start'] for g in gt[:6]]
    wz = [548, 572, 596]
    params = {'world': 'dawn', 'path': path, 'route': [[0, k0], [d, k1]], 'headDot': True, 'headColor': '#F08A3C',
              'headSize': 60, 'land': '#22346C', 'sea': '#1E2550', 'seaShade': '#141A33', 'road': '#41558F',
              'blocks': ['#2C4C9A', '#1E2550', '#2A3F80'], 'blockShade': '#141A33', 'window': '#F08A3C', 'litP': 0.4,
              'windowsOffSteps': [BEAT, 2 * BEAT, 3 * BEAT], 'routeColor': '#EDE3CF', 'routeOff': '#C9D3DC', 'rings': True,
              'ringColor': '#EDE3CF', 'fogColor': '#7C86BE', 'fogNear': 260, 'fogFar': 1300, 'lampColor': '#F7E3C2',
              'beam': {'speed': 38, 'len': 650, 'width': 150, 'color': '#F7E3C2', 'str': 0.75, 'phase': 140},
              'labelT': lt, 'walker': {'pts': [[_coast(z) - 5, z] for z in wz], 'times': [0.0, d / 2, d]}}
    return plate('B-chorus4-01', 's5_map', params, 0.0, d, fps=24)


def chorus4_01(s, t, local, fi):
    import cv2
    from mv.core import clamp, back_out
    pl = once('c401', _c401_plate)
    img = pl.frame(local).copy()
    gt = _map_gt(50)
    # his dot-person on the seawall, walking toward the lighthouse
    w = pl.anchor(local, 'walker')
    if w and 0 < w[0][2] < 1:
        img = _him_dot(img, w[0][0], w[0][1], t, 0.75)
    # 思い浮かぶの: one label per mora, pinned to the railway where the headlight is when it is sung
    lab = pl.anchor(local, 'labels') or []
    for i, ch in enumerate('思い浮かぶの'):
        if i >= len(lab) or t < gt[i] or not (0 < lab[i][2] < 1):
            continue
        x, y = lab[i][0], lab[i][1]
        k = clamp((t - gt[i]) / (4 / 24))
        m = np.zeros((1080, 1920), np.float32)
        cv2.line(m, (int(x), int(y)), (int(x + 18), int(y - 46 * k)), 1.0, 3, cv2.LINE_AA)
        img += (np.array([0.10, 0.08, 0.09], np.float32)[None, None] - img) * m[..., None]
        kit.halo(img, x, y, 16, '#F08A3C', 0.9 * (1 - 0.5 * k))
        kit.map_glyph(img, ch, x + 22, y - 46 * k - 40, 70, 0.0, 0.35 + 0.65 * back_out(k, 2.2), '#F6F2E7', '#1E2550', 7.0)
    # 君ばかり: a vertical label that pops at the lighthouse
    lh = pl.anchor(local, 'lighthouse')
    if lh and 0 < lh[0][2] < 1:
        x, y = lh[0][0], lh[0][1]
        for j, ch in enumerate('君ばかり'):
            i = 6 + j
            if t < gt[i]:
                continue
            k = clamp((t - gt[i]) / (4 / 24))
            kit.map_glyph(img, ch, x + 70, y - 30 + j * 74, 70 if j else 84, 0.0, 0.35 + 0.65 * back_out(k, 2.2),
                          '#F6F2E7', '#D9402B' if j == 0 else '#1E2550', 7.0)
    return _zh_fixed(img, t, 50, 147.5, ink='#EDE3CF', halo_col='#141A33')


R['B-chorus4-01'] = chorus4_01
tl.OWN_TYPE.add('B-chorus4-01')



# ---- B-bridge2-01: the dream train comes in (二色夢刷り two-ink riso world) ------------------------------------------
def _quad_sorted(pts):
    """projected quad -> TL, TR, BR, BL (screen space), robust to the mirrored scene"""
    p = sorted([q[:2] for q in pts], key=lambda q: q[1])
    top = sorted(p[:2], key=lambda q: q[0])
    bot = sorted(p[2:], key=lambda q: q[0])
    return np.float32([top[0], top[1], bot[1], bot[0]])


def led_on_quad(img, quad, rgb_board, alpha=1.0):
    """warp a flat LED board image onto a projected quad (perspective)"""
    import cv2
    h, w = rgb_board.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    M = cv2.getPerspectiveTransform(src, quad)
    warped = cv2.warpPerspective(rgb_board, M, (1920, 1080), flags=cv2.INTER_LINEAR)
    m = cv2.warpPerspective(np.ones((h, w), np.float32), M, (1920, 1080), flags=cv2.INTER_LINEAR) * alpha
    return img + (warped - img) * m[..., None]


def _b201_plate():
    s = tl.BY_ID['B-bridge2-01']
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [-0.4, 0.76, 37.0], 'look': [-0.3, 3.4, -40.0], 'fov': 44},
            {'t': d, 'pos': [-0.4, 0.76, 36.65], 'look': [-0.3, 3.4, -40.0], 'fov': 43.6, 'ease': 'linear'}]
    return plate('B-bridge2-01', 's4_station', {
        'world': 'dream', 'path': path, 'trackL': 1400, 'endBoard': True,
        'train': {'zStop': 20.5, 'D': 520.0, 'T': 2.5, 'p': 3, 't0': 0.0},
        'trainOpts': {'bigBoard': True, 'boardSize': [2.4, 0.75, 3.0], 'body': '#EDE3CF', 'band': '#F08A3C',
                      'headColor': '#F08A3C', 'headSize': 4.5},
        'stationName': '潮見', 'stationRoman': 'SHIOMI'}, 0.0, d, fps=24)


def bridge2_01(s, t, local, fi):
    import math
    from mv.core import clamp
    from . import print_fx
    pl = once('b201', _b201_plate)
    img = pl.frame(local).copy()
    bq = pl.anchor(local, 'board')
    hd = pl.anchor(local, 'head')
    scale = 0.0
    if bq and all(0 < q[2] < 1 for q in bq):
        quad = _quad_sorted(bq)
        scale = float(quad[1][0] - quad[0][0]) / 600.0
        if quad[1][0] - quad[0][0] > 6:
            if t < 136.24:
                brd, _ = print_fx.led_board(' 夢 行', cols=51, rows=16, dot=12, on='#F08A3C', off='#3A2A20', bg='#1A1416')
            else:
                sc = math.floor((t - 136.24) * 24) * 3 - 51
                brd, _ = print_fx.led_board('君はどんな夢のなかに', cols=51, rows=16, dot=12, on='#F08A3C', off='#3A2A20',
                                            bg='#1A1416', scroll=sc)
            img = led_on_quad(img, quad, brd)
    # headlight: AM halftone glow, breathing on beats (and with distance)
    if hd and 0 < hd[0][2] < 1:
        ph = ((t - 0.682) / BEAT) % 1.0
        breath = 1.0 + 0.22 * math.exp(-ph * 5.0) + (0.25 * clamp((t - 136.98) / 0.3) * math.exp(-((t - 136.98) % BEAT) * 3.0))
        r = (46 + 520 * min(1.0, scale)) * breath
        kit.halo(img, hd[0][0], hd[0][1], r, '#F08A3C', 1.0, period=12.0)
    img = print_fx.two_ink(img, mis=(2.0 + 0.6 * math.sin(t * 1.3), -1.0))
    ly = once('b201_ly', lambda: VLyric(46, x=1832, color='#2C4C9A', accent='#F08A3C'))
    return ly.draw(img, t)


R['B-bridge2-01'] = bridge2_01
tl.OWN_TYPE.add('B-bridge2-01')


# ---- B-chorus4-05: the build -- the headlight runs the rails at us, glow doubling on every beat ----------------------
def _c405_plate():
    s = tl.BY_ID['B-chorus4-05']
    d = s['end'] - s['start']
    # camera low between the rails, aimed at where the headlight ends (15 m out): the light climbs from the
    # horizon to the centre of frame as it comes -- the sunrise in miniature
    path = [{'t': 0.0, 'pos': [0.0, 0.45, 40.0], 'look': [0.0, 1.4, 25.0], 'fov': 40},
            {'t': d, 'pos': [0.0, 0.45, 40.0], 'look': [0.0, 1.4, 25.0], 'fov': 40, 'ease': 'linear'}]
    return plate('B-chorus4-05', 's4_station', {
        'world': 'predawn', 'path': path, 'trackL': 1400, 'noStation': True, 'poles': True,
        'train': {'zStop': 16.0, 'D': 385.0, 'T': d, 'p': 1.6, 't0': 0.0},
        'trainOpts': {'bigBoard': True, 'boardSize': [2.4, 0.75, 3.0], 'body': '#C9D3DC', 'band': '#F08A3C',
                      'headColor': '#F5C842', 'headSize': 4.0}}, 0.0, d, fps=24)


def chorus4_05(s, t, local, fi):
    import math
    import cv2
    from mv.core import clamp
    from . import print_fx
    pl = once('c405', _c405_plate)
    img = pl.frame(local).copy()
    bq = pl.anchor(local, 'board')
    hd = pl.anchor(local, 'head')
    nb = (t - s['start']) / BEAT
    r = 42.0 * 2.0 ** min(nb, 3.0)                 # AM glow radius doubles on 159.94 / 160.68 / 161.42
    if nb > 3.0:
        r *= 1.0 + 9.0 * (nb - 3.0) ** 2.2         # ...then floods the frame by 162.17 (relay to the sun)
    r *= 1.0 + 0.18 * math.exp(-(nb % 1.0) * 6.0)
    x = y = None
    lamp = 5.0
    if bq and all(0 < q[2] < 1.001 for q in bq):
        lamp = max(5.0, abs(bq[0][0] - bq[1][0]) * 0.067 * 2.2)      # lamp disc ~ 0.16 m, bloomed
    if hd and 0 < hd[0][2] < 1.001:
        x, y = hd[0][0], hd[0][1]
        kit.halo(img, x, y, r * 1.25, '#F08A3C', 0.9, period=max(8.0, min(26.0, r / 18)))
        kit.halo(img, x, y, r * 0.7, '#F5C842', 1.0, period=max(8.0, min(24.0, r / 22)))
    if bq and all(0 < q[2] < 1.001 for q in bq):
        quad = _quad_sorted(bq)
        bw = float(quad[1][0] - quad[0][0])
        if bw > 4:
            # the car's front printed as a flat night-ink silhouette over the glow (extrapolated from the board quad)
            TL, TR, BR, BL = quad
            def at(u, v):      # u: -1..1 across the board, v: +1 top .. -1 bottom of the board
                top = TL + (TR - TL) * (u + 1) / 2
                bot = BL + (BR - BL) * (u + 1) / 2
                return top + (bot - top) * (1 - v) / 2
            fr = np.float32([at(-1.167, 1.333), at(1.167, 1.333), at(1.167, -5.867), at(-1.167, -5.867)])
            m = np.zeros((1080, 1920), np.float32)
            cv2.fillConvexPoly(m, fr.astype(np.int32), 1.0, cv2.LINE_AA)
            fade = clamp((bw - 6) / 30) * (1 - clamp((nb - 3.55) / 0.35))
            img += (print_fx.hexc('#141A33')[None, None] - img) * (m * fade)[..., None]
            for u0, u1 in ((-0.95, -0.07), (0.07, 0.95)):       # windshield panes catching the dawn
                wq = np.float32([at(u0, -1.25), at(u1, -1.25), at(u1, -2.75), at(u0, -2.75)])
                m = np.zeros((1080, 1920), np.float32)
                cv2.fillConvexPoly(m, wq.astype(np.int32), 1.0, cv2.LINE_AA)
                img += (print_fx.hexc('#5A6AA8')[None, None] - img) * (m * fade)[..., None]
            if t < 159.94:
                brd, _ = print_fx.led_board('  夢  ', cols=51, rows=16, dot=12, on='#F08A3C', off='#3A2A20', bg='#141018')
            else:
                top, _ = print_fx.led_board('日の出', cols=51, rows=16, dot=12, on='#F5C842', off='#3A3420', bg='#141018')
                sc = math.floor((t - 159.94) * 24)
                bot, _ = print_fx.led_board('SUNRISE  SUNRISE  ', cols=51, rows=10, dot=12, on='#F08A3C', off='#3A2A20',
                                            bg='#141018', font='silk', scroll=sc % 120)
                brd = np.concatenate([top, bot], 0)
            img = led_on_quad(img, quad, brd, alpha=fade if bw > 10 else 1.0)
    if x is not None:
        m = np.zeros((1080, 1920), np.float32)
        sun = clamp((nb - 3.35) / 0.65) ** 1.6          # the lamp becomes the sun disc in the last half-beat
        cv2.circle(m, (int(x), int(y)), int(lamp + (400 - lamp) * sun), 1.0, -1, cv2.LINE_AA)
        img += (print_fx.hexc('#FFF2C8')[None, None] - img) * m[..., None]
    ly = once('c405_ly', lambda: VLyric(54, x=1720, accent='#F08A3C',
                                        snap=lambda tc: 3.0 - 2.0 * clamp((tc - 159.3) / (161.42 - 159.3))))
    return ly.draw(img, t)


R['B-chorus4-05'] = chorus4_05
tl.OWN_TYPE.add('B-chorus4-05')


# ---- shared: the stamp card lying on the chabudai, seen from a high angle --------------------------------------------
TABLE_PAD = (700, 520)          # table margin around the card, in card px


def card_on_table(card, cx, cy, zoom, tilt=0.30, table='#1A1E3A', wood='#232B57', with_mask=False):
    """flat top-down view of the card on the dark table, then a keystone so the far edge recedes (high angle).
    cx, cy, zoom in card coordinates as card.view; tilt = how much narrower the far edge is (fraction)."""
    import cv2
    from . import card as C
    from .print_fx import hexc as H
    key = ('table', table, wood)
    if key not in _cache:
        tw, th = C.CW + 2 * TABLE_PAD[0], C.CH + 2 * TABLE_PAD[1]
        ys, xs = np.mgrid[0:th // 4, 0:tw // 4].astype(np.float32)
        grain = 0.5 + 0.5 * np.sin(ys / 3.0 + 2.5 * np.sin(xs / 90.0) + 0.6 * np.sin(xs / 23.0))
        base = H(table)[None, None] + (H(wood) - H(table))[None, None] * (grain[..., None] * 0.6)
        _cache[key] = cv2.resize(base.astype(np.float32), (tw, th), interpolation=cv2.INTER_LINEAR)
        sh = np.zeros((th, tw), np.float32)
        sh[TABLE_PAD[1] + 30:TABLE_PAD[1] + C.CH + 30, TABLE_PAD[0] + 24:TABLE_PAD[0] + C.CW + 24] = 1
        _cache[key + ('sh',)] = cv2.GaussianBlur(sh, (0, 0), 18) * 0.55
    tab, sh = _cache[key], _cache[key + ('sh',)]
    full = tab * (1 - sh[..., None])
    full[TABLE_PAD[1]:TABLE_PAD[1] + C.CH, TABLE_PAD[0]:TABLE_PAD[0] + C.CW] = card
    ow, oh = 2400, 1350                             # flat view, bigger than the frame so the keystone has margin
    s = ow / C.CW * zoom
    M = cv2.getRotationMatrix2D((cx + TABLE_PAD[0], cy + TABLE_PAD[1]), 0.0, s)
    M[0, 2] += ow / 2 - (cx + TABLE_PAD[0])
    M[1, 2] += oh / 2 - (cy + TABLE_PAD[1])
    flat = cv2.warpAffine(full, M, (ow, oh), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    m = tilt * ow / 2
    scr = np.float32([[0, 0], [1920, 0], [1920, 1080], [0, 1080]])
    src = np.float32([[0, 0], [ow, 0], [ow - m, oh], [m, oh]])
    Hm = cv2.getPerspectiveTransform(scr, src)
    out = cv2.warpPerspective(flat, Hm, (1920, 1080), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    if with_mask:
        cm = np.zeros(full.shape[:2], np.float32)
        cm[TABLE_PAD[1]:TABLE_PAD[1] + C.CH, TABLE_PAD[0]:TABLE_PAD[0] + C.CW] = 1
        cmf = cv2.warpAffine(cm, M, (ow, oh), flags=cv2.INTER_LINEAR)
        tf = cv2.warpAffine(tab, M, (ow, oh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        mask = cv2.warpPerspective(cmf, Hm, (1920, 1080), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        table_img = cv2.warpPerspective(tf, Hm, (1920, 1080), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)

    def to_screen(px, py):        # card px -> screen px (for overlays that must sit on the card)
        fx_ = (px + TABLE_PAD[0] - (cx + TABLE_PAD[0])) * s + ow / 2
        fy_ = (py + TABLE_PAD[1] - (cy + TABLE_PAD[1])) * s + oh / 2
        Hinv = np.linalg.inv(Hm)
        v = Hinv @ np.array([fx_, fy_, 1.0])
        return v[0] / v[2], v[1] / v[2]
    if with_mask:
        return out, to_screen, mask, table_img
    return out, to_screen


def stamp_ring_layer(word, n, center, radius, size=84, dry=(), seed=5, start_deg=-90.0, span=330.0):
    """rubber-stamped glyphs around a circle (date-stamp ring) as an RGBA card layer; uneven pressure"""
    import cv2
    import skia
    from . import card as C
    key = ('ring', word, n, center, radius, size, tuple(dry))
    if key in _cache:
        return _cache[key]
    rng = np.random.default_rng(seed)
    jit = rng.uniform(-4, 4, len(word))
    press = rng.uniform(0.72, 0.95, len(word))

    def draw(c):
        for i, ch in enumerate(word[:n]):
            a = math.radians(start_deg + span * i / max(1, len(word) - 1))
            x, y = center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)
            c.save()
            c.translate(x, y)
            c.rotate(math.degrees(a) + 90 + jit[i])
            alpha = 0.25 if ch in dry else press[i]
            C._text(c, ch, 0, size * 0.36, size, C.VERM, 'mincho', alpha=alpha)
            c.restore()
    import math
    lay = C._layer(draw)
    sp = (rng.random((C.CH // 3, C.CW // 3)) > 0.22).astype(np.float32)
    sp = cv2.resize(sp, (C.CW, C.CH), interpolation=cv2.INTER_NEAREST)
    lay[..., 3] *= sp
    if len([k for k in _cache if isinstance(k, tuple) and k[0] == 'ring']) > 12:
        for k in [k for k in _cache if isinstance(k, tuple) and k[0] == 'ring']:
            del _cache[k]
    _cache[key] = lay
    return lay


def channel_flip(img, t, t0, t1, seed=0):
    """チャンネル送り: a 2-frame halftone static band, then the picture rolls up with a black blanking bar"""
    import cv2
    if t < t0 or t > t1:
        return img
    k = (t - t0) / max(1e-6, t1 - t0)
    fr = int((t - t0) * 24)
    out = img
    if fr < 2 or k > 0.55:
        st = tv_static(seed * 31 + fr, 1080 // 2, 1920 // 2)
        st = cv2.resize(st, (1920, 1080), interpolation=cv2.INTER_NEAREST)
        rng = np.random.default_rng(seed * 7 + fr)
        y0 = int(rng.uniform(0, 760))
        band = np.zeros((1080, 1), np.float32)
        band[y0:y0 + int(rng.uniform(180, 320))] = 1
        out = out * (1 - band[..., None]) + st * band[..., None]
    roll = int(1080 * (k ** 1.6))
    if roll:
        out = np.roll(out, -roll, axis=0)
        out[max(0, 1080 - roll - 40):max(0, 1080 - roll), :] *= 0.08
    return out


# ---- B-chorus1-07: back at night -- the stamp card, the empty sixth circle, a sun that cannot rise -------------------
def chorus1_07(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import card as C
    from .print_fx import hexc as H
    # the paper-cut sun tries twice and fails: rises 30% on 50.31 and slips back, again on 51.05, flickers out 51.79
    def bump(t0, peak, up=0.30, down=0.42):
        if t < t0:
            return 0.0
        if t < t0 + up:
            return peak * _ease_io((t - t0) / up)
        return peak * (1 - _ease_io(clamp((t - t0 - up) / down)))
    sun = max(bump(50.31, 0.42), bump(51.05, 0.47))
    if 51.79 <= t < 52.05:
        sun = 0.38 if int((t - 51.79) * 24) % 2 == 0 else 0.0
    gt = _map_gt(17)
    n = sum(1 for g in gt if t >= g)
    key = ('c107card', round(sun, 3), n)
    if key not in _cache:
        for k in [k for k in _cache if isinstance(k, tuple) and k[0] == 'c107card']:
            del _cache[k]
        card = C.render_card(stamp_k=(1, 1, 1, 1, 1), sun_k=sun, glow_k=0.0, footer_n=0)
        x6, y6, _ = C.CIRCLES[5]
        lay = stamp_ring_layer('君に幸せあげられない', n, (x6, y6), C.R0 + 92, 112, dry=('幸', 'せ'), start_deg=-208.0,
                               span=236.0)
        a = lay[..., 3:4]
        card = card * (1 - a) + lay[..., :3] * a
        _cache[key] = card
    card = _cache[key]
    k = clamp(local / (s['end'] - s['start']))
    zoom = 1.45 * (1 + 0.10 * _ease_io(k))                        # 10% push toward the sixth circle
    cx, cy = 2330 + 120 * k, 820 - 40 * k
    img, to_s = card_on_table(card, cx, cy, zoom, tilt=0.28)
    # night: the room is lit only by the CRT -- navy multiply with a mint key from the left
    xs, ys = kit._XS / 1920, kit._YS / 1080
    key_l = np.clip(1.15 - 0.9 * xs - 0.25 * ys, 0, 1)[..., None]
    img = img * (0.16 + 0.58 * key_l) * (H('#C9D3DC') * 0.5 + H('#7FC8B8') * 0.5)[None, None] * 1.2
    img = img + (H('#141A33')[None, None] - img) * (0.35 * (1 - key_l))
    # CRT colour wash: a new channel colour sweeps across the card on every beat
    cols = ['#7FC8B8', '#D9402B', '#2C4C9A', '#F5C842']
    nb = (t - 0.682) / BEAT
    bi, ph = int(math.floor(nb)), nb % 1.0
    band = np.exp(-((xs - (-0.3 + 1.6 * ph)) / 0.22) ** 2) * 0.32 * (1 - ph * 0.5)
    img = img + (H(cols[bi % 4])[None, None] - img) * band[..., None]
    # fan shadow: three blurred blades turning slowly, top-left
    ang = t * 2.2
    th = np.arctan2(ys * 1080 + 260, xs * 1920 + 300)
    blades = (np.cos(3 * (th - ang)) > 0.55).astype(np.float32)
    rr = np.sqrt((xs * 1920 + 300) ** 2 + (ys * 1080 + 260) ** 2)
    fan = cv2.GaussianBlur(blades * (rr < 1300), (0, 0), 22) * 0.22
    img = img * (1 - fan[..., None])
    # dashed-circle pulse on beats, on the card
    x6, y6, _ = C.CIRCLES[5]
    sx, sy = to_s(x6, y6)
    ex, _ = to_s(x6 + C.R0, y6)
    rpx = abs(ex - sx)
    pk = math.exp(-ph * 4.0)
    m = np.zeros((1080, 1920), np.float32)
    rr2 = rpx * (1.0 + 0.25 * ph)
    for j in range(24):
        a0 = j * 15
        cv2.ellipse(m, (int(sx), int(sy)), (int(rr2), int(rr2 * 0.86)), 0, a0, a0 + 8, 1.0, 5, cv2.LINE_AA)
    img = img + (H('#EDE3CF')[None, None] - img) * (m * 0.7 * pk)[..., None]
    img = _zh_fixed(img, t, 17, 49.66, ink='#EDE3CF', halo_col='#141A33')
    return channel_flip(img, t, 52.20, 52.53, seed=17)


R['B-chorus1-07'] = chorus1_07
tl.OWN_TYPE.add('B-chorus1-07')


# ---- B-outro-07: the sun lands in the sixth circle like a hanko; the card is complete ---------------------------------
def sun_stamp_layer():
    """the sixth stamp: vermilion double ring, yellow core, short rays; rubber speckle (RGBA card layer)"""
    import cv2, math
    from . import card as C
    if 'sun_stamp' in _cache:
        return _cache['sun_stamp']
    x, y, _ = C.CIRCLES[5]
    r = C.R0 * 0.93

    def draw(c):
        c.drawCircle(x, y, r * 0.98, C._paint(C.VERM, 1.0, stroke=16))
        c.drawCircle(x, y, r * 0.82, C._paint(C.VERM, 1.0, stroke=6))
        c.drawCircle(x, y, r * 0.46, C._paint(C.SUN, 1.0))
        c.drawCircle(x, y, r * 0.46, C._paint(C.VERM, 1.0, stroke=7))
        for k in range(12):
            a = k * math.pi / 6
            c.drawLine(x + math.cos(a) * r * 0.56, y + math.sin(a) * r * 0.56, x + math.cos(a) * r * 0.72,
                       y + math.sin(a) * r * 0.72, C._paint(C.VERM, 1.0, stroke=12))
    lay = C._layer(draw)
    rng = np.random.default_rng(66)
    sp = (rng.random((C.CH // 3, C.CW // 3)) > 0.12).astype(np.float32)
    lay[..., 3] *= cv2.resize(sp, (C.CW, C.CH), interpolation=cv2.INTER_NEAREST)
    _cache['sun_stamp'] = lay
    return lay


def outro_07(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import card as C
    from .print_fx import hexc as H
    x6, y6, _ = C.CIRCLES[5]
    # card art: five full stamps + the sun stamp (slam: ink spread for the first frames) + footers
    slam = clamp(local / (3 / 24))
    old = 'YOU KNOW THAT I\'M NEVER GONNA LOSE'
    words = ['HEAT', 'WAVES', 'BEEN', 'FAKIN\'', 'ME', 'OUT']
    gt = _map_gt(61)
    new = ''
    for i, w_ in enumerate(words):
        if t >= gt[i]:
            nl = min(len(w_), int((t - gt[i]) / (BEAT / 8)) + 1)      # letters within a word on 32nds
            new += (' ' if new else '') + w_[:nl]
    old_a = 1.0 - clamp((t - 180.15) / (181.6 - 180.15))
    key = ('o07card', round(slam, 2), new, round(old_a, 2))
    if key not in _cache:
        for k in [k for k in _cache if isinstance(k, tuple) and k[0] == 'o07card']:
            del _cache[k]
        card = C.render_card(stamp_k=(1, 1, 1, 1, 1), footer_n=0)
        lay = sun_stamp_layer()
        a0 = lay[..., 3]
        card = card * (1 - a0[..., None]) + lay[..., :3] * a0[..., None]
        if slam < 1:                       # ink spread on impact: a fatter, wetter stamp that settles
            a1 = cv2.dilate(a0, np.ones((9, 9), np.uint8), iterations=int(round(3 * (1 - slam))))
            spread = np.clip(a1 - a0, 0, 1) * 0.85
            card = card + (H(C.VERM)[None, None] - card) * spread[..., None]
        L = C._layer(lambda c: (C._text(c, old, 1600, 1440, 64, C.NAVY, 'mincho', tracking=0.4, alpha=old_a * 0.9)))
        card = card * (1 - L[..., 3:4]) + L[..., :3] * L[..., 3:4]
        if new:
            # letterpress: dark bite on the lower-right, light on the upper-left, then the ink
            for dx, dy, col, al in ((3, 3, '#B9A98C', 0.9), (-2, -2, '#FFF8EA', 0.8), (0, 0, C.VERM, 1.0)):
                L = C._layer(lambda c, dx=dx, dy=dy, col=col, al=al: C._text(c, new, 1600 + dx, 1440 + dy, 64, col,
                                                                              'mincho', tracking=0.4, alpha=al))
                card = card * (1 - L[..., 3:4]) + L[..., :3] * L[..., 3:4]
        _cache[key] = card
    card = _cache[key]
    # camera: hold on the sixth circle at x2.2 (relay landing), pull back from 180.68 to the whole card
    k = _ease_io(clamp((t - 180.68) / (181.95 - 180.68)))
    zoom = 2.2 + (0.92 - 2.2) * k
    cx, cy = x6 + (1600 - x6) * k, y6 + (900 - y6) * k
    if slam < 1:                           # the hanko press: a little overshoot of scale on impact
        zoom *= 1.0 + 0.06 * (1 - slam)
    img, to_s, cm, table = card_on_table(card, cx, cy, zoom, tilt=0.0, table='#8A4A26', wood='#B8632F', with_mask=True)
    # paper flutter on the free edge (right), lifting on 182.17
    lift = clamp((t - 182.17) / 0.5)
    lx, _ = to_s(0, 0)
    rx, _ = to_s(C.CW, 0)
    u = np.clip((kit._XS - lx) / max(1.0, rx - lx), 0, 1)
    wgt = np.clip((u - 0.62) / 0.38, 0, 1) ** 2
    amp = (5.0 + 30.0 * lift) * wgt
    dy = amp * np.sin(2 * np.pi * (u * 1.7 - 2.4 * t)) - 26.0 * lift * wgt
    mapy = (kit._YS - dy).astype(np.float32)
    cardimg = cv2.remap(img, kit._XS, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    cmw = cv2.remap(cm, kit._XS, mapy, cv2.INTER_LINEAR)
    shade = 1.0 + 0.010 * np.gradient(dy, axis=1) * 8 * wgt
    cardimg = cardimg * np.clip(shade, 0.8, 1.15)[..., None]
    shadow = cv2.GaussianBlur(np.roll(cmw, (int(8 + 18 * lift), int(10 + 12 * lift)), (0, 1)), (0, 0), 6 + 10 * lift) * 0.45
    base = table * (1 - shadow[..., None])
    img = base * (1 - cmw[..., None]) + cardimg * cmw[..., None]
    # warm dawn light from the upper right + halftone glare
    xs, ys = kit._XS / 1920, kit._YS / 1080
    warm = np.clip(0.55 + 0.6 * xs - 0.35 * ys, 0, 1.15)[..., None]
    img = img * (0.72 + 0.32 * warm) * np.array([1.04, 0.98, 0.90], np.float32)
    kit.halo(img, 1980, -60, 760, '#F5C842', 0.45, period=14.0)
    # impact: a dot burst out of the circle (vermilion + sun yellow), 10 frames
    sx, sy = to_s(x6, y6)
    ex, _ = to_s(x6 + C.R0, y6)
    rp = abs(ex - sx)
    if local < 0.5:
        kb = local / 0.5
        rng = np.random.default_rng(7)
        m1 = np.zeros((1080, 1920), np.float32)
        m2 = np.zeros((1080, 1920), np.float32)
        for j in range(70):
            a = rng.uniform(0, 2 * np.pi)
            d = rp * (1.0 + rng.uniform(0.15, 1.3) * (1 - (1 - kb) ** 3))
            rr = max(1, int(rng.uniform(5, 15) * (1 - kb)))
            cv2.circle(m1 if j % 3 else m2, (int(sx + np.cos(a) * d), int(sy + np.sin(a) * d)), rr, 1.0, -1, cv2.LINE_AA)
        img = img + (H('#D9402B')[None, None] - img) * m1[..., None]
        img = img + (H('#F5C842')[None, None] - img) * m2[..., None]
    # the relay arrival: the sun (outro-06's) is still there for 2 frames, pressing into the circle
    if local < 2 / 24:
        m = np.zeros((1080, 1920), np.float32)
        cv2.circle(m, (int(sx), int(sy)), int(rp * 0.98), 1.0, -1, cv2.LINE_AA)
        img = img + (H('#FFF2C8')[None, None] - img) * (m * (1 - local * 12))[..., None]
    # all six stamps pulse once on 181.43
    if 181.43 <= t < 181.85:
        pk = (t - 181.43) / 0.42
        m = np.zeros((1080, 1920), np.float32)
        for (x, y, _) in C.CIRCLES:
            px, py = to_s(x, y)
            cv2.circle(m, (int(px), int(py)), int(rp * (1.0 + 0.35 * pk)), 1.0, max(1, int(6 * (1 - pk))), cv2.LINE_AA)
        img = img + (H('#D9402B')[None, None] - img) * (m * (1 - pk))[..., None]
    return _zh_fixed(img, t, 61, 180.15, ink='#1A1416', halo_col='#EDE3CF')


R['B-outro-07'] = outro_07
tl.OWN_TYPE.add('B-outro-07')


# ---- B-outro-06: the lighthouse at sunrise -- spiral up, the beam fades, he arrives, the sun waits beside the lamp ----
def _o06_geom():
    import math
    s = tl.BY_ID['B-outro-06']
    d = s['end'] - s['start']
    R_, h0, h1, ph0, ph1 = 13.0, 5.0, 18.0, -60.0, 60.0
    E = np.array([R_ * math.sin(math.radians(ph1)), h1, R_ * math.cos(math.radians(ph1))])
    L = np.array([0.0, 17.3, 0.0])
    dl = (L - E) / np.linalg.norm(L - E)
    a = math.radians(17.0)                          # the sun sits 17 degrees beside the lamp room
    sun_dir = np.array([dl[0] * math.cos(a) + dl[2] * math.sin(a), 0.0, -dl[0] * math.sin(a) + dl[2] * math.cos(a)])
    sun_dir[1] = math.tan(math.radians(4.0))
    sun_dir /= np.linalg.norm(sun_dir)
    dist = 700.0
    S = E + sun_dir * dist
    sun_r = dist * (224.0 / 540.0) * math.tan(math.radians(20.0))      # = the stamp card's sixth circle on screen
    return s, d, R_, h0, h1, ph0, ph1, sun_dir, S, sun_r


def _o06_cam(u):
    """camera on the spiral at progress u: (pos, unit look dir, look height on the tower axis)"""
    import math
    s, d, R_, h0, h1, ph0, ph1, sun_dir, S, sun_r = _o06_geom()
    ph = math.radians(ph0 + (ph1 - ph0) * u)
    h = h0 + (h1 - h0) * u
    pos = np.array([R_ * math.sin(ph), h, R_ * math.cos(ph)])
    k = min(1.0, max(0.0, (u - 0.08) / 0.5))
    k = k * k * (3 - 2 * k)
    ly = 1.7 + (h - 1.4 + 1.2 * u - 1.7) * k          # starts looking down at the door, rises with the climb
    to_t = np.array([0.0, ly, 0.0]) - pos
    to_t /= np.linalg.norm(to_t)
    w = max(0.0, min(1.0, (u - 0.42) / 0.58))
    w = w * w * (3 - 2 * w)
    dv = to_t * (1 - w) + sun_dir * w
    return pos, dv / np.linalg.norm(dv), ly


def _o06_plate():
    import math
    s, d, R_, h0, h1, ph0, ph1, sun_dir, S, sun_r = _o06_geom()
    path = []
    n = 24
    for i in range(n + 1):
        u = i / n
        pos, dv, _ = _o06_cam(u)
        path.append({'t': d * u, 'pos': pos.round(4).tolist(), 'look': (pos + dv * 30).round(4).tolist(), 'fov': 40,
                     'ease': 'linear'})
    gt = _map_gt(60)
    names = ['LATE', 'NIGHTS', 'IN', 'THE', 'MIDDLE', 'OF', 'JUNE']
    words = []
    for i, w_ in enumerate(names):
        t0 = gt[i] - s['start']
        t1 = (gt[i + 1] - s['start']) if i + 1 < len(names) else d + 1
        um = min(1.0, (t0 + min(t1, d) ) / 2 / d)
        _, _, ly = _o06_cam((t0 + 0.15) / d)
        words.append({'text': w_, 'theta': ph0 + (ph1 - ph0) * um, 'y': round(min(15.2, max(3.0, ly + 0.9)), 3),
                      't': t0, 't1': t1})
    return plate('B-outro-06', 's8_lighthouse', {'world': 'dawnprint', 'path': path, 'sun': {'pos': S.round(3).tolist(), 'r': sun_r},
                                                 'beamFade': [177.72 - s['start'], 179.20 - s['start']], 'words': words,
                                                 'doorTheta': -48.0}, 0.0, d, fps=24)


def outro_06(s, t, local, fi):
    import math
    from mv.core import clamp
    pl = once('o06', _o06_plate)
    img = pl.frame(local).copy()
    # him arriving at the door (pedestrian-signal dot figure), stops at 177.72
    a0, a1 = pl.anchor(local, 'doorFar'), pl.anchor(local, 'door')
    if a0 and a1:
        k = clamp((t - s['start']) / (177.72 - s['start']))
        e = 1 - (1 - k) ** 2
        x = a0[0][0] + (a1[0][0] - a0[0][0]) * e
        y = a0[0][1] + (a1[0][1] - a0[0][1]) * e
        if -50 < x < 1970 and 0 < y < 1150 and a1[0][2] < 1:
            img = kit.dot_walker(img, x, y, 200, (t - s['start']) * 1.9 if k < 1 else 0.0, pitch=7.0)
    # gulls crossing the dawn sky
    for j, (y0, sp, ph, span) in enumerate(((210, 260, 0.0, 70), (300, 210, 0.4, 54), (160, 300, 0.7, 46))):
        gx = -120 + ((t - s['start']) * sp + j * 620) % 2160
        kit.gull(img, gx, y0 + 18 * math.sin(t * 1.7 + j), span, t * 2.6 + ph, '#1A1416', 0.8)
    return img


R['B-outro-06'] = outro_06


# ---- B-outro_hook-03: the end -- the title re-forms in the mirror, then the print runs backwards plate by plate --------
NOON_INKS = ['#2D6BE0', '#F5C842', '#F6F2E7', '#C9D3DC', '#F08A3C', '#D9402B', '#1A1416', '#EDE3CF']
LIFTS = [(194.76, ['#F5C842']), (195.50, ['#2D6BE0']), (196.24, ['#F08A3C']), (196.98, ['#C9D3DC', '#1A1416', '#D9402B', '#F6F2E7'])]


def _separate(img, inks):
    """nearest-ink separation of an image already printed in these inks -> {ink: coverage}"""
    import cv2
    from .print_fx import hexc as H
    pal = np.stack([H(c) for c in inks])
    d = ((img[..., None, :] - pal[None, None]) ** 2).sum(-1)
    idx = d.argmin(-1)
    return {c: cv2.GaussianBlur((idx == i).astype(np.float32), (0, 0), 0.6) for i, c in enumerate(inks)}


def _plate_lift(cov, p, cx=960, cy=540):
    """a plate peeling toward camera: scale up, drift up-left, rotate; returns (moved coverage, shadow)"""
    import cv2
    e = p * p * (3 - 2 * p)
    M = cv2.getRotationMatrix2D((cx, cy), 5.0 * e, 1.0 + 0.45 * e)
    M[0, 2] += -90 * e
    M[1, 2] += -260 * e - 400 * e * e
    moved = cv2.warpAffine(cov, M, (1920, 1080), flags=cv2.INTER_LINEAR)
    sh = cv2.GaussianBlur(cv2.warpAffine(cov, M, (1920, 1080)), (0, 0), 6 + 30 * e)
    sh = np.roll(sh, (int(24 * e), int(30 * e)), (0, 1)) * 0.35 * (1 - e)
    return moved * (1 - e ** 3), sh


def outro_hook_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text, lyrics
    from mva import fx
    from . import card as C
    from .print_fx import hexc as H
    plates = {c: np.zeros((1080, 1920), np.float32) for c in NOON_INKS}

    def put(ink, cov):
        plates[ink] = np.maximum(plates[ink] * (1 - cov), cov) if ink in plates else cov
        for k in plates:                       # knock-out: an ink covers what is under it
            if k != ink:
                plates[k] *= (1 - cov)
    pull = 1.04 - 0.04 * _ease_io(clamp((t - 191.80) / (194.76 - 191.80)))
    cx, cy, R = 860, 470, int(400 * pull)
    # the mirror on its pole, empty noon road inside, mirage moving
    pole = np.zeros((1080, 1920), np.float32)
    cv2.rectangle(pole, (cx - 14, cy + R), (cx + 14, 1080), 1.0, -1)
    put('#F08A3C', pole)
    pl = once('hook03', _hook03_plate)
    road = pl.frame(2.2)[:, ::-1].copy()
    road = kit.mirage_band(road, t, 540, 600, 1320, 30)
    road = fx.fisheye(cv2.resize(road, (2 * R, 2 * R)), k=0.45)
    disc = np.zeros((1080, 1920), np.float32)
    cv2.circle(disc, (cx, cy), R, 1.0, -1, cv2.LINE_AA)
    full = np.zeros((1080, 1920, 3), np.float32)
    y0, x0 = cy - R, cx - R
    ya, yb, xa, xb = max(0, y0), min(1080, y0 + 2 * R), max(0, x0), min(1920, x0 + 2 * R)
    full[ya:yb, xa:xb] = road[ya - y0:yb - y0, xa - x0:xb - x0]
    for ink, cov in _separate(full, NOON_INKS).items():
        put(ink, cov * disc)
    ring = np.zeros((1080, 1920), np.float32)
    cv2.circle(ring, (cx, cy), R + 16, 1.0, 30, cv2.LINE_AA)
    put('#F08A3C', ring)
    ring = np.zeros((1080, 1920), np.float32)
    cv2.circle(ring, (cx, cy), R + 32, 1.0, 3, cv2.LINE_AA)
    put('#1A1416', ring)
    # title 泳いでくミラー: cream fill (paper), black line, cobalt shadow; forms from the mirage dots 192.54-193.28
    form = clamp((t - 192.54) / (193.28 - 192.54))
    if t >= 192.54:
        reg = 1 - _ease_io(form)
        fill_all = np.zeros((1080, 1920), np.float32)
        shadow_all = np.zeros((1080, 1920), np.float32)
        for word, x, dyw in (('泳いでく', cx + 120, 0), ('ミラー', cx - 120, 90)):
            gl = text.layout_v(word, x, cy - 380, 220 * 0.8, 'mincho', tracking=0.04)
            for g in gl:
                g['cy'] += dyw
            f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=1.0, dy=reg * 90, dx=reg * 30 * math.sin(t * 9)))
            sh, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=1.0, dx=10 - reg * 40, dy=10 + reg * 140))
            if f is not None:
                fill_all = np.maximum(fill_all, f)
                shadow_all = np.maximum(shadow_all, sh)
        if form < 1:                           # still dots: the glyphs are made of the mirage's halftone dots
            dm = 1.0 - _dots_k(1 - form)
            fill_all, shadow_all = fill_all * dm, shadow_all * dm
        line = cv2.dilate(fill_all, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        put('#2D6BE0', shadow_all)
        put('#1A1416', line)
        put('#EDE3CF', fill_all)
    # HEAT WAVES caps (vermilion) on 194.02
    if t >= 194.02:
        n = min(10, int((t - 194.02) / (BEAT / 4)) + 1)
        gl, _ = text.layout_h('HEAT WAVES'[:n], 1336, 330, 50, 'mincho', tracking=0.36, align='left')
        f, _ = text.render_glyphs(gl)
        if f is not None:
            put('#D9402B', f)
    # L65 under the mirror, one word per beat from 192.00 (warm black, letter-spaced)
    gt65 = _map_gt(65)
    ws = ['ROAD', 'SHIMMER', 'WIGGLIN\'', 'THE', 'VISION']
    shown = ' '.join(w for w, g in zip(ws, gt65) if t >= g)
    if shown:
        gl, _ = text.layout_h(shown, 1010, cy + R + 66, 30, 'mincho', tracking=0.36, align='center')
        f, _ = text.render_glyphs(gl)
        if f is not None:
            put('#1A1416', f)
    # L66 word by word from 194.70, each word in the ink of the plate it leaves with
    gt66 = _map_gt(66)
    w66 = [('HEAT,', '#F5C842'), ('HEAT', '#2D6BE0'), ('WAVES,', '#2D6BE0'), ('I\'M', '#F08A3C'), ('SWIMMIN\'', '#F08A3C'),
           ('IN', '#C9D3DC'), ('A', '#C9D3DC'), ('MIRROR', '#1A1416')]
    yy = 460
    for i, (w, ink) in enumerate(w66):
        if t < gt66[i]:
            continue
        gl, _ = text.layout_h(w, 1336, yy + i * 64, 44, 'mincho', tracking=0.28, align='left')
        f, _ = text.render_glyphs(gl)
        if f is not None:
            put(ink, f)
    # the completed stamp card, small, lower left (its art separates too; the sun stamp itself never lifts)
    if 'oh3_card' not in _cache:
        card = C.render_card(stamp_k=(1, 1, 1, 1, 1), footer_n=0)
        lay = sun_stamp_layer()
        card = card * (1 - lay[..., 3:4]) + lay[..., :3] * lay[..., 3:4]
        small = cv2.resize(card, (336, 189), interpolation=cv2.INTER_AREA)
        _cache['oh3_card'] = small
        st = cv2.resize(lay[..., 3], (336, 189), interpolation=cv2.INTER_AREA)
        _cache['oh3_stamp'] = (cv2.resize(lay[..., :3], (336, 189), interpolation=cv2.INTER_AREA), st)
    small = _cache['oh3_card']
    srgb, sa = _cache['oh3_stamp']
    cardfull = np.zeros((1080, 1920, 3), np.float32)
    cm = np.zeros((1080, 1920), np.float32)
    cardfull[800:989, 60:396] = small
    cm[800:989, 60:396] = 1.0
    for ink, cov in _separate(cardfull, NOON_INKS + ['#1E2550']).items():
        put(ink if ink in plates else '#1A1416', cov * cm)
    # composite: paper, then each plate (lifting ones peel toward camera)
    img = np.empty((1080, 1920, 3), np.float32)
    img[:] = H('#EDE3CF')
    lift_of = {}
    for tl_, inks in LIFTS:
        for ink in inks:
            lift_of[ink] = tl_
    for ink, cov in plates.items():
        if ink == '#EDE3CF':
            continue
        tl_ = lift_of.get(ink)
        if tl_ is not None and t >= tl_:
            p = clamp((t - tl_) / 0.62)
            if p >= 1:
                continue
            cov, sh = _plate_lift(cov, p)
            img = img * (1 - sh[..., None])
        img = img + (H(ink)[None, None] - img) * cov[..., None]
    # exempt: the sun stamp on the small card + its glow, registration marks, colour bar (swatches leave with plates)
    sfull = np.zeros((1080, 1920), np.float32)
    sfull[800:989, 60:396] = sa
    srgbf = np.zeros((1080, 1920, 3), np.float32)
    srgbf[800:989, 60:396] = srgb
    x6, y6, _ = C.CIRCLES[5]
    gx, gy = 60 + x6 * 336 / C.CW, 800 + y6 * 189 / C.CH
    kit.halo(img, gx, gy, 70 + 8 * math.sin(t * 3), '#F5C842', 0.7 if t < 198.4 else 0.0, period=9.0)
    img = img + (srgbf - img) * sfull[..., None]
    k_ = tuple(float(v) for v in H('#1A1416'))
    for (mx, my) in ((70, 70), (1850, 70), (70, 1010), (1850, 1010)):
        cv2.circle(img, (mx, my), 18, k_, 2, cv2.LINE_AA)
        cv2.line(img, (mx - 30, my), (mx + 30, my), k_, 2, cv2.LINE_AA)
        cv2.line(img, (mx, my - 30), (mx, my + 30), k_, 2, cv2.LINE_AA)
    for i, c in enumerate(['#2D6BE0', '#F5C842', '#F6F2E7', '#C9D3DC', '#F08A3C', '#D9402B', '#1A1416']):
        tl_ = lift_of.get(c)
        if tl_ is not None and t >= tl_ + 0.3:
            continue
        cv2.rectangle(img, (560 + i * 90, 1030), (640 + i * 90, 1060), tuple(float(v) for v in H(c)), -1)
    # the film's first LED dot, blinking bottom right; off on 197.72
    if t < 197.72:
        on = (int((t - 0.682) / (BEAT / 2)) % 2 == 0)
        m = np.zeros((1080, 1920), np.float32)
        cv2.circle(m, (1790, 960), 9, 1.0, -1, cv2.LINE_AA)
        img = img + (H('#7FC8B8' if on else '#2B4A44')[None, None] - img) * m[..., None]
        if on:
            kit.halo(img, 1790, 960, 26, '#7FC8B8', 0.6, period=6.0)
    # credit on 196.24
    if t >= 196.24:
        a = clamp((t - 196.24) / 0.25)
        gl, _ = text.layout_h('Heat Waves (Japanese ver., Lime)  /  MV-B', 960, 960, 28, 'zh', tracking=0.12, align='center')
        f, _ = text.render_glyphs(gl, anim=lambda g: dict(alpha=a))
        if f is not None:
            img = img + (H('#1A1416')[None, None] - img) * f[..., None]
    # Chinese, fixed
    zl = 65 if t < 194.7 else 66
    if t < 197.9:
        img = _zh_fixed(img, t, zl, 192.0 if zl == 65 else 194.7, y=1012, ink='#1A1416', halo_col='#EDE3CF')
    # 198.40-198.74: 45-degree halftone dot-dissolve to warm black
    if t >= 198.40:
        k = clamp((t - 198.40) / 0.34)
        img = img + (H('#1A1416')[None, None] - img) * _dots_k(k, period=24.0)[..., None]
    return img


def _dots_k(k, period=10.0):
    """45-degree screen whose dots grow with k (0 = nothing, 1 = solid)"""
    c, s_ = math.cos(math.radians(45)), math.sin(math.radians(45))
    u = (kit._XS * c + kit._YS * s_) / period
    v = (-kit._XS * s_ + kit._YS * c) / period
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    return np.clip((0.7072 * math.sqrt(max(0.0, min(1.0, k))) - d) * period * 0.8, 0, 1)


R['B-outro_hook-03'] = outro_hook_03
tl.OWN_TYPE.add('B-outro_hook-03')


# ---- chalk on the seawall concrete (shared by bridge1-02 / bridge1-04) ------------------------------------------------
def concrete_dusk():
    """warm dusk-lit seawall concrete, printed: cream/orange base, indigo halftone aggregate, a few seams"""
    import cv2
    from .print_fx import hexc as H
    if 'concrete' in _cache:
        return _cache['concrete']
    rng = np.random.default_rng(31)
    n = cv2.resize(rng.random((135, 240)).astype(np.float32), (1920, 1080), interpolation=cv2.INTER_CUBIC)
    n2 = cv2.resize(rng.random((540, 960)).astype(np.float32), (1920, 1080), interpolation=cv2.INTER_LINEAR)
    xs, ys = kit._XS / 1920, kit._YS / 1080
    light = np.clip(1.05 - 0.45 * xs - 0.35 * ys, 0, 1)
    base = (H('#EDE3CF')[None, None] * (0.40 + 0.26 * light[..., None]) + H('#F08A3C')[None, None] * (0.30 * light[..., None])
            + H('#1E2550')[None, None] * (0.20 * (1 - light[..., None])))
    tone = np.clip(0.18 + 0.35 * (n - 0.5) + 0.25 * (1 - light), 0, 1)
    c, s_ = math.cos(math.radians(45)), math.sin(math.radians(45))
    u = (kit._XS * c + kit._YS * s_) / 8.0
    v = (-kit._XS * s_ + kit._YS * c) / 8.0
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    dots = np.clip((np.sqrt(tone) * 0.55 - d) * 6, 0, 1)
    img = base + (H('#1E2550')[None, None] - base) * (dots * 0.55)[..., None]
    speck = (n2 > 0.985).astype(np.float32)
    img = img + (H('#1A1416')[None, None] - img) * (speck * 0.5)[..., None]
    for x in (430, 1490):                       # expansion seams
        m = np.zeros((1080, 1920), np.float32)
        cv2.line(m, (x, -10), (x + 14, 1090), 1.0, 3, cv2.LINE_AA)
        img = img + (H('#1E2550')[None, None] - img) * (m * 0.6)[..., None]
    _cache['concrete'] = np.clip(img, 0, 1).astype(np.float32)
    return _cache['concrete']


def chalk(mask, seed=0, dry=0.32):
    """turn a stroke mask into dry chalk: grainy coverage with broken edges"""
    import cv2
    key = ('chalkgrain', seed)
    if key not in _cache:
        rng = np.random.default_rng(seed + 100)
        g = rng.random((1080, 1920)).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 0.8)
        _cache[key] = g
    g = _cache[key]
    return np.clip((mask * (0.75 + 0.5 * g) - dry) * 2.2, 0, 1)


def aiaigasa_masks(cx=900, top=190, w=290, hy=470, bot=900):
    """相合傘 doodle: umbrella (roof + handle + heart), the sun (her) left, the crescent (him) right. stroke masks"""
    import cv2
    if ('aiai', cx) in _cache:
        return _cache[('aiai', cx)]
    um = np.zeros((1080, 1920), np.float32)
    pts = np.array([[cx - w, hy], [cx - w * 0.5, top + (hy - top) * 0.45], [cx, top], [cx + w * 0.5, top + (hy - top) * 0.45],
                     [cx + w, hy]], np.int32)
    cv2.polylines(um, [pts], False, 1.0, 9, cv2.LINE_AA)
    for k in range(-2, 3):                           # scalloped hem
        x0 = cx + k * w * 0.4
        cv2.ellipse(um, (int(x0), hy), (int(w * 0.2), 22), 0, 0, 180, 1.0, 7, cv2.LINE_AA)
    cv2.line(um, (cx, top), (cx, bot), 1.0, 9, cv2.LINE_AA)
    cv2.ellipse(um, (cx - 26, bot), (26, 26), 0, 0, 180, 1.0, 9, cv2.LINE_AA)
    hp = np.array([[cx, top - 8], [cx - 20, top - 30], [cx - 10, top - 46], [cx, top - 36], [cx + 10, top - 46],
                   [cx + 20, top - 30]], np.int32)
    cv2.polylines(um, [hp], True, 1.0, 6, cv2.LINE_AA)
    sun = np.zeros((1080, 1920), np.float32)
    sx, sy = cx - 150, 650
    cv2.circle(sun, (sx, sy), 50, 1.0, 8, cv2.LINE_AA)
    for k in range(10):
        a = k * math.pi / 5
        cv2.line(sun, (int(sx + 66 * math.cos(a)), int(sy + 66 * math.sin(a))), (int(sx + 92 * math.cos(a)), int(sy + 92 * math.sin(a))),
                 1.0, 7, cv2.LINE_AA)
    moon = np.zeros((1080, 1920), np.float32)
    mx, my = cx + 150, 650
    cv2.ellipse(moon, (mx, my), (62, 62), 0, 40, 320, 1.0, 8, cv2.LINE_AA)
    cv2.ellipse(moon, (mx + 26, my - 6), (46, 50), 0, 70, 290, 1.0, 7, cv2.LINE_AA)
    _cache[('aiai', cx)] = (um, sun, moon, (sx, sy), (mx, my))
    return _cache[('aiai', cx)]


def _dot_targets(mask, pitch=12, thr=0.45, seed=0):
    """grid points (centres) where a glyph mask is inked: targets for dot-assembly"""
    ys = np.arange(pitch // 2, 1080, pitch)
    xs = np.arange(pitch // 2, 1920, pitch)
    sub = mask[np.ix_(ys, xs)]
    yy, xx = np.nonzero(sub > thr)
    pts = np.stack([xs[xx], ys[yy]], 1).astype(np.float32)
    rng = np.random.default_rng(seed)
    return pts, rng.permutation(len(pts))


# ---- B-bridge1-04: the wave takes his half of the chalk umbrella; a dotted question mark takes its place -------------
def bridge1_04(s, t, local, fi):
    import cv2
    from mv.core import clamp
    from mv import text
    from .print_fx import hexc as H
    img = concrete_dusk().copy()
    um, sun, moon, (sx, sy), (mx, my) = aiaigasa_masks()
    gt = _map_gt(33)
    word = 'ほかの誰かふさわしいよ'
    colx, coly, gs = 1300, 220, 64
    # wave tongue (middle band, from the right): in 97.72 -> 98.00 max reach, retreats by 98.46
    if t < 97.72:
        front = 2100.0
    elif t < 98.0:
        front = 2100 - (2100 - 960) * _ease_io((t - 97.72) / 0.28)
    else:
        front = 960 + (2100 - 960) * _ease_in(clamp((t - 98.0) / 0.46)) ** 0.7
    wob = 40 * np.sin(kit._YS / 37.0 + t * 7.0) + 25 * np.sin(kit._YS / 13.0 - t * 11.0)
    band = np.sqrt(np.clip(1 - ((kit._YS - 590) / 250.0) ** 2, 0, 1))
    reach = 2100 - (2100 - front) * band
    water = np.clip((kit._XS - (reach + wob)) / 10.0, 0, 1) * (band > 0.02)
    washed = t >= 97.86                               # the crescent and 誰か are gone once the tongue has passed them
    # chalk (cream): umbrella + sun always; crescent until washed, then a smear
    ch = chalk(um, 1) + chalk(sun, 2)
    if not washed:
        ch = ch + chalk(moon, 3)
    else:
        sm = cv2.GaussianBlur(np.roll(moon, 36, axis=1), (61, 9), 0) * 0.35 * (1 - clamp((t - 98.5) / 1.4) * 0.4)
        ch = ch + sm
    # L33 chalk column per mora, 誰か washed then re-formed as dots
    for i, chr_ in enumerate(word):
        if t < gt[i]:
            continue
        if washed and chr_ in '誰' or (washed and i == 4):
            continue
        key = ('chalkglyph', i)
        if key not in _cache:
            gl = text.layout_v(chr_, colx, coly + i * gs * 1.08, gs, 'mincho', tracking=0.0)
            f, _ = text.render_glyphs(gl)
            _cache[key] = f
        f = _cache[key]
        if f is not None:
            k = clamp((t - gt[i]) / (4 / 24))
            ch = ch + chalk(f * k, 4 + i, 0.25)
    ch = np.clip(ch, 0, 1)
    img = img + (H('#F6F2E7')[None, None] - img) * ch[..., None]
    # wet concrete left behind: darker, glossy dots, slowly drying
    if t >= 97.72:
        key = 'wetmask'
        wet = _cache.get(key)
        wet = water if wet is None else np.maximum(wet, water)
        _cache[key] = wet
        dry = 1 - clamp((t - 98.46) / 3.0) * 0.5
        img = img * (1 - (wet * 0.22 * dry)[..., None]) + H('#7A2A22')[None, None] * (wet * 0.05 * dry)[..., None]
        sheen = _dots_k(0.08, 9.0) * wet * np.clip(np.sin(kit._XS / 90.0 + kit._YS / 140.0) * 0.5 + 0.5, 0, 1) * dry
        img = img + (H('#F6F2E7')[None, None] - img) * (sheen * 0.7)[..., None]
    else:
        _cache.pop('wetmask', None)
    # the water itself: indigo sheet with foam dots at its front
    if 97.72 <= t < 98.6:
        img = img * (1 - water[..., None] * 0.30) + H('#2C4C9A')[None, None] * (water * 0.22)[..., None]
        edge = np.clip(1 - np.abs(kit._XS - (reach + wob) - 30) / 55.0, 0, 1) * (band > 0.05)
        streak = np.clip(np.sin(kit._YS / 9.0 + np.sin(kit._XS / 60.0) * 2) * 0.5 + 0.2, 0, 1) * water
        foam = _dots_k(0.85, 12.0) * edge + _dots_k(0.3, 8.0) * streak
        img = img + (H('#C9D3DC')[None, None] - img) * np.clip(foam, 0, 1)[..., None]
    # dot assembly 98.46-99.20: the question mark in his slot, and 誰か re-forming, from the same dots
    if t >= 98.40:
        if 'qdots' not in _cache:
            gl, _ = text.layout_h('？', mx, my, 250, 'mincho', align='center')
            qm, _ = text.render_glyphs(gl)
            g2 = text.layout_v('誰か', colx, coly + 3 * gs * 1.08, gs, 'mincho', tracking=0.08)
            dm, _ = text.render_glyphs(g2)
            pq, oq = _dot_targets(qm, 12, 0.4, 1)
            pd, od = _dot_targets(dm, 9, 0.5, 2)
            pts = np.concatenate([pq, pd])
            order = np.concatenate([oq, od + len(pq)])
            rng = np.random.default_rng(9)
            src = np.stack([rng.uniform(1150, 1850, len(pts)), rng.uniform(420, 760, len(pts))], 1).astype(np.float32)
            rad = np.concatenate([np.full(len(pq), 6.2), np.full(len(pd), 4.2)])
            _cache['qdots'] = (pts, order, src, rad)
        pts, order, src, rad = _cache['qdots']
        m = np.zeros((1080, 1920), np.float32)
        nd = len(pts)
        for j in range(nd):
            i = order[j]
            st = 98.46 + 0.5 * j / nd
            k = clamp((t - st) / 0.26)
            if k <= 0:
                continue
            e = 1 - (1 - k) ** 3
            p = src[i] + (pts[i] - src[i]) * e
            cv2.circle(m, (int(p[0]), int(p[1])), int(round(rad[i] * (0.6 + 0.4 * e))), 1.0, -1, cv2.LINE_AA)
        img = img + (H('#F6F2E7')[None, None] - img) * m[..., None]
    # her shadow falls into frame from the left on 99.20 (soft indigo, long dusk shadow)
    if t >= 99.20:
        k = _ease_io(clamp((t - 99.20) / 0.6))
        sh = np.zeros((1080, 1920), np.float32)
        x0 = int(-560 + 520 * k)
        hx = x0 + 520
        cv2.ellipse(sh, (hx, 600), (70, 64), 0, 0, 360, 1.0, -1, cv2.LINE_AA)            # bob: wider than the head
        cv2.ellipse(sh, (hx - 40, 600), (60, 78), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cv2.rectangle(sh, (hx - 120, 586), (hx - 60, 614), 1.0, -1)                      # neck
        sh_pts = np.array([[hx - 120, 520], [hx - 120, 680], [hx - 330, 700], [hx - 330, 500]], np.int32)
        cv2.fillConvexPoly(sh, sh_pts, 1.0, cv2.LINE_AA)                                 # shoulders
        cv2.fillConvexPoly(sh, np.array([[hx - 330, 510], [hx - 330, 690], [-10, 660], [-10, 540]], np.int32), 1.0, cv2.LINE_AA)
        sh = cv2.GaussianBlur(sh, (0, 0), 9) * 0.5
        img = img * (1 - sh[..., None]) + H('#1E2550')[None, None] * (sh * 0.5)[..., None]
    # camera: 1 degree over the bar, 4-frame shake on the hit
    ang = 1.0 * clamp(local / (s['end'] - s['start']))
    dx = dy = 0.0
    if 97.72 <= t < 97.72 + 4 / 24:
        rng = np.random.default_rng(int(t * 24))
        dx, dy = rng.uniform(-14, 14), rng.uniform(-10, 10)
    M = cv2.getRotationMatrix2D((960, 540), ang, 1.02)
    M[0, 2] += dx
    M[1, 2] += dy
    img = cv2.warpAffine(img, M, (1920, 1080), borderMode=cv2.BORDER_REFLECT)
    return _zh_fixed(img, t, 33, 96.9, ink='#1A1416', halo_col='#EDE3CF')


R['B-bridge1-04'] = bridge1_04
tl.OWN_TYPE.add('B-bridge1-04')


# ---- shared: the pool's LED scoreboard (8 lanes of 君 + amber ticker) ---------------------------------------------------
def scoreboard_img(t, lanes_on=(1,) * 8, ticker='', t0=0.0, on='#F5C842', speed=2):
    """flat scoreboard image: an amber 5x7 ticker row over 4x2 lane fields '1 君' ... '8 君' (dark lanes unlit)"""
    from . import print_fx
    key = ('sb_lanes', tuple(lanes_on), on)
    if key not in _cache:
        rows = []
        for r in range(2):
            fields = []
            for c in range(4):
                i = r * 4 + c
                b, _ = print_fx.led_board(f'{i + 1} 君', cols=34, rows=16, dot=12, on=on if lanes_on[i] else '#3A3420',
                                          off='#2A2418', bg='#141018', glow=0.45 if lanes_on[i] else 0.0)
                fields.append(b)
            rows.append(np.concatenate(fields, 1))
        for k in [k for k in _cache if isinstance(k, tuple) and k[0] == 'sb_lanes']:
            del _cache[k]
        _cache[key] = np.concatenate(rows, 0)
    lanes = _cache[key]
    sc = int(max(0.0, t - t0) * 24) * speed - 136
    top, _ = print_fx.led_board(ticker or ' ', cols=136, rows=10, dot=12, on=on, off='#2A2418', bg='#141018', font='silk',
                                scroll=sc)
    return np.concatenate([top, lanes], 0)


# ---- B-outro-04: the pool at dawn -- the eight 君 go dark one per 8th; her afterimage dissolves into the caustics -----
def _o04_plate():
    s = tl.BY_ID['B-outro-04']
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [-9.5, 5.6, 5.0], 'look': [16.0, 4.0, -0.5], 'fov': 40},
            {'t': d, 'pos': [-9.5, 3.6, 5.0], 'look': [16.0, 3.7, -0.5], 'fov': 39.4, 'ease': 'inout'}]
    return plate('B-outro-04', 's7_pool', {'world': 'dawnprint', 'path': path, 'school': True, 'schoolWindow': '#F5C842',
                                          'waterA': '#3F9FA8', 'waterB': '#F5C842', 'waterDeep': '#2C4C9A',
                                          'sunPos': [420, 70, -300]}, 0.0, d, fps=24)


def outro_04(s, t, local, fi):
    import cv2
    from mv.core import clamp
    pl = once('o04', _o04_plate)
    img = pl.frame(local).copy()
    offs = [171.05 + k * BEAT / 2 for k in range(8)]
    lanes = tuple(0 if t >= o else 1 for o in offs)
    q = pl.anchor(local, 'scoreboard')
    if q and all(0 < p[2] < 1.001 for p in q):
        brd = scoreboard_img(t, lanes, "CAN'T MAKE YOU HAPPIER NOW", 171.10)
        img = led_on_quad(img, _quad_sorted(q), brd)
    # her afterimage at the pool edge (B-chorus1-05's keyframe), 50%, dissolving into the caustic dots 172.54-173.28
    from . import chars
    cl = once('o04_char', lambda: chars.CharLayer('B-chorus1-05', rim=False))
    e = pl.anchor(local, 'edge')
    if cl.ok and e:
        rgb, a = cl.frame(0.0, x=e[0][0], y=e[0][1], cx=0.5, cy=0.95, height=420)
        k = clamp((t - 172.54) / (173.28 - 172.54))
        a = a * 0.5 * (1 - _dots_k(k, 9.0))
        img = chars.over(img, rgb, a)
    return img


R['B-outro-04'] = outro_04


# ---- B-outro-02: flight over the waking town -- the night plate peels off like paper; every LED sings one word -------
O02_WORDS = [('LATE', 165.25, '#F08A3C', 'vend'), ('NIGHTS', 165.87, '#F08A3C', 'station'), ('IN THE', 166.61, '#F5C842', 'pool'),
             ('MIDDLE', 167.00, '#7FC8B8', 'clock'), ('OF JUNE', 167.35, '#F5C842', 'bus')]


def _o02_common():
    s = tl.BY_ID['B-outro-02']
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [-110.0, 40.0, 92.0], 'look': [80.0, 0.0, 92.0], 'fov': 42, 'bank': 0.0, 'ease': 'linear'},
            {'t': 1.20, 'pos': [-80.0, 40.0, 93.0], 'look': [110.0, 0.0, 96.0], 'fov': 42, 'bank': 0.0, 'ease': 'linear'},
            {'t': 2.10, 'pos': [-57.5, 39.0, 97.0], 'look': [128.0, 0.0, 128.0], 'fov': 42, 'bank': -15.0, 'ease': 'inout'},
            {'t': d, 'pos': [-36.0, 38.0, 104.0], 'look': [146.0, 0.0, 150.0], 'fov': 42, 'bank': -15.0, 'ease': 'linear'}]
    marks = []
    for i, (w, tw, col, kind) in enumerate(O02_WORDS):
        tau = tw - s['start']
        xc = -110 + 25.4 * tau
        marks.append([round(xc + 58 + 6 * i, 1), round(92 + (22 if i % 2 else -18) + 6 * tau, 1), {'vend': 2.0, 'station': 3.5,
                      'pool': 6.0, 'clock': 5.0, 'bus': 2.5}[kind]])
    marks.append([2400.0, 520.0, 260.0])                                   # the sun, far out over the sea
    walker = {'pts': [[_coast(70) - 6, 70], [_coast(150) - 6, 150]], 'times': [0.0, d]}
    common = {'path': path, 'marks': marks, 'walker': walker, 'vend': 140, 'fogNear': 400, 'fogFar': 1500,
              'moonPath': {'z': 100, 'len': 900, 'w': 90, 'color': '#F5C842', 'str': 0.85}}
    return s, d, common


def _o02_plates():
    s, d, common = _o02_common()
    night = dict(common, world='night', land='#141A33', sea='#1E2550', seaShade='#0E1226', road='#C9D3DC',
                 blocks=['#1E2550', '#2C4C9A', '#232B57'], blockShade='#0E1226', window='#F08A3C', litP=0.06,
                 vendColor='#7FC8B8', moonPath=dict(common['moonPath'], color='#C9D3DC'))
    dawn = dict(common, world='dawnprint', land='#EDE3CF', sea='#2C4C9A', seaShade='#1E2550', road='#C9D3DC',
                blocks=['#EDE3CF', '#F08A3C', '#C9D3DC'], blockShade='#2C4C9A', window='#F5C842', litP=0.06,
                vendColor='#D9402B', fogColor='#F2C58A')
    return plate('B-outro-02n', 's5_map', night, 0.0, d, fps=24), plate('B-outro-02d', 's5_map', dawn, 0.0, d, fps=24)


def outro_02(s, t, local, fi):
    import cv2
    from mv.core import clamp
    from . import print_fx
    from .print_fx import hexc as H
    pn, pd = once('o02', _o02_plates)
    night, dawn = pn.frame(local), pd.frame(local)
    # 版はがし: the night plate peels from the sea edge (top of frame) inland, 165.13 -> 167.35
    if t < 166.61:                                    # halfway on 166.61, off on 167.35: slow lift, fast finish
        k = 0.5 * clamp((t - 165.13) / 1.48) ** 1.35
    else:
        k = 0.5 + 0.5 * clamp((t - 166.61) / 0.74)
    Y = -140 + (1080 + 420) * k
    xs, ys = kit._XS, kit._YS
    yf = Y + np.tan(np.radians(7)) * (xs - 960) + 12 * np.sin(xs / 210.0 + t * 3.0)
    hc = 70 + 90 * (1 - abs(2 * k - 1))
    below = np.clip((ys - yf) / 2.0, 0, 1)
    img = dawn * (1 - below[..., None]) + night * below[..., None]
    # the curl: the sheet's back rolled over the fold, cream with a cylinder shade, edges inked; shadow below it
    u = np.clip((ys - yf) / hc, 0, 1)
    curl = ((ys >= yf) & (ys <= yf + hc)).astype(np.float32)
    shade = 0.70 + 0.30 * np.sin(np.pi * u)
    back = H('#EDE3CF')[None, None] * shade[..., None]
    shadow = np.clip(1 - np.abs(ys - (yf + hc + 26)) / 34.0, 0, 1) * 0.45 * (ys > yf + hc)
    if 0 < k < 1:
        img = img * (1 - shadow[..., None])
        img = img + (back - img) * curl[..., None]
        edge = (np.abs(ys - yf) < 2.0) | (np.abs(ys - (yf + hc)) < 2.0)
        img = img + (H('#1A1416')[None, None] - img) * (edge.astype(np.float32) * 0.85)[..., None]
    # the paper-cut sun on the horizon (dawn side only)
    mk = pd.anchor(local, 'marks') or []
    if mk and 0 < mk[-1][2] < 1.001:
        sx, sy = mk[-1][0], mk[-1][1]
        sun = np.zeros((1080, 1920), np.float32)
        cv2.circle(sun, (int(sx), int(sy)), 62, 1.0, -1, cv2.LINE_AA)
        sun *= (1 - below)
        kit.halo(img, sx, sy, 260, '#F5C842', 0.55 * float((sy < yf[int(min(1079, max(0, sy))), int(min(1919, max(0, sx)))])), period=12.0)
        img = img + (H('#FFF2C8')[None, None] - img) * sun[..., None]
    # LED relay across town: each display lights its word as the camera passes
    for i, (w, tw, col, kind) in enumerate(O02_WORDS):
        if t < tw or i >= len(mk) or not (0 < mk[i][2] < 1.001):
            continue
        x, y = mk[i][0], mk[i][1]
        if not (-200 < x < 2120 and -100 < y < 1180):
            continue
        a = clamp((t - tw) / (2 / 24))
        brd, _ = print_fx.led_board(w, cols=max(18, len(w) * 8 + 4), rows=10, dot=9, on=col, off='#2A2418', bg='#141018',
                                    font='silk', glow=0.5)
        bh, bw = brd.shape[:2]
        x0, y0 = int(x - bw / 2), int(y - bh - 26)
        m = np.zeros((1080, 1920), np.float32)
        cv2.line(m, (int(x), int(y)), (int(x), int(y - 26)), 1.0, 3, cv2.LINE_AA)
        img = img + (H('#1A1416')[None, None] - img) * m[..., None]
        ya, yb, xa, xb = max(0, y0), min(1080, y0 + bh), max(0, x0), min(1920, x0 + bw)
        if ya < yb and xa < xb:
            roi = img[ya:yb, xa:xb]
            img[ya:yb, xa:xb] = roi + (brd[ya - y0:yb - y0, xa - x0:xb - x0] - roi) * a
            kit.halo(img, x, y0 + bh / 2, bw * 0.75, col, 0.35 * a, period=10.0)
    # him, running on the seawall far below
    wk = pd.anchor(local, 'walker')
    if wk and 0 < wk[0][2] < 1.001:
        img = kit.dot_walker(img, wk[0][0], wk[0][1], 46, (t - s['start']) * 2.6, pitch=3.0, run=True)
    for j, (y0_, sp, ph, span) in enumerate(((240, 330, 0.1, 64), (330, 270, 0.5, 48), (190, 380, 0.8, 40))):
        gx = 2050 - ((t - s['start']) * sp + j * 700) % 2300
        kit.gull(img, gx, y0_ + 16 * np.sin(t * 1.9 + j), span, t * 2.8 + ph, '#1A1416', 0.8)
    return _zh_fixed(img, t, 56, 165.25, y=1012, ink='#1A1416', halo_col='#EDE3CF')


R['B-outro-02'] = outro_02
tl.OWN_TYPE.add('B-outro-02')


# ---- B-outro_hook-01: the card flies over town; the sky reprints dawn -> morning -> noon, one pass per beat ------------
def _oh1_common():
    import math
    s = tl.BY_ID['B-outro_hook-01']
    d = s['end'] - s['start']
    zc = lambda tt: -10.0 + 62.0 * (tt / d)
    mirror = np.array([-4.1, 3.0, 62.0])
    path = []
    for i in range(9):
        u = i / 8
        tt = d * u
        e = u * u * (3 - 2 * u)
        y = 20.0 + (2.6 - 20.0) * e
        pos = np.array([-1.3 * e, y, zc(tt)])
        ahead = np.array([-1.0 * u, 5.0 + (1.95 - 5.0) * e, zc(tt) + 34.0])
        w = max(0.0, min(1.0, (u - 0.55) / 0.45))
        w = w * w * (3 - 2 * w)
        look = ahead * (1 - w) + mirror * w                 # the last beat turns onto the curve mirror
        path.append({'t': tt, 'pos': pos.round(3).tolist(), 'look': look.round(3).tolist(), 'fov': 38, 'ease': 'linear'})
    gt = _map_gt(63)
    words = ['ROAD', 'SHIMMER', 'WIGGLIN\'', 'THE', 'VISION']
    decals = [{'word': w, 'z': round(zc(min(d, g - s['start'])) + 17.0, 2), 'x': 0.0, 'size': 0.95, 'stretch': 3.0,
               'color': '#F6F2E7', 'showT': round(g - s['start'], 3)} for w, g in zip(words, gt)]
    return s, d, path, decals


def _oh1_plates():
    import math
    s, d, path, decals = _oh1_common()
    out = []
    for k, w in enumerate(('dawnprint', 'morning', 'noon')):
        el = math.radians(6 + 6 * k)
        common = {'world': w, 'day': True, 'path': path, 'decals': decals, 'mirrors': [62.0], 'wallH': 0.5,
                  'poleSpacing': 16.3, 'moonPos': [230.0, round(720 * math.tan(el), 1), 720.0]}
        out.append(plate(f'B-outro_hook-01{w[0]}', 's2_coast', common, 0.0, d, fps=24))
    return out


def outro_hook_01(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import card as C
    from .print_fx import hexc as H
    pls = once('oh1', _oh1_plates)
    # print passes as a time-lapse: dawn, then morning on 186.61, noon on 187.35 (6-frame drum wipe, ragged edge)
    frames = [p.frame(local) for p in pls]
    img = frames[0].copy()
    for k, tp in ((1, 186.61), (2, 187.35)):
        if t >= tp:
            w = clamp((t - tp) / (6 / 24))
            edge = (-60 + 2040 * w) + 14 * np.sin(kit._YS / 23.0 + k)
            m = np.clip((edge - kit._XS) / 6.0, 0, 1)
            img = img + (frames[k] - img) * m[..., None]
    # the mirage band returns on 188.09 (dot-melt on the road near the horizon)
    vp = pls[2].anchor(local, 'vp')
    if t >= 188.09 and vp:
        a = clamp((t - 188.09) / 0.5)
        img = kit.mirage_band(img, t, float(np.clip(vp[0][1] + 20, 300, 900)), 0, 1920, 26 * a + 1, 3.0 * a, strength=0.85 * a)
    # the stamp card flying ahead (paper flutter), drawn into the curve mirror at the end
    if 'oh1_card' not in _cache:
        card = C.render_card(stamp_k=(1, 1, 1, 1, 1), footer_n=0)
        lay = sun_stamp_layer()
        card = card * (1 - lay[..., 3:4]) + lay[..., :3] * lay[..., 3:4]
        _cache['oh1_card'] = cv2.resize(card, (480, 270), interpolation=cv2.INTER_AREA)
    cd = _cache['oh1_card']
    mr = pls[2].anchor(local, 'mirrors')
    mx, my = (mr[0][0], mr[0][1]) if mr and 0 < mr[0][2] < 1.001 else (960.0, 500.0)
    k_in = _ease_in(clamp((t - 188.2) / 0.63))
    cx = 960 + 70 * math.sin(t * 1.3) + (mx - 960) * k_in
    cy = 600 + 40 * math.sin(t * 2.1) - 60 * clamp(local / 1.5) + (my - 560) * k_in
    sc = (0.9 - 0.25 * clamp(local / 2.0)) * (1 - 0.9 * k_in)
    if sc > 0.02:
        hh, ww = cd.shape[:2]
        ys, xs = np.mgrid[0:hh, 0:ww].astype(np.float32)
        wave = 10 * np.sin(xs / 70.0 - t * 9.0) * (xs / ww)
        warped = cv2.remap(cd, xs, ys + wave, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        am = cv2.remap(np.ones((hh, ww), np.float32), xs, ys + wave, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        shade = (1.0 + 0.012 * np.gradient(wave, axis=1) * 10)[..., None]
        M = cv2.getRotationMatrix2D((ww / 2, hh / 2), 8 * math.sin(t * 1.7), sc)
        M[0, 2] += cx - ww / 2
        M[1, 2] += cy - hh / 2
        lay = cv2.warpAffine(np.clip(warped * shade, 0, 1), M, (1920, 1080))
        a = cv2.warpAffine(am, M, (1920, 1080))
        sh = cv2.GaussianBlur(np.roll(a, (28, 18), (0, 1)), (0, 0), 9) * 0.3
        img = img * (1 - sh[..., None])
        img = img + (lay - img) * a[..., None]
    # ミラー・アイリス on 188.83: the mirror disc grows to fill the frame in the last 5 frames
    if t >= 188.83 - 5 / 24 and mr:
        k = clamp((t - (188.83 - 5 / 24)) / (5 / 24))
        R0 = 60 + 1200 * k ** 2
        disc = np.zeros((1080, 1920), np.float32)
        cv2.circle(disc, (int(mx), int(my)), int(R0), 1.0, -1, cv2.LINE_AA)
        img = img + (H('#C9D3DC')[None, None] - img) * (disc * 0.85 * k)[..., None]
        ring = np.zeros((1080, 1920), np.float32)
        cv2.circle(ring, (int(mx), int(my)), int(R0 + 12), 1.0, int(10 + 30 * k), cv2.LINE_AA)
        img = img + (H('#F08A3C')[None, None] - img) * ring[..., None]
    return _zh_fixed(img, t, 63, 186.22, ink='#1A1416', halo_col='#EDE3CF')


R['B-outro_hook-01'] = outro_hook_01
tl.OWN_TYPE.add('B-outro_hook-01')


# ---- B-verse-06: 逃げ水 spreads -- the road's halftone melts into rippling LED dots that mirror the sky ----------------
def led_dots(src, pitch=14.0, ripple=0.0, t=0.0, gap='#2A3040', glow=0.4):
    """re-sample an image as round LED dots (screen-locked grid, dark gaps); ripple shifts the sampling like water"""
    import cv2
    from .print_fx import hexc as H
    xs, ys = kit._XS, kit._YS
    gx, gy = np.floor(xs / pitch), np.floor(ys / pitch)
    cx, cy = (gx + 0.5) * pitch, (gy + 0.5) * pitch
    if ripple:
        cy = cy + ripple * np.sin(cx / 61.0 + t * 5.0) + 0.5 * ripple * np.sin(cy / 17.0 - t * 7.0)
        cx = cx + 0.6 * ripple * np.sin(cy / 43.0 + t * 4.0)
    col = cv2.remap(src, cx.astype(np.float32), cy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    d = np.sqrt((xs - (gx + 0.5) * pitch) ** 2 + (ys - (gy + 0.5) * pitch) ** 2) / pitch
    core = np.clip((0.40 - d) * pitch * 0.9, 0, 1)
    out = H(gap)[None, None] + (col - H(gap)[None, None]) * core[..., None]
    if glow:
        out = out + col * cv2.GaussianBlur(core, (0, 0), pitch * 0.35)[..., None] * glow * 0.35
    return np.clip(out, 0, 1)


def _v06_plate():
    s = tl.BY_ID['B-verse-06']
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [0.6, 0.5, 0.0], 'look': [0.5, 0.62, 60.0], 'fov': 40},
            {'t': d, 'pos': [0.6, 0.5, 4.0 * d], 'look': [0.5, 0.62, 4.0 * d + 60.0], 'fov': 40, 'ease': 'linear'}]
    return plate('B-verse-06', 's2_coast', {'world': 'noon', 'day': True, 'path': path, 'wallH': 0.5, 'poleSpacing': 16.3,
                                           'mirrors': [38.0, 120.0], 'fogNear': 80, 'fogFar': 520}, 0.0, d, fps=24)


def ground_led(src, hy, t, scroll=0.0, p0=6.0, p1=34.0, gap='#7A8498', glow=0.55, ripple=3.0):
    """round LED dots on the road below horizon hy: rows whose pitch grows from p0 (horizon) to p1 (bottom edge),
    scrolling toward the camera; each dot takes src's colour at its centre (rippling like water)."""
    import cv2
    from .print_fx import hexc as H
    xs, ys = kit._XS, kit._YS
    span = max(1.0, 1080.0 - hy)
    a = (p1 - p0) / span
    yy = np.maximum(ys - hy, 0.0)
    r = np.log((p0 + a * yy) / p0) / a              # continuous row coordinate (rows per pixel = 1 / pitch)
    rc = np.floor(r - scroll) + 0.5 + scroll
    pc = p0 * np.exp(a * rc)
    yc = hy + (pc - p0) / a
    ix = np.floor((xs - 960) / pc)
    xc = 960 + (ix + 0.5) * pc
    sx = (xc + ripple * 0.6 * np.sin(yc / 23.0 + t * 5.0)).astype(np.float32)
    sy = np.clip(yc + ripple * np.sin(xc / 47.0 + t * 6.0), 0, 1079).astype(np.float32)
    col = cv2.remap(src, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    d = np.sqrt((xs - xc) ** 2 + (ys - yc) ** 2) / pc
    core = np.clip((0.42 - d) * pc * 0.9, 0, 1)
    out = H(gap)[None, None] + (col - H(gap)[None, None]) * core[..., None]
    out = out + col * cv2.GaussianBlur(core, (0, 0), 2.5)[..., None] * glow * 0.4
    return np.clip(out, 0, 1)


def verse_06(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from .print_fx import hexc as H
    pl = once('v06', _v06_plate)
    img = pl.frame(local).copy()
    vp = pl.anchor(local, 'vp')
    hy = float(np.clip(vp[0][1], 420, 640)) if vp else 540.0
    # the mirage front: starts at the horizon, wavefront 1 on 71.05, wavefront 2 reaches mid-frame on 71.79
    if t < 71.05:
        front = hy + 40 * clamp((t - 70.31) / 0.74)
    elif t < 71.79:
        front = hy + 40 + (810 - hy - 40) * _ease_io((t - 71.05) / 0.74) * 0.55
    else:
        front = hy + 40 + (810 - hy - 40) * (0.55 + 0.45 * _ease_io(clamp((t - 71.79) / 0.74)))
    under = clamp((t - 72.53) / 0.75)                       # the lens dips under the silver surface
    front = front + (1180 - front) * under
    top = hy - (hy + 40) * _ease_in(under)                  # ... and the surface rises over the frame
    # what the mirage shows: the sky above the horizon, flipped, rippling, brightened toward silver
    yy = np.clip(2 * hy - kit._YS + 3 * np.sin(kit._XS / 31.0 + t * 7.0), 0, 1079).astype(np.float32)
    refl = cv2.remap(img, kit._XS, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    refl = np.clip(refl * 0.75 + H('#E6EEF5')[None, None] * 0.35, 0, 1)
    dots = ground_led(refl, hy - 2, t, scroll=local * 3.2)
    edge = front + 18 * np.sin(kit._XS / 57.0 + t * 6.0) + 9 * np.sin(kit._XS / 13.0 - t * 9.0)
    m = np.clip((kit._YS - top) / 6.0, 0, 1) * np.clip((edge - kit._YS) / 10.0, 0, 1)
    if under > 0:                              # above the old horizon (when the surface rises) use a flat dot field
        flat = led_dots(refl, pitch=15.0, ripple=5.0, t=t, gap='#7A8498')
        dots = np.where((kit._YS < hy + 4)[..., None], flat, dots)
    img = img + (dots - img) * m[..., None]
    # her, far away in the mirage with an inverted reflection, dissolving into LED dots on 72.53
    from . import chars
    cl = once('v06_char', lambda: chars.CharLayer('B-chorus1-03', rim=True, rim_w=(1.5, 3.0, 0.0)))
    if cl.ok:
        rgb, a = cl.frame(0.0, x=960, y=hy + 14, cx=0.5, cy=0.92, height=200)
        k = clamp((t - 72.53) / 0.5)
        a = a * (1 - _dots_k(k, 7.0))
        img = chars.over(img, rgb, a)
        rr = cv2.flip(rgb, 0)
        ra = cv2.flip(a, 0)
        shift = int(2 * (hy + 14) - 1080)
        rr, ra = np.roll(rr, shift, 0), np.roll(ra, shift, 0) * 0.5
        ra = cv2.remap(ra, (kit._XS + 3 * np.sin(kit._YS / 4.0 + t * 12)).astype(np.float32), kit._YS, cv2.INTER_LINEAR)
        img = chars.over(img, rr, ra * (kit._YS > hy + 14))
    # L24 column above the horizon, each glyph with an inverted wobbling reflection below it
    gt = _map_gt(24)
    word = '路に広がる逃げ水'
    size = 52
    y0 = max(40.0, hy - 40 - len(word) * size * 1.06)
    fill = np.zeros((1080, 1920), np.float32)
    for i, ch in enumerate(word):
        if t < gt[i]:
            continue
        gl = text.layout_v(ch, 1730, y0 + i * size * 1.06, size, 'mincho')
        f, _ = text.render_glyphs(gl)
        if f is None:
            continue
        if ch in '逃げ水':                                    # built from the same LED dots
            f = f * (1 - _dots_k(0.35, 7.0)) if t < 72.6 else f
        fill = np.maximum(fill, f)
    if fill.max() > 0:
        sh = np.roll(np.roll(fill, 6, 0), 6, 1)
        line = cv2.dilate(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        img = img + (H('#2D6BE0')[None, None] - img) * sh[..., None]
        img = img + (H('#1A1416')[None, None] - img) * line[..., None]
        img = img + (H('#EDE3CF')[None, None] - img) * fill[..., None]
        rf = cv2.flip(np.maximum(line, sh), 0)
        rf = np.roll(rf, int(2 * hy - 1080), 0)
        rf = cv2.remap(rf, (kit._XS + 6 * np.sin(kit._YS / 9.0 + t * 8)).astype(np.float32), kit._YS, cv2.INTER_LINEAR)
        img = img + (H('#C9D3DC')[None, None] - img) * (rf * 0.55 * (kit._YS > hy))[..., None]
    # under the surface: everything goes to the grey of the TV sign-off screen
    if under > 0:
        img = img + (H('#8E95A6')[None, None] - img) * (clamp((under - 0.55) / 0.45) ** 1.5)
    return _zh_fixed(img, t, 24, 70.35, ink='#1A1416', halo_col='#EDE3CF')


R['B-verse-06'] = verse_06
tl.OWN_TYPE.add('B-verse-06')


# ---- shared: convex mirror content composited into a projected mirror disc ---------------------------------------------
def mirror_insert(img, content, C, X, Y, sat=1.0, k=0.38, tint='#C9D3DC', sheen_t=None):
    """content (square float image) -> fisheye -> affine onto the mirror disc given projected centre C and rim points
    X (local +x) and Y (local +y). sat < 1 desaturates toward silver (mirrors not facing camera)."""
    import cv2
    from mva import fx
    from .print_fx import hexc as H
    S = content.shape[0]
    cont = fx.fisheye(content, k=k)
    if sat < 1.0:
        g = cont.mean(-1, keepdims=True)
        cont = g + (cont - g) * sat
        cont = cont * (0.8 + 0.2 * sat) + H(tint)[None, None] * (0.2 * (1 - sat))
    src = np.float32([[S / 2, S / 2], [S, S / 2], [S / 2, 0]])
    dst = np.float32([[C[0], C[1]], [X[0], X[1]], [Y[0], Y[1]]])
    M = cv2.getAffineTransform(src, dst)
    warped = cv2.warpAffine(cont, M, (1920, 1080), flags=cv2.INTER_LINEAR)
    disc = np.zeros((S, S), np.float32)
    cv2.circle(disc, (S // 2, S // 2), S // 2 - 2, 1.0, -1, cv2.LINE_AA)
    m = cv2.warpAffine(disc, M, (1920, 1080), flags=cv2.INTER_LINEAR)
    out = img + (warped - img) * m[..., None]
    if sheen_t is not None:                       # a silver sheen band sweeping the glass
        band = np.exp(-((kit._XS - kit._YS - (C[0] - C[1]) - 300 * np.sin(sheen_t)) / 40.0) ** 2) * m
        out = out + (H('#F6F2E7')[None, None] - out) * (band * 0.5)[..., None]
    return out, m


# ---- B-chorus1-01: three curve mirrors at the junction, all full of her; the camera clicks round 10 degrees a beat -----
C101_BEATS = [28.83, 29.57, 30.31, 31.05]


def _c101_geom():
    import math
    A = np.array([-4.0, 2.75, 3.6])
    mirrors = [{'pos': A.tolist(), 'yaw': math.radians(15), 'r': 0.6},
               {'pos': [-3.55, 2.75, 3.2], 'yaw': math.radians(78), 'r': 0.6, 'pole': False},
               {'pos': [4.9, 2.65, 9.5], 'yaw': math.radians(-112), 'r': 0.6}]
    return A, mirrors


def _c101_theta(t):
    from mv.core import clamp
    th = 55.0
    for b in C101_BEATS:
        if t >= b:
            k = clamp((t - b) / (4 / 24))
            th -= 10.0 * k * k * (3 - 2 * k)
    return th


def _c101_plate():
    import math
    s = tl.BY_ID['B-chorus1-01']
    d = s['end'] - s['start']
    A, mirrors = _c101_geom()
    path = []
    for i in range(int(round(d * 24)) + 1):
        tt = i / 24
        th = math.radians(_c101_theta(s['start'] + tt))
        pos = A + 3.0 * np.array([math.sin(th), 0.0, math.cos(th)])
        pos[1] = 1.95
        look = A + np.array([0.0, 0.0, 0.0])
        path.append({'t': tt, 'pos': pos.round(4).tolist(), 'look': look.round(4).tolist(), 'fov': 40, 'ease': 'linear'})
    return plate('B-chorus1-01', 's9_junction', {'world': 'noon', 'path': path, 'mirrors': mirrors}, 0.0, d, fps=24)


def chorus1_01(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    pl = once('c101', _c101_plate)
    img = pl.frame(local).copy()
    Cs, Xs, Ys = pl.anchor(local, 'mirrors') or [], pl.anchor(local, 'mirrorX') or [], pl.anchor(local, 'mirrorY') or []
    # the reflected world behind the camera: the noon road (hook-03 plate), her cut-out in front of it
    bg = once('c101_bg', lambda: cv2.resize(once('hook03', _hook03_plate).frame(1.6)[:, 420:1500], (640, 640)))
    cl = once('c101_char', lambda: chars.CharLayer('B-chorus1-01'))
    beat_i = max(i for i, b in enumerate(C101_BEATS) if t >= b) if t >= C101_BEATS[0] else 0
    # which mirror faces the camera: the one whose projected disc is roundest / biggest
    areas = []
    for C, X, Y in zip(Cs, Xs, Ys):
        ax = np.hypot(X[0] - C[0], X[1] - C[1])
        ay = np.hypot(Y[0] - C[0], Y[1] - C[1])
        areas.append(ax * ay)
    face = int(np.argmax(areas)) if areas else 0
    for j, (C, X, Y) in enumerate(zip(Cs, Xs, Ys)):
        if not (0 < C[2] < 1.001):
            continue
        cont = bg.copy()
        if cl.ok:
            rgb, a = cl.frame(local + 0.37 * j, x=960, y=560, cx=0.5, cy=0.5, height=720)   # whole clip frame in the glass
            rgb, a = rgb[220:860, 640:1280], a[220:860, 640:1280]
            cont = cont + (rgb - cont) * a[..., None]
        img, m = mirror_insert(img, cont, C, X, Y, sat=1.0 if j == face else 0.7, k=0.4, sheen_t=t * 0.8 + j)
        # 君 leaves the column on 30.31 and prints at 200 px in sun yellow in the mirror facing camera
        if j == face and 30.31 <= t < 31.05:
            kk = clamp((t - 30.31) / (3 / 24))
            kit.map_glyph(img, '君', C[0], C[1], 200, 0.0, 0.4 + 0.6 * kk, '#F5C842', '#1A1416', 9.0)
    # the sun glint jumps to the facing mirror's rim on every beat (AM halftone star)
    if Cs:
        C, X, Y = Cs[face], Xs[face], Ys[face]
        gx, gy = C[0] + 0.55 * (X[0] - C[0]) + 0.55 * (Y[0] - C[0]), C[1] + 0.55 * (X[1] - C[1]) + 0.55 * (Y[1] - C[1])
        ph = (t - C101_BEATS[beat_i]) if t >= C101_BEATS[0] else 1.0
        kk = math.exp(-ph * 2.5)
        kit.halo(img, gx, gy, 120 * kk + 30, '#F6F2E7', 0.95 * kk + 0.2, period=8.0)
        m = np.zeros((1080, 1920), np.float32)
        L = int(90 * kk + 20)
        cv2.line(m, (int(gx - L), int(gy)), (int(gx + L), int(gy)), 1.0, 3, cv2.LINE_AA)
        cv2.line(m, (int(gx), int(gy - L)), (int(gx), int(gy + L)), 1.0, 3, cv2.LINE_AA)
        img = img + (H('#F6F2E7')[None, None] - img) * m[..., None]
    ly = once('c101_ly', lambda: VLyric(10, x=1720, accent='#2D6BE0', hide=lambda i, tt: i == 6 and 30.31 <= tt < 31.05))
    return ly.draw(img, t)


R['B-chorus1-01'] = chorus1_01
tl.OWN_TYPE.add('B-chorus1-01')


# ---- B-chorus1-02: relay mirror -> CRT; pull back into his room at night; the clock turns 0:00 -----------------------
def _c102_plate():
    s = tl.BY_ID['B-chorus1-02']
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [-0.62, 0.725, 0.47], 'look': [-0.62, 0.725, -0.79], 'fov': 42},
            {'t': 1.48, 'pos': [-0.15, 0.98, 1.28], 'look': [0.12, 0.52, -0.92], 'fov': 54, 'ease': 'inout'},
            {'t': d, 'pos': [-0.12, 0.98, 1.24], 'look': [0.15, 0.52, -0.92], 'fov': 53.5, 'ease': 'linear'}]
    return plate('B-chorus1-02', 's1_room', {'path': path}, 0.0, d, fps=24)


def tv_content_her(local, sid='B-chorus1-01', size=(640, 480), in_t=0.0):
    """what the CRT shows: her clip (printed cut-out) over a noon-blue field, CRT Glow tinted"""
    import cv2
    from . import chars
    from .print_fx import hexc as H
    cl = once(('tvher', sid), lambda: chars.CharLayer(sid))
    w, h = size
    bg = np.empty((h, w, 3), np.float32)
    bg[:] = H('#2D6BE0')
    bg = bg * (0.75 + 0.25 * np.linspace(1, 0, h)[:, None, None])
    if cl.ok:
        rgb, a = cl.frame(in_t + local, x=960, y=540, cx=0.5, cy=0.45, height=1080)
        rgb = cv2.resize(rgb[60:1020, 240:1680], (w, h), interpolation=cv2.INTER_AREA)
        a = cv2.resize(a[60:1020, 240:1680], (w, h), interpolation=cv2.INTER_AREA)
        bg = bg + (rgb - bg) * a[..., None]
    return np.clip(bg * 0.85 + H('#7FC8B8')[None, None] * 0.18, 0, 1)


def chorus1_02(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mva import fx
    from . import chars
    from .print_fx import clock_grid, dot_matrix, hexc as H
    pl = once('c102', _c102_plate)
    img = pl.frame(local).copy()
    # the CRT: her laughing face, barrel glass, mint light into the room
    q = pl.anchor(local, 'tv')
    flick = 1.0 - 0.25 * (1 if 34.02 <= t < 34.02 + 2 / 24 else 0)
    if q:
        cont = fx.barrel(cv2.resize(tv_content_her(local + 0.6), (1920, 1080)), 0.10)
        img = warp_quad(img, cv2.resize(cont, (640, 480)) * flick, [p[:2] for p in q])
        cx = sum(p[0] for p in q) / 4
        cy = sum(p[1] for p in q) / 4
        kit.halo(img, cx, cy, 900, '#7FC8B8', 0.22 * flick, period=12.0)
    # the boy on the tatami, screen right, lit by the TV on his left side
    b = pl.anchor(local, 'boy')
    cl = once('c102_char', lambda: chars.CharLayer('B-chorus1-02'))
    if cl.ok and b and 0 < b[0][2] < 1.001:
        ppm = abs(b[0][1] - b[1][1])                      # pixels per metre at his spot
        rgb, a = cl.frame(local, x=b[0][0], y=b[0][1], cx=0.5, cy=0.95, height=ppm * 1.25)
        side = np.clip((b[0][0] + ppm * 0.2 - kit._XS) / (ppm * 0.6), 0, 1) * a
        rgb = rgb + (H('#7FC8B8')[None, None] - rgb) * (side * 0.35 * _dots_k(0.45, 8.0))[..., None]
        img = chars.over(img, rgb, a, shadow='#141A33')
    # the LED clock: 23:59 -> 0:00 on 32.53, colon blinking on beats
    cq = pl.anchor(local, 'clock')
    if cq and all(0 < p[2] < 1.001 for p in cq):
        colon = int((t - 0.682) / BEAT) % 2 == 0
        txt = '23:59' if t < 32.53 else '0:00'
        brd = dot_matrix(clock_grid(txt, colon_on=colon), pitch=10, on='#7FC8B8', bg='#0B1414')
        img = led_on_quad(img, _quad_sorted(cq), np.asarray(brd, np.float32))
    # 32.53: 0:00 fills the frame as giant LED dots for 4 frames + mint dot flash
    if 32.53 <= t < 32.53 + 4 / 24:
        big = np.asarray(dot_matrix(clock_grid('0:00'), pitch=44, on='#7FC8B8', bg='#0B1414'), np.float32)
        sc = min(1840 / big.shape[1], 1000 / big.shape[0])
        big = cv2.resize(big, (int(big.shape[1] * sc), int(big.shape[0] * sc)), interpolation=cv2.INTER_AREA)
        img = np.empty((1080, 1920, 3), np.float32)
        img[:] = H('#0B1414')
        y0, x0 = (1080 - big.shape[0]) // 2, (1920 - big.shape[1]) // 2
        img[y0:y0 + big.shape[0], x0:x0 + big.shape[1]] = big
        img = kit.dot_flash(img, 0.45 * (1 - (t - 32.53) / (4 / 24)), '#7FC8B8', 20)
    # 34.40-34.76: the room's dots ripple and grow into silver mirage dots that re-form as the noon road
    if t >= 34.40:
        k = clamp((t - 34.40) / 0.36)
        dots = led_dots(img, pitch=8 + 16 * k, ripple=6 * k, t=t, gap='#5A6478')
        road = once('hook03', _hook03_plate).frame(0.2)
        img = img + (dots - img) * clamp(k * 2)
        img = img + (led_dots(road, pitch=8 + 16 * (1 - k), ripple=6 * (1 - k), t=t, gap='#7A8498') - img) * clamp(k * 2 - 1)
    ly1 = once('c102_ly1', lambda: VLyric(11, x=1720, accent='#D9402B', hide=lambda i, tt: i in (2, 3)))
    ly2 = once('c102_ly2', lambda: VLyric(11, x=1720, accent='#D9402B', color='#7FC8B8', zh=False,
                                          hide=lambda i, tt: i not in (2, 3)))
    return ly2.draw(ly1.draw(img, t), t)


R['B-chorus1-02'] = chorus1_02
tl.OWN_TYPE.add('B-chorus1-02')


# ---- B-chorus1-03: lost in the heat haze -- dolly-zoom on the noon road, she stays the same size ----------------------
def _c103_plate():
    import math
    s = tl.BY_ID['B-chorus1-03']
    d = s['end'] - s['start']
    zh, D0, D1 = 40.0, 10.2, 2.8
    K = D0 * math.tan(math.radians(8.0))
    path = []
    for i in range(int(round(d * 24)) + 1):
        tt = i / 24
        u = tt / d
        e = u * u * (3 - 2 * u)
        D = D0 + (D1 - D0) * e
        fov = 2 * math.degrees(math.atan(K / D))
        bank = 2.0 * math.sin(2 * math.pi * (s['start'] + tt - 0.682) / (BEAT / 2))
        path.append({'t': tt, 'pos': [0.3, 1.45, round(zh - D, 4)], 'look': [0.3, 1.0, zh], 'fov': round(fov, 4),
                     'bank': round(bank, 3), 'ease': 'linear'})
    return plate('B-chorus1-03', 's2_coast', {'world': 'noon', 'day': True, 'path': path, 'wallH': 0.5, 'poleSpacing': 16.3,
                                             'mirrors': [52.0, 140.0], 'fogNear': 120, 'fogFar': 900}, 0.0, d, fps=24)


def chorus1_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    pl = once('c103', _c103_plate)
    img = pl.frame(local).copy()
    vp = pl.anchor(local, 'vp')
    hy = float(np.clip(vp[0][1], 300, 800)) if vp else 520.0
    # heat haze below the horizon (1.5%) and the mirage pool spreading on the road
    dx = np.sin(kit._YS / 9.0 + t * 9.0) * 16 * np.clip((kit._YS - hy) / 300.0, 0, 1)
    img = cv2.remap(img, (kit._XS + dx).astype(np.float32), kit._YS, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img = kit.mirage_band(img, t, hy + 4, 0, 1920, 46 + 30 * clamp(local / 2.0), 4.0)
    # her, centre, constant size, inverted mirage reflection under her feet
    cl = once('c103_char', lambda: chars.CharLayer('B-chorus1-03', rim_w=(2.0, 4.0, 0.0)))
    feet = 540 + 310
    if cl.ok:
        rgb, a = cl.frame(local, x=960, y=feet, cx=0.5, cy=0.96, height=650)
        img = chars.over(img, rgb, a, shadow='#2D6BE0', shadow_amt=0.35)
        rr, ra = cv2.flip(rgb, 0), cv2.flip(a, 0)
        sh_ = int(2 * feet - 1080)
        rr, ra = np.roll(rr, sh_, 0), np.roll(ra, sh_, 0) * 0.4 * (kit._YS > feet)
        wob = (kit._XS + 7 * np.sin(kit._YS / 6.0 + t * 10)).astype(np.float32)
        rr = cv2.remap(rr, wob, kit._YS, cv2.INTER_LINEAR)
        ra = cv2.remap(ra.astype(np.float32), wob, kit._YS, cv2.INTER_LINEAR)
        img = chars.over(img, rr * 0.8 + H('#C9D3DC')[None, None] * 0.2, ra)
    # L12 column; 迷 turns one slow full rotation 35.50-36.98
    ly = once('c103_ly', lambda: VLyric(12, x=1720, accent='#2D6BE0', hide=lambda i, tt: i == 8))
    drift = 6 * math.sin(t * 2.3)
    img = ly.draw(img, t)
    t_mei = ly.times[8] if len(ly.times) > 8 else 35.5
    if t >= t_mei and len(ly.glyphs) > 8 and t <= ly.out_t + 0.2:
        g = ly.glyphs[8]
        r0 = max(35.50, t_mei)
        ang = -360.0 * _ease_io(clamp((t - r0) / max(0.9, 36.98 - r0)))
        kit.map_glyph(img, '迷', g['cx'] + drift, g['cy'], int(ly.size), ang, 1.0, '#EDE3CF', '#1A1416', 6.0)
    # 37.35-37.72 版ずれ: the cobalt plate slides 40 px left, the yellow plate 40 px right
    if t >= 37.35:
        k = clamp((t - 37.35) / 0.37)
        sh = int(40 * k)
        L, Rr = np.roll(img, -sh, 1), np.roll(img, sh, 1)
        img = np.stack([Rr[..., 0], (L[..., 1] + Rr[..., 1]) * 0.5, L[..., 2]], -1)
    return img


R['B-chorus1-03'] = chorus1_03
tl.OWN_TYPE.add('B-chorus1-03')


# ---- B-chorus1-06: the curve-mirror forest -- 90-degree yaws on beats, her in every glass, the line read across mirrors
C106_YAWS = [47.35, 48.09, 48.83]


def _c106_geom():
    import math
    s = tl.BY_ID['B-chorus1-06']
    d = s['end'] - s['start']
    n = int(round(d * 24))
    # integrate the flight: 6 m/s, heading turns +90 deg on each beat in 5 frames, last 0.37 s turns into a mirror
    pos = np.array([0.0, 1.6, -2.0])
    head = 0.0
    cam = []
    for i in range(n + 1):
        tt = s['start'] + i / 24
        h = 0.0
        for yb in C106_YAWS:
            k = min(1.0, max(0.0, (tt - yb) / (5 / 24)))
            h += 90.0 * k * k * (3 - 2 * k)
        cam.append((pos.copy(), h))
        hr = math.radians(h)
        pos = pos + np.array([math.sin(hr), 0.0, math.cos(hr)]) * (6.0 / 24)
    # mirror grid around the flight path (keep 1.3 m clear of it)
    rng = np.random.default_rng(16)
    mirrors = []
    pts = np.array([c[0] for c in cam])
    for gx in np.arange(-14, 15, 3.4):
        for gz in np.arange(-6, 26, 3.4):
            x, z = gx + rng.uniform(-0.8, 0.8), gz + rng.uniform(-0.8, 0.8)
            if np.min(np.hypot(pts[:, 0] - x, pts[:, 2] - z)) < 1.3:
                continue
            mirrors.append({'pos': [round(x, 3), round(2.3 + rng.uniform(0, 1.0), 3), round(z, 3)],
                            'yaw': round(rng.uniform(-math.pi, math.pi), 3), 'tilt': 0.08, 'r': round(rng.uniform(0.5, 0.65), 3)})
    # the mirror we fly into at the end: the one most straight ahead at 49.20
    i20 = int(round((49.20 - s['start']) * 24))
    p20, h20 = cam[i20]
    fwd = np.array([math.sin(math.radians(h20)), 0, math.cos(math.radians(h20))])
    best, bi = -1e9, 0
    for j, m in enumerate(mirrors):
        v = np.array(m['pos']) - p20
        dist = np.linalg.norm(v)
        score = v.dot(fwd) / dist - 0.04 * dist
        if score > best and 2.5 < dist < 9:
            best, bi = score, j
    target = np.array(mirrors[bi]['pos'])
    tv = p20 - target
    mirrors[bi]['yaw'] = round(math.atan2(tv[0], tv[2]), 3)            # make it face the incoming camera
    mirrors[bi]['tilt'] = 0.0
    return s, d, cam, mirrors, bi, target


def _c106_plate():
    import math
    s, d, cam, mirrors, bi, target = _c106_geom()
    path = []
    i20 = int(round((49.20 - s['start']) * 24))
    for i, (p, h) in enumerate(cam):
        hr = math.radians(h)
        look = p + np.array([math.sin(hr), -0.02, math.cos(hr)]) * 10
        if i >= i20:                                   # turn and close in on the chosen mirror
            k = min(1.0, (i - i20) / max(1, len(cam) - 1 - i20))
            e = k * k * (3 - 2 * k)
            look = look * (1 - e) + target * e
            p = p * (1 - 0.55 * e) + (target + (p - target) * 0.45) * (0.55 * e)
        path.append({'t': i / 24, 'pos': np.round(p, 4).tolist(), 'look': np.round(look, 4).tolist(), 'fov': 50,
                     'ease': 'linear'})
    return plate('B-chorus1-06', 's9_junction', {'world': 'noon', 'path': path, 'mirrors': mirrors, 'fogNear': 30,
                                                'fogFar': 160}, 0.0, d, fps=24)


def chorus1_06(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    pl = once('c106', _c106_plate)
    _, _, _, mirrors, bi, _ = once('c106g', _c106_geom)
    img = pl.frame(local).copy()
    Cs, Xs, Ys = pl.anchor(local, 'mirrors') or [], pl.anchor(local, 'mirrorX') or [], pl.anchor(local, 'mirrorY') or []
    bg = once('c101_bg', lambda: cv2.resize(once('hook03', _hook03_plate).frame(1.6)[:, 420:1500], (640, 640)))
    srcs = ['B-hook-01', 'B-hook-02', 'B-chorus1-01', 'B-chorus1-03']
    cls = [once(('c106cl', sid), lambda sid=sid: chars.CharLayer(sid)) for sid in srcs]
    gt = _map_gt(16)
    word = 'ヒートウェイブに迷うのさ'
    # glyph i lives in the i-th visible mirror (stable assignment by mirror index, chosen by onset time)
    sizes = []
    for j, (C, X, Y) in enumerate(zip(Cs, Xs, Ys)):
        if not (0 < C[2] < 1.001):
            sizes.append(0)
            continue
        sizes.append(np.hypot(X[0] - C[0], X[1] - C[1]) * np.hypot(Y[0] - C[0], Y[1] - C[1]))
    order = [j for j in np.argsort(sizes)[::-1] if sizes[j] > 900]
    near = order[0] if order else -1
    holder = once(('c106_holder',), lambda: {})
    for i, tg in enumerate(gt):
        if t >= tg and i not in holder:
            free = [j for j in order if j not in holder.values() and -60 < Cs[j][0] < 1980 and 40 < Cs[j][1] < 1040]
            if free:
                holder[i] = free[min(len(free) - 1, 1)]
    for j in sorted(order, key=lambda j: sizes[j]):
        C, X, Y = Cs[j], Xs[j], Ys[j]
        r = np.hypot(X[0] - C[0], X[1] - C[1])
        if r < 12 or r > 520 or not (-r < C[0] < 1920 + r and -r < C[1] < 1080 + r):
            continue                                   # tiny, off-screen, or brushing past the lens
        cont = bg.copy()
        cl = cls[j % len(cls)]
        if cl.ok:
            rgb, a = cl.frame((local * 0.8 + 0.4 * j) % 1.6, x=960, y=560, cx=0.5, cy=0.5, height=720)
            cont = cont + (rgb[220:860, 640:1280] - cont) * a[220:860, 640:1280][..., None]
        img, m = mirror_insert(img, cont, C, X, Y, sat=1.0 if j == near else 0.72, k=0.4)
        for i, jj in holder.items():                    # this mirror carries a glyph of L16
            if jj == j and t < 48.83:
                kk = clamp((t - gt[i]) / (3 / 24))
                kit.map_glyph(img, word[i], C[0], C[1], int(min(150, r * 1.2)), 0.0, 0.4 + 0.6 * kk, '#F5C842', '#1A1416', 6.0)
    # glints on 8ths on the nearest mirror
    if near >= 0:
        C, X = Cs[near], Xs[near]
        ph = ((t - 0.682) / (BEAT / 2)) % 1.0
        kk = math.exp(-ph * 4)
        gx, gy = C[0] + 0.6 * (X[0] - C[0]), C[1] - 0.6 * abs(X[0] - C[0])
        kit.halo(img, gx, gy, 70 * kk + 15, '#F6F2E7', 0.9 * kk, period=7.0)
    # 48.83: the glyphs fly out of the mirrors and assemble into the column at x~1720
    if t >= 48.83:
        k = _ease_io(clamp((t - 48.83) / 0.37))
        ly = once('c106_ly', lambda: VLyric(16, x=1720, accent='#2D6BE0'))
        for i, g in enumerate(ly.glyphs):
            if i not in holder or holder[i] >= len(Cs):
                continue
            C = Cs[holder[i]]
            x = C[0] + (g['cx'] - C[0]) * k
            y = C[1] + (g['cy'] - C[1]) * k
            if k < 1:
                kit.map_glyph(img, word[i], x, y, int(ly.size), 0.0, 1.0, '#F5C842' if k < 0.5 else '#EDE3CF', '#1A1416', 6.0)
        if k >= 1:
            img = ly.draw(img, t)
    # 49.20-49.57 reverse mirror iris: into the chosen mirror, which shrinks to the stamp card's dashed circle
    if t >= 49.38:
        from mva import fx
        k = _ease_io(clamp((t - 49.38) / 0.19))
        tx, ty, tr = once('c107_target', _c107_circle)
        cx, cy = 960 + (tx - 960) * k, 540 + (ty - 540) * k
        R_ = 1150 * (1 - k) + tr * k
        cont = bg.copy()
        cl = cls[bi % len(cls)]
        if cl.ok:
            rgb, a = cl.frame((local * 0.8 + 0.4 * bi) % 1.6, x=960, y=560, cx=0.5, cy=0.5, height=720)
            cont = cont + (rgb[220:860, 640:1280] - cont) * a[220:860, 640:1280][..., None]
        cont = fx.fisheye(cont, k=0.4)
        S = int(2 * R_)
        big = cv2.resize(cont, (S, S), interpolation=cv2.INTER_AREA if S < 640 else cv2.INTER_LINEAR)
        out = np.empty_like(img)
        out[:] = H('#1A1E3A')
        disc = np.zeros((S, S), np.float32)
        cv2.circle(disc, (S // 2, S // 2), S // 2 - 1, 1.0, -1, cv2.LINE_AA)
        x0, y0 = int(cx - S / 2), int(cy - S / 2)
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(1920, x0 + S), min(1080, y0 + S)
        if xa < xb and ya < yb:
            sub = big[ya - y0:yb - y0, xa - x0:xb - x0]
            dm = disc[ya - y0:yb - y0, xa - x0:xb - x0][..., None]
            out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - dm) + sub * dm
        img = out
    return img


def _c107_circle():
    """screen position and radius of the sixth circle in chorus1-07's first frame (for the reverse iris)"""
    from . import card as C
    s7 = tl.BY_ID['B-chorus1-07']
    zoom = 1.45
    cx, cy = 2330, 820
    _, to_s = card_on_table(np.zeros((C.CH, C.CW, 3), np.float32), cx, cy, zoom, tilt=0.28)
    x6, y6, _ = C.CIRCLES[5]
    sx, sy = to_s(x6, y6)
    ex, _ = to_s(x6 + C.R0, y6)
    return sx, sy, abs(ex - sx)


R['B-chorus1-06'] = chorus1_06
tl.OWN_TYPE.add('B-chorus1-06')


# ---- shared: 8-lane scoreboard (lane no. + 16-dot name field + time) with a race clock and a top ticker ------------
def scoreboard8_img(t, filled=0, ticker='', t0=0.0, clock='0:00.00', on='#F5C842'):
    from . import print_fx
    key = ('sb8', filled, on)
    if key not in _cache:
        cols_ = []
        for c in range(2):                                 # two columns of four lanes (landscape board)
            rows = []
            for r in range(4):
                i = c * 4 + r
                name = '君' if i < filled else '  '
                b, _ = print_fx.led_board(f'{i + 1} {name}', cols=40, rows=16, dot=10, on=on, off='#2A2418', bg='#141018',
                                          glow=0.45)
                tm, _ = print_fx.led_board('-:--.--' if i >= filled else '0:00.00', cols=50, rows=16, dot=10, on=on,
                                           off='#2A2418', bg='#141018', font='silk', glow=0.3)
                rows.append(np.concatenate([b, tm], 1))
            cols_.append(np.concatenate(rows, 0))
        for k in [k for k in _cache if isinstance(k, tuple) and k[0] == 'sb8']:
            del _cache[k]
        _cache[key] = np.concatenate(cols_, 1)
    body = _cache[key]
    sc = int(max(0.0, t - t0) * 24) * 2 - 180
    top, _ = print_fx.led_board(ticker or ' ', cols=180, rows=12, dot=10, on=on, off='#2A2418', bg='#141018', font='dot',
                                scroll=sc if ticker else 0)
    clk, _ = print_fx.led_board('     ' + clock, cols=180, rows=16, dot=10, on=on, off='#2A2418', bg='#141018', font='silk',
                                glow=0.6)
    return np.concatenate([clk, top, body], 0)


# ---- B-chorus1-05: one take -- noon pool, every lane says 君, push into the race clock, which melts into his 0:00 ------
def _c105_plates():
    s = tl.BY_ID['B-chorus1-05']
    d = s['end'] - s['start']
    tA, tB = 43.65 - s['start'], 45.13 - s['start']
    path = [{'t': 0.0, 'pos': [6.5, 5.2, -1.6], 'look': [12.5, 2.4, -0.6], 'fov': 44},
            {'t': tA, 'pos': [7.2, 1.2, -1.9], 'look': [12.5, 1.9, -0.4], 'fov': 46, 'ease': 'inout'},
            {'t': tB, 'pos': [10.2, 1.7, -0.6], 'look': [17.25, 6.75, 0.6], 'fov': 22, 'ease': 'inout'},
            {'t': d, 'pos': [10.25, 1.72, -0.6], 'look': [17.25, 6.75, 0.6], 'fov': 21.5, 'ease': 'linear'}]
    pool = plate('B-chorus1-05', 's7_pool', {'world': 'noon', 'path': path}, 0.0, d, fps=24)
    tc = d - tB
    rpath = [{'t': 0.0, 'pos': [0.02, 0.12, -0.45], 'look': [0.1, 0.07, -0.6], 'fov': 40},
             {'t': tc, 'pos': [-0.25, 0.42, 0.35], 'look': [0.1, 0.07, -0.6], 'fov': 40, 'ease': 'out'}]
    room = plate('B-chorus1-05r', 's1_room', {'path': rpath, 'fanStopT': None}, 0.0, tc, fps=24)
    return pool, room, tA, tB


def chorus1_05(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import clock_grid, dot_matrix, hexc as H
    pool, room, tA, tB = once('c105', _c105_plates)
    lanes = [41.42, 42.16, 42.90, 43.65]
    filled = 2 * sum(1 for x in lanes if t >= x)
    if local < tB + 0.74:
        img = pool.frame(min(local, tB + 0.74)).copy()
        q = pool.anchor(min(local, tB + 0.74), 'scoreboard')
        if q and all(0 < p[2] < 1.001 for p in q):
            brd = scoreboard8_img(t, filled, '初夏零時過ぎたばかり' if t >= 43.65 else '', 43.65,
                                  '0:00.00' if t >= 44.39 else '0:59.98')
            img = led_on_quad(img, _quad_sorted(q), brd)
        # her on the pool edge, screen-left third, feet in the water; splash rings on each forward swing
        cl = once('c105_char', lambda: chars.CharLayer('B-chorus1-05'))
        if cl.ok and local < tA + 0.6:
            out = clamp((local - tA) / 0.6)                       # she leaves frame as the camera tilts up
            rgb, a = cl.frame(local, x=560, y=1000 + 700 * out, cx=0.5, cy=0.9, height=900)
            img = chars.over(img, rgb, a, shadow='#2C4C9A', shadow_amt=0.3)
            for b in lanes + [40.68]:
                k = (t - b) / 0.6
                if 0 <= k < 1:
                    m = np.zeros((1080, 1920), np.float32)
                    cv2.ellipse(m, (600, int(1010 + 700 * out)), (int(60 + 160 * k), int(14 + 40 * k)), 0, 0, 360, 1.0, 3,
                                cv2.LINE_AA)
                    img = img + (H('#F6F2E7')[None, None] - img) * (m * (1 - k))[..., None]
        if local >= tB:                                          # 陽炎ドット溶け: the amber LEDs ripple and grow
            k = clamp((local - tB) / 0.74)
            img = led_dots(img, pitch=10 + 26 * k, ripple=8 * k, t=t, gap='#141018')
            img = img * (1 - 0.25 * k) + (img.mean(-1, keepdims=True) * H('#7FC8B8')[None, None] * 1.6) * (0.25 * k)
    if local >= tB + 0.74 - 1e-6 or local >= tB + 0.5:
        lr = max(0.0, local - tB)
        rimg = room.frame(lr).copy()
        cq = room.anchor(lr, 'clock')
        if cq and all(0 < p[2] < 1.001 for p in cq):
            colon = int((t - 0.682) / BEAT) % 2 == 0
            brd = dot_matrix(clock_grid('0:00', colon_on=colon), pitch=10, on='#7FC8B8', bg='#0B1414')
            rimg = led_on_quad(rimg, _quad_sorted(cq), np.asarray(brd, np.float32))
        # the fan's shadow passes over the clock
        ang = t * 2.0
        th = np.arctan2(kit._YS - 300, kit._XS - 1500)
        blades = (np.cos(3 * (th - ang)) > 0.6).astype(np.float32)
        rimg = rimg * (1 - cv2.GaussianBlur(blades, (0, 0), 25)[..., None] * 0.25)
        k = clamp((local - (tB + 0.5)) / 0.4)
        re = led_dots(rimg, pitch=36 * (1 - k) + 6, ripple=6 * (1 - k), t=t, gap='#0B1414')
        rimg = re * (1 - k) + rimg * k if k < 1 else rimg
        if local < tB + 0.74:
            img = img + (rimg - img) * clamp((local - (tB + 0.5)) / 0.24)
        else:
            img = rimg
    ly = once('c105_ly', lambda: VLyric(14, x=1720, accent='#2D6BE0'))
    img = ly.draw(img, t)
    return img


R['B-chorus1-05'] = chorus1_05
tl.OWN_TYPE.add('B-chorus1-05')


# ---- shared: two-plate riso print of a two-person still (cobalt plate / orange plate, overprint) ----------------------
INK2 = {'P': '#EDE3CF', 'C': '#2C4C9A', 'O': '#F08A3C', 'X': '#292924'}


def _fig_plate(rgb, alpha, bbox, t, sway=None, period=8.0, angle=15.0):
    """one figure as a single-ink plate coverage: solid darks, halftone mids, inked contour; optional mesh sway"""
    import cv2
    from . import print_fx
    lum = rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11
    tone = np.clip((0.92 - lum) * 1.35, 0, 1)
    if sway is not None:
        x, y, w, h = bbox
        ys = np.arange(rgb.shape[0], dtype=np.float32)[:, None]
        xs = np.arange(rgb.shape[1], dtype=np.float32)[None, :]
        dx = sway(xs, ys, x, y, w, h, t)
        mx = (xs + dx).astype(np.float32) * np.ones_like(ys)
        my = ys * np.ones_like(xs)
        tone = cv2.remap(tone, mx, my, cv2.INTER_LINEAR)
        alpha = cv2.remap(alpha, mx, my, cv2.INTER_LINEAR)
    edge = np.clip(cv2.dilate(alpha, np.ones((5, 5), np.uint8)) - cv2.erode(alpha, np.ones((5, 5), np.uint8)), 0, 1)
    return np.clip(tone * alpha, 0, 1), edge


def riso_two_person(sid, t, local, plates_off, layout=(960, 1000, 860), bg_extra=None, swap=False, fade_c=1.0, fade_o=1.0):
    """compose a two-person still as a two-plate print. plates_off = ((dx_c, dy_c), (dx_o, dy_o)) screen shifts.
    Returns (image, cobalt coverage, orange coverage). Left figure -> cobalt (him), right -> orange (her) unless swap."""
    import cv2, math
    from . import chars, print_fx
    from .print_fx import hexc as H
    raw = once(('raw', sid), lambda: chars.raw_matte(sid))
    covC = np.zeros((1080, 1920), np.float32)
    covO = np.zeros((1080, 1920), np.float32)
    lineC = np.zeros((1080, 1920), np.float32)
    lineO = np.zeros((1080, 1920), np.float32)
    if raw is not None:
        rgb, a, parts = raw
        if len(parts) == 1:
            parts = [parts[0], parts[0]]
        cx, cy, hgt = layout
        k = hgt / rgb.shape[0]
        for idx, (pa, bb) in enumerate(parts[:2]):
            to_c = (idx == 0) != swap
            def sway(xs, ys, x, y, w, h, tt, her=not to_c):
                yy = (ys - y) / max(1, h)
                if her:                                    # legs swing +-8 deg, hair sways at 2 Hz
                    legs = np.clip((yy - 0.62) / 0.38, 0, 1) ** 1.5 * h * 0.38 * math.tan(math.radians(8)) * math.sin(2 * math.pi * 0.675 * tt)
                    hair = np.clip((0.25 - yy) / 0.25, 0, 1) * 3.0 * np.sin(2 * math.pi * 2.0 * tt + yy * 6)
                    return legs + hair
                return np.clip(1 - np.abs(yy - 0.6) / 0.08, 0, 1) * 2.5 * np.sin(2 * math.pi * 3.1 * tt + xs / 9.0)
            cov, edge = _fig_plate(rgb, pa, bb, t, sway)
            M = np.float32([[k, 0, cx - rgb.shape[1] * k / 2], [0, k, cy - rgb.shape[0] * k]])
            cov = cv2.warpAffine(cov, M, (1920, 1080))
            edge = cv2.warpAffine(edge, M, (1920, 1080))
            if to_c:
                covC, lineC = np.maximum(covC, cov), np.maximum(lineC, edge)
            else:
                covO, lineO = np.maximum(covO, cov), np.maximum(lineO, edge)
    if bg_extra is not None:
        bc, bo = bg_extra
        covC, covO = np.maximum(covC, bc), np.maximum(covO, bo)
    (dxc, dyc), (dxo, dyo) = plates_off
    covC = np.roll(np.roll(np.maximum(covC, lineC), int(dyc), 0), int(dxc), 1) * fade_c
    covO = np.roll(np.roll(np.maximum(covO, lineO), int(dyo), 0), int(dxo), 1) * fade_o
    cd = np.where(covC > 0.9, 1.0, print_fx._screen(covC, 8.0, 15.0))[..., None]
    od = np.where(covO > 0.9, 1.0, print_fx._screen(covO, 8.0, 75.0))[..., None]
    P_, C_, O_, X_ = [H(INK2[c]) for c in 'PCOX']
    img = P_ * (1 - cd) * (1 - od) + C_ * cd * (1 - od) + O_ * od * (1 - cd) + X_ * cd * od
    return img.astype(np.float32), covC, covO


def reg_marks(img, color='#1A1416'):
    import cv2
    from .print_fx import hexc as H
    k_ = tuple(float(v) for v in H(color))
    for (mx, my) in ((70, 70), (1850, 70), (70, 1010), (1850, 1010)):
        cv2.circle(img, (mx, my), 18, k_, 2, cv2.LINE_AA)
        cv2.line(img, (mx - 30, my), (mx + 30, my), k_, 2, cv2.LINE_AA)
        cv2.line(img, (mx, my - 30), (mx, my + 30), k_, 2, cv2.LINE_AA)
    return img


# ---- B-chorus1-04: the two of them as a two-plate riso print; the plates drift out of register on 幸せ ------------------
def chorus1_04(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from .print_fx import hexc as H
    d = s['end'] - s['start']
    u = clamp(local / d)
    steps = sum(1 for b in (38.46, 39.20, 39.94) if t >= b)
    stepk = steps + (clamp((t - (38.46 + BEAT * (steps - 1))) / (4 / 24)) - 1 if steps else 0)
    drift = 14.0 * max(0.0, stepk) * 2 / 2
    truck = -80.0 * u
    push = 1.0 + 0.015 * u
    offC = (truck - drift * 0.5, 0.0)
    offO = (truck * 1.06 + drift * 0.5 + 4, 0.0)
    # background plates: cobalt sea band + seawall line; orange sun disc + road
    key = 'c104_bg'
    if key not in _cache:
        bc = np.zeros((1080, 1920), np.float32)
        bo = np.zeros((1080, 1920), np.float32)
        ys = kit._YS
        bc += np.clip((ys - 300) / 60.0, 0, 1) * np.clip((560 - ys) / 20.0, 0, 1) * 0.55
        cv2.line(bc, (0, 760), (1920, 760), 1.0, 6, cv2.LINE_AA)
        cv2.rectangle(bc, (0, 760), (1920, 790), 0.35, -1)
        cv2.circle(bo, (330, 200), 120, 1.0, -1, cv2.LINE_AA)
        for k in range(5):
            cv2.line(bo, (0, 860 + k * 40), (1920, 840 + k * 46), 0.5, 3, cv2.LINE_AA)
        _cache[key] = (bc, bo)
    img, covC, covO = riso_two_person('B-chorus1-04', t, local, (offC, offO), layout=(900, 900, 640),
                                      bg_extra=_cache[key])
    if push != 1.0:
        M = cv2.getRotationMatrix2D((960, 540), 0, push)
        img = cv2.warpAffine(img, M, (1920, 1080), borderMode=cv2.BORDER_REFLECT)
    img = reg_marks(img)
    # L13: 幸せ printed in both plates (orange fill / cobalt shadow) drifting apart; the rest in register
    ly = once('c104_ly', lambda: VLyric(13, x=1720, accent='#2C4C9A', color='#EDE3CF', hide=lambda i, tt: i in (2, 3)))
    img = ly.draw(img, t)
    for i in (2, 3):
        if i < len(ly.glyphs) and t >= ly.times[i]:
            g = ly.glyphs[i]
            kit.map_glyph(img, g['ch'], g['cx'] + 7 + offC[0] - truck, g['cy'] + 7, int(ly.size), 0.0, 1.0, '#2C4C9A', '#2C4C9A', 0.5)
            kit.map_glyph(img, g['ch'], g['cx'] + offO[0] - truck, g['cy'], int(ly.size), 0.0, 1.0, '#F08A3C', '#F08A3C', 0.5)
    return img


R['B-chorus1-04'] = chorus1_04
tl.OWN_TYPE.add('B-chorus1-04')


# ---- B-verse-05: the platform photo -- his cobalt plate peels off like a silkscreen sheet; hers brightens --------------
def verse_05(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import print_fx
    from .print_fx import hexc as H
    pk = clamp((t - 68.09) / (69.57 - 68.09))               # peel progress (45 deg at 68.83)
    bright = clamp((t - 68.09) / 1.2)
    key = 'v05_bg'
    if key not in _cache:
        bc = np.zeros((1080, 1920), np.float32)
        bo = np.zeros((1080, 1920), np.float32)
        cv2.rectangle(bc, (0, 900), (1920, 960), 0.55, -1)                     # platform edge
        cv2.line(bc, (0, 900), (1920, 900), 1.0, 5, cv2.LINE_AA)
        cv2.rectangle(bc, (300, 330), (640, 440), 1.0, 4, cv2.LINE_AA)          # station-name board (his plate)
        cv2.line(bc, (360, 440), (360, 900), 1.0, 6, cv2.LINE_AA)
        cv2.line(bc, (580, 440), (580, 900), 1.0, 6, cv2.LINE_AA)
        gl, _ = text.layout_h('潮見', 470, 385, 64, 'mincho', align='center')
        f, _ = text.render_glyphs(gl)
        if f is not None:
            bc = np.maximum(bc, f)
        for k in range(4):
            cv2.line(bo, (0, 980 + k * 22), (1920, 980 + k * 22), 0.45, 3, cv2.LINE_AA)
        _cache[key] = (bc, bo)
    bc, bo = _cache[key]
    # her (orange) on the paper; his plate is composited separately so it can peel
    img, covC, covO = riso_two_person('B-verse-05', t, local, ((0, 0), (0, 0)), layout=(980, 900, 760),
                                      bg_extra=(bc, bo), fade_c=0.0, fade_o=1.0 - 0.2 * bright)
    if bright > 0:                                         # a sun-yellow overprint blooms behind her
        kit.halo(img, 1120, 560, 520 * bright, '#F5C842', 0.55 * bright, period=10.0)
    _, covC, _ = riso_two_person('B-verse-05', t, local, ((0, 0), (0, 0)), layout=(980, 900, 760), bg_extra=(bc, bo),
                                 fade_c=1.0, fade_o=0.0)
    # 僕じゃ ride the cobalt sheet
    ly = once('v05_ly', lambda: VLyric(23, x=1720, accent='#F08A3C', hide=lambda i, tt: i in (0, 1, 2)))
    for i in (0, 1, 2):
        if i < len(ly.glyphs) and t >= ly.times[i]:
            gl = [dict(ly.glyphs[i])]
            f, _ = text.render_glyphs(gl)
            if f is not None:
                covC = np.maximum(covC, f)
    # the sheet lifts from its left corner, curls toward camera and slides off top-right
    if pk > 0:
        e = pk * pk * (3 - 2 * pk)
        src = np.float32([[0, 0], [1920, 0], [1920, 1080], [0, 1080]])
        lift = np.float32([[0 + 900 * e, -380 * e], [1920 + 700 * e, -200 * e], [1920 + 420 * e, 1080 - 120 * e],
                           [0 + 1250 * e, 1080 - 760 * e]])
        lift[:, 0] += 1500 * max(0.0, e - 0.5) * 2
        lift[:, 1] -= 900 * max(0.0, e - 0.5) * 2
        Hm = cv2.getPerspectiveTransform(src, lift)
        sheet = cv2.warpPerspective(covC, Hm, (1920, 1080))
        sm = cv2.warpPerspective(np.ones((1080, 1920), np.float32), Hm, (1920, 1080))
        shadow = cv2.GaussianBlur(np.roll(np.roll(sm, 40, 0), 30, 1), (0, 0), 24) * 0.30 * (1 - e * 0.6)
        img = img * (1 - shadow[..., None])
        backing = sm * 0.18                               # the sheet itself: faint film
        img = img + (H('#C9D3DC')[None, None] - img) * backing[..., None]
        covC = sheet
    cd = np.where(covC > 0.9, 1.0, print_fx._screen(covC, 8.0, 15.0))[..., None]
    if pk == 0:                                           # in register: overprint where both inks meet
        od = (np.abs(img - H('#F08A3C')[None, None]).sum(-1, keepdims=True) < 0.12).astype(np.float32)
        img = img * (1 - cd) + (H('#2C4C9A')[None, None] * (1 - od) + H('#292924')[None, None] * od) * cd
    else:
        img = img + (H('#2C4C9A')[None, None] - img) * cd
    img = reg_marks(img)
    img = ly.draw(img, t)
    # paper tilted 12 deg to camera; the camera follows the sheet up 8%
    up = 0.08 * 1080 * clamp((t - 68.09) / 1.6)
    srcq = np.float32([[0, 0], [1920, 0], [1920, 1080], [0, 1080]])
    dstq = np.float32([[60, 20 + up], [1860, 20 + up], [1920 + 40, 1080 + up], [-40, 1080 + up]])
    img = cv2.warpPerspective(img, cv2.getPerspectiveTransform(srcq, dstq), (1920, 1080), borderMode=cv2.BORDER_REPLICATE)
    # ポスター抜け: push into the blank where his plate was -> the noon road's glare
    if t >= 69.94:
        k = clamp((t - 69.94) / 0.37)
        M = cv2.getRotationMatrix2D((760, 560), 0, 1 + 2.5 * k * k)
        img = cv2.warpAffine(img, M, (1920, 1080), borderMode=cv2.BORDER_REPLICATE)
        kit.halo(img, 960, 540, 300 + 1500 * k, '#F6F2E7', 0.95 * k, period=16.0)
    return img


R['B-verse-05'] = verse_05
tl.OWN_TYPE.add('B-verse-05')


# ---- B-verse-02: TV point of view -- from inside the CRT, looking out at him; the lyric reads mirror-reversed ------------
def _v02_plate():
    s = tl.BY_ID['B-verse-02']
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [-0.62, 0.74, -0.80], 'look': [-0.25, 0.68, 1.3], 'fov': 52},
            {'t': d, 'pos': [-0.62, 0.74, -0.80], 'look': [-0.25, 0.68, 1.3], 'fov': 50.5, 'ease': 'linear'}]
    return plate('B-verse-02', 's1_room', {'path': path}, 0.0, d, fps=24)


def crt_glass(img, t, k=0.18, osd=None, mirror_osd=False, sheen=0.10):
    """the CRT glass over a frame: barrel warp, rounded mask, phosphor-dot sheen (halftone, no scanlines), OSD"""
    import cv2
    from mva import fx
    from .print_fx import clock_grid, dot_matrix, hexc as H
    out = fx.barrel(img, k)
    if osd is not None:
        o = once(('osd', osd), lambda: np.asarray(dot_matrix(clock_grid(str(osd)), pitch=14, on='#7FC8B8', bg='#000000'),
                                                   np.float32))
        if mirror_osd:
            o = o[:, ::-1]
        oh, ow = o.shape[:2]
        x0 = 120 if mirror_osd else 1920 - ow - 120
        out[90:90 + oh, x0:x0 + ow] = np.maximum(out[90:90 + oh, x0:x0 + ow], o)
    out = out + (H('#C9D3DC')[None, None] - out) * (_dots_k(0.08, 6.0) * sheen)[..., None]
    nx, ny = (kit._XS - 960) / 960, (kit._YS - 540) / 540
    vig = np.clip(1.15 - 0.35 * (nx ** 4 + ny ** 4), 0, 1)
    return out * vig[..., None]


def verse_02(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    pl = once('v02', _v02_plate)
    img = cv2.GaussianBlur(pl.frame(local), (0, 0), 5.0)          # the room behind him, out of focus
    lights = [(55.50, '#7FC8B8'), (56.24, '#F5C842'), (57.72, '#D9402B')]
    col = [c for tt, c in lights if t >= tt][-1]
    cl = once('v02_char', lambda: chars.CharLayer('B-verse-02'))
    if cl.ok:
        rgb, a = cl.frame(local, x=960, y=1080, cx=0.5, cy=0.98, height=860)
        lit = rgb * (0.75 + 0.35 * H(col)[None, None])
        img = chars.over(img, lit, a)
    img = img * (0.85 + 0.15 * H(col)[None, None])
    img = crt_glass(img, t, 0.18, osd=3, mirror_osd=True)
    # L19 mirror-reversed until sung, each glyph flipping on its mora (3 frames); 僕ら in vermilion
    ly = once('v02_ly', lambda: VLyric(19, x=1720, accent='#D9402B', zh=False))
    for i, g in enumerate(ly.glyphs):
        tc = ly.times[min(i, len(ly.times) - 1)]
        k = clamp((t - tc) / (3 / 24))
        sx = -math.cos(math.pi * k) if k > 0 else -1.0
        if abs(sx) < 0.06:
            continue
        fill = '#D9402B' if i < 2 else '#EDE3CF'
        kit.map_glyph(img, g['ch'], g['cx'] + 7, g['cy'] + 7, int(ly.size), 0.0, 1.0, '#D9402B', '#D9402B', 0.5, sx=sx)
        kit.map_glyph(img, g['ch'], g['cx'], g['cy'], int(ly.size), 0.0, 1.0, fill, '#1A1416', 6.0, sx=sx)
    return _zh_fixed(img, t, 19, 55.68, ink='#EDE3CF', halo_col='#141A33')


R['B-verse-02'] = verse_02
tl.OWN_TYPE.add('B-verse-02')


# ---- B-verse-03: tonight's roadshow -- a halftone movie poster of the two of them, then its light on his face --------
ROADSHOW = ['#D9402B', '#F5C842', '#2D6BE0', '#EDE3CF', '#1A1416']


def roadshow_poster():
    """the poster (1920 x 2600): night sky with searchlight bases, slab title, tagline, the two as stars, credits"""
    import cv2
    from mv import text
    from . import chars
    from .halftone import PrintStyle
    from .print_fx import hexc as H
    if 'poster' in _cache:
        return _cache['poster']
    W_, H_ = 1920, 2600
    im = np.empty((H_, W_, 3), np.float32)
    g = np.linspace(0, 1, H_)[:, None, None]
    im[:] = H('#2D6BE0') * (1 - g) + H('#1A1416') * g
    def put(txt, x, y, size, font, col, tr=0.0, align='center', shadow=None):
        nonlocal im
        gl, _ = text.layout_h(txt, x, 540, size, font, tracking=tr, align=align)
        f, _ = text.render_glyphs(gl)
        if f is None:
            return
        canvas = np.zeros((H_, W_), np.float32)
        r0, r1 = y - 540, y + 540                      # paste the 1080-row text canvas centred on row y
        a0, a1 = max(0, r0), min(H_, r1)
        canvas[a0:a1] = f[a0 - r0:a1 - r0]
        if shadow:
            sh = np.roll(np.roll(canvas, 12, 0), 12, 1)
            im = im + (H(shadow)[None, None] - im) * sh[..., None]
        im = im + (H(col)[None, None] - im) * canvas[..., None]
    put('HEAT WAVE', 960, 330, 250, 'dela', '#F5C842', 0.04, shadow='#D9402B')
    put('A SUMMER THAT NEVER ENDS', 960, 560, 54, 'mincho', '#EDE3CF', 0.45)
    put("TONIGHT'S ROADSHOW", 960, 2380, 46, 'mincho', '#F5C842', 0.5)
    put('DIRECTED BY  LIME     MUSIC  HEAT WAVES     STARRING  KIMI  &  BOKU', 960, 2470, 30, 'mincho', '#EDE3CF', 0.3)
    raw = chars.raw_matte('B-verse-05')
    if raw is not None:
        rgb, a, parts = raw
        k = 1500 / rgb.shape[0]
        art = cv2.resize(rgb, (int(rgb.shape[1] * k), 1500))
        aa = cv2.resize(a, (int(rgb.shape[1] * k), 1500))
        sty = PrintStyle(ROADSHOW + ['#F08A3C'], period=8, grain=0.0, dead=0.06)
        art = sty(art)
        x0 = (W_ - art.shape[1]) // 2
        x0c, x1c = max(0, x0), min(W_, x0 + art.shape[1])
        sub = im[760:2260, x0c:x1c]
        ac = aa[:, x0c - x0:x1c - x0][..., None]
        im[760:2260, x0c:x1c] = sub * (1 - ac) + art[:, x0c - x0:x1c - x0] * ac
    _cache['poster'] = np.clip(im, 0, 1)
    return _cache['poster']


def _v03_plate():
    s = tl.BY_ID['B-verse-03']
    d = 64.39 - 61.42
    path = [{'t': 0.0, 'pos': [-0.62, 0.73, -0.34], 'look': [-0.62, 0.73, -0.79], 'fov': 50},
            {'t': 1.3, 'pos': [-0.05, 0.86, 1.05], 'look': [0.55, 0.78, -0.55], 'fov': 46, 'ease': 'inout'},
            {'t': d, 'pos': [0.0, 0.86, 1.02], 'look': [0.58, 0.78, -0.55], 'fov': 45.5, 'ease': 'linear'}]
    return plate('B-verse-03', 's1_room', {'path': path}, 0.0, d, fps=24)


def verse_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    poster = roadshow_poster()
    passes = [(58.46, '#F5C842'), (59.20, '#D9402B'), (59.94, '#2D6BE0'), (60.68, '#1A1416')]
    printed = [c for tt, c in passes if t >= tt] + ['#EDE3CF']
    sep = once('v03_sep', lambda: _separate(poster, ROADSHOW + ['#F08A3C']))

    def poster_now():
        out = np.empty_like(poster)
        out[:] = H('#EDE3CF')
        for ink, cov in sep.items():
            if ink in printed or (ink == '#F08A3C' and '#D9402B' in printed):
                out = out + (H(ink)[None, None] - out) * cov[..., None]
        return out
    if t < 61.42:
        # Phase A: crane down the poster, title -> stars, x1.0 -> x1.15, searchlights sweeping
        k = _ease_io(clamp((t - 58.46) / 2.96))
        zoom = 0.62 + 0.10 * k                         # the whole poster width fits the TV frame, slow push
        y_c = 620 + (1650 - 620) * k
        pimg = poster_now()
        for j, ph in enumerate((0.0, 1.7)):
            ang = math.radians(-20 + 40 * (0.5 + 0.5 * math.sin((t - 58.46) / (4 * BEAT) * 2 * math.pi + ph)))
            bx = 560 + 800 * j
            pts = np.array([[bx, 2300], [bx + int(math.sin(ang) * 2600) - 110, 2300 - int(math.cos(ang) * 2600)],
                            [bx + int(math.sin(ang) * 2600) + 110, 2300 - int(math.cos(ang) * 2600)]], np.int32)
            m = np.zeros(pimg.shape[:2], np.float32)
            cv2.fillConvexPoly(m, pts, 1.0, cv2.LINE_AA)
            m = cv2.GaussianBlur(m, (0, 0), 30) * 0.5
            pimg = pimg + (H('#EDE3CF')[None, None] - pimg) * m[..., None]
        M = cv2.getRotationMatrix2D((960, y_c), 0, zoom)
        M[1, 2] += 540 - y_c
        img = cv2.warpAffine(pimg, M, (1920, 1080), borderMode=cv2.BORDER_REPLICATE)
        img = crt_glass(img, t, 0.06, osd=4, sheen=0.06)
        ly = once('v03_ly', lambda: VLyric(20, x=1740, size=120, accent='#D9402B'))
        return ly.draw(img, t)
    # Phase B: pull back out through the CRT glass, swing to his face; the poster's light slides across him
    pl = once('v03', _v03_plate)
    lb = t - 61.42
    img = pl.frame(lb).copy()
    q = pl.anchor(lb, 'tv')
    tvc = cv2.resize(poster_now()[300:2400], (640, 480))
    if 64.02 <= t:
        tvc = cv2.resize(tv_static(int(t * 24)), (640, 480))
    if q:
        img = warp_quad(img, tvc, [p[:2] for p in q])
    cl = once('v03_char', lambda: chars.CharLayer('B-verse-03'))
    if cl.ok:
        rgb, a = cl.frame(lb, x=1180, y=1080, cx=0.5, cy=0.98, height=1150)
        a = a * clamp((lb - 0.55) / 0.5)                # he comes into frame as the camera swings round
        shutter = 0.75 + 0.25 * (int(t * 24) % 2)
        proj = cv2.resize(poster_now(), (1920, 2600))[600 + int(30 * lb * 2):1680 + int(30 * lb * 2)]
        proj = np.roll(proj, int(30 * lb), 1)
        light = 0.55 + 0.45 * proj * shutter
        rgb = rgb * (1 - 0.7 * a[..., None]) + rgb * light * (0.7 * a[..., None])
        img = chars.over(img, rgb, a)
    # L21 projected on the wall beside his face: cream light, keystoned, flickering; 投影 with a soft ghost
    gt = _map_gt(21)
    word = '僕らのことまるで投影'
    fl = 0.8 + 0.2 * (int(t * 24) % 2)
    for i, ch in enumerate(word):
        if t < gt[min(i, len(gt) - 1)]:
            continue
        x, y = 560 + i * 4, 230 + i * 74
        if ch in '投影':
            kit.map_glyph(img, ch, x + 12, y + 6, 62, -4.0, 1.04, '#EDE3CF', '#EDE3CF', 1.0, alpha=0.3 * fl)
        kit.map_glyph(img, ch, x, y, 62, -4.0, 1.0, '#F6F2E7', '#F6F2E7', 1.0, alpha=0.85 * fl)
    return channel_flip(_zh_fixed(img, t, 21, 61.6, ink='#EDE3CF', halo_col='#141A33'), t, 64.02, 64.39, seed=21)


R['B-verse-03'] = verse_03
tl.OWN_TYPE.add('B-verse-03')


# ---- B-verse-04: the summer commercial inside the TV -- she runs at us on a perfect beach; the slogan is the lyric ------
def _v04_plate():
    s = tl.BY_ID['B-verse-04']
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [-1.8, 1.5, 22.0], 'look': [3.0, 1.2, 60.0], 'fov': 44},
            {'t': d, 'pos': [-1.8, 1.5, 20.0], 'look': [3.0, 1.2, 58.0], 'fov': 44, 'ease': 'linear'}]
    return plate('B-verse-04', 's2_coast', {'world': 'noon', 'day': True, 'path': path, 'wallH': 0.5, 'poleSpacing': 16.3,
                                           'mirrors': [], 'moonPos': [160.0, 120.0, 720.0]}, 0.0, d, fps=24)


def sun_logo(img, cx, cy, r, t, label='夏ソーダ'):
    """paper-cut sun logo with spinning rays + brand"""
    import cv2
    from mv import text
    from .print_fx import hexc as H
    m = np.zeros((1080, 1920), np.float32)
    for k in range(12):
        a = k * np.pi / 6 + t * 1.6
        pts = np.array([[cx + np.cos(a - 0.12) * r * 1.15, cy + np.sin(a - 0.12) * r * 1.15],
                        [cx + np.cos(a) * r * 1.75, cy + np.sin(a) * r * 1.75],
                        [cx + np.cos(a + 0.12) * r * 1.15, cy + np.sin(a + 0.12) * r * 1.15]], np.int32)
        cv2.fillConvexPoly(m, pts, 1.0, cv2.LINE_AA)
    img = img + (H('#F08A3C')[None, None] - img) * m[..., None]
    d = np.zeros((1080, 1920), np.float32)
    cv2.circle(d, (int(cx), int(cy)), int(r), 1.0, -1, cv2.LINE_AA)
    img = img + (H('#F5C842')[None, None] - img) * d[..., None]
    gl, _ = text.layout_h(label, cx, cy, int(r * 0.55), 'dela', align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        img = img + (H('#D9402B')[None, None] - img) * f[..., None]
    return img


def verse_04(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    pl = once('v04', _v04_plate)
    img = pl.frame(local).copy()
    # sea sparkle: AM halftone glints on beats (flash on 65.13)
    nb = (t - 0.682) / BEAT
    ph = nb % 1.0
    rng = np.random.default_rng(int(nb))
    for _ in range(9):
        gx, gy = rng.uniform(1000, 1900), rng.uniform(560, 760)
        kit.halo(img, gx, gy, 40 * math.exp(-ph * 3) + 8, '#F6F2E7', 0.9 * math.exp(-ph * 3), period=7.0)
    if 65.13 <= t < 65.13 + 4 / 24:
        img = kit.dot_flash(img, 0.55 * (1 - (t - 65.13) / (4 / 24)), '#F5C842', 22)
    # her, running in: 500 -> 900 px, thick cream CM cut-out rim, AM sun glare behind her
    kit.halo(img, 760, 380, 520, '#F5C842', 0.55, period=12.0)
    cl = once('v04_char', lambda: chars.CharLayer('B-verse-04', rim_w=(2.0, 6.0, 0.0)))
    hgt = 500 + 400 * _ease_in(clamp(local / (s['end'] - s['start'])))
    frz = 1.0
    lt = local
    if 66.61 <= t < 66.61 + 3 / 24:                     # CM freeze-zoom on the laugh
        frz = 1.06
        lt = 66.61 - s['start']
    if cl.ok:
        rgb, a = cl.frame(lt, x=820, y=1080, cx=0.5, cy=0.98, height=hgt * frz)
        img = chars.over(img, rgb, a, shadow='#2D6BE0', shadow_amt=0.35)
    # CM supers: sun logo, brand, SUMMER 1985
    img = sun_logo(img, 230, 200, 92 * frz, t)
    gl, _ = text.layout_h('SUMMER 1985', 230, 360, 34, 'mincho', tracking=0.4, align='center')
    f, _ = text.render_glyphs(gl)
    if f is not None:
        img = img + (H('#1A1416')[None, None] - img) * f[..., None]
    # L22 slogan: 150 px sun-yellow with cobalt shadow, snapping per mora; bounces 6% with the freeze
    gt = _map_gt(22)
    word = '幸せに君なるはず'
    for i, ch in enumerate(word):
        if t < gt[min(i, len(gt) - 1)] - 0.09:
            continue
        k = clamp((t - gt[min(i, len(gt) - 1)] + 0.09) / (2 / 24))
        y = 120 + i * 118 * frz
        kit.map_glyph(img, ch, 1700 + 9, y + 9, int(112 * frz), 0.0, 1.0, '#2D6BE0', '#2D6BE0', 0.5, alpha=k)
        kit.map_glyph(img, ch, 1700 + (1 - k) * 24, y - (1 - k) * 24, int(112 * frz), 0.0, 1.0, '#F5C842', '#1A1416', 6.0)
    # the TV frame: rounded mask + barrel 0.08 + OSD 10
    img = crt_glass(img, t, 0.08, osd=10, sheen=0.08)
    # 67.00-67.35 版ずれ: the CM separates into its plates (yellow up, cobalt down)
    if t >= 67.00:                                         # separate into a yellow plate (up) and a cobalt plate (down)
        from . import print_fx
        k = clamp((t - 67.00) / 0.35)
        sh = int(60 * k)
        lum = img.mean(-1)
        cov_y = np.clip((img[..., 0] + img[..., 1] - 2 * img[..., 2]) * 1.4 + (1 - lum) * 0.25, 0, 1)
        cov_b = np.clip((img[..., 2] - img[..., 0]) * 1.6 + (1 - lum) * 0.75, 0, 1)
        cov_y, cov_b = np.roll(cov_y, -sh, 0), np.roll(cov_b, sh, 0)
        yd = np.where(cov_y > 0.9, 1.0, print_fx._screen(cov_y, 8.0, 75.0))[..., None]
        bd = np.where(cov_b > 0.9, 1.0, print_fx._screen(cov_b, 8.0, 15.0))[..., None]
        sep = H('#EDE3CF') * (1 - yd) * (1 - bd) + H('#F5C842') * yd * (1 - bd) + H('#2D6BE0') * bd * (1 - yd) + H('#1E2550') * yd * bd
        img = img + (sep - img) * clamp(k * 1.6)
    return _zh_fixed(img, t, 22, 64.3, ink='#1A1416', halo_col='#EDE3CF')


R['B-verse-04'] = verse_04
tl.OWN_TYPE.add('B-verse-04')


# ---- B-chorus2-01: under the eaves -- ten furin light one per syllable as he walks; relay from the test-card circle ----
def _c201_plate():
    s = tl.BY_ID['B-chorus2-01']
    d = s['end'] - s['start']
    v = 1.3
    path = []
    for i in range(int(round(d * 24)) + 1):
        tt = i / 24
        u = min(1.0, tt / 1.1)
        e = u * u * (3 - 2 * u)
        z = 14.0 + v * tt
        y = 6.2 + (1.5 - 6.2) * e
        look_y = 9.0 + (1.9 - 9.0) * e
        path.append({'t': tt, 'pos': [-2.6, round(y, 4), round(z, 4)], 'look': [-6.4, round(look_y, 4), round(z + 1.2 - 0.6 * e, 4)],
                     'fov': 44, 'ease': 'linear'})
    return plate('B-chorus2-01', 's2_coast', {'world': 'night', 'path': path, 'wallH': 0.5, 'poleSpacing': 16.3, 'mirrors': [],
                                             'vending': [], 'furin': {'z0': 14.6, 'dz': 0.62, 'n': 10, 'x': -5.6},
                                             'moonPos': [-60.0, 110.0, 360.0]}, 0.0, d, fps=24)


def chorus2_01(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    pl = once('c201', _c201_plate)
    img = pl.frame(local).copy()
    # relay landing: the paper-cut moon sits where the test-card circle was, then the crane carries it up and away
    k = _ease_io(clamp(local / 1.1))
    mx, my = 820 + 140 * k, 467 - 560 * k
    img = moon_with_halo(img, mx, my, 57 + 10 * k, 0.4 + 0.3 * math.exp(-local * 2))
    gt = _map_gt(26)
    word = '思い浮かぶの君ばかり'
    F = pl.anchor(local, 'furin') or []
    for i, ch in enumerate(word):
        if i >= len(F) or not (0 < F[i][2] < 1.001):
            continue
        x, y = F[i][0], F[i][1]
        if not (-100 < x < 2020 and -200 < y < 1200):
            continue
        tg = gt[min(i, len(gt) - 1)]
        on = t >= tg
        swing = 6.0 * math.sin(2 * math.pi * 1.4 * (t - tg)) * math.exp(-(t - tg) * 1.5) if on else 1.5 * math.sin(t * 2 + i)
        lit = clamp((t - tg) / (6 / 24)) if on else 0.0
        col = '#D9402B' if ch == '君' else ('#7FC8B8' if lit > 0 else '#C9D3DC')
        if lit > 0:
            kit.halo(img, x, y + 20, 70 * lit + 10, col, 0.8 * lit, period=7.0)
        m = np.zeros((1080, 1920), np.float32)
        cv2.ellipse(m, (int(x), int(y + 22)), (24, 22), 0, 180, 360, 1.0, -1, cv2.LINE_AA)
        img = img + (H(col)[None, None] - img) * (m * (0.55 + 0.45 * lit))[..., None]
        # tanzaku strip with its glyph, swinging from the bell
        tx, ty = x + swing * 3, y + 118
        m = np.zeros((1080, 1920), np.float32)
        pts = cv2.boxPoints(((tx, ty), (64, 150), swing))
        cv2.fillConvexPoly(m, pts.astype(np.int32), 1.0, cv2.LINE_AA)
        img = img + (H('#EDE3CF')[None, None] - img) * m[..., None]
        kit.map_glyph(img, ch, tx, ty, 58, -swing, 1.0, '#1A1416' if ch != '君' else '#D9402B', '#EDE3CF', 1.0)
        if on and t - tg < 0.12:                         # the ring: a glass glint
            kit.halo(img, x + 8, y + 14, 26, '#F6F2E7', 1.0, period=5.0)
    # him walking left, side-on, moonlight on his right side
    cl = once('c201_char', lambda: chars.CharLayer('B-chorus2-01'))
    if cl.ok:
        rgb, a = cl.frame(local, x=760, y=1060, cx=0.5, cy=0.98, height=640)
        side = np.clip((kit._XS - 700) / 120.0, 0, 1) * a * _dots_k(0.35, 8.0)
        rgb = rgb + (H('#C9D3DC')[None, None] - rgb) * (side * 0.5)[..., None]
        img = chars.over(img, rgb, a * clamp((local - 0.7) / 0.4), shadow='#141A33')
    # eave edge in the foreground passing at 2x
    fx_ = (-local * 2 * 260) % 520
    m = np.zeros((1080, 1920), np.float32)
    for x0 in np.arange(-520 + fx_, 1920 + 520, 520):
        cv2.rectangle(m, (int(x0), 0), (int(x0) + 34, 70), 1.0, -1)
    cv2.rectangle(m, (0, 0), (1920, 26), 1.0, -1)
    img = img + (H('#141018')[None, None] - img) * (m * clamp((local - 0.5) / 0.6))[..., None]
    return _zh_fixed(img, t, 26, 76.2, ink='#EDE3CF', halo_col='#141A33')


R['B-chorus2-01'] = chorus2_01
tl.OWN_TYPE.add('B-chorus2-01')


# ---- B-chorus2-02: the vending machine at midnight -- ticker, roulette stopping 0 0 1 2, moths; melt into the map -------
def vending_face(t, ticker, t0, digits, stops, seed=3, on='#7FC8B8'):
    """flat vending-machine front (720 x 1300): 12 can dummies in halftone, 16-dot ticker band, 4-digit roulette"""
    import cv2
    from . import print_fx
    from .print_fx import hexc as H, clock_grid, dot_matrix
    key = ('vendbase', seed)
    if key not in _cache:
        im = np.empty((1300, 720, 3), np.float32)
        im[:] = H('#EDE3CF')
        cv2.rectangle(im, (40, 40), (680, 700), tuple(float(v) for v in H('#141018')), -1)
        rng = np.random.default_rng(seed)
        cans = ['#D9402B', '#2C4C9A', '#F5C842', '#7FC8B8', '#F08A3C', '#EDE3CF']
        for r in range(3):
            for c in range(4):
                x, y = 80 + c * 150, 70 + r * 210
                col = cans[rng.integers(len(cans))]
                cv2.rectangle(im, (x, y), (x + 100, y + 150), tuple(float(v) for v in H(col)), -1)
                cv2.rectangle(im, (x, y + 160), (x + 100, y + 180), tuple(float(v) for v in H('#F6F2E7')), -1)
        dk = np.tile(_dots_k(0.3, 8.0)[:, :720], (2, 1))[:1300]
        im[40:700, 40:680] = im[40:700, 40:680] * (1 - dk[40:700, 40:680, None] * 0.25)
        cv2.rectangle(im, (40, 1060), (680, 1220), tuple(float(v) for v in H('#141018')), -1)
        _cache[key] = im
    im = _cache[key].copy()
    sc = int(max(0.0, t - t0) * 24) * 2 - 60
    tk, _ = print_fx.led_board(ticker, cols=60, rows=16, dot=10, on=on, off='#16302E', bg='#0B1414', scroll=sc)
    tk = cv2.resize(tk, (640, 170), interpolation=cv2.INTER_AREA)
    im[740:910, 40:680] = tk
    shown = ''
    for j, (dg, st) in enumerate(zip(digits, stops)):
        shown += dg if t >= st else str(int((t * 24 * 4 + j * 3)) % 10)       # spinning on 16ths until it stops
    rl = np.asarray(dot_matrix(clock_grid(shown, colon_on=False), pitch=9, on='#F08A3C', bg='#0B1414'), np.float32)
    rl = cv2.resize(rl, (560, 130), interpolation=cv2.INTER_AREA)
    im[1075:1205, 80:640] = rl
    return im


def _c202_plate():
    s = tl.BY_ID['B-chorus2-02']
    d = s['end'] - s['start']
    zc = 40.0
    path = [{'t': 0.0, 'pos': [-2.05, 1.35, zc - 1.25], 'look': [-4.2, 1.05, zc - 0.55], 'fov': 50},
            {'t': 1.48, 'pos': [-2.15, 1.35, zc - 1.10], 'look': [-4.2, 1.05, zc - 0.58], 'fov': 48.5, 'ease': 'inout'},
            {'t': d, 'pos': [-2.35, 1.35, zc - 0.85], 'look': [-4.2, 1.05, zc - 0.6], 'fov': 48, 'ease': 'linear'}]
    return plate('B-chorus2-02', 's2_coast', {'world': 'night', 'path': path, 'wallH': 0.5, 'poleSpacing': 16.3,
                                             'mirrors': [70.0], 'vending': [zc]}, 0.0, d, fps=24)


def chorus2_02(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    pl = once('c202', _c202_plate)
    img = pl.frame(local).copy()
    q = pl.anchor(local, 'vend')
    stops = [79.94, 80.68, 81.42, 82.16]
    fl = 0.9 + 0.1 * ((int((t - 0.682) / (BEAT / 2)) % 2))
    if q and all(0 < p[2] < 1.001 for p in q):
        face = vending_face(t, '初夏零時過ぎたばかり', 79.25, '0012', stops)
        quad = _quad_sorted(q)
        img = led_on_quad(img, quad, face * fl)
        cx, cy = float(quad[:, 0].mean()), float(quad[:, 1].mean())
        kit.halo(img, cx, cy, 520, '#F08A3C', 0.35 * fl, period=10.0)
        # moths circling the light, flapping on 2s; they scatter on 80.68
        rng = np.random.default_rng(12)
        for j in range(12):
            a0, r0, sp = rng.uniform(0, 6.28), rng.uniform(90, 240), rng.uniform(1.5, 3.2)
            sc = 1.0 + (3.0 * clamp((t - 80.68) / 0.6) if t >= 80.68 else 0.0)
            ang = a0 + sp * t
            x = cx + math.cos(ang) * r0 * sc
            y = cy - 120 + math.sin(ang * 1.3) * r0 * 0.6 * sc
            flap = (int(t * 12) + j) % 2
            m = np.zeros((1080, 1920), np.float32)
            cv2.ellipse(m, (int(x - 5), int(y)), (7, 3 if flap else 6), 30 if flap else 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            cv2.ellipse(m, (int(x + 5), int(y)), (7, 3 if flap else 6), -30 if flap else 0, 0, 360, 1.0, -1, cv2.LINE_AA)
            img = img + (H('#EDE3CF')[None, None] - img) * (m * 0.85)[..., None]
    # him: waist-up, screen-left half, heat-orange light on the machine side
    cl = once('c202_char', lambda: chars.CharLayer('B-chorus2-02'))
    if cl.ok:
        rgb, a = cl.frame(local, x=470, y=1080, cx=0.5, cy=0.7, height=1150)
        side = np.clip((kit._XS - 430) / 160.0, 0, 1) * a * _dots_k(0.45 * fl, 8.0)
        rgb = rgb + (H('#F08A3C')[None, None] - rgb) * (side * 0.55)[..., None]
        img = chars.over(img, rgb, a, shadow='#141A33')
    ly = once('c202_ly', lambda: VLyric(27, x=880, y=110, size=86, accent='#D9402B'))
    img = ly.draw(img, t)
    # 81.80-82.16: the ticker's mint dots spread over the frame and re-form as the night town map
    if t >= 81.80:
        k = clamp((t - 81.80) / 0.36)
        dots = led_dots(img, pitch=8 + 18 * k, ripple=5 * k, t=t, gap='#0B1414')
        mint = dots.mean(-1, keepdims=True) * H('#7FC8B8')[None, None] * 1.4
        img = img + (mint - img) * k
    return img


R['B-chorus2-02'] = chorus2_02
tl.OWN_TYPE.add('B-chorus2-02')


# ---- B-chorus2-04: on the seawall at night -- the moon path on the sea is the lyric column; a swell rises over the wall -
def chorus2_04(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    push = 1.0 + 0.015 * clamp(local / 2.2)
    drop = _ease_in(clamp((t - 87.35) / 0.74))
    img, hor = night_bay(260)
    hy = 330                                               # looking down from the wall: sea fills the lower 2/3
    sea_top = int(hor)
    shift = hy - sea_top
    img = np.roll(img, shift, 0)
    if shift > 0:                                          # extend the sky upward
        img[:shift] = img[shift:shift + 1]
    sea = np.zeros((1080, 1920, 3), np.float32)
    g = np.clip((kit._YS - hy) / (1080 - hy), 0, 1)[..., None]
    sea[:] = H('#1E2550') * (1 - g) + H('#141A33') * g
    dep = np.maximum(kit._YS - hy, 0.0)
    ph = dep / (2.0 + 0.018 * dep) - t * 2.4 + np.sin(kit._XS / (60 + 0.4 * dep) + dep / 40.0) * 2.2
    brk = np.sin(kit._XS / (25 + 0.3 * dep) + dep / 7.0 + t)
    swell = ((np.sin(ph) > 0.82) & (brk > -0.2)).astype(np.float32)
    sea = sea + (H('#2C4C9A')[None, None] - sea) * (swell * _dots_k(0.35, 8.0))[..., None]
    img = np.where((kit._YS > hy)[..., None], sea, img)
    if push != 1.0:
        img = cv2.warpAffine(img, cv2.getRotationMatrix2D((960, 540), 0, push), (1920, 1080), borderMode=cv2.BORDER_REFLECT)
    mx = 1080
    img = moon_with_halo(img, mx, 150, 62, 0.4)
    # the moon path: a vertical column of silver dots on the sea, rippled by passing wave lines
    ys = kit._YS
    wave = 8 * np.sin(ys / 13.0 - t * 5.0) + 6 * np.sin(ys / 5.0 + t * 7.0)
    width = 26 + (ys - hy) * 0.22
    col = np.clip(1 - np.abs(kit._XS - mx - wave) / np.maximum(width, 1), 0, 1) * (ys > hy + 4)
    lines = (np.sin(ys / 7.0 - t * 6.0 + np.sin(kit._XS / 50.0)) > 0.35).astype(np.float32)
    path = col * lines
    img = img + (H('#C9D3DC')[None, None] - img) * (path * _dots_k(0.75, 7.0) + path * 0.25)[..., None]
    # L29 inside the moon path, 110 px cream, formed out of the silver dots per mora; 幸せ breaks apart on 86.61
    gt = _map_gt(29)
    word = '君に幸せあげられない'
    ystart, step = hy + 60, 70
    for i, ch in enumerate(word):
        if t < gt[min(i, len(gt) - 1)]:
            continue
        y = ystart + i * step
        if y > 1040:
            break
        k = clamp((t - gt[min(i, len(gt) - 1)]) / (4 / 24))
        size = int(52 + 0.07 * (y - hy))
        if ch in '幸せ' and t >= 86.61:
            br = clamp((t - 86.61) / 0.5)
            if br >= 1:
                continue
            tmp = np.zeros((1080, 1920, 3), np.float32)
            kit.map_glyph(tmp, ch, mx, y, size, 0.0, 1.0, '#EDE3CF', '#EDE3CF', 0.5)
            mm = (tmp.mean(-1) > 0.3).astype(np.float32) * (1 - _dots_k(br, 8.0))
            mm = np.roll(mm, int(30 * br * (1 if ch == '幸' else -1)), 1)
            img = img + (H('#EDE3CF')[None, None] - img) * mm[..., None]
            continue
        xw = mx + 8 * math.sin(y / 13.0 - t * 5.0)
        tmp = np.zeros((1080, 1920, 3), np.float32)
        kit.map_glyph(tmp, ch, xw, y, size, 0.0, 1.0, '#EDE3CF', '#EDE3CF', 0.5)
        mm = (tmp.mean(-1) > 0.3).astype(np.float32)
        mm = mm * (1 - (1 - k) * (1 - _dots_k(k, 7.0)))
        mm = mm * (1 - 0.6 * lines * (np.abs(kit._YS - y) < size * 0.5))
        img = img + (H('#EDE3CF')[None, None] - img) * mm[..., None]
    # him, back view on the seawall top, screen-left third; t-shirt hem and hair in the wind (mesh sway)
    cl = once('c204_char', lambda: chars.CharLayer('B-chorus2-04'))
    if cl.ok:
        rgb, a = cl.frame(0.0, x=520, y=1060 + 300 * drop, cx=0.5, cy=0.97, height=560)
        sway = (3.5 * np.sin(2 * math.pi * 1.6 * t + kit._YS / 30.0)).astype(np.float32)
        rgb = cv2.remap(rgb, (kit._XS + sway).astype(np.float32), kit._YS, cv2.INTER_LINEAR)
        a = cv2.remap(a, (kit._XS + sway).astype(np.float32), kit._YS, cv2.INTER_LINEAR)
        rim = np.clip(a - cv2.erode(a, np.ones((7, 7), np.uint8)), 0, 1) * (kit._XS > 520)
        rgb = rgb + (H('#EDE3CF')[None, None] - rgb) * (rim * 0.8)[..., None]
        img = chars.over(img, rgb, a, shadow='#141A33')
    # the seawall edge in the foreground
    m = (kit._YS > 1000 + 300 * drop).astype(np.float32)
    img = img + (H('#26345E')[None, None] - img) * (m * 0.95)[..., None]
    # 87.35-88.09: the swell rises over the wall and the camera; halftone foam at the crest
    if t >= 87.35:
        k = clamp((t - 87.35) / 0.74)
        crest = 1080 - 1250 * _ease_in(k) + 30 * np.sin(kit._XS / 90.0 + t * 4)
        water = (kit._YS > crest).astype(np.float32)
        img = img + (H('#1E2550')[None, None] - img) * (water * 0.92)[..., None]
        foam = np.clip(1 - np.abs(kit._YS - crest) / 40.0, 0, 1)
        img = img + (H('#C9D3DC')[None, None] - img) * (foam * _dots_k(0.8, 10.0))[..., None]
    return _zh_fixed(img, t, 29, 85.15, y=1012, ink='#EDE3CF', halo_col='#141A33')


R['B-chorus2-04'] = chorus2_04
tl.OWN_TYPE.add('B-chorus2-04')


# ---- shared: dusk over the seawall (paper-cut vermilion sun, orange halftone sea, the wall receding) -----------------
def dusk_wall(t, hy=470, sun=(1460, 440, 120), vp_x=1500, wall_top=640):
    """a 2D printed dusk view along the seawall: sky band, low sun, glittering orange sea, wall receding to vp"""
    import cv2
    from .print_fx import hexc as H
    img = np.empty((1080, 1920, 3), np.float32)
    g = np.clip(kit._YS / hy, 0, 1)[..., None]
    img[:] = H('#2B2350') * (1 - g) + H('#F08A3C') * g
    img = img + (H('#F5C842')[None, None] - img) * (np.clip(1 - np.abs(kit._YS - hy + 40) / 90.0, 0, 1) * 0.55)[..., None]
    sx, sy, sr = sun
    m = np.zeros((1080, 1920), np.float32)
    cv2.circle(m, (int(sx), int(sy)), int(sr), 1.0, -1, cv2.LINE_AA)
    m *= (kit._YS < hy)
    img = img + (H('#D9402B')[None, None] - img) * m[..., None]
    sea = (kit._YS >= hy).astype(np.float32)
    seac = H('#F08A3C') * 0.8 + H('#D9402B') * 0.2
    img = img + (seac[None, None] - img) * sea[..., None]
    dep = np.maximum(kit._YS - hy, 0.0)
    ph = dep / (1.5 + 0.02 * dep) - t * 2.0 + np.sin(kit._XS / (60 + 0.4 * dep) + dep / 30.0) * 2.0
    lines = ((np.sin(ph) > 0.85) & (sea > 0)).astype(np.float32)
    img = img + (H('#1E2550')[None, None] - img) * (lines * 0.45)[..., None]
    glit = np.clip(1 - np.abs(kit._XS - sx) / (40 + 0.6 * dep), 0, 1) * sea * lines
    img = img + (H('#F5C842')[None, None] - img) * glit[..., None]
    # the wall: a concrete band receding from the lower-left to the vanishing point
    pts = np.array([[0, 1080], [0, wall_top + 80], [vp_x, hy + 6], [vp_x + 6, hy + 10], [1920, 1080]], np.int32)
    wm = np.zeros((1080, 1920), np.float32)
    cv2.fillPoly(wm, [pts], 1.0, cv2.LINE_AA)
    return img, wm


# ---- B-bridge1-02: last summer at dusk -- the chalk 相合傘 draws itself; she sits beside it, shy -------------------------
def bridge1_02(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    arc = 10.0 * clamp(local / (s['end'] - s['start']))
    push = 1.0 + 0.04 * _ease_io(clamp((t - 93.28) / 0.6))
    img, wm = dusk_wall(t, hy=420, sun=(1560, 380, 110), vp_x=1700, wall_top=560)
    conc = concrete_dusk()
    img = img + (conc - img) * wm[..., None]
    # the doodle in the screen-left foreground, foreshortened on the concrete
    um, sun, moon, (sx, sy), (mx, my) = aiaigasa_masks()
    draw_k = clamp((t - 91.05) / (91.79 - 91.05))
    sig_k = clamp((t - 91.79) / 0.45)
    def reveal(mask, k, seed):
        if k <= 0:
            return np.zeros_like(mask)
        if k >= 1:
            return mask
        order = np.clip((kit._YS - 150) / 800.0 + 0.15 * np.sin(kit._XS / 60.0 + seed), 0, 1)
        return mask * (order < k)
    doodle = chalk(reveal(um, draw_k, 0), 1) + chalk(reveal(sun, sig_k, 1), 2) + chalk(reveal(moon, sig_k, 2), 3)
    # L31 down the umbrella handle per mora; 愛 at the umbrella tip in vermilion chalk
    gt = _map_gt(31)
    word = '愛とか言っていたって'
    ver = np.zeros((1080, 1920), np.float32)
    for i, ch in enumerate(word):
        if t < gt[min(i, len(gt) - 1)]:
            continue
        key = ('b102g', i)
        if key not in _cache:
            if i == 0:
                gl = text.layout_v(ch, 900, 70, 96, 'mincho')
            else:
                gl = text.layout_v(ch, 990, 230 + (i - 1) * 74, 72, 'mincho')
            f, _ = text.render_glyphs(gl)
            _cache[key] = f
        f = _cache[key]
        if f is None:
            continue
        if i == 0:
            ver = np.maximum(ver, chalk(f, 9, 0.25))
        else:
            doodle = doodle + chalk(f, 10 + i, 0.25)
    doodle = np.clip(doodle, 0, 1)
    # lay the doodle on the ground: keystone into the lower-left of the frame
    src = np.float32([[300, 0], [1500, 0], [1500, 1080], [300, 1080]])
    dst = np.float32([[60, 470], [1000, 470], [1240, 1080], [-320, 1080]])
    Hm = cv2.getPerspectiveTransform(src, dst)
    dg = cv2.warpPerspective(doodle, Hm, (1920, 1080))
    vg = cv2.warpPerspective(ver, Hm, (1920, 1080))
    img = img + (H('#F6F2E7')[None, None] - img) * dg[..., None]
    img = img + (H('#D9402B')[None, None] - img) * vg[..., None]
    # long dusk shadows across the concrete
    sh = np.clip(np.sin((kit._XS * 0.3 + kit._YS) / 80.0) * 0.5 + 0.5, 0, 1) * (kit._YS > 700) * wm * 0.0
    # her, screen-right, sitting, sun-yellow rim light
    cl = once('b102_char', lambda: chars.CharLayer('B-bridge1-02'))
    if cl.ok:
        rgb, a = cl.frame(local, x=1360, y=1080, cx=0.5, cy=0.95, height=760)
        rim = np.clip(a - cv2.erode(a, np.ones((9, 9), np.uint8)), 0, 1) * (kit._XS > 1360)
        rgb = rgb + (H('#F5C842')[None, None] - rgb) * (rim * 0.9)[..., None]
        img = chars.over(img, rgb, a, shadow='#2B2350', shadow_off=(-30, 14), shadow_amt=0.5)
    M = cv2.getRotationMatrix2D((960, 540), -arc * 0.3, push)
    M[0, 2] -= arc * 6
    img = cv2.warpAffine(img, M, (1920, 1080), borderMode=cv2.BORDER_REFLECT)
    return _zh_fixed(img, t, 31, 90.8, ink='#1A1416', halo_col='#EDE3CF')


R['B-bridge1-02'] = bridge1_02
tl.OWN_TYPE.add('B-bridge1-02')


# ---- B-bridge1-03: she watches him walk away along the wall; the lyric is only long shadows on the concrete ------------
def bridge1_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    push = 1.0 + 0.02 * clamp(local / (s['end'] - s['start']))
    sink = clamp((t - 96.24) / 0.7) * 40
    img, wm = dusk_wall(t, hy=520, sun=(1650, 470 + sink, 70), vp_x=1180, wall_top=600)
    conc = concrete_dusk()
    img = img + (conc * 0.85 - img) * wm[..., None]
    # glints on beats
    ph = ((t - 0.682) / BEAT) % 1.0
    rng = np.random.default_rng(int((t - 0.682) / BEAT))
    for _ in range(6):
        kit.halo(img, rng.uniform(1250, 1900), rng.uniform(540, 760), 30 * math.exp(-ph * 3) + 6, '#F5C842',
                 0.9 * math.exp(-ph * 3), period=7.0)
    # the curve mirror at the bend + his reflection flash on 95.50
    mxp, myp = 1205, 470
    m = np.zeros((1080, 1920), np.float32)
    cv2.line(m, (mxp, myp + 18), (mxp, myp + 64), 1.0, 3, cv2.LINE_AA)
    img = img + (H('#D9402B')[None, None] - img) * m[..., None]
    m = np.zeros((1080, 1920), np.float32)
    cv2.circle(m, (mxp, myp), 16, 1.0, -1, cv2.LINE_AA)
    flash = math.exp(-max(0.0, t - 95.50) * 6) if t >= 95.50 else 0.0
    img = img + (H('#F5D7A0')[None, None] * (1 + 0.3 * flash) - img) * m[..., None]
    if flash > 0.05:
        kit.halo(img, mxp, myp, 50 * flash + 10, '#F6F2E7', flash, period=6.0)
    # him: a dot-person walking away along the wall top (90 -> 40 px)
    u = clamp(local / (s['end'] - s['start']))
    x = 760 + (1150 - 760) * u
    y = 640 + (530 - 640) * u
    img = kit.dot_walker(img, x, y, 90 - 50 * u, local * 1.8, colors=('#1A1416', '#F6F2E7', '#1A1416', '#1A1416'),
                         pitch=max(2.6, (90 - 50 * u) / 16))
    # L32 as invisible glyphs on the wall: only their long indigo halftone shadows print, stretching as the sun sinks
    gt = _map_gt(32)
    word = '行くべきなのさ'
    shadow = np.zeros((1080, 1920), np.float32)
    for i, ch in enumerate(word):
        if t < gt[min(i, len(gt) - 1)]:
            continue
        key = ('b103g', i)
        if key not in _cache:
            gl, _ = text.layout_h(ch, 960, 540, 150, 'mincho', align='center')
            _cache[key], _ = text.render_glyphs(gl)
        f = _cache[key]
        if f is None:
            continue
        bx = 560 + i * 120
        by = 1000 - i * 62
        stretch = 2.6 + 0.9 * clamp((t - 94.34) / 2.6) + sink / 40
        src = np.float32([[880, 460], [1040, 460], [1040, 620], [880, 620]])
        sc_ = 1.0 - i * 0.08
        dst = np.float32([[bx - 150 * stretch * sc_, by - 60 * sc_], [bx - 50 * stretch * sc_, by - 70 * sc_ - 25 * stretch * sc_],
                          [bx + 70 * sc_, by], [bx - 40 * sc_, by + 20 * sc_]])
        Hm = cv2.getPerspectiveTransform(src, dst)
        shadow = np.maximum(shadow, cv2.warpPerspective(f, Hm, (1920, 1080)))
    shadow = shadow * wm
    img = img + (H('#1E2550')[None, None] - img) * (shadow * (0.55 + 0.45 * _dots_k(0.75, 8.0)))[..., None]
    # her back, out of focus, foreground left, cropped at the waist; bob and neckerchief in the wind
    cl = once('b103_char', lambda: chars.CharLayer('B-bridge1-03'))
    if cl.ok:
        rgb, a = cl.frame(0.0, x=330, y=1080, cx=0.5, cy=0.6, height=1500)
        sway = (4.0 * np.sin(2 * math.pi * 1.4 * t + kit._YS / 40.0) * (kit._YS < 500)).astype(np.float32)
        rgb = cv2.remap(rgb, (kit._XS + sway).astype(np.float32), kit._YS, cv2.INTER_LINEAR)
        a = cv2.remap(a, (kit._XS + sway).astype(np.float32), kit._YS, cv2.INTER_LINEAR)
        rgb = cv2.GaussianBlur(rgb, (0, 0), 4.0)
        a = cv2.GaussianBlur(a, (0, 0), 3.0)
        img = chars.over(img, rgb, a)
    if push != 1.0:
        img = cv2.warpAffine(img, cv2.getRotationMatrix2D((1180, 520), 0, push), (1920, 1080), borderMode=cv2.BORDER_REFLECT)
    return _zh_fixed(img, t, 32, 94.34, ink='#1A1416', halo_col='#EDE3CF')


R['B-bridge1-03'] = bridge1_03
tl.OWN_TYPE.add('B-bridge1-03')


# ---- shared: night bokeh backdrop (sea and sky as halftone discs) ----------------------------------------------------
def bokeh_night(t, seed=4, top='#141A33', bottom='#1E2550', cols=('#C9D3DC', '#F08A3C', '#7FC8B8')):
    import cv2
    from .print_fx import hexc as H
    key = ('bokeh', seed, top, bottom)
    if key not in _cache:
        img = np.empty((1080, 1920, 3), np.float32)
        g = (kit._YS / 1080)[..., None]
        img[:] = H(top) * (1 - g) + H(bottom) * g
        rng = np.random.default_rng(seed)
        for _ in range(26):
            x, y, r = rng.uniform(0, 1920), rng.uniform(380, 1000), rng.uniform(30, 110)
            c = cols[rng.integers(len(cols))]
            kit.halo(img, x, y, r, c, rng.uniform(0.25, 0.6), period=10.0)
        _cache[key] = img
    return _cache[key].copy()


# ---- B-bridge1-05: now, at night -- the lighthouse beam crosses his face every second beat ----------------------------
def bridge1_05(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    img = bokeh_night(t)
    push = 1.0 + 0.05 * clamp(local / (s['end'] - s['start']))
    # the beam: an AM halftone fan sweeping left -> right, passing on 100.68 and 102.16
    passes = [100.68, 102.16]
    bx = None
    for p in passes:
        k = (t - p) / 0.62
        if -0.6 <= k <= 0.6:
            bx = 960 + 1500 * k
    if bx is not None:
        ang = np.arctan2(kit._XS - (bx - 300), -(kit._YS + 900))
        fan = np.clip(1 - np.abs(ang) / 0.22, 0, 1)
        img = img + (H('#F6F2E7')[None, None] - img) * (fan * _dots_k(0.6, 12.0) * 0.8)[..., None]
    cl = once('b105_char', lambda: chars.CharLayer('B-bridge1-05'))
    if cl.ok:
        rgb, a = cl.frame(local, x=1120, y=1080, cx=0.5, cy=0.62, height=1300 * push)
        if bx is not None:                                    # a cream halftone band crosses his face
            band = np.clip(1 - np.abs(kit._XS - bx) / 140.0, 0, 1) * a
            rgb = rgb + (H('#EDE3CF')[None, None] - rgb) * (band * (0.35 + 0.65 * _dots_k(0.8, 8.0)))[..., None]
        img = chars.over(img, rgb, a, shadow='#141A33')
    # L34 left of his face; つらい cracks open in hairline gaps
    ly = once('b105_ly', lambda: VLyric(34, x=560, y=140, accent='#D9402B'))
    img = ly.draw(img, t)
    gt = ly.times
    if len(ly.glyphs) > 6 and t >= gt[3]:
        rng = np.random.default_rng(34)
        crack = np.zeros((1080, 1920), np.float32)
        for i in (3, 4, 5):
            if i >= len(ly.glyphs) or t < gt[i]:
                continue
            g = ly.glyphs[i]
            k = clamp((t - gt[i]) / 0.5)
            for _ in range(5):
                x0, y0 = g['cx'] + rng.uniform(-30, 30), g['cy'] + rng.uniform(-30, 30)
                pts = [(x0, y0)]
                for _ in range(4):
                    x0 += rng.uniform(-18, 18) * k
                    y0 += rng.uniform(-18, 18) * k
                    pts.append((x0, y0))
                cv2.polylines(crack, [np.array(pts, np.int32)], False, 1.0, 2, cv2.LINE_AA)
        img = img + (H('#1A1416')[None, None] - img) * crack[..., None]
    return img


R['B-bridge1-05'] = bridge1_05
tl.OWN_TYPE.add('B-bridge1-05')


# ---- B-bridge1-06: she understands, nods, smiles, cries -- her printed edge starts to come apart into dots ----------
def bridge1_06(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    # sky shifts dusk -> blue in halftone steps on 104.39 / 105.87 / 107.35
    steps = sum(1 for b in (104.39, 105.87, 107.35) if t >= b)
    skies = [('#F08A3C', '#F5C842'), ('#C9688A', '#F08A3C'), ('#5A5E86', '#C9688A'), ('#2C4C9A', '#5A5E86')]
    top, bot = skies[steps]
    img = np.empty((1080, 1920, 3), np.float32)
    g = (kit._YS / 1080)[..., None]
    img[:] = H(top) * (1 - g) + H(bot) * g
    img = img + (H(bot)[None, None] - img) * (_dots_k(0.3, 10.0) * 0.5)[..., None]
    push = 1.0 + 0.06 * clamp(local / (s['end'] - s['start']))
    cl = once('b106_char', lambda: chars.CharLayer('B-bridge1-06', speed=0.68))
    if cl.ok:
        rgb, a = cl.frame(local, x=760, y=1080, cx=0.5, cy=0.6, height=1350 * push)
        # dot-scatter edge from 106.61, reversing after 108.09
        sc = clamp((t - 106.61) / 1.48) if t < 108.09 else clamp(1 - (t - 108.09) / 0.74)
        if sc > 0:
            ring = np.clip(cv2.dilate(a, np.ones((19, 19), np.uint8)) - cv2.erode(a, np.ones((19, 19), np.uint8)), 0, 1)
            dots = _dots_k(0.6, 9.0) * ring
            rng = np.random.default_rng(int(local * 24))
            up = int(60 * sc)
            drift = np.roll(dots, -up, 0) * sc
            jitter = np.roll(drift, int(rng.integers(-3, 4)), 1)
            a = a * (1 - ring * sc * 0.8)
            img = img + (H('#EDE3CF')[None, None] - img) * (jitter * 0.9)[..., None]
        # sky light shifts her inks toward blue as the sky does
        rgb = rgb * (0.9 + 0.1 * H(top)[None, None])
        img = chars.over(img, rgb, a, shadow='#2B2350')
    ly1 = once('b106_ly1', lambda: VLyric(35, x=1720, accent='#D9402B'))
    img = ly1.draw(img, t)
    ly2 = once('b106_ly2', lambda: VLyric(36, x=1720, accent='#D9402B', hide=lambda i, tt: i == 5 and tt < 107.0 + BEAT))
    img = ly2.draw(img, t)
    if len(ly2.glyphs) > 5 and t >= ly2.times[5] and t < ly2.times[5] + BEAT:     # 壊 splits into dots, re-forms a beat later
        g = ly2.glyphs[5]
        k = (t - ly2.times[5]) / BEAT
        tmp = np.zeros((1080, 1920, 3), np.float32)
        kit.map_glyph(tmp, g['ch'], g['cx'], g['cy'], int(ly2.size), 0.0, 1.0, '#EDE3CF', '#EDE3CF', 0.5)
        mm = (tmp.mean(-1) > 0.3).astype(np.float32)
        sp = math.sin(math.pi * k)
        mm = mm * (1 - _dots_k(1 - 0.6 * sp, 9.0) * 0) * _dots_k(1 - 0.55 * sp, 9.0)
        img = img + (H('#EDE3CF')[None, None] - img) * mm[..., None]
    return img


R['B-bridge1-06'] = bridge1_06
tl.OWN_TYPE.add('B-bridge1-06')


# ---- festival shots (chorus3-02 / 03 / 07): the lit street, the dot crowd, her and him -------------------------------
def _fest_plate(sid, path, **kw):
    s = tl.BY_ID[sid]
    d = s['end'] - s['start']
    params = {'world': 'festival', 'litT': -10.0, 'shutterT': -10.0, 'crowdT': -10.0, 'crowd': 900, 'path': path}
    params.update(kw)
    return plate(sid, 's3_festival', params, 0.0, d, fps=24)


def _lantern_bokeh(img, t, seed=7, n=14, r=(70, 180)):
    """foreground lantern bokeh: big halftone discs, pulsing on beats"""
    import math
    rng = np.random.default_rng(seed)
    pulse = 1.0 + 0.25 * math.exp(-(((t - 0.682) / BEAT) % 1.0) * 4)
    for _ in range(n):
        x, y, rr = rng.uniform(-100, 2020), rng.uniform(-60, 420), rng.uniform(*r)
        kit.halo(img, x, y, rr * pulse, '#D9402B' if rng.random() < 0.6 else '#F08A3C', 0.55, period=14.0)
    return img


def _fg_crowd(img, t, speed=2.0, n=5, seed=3, y=1080, h=520):
    """foreground dot people crossing the lens (big, dark, blurred silhouettes)"""
    import cv2
    rng = np.random.default_rng(seed)
    m = np.zeros((1080, 1920), np.float32)
    for j in range(n):
        x0 = rng.uniform(0, 2400)
        x = (x0 + speed * 400 * t * (1 if j % 2 else -1)) % 2600 - 340
        cv2.ellipse(m, (int(x), int(y - h * 0.62)), (int(h * 0.16), int(h * 0.18)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cv2.ellipse(m, (int(x), int(y)), (int(h * 0.3), int(h * 0.45)), 0, 180, 360, 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 6)
    return img + (np.array([0.08, 0.06, 0.09], np.float32)[None, None] - img) * (m * 0.92)[..., None]


def chorus3_02(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [1.6, 1.5, 6.0], 'look': [-0.6, 1.9, 30.0], 'fov': 42},
            {'t': d, 'pos': [2.3, 1.5, 7.2], 'look': [-0.9, 1.9, 30.0], 'fov': 40, 'ease': 'linear'}]
    pl = once('c302', lambda: _fest_plate('B-chorus3-02', path, crowdLane=1.2))
    img = cv2.GaussianBlur(pl.frame(local), (0, 0), 2.2)
    img = _lantern_bokeh(img, t, 7)
    cl = once('c302_char', lambda: chars.CharLayer('B-chorus3-02'))
    if cl.ok:
        push = 1.0 + 0.06 * clamp(local / d)
        rgb, a = cl.frame(local, x=860, y=1080, cx=0.5, cy=0.68, height=1180 * push)
        # lantern light pulsing on her lit side, a firework flash on 116.98
        ph = ((t - 0.682) / BEAT) % 1.0
        side = np.clip((860 - kit._XS) / 200.0, 0, 1) * a * _dots_k(0.35 + 0.3 * math.exp(-ph * 4), 8.0)
        rgb = rgb + (H('#F08A3C')[None, None] - rgb) * (side * 0.5)[..., None]
        if 116.98 <= t < 117.3:
            fk = 1 - (t - 116.98) / 0.32
            rgb = rgb + (H('#7FC8B8')[None, None] - rgb) * (a * _dots_k(0.6 * fk, 8.0) * 0.6)[..., None]
        img = chars.over(img, rgb, a, shadow='#141A33')
    img = _fg_crowd(img, local, 2.0, 4, 31)
    ly1 = once('c302_ly1', lambda: VLyric(39, x=1720, accent='#D9402B', hide=lambda i, tt: i in (2, 3)))
    ly2 = once('c302_ly2', lambda: VLyric(39, x=1720, accent='#D9402B', color='#7FC8B8', zh=False, hide=lambda i, tt: i not in (2, 3)))
    return ly2.draw(ly1.draw(img, t), t)


R['B-chorus3-02'] = chorus3_02
tl.OWN_TYPE.add('B-chorus3-02')


def chorus3_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    d = s['end'] - s['start']
    # locked on him; on 119.20 a 90-degree stepped orbit (6 frames) around him
    def cam(tt):
        k = clamp((tt + s['start'] - 119.20) / (6 / 24))
        ang = math.radians(90 * k * k * (3 - 2 * k))
        cx, cz = 0.0, 22.0
        return [cx + 3.2 * math.sin(ang), 1.6, cz - 3.2 * math.cos(ang)], [cx, 1.5, cz]
    path = []
    for i in range(int(round(d * 24)) + 1):
        p, l = cam(i / 24)
        path.append({'t': i / 24, 'pos': p, 'look': l, 'fov': 46, 'ease': 'linear'})
    pl = once('c303', lambda: _fest_plate('B-chorus3-03', path, crowd=1200))
    img = cv2.GaussianBlur(pl.frame(local), (0, 0), 1.2)
    cl = once('c303_char', lambda: chars.CharLayer('B-chorus3-03'))
    if cl.ok:
        rgb, a = cl.frame(local, x=960, y=1080, cx=0.5, cy=0.7, height=1150)
        img = chars.over(img, rgb, a, shadow='#141A33')
    # near crowd layer (4x, motion-blurred) flowing past in front of him
    img = _fg_crowd(img, local, 4.0, 6, 7, h=620)
    # uchiwa fans flip to show the glyphs as they pass him, on their mora; the column at right gathers them
    gt = _map_gt(40)
    word = 'ヒートウェイブに迷うのさ'
    for i, ch in enumerate(word):
        tg = gt[min(i, len(gt) - 1)]
        dt = t - tg
        if dt < -0.3 or dt > 0.5:
            continue
        x = 300 + (i * 137) % 1300 + 900 * dt
        y = 640 + 60 * math.sin(i * 1.7)
        flip = math.cos(math.pi * clamp((dt + 0.1) / 0.2))
        m = np.zeros((1080, 1920), np.float32)
        cv2.ellipse(m, (int(x), int(y)), (max(2, int(70 * abs(flip))), 70), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cv2.line(m, (int(x), int(y + 70)), (int(x), int(y + 150)), 1.0, 8, cv2.LINE_AA)
        fan_col = '#EDE3CF' if flip < 0 else '#D9402B'
        img = img + (H(fan_col)[None, None] - img) * m[..., None]
        if flip < -0.2:
            kit.map_glyph(img, ch, x, y, 74, 0.0, 1.0, sx=-flip, fill='#D9402B', stroke='#1A1416', sw=4.0)
    ly = once('c303_ly', lambda: VLyric(40, x=1720, accent='#D9402B'))
    return ly.draw(img, t)


R['B-chorus3-03'] = chorus3_03
tl.OWN_TYPE.add('B-chorus3-03')


def chorus3_07(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    d = s['end'] - s['start']
    v = 3.0
    # backward tracking: she runs at the lens, the camera retreats at her speed (the street recedes)
    path = [{'t': 0.0, 'pos': [0.0, 1.3, 30.0], 'look': [0.0, 1.7, 0.0], 'fov': 50},
            {'t': d, 'pos': [0.0, 1.3, 30.0 + v * d], 'look': [0.0, 1.7, v * d], 'fov': 50, 'ease': 'linear'}]
    pl = once('c307', lambda: _fest_plate('B-chorus3-07', path, crowdLane=1.6, wireSpacing=5))
    img = pl.frame(local).copy()
    # L44 on the right-hand lantern row: each glyph's lantern lights as it enters past the lens, then recedes lit
    gt = _map_gt(44)
    word = 'ヒートウェイブに迷うのさ'
    holder = once(('c307_holder',), lambda: {})
    for i, ch in enumerate(word):
        tg = gt[min(i, len(gt) - 1)]
        if t < tg:
            continue
        if i not in holder:
            row = pl.anchor(tg - s['start'], 'rowR') or []
            cand = [(j, p) for j, p in enumerate(row) if 0 < p[2] < 1.0 and 960 < p[0] < 1900 and -100 < p[1] < 900
                    and j not in holder.values()]
            if not cand:
                continue
            holder[i] = max(cand, key=lambda jp: jp[1][0])[0]          # the nearest one just in view
        j = holder[i]
        row = pl.anchor(local, 'rowR') or []
        top = pl.anchor(local, 'rowRTop') or []
        if j >= len(row) or not (0 < row[j][2] < 1.0):
            continue
        x, y = row[j][0], row[j][1]
        px = abs(top[j][1] - y) if j < len(top) else 40.0           # pixels per 0.4 m at the lantern
        r = px * 1.3                                                 # big paper lanterns carry the glyphs
        if r < 6 or x > 2000:
            continue
        lit = clamp((t - tg) / (3 / 24))
        kit.halo(img, x, y, r * 2.4, '#F08A3C', 0.75 * lit, period=max(7.0, min(16.0, r / 6)))
        m = np.zeros((1080, 1920), np.float32)
        cv2.ellipse(m, (int(x), int(y)), (int(r), int(r * 1.25)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        img = img + (H('#F5C842')[None, None] * (0.75 + 0.25 * lit) - img) * (m * lit)[..., None]
        kit.map_glyph(img, ch, x, y, int(max(14, r * 1.3)), 0.0, 1.0, '#1A1416', '#F5C842', max(1.0, r * 0.06), alpha=lit)
    cl = once('c307_char', lambda: chars.CharLayer('B-chorus3-07'))
    punch = 1.02 if 131.05 <= t < 131.05 + 2 / 24 else 1.0
    if cl.ok:
        rgb, a = cl.frame(local, x=960, y=1080, cx=0.5, cy=0.98, height=700 * punch)
        img = chars.over(img, rgb, a, shadow='#141A33')
    if t >= 131.79:                                           # lantern burst
        k = clamp((t - 131.79) / 0.4)
        img = kit.dot_flash(img, 0.5 * (1 - k), '#F08A3C', 26)
    img = _lantern_bokeh(img, t * 2.0, 11, 8, (90, 200))
    return _zh_fixed(img, t, 44, 129.55, ink='#EDE3CF', halo_col='#141A33')


R['B-chorus3-07'] = chorus3_07
tl.OWN_TYPE.add('B-chorus3-07')


# ---- B-chorus3-04: kingyo-sukui -- the goldfish flock into 幸せ; the paper poi tears and they scatter ------------------
def _fish_targets():
    import cv2
    from mv import text
    gl, _ = text.layout_h('幸せ', 820, 520, 520, 'mincho', tracking=0.05, align='center')
    f, _ = text.render_glyphs(gl)
    pts, order = _dot_targets(f, 22, 0.5, 4)
    return pts[order]                                  # every grid cell of the glyphs gets a fish


def chorus3_04(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    img = np.empty((1080, 1920, 3), np.float32)
    img[:] = H('#2C4C9A')
    caus = np.abs(np.sin(kit._XS / 37.0 + np.sin(kit._YS / 29.0 + t) * 1.5 + t * 0.9) +
                  np.sin(kit._YS / 41.0 + np.sin(kit._XS / 33.0 - t * 0.8) * 1.7 - t * 0.7)) * 0.5
    line = (caus < 0.12).astype(np.float32) * (np.sin(kit._YS / 3.0) > 0)
    img = img + (H('#7FC8B8')[None, None] - img) * (line * 0.8)[..., None]
    # her face reflected in the water (still), ripple-distorted
    cl = once('c304_char', lambda: chars.CharLayer('B-chorus3-02', rim=False))
    if cl.ok:
        rgb, a = cl.frame(0.0, x=1280, y=760, cx=0.5, cy=0.35, height=1700)
        rx = (kit._XS + 8 * np.sin(kit._YS / 23.0 + t * 3)).astype(np.float32)
        ry = (kit._YS + 6 * np.sin(kit._XS / 31.0 - t * 2.5)).astype(np.float32)
        rgb = cv2.remap(rgb, rx, ry, cv2.INTER_LINEAR)
        a = cv2.remap(a, rx, ry, cv2.INTER_LINEAR) * 0.22
        img = img + (rgb * 0.6 + H('#C9D3DC')[None, None] * 0.4 - img) * a[..., None]
    # 80 goldfish: wander, lock into 幸せ on 121.42, scatter after the tear on 122.91
    tg = once('fish_tg', _fish_targets)
    n = len(tg)
    rng = np.random.default_rng(41)
    home = np.stack([rng.uniform(200, 1700, n), rng.uniform(150, 950, n)], 1)
    ph = rng.uniform(0, 6.28, n)
    wander = home + np.stack([90 * np.sin(t * 0.9 + ph), 70 * np.cos(t * 1.1 + ph * 1.3)], 1)
    lock = _ease_io(clamp((t - 120.68) / (121.42 - 120.68)))
    pos = wander * (1 - lock) + tg * lock
    if t >= 122.91:
        k = clamp((t - 122.91) / 0.7)
        dirs = np.stack([np.cos(ph * 3), np.sin(ph * 3)], 1)
        pos = tg + dirs * (500 * (1 - (1 - k) ** 2)) + np.stack([40 * np.sin(t * 2 + ph), 0 * ph], 1)
    heading = np.arctan2(np.cos(t * 1.1 + ph * 1.3), np.sin(t * 0.9 + ph)) * (1 - lock) + lock * 0.0
    if t >= 122.91:
        heading = ph * 3
    fm = np.zeros((1080, 1920), np.float32)
    tm = np.zeros((1080, 1920), np.float32)
    for (x, y), hd, p in zip(pos, heading, ph):
        c, s_ = math.cos(hd), math.sin(hd)
        cv2.ellipse(fm, (int(x), int(y)), (16, 9), math.degrees(hd), 0, 360, 1.0, -1, cv2.LINE_AA)
        wag = 0.5 * math.sin(t * 14 + p)
        tx, ty = x - c * 16, y - s_ * 16
        pts = np.array([[tx, ty], [tx - math.cos(hd + 0.6 + wag) * 15, ty - math.sin(hd + 0.6 + wag) * 15],
                        [tx - math.cos(hd - 0.6 + wag) * 15, ty - math.sin(hd - 0.6 + wag) * 15]], np.int32)
        cv2.fillConvexPoly(tm, pts, 1.0, cv2.LINE_AA)
    img = img + (H('#D9402B')[None, None] - img) * np.clip(fm + tm * 0.85, 0, 1)[..., None]
    img = img + (H('#F08A3C')[None, None] - img) * (fm * _dots_k(0.35, 6.0))[..., None]
    # the paper poi dips in on 122.17 and tears on 122.91
    if t >= 122.0:
        k = clamp((t - 122.0) / 0.3)
        px, py = 960 + 600 * (1 - k), 520 + 300 * (1 - k)
        m = np.zeros((1080, 1920), np.float32)
        cv2.circle(m, (int(px), int(py)), 230, 1.0, 18, cv2.LINE_AA)
        cv2.line(m, (int(px + 160), int(py + 160)), (int(px + 520), int(py + 520)), 1.0, 26, cv2.LINE_AA)
        img = img + (H('#D9402B')[None, None] - img) * m[..., None]
        tissue = np.zeros((1080, 1920), np.float32)
        cv2.circle(tissue, (int(px), int(py)), 220, 1.0, -1, cv2.LINE_AA)
        if t >= 122.91:
            tk = clamp((t - 122.91) / 0.3)
            tear = np.zeros((1080, 1920), np.float32)
            pts = np.array([[px - 30, py - 220], [px + 20, py - 80], [px - 40, py + 10], [px + 30, py + 120], [px - 10, py + 220]], np.int32)
            cv2.polylines(tear, [pts], False, 1.0, int(4 + 120 * tk), cv2.LINE_AA)
            tissue = tissue * (1 - tear)
        img = img + (H('#F6F2E7')[None, None] - img) * (tissue * 0.42)[..., None]
    # ripples on the surface in halftone
    if t >= 122.17:                                      # ripples only where the poi breaks the surface
        k = clamp((t - 122.17) / 1.2)
        dd = np.sqrt((kit._XS - 960) ** 2 + (kit._YS - 520) ** 2)
        rr = np.sin(dd / 18.0 - t * 6.0) * np.clip(1 - dd / (200 + 900 * k), 0, 1)
        img = img + (H('#C9D3DC')[None, None] - img) * ((rr > 0.9) * 0.3)[..., None]
    # 2% slow rotation, 3% punch-in on 122.91
    rot = 2.0 * clamp(local / (s['end'] - s['start']))
    pk = 1.03 if t >= 122.91 else 1.0
    img = cv2.warpAffine(img, cv2.getRotationMatrix2D((960, 540), rot, pk), (1920, 1080), borderMode=cv2.BORDER_REFLECT)
    ly = once('c304_ly', lambda: VLyric(41, x=1740, accent='#D9402B', hide=lambda i, tt: i in (2, 3)))
    return ly.draw(img, t)


R['B-chorus3-04'] = chorus3_04
tl.OWN_TYPE.add('B-chorus3-04')


# ---- B-chorus3-06: a starmine writes 0:00 in the sky, one character per beat; the two of them look up side by side ------
def chorus3_06(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import fireworks as fw
    from .print_fx import hexc as H
    push = 1.0 + 0.04 * clamp(local / (s['end'] - s['start']))
    img = np.empty((1080, 1920, 3), np.float32)
    g = (kit._YS / 1080)[..., None]
    img[:] = H('#141A33') * (1 - g) + H('#1E2550') * g
    # lantern wires along the bottom of the sky
    for k in range(3):
        pts = [(x, int(560 + k * 40 + 60 * (1 - ((x - 960) / 1100) ** 2))) for x in range(-50, 1980, 40)]
        for a, b in zip(pts, pts[1:]):
            cv2.line(img, a, b, tuple(float(v) for v in H('#1A1416')), 2, cv2.LINE_AA)
        for j, (x, y) in enumerate(pts[1::4]):
            kit.halo(img, x, y + 22, 26, '#D9402B', 0.8, period=7.0)
    # the starmine: '0' ':' '0' '0' in mint dot sparks, one per beat
    chars_ = [('0', 126.61, 520), (':', 127.35, 800), ('0', 128.09, 1040), ('0', 128.83, 1340)]
    flash = 0.0
    for ch, t0, x in chars_:
        img = fw.glyph_burst(img, t, t0 - 0.35, x, 270, 380, ch, '#7FC8B8', hold=2.5, life=2.4, grid=14)
        if t0 <= t < t0 + 0.35:
            flash = max(flash, 1 - (t - t0) / 0.35)
    # the two of them, side by side, faces up (two-person still, separate figures), lit by the bursts
    from . import chars
    raw = once(('raw', 'B-chorus3-06'), lambda: chars.raw_matte('B-chorus3-06'))
    if raw is not None:
        rgb, a, parts = raw
        k_ = 900 / rgb.shape[0]
        M = np.float32([[k_ * push, 0, 960 - rgb.shape[1] * k_ * push / 2], [0, k_ * push, 1080 + 60 - rgb.shape[0] * k_ * push]])
        lr = cv2.warpAffine(rgb, M, (1920, 1080))
        la = cv2.warpAffine(a, M, (1920, 1080))
        from .halftone import PrintStyle
        sty = once('c306_sty', lambda: PrintStyle(['#141A33', '#1E2550', '#D9402B', '#F08A3C', '#EDE3CF', '#7FC8B8', '#1A1416'],
                                                  period=8, grain=0.0, dead=0.06))
        key = ('c306_print', round(push, 3))
        if key not in _cache:
            for kk in [kk for kk in _cache if isinstance(kk, tuple) and kk[0] == 'c306_print']:
                del _cache[kk]
            _cache[key] = sty(lr)
        pr = _cache[key]
        pr = pr + (H('#7FC8B8')[None, None] - pr) * (la * _dots_k(0.25 + 0.5 * flash, 8.0) * 0.6)[..., None]
        pr, la2 = chars.sticker(pr, la)
        img = chars.over(img, pr, la2)
    ly1 = once('c306_ly1', lambda: VLyric(43, x=1740, accent='#D9402B', hide=lambda i, tt: i in (2, 3)))
    ly2 = once('c306_ly2', lambda: VLyric(43, x=1740, accent='#D9402B', color='#7FC8B8', zh=False, hide=lambda i, tt: i not in (2, 3)))
    return ly2.draw(ly1.draw(img, t), t)


R['B-chorus3-06'] = chorus3_06
tl.OWN_TYPE.add('B-chorus3-06')


# ---- B-bridge2-02: 走馬灯 -- the dream train moves one window per frame so it looks frozen; she moves window by window --
def bridge2_02(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars, print_fx
    from .print_fx import hexc as H
    pitch = 180
    lock_break = 140.68
    f_idx = int(round(local * 24))
    img = np.empty((1080, 1920, 3), np.float32)
    g = (kit._YS / 1080)[..., None]
    img[:] = H('#EDE3CF') * (1 - g * 0.3) + H('#2C4C9A') * (g * 0.3)
    img = img + (H('#2C4C9A')[None, None] - img) * (_dots_k(0.18, 10.0) * (kit._YS < 300))[..., None]
    # train offset: whole window pitches per frame (frozen look), then slows and smears after the break
    if t < lock_break:
        off, blur = 0.0, 0.0
    else:
        k = t - lock_break
        v = pitch * 24 * math.exp(-k * 2.2)               # px/s, decaying
        off = (pitch * 24 * (1 - math.exp(-k * 2.2)) / 2.2) % pitch
        blur = v / 24 * 0.5
    car_top, car_bot = 300, 820
    body = np.zeros((1080, 1920), np.float32)
    body[car_top:car_bot] = 1
    img = img + (H('#EDE3CF')[None, None] * 0.96 - img) * body[..., None]
    band = np.zeros((1080, 1920), np.float32)
    band[car_bot - 90:car_bot - 50] = 1
    img = img + (H('#F08A3C')[None, None] - img) * band[..., None]
    # windows: window n shows clip frame n (the walking-lantern effect)
    cl = once('b202_char', lambda: chars.CharLayer('B-bridge2-02'))
    gt = _map_gt(47)
    word = '満たされた笑み浮かべて'
    for j in range(-1, 12):
        x0 = int(j * pitch - off + 30)
        if x0 > 1920 or x0 + 140 < 0:
            continue
        win = np.empty((300, 140, 3), np.float32)
        win[:] = H('#2C4C9A')
        if cl.ok:
            n = (j + f_idx) if t >= lock_break else j
            rgb, a = cl.frame((n % 24) / 24.0 * 3.0, x=960, y=540, cx=0.5, cy=0.42, height=1300)
            rgb = cv2.resize(rgb[90:990, 750:1170], (140, 300))
            a = cv2.resize(a[90:990, 750:1170], (140, 300))
            win = win + (rgb - win) * a[..., None]
        win = win * 0.8 + H('#F08A3C')[None, None] * 0.2
        xa, xb = max(0, x0), min(1920, x0 + 140)
        img[380:680, xa:xb] = win[:, xa - x0:xb - x0]
        # window plate with a glyph (like a car number), lighting orange on its mora
        gi = j - 0
        if 0 <= gi < len(word):
            on = t >= gt[min(gi, len(gt) - 1)]
            kit.map_glyph(img, word[gi], x0 + 70, 345, 48, 0.0, 1.0, '#F08A3C' if on else '#C9D3DC', '#292924', 3.0)
    if blur > 0.5:
        img = kit.dir_blur(img, blur)
    # wheels: frozen spokes (wagon-wheel)
    for j in range(-1, 12):
        x0 = j * pitch * 2 - off * 2 % (pitch * 2) + 90
        m = np.zeros((1080, 1920), np.float32)
        cv2.circle(m, (int(x0), car_bot + 40), 56, 1.0, 6, cv2.LINE_AA)
        for k in range(6):
            a_ = k * math.pi / 3
            cv2.line(m, (int(x0), car_bot + 40), (int(x0 + math.cos(a_) * 52), int(car_bot + 40 + math.sin(a_) * 52)), 1.0, 4, cv2.LINE_AA)
        img = img + (H('#292924')[None, None] - img) * m[..., None]
    # platform edge and lamps in the foreground
    plat = (kit._YS > 930).astype(np.float32)
    img = img + (H('#2C4C9A')[None, None] - img) * (plat * 0.85)[..., None]
    if 139.20 <= t < 139.45:                              # window light pulse
        kk = 1 - (t - 139.20) / 0.25
        img[380:680] = img[380:680] + (H('#F5C842')[None, None] - img[380:680]) * (0.35 * kk)
    img = print_fx.two_ink(img, mis=(2.0, -1.0))
    return _zh_fixed(img, t, 47, 138.55, ink='#292924', halo_col='#EDE3CF')


R['B-bridge2-02'] = bridge2_02
tl.OWN_TYPE.add('B-bridge2-02')


# ---- B-bridge2-03: he stands on the platform; the train's window light strobes across him; he is printed under-inked ---
def bridge2_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars, print_fx
    from .print_fx import hexc as H
    img = np.empty((1080, 1920, 3), np.float32)
    g = (kit._YS / 1080)[..., None]
    img[:] = H('#EDE3CF') * (1 - g * 0.25) + H('#2C4C9A') * (g * 0.25)
    # passing windows behind him (blurred orange rectangles moving right -> left)
    off = (local * 1400) % 260
    win = np.zeros((1080, 1920), np.float32)
    for j in range(-1, 9):
        x0 = int(1920 - (j * 260 + off))
        cv2.rectangle(win, (x0, 300), (x0 + 170, 600), 1.0, -1)
    win = cv2.blur(win, (61, 1))
    img = img + (H('#F08A3C')[None, None] - img) * (win * 0.85)[..., None]
    body = np.zeros((1080, 1920), np.float32)
    body[250:680] = 1
    img = img + (H('#2C4C9A')[None, None] - img) * (body * (1 - win) * 0.25)[..., None]
    # platform + lamp posts
    plat = (kit._YS > 900).astype(np.float32)
    img = img + (H('#2C4C9A')[None, None] - img) * (plat * 0.75)[..., None]
    for x in (260, 1700):
        m = np.zeros((1080, 1920), np.float32)
        cv2.line(m, (x, 900), (x, 160), 1.0, 10, cv2.LINE_AA)
        img = img + (H('#292924')[None, None] - img) * m[..., None]
    # strobe on 16ths
    strobe = (int((t - 0.682) / (BEAT / 4)) % 2 == 0)
    # him, under-inked (his plate starved of ink): pale tint, 60% coverage
    push = 1.0 + 0.03 * clamp(local / (s['end'] - s['start']))
    cl = once('b203_char', lambda: chars.CharLayer('B-bridge2-03', max_cov=0.6))
    if cl.ok:
        rgb, a = cl.frame(local, x=920, y=1080, cx=0.5, cy=0.82, height=1200 * push)
        if strobe:
            band = np.clip(1 - np.abs(kit._XS - (1920 - off * 6) % 1920) / 160.0, 0, 1) * a
            rgb = rgb + (H('#F08A3C')[None, None] - rgb) * (band * _dots_k(0.6, 8.0) * 0.7)[..., None]
        img = chars.over(img, rgb, a)
    img = print_fx.two_ink(img, mis=(2.0, -1.0))
    # L48 under-inked; 無力 so faint it reads only when a window light passes behind it
    gt = _map_gt(48)
    word = '思い知る自分の無力'
    for i, ch in enumerate(word):
        if t < gt[min(i, len(gt) - 1)]:
            continue
        x, y = 1740, 150 + i * 96
        faint = 0.5
        if ch in '無力':
            behind = float(win[int(min(1079, y)), int(min(1919, x))])
            faint = 0.12 + 0.6 * behind
        kit.map_glyph(img, ch, x, y, 84, 0.0, 1.0, '#EDE3CF', '#2C4C9A', 3.0, alpha=faint)
    return _zh_fixed(img, t, 48, 141.43, ink='#292924', halo_col='#EDE3CF')


R['B-bridge2-03'] = bridge2_03
tl.OWN_TYPE.add('B-bridge2-03')


# ---- B-bridge2-04: she opens her eyes; the halftone shade on her face peels off like a sheet; no shadow left ------------
def bridge2_04(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .halftone import PrintStyle
    from .print_fx import hexc as H
    img = np.empty((1080, 1920, 3), np.float32)
    img[:] = H('#EDE3CF')
    ang = np.arctan2(kit._YS + 300, kit._XS - 960)
    rays = (np.sin(ang * 22) > 0.2).astype(np.float32) * np.clip(1 - kit._YS / 1080, 0, 1)
    img = img + (H('#2C4C9A')[None, None] - img) * (rays * _dots_k(0.25, 10.0) * 0.6)[..., None]
    bloom = clamp((t - 146.61) / 0.6)
    if bloom > 0:
        kit.halo(img, 960, 380, 620 * bloom, '#F5C842', 0.55 * bloom, period=12.0)
    push = 1.0 + 0.04 * clamp(local / (s['end'] - s['start']))
    cl = once('b204_flat', lambda: chars.CharLayer('B-bridge2-04', shade=0.0, dot_gain=0.0))
    cs = once('b204_shade', lambda: chars.CharLayer('B-bridge2-04'))
    peel = clamp((t - 145.13) / (146.61 - 145.13))
    if cl.ok:
        flat, a = cl.frame(local, x=960, y=1080, cx=0.5, cy=0.62, height=1500 * push)
        shaded, _ = cs.frame(local, x=960, y=1080, cx=0.5, cy=0.62, height=1500 * push)
        shade = np.clip(flat - shaded, 0, 1).max(-1)                     # where the halftone shade sits
        img = chars.over(img, flat, a)
        if peel < 1:
            e = peel * peel * (3 - 2 * peel)
            src = np.float32([[0, 0], [1920, 0], [1920, 1080], [0, 1080]])
            dst = np.float32([[0 + 1500 * e, -900 * e], [1920 + 900 * e, -1200 * e], [1920 + 600 * e, 1080 - 1500 * e],
                              [0 + 1300 * e, 1080 - 700 * e]])
            Hm = cv2.getPerspectiveTransform(src, dst)
            sh_w = cv2.warpPerspective(shade, Hm, (1920, 1080))
            sheet = cv2.warpPerspective(np.ones((1080, 1920), np.float32), Hm, (1920, 1080))
            shadow = cv2.GaussianBlur(np.roll(np.roll(sheet, 30, 0), 20, 1), (0, 0), 20) * 0.18 * (1 - e)
            img = img * (1 - shadow[..., None])
            img = img + (H('#2C4C9A')[None, None] * 0.6 + H('#292924')[None, None] * 0.4 - img) * (sh_w * 0.85)[..., None]
    # L49: glyphs carry a halftone shadow that peels off with her shade sheet
    ly = once('b204_ly', lambda: VLyric(49, x=1740, accent='#2C4C9A', color='#EDE3CF'))
    if peel >= 1:
        ly.accent = '#EDE3CF'
    return ly.draw(img, t)


R['B-bridge2-04'] = bridge2_04
tl.OWN_TYPE.add('B-bridge2-04')


# ---- B-chorus4-03: blue hour -- he walks the seawall toward the lighthouse, its last sweeps -----------------------------
def _c403_plate():
    s = tl.BY_ID['B-chorus4-03']
    d = s['end'] - s['start']
    v = 1.3
    path = [{'t': 0.0, 'pos': [3.0, 1.2, 30.0], 'look': [-3.5, 1.8, 46.0], 'fov': 46},
            {'t': d, 'pos': [3.0, 1.2, 30.0 + v * d], 'look': [-3.5, 1.8, 46.0 + v * d], 'fov': 46, 'ease': 'linear'}]
    return plate('B-chorus4-03', 's2_coast', {'world': 'dawn', 'path': path, 'wallH': 0.5, 'poleSpacing': 16.3, 'mirrors': [],
                                             'vending': [], 'length': 260, 'fogNear': 40, 'fogFar': 520}, 0.0, d, fps=24)


def chorus4_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars
    from .print_fx import hexc as H
    pl = once('c403', _c403_plate)
    img = pl.frame(local).copy()
    # beam sweep across the frame on 154.02 (one pass per bar)
    k = (t - 154.02) / 0.5
    if -0.6 < k < 0.6:
        ang = np.arctan2(kit._XS - (300 + 1300 * (k + 0.5)), -(kit._YS + 700))
        fan = np.clip(1 - np.abs(ang) / 0.18, 0, 1)
        img = img + (H('#F7E3C2')[None, None] - img) * (fan * _dots_k(0.55, 12.0) * 0.6)[..., None]
    cl = once('c403_char', lambda: chars.CharLayer('B-chorus4-03'))
    if cl.ok:
        gust = 4.0 * math.exp(-max(0.0, t - 154.76) * 3) if t >= 154.76 else 0.0
        rgb, a = cl.frame(local, x=1050, y=1060, cx=0.5, cy=0.98, height=650)
        if gust:
            sw = (gust * np.sin(kit._YS / 20.0 + t * 20) * (kit._YS < 700)).astype(np.float32)
            rgb = cv2.remap(rgb, (kit._XS + sw).astype(np.float32), kit._YS, cv2.INTER_LINEAR)
            a = cv2.remap(a, (kit._XS + sw).astype(np.float32), kit._YS, cv2.INTER_LINEAR)
        img = chars.over(img, rgb, a, shadow='#1E2550')
    # railing posts in the foreground at 2x parallax
    off = (local * 1.3 * 2 * 180) % 360
    m = np.zeros((1080, 1920), np.float32)
    for x0 in np.arange(-360 + off, 2280, 360):
        cv2.rectangle(m, (int(x0), 760), (int(x0) + 36, 1080), 1.0, -1)
    cv2.rectangle(m, (0, 760), (1920, 790), 1.0, -1)
    img = img + (H('#1E2550')[None, None] - img) * (m * 0.95)[..., None]
    ly = once('c403_ly', lambda: VLyric(52, x=200, accent='#2C4C9A'))
    out = ly.draw(img, t)
    # the column wavers in the mist ripple
    wav = (3.0 * np.sin(kit._YS / 17.0 + t * 4)).astype(np.float32)
    region = (kit._XS < 360)[..., None]
    out = np.where(region, cv2.remap(out, (kit._XS + wav).astype(np.float32), kit._YS, cv2.INTER_LINEAR), out)
    return out


R['B-chorus4-03'] = chorus4_03
tl.OWN_TYPE.add('B-chorus4-03')


# ---- B-chorus4-04: the vending machine at dawn -- 7, 7, 7 ... 6, はずれ; his reflection slides across the glass ------------
def chorus4_04(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars, print_fx
    from .print_fx import hexc as H
    push = 1.0 + 0.02 * clamp(local / (s['end'] - s['start']))
    img = np.empty((1080, 1920, 3), np.float32)
    g = (kit._YS / 1080)[..., None]
    img[:] = H('#2C4C9A') * (1 - g) + H('#1E2550') * g
    img = img + (H('#C9D3DC')[None, None] - img) * ((np.abs(kit._YS - 420) < 3) * 0.6)[..., None]
    stops = [156.98, 157.72, 158.46, 158.83]
    face = vending_face(t, '君に幸せあげられない', 156.10, '7776', stops, seed=8)
    if t >= 158.83:                                          # はずれ blinking in red dots
        if int((t - 158.83) * 8) % 2 == 0:
            b, _ = print_fx.led_board('はずれ', cols=48, rows=16, dot=10, on='#D9402B', off='#2A1414', bg='#0B1414')
            b = cv2.resize(b, (560, 150), interpolation=cv2.INTER_AREA)
            face[900:1050, 80:640] = b
    fh, fw_ = face.shape[:2]
    sc = 0.78 * push
    fr = cv2.resize(face, (int(fw_ * sc), int(fh * sc)), interpolation=cv2.INTER_AREA)
    x0, y0 = 960 - fr.shape[1] // 2, 1080 - fr.shape[0] + 60
    ya, yb = max(0, y0), min(1080, y0 + fr.shape[0])
    img[ya:yb, x0:x0 + fr.shape[1]] = fr[ya - y0:yb - y0]
    kit.halo(img, 960, 600, 700, '#7FC8B8', 0.25, period=10.0)
    # his reflection sliding right -> left across the glass (30%)
    cl = once('c404_char', lambda: chars.CharLayer('B-chorus4-03', rim=False))
    if cl.ok:
        u = clamp(local / (s['end'] - s['start']))
        rgb, a = cl.frame(0.0, x=1300 - 700 * u, y=900, cx=0.5, cy=0.98, height=820)
        glass = np.zeros((1080, 1920), np.float32)
        glass[max(0, y0 + int(40 * sc)):y0 + int(700 * sc), x0 + int(40 * sc):x0 + int(680 * sc)] = 1
        img = img + (rgb * 0.6 + H('#C9D3DC')[None, None] * 0.4 - img) * (a * glass * 0.3)[..., None]
    # moths leaving in the dawn
    rng = np.random.default_rng(53)
    for j in range(5):
        x = 960 + rng.uniform(-200, 200) + 220 * local * (1 if j % 2 else -1)
        y = 300 - 120 * local + rng.uniform(-60, 60)
        m = np.zeros((1080, 1920), np.float32)
        flap = (int(t * 12) + j) % 2
        cv2.ellipse(m, (int(x - 5), int(y)), (7, 3 if flap else 6), 30 if flap else 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        cv2.ellipse(m, (int(x + 5), int(y)), (7, 3 if flap else 6), -30 if flap else 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        img = img + (H('#EDE3CF')[None, None] - img) * (m * 0.8)[..., None]
    if 158.83 <= t < 158.83 + 2 / 24:                       # 2-frame shake on the miss
        img = np.roll(img, (8, -10), (0, 1))
    ly = once('c404_ly', lambda: VLyric(53, x=1740, accent='#2C4C9A'))
    return ly.draw(img, t)


R['B-chorus4-04'] = chorus4_04
tl.OWN_TYPE.add('B-chorus4-04')


# ---- B-outro-01: the third burst -- the headlight becomes the rising sun; the dawn prints over the night; he turns -------
def _o01_plate():
    s = tl.BY_ID['B-outro-01']
    d = s['end'] - s['start']
    path = [{'t': 0.0, 'pos': [0.0, 2.0, 20.0], 'look': [40.0, 30.0, 720.0], 'fov': 34},
            {'t': 1.48, 'pos': [-6.0, 3.0, 12.0], 'look': [8.0, 2.4, 60.0], 'fov': 44, 'ease': 'inout'},
            {'t': 2.59, 'pos': [-6.6, 3.0, 13.0], 'look': [8.6, 2.4, 60.0], 'fov': 44, 'ease': 'linear'},
            {'t': d, 'pos': [-6.6, 3.0, 13.0], 'look': [8.6, 40.0, 70.0], 'fov': 44, 'ease': 'in'}]
    return plate('B-outro-01', 's2_coast', {'world': 'dawnprint', 'day': True, 'path': path, 'wallH': 0.5,
                                           'poleSpacing': 16.3, 'mirrors': [], 'vending': [], 'moonPos': [40.0, 30.0, 720.0]},
                 0.0, d, fps=24)


def outro_01(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars, print_fx
    from .print_fx import hexc as H
    pl = once('o01', _o01_plate)
    img = pl.frame(local).copy()
    # dawn printing over the night: orange 162.17, yellow 162.91, silver 163.65, each wiping outward from the sun
    sx, sy = 960, 540
    night = np.empty_like(img)
    night[:] = H('#1E2550')
    d_ = np.sqrt((kit._XS - sx) ** 2 + (kit._YS - sy) ** 2)
    cover = np.ones((1080, 1920), np.float32)
    for tp in (162.17, 162.91, 163.65):
        if t >= tp:
            r = 2400 * _ease_out_c(clamp((t - tp) / 0.6))
            cover *= np.clip((d_ - r) / 30.0, 0, 1)
    img = img + (night - img) * (cover * 0.85)[..., None]
    # the relay landing: sun disc with rays + AM glare at frame centre, then it rises out of frame with the pull-back
    k = _ease_io(clamp(local / 1.48))
    cx, cy = 960 - 300 * k, 540 - 420 * k
    rr = 365 * (1 - k) + 90 * k                       # = chorus4-05's disc on its last frame
    kit.halo(img, cx, cy, rr * 2.4, '#F5C842', 0.7, period=14.0)
    m = np.zeros((1080, 1920), np.float32)
    for j in range(12):
        a = j * math.pi / 6 + t * 0.6
        pts = np.array([[cx + math.cos(a - 0.1) * rr * 1.1, cy + math.sin(a - 0.1) * rr * 1.1],
                        [cx + math.cos(a) * rr * 1.6, cy + math.sin(a) * rr * 1.6],
                        [cx + math.cos(a + 0.1) * rr * 1.1, cy + math.sin(a + 0.1) * rr * 1.1]], np.int32)
        cv2.fillConvexPoly(m, pts, 1.0, cv2.LINE_AA)
    img = img + (H('#F08A3C')[None, None] - img) * m[..., None]
    m = np.zeros((1080, 1920), np.float32)
    cv2.circle(m, (int(cx), int(cy)), int(rr), 1.0, -1, cv2.LINE_AA)
    if t < 162.17 + 5 / 24:
        img = kit.dot_flash(img, 1 - (t - 162.17) / (5 / 24), '#F5C842', 24)
    img = img + (H('#FFF2C8')[None, None] - img) * m[..., None]
    # the train passing on the coastal track behind him, its LED board scrolling L55
    if local > 1.2:
        u = (local - 1.2) / 1.9
        tx = 2200 - 2600 * u
        body = np.zeros((1080, 1920), np.float32)
        cv2.rectangle(body, (int(tx), 520), (int(tx) + 1100, 700), 1.0, -1)
        img = img + (H('#EDE3CF')[None, None] - img) * body[..., None]
        band = np.zeros((1080, 1920), np.float32)
        cv2.rectangle(band, (int(tx), 660), (int(tx) + 1100, 680), 1.0, -1)
        img = img + (H('#D9402B')[None, None] - img) * band[..., None]
        for j in range(8):
            wx = int(tx + 40 + j * 130)
            cv2.rectangle(img, (wx, 545), (wx + 90, 620), tuple(float(v) for v in H('#F5C842')), -1)
        brd, _ = print_fx.led_board("SOMETIMES, ALL I THINK ABOUT IS YOU   ", cols=80, rows=8, dot=8, on='#F08A3C',
                                    off='#2A1C14', bg='#141018', font='silk', scroll=int((t - 162.30) * 24 * 2) % 300 - 80)
        bh, bw = brd.shape[:2]
        bx = int(tx + 200)
        xa, xb = max(0, bx), min(1920, bx + bw)
        if xa < xb:
            img[492:492 + bh, xa:xb] = brd[:, xa - bx:xb - bx]
    # him on the seawall, turning to the light (mid shot), sun-yellow hairline rim, gold halftone light on his lit side
    cl = once('o01_char', lambda: chars.CharLayer('B-outro-01', rim_hair='#F5C842'))
    if cl.ok and local > 0.9:
        rgb, a = cl.frame(local, x=560, y=1080, cx=0.5, cy=0.7, height=1100)
        lit = np.clip((kit._XS - 480) / 200.0, 0, 1) * a * _dots_k(0.45, 8.0)
        rgb = rgb + (H('#F5C842')[None, None] - rgb) * (lit * 0.5)[..., None]
        img = chars.over(img, rgb, a * clamp((local - 0.9) / 0.4), shadow='#2C4C9A')
    # 'SOMETIMES' across the sky band, one letter per 16th
    if t >= 162.30:
        n = min(9, int((t - 162.30) / (BEAT / 4)) + 1)
        from mv import text
        gl, _ = text.layout_h('SOMETIMES'[:n], 1500, 160, 72, 'mincho', tracking=0.5, align='center')
        f, _ = text.render_glyphs(gl)
        if f is not None:
            img = img + (H('#D9402B')[None, None] - img) * f[..., None]
    # whip-up 164.76-165.13 (30 px vertical blur)
    if t >= 164.76:
        k = clamp((t - 164.76) / 0.37)
        img = cv2.blur(img, (1, int(1 + 60 * k)))
    return _zh_fixed(img, t, 55, 162.3, ink='#1A1416', halo_col='#EDE3CF')


def _ease_out_c(x):
    return 1 - (1 - x) ** 3


R['B-outro-01'] = outro_01
tl.OWN_TYPE.add('B-outro-01')


# ---- B-outro-03: he runs along the seawall road; six vending machines, each lights one word as he passes ---------------
def _o03_plate():
    s = tl.BY_ID['B-outro-03']
    d = s['end'] - s['start']
    v = 5.0
    beats = [168.09, 168.83, 169.57, 170.31, 170.68, 171.05]
    zs = [round(20.0 + v * (b - s['start']) + 2.6, 2) for b in beats]
    path = [{'t': 0.0, 'pos': [-1.6, 1.3, 20.0], 'look': [-6.5, 1.25, 23.4], 'fov': 46},
            {'t': d, 'pos': [-1.6, 1.3, 20.0 + v * d], 'look': [-6.5, 1.25, 23.4 + v * d], 'fov': 46, 'ease': 'linear'}]
    return plate('B-outro-03', 's2_coast', {'world': 'dawnprint', 'day': True, 'path': path, 'wallH': 0.5,
                                           'poleSpacing': 16.3, 'mirrors': [], 'vending': zs}, 0.0, d, fps=24), zs


def outro_03(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars, print_fx
    from .print_fx import hexc as H
    pl, zs = once('o03', _o03_plate)
    img = pl.frame(local).copy()
    words = [('HEAT', 168.09), ('WAVES', 168.83), ('BEEN', 169.57), ("FAKIN'", 170.31), ('ME', 170.68), ('OUT', 171.05)]
    # each machine's mint ticker: the word lights as he passes (screen-space ticker band on the machine nearest him)
    lit = [w for w, b in words if t >= b - 0.05]
    if lit:
        w = lit[-1]
        brd, _ = print_fx.led_board(w, cols=max(24, len(w) * 9 + 6), rows=10, dot=12, on='#7FC8B8', off='#16302E',
                                    bg='#0B1414', font='silk', glow=0.6)
        bh, bw = brd.shape[:2]
        x0, y0 = 960 - bw // 2 + 260, 300
        img[y0:y0 + bh, x0:x0 + bw] = brd
        kit.halo(img, 960 + 260, y0 + bh / 2, bw * 0.8, '#7FC8B8', 0.3, period=10.0)
    cl = once('o03_char', lambda: chars.CharLayer('B-outro-03'))
    if cl.ok:
        rgb, a = cl.frame(local, x=700, y=1080, cx=0.5, cy=0.98, height=700)
        img = chars.over(img, rgb, a, shadow='#2C4C9A')
    # foreground poles whipping past at 2x
    off = (local * 5.0 * 2 * 120) % 900
    m = np.zeros((1080, 1920), np.float32)
    for x0 in np.arange(1920 - off, -400, -900):
        cv2.rectangle(m, (int(x0), 0), (int(x0) + 60, 1080), 1.0, -1)
    m = cv2.blur(m, (41, 1))
    img = img + (H('#1A1416')[None, None] - img) * (m * 0.9)[..., None]
    return _zh_fixed(img, t, 57, 168.05, ink='#1A1416', halo_col='#EDE3CF')


R['B-outro-03'] = outro_03
tl.OWN_TYPE.add('B-outro-03')


# ---- B-outro-05: four curve mirrors catch the sunrise; each shows one memory of her for one beat, then sun glare --------
def _o05_plate():
    s = tl.BY_ID['B-outro-05']
    d = s['end'] - s['start']
    v = 8.0
    beats = [174.02, 174.76, 175.50, 176.24]
    zs = [round(10.0 + v * (b - s['start']) + 4.0, 2) for b in beats]
    path = [{'t': 0.0, 'pos': [-1.2, 3.0, 10.0], 'look': [-4.0, 2.95, 14.0], 'fov': 46},
            {'t': d, 'pos': [-1.2, 3.0, 10.0 + v * d], 'look': [-4.0, 2.95, 14.0 + v * d], 'fov': 46, 'ease': 'linear'}]
    return plate('B-outro-05', 's2_coast', {'world': 'dawnprint', 'day': True, 'path': path, 'wallH': 0.5,
                                           'poleSpacing': 16.3, 'mirrors': zs, 'vending': []}, 0.0, d, fps=24), zs


def outro_05(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    pl, zs = once('o05', _o05_plate)
    img = pl.frame(local).copy()
    srcs = ['B-hook-02', 'B-chorus1-01', 'B-chorus3-02', 'B-chorus3-07']
    beats = [174.02, 174.76, 175.50, 176.24]
    phrases = ['SOMETIMES,', 'ALL I THINK', 'ABOUT', 'IS YOU']
    ms = pl.anchor(local, 'mirrors') or []
    mt = pl.anchor(local, 'mirrorTop') or []
    for j, (C, T) in enumerate(zip(ms, mt)):
        if not (0 < C[2] < 1.001):
            continue
        r = abs(C[1] - T[1])
        if r < 10 or not (-r < C[0] < 1920 + r):
            continue
        b = beats[j] if j < len(beats) else 1e9
        cont = np.empty((640, 640, 3), np.float32)
        cont[:] = H('#2D6BE0')
        cl = once(('o05cl', j), lambda j=j: chars.CharLayer(srcs[j % len(srcs)]))
        if cl.ok:
            rgb, a = cl.frame((t - b) % 1.5, x=960, y=560, cx=0.5, cy=0.5, height=720)
            cont = cont + (rgb[220:860, 640:1280] - cont) * a[220:860, 640:1280][..., None]
        # one beat of memory, then sun-glare whiteout in AM halftone (never plain white)
        g = clamp((t - (b + BEAT * 0.6)) / (BEAT * 0.4)) if t >= b else 0.0
        cont = cont + (H('#F6F2E7')[None, None] - cont) * (_dots_k(g, 10.0)[:640, :640, None] * 0.95)
        X = (C[0] + r, C[1], C[2])
        Y = (C[0], C[1] - r, C[2])
        img, m = mirror_insert(img, cont, C, X, Y, sat=1.0, k=0.4)
        if t >= b - 0.05 and j < len(phrases):
            gl, _ = text.layout_h(phrases[j], C[0], C[1] + r + 80, 64, 'mincho', tracking=0.45, align='center')
            f, _ = text.render_glyphs(gl)
            if f is not None:
                img = img + (H('#2C4C9A')[None, None] - img) * np.roll(np.roll(f, 5, 0), 5, 1)[..., None]
                img = img + (H('#EDE3CF')[None, None] - img) * f[..., None]
        if g > 0.5:
            kit.halo(img, C[0], C[1], r * 2.5 * g, '#F6F2E7', 0.8 * g, period=12.0)
    return _zh_fixed(img, t, 59, 174.15, ink='#1A1416', halo_col='#EDE3CF')


R['B-outro-05'] = outro_05
tl.OWN_TYPE.add('B-outro-05')


# ---- B-outro-08: his face at sunrise -- he smiles, eyes wet; the card lifts out of frame and flies off like a kite ------
def outro_08(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from . import chars, print_fx
    from .print_fx import hexc as H
    from . import card as C
    tilt = _ease_in(clamp((t - 185.13) / 0.74)) * 900
    img = np.empty((1080, 1920, 3), np.float32)
    g = np.clip((kit._YS + tilt) / 1600.0, 0, 1)[..., None]
    img[:] = H('#2C4C9A') * (1 - g) + H('#F5C842') * g
    hy = int(720 + tilt)
    if hy < 1080:
        img[hy:] = H('#2C4C9A')
        kit.halo(img, 1500, hy - 80, 520, '#F5C842', 0.6, period=14.0)
        m = np.zeros((1080, 1920), np.float32)
        cv2.circle(m, (1500, hy - 80), 90, 1.0, -1, cv2.LINE_AA)
        img = img + (H('#FFF2C8')[None, None] - img) * m[..., None]
        # the train far behind, its board scrolling L62 ('NOW' last as it leaves frame at 185.5)
        tx = int(-200 + (t - 182.91) * 700)
        if tx < 1920:
            body = np.zeros((1080, 1920), np.float32)
            cv2.rectangle(body, (tx - 500, hy - 60), (tx, hy - 10), 1.0, -1)
            img = img + (H('#EDE3CF')[None, None] - img) * body[..., None]
            brd, _ = print_fx.led_board("CAN'T MAKE YOU HAPPIER NOW", cols=60, rows=8, dot=5, on='#F08A3C', off='#2A1C14',
                                        bg='#141018', font='silk', scroll=int((t - 182.9) * 24 * 1.6) - 60)
            bh, bw = brd.shape[:2]
            bx = tx - 480
            xa, xb = max(0, bx), min(1920, bx + bw)
            if xa < xb and hy - 60 - bh > 0:
                img[hy - 60 - bh:hy - 60, xa:xb] = brd[:, xa - bx:xb - bx]
    cl = once('o08_char', lambda: chars.CharLayer('B-outro-08', rim_hair='#F5C842'))
    if cl.ok:
        push = 1.0 + 0.03 * clamp(local / 2.2)
        rgb, a = cl.frame(local, x=1200, y=1080 + tilt, cx=0.5, cy=0.62, height=1450 * push)
        lit = np.clip((kit._XS - 1100) / 260.0, 0, 1) * a * _dots_k(0.45, 8.0)
        rgb = rgb + (H('#F5C842')[None, None] - rgb) * (lit * 0.5)[..., None]
        img = chars.over(img, rgb, a, shadow='#1E2550')
    # the stamp card lifts from the bottom on 183.65 and flies up, tumbling
    if t >= 183.65:
        if 'o08_card' not in _cache:
            card = C.render_card(stamp_k=(1, 1, 1, 1, 1), footer_n=0)
            lay = sun_stamp_layer()
            card = card * (1 - lay[..., 3:4]) + lay[..., :3] * lay[..., 3:4]
            _cache['o08_card'] = cv2.resize(card, (640, 360), interpolation=cv2.INTER_AREA)
        cd = _cache['o08_card']
        k = t - 183.65
        cx = 520 + 260 * math.sin(k * 1.4) + 200 * k
        cy = 1180 - 420 * k - 60 * k * k + tilt * 0.4
        ang = 25 * math.sin(k * 2.3) + 40 * k
        sc = 0.9 - 0.12 * k
        sq = 0.35 + 0.65 * abs(math.cos(k * 2.6))          # tumbling: foreshortened as it turns
        M = cv2.getRotationMatrix2D((320, 180), ang, sc)
        M[1] *= sq
        M[0, 2] += cx - 320
        M[1, 2] += cy - 180 * sq
        lay = cv2.warpAffine(cd, M, (1920, 1080))
        am = cv2.warpAffine(np.ones((360, 640), np.float32), M, (1920, 1080))
        img = img + (lay - img) * am[..., None]
    return _zh_fixed(img, t, 62, 182.9, ink='#1A1416', halo_col='#EDE3CF')


R['B-outro-08'] = outro_08
tl.OWN_TYPE.add('B-outro-08')


# ---- B-outro_hook-02: inside the curve mirror at noon -- she walks into the haze, glances back, smiles; the glass ripples
def outro_hook_02(s, t, local, fi):
    import cv2, math
    from mv.core import clamp
    from mva import fx
    from mv import text
    from . import chars
    from .print_fx import hexc as H
    img = noon_sky(t)
    push = 1.0 + 0.05 * clamp(local / (s['end'] - s['start']))
    cx, cy, R0 = 960, 500, int(450 * push)
    pole = np.zeros((1080, 1920), np.float32)
    cv2.rectangle(pole, (cx - 16, cy + R0), (cx + 16, 1080), 1.0, -1)
    img = img + (H('#F08A3C')[None, None] - img) * pole[..., None]
    road = once('hook03', _hook03_plate).frame(1.0)[:, ::-1].copy()
    road = kit.mirage_band(road, t, 540, 600, 1320, 30)
    cl = once('oh2_char', lambda: chars.CharLayer('B-outro_hook-02', rim_w=(1.5, 3.0, 0.0)))
    if cl.ok:
        rgb, a = cl.frame(local, x=960, y=700, cx=0.5, cy=0.97, height=420)
        road = chars.over(road, rgb, a)
    road = fx.fisheye(cv2.resize(road, (2 * R0, 2 * R0)), k=0.42)
    ys, xs = np.mgrid[0:2 * R0, 0:2 * R0].astype(np.float32)
    rip = (6 * np.sin(2 * math.pi * 1.2 * t + ys / 40.0)).astype(np.float32)
    road = cv2.remap(road, xs + rip, ys + rip * 0.5, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    disc = np.zeros((1080, 1920), np.float32)
    cv2.circle(disc, (cx, cy), R0, 1.0, -1, cv2.LINE_AA)
    canvas = img.copy()
    y0, x0 = cy - R0, cx - R0
    ya, yb, xa, xb = max(0, y0), min(1080, y0 + 2 * R0), max(0, x0), min(1920, x0 + 2 * R0)
    canvas[ya:yb, xa:xb] = road[ya - y0:yb - y0, xa - x0:xb - x0]
    img = img + (canvas - img) * disc[..., None]
    cv2.circle(img, (cx, cy), R0 + 16, tuple(float(v) for v in H('#F08A3C')), 30, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), R0 + 32, tuple(float(v) for v in H('#1A1416')), 3, cv2.LINE_AA)
    # the flying card caught on the rim
    if 'oh2_card' not in _cache:
        from . import card as C
        card = C.render_card(stamp_k=(1, 1, 1, 1, 1), footer_n=0)
        lay = sun_stamp_layer()
        card = card * (1 - lay[..., 3:4]) + lay[..., :3] * lay[..., 3:4]
        _cache['oh2_card'] = cv2.resize(card, (320, 180), interpolation=cv2.INTER_AREA)
    cd = _cache['oh2_card']
    flut = 6 * math.sin(t * 7)
    M = cv2.getRotationMatrix2D((160, 90), -18 + flut, 1.0)
    M[0, 2] += cx + R0 * 0.62 - 160
    M[1, 2] += cy - R0 * 0.78 - 90
    lay = cv2.warpAffine(cd, M, (1920, 1080))
    am = cv2.warpAffine(np.ones((180, 320), np.float32), M, (1920, 1080))
    img = img + (lay - img) * am[..., None]
    # L64 swimming across the convex surface with the ripple, one word per 8th; each swims by and fades; MIRROR settles
    gt = _map_gt(64)
    words = ['HEAT,', 'HEAT', 'WAVES,', "I'M", "SWIMMIN'", 'IN', 'A', 'MIRROR']
    for i, w in enumerate(words):
        t0 = gt[min(i, len(gt) - 1)]
        if t < t0:
            continue
        settle = w == 'MIRROR'
        life = (t - t0)
        if not settle and life > 0.9:
            continue
        alpha = 1.0 if settle else clamp(1.0 - (life - 0.55) / 0.35)
        lane = [-220, -80, 60, 200][i % 4]
        if settle:
            k = clamp((t - t0) / max(0.05, 191.05 - t0))
            e = k * k * (3 - 2 * k)
            x, y = cx - 300 + 300 * e, cy + 180 - 140 * e
        else:
            x = cx - 320 + 560 * life / 0.9
            y = cy + lane + 12 * math.sin(2 * math.pi * 1.2 * t + i)
        gl, _ = text.layout_h(w, x, y, 64 if not settle else 84, 'mincho', tracking=0.4, align='center')
        f, _ = text.render_glyphs(gl)
        if f is None:
            continue
        if not (settle and t >= 191.05):
            f = cv2.remap(f, kit._XS, (kit._YS + 6 * np.sin(kit._XS / 50.0 + t * 7)).astype(np.float32), cv2.INTER_LINEAR)
        f = f * disc * alpha
        img = img + (H('#2C4C9A')[None, None] - img) * np.roll(np.roll(f, 5, 0), 5, 1)[..., None]
        img = img + (H('#EDE3CF')[None, None] - img) * f[..., None]
    return _zh_fixed(img, t, 64, 188.848, ink='#1A1416', halo_col='#EDE3CF')


R['B-outro_hook-02'] = outro_hook_02
tl.OWN_TYPE.add('B-outro_hook-02')

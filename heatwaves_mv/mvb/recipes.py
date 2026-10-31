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

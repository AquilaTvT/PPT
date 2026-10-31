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
                bot, _ = print_fx.led_board('SUNRISE  SUNRISE  ', cols=51, rows=8, dot=12, on='#F08A3C', off='#3A2A20',
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

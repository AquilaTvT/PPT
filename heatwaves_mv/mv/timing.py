"""Musical grid for Lime — Heat Waves (Japanese Version), 198.74 s.

Beat grid fitted on the demucs drum stem: 81.0 BPM, beat 0 at 0.682 s,
bars (4/4) start on beat 2, so bar m starts at BAR0 + m * BAR.
The song is exactly 66 bars + a short tail:

  bars  0- 4  intro (English, sparse)
  bars  5- 8  hook       光りだすロード …
  bars  9-16  chorus 1
  bars 17-24  verse      テレビつけて …
  bars 25-28  chorus 2
  bars 29-36  bridge 1   闘えず息できず …   (drops out at bar 35)
  bars 37-44  chorus 3 (x2, full)
  bars 45-48  bridge 2   君はどんな夢のなかに … (quiet)
  bars 49-53  chorus 4 (quiet, 5 bars)
  bars 54-61  outro chorus (English, full)
  bars 62-65  outro hook (Road shimmer …)
"""
import json
import os

FPS = 30
DURATION = 198.74
BEAT = 0.74075
BEAT0 = 0.682
BAR = 4 * BEAT
BAR0 = BEAT0 + 2 * BEAT          # 2.1635


def bar(m, beat=0.0):
    return BAR0 + m * BAR + beat * BEAT


def beat_index(t):
    return (t - BEAT0) / BEAT


def beat_phase(t):
    """0..1 position inside the current beat"""
    b = beat_index(t)
    return b - int(b // 1)


def beat_pulse(t, decay=6.0, offset=0.0):
    """1 on every beat, decaying"""
    import math
    ph = beat_phase(t - offset)
    return math.exp(-ph * BEAT * decay)


def bar_pos(t):
    """(bar index, beat within bar as float)"""
    x = (t - BAR0) / BAR
    m = int(x // 1)
    return m, (x - m) * 4


SECTIONS = [
    ('intro', 0, 5), ('hook', 5, 9), ('chorus1', 9, 17), ('verse', 17, 25), ('chorus2', 25, 29),
    ('bridge1', 29, 37), ('chorus3', 37, 45), ('bridge2', 45, 49), ('chorus4', 49, 54),
    ('outro', 54, 62), ('outro_hook', 62, 66),
]

# (refined vocal start, text, lang). End = next line start.
_L = [
    (2.45, 'Last night, all I think about is you', 'en'),
    (5.43, "Don't stop, baby, you can walk through", 'en'),
    (8.00, "Don't want, baby, think about you", 'en'),
    (11.39, "You know that I'm never gonna lose", 'en'),
    (16.80, '光りだすロード', 'ja'),
    (18.20, '揺らいでくビジョン', 'ja'),
    (19.92, '熱波ゆらり 泳いでくミラー', 'ja'),
    (22.70, '光りだすロード', 'ja'),
    (24.15, '揺らいでくビジョン', 'ja'),
    (25.80, '熱波ゆらり 泳いでくミラー', 'ja'),
    (28.99, '思い浮かぶの君ばかり', 'ja'),
    (31.95, '初夏零時過ぎたばかり', 'ja'),
    (35.05, 'ヒートウェイブに迷うのさ', 'ja'),
    (37.75, '君に幸せあげられない', 'ja'),
    (40.75, '思い浮かぶの君ばかり', 'ja'),
    (43.65, '初夏零時過ぎたばかり', 'ja'),
    (46.95, 'ヒートウェイブに迷うのさ', 'ja'),
    (49.66, '君に幸せあげられない', 'ja'),
    (52.60, 'テレビつけて消さないように', 'ja'),
    (55.68, '僕らのこと考えないように', 'ja'),
    (58.55, '今日のハリウッド映画放映', 'ja'),
    (61.60, '僕らのことまるで投影', 'ja'),
    (64.30, '幸せに君なるはず', 'ja'),
    (67.64, '僕じゃなきゃ可能なはず', 'ja'),
    (70.35, '路に広がる逃げ水', 'ja'),
    (73.60, '闇の中ではもう見えず', 'ja'),
    (76.20, '思い浮かぶの君ばかり', 'ja'),
    (79.25, '初夏零時過ぎたばかり', 'ja'),
    (82.60, 'ヒートウェイブに迷うのさ', 'ja'),
    (85.15, '君に幸せあげられない', 'ja'),
    (87.86, '闘えず息できず', 'ja'),
    (90.80, '愛とか言っていたって', 'ja'),
    (94.34, '行くべきなのさ', 'ja'),
    (96.90, 'ほかの誰かふさわしいよ', 'ja'),
    (99.90, 'そりゃつらいけど', 'ja'),
    (103.10, '君もわかるはず', 'ja'),
    (105.98, '泣いてる君壊れそうだ', 'ja'),
    (109.12, 'さよならにも一度だけ', 'ja'),
    (111.93, '思い浮かぶの君ばかり', 'ja'),
    (114.81, '初夏零時過ぎたばかり', 'ja'),
    (117.72, 'ヒートウェイブに迷うのさ', 'ja'),
    (120.60, '君に幸せあげられない', 'ja'),
    (123.70, '思い浮かぶの君ばかり', 'ja'),
    (126.60, '初夏零時過ぎたばかり', 'ja'),
    (129.55, 'ヒートウェイブに迷うのさ', 'ja'),
    (132.55, '君に幸せあげられない', 'ja'),
    (135.60, '君はどんな夢のなかに', 'ja'),
    (138.55, '満たされた笑み浮かべて', 'ja'),
    (141.43, '思い知る自分の無力', 'ja'),
    (144.35, '陰りない君の表情に', 'ja'),
    (147.40, '思い浮かぶの君ばかり', 'ja'),
    (150.38, '初夏零時過ぎたばかり', 'ja'),
    (153.75, 'ヒートウェイブに迷うのさ', 'ja'),
    (156.10, '君に幸せあげられない', 'ja'),
    (159.30, '君に幸せあげられない', 'ja'),
    (162.30, 'Sometimes, all I think about is you', 'en'),
    (165.25, 'Late nights in the middle of June', 'en'),
    (168.05, "Heat waves been fakin' me out", 'en'),
    (171.10, "Can't make you happier now", 'en'),
    (174.15, 'Sometimes, all I think about is you', 'en'),
    (177.12, 'Late nights in the middle of June', 'en'),
    (180.15, "Heat waves been fakin' me out", 'en'),
    (182.90, "Can't make you happier now", 'en'),
    (186.22, "Road shimmer wigglin' the vision", 'en'),
    (188.85, "Heat, heat waves, I'm swimmin' in a mirror", 'en'),
    (192.00, "Road shimmer wigglin' the vision", 'en'),
    (194.70, "Heat, heat waves, I'm swimmin' in a mirror", 'en'),
]

LYRICS = []
for i, (t, txt, lang) in enumerate(_L):
    end = _L[i + 1][0] if i + 1 < len(_L) else 197.9
    LYRICS.append(dict(i=i, t=t, end=end, text=txt, lang=lang))


def lyric_at(t):
    for ly in LYRICS:
        if ly['t'] - 0.3 <= t < ly['end']:
            return ly
    return None


def lyric(i):
    return LYRICS[i]


_ana = None


def analysis():
    global _ana
    if _ana is None:
        p = os.path.join(os.path.dirname(__file__), '..', 'assets', 'analysis.json')
        with open(p) as f:
            _ana = json.load(f)
    return _ana


def envelope(t, key='drm'):
    """audio envelope (stem RMS) at time t, normalised roughly to 0..1"""
    import bisect
    a = analysis()['env']
    ts = a['t']
    i = min(max(bisect.bisect_left(ts, t), 0), len(ts) - 1)
    v = a[key][i]
    norm = {'drm': 0.25, 'voc': 0.2, 'bass': 0.3, 'oth': 0.2}[key]
    return min(1.0, v / norm)

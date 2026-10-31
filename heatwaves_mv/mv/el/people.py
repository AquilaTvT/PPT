"""Vector silhouettes: the boy and 君 (hat + dress), standing, walking, sitting."""
import math

import skia

from ..core import P


def boy_back(c, x, y, h, sway=0.0, paint=None):
    """standing, seen from behind (t-shirt, shorts). (x, y) = feet centre, h = height"""
    p = paint or P()
    s = h / 1000.0
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.rotate(sway)
    # head + messy hair
    c.drawCircle(0, -900, 66, p)
    hair = _poly([(-72, -905), (-80, -950), (-58, -990), (-20, -1004), (10, -998), (40, -1006), (66, -980),
                  (80, -940), (74, -900), (60, -872), (-58, -872)])
    c.drawPath(hair, p)
    c.drawPath(_smooth([(-24, -860), (24, -860), (30, -820), (-30, -820)]), p)          # neck
    # torso: t-shirt with sleeves, slight taper
    torso = _smooth([(-140, -810), (-60, -832), (60, -832), (140, -810), (178, -760), (196, -690), (150, -676),
                     (128, -620), (124, -520), (116, -470), (-116, -470), (-124, -520), (-128, -620),
                     (-150, -676), (-196, -690), (-178, -760)])
    c.drawPath(torso, p)
    # arms (slight bend), hands
    for sg in (-1, 1):
        c.drawPath(_taper([(sg * 170, -700), (sg * 182, -590), (sg * 176, -470)], 44, 34), p)
        c.drawCircle(sg * 176, -452, 28, p)
    # shorts + legs + shoes
    c.drawPath(_smooth([(-120, -480), (120, -480), (128, -330), (14, -320), (0, -360), (-14, -320),
                        (-128, -330)]), p)
    for sg in (-1, 1):
        c.drawPath(_taper([(sg * 64, -340), (sg * 66, -180), (sg * 62, -30)], 70, 50), p)
        c.drawPath(_smooth([(sg * 62 - 40, -40), (sg * 62 + 40, -40), (sg * 62 + 46, 0), (sg * 62 - 46, 0)]), p)
    c.restore()


def _smooth(pts, close=True):
    from ..core import smooth_path
    return smooth_path(pts, close=close, tension=0.35)


def _taper(pts, w0, w1):
    """a limb as a filled tapered polygon along a polyline"""
    import numpy as np
    pts = [np.array(q, float) for q in pts]
    left, right = [], []
    n = len(pts)
    for i, q in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        d = b - a
        d = d / (np.hypot(*d) + 1e-6)
        nrm = np.array([-d[1], d[0]])
        w = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        left.append(q + nrm * w)
        right.append(q - nrm * w)
    return _smooth([tuple(v) for v in left + right[::-1]])


def _st(p, w):
    q = skia.Paint(p)
    q.setStyle(skia.Paint.kStroke_Style)
    q.setStrokeWidth(w)
    q.setStrokeCap(skia.Paint.kRound_Cap)
    return q


def girl_hat(c, x, y, h, wind=0.0, t=0.0, paint=None):
    """君 standing in her sundress and straw hat (front/back neutral silhouette)"""
    p = paint or P()
    s = h / 1000.0
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.drawOval(skia.Rect.MakeXYWH(-170, -962, 340, 62), p)          # brim
    crown = skia.Path()
    crown.moveTo(-82, -936)
    crown.cubicTo(-84, -1036, 84, -1036, 82, -936)
    crown.close()
    c.drawPath(crown, p)
    tail = skia.Path()                                              # ribbon tail
    wv = math.sin(t * 8) * 20 * (0.4 + wind)
    tail.moveTo(72, -950)
    tail.cubicTo(130, -950 + wv, 190, -930 - wv, 250 + wind * 60, -958 + wv)
    tail.lineTo(244 + wind * 60, -934 + wv)
    tail.cubicTo(186, -912 - wv, 130, -922 + wv, 72, -928)
    tail.close()
    c.drawPath(tail, p)
    c.drawCircle(0, -850, 62, p)                                     # head
    c.drawPath(_smooth([(-76, -900), (76, -900), (86, -800), (66, -756), (-66, -756), (-86, -800)]), p)
    c.drawPath(_smooth([(-22, -800), (22, -800), (26, -740), (-26, -740)]), p)       # neck
    sway = math.sin(t * 6) * 10
    dress = _smooth([(-78, -762), (78, -762), (84, -680), (74, -600), (130 + wind * 30, -470),
                     (196 + wind * 50, -336 + sway * 0.3), (90, -318 + sway), (0, -326), (-90, -318),
                     (-190, -336), (-124, -470), (-74, -600), (-84, -680)])
    c.drawPath(dress, p)
    for sg in (-1, 1):
        c.drawPath(_taper([(sg * 84, -748), (sg * 104, -640), (sg * 118, -530)], 34, 26), p)
        c.drawCircle(sg * 118, -516, 20, p)
        c.drawPath(_taper([(sg * 44, -330), (sg * 46, -180), (sg * 44, -40)], 50, 38), p)
        c.drawPath(_smooth([(sg * 44 - 30, -44), (sg * 44 + 30, -44), (sg * 44 + 34, 0), (sg * 44 - 34, 0)]), p)
    c.restore()


def boy_walk(c, x, y, h, phase, paint=None):
    """side view walking to the right"""
    p = paint or P()
    s = h / 1000.0
    w = math.sin(phase)
    c.save()
    c.translate(x, y - abs(math.cos(phase)) * 10 * s)
    c.scale(s, s)
    c.drawCircle(10, -905, 66, p)
    c.drawPath(_poly([(-60, -940), (30, -985), (90, -930), (60, -880), (-50, -880)]), p)
    c.drawRoundRect(skia.Rect.MakeXYWH(-70, -840, 140, 380), 50, 50, p)
    c.drawLine(0, -800, w * 120, -520, _st(p, 48))
    c.drawLine(w * 120, -520, w * 150, -420, _st(p, 40))
    for sg in (1, -1):
        k = w * sg
        knee = (k * 110, -250)
        foot = (k * 190 - 10, -20 + max(0, -k) * 40)
        c.drawLine(0, -470, knee[0], knee[1], _st(p, 84))
        c.drawLine(knee[0], knee[1], foot[0], foot[1], _st(p, 70))
        c.drawOval(skia.Rect.MakeXYWH(foot[0] - 30, foot[1] - 20, 110, 40), p)
    c.restore()


def sitting_pair(c, x, y, h, t=0.0, paint=None, lean=0.0):
    """the two of them sitting side by side, seen from behind"""
    p = paint or P()
    s = h / 1000.0
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    # boy (left)
    bx = -190
    c.drawCircle(bx, -760, 62, p)
    c.drawPath(_poly([(bx - 66, -770), (bx - 60, -830), (bx - 20, -850), (bx + 30, -846), (bx + 64, -812),
                      (bx + 66, -770)]), p)
    c.drawPath(_smooth([(bx - 140, -660), (bx - 50, -690), (bx + 50, -690), (bx + 140, -660), (bx + 160, -560),
                        (bx + 150, -380), (bx - 150, -380), (bx - 160, -560)]), p)
    c.drawPath(_taper([(bx - 140, -650), (bx - 170, -520), (bx - 190, -400)], 40, 32), p)
    c.drawPath(_taper([(bx + 140, -650), (bx + 165, -540), (bx + 175, -420)], 40, 32), p)
    # girl (right) with hat and bob
    gx = 170 + lean * 40
    c.drawOval(skia.Rect.MakeXYWH(gx - 160, -846, 320, 58), p)
    crown = skia.Path()
    crown.moveTo(gx - 76, -824)
    crown.cubicTo(gx - 78, -918, gx + 78, -918, gx + 76, -824)
    crown.close()
    c.drawPath(crown, p)
    c.drawPath(_smooth([(gx - 74, -800), (gx + 74, -800), (gx + 84, -720), (gx + 60, -690), (gx - 60, -690),
                        (gx - 84, -720)]), p)
    c.drawPath(_smooth([(gx - 110, -680), (gx + 110, -680), (gx + 128, -560), (gx + 170, -380), (gx - 170, -380),
                        (gx - 128, -560)]), p)
    c.drawPath(_taper([(gx + 110, -660), (gx + 140, -530), (gx + 150, -420)], 30, 24), p)
    c.drawPath(_taper([(gx - 110, -660), (gx - 130, -540), (gx - 120, -430)], 30, 24), p)
    tail = skia.Path()
    wv = math.sin(t * 6) * 16
    tail.moveTo(gx + 70, -836)
    tail.cubicTo(gx + 130, -836 + wv, gx + 190, -816 - wv, gx + 250, -846 + wv)
    tail.lineTo(gx + 244, -820 + wv)
    tail.cubicTo(gx + 186, -796 - wv, gx + 130, -810 + wv, gx + 66, -816)
    tail.close()
    c.drawPath(tail, p)
    c.restore()


def _poly(pts):
    pth = skia.Path()
    pth.moveTo(*pts[0])
    for q in pts[1:]:
        pth.lineTo(*q)
    pth.close()
    return pth

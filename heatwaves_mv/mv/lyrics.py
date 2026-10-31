"""Lyric typesetting presets (+ my own Chinese translation)."""
import numpy as np

from . import core, text
from .core import clamp, ease_out
from .timing import LYRICS

ZH = {
    0: '昨夜 满脑子都是你', 1: '别停下 宝贝 你走得过去', 2: '不想再 宝贝 想起你', 3: '你知道 我绝不会认输',
    4: '渐渐发亮的路', 5: '摇晃起来的视野', 6: '热浪摇曳 在镜中游去',
    7: '渐渐发亮的路', 8: '摇晃起来的视野', 9: '热浪摇曳 在镜中游去',
    10: '浮现在脑海的 全都是你', 11: '初夏 刚过零点', 12: '在热浪里迷失方向', 13: '我给不了你幸福',
    14: '浮现在脑海的 全都是你', 15: '初夏 刚过零点', 16: '在热浪里迷失方向', 17: '我给不了你幸福',
    18: '打开电视 别让它熄灭', 19: '好让自己不去想我们', 20: '今天放映的好莱坞电影', 21: '简直是我们的投影',
    22: '你本该会幸福的', 23: '只要那个人不是我', 24: '路面漫开的蜃景', 25: '在黑暗里 已经看不见',
    26: '浮现在脑海的 全都是你', 27: '初夏 刚过零点', 28: '在热浪里迷失方向', 29: '我给不了你幸福',
    30: '无力抵抗 无法呼吸', 31: '就算说过爱之类的话', 32: '我也该走了', 33: '别的谁 更适合你',
    34: '当然 会很难受', 35: '你也应该明白', 36: '哭着的你 像要碎掉', 37: '再一次 然后就说再见',
    38: '浮现在脑海的 全都是你', 39: '初夏 刚过零点', 40: '在热浪里迷失方向', 41: '我给不了你幸福',
    42: '浮现在脑海的 全都是你', 43: '初夏 刚过零点', 44: '在热浪里迷失方向', 45: '我给不了你幸福',
    46: '你在怎样的梦里', 47: '浮起满足的笑容', 48: '才明白自己的无力', 49: '面对你毫无阴霾的神情',
    50: '浮现在脑海的 全都是你', 51: '初夏 刚过零点', 52: '在热浪里迷失方向', 53: '我给不了你幸福',
    54: '我给不了你幸福',
    55: '有时候 满脑子都是你', 56: '六月中旬的深夜', 57: '热浪一直在骗我', 58: '如今已无法让你更快乐',
    59: '有时候 满脑子都是你', 60: '六月中旬的深夜', 61: '热浪一直在骗我', 62: '如今已无法让你更快乐',
    63: '路面微光 晃动了视线', 64: '热浪 热浪 我在镜中游泳', 65: '路面微光 晃动了视线', 66: '热浪 热浪 我在镜中游泳',
}


def active(t, lead=0.15):
    for ly in LYRICS:
        if ly['t'] - lead <= t < ly['end'] + 0.05:
            return ly
    return None


def _times(ly, n, frac=0.7, max_reveal=2.3, lead=0.0):
    d = min(max_reveal, (ly['end'] - ly['t']) * frac)
    return text.char_times(n, ly['t'] + lead, ly['t'] + lead + d)


def draw_v(f, t, idx, x=1750, y=110, size=74, fill='white', edge='ink', zh_color=None, zh=True,
           style='drop', stroke=8.0, out_dur=0.3, fname='mincho', shadow=True, glow=None, hold_to=None,
           zh_size=None, haze=None, alpha=1.0, max_reveal=2.3):
    """vertical Japanese line (right-anchored column) + small Chinese column on its left"""
    ly = LYRICS[idx]
    end = hold_to if hold_to is not None else ly['end']
    if t < ly['t'] - 0.2 or t > end + 0.05:
        return
    txt = ly['text'].replace(' ', '\n') if len(ly['text']) > 9 and ' ' in ly['text'] else ly['text']
    gl = text.layout_v(txt, x, y, size, fname)
    times = _times(ly, len(gl), max_reveal=max_reveal)
    out_t = end - out_dur
    anim = {'drop': text.reveal_drop, 'pop': text.reveal_pop, 'type': text.reveal_type}[style](times, t, out_t=out_t)
    fc, sc = text.render_glyphs(gl, stroke=stroke, anim=anim)
    if fc is None:
        return
    if haze is not None:
        fc = core.heat_haze(fc, t, amp=haze, wavelength=22)
        sc = core.heat_haze(sc, t, amp=haze, wavelength=22) if sc is not None else None
    if shadow and sc is not None:
        sh = np.roll(np.roll(sc, int(6 * core.S), 1), int(7 * core.S), 0)
        f.over(edge, core.halftone(sh * 0.9, cell=4.5, angle=45), alpha=0.6 * alpha)
    if glow is not None:
        f.add(glow, core.blur(fc, 12), alpha=0.5 * alpha)
    if sc is not None:
        f.over(edge, sc, alpha=alpha)
    f.over(fill, fc, alpha=alpha)
    if zh and idx in ZH:
        ncols = txt.count('\n') + 1
        zs = zh_size or max(20, size * 0.3)
        zx = x - size * (1.25 * (ncols - 1) + 0.95)
        zgl = text.layout_v(ZH[idx], zx, y + size * 0.15, zs, 'zh', tracking=0.12)
        zt = text.char_times(len(zgl), times[0] + 0.1, times[-1] + 0.25)
        zanim = text.reveal_drop(zt, t, dur=0.35, drop=8, out_t=out_t, blur=2)
        zf, zs_ = text.render_glyphs(zgl, stroke=3.5, anim=zanim)
        if zf is not None:
            f.over(edge, zs_, alpha=0.85 * alpha)
            f.over(zh_color or fill, zf, alpha=0.92 * alpha)
    return gl


def draw_h(f, t, idx, x=960, y=930, size=58, fill='white', edge='ink', align='center', fname='mincho',
           zh=True, style='drop', stroke=7.0, out_dur=0.3, shadow=True, glow=None, hold_to=None, zh_size=None,
           tracking=0.04, alpha=1.0, zh_gap=None, max_reveal=2.3, haze=None):
    ly = LYRICS[idx]
    end = hold_to if hold_to is not None else ly['end']
    if t < ly['t'] - 0.2 or t > end + 0.05:
        return
    if ly['lang'] == 'en' and fname == 'mincho':
        fname = 'corm_i'
    gl, wtot = text.layout_h(ly['text'], x, y, size, fname, tracking=tracking, align=align)
    times = _times(ly, len(gl), max_reveal=max_reveal)
    out_t = end - out_dur
    anim = {'drop': text.reveal_drop, 'pop': text.reveal_pop, 'type': text.reveal_type}[style](times, t, out_t=out_t)
    fc, sc = text.render_glyphs(gl, stroke=stroke, anim=anim)
    if fc is None:
        return
    if haze is not None:
        fc = core.heat_haze(fc, t, amp=haze, wavelength=18)
        sc = core.heat_haze(sc, t, amp=haze, wavelength=18) if sc is not None else None
    if shadow and sc is not None:
        sh = np.roll(np.roll(sc, int(5 * core.S), 1), int(6 * core.S), 0)
        f.over(edge, core.halftone(sh * 0.9, cell=4.5, angle=45), alpha=0.55 * alpha)
    if glow is not None:
        f.add(glow, core.blur(fc, 12), alpha=0.5 * alpha)
    if sc is not None:
        f.over(edge, sc, alpha=alpha)
    f.over(fill, fc, alpha=alpha)
    if zh and idx in ZH:
        zs = zh_size or max(20, size * 0.36)
        gap = zh_gap if zh_gap is not None else size * 0.85
        zgl, _ = text.layout_h(ZH[idx], x, y + gap, zs, 'zh', tracking=0.1, align=align)
        zt = text.char_times(len(zgl), times[0] + 0.1, times[-1] + 0.25)
        zanim = text.reveal_drop(zt, t, dur=0.35, drop=6, out_t=out_t, blur=2)
        zf, zs_ = text.render_glyphs(zgl, stroke=3.5, anim=zanim)
        if zf is not None:
            f.over(edge, zs_, alpha=0.85 * alpha)
            f.over(fill, zf, alpha=0.92 * alpha)
    return gl


def draw_tv(f, t, idx, x=960, y=900, size=40, fill='white', edge='black', alpha=1.0, zh=True):
    """pixel-font subtitles (typed on)"""
    ly = LYRICS[idx]
    if t < ly['t'] - 0.05 or t > ly['end']:
        return
    gl, _ = text.layout_h(ly['text'], x, y, size, 'dot', tracking=0.02, align='center')
    times = _times(ly, len(gl), frac=0.8, max_reveal=2.0)
    anim = text.reveal_type(times, t, out_t=ly['end'] - 0.12)
    fc, sc = text.render_glyphs(gl, stroke=6, anim=anim)
    if fc is None:
        return
    fc = core.dither(fc, 2) if core.S >= 0.99 else fc
    f.over(edge, sc, alpha=alpha * 0.9)
    f.over(fill, fc, alpha=alpha)
    if zh and idx in ZH:
        zgl, _ = text.layout_h(ZH[idx], x, y + size * 1.15, size * 0.62, 'dot', tracking=0.04, align='center')
        zt = text.char_times(len(zgl), times[0] + 0.1, times[-1] + 0.2)
        za = text.reveal_type(zt, t, out_t=ly['end'] - 0.12)
        zf, zs = text.render_glyphs(zgl, stroke=5, anim=za)
        if zf is not None:
            f.over(edge, zs, alpha=alpha * 0.9)
            f.over('aqua', zf, alpha=alpha)

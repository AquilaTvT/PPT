"""MV-A compositing effects (1920x1080 float32 RGB in [0, 1]).

Everything is a pure function of (image, time, params) so frames can be rendered out of order in
parallel workers. Masks are float32 (H, W) in [0, 1].
"""
import math

import cv2
import numpy as np

W, H = 1920, 1080
_YS, _XS = np.mgrid[0:H, 0:W].astype(np.float32)


# ------------------------------------------------------------------ basics
def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def fit(img, w=W, h=H, zoom=1.0, cx=0.5, cy=0.5, rot=0.0):
    """cover-fit any frame into w x h, optional zoom/pan/rotation about (cx, cy) in source fractions"""
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih) * zoom
    M = cv2.getRotationMatrix2D((cx * iw, cy * ih), rot, s)
    M[0, 2] += w / 2 - cx * iw
    M[1, 2] += h / 2 - cy * ih
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def lum(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


def exposure(img, ev):
    return img * np.float32(2.0 ** ev)


def grade(img, warm=0.0, sat=1.0, lift=0.0, gain=1.0, gamma=1.0, tint=None, tint_amt=0.0, contrast=1.0):
    """warm>0 pushes R up / B down; tint blends towards a colour (multiply-ish) in the mids"""
    out = img
    if warm:
        out = out * np.array([1 + 0.12 * warm, 1 + 0.02 * warm, 1 - 0.12 * warm], np.float32)
    if sat != 1.0:
        l = lum(out)[..., None]
        out = l + (out - l) * np.float32(sat)
    if contrast != 1.0:
        out = (out - 0.5) * np.float32(contrast) + 0.5
    if lift or gain != 1.0:
        out = lift + out * (gain - lift)
    if gamma != 1.0:
        out = np.clip(out, 0, None) ** np.float32(1.0 / gamma)
    if tint is not None and tint_amt:
        c = hexc(tint) if isinstance(tint, str) else np.asarray(tint, np.float32)
        out = out * (1 - tint_amt) + out * c * tint_amt * 1.6
    return out.astype(np.float32)


def hue_mask(img, ranges, sat_min=0.18):
    """mask of pixels whose hue (0..180, OpenCV) falls in any (h0, h1) range"""
    hsv = cv2.cvtColor(np.clip(img, 0, 1), cv2.COLOR_RGB2HSV)
    h, s = hsv[..., 0] / 2.0, hsv[..., 1]
    m = np.zeros(img.shape[:2], np.float32)
    for h0, h1 in ranges:
        if h0 <= h1:
            m = np.maximum(m, ((h >= h0) & (h <= h1)).astype(np.float32))
        else:
            m = np.maximum(m, ((h >= h0) | (h <= h1)).astype(np.float32))
    m *= np.clip((s - sat_min) * 4, 0, 1)
    return cv2.GaussianBlur(m, (0, 0), 3)


def selective_desat(img, amount, keep=((0, 12), (165, 180), (5, 25))):
    """drop saturation except skin / reds (bridge1 grade)"""
    keepm = hue_mask(img, keep)[..., None]
    l = lum(img)[..., None]
    grey = l + (img - l) * np.float32(1 - amount)
    return grey * (1 - keepm) + img * keepm


def blur(img, sigma):
    return cv2.GaussianBlur(img, (0, 0), sigma) if sigma > 0.05 else img


def screen(a, b, k=1.0):
    return 1.0 - (1.0 - a) * (1.0 - b * np.float32(k))


def over(a, b, m):
    m = m[..., None] if m.ndim == 2 else m
    return a + (b - a) * m


def add(a, b, k=1.0):
    return a + b * np.float32(k)


# ------------------------------------------------------------------ light
def bloom(img, thresh=0.75, sigma=18.0, amount=0.35, tint=None):
    hi = np.clip(img - thresh, 0, None) / max(1e-3, 1 - thresh)
    g = cv2.GaussianBlur(hi, (0, 0), sigma) + 0.5 * cv2.GaussianBlur(hi, (0, 0), sigma * 3)
    if tint is not None:
        g = g * (hexc(tint) if isinstance(tint, str) else tint)
    return img + g * np.float32(amount)


def halation(img, amount=0.25, sigma=10.0):
    """red-orange glow around highlights (film)"""
    hi = np.clip(lum(img) - 0.7, 0, None)[..., None] * np.array([1.0, 0.45, 0.2], np.float32)
    return img + cv2.GaussianBlur(hi, (0, 0), sigma) * np.float32(amount * 2.2)


def white_bloom(img, k):
    """overexposure to white (k 0..1)"""
    if k <= 0:
        return img
    e = img * (1 + 3.0 * k) + k * 0.6
    return np.clip(e, 0, 1) * (1 - k * 0.15) + k * 0.15


def vignette(img, strength=0.25, power=2.2):
    d = np.sqrt(((_XS - W / 2) / (W / 2)) ** 2 + ((_YS - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    return img * (1 - strength * d ** power)[..., None]


def light_leak(img, t, t0, dur=0.8, color='#FFB46B', direction=1, amount=0.5):
    """a soft warm band sweeping across the frame"""
    p = (t - t0) / dur
    if p < 0 or p > 1:
        return img
    x = (p * 1.6 - 0.3) * W if direction > 0 else (1.3 - p * 1.6) * W
    band = np.exp(-((_XS - x - (_YS - H / 2) * 0.35) / 260.0) ** 2) * math.sin(math.pi * p)
    return screen(img, hexc(color)[None, None] * band[..., None], amount)


def rect_sweep(img, t, t0, period, color='#FFB46B', n=8, w=240, h=150, y=None, speed=-2600.0, amount=0.35,
               skew=0.0, region=None):
    """lit train-window rectangles passing across the frame, one every `period` seconds"""
    acc = np.zeros((H, W), np.float32)
    for k in range(n):
        tk = t - (t0 + k * period)
        if tk < 0:
            continue
        x = (W + w if speed < 0 else -w) + speed * tk
        if x < -2 * w or x > W + 2 * w:
            continue
        yy = (y if y is not None else H * 0.3) + 18 * math.sin(k * 1.7)
        xs = _XS - x - (_YS - yy) * skew
        m = np.exp(-(np.maximum(np.abs(xs) - w / 2, 0) / 30.0) ** 2) * np.exp(-(np.maximum(np.abs(_YS - yy) - h / 2, 0) / 30.0) ** 2)
        acc = np.maximum(acc, m)
    if region is not None:
        acc *= region
    return add(img, hexc(color)[None, None] * acc[..., None], amount)


def pulse(t, times, decay=0.12):
    """sum of exponential pulses after each time in `times`"""
    v = 0.0
    for tb in times:
        if t >= tb:
            v += math.exp(-(t - tb) / decay)
    return v


# ------------------------------------------------------------------ distortion
_HAZE_TEX = None


def _haze_tex():
    """tileable smooth 2-channel noise (256 x 256, unit std) for the heat-haze displacement field"""
    global _HAZE_TEX
    if _HAZE_TEX is None:
        rng = np.random.default_rng(1907)
        n = rng.standard_normal((48, 48, 2)).astype(np.float32)
        big = cv2.GaussianBlur(np.tile(n, (3, 3, 1)), (0, 0), 1.6)[48:96, 48:96]       # blurred with wrap-around
        big = cv2.resize(np.tile(big, (3, 3, 1)), (768, 768), interpolation=cv2.INTER_CUBIC)[256:512, 256:512]
        _HAZE_TEX = (big / big.std()).astype(np.float32)
    return _HAZE_TEX


def heat_haze(img, t, amp=0.012, wavelength=38.0, speed=1.6, region=None, vertical=0.35, seed=0):
    """heat shimmer: two octaves of smooth noise drifting upward (rising hot air), so lines tremble irregularly instead
    of bending as one wave. amp is a fraction of frame height (the spec's %): peaks reach about amp, typical
    displacement is a third of it. region (0..1 mask) limits it."""
    a = amp * H
    tex = _haze_tex()
    d = np.zeros((H, W, 2), np.float32)
    for lam, wgt, rise in ((wavelength * 2.4, 0.62, 1.0), (wavelength * 0.95, 0.38, 1.7)):
        k = 256.0 / (lam * 6.0)                            # ~6 noise cells per wavelength across the texture
        u = (_XS * k + seed * 37.0 + t * speed * 6.0 * 0.3).astype(np.float32)
        v = (_YS * k + seed * 53.0 + t * speed * 6.0 * rise).astype(np.float32)    # the field rises with time
        d += cv2.remap(tex, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * wgt
    dx = d[..., 0] * (0.36 * a)
    dy = d[..., 1] * (0.36 * a * vertical)
    if region is not None:
        dx *= region
        dy *= region
    return cv2.remap(img, _XS + dx, _YS + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def ripple(img, cx, cy, t, t0, speed=520.0, wavelength=46.0, amp=9.0, decay=1.6, rings=3, region=None):
    """expanding ring ripple from (cx, cy) started at t0"""
    dt = t - t0
    if dt < 0:
        return img
    r = np.sqrt((_XS - cx) ** 2 + (_YS - cy) ** 2) + 1e-3
    front = speed * dt
    env = np.exp(-((r - front) / (wavelength * rings)) ** 2) * math.exp(-dt * decay)
    d = np.sin((r - front) / wavelength * 2 * math.pi) * amp * env
    if region is not None:
        d *= region
    return cv2.remap(img, _XS + d * (_XS - cx) / r, _YS + d * (_YS - cy) / r, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)


def water_refract(img, t, amp=7.0, scale=90.0, speed=0.8):
    dx = (np.sin(_YS / scale + t * speed * 2.0) + np.sin((_XS + _YS) / (scale * 1.7) + t * speed * 1.3)) * amp
    dy = (np.cos(_XS / (scale * 1.3) + t * speed * 1.7) + np.sin((_XS - _YS) / (scale * 2.1) + t * speed)) * amp
    return cv2.remap(img, _XS + dx, _YS + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def caustics(t, scale=140.0, speed=0.6, sharp=6.0):
    """animated caustic light pattern (H, W) in [0, 1]"""
    u = _XS / scale
    v = _YS / scale
    c = np.zeros((H, W), np.float32)
    for i, (a, b) in enumerate(((1.0, 0.7), (-0.6, 1.1), (0.4, -0.9))):
        c += np.sin(u * a * 2.3 + v * b * 2.3 + t * speed * (1.4 + i * 0.3) + np.sin(v * 1.7 + t * speed + i))
    c = np.abs(c) / 3.0
    return np.clip(1.0 - c, 0, 1) ** sharp


def fisheye(img, k=0.55):
    """convex-mirror look (barrel), returns same size"""
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (xs - w / 2) / (w / 2), (ys - h / 2) / (h / 2)
    r = np.sqrt(nx * nx + ny * ny)
    f = 1 + k * r * r
    return cv2.remap(img, (nx / f) * w / 2 + w / 2, (ny / f) * h / 2 + h / 2, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)


def barrel(img, k=0.08):
    nx, ny = (_XS - W / 2) / (W / 2), (_YS - H / 2) / (H / 2)
    r2 = nx * nx + ny * ny
    f = 1 + k * r2
    return cv2.remap(img, nx * f * W / 2 + W / 2, ny * f * H / 2 + H / 2, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))


def chroma(img, px=2.0):
    if px <= 0:
        return img
    out = img.copy()
    out[..., 0] = cv2.warpAffine(img[..., 0], np.float32([[1, 0, px], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    out[..., 2] = cv2.warpAffine(img[..., 2], np.float32([[1, 0, -px], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    return out


def swirl(img, cx, cy, ang):
    dx, dy = _XS - cx, _YS - cy
    r = np.sqrt(dx * dx + dy * dy)
    a = ang * np.exp(-r / 700.0)
    c, s = np.cos(a), np.sin(a)
    return cv2.remap(img, cx + dx * c - dy * s, cy + dx * s + dy * c, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ------------------------------------------------------------------ masks
def ellipse_mask(cx, cy, rx, ry, feather=3.0, rot=0.0):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    x, y = _XS - cx, _YS - cy
    u, v = (x * c + y * s) / rx, (-x * s + y * c) / ry
    d = np.sqrt(u * u + v * v)
    return np.clip((1 - d) * min(rx, ry) / max(feather, 0.5), 0, 1).astype(np.float32)


def poly_mask(points, feather=2.0):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(np.asarray(points, np.float32) * 4).astype(np.int32)], 255, lineType=cv2.LINE_AA, shift=2)
    m = m.astype(np.float32) / 255
    return cv2.GaussianBlur(m, (0, 0), feather) if feather > 0 else m


def noise_blob_mask(cx, cy, r, t, seed=0, lobes=7, rough=0.18):
    """organic spill / puddle shape that can grow (r) over time"""
    ang = np.arctan2(_YS - cy, (_XS - cx) * 0.45)
    rr = np.sqrt(((_XS - cx) * 0.45) ** 2 + (_YS - cy) ** 2)
    edge = r * (1 + rough * (np.sin(ang * lobes + seed) * 0.6 + np.sin(ang * (lobes + 4) + seed * 2.1 + t) * 0.4))
    return np.clip((edge - rr) / 6.0, 0, 1).astype(np.float32)


# ------------------------------------------------------------------ CRT
def crt(img, t, barrel_k=0.1, scan=0.22, mask=0.18, bloom_amt=0.3, hum=0.05, curve_vignette=True):
    out = barrel(img, barrel_k) if barrel_k else img
    if mask:
        trip = np.stack([(_XS % 3 == k).astype(np.float32) for k in range(3)], -1)
        out = out * (1 - mask + mask * 2.0 * trip)
    if scan:
        out = out * (1 - scan * (0.5 + 0.5 * np.cos(_YS * math.pi * 2 / 3.0)))[..., None]
    if hum:
        y = (H - (t * 90.0) % (H * 1.4))
        out = out * (1 - hum * np.exp(-((_YS - y) / 70.0) ** 2))[..., None]
    if bloom_amt:
        out = bloom(out, 0.6, 6.0, bloom_amt)
    if curve_vignette:
        nx, ny = (_XS - W / 2) / (W / 2), (_YS - H / 2) / (H / 2)
        corner = np.clip(1.0 - (np.abs(nx) ** 8 + np.abs(ny) ** 8) ** 0.125, 0, 1)
        out = out * np.clip(corner * 14, 0, 1)[..., None]
    return out


def tv_noise(t, seed=0, level=0.75):
    rng = np.random.default_rng(int(t * 240) + seed)
    n = rng.random((H // 3, W // 3), dtype=np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_NEAREST)
    roll = int((t * 2000) % H)
    n = np.roll(n, roll, axis=0)
    return np.repeat((n * level)[..., None], 3, -1)


# ------------------------------------------------------------------ particles (deterministic)
def _rng(seed):
    return np.random.default_rng(seed)


def sparkles(img, t, n=120, seed=1, area=(0, 500, 1920, 1080), color='#FFF4D6', size=(1.5, 4.0), rate=8.0, amount=1.0):
    r = _rng(seed)
    x = r.uniform(area[0], area[2], n)
    y = r.uniform(area[1], area[3], n)
    ph = r.uniform(0, 6.28, n)
    s = r.uniform(*size, n)
    acc = np.zeros((H, W), np.float32)
    tw = np.clip(np.sin(t * rate + ph), 0, 1) ** 6
    for i in np.nonzero(tw > 0.05)[0]:
        cv2.circle(acc, (int(x[i]), int(y[i])), max(1, int(s[i] * tw[i] * 1.6)), float(tw[i]), -1, cv2.LINE_AA)
        cv2.line(acc, (int(x[i] - s[i] * 4 * tw[i]), int(y[i])), (int(x[i] + s[i] * 4 * tw[i]), int(y[i])), float(tw[i] * 0.6), 1, cv2.LINE_AA)
    acc = cv2.GaussianBlur(acc, (0, 0), 1.0)
    return add(img, hexc(color)[None, None] * acc[..., None], amount)


def motes(img, t, n=70, seed=2, area=(0, 0, 1920, 1080), color='#FFF6E0', rise=14.0, amount=0.6, region=None):
    r = _rng(seed)
    x0 = r.uniform(area[0], area[2], n)
    y0 = r.uniform(area[1], area[3], n)
    sp = r.uniform(0.4, 1.0, n)
    ph = r.uniform(0, 6.28, n)
    s = r.uniform(1.0, 3.2, n)
    acc = np.zeros((H, W), np.float32)
    for i in range(n):
        x = x0[i] + math.sin(t * 0.5 * sp[i] + ph[i]) * 30
        y = area[1] + ((y0[i] - area[1] - rise * sp[i] * t) % max(1, area[3] - area[1]))
        a = 0.5 + 0.5 * math.sin(t * 1.3 + ph[i])
        cv2.circle(acc, (int(x), int(y)), int(s[i]), float(a), -1, cv2.LINE_AA)
    acc = cv2.GaussianBlur(acc, (0, 0), 1.2)
    if region is not None:
        acc *= region
    return add(img, hexc(color)[None, None] * acc[..., None], amount)


def rain(img, t, layers=((0.35, 900, 22, 1.0), (0.22, 1500, 40, 1.4), (0.12, 2300, 70, 2.0)), seed=3, angle=8.0,
         color='#D8E2EA', speed_k=1.0):
    """3 depth layers: (alpha, speed px/s, streak length, width)"""
    out = img
    for li, (alpha, speed, length, width) in enumerate(layers):
        r = _rng(seed + li)
        n = int(260 * (1 + li))
        x0 = r.uniform(-200, W + 200, n)
        y0 = r.uniform(0, H, n)
        acc = np.zeros((H, W), np.float32)
        dx = math.tan(math.radians(angle))
        for i in range(n):
            y = (y0[i] + speed * speed_k * t) % (H + length) - length
            x = x0[i] + dx * y
            cv2.line(acc, (int(x), int(y)), (int(x + dx * length), int(y + length)), 1.0, max(1, int(width)), cv2.LINE_AA)
        acc = cv2.GaussianBlur(acc, (0, 0), 0.6 + li * 0.5)
        out = screen(out, hexc(color)[None, None] * acc[..., None], alpha)
    return out


def bubbles(img, t, n=40, seed=4, area=(0, 0, 1920, 1080), rim='#BFF3FF', speed=120.0, amount=0.8):
    r = _rng(seed)
    x0 = r.uniform(area[0], area[2], n)
    y0 = r.uniform(area[1], area[3], n)
    rad = r.uniform(3, 16, n)
    sp = r.uniform(0.6, 1.4, n)
    acc = np.zeros((H, W), np.float32)
    for i in range(n):
        y = area[1] + ((y0[i] - area[1] - speed * sp[i] * t) % max(1, area[3] - area[1]))
        x = x0[i] + math.sin(t * 2.0 * sp[i] + i) * 8
        cv2.circle(acc, (int(x), int(y)), int(rad[i]), 1.0, 1, cv2.LINE_AA)
        cv2.circle(acc, (int(x - rad[i] * 0.35), int(y - rad[i] * 0.35)), max(1, int(rad[i] * 0.2)), 1.0, -1, cv2.LINE_AA)
    return add(img, hexc(rim)[None, None] * cv2.GaussianBlur(acc, (0, 0), 0.7)[..., None], amount)


# ------------------------------------------------------------------ frame finish
def grain(img, frame_idx, amount=0.03, size=1.2, freeze=False):
    r = np.random.default_rng(12345 if freeze else frame_idx * 7919 + 17)
    n = r.standard_normal((int(H / size), int(W / size)), dtype=np.float32)
    if size != 1.0:
        n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)
    l = lum(np.clip(img, 0, 1))
    k = amount * (0.6 + 0.8 * l * (1 - l) * 4)
    return img + (n * k)[..., None]


def letterbox(img, ratio=2.39, open_k=0.0, color=(0.0, 0.0, 0.0)):
    """open_k 0 = full 2.39 bars, 1 = no bars"""
    bar = int(round((H - W / ratio) / 2 * (1 - open_k)))
    if bar <= 0:
        return img
    out = img.copy()
    out[:bar] = color
    out[H - bar:] = color
    return out


def letterbox_bar(ratio=2.39):
    return int(round((H - W / ratio) / 2))


def to_u8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

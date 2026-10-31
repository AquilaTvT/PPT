"""Print-style stylizer for MV-B: flattened inks + screen-locked halftone shading + ink line art.

  sty = PrintStyle(inks=[...], period=10, angle=45)
  out = sty(rgb_float)          # (H, W, 3) float, same size

- edge-preserving flatten (bilateral) -> nearest ink in Lab (limited palette, like a screen print),
- tonal detail inside each ink region is carried by a 45-degree AM halftone in the darker ink
  (dot radius from local luminance), on a grid locked to the screen,
- XDoG ink lines in the warm-black ink,
- optional paper grain.
"""
import numpy as np
import cv2


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def to_lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2Lab)


class PrintStyle:
    def __init__(self, inks, ink_line='#1E1A22', paper='#EDE3CF', period=10.0, angle=45.0, line_w=1.0,
                 dot_gain=1.0, shade_strength=0.85, grain=0.025, seed=0):
        self.inks = np.stack([hexc(h) for h in inks]).astype(np.float32)
        self.inks_lab = to_lab(self.inks[None])[0]
        self.line = hexc(ink_line)
        self.paper = hexc(paper)
        self.period, self.angle, self.line_w = period, np.deg2rad(angle), line_w
        self.dot_gain, self.shade, self.grain = dot_gain, shade_strength, grain
        self.rng = np.random.default_rng(seed)
        self._grid = {}

    def grid(self, h, w):
        """distance (in cells) to the nearest dot centre on a rotated screen-locked grid"""
        key = (h, w)
        if key not in self._grid:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            c, s = np.cos(self.angle), np.sin(self.angle)
            u = (xx * c + yy * s) / self.period
            v = (-xx * s + yy * c) / self.period
            du = u - np.round(u)
            dv = v - np.round(v)
            self._grid[key] = np.sqrt(du * du + dv * dv)          # 0 at dot centre, ~0.707 at cell corner
        return self._grid[key]

    def __call__(self, rgb, alpha=None):
        h, w = rgb.shape[:2]
        img8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
        flat = img8
        for _ in range(2):
            flat = cv2.bilateralFilter(flat, 9, 40, 7)
        flat = flat.astype(np.float32) / 255.0
        # nearest ink (Lab) on a softened image -> flat colour regions
        lab = to_lab(flat)
        d = ((lab[:, :, None, :] - self.inks_lab[None, None]) ** 2).sum(-1)
        idx = d.argmin(-1)
        base = self.inks[idx]
        # tone inside each region: luminance relative to the ink's own luminance -> halftone dots of a darker ink
        lum = lab[:, :, 0] / 100.0
        ink_l = self.inks_lab[idx][:, :, 0] / 100.0
        dark = np.clip((ink_l - lum) * 2.2 * self.dot_gain, 0, 1)        # how much darker than the ink
        r = np.sqrt(dark) * 0.62                                           # dot radius in cell units (area ~ tone)
        g = self.grid(h, w)
        aa = 1.0 / self.period
        dot = np.clip((r - g) / aa + 0.5, 0, 1) * (r > 0.03)
        shade_col = base * 0.55 + self.line * 0.45
        out = base * (1 - dot[..., None] * self.shade) + shade_col * (dot[..., None] * self.shade)
        # highlights: small paper-coloured dots where the image is much lighter than the ink
        light = np.clip((lum - ink_l) * 2.0, 0, 1)
        rl = np.sqrt(light) * 0.45
        dl = np.clip((rl - g) / aa + 0.5, 0, 1) * (rl > 0.05)
        out = out * (1 - dl[..., None] * 0.7) + self.paper * (dl[..., None] * 0.7)
        # XDoG ink lines from the original luminance
        y = cv2.cvtColor(img8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        g1 = cv2.GaussianBlur(y, (0, 0), 0.9 * self.line_w)
        g2 = cv2.GaussianBlur(y, (0, 0), 1.6 * 0.9 * self.line_w)
        xdog = g1 - 0.98 * g2
        lines = np.clip(1 - np.tanh(np.maximum(0, -xdog - 0.004) * 60), 0, 1)   # 1 = no line
        lines = cv2.GaussianBlur(lines, (0, 0), 0.5)
        out = out * lines[..., None] + self.line * (1 - lines[..., None])
        if self.grain:
            n = self.rng.normal(0, self.grain, (h, w, 1)).astype(np.float32)
            out = out + n
        out = np.clip(out, 0, 1)
        if alpha is not None:
            out = out * alpha[..., None] + self.paper * (1 - alpha[..., None])
        return out

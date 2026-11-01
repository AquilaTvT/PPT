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


def skin_mask(flat):
    """(soft mask, core mask) of skin in an anime frame (faces, necks, hands). Core: clearly skin-coloured pixels
    (warm, R > G >= B, moderate saturation). Around the core, flushed / blushing / sun-lit reds join it (but not a
    fully saturated scarf), and the features skin encloses (eyes, an open mouth) are filled in."""
    f8 = (np.clip(flat, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(f8, cv2.COLOR_RGB2HSV)
    H, S, V = hsv[..., 0].astype(np.int16), hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
    R, G, B = f8[..., 0].astype(np.int16), f8[..., 1].astype(np.int16), f8[..., 2].astype(np.int16)
    core = ((R > G) & (G * 100 >= B * 95) & (R - B >= 16) & (V >= 70) & (S >= 18) & (S <= 205)
            & ((G - B) * 100 >= (R - B) * 5)).astype(np.uint8)            # pinks (blush) yes; pure reds (G = B) no
    core = cv2.morphologyEx(core, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    h, w = core.shape
    n, lab, stats, _ = cv2.connectedComponentsWithStats(core, 8)
    keep = np.zeros(n, bool)
    if n > 1:                     # big pieces only: a light-brown iris is skin-coloured but must keep its own ink
        areas = stats[1:, cv2.CC_STAT_AREA]
        keep[1:] = (areas >= max(64, int(h * w * 0.0004))) & (areas >= 0.12 * areas.max())
    core = keep[lab].astype(np.uint8)
    def grow(frac):
        r = max(4, int(h * frac))
        return cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    redish = ((H <= 15) | (H >= 160)) & (S >= 40) & (V >= 50)
    orange = (H >= 6) & (H <= 15)
    soft = (redish & ((S < 150) | orange)).astype(np.uint8)   # blush, flushed cheeks, orange sun on skin: anywhere on the face
    hard = (redish & (S >= 150) & ~orange).astype(np.uint8)  # pure reds (lips): only right next to skin, so a scarf keeps its red
    m = np.maximum(core, np.maximum(grow(0.03) & soft, grow(0.0125) & hard))
    cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is not None:          # fill enclosed reddish holes (an open, laughing mouth); eyes keep their own inks
        holes = np.zeros_like(m)
        for i, c in enumerate(cnts):
            par = hier[0][i][3]
            if par >= 0 and cv2.contourArea(c) < 0.3 * cv2.contourArea(cnts[par]):
                one = np.zeros_like(m)
                cv2.drawContours(one, [c], -1, 1, -1)
                inside = one.astype(bool) & ~m.astype(bool)
                if inside.sum() and redish[inside].mean() >= 0.4:
                    holes |= one
        m = np.maximum(m, holes)
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.5), core.astype(bool)


class PrintStyle:
    def __init__(self, inks, ink_line='#1E1A22', paper='#EDE3CF', period=10.0, angle=45.0, line_w=1.0,
                 dot_gain=1.0, shade_strength=0.85, grain=0.025, seed=0, dead=0.0, skin=None):
        self.inks = np.stack([hexc(h) for h in inks]).astype(np.float32)
        self.inks_lab = to_lab(self.inks[None])[0]
        # skin: print faces and hands on this ink (normally the paper) and let the screen carry their shading, the
        # way a manga page does; without it warm palettes pick orange / vermilion for skin and a laughing mouth
        # prints as a red blot
        self.skin = hexc(skin).astype(np.float32) if skin else None
        self.skin_l = float(to_lab(self.skin[None, None])[0, 0, 0]) / 100.0 if skin else None
        if skin:      # skin shading dots: the palette ink nearest a typical anime skin shadow, lifted toward the paper
            ref = to_lab(hexc('#C98B73')[None, None].astype(np.float32))[0, 0]
            near = self.inks[int(((self.inks_lab - ref) ** 2).sum(-1).argmin())]
            self.skin_shade = (0.5 * near + 0.5 * self.skin).astype(np.float32)
        self.line = hexc(ink_line)
        self.paper = hexc(paper)
        self.period, self.angle, self.line_w = period, np.deg2rad(angle), line_w
        self.dot_gain, self.shade, self.grain = dot_gain, shade_strength, grain
        self.dead = dead          # tone dead zone: small darkenings stay flat ink (dots only in real shadow)
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
        sm = None
        if self.skin is not None:
            sm, core = skin_mask(flat)
            # lit skin prints as plain paper: tone is measured against the frame's own lit-skin level, so only the
            # shadows carry dots
            ref = float(np.percentile(lum[core], 70)) if core.sum() > 200 else self.skin_l
            base = base * (1 - sm[..., None]) + self.skin[None, None] * sm[..., None]
            ink_l = ink_l * (1 - sm) + min(self.skin_l, ref + 0.03) * sm
        dark = np.clip(((ink_l - lum) - self.dead) * 2.2 * self.dot_gain, 0, 1)        # how much darker than the ink
        r = np.sqrt(dark) * 0.62                                           # dot radius in cell units (area ~ tone)
        g = self.grid(h, w)
        aa = 1.0 / self.period
        dot = np.clip((r - g) / aa + 0.5, 0, 1) * (r > 0.03)
        shade_col = base * 0.55 + self.line * 0.45
        if sm is not None:
            shade_col = shade_col * (1 - sm[..., None]) + self.skin_shade[None, None] * sm[..., None]
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

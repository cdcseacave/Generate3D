"""Procedurally painted images: children's drawings, wall prints, screens, labels.
Painted with numpy distance fields, saved as PNG under assets/generated."""
import math
import os
import random

import bpy
import numpy as np

from . import core as C


class Canvas:
    def __init__(self, w, h, bg=(1, 1, 1)):
        self.w, self.h = w, h
        self.px = np.empty((h, w, 3), dtype=np.float32)
        self.px[:] = bg
        ys, xs = np.mgrid[0:h, 0:w]
        self.x = xs.astype(np.float32) / w
        self.y = 1.0 - ys.astype(np.float32) / h   # y up, 0..1
        self.aspect = w / h

    def _blend(self, mask, color, alpha=1.0):
        a = np.clip(mask, 0, 1)[..., None] * alpha
        self.px = self.px * (1 - a) + np.array(color, dtype=np.float32) * a

    def rect(self, x0, y0, x1, y1, color, alpha=1.0):
        m = ((self.x >= x0) & (self.x <= x1) & (self.y >= y0) & (self.y <= y1)).astype(np.float32)
        self._blend(m, color, alpha)

    def disc(self, cx, cy, r, color, alpha=1.0, ring=None):
        d = np.hypot((self.x - cx) * self.aspect, self.y - cy)
        m = (d <= r).astype(np.float32) if ring is None else (np.abs(d - r) <= ring).astype(np.float32)
        self._blend(m, color, alpha)

    def line(self, x0, y0, x1, y1, width, color, alpha=1.0):
        ax, ay = (self.x - x0) * self.aspect, self.y - y0
        bx, by = (x1 - x0) * self.aspect, y1 - y0
        t = np.clip((ax * bx + ay * by) / max(bx * bx + by * by, 1e-9), 0, 1)
        d = np.hypot(ax - t * bx, ay - t * by)
        self._blend((d <= width).astype(np.float32), color, alpha)

    def gradient(self, c0, c1, vertical=True):
        t = (self.y if vertical else self.x)[..., None]
        self.px = np.array(c0, dtype=np.float32) * (1 - t) + np.array(c1, dtype=np.float32) * t

    def wobble(self, x0, y0, x1, y1, width, color, rnd, alpha=0.85, parts=5, amp=0.012):
        """A line drawn by an unsteady hand: jittered polyline, gone over twice."""
        for _ in range(2):
            px, py = x0 + rnd.uniform(-amp, amp) * 0.5, y0 + rnd.uniform(-amp, amp) * 0.5
            for k in range(1, parts + 1):
                t = k / parts
                nx = x0 + (x1 - x0) * t + rnd.uniform(-amp, amp)
                ny = y0 + (y1 - y0) * t + rnd.uniform(-amp, amp)
                self.line(px, py, nx, ny, width * rnd.uniform(0.7, 1.2), color, alpha * rnd.uniform(0.6, 1.0))
                px, py = nx, ny

    def hatch(self, x0, y0, x1, y1, color, rnd, n=26, width=0.006, inside=None):
        """Colour an area in with crayon strokes instead of a flat fill; strokes overshoot
        and leave gaps. `inside(x, y)` optionally limits them to a shape."""
        slope = rnd.uniform(0.5, 1.4) * rnd.choice((-1, 1))
        for k in range(n):
            t = (k + rnd.uniform(-0.3, 0.3)) / n
            cx = x0 + (x1 - x0) * t
            xa, xb = cx - (y1 - y0) * 0.5 / slope * 0.6, cx + (y1 - y0) * 0.5 / slope * 0.6
            ya, yb = y0 + rnd.uniform(-0.01, 0.02), y1 + rnd.uniform(-0.02, 0.01)
            xa, xb = min(max(xa, x0 - 0.01), x1 + 0.01), min(max(xb, x0 - 0.01), x1 + 0.01)
            if inside:
                steps = 8
                prev = None
                for j in range(steps + 1):
                    f = j / steps
                    p = (xa + (xb - xa) * f, ya + (yb - ya) * f)
                    if inside(*p):
                        if prev:
                            self.line(prev[0], prev[1], p[0], p[1], width, color, rnd.uniform(0.5, 0.9))
                        prev = p
                    else:
                        prev = None
            else:
                self.line(xa, ya, xb, yb, width * rnd.uniform(0.8, 1.3), color, rnd.uniform(0.5, 0.9))

    def soften(self, grain=0.05, seed=1, tint=(1.0, 0.985, 0.955)):
        """Printed-on-paper look: slightly soft edges, paper tooth, warm stock."""
        p = self.px
        blur = (p + np.roll(p, 1, 0) + np.roll(p, -1, 0) + np.roll(p, 1, 1) + np.roll(p, -1, 1)) / 5.0
        g = np.random.default_rng(seed).random((self.h, self.w, 1), dtype=np.float32)
        self.px = blur * (1.0 - grain + grain * g) * np.array(tint, dtype=np.float32)

    def crayon(self, rnd):
        """Break flat fills up so they read as wax crayon / paper grain."""
        n = np.random.default_rng(rnd.randint(0, 9999)).random((self.h, self.w, 1), dtype=np.float32)
        white = (self.px.min(axis=2, keepdims=True) > 0.97)
        self.px = np.where(white, self.px, self.px * (0.82 + 0.18 * n) + (n > 0.9) * 0.12)

    def save(self, name):
        os.makedirs(C.GEN, exist_ok=True)
        path = os.path.join(C.GEN, name + ".png")
        img = bpy.data.images.new("gen_" + name, self.w, self.h, alpha=False)
        rgba = np.concatenate([np.clip(self.px[::-1], 0, 1), np.ones((self.h, self.w, 1), np.float32)], axis=2)
        img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)
        return path


CRAYONS = [(0.86, 0.12, 0.1), (0.1, 0.35, 0.8), (0.1, 0.6, 0.2), (0.98, 0.78, 0.05), (0.95, 0.45, 0.05),
           (0.55, 0.2, 0.65), (0.35, 0.2, 0.1), (0.95, 0.4, 0.6)]


def kid_drawing(i):
    """Returns a material with a child's crayon drawing (variant i): wobbly outlines
    and scribbled-in colour on slightly creased paper."""
    name = "kid_drawing_{}".format(i)
    if name in C._MATS:
        return C._MATS[name]
    rnd = random.Random(100 + i)
    cv = Canvas(384, 272, (0.975, 0.97, 0.95))
    col = lambda: rnd.choice(CRAYONS)  # noqa: E731
    W = lambda *a, **k: cv.wobble(*a, rnd=rnd, **k)  # noqa: E731
    kind = i % 4
    if kind == 0:   # house, sun, family
        cv.hatch(0.02, 0.03, 0.98, 0.17, (0.25, 0.62, 0.25), rnd, n=46)
        cv.hatch(0.76, 0.7, 0.93, 0.9, (0.98, 0.78, 0.05), rnd, n=14, inside=lambda x, y: (x - 0.845) ** 2 * 2 + (y - 0.8) ** 2 < 0.0095)
        for k in range(9):
            a = k * math.pi * 2 / 9 + 0.2
            W(0.845 + 0.075 * math.cos(a), 0.8 + 0.11 * math.sin(a), 0.845 + 0.12 * math.cos(a), 0.8 + 0.17 * math.sin(a),
              0.005, (0.96, 0.66, 0.05), parts=2, amp=0.006)
        cv.hatch(0.13, 0.17, 0.41, 0.49, (0.82, 0.2, 0.16), rnd, n=24)
        for (xa, ya, xb, yb) in ((0.12, 0.16, 0.12, 0.5), (0.42, 0.16, 0.42, 0.5), (0.12, 0.5, 0.42, 0.5),
                                 (0.09, 0.5, 0.27, 0.73), (0.27, 0.73, 0.46, 0.49)):
            W(xa, ya, xb, yb, 0.006, (0.3, 0.18, 0.1))
        cv.hatch(0.23, 0.17, 0.31, 0.33, (0.32, 0.2, 0.1), rnd, n=9)
        W(0.33, 0.36, 0.39, 0.36, 0.005, (0.2, 0.4, 0.8), parts=2)
        W(0.33, 0.44, 0.39, 0.44, 0.005, (0.2, 0.4, 0.8), parts=2)
        W(0.33, 0.36, 0.33, 0.44, 0.005, (0.2, 0.4, 0.8), parts=2)
        W(0.39, 0.36, 0.39, 0.44, 0.005, (0.2, 0.4, 0.8), parts=2)
        for k, (px, hh) in enumerate(((0.57, 0.3), (0.69, 0.34), (0.79, 0.2))):
            c = CRAYONS[(k * 3 + 1) % len(CRAYONS)]
            cv.disc(px + rnd.uniform(-0.005, 0.005), 0.16 + hh, 0.034, c, 0.85, ring=0.006)
            W(px, 0.16 + hh - 0.045, px + rnd.uniform(-0.01, 0.01), 0.21, 0.005, c, parts=3)
            W(px - 0.045, 0.16 + hh - 0.09, px + 0.045, 0.16 + hh - 0.1, 0.005, c, parts=2)
            W(px, 0.21, px - 0.035, 0.15, 0.005, c, parts=2)
            W(px, 0.21, px + 0.035, 0.15, 0.005, c, parts=2)
    elif kind == 1:  # scribbles
        for _ in range(6):
            c = col()
            x, y = rnd.uniform(0.15, 0.85), rnd.uniform(0.15, 0.85)
            for _ in range(24):
                nx = min(0.95, max(0.05, x + rnd.uniform(-0.17, 0.17)))
                ny = min(0.95, max(0.05, y + rnd.uniform(-0.22, 0.22)))
                cv.line(x, y, nx, ny, rnd.uniform(0.004, 0.007), c, rnd.uniform(0.55, 0.9))
                x, y = nx, ny
    elif kind == 2:  # rainbow + clouds
        for k, c in enumerate(((0.86, 0.12, 0.1), (0.95, 0.45, 0.05), (0.98, 0.78, 0.05), (0.1, 0.6, 0.2),
                               (0.1, 0.35, 0.8), (0.55, 0.2, 0.65))):
            r = 0.6 - k * 0.055
            for rep_ in range(3):
                pa = None
                for j in range(15):
                    a = math.pi * (0.04 + 0.92 * j / 14)
                    rr = r + rnd.uniform(-0.012, 0.012) + (rep_ - 1) * 0.012
                    p = (0.5 + rr * math.cos(a) / cv.aspect, 0.12 + rr * math.sin(a))
                    if pa:
                        cv.line(pa[0], pa[1], p[0], p[1], 0.008, c, rnd.uniform(0.5, 0.85))
                    pa = p
        for cx in (0.15, 0.85):
            for dx, dy, r in ((-0.05, 0, 0.07), (0.04, 0.02, 0.085), (0.11, -0.005, 0.06)):
                cv.disc(cx + dx * 0.7, 0.15 + dy, r, (0.5, 0.72, 0.93), 0.8, ring=0.006)
    else:            # flowers
        cv.hatch(0.02, 0.02, 0.98, 0.13, (0.3, 0.68, 0.25), rnd, n=44)
        for k in range(4):
            fx, fy = 0.15 + k * 0.23 + rnd.uniform(-0.02, 0.02), rnd.uniform(0.45, 0.7)
            W(fx, 0.1, fx + rnd.uniform(-0.02, 0.02), fy, 0.006, (0.1, 0.5, 0.15), parts=4)
            c = col()
            for p in range(6):
                a = p * math.pi / 3 + rnd.uniform(-0.2, 0.2)
                cv.disc(fx + 0.045 * math.cos(a), fy + 0.06 * math.sin(a), rnd.uniform(0.035, 0.048), c, 0.8, ring=0.007)
            cv.hatch(fx - 0.03, fy - 0.04, fx + 0.03, fy + 0.04, (0.97, 0.78, 0.05), rnd, n=7)
    cv.crayon(rnd)
    cv.soften(0.04, 100 + i, (1.0, 0.99, 0.97))
    return C.image_mat(name, cv.save(name), rough=0.8)


PRINT_PALETTES = [
    ((0.93, 0.9, 0.84), [(0.76, 0.42, 0.28), (0.85, 0.66, 0.42), (0.2, 0.27, 0.3), (0.55, 0.6, 0.5)]),
    ((0.9, 0.9, 0.87), [(0.15, 0.25, 0.4), (0.82, 0.55, 0.3), (0.6, 0.72, 0.78), (0.92, 0.8, 0.6)]),
    ((0.94, 0.92, 0.88), [(0.3, 0.4, 0.33), (0.8, 0.7, 0.55), (0.6, 0.35, 0.3), (0.15, 0.15, 0.15)]),
]


def wall_print(i):
    """Abstract mid-century style print; eight distinct compositions/palettes."""
    name = "wall_print_{}".format(i)
    if name in C._MATS:
        return C._MATS[name]
    rnd = random.Random(200 + i)
    bg, pal = PRINT_PALETTES[(i // 2) % len(PRINT_PALETTES)]
    pal = pal[i % 4:] + pal[:i % 4]
    cv = Canvas(300, 400, bg)
    kind = i % 8
    if kind == 0:
        for k in range(4):
            cv.disc(0.5, 0.2, 0.52 - k * 0.1, pal[k % 4], ring=0.04)
        cv.rect(0, 0, 1, 0.2, bg)
        cv.disc(0.68, 0.78, 0.09, pal[0])
    elif kind == 1:
        cv.rect(0.12, 0.1, 0.55, 0.62, pal[0])
        cv.disc(0.62, 0.62, 0.2, pal[1])
        cv.rect(0.45, 0.2, 0.86, 0.4, pal[2], 0.9)
        cv.line(0.1, 0.86, 0.9, 0.86, 0.004, pal[3])
    elif kind == 2:
        for k in range(5):
            cv.disc(rnd.uniform(0.3, 0.7), 0.12 + k * 0.16, rnd.uniform(0.1, 0.2), pal[k % 4], 0.92)
        cv.line(0.5, 0.05, 0.5, 0.95, 0.003, pal[3])
    elif kind == 3:      # layered hills and a sun
        cv.disc(0.66, 0.72, 0.11, pal[1])
        for k in range(4):
            base = 0.52 - k * 0.12
            for x in range(0, 31):
                xx = x / 30
                yy = base + 0.07 * math.sin(xx * 5 + k * 1.7) + 0.03 * math.sin(xx * 11 + k)
                cv.rect(xx - 0.02, 0.0, xx + 0.02, yy, pal[(k + 2) % 4])
    elif kind == 4:      # botanical stem
        cv.line(0.5, 0.08, 0.52, 0.9, 0.006, pal[2])
        for k in range(7):
            y = 0.2 + k * 0.1
            s_ = 1 if k % 2 else -1
            cv.line(0.51, y, 0.51 + s_ * 0.2, y + 0.09, 0.022, pal[k % 2])
    elif kind == 5:      # stacked stones
        y = 0.12
        for k in range(5):
            r = rnd.uniform(0.09, 0.17)
            cv.disc(0.5 + rnd.uniform(-0.04, 0.04), y + r * 0.6, r, pal[k % 4])
            y += r * 1.15
    elif kind == 6:      # grid of soft squares
        for r in range(4):
            for c in range(3):
                cv.rect(0.14 + c * 0.25, 0.12 + r * 0.2, 0.34 + c * 0.25, 0.27 + r * 0.2, pal[(r + c) % 4], 0.9)
    else:                # line drawing arcs
        for k in range(9):
            cv.disc(0.5, 0.5, 0.06 + k * 0.035, pal[k % 4], ring=0.005)
        cv.rect(0.5, 0, 1, 1, bg, 0.75)
    cv.soften(0.07, 200 + i)
    return C.image_mat(name, cv.save(name), rough=0.38, wear=0.1)


def screen(kind):
    """Emissive display content: 'desktop' (document window) or 'code' (dark editor)."""
    name = "screen_" + kind
    if name in C._MATS:
        return C._MATS[name]
    rnd = random.Random(5 if kind == "code" else 9)
    cv = Canvas(480, 300)
    if kind == "code":
        cv.rect(0, 0, 1, 1, (0.07, 0.08, 0.1))
        cv.rect(0, 0, 0.16, 1, (0.1, 0.11, 0.14))
        cv.rect(0, 0.95, 1, 1, (0.14, 0.15, 0.19))
        cols = [(0.5, 0.75, 0.95), (0.85, 0.6, 0.85), (0.6, 0.85, 0.55), (0.9, 0.8, 0.5), (0.75, 0.77, 0.8)]
        for r in range(26):
            y = 0.91 - r * 0.033
            x = 0.19 + rnd.choice((0, 0.02, 0.04, 0.04, 0.06))
            for _ in range(rnd.randint(1, 4)):
                w = rnd.uniform(0.03, 0.14)
                if x + w > 0.95:
                    break
                cv.rect(x, y, x + w, y + 0.012, rnd.choice(cols))
                x += w + 0.012
        for r in range(12):
            cv.rect(0.02, 0.9 - r * 0.045, 0.02 + rnd.uniform(0.05, 0.11), 0.912 - r * 0.045, (0.55, 0.57, 0.62))
    else:
        cv.gradient((0.16, 0.3, 0.5), (0.55, 0.42, 0.6))
        cv.rect(0.1, 0.12, 0.72, 0.92, (0.97, 0.97, 0.97))
        cv.rect(0.1, 0.86, 0.72, 0.92, (0.85, 0.86, 0.88))
        for r in range(16):
            y = 0.8 - r * 0.04
            cv.rect(0.14, y, 0.14 + rnd.uniform(0.3, 0.54), y + 0.012, (0.3, 0.3, 0.33))
        cv.rect(0.76, 0.5, 0.96, 0.9, (0.95, 0.95, 0.96))
        cv.rect(0.78, 0.55, 0.94, 0.72, (0.3, 0.55, 0.8))
        cv.rect(0, 0, 1, 0.06, (0.1, 0.1, 0.12))
        for k in range(7):
            cv.rect(0.3 + k * 0.06, 0.012, 0.335 + k * 0.06, 0.048, rnd.choice(CRAYONS))
    return C.image_mat(name, cv.save(name), rough=0.1, emit=0.75, wear=0.12)


def calendar():
    name = "calendar"
    if name in C._MATS:
        return C._MATS[name]
    rnd = random.Random(3)
    cv = Canvas(300, 400, (0.98, 0.98, 0.97))
    cv.gradient((0.75, 0.55, 0.35), (0.35, 0.55, 0.7))
    cv.rect(0, 0, 1, 0.55, (0.98, 0.98, 0.97))
    cv.rect(0, 0.47, 1, 0.55, (0.75, 0.15, 0.15))
    for r in range(5):
        for c in range(7):
            x, y = 0.07 + c * 0.125, 0.39 - r * 0.085
            cv.rect(x, y, x + 0.05, y + 0.02, (0.25, 0.25, 0.28) if c < 5 else (0.75, 0.2, 0.2))
            if rnd.random() < 0.18:
                cv.disc(x + 0.025, y + 0.012, 0.035, (0.1, 0.35, 0.8), ring=0.004)
    return C.image_mat(name, cv.save(name), rough=0.6)


def label(i):
    """Flat packaging artwork for boxes (cereal, detergent, games)."""
    name = "label_{}".format(i)
    if name in C._MATS:
        return C._MATS[name]
    rnd = random.Random(300 + i)
    base = [(0.85, 0.2, 0.15), (0.1, 0.4, 0.7), (0.95, 0.75, 0.1), (0.2, 0.6, 0.35), (0.9, 0.5, 0.1),
            (0.45, 0.25, 0.6)][i % 6]
    cv = Canvas(200, 280, base)
    cv.disc(0.5, 0.45, 0.3, (0.98, 0.95, 0.85))
    cv.disc(0.5, 0.45, 0.2, rnd.choice(CRAYONS), 0.9)
    cv.rect(0.1, 0.8, 0.9, 0.92, (0.98, 0.98, 0.95))
    cv.rect(0.16, 0.84, 0.84, 0.88, (0.15, 0.15, 0.2))
    cv.rect(0.2, 0.06, 0.8, 0.1, (0.98, 0.98, 0.95))
    return C.image_mat(name, cv.save(name), rough=0.45)


def rug(kind, aspect=0.7, repeats=(20, 28)):
    """Woven rug artwork. kind: berber (cream with charcoal diamonds) | stripes | kilim."""
    name = "rug_" + kind
    if name in C._MATS:
        return C._MATS[name]
    rnd = random.Random(40 + len(kind))
    w = 560
    cv = Canvas(w, int(w / aspect), (0.80, 0.77, 0.70))
    if kind == "berber":
        ink = (0.17, 0.16, 0.15)
        px, py = 0.25, 0.25 * aspect * 1.25
        for i in range(-1, 6):
            for j in range(-1, int(1 / py) + 2):
                cx, cy = i * px + (px / 2 if j % 2 else 0), j * py / 2
                jx, jy = rnd.uniform(-0.012, 0.012), rnd.uniform(-0.008, 0.008)
                pts = [(cx - px / 2, cy), (cx + jx, cy + py / 2 + jy), (cx + px / 2, cy), (cx + jx, cy - py / 2 - jy)]
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    cv.line(a[0], a[1], b[0], b[1], 0.0045, ink, 0.85)
    elif kind == "stripes":
        cols = [(0.74, 0.70, 0.62), (0.56, 0.60, 0.58), (0.80, 0.77, 0.70), (0.66, 0.52, 0.42)]
        y = 0.0
        k = 0
        while y < 1.0:
            h = rnd.choice((0.03, 0.05, 0.08, 0.012))
            cv.rect(0, y, 1, y + h, cols[k % len(cols)])
            y += h
            k += rnd.choice((1, 1, 2))
    else:
        cv.rect(0, 0, 1, 1, (0.45, 0.2, 0.17))
        cv.rect(0.06, 0.04, 0.94, 0.96, (0.78, 0.72, 0.6))
        cv.rect(0.1, 0.07, 0.9, 0.93, (0.25, 0.3, 0.38))
        for j in range(7):
            cy = 0.14 + j * 0.12
            for a, b in (((0.5, cy + 0.05), (0.75, cy)), ((0.75, cy), (0.5, cy - 0.05)), ((0.5, cy - 0.05), (0.25, cy)),
                         ((0.25, cy), (0.5, cy + 0.05))):
                cv.line(a[0], a[1], b[0], b[1], 0.012, (0.78, 0.72, 0.6))
            cv.disc(0.5, cy, 0.03, (0.62, 0.3, 0.22))
    rg = np.random.default_rng(7)
    g = rg.random((cv.h, cv.w, 1), dtype=np.float32)
    rows = rg.random((cv.h // 6 + 2, 1, 1), dtype=np.float32).repeat(6, axis=0)[: cv.h]   # abrash: uneven dye lots
    cv.px = (cv.px * 0.85 + 0.15 * cv.px.mean(axis=2, keepdims=True)) * (0.86 + 0.1 * g + 0.1 * rows)
    for _ in range(3):      # yarn edges are fuzzy, not laser-cut
        p = cv.px
        cv.px = (p * 2 + np.roll(p, 1, 0) + np.roll(p, -1, 0) + np.roll(p, 1, 1) + np.roll(p, -1, 1)) / 6.0
    return C.image_mat(name, cv.save(name), rough=0.95, sheen=0.3, weave=("wool_boucle", repeats[0], repeats[1], 3.0))


def creases():
    """Height map of the small random creases every used textile carries (path to a PNG)."""
    path = os.path.join(C.GEN, "creases.png")
    if os.path.exists(path) and "creases" in _DONE:
        return path
    rnd = random.Random(77)
    cv = Canvas(640, 640, (0.5, 0.5, 0.5))
    for _ in range(260):
        x, y = rnd.uniform(-0.1, 1.1), rnd.uniform(-0.1, 1.1)
        a = rnd.uniform(0, math.pi)
        ln = rnd.uniform(0.06, 0.4)
        tone = rnd.choice((0.0, 1.0))
        cv.line(x, y, x + ln * math.cos(a), y + ln * math.sin(a), rnd.uniform(0.003, 0.012), (tone, tone, tone), rnd.uniform(0.12, 0.38))
    for _ in range(7):
        p = cv.px
        cv.px = (p * 2 + np.roll(p, 2, 0) + np.roll(p, -2, 0) + np.roll(p, 2, 1) + np.roll(p, -2, 1)) / 6.0
    _DONE.add("creases")
    return cv.save("creases")


_DONE = set()

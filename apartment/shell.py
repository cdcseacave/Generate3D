"""Architecture: floor plan, walls with openings, floors, ceiling, doors, windows,
baseboards, radiators, switches."""
import math

from . import core as C

H = 2.7            # ceiling height
TE, TI = 0.30, 0.12  # exterior / interior wall thickness
X1, Y1 = 10.0, 10.6
YH0, YH1 = 4.6, 6.6  # hallway band
XLK = 6.2            # living | kitchen
XBO, XOB = 4.2, 7.4  # bedroom | office | bath

# room -> rectangle on wall centre lines (x0, y0, x1, y1)
ROOMS = {
    "living": (0.0, 0.0, XLK, YH0),
    "kitchen": (XLK, 0.0, X1, YH0),
    "hall": (0.0, YH0, X1, YH1),
    "bedroom": (0.0, YH1, XBO, Y1),
    "office": (XBO, YH1, XOB, Y1),
    "bath": (XOB, YH1, X1, Y1),
}


class Opening:
    def __init__(self, s0, s1, sill, head, kind, **opts):
        self.s0, self.s1, self.sill, self.head, self.kind, self.opts = s0, s1, sill, head, kind, opts


class Wall:
    def __init__(self, name, axis, c, a0, a1, t, openings=()):
        self.name, self.axis, self.c, self.a0, self.a1, self.t = name, axis, c, a0, a1, t
        self.openings = list(openings)


def win(s0, s1, sill=0.85, head=2.3, **o):
    return Opening(s0, s1, sill, head, "window", **o)


def door(s0, s1, **o):
    return Opening(s0, s1, 0.0, 2.07, "door", **o)


def arch(s0, s1):
    return Opening(s0, s1, 0.0, 2.2, "arch")


WALLS = [
    Wall("S", "x", 0.0, -TE / 2, X1 + TE / 2, TE, [win(1.6, 4.4, 0.5, 2.4, out=-1), win(7.3, 8.9, 1.08, 2.3, out=-1)]),
    Wall("N", "x", Y1, -TE / 2, X1 + TE / 2, TE, [win(1.2, 3.0, out=1), win(5.0, 6.6, out=1),
                                                    win(8.45, 9.15, 1.4, 2.2, out=1)]),
    Wall("W", "y", 0.0, TE / 2, Y1 - TE / 2, TE, [door(5.15, 6.1, hinge="s1", side=1, angle=0, style="entrance")]),
    Wall("E", "y", X1, TE / 2, Y1 - TE / 2, TE, [win(5.1, 6.1, out=1)]),
    Wall("HS", "x", YH0, TE / 2, X1 - TE / 2, TI, [arch(2.0, 3.4), arch(7.3, 8.3)]),
    Wall("HN", "x", YH1, TE / 2, X1 - TE / 2, TI, [door(2.6, 3.5, hinge="s1", side=1, angle=84),
                                                    door(5.0, 5.9, hinge="s1", side=1, angle=76),
                                                    door(8.0, 8.8, hinge="s0", side=1, angle=80)]),
    Wall("LK", "y", XLK, TE / 2, YH0 - TI / 2, TI),
    Wall("BO", "y", XBO, YH1 + TI / 2, Y1 - TE / 2, TI),
    Wall("OB", "y", XOB, YH1 + TI / 2, Y1 - TE / 2, TI),
]


def _wall_at(axis, c):
    for w in WALLS:
        if w.axis == axis and abs(w.c - c) < 1e-6:
            return w
    raise KeyError((axis, c))


def inner(room):
    """Clear interior bounds (x0, y0, x1, y1) between wall faces."""
    x0, y0, x1, y1 = ROOMS[room]
    return (x0 + _wall_at("y", x0).t / 2, y0 + _wall_at("x", y0).t / 2,
            x1 - _wall_at("y", x1).t / 2, y1 - _wall_at("x", y1).t / 2)


def P(axis, a, c, z):
    return (a, c, z) if axis == "x" else (c, a, z)


def strip_items(axis, c_lo, c_hi, a0, a1, z0, z1, openings, kinds=None):
    """Boxes filling a wall-like strip, leaving the openings free."""
    items = []
    cur = a0

    def seg(s0, s1, za, zb):
        if s1 - s0 > 1e-4 and zb - za > 1e-4:
            items.append((P(axis, s0, c_lo, za), P(axis, s1, c_hi, zb)))

    for o in sorted(openings, key=lambda o: o.s0):
        if kinds and o.kind not in kinds:
            continue
        s0, s1 = max(o.s0, a0), min(o.s1, a1)
        if s1 <= s0:
            continue
        seg(cur, s0, z0, z1)
        seg(s0, s1, max(o.head, z0), z1)
        seg(s0, s1, z0, min(o.sill, z1))
        cur = s1
    seg(cur, a1, z0, z1)
    return items


def room_sides(room):
    """Yield (axis, face coordinate, into-room sign, a0, a1, wall) for the 4 sides."""
    x0, y0, x1, y1 = ROOMS[room]
    ix0, iy0, ix1, iy1 = inner(room)
    yield "x", iy0, 1, ix0, ix1, _wall_at("x", y0)
    yield "x", iy1, -1, ix0, ix1, _wall_at("x", y1)
    yield "y", ix0, 1, iy0, iy1, _wall_at("y", x0)
    yield "y", ix1, -1, iy0, iy1, _wall_at("y", x1)


# ----------------------------------------------------------------- build ---
def build_structure(M):
    """Walls, per-room wall skins, floors, ceiling, baseboards."""
    C.collection("Structure", C.collection("Architecture"))
    for w in WALLS:
        items = strip_items(w.axis, w.c - w.t / 2, w.c + w.t / 2, w.a0, w.a1, 0.0, H, w.openings)
        C.boxes("Wall_" + w.name, items, M["wall_core"])
    for room, (x0, y0, x1, y1) in ROOMS.items():
        C.boxes("Floor_" + room, [((x0, y0, -0.05), (x1, y1, 0.0))], M["floor_" + room])
        skin, base, cornice = [], [], []
        for axis, face, sgn, a0, a1, wall in room_sides(room):
            cornice += strip_items(axis, face + sgn * 0.004, face + sgn * 0.064, a0, a1, H - 0.06, H, [])
            skin += strip_items(axis, face, face + sgn * 0.004, a0, a1, 0.0, H, wall.openings)
            base += strip_items(axis, face + sgn * 0.004, face + sgn * 0.018, a0, a1, 0.0, 0.075,
                                [o for o in wall.openings if o.kind != "window"])
        C.boxes("Skin_" + room, skin, M["wall_" + room])
        if room != "bath":
            C.boxes("Baseboard_" + room, base, M["trim"])
        C.add_bevel(C.boxes("Cornice_" + room, cornice, M["trim"]), 0.022, 3)
    ceil = C.boxes("Ceiling", [((-TE / 2, -TE / 2, H), (X1 + TE / 2, Y1 + TE / 2, H + 0.2))], M["ceiling"])
    ceil["is_ceiling"] = True
    # thresholds between different floorings
    thr = []
    for w in WALLS:
        for o in w.openings:
            if o.kind in ("door", "arch"):
                thr.append((P(w.axis, o.s0, w.c - 0.03, 0.0), P(w.axis, o.s1, w.c + 0.03, 0.004)))
    C.boxes("Thresholds", thr, M["steel"])


def build_openings(M):
    C.collection("Doors & Windows", C.collection("Architecture"))
    for w in WALLS:
        for i, o in enumerate(w.openings):
            name = "{}_{}{}".format(w.name, o.kind, i)
            if o.kind == "window":
                _window(name, w, o, M)
            else:
                _door(name, w, o, M)


def _door(name, w, o, M):
    ax, c, t = w.axis, w.c, w.t
    jt = 0.025
    lo, hi = c - t / 2 - 0.012, c + t / 2 + 0.012
    items = [  # jamb lining
        (P(ax, o.s0, lo, 0), P(ax, o.s0 + jt, hi, o.head)),
        (P(ax, o.s1 - jt, lo, 0), P(ax, o.s1, hi, o.head)),
        (P(ax, o.s0, lo, o.head - jt), P(ax, o.s1, hi, o.head)),
    ]
    cw = 0.07  # casing on both faces
    for f0, f1 in ((lo - 0.006, lo + 0.006), (hi - 0.006, hi + 0.006)):
        items += [(P(ax, o.s0 - cw, f0, 0), P(ax, o.s0, f1, o.head + cw)),
                  (P(ax, o.s1, f0, 0), P(ax, o.s1 + cw, f1, o.head + cw)),
                  (P(ax, o.s0, f0, o.head), P(ax, o.s1, f1, o.head + cw))]
    C.boxes(name + "_frame", items, M["trim"])
    if o.kind != "door":
        return
    if o.opts.get("style") == "entrance":      # threshold seal and a landing wall beyond: no daylight leaks under the door
        C.boxes(name + "_seal", [(P(ax, o.s0, c - 0.03, 0.0), P(ax, o.s1, c + 0.03, 0.014)),
                                 (P(ax, o.s0 - 0.3, c - t / 2 - 0.5, -0.05), P(ax, o.s1 + 0.3, c - t / 2 - 0.45, H))],
                C.mat("DoorSeal", "#1a1a1a", rough=0.8))
    side = o.opts.get("side", 1)
    hinge = o.opts.get("hinge", "s0")
    ang = math.radians(o.opts.get("angle", 0))
    entrance = o.opts.get("style") == "entrance"
    lw, lh, lt = (o.s1 - o.s0) - 2 * jt - 0.006, o.head - jt - 0.01, 0.042
    hp = o.s0 + jt + 0.003 if hinge == "s0" else o.s1 - jt - 0.003
    base = {("x", "s0"): 0.0, ("x", "s1"): math.pi, ("y", "s0"): math.pi / 2, ("y", "s1"): -math.pi / 2}[(ax, hinge)]
    # positive rotation direction that swings the leaf towards `side`
    turn = side if (ax == "x") == (hinge == "s0") else -side
    rot = base + turn * ang
    pos = P(ax, hp, c + side * (t / 2 - lt / 2), 0.008)
    leaf_mat = M["door_entrance"] if entrance else M["door"]
    leaf = C.box(name + "_leaf", (lw, lt - 0.022, lh), pos, leaf_mat, rot=rot, bevel=0.002, anchor=(-1, 0, -1))
    # frame-and-panel faces: stiles and rails stand 7 mm proud of two recessed panels
    parts = []
    sw, rails = 0.105, []
    for s in (-1, 1):
        ya, yb = s * (lt / 2 - 0.011), s * lt / 2
        rails += [((0, ya, 0), (sw, yb, lh)), ((lw - sw, ya, 0), (lw, yb, lh)),
                  ((sw, ya, 0), (lw - sw, yb, 0.2)), ((sw, ya, lh - sw), (lw - sw, yb, lh)),
                  ((sw, ya, 0.93), (lw - sw, yb, 1.07))]
        if entrance:
            rails.append(((sw, ya, 1.52), (lw - sw, yb, 1.6)))
    pf = C.boxes(name + "_panels", rails, leaf_mat)
    C.add_bevel(pf, 0.004, 3)
    parts.append(pf)
    parts.append(C.box(name + "_latch", (0.003, 0.022, 0.16), (lw, 0, 0.94), M["steel"], anchor=(1, 0, -1)))
    for s in (-1, 1):
        y = s * (lt / 2)
        parts.append(C.cyl(name + "_rose", 0.026, 0.008, (lw - 0.065, y, 1.02), M["steel"],
                           rot=(math.radians(-90 * s), 0, 0)))
        parts.append(C.cyl(name + "_neck", 0.009, 0.05, (lw - 0.065, y, 1.02), M["steel"],
                           rot=(math.radians(-90 * s), 0, 0)))
        parts.append(C.box(name + "_lever", (0.125, 0.012, 0.02), (lw - 0.12, y + s * 0.05, 1.02), M["steel"],
                           bevel=0.004, anchor=(0, 0, 0)))
        if entrance and s == side:
            parts.append(C.box(name + "_lock", (0.04, 0.012, 0.09), (lw - 0.065, y + s * 0.006, 1.2), M["steel"],
                               bevel=0.003, anchor=(0, 0, 0)))
            parts.append(C.cyl(name + "_peep", 0.012, 0.01, (lw / 2, y, 1.5), M["steel"],
                               rot=(math.radians(-90 * s), 0, 0)))
    # hinge knuckles on the side the door swings towards
    for hz in (0.22, 1.0, lh - 0.22):
        parts.append(C.cyl(name + "_hinge", 0.011, 0.11, (-0.004, turn * (lt / 2 + 0.006), hz - 0.055), M["steel"], segs=14, bevel=0.002))
    for p in parts:
        p.parent = leaf


def _window(name, w, o, M):
    ax, c, t = w.axis, w.c, w.t
    out = o.opts.get("out", 1)
    fc = c + out * (t / 2 - 0.10)          # frame centre plane
    fd = 0.035                              # half frame depth
    pw = 0.055                              # frame profile width
    width = o.s1 - o.s0
    frame = [
        (P(ax, o.s0, fc - fd, o.sill), P(ax, o.s0 + pw, fc + fd, o.head)),
        (P(ax, o.s1 - pw, fc - fd, o.sill), P(ax, o.s1, fc + fd, o.head)),
        (P(ax, o.s0, fc - fd, o.sill), P(ax, o.s1, fc + fd, o.sill + pw)),
        (P(ax, o.s0, fc - fd, o.head - pw), P(ax, o.s1, fc + fd, o.head)),
    ]
    n = 1 if width < 1.0 else (2 if width < 2.0 else 3)
    a0, a1 = o.s0 + pw, o.s1 - pw
    z0, z1 = o.sill + pw, o.head - pw
    sw = (a1 - a0) / n
    sp, sd = 0.05, 0.028
    sc = fc - out * 0.012
    glass = []
    handles = []
    for i in range(n):
        b0, b1 = a0 + i * sw, a0 + (i + 1) * sw
        frame += [
            (P(ax, b0, sc - sd, z0), P(ax, b0 + sp, sc + sd, z1)),
            (P(ax, b1 - sp, sc - sd, z0), P(ax, b1, sc + sd, z1)),
            (P(ax, b0, sc - sd, z0), P(ax, b1, sc + sd, z0 + sp)),
            (P(ax, b0, sc - sd, z1 - sp), P(ax, b1, sc + sd, z1)),
        ]
        glass.append((P(ax, b0 + sp - 0.005, sc - 0.008, z0 + sp - 0.005),
                      P(ax, b1 - sp + 0.005, sc + 0.008, z1 - sp + 0.005)))
        hx = b1 - sp / 2 if i % 2 == 0 else b0 + sp / 2
        hz = (z0 + z1) / 2
        handles.append((P(ax, hx - 0.009, sc - out * sd, hz - 0.03),
                        P(ax, hx + 0.009, sc - out * (sd + 0.008), hz + 0.03)))
        handles.append((P(ax, hx - 0.006, sc - out * (sd + 0.008), hz - 0.105),
                        P(ax, hx + 0.006, sc - out * (sd + 0.022), hz + 0.008)))
    C.boxes(name + "_frame", frame, M["pvc"])
    C.boxes(name + "_glass", glass, M["glass_frosted"] if o.opts.get("frosted") else M["glass"])
    C.add_bevel(C.boxes(name + "_handles", handles, M["pvc"]), 0.003)
    # interior sill board
    inner_face = c - out * t / 2
    nose = inner_face - out * 0.04
    sill = [(P(ax, o.s0, fc - out * fd, o.sill - 0.03), P(ax, o.s1, inner_face, o.sill + 0.004)),
            (P(ax, o.s0 - 0.05, inner_face, o.sill - 0.03), P(ax, o.s1 + 0.05, nose, o.sill + 0.004))]
    C.boxes(name + "_sill", sill, M["sill"])
    # exterior ledge so the window does not open onto a razor-thin void
    outer_face = c + out * t / 2
    C.boxes(name + "_ledge", [(P(ax, o.s0 - 0.05, fc + out * fd, o.sill - 0.04),
                               P(ax, o.s1 + 0.05, outer_face + out * 0.05, o.sill))], M["ledge"])


# ---------------------------------------------------------------- extras ---
def radiator(name, axis, face, a_mid, width, sgn, M, height=0.58, z=0.14):
    """Panel radiator against a wall face (`sgn` points into the room)."""
    c0, c1 = face + sgn * 0.035, face + sgn * 0.115
    a0, a1 = a_mid - width / 2, a_mid + width / 2
    items = [(P(axis, a0, c0, z), P(axis, a1, c1 - sgn * 0.012, z + height)),
             (P(axis, a0, c0, z + height - 0.004), P(axis, a1, c1, z + height + 0.008))]
    for ab in (a0 + 0.12, a1 - 0.15):       # wall brackets
        items.append((P(axis, ab, face, z + height - 0.14), P(axis, ab + 0.03, c0, z + height - 0.11)))
    n = int(width / 0.05)
    for i in range(n):
        s = a0 + 0.012 + i * (width - 0.024) / n
        items.append((P(axis, s, c1 - sgn * 0.012, z + 0.03), P(axis, s + 0.028, c1, z + height - 0.03)))
    r = C.boxes(name, items, M["radiator"])
    C.add_bevel(r, 0.004)
    v0 = a1 + 0.035
    for k, vv in enumerate((a1 + 0.05, a0 - 0.05)):          # supply and return pipes up from the floor at both ends
        end = a1 if k == 0 else a0
        C.pipe("{}_pipe{}".format(name, k), [P(axis, vv, c0 + sgn * 0.045, 0.0), P(axis, vv, c0 + sgn * 0.045, z + 0.07),
                                             P(axis, end, c0 + sgn * 0.045, z + 0.07)], 0.011, M["steel"], smooth=False)
        C.cyl("{}_rose{}".format(name, k), 0.022, 0.006, P(axis, vv, c0 + sgn * 0.045, 0.0), M["trim"], segs=18)
    C.cyl(name + "_valve", 0.026, 0.085, P(axis, a1 + 0.05, c0 + sgn * 0.045, z + 0.085), M["trim"], bevel=0.006, segs=22)
    C.cyl(name + "_valve_neck", 0.014, 0.03, P(axis, a1 + 0.05, c0 + sgn * 0.045, z + 0.06), M["steel"], segs=14)
    return r


def switch(name, axis, face, a, sgn, M, z=1.1, socket=False, double=False):
    """Light switch or wall socket plate."""
    w = 0.16 if double else 0.082
    items = [(P(axis, a - w / 2, face, z - 0.041), P(axis, a + w / 2, face + sgn * 0.009, z + 0.041))]
    o = C.boxes(name, items, M["plastic_white"])
    C.add_bevel(o, 0.003)
    n = 2 if double else 1
    inner_items = []
    for i in range(n):
        ca = a + (i - (n - 1) / 2) * 0.08
        if socket:
            C.cyl(name + "_hole", 0.019, 0.006, P(axis, ca, face + sgn * 0.006, z), M["plastic_white_dark"],
                  rot=(math.radians(-90 * sgn), 0, 0) if axis == "x" else (0, math.radians(90 * sgn), 0), segs=24)
        else:
            inner_items.append((P(axis, ca - 0.026, face + sgn * 0.008, z - 0.027),
                                P(axis, ca + 0.026, face + sgn * 0.0125, z + 0.027)))
    if inner_items:
        r = C.boxes(name + "_rocker", inner_items, M["plastic_white"])
        C.add_bevel(r, 0.002)
    return o

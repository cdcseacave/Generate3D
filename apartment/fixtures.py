"""Large procedural fixtures: kitchen units, bathroom ware, bed, crib, desk,
chairs, curtains. Wall-standing pieces have their origin at back-centre on the
floor with the front towards -Y; free-standing ones are centred."""
import math

from . import art
from . import core as C
from . import props as P
from . import shell as S

R = C.rng
PI = math.pi


# --------------------------------------------------------------- kitchen ---
def CHAIR_MESH():
    """Elastic office-chair mesh: a fine woven grid you can partly see through."""
    name = "ChairMesh"
    if name in C._MATS:
        return C._MATS[name]
    m = C.mat(name, "#26282c", rough=0.75)
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.0012
    br.inputs["Brick Width"].default_value = 0.004
    br.inputs["Row Height"].default_value = 0.004
    br.inputs["Color1"].default_value = (0.5, 0.5, 0.5, 1)
    br.inputs["Color2"].default_value = (0.5, 0.5, 0.5, 1)
    br.inputs["Mortar"].default_value = (1, 1, 1, 1)
    nt.links.new(tc.outputs["UV"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], bsdf.inputs["Alpha"])
    return m


def DUVET():
    """Linen duvet cover: visible weave plus box-quilt stitch lines pressed into the filling."""
    name = "DuvetLinen"
    if name in C._MATS:
        return C._MATS[name]
    m = P.FAB("rough_linen", "#c6cfc9", size=0.16, normal=2.6)
    m.name = name
    C._MATS[name] = m
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Mortar Smooth"].default_value = 1.0
    br.inputs["Brick Width"].default_value = 0.32
    br.inputs["Row Height"].default_value = 0.32
    br.inputs["Color1"].default_value = (1, 1, 1, 1)
    br.inputs["Color2"].default_value = (1, 1, 1, 1)
    br.inputs["Mortar"].default_value = (0, 0, 0, 1)
    nt.links.new(tc.outputs["UV"], br.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.9
    bp.inputs["Distance"].default_value = 0.012
    nt.links.new(br.outputs["Color"], bp.inputs["Height"])
    prev = bsdf.inputs["Normal"].links[0].from_socket if bsdf.inputs["Normal"].links else None
    if prev is not None:
        nt.links.new(prev, bp.inputs["Normal"])
    nt.links.new(bp.outputs[0], bsdf.inputs["Normal"])
    return m


def WORKTOP():
    """Pale quartz composite: off-white with fine speckle, satin."""
    return C.mat("WorktopQuartz", "#d9d6cf", rough=0.3, noise=0.05, bump=0.15, bump_scale=900, wear=0.12)


def KITCHEN_FRONT():
    return C.mat("KitchenFront", "#dfe2d8", rough=0.38, noise=0.02, wear=0.2)


def base_run(name, units, loc, rot, sink=None, top=None):
    """Row of base cabinets along local +X from x=0 (back on y=0). units: (width, kind) with
    kind in door|drawers|oven|dishwasher|blind. sink = x centre of a counter cut-out."""
    C.begin()
    D, g = 0.58, 0.002
    fr, carc, glass, steel, handles = [], [], [], [], []
    x = 0.0
    for w, kind in units:
        carc.append(((x, -D + 0.02, 0.1), (x + w, 0, 0.86)))
        y0, y1 = -D - 0.0, -D + 0.02

        def slab(xa, xb, za, zb, lst=fr):
            lst.append(((xa + g, y0, za), (xb - g, y1, zb)))

        def bar(xc, z, length=0.16, vertical=False):
            if vertical:
                handles.append(((xc - 0.006, y0 - 0.03, z - length / 2), (xc + 0.006, y0 - 0.018, z + length / 2)))
                for dz in (-length / 2 + 0.015, length / 2 - 0.015):
                    handles.append(((xc - 0.005, y0 - 0.02, z + dz - 0.005), (xc + 0.005, y0, z + dz + 0.005)))
            else:
                handles.append(((xc - length / 2, y0 - 0.03, z - 0.006), (xc + length / 2, y0 - 0.018, z + 0.006)))
                for dx in (-length / 2 + 0.015, length / 2 - 0.015):
                    handles.append(((xc + dx - 0.005, y0 - 0.02, z - 0.005), (xc + dx + 0.005, y0, z + 0.005)))

        if kind == "door":
            n = 1 if w <= 0.62 else 2
            for i in range(n):
                xa, xb = x + i * w / n, x + (i + 1) * w / n
                slab(xa, xb, 0.105, 0.855)
                bar(xb - 0.05 if i == 0 and n == 2 else (xa + 0.05 if n == 2 else xb - 0.05), 0.76, 0.14, True)
        elif kind == "drawers":
            for za, zb in ((0.105, 0.385), (0.39, 0.67), (0.675, 0.855)):
                slab(x, x + w, za, zb)
                bar(x + w / 2, zb - 0.045, min(0.3, w * 0.5))
        elif kind == "oven":
            slab(x, x + w, 0.105, 0.2)
            slab(x, x + w, 0.205, 0.76, glass)
            slab(x, x + w, 0.765, 0.855, steel)
            steel.append(((x + 0.05, y0 - 0.045, 0.7), (x + w - 0.05, y0 - 0.03, 0.716)))
            for dx in (0.05, w - 0.05):
                steel.append(((x + dx - 0.006, y0 - 0.03, 0.702), (x + dx + 0.006, y0, 0.714)))
            for i in range(4):
                C.cyl("knob", 0.016, 0.02, (x + 0.09 + i * (w - 0.18) / 3, y0, 0.81), P.METAL("black"),
                      rot=(PI / 2, 0, 0), segs=16, bevel=0.003)
        elif kind == "dishwasher":
            slab(x, x + w, 0.105, 0.74)
            slab(x, x + w, 0.745, 0.855, steel)
            bar(x + w / 2, 0.69, w * 0.7)
        x += w
    total = x
    C.boxes("carcass", carc, C.mat("KitchenCarcass", "#e9e7e1", rough=0.5))
    f = C.boxes("fronts", fr, KITCHEN_FRONT())
    C.add_bevel(f, 0.0015)
    if glass:
        C.boxes("oven_glass", glass, C.mat("OvenGlass", "#070708", rough=0.04, coat=1.0, wear=0.2))
    if steel:
        C.add_bevel(C.boxes("steel", steel, P.METAL("steel")), 0.002)
    if handles:
        C.add_bevel(C.boxes("handles", handles, P.METAL("black")), 0.002)
    C.boxes("plinth", [((0, -D + 0.06, 0), (total, -D + 0.075, 0.1))], C.mat("Plinth", "#2a2b2c", rough=0.5))
    top = top or WORKTOP()
    ct = [((0, -D - 0.025, 0.86), (total, 0, 0.9))]
    if sink is not None:
        sx0, sx1, sy0, sy1 = sink - 0.25, sink + 0.25, -0.53, -0.13
        ct = [((0, -D - 0.025, 0.86), (sx0, 0, 0.9)), ((sx1, -D - 0.025, 0.86), (total, 0, 0.9)),
              ((sx0, -D - 0.025, 0.86), (sx1, sy0, 0.9)), ((sx0, sy1, 0.86), (sx1, 0, 0.9))]
        st = P.METAL("steel")
        C.basin("sink", (0.52, 0.42, 0.2), (sink, -0.33, 0.703), st, wall=0.012, bevel=0.012)
        C.cyl("drain", 0.028, 0.004, (sink, -0.33, 0.716), P.METAL("black"), segs=20)
        ch = P.METAL("chrome")
        C.cyl("tap_base", 0.024, 0.045, (sink, -0.085, 0.9), ch, segs=24, bevel=0.004)
        C.pipe("tap", [(sink, -0.085, 0.93), (sink, -0.085, 1.2), (sink, -0.13, 1.29), (sink, -0.22, 1.28),
                       (sink, -0.25, 1.2)], 0.011, ch)
        C.box("tap_lever", (0.012, 0.012, 0.09), (sink + 0.035, -0.085, 0.93), ch, bevel=0.004)
    c = C.boxes("counter", ct, top)
    C.add_bevel(c, 0.003)
    return C.end(name, loc, rot)


def upper_run(name, units, loc, rot, z0=1.45, h=0.75, D=0.34):
    """Wall cabinets along local +X. kinds: door | open | hood | gap."""
    C.begin()
    g = 0.002
    carc, fr, handles, boards = [], [], [], []
    x = 0.0
    for w, kind in units:
        if kind == "door":
            carc.append(((x, -D + 0.02, z0), (x + w, 0, z0 + h)))
            n = 1 if w <= 0.55 else 2
            for i in range(n):
                xa, xb = x + i * w / n, x + (i + 1) * w / n
                fr.append(((xa + g, -D, z0), (xb - g, -D + 0.02, z0 + h)))
                hx = xb - 0.04 if (i == 0 and n == 2) or (n == 1) else xa + 0.04
                handles.append(((hx - 0.006, -D - 0.03, z0 + 0.04), (hx + 0.006, -D - 0.018, z0 + 0.16)))
                for dz in (0.055, 0.145):
                    handles.append(((hx - 0.005, -D - 0.02, z0 + dz - 0.005), (hx + 0.005, -D, z0 + dz + 0.005)))
        elif kind == "open":
            t = 0.018
            boards += [((x, -D, z0), (x + w, 0, z0 + t)), ((x, -D, z0 + h - t), (x + w, 0, z0 + h)),
                       ((x, -D, z0), (x + t, 0, z0 + h)), ((x + w - t, -D, z0), (x + w, 0, z0 + h)),
                       ((x, -D + 0.01, z0 + h * 0.48), (x + w, 0, z0 + h * 0.48 + t)),
                       ((x, -0.006, z0), (x + w, 0, z0 + h))]
        elif kind == "hood":
            st = P.METAL("steel")
            C.box("hood", (w, 0.48, 0.05), (x + w / 2, -0.24, z0 + 0.12), st, bevel=0.004)
            C.box("hood_body", (w, 0.3, 0.2), (x + w / 2, -0.15, z0 + 0.17), st, bevel=0.004)
            C.box("chimney", (0.24, 0.22, S.H - z0 - 0.37), (x + w / 2, -0.11, z0 + 0.37), st, bevel=0.003)
            C.box("hood_filter", (w - 0.08, 0.36, 0.004), (x + w / 2, -0.24, z0 + 0.116), P.METAL("black"))
            C.light("hood_light", (x + w / 2, -0.25, z0 + 0.1), 6, "#fff1d6", radius=0.03)
        x += w
    if carc:
        C.boxes("carcass", carc, C.mat("KitchenCarcass", "#e9e7e1", rough=0.5))
        C.add_bevel(C.boxes("fronts", fr, KITCHEN_FRONT()), 0.0015)
        C.add_bevel(C.boxes("handles", handles, P.METAL("black")), 0.002)
    if boards:
        C.boxes("open_shelf", boards, P.WOOD("oak"))
    return C.end(name, loc, rot)


def fridge(loc, rot, w=0.6, d=0.66, h=1.86):
    C.begin()
    body = C.mat("FridgeSteel", "#c4c6c8", rough=0.3, metal=0.9, wear=0.07)
    C.box("body", (w, d - 0.05, h), (0, -(d - 0.05) / 2, 0.0), C.mat("FridgeSide", "#b9bbbd", rough=0.45, metal=0.6),
          bevel=0.006)
    split = 0.68
    C.add_bevel(C.boxes("doors", [((-w / 2, -d, 0.03), (w / 2, -d + 0.05, split - 0.004)),
                                  ((-w / 2, -d, split + 0.004), (w / 2, -d + 0.05, h))], body), 0.008)
    st = P.METAL("steel")
    for za, zb in ((split - 0.4, split - 0.06), (split + 0.06, split + 0.6)):
        C.pipe("handle", [(-w / 2 + 0.05, -d - 0.035, za), (-w / 2 + 0.05, -d - 0.035, zb)], 0.009, st, smooth=False)
        for z in (za + 0.02, zb - 0.02):
            C.pipe("handle_post", [(-w / 2 + 0.05, -d, z), (-w / 2 + 0.05, -d - 0.035, z)], 0.006, st, smooth=False)
    # magnets, drawings, notes on the upper door
    yy = -d - 0.0008
    for i, (dx, z, a) in enumerate(((0.06, 1.42, 0.05), (-0.02, 1.13, -0.08))):
        C.quad("fridge_drawing", 0.26, 0.19, (dx, yy, z), art.kid_drawing(i + 1), rot=(PI / 2, a, 0))
        C.cyl("magnet", 0.014, 0.006, (dx + R.uniform(-0.05, 0.05), yy, z + 0.08), P.PL(R.choice(P.TOY_COLORS)),
              rot=(PI / 2, 0, 0), segs=16)
    for i in range(5):
        C.box("magnet", (0.03, 0.006, 0.03), (R.uniform(-0.2, 0.22), yy - 0.003, R.uniform(0.85, 1.7)),
              P.PL(R.choice(P.TOY_COLORS)), rot=0.0, bevel=0.002, anchor=(0, 0, 0))
    C.quad("note", 0.075, 0.075, (0.2, yy, 1.62), P.PL("#f5e663", 0.7), rot=(PI / 2, 0.1, 0))
    C.quad("list", 0.1, 0.2, (-0.17, yy, 1.5), P.PAPER(), rot=(PI / 2, -0.04, 0))
    return C.end("Fridge", loc, rot)


def cooktop(loc, rot):
    C.begin()
    C.box("glass", (0.58, 0.5, 0.008), (0, 0, 0), C.mat("HobGlass", "#0a0a0b", rough=0.03, coat=1.0, wear=0.22), bevel=0.002)
    for (x, y, r) in ((-0.15, 0.11, 0.09), (0.15, 0.11, 0.075), (-0.15, -0.11, 0.075), (0.15, -0.11, 0.09)):
        C.ring("zone", r, 0.0015, (x, y, 0.008), C.mat("HobRing", "#6b6b6e", rough=0.3))
    return C.end("Cooktop", loc, rot)


def table(name, size, loc, rot=0.0, top=None, legs=None, h=0.74, leg=0.05):
    """Simple four-legged table (centred)."""
    w, d = size
    C.begin()
    C.box("top", (w, d, 0.032), (0, 0, h - 0.032), top or P.WOOD("walnut"), bevel=0.004)
    lm = legs or P.WOOD("white")
    items = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.06), sy * (d / 2 - 0.06)
            items.append(((x - leg / 2, y - leg / 2, 0), (x + leg / 2, y + leg / 2, h - 0.032)))
    items += [((-w / 2 + 0.06, sy * (d / 2 - 0.06) - 0.01, h - 0.11), (w / 2 - 0.06, sy * (d / 2 - 0.06) + 0.01, h - 0.032))
              for sy in (-1, 1)]
    items += [((sx * (w / 2 - 0.06) - 0.01, -d / 2 + 0.06, h - 0.11), (sx * (w / 2 - 0.06) + 0.01, d / 2 - 0.06, h - 0.032))
              for sx in (-1, 1)]
    C.add_bevel(C.boxes("legs", items, lm), 0.003)
    return C.end(name, loc, rot)


def high_chair(loc, rot=0.0):
    C.begin()
    wd = P.WOOD("light")
    for sx in (-1, 1):
        for sy in (-1, 1):
            C.pipe("leg", [(sx * 0.215, sy * 0.215, 0.0), (sx * 0.15, sy * 0.15, 0.56)], 0.018, wd, smooth=False)
    for sy in (-1, 1):
        C.pipe("stretcher", [(-0.185, sy * 0.185, 0.26), (0.185, sy * 0.185, 0.26)], 0.012, wd, smooth=False)
    for sx in (-1, 1):
        C.pipe("stretcher", [(sx * 0.19, -0.19, 0.2), (sx * 0.19, 0.19, 0.2)], 0.012, wd, smooth=False)
    C.basin("seat", (0.34, 0.33, 0.14), (0, 0, 0.54), P.PL("#f3f2ee", 0.35), wall=0.02, depth=0.08, bevel=0.03)
    C.soft_box("back", (0.32, 0.035, 0.3), (0, 0.16, 0.62), P.PL("#f3f2ee", 0.35), round_=0.015, cuts=2)
    C.soft_box("pad", (0.26, 0.26, 0.03), (0, -0.005, 0.585), P.FAB("cotton_jersey", "#9fb7ad", size=0.15), round_=0.012,
               cuts=3)
    C.basin("tray", (0.44, 0.28, 0.03), (0, -0.24, 0.74), P.PL("#f3f2ee", 0.35), wall=0.02, depth=0.012, bevel=0.012)
    for sx in (-1, 1):
        C.pipe("tray_arm", [(sx * 0.17, 0.1, 0.72), (sx * 0.19, -0.2, 0.745)], 0.01, wd, smooth=False)
    return C.end("HighChair", loc, rot)


# -------------------------------------------------------------- bathroom ---
def bathtub(loc, rot, l=1.7, w=0.75, h=0.56):
    """Origin at back-centre; long side along X; front (room side) towards -Y."""
    C.begin()
    ac = C.mat("Acrylic", "#f5f5f2", rough=0.06, coat=0.6, wear=0.15)
    # Built-in acrylic tub: a rounded shell dropped into a tiled surround, with a
    # thin rim lip overhanging the apron and a silicone joint against the walls.
    tile = C._MATS.get("BathWallTiles") or ac
    C.boxes("apron", [((-l / 2, -w, 0), (l / 2, -w + 0.02, h - 0.03)), ((-l / 2, -w, 0), (-l / 2 + 0.02, 0, h - 0.03))], tile)
    tub = C.basin("tub", (l - 0.1, w - 0.1, 0.47), (0.0, -w / 2, h - 0.472), ac, wall=0.03, depth=0.42, taper=0.2,
                  bevel=0.05, segs=6)
    C.subsurf(tub, 1)
    lip = [((-l / 2 - 0.012, -w - 0.012, h - 0.045), (l / 2, -w + 0.075, h)), ((-l / 2 - 0.012, -0.075, h - 0.045), (l / 2, 0, h)),
           ((-l / 2 - 0.012, -w - 0.012, h - 0.045), (-l / 2 + 0.075, 0, h)), ((l / 2 - 0.075, -w - 0.012, h - 0.045), (l / 2, 0, h))]
    C.add_bevel(C.boxes("rim", lip, ac), 0.014, 4)
    C.boxes("silicone", [((-l / 2, -0.008, h), (l / 2, 0, h + 0.006)), ((l / 2 - 0.008, -w, h), (l / 2, 0, h + 0.006))],
            C.mat("Silicone", "#ecebe6", rough=0.5))
    ch = P.METAL("chrome")
    C.cyl("drain", 0.028, 0.004, (l / 2 - 0.42, -w / 2, h - 0.416), ch, segs=20)
    C.cyl("overflow", 0.028, 0.012, (l / 2 - 0.115, -w / 2, h - 0.15), ch, rot=(0, -PI / 2, 0), segs=20)
    # wall mixer + hand shower at the +X end of the back wall
    mx = l / 2 - 0.45
    C.box("mixer", (0.2, 0.05, 0.05), (mx, -0.04, h + 0.2), ch, bevel=0.012)
    for s in (-1, 1):
        C.cyl("mixer_knob", 0.024, 0.04, (mx + s * 0.12, -0.04, h + 0.2 + 0.025), ch, rot=(0, s * PI / 2, 0),
              segs=16, bevel=0.004)
    C.pipe("spout", [(mx, -0.06, h + 0.22), (mx, -0.16, h + 0.2), (mx, -0.19, h + 0.16)], 0.011, ch)
    C.pipe("riser", [(mx + 0.3, -0.035, h + 0.45), (mx + 0.3, -0.035, h + 1.25)], 0.009, ch, smooth=False)
    C.cyl("shower_head", 0.045, 0.018, (mx + 0.3, -0.1, h + 1.12), ch, rot=(PI / 2 - 0.5, 0, 0), segs=24)
    C.cyl("shower_face", 0.04, 0.003, (mx + 0.3, -0.1 - 0.0185 * math.cos(0.5), h + 1.12 - 0.0185 * math.sin(0.5)),
          C.mat("ShowerFace", "#b9bbbd", rough=0.55, bump=1.0, bump_scale=700), rot=(PI / 2 - 0.5, 0, 0), segs=24)
    C.pipe("shower_handle", [(mx + 0.3, -0.045, h + 1.06), (mx + 0.3, -0.09, h + 1.12)], 0.011, ch, smooth=False)
    C.pipe("hose", [(mx + 0.05, -0.05, h + 0.19), (mx + 0.16, -0.08, h + 0.02), (mx + 0.27, -0.07, h + 0.4),
                    (mx + 0.3, -0.05, h + 1.05)], 0.006, ch)
    # fixed glass screen standing on the front rim at the shower end
    C.box("screen", (0.8, 0.008, 1.4), (l / 2 - 0.41, -w + 0.04, h), C.glass("ShowerGlass"))
    C.pipe("screen_profile", [(l / 2 - 0.008, -w + 0.04, h), (l / 2 - 0.008, -w + 0.04, h + 1.4)], 0.008, ch, smooth=False)
    return C.end("Bathtub", loc, rot)


def toilet(loc, rot):
    C.begin()
    cer = P.CER("#f5f5f2")
    C.lathe("bowl", [(0, 0), (0.125, 0), (0.135, 0.03), (0.115, 0.13), (0.125, 0.26), (0.18, 0.37), (0.188, 0.4),
                     (0.16, 0.4), (0.13, 0.33), (0.08, 0.25), (0, 0.22)], (0, -0.31, 0), cer, segs=40,
            scale=(1.0, 1.32, 1.0))
    C.lathe("lid", [(0, 0.404), (0.192, 0.404), (0.198, 0.425), (0.17, 0.438), (0, 0.442)], (0, -0.31, 0),
            P.PL("#f7f7f4", 0.25), segs=40, scale=(1.0, 1.3, 1.0))
    C.lathe("seat", [(0.196, 0.392), (0.2, 0.402), (0.12, 0.402), (0.12, 0.392)], (0, -0.31, 0), P.PL("#f1f1ee", 0.3), segs=40,
            scale=(1.0, 1.3, 1.0), sub=0)
    for sx in (-1, 1):
        C.cyl("seat_hinge", 0.016, 0.022, (sx * 0.075, -0.075, 0.402), P.METAL("chrome"), segs=16, bevel=0.003)
    C.box("neck", (0.24, 0.26, 0.39), (0, -0.14, 0), cer, bevel=0.035)
    C.box("tank", (0.37, 0.16, 0.37), (0, -0.09, 0.4), cer, bevel=0.035)
    C.box("tank_lid", (0.41, 0.19, 0.03), (0, -0.09, 0.77), cer, bevel=0.01)
    C.box("flush_plate", (0.11, 0.07, 0.006), (0, -0.09, 0.8), P.METAL("chrome"), bevel=0.003)
    C.box("flush_split", (0.002, 0.066, 0.002), (0.012, -0.09, 0.806), P.PL("#555555", 0.4))
    C.boxes("cistern_gap", [((-0.196, -0.176, 0.768), (0.196, -0.004, 0.771))], P.PL("#9a9a98", 0.6))
    return C.end("Toilet", loc, rot)


def vanity(loc, rot, w=0.9):
    C.begin()
    wd = P.WOOD("oak")
    C.box("cabinet", (w - 0.02, 0.44, 0.44), (0, -0.23, 0.29), wd, bevel=0.003)
    fr = [((-w / 2 + 0.012, -0.47, 0.295), (-0.002, -0.452, 0.725)), ((0.002, -0.47, 0.295), (w / 2 - 0.012, -0.452, 0.725))]
    C.add_bevel(C.boxes("fronts", fr, wd), 0.002)
    for s in (-1, 1):
        C.box("pull", (0.012, 0.012, 0.12), (s * 0.05, -0.478, 0.58), P.METAL("black"), bevel=0.003)
    C.basin("basin", (w, 0.48, 0.15), (0, -0.24, 0.73), P.CER("#f5f5f2"), wall=0.07, depth=0.105, taper=0.1,
            bevel=0.02, segs=4)
    ch = P.METAL("chrome")
    C.cyl("drain", 0.022, 0.004, (0, -0.24, 0.776), ch, segs=20)
    C.cyl("tap_base", 0.022, 0.1, (0, -0.045, 0.88), ch, segs=24, bevel=0.004)
    C.pipe("tap", [(0, -0.045, 0.96), (0, -0.1, 0.975), (0, -0.16, 0.955)], 0.011, ch)
    C.box("tap_lever", (0.014, 0.07, 0.012), (0, -0.05, 0.985), ch, bevel=0.004)
    # mirror cabinet with a light bar
    C.box("mirror_cab", (w - 0.04, 0.13, 0.66), (0, -0.065, 1.16), C.mat("MirrorCab", "#ecebe7", rough=0.4), bevel=0.003)
    mir = C.mat("Mirror", "#f2f2f2", rough=0.0, metal=1.0, wear=0.035)
    C.boxes("mirror", [((-w / 2 + 0.024, -0.134, 1.164), (-0.001, -0.13, 1.816)),
                       ((0.001, -0.134, 1.164), (w / 2 - 0.024, -0.13, 1.816))], mir)
    C.box("light_bar", (w - 0.2, 0.035, 0.03), (0, -0.11, 1.84), C.mat("LightBar", "#fff6e6", rough=0.3, emit=12.0,
                                                                       emit_color="#fff0d8"), bevel=0.006)
    C.light("vanity_light", (0, -0.2, 1.84), 14, "#fff0d8", radius=0.05)
    return C.end("Vanity", loc, rot)


def washing_machine(loc, rot):
    C.begin()
    wh = C.mat("ApplianceWhite", "#f1f1ee", rough=0.25, wear=0.2)
    gy = C.mat("ApplianceGrey", "#cfd0d1", rough=0.35)
    C.box("body", (0.6, 0.57, 0.85), (0, -0.285, 0), wh, bevel=0.012)
    C.box("kick", (0.58, 0.004, 0.07), (0, -0.572, 0.012), gy, bevel=0.001)
    C.box("panel", (0.585, 0.006, 0.105), (0, -0.572, 0.735), gy, bevel=0.002)
    C.box("drawer", (0.17, 0.008, 0.08), (-0.195, -0.575, 0.747), wh, bevel=0.004)
    C.box("drawer_grip", (0.1, 0.006, 0.012), (-0.195, -0.58, 0.752), gy, bevel=0.002)
    C.cyl("dial", 0.032, 0.022, (0.045, -0.575, 0.787), P.METAL("steel"), rot=(PI / 2, 0, 0), segs=28, bevel=0.004)
    C.box("dial_mark", (0.004, 0.004, 0.02), (0.045, -0.598, 0.797), P.PL("#222222", 0.4))
    C.quad("display", 0.085, 0.032, (0.165, -0.5755, 0.795), C.mat("LcdOff", "#0c1512", rough=0.1), rot=(PI / 2, 0, 0))
    for i in range(4):
        C.cyl("button", 0.007, 0.004, (0.125 + i * 0.027, -0.575, 0.757), P.PL("#e2e2df", 0.3), rot=(PI / 2, 0, 0), segs=12)
    C.ring("door_frame", 0.2, 0.013, (0, -0.577, 0.4), wh, rot=(PI / 2, 0, 0))
    C.ring("door_ring", 0.172, 0.012, (0, -0.588, 0.4), P.METAL("chrome"), rot=(PI / 2, 0, 0))
    C.lathe("door_glass", [(0, 0.03), (0.09, 0.027), (0.16, 0.008), (0.166, 0.0)], (0, -0.585, 0.4),
            C.mat("DrumGlass", "#0b0d10", rough=0.03, coat=1.0, wear=0.1), rot=(PI / 2, 0, 0), segs=40, sub=1)
    C.box("door_handle", (0.02, 0.022, 0.1), (0.2, -0.592, 0.35), gy, bevel=0.006)
    return C.end("WashingMachine", loc, rot)


def towel_radiator(loc, rot, w=0.5, h=1.1, z0=0.75):
    C.begin()
    ch = P.METAL("chrome")
    for s in (-1, 1):
        C.pipe("rail", [(s * w / 2, -0.06, z0), (s * w / 2, -0.06, z0 + h)], 0.014, ch, smooth=False)
        for z in (z0 + 0.08, z0 + h - 0.08):
            C.pipe("bracket", [(s * w / 2, 0, z), (s * w / 2, -0.06, z)], 0.008, ch, smooth=False)
    n = 10
    for i in range(n):
        z = z0 + 0.06 + i * (h - 0.12) / (n - 1) + (0.03 if i % 5 > 2 else 0)
        C.pipe("rung", [(-w / 2, -0.06, z), (w / 2, -0.06, z)], 0.009, ch, smooth=False)
    return C.end("TowelRadiator", loc, rot)


# --------------------------------------------------------------- bedroom ---
def _ticking(m, period=0.085, color="#7f95a1"):
    """Woven ticking stripes across the cloth's own UVs (metres at rest), so the stripes
    bend and bunch with every fold instead of being projected onto the bed."""
    from . import wear as W
    if m.get("ticking"):
        return m
    m["ticking"] = 1
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    ph = W._math(nt, "FRACT", W._math(nt, "DIVIDE", sep.outputs["X"], period))
    wide = W._range(nt, W._math(nt, "ABSOLUTE", W._math(nt, "SUBTRACT", ph, 0.2)), 0.1, 0.085, 0.0, 0.8)
    thin = W._range(nt, W._math(nt, "ABSOLUTE", W._math(nt, "SUBTRACT", ph, 0.42)), 0.022, 0.012, 0.0, 0.6)
    W._blend(nt, bsdf, "Base Color", W._math(nt, "MAXIMUM", wide, thin), color)
    return m


def bed(loc, rot, w=1.6, l=2.0):
    """Double bed, head at +Y (against a wall), slept-in. Pillows are inflated fabric
    shells and the duvet is a cloth-simulated quilt dropped over mattress and
    pillows, so the bedding has real folds, sag and overhang."""
    C.begin()
    up = P.FAB("poly_wool_herringbone", "#8d8a84", size=0.2, normal=1.6)
    frame = C.box("frame", (w + 0.08, l + 0.06, 0.2), (0, 0, 0.09), up, bevel=0.015)
    for sx in (-1, 1):
        for sy in (-1, 1):
            C.box("leg", (0.06, 0.06, 0.09), (sx * (w / 2 - 0.06), sy * (l / 2 - 0.08), 0), P.WOOD("oak"), bevel=0.004)
    # channel-tufted headboard: vertical padded panels with seams between them
    n = 7
    pw = (w + 0.14) / n
    head = [C.soft_box("headboard", (pw - 0.004, 0.1, 1.0), (-(w + 0.14) / 2 + (i + 0.5) * pw, l / 2 + 0.07, 0.07), up,
                       round_=0.03, puff=0.0, cuts=4) for i in range(n)]
    C.box("headboard_back", (w + 0.14, 0.03, 1.0), (0, l / 2 + 0.11, 0.07), up)
    sheet = P.creased(P.FAB("cotton_jersey", "#ecebe6", size=0.2, normal=1.5), 0.35)
    mat_ = C.soft_box("mattress", (w, l, 0.22), (0, 0, 0.27), sheet, round_=0.06, puff=0.04, cuts=8)
    top = 0.49
    pil = P.creased(P.FAB("cotton_jersey", "#f0eeea", size=0.2, normal=1.5), 0.5, 0.6)
    pillows = []
    for i, (px, py, a, tz) in enumerate(((-0.4, l / 2 - 0.27, 0.08, 0.0), (0.42, l / 2 - 0.25, -0.15, 0.25))):
        # a head-sized weight rests in the middle while the pillow settles, leaving a slept-on dent
        dent = C.sphere("dent", 0.16, (px + 0.03, py - 0.02, top + 0.36 + 0.06 * i), None, scale=(1.3, 1.0, 0.7), segs=16)
        p = C.inflate("pillow", (0.64, 0.42, 0.05), (px, py, top + 0.18 + 0.06 * i), pil, rot=a, pressure=9.0, frames=34,
                      colliders=[mat_, dent] + head, gravity=1.0, cuts=14, shrink=-0.13, bend=0.1)
        if C._REC and dent in C._REC[-1]:
            C._REC[-1].remove(dent)
        import bpy as _bpy
        _bpy.data.objects.remove(dent)
        pillows.append(p)
    duv = P.creased(P.FAB("rough_linen", "#e3e3dc", size=0.16, normal=3.2), 0.7, 0.9)
    _ticking(duv)

    def start(u, v):          # starts pushed back from the pillows and slightly skewed, as when someone got up
        x = (u - 0.5) * (w + 0.5) + 0.04
        y = -l / 2 - 0.16 + v * (l * 0.8)
        crumple = 0.06 * math.sin(x * 7 + y * 4) * math.cos(y * 6 - x * 2) + 0.03 * math.sin(x * 15 + y * 11)
        return (x * 0.94 + 0.06 * math.sin(y * 3), y * 0.96, top + 0.22 + crumple + 0.09 * v * v)

    d = C.drape("duvet", w + 0.5, l * 0.8, (0, 0, 0), 0.05, duv, [mat_, frame] + pillows, frames=45, res=58, thick=0.034,
                stiffness=5.0, bend=0.14, shrink=-0.07, mass=0.4, shape=start, piping=0.007)
    return C.end("Bed", loc, rot)


def crib(loc, rot, w=0.72, l=1.3, h=0.92):
    C.begin()
    wd = P.WOOD("white")
    t = 0.04
    items = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - t / 2), sy * (l / 2 - t / 2)
            items.append(((x - t / 2, y - t / 2, 0), (x + t / 2, y + t / 2, h)))
    for sy in (-1, 1):
        y = sy * (l / 2 - t / 2)
        items += [((-w / 2, y - 0.012, h - 0.05), (w / 2, y + 0.012, h)), ((-w / 2, y - 0.012, 0.3), (w / 2, y + 0.012, 0.35))]
    for sx in (-1, 1):
        x = sx * (w / 2 - t / 2)
        items += [((x - 0.012, -l / 2, h - 0.05), (x + 0.012, l / 2, h)), ((x - 0.012, -l / 2, 0.3), (x + 0.012, l / 2, 0.35))]
    n = int(l / 0.07)
    for i in range(1, n):
        y = -l / 2 + i * l / n
        for sx in (-1, 1):
            x = sx * (w / 2 - t / 2)
            items.append(((x - 0.008, y - 0.008, 0.35), (x + 0.008, y + 0.008, h - 0.05)))
    n = int(w / 0.07)
    for i in range(1, n):
        x = -w / 2 + i * w / n
        for sy in (-1, 1):
            y = sy * (l / 2 - t / 2)
            items.append(((x - 0.008, y - 0.008, 0.35), (x + 0.008, y + 0.008, h - 0.05)))
    C.add_bevel(C.boxes("frame", items, wd), 0.004)
    C.soft_box("mattress", (w - 0.1, l - 0.1, 0.1), (0, 0, 0.34), P.FAB("cotton_jersey", "#f1efe9", size=0.3),
               round_=0.03, cuts=4)
    b = P.blanket("crib_blanket", w - 0.16, l * 0.5, (0.0, -l * 0.18, 0.455), rot=0.06, color=None, tex="gingham_check",
                  z_amp=0.012, thick=0.012, size=0.28)
    C.lumpy(b, 0.02, 0.15, seed=7)
    C.soft_box("pillow", (0.36, 0.26, 0.07), (0, l / 2 - 0.24, 0.44), P.FAB("cotton_jersey", "#dfe7ea", size=0.3),
               round_=0.03, puff=0.6, cuts=6)
    P.teddy((0.14, 0.12, 0.45), rot=2.6, scale=0.8, color="#c9a373")
    # mobile
    wm = P.WOOD("light")
    C.pipe("mobile_arm", [(-w / 2 + 0.02, l / 2 - 0.02, h - 0.02), (-w / 2 + 0.02, l / 2 - 0.02, h + 0.5),
                          (-w / 2 + 0.12, l / 2 - 0.12, h + 0.62), (-0.05, l / 2 - 0.32, h + 0.6)], 0.008, wm)
    cx, cy, cz = -0.05, l / 2 - 0.32, h + 0.6
    C.ring("mobile_ring", 0.11, 0.004, (cx, cy, cz - 0.08), wm)
    for i in range(5):
        a = i * 2 * PI / 5
        x, y = cx + 0.11 * math.cos(a), cy + 0.11 * math.sin(a)
        dz = 0.14 + 0.05 * (i % 2)
        C.pipe("string", [(x, y, cz - 0.08), (x, y, cz - 0.08 - dz)], 0.0008, P.PL("#ffffff"), smooth=False)
        C.sphere("mobile_toy", 0.025, (x, y, cz - 0.1 - dz), P.FAB("knitted_fleece", ["#e7c36a", "#9fc3c8", "#e6a6a0",
                                                                                   "#b9cfa5", "#d9d2c4"][i], size=0.1))
    for a in range(3):
        an = a * 2 * PI / 3
        C.pipe("string", [(cx, cy, cz), (cx + 0.11 * math.cos(an), cy + 0.11 * math.sin(an), cz - 0.08)], 0.0008,
               P.PL("#ffffff"), smooth=False)
    return C.end("Crib", loc, rot)


# ---------------------------------------------------------------- office ---
def desk(loc, rot, w=1.5, d=0.72, h=0.74):
    """Origin at back-centre (wall side)."""
    C.begin()
    C.box("top", (w, d, 0.03), (0, -d / 2, h - 0.03), P.WOOD("ply"), bevel=0.004)
    bm = P.METAL("black")
    items = []
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.08)
        items += [((x - 0.02, -d + 0.05, 0), (x + 0.02, -d + 0.09, h - 0.03)), ((x - 0.02, -0.09, 0), (x + 0.02, -0.05, h - 0.03)),
                  ((x - 0.02, -d + 0.05, 0), (x + 0.02, -0.05, 0.03)), ((x - 0.02, -d + 0.05, h - 0.07), (x + 0.02, -0.05, h - 0.03))]
    items.append(((-w / 2 + 0.08, -0.08, h - 0.2), (w / 2 - 0.08, -0.06, h - 0.1)))
    C.add_bevel(C.boxes("legs", items, bm), 0.003)
    # drawer pedestal under the right side
    wh = C.mat("PedestalWhite", "#ecebe7", rough=0.4)
    px = w / 2 - 0.36
    C.box("pedestal", (0.4, 0.52, 0.56), (px, -d / 2 - 0.02, 0.04), wh, bevel=0.004)
    fr = [((px - 0.196, -d / 2 - 0.296, 0.045 + i * 0.185), (px + 0.196, -d / 2 - 0.28, 0.045 + i * 0.185 + 0.18))
          for i in range(3)]
    C.add_bevel(C.boxes("pedestal_fronts", fr, wh), 0.002)
    for sx in (-1, 1):
        for sy in (-1, 1):
            C.cyl("caster", 0.02, 0.02, (px + sx * 0.16, -d / 2 - 0.02 + sy * 0.2 - 0.01, 0.02), P.RUBBER(),
                  rot=(PI / 2, 0, 0), segs=12)
    return C.end("Desk", loc, rot)


def office_chair(loc, rot=0.0, color="#3a3f45"):
    C.begin()
    bm = P.PL("#161617", 0.45)
    fab = P.FAB("poly_wool_herringbone", color, size=0.2)
    for i in range(5):
        a = i * 2 * PI / 5 + 0.3
        C.pipe("spoke", [(0, 0, 0.09), (0.3 * math.cos(a), 0.3 * math.sin(a), 0.06)], 0.016, bm, smooth=False)
        C.cyl("caster", 0.026, 0.022, (0.3 * math.cos(a), 0.3 * math.sin(a) - 0.011, 0.026), bm, rot=(PI / 2, 0, 0),
              segs=14)
    C.cyl("column", 0.027, 0.33, (0, 0, 0.08), P.METAL("black"), segs=16)
    C.box("mech", (0.2, 0.2, 0.04), (0, 0, 0.4), bm, bevel=0.01)
    C.inflate("seat", (0.5, 0.48, 0.03), (0, -0.02, 0.485), fab, pressure=2.2, gravity=0.0, frames=18, cuts=10, shrink=-0.02)
    C.box("seat_pan", (0.46, 0.44, 0.02), (0, -0.02, 0.44), bm, bevel=0.008)
    def back(u, v):
        x = (u - 0.5) * 0.46 * (1.0 - 0.12 * v * v)
        y = 0.23 - 0.05 * (2 * u - 1) ** 2 + 0.11 * v - 0.035 * math.sin(v * PI * 0.9)
        return (x, y, 0.56 + v * 0.54)

    # mesh back: a see-through woven panel stretched in a moulded frame, plus a lumbar pad
    mesh = P.FAB("cotton_jersey", "#25272b", size=0.06, normal=2.2)     # knit back; the see-through grid aliased into noise
    C.grid("back_mesh", 12, 14, back, (0, 0, 0), mesh, sub=1)
    rim = [back(u, 0.0) for u in (0, 0.25, 0.5, 0.75, 1)] + [back(1, v) for v in (0.25, 0.5, 0.75, 1)] + \
          [back(u, 1.0) for u in (0.75, 0.5, 0.25, 0)] + [back(0, v) for v in (0.75, 0.5, 0.25)]
    C.pipe("back_frame", rim, 0.014, bm, cyclic=True)
    C.pipe("lumbar", [back(0.04, 0.3), back(0.5, 0.3), back(0.96, 0.3)], 0.018, bm)
    C.pipe("back_spine", [back(0.5, 0.0), back(0.5, 0.5), back(0.5, 1.0)], 0.012, bm)
    C.pipe("back_arm", [(0, 0.1, 0.42), (0, 0.27, 0.45), (0, 0.3, 0.75)], 0.018, bm)
    for s in (-1, 1):
        C.pipe("arm", [(s * 0.2, 0.05, 0.43), (s * 0.29, 0.05, 0.47), (s * 0.29, 0.03, 0.66)], 0.013, bm)
        C.soft_box("armpad", (0.07, 0.26, 0.03), (s * 0.29, -0.04, 0.66), bm, round_=0.012, cuts=2)
    return C.end("OfficeChair", loc, rot)


def printer(loc, rot=0.0):
    C.begin()
    wh = P.PL("#e9e9e6", 0.4)
    C.box("body", (0.42, 0.34, 0.16), (0, 0, 0), wh, bevel=0.012)
    C.box("lid", (0.42, 0.34, 0.03), (0, 0, 0.16), P.PL("#2b2c2f", 0.4), bevel=0.008)
    C.box("tray", (0.3, 0.14, 0.006), (0, -0.22, 0.05), P.PL("#2b2c2f", 0.4), bevel=0.002)
    C.grid("printed_sheet", 2, 8, lambda u, v: ((u - 0.5) * 0.21, -0.13 - v * 0.2, 0.058 - 0.05 * v * v), (0, 0, 0), P.PAPER())
    return C.end("Printer", loc, rot)


def corkboard(loc, face, w=0.9, h=0.6):
    C.begin()
    C.box("cork", (w, 0.012, h), (0, -0.006, -h / 2), C.mat("Cork", "#b78a5b", rough=0.9, bump=0.8, bump_scale=160,
                                                             noise=0.08), anchor=(0, 0, -1))
    C.boxes("frame", [((-w / 2, -0.02, -h / 2), (-w / 2 + 0.02, 0, h / 2)), ((w / 2 - 0.02, -0.02, -h / 2), (w / 2, 0, h / 2)),
                      ((-w / 2, -0.02, -h / 2), (w / 2, 0, -h / 2 + 0.02)), ((-w / 2, -0.02, h / 2 - 0.02), (w / 2, 0, h / 2))],
            P.WOOD("light"))
    y = -0.0135
    C.quad("pin_drawing", 0.26, 0.19, (-0.25, y, 0.1), art.kid_drawing(3), rot=(PI / 2, 0.06, 0))
    C.quad("pin_cal", 0.2, 0.27, (0.28, y, 0.08), P.PAPER(), rot=(PI / 2, -0.02, 0))
    for i in range(7):
        col = ["#f5e663", "#f7a8c4", "#a8e0f0", "#b7ec9a"][i % 4]
        C.quad("sticky", 0.075, 0.075, (R.uniform(-0.38, 0.1), y - 0.0005 * i, R.uniform(-0.24, -0.02)), P.PL(col, 0.7),
               rot=(PI / 2, R.uniform(-0.2, 0.2), 0))
    C.quad("pin_paper", 0.21, 0.297, (0.02, y, 0.1), P.PAPER(), rot=(PI / 2, 0.03, 0))
    for i in range(6):
        C.sphere("pin", 0.006, (R.uniform(-0.4, 0.4), y - 0.004, R.uniform(0.0, 0.26)), P.PL(R.choice(P.TOY_COLORS)))
    return C.end("Corkboard", loc, P.FACE[face])


# ------------------------------------------------------------- soft/room ---
def curtains(name, axis, face, sgn, a0, a1, color="#d7cfc0", z_top=2.5, z_bot=0.03, open_frac=0.3, sheer=False,
             tex="rough_linen", off=0.1):
    """Curtain rod with two panels gathered to the sides of a window.
    face = wall face coordinate, sgn = direction into the room."""
    rod_c = face + sgn * off
    C.pipe(name + "_rod", [S.P(axis, a0 - 0.25, rod_c, z_top + 0.03), S.P(axis, a1 + 0.25, rod_c, z_top + 0.03)], 0.012,
           P.METAL("black"), smooth=False)
    for a in (a0 - 0.2, (a0 + a1) / 2, a1 + 0.2):
        C.pipe(name + "_bracket", [S.P(axis, a, face, z_top + 0.03), S.P(axis, a, rod_c, z_top + 0.03)], 0.007,
               P.METAL("black"), smooth=False)
    width = (a1 - a0 + 0.4)
    pw = width * open_frac
    if sheer:
        m = C.mat("SheerCurtain", "#f4f2ec", rough=0.9, alpha=0.5, trans=0.3)
        spans = [(a0 - 0.2, a1 + 0.2, 7.0)]
    else:
        m = P.FAB(tex, color, size=0.3)
        spans = [(a0 - 0.22, a0 - 0.22 + pw, 9.0 / pw), (a1 + 0.22 - pw, a1 + 0.22, 9.0 / pw)]
    for i, (s0, s1, freq) in enumerate(spans):
        waves = (s1 - s0) * freq
        p1, p2, p3, p4, p5 = (R.uniform(0, 6.28) for _ in range(5))
        hem = z_bot if sheer else 0.004           # drapes rest on the floor, the sheer hangs just clear

        def fn(u, v, s0=s0, s1=s1, waves=waves, p=(p1, p2, p3, p4, p5), hem=hem):
            # hand-gathered pleats: spacing and depth vary along the rod, drift down the
            # length, and the panel flares slightly towards the hem
            phi = 2 * PI * (waves * u + 0.33 * math.sin(2 * PI * 1.3 * u + p[0]) + 0.21 * math.sin(2 * PI * 2.9 * u + p[1]))
            phi += 0.7 * v * math.sin(2 * PI * 0.7 * u + p[3])
            amp = (0.03 + 0.022 * v) * (0.65 + 0.35 * math.sin(2 * PI * 0.8 * u + p[2]))
            a = s0 + u * (s1 - s0) + (u - 0.5) * 0.05 * v + 0.012 * v * math.sin(3 * u + p[4])
            z = z_top - v * (z_top - hem) + (0.012 * math.sin(phi * 0.5 + p[4]) * v if v > 0.9 else 0.0)
            off = amp * math.sin(phi) + 0.012 * math.sin(v * 5 + u * 13 + p[0])
            return S.P(axis, a, rod_c + off, max(z, 0.003))
        C.grid("{}_panel{}".format(name, i), max(24, int(waves * 9)), 18, fn, material=m, thick=0.0 if sheer else 0.004)


def roller_blind(name, axis, face, sgn, a0, a1, z_top, drop, color="#e9e5da"):
    c = face + sgn * 0.03
    C.boxes(name, [(S.P(axis, a0, c, z_top - drop), S.P(axis, a1, c + sgn * 0.003, z_top))],
            P.FAB("rough_linen", color, size=0.3))
    C.pipe(name + "_roll", [S.P(axis, a0 - 0.02, c, z_top + 0.02), S.P(axis, a1 + 0.02, c, z_top + 0.02)], 0.022,
           P.METAL("white"), smooth=False)
    C.pipe(name + "_bar", [S.P(axis, a0, c, z_top - drop), S.P(axis, a1, c, z_top - drop)], 0.008, P.METAL("white"),
           smooth=False)


def coat_rack(loc, face, w=1.3):
    """Wall board with hooks; returns hook positions in local X."""
    C.begin()
    C.box("board", (w, 0.022, 0.12), (0, -0.011, -0.06), P.WOOD("oak"), bevel=0.004, anchor=(0, 0, -1))
    xs = [-w / 2 + 0.1 + i * (w - 0.2) / 5 for i in range(6)]
    for x in xs:
        C.pipe("hook", [(x, -0.02, 0.01), (x, -0.07, -0.0), (x, -0.085, 0.03)], 0.006, P.METAL("black"))
    C.box("shelf", (w, 0.2, 0.022), (0, -0.1, 0.07), P.WOOD("oak"), bevel=0.004)
    return C.end("CoatRack", loc, P.FACE[face]), xs


def kid_table(loc, rot=0.0):
    C.begin()
    table("kid_table_top", (0.6, 0.46), (0, 0, 0), top=P.WOOD("white"), legs=P.WOOD("light"), h=0.46, leg=0.04)
    for i, (x, y, a, col) in enumerate(((-0.02, -0.42, 0.15, "#e9b44c"), (0.48, 0.05, 1.7, "#7fb7be"))):
        C.begin()
        C.box("seat", (0.28, 0.27, 0.02), (0, 0, 0.26), P.PL(col, 0.45), bevel=0.006)
        C.box("back", (0.28, 0.02, 0.22), (0, 0.125, 0.32), P.PL(col, 0.45), bevel=0.006)
        items = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                px, py = sx * 0.115, sy * 0.11
                items.append(((px - 0.015, py - 0.015, 0), (px + 0.015, py + 0.015, 0.26 if sy < 0 else 0.5)))
        C.boxes("legs", items, P.WOOD("light"))
        C.end("KidChair", (x, y, 0), a)
    return C.end("KidTable", loc, rot)


def play_mat(loc, rot=0.0, nx=4, ny=3, s=0.31):
    """Interlocking foam tiles: embossed surface, uneven joints, one tile kicked loose."""
    C.begin()
    cols = ["#a8d5c9", "#f2d3a2", "#e7b3b0", "#b9c8e6", "#d7e3a8", "#efe6d2"]
    k = 0
    for i in range(nx):
        for j in range(ny):
            loose = (i, j) == (nx - 1, 0)
            px = (i - (nx - 1) / 2) * s + R.uniform(-0.003, 0.003) + (0.06 if loose else 0.0)
            py = (j - (ny - 1) / 2) * s + R.uniform(-0.003, 0.003) - (0.09 if loose else 0.0)
            C.box("mat_tile", (s - 0.003, s - 0.003, 0.012), (px, py, 0), C.mat("Foam_" + cols[k % len(cols)],
                  cols[k % len(cols)], rough=0.9, bump=1.0, bump_scale=260, noise=0.05), rot=R.uniform(-0.012, 0.012) + (0.35 if loose else 0.0),
                  bevel=0.004)
            k += 1 + (j % 2)
    return C.end("PlayMat", loc, rot)


# ---------------------------------------------------- more furniture/props ---
def wardrobe(loc, rot, w=1.7, d=0.6, h=2.3, doors=4):
    C.begin()
    wh = C.mat("WardrobeWhite", "#eeece6", rough=0.36, noise=0.015, wear=0.18)
    C.box("carcass", (w, d - 0.02, h - 0.06), (0, -(d - 0.02) / 2, 0.06), C.mat("WardrobeCarcass", "#e6e4de", rough=0.5))
    C.boxes("plinth", [((-w / 2 + 0.01, -d + 0.05, 0), (w / 2 - 0.01, -d + 0.065, 0.06))], wh)
    dw = w / doors
    fr, hd = [], []
    for i in range(doors - 1):
        x0 = -w / 2 + i * dw
        fr.append(((x0 + 0.002, -d, 0.065), (x0 + dw - 0.002, -d + 0.02, h)))
        hx = x0 + dw - 0.04 if i % 2 == 0 else x0 + 0.04
        hd.append(((hx - 0.006, -d - 0.028, 0.95), (hx + 0.006, -d - 0.016, 1.25)))
        for z in (0.97, 1.23):
            hd.append(((hx - 0.005, -d - 0.018, z - 0.005), (hx + 0.005, -d, z + 0.005)))
    C.add_bevel(C.boxes("doors", fr, wh), 0.002)
    rails = []
    st = 0.07
    for (p0, p1) in fr:
        x0, x1, z0, z1 = p0[0], p1[0], p0[2], p1[2]
        y0, y1 = -d - 0.012, -d
        rails += [((x0, y0, z0), (x0 + st, y1, z1)), ((x1 - st, y0, z0), (x1, y1, z1)),
                  ((x0 + st, y0, z0), (x1 - st, y1, z0 + st * 1.3)), ((x0 + st, y0, z1 - st), (x1 - st, y1, z1)),
                  ((x0 + st, y0, 1.05), (x1 - st, y1, 1.05 + st))]
    C.add_bevel(C.boxes("door_frames", rails, wh), 0.0025)
    C.add_bevel(C.boxes("handles", [((a[0], a[1] - 0.012, a[2]), (b[0], b[1] - 0.012, b[2])) for a, b in hd], P.METAL("steel")), 0.002)
    # the last door stands slightly open, with a sleeve of something caught in it
    hx_ = w / 2 - 0.004
    C.boxes("ajar_shadow", [((hx_ - dw + 0.004, -d + 0.001, 0.07), (hx_, -d + 0.02, h - 0.004))], C.mat("WardrobeDark", "#0e0e0f", rough=0.9))
    C.begin()
    C.add_bevel(C.boxes("door", [((-dw + 0.006, -0.02, 0.065), (0, 0, h))], wh), 0.002)
    C.add_bevel(C.boxes("door_frame", [((-dw + 0.006, -0.032, 0.065), (-dw + 0.006 + st, -0.02, h)), ((-st, -0.032, 0.065), (0, -0.02, h)),
                                       ((-dw + 0.006 + st, -0.032, 0.065), (-st, -0.02, 0.065 + st * 1.3)),
                                       ((-dw + 0.006 + st, -0.032, h - st), (-st, -0.02, h)),
                                       ((-dw + 0.006 + st, -0.032, 1.05), (-st, -0.02, 1.05 + st))], wh), 0.0025)
    C.add_bevel(C.boxes("door_handle", [((-dw + 0.04, -0.06, 0.95), (-dw + 0.052, -0.048, 1.25))], P.METAL("steel")), 0.002)
    C.end("door_ajar", (hx_, -d + 0.02, 0), 0.16)
    C.box("cornice", (w + 0.03, d + 0.02, 0.04), (0, -d / 2, h), wh, bevel=0.006)
    return C.end("Wardrobe", loc, rot)


def shoe_cabinet(loc, rot, w=0.95, d=0.3, h=1.02):
    C.begin()
    wh = C.mat("WardrobeWhite", "#eeece6", rough=0.36, noise=0.015, wear=0.18)
    C.box("carcass", (w, d - 0.02, h - 0.1), (0, -(d - 0.02) / 2, 0.1), wh)
    C.box("top", (w + 0.02, d + 0.01, 0.022), (0, -d / 2, h - 0.022), P.WOOD("oak"), bevel=0.003)
    fr = [((-w / 2 + 0.003, -d, 0.105 + i * 0.3), (w / 2 - 0.003, -d + 0.02, 0.105 + i * 0.3 + 0.293)) for i in range(3)]
    C.add_bevel(C.boxes("flaps", fr, wh), 0.002)
    C.boxes("pulls", [((-0.07, -d - 0.012, 0.36 + i * 0.3), (0.07, -d, 0.372 + i * 0.3)) for i in range(3)], P.METAL("black"))
    items = [((sx * (w / 2 - 0.05) - 0.015, -d / 2 - 0.015, 0), (sx * (w / 2 - 0.05) + 0.015, -d / 2 + 0.015, 0.1)) for sx in (-1, 1)]
    C.boxes("feet", items, P.METAL("black"))
    return C.end("ShoeCabinet", loc, rot)


def microwave(loc, rot=0.0):
    C.begin()
    C.box("body", (0.47, 0.35, 0.27), (0, 0, 0), C.mat("ApplianceSteel", "#b9bbbe", rough=0.35, metal=0.9), bevel=0.008)
    C.box("door", (0.33, 0.006, 0.23), (-0.06, -0.177, 0.02), C.mat("OvenGlass", "#070708", rough=0.04, coat=1.0, wear=0.2), bevel=0.003)
    C.box("panel", (0.1, 0.006, 0.23), (0.17, -0.177, 0.02), P.PL("#1a1a1b", 0.4), bevel=0.003)
    C.cyl("dial", 0.02, 0.014, (0.17, -0.18, 0.08), P.METAL("steel"), rot=(PI / 2, 0, 0), segs=20)
    C.quad("lcd", 0.07, 0.025, (0.17, -0.1805, 0.2), C.mat("LcdGreen", "#123a22", rough=0.2, emit=1.5, emit_color="#3cff8a"),
           rot=(PI / 2, 0, 0))
    C.box("handle", (0.012, 0.02, 0.2), (0.105, -0.19, 0.035), P.METAL("steel"), bevel=0.004)
    return C.end("Microwave", loc, rot)


def toaster(loc, rot=0.0):
    C.begin()
    C.soft_box("body", (0.28, 0.16, 0.18), (0, 0, 0.008), C.mat("ToasterCream", "#e9e2d0", rough=0.3), round_=0.03, cuts=3)
    C.boxes("slots", [((-0.1, -0.045, 0.186), (0.1, -0.015, 0.19)), ((-0.1, 0.015, 0.186), (0.1, 0.045, 0.19))], P.PL("#151515", 0.6))
    C.box("lever", (0.02, 0.03, 0.012), (0.145, 0, 0.11), P.PL("#151515", 0.4), bevel=0.003)
    return C.end("Toaster", loc, rot)


def dish_rack(loc, rot=0.0):
    C.begin()
    st = P.METAL("chrome")
    C.basin("tray", (0.42, 0.3, 0.02), (0, 0, 0), P.PL("#3a3d40", 0.5), wall=0.01, depth=0.012, bevel=0.006)
    C.pipe("rail", [(-0.19, -0.13, 0.11), (0.19, -0.13, 0.11), (0.19, 0.13, 0.11), (-0.19, 0.13, 0.11)], 0.004, st,
           smooth=False, cyclic=True)
    for sx in (-0.19, 0.19):
        for sy in (-0.13, 0.13):
            C.pipe("post", [(sx, sy, 0.012), (sx, sy, 0.11)], 0.004, st, smooth=False)
    for i in range(9):
        x = -0.16 + i * 0.04
        C.pipe("tine", [(x, -0.05, 0.02), (x, -0.05, 0.09)], 0.0025, st, smooth=False)
    for i, col in enumerate(("#f1efe9", "#f1efe9", "#cfd9d6", "#f1efe9")):
        p = P.plate((-0.12 + i * 0.04, 0.0, 0.135), 0.115, col)
        p.rotation_euler = (0, PI / 2 - 0.12, 0)
    g = P.glass_cup((0.12, 0.07, 0.115))
    g.rotation_euler = (PI, 0, 0)
    m = P.mug((0.13, -0.07, 0.115), "#3d6a73", full=False)
    m.rotation_euler = (PI, 0, 0.4)
    return C.end("DishRack", loc, rot)


def knife_block(loc, rot=0.0):
    C.begin()
    b = C.box("block", (0.09, 0.14, 0.2), (0, 0, 0), P.WOOD("walnut"), bevel=0.006)
    b.rotation_euler = (0.3, 0, 0)
    for i in range(4):
        k = C.box("knife", (0.016, 0.022, 0.09), (-0.03 + i * 0.02, -0.062, 0.185), P.PL("#161616", 0.4), bevel=0.004)
        k.rotation_euler = (0.3, 0, 0)
    return C.end("KnifeBlock", loc, rot)


def paper_towel(loc):
    C.begin()
    C.cyl("base", 0.07, 0.012, (0, 0, 0), P.WOOD("light"), bevel=0.003)
    C.cyl("pole", 0.008, 0.3, (0, 0, 0.01), P.WOOD("light"), segs=12)
    C.cyl("roll", 0.055, 0.25, (0, 0, 0.015), C.mat("TissuePaper", "#f6f5f1", rough=0.9, bump=0.4, bump_scale=300), segs=28)
    return C.end("PaperTowel", loc)


def utensil_jar(loc):
    C.begin()
    C.lathe("jar", [(0, 0), (0.05, 0), (0.055, 0.15), (0.05, 0.15), (0.046, 0.008), (0, 0.008)], (0, 0, 0), P.CER("#d9d2c0"),
            segs=24)
    for i in range(5):
        a = i * 1.3 + 0.3
        m = P.WOOD("light") if i % 2 == 0 else P.METAL("steel")
        tip = (0.045 * math.cos(a), 0.045 * math.sin(a), 0.27 + 0.02 * (i % 3))
        C.pipe("utensil", [(0.015 * math.cos(a), 0.015 * math.sin(a), 0.01), tip], 0.005, m, smooth=False)
        C.sphere("utensil_head", 0.02, tip, m, scale=(1, 0.3, 1.4), rot=(0, 0, a))
    return C.end("UtensilJar", loc)


def desk_lamp(loc, rot=0.0, on=True):
    C.begin()
    k = P.METAL("black")
    C.cyl("base", 0.085, 0.02, (0, 0, 0), k, bevel=0.005)
    C.pipe("arm1", [(0, 0.02, 0.02), (0, 0.13, 0.33)], 0.007, k, smooth=False)
    C.pipe("arm2", [(0, 0.13, 0.33), (0, -0.12, 0.5)], 0.007, k, smooth=False)
    C.sphere("joint", 0.014, (0, 0.13, 0.33), k)
    sh = C.lathe("shade", [(0.02, 0.0), (0.035, -0.02), (0.075, -0.11)], (0, -0.13, 0.52), k, segs=28, sub=0)
    sh.rotation_euler = (-0.5, 0, 0)
    if on:
        C.light("bulb", (0, -0.15, 0.47), 30, "#ffe1b8", kind="SPOT", radius=0.02, rot=(-0.5, 0, 0), spot=math.radians(105))
    return C.end("DeskLamp", loc, rot)


def wall_shelf(loc, face, w=0.8, d=0.2):
    """Floating shelf; loc = centre of its back edge at the top surface height."""
    C.begin()
    C.box("board", (w, d, 0.03), (0, -d / 2, -0.03), P.WOOD("oak"), bevel=0.004)
    return C.end("WallShelf", loc, P.FACE[face])


def potty(loc, rot=0.0):
    C.begin()
    C.lathe("potty", [(0, 0), (0.13, 0), (0.15, 0.03), (0.155, 0.17), (0.13, 0.17), (0.11, 0.06), (0, 0.05)], (0, 0, 0),
            P.PL("#8fd0c4", 0.35), segs=28, scale=(1.0, 1.15, 1.0))
    C.soft_box("back", (0.2, 0.04, 0.12), (0, 0.15, 0.15), P.PL("#8fd0c4", 0.35), round_=0.02, cuts=2)
    return C.end("Potty", loc, rot)


def sippy_cup(loc, color="#f2a23a"):
    C.begin()
    C.lathe("cup", [(0, 0), (0.03, 0), (0.034, 0.09), (0, 0.09)], (0, 0, 0), P.PL(color, 0.3), segs=20)
    C.lathe("lid", [(0.036, 0.085), (0.036, 0.1), (0.015, 0.115), (0.008, 0.135), (0, 0.137)], (0, 0, 0), P.PL("#ffffff", 0.3),
            segs=20)
    for s in (-1, 1):
        C.pipe("grip", [(s * 0.033, 0, 0.075), (s * 0.06, 0, 0.06), (s * 0.058, 0, 0.03), (s * 0.032, 0, 0.02)], 0.005,
               P.PL("#ffffff", 0.3))
    return C.end("SippyCup", loc, R.uniform(0, 6.28))


def toothbrush_cup(loc):
    C.begin()
    C.lathe("cup", [(0, 0), (0.033, 0), (0.037, 0.1), (0.034, 0.1), (0.03, 0.006), (0, 0.006)], (0, 0, 0), P.CER("#dfe6e4"),
            segs=24)
    for i, col in enumerate(("#3f7fd0", "#e2577a", "#f2b81f")):
        a = i * 2.1
        length = 0.19 if i < 2 else 0.14
        C.pipe("brush", [(0.012 * math.cos(a), 0.012 * math.sin(a), 0.01),
                         (0.03 * math.cos(a), 0.03 * math.sin(a), length)], 0.004, P.PL(col, 0.35), smooth=False)
        C.box("bristles", (0.01, 0.01, 0.025), (0.031 * math.cos(a), 0.031 * math.sin(a), length - 0.01), P.PL("#ffffff", 0.8))
    return C.end("ToothbrushCup", loc)


def router(loc, rot=0.0):
    C.begin()
    C.box("body", (0.2, 0.13, 0.035), (0, 0, 0), P.PL("#f0f0ee", 0.35), bevel=0.008)
    for i in range(4):
        C.sphere("led", 0.003, (-0.06 + i * 0.02, -0.066, 0.018), C.mat("LedGreen", "#30ff70", rough=0.3, emit=8.0,
                                                                        emit_color="#30ff70"))
    for s in (-1, 1):
        C.pipe("antenna", [(s * 0.08, 0.06, 0.02), (s * 0.085, 0.07, 0.17)], 0.005, P.PL("#f0f0ee", 0.35), smooth=False)
    return C.end("Router", loc, rot)


def shoe_rack(loc, rot, w=0.9, d=0.3):
    """Open three-tier rack (origin back-centre). Returns (group, shelf heights)."""
    C.begin()
    bm = P.METAL("black")
    items = []
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.01)
        items += [((x - 0.01, -d, 0), (x + 0.01, -d + 0.02, 0.52)), ((x - 0.01, -0.02, 0), (x + 0.01, 0, 0.52)),
                  ((x - 0.01, -d, 0.5), (x + 0.01, 0, 0.52)), ((x - 0.01, -d, 0.03), (x + 0.01, 0, 0.05))]
    C.add_bevel(C.boxes("frame", items, bm), 0.003)
    levels = [0.062, 0.272, 0.512]
    slats = []
    for z in levels[:2]:
        for i in range(5):
            y = -d + 0.025 + i * (d - 0.05) / 4
            slats.append(((-w / 2 + 0.01, y - 0.026, z - 0.012), (w / 2 - 0.01, y + 0.026, z)))
    C.add_bevel(C.boxes("slats", slats, P.WOOD("oak")), 0.002)
    C.box("top", (w + 0.02, d + 0.01, 0.022), (0, -d / 2, levels[2] - 0.022), P.WOOD("oak"), bevel=0.004)
    return C.end("ShoeRack", loc, rot), levels


def console_table(loc, rot, w=1.0, d=0.32, h=0.8, wood="oak"):
    C.begin()
    C.box("top", (w, d, 0.026), (0, -d / 2, h - 0.026), P.WOOD(wood), bevel=0.004)
    C.box("drawer", (w - 0.12, d - 0.03, 0.085), (0, -d / 2, h - 0.115), P.WOOD(wood), bevel=0.002)
    C.sphere("knob", 0.012, (0, -d + 0.008, h - 0.072), P.METAL("black"))
    items = []
    for sx in (-1, 1):
        for sy in (0.03, d - 0.03):
            x = sx * (w / 2 - 0.035)
            items.append(((x - 0.011, -sy - 0.011, 0), (x + 0.011, -sy + 0.011, h - 0.026)))
        x = sx * (w / 2 - 0.035)
        items.append(((x - 0.009, -d + 0.03, 0.14), (x + 0.009, -0.03, 0.158)))
    items.append(((-w / 2 + 0.035, -d / 2 - 0.009, 0.14), (w / 2 - 0.035, -d / 2 + 0.009, 0.158)))
    C.add_bevel(C.boxes("legs", items, P.METAL("black")), 0.002)
    return C.end("ConsoleTable", loc, rot)


def coffee_maker(loc, rot=0.0):
    """Drip coffee machine with a half-full glass carafe (front towards -Y)."""
    C.begin()
    k = C.mat("CoffeeMakerBody", "#1b1b1d", rough=0.3, wear=0.2)
    C.box("column", (0.19, 0.1, 0.31), (0, 0.07, 0), k, bevel=0.012)
    C.box("head", (0.19, 0.24, 0.075), (0, 0.0, 0.245), k, bevel=0.012)
    C.box("base", (0.19, 0.24, 0.028), (0, 0.0, 0), k, bevel=0.008)
    C.cyl("hotplate", 0.075, 0.004, (0, -0.035, 0.028), P.METAL("steel"), segs=28)
    C.box("water_window", (0.004, 0.05, 0.14), (0.096, 0.07, 0.09), P.CLEAR("#d8e8f0", "WaterGauge"))
    C.cyl("button", 0.012, 0.006, (0.06, -0.12, 0.275), C.mat("LedOrange", "#ff8a2a", rough=0.3, emit=4.0, emit_color="#ff8a2a"),
          rot=(PI / 2, 0, 0), segs=16)
    r, h = 0.068, 0.13
    C.lathe("carafe", [(0, 0), (r * 0.9, 0), (r, 0.02), (r, h * 0.62), (r * 0.7, h * 0.92), (r * 0.72, h), (r * 0.7 - 0.003, h),
                       (r * 0.68, h * 0.92), (r - 0.003, h * 0.62), (r - 0.003, 0.022), (r * 0.88, 0.004), (0, 0.004)],
            (0, -0.035, 0.033), P.CLEAR(), segs=32, sub=1)
    C.cyl("coffee", r - 0.006, h * 0.4, (0, -0.035, 0.04), C.mat("Coffee", "#2a1708", rough=0.1), segs=28)
    C.cyl("carafe_lid", r * 0.74, 0.012, (0, -0.035, 0.033 + h), k, segs=28, bevel=0.003)
    C.pipe("carafe_handle", [(r - 0.002, -0.035, 0.033 + h * 0.9), (r + 0.04, -0.035, 0.033 + h * 0.85),
                             (r + 0.042, -0.035, 0.033 + h * 0.3), (r - 0.002, -0.035, 0.033 + h * 0.22)], 0.007, k)
    return C.end("CoffeeMaker", loc, rot)


def spice_jars(loc, face, n=6, pitch=0.062):
    """Row of small spice jars along the wall-parallel axis starting at loc."""
    cols = ["#b5472a", "#c9a227", "#5a6b2f", "#3a2a1c", "#d8cfb4", "#8a3a22", "#6f7f3a"]
    C.begin()
    for i in range(n):
        x = (i - (n - 1) / 2) * pitch
        C.lathe("spice_glass", [(0, 0), (0.022, 0), (0.022, 0.07), (0.018, 0.078), (0.0155, 0.078), (0.0195, 0.07),
                                (0.0195, 0.003), (0, 0.003)], (x, 0, 0), P.CLEAR(), segs=20, sub=0)
        C.cyl("spice", 0.019, 0.02 + 0.04 * R.random(), (x, 0, 0.004),
              C.mat("Spice_" + cols[i % len(cols)], cols[i % len(cols)], rough=0.9, bump=0.8, bump_scale=600), segs=16)
        C.cyl("spice_lid", 0.02, 0.016, (x, 0, 0.078), P.PL("#1c1c1c", 0.4), segs=20, bevel=0.002)
    return C.end("SpiceJars", loc, P.FACE[face])


def led_strip(name, p0, p1):
    """Under-cabinet lighting as a row of recessed puck lights (a visible fitting with
    its own hot spot) rather than one even glowing line."""
    n = max(2, int(round(math.dist(p0, p1) / 0.42)))
    puck = C.mat("LedPuck", "#fff2dc", rough=0.4, emit=12.0, emit_color="#ffe6c2")
    out = []
    for i in range(n):
        t = (i + 0.5) / n
        p = [a + (b - a) * t for a, b in zip(p0, p1)]
        out.append(C.cyl(name, 0.028, 0.006, (p[0], p[1], p[2] - 0.003), puck, segs=20))
        C.cyl(name + "_ring", 0.034, 0.004, (p[0], p[1], p[2]), P.METAL("steel"), segs=20)
    return out


def skincare(loc, face):
    """A few small bathroom bottles and a cream jar in a loose row."""
    C.begin()
    P.bottle((-0.1, 0, 0), 0.115, 0.02, "#f3ede4", "#c9a45c", name="Serum")
    P.bottle((-0.035, 0.01, 0), 0.14, 0.024, "#cfe0dc", "#ffffff", pump=True, name="Cleanser")
    C.lathe("cream_jar", [(0, 0), (0.03, 0), (0.032, 0.035), (0, 0.035)], (0.04, -0.005, 0), P.CER("#f4f1ea"), segs=24, sub=0)
    C.cyl("cream_lid", 0.033, 0.014, (0.04, -0.005, 0.035), P.METAL("brass"), segs=24, bevel=0.002)
    P.bottle((0.105, 0.008, 0), 0.09, 0.017, "#e8c7c0", "#ffffff", name="Toner")
    return C.end("Skincare", loc, P.FACE[face])

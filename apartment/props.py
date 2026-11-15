"""Small procedural props: crockery, books, toys, clothes, lamps, frames.

Every prop is built around the origin (front towards -Y, resting on z=0) and
then placed with (loc, rot). Colours are sRGB hex strings.
"""
import math

from . import art
from . import core as C

R = C.rng
PI = math.pi
FACE = {"S": 0.0, "E": PI / 2, "N": PI, "W": -PI / 2}   # direction a front (-Y) faces after rotation


# ------------------------------------------------------------- materials ---
def PL(color, rough=0.35):
    return C.mat("Plastic_{}_{}".format(color, rough), color, rough=rough)


def CER(color="#f3f2ee"):
    return C.mat("Ceramic_" + color, color, rough=0.08, coat=0.5, wear=0.12)


def FAB(tex, color=None, size=None, **kw):
    if color:
        return C.pbr("Fab_{}_{}".format(tex, color), tex, flat=color, size=size, sheen=0.25, **kw)
    return C.pbr("Fab_" + tex, tex, size=size, **kw)


def creased(m, strength=0.55, size=0.8):
    """Add fine creases to a fabric material (once): slept-in bedding and worn clothes are
    never smooth between their big folds."""
    if m.get("creased"):
        return m
    m["creased"] = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / size, 1.0 / size, 1.0)
    mp.inputs["Rotation"].default_value = (0, 0, 0.6)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    im = nt.nodes.new("ShaderNodeTexImage")
    im.image = C._img(art.creases(), True)
    nt.links.new(mp.outputs[0], im.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = 0.02
    nt.links.new(im.outputs["Color"], bp.inputs["Height"])
    if bsdf.inputs["Normal"].links:
        nt.links.new(bsdf.inputs["Normal"].links[0].from_socket, bp.inputs["Normal"])
    nt.links.new(bp.outputs[0], bsdf.inputs["Normal"])
    return m


def WOOD(kind="oak"):
    if kind == "oak":
        return C.pbr("WoodOak", "oak_veneer_01", size=1.83, value=1.25, rough_add=0.1)
    if kind == "walnut":
        return C.pbr("WoodWalnut", "walnut_veneer_02", size=1.0, rough_add=0.15, value=1.15)
    if kind == "light":
        return C.pbr("WoodLight", "oak_veneer_01", size=1.2, value=1.9, sat=0.7, rough_add=0.15)
    if kind == "ply":
        return C.pbr("WoodPly", "plywood", size=1.2, value=1.8, sat=0.8, rough_add=0.15)
    return C.pbr("WoodWhite", "oak_veneer_01", size=1.2, flat="#eeece6", rough_add=0.25, normal=0.5)


def METAL(kind="steel"):
    return {"steel": lambda: C.mat("BrushedSteel", "#c9c9c7", rough=0.26, metal=1.0, wear=0.09),
            "chrome": lambda: C.mat("Chrome", "#e6e6e6", rough=0.04, metal=1.0, wear=0.07),
            "black": lambda: C.mat("BlackMetal", "#1b1b1c", rough=0.35, metal=0.9, wear=0.2),
            "brass": lambda: C.mat("Brass", "#c9a45c", rough=0.2, metal=1.0, wear=0.2),
            "white": lambda: C.mat("WhiteMetal", "#eeeeea", rough=0.35, metal=0.0)}[kind]()


def CLEAR(color="#ffffff", name=None):
    return C.mat(name or "Clear_" + color, color, rough=0.02, trans=1.0, ior=1.45)


def PAPER():
    return C.mat("Paper", "#f4f2ec", rough=0.7)


def SCREEN_OFF():
    return C.mat("ScreenOff", "#050506", rough=0.05, coat=1.0, wear=0.2)


RUBBER = lambda: C.mat("Rubber", "#141414", rough=0.7)  # noqa: E731

TOY_COLORS = ["#e2392f", "#2f6fd0", "#f2b81f", "#3aa655", "#f08a24", "#8a4fb5", "#ef6aa0", "#31b7c4"]
BOOK_COLORS = ["#7a2e2a", "#2c4a6e", "#d9c7a0", "#39594a", "#c9772e", "#333333", "#e9e4d8", "#8c5b7a", "#bf3b33",
               "#3b7ea1", "#e0b83c"]
FABRIC_COLORS = ["#c9b79c", "#59636b", "#a34a3a", "#40574b", "#d8d2c6", "#2f3b52", "#b98a4a"]


def jit(v, a):
    return v + R.uniform(-a, a)


# --------------------------------------------------------------- kitchen ---
def mug(loc, color="#e8e4da", rot=None, full=True, r=0.041, h=0.095):
    C.begin()
    C.lathe("mug", [(0, 0), (r * 0.88, 0), (r, 0.01), (r, h), (r - 0.004, h), (r - 0.006, 0.014), (0, 0.012)],
            (0, 0, 0), CER(color), segs=28)
    C.pipe("handle", [(r - 0.004, 0, h * 0.78), (r + 0.026, 0, h * 0.72), (r + 0.028, 0, h * 0.36),
                      (r - 0.004, 0, h * 0.24)], 0.0055, CER(color))
    if full:
        C.cyl("drink", r - 0.006, 0.002, (0, 0, h * R.uniform(0.3, 0.8)), C.mat("Coffee", "#2a1708", rough=0.1),
              segs=24)
    return C.end("Mug", loc, R.uniform(0, 6.28) if rot is None else rot)


def plate(loc, r=0.13, color="#f1efe9", name="Plate"):
    return C.lathe(name, [(0, 0), (r * 0.62, 0), (r, 0.016), (r, 0.021), (r * 0.6, 0.007), (0, 0.007)], loc,
                   CER(color), segs=36)


def bowl(loc, r=0.075, h=0.065, color="#f1efe9", name="Bowl"):
    return C.lathe(name, [(0, 0), (r * 0.45, 0), (r, h), (r - 0.006, h), (r * 0.42, 0.009), (0, 0.009)], loc,
                   CER(color), segs=32)


def glass_cup(loc, r=0.034, h=0.11, fill=0.0, drink="#d9a441"):
    prof = [(0, 0), (r * 0.85, 0), (r, h), (r - 0.0025, h), (r * 0.83, 0.008), (0, 0.008)]
    if not fill:
        return C.lathe("Glass", prof, loc, CLEAR(), segs=28)
    C.begin()
    C.lathe("glass", prof, (0, 0, 0), CLEAR(), segs=28)
    C.cyl("drink", r * 0.86, h * fill, (0, 0, 0.009), C.mat("Drink_" + drink, drink, rough=0.05, trans=0.8), segs=24)
    return C.end("Glass", loc)


def text(body, loc, rot=(0, 0, 0), size=0.02, color="#222222", name="Print"):
    """Printed lettering as real (flat) geometry: a font curve converted to a mesh, lying in
    its local XY plane. Used for product labels, which is what makes packaging read as real."""
    import bpy
    cu = bpy.data.curves.new(name + "_font", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    tmp = bpy.data.objects.new(name + "_font", cu)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    me.materials.append(PL(color, 0.55))
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    ob.visible_shadow = False
    return C._link(ob)


def flat_bottle(loc, rot=0.0, w=0.07, d=0.042, h=0.2, color="#3f8fb0", cap="#ffffff", label="#f4f1ea",
                lines=(("NORDA", 0.013), ("shampoo", 0.0075)), ink="#1f2d3a", name="Shampoo"):
    """Oval-section toiletry bottle with a printed front label (front faces local -Y)."""
    C.begin()
    rr = d * 0.3
    C.soft_box("body", (w, d, h * 0.86), (0, 0, 0), PL(color, 0.28), round_=rr, cuts=3)
    C.cyl("cap", min(w, d) * 0.34, h * 0.14, (0, 0, h * 0.86), PL(cap), segs=20)
    lw, lh = w - 2.4 * rr, h * 0.44
    C.quad("label", lw, lh, (0, -d / 2 - 0.0004, h * 0.42), PL(label, 0.5), rot=(PI / 2, 0, 0))
    C.quad("stripe", lw, lh * 0.13, (0, -d / 2 - 0.0006, h * 0.42 + lh * 0.435), PL(ink, 0.5), rot=(PI / 2, 0, 0))
    z = h * 0.42 + lh * 0.2
    for body, size in lines:
        text(body, (0, -d / 2 - 0.0009, z), (PI / 2, 0, 0), size, ink)
        z -= size * 1.7
    z = min(z, h * 0.42 - lh * 0.12)
    for k in range(4):                       # the small print every real label carries
        bw = lw * R.uniform(0.45, 0.82)
        C.quad("print", bw, 0.0011, ((bw - lw * 0.86) / 2, -d / 2 - 0.0007, z), PL("#5a5a58", 0.6), rot=(PI / 2, 0, 0))
        z -= 0.0034
    C.quad("barcode", lw * 0.3, lh * 0.09, (lw * 0.28, -d / 2 - 0.0007, h * 0.42 - lh * 0.42), PL("#222222", 0.6), rot=(PI / 2, 0, 0))
    return C.end(name, loc, rot)


def carton(loc, rot=0.0, size=(0.19, 0.06, 0.27), color="#e2ad2f", band="#7a2f1d", lines=(("HAVRE", 0.032), ("crunch", 0.02)),
           ink="#fbf6e6", cap=None, name="CerealBox"):
    """Printed cardboard pack (cereal box, milk carton): coloured board, a contrasting band, lettering."""
    w, d, h = size
    C.begin()
    C.box("pack", size, (0, 0, 0), PL(color, 0.55), bevel=0.0025)
    C.quad("band", w * 0.999, h * 0.34, (0, -d / 2 - 0.0004, h * 0.6), PL(band, 0.5), rot=(PI / 2, 0, 0))
    z = h * 0.66
    for body, sz in lines:
        text(body, (0, -d / 2 - 0.0009, z), (PI / 2, 0, 0), sz, ink)
        z -= sz * 1.6
    text("net 500 g", (w * 0.22, -d / 2 - 0.0009, h * 0.1), (PI / 2, 0, 0), 0.007, "#3a2a1a")
    if cap:
        C.cyl("cap", 0.014, 0.012, (w * 0.2, 0, h), PL(cap), segs=18)
    return C.end(name, loc, rot)


def bottle(loc, h=0.2, r=0.032, color="#e9e2d0", cap="#ffffff", pump=False, clear=False, name="Bottle"):
    C.begin()
    m = CLEAR(color, "ClearPlastic_" + color) if clear else PL(color, 0.3)
    C.lathe("body", [(0, 0), (r * 0.92, 0), (r, 0.008), (r, h * 0.68), (r * 0.5, h * 0.82), (r * 0.42, h * 0.86),
                     (0, h * 0.86)], (0, 0, 0), m, segs=24)
    C.cyl("cap", r * 0.46, h * 0.14, (0, 0, h * 0.86), PL(cap), segs=20)
    if pump:
        C.cyl("stem", 0.004, h * 0.12, (0, 0, h), PL(cap), segs=10)
        C.box("nozzle", (0.012, 0.045, 0.012), (0, -0.012, h * 1.12), PL(cap), bevel=0.003)
    return C.end(name, loc, R.uniform(0, 6.28))


def jar(loc, h=0.14, r=0.045, content="#c9a56a", lid="#b33a2e", fill=0.7):
    C.begin()
    C.lathe("jar", [(0, 0), (r, 0), (r, h * 0.9), (r * 0.85, h), (r * 0.85 - 0.003, h), (r - 0.003, h * 0.9),
                    (r - 0.003, 0.004), (0, 0.004)], (0, 0, 0), CLEAR(), segs=24, sub=0)
    C.cyl("content", r - 0.004, h * 0.9 * fill, (0, 0, 0.005), C.mat("Food_" + content, content, rough=0.7,
                                                                   bump=0.6, bump_scale=120), segs=20)
    C.cyl("lid", r * 0.9, 0.014, (0, 0, h), PL(lid, 0.4), segs=24, bevel=0.002)
    return C.end("Jar", loc)


def box_pack(loc, size=(0.19, 0.06, 0.27), label=0, rot=0.0, name="Pack"):
    """Printed cardboard pack (cereal, detergent, board game)."""
    C.begin()
    sx, sy, sz = size
    C.box("box", size, (0, 0, 0), C.mat("Cardboard", "#b99a6b", rough=0.75))
    lm = art.label(label)
    for s in (-1, 1):
        C.quad("label", sx * 0.98, sz * 0.98, (0, s * (sy / 2 + 0.0006), sz / 2), lm,
               rot=(PI / 2, 0, 0 if s < 0 else PI))
    return C.end(name, loc, rot)


# ------------------------------------------------------------ books/paper ---
def book(loc, rot=0.0, size=(0.15, 0.215, 0.026), color=None):
    """Closed book lying flat."""
    w, d, t = size
    color = color or R.choice(BOOK_COLORS)
    C.begin()
    c = 0.0025
    C.boxes("cover", [((-w / 2, -d / 2, 0), (w / 2, d / 2, c)), ((-w / 2, -d / 2, t - c), (w / 2, d / 2, t)),
                      ((-w / 2, -d / 2, 0), (-w / 2 + c, d / 2, t))], PL(color, 0.6))
    C.boxes("pages", [((-w / 2 + c, -d / 2 + 0.004, c), (w / 2 - 0.004, d / 2 - 0.004, t - c))],
            C.mat("Pages", "#eee9dc", rough=0.8))
    return C.end("Book", loc, rot)


def book_stack(loc, n=3, rot=0.0):
    z = loc[2]
    for i in range(n):
        s = (R.uniform(0.13, 0.2), R.uniform(0.19, 0.27), R.uniform(0.014, 0.035))
        book((jit(loc[0], 0.008), jit(loc[1], 0.008), z), rot + R.uniform(-0.25, 0.25), s)
        z += s[2]
    return z


_BOOKS = []


def _vary_cover(m):
    """Give every placed copy of a scanned book its own cover hue and tone (per-object random)."""
    if m is None or m.get("hue_var") or "paper" in m.name.lower() or not m.node_tree:
        return
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None or not bsdf.inputs["Base Color"].links:
        return
    m["hue_var"] = 1
    src = bsdf.inputs["Base Color"].links[0].from_socket
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hue = nt.nodes.new("ShaderNodeMapRange")
    hue.inputs["To Min"].default_value = 0.45       # a nudge, not a repaint: big shifts turned spines into flat colour blocks
    hue.inputs["To Max"].default_value = 0.55
    nt.links.new(oi.outputs["Random"], hue.inputs["Value"])
    frac = nt.nodes.new("ShaderNodeMath")
    frac.operation = "MULTIPLY"
    frac.inputs[1].default_value = 7.31
    nt.links.new(oi.outputs["Random"], frac.inputs[0])
    fr2 = nt.nodes.new("ShaderNodeMath")
    fr2.operation = "FRACT"
    nt.links.new(frac.outputs[0], fr2.inputs[0])
    val = nt.nodes.new("ShaderNodeMapRange")
    val.inputs["To Min"].default_value = 0.78
    val.inputs["To Max"].default_value = 1.08
    nt.links.new(fr2.outputs[0], val.inputs["Value"])
    nt.links.new(hue.outputs[0], hsv.inputs["Hue"])
    nt.links.new(val.outputs[0], hsv.inputs["Value"])
    hsv.inputs["Saturation"].default_value = 1.0
    nt.links.new(src, hsv.inputs["Color"])
    nt.links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])


def _book_pool():
    if not _BOOKS:
        for aid in ("decorative_book_set_01", "book_encyclopedia_set_01"):
            for p in C.load_asset(aid):
                d = p["hi"] - p["lo"]
                if "book" in p["name"].lower() and d.x < 0.08 and d.z > 0.15:
                    _BOOKS.append((aid, "^" + p["name"].replace(".", r"\.") + "$", d))
                    for mbr in p["members"]:       # same scans, different editions: shift each copy's cover colour
                        for sl in getattr(mbr, "material_slots", []):
                            _vary_cover(sl.material)
    return _BOOKS


def book_row(loc, length, rot=0.0, fill=1.0):
    """Upright books along local +X starting at loc (against the shelf side). The free
    end is always held up: a book leans on the row, or a steel bookend stops it."""
    pool = _book_pool()
    C.begin()
    x = 0.0
    last = None
    while x < length * fill:
        aid, part, d = R.choice(pool)
        if x + d.x > length:
            break
        k = R.choice((0.84, 0.9, 0.95, 1.0, 1.0, 1.05, 1.1))          # a shelf of books is never one height
        last = C.place(aid, (x + d.x * k / 2, R.uniform(-0.012, 0.004), 0), part=part, scale=k, tilt=(0, R.uniform(-0.012, 0.012)))
        x += d.x * k + R.choice((0.0008, 0.0015, 0.003))
    if last is not None:
        if length - x > 0.09 and R.random() < 0.6:
            aid, part, d = R.choice(pool)
            lean = math.radians(R.uniform(12, 20))
            C.place(aid, (x + d.x / 2 + d.z * math.sin(lean) * 0.5, 0, 0), part=part, tilt=(0, -lean))
        else:
            C.add_bevel(C.boxes("bookend", [((x + 0.001, -0.055, 0), (x + 0.003, 0.055, 0.15)),
                                            ((x + 0.001, -0.055, 0), (x + 0.09, 0.055, 0.002))], METAL("black")), 0.0008)
    return C.end("BookRow", loc, rot)


def paper(loc, rot=0.0, w=0.21, h=0.297, material=None, name="Paper"):
    return C.quad(name, w, h, loc, material or PAPER(), rot=(0, 0, rot))


def papers(loc, n=4, spread=0.05, rot=0.0):
    for i in range(n):
        paper((jit(loc[0], spread), jit(loc[1], spread), loc[2] + 0.0006 * (i + 1)), rot + R.uniform(-0.5, 0.5))


def drawing(loc, i=0, rot=0.0, on_wall=None, w=0.297, h=0.21):
    """Child's drawing lying flat, or taped to a wall if on_wall is a FACE key. On a
    wall the sheet bows off the surface with lifted corners and two strips of tape."""
    m = art.kid_drawing(i)
    if on_wall is None:
        return C.quad("KidDrawing", w, h, loc, m, rot=(0, 0, rot))
    lift = [R.uniform(0.003, 0.012) for _ in range(4)]

    def fn(u, v):
        c = (lift[0] * (1 - u) * (1 - v) + lift[1] * u * (1 - v) + lift[2] * (1 - u) * v * 0.3 + lift[3] * u * v * 0.3)
        bow = 0.004 * math.sin(u * PI) * (1 - v)
        return ((u - 0.5) * w, -(0.0015 + c + bow), (v - 0.5) * h)

    C.begin()
    C.grid("sheet", 8, 6, fn, (0, 0, 0), m, uv01=True)
    tape = C.mat("Tape", "#e9e2c4", rough=0.35, alpha=0.75)
    for sx in (-0.3, 0.32):
        C.box("tape", (0.05, 0.0012, 0.018), (sx * w, -0.003, h / 2 - 0.006), tape, anchor=(0, 0, 0)).rotation_euler[1] = R.uniform(-0.3, 0.3)
    g = C.end("KidDrawing", loc, FACE[on_wall])
    g.rotation_euler[1] = R.uniform(-0.05, 0.05)
    return g


def frame(loc, face="S", w=0.4, h=0.5, i=0, color="#1c1c1c", kid=False, matboard=True):
    """Framed print hanging on a wall; `loc` is the centre of its back."""
    C.begin()
    b, t = 0.02, 0.022
    C.boxes("frame", [((-w / 2, -t, -h / 2), (-w / 2 + b, 0, h / 2)), ((w / 2 - b, -t, -h / 2), (w / 2, 0, h / 2)),
                      ((-w / 2, -t, -h / 2), (w / 2, 0, -h / 2 + b)), ((-w / 2, -t, h / 2 - b), (w / 2, 0, h / 2))],
            C.mat("Frame_" + color, color, rough=0.4))
    C.quad("back", w - 0.01, h - 0.01, (0, -0.006, 0), C.mat("Matboard", "#f3f1ea", rough=0.8), rot=(PI / 2, 0, 0))
    m = 0.055 if matboard else 0.0
    pm = art.kid_drawing(i) if kid else art.wall_print(i)
    C.quad("print", w - 2 * b - 2 * m, h - 2 * b - 2 * m, (0, -0.008, 0), pm, rot=(PI / 2, 0, 0))
    g = C.end("Frame", loc, FACE[face])
    g.rotation_euler[1] = R.uniform(-0.012, 0.012)          # pictures never hang perfectly level
    return g


# ------------------------------------------------------------------ toys ---
BLOCK_COLORS = ["#b8523f", "#41688a", "#cf9f35", "#5c8660", None, None, None]


def blocks(loc, n=8, spread=0.25):
    """Wooden building blocks: beech cubes and bricks, some stained, worn edges."""
    for i in range(n):
        s = R.choice((0.04, 0.045, 0.05))
        col = R.choice(BLOCK_COLORS)
        m = C.pbr("BlockWood_{}".format(col), "oak_veneer_01", size=0.35, tint=col, tint_fac=0.85 if col else 0.0,
                  value=1.7, sat=0.7, rough_add=0.25)
        size = (s, s * R.choice((1, 1, 2)), s)
        x, y, z = jit(loc[0], spread), jit(loc[1], spread), loc[2]
        C.box("ToyBlock", size, (x, y, z), m, rot=R.uniform(0, 3.14), bevel=0.0045)
        if R.random() < 0.3:
            C.box("ToyBlock", (s, s, s), (x + 0.004, y, z + s), m, rot=R.uniform(0, 3.14), bevel=0.0045)


def teddy(loc, rot=0.0, scale=1.0, color=None):
    """Sitting plush bear: metaball body so limbs blend into the torso, curly fleece
    texture, glossy bead eyes."""
    C.begin()
    f = C.pbr("TeddyFleece_{}".format(color), "curly_teddy_natural", size=0.09, tint=color, tint_fac=0.75 if color else 0.0,
              normal=2.0, sheen=0.6, value=1.05)
    k = C.mat("ToyEye", "#0c0c0c", rough=0.08, coat=1.0)
    elems = [(0, 0, 0.1, 0.085, (1.0, 0.9, 1.15)), (0, -0.012, 0.25, 0.07), (0, -0.062, 0.238, 0.032),
             (-0.052, 0, 0.312, 0.026), (0.052, 0, 0.312, 0.026),
             (-0.092, -0.03, 0.15, 0.03, (0.9, 1.0, 1.9)), (0.092, -0.03, 0.15, 0.03, (0.9, 1.0, 1.9)),
             (-0.055, -0.09, 0.04, 0.034, (1.0, 1.9, 1.0)), (0.055, -0.09, 0.04, 0.034, (1.0, 1.9, 1.0))]
    body = C.blob("plush", elems, (0, 0, 0), f, height=0.33)
    C.lumpy(body, 0.006, 0.02, 2)
    C.fur(body)
    C.sphere("nose", 0.009, (0, -0.098, 0.242), C.mat("ToyNose", "#2a1a12", rough=0.4))
    for sx in (-1, 1):
        C.sphere("eye", 0.0075, (sx * 0.027, -0.074, 0.268), k)
    g = C.end("Teddy", loc, rot)
    g.scale = (scale,) * 3
    return g


def toy_car(loc, rot=0.0, color=None):
    color = color or R.choice(TOY_COLORS)
    C.begin()
    C.soft_box("body", (0.12, 0.055, 0.028), (0, 0, 0.012), PL(color, 0.25), round_=0.01, cuts=2)
    C.soft_box("cabin", (0.06, 0.048, 0.024), (-0.008, 0, 0.038), PL("#bfe3ee", 0.1), round_=0.01, cuts=2)
    for sx in (-0.038, 0.038):
        for sy in (-0.03, 0.03):
            C.cyl("wheel", 0.014, 0.012, (sx, sy - 0.006, 0.014), RUBBER(), rot=(-PI / 2, 0, 0), segs=16)
    return C.end("ToyCar", loc, rot)


def ball(loc, r=0.08, color=None):
    return C.sphere("Ball", r, (loc[0], loc[1], loc[2] + r), PL(color or R.choice(TOY_COLORS), 0.3))


def stack_rings(loc):
    C.begin()
    C.cyl("base", 0.06, 0.012, (0, 0, 0), PL("#f4f1e6"), bevel=0.003)
    C.cyl("pole", 0.012, 0.17, (0, 0, 0.01), PL("#f4f1e6"), r2=0.007, segs=16)
    z = 0.03
    for i, col in enumerate(TOY_COLORS[:5]):
        r = 0.05 - i * 0.006
        C.ring("ring", r, 0.014, (0, 0, z), PL(col, 0.3))
        z += 0.027
    return C.end("StackRings", loc)


def crayons(loc, n=6, spread=0.06):
    for i in range(n):
        C.cyl("Crayon", 0.0045, 0.085, (jit(loc[0], spread), jit(loc[1], spread), loc[2] + 0.0045),
              PL(TOY_COLORS[i % len(TOY_COLORS)], 0.6), rot=(PI / 2, 0, R.uniform(0, 3.14)), segs=10)


def picture_book(loc, rot=0.0, i=0):
    C.begin()
    C.box("board", (0.2, 0.2, 0.012), (0, 0, 0), PL(R.choice(TOY_COLORS), 0.5), bevel=0.003)
    C.quad("cover", 0.19, 0.19, (0, 0, 0.0126), art.kid_drawing(i), rot=(0, 0, 0))
    return C.end("PictureBook", loc, rot)


def scooter(loc, rot=0.0, color="#35b5a6"):
    C.begin()
    C.box("deck", (0.12, 0.42, 0.022), (0, 0.02, 0.05), PL(color, 0.3), bevel=0.008)
    C.box("grip", (0.09, 0.3, 0.002), (0, 0.04, 0.072), RUBBER())
    for sx in (-0.085, 0.085):
        C.cyl("wheel", 0.05, 0.024, (sx - 0.012, -0.2, 0.05), PL("#f1f1f1", 0.3), rot=(0, PI / 2, 0), segs=24,
              bevel=0.006)
    C.cyl("wheel_r", 0.04, 0.03, (-0.015, 0.25, 0.04), PL("#f1f1f1", 0.3), rot=(0, PI / 2, 0), segs=24, bevel=0.006)
    C.pipe("column", [(0, -0.19, 0.06), (0, -0.2, 0.3), (0, -0.21, 0.66)], 0.013, METAL("steel"))
    C.pipe("bar", [(-0.14, -0.21, 0.66), (0.14, -0.21, 0.66)], 0.011, METAL("steel"), smooth=False)
    for s in (-1, 1):
        C.pipe("hand", [(s * 0.08, -0.21, 0.66), (s * 0.15, -0.21, 0.66)], 0.015, PL(color, 0.5), smooth=False)
    return C.end("KidScooter", loc, rot)


# --------------------------------------------------------- clothes / soft ---
def _shoe(size, color, sole, kind="sneaker"):
    """One shoe, toes towards -Y, built by lofting cross-sections heel -> toe."""
    Ln, W = size, size * 0.36
    prof = [  # t along length, half-width factor, height factor (low-top trainer)
        (0.0, 0.26, 0.21), (0.05, 0.40, 0.25), (0.18, 0.46, 0.265), (0.34, 0.47, 0.255), (0.46, 0.49, 0.225),
        (0.62, 0.52, 0.185), (0.78, 0.50, 0.15), (0.9, 0.42, 0.125), (0.97, 0.28, 0.10), (1.0, 0.12, 0.07)]
    if kind == "boot":
        prof = [(t, w, h * (2.6 if t < 0.4 else 1.25)) for t, w, h in prof]
    sole_h = size * 0.075
    upper, base = [], []
    n = 14
    for t, wf, hf in prof:
        y = Ln / 2 - t * Ln
        w, h = W * wf, size * hf
        ring, ring2 = [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            cx, sz = math.cos(a), math.sin(a)
            x = w * math.copysign(abs(cx) ** 0.6, cx)
            z = h / 2 + (h / 2) * math.copysign(abs(sz) ** 0.6, sz)
            ring.append((x, y, sole_h * 0.7 + z))
            ring2.append((x * 1.07, y * 1.02, sole_h / 2 + (sole_h / 2) * math.copysign(abs(sz) ** 0.4, sz)))
        upper.append(ring)
        base.append(ring2)
    fab = FAB("denim_fabric", color, size=0.06, normal=1.8) if kind != "boot" else C.mat("Leather_" + color, color, rough=0.45,
                                                                                         wear=0.2, bump=0.3, bump_scale=900)
    rub = PL(sole, 0.55)
    C.loft("sole", base, (0, 0, 0), rub, sub=1)
    C.loft("upper", upper, (0, 0, 0), fab, sub=2)
    zu = sole_h * 0.7
    top = size * prof[2][2]
    oy = Ln / 2 - 0.19 * Ln
    C.sphere("opening", size * 0.125, (0, oy, zu + top - 0.003), C.mat("ShoeInside", "#141414", rough=0.9), scale=(0.9, 1.3, 0.14))
    collar = C.ring("collar", size * 0.125, size * 0.022, (0, oy, zu + top - 0.004), fab)
    collar.scale = (0.95, 1.36, 1.0)
    C.box("heel_tab", (size * 0.07, size * 0.012, size * 0.07), (0, Ln / 2 - 0.006, zu + top - size * 0.03), fab, bevel=0.002)
    if kind == "sneaker":
        # rubber toe cap + midsole stripe
        cap = [[(x * 1.035, y - 0.002, z * 1.03 + 0.0005) for (x, y, z) in ring] for ring in upper[-4:]]
        C.loft("toe_cap", cap, (0, 0, 0), rub, sub=2)
        t = C.soft_box("tongue", (W * 0.5, size * 0.24, size * 0.035), (0, Ln / 2 - 0.37 * Ln, zu + size * 0.235), fab,
                       round_=size * 0.015, cuts=3)
        t.rotation_euler = (-0.4, 0, 0)
        for k in range(5):
            tt = 0.44 + k * 0.058
            hz = zu + size * (0.24 - (tt - 0.44) * 0.36)
            lace = C.box("lace", (W * 0.66, size * 0.016, size * 0.012), (0, Ln / 2 - tt * Ln, hz), PL("#f4f4f2", 0.8), bevel=0.001)
            lace.rotation_euler = (-0.33, 0, 0.25 if k % 2 else -0.25)
        for sx in (-1, 1):
            bow = C.ring("bow", size * 0.045, size * 0.007, (sx * size * 0.05, Ln / 2 - 0.42 * Ln, zu + size * 0.255),
                         PL("#f4f4f2", 0.8), rot=(0.4, sx * 0.5, 0))
            bow.scale = (1.0, 0.55, 1.0)
    else:
        C.pipe("welt", [(x * 1.02, y, zu + 0.002) for (x, y, z) in [r[0] for r in upper]] +
               [(x * 1.02, y, zu + 0.002) for (x, y, z) in [r[len(r) // 2] for r in upper][::-1]], size * 0.008,
               C.mat("BootWelt", "#1a1410", rough=0.6), cyclic=True)


def shoes(loc, rot=0.0, size=0.28, color="#e8e6e1", sole="#f4f4f2", gap=0.11, kind="sneaker", single=False):
    """A pair, toes towards -Y, kicked off slightly out of line."""
    C.begin()
    for s in ((-1,) if single else (-1, 1)):
        C.begin()
        _shoe(size, color, sole, kind)
        C.end("Shoe", (s * gap / 2 + R.uniform(-0.008, 0.008), R.uniform(-0.025, 0.025), 0), R.uniform(-0.12, 0.12))
    return C.end("Shoes", loc, rot)


def slippers(loc, rot=0.0, color="#7c8a97"):
    C.begin()
    for s in (-1, 1):
        C.begin()
        C.soft_box("sole", (0.095, 0.26, 0.018), (0, 0, 0), FAB("knitted_fleece", "#d9cdb8", size=0.1), round_=0.008,
                   cuts=3)
        C.sphere("strap", 0.06, (0, -0.045, 0.016), FAB("knitted_fleece", color, size=0.1), scale=(0.82, 1.3, 0.75))
        C.end("Slipper", (s * 0.06, R.uniform(-0.03, 0.03), 0), R.uniform(-0.25, 0.25))
    return C.end("Slippers", loc, rot)


def backpack(loc, rot=0.0, color="#2f4a66"):
    """Soft daypack: body and front pocket are fabric shells inflated by cloth pressure."""
    C.begin()
    f = FAB("denim_fabric", color, size=0.1, normal=1.8)
    k = PL("#1a1a1a", 0.6)
    C.inflate("body", (0.27, 0.11, 0.4), (0, 0.0, 0.2), f, pressure=1.1, gravity=0.0, frames=20, cuts=12, shrink=-0.07, bend=0.1)
    C.inflate("pocket", (0.2, 0.03, 0.17), (0, -0.075, 0.13), f, pressure=0.8, gravity=0.0, frames=16, cuts=8, shrink=-0.06)
    C.pipe("zip", [(-0.12, -0.035, 0.3), (-0.07, -0.06, 0.37), (0.07, -0.06, 0.37), (0.12, -0.035, 0.3)], 0.003, k)
    C.pipe("handle", [(-0.04, 0.02, 0.4), (-0.03, 0.02, 0.46), (0.03, 0.02, 0.46), (0.04, 0.02, 0.4)], 0.008, k)
    for s_ in (-1, 1):
        C.box("strap", (0.045, 0.01, 0.34), (s_ * 0.075, 0.075, 0.04), PL("#1a1a1a", 0.7), bevel=0.004)
    return C.end("Backpack", loc, rot)


def coat(loc, face="S", color="#39424e", length=0.95, width=0.5):
    """Coat hanging flat against a wall; loc = hook point (top centre, on the wall)."""
    C.begin()
    f = FAB("poly_wool_herringbone", color, size=0.25)
    b = C.soft_box("body", (width, 0.13, length), (0, -0.075, -length), f, round_=0.05, cuts=8)
    C.lumpy(b, 0.02, 0.2)
    for s in (-1, 1):
        a = C.soft_box("sleeve", (0.13, 0.11, length * 0.68), (s * (width / 2 + 0.03), -0.07, -length * 0.78), f,
                       rot=0.0, round_=0.045, cuts=6)
        a.rotation_euler = (0, s * -0.1, 0)
        C.lumpy(a, 0.015, 0.2)
    C.soft_box("collar", (0.22, 0.1, 0.1), (0, -0.07, -0.08), f, round_=0.04, cuts=3)
    return C.end("Coat", loc, FACE[face])


def tote(loc, face="S", color="#d8cfb9"):
    C.begin()
    f = FAB("rough_linen", color, size=0.2)
    b = C.soft_box("bag", (0.36, 0.07, 0.4), (0, -0.05, -0.62), f, round_=0.02, cuts=6)
    C.lumpy(b, 0.015, 0.15)
    for s in (-0.08, 0.08):
        C.pipe("strap", [(s, -0.05, -0.23), (s * 0.5, -0.02, -0.02), (0, -0.012, 0.0)], 0.007, f)
    return C.end("ToteBag", loc, FACE[face])


def towel_folded(loc, rot=0.0, color="#d9d3c5", n=2, size=(0.34, 0.24, 0.04)):
    """Stack of folded towels/laundry; each piece is a strip folded on itself, so the
    stack shows fold loops on one side and loose layers on the other."""
    f = FAB("terry_cloth", color, size=0.18, normal=1.8)
    z = loc[2]
    for i in range(n):
        hgt = max(size[2], 0.05)                 # a folded towel is a few centimetres thick, not a sheet
        t = hgt / 2.55
        o = C.folded("TowelFolded", size[0], size[1], (jit(loc[0], 0.01), jit(loc[1], 0.01), z), f, layers=2, t=t,
                     rot=rot + (PI if i % 2 else 0.0) + R.uniform(-0.08, 0.08))
        z += hgt * 0.97
    return z


def towel_hanging(loc, face="S", w=0.42, front=0.5, back=0.3, color="#c9d3d6", gap=0.022, tex="terry_cloth", colliders=()):
    """Towel thrown over a rail (cloth-simulated). loc = rail centre; the longer
    `front` side hangs towards `face`."""
    return C.drape_over("TowelHanging", w, front, back, loc, FACE[face], creased(FAB(tex, color, size=0.16, normal=2.0), 0.3, 0.5),
                        colliders)


def cloth_pile(loc, size=(0.4, 0.3, 0.14), color=None, rot=0.0, seed=1, tex="cotton_jersey", name="Clothes"):
    """Crumpled fabric: a soft slab displaced at two scales, then smoothed, so it
    reads as loose folds rather than foam or spikes."""
    o = C.soft_box(name, size, loc, FAB(tex, color or R.choice(FABRIC_COLORS), size=0.25), rot=rot,
                   round_=min(size) * 0.45, cuts=12, puff=0.5)
    big = max(size[0], size[1])
    C.lumpy(o, size[2] * 0.9, big * 0.3, seed)
    C.lumpy(o, size[2] * 0.3, big * 0.12, seed + 1)
    C.subsurf(o, 2)
    return o


def cushion(loc, rot=0.0, s=0.45, color="#b4664a", tilt=0.0, tex="rough_linen", thick=0.16):
    """Scatter cushion: a fabric envelope inflated by cloth pressure, so it has a seam
    edge, puckered corners and a soft crown."""
    m = FAB(tex, color, size=0.22, normal=1.8) if color else FAB(tex, size=0.22, normal=1.8)
    o = C.inflate("Cushion", (s, s, 0.03), loc, m, pressure=2.6 * (thick / 0.16), gravity=0.0, frames=24, cuts=14, shrink=-0.09,
                  bend=0.15)
    o.rotation_euler = (tilt, 0, rot)
    return o


def blanket(name, w, l, loc, rot=0.0, color="#b9a98f", tex="knitted_fleece", z_amp=0.012, thick=0.012, fn=None,
            size=0.3):
    """Flat throw/rug with gentle waviness (or a custom height function)."""
    def surf(u, v):
        x, y = (u - 0.5) * w, (v - 0.5) * l
        z = fn(x, y) if fn else z_amp * (math.sin(x * 9 + 1.3) * math.cos(y * 7) + 0.5 * math.sin(y * 13 + x * 5))
        return (x, y, z)
    m = FAB(tex, color, size=size) if color else FAB(tex, size=size)
    return C.grid(name, max(8, int(w * 14)), max(8, int(l * 14)), surf, loc, m, rot=rot, thick=thick, sub=1)


def rug(name, w, l, loc, rot=0.0, color=None, tex="wool_boucle", thick=0.012, size=0.35, kind=None, curl=0.012, ruck=()):
    """Floor rug as a slightly uneven thick sheet (rippled surface, one lifted corner,
    soft edge) rather than a perfect slab. With `kind` it carries woven artwork."""
    ph = R.uniform(0, 6.28)

    def fn(u, v):
        x, y = (u - 0.5) * w, (v - 0.5) * l
        z = thick / 2 + 0.0016 * (math.sin(x * 7 + ph) * math.cos(y * 5 + ph) + 0.6 * math.sin(y * 11 + x * 3))
        d = math.hypot(u - 1.0, v - 0.0) * max(w, l)          # distance from one corner
        z += curl * math.exp(-d / 0.09)
        for v0, amp in ruck:                                   # walked-on runners bunch into a ridge across their width
            z += amp * math.exp(-(((v - v0) + 0.012 * math.sin(u * 5 + ph)) / 0.016) ** 2)
        edge = 0.004 * math.sin((u + v) * 40 + ph)             # hand-finished edge, not laser straight
        return (x + (edge if v in (0.0, 1.0) else 0.0), y + (edge if u in (0.0, 1.0) else 0.0), z)

    C.begin()
    nu, nv = max(10, int(w * 12)), max(10, int(l * (40 if ruck else 12)))
    if kind:
        m = art.rug(kind, w / l, (w / 0.12, l / 0.12))
        C.grid("weave", nu, nv, fn, (0, 0, 0), m, thick=thick, sub=1, uv01=True)
        if kind == "kilim":
            n = int(w / 0.014)
            C.boxes("fringe", [((-w / 2 + (i + 0.5) * w / n - 0.003 + R.uniform(-0.002, 0.002), sy * (l / 2 - 0.004), 0.001),
                                (-w / 2 + (i + 0.5) * w / n + 0.003, sy * (l / 2 + R.uniform(0.035, 0.065)), 0.005))
                               for sy in (-1, 1) for i in range(n)], C.mat("RugFringe", "#d9cfb8", rough=0.95))
    else:
        m = FAB(tex, color, size=size, normal=2.5) if color else FAB(tex, size=size, normal=2.5)
        C.grid("pile", nu, nv, fn, (0, 0, 0), m, thick=thick, sub=1)
    return C.end(name, loc, rot)


# ------------------------------------------------------------ electronics ---
def remote(loc, rot=0.0):
    return C.box("Remote", (0.045, 0.17, 0.017), loc, PL("#151515", 0.45), rot=rot, bevel=0.006)


def phone(loc, rot=0.0):
    C.begin()
    C.box("body", (0.072, 0.15, 0.008), (0, 0, 0), PL("#1b1c1f", 0.3), bevel=0.0035)
    C.quad("screen", 0.066, 0.143, (0, 0, 0.0083), SCREEN_OFF())
    return C.end("Phone", loc, rot)


def laptop(loc, rot=0.0, open_deg=105, kind="code"):
    C.begin()
    al = C.mat("Aluminium", "#aeb1b6", rough=0.35, metal=1.0)
    C.box("base", (0.32, 0.22, 0.012), (0, 0, 0), al, bevel=0.004)
    C.box("keys", (0.27, 0.105, 0.001), (0, 0.035, 0.012), PL("#161616", 0.5))
    C.box("pad", (0.1, 0.065, 0.0006), (0, -0.065, 0.012), C.mat("Trackpad", "#9da0a5", rough=0.25, metal=1.0))
    C.begin()
    C.box("lid", (0.32, 0.007, 0.215), (0, 0, 0), al, bevel=0.003)
    C.quad("screen", 0.3, 0.19, (0, -0.0042, 0.11), art.screen(kind), rot=(PI / 2, 0, 0))
    lid = C.end("lid", (0, 0.108, 0.012))
    lid.rotation_euler = (math.radians(-(open_deg - 90)), 0, 0)
    return C.end("Laptop", loc, rot)


def monitor(loc, rot=0.0, w=0.61, h=0.36, kind="desktop"):
    C.begin()
    bm = PL("#141416", 0.4)
    C.box("foot", (0.24, 0.17, 0.012), (0, 0.03, 0), bm, bevel=0.005)
    C.box("neck", (0.05, 0.03, 0.14), (0, 0.06, 0.01), bm, bevel=0.005)
    C.box("panel", (w, 0.035, h), (0, 0.03, 0.12), bm, bevel=0.006)
    C.quad("screen", w - 0.02, h - 0.03, (0, 0.012, 0.12 + h / 2 + 0.005), SCREEN_OFF() if kind == "off" else art.screen(kind),
           rot=(PI / 2, 0, 0))
    return C.end("Monitor", loc, rot)


def keyboard(loc, rot=0.0):
    C.begin()
    C.box("body", (0.36, 0.125, 0.014), (0, 0, 0), PL("#d9d9d6", 0.4), bevel=0.004)
    items = []
    for r in range(5):
        for c in range(14):
            x, y = -0.166 + c * 0.0255, -0.048 + r * 0.024
            items.append(((x - 0.0105, y - 0.0095, 0.014), (x + 0.0105, y + 0.0095, 0.019)))
    C.boxes("keys", items, PL("#f2f2ef", 0.45))
    return C.end("Keyboard", loc, rot)


def mouse(loc, rot=0.0):
    return C.sphere("Mouse", 0.05, (loc[0], loc[1], loc[2] + 0.004), PL("#1c1c1e", 0.35), scale=(0.6, 1.0, 0.36),
                    rot=(0, 0, rot))


def headphones(loc, rot=0.0):
    C.begin()
    k = PL("#1a1a1c", 0.45)
    for s in (-1, 1):
        C.cyl("cup", 0.042, 0.03, (s * 0.085, 0, 0.045), k, rot=(0, s * PI / 2, 0), bevel=0.008, segs=24)
    C.pipe("band", [(-0.085, 0, 0.06), (-0.075, 0, 0.14), (0, 0, 0.185), (0.075, 0, 0.14), (0.085, 0, 0.06)], 0.008, k)
    g = C.end("Headphones", loc, rot)
    g.rotation_euler = (PI / 2 - 0.1, 0, rot)
    return g


def tv(loc, face="E", w=1.24, h=0.72):
    """Wall-mounted flat TV; loc = centre of the back."""
    C.begin()
    C.box("panel", (w, 0.035, h), (0, -0.03, -h / 2), PL("#0d0d0e", 0.35), bevel=0.004, anchor=(0, 0, -1))
    C.quad("screen", w - 0.02, h - 0.025, (0, -0.0485, 0.004), SCREEN_OFF(), rot=(PI / 2, 0, 0))
    C.box("mount", (0.3, 0.02, 0.3), (0, -0.01, -0.15), METAL("black"))
    return C.end("TV", loc, FACE[face])


def cable(pts, r=0.003, color="#161616"):
    """Flexible lead through the given points. Real cable never follows a clean arc: it keeps
    the memory of being coiled, so each span gets several extra points on a wandering offset."""
    out = [tuple(pts[0])]
    ox = oy = 0.0
    for a, b in zip(pts, pts[1:]):
        n = 6
        for k in range(1, n):
            t = k / n
            ox = ox * 0.6 + R.uniform(-0.011, 0.011)
            oy = oy * 0.6 + R.uniform(-0.011, 0.011)
            q = [a[i] + (b[i] - a[i]) * t for i in range(3)]
            out.append((q[0] + ox, q[1] + oy, max(q[2] + R.uniform(-0.004, 0.004), r)))
        out.append(tuple(b))
    return C.pipe("Cable", out, r, PL(color, 0.5))


def power_strip(loc, rot=0.0):
    C.begin()
    C.box("strip", (0.26, 0.055, 0.035), (0, 0, 0), PL("#efefec", 0.4), bevel=0.006)
    for i in range(4):
        C.cyl("sock", 0.018, 0.002, (-0.085 + i * 0.056, 0, 0.035), PL("#d5d5d2", 0.5), segs=16)
    return C.end("PowerStrip", loc, rot)


# ---------------------------------------------------------------- lamps ---
def _shade_mat(color="#efe3cc", glow=2.0):
    """Fabric lamp shade lit from inside: brightest in a band at bulb height and
    falling off towards the rims, like a real shade, instead of an even glow."""
    name = "LampShade_{}_{}".format(color, glow)
    if name in C._MATS:
        return C._MATS[name]
    m = C.mat(name, color, rough=0.8, emit=glow, emit_color="#ffcf9a", trans=0.25)
    if glow:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        d = nt.nodes.new("ShaderNodeMath")          # |z - 0.4|
        d.operation = "SUBTRACT"
        d.inputs[1].default_value = 0.4
        nt.links.new(sep.outputs["Z"], d.inputs[0])
        ab = nt.nodes.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        nt.links.new(d.outputs[0], ab.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.0
        mr.inputs["From Max"].default_value = 0.6
        mr.inputs["To Min"].default_value = glow * 2.2
        mr.inputs["To Max"].default_value = glow * 0.25
        nt.links.new(ab.outputs[0], mr.inputs["Value"])
        nt.links.new(mr.outputs[0], bsdf.inputs["Emission Strength"])
    return m


def table_lamp(loc, on=True, h=0.42, base="#3b5a5e", power=9):
    C.begin()
    C.lathe("base", [(0, 0), (0.055, 0), (0.07, 0.03), (0.075, 0.09), (0.05, 0.16), (0.018, 0.2), (0.012, h * 0.6),
                     (0, h * 0.6)], (0, 0, 0), CER(base), segs=28)
    C.lathe("shade_o", [(0.13, h * 0.55), (0.095, h)], (0, 0, 0), _shade_mat(glow=0.3 if on else 0.0), segs=32, sub=0)
    if on:
        C.light("bulb", (0, 0, h * 0.78), power, radius=0.03)
    return C.end("TableLamp", loc)


def floor_lamp(loc, on=True, h=1.55, power=22):
    C.begin()
    C.cyl("base", 0.14, 0.02, (0, 0, 0), METAL("black"), bevel=0.005)
    C.pipe("pole", [(0, 0, 0.02), (0, 0, h - 0.2)], 0.011, METAL("black"), smooth=False)
    C.lathe("shade", [(0.2, h - 0.3), (0.16, h)], (0, 0, 0), _shade_mat("#e9dcc3", 1.1 if on else 0.0), segs=36, sub=0)
    if on:
        C.light("bulb", (0, 0, h - 0.12), power, radius=0.04)
    return C.end("FloorLamp", loc)


def ceiling_dome(loc, power=60, r=0.19, on=True):
    """Flush opal ceiling light; loc.z = ceiling height."""
    C.begin()
    C.cyl("rim", r + 0.012, 0.025, (0, 0, -0.025), METAL("white"), segs=40)
    opal = C.mat("OpalOn" if on else "OpalOff", "#f6f1e6", rough=0.3, emit=3.5 if on else 0.0, emit_color="#ffe2bd")
    C.lathe("dome", [(r, -0.025), (r * 0.92, -0.06), (r * 0.6, -0.085), (0, -0.095)], (0, 0, 0), opal, segs=40)
    if on:
        C.light("light", (0, 0, -0.2), power, radius=0.045)
    return C.end("CeilingLight", loc)


def pendant(loc, drop=0.9, power=50, color="#22262a", r=0.19, on=True):
    """Hanging metal dome pendant; loc.z = ceiling height."""
    C.begin()
    C.cyl("rose", 0.05, 0.025, (0, 0, -0.025), METAL("black"), segs=24)
    C.pipe("cord", [(0, 0, -0.02), (0, 0, -drop + 0.16)], 0.003, PL("#111111"), smooth=False)
    C.lathe("shade", [(0.02, -drop + 0.2), (0.05, -drop + 0.17), (r * 0.8, -drop + 0.08), (r, -drop)], (0, 0, 0),
            C.mat("PendantOuter_" + color, color, rough=0.35, metal=0.6), segs=40)
    bulb = C.mat("BulbOn", "#fff3df", rough=0.3, emit=25.0 if on else 0.0, emit_color="#ffd9a6")
    C.sphere("bulb", 0.03, (0, 0, -drop + 0.07), bulb)
    if on:
        C.light("light", (0, 0, -drop - 0.02), power, radius=0.06)
    return C.end("Pendant", loc)


# ----------------------------------------------------------------- misc ---
def garment(name, w, l, loc, colliders, color=None, tex="cotton_jersey", rot=0.0, drop=0.25):
    """A piece of clothing dropped where it lies: a small sheet of cloth simulated
    falling onto whatever is below, so it crumples and hangs like real fabric."""
    ph_ = R.uniform(0, 6.28)
    shape = lambda u, v: ((u - 0.5) * w * 0.8, (v - 0.5) * l * 0.8,                                   # noqa: E731
                          0.05 * math.sin(u * 8 + ph_) * math.cos(v * 6 + ph_) + 0.03 * math.sin(u * 15 + v * 11))
    return C.drape(name, w, l, (loc[0], loc[1], loc[2] + drop), rot,
                   creased(FAB(tex, color or R.choice(FABRIC_COLORS), size=0.14, normal=2.2), 0.4, 0.5), colliders,
                   frames=36, res=26, thick=0.007, bend=0.07, shrink=-0.035, shape=shape, mass=0.4)


def laundry_basket(loc, rot=0.0, color="#cfc4ad", full=True):
    """Round fabric hamper with rope handles, clothes dropped into it by simulation."""
    C.begin()
    f = FAB("rough_linen", color, size=0.12, normal=2.4)
    r, h = 0.2, 0.46
    b = C.lathe("basket", [(0, 0), (r * 0.9, 0), (r, h), (r + 0.012, h + 0.012), (r + 0.004, h + 0.02), (r - 0.012, h),
                           (r * 0.9 - 0.01, 0.012), (0, 0.012)], (0, 0, 0), f, segs=36, sub=1)
    C.lumpy(b, 0.008, 0.12, 4)
    for sx in (-1, 1):
        C.pipe("handle", [(sx * (r + 0.004), -0.05, h - 0.04), (sx * (r + 0.05), -0.03, h - 0.09), (sx * (r + 0.05), 0.03, h - 0.09),
                          (sx * (r + 0.004), 0.05, h - 0.04)], 0.007, C.mat("Rope", "#b9a37a", rough=0.9, bump=0.8, bump_scale=900))
    if full:
        inside = [b]
        for i, (col, tex) in enumerate((("#d8d2c6", "cotton_jersey"), ("#59636b", "cotton_jersey"), ("#8c4a40", "cotton_jersey"))):
            inside.append(garment("laundry", 0.46, 0.5, (R.uniform(-0.03, 0.03), R.uniform(-0.03, 0.03), 0.46 + 0.12 * i), inside,
                                  col, tex, rot=R.uniform(0, 3), drop=0.2))
    return C.end("LaundryBasket", loc, rot)


def bin_round(loc, r=0.13, h=0.3, material=None, bag=True):
    C.begin()
    C.lathe("bin", [(0, 0), (r * 0.85, 0), (r, h), (r - 0.004, h), (r * 0.85 - 0.004, 0.006), (0, 0.006)], (0, 0, 0),
            material or METAL("steel"), segs=32, sub=0)
    if bag:
        C.lathe("bag", [(r + 0.004, h - 0.03), (r + 0.006, h + 0.002), (r - 0.01, h + 0.002), (r * 0.8, h * 0.4)],
                (0, 0, 0), C.mat("BinBag", "#e9e9e6", rough=0.35, trans=0.2), segs=32, sub=0)
    return C.end("Bin", loc)


def crumpled(loc, n=4, spread=0.05, r=0.03):
    for i in range(n):
        o = C.sphere("PaperBall", r * R.uniform(0.8, 1.2), (jit(loc[0], spread), jit(loc[1], spread), loc[2] + r),
                     PAPER(), segs=10)
        C.lumpy(o, 0.02, 0.03, seed=i + 1)


def umbrella(loc, lean=(0.12, 0.05), color="#263a4f"):
    C.begin()
    C.lathe("canopy", [(0, 0.06), (0.03, 0.1), (0.042, 0.45), (0.014, 0.62), (0, 0.63)], (0, 0, 0),
            FAB("denim_fabric", color, size=0.15), segs=16)
    C.cyl("tip", 0.006, 0.07, (0, 0, 0), METAL("steel"), segs=8)
    C.pipe("shaft", [(0, 0, 0.0), (0, 0, 0.75), (0.0, 0.0, 0.8), (0.03, 0, 0.84), (0.06, 0, 0.8)], 0.007,
           PL("#2a1b12", 0.4))
    g = C.end("Umbrella", loc)
    g.rotation_euler = (lean[0], lean[1], R.uniform(0, 6.28))
    return g


def candle(loc, h=0.09, r=0.03, color="#efe8d8"):
    C.begin()
    C.cyl("wax", r, h, (0, 0, 0), C.mat("Wax_" + color, color, rough=0.5, sss=0.3), bevel=0.004, segs=24)
    C.cyl("wick", 0.0015, 0.012, (0, 0, h), PL("#1a1a1a"), segs=6)
    return C.end("Candle", loc)


def toilet_roll(loc, rot=(0, 0, 0)):
    C.begin()
    C.lathe("roll", [(0.021, 0.002), (0.05, 0), (0.052, 0.006), (0.052, 0.09), (0.05, 0.096), (0.021, 0.094), (0.021, 0.002)], (0, 0, 0),
            C.mat("TissuePaper", "#f6f5f1", rough=0.9, bump=0.5, bump_scale=420, noise=0.03), segs=28, sub=0)
    C.lathe("core", [(0.0205, 0.0), (0.0205, 0.096), (0.018, 0.096), (0.018, 0.0), (0.0205, 0.0)], (0, 0, 0),
            C.mat("RollCore", "#9a7a55", rough=0.9), segs=20, sub=0)
    g = C.end("ToiletRoll", loc)
    g.rotation_euler = rot
    return g

"""Furnish and clutter every room. Coordinates are absolute (see shell.ROOMS)."""
import math

import bpy

from . import art
from . import core as C
from . import fixtures as X
from . import props as P
from . import shell as S
from . import wear as W
from . import mitsuba as MI
from . import gso as G
from mathutils import Vector

R = C.rng
PI = math.pi
F = P.FACE
_DG = [None]


def refresh():
    _DG[0] = C.refresh()


def Z(x, y, zf=1.5):
    z = C.surface_z(x, y, zf, _DG[0])
    return 0.0 if z is None else z


def L(cx, cy, rot, lx, ly):
    c, s = math.cos(rot), math.sin(rot)
    return cx + lx * c - ly * s, cy + lx * s + ly * c


def ph(aid, x, y, z=0.0, rot=0.0, **kw):
    return C.place(aid, (x, y, z), rot, **kw)


def on(aid, x, y, zf=1.5, rot=None, **kw):
    """Drop a Poly Haven prop onto whatever surface is below (x, y, zf)."""
    return ph(aid, x, y, Z(x, y, zf), R.uniform(0, 6.28) if rot is None else rot, **kw)


def sc(name, x, y, zf=1.5, rot=None, **kw):
    """Set a photo-scanned object (apartment/gso.py) on whatever surface is below (x, y, zf)."""
    return G.put(name, x, y, Z(x, y, zf), R.uniform(0, 6.28) if rot is None else rot, **kw)


def fruit_bowl(x, y, zf=1.5, bananas=None):
    """Wooden bowl with fruit settled side by side on its curved bottom (each piece is
    dropped onto the bowl by ray cast, so nothing interpenetrates), bananas beside it."""
    z = Z(x, y, zf)
    ph("wooden_bowl_01", x, y, z)
    refresh()
    fruit = (("food_apple_01", None), ("lemon", None), ("food_apple_01", None), ("food_pears_asian_01", "_b$"), ("lemon", None))
    a0 = R.uniform(0, 6.28)
    for i, (aid, part) in enumerate(fruit):
        a = a0 + i * 2 * PI / len(fruit)
        fx, fy = x + 0.088 * math.cos(a), y + 0.088 * math.sin(a)
        ph(aid, fx, fy, Z(fx, fy, z + 0.3) - 0.003, R.uniform(0, 6), part=part)
    if bananas:
        bx, by, br = bananas
        ph("bananas", bx, by, Z(bx, by, zf), br, part="bunch", scale=0.85)


def shelf_fill(cx, cy, rot, width, depth_off, zf, specs):
    """Fill shelf boards found below (cx, cy). specs: per level (top first) a tuple
    (book_fill 0..1, callable(x, y, z) for the free end or None)."""
    lv = C.levels(cx, cy, zf, dg=_DG[0])
    for z, (fill, extra) in zip(lv, specs):
        sx, sy = L(cx, cy, rot, -width / 2, depth_off)
        if fill:
            P.book_row((sx, sy, z), width * fill, rot, fill=1.0)
        if extra:
            ex, ey = L(cx, cy, rot, width / 2 - 0.16, depth_off)
            extra(ex, ey, z)
    return lv


def storage_box(x, y, z, color="#b9a98c", size=(0.3, 0.26, 0.2), rot=0.0):
    return C.basin("StorageBox", size, (x, y, z), P.FAB("rough_linen", color, size=0.2), wall=0.008, bevel=0.01, rot=rot)


def basket(x, y, z, w=0.27, hmax=0.24, rot=0.0, aid="wicker_basket_01", part=None):
    """Scanned wicker basket scaled to fit a shelf cell."""
    lo, hi = C._bounds(C._pick(C.load_asset(aid), part))
    sc = min(w / max(hi.x - lo.x, hi.y - lo.y), hmax / (hi.z - lo.z))
    return ph(aid, x, y, z, rot=rot, scale=sc, part=part)


def games(x, y, z, n=3, rot=0.0):
    for i in range(n):
        s = (R.uniform(0.24, 0.3), R.uniform(0.2, 0.27), R.uniform(0.035, 0.055))
        C.box("BoardGame", s, (x + R.uniform(-0.01, 0.01), y + R.uniform(-0.01, 0.01), z),
              P.PL(R.choice(P.TOY_COLORS + P.BOOK_COLORS), 0.5), rot=rot + R.uniform(-0.12, 0.12), bevel=0.003)
        z += s[2]
    return z


def planter(x, y, r=0.18, h=0.34, color="#d9d4c8"):
    C.lathe("Planter", [(0, 0), (r * 0.78, 0), (r, h), (r - 0.015, h), (r * 0.76 - 0.01, 0.02), (0, 0.02)], (x, y, 0),
            P.CER(color), segs=36)
    C.cyl("Soil", r * 0.8, h - 0.07, (x, y, 0.02), C.mat("Soil", "#2a1e14", rough=1.0, bump=1.0, bump_scale=90), segs=24)


def small_plant(x, y, z, kind="fern", pot="#b5673f", r=0.065, h=0.1):
    """Little pot plant; different species and pots so the same one is not cloned around the flat."""
    C.begin()
    C.lathe("PlantPot", [(0, 0), (r * 0.72, 0), (r, h), (r - 0.008, h), (r * 0.7 - 0.006, 0.012), (0, 0.012)], (0, 0, 0),
            C.mat("Pot_" + pot, pot, rough=0.75, noise=0.08, bump=0.4, bump_scale=300), segs=28)
    C.cyl("PotSoil", r * 0.78, h - 0.03, (0, 0, 0.012), C.mat("Soil", "#2a1e14", rough=1.0, bump=1.0, bump_scale=90), segs=18)
    aid, part, sc = {"fern": ("fern_02", "_a$", 0.42), "fern2": ("fern_02", "_d$", 0.4),
                     "anthurium": ("anthurium_botany_01", "_e$", 0.75)}[kind]
    C.place(aid, (0, 0, h - 0.025), R.uniform(0, 6), part=part, scale=sc)
    return C.end("PotPlant", (x, y, z))


def switches(M):
    C.collection("Switches & Sockets", C.collection("Architecture"))
    sw = S.switch
    sw("Sw_Entrance", "x", S.YH0 + S.TI / 2 + 0.004, 0.55, 1, M, double=True)
    sw("Sw_Living", "x", S.YH0 - S.TI / 2 - 0.004, 1.82, -1, M)
    sw("Sw_Kitchen", "x", S.YH0 - S.TI / 2 - 0.004, 7.12, -1, M)
    sw("Sw_Bedroom", "x", S.YH1 + S.TI / 2 + 0.004, 2.42, 1, M)
    sw("Sw_Office", "x", S.YH1 + S.TI / 2 + 0.004, 4.82, 1, M)
    sw("Sw_Bath", "x", S.YH1 - S.TI / 2 - 0.004, 7.82, -1, M)
    for name, axis, face, a, sgn in (("So_Liv1", "y", 0.154, 3.75, 1), ("So_Liv2", "y", S.XLK - 0.064, 0.45, -1),
                                     ("So_Kit", "y", S.XLK + 0.064, 1.6, 1), ("So_Hall", "x", S.YH0 + 0.064, 6.2, 1),
                                     ("So_Bed", "y", 0.154, 7.63, 1), ("So_Off", "y", S.XOB - 0.064, 9.75, -1)):
        sw(name, axis, face, a, sgn, M, z=0.3, socket=True, double=True)
    sw("Sw_HallOffice", "x", S.YH1 - S.TI / 2 - 0.004, 6.08, -1, M)
    sw("Sw_HallBed", "x", S.YH1 - S.TI / 2 - 0.004, 3.68, -1, M)
    sw("So_HallN", "x", S.YH1 - S.TI / 2 - 0.004, 7.6, -1, M, z=0.3, socket=True)
    sw("So_KitWest", "y", S.XLK + S.TI / 2 + 0.004, 3.75, 1, M, z=0.3, socket=True, double=True)
    sw("Sw_KitWest", "y", S.XLK + S.TI / 2 + 0.004, 4.25, 1, M)
    # intercom by the entrance
    C.add_bevel(C.boxes("Intercom", [((0.154, 4.95, 1.35), (0.18, 5.05, 1.55))], M["plastic_white"]), 0.004)
    C.quad("Intercom_screen", 0.07, 0.05, (0.1805, 5.0, 1.49), P.SCREEN_OFF(), rot=(PI / 2, 0, PI / 2))


# ================================================================ LIVING ===
def living(M):
    C.collection("Living Room")
    x0, y0, x1, y1 = S.inner("living")
    S.radiator("LivRadiator", "x", y0 + 0.004, 3.0, 1.7, 1, M)
    X.curtains("LivCurtain", "x", y0, 1, 1.6, 4.4, color="#cbbfa9", z_top=2.52, open_frac=0.26, off=0.17)
    ph("modern_wooden_cabinet", x0 + 0.36, 2.2, rot=F["E"])
    P.tv((x0 + 0.004, 2.2, 1.36), "E", 1.3, 0.75)
    ph("modern_coffee_table_01", 2.1, 2.2, 0.012, rot=PI / 2 + 0.04)
    sofa, _ssz, sofa_objs = C.demo("flat-archiviz.blend", collection="Sofa", name="SofaSet",
                                   exclude=r"^(New_Works|Bicchiere|Bottiglia|Tappo|Vassoio)")   # no designer lamp / crystal set here
    sofa.location = (2.75, 2.2, 0)
    sofa.rotation_euler = (0, 0, PI)          # their set faces +X; ours faces the TV on the west wall
    for nd in bpy.data.materials["Fabric_Sofa"].node_tree.nodes:      # let the weave read at room distance
        if nd.type == "BUMP":
            nd.inputs["Strength"].default_value = 0.55
    ph("modern_arm_chair_01", 1.3, 0.95, rot=2.5)
    ph("mid_century_lounge_chair", 4.95, 0.98, rot=-2.25)
    ph("side_table_01", 3.75, 3.92, rot=F["W"])
    ph("steel_frame_shelves_01", x1 - 0.26, 1.6, rot=F["W"])
    ph("wooden_display_shelves_01", x1 - 0.19, 3.0, rot=F["W"])
    X.play_mat((4.98, 2.55, 0), rot=PI / 2 + 0.05)
    X.kid_table((5.0, 4.02, 0), rot=0.1)
    rail = [((1.55, -0.2, 1.0), (4.45, -0.17, 1.03)), ((1.55, -0.2, 0.52), (4.45, -0.17, 0.545))]
    rail += [((1.6 + i * 0.115, -0.193, 0.545), (1.612 + i * 0.115, -0.181, 1.0)) for i in range(25)]
    C.boxes("JulietRailing", rail, P.METAL("black"))
    ph("potted_plant_01", 0.6, 4.05, rot=1.0)
    ph("potted_plant_02", 5.78, 0.55, rot=2.0)
    P.floor_lamp((0.55, 0.6, 0), power=12)
    ph("modern_ceiling_lamp_01", 2.2, 2.2, S.H - 0.95 * 0.72, scale=0.72)
    # walls
    ph("hanging_picture_frame_02", 1.05, y1 - 0.02, 1.3, rot=F["S"])
    P.frame((4.25, y1 - 0.004, 1.55), "S", 0.5, 0.7, i=0, color="#2a2420")
    P.frame((4.9, y1 - 0.004, 1.68), "S", 0.4, 0.5, i=3, color="#b89a6a")
    P.frame((5.5, y1 - 0.004, 1.5), "S", 0.42, 0.32, i=0, kid=True, color="#e8e2d4")
    P.drawing((5.2, y1 - 0.006, 1.05), 3, on_wall="S")
    P.frame((x1 - 0.004, 3.0, 1.98), "W", 0.5, 0.4, i=6, color="#e8e2d4")
    P.frame((5.3, y0 + 0.004, 1.45), "N", 0.5, 0.7, i=2, color="#1c1c1c")
    refresh()

    # low console behind the sofa
    P.book_stack((4.02, 1.95, Z(4.02, 1.95, 1.0)), 3, 0.35)
    small_plant(4.04, 1.45, Z(4.04, 1.45, 1.0), "fern", "#b9a58c", 0.085, 0.13)
    # coffee table
    zt = Z(2.1, 2.2, 1.0)
    P.remote((2.05, 1.85, zt), 0.4)
    P.remote((2.13, 1.92, zt), 0.9)
    G.put("mug_red", 2.2, 2.45, zt, 2.4, rough=0.14)
    P.book_stack((2.05, 2.2, zt), 2, 0.2)
    X.sippy_cup((2.22, 1.72, zt))
    P.candle((2.18, 2.08, zt), 0.07, 0.035)
    # tv cabinet
    zc = Z(0.45, 2.2, 1.2)
    C.box("Soundbar", (0.09, 0.9, 0.06), (0.4, 2.2, zc), P.PL("#18181a", 0.5), bevel=0.012)
    on("gaming_console", 0.47, 1.35, 1.2, rot=PI / 2)
    on("gamepad", 0.6, 1.72, 1.2, rot=1.0, scale=0.42)
    X.router((0.42, 3.2, zc), PI / 2)
    on("standing_picture_frame_01", 0.45, 2.92, 1.2, rot=PI / 2 + 0.3)
    on("ceramic_vase_02", 0.42, 1.08, 1.2)
    P.cable([(0.3, 2.2, 1.0), (0.26, 2.25, 0.8), (0.3, 2.3, zc + 0.03)])
    # sofa
    zs = Z(3.45, 2.2, 1.3)
    C.drape("SofaThrow", 0.95, 1.25, (3.4, 1.3, zs + 0.5), 0.18, P.creased(P.FAB("knitted_fleece", "#c9a13f", size=0.16, normal=2.0), 0.4, 0.6),
            [o for o in sofa_objs if o.type == "MESH"] + [bpy.data.objects["Floor_living"]], bend=0.03, shrink=-0.04, res=44, thick=0.0035)
    # side table
    zt = Z(3.75, 3.92, 1.0)
    P.table_lamp((3.8, 4.0, zt), on=False)
    # play corner
    G.put("duplo", 5.0, 2.55, 0.012, 0.5, rough=0.3)         # what got built this morning
    G.put("abc", 5.42, 2.1, 0.012, 2.0, rough=0.6)
    G.put("truck", 4.72, 2.9, 0.012, 1.2, rough=0.35)
    G.put("dino", 5.28, 3.0, 0.012, 4.0, rough=0.45)
    G.put("teddy", 4.25, 3.3, 0.0, 0.7, rough=0.95, spec=0.2)
    P.stack_rings((4.72, 3.2, 0.012))
    ph("football", 4.55, 1.8, rot=1.1, part="inflated")
    P.picture_book((5.35, 3.3, 0.0), 0.5, 2)
    P.picture_book((4.6, 2.3, 0.012), 2.1, 3)
    zk = 0.46
    P.drawing((5.0, 4.02, zk + 0.001), 1, rot=0.25)
    P.crayons((5.12, 3.93, zk), 7, 0.07)
    G.put("mug_yellow", 4.8, 4.14, zk, 3.6, rough=0.14)
    G.put("crayon_box", 5.2, 4.1, zk, 0.4, rough=0.55)
    # toy basket
    C.basin("ToyBin", (0.44, 0.36, 0.26), (4.62, 3.55, 0), P.FAB("rough_linen", "#b9a98c", size=0.2), wall=0.012,
            bevel=0.03, rot=0.3)
    P.ball((4.52, 3.47, 0.012), 0.07, "#2f6fd0")
    P.ball((4.76, 3.52, 0.012), 0.055, "#f2b81f")
    P.blocks((4.66, 3.63, 0.012), n=4, spread=0.07)
    # shelves
    sx, sy = x1 - 0.27, 1.6
    shelf_fill(sx, sy, F["W"], 0.96, 0.0, 2.3, [
        (0.0, lambda x, y, z: ph("potted_plant_04", x, y + 0.2, z, scale=1.6)),
        (0.62, lambda x, y, z: ph("ceramic_vase_01", x, y, z)),
        (0.8, lambda x, y, z: None),
        (0.45, lambda x, y, z: (G.put("monopoly", x - 0.02, y + 0.1, z, PI / 2, rough=0.5, pre=(PI / 2, 0, 0)),
                                G.put("puzzle", x - 0.01, y + 0.11, z + 0.06, PI / 2 + 0.12, rough=0.6))),
        (0.0, lambda x, y, z: (basket(x, y - 0.02, z, 0.32, 0.26, rot=0.2),
                               storage_box(x, y + 0.42, z, "#b9a98c", rot=PI / 2))),
    ])
    lv = C.levels(sx, sy, 2.3, dg=_DG[0])
    if lv:
        on("standing_picture_frame_02", sx, sy - 0.25, 2.3, rot=F["W"] + 0.2)
        on("carved_wooden_elephant", sx, sy + 0.05, 2.3, rot=F["W"])
        if len(lv) > 1:
            ph("Camera_01", sx, sy - 0.3, lv[1], rot=1.9, part="^Camera_01$")
    # cube shelf: toys and kids' books
    kx, ky = x1 - 0.2, 3.0
    top = Z(kx, ky, 2.0)
    ph("ceramic_vase_01", kx, ky - 0.33, top)
    on("standing_picture_frame_02", kx, ky + 0.3, 2.0, rot=F["W"] + 0.15)
    P.stack_rings((kx - 0.02, ky + 0.02, top))
    for dy, kind in ((-0.36, "books"), (0.0, "toys"), (0.36, "books")):
        lvc = C.levels(kx, ky + dy, top - 0.05, dg=_DG[0])
        for i, z in enumerate(lvc[:2]):
            if kind == "books" and i == 0 or kind == "toys" and i == 1:
                P.book_row((kx, ky + dy + 0.13, z), 0.26, F["W"])
            elif i == 0:
                games(kx - 0.02, ky + dy, z, 2, PI / 2)
            else:
                basket(kx - 0.01, ky + dy, z, 0.27, 0.22, rot=R.uniform(-0.1, 0.1), aid="wicker_basket_02", part="base")


# =============================================================== KITCHEN ===
def under(x, y, z0=1.15, zmax=2.0):
    """Height of the first surface above (x, y, z0) - the underside of a wall cupboard - or None."""
    hit, loc, _n, _i, _o, _m = bpy.context.scene.ray_cast(_DG[0], (x, y, z0), (0, 0, 1))
    return loc.z if hit and loc.z < zmax else None


def kitchen(M):
    """Fitted kitchen from 'Country Kitchen' by Jay-Artist (CC-BY): cupboard run with range cooker,
    hood and microwave on the east wall, an island, and a table with four chairs by the window.
    Scaled 0.92 so the 4.75 m run fits the 4.39 m wall, which also brings its tall worktop to 0.92 m."""
    C.collection("Kitchen")
    x0, y0, x1, y1 = S.inner("kitchen")
    k = 0.92
    kit, parts = MI.kit("kitchen", "CountryKitchen",
                        drop=r"^(Walls|Floor|Ceiling|Window|Skirting|Blind|Lamp|Bulb|CeilingLight|Home|Carrots|Mushroom|SlicedMushroms|Pepper|Tomatoes|Chopping|Book|LeftPage)",
                        scale=k, rot=PI, loc=(x1 - 2.49 * k, y0 + 2.47 * k, 0.02 * k))
    X.fridge((x0, 4.1, 0), PI / 2)
    X.roller_blind("KitchenBlind", "x", y0 - 0.1, 1, 7.36, 8.84, 2.28, 0.35)
    tx, ty = 7.44, 0.97                                   # their table, after the move
    P.pendant((tx, ty, S.H), drop=1.0, power=25, color="#c9a45c", on=False)
    P.ceiling_dome((8.3, 2.6, S.H), power=28, on=False)
    P.bin_round((6.45, 3.4, 0), 0.14, 0.42)
    ph("wall_clock", 8.9, y1 - 0.03, 1.95, rot=F["S"])
    P.frame((x0 + 0.004, 2.4, 1.55), "E", 0.5, 0.4, i=4, color="#b89a6a")
    refresh()

    # a sink let into the free worktop at the north end of the run (the scene has none)
    sx, sy = x1 - 0.4, 4.08
    zc = Z(sx, sy, 1.3)
    cut = C.box("SinkCut", (0.5, 0.42, 0.5), (sx, sy, zc - 0.3), None)
    cut.hide_render = True
    cut.display_type = "WIRE"
    for o in parts.get("Worktops", []) + parts.get("CupboardUnits", []):
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        if (min(q.x for q in pts) < sx + 0.25 and max(q.x for q in pts) > sx - 0.25 and min(q.y for q in pts) < sy + 0.21
                and max(q.y for q in pts) > sy - 0.21 and max(q.z for q in pts) > zc - 0.25):
            md = o.modifiers.new("SinkCut", "BOOLEAN")
            md.operation = "DIFFERENCE"
            md.object = cut
    st, ch = P.METAL("steel"), P.METAL("chrome")
    C.basin("KitchenSink", (0.5, 0.42, 0.2), (sx, sy, zc - 0.197), st, wall=0.012, bevel=0.012)
    C.cyl("SinkDrain", 0.028, 0.004, (sx, sy, zc - 0.184), P.METAL("black"), segs=20)
    C.cyl("TapBase", 0.024, 0.045, (x1 - 0.1, sy, zc), ch, segs=24, bevel=0.004)
    C.pipe("Tap", [(x1 - 0.1, sy, zc + 0.012), (x1 - 0.1, sy, zc + 0.3), (x1 - 0.15, sy, zc + 0.39), (x1 - 0.24, sy, zc + 0.38),
                   (x1 - 0.27, sy, zc + 0.3)], 0.011, ch)
    C.box("TapLever", (0.012, 0.012, 0.09), (x1 - 0.1, sy + 0.035, zc + 0.03), ch, bevel=0.004)
    refresh()
    P.plate((sx, sy, zc - 0.184), 0.11)                    # breakfast things waiting in the sink
    G.put("bowl_white", sx + 0.04, sy + 0.09, zc - 0.178, 0.5, rough=0.1)
    G.put("mug_white", sx - 0.1, sy - 0.09, zc - 0.184, 1.1, rough=0.1)
    G.put("drainer", x1 - 0.4, 3.6, zc, 0.03, rough=0.4)           # scanned drainer with the washed-up things in it
    G.put("bowl_teal", x1 - 0.42, 3.52, zc + 0.014, 0.0, rough=0.12)
    G.put("mug_teal", x1 - 0.38, 3.7, zc + 0.014, 2.3, rough=0.12)
    P.bottle((x1 - 0.12, 3.84, zc), 0.19, 0.03, "#7bc47f", "#ffffff", pump=True, clear=True, name="DishSoap")
    G.put("sponge", x1 - 0.14, 4.33, zc, 0.3, rough=0.95, spec=0.2)
    sc("towel_stripe", x1 - 0.47, 3.27, 1.3, rot=0.12, rough=0.95, spec=0.2)
    X.paper_towel((x1 - 0.14, 4.44, zc))
    # between the radio and the cooker
    X.coffee_maker((x1 - 0.36, 1.5, Z(x1 - 0.36, 1.5, 1.3)), F["W"])
    sc("mug_yellow", x1 - 0.5, 1.7, 1.3, rot=0.9, rough=0.12)
    sc("capsules", x1 - 0.17, 1.78, 1.3, rot=F["W"] + 0.25, rough=0.5)
    # island: fruit, spices, the day's bits
    zi = Z(7.95, 3.44, 1.3)
    ph("wooden_cutting_board", 7.44, 3.4, zi, rot=PI / 2 + 0.12)
    fruit_bowl(7.95, 3.42, 1.3, bananas=(8.02, 3.14, 0.4))
    # breakfast was not cleared away: cereal, cocoa, the bowl and a mug
    sc("cereal", 7.52, 3.02, 1.3, rot=G.face(-0.55, 0.85), rough=0.5)
    sc("cocoa", 7.72, 2.96, 1.3, rot=G.face(-0.3, 0.9) , rough=0.4)
    sc("bowl_white", 7.5, 3.36, 1.3, rot=0.0, rough=0.1)
    sc("mug_red", 7.7, 3.28, 1.3, rot=2.2, rough=0.14)
    sc("teapot", x1 - 0.2, 3.08, 1.3, rot=2.6, rough=0.1)
    # under-cupboard lights wherever there really is a cupboard above the worktop
    for i, yy in enumerate((0.5, 1.1, 3.3, 3.8, 4.3)):
        zu = under(x1 - 0.22, yy)
        if zu is not None:
            X.led_strip("LedEast{}".format(i), (x1 - 0.22, yy - 0.12, zu - 0.003), (x1 - 0.22, yy + 0.12, zu - 0.003))
            C.light("UnderCabinet{}".format(i), (x1 - 0.22, yy, zu - 0.06), 2.2, "#fff1d6", radius=0.04)
    # window sill
    small_plant(7.55, 0.03, 1.084, "fern")
    P.bottle((8.6, 0.03, 1.084), 0.16, 0.028, "#e9e2d0", "#3a8a5a")
    # the table is laid for dinner; the family's own things are on it too
    zt = Z(tx, ty, 1.2)
    P.phone((tx + 0.12, ty + 0.05, zt), 0.3)
    G.put("bowl_teal", tx - 0.1, ty + 0.3, zt, 0.0, rough=0.12)
    X.sippy_cup((tx - 0.02, ty + 0.48, zt), "#ef6aa0")
    G.put("mug_teal", tx + 0.2, ty - 0.35, zt, 4.0, rough=0.12)
    G.put("pencil_case", tx + 0.16, ty - 0.02, zt, 1.1, rough=0.7)
    P.drawing((tx - 0.12, ty - 0.05, zt + 0.001), 2, rot=0.4)
    P.crayons((tx + 0.02, ty - 0.2, zt), 5, 0.06)
    on("long_life_food", x0 + 0.3, 4.1, 2.3, part="milk")


# ================================================================== HALL ===
def hall(M):
    C.collection("Hallway")
    x0, y0, x1, y1 = S.inner("hall")
    P.rug("HallRunner", 0.8, 4.6, (5.2, 5.6, 0), rot=PI / 2 + 0.018, kind="kilim", thick=0.016, ruck=((0.2, 0.022), (0.69, 0.014)))
    C.box("Doormat", (0.46, 0.76, 0.016), (0.55, 5.62, 0), C.mat("Coir", "#7d5f3c", rough=1.0, bump=1.0, bump_scale=700,
                                                              noise=0.15), bevel=0.002)
    C.add_bevel(C.boxes("DoormatBorder", [((0.3, 5.22, 0), (0.8, 5.24, 0.01)), ((0.3, 6.0, 0), (0.8, 6.02, 0.01)),
                                          ((0.3, 5.22, 0), (0.32, 6.02, 0.01)), ((0.78, 5.22, 0), (0.8, 6.02, 0.01))],
                        P.RUBBER()), 0.003)
    P.ceiling_dome((2.6, 5.6, S.H), power=20)
    P.ceiling_dome((7.3, 5.6, S.H), power=20, on=False)
    # coat hooks on the north wall: jackets, child's raincoat, backpack, tote
    rack, hooks = X.coat_rack((1.3, y1 - 0.004, 1.78), "S", 1.3)
    hx = lambda i: 1.3 + hooks[i]  # noqa: E731
    wall = [bpy.data.objects["Skin_hall"], bpy.data.objects["Wall_HN"]]
    for i, (cx, w, h, col, tex) in enumerate(((hx(0), 0.6, 0.86, "#39424e", "poly_wool_herringbone"),
                                               (hx(1) + 0.08, 0.56, 0.8, "#8a6a4a", "poly_wool_herringbone"),
                                               (hx(2) + 0.15, 0.4, 0.5, "#d9a441", "cotton_jersey"))):   # last: child's raincoat
        C.hang("Coat", w, h, (cx, y1 - 0.004, 1.78), 0.0, P.FAB(tex, col, size=0.25), wall, pin=0.13 if i < 2 else 0.1)
        for sx in (-1, 1):       # sleeves hanging in front of the body give the garment volume
            C.hang("CoatSleeve", 0.15, h * 0.72, (cx + sx * w * 0.2, y1 - 0.03, 1.74), 0.0, P.FAB(tex, col, size=0.25), wall,
                   pin=0.05, frames=40, res=10, thick=0.03)
        C.soft_box("CoatCollar", (0.2 if i < 2 else 0.14, 0.07, 0.07), (cx, y1 - 0.075, 1.72),
                   P.FAB(tex, col, size=0.25), round_=0.03, cuts=3)
    P.tote((hx(4) - 0.02, y1 - 0.03, 1.79), "S")
    ph("fishermans_hat", 1.65, y1 - 0.11, 1.872, rot=0.4)
    G.put("hat", 1.28, y1 - 0.16, 1.872, 0.9, rough=0.85, spec=0.25, scale=0.9)
    C.box("ScarfBox", (0.3, 0.16, 0.12), (0.95, y1 - 0.105, 1.872), P.FAB("rough_linen", "#59636b", size=0.2), bevel=0.01)
    # open shoe rack with mismatched everyday pairs
    _, lv = X.shoe_rack((1.3, y1 - 0.004, 0), F["S"])
    ry = y1 - 0.004 - 0.15
    S_ = -PI / 2                                             # toes point out into the hall
    G.pair("boot_red", 1.03, ry, lv[2], S_ + 0.05, gap=0.12)
    G.pair("run_blue", 1.33, ry + 0.01, lv[2], S_ - 0.08, gap=0.12, stagger=0.03)
    G.pair("kid_trainer", 1.6, ry - 0.01, lv[2], S_ + 0.2, gap=0.1, stagger=-0.04)
    G.pair("run_pink", 1.05, ry, lv[1], S_ - 0.04, gap=0.12)
    G.pair("sneaker_white", 1.37, ry - 0.01, lv[1], S_ + 0.07, gap=0.115, stagger=0.02)
    G.shoe("kid_deck", 1.62, ry + 0.01, lv[1], S_ + PI + 0.15)          # its twin is under the rack
    G.shoe("kid_deck", 1.98, y1 - 0.56, 0.0, S_ + 0.9, mirror=True)
    G.pair("boot_ugg", 1.52, y1 - 0.62, 0.0, S_ - 0.45, gap=0.15, stagger=0.09, splay=0.16)     # kicked off in front of the rack
    G.put("backpack", 2.52, y1 - 0.2, 0.0, 0.12, rough=0.7, spec=0.3, tilt=(-0.07, 0.0))
    G.put("kid_backpack", 1.85, y0 + 0.19, 0.0, PI - 0.2, rough=0.75, spec=0.3)
    G.put("lunchbox", 2.2, y0 + 0.1, 0.0, PI + 0.25, rough=0.6, spec=0.3)
    ph("rubber_boots", 2.02, y1 - 0.2, rot=0.1, part=r"^rubber_boots_l_LOD0")
    ph("rubber_boots", 2.16, y1 - 0.22, rot=-0.15, part=r"^rubber_boots_r_LOD0")
    P.bin_round((0.33, y1 - 0.17, 0), 0.11, 0.5, P.METAL("black"), bag=False)
    P.umbrella((0.33, y1 - 0.17, 0.007), (0.1, 0.06))
    P.umbrella((0.35, y1 - 0.15, 0.007), (-0.08, 0.1), "#b24b3f")
    # console table + mirror on the south wall
    X.console_table((1.1, y0 + 0.004, 0), F["N"])
    ph("ornate_mirror_01", 1.1, y0 + 0.02, 1.2, rot=F["N"])
    P.scooter((0.42, y0 + 0.2, 0), rot=PI / 2 + 0.25)
    # gallery wall + cabinet between the cased openings
    X.console_table((5.35, y0 + 0.004, 0), F["N"], w=1.2, h=0.78, wood="walnut")
    ph("wicker_basket_02", 5.6, y0 + 0.19, rot=0.4, scale=1.7, part="base")
    ph("hanging_picture_frame_01", 4.2, y0 + 0.02, 1.15, rot=F["N"])
    P.frame((4.95, y0 + 0.004, 1.5), "N", 0.4, 0.5, i=4, color="#2a2420")
    P.frame((5.5, y0 + 0.004, 1.6), "N", 0.5, 0.4, i=5, color="#b89a6a")
    P.frame((6.05, y0 + 0.004, 1.5), "N", 0.3, 0.4, i=3, kid=True, color="#f1efe9")
    P.frame((6.5, y0 + 0.004, 1.55), "N", 0.4, 0.5, i=7, color="#1c1c1c")
    S.radiator("HallRadiator", "x", y1 - 0.004, 4.25, 1.0, -1, M)
    ph("cardboard_box_01", 6.6, y1 - 0.3, rot=0.2)
    ph("plastic_container", 7.25, y1 - 0.28, rot=PI / 2 + PI, scale=0.62)
    ph("side_table_tall_01", 9.5, y0 + 0.3, rot=0.2)
    planter(9.45, 6.2, 0.19, 0.36)
    ph("pachira_aquatica_01", 9.45, 6.2, 0.3, rot=0.6, part="_d$")
    ph("watering_can_metal_01", 9.1, 6.3, rot=2.2)
    refresh()

    zc = 0.8
    P.bowl((0.82, y0 + 0.16, zc), 0.07, 0.035, "#59636b")
    C.ring("Keyring", 0.014, 0.0015, (0.82, y0 + 0.16, zc + 0.012), P.METAL("steel"))
    for i in range(2):
        C.box("Key", (0.008, 0.05, 0.002), (0.8 + i * 0.025, y0 + 0.165, zc + 0.012), P.METAL("brass"), rot=0.5 + i * 0.8)
    P.papers((1.2, y0 + 0.16, zc), 4, 0.03, 0.3)
    C.box("Envelope", (0.22, 0.11, 0.003), (1.22, y0 + 0.17, zc + 0.004), C.mat("EnvelopeKraft", "#c8a877", rough=0.8), rot=0.5)
    on("round_spectacles", 1.45, y0 + 0.14, 1.3, rot=0.5)
    P.phone((1.0, y0 + 0.2, zc), 1.3)
    on("ceramic_vase_02", 0.68, y0 + 0.15, 1.3)
    zc = 0.78
    P.table_lamp((4.95, y0 + 0.17, zc), base="#b9a98c", power=55)
    on("ceramic_vase_04", 5.75, y0 + 0.16, 1.2)
    on("standing_picture_frame_01", 5.45, y0 + 0.2, 1.2, rot=F["N"] + 0.2)
    for i, (part, br) in enumerate((("cover24", 0.35), ("cover62", 0.6), ("softcover_01_cover14", 0.2))):   # scanned books, lying flat
        c_, s_ = math.cos(br), math.sin(br)
        ph("decorative_book_set_01", 5.2 - 0.115 * c_, y0 + 0.17 - 0.115 * s_, zc + 0.02 + i * 0.038, rot=br, part=part, tilt=(0.0, PI / 2))
    P.cable([(4.95, y0 + 0.1, zc + 0.012), (4.97, y0 + 0.008, zc + 0.006), (5.0, y0 + 0.01, 0.3), (5.3, y0 + 0.03, 0.008),
             (5.95, y0 + 0.035, 0.006), (6.15, y0 + 0.03, 0.06), (6.2, y0 + 0.03, 0.3)], 0.0025, "#e9e6df")
    C.box("LampPlug", (0.04, 0.035, 0.04), (6.2, y0 + 0.022, 0.28), P.PL("#f4f4f2", 0.3), bevel=0.006)
    small_plant(9.5, y0 + 0.3, Z(9.5, y0 + 0.3, 1.2), "anthurium", "#e9e6df", 0.08, 0.12)
    zb = Z(6.6, y1 - 0.3, 1.0)
    ph("football", 8.9, y0 + 0.25, part="inflated")


# =============================================================== BEDROOM ===
def bedroom(M):
    C.collection("Primary Bedroom")
    x0, y0, x1, y1 = S.inner("bedroom")
    S.radiator("BedRadiator", "x", y1 - 0.004, 2.1, 1.3, -1, M)
    X.curtains("BedCurtain", "x", y1, -1, 1.2, 3.0, color="#7f8c8a", z_top=2.5, open_frac=0.3, off=0.24)
    X.curtains("BedSheer", "x", y1, -1, 1.2, 3.0, z_top=2.5, sheer=True, off=0.17)
    # Bed with its bedding, two low bedside tables and the mirrored wardrobe: 'Bedroom' by SlykDrako (CC0)
    by = 8.6
    _bed, bparts = MI.kit("bedroom", "BedSet",
           keep=r"^(WoodFurniture|StainlessSmooth|Aluminium|Matress|Bedsheets|PictureFrame|PictureBacking|Picture|BookCover|BookPages)$",
           box=((-1.78, -1.08, -0.1), (1.86, 1.12, 1.0)), rot=PI / 2, loc=(x0 + 1.07, by - 0.015, 0.0))
    MI.kit("bedroom", "Wardrobe", keep=r"^(WoodFurniture|StainlessSmooth|Aluminium|Mirror|Blankets|Boxes)$",
           box=((-2.8, -0.9, -0.1), (-2.05, 0.9, 2.3)), rot=PI / 2, loc=(1.72, y0 + 2.76, 0.0))
    X.crib((x1 - 0.38, 9.72, 0), 0.0)
    ph("painted_wooden_cabinet", x1 - 0.33, 8.25, rot=F["W"])
    P.rug("BedRug", 1.15, 1.9, (2.9, 8.6, 0), kind="stripes")
    chair = ph("dining_chair_02", 2.92, 10.05, rot=0.5)
    P.ceiling_dome((2.2, 8.6, S.H), power=28, on=False)
    P.laundry_basket((3.82, 7.08, 0), 0.1)
    # walls
    P.frame((x0 + 0.004, by - 0.38, 1.6), "E", 0.5, 0.7, i=5, color="#b89a6a")
    P.frame((x0 + 0.004, by + 0.38, 1.6), "E", 0.5, 0.7, i=1, color="#b89a6a")
    ph("hanging_picture_frame_03", x1 - 0.02, 8.25, 1.45, rot=F["W"])
    refresh()

    # bedside tables (south one has the lamp that is on, the clock and the charging phone)
    ys, yn = by - 1.43, by + 1.49
    zt = Z(x0 + 0.33, ys + 0.2, 1.0)
    P.table_lamp((x0 + 0.3, ys + 0.16, zt), on=True, h=0.38, base="#d9d2c0")
    ph("alarm_clock_01", x0 + 0.38, ys - 0.02, zt, rot=F["E"] - 0.3, part="^rig_")
    P.phone((x0 + 0.42, ys + 0.26, zt), 1.2)
    zt2 = Z(x0 + 0.33, yn - 0.2, 1.0)
    P.table_lamp((x0 + 0.3, yn - 0.18, zt2), on=False, h=0.38, base="#d9d2c0")
    on("round_spectacles", x0 + 0.4, yn - 0.02, 1.0, rot=1.0)
    G.put("jar_cream", x0 + 0.22, yn + 0.02, zt2, 1.0, rough=0.25)
    # phone charger: adapter in the wall socket between table and bed, lead up to the phone
    C.box("ChargerPlug", (0.03, 0.045, 0.045), (x0 + 0.03, 7.63, 0.28), P.PL("#f4f4f2", 0.3), bevel=0.006)
    P.cable([(x0 + 0.045, 7.63, 0.3), (x0 + 0.1, 7.62, 0.06), (x0 + 0.42, 7.58, 0.006), (x0 + 0.56, 7.5, 0.1),
             (x0 + 0.5, ys + 0.3, zt + 0.004), (x0 + 0.43, ys + 0.27, zt + 0.006)], 0.0022, "#f1f1ee")
    P.slippers((2.5, 8.3, 0), PI / 2 + 0.2)
    for i, (sx_, sy_) in enumerate(((2.62, 7.62), (2.8, 7.5))):
        P.garment("Sock", 0.1, 0.24, (sx_, sy_, 0.0), [bpy.data.objects["Floor_bedroom"]], "#e4e0d6", "cotton_jersey", rot=0.6 + i, drop=0.06)
    # dresser top
    dx, dy = x1 - 0.33, 8.25
    zd = Z(dx, dy, 1.5)
    G.put("basket", dx + 0.04, dy - 0.36, zd, PI / 2 + 0.08, rough=0.8, spec=0.3)           # nappy-change bits live in here
    G.put("washcloth", dx + 0.04, dy - 0.36, zd + 0.07, PI / 2 + 0.3, rough=0.95, spec=0.2)
    on("standing_picture_frame_02", dx + 0.1, dy - 0.12, 1.5, rot=F["W"] - 0.2)
    C.box("BabyMonitor", (0.07, 0.04, 0.11), (dx + 0.12, dy + 0.22, zd), P.PL("#f1f1ee", 0.35), rot=-PI / 2 - 0.3, bevel=0.01)
    # clothes chair
    refresh()
    zc = Z(2.92, 10.0, 0.7)
    P.garment("Jeans", 0.5, 0.75, (2.93, 10.02, zc), [chair, bpy.data.objects["Floor_bedroom"]], "#2f3b52", "denim_fabric", rot=0.5)
    P.towel_hanging((2.8, 10.27, 0.985), "S", 0.38, 0.3, 0.35, "#d8d2c6", gap=0.03, tex="cotton_jersey").rotation_euler[2] = 0.5
    # floor
    ph("baseball_01", 3.2, 9.2, 0.014)
    P.picture_book((3.05, 8.95, 0.012), 1.1, 1)
    G.pair("boat", 3.25, 7.75, 0.0, 1.9, gap=0.13, stagger=0.07, splay=0.12)
    sc("teddy", x0 + 1.25, by + 0.45, 1.2, rot=1.9, rough=0.95, spec=0.2)                     # left on the parents' bed
    throw = C.drape("BedThrow", 0.72, 1.95, (x0 + 1.5, by + 0.06, 0.85), 0.07, P.creased(P.FAB("knitted_fleece", "#4f6d73", size=0.16, normal=2.0), 0.4, 0.6),
            [o for objs in bparts.values() for o in objs if o.type == "MESH"] + [bpy.data.objects["Floor_bedroom"]],
            bend=0.03, shrink=-0.04, res=44, thick=0.0035)
    if throw is not None:
        throw.location.z += 0.012                                        # clear of the bedspread it settled into


# ================================================================ OFFICE ===
def office(M):
    C.collection("Home Office")
    x0, y0, x1, y1 = S.inner("office")
    X.roller_blind("OfficeBlind", "x", y1 + 0.1, -1, 5.06, 6.54, 2.28, 0.55)
    ph("metal_office_desk", 5.8, y1 - 0.47, rot=F["S"])            # scanned steel desk (the generated one failed every blind test)
    X.office_chair((5.72, 9.2, 0), F["N"] + 0.35)
    P.rug("OfficeRug", 1.9, 1.4, (5.8, 9.0, 0), color=None, tex="wool_boucle", size=0.7)
    ph("steel_frame_shelves_01", x0 + 0.26, 8.3, rot=F["E"])
    ph("painted_wooden_shelves", x0 + 0.2, 9.45, rot=F["E"])
    osofa = ph("sofa_02", x1 - 0.42, 8.2, rot=F["W"])
    X.corkboard((x1 - 0.004, 8.2, 1.6), "W")
    P.ceiling_dome((5.8, 8.5, S.H), power=28, on=False)
    ph("cardboard_box_01", 7.1, 9.6, rot=0.15)
    ph("plastic_container", 7.0, 7.08, rot=PI / 2 + 0.1, scale=0.6)
    ph("Ukulele_01", 7.27, 9.38, 0.0, rot=-PI / 2, tilt=(-0.14, 0.0))
    P.backpack((4.72, 10.2, 0), 0.6, "#40574b")
    G.put("bin", 4.6, 9.9, 0.0, 0.3, rough=0.45)
    P.crumpled((4.6, 9.9, 0.008), 3, 0.045)
    P.crumpled((4.85, 9.72, 0.0), 1, 0.02)
    ph("wall_clock", 4.6, y0 + 0.03, 1.9, rot=F["N"])
    P.frame((6.6, y0 + 0.004, 1.5), "N", 0.5, 0.7, i=7, color="#1c1c1c")
    refresh()

    zt = Z(5.8, 10.0, 1.2)
    P.monitor((5.45, 10.2, zt), 0.0, kind="off")
    G.put("keyboard", 5.45, 9.9, zt, 0.02, rough=0.4)
    on("classic_laptop", 6.12, 10.02, 1.2, rot=PI + 0.35, scale=0.56)
    C.box("Mousepad", (0.24, 0.2, 0.003), (5.82, 9.9, zt), P.PL("#1d1d1f", 0.9), bevel=0.001)
    G.put("mouse", 5.82, 9.9, zt + 0.003, 0.1, rough=0.4)
    X.desk_lamp((6.58, 10.3, zt), 0.5)
    G.put("mug_teal", 6.55, 10.02, zt, 5.2, rough=0.12)
    G.put("drive", 5.93, 10.24, zt, 0.25, rough=0.35, pre=(0, PI / 2, 0))
    P.mug((5.0, 10.3, zt), "#333333", full=False)
    for i in range(3):
        C.pipe("Pen", [(4.98 + i * 0.012, 10.3, zt + 0.01), (4.97 + i * 0.03, 10.31 - i * 0.02, zt + 0.17)], 0.004,
               P.PL(P.TOY_COLORS[i]), smooth=False)
    on("office_notepads", 6.1, 9.7, 1.2, rot=0.2, part="a4_stack")
    on("stationery_supplies", 6.14, 9.72, 1.2, rot=0.9, part="pen_blue")
    on("clipboard", 6.45, 9.72, 1.2, rot=0.25)
    on("round_spectacles", 6.43, 9.74, 1.2, rot=2.2)
    on("vintage_stapler", 6.68, 10.14, 1.2, rot=1.1)
    on("binder_notebook", 6.7, 9.78, 1.2, rot=-0.3)
    P.headphones((5.05, 9.86, zt + 0.045), 0.7)
    P.phone((5.95, 9.68, zt), -0.2)
    P.power_strip((5.5, 10.33, 0), 0.05)
    P.cable([(5.45, 10.26, zt + 0.1), (5.45, 10.4, zt - 0.1), (5.5, 10.38, 0.03)])
    P.cable([(6.12, 10.2, zt + 0.02), (6.0, 10.41, zt - 0.05), (5.6, 10.4, 0.03)])
    small_plant(6.35, y1 + 0.06, 0.854, "fern2", "#d9d4c8")
    # shelves
    sx, sy = x0 + 0.27, 8.3
    shelf_fill(sx, sy, F["E"], 0.96, 0.0, 2.3, [
        (0.0, lambda x, y, z: (ph("boombox", x, y - 0.25, z, rot=F["E"], scale=0.7), storage_box(x, y - 0.75, z, "#59636b", rot=PI / 2))),
        (0.7, lambda x, y, z: ph("standing_picture_frame_01", x, y, z, rot=F["E"] + 0.2)),
        (0.55, lambda x, y, z: ph("Camera_01", x, y - 0.05, z, rot=1.3, part="^Camera_01$")),
        (0.85, None),
        (0.0, lambda x, y, z: (storage_box(x, y, z, "#b9a98c", (0.34, 0.3, 0.24), PI / 2), games(x, y - 0.42, z, 4, PI / 2))),
    ])
    zs = Z(x0 + 0.2, 9.45, 1.6)
    X.printer((x0 + 0.24, 9.45, zs), F["E"])
    # sofa
    zf = Z(x1 - 0.5, 8.2, 1.0)
    P.cushion((x1 - 0.32, 8.75, zf + 0.19), rot=-PI / 2 + 0.2, s=0.42, color="#b98a4a", tilt=1.15)
    P.garment("Sweater", 0.6, 0.7, (x1 - 0.5, 7.82, zf), [osofa], "#b24b3f", "knitted_fleece", rot=0.3)
    P.garment("Shirt", 0.55, 0.6, (x1 - 0.55, 8.22, zf), [osofa], "#d8d2c6", "cotton_jersey", rot=1.2)
    zb = Z(7.1, 9.6, 1.0)
    ph("cardboard_box_01", 7.12, 9.58, zb, rot=0.5, scale=0.75)


# ================================================================== BATH ===
def bath(M):
    """Wood vanity with two marble basins, long mirror and pendant bulbs, a freestanding tub, the rug
    and the wall shelf come from 'Contemporary Bathroom' by Mareck (CC0), turned so that its window
    wall is our north wall and widened 3.5 % to span the room. Toilet, towel rail and the family's
    things are ours."""
    C.collection("Bathroom")
    x0, y0, x1, y1 = S.inner("bath")
    k = (x1 - x0) / 2.31
    lx, ly = x0 - 0.19 * k, y1 - 2.5 * k
    _kit, _parts = MI.kit("bathroom", "ContempBath", drop=r"^(Floor|GreyWall|Ceiling|Wallpaper|WhiteWood|WindowFrame|Blinds|BlindsString|Light|Leaves|LeaveStems|Foam|Painting3|Painting4)$",
           box=((-2.7, 0.0, -0.1), (0.3, 2.6, 3.0)), scale=k, rot=-PI / 2, loc=(lx, ly, 0.0))
    mm = bpy.data.materials.get("bathroom:Marble")
    if mm:                                                             # the scene's UVs smear the stone over the basin sides
        nt = mm.node_tree
        tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
        tex.projection, tex.projection_blend = "BOX", 0.2
        tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1.7, 1.7, 1.7)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs[0], tex.inputs["Vector"])
        nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.22
    for o in _parts.get("Marble", []):
        bv = o.modifiers.new("Arris", "BEVEL")
        bv.width, bv.segments, bv.limit_method, bv.angle_limit = 0.003, 2, "ANGLE", 0.7
    ch = P.METAL("chrome")
    ty_ = 9.52                                                         # bath filler on the wall, waste in the tub floor
    C.cyl("BathTapRose", 0.03, 0.01, (x0 + 0.004, ty_, 0.82), ch, rot=(0, PI / 2, 0), segs=24)
    C.pipe("BathSpout", [(x0 + 0.006, ty_, 0.82), (x0 + 0.13, ty_, 0.82), (x0 + 0.17, ty_, 0.775)], 0.013, ch)
    for sgn in (-1, 1):
        C.cyl("BathTapHead", 0.024, 0.045, (x0 + 0.004, ty_ + sgn * 0.13, 0.82), ch, rot=(0, PI / 2, 0), segs=20, bevel=0.004)
        C.box("BathTapLever", (0.012, 0.07, 0.012), (x0 + 0.055, ty_ + sgn * 0.13, 0.814), ch, bevel=0.004, rot=0.3 * sgn)
    for i, bxs in enumerate((-1.7, -1.36, -1.0)):                      # the pendant bulbs over the vanity are on
        C.light("VanityBulb{}".format(i), (lx + k * 2.2, ly - k * bxs, 1.89 * k), 7, "#ffd9a8", radius=0.03)
    X.roller_blind("BathBlind", "x", y1 + 0.1, -1, 8.5, 9.1, 2.18, 0.42, "#e9e5da")
    X.toilet((x0, 7.75, 0), F["E"])
    X.towel_radiator((x1, 7.3, 0), F["W"])
    P.ceiling_dome((8.65, 8.3, S.H), power=22)
    P.laundry_basket((x0 + 0.27, 7.05, 0), PI / 2)
    X.wall_shelf((x0 + 0.004, 7.75, 1.25), "E", 0.7, 0.18)
    C.pipe("TPHolder", [(x0 + 0.004, 8.2, 0.72), (x0 + 0.08, 8.2, 0.72), (x0 + 0.08, 8.35, 0.72)], 0.008, P.METAL("chrome"), smooth=False)
    C.cyl("TPHolderRose", 0.024, 0.008, (x0 + 0.004, 8.2, 0.72), P.METAL("chrome"), rot=(0, PI / 2, 0), segs=20)
    P.toilet_roll((x0 + 0.08, 8.33, 0.72), (PI / 2, 0, 0))
    C.cyl("BrushHolder", 0.05, 0.14, (x0 + 0.12, 7.4, 0), P.PL("#f1f1ee", 0.35), bevel=0.008)
    C.pipe("BrushHandle", [(x0 + 0.12, 7.4, 0.1), (x0 + 0.12, 7.4, 0.42)], 0.007, P.PL("#f1f1ee", 0.35), smooth=False)
    P.bin_round((x0 + 0.14, 8.5, 0), 0.08, 0.24, P.PL("#f1f1ee", 0.35))
    ph("plunger", x0 + 0.12, 8.08)
    on("bleach_bottle", x0 + 0.1, 6.78, 0.5, rot=1.0)
    ph("potted_plant_04", 8.8, y1 + 0.07, 1.404, scale=1.1)
    ph("wooden_stool_01", 8.56, 9.82, rot=0.4)                         # scanned stool by the tub for the bath towel
    bw = [bpy.data.objects["Skin_bath"]]
    P.towel_hanging((x1 - 0.06, 7.15, 1.565), "W", 0.4, 0.55, 0.38, "#c9d3d6", colliders=bw)
    P.towel_hanging((x1 - 0.06, 7.42, 1.21), "W", 0.36, 0.36, 0.28, "#e2b8a0", colliders=bw)
    refresh()
    # shampoo within reach of the tub, on the wall shelf above it
    for yy, args in ((8.72, (0.068, 0.04, 0.22, "#2f7fa6", "#ffffff", "#f4f1ea", (("NORDA", 0.012), ("shampoo", 0.007), ("400 ml", 0.005)), "#173247", "Shampoo")),
                     (8.86, (0.062, 0.038, 0.19, "#f0e4c4", "#3a3a3a", "#ffffff", (("Dr. Hale", 0.0095), ("body wash", 0.0065), ("sensitive", 0.005)), "#30463a", "BodyWash")),
                     (9.0, (0.06, 0.038, 0.165, "#e77fa6", "#ffffff", "#fff6da", (("lumi", 0.014), ("kids 2in1", 0.0065)), "#7a2d58", "KidsShampoo"))):
        zs_ = Z(x0 + 0.07, yy, 1.9)
        if zs_ > 1.0:
            P.flat_bottle((x0 + 0.07, yy, zs_), PI / 2 + R.uniform(-0.2, 0.2), *args[:8], name=args[8])
    ph("rubber_duck_toy", x0 + 0.45, 9.25, Z(x0 + 0.45, 9.25, 1.0), rot=2.9, scale=0.36)
    C.cyl("BathWaste", 0.027, 0.004, (x0 + 0.4, 9.9, Z(x0 + 0.4, 9.9, 0.5)), P.METAL("chrome"), segs=24)
    sc("bath_towel_blue", 8.56, 9.82, 1.0, rot=0.55, rough=0.95, spec=0.2)
    # vanity top, south of the basins
    zv = Z(x1 - 0.2, 8.2, 1.2)
    X.toothbrush_cup((x1 - 0.1, 8.1, zv))
    G.put("fish_holder", x1 - 0.12, 8.3, zv, PI / 2, rough=0.15)          # the child's
    G.put("soap_dish", x1 - 0.37, 8.31, zv, 0.2, rough=0.2)
    G.put("hand_towel", x1 - 0.36, 8.1, zv, 0.1, rough=0.95, spec=0.2)
    G.put("jar_cream", x1 - 0.22, 8.21, zv, 2.0, rough=0.25)
    G.put("argan", x1 - 0.11, 8.19, zv, F["W"] + 0.2, rough=0.4)
    P.flat_bottle((x1 - 0.1, 9.34, Z(x1 - 0.1, 9.34, 1.2)), -PI / 2 + 0.2, 0.055, 0.034, 0.15, "#e9ede6", "#9fb7a8", "#ffffff",
                  (("mild", 0.011), ("face wash", 0.006)), "#365246", name="FaceWash")
    # shelf above the toilet
    zs = 1.25
    for i in range(3):
        P.toilet_roll((x0 + 0.1, 7.5 + i * 0.115, zs))
    P.toilet_roll((x0 + 0.1, 7.56, zs + 0.1))
    P.bottle((x0 + 0.09, 7.95, zs), 0.15, 0.03, "#f4f0e6", "#b89a6a", name="Lotion2")
    P.candle((x0 + 0.1, 8.04, zs), 0.06, 0.03)


def furnish(M):
    import importlib
    importlib.reload(W)
    importlib.reload(MI)
    importlib.reload(G)
    switches(M)
    for fn in (living, kitchen, hall, bedroom, office, bath):
        fn(M)
    refresh()
    # crumbs where the family eats (after refresh, so each one lands on what is really under it)
    C.collection("Kitchen")
    tx, ty = 7.44, 0.97
    zt = Z(tx, ty, 1.2)
    W.crumbs("CrumbsKid", (tx - 0.1, ty + 0.3, zt), 16, 0.1, hole=0.07, seed=5, zf=lambda x, y: Z(x, y, zt + 0.05))
    W.crumbs("CrumbsFloor", (tx - 0.35, ty + 0.75, 0.0), 26, 0.24, seed=8, zf=lambda x, y: Z(x, y, 0.05))
    W.apply(M)
    refresh()

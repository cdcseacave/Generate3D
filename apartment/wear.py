"""Lived-in imperfections layered on top of finished materials: stains, scratches and
smudges placed by world position, dust that settles on upward faces, a dirt film on
glass, crumbs, and a toddler's crayon scribble.

Everything here edits existing node trees in place. Marks are ellipsoids in world space,
so one shared material (all the walls of a room, every part of the sofa) can carry marks
at specific spots without new UVs or decal geometry."""
import math
import os
import random
import re

import bpy

from . import core as C
from . import shell as S


def _bsdf(m):
    if not m or not m.node_tree:
        return None
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def _blend(nt, bsdf, name, fac, value):
    """Mix a Principled input towards `value` by the factor socket `fac`, keeping whatever fed it."""
    inp = bsdf.inputs[name]
    mx = nt.nodes.new("ShaderNodeMix")
    if inp.type == "RGBA":
        mx.data_type = "RGBA"
        a, b, out = mx.inputs[6], mx.inputs[7], mx.outputs[2]
        b.default_value = C.rgb(value)
        if not inp.links:
            a.default_value = tuple(inp.default_value)
    else:
        mx.data_type = "FLOAT"
        a, b, out = mx.inputs[2], mx.inputs[3], mx.outputs[0]
        b.default_value = value
        if not inp.links:
            a.default_value = inp.default_value
    if inp.links:
        nt.links.new(inp.links[0].from_socket, a)
    nt.links.new(fac, mx.inputs[0])
    nt.links.new(out, inp)


def _math(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _range(nt, value, f0, f1, t0, t1, smooth=True):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.clamp = True
    if smooth:
        n.interpolation_type = "SMOOTHSTEP"
    for k, v in (("From Min", f0), ("From Max", f1), ("To Min", t0), ("To Max", t1)):
        n.inputs[k].default_value = v
    nt.links.new(value, n.inputs["Value"])
    return n.outputs[0]


def _noise(nt, vec, scale, detail=3.0, rough=0.55):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    nt.links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def spots(mat, items, color, key, rough=None, metal=None, ragged=0.3, patchy=0.0, fine=120.0, ring=False, cover=(0.46, 0.62), sheen=None):
    """Marks on `mat`. items: (world position, radii (x, y, z), euler rotation, strength 0..1).
    `ragged` roughens the outline, `patchy` breaks the inside up into specks (scuffs,
    spatter; `cover` = noise thresholds, higher means sparser specks), `ring` leaves the
    centre lighter than the rim (dried liquid)."""
    bsdf = _bsdf(mat)
    if bsdf is None or not items or mat.get("wear_" + key):
        return False
    mat["wear_" + key] = 1
    nt = mat.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    pos = geo.outputs["Position"]
    off = _math(nt, "MULTIPLY_ADD", _noise(nt, pos, 11.0), 2.0 * ragged)
    off.node.inputs[2].default_value = -ragged
    acc = None
    for p, radii, rot, strength in items:
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.vector_type = "TEXTURE"                     # inverse transform: world -> unit sphere of the mark
        mp.inputs["Location"].default_value = p
        mp.inputs["Rotation"].default_value = rot
        mp.inputs["Scale"].default_value = radii
        nt.links.new(pos, mp.inputs["Vector"])
        ln = nt.nodes.new("ShaderNodeVectorMath")
        ln.operation = "LENGTH"
        nt.links.new(mp.outputs[0], ln.inputs[0])
        d = _math(nt, "ADD", ln.outputs["Value"], off)
        m = _range(nt, d, 1.0, 0.6, 0.0, strength)
        if ring:
            m = _math(nt, "SUBTRACT", m, _range(nt, d, 0.78, 0.5, 0.0, strength * 0.7))
        acc = m if acc is None else _math(nt, "MAXIMUM", acc, m)
    if patchy:
        acc = _math(nt, "MULTIPLY", acc, _range(nt, _noise(nt, pos, fine, 2.0), cover[0], cover[1], 1.0 - patchy, 1.0))
    _blend(nt, bsdf, "Base Color", acc, color)
    if rough is not None:
        _blend(nt, bsdf, "Roughness", acc, rough)
    if metal is not None:
        _blend(nt, bsdf, "Metallic", acc, metal)
    if sheen is not None and "Sheen Weight" in bsdf.inputs:      # matted fibres lose the fabric's soft sheen
        _blend(nt, bsdf, "Sheen Weight", acc, sheen)
    return True


def dust(mat, amount=0.3, color="#b6aea1", high=False):
    """Settled dust: a pale matte film on faces that point up, broken up so it is
    thicker in some places, and (high=True) heavier above reach height."""
    bsdf = _bsdf(mat)
    if bsdf is None or mat.get("wear_dust"):
        return False
    mat["wear_dust"] = 1
    nt = mat.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    nz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["True Normal"], nz.inputs[0])
    up = _range(nt, nz.outputs["Z"], 0.6, 0.95, 0.0, 1.0)
    fac = _math(nt, "MULTIPLY", up, _range(nt, _noise(nt, geo.outputs["Position"], 4.0, 5.0), 0.3, 0.7, 0.35, 1.0))
    fac = _math(nt, "MULTIPLY", fac, amount)
    if high:
        pz = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], pz.inputs[0])
        fac = _math(nt, "MULTIPLY", fac, _range(nt, pz.outputs["Z"], 1.2, 1.9, 0.55, 1.6))
    _blend(nt, bsdf, "Base Color", fac, color)
    _blend(nt, bsdf, "Roughness", fac, 0.95)
    if bsdf.inputs["Metallic"].links or bsdf.inputs["Metallic"].default_value > 0.0:
        _blend(nt, bsdf, "Metallic", fac, 0.0)
    return True


def grime(mat, amount=0.15, color="#8f8676", scale=3.0, rough_to=None, kick=0.0):
    """Handling grime on fronts and doors: soft irregular patches (finger grease changes the
    sheen more than the colour) and, with `kick`, scuffing that builds up near the floor."""
    bsdf = _bsdf(mat)
    if bsdf is None or mat.get("wear_grime"):
        return False
    mat["wear_grime"] = 1
    nt = mat.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    pos = geo.outputs["Position"]
    fac = _math(nt, "MULTIPLY", _range(nt, _noise(nt, pos, scale, 4.0, 0.6), 0.5, 0.74, 0.0, 1.0), amount)
    if kick:
        pz = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(pos, pz.inputs[0])
        low = _math(nt, "MULTIPLY", _range(nt, pz.outputs["Z"], 0.02, 0.32, kick, 0.0),
                    _range(nt, _noise(nt, pos, 26.0, 3.0), 0.42, 0.66, 0.0, 1.0))
        fac = _math(nt, "MAXIMUM", fac, low)
    if color:
        _blend(nt, bsdf, "Base Color", fac, color)
    if rough_to is not None:
        _blend(nt, bsdf, "Roughness", _math(nt, "MULTIPLY", fac, min(1.0, 0.5 / max(amount, 1e-3))), rough_to)
    return True


def blotch(rnd, center, r, strength, n=3):
    """An irregular stain as a few overlapping lobes, never a neat disc."""
    cx, cy, cz = center
    items = []
    for i in range(n):
        k = 1.0 if i == 0 else rnd.uniform(0.45, 0.8)
        a = rnd.uniform(0, 6.28)
        off = 0.0 if i == 0 else rnd.uniform(0.5, 0.95) * r
        items.append(((cx + off * math.cos(a), cy + off * math.sin(a), cz), (r * k * rnd.uniform(0.75, 1.25), r * k * rnd.uniform(0.6, 1.0), 0.08),
                      (0.0, 0.0, rnd.uniform(0, 3.1)), strength * (1.0 if i == 0 else rnd.uniform(0.6, 0.9))))
    return items


def film(mat, amount=0.06, scale=7.0):
    """Dirt / dried water spots on glass, seen by the camera only (light transport unchanged)."""
    if not mat or not mat.node_tree or mat.get("wear_film"):
        return False
    nt = mat.node_tree
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out is None or not out.inputs[0].links:
        return False
    mat["wear_film"] = 1
    src = out.inputs[0].links[0].from_socket
    tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
    df = nt.nodes.new("ShaderNodeBsdfDiffuse")
    for n in (tl, df):
        n.inputs["Color"].default_value = (0.62, 0.6, 0.56, 1.0)
    dirt = nt.nodes.new("ShaderNodeMixShader")
    dirt.inputs[0].default_value = 0.5
    nt.links.new(tl.outputs[0], dirt.inputs[1])
    nt.links.new(df.outputs[0], dirt.inputs[2])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    lp = nt.nodes.new("ShaderNodeLightPath")
    fac = _range(nt, _noise(nt, geo.outputs["Position"], scale, 4.0, 0.65), 0.42, 0.72, 0.25, 1.0)
    fac = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", fac, amount), lp.outputs["Is Camera Ray"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fac, mix.inputs[0])
    nt.links.new(src, mix.inputs[1])
    nt.links.new(dirt.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return True


def crumbs(name, center, n=14, spread=0.1, hole=0.0, seed=1, color="#c79a58", zf=None):
    """A scatter of irregular crumbs lying on the surface at center[2]; `hole` keeps a clear
    disc (a plate). zf(x, y) -> surface height lets each crumb sit on what is really there
    (a placemat), and drops any that would land on top of another object."""
    import bmesh
    from mathutils import Euler, Matrix, Vector
    rnd = random.Random(seed)
    bm = bmesh.new()
    for _ in range(n):
        r = rnd.uniform(max(hole, 0.0), max(hole, 0.0) + spread) if hole else abs(rnd.gauss(0, spread * 0.55))
        a = rnd.uniform(0, 2 * math.pi)
        s = rnd.uniform(0.0012, 0.0032)
        cx, cy, cz = center[0] + r * math.cos(a), center[1] + r * math.sin(a), center[2]
        if zf is not None:
            z = zf(cx, cy)
            if z is None or not (center[2] - 0.002 <= z <= center[2] + 0.007):
                continue
            cz = z
        made = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        mtx = (Matrix.Translation(Vector((cx, cy, cz + s * 0.45)))
               @ Euler((rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))).to_matrix().to_4x4()
               @ Matrix.Diagonal((s * rnd.uniform(0.8, 1.7), s * rnd.uniform(0.7, 1.3), s * rnd.uniform(0.45, 0.8), 1.0)))
        bmesh.ops.transform(bm, matrix=mtx, verts=made["verts"])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    me.materials.append(C.mat("Crumb_" + color, color, rough=0.9, noise=0.2))
    return C._link(ob)


def scribble(name, center, axis, sgn, w=0.5, h=0.34, seed=4):
    """Crayon on the wall at toddler height: a transparent decal a hair off the plaster.
    axis 'x' = wall runs along X; sgn = which way the wall face points along the other axis."""
    import numpy as np
    rnd = random.Random(seed)
    W, Hh = 640, int(640 * h / w)
    px = np.zeros((Hh, W, 4), dtype=np.float32)
    ys, xs = np.mgrid[0:Hh, 0:W].astype(np.float32)
    for col, loops, x0 in (((0.80, 0.16, 0.13), 26, 0.36), ((0.13, 0.33, 0.72), 18, 0.66)):
        x, y = x0 * W, 0.5 * Hh
        ang = rnd.uniform(0, 6.28)
        for _ in range(loops * 6):
            ang += rnd.gauss(0.75, 0.5)                       # mostly looping, like a fist-held crayon
            step = rnd.uniform(14, 34)
            nx = min(max(x + math.cos(ang) * step * 1.5, 0.06 * W), 0.94 * W)
            ny = min(max(y + math.sin(ang) * step, 0.1 * Hh), 0.9 * Hh)
            xa, xb, ya, yb = int(min(x, nx)) - 4, int(max(x, nx)) + 5, int(min(y, ny)) - 4, int(max(y, ny)) + 5
            xa, ya = max(xa, 0), max(ya, 0)
            sx, sy = xs[ya:yb, xa:xb], ys[ya:yb, xa:xb]
            dx, dy = nx - x, ny - y
            t = np.clip(((sx - x) * dx + (sy - y) * dy) / max(dx * dx + dy * dy, 1e-6), 0, 1)
            dist = np.hypot(sx - (x + t * dx), sy - (y + t * dy))
            a = np.clip(1.6 - dist / 1.5, 0, 1) * rnd.uniform(0.45, 0.85)
            reg = px[ya:yb, xa:xb]
            reg[..., :3] = np.where(a[..., None] > 0, np.array(col, dtype=np.float32), reg[..., :3])
            reg[..., 3] = np.maximum(reg[..., 3], a)
            x, y = nx, ny
    px[..., 3] *= 0.55 + 0.45 * np.random.default_rng(seed).random((Hh, W), dtype=np.float32)   # waxy, skips the plaster grain
    os.makedirs(C.GEN, exist_ok=True)
    path = os.path.join(C.GEN, name + ".png")
    img = bpy.data.images.new("gen_" + name, W, Hh, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(px[::-1], dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    m, nt, bsdf, _ = C._new_mat(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "CLIP"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.55
    cx, cy, cz = center
    if axis == "x":
        u = -sgn                                             # keep the image unmirrored when seen from the room
        co = [(cx - u * w / 2, cy, cz - h / 2), (cx + u * w / 2, cy, cz - h / 2), (cx + u * w / 2, cy, cz + h / 2), (cx - u * w / 2, cy, cz + h / 2)]
    else:
        u = sgn
        co = [(cx, cy - u * w / 2, cz - h / 2), (cx, cy + u * w / 2, cz - h / 2), (cx, cy + u * w / 2, cz + h / 2), (cx, cy - u * w / 2, cz + h / 2)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(co, [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    ob.visible_shadow = False
    return C._link(ob)


# ---------------------------------------------------------------- placement ---
def _mats(pattern):
    """Materials of every object whose name, or whose material's name, matches the pattern."""
    rx, out = re.compile(pattern), []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.users_scene:
            continue
        names, q = [], o
        while q is not None:                       # grouped props carry their name on the parent empty
            names.append(q.name)
            q = q.parent
        for sl in o.material_slots:
            m = sl.material
            if m and (rx.search(m.name) or any(rx.search(n) for n in names)) and m not in out:
                out.append(m)
    return out


def _center(name):
    from mathutils import Vector
    o = bpy.data.objects.get(name)
    if o is None:
        return None
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(pts, Vector()) / 8.0


def apply(M):
    """Dress the finished flat with the wear a family of three leaves behind."""
    rnd = random.Random(23)
    bpy.context.view_layer.update()
    SCRATCH, SMUDGE, DUSTC = "#5b5349", "#8b8173", "#b9b2a6"

    def wall_of(x, y):
        for room in S.ROOMS:
            x0, y0, x1, y1 = S.inner(room)
            if x0 - 0.03 <= x <= x1 + 0.03 and y0 - 0.03 <= y <= y1 + 0.03:
                return None if room == "bath" else M["wall_" + room]
        return None

    scratch, smudge, chips = {}, {}, []

    def add(store, m, item):
        if m is not None:
            store.setdefault(m.name, (m, []))[1].append(item)

    def streak(axis, a, face, z, length, width, ang):
        """A thin mark lying in the wall plane."""
        if axis == "x":
            return ((a, face, z), (length, 0.05, width), (0.0, ang, 0.0))
        return ((face, a, z), (0.05, length, width), (ang, 0.0, 0.0))

    # --- walls by the doors: key and bag scratches at hand height, wider rubbed smears,
    #     and knocks on the painted casings lower down
    for w in S.WALLS:
        for o in w.openings:
            if o.kind not in ("door", "arch"):
                continue
            for side in (-1, 1):
                face = w.c + side * w.t / 2
                mid = S.P(w.axis, (o.s0 + o.s1) / 2, face + side * 0.12, 0.0)
                wm = wall_of(mid[0], mid[1])
                if wm is None:
                    continue
                for jamb, out in ((o.s0, -1), (o.s1, 1)):
                    for _ in range(rnd.randint(2, 3)):
                        a = jamb + out * rnd.uniform(0.13, 0.42)
                        p, r, e = streak(w.axis, a, face, rnd.uniform(0.5, 1.25), rnd.uniform(0.015, 0.05),
                                         rnd.uniform(0.0016, 0.003), rnd.gauss(0.0, 0.5))
                        add(scratch, wm, (p, r, e, rnd.uniform(0.45, 0.7)))
                    p, r, e = streak(w.axis, jamb + out * rnd.uniform(0.15, 0.35), face, rnd.uniform(0.62, 1.0),
                                     rnd.uniform(0.035, 0.075), rnd.uniform(0.009, 0.018), rnd.gauss(0.0, 0.3))
                    add(smudge, wm, (p, r, e, rnd.uniform(0.16, 0.26)))
                    for _ in range(2):
                        cp = S.P(w.axis, jamb + out * rnd.uniform(0.0, 0.05), face + side * 0.008, rnd.uniform(0.08, 0.95))
                        chips.append((cp, (rnd.uniform(0.012, 0.03), rnd.uniform(0.012, 0.03), rnd.uniform(0.02, 0.06)),
                                      (0.0, 0.0, 0.0), rnd.uniform(0.45, 0.75)))

    # --- finger marks around every light switch, hand grime around the door levers
    for o in list(bpy.data.objects):
        if re.match(r"^Sw_[A-Za-z]+$", o.name):
            c = _center(o.name)
            add(smudge, wall_of(c.x, c.y), (tuple(c), (0.1, 0.1, 0.13), (0.0, 0.0, 0.0), 0.3))
    levers = [(tuple(_center(o.name)), (0.12, 0.12, 0.14), (0.0, 0.0, 0.0), 0.4)
              for o in bpy.data.objects if o.name.endswith("_lever")]
    spots(M["door"], levers, "#857b6c", "hands", rough=0.5, ragged=0.35, patchy=0.35, fine=60.0)

    # --- by the entrance: shoes and bags against the wall, low down
    hx0, hy0, hx1, hy1 = S.inner("hall")
    for _ in range(7):
        p, r, e = streak("x", rnd.uniform(0.35, 2.4), hy1, rnd.uniform(0.1, 0.5), rnd.uniform(0.03, 0.08),
                         rnd.uniform(0.006, 0.014), rnd.gauss(0.0, 0.35))
        add(smudge, M["wall_hall"], (p, r, e, rnd.uniform(0.18, 0.3)))
    for _ in range(4):
        p, r, e = streak("x", rnd.uniform(3.6, 7.2), hy0 if rnd.random() < 0.5 else hy1, rnd.uniform(0.25, 0.9),
                         rnd.uniform(0.015, 0.05), rnd.uniform(0.0016, 0.003), rnd.gauss(0.0, 0.4))
        add(scratch, M["wall_hall"], (p, r, e, rnd.uniform(0.45, 0.7)))
    # splashes on the kitchen wall behind the bin
    kx0, ky0, kx1, ky1 = S.inner("kitchen")
    for _ in range(6):
        add(smudge, M["wall_kitchen"], ((kx0, rnd.uniform(4.0, 4.45), rnd.uniform(0.25, 0.65)),
                                        (0.05, rnd.uniform(0.012, 0.03), rnd.uniform(0.015, 0.045)), (0.0, 0.0, 0.0), 0.45))
    # chair backs against the kitchen wall, soot streak above the hall radiator
    for _ in range(4):
        p, r, e = streak("y", rnd.uniform(2.2, 3.4), kx0, rnd.uniform(0.74, 0.86), rnd.uniform(0.05, 0.1), rnd.uniform(0.006, 0.01), rnd.gauss(0.0, 0.08))
        add(smudge, M["wall_kitchen"], (p, r, e, 0.3))
    spots(M["wall_hall"], [((4.25, hy1, 1.02), (0.55, 0.05, 0.34), (0, 0, 0), 0.16)], "#6d665c", "soot", ragged=0.2)
    # everyday knocks around every room, one touched-up patch of paint, old nail holes
    for room in ("living", "kitchen", "hall", "bedroom", "office"):
        x0, y0, x1, y1 = S.inner(room)
        wm = M["wall_" + room]

        def on_wall():
            if rnd.random() < 0.5:
                return "x", rnd.uniform(x0 + 0.3, x1 - 0.3), rnd.choice((y0, y1))
            return "y", rnd.uniform(y0 + 0.3, y1 - 0.3), rnd.choice((x0, x1))

        for _ in range(12):
            ax, a_, face = on_wall()
            if rnd.random() < 0.6:
                p, r, e = streak(ax, a_, face, rnd.uniform(0.2, 1.3), rnd.uniform(0.012, 0.045), rnd.uniform(0.0016, 0.003), rnd.gauss(0.0, 0.6))
                add(scratch, wm, (p, r, e, rnd.uniform(0.4, 0.65)))
            else:
                p, r, e = streak(ax, a_, face, rnd.uniform(0.2, 1.2), rnd.uniform(0.03, 0.07), rnd.uniform(0.008, 0.016), rnd.gauss(0.0, 0.4))
                add(smudge, wm, (p, r, e, rnd.uniform(0.14, 0.24)))
        for _ in range(4):
            ax, a_, face = on_wall()
            p, r, e = streak(ax, a_, face, rnd.uniform(1.35, 1.85), 0.0035, 0.0035, 0.0)
            add(scratch, wm, (p, r, e, 0.9))
        ax, a_, face = on_wall()
        p, r, e = streak(ax, a_, face, rnd.uniform(0.9, 1.6), rnd.uniform(0.22, 0.4), rnd.uniform(0.18, 0.3), 0.0)
        spots(wm, [(p, r, e, 0.3)], "#f7f4ee", "touchup", rough=0.78, ragged=0.1)
    for m, items in scratch.values():
        spots(m, [(q, r_, e, st * 0.55) for q, r_, e, st in items], SCRATCH, "scratch", ragged=0.4)
    for m, items in smudge.values():
        spots(m, [(q, r_, e, st * 0.6) for q, r_, e, st in items], SMUDGE, "smudge", rough=0.5, ragged=0.6, patchy=0.2, fine=18.0)

    # --- painted woodwork: knocks on casings, vacuum-cleaner and shoe scuffs on the skirting
    for _ in range(26):
        if rnd.random() < 0.5:
            cp = (rnd.uniform(hx0 + 0.2, hx1 - 0.2), hy0 if rnd.random() < 0.5 else hy1, rnd.uniform(0.015, 0.065))
            rr = (rnd.uniform(0.03, 0.1), 0.04, rnd.uniform(0.006, 0.012))
        else:
            room = rnd.choice(("living", "bedroom", "office", "kitchen"))
            x0, y0, x1, y1 = S.inner(room)
            cp = (rnd.choice((x0, x1)), rnd.uniform(y0 + 0.3, y1 - 0.3), rnd.uniform(0.015, 0.065))
            rr = (0.04, rnd.uniform(0.03, 0.1), rnd.uniform(0.006, 0.012))
        chips.append((cp, rr, (0.0, 0.0, 0.0), rnd.uniform(0.4, 0.7)))
    spots(M["trim"], chips, "#6f675c", "chips", rough=0.6, ragged=0.3, patchy=0.3, fine=90.0)

    # --- soft furnishings
    for m in _mats(r"^Fabric_Sofa"):
        # spills that dried in: matted, sheen gone, irregular
        st = blotch(rnd, (2.6, 2.78, 0.39), 0.085, 0.5) + blotch(rnd, (2.85, 1.72, 0.39), 0.06, 0.42, 2)
        st += blotch(rnd, (3.1, 3.4, 0.7), 0.07, 0.36, 2) + blotch(rnd, (2.95, 1.04, 0.57), 0.06, 0.34, 2)
        spots(m, st, "#141110", "stain", rough=0.6, ragged=0.55, sheen=0.1)
    for m in _mats(r"Chocofur_Rug|^Carpet Grey"):
        st = blotch(rnd, (1.6, 1.8, 0.0), 0.13, 0.8) + blotch(rnd, (1.78, 2.82, 0.0), 0.08, 0.7, 2)
        st += blotch(rnd, (2.6, 1.2, 0.0), 0.07, 0.65, 2) + blotch(rnd, (1.95, 1.25, 0.0), 0.09, 0.75)
        spots(m, st, "#d2c9b6", "stain", ragged=0.5, patchy=0.3, fine=60.0)                # dried milk on the dark pile
    for m in _mats(r"^HallRunner"):
        spots(m, [((2.75, 5.5, 0.0), (0.1, 0.07, 0.08), (0, 0, 0.5), 0.42), ((3.25, 5.78, 0.0), (0.07, 0.09, 0.08), (0, 0, 0), 0.36),
                  ((3.9, 5.52, 0.0), (0.09, 0.06, 0.08), (0, 0, -0.4), 0.3), ((5.6, 5.66, 0.0), (0.06, 0.05, 0.08), (0, 0, 0), 0.3)],
              "#6a5743", "stain", ragged=0.45, patchy=0.4, fine=55.0)                    # trodden-in dirt from the door
    for m in _mats(r"^BedRug"):
        spots(m, [((2.72, 8.28, 0.0), (0.075, 0.06, 0.08), (0, 0, 0), 0.4)], "#6a5238", "stain", ragged=0.45)
    for m in _mats(r"^OfficeRug"):
        spots(m, [((5.28, 8.72, 0.0), (0.085, 0.07, 0.08), (0, 0, 0.2), 0.5), ((6.25, 9.22, 0.0), (0.04, 0.04, 0.08), (0, 0, 0), 0.4)],
              "#4a3826", "stain", ragged=0.45)                                             # coffee
    for m in _mats(r"^BathMat"):
        spots(m, [((8.84, 9.36, 0.0), (0.05, 0.11, 0.08), (0, 0, 0.15), 0.4), ((9.05, 9.41, 0.0), (0.05, 0.11, 0.08), (0, 0, -0.1), 0.36)],
              "#566a60", "stain", ragged=0.3)                                             # damp footprints

    # --- floors: dust where the vacuum does not reach, grit by the door, kitchen spills
    spots(M["floor_hall"], [((1.1, hy0 + 0.14, 0.0), (0.5, 0.14, 0.06), (0, 0, 0), 0.5), ((0.27, hy0 + 0.1, 0.0), (0.16, 0.13, 0.06), (0, 0, 0), 0.5),
                            ((1.3, hy1 - 0.13, 0.0), (0.5, 0.13, 0.06), (0, 0, 0), 0.45), ((5.35, hy0 + 0.13, 0.0), (0.6, 0.13, 0.06), (0, 0, 0), 0.45),
                            ((3.0, 0.3, 0.0), (1.3, 0.12, 0.06), (0, 0, 0), 0.5), ((3.86, 8.25, 0.0), (0.2, 0.42, 0.06), (0, 0, 0), 0.5),
                            ((3.8, 9.72, 0.0), (0.3, 0.55, 0.06), (0, 0, 0), 0.4), ((5.8, 10.3, 0.0), (0.7, 0.14, 0.06), (0, 0, 0), 0.5),
                            ((4.42, 10.28, 0.0), (0.18, 0.16, 0.06), (0, 0, 0), 0.5), ((0.3, 10.3, 0.0), (0.16, 0.16, 0.06), (0, 0, 0), 0.5)],
          DUSTC, "dust", rough=0.95, ragged=0.45, patchy=0.55, fine=38.0)
    spots(M["floor_hall"], [((1.05, 5.6, 0.0), (0.32, 0.45, 0.06), (0, 0, 0), 0.2)], "#5e5346", "grit",
          rough=0.9, ragged=0.5, patchy=0.7, fine=160.0)
    spots(M["floor_kitchen"], [((9.2, 2.25, 0.0), (0.3, 0.42, 0.06), (0, 0, 0), 0.2), ((6.55, 4.1, 0.0), (0.2, 0.22, 0.06), (0, 0, 0), 0.22),
                               ((8.1, 0.95, 0.0), (0.4, 0.22, 0.06), (0, 0, 0), 0.14), ((7.2, 3.3, 0.0), (0.045, 0.06, 0.06), (0, 0, 0.5), 0.5),
                               ((7.05, 3.12, 0.0), (0.028, 0.03, 0.06), (0, 0, 0), 0.5)],
          "#6b5a44", "spill", rough=0.5, ragged=0.45, patchy=0.4, fine=50.0)

    # parquet: toy, chair-leg and grit scratches where the floor gets used
    fs = []
    for (ax0, ay0, ax1, ay1), n in (((4.4, 2.2, 5.6, 4.2), 10), ((1.6, 2.9, 2.6, 3.6), 5), ((2.2, 7.2, 3.4, 8.0), 5),
                                    ((4.6, 8.0, 5.2, 9.8), 5), ((0.9, 4.9, 2.2, 6.3), 7)):
        for _ in range(n):
            fs.append(((rnd.uniform(ax0, ax1), rnd.uniform(ay0, ay1), 0.0), (rnd.uniform(0.05, 0.2), rnd.uniform(0.0022, 0.0045), 0.05),
                       (0.0, 0.0, rnd.uniform(0, 3.14)), rnd.uniform(0.4, 0.65)))
    spots(M["floor_hall"], fs, "#dccaa6", "scratches", rough=0.95, ragged=0.2)
    # fronts and doors that hands and feet touch every day
    grime(C._MATS.get("KitchenFront"), 0.16, rough_to=0.22, kick=0.25)
    grime(C._MATS.get("WardrobeWhite"), 0.12, rough_to=0.22)
    grime(M["door"], 0.12, kick=0.3)
    spots(M["door_entrance"], levers, "#27352f", "hands", rough=0.2, ragged=0.35, patchy=0.3, fine=60.0)
    grime(M["door_entrance"], 0.14, color="#8f9a93", kick=0.4)
    grime(C._MATS.get("ApplianceWhite"), 0.1)
    grime(C._MATS.get("FridgeSteel"), 0.2, color=None, rough_to=0.42, scale=6.0)      # fingerprints on steel
    grime(C._MATS.get("Plinth"), 0.3, color="#6b6558", kick=0.6)

    # --- kitchen: grease spatter behind the hob, a coffee ring by the machine, marks on the table
    spots(C._MATS.get("KitchenBacksplash"), [((kx1, 2.25, 1.1), (0.06, 0.34, 0.17), (0, 0, 0), 0.4)], "#b8974a", "grease",
          rough=0.22, ragged=0.3, patchy=1.0, fine=200.0, cover=(0.64, 0.7))
    spots(C._MATS.get("WorktopQuartz"), [((7.17, 0.55, 0.9), (0.043, 0.043, 0.03), (0, 0, 0), 0.6), ((9.55, 2.72, 0.9), (0.09, 0.14, 0.03), (0, 0, 0), 0.3),
                                         ((8.5, 0.34, 0.9), (0.16, 0.06, 0.03), (0, 0, 0), 0.25)],
          "#6e5134", "rings", rough=0.5, ragged=0.15, ring=True)
    for m in _mats(r"^Table Kitchen"):
        spots(m, [((7.3, 3.02, 0.745), (0.042, 0.042, 0.03), (0, 0, 0), 0.5), ((7.66, 2.42, 0.745), (0.07, 0.04, 0.03), (0, 0, 0.6), 0.35)],
              "#7b5e42", "rings", rough=0.55, ragged=0.15, ring=True)

    for m in _mats(r"^Table Kitchen"):
        spots(m, blotch(rnd, (7.36, 3.1, 0.745), 0.04, 0.5, 2) + [((7.62, 2.5, 0.745), (0.09, 0.022, 0.03), (0, 0, 0.7), 0.35)],
              "#c08a40", "spill", rough=0.35, ragged=0.4)                                # dried juice, a wiped smear
    # --- bathroom: toothpaste and water spots on the mirror, mould in the joint along the tub
    bx0, by0, bx1, by1 = S.inner("bath")
    spots(C._MATS.get("Mirror"), [((bx1 - 0.13, 7.8, 1.27), (0.1, 0.3, 0.11), (0, 0, 0), 0.75)], "#eef0ee", "spatter",
          rough=0.6, metal=0.0, ragged=0.3, patchy=1.0, fine=210.0, cover=(0.685, 0.73))      # a scatter of toothpaste and water specks
    joint = [((rnd.uniform(8.25, 9.75), by1, rnd.uniform(0.575, 0.63)), (rnd.uniform(0.04, 0.11), 0.03, rnd.uniform(0.012, 0.024)),
              (0, 0, 0), rnd.uniform(0.35, 0.55)) for _ in range(7)]
    joint += [((bx1, rnd.uniform(9.8, 10.4), rnd.uniform(0.575, 0.63)), (0.03, rnd.uniform(0.04, 0.1), 0.02), (0, 0, 0), 0.45) for _ in range(3)]
    # (mould patches along the tub joint were removed: at close range they read as decals)
    scale = [((bx0, rnd.uniform(8.8, 10.3), rnd.uniform(0.7, 1.3)), (0.03, rnd.uniform(0.006, 0.014), rnd.uniform(0.12, 0.3)),
              (0, 0, 0), rnd.uniform(0.3, 0.5)) for _ in range(9)]
    scale += [((bx0, 9.5, 0.95), (0.05, 0.6, 0.4), (0, 0, 0), 0.3)]
    spots(M["wall_bath"], scale, "#cfccc0", "scale", rough=0.62, ragged=0.35, patchy=0.5, fine=40.0)    # limescale where the shower hits
    film(C._MATS.get("ShowerGlass"), 0.16, 26.0)
    film(M["glass"], 0.05, 6.0)

    # --- dust: thick on high shelves and the tops of things nobody wipes, lighter lower down
    for m in _mats(r"^(steel_frame_shelves|wooden_display_shelves|modern_wooden_cabinet|television|ClassicConsole|drawer_cabinet|"
                   r"vintage_wooden_drawer|painted_wooden_cabinet|side_table|wall_clock|ClassicNightstand|painted_wooden_nightstand|"
                   r"hanging_picture_frame|boombox|book_encyclopedia|decorative_book)"):
        dust(m, 0.3, high=True)
    for m in _mats(r"^Table(\.\d+)?$"):
        dust(m, 0.3)
    dust(M["trim"], 0.3)
    dust(M["sill"], 0.22)
    dust(M["radiator"], 0.35)
    dust(M["black_metal"], 0.4, high=True)
    dust(C._MATS.get("MirrorCab"), 0.3)
    return {"walls": sum(len(v[1]) for v in scratch.values()) + sum(len(v[1]) for v in smudge.values()), "chips": len(chips)}

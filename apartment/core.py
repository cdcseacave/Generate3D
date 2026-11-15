"""Core helpers: scene housekeeping, mesh builders, materials, Poly Haven assets.

Conventions: metres, X east, Y north, Z up. Procedural meshes are built at
real size in local space (object scale stays 1) so box-projected UVs are in
metres and tiling textures get a physically meaningful scale.
"""
import glob
import json
import math
import os
import random
import re

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "out")
GEN = os.path.join(ASSETS, "generated")

rng = random.Random(7)
_state = {"col": None}


# ----------------------------------------------------------------- scene ---
def reset_scene():
    """Remove every datablock without reloading the file (keeps the MCP bridge alive)."""
    for coll in (bpy.data.objects, bpy.data.collections, bpy.data.meshes, bpy.data.curves,
                 bpy.data.materials, bpy.data.images, bpy.data.lights, bpy.data.cameras,
                 bpy.data.node_groups, bpy.data.worlds, bpy.data.textures, bpy.data.libraries):
        ids = [i for i in coll]
        if ids:
            bpy.data.batch_remove(ids)
    _MATS.clear()
    _PROTO.clear()
    _REC.clear()
    _state["col"] = None


def collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    _state["col"] = col
    return col


def _link(obj, col=None):
    (col or _state["col"] or bpy.context.scene.collection).objects.link(obj)
    if _REC:
        _REC[-1].append(obj)
    return obj


_REC = []


def begin():
    """Start recording created objects; build a fixture around the origin
    (front towards -Y), then call end() to group and place it."""
    _REC.append([])


def end(name, loc=(0, 0, 0), rot=0.0):
    objs = _REC.pop()
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.15
    _link(e)
    for o in objs:
        if o.parent is None:
            o.parent = e
    e.location = loc
    e.rotation_euler = (0, 0, rot)
    return e


# ------------------------------------------------------------- materials ---
_MATS = {}
_TEXINFO = {}


def _new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:  # noqa: BLE001  (always-on in newer versions)
        pass
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    _MATS[name] = m
    return m, nt, bsdf, out


def _set(bsdf, **kw):
    names = {"rough": "Roughness", "metal": "Metallic", "spec": "Specular IOR Level", "ior": "IOR",
             "trans": "Transmission Weight", "coat": "Coat Weight", "coat_rough": "Coat Roughness",
             "sheen": "Sheen Weight", "sss": "Subsurface Weight", "alpha": "Alpha",
             "emit": "Emission Strength"}
    for k, v in kw.items():
        if v is None or k not in names:
            continue
        if names[k] in bsdf.inputs:
            bsdf.inputs[names[k]].default_value = v


def rgb(c):
    """Accept '#rrggbb' (sRGB) or a linear tuple; return linear RGBA."""
    if isinstance(c, str):
        c = c.lstrip("#")
        v = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return (*v, 1.0)
    return (*c[:3], 1.0)


def wear_nodes(nt, base, amount, scale=1.0):
    """Roughness = base + amount * (smudgy patches + fine directional scratches).
    Returns the output socket. Keeps glossy surfaces from looking factory-new."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 5.0 * scale
    n1.inputs["Detail"].default_value = 4.0
    n1.inputs["Roughness"].default_value = 0.65
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    r1 = nt.nodes.new("ShaderNodeMapRange")
    r1.inputs["From Min"].default_value = 0.42
    r1.inputs["From Max"].default_value = 0.72
    nt.links.new(n1.outputs["Fac"], r1.inputs["Value"])
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0 * scale, 140.0 * scale, 2.0 * scale)
    mp.inputs["Rotation"].default_value = (0.3, 0.2, 0.6)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 6.0
    n2.inputs["Detail"].default_value = 2.0
    nt.links.new(mp.outputs[0], n2.inputs["Vector"])
    r2 = nt.nodes.new("ShaderNodeMapRange")
    r2.inputs["From Min"].default_value = 0.6
    r2.inputs["From Max"].default_value = 0.7
    nt.links.new(n2.outputs["Fac"], r2.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = "MULTIPLY_ADD"
    mix.inputs[1].default_value = 0.45
    nt.links.new(r2.outputs[0], mix.inputs[0])
    nt.links.new(r1.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeMath")
    out.operation = "MULTIPLY_ADD"
    out.use_clamp = True
    out.inputs[1].default_value = amount
    out.inputs[2].default_value = base
    nt.links.new(mix.outputs[0], out.inputs[0])
    return out.outputs[0]


def mat(name, color="#808080", rough=0.5, metal=0.0, noise=0.0, bump=0.0, bump_scale=200.0, wear=0.0, **kw):
    """Plain principled material. `noise` adds subtle colour/roughness mottling,
    `bump` a fine procedural grain so large flat surfaces do not look CG-clean."""
    if name in _MATS:
        return _MATS[name]
    m, nt, bsdf, _ = _new_mat(name)
    col = rgb(color)
    bsdf.inputs["Base Color"].default_value = col
    _set(bsdf, rough=rough, metal=metal, **kw)
    if "emit_color" in kw:
        bsdf.inputs["Emission Color"].default_value = rgb(kw["emit_color"])
    if noise or bump:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 3.0
        nz.inputs["Detail"].default_value = 6.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        if noise:
            ramp = nt.nodes.new("ShaderNodeMapRange")
            ramp.inputs["To Min"].default_value = 1.0 - noise
            ramp.inputs["To Max"].default_value = 1.0 + noise * 0.3
            nt.links.new(nz.outputs["Fac"], ramp.inputs["Value"])
            mul = nt.nodes.new("ShaderNodeMix")
            mul.data_type = "RGBA"
            mul.blend_type = "MULTIPLY"
            mul.inputs[0].default_value = 1.0
            mul.inputs[6].default_value = col
            nt.links.new(ramp.outputs[0], mul.inputs[7])
            nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
            rr = nt.nodes.new("ShaderNodeMapRange")
            rr.inputs["To Min"].default_value = max(0.0, rough - noise)
            rr.inputs["To Max"].default_value = min(1.0, rough + noise)
            nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
            if not wear:
                nt.links.new(rr.outputs[0], bsdf.inputs["Roughness"])
        if bump:
            n2 = nt.nodes.new("ShaderNodeTexNoise")
            n2.inputs["Scale"].default_value = bump_scale
            n2.inputs["Detail"].default_value = 4.0
            nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
            bp = nt.nodes.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = bump
            bp.inputs["Distance"].default_value = 0.002
            nt.links.new(n2.outputs["Fac"], bp.inputs["Height"])
            nt.links.new(bp.outputs[0], bsdf.inputs["Normal"])
    if wear:
        nt.links.new(wear_nodes(nt, rough, wear), bsdf.inputs["Roughness"])
    return m


def _texinfo(tex):
    if not _TEXINFO:
        p = os.path.join(ASSETS, "_catalog", "textures.json")
        if os.path.exists(p):
            _TEXINFO.update(json.load(open(p)))
    return _TEXINFO.get(tex, {})


def _img(path, noncolor=False):
    img = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    return img


def pbr(name, tex, size=None, tint=None, tint_fac=1.0, rot=0.0, rough=1.0, normal=1.0,
        value=1.0, sat=1.0, rough_add=0.0, flat=None, **kw):
    """Tiling Poly Haven material. `size` = metres per repeat (defaults to the
    scanned real-world size). `tint` multiplies the albedo; `rough` scales roughness."""
    if name in _MATS:
        return _MATS[name]
    d = os.path.join(ASSETS, "textures", tex)
    m, nt, bsdf, _ = _new_mat(name)
    if size is None:
        dims = _texinfo(tex).get("dimensions") or [2000, 2000]
        size = (dims[0] / 1000.0, dims[1] / 1000.0)
    if not isinstance(size, (tuple, list)):
        size = (size, size)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / size[0], 1.0 / size[1], 1.0)
    mp.inputs["Rotation"].default_value = (0, 0, rot)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])

    def tex_node(suffix, noncolor):
        p = os.path.join(d, "{}_{}.jpg".format(tex, suffix))
        if not os.path.exists(p):
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = _img(p, noncolor)
        nt.links.new(mp.outputs[0], n.inputs["Vector"])
        return n

    dn = None if flat is not None else tex_node("Diffuse", False)
    if flat is not None:
        bsdf.inputs["Base Color"].default_value = rgb(flat)
    if dn:
        src = dn.outputs["Color"]
        if value != 1.0 or sat != 1.0:
            hsv = nt.nodes.new("ShaderNodeHueSaturation")
            hsv.inputs["Saturation"].default_value = sat
            hsv.inputs["Value"].default_value = value
            nt.links.new(src, hsv.inputs["Color"])
            src = hsv.outputs[0]
        if tint is not None:
            mul = nt.nodes.new("ShaderNodeMix")
            mul.data_type = "RGBA"
            mul.blend_type = "MULTIPLY"
            mul.inputs[0].default_value = tint_fac
            mul.inputs[7].default_value = rgb(tint)
            nt.links.new(src, mul.inputs[6])
            src = mul.outputs[2]
        nt.links.new(src, bsdf.inputs["Base Color"])
    rn = tex_node("Rough", True)
    if rn:
        mr = nt.nodes.new("ShaderNodeMath")
        mr.operation = "MULTIPLY_ADD"
        mr.use_clamp = True
        mr.inputs[1].default_value = rough
        mr.inputs[2].default_value = rough_add
        nt.links.new(rn.outputs["Color"], mr.inputs[0])
        nt.links.new(mr.outputs[0], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.5 * rough
    nn = tex_node("nor_gl", True)
    if nn:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal
        nt.links.new(nn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    _set(bsdf, **kw)
    return m


def paint(name, color, rough=0.6, strength=0.35, scuff=0.09):
    """Wall paint: flat colour with faint mottling plus the plaster normal map."""
    if name in _MATS:
        return _MATS[name]
    # Roller-painted plaster: a fine, even stipple in object space. (A tangent-space
    # plaster map made adjoining walls look embossed on one side and smooth on the other.)
    m = mat(name, color, rough=rough, noise=0.03)          # no fine bump: in dim rooms the denoiser smeared it into swirls
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    # Real plaster is never flat: a millimetre or two of slow undulation shows up as
    # uneven shading in raking light. Low frequency only, so the denoiser keeps it.
    wtc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexNoise")
    wave.inputs["Scale"].default_value = 1.6
    wave.inputs["Detail"].default_value = 1.5
    wave.inputs["Roughness"].default_value = 0.45
    nt.links.new(wtc.outputs["Object"], wave.inputs["Vector"])
    wb = nt.nodes.new("ShaderNodeBump")
    wb.inputs["Strength"].default_value = 1.0
    wb.inputs["Distance"].default_value = 0.012
    nt.links.new(wave.outputs["Fac"], wb.inputs["Height"])
    nt.links.new(wb.outputs[0], bsdf.inputs["Normal"])
    # Roller-painted plaster photographed from a real wall, box-projected in world space and used
    # as a height (bump), a faint tone variation and a sheen variation. A height map has no tangent
    # direction, so adjoining walls match (the earlier normal-map attempt looked embossed).
    ptex = os.path.join(ASSETS, "textures", "painted_plaster_wall", "painted_plaster_wall_Diffuse.jpg")
    if os.path.exists(ptex):
        pm = nt.nodes.new("ShaderNodeMapping")
        pm.inputs["Scale"].default_value = (0.8, 0.8, 0.8)
        nt.links.new(wtc.outputs["Object"], pm.inputs["Vector"])
        pt = nt.nodes.new("ShaderNodeTexImage")
        pt.image = _img(ptex, True)
        pt.projection = "BOX"
        pt.projection_blend = 0.25
        nt.links.new(pm.outputs[0], pt.inputs["Vector"])
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(pt.outputs["Color"], bw.inputs[0])
        fb = nt.nodes.new("ShaderNodeBump")
        fb.inputs["Strength"].default_value = 0.45
        fb.inputs["Distance"].default_value = 0.0012
        nt.links.new(bw.outputs[0], fb.inputs["Height"])
        nt.links.new(wb.outputs[0], fb.inputs["Normal"])
        nt.links.new(fb.outputs[0], bsdf.inputs["Normal"])
        tone = nt.nodes.new("ShaderNodeMapRange")              # tone 0.93 .. 1.04 around the paint colour
        tone.inputs["From Min"].default_value = 0.25
        tone.inputs["From Max"].default_value = 0.85
        tone.inputs["To Min"].default_value = 0.93
        tone.inputs["To Max"].default_value = 1.04
        nt.links.new(bw.outputs[0], tone.inputs["Value"])
        src0 = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].links else None
        tm = nt.nodes.new("ShaderNodeMix")
        tm.data_type = "RGBA"
        tm.blend_type = "MULTIPLY"
        tm.inputs[0].default_value = 1.0
        if src0 is not None:
            nt.links.new(src0, tm.inputs[6])
        else:
            tm.inputs[6].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(tone.outputs[0], tm.inputs[7])
        nt.links.new(tm.outputs[2], bsdf.inputs["Base Color"])
    # Lived-in walls: grime and scuffs that build up near the floor, plus fainter
    # hand-height smudges, instead of a factory-fresh surface.
    src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].links else None
    if src is not None:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        low = nt.nodes.new("ShaderNodeMapRange")        # 1 at the skirting, 0 above 0.45 m
        low.inputs["From Min"].default_value = 0.08
        low.inputs["From Max"].default_value = 0.45
        low.inputs["To Min"].default_value = 1.0
        low.inputs["To Max"].default_value = 0.0
        nt.links.new(sep.outputs["Z"], low.inputs["Value"])
        band = nt.nodes.new("ShaderNodeMapRange")       # faint band around 0.8-1.3 m (hands, bags, chair backs)
        band.inputs["From Min"].default_value = 0.0
        band.inputs["From Max"].default_value = 0.35
        band.inputs["To Min"].default_value = 0.35
        band.inputs["To Max"].default_value = 0.0
        dz = nt.nodes.new("ShaderNodeMath")
        dz.operation = "SUBTRACT"
        dz.inputs[1].default_value = 1.05
        nt.links.new(sep.outputs["Z"], dz.inputs[0])
        az = nt.nodes.new("ShaderNodeMath")
        az.operation = "ABSOLUTE"
        nt.links.new(dz.outputs[0], az.inputs[0])
        nt.links.new(az.outputs[0], band.inputs["Value"])
        zone = nt.nodes.new("ShaderNodeMath")
        zone.operation = "MULTIPLY"                      # hand-height band disabled: it read as cloudy blotches
        zone.inputs[1].default_value = 1.0
        nt.links.new(low.outputs[0], zone.inputs[0])
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (2.0, 2.0, 14.0)   # short horizontal scuff marks
        nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
        sn = nt.nodes.new("ShaderNodeTexNoise")
        sn.inputs["Scale"].default_value = 9.0
        sn.inputs["Detail"].default_value = 6.0
        sn.inputs["Roughness"].default_value = 0.7
        nt.links.new(mp.outputs[0], sn.inputs["Vector"])
        patch_ = nt.nodes.new("ShaderNodeMapRange")
        patch_.inputs["From Min"].default_value = 0.5
        patch_.inputs["From Max"].default_value = 0.72
        nt.links.new(sn.outputs["Fac"], patch_.inputs["Value"])
        fac = nt.nodes.new("ShaderNodeMath")
        fac.operation = "MULTIPLY"
        nt.links.new(zone.outputs[0], fac.inputs[0])
        nt.links.new(patch_.outputs[0], fac.inputs[1])
        amt = nt.nodes.new("ShaderNodeMath")
        amt.operation = "MULTIPLY"
        amt.inputs[1].default_value = scuff
        nt.links.new(fac.outputs[0], amt.inputs[0])
        mixd = nt.nodes.new("ShaderNodeMix")
        mixd.data_type = "RGBA"
        mixd.inputs[7].default_value = rgb("#7a6c5c")
        nt.links.new(amt.outputs[0], mixd.inputs[0])
        nt.links.new(src, mixd.inputs[6])
        nt.links.new(mixd.outputs[2], bsdf.inputs["Base Color"])
    return m


def wall_tile(name, tw=0.6, th=0.3, grout=0.0028, color="#ecebe5", color2="#e3e1da", grout_color="#aaa59a", rough=0.14, tilt=0.012):
    """Large-format glazed wall tile laid in a half bond, projected on vertical faces in
    world space. Each tile takes one of two near-identical glaze tones and sits a hair
    proud of the recessed grout, so reflections break at the joints like fired tile."""
    if name in _MATS:
        return _MATS[name]
    m, nt, bsdf, _ = _new_mat(name)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    pos = nt.nodes.new("ShaderNodeSeparateXYZ")
    nor = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], pos.inputs[0])
    nt.links.new(geo.outputs["True Normal"], nor.inputs[0])

    def absn(sock):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = "ABSOLUTE"
        nt.links.new(sock, n.inputs[0])
        return n.outputs[0]

    gt = nt.nodes.new("ShaderNodeMath")          # 1 where the face looks along X (use Y as the run), else 0
    gt.operation = "GREATER_THAN"
    nt.links.new(absn(nor.outputs["X"]), gt.inputs[0])
    nt.links.new(absn(nor.outputs["Y"]), gt.inputs[1])
    run = nt.nodes.new("ShaderNodeMix")
    run.data_type = "FLOAT"
    nt.links.new(gt.outputs[0], run.inputs[0])
    nt.links.new(pos.outputs["X"], run.inputs[2])
    nt.links.new(pos.outputs["Y"], run.inputs[3])
    vec = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(run.outputs[0], vec.inputs["X"])
    nt.links.new(pos.outputs["Z"], vec.inputs["Y"])
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.5
    br.inputs["Color1"].default_value = rgb(color)
    br.inputs["Color2"].default_value = rgb(color2)
    br.inputs["Mortar"].default_value = rgb(grout_color)
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = grout
    br.inputs["Mortar Smooth"].default_value = 0.25
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Brick Width"].default_value = tw
    br.inputs["Row Height"].default_value = th
    nt.links.new(vec.outputs[0], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], bsdf.inputs["Base Color"])
    # grout is never one colour: it yellows and greys unevenly, worst low down where it gets wet
    gn = nt.nodes.new("ShaderNodeTexNoise")
    gn.inputs["Scale"].default_value = 2.4
    gn.inputs["Detail"].default_value = 3.0
    nt.links.new(geo.outputs["Position"], gn.inputs["Vector"])
    gr = nt.nodes.new("ShaderNodeMapRange")
    gr.interpolation_type = "SMOOTHSTEP"
    gr.inputs["From Min"].default_value = 0.42
    gr.inputs["From Max"].default_value = 0.68
    nt.links.new(gn.outputs["Fac"], gr.inputs["Value"])
    lowz = nt.nodes.new("ShaderNodeMapRange")
    lowz.inputs["From Min"].default_value = 1.4
    lowz.inputs["From Max"].default_value = 0.1
    lowz.inputs["To Min"].default_value = 0.35
    lowz.inputs["To Max"].default_value = 1.0
    nt.links.new(pos.outputs["Z"], lowz.inputs["Value"])
    gf = nt.nodes.new("ShaderNodeMath")
    gf.operation = "MULTIPLY"
    nt.links.new(gr.outputs[0], gf.inputs[0])
    nt.links.new(lowz.outputs[0], gf.inputs[1])
    gm = nt.nodes.new("ShaderNodeMix")
    gm.data_type = "RGBA"
    gm.inputs[6].default_value = rgb(grout_color)
    gm.inputs[7].default_value = rgb("#6a6254")
    nt.links.new(gf.outputs[0], gm.inputs[0])
    nt.links.new(gm.outputs[2], br.inputs["Mortar"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough
    rr.inputs["To Max"].default_value = 0.85
    nt.links.new(br.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs[0], bsdf.inputs["Roughness"])
    wob = nt.nodes.new("ShaderNodeTexNoise")       # glaze is never optically flat
    wob.inputs["Scale"].default_value = 3.5
    wob.inputs["Detail"].default_value = 1.0
    nt.links.new(geo.outputs["Position"], wob.inputs["Vector"])
    hgt = nt.nodes.new("ShaderNodeMath")
    hgt.operation = "MULTIPLY_ADD"                 # height = -grout recess + slow glaze waviness
    hgt.inputs[1].default_value = -1.0
    nt.links.new(br.outputs["Fac"], hgt.inputs[0])
    nt.links.new(wob.outputs["Fac"], hgt.inputs[2])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    bp.inputs["Distance"].default_value = 0.0012
    nt.links.new(hgt.outputs[0], bp.inputs["Height"])
    # lippage: every tile is bedded at its own slight tilt, so reflections break from tile to tile
    rb = nt.nodes.new("ShaderNodeTexBrick")
    rb.offset = 0.5
    rb.inputs["Color1"].default_value = (0, 0, 0, 1)
    rb.inputs["Color2"].default_value = (1, 1, 1, 1)
    rb.inputs["Mortar"].default_value = (0.5, 0.5, 0.5, 1)
    rb.inputs["Scale"].default_value = 1.0
    rb.inputs["Mortar Size"].default_value = grout
    rb.inputs["Bias"].default_value = 0.0
    rb.inputs["Brick Width"].default_value = tw
    rb.inputs["Row Height"].default_value = th
    nt.links.new(vec.outputs[0], rb.inputs["Vector"])

    def mth(op, a_, b_=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a_, b_)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    r1 = rb.outputs["Color"]
    t1 = mth("MULTIPLY", mth("SUBTRACT", r1, 0.5), 2.0 * tilt)
    t2 = mth("MULTIPLY", mth("SUBTRACT", mth("FRACT", mth("MULTIPLY", r1, 13.7)), 0.5), 2.0 * tilt)
    cr = nt.nodes.new("ShaderNodeVectorMath")
    cr.operation = "CROSS_PRODUCT"
    cr.inputs[0].default_value = (0, 0, 1)
    nt.links.new(geo.outputs["True Normal"], cr.inputs[1])
    su = nt.nodes.new("ShaderNodeVectorMath")
    su.operation = "SCALE"
    nt.links.new(cr.outputs[0], su.inputs[0])
    nt.links.new(t1, su.inputs["Scale"])
    cz = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(t2, cz.inputs["Z"])
    ad = nt.nodes.new("ShaderNodeVectorMath")
    nt.links.new(geo.outputs["True Normal"], ad.inputs[0])
    nt.links.new(su.outputs[0], ad.inputs[1])
    ad2 = nt.nodes.new("ShaderNodeVectorMath")
    nt.links.new(ad.outputs[0], ad2.inputs[0])
    nt.links.new(cz.outputs[0], ad2.inputs[1])
    nn = nt.nodes.new("ShaderNodeVectorMath")
    nn.operation = "NORMALIZE"
    nt.links.new(ad2.outputs[0], nn.inputs[0])
    nt.links.new(nn.outputs[0], bp.inputs["Normal"])
    nt.links.new(bp.outputs[0], bsdf.inputs["Normal"])
    try:
        bsdf.inputs["Coat Weight"].default_value = 0.3
        bsdf.inputs["Coat Roughness"].default_value = 0.06
    except Exception:  # noqa: BLE001
        pass
    return m


def glass(name="glass", frosted=False):
    """Architectural glass: reflective to the camera, transparent to shadow and
    diffuse rays so daylight enters cleanly instead of as noisy caustics."""
    if name in _MATS:
        return _MATS[name]
    m, nt, bsdf, out = _new_mat(name)
    nt.nodes.remove(bsdf)
    if frosted:
        tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
        tr.inputs["Color"].default_value = (0.9, 0.93, 0.95, 1)
        df = nt.nodes.new("ShaderNodeBsdfGlossy")
        df.inputs["Roughness"].default_value = 0.35
        clear = nt.nodes.new("ShaderNodeBsdfTransparent")
        clear.inputs["Color"].default_value = (0.9, 0.92, 0.93, 1)
        pre = nt.nodes.new("ShaderNodeMixShader")
        pre.inputs[0].default_value = 0.5
        nt.links.new(tr.outputs[0], pre.inputs[1])
        nt.links.new(clear.outputs[0], pre.inputs[2])
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = 0.12
        nt.links.new(pre.outputs[0], mix.inputs[1])
        nt.links.new(df.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0])
        return m
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (0.96, 0.98, 0.97, 1)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    nt.links.new(wear_nodes(nt, 0.0, 0.02, 0.6), gl.inputs["Roughness"])
    fr = nt.nodes.new("ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.5
    lp = nt.nodes.new("ShaderNodeLightPath")
    cam = nt.nodes.new("ShaderNodeMath")
    cam.operation = "MULTIPLY"
    nt.links.new(fr.outputs[0], cam.inputs[0])
    nt.links.new(lp.outputs["Is Camera Ray"], cam.inputs[1])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(cam.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def emissive(name, color, strength):
    if name in _MATS:
        return _MATS[name]
    m, nt, bsdf, out = _new_mat(name)
    nt.nodes.remove(bsdf)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = rgb(color)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def image_mat(name, path, rough=0.6, emit=0.0, bump=0.0, bump_scale=300.0, wear=0.0, weave=None, **kw):
    """Material showing a generated picture (drawings, screens, posters) via UVs 0..1."""
    if name in _MATS:
        return _MATS[name]
    m, nt, bsdf, _ = _new_mat(name)
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = _img(path)
    n.extension = "EXTEND"
    nt.links.new(n.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, rough=rough, **kw)
    if emit:
        nt.links.new(n.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit
    if wear:
        nt.links.new(wear_nodes(nt, rough, wear), bsdf.inputs["Roughness"])
    if weave:        # (fabric texture id, repeats across the image in u, in v, strength): real pile/weave relief
        tex, ru, rv, strength = weave
        p = os.path.join(ASSETS, "textures", tex, tex + "_nor_gl.jpg")
        if os.path.exists(p):
            tcw = nt.nodes.new("ShaderNodeTexCoord")
            mpw = nt.nodes.new("ShaderNodeMapping")
            mpw.inputs["Scale"].default_value = (ru, rv, 1)
            nt.links.new(tcw.outputs["UV"], mpw.inputs["Vector"])
            nw = nt.nodes.new("ShaderNodeTexImage")
            nw.image = _img(p, True)
            nt.links.new(mpw.outputs[0], nw.inputs["Vector"])
            nmw = nt.nodes.new("ShaderNodeNormalMap")
            nmw.inputs["Strength"].default_value = strength
            nt.links.new(nw.outputs["Color"], nmw.inputs["Color"])
            rel = nt.nodes.new("ShaderNodeBump")             # the woven pattern itself stands proud of / sinks into the pile
            rel.inputs["Strength"].default_value = 0.6
            rel.inputs["Distance"].default_value = 0.004
            nt.links.new(n.outputs["Color"], rel.inputs["Height"])
            nt.links.new(nmw.outputs[0], rel.inputs["Normal"])
            nt.links.new(rel.outputs[0], bsdf.inputs["Normal"])
            bump = 0.0
    if bump:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = bump_scale
        nz.inputs["Detail"].default_value = 5.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.004
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs[0], bsdf.inputs["Normal"])
    return m


# ---------------------------------------------------------------- meshes ---
def uv_project(me, swap=False):
    """Box-project UVs in local metres."""
    uv = me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name="UVMap")
    verts = me.vertices
    loops = me.loops
    data = uv.data
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            v = verts[loops[li].vertex_index].co
            if ax == 0:
                u, w = v.y, v.z
            elif ax == 1:
                u, w = v.x, v.z
            else:
                u, w = v.x, v.y
            data[li].uv = (w, u) if swap else (u, w)


def _finish(name, bm, loc, rot, material, smooth=False, bevel=0.0, swap=False, col=None, segs=2):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    uv_project(me, swap)
    if smooth or bevel:
        me.shade_smooth()
    obj = bpy.data.objects.new(name, me)
    _link(obj, col)
    obj.location = loc
    if isinstance(rot, (int, float)):
        rot = (0.0, 0.0, rot)
    obj.rotation_euler = rot
    if material is not None:
        me.materials.append(material)
    if bevel:
        add_bevel(obj, bevel, segs)
    elif smooth:
        wn = obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        me.set_sharp_from_angle(angle=math.radians(50))
    return obj


def add_bevel(obj, width, segs=2):
    b = obj.modifiers.new("Bevel", "BEVEL")
    b.width = width
    b.segments = segs
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(40)
    b.harden_normals = True
    return b


def subsurf(obj, levels=2):
    s = obj.modifiers.new("Subsurf", "SUBSURF")
    s.levels = levels
    s.render_levels = levels
    obj.data.shade_smooth()
    return s


def box(name, size, loc, material=None, rot=0.0, bevel=0.0, anchor=(0, 0, -1), swap=False, col=None):
    """Box of `size`; `anchor` picks which point sits at `loc` (default bottom centre)."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    off = Vector((-anchor[0] * sx / 2, -anchor[1] * sy / 2, -anchor[2] * sz / 2))
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz)) + off
    return _finish(name, bm, loc, rot, material, bevel=bevel, swap=swap, col=col)


def box2(name, p0, p1, material=None, bevel=0.0, swap=False, col=None):
    """Axis-aligned box from two corners (absolute coordinates)."""
    lo = [min(a, b) for a, b in zip(p0, p1)]
    hi = [max(a, b) for a, b in zip(p0, p1)]
    size = [h - l for l, h in zip(lo, hi)]
    loc = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
    return box(name, size, loc, material, bevel=bevel, swap=swap, col=col)


def cyl(name, r, h, loc, material=None, rot=(0, 0, 0), segs=32, bevel=0.0, r2=None, col=None):
    """Cylinder/cone standing on `loc` (base centre) before rotation."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r2 is None else r2,
                          depth=h)
    for v in bm.verts:
        v.co.z += h / 2
    return _finish(name, bm, loc, rot, material, smooth=True, bevel=bevel, col=col)


def sphere(name, r, loc, material=None, scale=(1, 1, 1), segs=24, col=None, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(8, segs // 2), radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    me_obj = _finish(name, bm, loc, rot, material, col=col)
    me_obj.data.shade_smooth()
    return me_obj


def lathe(name, profile, loc, material=None, segs=40, rot=(0, 0, 0), col=None, sub=1, scale=(1, 1, 1)):
    """Surface of revolution around Z from (radius, z) points. Points with r == 0 are poles."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs) * scale[0],
                                        r * math.sin(2 * math.pi * i / segs) * scale[1], z))
                          for i in range(segs)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        for i in range(segs):
            j = (i + 1) % segs
            if len(a) == 1:
                bm.faces.new((a[0], b[j], b[i]))
            elif len(b) == 1:
                bm.faces.new((a[i], a[j], b[0]))
            else:
                bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = _finish(name, bm, loc, rot, material, col=col)
    obj.data.shade_smooth()
    if sub:
        subsurf(obj, sub)
    return obj


def grid(name, nu, nv, fn, loc=(0, 0, 0), material=None, rot=(0, 0, 0), thick=0.0, sub=0, col=None,
         uv01=False):
    """Parametric surface: fn(u, v) -> (x, y, z) for u, v in 0..1. Used for cloth,
    duvets, curtains, rugs, paper."""
    bm = bmesh.new()
    vs = [[bm.verts.new(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    uvl = bm.loops.layers.uv.new("UVMap") if uv01 else None
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
            if uvl:
                for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    lp[uvl].uv = (a / nu, b / nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if not uv01:
        uv_project(me)
    me.shade_smooth()
    obj = bpy.data.objects.new(name, me)
    _link(obj, col)
    obj.location = loc
    obj.rotation_euler = (0, 0, rot) if isinstance(rot, (int, float)) else rot
    if material is not None:
        me.materials.append(material)
    if thick:
        s = obj.modifiers.new("Solidify", "SOLIDIFY")
        s.thickness = thick
        s.offset = 0.0
    if sub:
        subsurf(obj, sub)
    return obj


def quad(name, w, h, loc, material=None, rot=(0, 0, 0), col=None):
    """Flat sheet in local XY with 0..1 UVs (paper, pictures, screens)."""
    return grid(name, 1, 1, lambda u, v: ((u - 0.5) * w, (v - 0.5) * h, 0.0), loc, material, rot,
                col=col, uv01=True)


def pipe(name, pts, r, material=None, smooth=True, col=None, cyclic=False, res=8):
    """Tube through absolute points (rails, faucets, lamp arms, cables)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    cu.resolution_u = res
    sp = cu.splines.new("BEZIER" if smooth else "POLY")
    if smooth:
        sp.bezier_points.add(len(pts) - 1)
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = p
            bp.handle_left_type = bp.handle_right_type = "AUTO"
    else:
        sp.points.add(len(pts) - 1)
        for sp_p, p in zip(sp.points, pts):
            sp_p.co = (*p, 1.0)
    sp.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, cu)
    _link(obj, col)
    if material is not None:
        cu.materials.append(material)
    return obj


def soft_box(name, size, loc, material=None, rot=0.0, round_=0.06, puff=0.0, col=None, anchor=(0, 0, -1),
             cuts=6):
    """Rounded, slightly puffy box for cushions, mattresses, pillows."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    off = Vector((-anchor[0] * sx / 2, -anchor[1] * sy / 2, -anchor[2] * sz / 2))
    for v in bm.verts:
        x, y, z = v.co
        if puff:
            # bulge the top/bottom towards the centre, pinch towards the seams
            k = max((1 - (2 * x) ** 2) * (1 - (2 * y) ** 2), 0.0) ** 0.9
            z *= (1 - puff) + puff * (0.22 + 1.6 * k)
        v.co = Vector((x * sx, y * sy, z * sz)) + off
    obj = _finish(name, bm, loc, rot, material, col=col)
    obj.data.shade_smooth()
    b = obj.modifiers.new("Bevel", "BEVEL")
    b.width = min(round_, min(size) * 0.45)
    b.segments = 4
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(60)
    return obj


def join(objs, name=None):
    """Join meshes into the first object (keeps scene object count sane)."""
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs,
                                       selected_objects=objs, object=objs[0]):
            bpy.ops.object.join()
    if name:
        objs[0].name = name
    return objs[0]


def group(name, objs, loc=None, rot=0.0, col=None):
    """Parent objects under an empty placed at `loc`; children keep world positions
    relative to the origin they were built around."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.1
    _link(e, col)
    for o in objs:
        if o is not None and o.parent is None:
            o.parent = e
    if loc is not None:
        e.location = loc
    e.rotation_euler = (0, 0, rot)
    return e


# ---------------------------------------------------------------- assets ---
_PROTO = {}


def _world(o, cache):
    if o in cache:
        return cache[o]
    m = o.matrix_basis.copy()
    if o.parent is not None:
        m = _world(o.parent, cache) @ o.matrix_parent_inverse @ m
    cache[o] = m
    return m


def load_asset(aid):
    """Append a Poly Haven model once; return its parts (top-level objects) with bounds."""
    if aid in _PROTO:
        return _PROTO[aid]
    blends = sorted(glob.glob(os.path.join(ASSETS, "models", aid, "*.blend")))
    if not blends:
        raise FileNotFoundError("asset not downloaded: " + aid)
    with bpy.data.libraries.load(blends[0], link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None]
    oset = set(objs)
    cache = {}
    parts = []
    for root in sorted((o for o in objs if o.parent is None or o.parent not in oset), key=lambda o: o.name):
        members = [root] + [c for c in root.children_recursive if c in oset]
        lo = Vector((1e9,) * 3)
        hi = Vector((-1e9,) * 3)
        has_mesh = False
        for mbr in members:
            if mbr.type != "MESH":
                continue
            has_mesh = True
            mw = _world(mbr, cache)
            for c in mbr.bound_box:
                p = mw @ Vector(c)
                lo = Vector(map(min, lo, p))
                hi = Vector(map(max, hi, p))
        if has_mesh:
            parts.append({"name": root.name, "root": root, "members": members, "lo": lo, "hi": hi,
                          "world": {m: _world(m, cache) for m in members}})
    _PROTO[aid] = parts
    return parts


def asset_size(aid, part=None):
    lo, hi = _bounds(_pick(load_asset(aid), part))
    return hi - lo


def _pick(parts, part):
    """part: None (whole set), int (index) or regex matched against part names (all matches)."""
    if part is None:
        return parts
    if isinstance(part, int):
        return [parts[part % len(parts)]]
    sel = [p for p in parts if re.search(part, p["name"])]
    if not sel:
        raise KeyError("part {} not in {}".format(part, [p["name"] for p in parts]))
    return sel


def _bounds(parts):
    lo = Vector(map(min, *[p["lo"] for p in parts])) if len(parts) > 1 else parts[0]["lo"].copy()
    hi = Vector(map(max, *[p["hi"] for p in parts])) if len(parts) > 1 else parts[0]["hi"].copy()
    return lo, hi


def place(aid, loc, rot=0.0, scale=1.0, part=None, col=None, tilt=(0.0, 0.0), name=None):
    """Instance a Poly Haven model (or one part of a set) with its bounding-box
    bottom centre at `loc`, rotated `rot` radians about Z. Returns the root copy;
    obj['top'] is the world Z of its top, obj['dims'] its scaled size."""
    parts = _pick(load_asset(aid), part)
    lo, hi = _bounds(parts)
    anchor = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    M = (Matrix.Translation(Vector(loc)) @ Euler((tilt[0], tilt[1], rot)).to_matrix().to_4x4()
         @ Matrix.Scale(scale, 4) @ Matrix.Translation(-anchor))
    roots = []
    for p in parts:
        mapping = {}
        for mbr in p["members"]:
            c = mbr.copy()
            _link(c, col)
            mapping[mbr] = c
        for mbr, c in mapping.items():
            if mbr is p["root"]:
                c.parent = None
                c.matrix_world = M @ p["world"][mbr]
            else:
                c.parent = mapping[mbr.parent]
            for md in c.modifiers:
                tgt = getattr(md, "object", None)
                if tgt in mapping:
                    md.object = mapping[tgt]
        roots.append(mapping[p["root"]])
    root = roots[0]
    if len(roots) > 1:
        bpy.context.view_layer.update()
        root = group(name or aid, [], col=col)
        for r in roots:
            mw = r.matrix_world.copy()
            r.parent = root
            r.matrix_world = mw
    elif name:
        root.name = name
    dims = (hi - lo) * scale
    root["dims"] = tuple(dims)
    root["top"] = loc[2] + dims.z
    return root


def describe_assets(ids=None):
    """Summarise every downloaded model: part names and sizes (for layout planning)."""
    out = {}
    for d in sorted(os.listdir(os.path.join(ASSETS, "models"))):
        if ids and d not in ids:
            continue
        try:
            parts = load_asset(d)
        except Exception as ex:  # noqa: BLE001
            out[d] = "ERR " + str(ex)
            continue
        lo, hi = _bounds(parts)
        s = hi - lo
        entry = "{:.2f}x{:.2f}x{:.2f}".format(s.x, s.y, s.z)
        if len(parts) > 1:
            entry += " | " + "; ".join("{} {:.2f}x{:.2f}x{:.2f}".format(
                p["name"], *(p["hi"] - p["lo"])) for p in parts[:14])
        out[d] = entry
    return out


def boxes(name, items, material=None, col=None, swap=False):
    """One mesh made of many axis-aligned boxes given as (p0, p1) absolute corners.
    Vertices stay in world space so box-projected UVs line up across pieces
    (tile grout continues around door and window openings)."""
    bm = bmesh.new()
    for p0, p1 in items:
        lo = [min(a, b) for a, b in zip(p0, p1)]
        hi = [max(a, b) for a, b in zip(p0, p1)]
        if min(h - l for l, h in zip(lo, hi)) <= 1e-6:
            continue
        geom = bmesh.ops.create_cube(bm, size=1.0)
        for v in geom["verts"]:
            v.co = Vector(((v.co.x + 0.5) * (hi[0] - lo[0]) + lo[0],
                           (v.co.y + 0.5) * (hi[1] - lo[1]) + lo[1],
                           (v.co.z + 0.5) * (hi[2] - lo[2]) + lo[2]))
    return _finish(name, bm, (0, 0, 0), 0.0, material, swap=swap, col=col)


def light(name, loc, power, color="#ffd9b0", kind="POINT", radius=0.05, size=None, rot=(0, 0, 0), spot=None):
    """Lamp. Point lights get a soft radius; AREA lights take `size` (w, h)."""
    li = bpy.data.lights.new(name, kind)
    li.energy = power
    li.color = rgb(color)[:3]
    if kind == "AREA":
        li.shape = "RECTANGLE"
        li.size, li.size_y = size or (0.3, 0.3)
    else:
        li.shadow_soft_size = radius
    if kind == "SPOT" and spot:
        li.spot_size = spot
        li.spot_blend = 0.5
    obj = bpy.data.objects.new(name, li)
    _link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    # the bare emitter stays out of sight and out of reflections; the visible fitting
    # (shade, opal diffuser, LED puck) is what the camera and glossy surfaces see
    obj.visible_camera = False
    obj.visible_glossy = False
    return obj


_TEX = {}


def lumpy(obj, strength=0.03, size=0.25, seed=0):
    """Displace along normals with cloud noise: wrinkles for duvets, clothes, cushions."""
    key = (round(size, 3), seed)
    if key not in _TEX or _TEX[key].name not in bpy.data.textures:
        t = bpy.data.textures.new("Clouds_{}_{}".format(size, seed), "CLOUDS")
        t.noise_scale = size
        t.noise_depth = 2
        _TEX[key] = t
    d = obj.modifiers.new("Wrinkle", "DISPLACE")
    d.texture = _TEX[key]
    d.strength = strength
    d.mid_level = 0.5
    d.texture_coords = "GLOBAL" if seed else "LOCAL"
    return d


def basin(name, size, loc, material=None, wall=0.03, depth=None, taper=0.0, rot=0.0, bevel=0.01, col=None,
          segs=3):
    """Open-topped vessel (sink, tub, tray, bin, drawer): a box whose top face is
    inset and pushed down so it has a real cavity."""
    sx, sy, sz = size
    depth = sz - wall if depth is None else depth
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, (v.co.z + 0.5) * sz))
    bm.faces.ensure_lookup_table()
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    res = bmesh.ops.inset_region(bm, faces=[top], thickness=wall, depth=0.0)
    for v in top.verts:
        v.co.z -= depth
        v.co.x *= 1.0 - taper
        v.co.y *= 1.0 - taper
    return _finish(name, bm, loc, rot, material, bevel=bevel, col=col, segs=segs)


def ring(name, r, tube, loc, material=None, rot=(0, 0, 0), col=None, n=24):
    """Torus built as a closed tube."""
    pts = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), 0.0) for i in range(n)]
    o = pipe(name, pts, tube, material, smooth=True, col=col, cyclic=True, res=4)
    o.location = loc
    o.rotation_euler = rot
    return o


def refresh():
    """Update the dependency graph so ray casts see everything placed so far."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    return dg


def surface_z(x, y, z_from=2.6, dg=None):
    """Height of the first surface below (x, y, z_from); None if nothing is hit."""
    dg = dg or bpy.context.evaluated_depsgraph_get()
    hit, loc, _n, _i, _o, _m = bpy.context.scene.ray_cast(dg, Vector((x, y, z_from)), Vector((0, 0, -1)))
    return loc.z if hit else None


def levels(x, y, z_from=2.6, z_min=0.02, dg=None):
    """All upward-facing surface heights below a point (shelf boards, table tops)."""
    dg = dg or bpy.context.evaluated_depsgraph_get()
    out = []
    z = z_from
    for _ in range(40):
        hit, loc, n, _i, _o, _m = bpy.context.scene.ray_cast(dg, Vector((x, y, z)), Vector((0, 0, -1)))
        if not hit or loc.z < z_min:
            break
        if n.z > 0.5 and (not out or out[-1] - loc.z > 0.03):
            out.append(loc.z)
        z = loc.z - 0.004
    return out


def loft(name, rings, loc, material=None, rot=0.0, sub=2, col=None):
    """Skin a sequence of closed cross-sections (equal point counts) into a capped solid."""
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(vr[0])
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(vr[0][::-1])
    bm.faces.new(vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = _finish(name, bm, loc, rot, material, col=col)
    obj.data.shade_smooth()
    if sub:
        subsurf(obj, sub)
    return obj


def _collide(colliders):
    added = []
    for c in colliders:
        for o in [c] + list(c.children_recursive):
            if o.type == "MESH" and not any(m.type == "COLLISION" for m in o.modifiers):
                md = o.modifiers.new("Collision", "COLLISION")
                o.collision.thickness_outer = 0.012
                o.collision.cloth_friction = 25.0
                added.append((o, md))
    return added


def _freeze(obj, frames, added):
    """Step the cloth solver, bake the result into plain mesh data, drop the physics."""
    sc = bpy.context.scene
    for f in range(1, frames + 1):
        sc.frame_set(f)
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    old = obj.data
    obj.modifiers.clear()
    obj.vertex_groups.clear()
    obj.data = me
    bpy.data.meshes.remove(old)
    me.shade_smooth()
    for o, md in added:
        o.modifiers.remove(md)
    sc.frame_set(1)
    return obj


def drape(name, w, l, loc, rot, material, colliders, frames=40, res=36, thick=0.006, stiffness=4.0, bend=0.08,
          shrink=0.0, mass=0.25, shape=None, piping=0.0):
    """Drop a sheet of cloth onto `colliders` with the cloth solver, then freeze the
    result into a plain mesh. Gives real folds and overhang for blankets and throws."""
    sc = bpy.context.scene
    nx, ny = res, max(8, int(res * l / w))
    obj = grid(name, nx, ny, shape or (lambda u, v: ((u - 0.5) * w, (v - 0.5) * l, 0.0)), loc, material, rot)
    cm = obj.modifiers.new("Cloth", "CLOTH")
    st = cm.settings
    st.quality = 6
    st.mass = mass
    st.tension_stiffness = st.compression_stiffness = st.shear_stiffness = stiffness
    st.bending_stiffness = bend
    st.shrink_min = shrink          # negative = surplus fabric, which buckles into wrinkles
    st.air_damping = 2.0
    cs = cm.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.012
    cs.collision_quality = 3
    cs.use_self_collision = False
    cm.point_cache.frame_start = 1
    cm.point_cache.frame_end = frames
    _freeze(obj, frames, _collide(colliders))
    if piping:                    # sewn edge: a cord running round the whole hem
        idx = [i * (ny + 1) for i in range(nx + 1)] + [nx * (ny + 1) + j for j in range(1, ny + 1)] + \
              [i * (ny + 1) + ny for i in range(nx - 1, -1, -1)] + [j for j in range(ny - 1, 0, -1)]
        vs = obj.data.vertices
        cord = pipe(name + "_piping", [tuple(vs[k].co) for k in idx[::2]], piping, material, cyclic=True, res=3)
        cord.location = obj.location
        cord.rotation_euler = obj.rotation_euler
    if thick:
        sd = obj.modifiers.new("Solidify", "SOLIDIFY")
        sd.thickness = thick
        sd.offset = 1.0
    subsurf(obj, 1)
    return obj


def hang(name, w, h, loc, rot, material, colliders, pin=0.12, frames=60, res=28, thick=0.01):
    """Garment-like sheet hung from a hook: only a short stretch of the top edge is
    pinned, the cloth solver lets the corners sag and fold. loc = hook point on the
    wall (local front is -Y)."""
    sc = bpy.context.scene
    nx, ny = res, max(8, int(res * h / w))
    obj = grid(name, nx, ny, lambda u, v: ((u - 0.5) * w, -0.045 - 0.03 * math.sin(u * math.pi), -v * h),
               loc, material, rot)
    vg = obj.vertex_groups.new(name="pin")
    ids = [i * (ny + 1) for i in range(nx + 1) if abs((i / nx - 0.5) * w) <= pin / 2 + 1e-6]
    vg.add(ids, 1.0, "REPLACE")
    cm = obj.modifiers.new("Cloth", "CLOTH")
    st = cm.settings
    st.quality = 6
    st.mass = 0.3
    st.tension_stiffness = st.compression_stiffness = st.shear_stiffness = 6.0
    st.bending_stiffness = 0.03
    st.shrink_min = -0.05
    st.air_damping = 6.0
    st.vertex_group_mass = "pin"
    st.pin_stiffness = 1.0
    cs = cm.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.012
    cs.use_self_collision = False
    cm.point_cache.frame_start = 1
    cm.point_cache.frame_end = frames
    added = []
    for c in colliders:
        if c.type == "MESH" and not any(m.type == "COLLISION" for m in c.modifiers):
            added.append((c, c.modifiers.new("Collision", "COLLISION")))
            c.collision.thickness_outer = 0.01
    for f in range(1, frames + 1):
        sc.frame_set(f)
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    old = obj.data
    obj.modifiers.clear()
    obj.vertex_groups.clear()
    obj.data = me
    bpy.data.meshes.remove(old)
    me.shade_smooth()
    for o, md in added:
        o.modifiers.remove(md)
    sc.frame_set(1)
    sd = obj.modifiers.new("Solidify", "SOLIDIFY")
    sd.thickness = thick
    sd.offset = 0.0
    subsurf(obj, 1)
    return obj


_MB = [0]


def blob(name, elems, loc, material=None, rot=0.0, height=None, res=0.01):
    """Organic solid from metaballs (elements blend into each other), frozen to a
    mesh. elems: (x, y, z, radius[, (sx, sy, sz)]). `height` rescales the result."""
    _MB[0] += 1
    mb = bpy.data.metaballs.new("blobfam{}q".format(_MB[0]))
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = 0.6
    for e in elems:
        el = mb.elements.new(type="ELLIPSOID" if len(e) > 4 else "BALL")
        el.co = e[:3]
        el.radius = e[3] * 1.7
        el.stiffness = 2.0
        if len(e) > 4:
            el.size_x, el.size_y, el.size_z = e[4]
    tmp = bpy.data.objects.new("blobfam{}q".format(_MB[0]), mb)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp)
    bpy.data.metaballs.remove(mb)
    if len(me.vertices) and height:
        zs = [v.co.z for v in me.vertices]
        k = height / max(max(zs) - min(zs), 1e-6)
        z0 = min(zs)
        for v in me.vertices:
            v.co = Vector((v.co.x * k, v.co.y * k, (v.co.z - z0) * k))
    uv_project(me)
    me.shade_smooth()
    obj = bpy.data.objects.new(name, me)
    _link(obj)
    obj.location = loc
    obj.rotation_euler = (0, 0, rot)
    if material is not None:
        me.materials.append(material)
    return obj


def inflate(name, size, loc, material, rot=0.0, pressure=6.0, frames=28, colliders=(), gravity=1.0, cuts=12, shrink=-0.05,
            bend=0.4, sub=1):
    """Stuffed fabric form (pillow, cushion, soft bag): a flat closed box inflated by
    cloth pressure, with surplus fabric so seams pucker, optionally settling under
    gravity onto colliders."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    obj = _finish(name, bm, loc, rot, material)
    cm = obj.modifiers.new("Cloth", "CLOTH")
    st = cm.settings
    st.quality = 7
    st.mass = 0.3
    st.tension_stiffness = st.compression_stiffness = st.shear_stiffness = 12.0
    st.bending_stiffness = bend
    st.shrink_min = shrink
    st.use_pressure = True
    st.uniform_pressure_force = pressure
    st.air_damping = 4.0
    st.effector_weights.gravity = gravity
    cs = cm.collision_settings
    cs.use_collision = bool(colliders)
    cs.distance_min = 0.01
    cs.use_self_collision = False
    cm.point_cache.frame_start = 1
    cm.point_cache.frame_end = frames
    _freeze(obj, frames, _collide(colliders))
    if sub:
        subsurf(obj, sub)
    return obj


def drape_over(name, w, front, back, loc, rot, material, colliders=(), frames=75, res=28, thick=0.012, bend=0.01):
    """Towel thrown over a rail: a flat sheet pinned along the line that sits on the
    rail, with a thin bar under it so the two flaps fall on opposite sides. loc = rail
    centre; the `front` length hangs towards local -Y."""
    L = front + back
    ny = max(12, int(res * L / w))
    row = round(ny * back / L)
    # gathered on the rail: the cloth is ~15 % wider than the stretch it is pinned to, so it falls in soft vertical folds
    obj = grid(name, res, ny, lambda u, v: ((u - 0.5) * w * 0.86 + 0.01 * math.sin(v * 7), back - v * L,
                                             0.016 + 0.012 * math.sin(u * 21) * (1.0 if abs(v * L - back) > 0.03 else 0.2)),
               loc, material, rot)
    vg = obj.vertex_groups.new(name="pin")
    vg.add([i * (ny + 1) + row for i in range(res + 1)], 1.0, "REPLACE")
    bar = box(name + "_bar", (w + 0.06, 0.014, 0.014), loc, None, rot=rot, anchor=(0, 0, 1))
    cm = obj.modifiers.new("Cloth", "CLOTH")
    st = cm.settings
    st.quality = 6
    st.mass = 0.3
    st.tension_stiffness = st.compression_stiffness = st.shear_stiffness = 5.0
    st.bending_stiffness = bend
    st.shrink_min = -0.07         # surplus cloth: soft vertical ripples instead of a flat card
    st.air_damping = 8.0          # heavy damping: the flaps must hang still, not be caught mid-swing
    st.vertex_group_mass = "pin"
    st.pin_stiffness = 1.0
    cs = cm.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.004
    cs.use_self_collision = False
    cm.point_cache.frame_start = 1
    cm.point_cache.frame_end = frames
    _freeze(obj, frames, _collide([bar] + list(colliders)))
    bpy.data.objects.remove(bar)
    if _REC and bar in _REC[-1]:
        _REC[-1].remove(bar)
    sd = obj.modifiers.new("Solidify", "SOLIDIFY")
    sd.thickness = thick
    sd.offset = 0.0
    subsurf(obj, 1)
    return obj


def folded(name, w, d, loc, material, layers=3, t=0.012, rot=0.0):
    """Folded textile: one strip laid back and forth on itself, so the edge shows real
    fold loops and stacked layers instead of a block."""
    def fn(u, v):
        s = u * layers
        tri = 1.0 - 2.0 * abs((s % 2.0) - 1.0)            # triangle wave -1..1
        x = (w / 2) * tri
        z = t * 0.62 + t * 1.25 * s + 0.0012 * math.sin(v * 7 + s * 2)
        return (x, (v - 0.5) * d * (1.0 - 0.02 * (s % 2.0)), z)
    obj = grid(name, layers * 10, 8, fn, loc, material, rot)
    sd = obj.modifiers.new("Solidify", "SOLIDIFY")
    sd.thickness = t
    sd.offset = 0.0
    subsurf(obj, 2)
    return obj


def fur(obj, length=0.0045, count=12000, children=3):
    """Short plush pile as real hair strands, so the silhouette is fuzzy rather than
    a smooth shell. Silently skipped if the hair system is unavailable."""
    try:
        obj.modifiers.new("Fur", "PARTICLE_SYSTEM")
        st = obj.particle_systems[-1].settings
        st.type = "HAIR"
        st.count = count
        st.hair_length = length
        st.hair_step = 3
        st.display_step = 2
        st.render_step = 3
        st.child_type = "INTERPOLATED"
        st.child_percent = children
        st.rendered_child_count = children
        st.child_length = 1.0
        st.roughness_2 = 0.25
        st.roughness_endpoint = 0.02
        st.root_radius = 0.35
        st.tip_radius = 0.12
        st.radius_scale = 0.006
        st.material = 1
        return True
    except Exception:  # noqa: BLE001
        return False


DEMO = os.path.join(ASSETS, "demo")


def demo(fname, collection=None, names=None, exclude=None, name=None):
    """Append artist-made pieces from one of Blender's official demo scenes and gather
    them under an empty at the bottom-centre of their bounding box, so the group can
    be placed like any other fixture. Pick by `collection` or by a regex on object
    names; `exclude` drops matching objects. Returns (empty, size, objects)."""
    path = os.path.join(DEMO, fname)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        if collection:
            dst.collections = [collection]
        else:
            dst.objects = [o for o in src.objects if re.search(names, o)]
    if collection:
        col = dst.collections[0]
        objs = list(col.all_objects)
        bpy.data.collections.remove(col)
    else:
        objs = [o for o in dst.objects if o is not None]
    if exclude:
        drop = [o for o in objs if re.search(exclude, o.name)]
        objs = [o for o in objs if o not in drop]
        for o in drop:
            bpy.data.objects.remove(o)
    keep = []
    for o in objs:
        if o.type in ("MESH", "CURVE", "EMPTY"):
            _link(o)
            keep.append(o)
        else:                                  # their lights and cameras stay behind
            bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in keep if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    e = bpy.data.objects.new(name or (collection or "Demo"), None)
    e.empty_display_size = 0.2
    _link(e)
    e.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)
    bpy.context.view_layer.update()
    inv = e.matrix_world.inverted()
    kset = set(keep)
    for o in keep:
        if o.parent is None or o.parent not in kset:
            mw = o.matrix_world.copy()
            o.parent = e
            o.matrix_parent_inverse = inv
            o.matrix_world = mw
    e["dims"] = tuple(hi - lo)
    return e, hi - lo, keep

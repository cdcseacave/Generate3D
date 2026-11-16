"""Bring artist-made furnishings in from Mitsuba scene exports (Benedikt Bitterli's
"Rendering resources", https://benedikt-bitterli.me/resources/): OBJ meshes in world
coordinates plus a scene.xml that names each mesh's material ("Kettle", "CupboardUnits").

Scenes used and their licences (each folder carries its LICENSE.txt):
    kitchen   'Country Kitchen' by Jay-Artist       CC-BY
    bathroom  'Contemporary Bathroom' by Mareck     CC0
    bedroom   'Bedroom' by SlykDrako                CC0
    bathroom2 'Salle de bain' by nacimus            CC-BY

`kit()` imports the shapes whose material id matches, converts Y-up to Z-up, rebuilds the
materials on the Principled BSDF and parents everything to one empty, so a whole fitted
kitchen or a bed can be scaled, turned and set down inside a room of the plan."""
import math
import os
import re
import xml.etree.ElementTree as ET

import bpy
from mathutils import Matrix, Vector

from . import core as C

SCENES = os.path.join(C.ASSETS, "scenes")
_YUP = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))      # Mitsuba (x, y, z) -> Blender (x, -z, y)


def _floats(s):
    v = [float(x) for x in s.replace(",", " ").split()]
    return v * 3 if len(v) == 1 else v


def _params(node):
    """name -> ('rgb', (r, g, b)) | ('tex', path) | ('float', v) | ('str', s) for one bsdf element."""
    out = {}
    for k in node:
        n = k.get("name")
        if k.tag in ("rgb", "spectrum", "srgb"):
            out[n] = ("rgb", tuple(_floats(k.get("value"))[:3]))
        elif k.tag == "float":
            out[n] = ("float", float(k.get("value")))
        elif k.tag == "string":
            out[n] = ("str", k.get("value"))
        elif k.tag == "texture":
            fn = next((s.get("value") for s in k.iter("string") if s.get("name") == "filename"), None)
            sc = {f.get("name"): float(f.get("value")) for f in k.iter("float")}
            out[n] = ("tex", fn, sc.get("uscale", 1.0), sc.get("vscale", 1.0)) if fn else ("rgb", (0.5, 0.5, 0.5))
    return out


def _socket(nt, bsdf, scene, name, val, noncolor=False):
    """Feed a Principled input from a colour or a texture file."""
    if val is None:
        return
    if val[0] == "rgb":
        bsdf.inputs[name].default_value = (*val[1], 1.0)
        return
    path = os.path.join(SCENES, scene, val[1])
    if not os.path.exists(path):
        return
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = C._img(path, noncolor)
    if val[2] != 1.0 or val[3] != 1.0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (val[2], val[3], 1.0)
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
        nt.links.new(mp.outputs[0], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs[name])
    return tex


def material(scene, bid, node):
    """Translate one Mitsuba bsdf (unwrapping twosided / bumpmap / mask) to a Principled material."""
    name = "{}:{}".format(scene, bid)
    if name in C._MATS:
        return C._MATS[name]
    m, nt, bsdf, _ = C._new_mat(name)
    bump = None
    while node is not None and node.get("type") in ("twosided", "bumpmap", "mask", "coating", "roughcoating"):
        if node.get("type") == "bumpmap":
            t = node.find("texture")
            fn = next((s.get("value") for s in t.iter("string") if s.get("name") == "filename"), None) if t is not None else None
            sc = next((float(f.get("value")) for f in t.iter("float") if f.get("name") == "scale"), 1.0) if t is not None else 1.0
            bump = (fn, sc)
        node = node.find("bsdf")
    kind = node.get("type") if node is not None else "diffuse"
    p = _params(node) if node is not None else {}
    I = bsdf.inputs
    rough = math.sqrt(p["alpha"][1]) if "alpha" in p and p["alpha"][0] == "float" else None
    if kind in ("diffuse", "roughdiffuse"):
        _socket(nt, bsdf, scene, "Base Color", p.get("reflectance", ("rgb", (0.5, 0.5, 0.5))))
        I["Roughness"].default_value = 0.85
        I["Specular IOR Level"].default_value = 0.25
    elif kind in ("plastic", "roughplastic"):
        _socket(nt, bsdf, scene, "Base Color", p.get("diffuseReflectance", ("rgb", (0.5, 0.5, 0.5))))
        I["Roughness"].default_value = rough if rough is not None else 0.06
        I["IOR"].default_value = p.get("intIOR", ("float", 1.5))[1]
    elif kind in ("conductor", "roughconductor"):
        eta = p.get("eta", ("rgb", (0.2, 0.92, 1.1)))[1]
        k = p.get("k", ("rgb", (3.9, 2.45, 2.14)))[1]
        spec = p.get("specularReflectance", ("rgb", (1, 1, 1)))
        spec = spec[1] if spec[0] == "rgb" else (1, 1, 1)
        col = [min(1.0, s * ((n - 1) ** 2 + kk ** 2) / ((n + 1) ** 2 + kk ** 2)) for n, kk, s in zip(eta, k, spec)]
        if p.get("material", ("", ""))[1] == "none":            # Mitsuba's ideal mirror: silvered glass, not a tinted metal
            col = [0.93, 0.945, 0.94]
        I["Base Color"].default_value = (*col, 1.0)
        I["Metallic"].default_value = 1.0
        I["Roughness"].default_value = rough if rough is not None else 0.03
        if rough is not None and rough > 0.12:                  # used metal is never evenly brushed: smears, rub marks, cleaner streaks
            tc = nt.nodes.new("ShaderNodeTexCoord")
            nz = nt.nodes.new("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = 9.0
            nz.inputs["Detail"].default_value = 9.0
            nz.inputs["Roughness"].default_value = 0.62
            mp = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (1.0, 1.0, 0.18)   # drawn out along the object's height, like wiping marks
            mr = nt.nodes.new("ShaderNodeMapRange")
            mr.inputs["From Min"].default_value = 0.3
            mr.inputs["From Max"].default_value = 0.72
            mr.inputs["To Min"].default_value = rough * 0.62
            mr.inputs["To Max"].default_value = min(0.6, rough * 1.55 + 0.04)
            nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
            nt.links.new(mp.outputs[0], nz.inputs["Vector"])
            nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
            nt.links.new(mr.outputs[0], I["Roughness"])
    elif kind in ("dielectric", "thindielectric", "roughdielectric"):
        I["Base Color"].default_value = (1, 1, 1, 1)
        I["Transmission Weight"].default_value = 1.0
        I["Roughness"].default_value = rough if rough is not None else 0.0
        I["IOR"].default_value = p.get("intIOR", ("float", 1.5))[1] if kind != "thindielectric" else 1.02
    else:
        I["Roughness"].default_value = 0.6
    if bump and bump[0]:
        path = os.path.join(SCENES, scene, bump[0])
        if os.path.exists(path):
            bt = nt.nodes.new("ShaderNodeTexImage")
            bt.image = C._img(path, True)
            bp = nt.nodes.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = min(1.0, 0.25 * max(bump[1], 0.2) + 0.15)
            bp.inputs["Distance"].default_value = 0.004
            nt.links.new(bt.outputs["Color"], bp.inputs["Height"])
            nt.links.new(bp.outputs[0], I["Normal"])
    return m


def kit(scene, name, keep=None, drop=None, box=None, scale=1.0, rot=0.0, loc=(0.0, 0.0, 0.0), xml="scene_v0.6.xml", lights=False):
    """Import part of a scene as one movable group.

    keep / drop: regex on the material id of each shape. box: ((x0, y0, z0), (x1, y1, z1)) in the
    scene's own Z-up coordinates; a shape is taken only if its centre lies inside. The group is
    then scaled, turned about Z and moved: p_world = Rz(rot) * scale * p_scene + loc.
    Returns (empty, {material id: [objects]})."""
    root = ET.parse(os.path.join(SCENES, scene, xml)).getroot()
    bsdfs = {b.get("id"): b for b in root if b.tag == "bsdf" and b.get("id")}
    rk = re.compile(keep) if keep else None
    rd = re.compile(drop) if drop else None
    col = C._state["col"] or bpy.context.scene.collection
    made = {}
    for n, s in enumerate(root.iter("shape")):
        fn = next((k.get("value") for k in s if k.tag == "string" and k.get("name") == "filename"), None)
        if not fn or not fn.lower().endswith(".obj"):
            continue
        ref = next((k.get("id") for k in s if k.tag == "ref"), None)
        inline = s.find("bsdf")
        if s.find("emitter") is not None and not lights:
            continue
        bid = ref or "inline{}".format(n)
        if (rk and not rk.search(bid)) or (rd and rd.search(bid)):
            continue
        before = set(bpy.data.objects)
        bpy.ops.wm.obj_import(filepath=os.path.join(SCENES, scene, fn), forward_axis="NEGATIVE_Z", up_axis="Y")
        new = [o for o in bpy.data.objects if o not in before]
        tm = s.find("transform")
        mv = _floats(tm.find("matrix").get("value")) if tm is not None and tm.find("matrix") is not None else None
        M = Matrix((mv[0:4], mv[4:8], mv[8:12], mv[12:16])) if mv and len(mv) == 16 else Matrix.Identity(4)
        mat = material(scene, bid, bsdfs.get(ref) if ref else inline)
        for o in new:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            col.objects.link(o)
            if M != Matrix.Identity(4):
                o.matrix_world = _YUP @ M @ _YUP.inverted() @ o.matrix_world
            if box is not None:
                bpy.context.view_layer.update()
                pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
                ctr = sum(pts, Vector()) / 8.0
                if not all(box[0][i] <= ctr[i] <= box[1][i] for i in range(3)):
                    bpy.data.objects.remove(o)
                    continue
            o.data.materials.clear()
            o.data.materials.append(mat)
            for poly in o.data.polygons:
                poly.use_smooth = not any(k.tag == "boolean" and k.get("name") == "faceNormals" and k.get("value") == "true" for k in s)
            o["mid"] = bid
            o.name = "{}_{}".format(name, bid)
            made.setdefault(bid, []).append(o)
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.2
    col.objects.link(e)
    for objs in made.values():
        for o in objs:
            o.parent = e                    # children keep their scene coordinates as local coordinates
    e.scale = (scale, scale, scale)
    e.rotation_euler = (0.0, 0.0, rot)
    e.location = loc
    bpy.context.view_layer.update()
    return e, made

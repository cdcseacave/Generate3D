"""Fly-through of the whole flat. Runs in its own Blender, not through the MCP bridge:

    blender -b out/apartment_scene.blend -P apartment/flythrough.py -- plan
    blender -b out/apartment_scene.blend -P apartment/flythrough.py -- preview
    blender -b out/apartment_scene.blend -P apartment/flythrough.py -- final [first last]

The route starts at the front door and visits living room, bedroom, kitchen, office and
bathroom in that order, crossing the hallway between them, then walks back to the door. Inside a
room the camera circles along the walls, its back to the nearest wall, looking across the
middle of the room at the far side. The circle is fitted to what is really there: anything
standing in the camera's height band (wardrobe, shelves, fridge, open door leaves, plants,
wall cupboards) pushes the path inwards, lower furniture is flown over.

plan     top view of the flat with the route drawn in  -> out/flythrough/path.png
preview  small, fast frames (EEVEE) and an mp4         -> out/flythrough/preview.mp4
final    2560 x 1440 Cycles frames, resumable          -> out/flythrough/frames/*.png
         (encode with ffmpeg afterwards; see PLAN.md)"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from apartment import shell as S  # noqa: E402

OUT = os.path.join(ROOT, "out", "flythrough")
FPS = 24
SPEED = 1.0                 # m/s
EYE = 1.5
LENS = 18.0
MARGIN = 0.36               # camera to wall or tall furniture
BAND = (1.25, 1.85)         # anything between these heights is in the camera's way
# metered like the stills; the camera's exposure follows the room it is in
ROOM_AT = []
ROOM_EV = {"living": 3.3, "kitchen": 3.1, "hall": 1.7, "bedroom": 3.2, "office": 3.0, "bath": 1.0}
# (room, x where the route crosses the wall, wall y, +1 if the room is north of the hall)
# in visiting order: living room, bedroom across the hall, kitchen, office, bathroom
DOORS = [("living", 2.7, S.YH0, -1), ("bedroom", 2.96, S.YH1, 1), ("kitchen", 7.8, S.YH0, -1),
         ("office", 5.35, S.YH1, 1), ("bath", 8.5, S.YH1, 1)]


# ------------------------------------------------------------------ free space ---
def blocked(dg, x, y):
    hit, loc, _n, _i, ob, _m = bpy.context.scene.ray_cast(dg, (x, y, BAND[0]), (0, 0, 1), distance=BAND[1] - BAND[0])
    return bool(hit and ob is not None and not ob.get("is_ceiling"))


def circuit(dg, room, n=360):
    """Closed path (list of (x, y)) hugging the walls of a room, counter-clockwise."""
    x0, y0, x1, y1 = S.inner(room)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if blocked(dg, cx, cy):                                    # e.g. a pendant in the middle: step aside
        for r in (0.3, 0.5, 0.7, 0.9):
            cand = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in (0, 1.57, 3.14, 4.71)]
            free = [c for c in cand if not blocked(dg, *c)]
            if free:
                cx, cy = free[0]
                break
    rad = []
    for i in range(n):
        a = 2 * math.pi * i / n
        dx, dy = math.cos(a), math.sin(a)
        r = 0.0
        while r < 12.0:
            px, py = cx + (r + 0.04) * dx, cy + (r + 0.04) * dy
            if not (x0 < px < x1 and y0 < py < y1) or blocked(dg, px, py):
                break
            r += 0.04
        rad.append(max(0.25, r - MARGIN))
    w = 4                                                       # never cut the corner of an obstacle, then round it off
    rad = [min(rad[(i + k) % n] for k in range(-w, w + 1)) for i in range(n)]
    for _ in range(2):
        rad = [sum(rad[(i + k) % n] for k in range(-4, 5)) / 9.0 for i in range(n)]
    return [(cx + rad[i] * math.cos(2 * math.pi * i / n), cy + rad[i] * math.sin(2 * math.pi * i / n)) for i in range(n)], (cx, cy)


def nearest(path, p):
    return min(range(len(path)), key=lambda i: (path[i][0] - p[0]) ** 2 + (path[i][1] - p[1]) ** 2)


def line(a, b, step=0.05):
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(1, n + 1)]


def route(dg):
    """[(x, y, look_x, look_y, room)] at irregular spacing; look = point the camera faces."""
    loops = {r: circuit(dg, r) for r in S.ROOMS if r != "hall"}
    here = (0.9, (S.YH0 + S.YH1) / 2)                           # just inside the entrance door
    out = []

    def across(p, c, room):                                     # look through the middle of the room at the far side
        out.append((p[0], p[1], 2 * c[0] - p[0], 2 * c[1] - p[1], room))

    def ahead(pts, room):                                       # look where you are going
        for i, p in enumerate(pts):
            q = pts[min(i + 8, len(pts) - 1)]
            d = (q[0] - p[0], q[1] - p[1]) if q != p else (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            out.append((p[0], p[1], p[0] + d[0] * 50, p[1] + d[1] * 50, room))

    for room, dx, wy, sgn in DOORS:
        loop, c = loops[room]
        d_hall, d_room = (dx, wy - sgn * 0.45), (dx, wy + sgn * 0.55)
        k = nearest(loop, d_room)
        ahead(line(here, d_hall) + line(d_hall, d_room), "hall")   # along the hall, looking where it goes
        ahead(line(d_room, loop[k]), room)
        for q in loop[k:] + loop[:k + 1]:
            across(q, c, room)
        ahead(line(loop[k], d_room) + line(d_room, d_hall), room)
        here = d_hall
    ahead(line(here, (8.2, 5.6)) + line((8.2, 5.6), (1.6, 5.6)), "hall")   # and back down the hall to the front door
    return out


def _smooth(vals, sigma):
    r = int(sigma * 3)
    ker = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-r, r + 1)]
    n = len(vals)
    res = []
    for i in range(n):
        acc, wsum = None, 0.0
        for k, wk in zip(range(-r, r + 1), ker):
            v = vals[min(max(i + k, 0), n - 1)]
            acc = v * wk if acc is None else acc + v * wk
            wsum += wk
        res.append(acc / wsum)
    return res


def frames(dg):
    """One (position, look direction, exposure) per frame at constant walking speed."""
    pts = route(dg)
    step = SPEED / FPS
    res, carry = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        t = step - carry
        while t <= seg:
            f = t / seg
            res.append(tuple(a[j] + (b[j] - a[j]) * f for j in range(4)) + (b[4],))
            t += step
        carry = (carry + seg) % step
    pos = _smooth([Vector((p[0], p[1])) for p in res], 0.2 * FPS)
    look = [(Vector((p[2], p[3])) - Vector((p[0], p[1]))).normalized() for p in res]
    look = [v.normalized() for v in _smooth(look, 0.9 * FPS)]
    ev = _smooth([ROOM_EV[p[4]] for p in res], 0.7 * FPS)
    ROOM_AT[:] = [p[4] for p in res]                            # room of each frame (index 0 = frame 1)
    return pos, look, ev


# ---------------------------------------------------------------------- scene ---
def setup():
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    pos, look, ev = frames(dg)
    cam = bpy.data.objects.get("Cam_Fly")
    if cam is None:
        cam = bpy.data.objects.new("Cam_Fly", bpy.data.cameras.new("Cam_Fly"))
        sc.collection.objects.link(cam)
    cam.data.lens, cam.data.sensor_width = LENS, 36.0
    cam.data.clip_start = 0.08
    cam.data.dof.use_dof = False
    cam.animation_data_clear()
    for o in bpy.data.objects:                                  # the stills' flash guns and their per-frame keys stay off
        if o.name.startswith("Flash_"):
            o.animation_data_clear()
            o.hide_render = True
    sc.animation_data_clear()
    prev = None
    for i, (p, d, e) in enumerate(zip(pos, look, ev), 1):
        cam.location = (p.x, p.y, EYE)
        q = Vector((d.x, d.y, -0.07)).to_track_quat("-Z", "Y")
        eul = q.to_euler("XYZ", prev) if prev else q.to_euler("XYZ")
        cam.rotation_euler = prev = eul
        cam.keyframe_insert("location", frame=i)
        cam.keyframe_insert("rotation_euler", frame=i)
        sc.view_settings.exposure = e
        sc.view_settings.keyframe_insert("exposure", frame=i)
    sc.camera = cam
    sc.frame_start, sc.frame_end = 1, len(pos)
    sc.render.fps = FPS
    for m in list(sc.timeline_markers):
        sc.timeline_markers.remove(m)
    return pos


def plan(pos):
    sc = bpy.context.scene
    cu = bpy.data.curves.new("FlyPath", "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    pts = pos[::4]
    sp.points.add(len(pts) - 1)
    for q, p in zip(sp.points, pts):
        q.co = (p.x, p.y, 2.2, 1.0)
    cu.bevel_depth = 0.025
    mat = bpy.data.materials.new("FlyPath")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em, om = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value = (1.0, 0.05, 0.02, 1.0)
    em.inputs["Strength"].default_value = 1.2
    nt.links.new(em.outputs[0], om.inputs["Surface"])
    cu.materials.append(mat)
    ob = bpy.data.objects.new("FlyPath", cu)
    sc.collection.objects.link(ob)
    for o in bpy.data.objects:
        if o.get("is_ceiling"):
            o.hide_render = True
    sc.animation_data_clear()
    sc.camera = bpy.data.objects["Cam_Top"]
    sc.view_settings.exposure = 2.6
    sc.cycles.samples = 48
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1240, 1300, 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(OUT, "path.png")
    sc.frame_set(1)
    bpy.ops.render.render(write_still=True)


def gpu():
    """A fresh Blender renders on the CPU unless told otherwise: pick the platform's GPU backend
    (Metal on a Mac; OptiX on an RTX card, else CUDA, HIP or oneAPI) and enable only its GPUs."""
    prefs = bpy.context.preferences.addons["cycles"].preferences
    order = ["METAL"] if sys.platform == "darwin" else ["OPTIX", "CUDA", "HIP", "ONEAPI"]
    for kind in order:
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        devs = [d for d in prefs.devices if d.type == kind]
        if not devs or (kind == "OPTIX" and not any("RTX" in d.name for d in devs)):
            continue
        hybrid = os.environ.get("FLY_CPU", "0") == "1" and kind != "METAL"   # FLY_CPU=1: the CPU joins in (about 2% faster on a GTX 1060)
        for d in prefs.devices:
            d.use = d.type == kind or (hybrid and d.type == "CPU")
        bpy.context.scene.cycles.device = "GPU"
        return kind, [d.name for d in prefs.devices if d.use]
    return "CPU", []


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["plan"]
    mode = argv[0]
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    pos = setup()
    print("FLY frames", len(pos), "seconds", round(len(pos) / FPS, 1))
    if mode == "plan":
        return plan(pos)
    if mode == "passes":
        return passes()
    sc.view_settings.view_transform = "AgX"
    r = sc.render
    r.use_overwrite, r.use_placeholder = False, False            # a stopped render picks up where it left off
    r.resolution_percentage = 100
    if mode == "preview":
        r.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in type(r).bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE_NEXT"
        try:
            sc.eevee.use_raytracing = True
            sc.eevee.taa_render_samples = 12
        except Exception:  # noqa: BLE001
            pass
        r.resolution_x, r.resolution_y = 640, 360
        r.image_settings.file_format = "JPEG"
        r.image_settings.quality = 88
        sc.frame_step = 2
        r.filepath = os.path.join(OUT, "preview_frames", "f_")
    else:
        r.engine = "CYCLES"
        cy = sc.cycles
        print("FLY device", gpu())
        cy.samples = int(os.environ.get("FLY_SAMPLES", "128"))
        cy.use_adaptive_sampling, cy.adaptive_threshold = True, 0.02
        cy.use_denoising = True
        r.use_persistent_data = True                             # keep the scene on the GPU between frames
        r.resolution_x, r.resolution_y = 2560, 1440
        r.image_settings.file_format = "PNG"
        r.image_settings.color_depth = "8"
        r.filepath = os.path.join(OUT, "frames", "f_")
    if len(argv) >= 3:
        sc.frame_start, sc.frame_end = int(argv[1]), int(argv[2])
    claim = os.environ.get("FLY_CLAIM")
    if claim:
        # sharing the render with another machine: the FLY_CLAIM command hands out one frame at a
        # time (prints its number, or nothing when none is left) and marks it taken on the other side
        import subprocess
        while True:
            got = subprocess.run(claim, shell=True, capture_output=True, text=True).stdout.strip()
            if not got.isdigit():
                print("FLY no frame left to claim", got)
                return
            sc.frame_set(int(got))
            r.filepath = os.path.join(OUT, "frames", "f_{:04d}.png".format(int(got)))
            print("FLY claimed frame", got, flush=True)
            bpy.ops.render.render(write_still=True)
    if sys.platform == "darwin":
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "out", "apartment_flythrough.blend"), copy=True)
    bpy.ops.render.render(animation=True)


# ------------------------------------------------------------------ passes ---
def turbo(x):
    """Google's Turbo colour map (polynomial fit by Anton Mikhailov), x in 0..1 -> RGB 0..1."""
    import numpy as np
    x = np.clip(x, 0.0, 1.0)
    r = 0.13572138 + x * (4.61539260 + x * (-42.66032258 + x * (132.13108234 + x * (-152.94239396 + x * 59.28637943))))
    g = 0.09140261 + x * (2.19418839 + x * (4.84296658 + x * (-14.18503333 + x * (4.27729857 + x * 2.82956604))))
    b = 0.10667330 + x * (12.64194608 + x * (-60.58204836 + x * (110.36276771 + x * (-89.90310912 + x * 27.34824973))))
    return np.clip(np.stack([r, g, b], -1), 0.0, 1.0)


def passes():
    """One frame per room (the middle of the longest stretch spent in it): a depth map in Turbo
    colours (near = blue, far = red, per-frame range) and an object map (one flat colour per object),
    from Cycles' Depth and Object Index passes, so alpha cut-outs and glass behave as in the film."""
    import numpy as np
    import OpenImageIO as oiio
    sc = bpy.context.scene
    r, cy, vl = sc.render, sc.cycles, bpy.context.view_layer
    pick = {}
    i = 0
    while i < len(ROOM_AT):
        j = i
        while j < len(ROOM_AT) and ROOM_AT[j] == ROOM_AT[i]:
            j += 1
        if j - i > pick.get(ROOM_AT[i], (0, 0))[1]:
            pick[ROOM_AT[i]] = ((i + j) // 2 + 1, j - i)
        i = j
    r.engine = "CYCLES"
    print("FLY device", gpu())
    cy.samples, cy.use_adaptive_sampling, cy.use_denoising = 1, False, False
    cy.max_bounces = cy.diffuse_bounces = cy.glossy_bounces = cy.transmission_bounces = 0
    r.filter_size = 0.01                                          # one sample, no blending: object edges stay crisp
    r.resolution_x, r.resolution_y, r.resolution_percentage = 2560, 1440, 100
    vl.use_pass_z = vl.use_pass_object_index = True
    for k, o in enumerate(bpy.data.objects, 1):
        o.pass_index = k
    try:
        r.image_settings.media_type = "MULTI_LAYER_IMAGE"              # Blender 5
        r.image_settings.file_format = "OPEN_EXR"
    except (AttributeError, TypeError):
        r.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    r.image_settings.color_depth = "32"
    d = os.path.join(OUT, "passes")
    os.makedirs(d, exist_ok=True)
    for room, (f, _) in pick.items():
        sc.frame_set(f)
        exr = os.path.join(d, "_tmp.exr")
        r.filepath = exr
        bpy.ops.render.render(write_still=True)
        ch = {}
        for part in range(oiio.ImageBuf(exr).nsubimages):            # each pass may be its own EXR part
            img = oiio.ImageBuf(exr, part, 0)
            spec = img.spec()
            px = img.get_pixels(oiio.FLOAT).reshape(spec.height, spec.width, -1)
            for k, n in enumerate(spec.channelnames):
                ch[n] = px[..., k]
        z = next(v for n, v in ch.items() if n.endswith("Depth.Z"))
        idx = next(v for n, v in ch.items() if n.endswith(("IndexOB.X", "Object Index.X"))).round().astype(np.int64)
        hit = (z < 1e5) & (idx > 0)
        lo, hi = np.percentile(z[hit], 0.5), np.percentile(z[hit], 99.5)
        dep = turbo((z - lo) / max(hi - lo, 1e-6))
        dep[~hit] = 0.0
        h = (idx * 0.6180339887) % 1.0                         # golden-ratio hues: neighbouring ids look different
        sat = 0.55 + 0.4 * ((idx * 7919) % 5) / 4
        val = 0.6 + 0.4 * ((idx * 104729) % 3) / 2
        k6 = (h * 6.0)[..., None]
        rgb = np.clip(np.abs(((k6 + np.array([0.0, 4.0, 2.0])) % 6.0) - 3.0) - 1.0, 0.0, 1.0)
        obj = val[..., None] * (1.0 - sat[..., None] + sat[..., None] * rgb)
        obj[idx <= 0] = 0.0
        for tag, a in (("depth", dep), ("objects", obj)):
            out = oiio.ImageBuf(oiio.ImageSpec(spec.width, spec.height, 3, oiio.UINT8))
            out.set_pixels(oiio.ROI(0, spec.width, 0, spec.height, 0, 1, 0, 3), (a * 255 + 0.5).astype(np.uint8))
            out.write(os.path.join(d, "{}_f{:04d}_{}.png".format(room, f, tag)))
        print("FLY passes", room, f, "depth {:.2f}-{:.2f} m".format(lo, hi), "objects", len(np.unique(idx[hit])))
        os.remove(exr)


main()

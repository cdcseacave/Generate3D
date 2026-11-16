"""Fly-through of the whole flat. Runs in its own Blender, not through the MCP bridge:

    blender -b out/apartment_scene.blend -P apartment/flythrough.py -- plan
    blender -b out/apartment_scene.blend -P apartment/flythrough.py -- preview
    blender -b out/apartment_scene.blend -P apartment/flythrough.py -- final [first last]

The route is one loop of the hallway, stepping into each room as its door comes up. Inside a
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
ROOM_EV = {"living": 3.3, "kitchen": 3.1, "hall": 1.7, "bedroom": 3.2, "office": 3.0, "bath": 1.0}
# (room, x where the route crosses the wall, wall y, +1 if the room is north of the hall)
DOORS = [("living", 2.7, S.YH0, -1), ("kitchen", 7.8, S.YH0, -1), ("bath", 8.5, S.YH1, 1),
         ("office", 5.35, S.YH1, 1), ("bedroom", 2.96, S.YH1, 1)]


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
    loops = {r: circuit(dg, r) for r in S.ROOMS}
    hall, hc = loops["hall"]
    start = nearest(hall, (0.9, (S.YH0 + S.YH1) / 2))          # by the entrance door
    order = hall[start:] + hall[:start]
    stops = {}
    for room, dx, wy, sgn in DOORS:                             # where on the hall loop each door is passed
        side = [i for i, p in enumerate(order) if (p[1] - hc[1]) * sgn > 0]
        stops[min(side, key=lambda i: abs(order[i][0] - dx))] = (room, dx, wy, sgn)
    out = []

    def across(p, c, room):                                     # look through the middle of the room at the far side
        out.append((p[0], p[1], 2 * c[0] - p[0], 2 * c[1] - p[1], room))

    def ahead(pts, room):                                       # look where you are going
        for i, p in enumerate(pts):
            q = pts[min(i + 8, len(pts) - 1)]
            d = (q[0] - p[0], q[1] - p[1]) if q != p else (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            out.append((p[0], p[1], p[0] + d[0] * 50, p[1] + d[1] * 50, room))

    for i, p in enumerate(order):
        across(p, hc, "hall")
        if i in stops:
            room, dx, wy, sgn = stops[i]
            loop, c = loops[room]
            d_hall, d_room = (dx, wy - sgn * 0.45), (dx, wy + sgn * 0.55)
            k = nearest(loop, d_room)
            ahead(line(p, d_hall) + line(d_hall, d_room), "hall")
            ahead(line(d_room, loop[k]), room)
            for q in loop[k:] + loop[:k + 1]:
                across(q, c, room)
            ahead(line(loop[k], d_room) + line(d_room, d_hall), room)
            ahead(line(d_hall, p), "hall")
    across(order[0], hc, "hall")
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["plan"]
    mode = argv[0]
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    pos = setup()
    print("FLY frames", len(pos), "seconds", round(len(pos) / FPS, 1))
    if mode == "plan":
        return plan(pos)
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
        cy.samples = int(os.environ.get("FLY_SAMPLES", "160"))
        cy.use_adaptive_sampling, cy.adaptive_threshold = True, 0.02
        cy.use_denoising = True
        r.use_persistent_data = True                             # keep the scene on the GPU between frames
        r.resolution_x, r.resolution_y = 2560, 1440
        r.image_settings.file_format = "PNG"
        r.image_settings.color_depth = "8"
        r.filepath = os.path.join(OUT, "frames", "f_")
    if len(argv) >= 3:
        sc.frame_start, sc.frame_end = int(argv[1]), int(argv[2])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "out", "apartment_flythrough.blend"), copy=True)
    bpy.ops.render.render(animation=True)


main()

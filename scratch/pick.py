import bpy
from mathutils import Vector
sc = bpy.context.scene
cam = bpy.data.objects["Cam_living_room_01"]
dg = bpy.context.evaluated_depsgraph_get()
tr, br, bl, tl = [Vector(v) for v in cam.data.view_frame(scene=sc)]
out = {}
for name, (px, py) in {"seat_mid": (930, 900), "seat_right": (1150, 800), "arm_top": (600, 740), "arm_front": (560, 900), "chaise": (1250, 760),
                       "rug_a": (1650, 1030), "rug_b": (1250, 1060), "rug_c": (1800, 990), "cushion": (860, 760)}.items():
    u, v = px / 1920.0, 1.0 - py / 1080.0
    p = bl + (br - bl) * u + (tl - bl) * v
    d = (cam.matrix_world.to_3x3() @ p).normalized()
    hit, loc, nor, idx, ob, mw = sc.ray_cast(dg, cam.matrix_world.translation, d)
    out[name] = [ob.name if ob else None, [round(c, 3) for c in loc], [m.material.name for m in ob.material_slots][:2] if ob else None]
result = out

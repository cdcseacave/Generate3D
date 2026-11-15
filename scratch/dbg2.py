import bpy, sys, numpy as np
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.render as R
def load(p):
    img = bpy.data.images.load(p); w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(a); bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[:, :, :3]
res = {}
D = "/Users/dancostin/Downloads/Generate3D/scratch/"
mixes = {}
for name in ("Fabric_Sofa", "Carpet Grey"):
    nt = bpy.data.materials[name].node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mixes[name] = (nt, b.inputs["Base Color"].links[0].from_node)
    res[name + "_B"] = [round(v, 3) for v in mixes[name][1].inputs[7].default_value][:3]
    a = mixes[name][1].inputs[6]
    res[name + "_Asrc"] = a.links[0].from_node.type if a.links else [round(v, 3) for v in a.default_value][:3]
R.render("Cam_living_room_01", D + "dbg_on.exr", 48, (640, 360))
saved = {}
for name, (nt, mx) in mixes.items():
    l = mx.inputs[0].links[0]; saved[name] = l.from_socket; nt.links.remove(l); mx.inputs[0].default_value = 0.0
R.render("Cam_living_room_01", D + "dbg_off.exr", 48, (640, 360))
for name, (nt, mx) in mixes.items():
    nt.links.new(saved[name], mx.inputs[0])
bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1920, 1080
on, off = load(D + "dbg_on.exr"), load(D + "dbg_off.exr")
ratio = (on.mean(axis=2) + 1e-4) / (off.mean(axis=2) + 1e-4)
h, w = ratio.shape
def box(cx, cy, r=6):   # top-left pixel coords
    y = h - 1 - cy
    return ratio[y - r:y + r, cx - r:cx + r]
res["seat"] = [round(float(box(310, 303).min()), 2), round(float(box(310, 303).max()), 2)]
res["rug"] = [round(float(box(543, 340).min()), 2), round(float(box(543, 340).max()), 2)]
res["global"] = [round(float(np.percentile(ratio, 0.5)), 2), round(float(np.percentile(ratio, 99.5)), 2)]
result = res

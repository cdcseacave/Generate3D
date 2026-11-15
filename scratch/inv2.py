import bpy, json, sys
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.core as C
from mathutils import Vector
C.reset_scene()
out = {}
for fname, cols in (("loft.blend", ["Bad room", "Living", "Kitchen", "Collection", "Collection.001"]),
                    ("flat-archiviz.blend", ["Sofa", "Chair", "Dinner", "Kitchen", "Furniture", "Details", "Library", "Lamp", "Living"])):
    path = "/Users/dancostin/Downloads/Generate3D/assets/demo/" + fname
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [c for c in cols if c in src.collections]
    for col in dst.collections:
        if col is None:
            continue
        bpy.context.scene.collection.children.link(col)
    bpy.context.view_layer.update()
    for col in dst.collections:
        if col is None:
            continue
        objs = [o for o in col.all_objects if o.type == "MESH"]
        if not objs:
            out[fname + "/" + col.name] = "no meshes ({} objs)".format(len(col.all_objects))
            continue
        pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        big = sorted(objs, key=lambda o: -max(o.dimensions))[:14]
        out[fname + "/" + col.name] = {"n": len(objs), "lo": [round(v, 2) for v in lo], "hi": [round(v, 2) for v in hi],
                                       "tris": sum(len(o.data.polygons) for o in objs),
                                       "big": ["{} {:.2f}x{:.2f}x{:.2f}".format(o.name, *o.dimensions) for o in big],
                                       "children": [c.name for c in col.children]}
open("/Users/dancostin/Downloads/Generate3D/scratch/inv2.json", "w").write(json.dumps(out, indent=1))
result = {"groups": len(out)}

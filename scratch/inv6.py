import bpy, json, sys
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.core as C
from mathutils import Vector
path = "/Users/dancostin/Downloads/Generate3D/assets/demo/flat-archiviz.blend"
with bpy.data.libraries.load(path, link=False) as (src, dst):
    dst.collections = ["Kitchen"]
col = dst.collections[0]
rows = []
for o in col.all_objects:
    if o.type != "MESH": 
        rows.append([o.name, o.type]); continue
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = [round(min(p[i] for p in pts), 2) for i in range(3)]; hi = [round(max(p[i] for p in pts), 2) for i in range(3)]
    rows.append([o.name, lo, hi, len(o.data.polygons), [s.material.name for s in o.material_slots if s.material][:3]])
for o in list(col.all_objects):
    bpy.data.objects.remove(o)
bpy.data.collections.remove(col)
open("/Users/dancostin/Downloads/Generate3D/scratch/inv6.json", "w").write(json.dumps(rows))
ph = {}
for aid in ("metal_office_desk", "classic_laptop", "Television_01"):
    try:
        parts = C.load_asset(aid)
        ph[aid] = [[p["name"], [round(v, 2) for v in (p["hi"] - p["lo"])]] for p in parts][:8]
    except Exception as ex:
        ph[aid] = str(ex)[:80]
result = {"n": len(rows), "ph": ph}

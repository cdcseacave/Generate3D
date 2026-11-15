import bpy, json
out = {}
for nm in ("SofaSet", "DiningSet"):
    e = bpy.data.objects.get(nm)
    rows = []
    for o in (e.children_recursive if e else []):
        if o.type != "MESH": continue
        mats = []
        for s in o.material_slots:
            m = s.material
            if not m: continue
            tex = [n.image.name for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image] if m.node_tree else []
            mats.append([m.name, tex[:4]])
        w = o.matrix_world.translation
        rows.append([o.name, [round(v, 2) for v in w], [round(v, 2) for v in o.dimensions], len(o.data.polygons), mats])
    out[nm] = rows
open("/Users/dancostin/Downloads/Generate3D/scratch/inv3.json", "w").write(json.dumps(out, indent=0))
result = {"n": {k: len(v) for k, v in out.items()}}

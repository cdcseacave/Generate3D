import bpy, json
path = "/Users/dancostin/Downloads/Generate3D/assets/demo/flat-archiviz.blend"
with bpy.data.libraries.load(path, link=False) as (src, dst):
    cols = list(src.collections); objs = list(src.objects)
out = {"collections": cols, "n_objects": len(objs), "objects": sorted(objs)}
open("/Users/dancostin/Downloads/Generate3D/scratch/inv5.json", "w").write(json.dumps(out))
result = {"cols": len(cols), "objs": len(objs)}

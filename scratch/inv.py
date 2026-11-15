import bpy, re, json
out = {}
for name in ("flat-archiviz.blend", "loft.blend"):
    path = "/Users/dancostin/Downloads/Generate3D/assets/demo/" + name
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        objs = list(src.objects)
        cols = list(src.collections)
        texts = list(src.texts)
        scenes = list(src.scenes)
        dst.texts = texts
    keys = r"bed|pillow|duvet|blanket|sheet|matt|toilet|wc|sink|basin|bath|tub|faucet|tap|towel|kitchen|cabinet|oven|fridge|stove|hood|chair|sofa|couch|table|lamp|curtain|rug|carpet|plant|book|shoe|coat|jacket|mirror|shower|cushion|wardrobe|closet"
    hits = sorted(o for o in objs if re.search(keys, o, re.I))
    txt = {t.name: t.as_string()[:400] for t in dst.texts if t is not None}
    out[name] = {"objects": len(objs), "collections": cols[:80], "scenes": scenes, "hits": len(hits), "hit_names": hits[:140], "texts": txt}
    for t in dst.texts:
        if t is not None:
            bpy.data.texts.remove(t)
open("/Users/dancostin/Downloads/Generate3D/scratch/inv.json", "w").write(json.dumps(out, indent=1))
result = {k: {"objects": v["objects"], "collections": len(v["collections"]), "hits": v["hits"], "texts": list(v["texts"])} for k, v in out.items()}

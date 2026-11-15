import bpy, numpy as np, json
cfg = json.load(open("/Users/dancostin/Downloads/Generate3D/scratch/crop.json"))
img = bpy.data.images.load(cfg["src"])
w, h = img.size
px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
px = px.reshape(h, w, 4)
x0, y0, x1, y1 = cfg["box"]            # top-left origin
sub = px[h - y1:h - y0, x0:x1]
k = cfg.get("zoom", 2)
sub = np.repeat(np.repeat(sub, k, axis=0), k, axis=1)
out = bpy.data.images.new("crop", sub.shape[1], sub.shape[0])
out.pixels.foreach_set(np.ascontiguousarray(sub).ravel())
out.filepath_raw = cfg["dst"]; out.file_format = "PNG"; out.save()
bpy.data.images.remove(out); bpy.data.images.remove(img)
result = {"size": [sub.shape[1], sub.shape[0]]}

import sys, os, json, xml.etree.ElementTree as ET
root = "assets/scenes"
out = {}
for name in sys.argv[1:]:
    d = os.path.join(root, name)
    r = ET.parse(os.path.join(d, "scene_v0.6.xml")).getroot()
    agg = {}
    for s in r.iter("shape"):
        fn = next((k.get("value") for k in s if k.tag == "string" and k.get("name") == "filename"), None)
        ref = next((k.get("id") for k in s if k.tag == "ref"), None) or "(inline:%s)" % ("emitter" if s.find("emitter") is not None else "bsdf")
        if not fn or not fn.endswith(".obj"):
            continue
        M = [float(v) for v in s.find("transform").find("matrix").get("value").replace(",", " ").split()]
        lo, hi, n = [1e9] * 3, [-1e9] * 3, 0
        with open(os.path.join(d, fn)) as fh:
            for line in fh:
                if line.startswith("v "):
                    x, y, z = map(float, line.split()[1:4])
                    X = M[0] * x + M[1] * y + M[2] * z + M[3]; Y = M[4] * x + M[5] * y + M[6] * z + M[7]; Z = M[8] * x + M[9] * y + M[10] * z + M[11]
                    p = (X, -Z, Y)                       # Mitsuba Y-up -> Blender Z-up
                    for i in range(3):
                        lo[i] = min(lo[i], p[i]); hi[i] = max(hi[i], p[i])
                    n += 1
        a = agg.setdefault(ref, {"lo": lo[:], "hi": hi[:], "n": 0, "shapes": 0})
        for i in range(3):
            a["lo"][i] = min(a["lo"][i], lo[i]); a["hi"][i] = max(a["hi"][i], hi[i])
        a["n"] += n; a["shapes"] += 1
    out[name] = agg
    print("==", name)
    for k, a in sorted(agg.items(), key=lambda kv: -(kv[1]["hi"][0] - kv[1]["lo"][0]) * (kv[1]["hi"][1] - kv[1]["lo"][1])):
        print("  %-22s x %6.2f..%6.2f  y %6.2f..%6.2f  z %5.2f..%5.2f  shapes %3d verts %6d" % (k[:22], a["lo"][0], a["hi"][0], a["lo"][1], a["hi"][1], a["lo"][2], a["hi"][2], a["shapes"], a["n"]))
json.dump(out, open("scratch/scene_bbox.json", "w"))

import sys, json, time, importlib
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.render, apartment.build as B
importlib.reload(apartment.render)
keep = dict(B._EXPOSURE)
importlib.reload(B)
B._EXPOSURE.update(keep)
cfg = json.load(open("/Users/dancostin/Downloads/Generate3D/scratch/refinish.json"))
t = time.time()
done = B.refinish(cfg.get("prefix", ""), **cfg.get("kw", {}))
result = {"n": len(done), "secs": round(time.time() - t, 1)}

import sys, json, time
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.build as B
cfg = json.load(open("/Users/dancostin/Downloads/Generate3D/scratch/final.json"))
t = time.time()
B.shot(cfg["view"], "final")
result = {"view": cfg["view"], "secs": round(time.time() - t, 1)}

import sys, importlib, json, time
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.core, apartment.shell, apartment.render, apartment.art, apartment.props, apartment.fixtures, apartment.build as B
cfg = json.load(open("/Users/dancostin/Downloads/Generate3D/scratch/run.json"))
if cfg.get("reload", True):
    keep = dict(B._EXPOSURE) if hasattr(B, "_EXPOSURE") else {}
    for m in (apartment.core, apartment.shell, apartment.render, apartment.art, apartment.props, apartment.fixtures, B):
        importlib.reload(m)
    if not cfg.get("build", True):
        B._EXPOSURE.update(keep)
t = time.time()
result = {}
if cfg.get("build", True):
    result["build"] = B.build(furnish=cfg.get("furnish", True))
for v in cfg.get("shots", []):
    B.shot(v, cfg.get("quality", "preview"), cfg.get("exposure"))
if cfg.get("save"):
    result["saved"] = B.save()
result["exposure"] = {k: round(v, 2) for k, v in B._EXPOSURE.items()}
result["secs"] = round(time.time() - t, 1)

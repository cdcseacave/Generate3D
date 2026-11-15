import sys, time
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.build as B
t = time.time()
r = B.check_floating()
result = {"checked": r["checked"], "flagged": len(r["flagged"]), "secs": round(time.time() - t, 1),
          "items": ["{} {} {} @({},{},{})".format(*i) for i in r["flagged"][:70]]}

import sys
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.build as B
for v, b in {"office_01": -0.25, "bedroom_01": -0.15, "living_room_01": -0.1}.items():
    B._EXPOSURE[v] += b
result = {"exposure": {k: round(v, 2) for k, v in B._EXPOSURE.items()}}

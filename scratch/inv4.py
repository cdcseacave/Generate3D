import bpy
out = {}
m = bpy.data.materials.get("Fabric_Sofa")
rows = []
for n in m.node_tree.nodes:
    ins = {i.name: (round(i.default_value, 3) if isinstance(i.default_value, float) else None) for i in n.inputs if hasattr(i, "default_value") and not i.is_linked and isinstance(i.default_value, float)}
    rows.append([n.type, n.name, getattr(getattr(n, "image", None), "name", None), ins])
links = [[l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name] for l in m.node_tree.links]
out["nodes"] = rows; out["links"] = links
e = bpy.data.objects["DiningSet"]
out["parents"] = {o.name: (o.parent.name if o.parent else None) for o in e.children_recursive}
import json
open("/Users/dancostin/Downloads/Generate3D/scratch/inv4.json", "w").write(json.dumps(out))
result = {"ok": 1}

import bpy, sys
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.render as R
m = bpy.data.materials["Carpet Grey"]
nt = m.node_tree
b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
mx = b.inputs["Base Color"].links[0].from_node
old = tuple(mx.inputs[7].default_value)
mx.inputs[7].default_value = (5.0, 0.0, 0.0, 1.0)
fac = mx.inputs[0].links[0].from_node if mx.inputs[0].links else None
info = {"mix_type": mx.type, "blend": mx.blend_type, "dtype": mx.data_type, "fac_from": fac.type + ":" + getattr(fac, "operation", "") if fac else None,
        "A_linked": bool(mx.inputs[6].links), "out_links": [l.to_node.type + "." + l.to_socket.name for l in mx.outputs[2].links]}
R.render("Cam_living_room_01", "/Users/dancostin/Downloads/Generate3D/scratch/dbg.png", 24, (640, 360), exposure=2.7)
mx.inputs[7].default_value = old
bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1920, 1080
result = info

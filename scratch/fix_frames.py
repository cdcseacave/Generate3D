"""Window frames are built from overlapping boxes; where one box's face lies inside another,
CUDA renders it black (Metal happened not to). Union each frame into one clean solid."""
import bpy
empty = bpy.data.collections.new("_none")
done = []
for o in bpy.data.objects:
    if o.type == "MESH" and "window" in o.name and o.name.endswith("_frame"):
        md = o.modifiers.new("Union", "BOOLEAN")
        md.operation, md.operand_type, md.solver = "UNION", "COLLECTION", "EXACT"
        md.collection, md.use_self = empty, True
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier=md.name)
        done.append((o.name, len(o.data.polygons)))
bpy.data.collections.remove(empty)
print("FIXED", done)
bpy.ops.wm.save_mainfile()

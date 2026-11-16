"""Contact sheet of the downloaded scanned objects: grid seen from the -Y side, 50 degrees down.
Row-major from the far-left; +X is to the right, +Y away from the viewer."""
import sys, os, math, importlib
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import bpy
import apartment.core as C
import apartment.gso as G
importlib.reload(G)
C.reset_scene()
C._MATS.clear()
G._PROTO.clear()
names = sorted(os.listdir(G.DIR))
cols, cell = 10, 0.55
sc = bpy.context.scene
for i, n in enumerate(names):
    r, c = divmod(i, cols)
    G.put(n, c * cell, -r * cell * 1.15, 0.0)
rows = (len(names) + cols - 1) // cols
C.box("Ground", (cols * cell + 1, rows * cell * 1.15 + 1, 0.01), ((cols - 1) * cell / 2, -(rows - 1) * cell * 1.15 / 2, -0.01),
      C.mat("SheetGround", "#8a8a8a", rough=0.9))
cam = bpy.data.objects.new("SheetCam", bpy.data.cameras.new("SheetCam"))
sc.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = cols * cell + 0.3
cx, cy = (cols - 1) * cell / 2, -(rows - 1) * cell * 1.15 / 2
a = math.radians(50)
cam.location = (cx, cy - 10 * math.sin(a), 0.1 + 10 * math.cos(a))
cam.rotation_euler = (a, 0, 0)
sc.camera = cam
sun = bpy.data.objects.new("SheetSun", bpy.data.lights.new("SheetSun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(40), 0, math.radians(-30))
sc.collection.objects.link(sun)
w = bpy.data.worlds.new("SheetWorld")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = w
sc.render.engine = "CYCLES"
sc.cycles.samples = 24
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 2000, 1400
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "JPEG"
sc.render.filepath = "/Users/dancostin/Downloads/Generate3D/scratch/gso_sheet.jpg"
bpy.ops.render.render(write_still=True)
sc.render.image_settings.file_format = "PNG"
result = {"n": len(names), "names": {i: n[:30] for i, n in enumerate(names)}}

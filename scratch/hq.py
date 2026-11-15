import sys, time, bpy
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.build as B
sc = bpy.context.scene
old = (B.FINAL_SAMPLES, sc.cycles.adaptive_threshold)
B.FINAL_SAMPLES = 1400
sc.cycles.adaptive_threshold = 0.006
t = time.time()
B.shot("kitchen_02", "final")
B.FINAL_SAMPLES, sc.cycles.adaptive_threshold = old
result = {"secs": round(time.time() - t, 1)}

import sys, importlib
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.render as R, apartment.build as B
import bpy
keep = dict(B._EXPOSURE)
importlib.reload(R)
importlib.reload(B)
B._EXPOSURE.update(keep)
sc = bpy.context.scene
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "8"
result = {"depth": sc.render.image_settings.color_depth, "exposures": {k: round(v, 2) for k, v in B._EXPOSURE.items()}, "frame": sc.frame_current,
          "keyed": [round(sc.animation_data.action.fcurves[0].evaluate(f), 2) for f in range(1, 13)] if sc.animation_data and sc.animation_data.action and hasattr(sc.animation_data.action, "fcurves") and len(sc.animation_data.action.fcurves) else "n/a"}

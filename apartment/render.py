"""World lighting, cameras and Cycles settings."""
import json
import math
import os

import bpy
from mathutils import Vector

from . import core as C

# sky name -> (HDRI file, compass azimuth the sun should come from: 180 = south, 270 = west)
SKIES = {
    "afternoon": ("syferfontein_18d_clear_puresky_4k.hdr", 222.0),
    "midday": ("kloofendal_48d_partly_cloudy_puresky_4k.hdr", 205.0),
}


def _hdri_sun_angle(img, path):
    """Angle (radians, atan2(y, x)) of the brightest region of an equirect HDRI in
    Blender's default environment mapping. Cached next to the file."""
    cache = path + ".sun.json"
    if os.path.exists(cache):
        return json.load(open(cache))["angle"]
    import numpy as np
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    lum = px.reshape(h, w, 4)[:, :, :3].sum(axis=2)
    b = 8
    lum = lum[: h // b * b, : w // b * b].reshape(h // b, b, w // b, b).mean(axis=(1, 3))
    r, c = np.unravel_index(np.argmax(lum), lum.shape)
    u = (c + 0.5) / lum.shape[1]
    v = (r + 0.5) / lum.shape[0]
    phi = (u - 0.5) * 2 * math.pi
    th = (v - 0.5) * math.pi
    d = (math.cos(phi) * math.cos(th), -math.sin(phi) * math.cos(th), math.sin(th))
    ang = math.atan2(d[1], d[0])
    json.dump({"angle": ang, "elevation_deg": math.degrees(th)}, open(cache, "w"))
    return ang


def setup_world(strength=1.0, sky="afternoon", azimuth_deg=None, camera_boost=3.0, backdrop="balcony",
                backdrop_rot=292.0, backdrop_strength=4.0, backdrop_lift=0.17):
    fname, default_az = SKIES[sky]
    path = os.path.join(C.ASSETS, "hdris", fname)
    world = bpy.data.worlds.new("Sky")
    try:
        world.use_nodes = True
    except Exception:  # noqa: BLE001
        pass
    bpy.context.scene.world = world
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(path, check_existing=True)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    az = math.radians(default_az if azimuth_deg is None else azimuth_deg)
    want = math.atan2(math.cos(az), math.sin(az))  # north = +Y, east = +X
    have = _hdri_sun_angle(env.image, path)
    mp.inputs["Rotation"].default_value = (0, 0, have - want)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    # The view through the windows is exposed for the interior, so the sky a camera
    # sees is lifted towards white; lighting and reflections keep the true values.
    lp = nt.nodes.new("ShaderNodeLightPath")
    bpath = os.path.join(C.ASSETS, "backdrops", backdrop + ".jpg") if backdrop else None
    if bpath and os.path.exists(bpath):
        # What the camera sees through the glass is a photographed neighbourhood
        # panorama; light and reflections still come from the HDRI sky above.
        # The panorama has one good half (fields, trees) and one bad half (the house it
        # was shot from). Directions pointing north-east are mirrored back onto the good
        # half, with the seam (ESE / WNW) placed where no window looks.
        nrm = (math.cos(math.radians(60.0)), math.sin(math.radians(60.0)), 0.0)
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = nrm
        nt.links.new(tc.outputs["Generated"], dot.inputs[0])
        pos = nt.nodes.new("ShaderNodeMath")
        pos.operation = "MAXIMUM"
        pos.inputs[1].default_value = 0.0
        nt.links.new(dot.outputs["Value"], pos.inputs[0])
        twice = nt.nodes.new("ShaderNodeMath")
        twice.operation = "MULTIPLY"
        twice.inputs[1].default_value = 2.0
        nt.links.new(pos.outputs[0], twice.inputs[0])
        scl = nt.nodes.new("ShaderNodeVectorMath")
        scl.operation = "SCALE"
        scl.inputs[0].default_value = nrm
        nt.links.new(twice.outputs[0], scl.inputs["Scale"])
        refl = nt.nodes.new("ShaderNodeVectorMath")
        refl.operation = "SUBTRACT"
        nt.links.new(tc.outputs["Generated"], refl.inputs[0])
        nt.links.new(scl.outputs["Vector"], refl.inputs[1])
        mp2 = nt.nodes.new("ShaderNodeMapping")
        mp2.inputs["Rotation"].default_value = (0, 0, math.radians(backdrop_rot))
        mp2.inputs["Location"].default_value = (0, 0, backdrop_lift)     # look slightly up into the panorama: an upper floor sees tree crowns and sky, not the ground
        nt.links.new(refl.outputs["Vector"], mp2.inputs["Vector"])
        env2 = nt.nodes.new("ShaderNodeTexEnvironment")
        env2.image = bpy.data.images.load(bpath, check_existing=True)
        nt.links.new(mp2.outputs[0], env2.inputs["Vector"])
        bg2 = nt.nodes.new("ShaderNodeBackground")
        bg2.inputs["Strength"].default_value = backdrop_strength
        nt.links.new(env2.outputs["Color"], bg2.inputs["Color"])
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
        nt.links.new(bg.outputs[0], mix.inputs[1])
        nt.links.new(bg2.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0])
        return world
    boost = nt.nodes.new("ShaderNodeMath")
    boost.operation = "MULTIPLY_ADD"
    boost.inputs[1].default_value = strength * (camera_boost - 1.0)
    boost.inputs[2].default_value = strength
    nt.links.new(lp.outputs["Is Camera Ray"], boost.inputs[0])
    nt.links.new(boost.outputs[0], bg.inputs["Strength"])
    nt.links.new(bg.outputs[0], out.inputs[0])
    return world


def setup_cycles(samples=96, res=(960, 640), exposure=0.0, white_balance=5200.0):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "METAL"
    cy = sc.cycles
    cy.device = "GPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.012
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
        cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    except Exception:  # noqa: BLE001
        pass
    cy.max_bounces = 12
    cy.diffuse_bounces = 6
    cy.glossy_bounces = 6
    cy.transmission_bounces = 12
    cy.transparent_max_bounces = 12
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.sample_clamp_indirect = 4.0
    cy.blur_glossy = 0.5
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.render.film_transparent = False
    vs = sc.view_settings
    for vt in ("AgX", "Filmic"):
        try:
            vs.view_transform = vt
            break
        except Exception:  # noqa: BLE001
            continue
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "AgX - Base Contrast", "None"):
        try:
            vs.look = look
            break
        except Exception:  # noqa: BLE001
            continue
    vs.exposure = exposure
    try:  # neutralise part of the warm cast from low sun + tungsten lamps, as a camera would
        vs.use_white_balance = True
        vs.white_balance_temperature = white_balance
        vs.white_balance_tint = 10.0
    except Exception:  # noqa: BLE001
        pass


def camera(name, loc, target, lens=24.0, fstop=None, sensor=36.0, col=None, handheld=True):
    """Hand-held camera at eye height, pointed straight at the target the way a person
    holds a phone: the whole tilt is real pitch (verticals converge; no architectural
    lens shift) and the horizon is off by up to a few degrees, differently per shot."""
    import zlib
    from mathutils import Quaternion
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = sensor
    cam.clip_start = 0.05
    cam.clip_end = 100
    obj = bpy.data.objects.new(name, cam)
    (col or bpy.context.scene.collection).objects.link(obj)
    obj.location = loc
    d = Vector(target) - Vector(loc)
    flat = Vector((d.x, d.y, 0.0))
    pitch_share = 1.0 if handheld else 0.0
    aim = Vector((d.x, d.y, d.z * pitch_share))
    q = aim.to_track_quat("-Z", "Y")
    if handheld:
        h = zlib.crc32(name.encode()) % 1000 / 1000.0
        roll = math.radians((h - 0.5) * 6.4)                 # about +/- 3.2 degrees
        q = q @ Quaternion((0.0, 0.0, 1.0), roll)
    obj.rotation_euler = q.to_euler()
    cam.shift_y = lens * (d.z * (1.0 - pitch_share) / max(flat.length, 1e-6)) / sensor
    if fstop:
        cam.dof.use_dof = True
        cam.dof.focus_distance = d.length
        cam.dof.aperture_fstop = fstop
    return obj


def measure_key(cam_name):
    """Log-average scene luminance seen by a camera (tiny linear EXR test render)."""
    import numpy as np
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples,
            sc.render.image_settings.file_format, sc.render.filepath)
    sc.camera = bpy.data.objects[cam_name]
    sc.render.resolution_x, sc.render.resolution_y = 192, 108
    sc.cycles.samples = 48
    sc.render.image_settings.file_format = "OPEN_EXR"
    path = os.path.join(bpy.app.tempdir, "key_" + cam_name + ".exr")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    px = px.reshape(-1, 4)
    lum = 0.2126 * px[:, 0] + 0.7152 * px[:, 1] + 0.0722 * px[:, 2]
    lum = np.clip(lum, 1e-4, 50.0)
    key = float(np.exp(np.mean(np.log(lum))))
    measure_key.p90 = float(np.percentile(lum, 90))       # how bright the brightest tenth is: guards flash-lit white subjects
    (sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples,
     sc.render.image_settings.file_format, sc.render.filepath) = keep
    sc.render.image_settings.color_depth = "8"      # the EXR detour leaves 16-bit selected otherwise
    return key


def ortho_top(name, center, scale, col=None):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = scale
    obj = bpy.data.objects.new(name, cam)
    (col or bpy.context.scene.collection).objects.link(obj)
    obj.location = (center[0], center[1], 30)
    return obj


def render(cam_name, path, samples=None, res=None, hide_ceiling=False, exposure=None):
    sc = bpy.context.scene
    sc.camera = bpy.data.objects[cam_name]
    if samples:
        sc.cycles.samples = samples
    if res:
        sc.render.resolution_x, sc.render.resolution_y = res
    if exposure is not None:
        sc.view_settings.exposure = exposure
    hidden = []
    if hide_ceiling:
        for o in bpy.data.objects:
            if o.get("is_ceiling") and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
    ims = sc.render.image_settings
    linear = path.lower().endswith(".exr")      # scene-linear, no view transform: developed by photo_finish
    if linear:
        ims.file_format = "OPEN_EXR"
        ims.color_depth = "16"
        ims.exr_codec = "ZIP"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if linear:
        ims.file_format = "PNG"
        ims.color_depth = "8"
    for o in hidden:
        o.hide_render = False
    return path


def _box(a, r, axis):
    """Box blur of radius r along one axis (edge-padded), via a running sum."""
    import numpy as np
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def _blur(a, sigma):
    """Gaussian-like blur: small sigmas use a real 5-tap kernel, large ones three box passes."""
    import numpy as np
    if sigma <= 0:
        return a
    if sigma < 1.6:
        k = np.exp(-0.5 * (np.arange(-3, 4) / sigma) ** 2).astype(np.float32)
        k /= k.sum()
        out = a
        for axis in (0, 1):
            pad = [(0, 0)] * a.ndim
            pad[axis] = (3, 3)
            p = np.pad(out, pad, mode="edge")
            n = out.shape[axis]
            out = sum(k[j] * np.take(p, np.arange(j, j + n), axis=axis) for j in range(7))
        return out
    r = max(1, int(round(sigma * 0.95)))
    out = a
    for _ in range(3):
        out = _box(_box(out, r, 0), r, 1)
    return out


def photo_finish(src, dst=None, seed=3, ev=0.0, exposure=0.0, wb=(0.94, 1.0, 1.07), cast=(1.012, 1.0, 0.985),
                 glare=0.028, veil=0.008, vignette=0.22, barrel=-0.03, ca=0.0012, soften=0.65, shot=0.0005,
                 read=0.0012, shoulder=0.5, contrast=0.16, black=0.012, saturation=0.9, sharpen=0.45, jpeg=90, mottle=1.4, fringe=0.14, gain=None, smear=0.75):
    """Develop a scene-linear Cycles frame (EXR) the way a camera would, in the order the
    light meets the hardware: lens falloff, glare around bright windows, distortion and
    fringing, slight optical softness; then the sensor (white balance, photon and read
    noise, channels that saturate one by one); then the in-camera JPEG engine (tone curve
    with a short shoulder, saturation, sharpening with its halo, 8-bit JPEG compression).
    `ev` is the metered exposure in stops, `exposure` a bias on top. Writes an 8-bit PNG."""
    import numpy as np
    dst = dst or (os.path.splitext(src)[0] + ".png")
    img = bpy.data.images.load(src)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    lin = np.clip(px.reshape(h, w, 4)[:, :, :3], 0.0, None) * np.float32(2.0 ** (ev + exposure))
    bpy.data.images.remove(img)
    rng = np.random.default_rng(seed)

    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (xs - w / 2) / (w / 2), (ys - h / 2) / (w / 2)
    r2 = nx * nx + ny * ny

    # lens: light falloff towards the corners
    lin = lin * (1.0 - vignette * np.clip(r2, 0, 2) ** 1.2 / 1.6)[..., None]

    # lens: halation right around blown highlights plus a faint veil over the whole frame
    hot = np.minimum(lin, 24.0)
    if glare > 0:
        lin = lin * (1.0 - glare) + glare * (0.6 * _blur(hot, 5.0) + 0.4 * _blur(hot, 16.0))
    if veil > 0:
        k = 8
        hs, ws = h // k * k, w // k * k
        small = hot[:hs, :ws].reshape(hs // k, k, ws // k, k, 3).mean(axis=(1, 3))
        small = _blur(small, 14.0)
        wide = np.repeat(np.repeat(small, k, axis=0), k, axis=1)
        wide = np.pad(wide, ((0, h - hs), (0, w - ws), (0, 0)), mode="edge")
        lin = lin * (1.0 - veil) + veil * _blur(wide, 4.0)

    # lens: barrel distortion, red and blue magnified slightly differently (lateral fringing)
    out = np.empty_like(lin)
    for ch, mag in enumerate((1.0 + ca, 1.0, 1.0 - ca)):
        f = (1.0 + barrel * r2) * mag / (1.0 + barrel * 0.35)     # keep the frame filled
        sx = np.clip(nx * f * (w / 2) + w / 2, 0, w - 1.001)
        sy = np.clip(ny * f * (w / 2) + h / 2, 0, h - 1.001)
        x0, y0 = sx.astype(np.int32), sy.astype(np.int32)
        fx, fy = sx - x0, sy - y0
        c = lin[:, :, ch]
        out[:, :, ch] = (c[y0, x0] * (1 - fx) * (1 - fy) + c[y0, x0 + 1] * fx * (1 - fy)
                         + c[y0 + 1, x0] * (1 - fx) * fy + c[y0 + 1, x0 + 1] * fx * fy)
    lin = _blur(out, soften)            # lens + anti-alias filter + demosaic softness

    # sensor: white balance (auto WB never quite neutralises mixed light), photon + read noise
    lin = lin * (np.array(wb, dtype=np.float32) * np.array(cast, dtype=np.float32))
    # dim rooms need more sensor gain, and gain amplifies noise: a lamp-lit bedroom is far grainier than a sunlit one
    g = float(np.clip(2.0 ** (0.3 * (ev + exposure - 1.5)), 0.7, 3.0)) if gain is None else gain
    sigma = np.sqrt(shot * np.minimum(lin, 1.5) + read * read) * g
    if fringe > 0:                         # purple fringing where a blown highlight meets something dark
        hotm = np.clip(lin.min(axis=2) - 1.2, 0.0, 1.0)
        halo = np.clip(_blur(hotm[..., None], 2.6)[..., 0] - hotm, 0.0, 1.0)
        lin = lin + halo[..., None] * fringe * np.array((0.55, 0.08, 1.0), dtype=np.float32)
    grain = _blur(rng.normal(0.0, 1.0, (h, w, 3)).astype(np.float32), 0.55) * 1.9
    blotch = rng.normal(0.0, 1.0, (h // 3 + 1, w // 3 + 1, 3)).astype(np.float32)
    blotch = _blur(np.repeat(np.repeat(blotch, 3, axis=0), 3, axis=1)[:h, :w], 1.2)
    blotch -= blotch.mean(axis=2, keepdims=True)
    coarse = rng.normal(0.0, 1.0, (h // 8 + 1, w // 8 + 1, 3)).astype(np.float32)      # blotchy colour mottle left by
    coarse = _blur(np.repeat(np.repeat(coarse, 8, axis=0), 8, axis=1)[:h, :w], 3.0)    # noise reduction in the shadows
    coarse -= coarse.mean(axis=2, keepdims=True)
    lin = np.clip(lin + sigma * (grain + 0.9 * blotch) + read * g * mottle * coarse, 0.0, None)

    # JPEG engine: short highlight shoulder (each channel saturates on its own), display curve
    a = shoulder
    lin = np.where(lin <= a, lin, a + (1.0 - a) * (1.0 - np.exp(-(lin - a) / (1.0 - a))))
    lin = np.clip(lin * 1.012, 0.0, 1.0)
    px = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    px = px + contrast * (px - 0.46) * (1.0 - np.abs(2 * px - 1.0) ** 2) * 1.2
    px = np.clip((px - black) / (1.0 - black), 0, 1)
    grey = (px * np.array((0.3, 0.59, 0.11), dtype=np.float32)).sum(axis=2, keepdims=True)
    px = grey + (px - grey) * saturation
    if smear > 0:
        # The phone's noise reduction: fine grain is wiped wherever local contrast is low and kept at
        # edges, which leaves soft colour blotches and a slightly "painted" look instead of crisp grain.
        base = _blur(px, 1.7)
        d = px - base
        w_ = np.clip((np.abs(d).max(axis=2, keepdims=True) - 0.025) / 0.06, 0.0, 1.0)
        w_ = w_ * w_ * (3.0 - 2.0 * w_)
        px = base + d * ((1.0 - smear) + smear * w_)
    px = px + sharpen * (px - _blur(px, 1.0))

    rgba = np.concatenate([np.clip(px, 0, 1), np.ones((h, w, 1), np.float32)], axis=2).astype(np.float32)
    outimg = bpy.data.images.new("finish_tmp", w, h, alpha=False, float_buffer=False)
    outimg.pixels.foreach_set(rgba.ravel())
    if jpeg:                             # 8x8 DCT blocks and chroma subsampling, then back to PNG
        tmp = os.path.join(bpy.app.tempdir, "finish_{}.jpg".format(seed))
        outimg.file_format = "JPEG"
        outimg.save(filepath=tmp, quality=int(jpeg))
        bpy.data.images.remove(outimg)
        outimg = bpy.data.images.load(tmp)
        outimg.pixels[0]                 # force the load before the format switch
    outimg.filepath_raw = dst
    outimg.file_format = "PNG"
    outimg.save()
    bpy.data.images.remove(outimg)
    return dst

"""Shared camera, lighting and render setup for 2.5D sprite renders (runs inside Blender).

World frame for every asset: Z up, the visible front faces -Y, metres, and the asset
origin is its ground-footprint origin at z = 0. No ground plane or shadow catcher is
rendered, so no ground shadow is baked into the alpha.
"""

import math

import bpy
from mathutils import Vector

from pipeline import conventions as C


def reset_scene(name):
    for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                       bpy.data.lights, bpy.data.cameras, bpy.data.collections):
        for block in list(collection):
            collection.remove(block)
    scene = bpy.context.scene
    scene.name = name
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return scene


def new_collection(scene, name):
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    return coll


def direction(elevation_deg, azimuth_deg):
    """Unit vector pointing from the scene towards a light or camera.

    Azimuth 0 = straight from the front (-Y); negative = from -X (viewer's left).
    """
    el, az = math.radians(elevation_deg), math.radians(azimuth_deg)
    return Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))).normalized()


def _add_sun(collection, name, to_light, strength, angle_deg, color):
    light = bpy.data.lights.new(name, "SUN")
    light.energy = strength
    light.angle = math.radians(angle_deg)
    light.color = color
    obj = bpy.data.objects.new(name, light)
    collection.objects.link(obj)
    obj.rotation_euler = to_light.to_track_quat("Z", "Y").to_euler()
    return obj


def setup_lighting(scene, rig_collection, asset_collection):
    """Key sun plus fill suns light-linked to the asset collection; no world light."""
    sun_dir = direction(C.SUN_ELEVATION_DEG, C.SUN_AZIMUTH_FROM_FRONT_DEG)
    _add_sun(rig_collection, "KeySun", sun_dir, C.SUN_STRENGTH, C.SUN_ANGLE_DEG, C.SUN_COLOR)
    for name, el, az, strength, angle, color in C.FILL_LIGHTS:
        fill = _add_sun(rig_collection, name, direction(el, az), strength, angle, color)
        fill.light_linking.receiver_collection = asset_collection

    world = bpy.data.worlds.new("NoWorldLight")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Strength"].default_value = 0.0
    return {
        "sun_elevation_deg": C.SUN_ELEVATION_DEG,
        "sun_azimuth_deg_from_front": C.SUN_AZIMUTH_FROM_FRONT_DEG,
        "sun_direction_to_light": [round(c, 4) for c in sun_dir],
        "sun_strength": C.SUN_STRENGTH,
        "sun_angle_deg": C.SUN_ANGLE_DEG,
        "fill_lights_linked_to_asset_only": [
            {"name": n, "elevation_deg": el, "azimuth_deg_from_front": az,
             "strength": s, "angle_deg": a, "color": list(c)}
            for n, el, az, s, a, c in C.FILL_LIGHTS
        ],
        "world_light": "none (strength 0)",
        "ground": "none (no shadow catcher; no cast shadow baked into the PNG)",
    }


def setup_camera(scene, collection, bounds_points, elevation, azimuth, width_px, px_per_m=None):
    """Orthographic camera framing `bounds_points` with the shared margin.

    With `px_per_m` the render scale is fixed instead of `width_px`: the width becomes the
    framed extent at that scale, so assets of different sizes share one texel density.

    Returns (camera_info, projection). `projection` maps a world point to texture
    pixels (top-left origin): x = W/2 + (p.right - cx) * ppm, y = H/2 - (p.up - cy) * ppm.
    """
    cam_data = bpy.data.cameras.new("OrthoCamera")
    cam_data.type = "ORTHO"
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("OrthoCamera", cam_data)
    collection.objects.link(cam)
    scene.camera = cam

    # Azimuth 0: camera on the -Y side looking along +Y at the front face.
    cam.rotation_euler = (math.radians(90.0 - elevation), 0.0, math.radians(azimuth))
    rot = cam.rotation_euler.to_matrix()
    right, up, forward = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0)), rot @ Vector((0, 0, -1))

    xs = [p.dot(right) for p in bounds_points]
    ys = [p.dot(up) for p in bounds_points]
    fs = [p.dot(forward) for p in bounds_points]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
    margin = C.FRAME_MARGIN_FRACTION * max(w, h)
    frame_w, frame_h = w + 2 * margin, h + 2 * margin
    if px_per_m:
        width_px = int(round(frame_w * px_per_m))
        frame_w = width_px / px_per_m

    cam.location = right * cx + up * cy + forward * (min(fs) - 20.0)
    cam_data.ortho_scale = frame_w

    res_x = width_px
    res_y = int(round(res_x * frame_h / frame_w / 2.0)) * 2
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    ppm = res_x / frame_w

    camera_info = {
        "type": "ORTHO",
        "elevation_deg": elevation,
        "azimuth_deg": azimuth,
        "rotation_euler_deg": [round(math.degrees(a), 4) for a in cam.rotation_euler],
        "location_m": [round(c, 4) for c in cam.location],
        "ortho_scale_m": round(frame_w, 6),
        "sensor_fit": "HORIZONTAL",
        "content_extent_m": [round(w, 4), round(h, 4)],
        "margin_m_each_side": round(margin, 4),
        "pixels_per_metre_on_screen": round(ppm, 6),
    }
    projection = {
        "image_px": [res_x, res_y],
        "px_per_m": ppm,
        "right": [right.x, right.y, right.z],
        "up": [up.x, up.y, up.z],
        "center_m": [cx, cy],
    }
    return camera_info, projection


def project(projection, point):
    """World point (metres) -> texture pixel (x, y), top-left origin, pixel-edge coordinates."""
    w, h = projection["image_px"]
    ppm = projection["px_per_m"]
    cx, cy = projection["center_m"]
    r, u = projection["right"], projection["up"]
    pr = sum(a * b for a, b in zip(point, r))
    pu = sum(a * b for a, b in zip(point, u))
    return (w / 2.0 + (pr - cx) * ppm, h / 2.0 - (pu - cy) * ppm)


def _setup_compositor(scene):
    """Denoise colour only. Cycles' own denoiser also denoises alpha, which left
    stray semi-transparent pixels on the transparent border; the raw alpha is clean."""
    scene.view_layers[0].cycles.denoising_store_passes = True
    tree = bpy.data.node_groups.new("AssetCompositing", "CompositorNodeTree")
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = tree
    scene.render.use_compositing = True

    layers = tree.nodes.new("CompositorNodeRLayers")
    denoise = tree.nodes.new("CompositorNodeDenoise")
    set_alpha = tree.nodes.new("CompositorNodeSetAlpha")
    set_alpha.inputs["Type"].default_value = "Replace Alpha"
    output = tree.nodes.new("NodeGroupOutput")

    tree.links.new(layers.outputs["Image"], denoise.inputs["Image"])
    tree.links.new(layers.outputs["Denoising Albedo"], denoise.inputs["Albedo"])
    tree.links.new(layers.outputs["Denoising Normal"], denoise.inputs["Normal"])
    tree.links.new(denoise.outputs["Image"], set_alpha.inputs["Image"])
    tree.links.new(layers.outputs["Alpha"], set_alpha.inputs["Alpha"])
    tree.links.new(set_alpha.outputs["Image"], output.inputs["Image"])


def setup_render(scene, samples, use_cpu):
    scene.render.engine = "CYCLES"
    cycles = scene.cycles
    device = "CPU"
    if not use_cpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = backend
            except TypeError:
                continue
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == backend]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == backend
                device = f"GPU ({backend}: {gpus[0].name})"
                cycles.device = "GPU"
                break
    if device == "CPU":
        cycles.device = "CPU"

    cycles.samples = samples
    cycles.use_adaptive_sampling = True
    cycles.use_denoising = False
    _setup_compositor(scene)
    cycles.max_bounces = C.MAX_BOUNCES
    scene.render.film_transparent = True
    scene.render.filter_size = C.FILTER_SIZE_PX

    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

    img = scene.render.image_settings
    img.file_format = "PNG"
    img.color_mode = "RGBA"
    img.color_depth = "8"
    img.compression = 15
    return {
        "engine": "CYCLES",
        "device": device,
        "samples": cycles.samples,
        "adaptive_sampling": True,
        "denoiser": "compositor OIDN on colour only (albedo + normal guides); raw render alpha kept",
        "max_bounces": cycles.max_bounces,
        "film_transparent": True,
        "filter_size_px": scene.render.filter_size,
        "view_transform": "Standard",
        "output_format": "PNG RGBA 8-bit",
    }

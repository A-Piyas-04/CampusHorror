"""Red-brick wall module: production-art pipeline test (Milestone G Part 2).

Builds ONE straight red-brick wall module from modeled bricks, renders it with an
orthographic camera to a transparent RGBA PNG, and saves the generated source as
a NEW .blend file. It never opens or writes campus_asset_workshop.blend.

Run from the project root:

    "F:\\bbbb\\blender.exe" --background --factory-startup --python-exit-code 1 ^
        --python assets/source/blender/scripts/red_brick_wall_test.py

Optional arguments after `--`:
    --cpu            render on the CPU instead of the GPU
    --samples N      Cycles samples (default 256)
    --width N        output width in pixels (default 768)
    --azimuth DEG    camera horizontal azimuth (default 0 = facing the wall front)
    --elevation DEG  camera elevation above the horizon (default 40)
    --preview NAME   preview render: writes only assets/sprites/architecture/NAME.png and
                     assets/source/blender/NAME.render.json; no .blend is saved and the
                     default outputs are never touched
    --no-ground-shadow  omit the shadow catcher, so no cast shadow is baked into the alpha

Angled preview used for the 2.5D depth review:

    ... --python assets/source/blender/scripts/red_brick_wall_test.py -- ^
        --preview red_brick_wall_angle_test --azimuth 20 --no-ground-shadow

Coordinate frame: the wall runs along X, its visible front face points to -Y,
Z is up, and the object origin is the centre of the footprint on the ground.
All dimensions are metres.
"""

import json
import math
import random
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[4]
OUT_BLEND = PROJECT_ROOT / "assets/source/blender/red_brick_wall_test.blend"
OUT_PNG = PROJECT_ROOT / "assets/sprites/architecture/red_brick_wall_test.png"
OUT_RECORD = PROJECT_ROOT / "assets/source/blender/red_brick_wall_test.render.json"
PROTECTED_BLEND = PROJECT_ROOT / "assets/source/blender/campus_asset_workshop.blend"

SEED = 20261013

# Module size (test dimensions).
WALL_LENGTH = 3.0
WALL_THICKNESS = 0.30
WALL_HEIGHT = 2.40

# Brick format (approximate South-Asian standard brick, 10 mm joints).
BRICK_LENGTH = 0.24
BRICK_HEIGHT = 0.07
BRICK_DEPTH = 0.11
JOINT = 0.01
COURSE = BRICK_HEIGHT + JOINT          # 0.08
BRICK_PITCH = BRICK_LENGTH + JOINT     # 0.25 -> exactly 12 per 3 m course
JOINT_RECESS = 0.010                   # mortar sits this far behind the brick face

PLINTH_COURSES = 3                     # courses 0..2 project from the face
PLINTH_PROJECTION = 0.02
OVERSAIL_PROJECTION = 0.025            # last course below the coping
BODY_COURSES = 28                      # 28 * 0.08 = 2.24 m incl. top bed joint
COPING_PROJECTION = 0.040              # rowlock coping overhang on each side
COPING_UNITS = 35                      # bricks-on-edge along the top

# Camera / render.
CAMERA_ELEVATION_DEG = 40.0
CAMERA_AZIMUTH_DEG = 0.0
RENDER_WIDTH = 768
SAMPLES = 256
FRAME_MARGIN_FRACTION = 0.08           # transparent margin on each side, of the larger extent

# Sun: comes from the front-left and above, so the front face and the top are lit
# and the cast shadow falls back and to the right.
SUN_ELEVATION_DEG = 55.0
SUN_AZIMUTH_FROM_FRONT_DEG = -35.0     # negative = from the viewer's left
SUN_STRENGTH = 3.2
SUN_ANGLE_DEG = 3.0                    # angular diameter -> slightly soft shadow edges

# Fill lights are light-linked to the wall only, so the shadow catcher records the
# key sun's shadow and nothing else (no faint sky-occlusion haze across the ground).
# (name, elevation, azimuth from front, strength, angle, colour)
SHADOW_OPACITY = 0.6                   # alpha of the cast shadow in the PNG
FILL_LIGHTS = (
    ("SkyFill", 70.0, 20.0, 0.8, 90.0, (0.75, 0.85, 1.0)),
    ("GroundBounce", -25.0, 10.0, 0.35, 90.0, (1.0, 0.8, 0.65)),
)


def parse_args():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {
        "cpu": False,
        "samples": SAMPLES,
        "width": RENDER_WIDTH,
        "azimuth": CAMERA_AZIMUTH_DEG,
        "elevation": CAMERA_ELEVATION_DEG,
        "preview": None,
        "ground_shadow": True,
    }
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--cpu":
            opts["cpu"] = True
        elif a == "--no-ground-shadow":
            opts["ground_shadow"] = False
        elif a == "--preview":
            name = args[i + 1]
            if not name.replace("_", "").isalnum() or name == OUT_PNG.stem:
                raise SystemExit(f"Invalid preview name: {name!r}")
            opts["preview"] = name
            i += 1
        elif a in ("--samples", "--width"):
            opts[a[2:]] = int(args[i + 1])
            i += 1
        elif a in ("--azimuth", "--elevation"):
            opts[a[2:]] = float(args[i + 1])
            i += 1
        else:
            raise SystemExit(f"Unknown argument: {a}")
        i += 1
    return opts


# ---------------------------------------------------------------------------
# Scene reset
# ---------------------------------------------------------------------------

def reset_scene():
    for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                       bpy.data.lights, bpy.data.cameras, bpy.data.collections):
        for block in list(collection):
            collection.remove(block)
    scene = bpy.context.scene
    scene.name = "RedBrickWallTest"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return scene


def new_collection(scene, name):
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    return coll


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class BoxBuilder:
    """Accumulates axis-aligned boxes into one bmesh with per-box attributes."""

    def __init__(self):
        self.bm = bmesh.new()
        self.rand_layer = self.bm.faces.layers.float.new("brick_rand")
        self.box_count = 0

    def add(self, x0, x1, y0, y1, z0, z1, rand=0.0, material_index=0):
        v = [self.bm.verts.new(c) for c in (
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        )]
        faces = (
            (v[0], v[3], v[2], v[1]),  # bottom
            (v[4], v[5], v[6], v[7]),  # top
            (v[0], v[1], v[5], v[4]),  # -Y (front)
            (v[2], v[3], v[7], v[6]),  # +Y (back)
            (v[1], v[2], v[6], v[5]),  # +X
            (v[3], v[0], v[4], v[7]),  # -X
        )
        for f in faces:
            face = self.bm.faces.new(f)
            face[self.rand_layer] = rand
            face.material_index = material_index
        self.box_count += 1

    def to_mesh(self, name):
        mesh = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(mesh)
        self.bm.free()
        return mesh


def brick_rand(rng):
    # Mostly mid reds; a few dark over-fired and a few pale under-fired bricks.
    r = rng.random()
    if r < 0.06:
        return rng.uniform(0.0, 0.08)
    if r > 0.96:
        return rng.uniform(0.9, 1.0)
    return rng.uniform(0.15, 0.85)


def add_course(builder, rng, z0, face_offset, offset_half):
    """One running-bond course on the front and back skins."""
    half = WALL_LENGTH / 2.0
    lo, hi = -half + JOINT / 2.0, half - JOINT / 2.0
    start = -half - (BRICK_PITCH / 2.0 if offset_half else 0.0)
    for side in (-1, 1):
        face_y = side * (WALL_THICKNESS / 2.0 + face_offset)
        x = start
        while x < half:
            bx0 = max(x + JOINT / 2.0, lo)
            bx1 = min(x + JOINT / 2.0 + BRICK_LENGTH, hi)
            x += BRICK_PITCH
            if bx1 - bx0 < 0.03:
                continue
            # Small hand-laid irregularities.
            jitter_out = rng.uniform(-0.0015, 0.0015)
            shrink_l = rng.uniform(0.0, 0.0015)
            shrink_r = rng.uniform(0.0, 0.0015)
            shrink_top = rng.uniform(0.0, 0.001)
            outer = face_y + side * jitter_out
            inner = face_y - side * BRICK_DEPTH
            y0, y1 = sorted((outer, inner))
            builder.add(bx0 + shrink_l, bx1 - shrink_r, y0, y1,
                        z0, z0 + BRICK_HEIGHT - shrink_top,
                        rand=brick_rand(rng), material_index=0)


def build_wall(collection, rng):
    builder = BoxBuilder()
    half_l = WALL_LENGTH / 2.0
    half_t = WALL_THICKNESS / 2.0

    for course in range(BODY_COURSES):
        z0 = course * COURSE
        if course < PLINTH_COURSES:
            face_offset = PLINTH_PROJECTION
        elif course == BODY_COURSES - 1:
            face_offset = OVERSAIL_PROJECTION
        else:
            face_offset = 0.0
        add_course(builder, rng, z0, face_offset, offset_half=bool(course % 2))

    # Rowlock coping: bricks on edge spanning the full (projecting) thickness.
    coping_z0 = BODY_COURSES * COURSE
    coping_half_t = half_t + COPING_PROJECTION
    pitch = WALL_LENGTH / COPING_UNITS
    for i in range(COPING_UNITS):
        x0 = -half_l + i * pitch + JOINT / 2.0
        x1 = x0 + pitch - JOINT
        builder.add(x0 + rng.uniform(0, 0.001), x1 - rng.uniform(0, 0.001),
                    -coping_half_t - rng.uniform(-0.001, 0.001),
                    coping_half_t + rng.uniform(-0.001, 0.001),
                    coping_z0, WALL_HEIGHT - rng.uniform(0.0, 0.0015),
                    rand=brick_rand(rng), material_index=0)

    # Mortar cores, recessed behind each band of brick faces (material 1).
    plinth_top = PLINTH_COURSES * COURSE
    oversail_z0 = (BODY_COURSES - 1) * COURSE
    for (z0, z1, face) in (
        (0.0, plinth_top, half_t + PLINTH_PROJECTION),
        (plinth_top, oversail_z0, half_t),
        (oversail_z0, coping_z0, half_t + OVERSAIL_PROJECTION),
        (coping_z0, WALL_HEIGHT - 0.004, coping_half_t),
    ):
        depth = face - JOINT_RECESS
        builder.add(-half_l, half_l, -depth, depth, z0, z1, rand=0.5, material_index=1)

    brick_count = builder.box_count - 4
    mesh = builder.to_mesh("RedBrickWallMesh")
    obj = bpy.data.objects.new("RedBrickWall", mesh)
    collection.objects.link(obj)

    bevel = obj.modifiers.new("BrickBevel", "BEVEL")
    bevel.width = 0.004
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(30)
    bevel.harden_normals = True
    return obj, brick_count


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def _socket(sockets, identifier):
    return next(s for s in sockets if s.identifier == identifier)


def _new_material(name):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf


def _noise(nt, coords, scale, detail=6.0, roughness=0.6):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = roughness
    nt.links.new(coords, n.inputs["Vector"])
    return n


def _map_range(nt, value_socket, from_min, from_max, to_min, to_max, clamp=True):
    m = nt.nodes.new("ShaderNodeMapRange")
    m.clamp = clamp
    m.inputs["From Min"].default_value = from_min
    m.inputs["From Max"].default_value = from_max
    m.inputs["To Min"].default_value = to_min
    m.inputs["To Max"].default_value = to_max
    nt.links.new(value_socket, m.inputs["Value"])
    return m.outputs["Result"]


def _multiply_color(nt, color_socket, factor_socket):
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    _socket(mix.inputs, "Factor_Float").default_value = 1.0
    nt.links.new(color_socket, _socket(mix.inputs, "A_Color"))
    nt.links.new(factor_socket, _socket(mix.inputs, "B_Color"))
    return _socket(mix.outputs, "Result_Color")


def _ground_grime(nt):
    """Darkening factor: 0.72 at the ground, 1.0 from 0.6 m up."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    return _map_range(nt, sep.outputs["Z"], 0.0, 0.6, 0.72, 1.0)


def make_brick_material():
    mat, nt, bsdf = _new_material("BrickRed")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]

    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    attr.attribute_name = "brick_rand"

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    elements = ramp.color_ramp.elements
    # Linear-space colours (sRGB in comments).
    stops = (
        (0.00, (0.100, 0.016, 0.008)),  # over-fired dark   ~ (0.35, 0.13, 0.09)
        (0.10, (0.240, 0.032, 0.014)),  # deep red          ~ (0.53, 0.20, 0.12)
        (0.45, (0.370, 0.056, 0.022)),  # warm red          ~ (0.64, 0.26, 0.16)
        (0.80, (0.480, 0.095, 0.036)),  # orange red        ~ (0.72, 0.34, 0.21)
        (1.00, (0.540, 0.160, 0.085)),  # pale under-fired  ~ (0.76, 0.44, 0.32)
    )
    elements[0].position, elements[0].color = stops[0][0], (*stops[0][1], 1.0)
    elements[1].position, elements[1].color = stops[-1][0], (*stops[-1][1], 1.0)
    for pos, col in stops[1:-1]:
        e = elements.new(pos)
        e.color = (*col, 1.0)
    nt.links.new(attr.outputs["Fac"], ramp.inputs["Fac"])

    # Surface mottling within a brick, plus broad weathering across the wall.
    fine = _noise(nt, coords, 45.0)
    broad = _noise(nt, coords, 2.5, detail=3.0)
    color = _multiply_color(nt, ramp.outputs["Color"],
                            _map_range(nt, fine.outputs["Fac"], 0.3, 0.7, 0.82, 1.12))
    color = _multiply_color(nt, color,
                            _map_range(nt, broad.outputs["Fac"], 0.35, 0.65, 0.9, 1.06))
    color = _multiply_color(nt, color, _ground_grime(nt))

    # Upward-facing brick faces (coping top, ledges) are sun-bleached and dusty.
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    dust = nt.nodes.new("ShaderNodeMix")
    dust.data_type = "RGBA"
    dust.blend_type = "MIX"
    nt.links.new(_map_range(nt, sep.outputs["Z"], 0.6, 0.95, 0.0, 0.32),
                 _socket(dust.inputs, "Factor_Float"))
    nt.links.new(color, _socket(dust.inputs, "A_Color"))
    _socket(dust.inputs, "B_Color").default_value = (0.50, 0.30, 0.20, 1.0)
    nt.links.new(_socket(dust.outputs, "Result_Color"), bsdf.inputs["Base Color"])

    rough = _map_range(nt, fine.outputs["Fac"], 0.3, 0.7, 0.74, 0.92)
    nt.links.new(rough, bsdf.inputs["Roughness"])

    pores = _noise(nt, coords, 220.0, detail=4.0, roughness=0.7)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(pores.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_mortar_material():
    mat, nt, bsdf = _new_material("Mortar")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (0.40, 0.375, 0.33, 1.0)  # ~ sRGB (0.67, 0.65, 0.61)

    grain = _noise(nt, coords, 160.0, detail=5.0)
    color = _multiply_color(nt, base.outputs["Color"],
                            _map_range(nt, grain.outputs["Fac"], 0.3, 0.7, 0.8, 1.1))
    color = _multiply_color(nt, color, _ground_grime(nt))
    nt.links.new(color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------------------------------------------------------------------------
# Lighting, ground, camera
# ---------------------------------------------------------------------------

def direction(elevation_deg, azimuth_deg):
    """Unit vector pointing from the scene towards a light.

    Azimuth 0 = straight from the front (-Y); negative = from -X (viewer's left).
    """
    el, az = math.radians(elevation_deg), math.radians(azimuth_deg)
    return Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))).normalized()


def sun_direction():
    return direction(SUN_ELEVATION_DEG, SUN_AZIMUTH_FROM_FRONT_DEG)


def _add_sun(collection, name, to_light, strength, angle_deg, color):
    light = bpy.data.lights.new(name, "SUN")
    light.energy = strength
    light.angle = math.radians(angle_deg)
    light.color = color
    obj = bpy.data.objects.new(name, light)
    collection.objects.link(obj)
    obj.rotation_euler = to_light.to_track_quat("Z", "Y").to_euler()
    return obj


def setup_lighting(scene, collection, receivers, ground):
    sun = _add_sun(collection, "KeySun", sun_direction(), SUN_STRENGTH, SUN_ANGLE_DEG, (1.0, 0.96, 0.9))
    for name, el, az, strength, angle, color in FILL_LIGHTS:
        fill = _add_sun(collection, name, direction(el, az), strength, angle, color)
        fill.light_linking.receiver_collection = receivers

    if ground is not None:
        # Shadowless light on the ground only: catcher alpha = key / (key + ambient).
        key_on_ground = SUN_STRENGTH * sun_direction().z
        ambient = _add_sun(collection, "GroundAmbient", Vector((0, 0, 1)),
                           key_on_ground * (1.0 / SHADOW_OPACITY - 1.0), 0.0, (1.0, 1.0, 1.0))
        ambient.data.use_shadow = False
        ambient.light_linking.receiver_collection = ground

    world = bpy.data.worlds.new("NoWorldLight")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Strength"].default_value = 0.0
    return sun


def add_shadow_catcher(collection):
    mesh = bpy.data.meshes.new("ShadowCatcherMesh")
    s = 8.0
    mesh.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new("ShadowCatcher", mesh)
    collection.objects.link(obj)
    obj.is_shadow_catcher = True
    return obj


def frame_points(include_shadow):
    """Points that must be inside the frame: wall bounds, plus its cast shadow if baked."""
    hl = WALL_LENGTH / 2.0
    ht = WALL_THICKNESS / 2.0 + COPING_PROJECTION
    pts = [Vector((x, y, z)) for x in (-hl, hl) for y in (-ht, ht) for z in (0.0, WALL_HEIGHT)]
    if include_shadow:
        to_sun = sun_direction()
        for p in [p for p in pts if p.z > 0]:
            pts.append(p - to_sun * (p.z / to_sun.z))
    return pts


def setup_camera(scene, collection, opts):
    cam_data = bpy.data.cameras.new("OrthoCamera")
    cam_data.type = "ORTHO"
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("OrthoCamera", cam_data)
    collection.objects.link(cam)
    scene.camera = cam

    elevation = opts["elevation"]
    azimuth = opts["azimuth"]
    # Azimuth 0: camera on the -Y side looking along +Y at the front face.
    cam.rotation_euler = (math.radians(90.0 - elevation), 0.0, math.radians(azimuth))
    rot = cam.rotation_euler.to_matrix()
    right, up, forward = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0)), rot @ Vector((0, 0, -1))

    pts = frame_points(opts["ground_shadow"])
    xs = [p.dot(right) for p in pts]
    ys = [p.dot(up) for p in pts]
    fs = [p.dot(forward) for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
    margin = FRAME_MARGIN_FRACTION * max(w, h)
    frame_w, frame_h = w + 2 * margin, h + 2 * margin

    cam.location = right * cx + up * cy + forward * (min(fs) - 20.0)
    cam_data.ortho_scale = frame_w

    res_x = opts["width"]
    res_y = int(round(res_x * frame_h / frame_w / 2.0)) * 2
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100

    return cam, {
        "type": "ORTHO",
        "elevation_deg": elevation,
        "azimuth_deg": azimuth,
        "rotation_euler_deg": [round(math.degrees(a), 4) for a in cam.rotation_euler],
        "location_m": [round(c, 4) for c in cam.location],
        "ortho_scale_m": round(frame_w, 4),
        "sensor_fit": "HORIZONTAL",
        "content_extent_m": [round(w, 4), round(h, 4)],
        "margin_m_each_side": round(margin, 4),
        "pixels_per_metre_on_screen": round(res_x / frame_w, 2),
    }


# ---------------------------------------------------------------------------
# Render settings
# ---------------------------------------------------------------------------

def setup_compositor(scene):
    """Denoise colour only. Cycles' own denoiser also denoises alpha, which left
    stray semi-transparent pixels on the transparent border; the raw alpha is clean."""
    scene.view_layers[0].cycles.denoising_store_passes = True
    tree = bpy.data.node_groups.new("WallTestCompositing", "CompositorNodeTree")
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


def setup_render(scene, opts):
    scene.render.engine = "CYCLES"
    cycles = scene.cycles
    device = "CPU"
    if not opts["cpu"]:
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

    cycles.samples = opts["samples"]
    cycles.use_adaptive_sampling = True
    cycles.use_denoising = False
    setup_compositor(scene)
    cycles.max_bounces = 6
    scene.render.film_transparent = True
    scene.render.filter_size = 1.5

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


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_png(path):
    raw = path.read_bytes()
    png_ok = raw[:8] == b"\x89PNG\r\n\x1a\n"
    width = int.from_bytes(raw[16:20], "big")
    height = int.from_bytes(raw[20:24], "big")
    bit_depth, color_type = raw[24], raw[25]

    img = bpy.data.images.load(str(path), check_existing=False)
    pixels = list(img.pixels)
    bpy.data.images.remove(img)
    alpha = pixels[3::4]
    min_x, min_y, max_x, max_y = width, height, -1, -1
    opaque = partial = 0
    for i, a in enumerate(alpha):
        if a <= 1.0 / 255.0:
            continue
        if a >= 254.0 / 255.0:
            opaque += 1
        else:
            partial += 1
        x, y = i % width, i // width  # y counts up from the bottom row
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)
    border_alpha = max(
        max(alpha[x] for x in range(width)),
        max(alpha[(height - 1) * width + x] for x in range(width)),
        max(alpha[y * width] for y in range(height)),
        max(alpha[y * width + width - 1] for y in range(height)),
    )
    has_content = max_x >= 0
    return {
        "png_signature_ok": png_ok,
        "size_px": [width, height],
        "bit_depth": bit_depth,
        "png_color_type": color_type,
        "is_rgba": color_type == 6,
        "file_bytes": len(raw),
        "opaque_pixels": opaque,
        "partially_transparent_pixels": partial,
        "fully_transparent_pixels": width * height - opaque - partial,
        "content_bbox_px_top_left_origin": [min_x, height - 1 - max_y, max_x, height - 1 - min_y] if has_content else None,
        "margins_px": {
            "left": min_x,
            "right": width - 1 - max_x,
            "top": height - 1 - max_y,
            "bottom": min_y,
        } if has_content else None,
        "max_alpha_on_image_border": round(border_alpha, 4),
    }


# ---------------------------------------------------------------------------

def main():
    opts = parse_args()
    t0 = time.time()
    if bpy.data.filepath and Path(bpy.data.filepath).resolve() == PROTECTED_BLEND.resolve():
        raise SystemExit("Refusing to run with campus_asset_workshop.blend loaded; use --factory-startup.")

    rng = random.Random(SEED)
    scene = reset_scene()
    asset_coll = new_collection(scene, "RedBrickWall")
    rig_coll = new_collection(scene, "RenderRig")

    wall, brick_count = build_wall(asset_coll, rng)
    wall.data.materials.append(make_brick_material())
    wall.data.materials.append(make_mortar_material())

    ground_coll = None
    if opts["ground_shadow"]:
        ground_coll = new_collection(scene, "GroundShadow")
        add_shadow_catcher(ground_coll)
    setup_lighting(scene, rig_coll, receivers=asset_coll, ground=ground_coll)
    _, camera_info = setup_camera(scene, rig_coll, opts)
    render_info = setup_render(scene, opts)

    preview = opts["preview"]
    out_png = OUT_PNG.with_name(f"{preview}.png") if preview else OUT_PNG
    out_record = OUT_RECORD.with_name(f"{preview}.render.json") if preview else OUT_RECORD
    out_blend = None if preview else OUT_BLEND
    out_png.parent.mkdir(parents=True, exist_ok=True)

    if out_blend is not None:
        assert out_blend.resolve() != PROTECTED_BLEND.resolve()
        # Saved first so the source exists even if rendering fails. Paths stay relative
        # so the .blend re-renders to the same PNG from its own location.
        for stale in (out_blend, out_blend.with_suffix(".blend1")):
            if stale.exists():
                stale.unlink()
        scene.render.filepath = "//../../sprites/architecture/red_brick_wall_test.png"
        bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), check_existing=False,
                                    relative_remap=True, compress=True)
        print(f"[WALLTEST] Saved source: {out_blend}")
    else:
        scene.render.filepath = str(out_png)

    t_render = time.time()
    bpy.ops.render.render(write_still=True)
    render_seconds = time.time() - t_render
    if not out_png.exists():
        raise RuntimeError(f"Render finished but {out_png} was not written.")
    print(f"[WALLTEST] Rendered: {out_png} in {render_seconds:.1f} s")

    check = verify_png(out_png)
    margins = check["margins_px"]
    passed = (check["png_signature_ok"] and check["is_rgba"]
              and margins is not None and min(margins.values()) >= 16
              and check["max_alpha_on_image_border"] <= 1.0 / 255.0)

    evaluated = wall.evaluated_get(bpy.context.evaluated_depsgraph_get())
    dims = evaluated.dimensions
    record = {
        "asset": preview or "red_brick_wall_test",
        "purpose": ("Preview render of the red_brick_wall_test geometry (visual-direction review, not final)"
                    if preview else
                    "Milestone G Part 2 production-art pipeline test (visual review only, not imported into Godot)"),
        "generator": str(SCRIPT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "arguments": sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [],
        "blender_version": bpy.app.version_string,
        "random_seed": SEED,
        "outputs": {
            "blend": str(out_blend.relative_to(PROJECT_ROOT)).replace("\\", "/") if out_blend else None,
            "png": str(out_png.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "record": str(out_record.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        },
        "wall": {
            "object": wall.name,
            "origin": "centre of footprint on the ground (z = 0); front face towards -Y",
            "design_size_m": {"length_x": WALL_LENGTH, "thickness_y": WALL_THICKNESS, "height_z": WALL_HEIGHT},
            "evaluated_bounds_m": {"x": round(dims.x, 4), "y": round(dims.y, 4), "z": round(dims.z, 4)},
            "brick_mm": [BRICK_LENGTH * 1000, BRICK_DEPTH * 1000, BRICK_HEIGHT * 1000],
            "joint_mm": JOINT * 1000,
            "joint_recess_mm": JOINT_RECESS * 1000,
            "courses": BODY_COURSES,
            "bond": "running (half) bond, front and back skins",
            "plinth": f"{PLINTH_COURSES} courses projecting {PLINTH_PROJECTION * 1000:.0f} mm",
            "oversail_course_projection_mm": OVERSAIL_PROJECTION * 1000,
            "coping": f"{COPING_UNITS} rowlock units, {COPING_PROJECTION * 1000:.0f} mm overhang each side",
            "modeled_bricks": brick_count,
            "bevel": "modifier, 4 mm, 2 segments, harden normals",
            "evaluated_faces": len(evaluated.to_mesh().polygons),
        },
        "camera": camera_info,
        "lighting": {
            "sun_elevation_deg": SUN_ELEVATION_DEG,
            "sun_azimuth_deg_from_front": SUN_AZIMUTH_FROM_FRONT_DEG,
            "sun_direction_to_light": [round(c, 4) for c in sun_direction()],
            "sun_strength": SUN_STRENGTH,
            "sun_angle_deg": SUN_ANGLE_DEG,
            "fill_lights_linked_to_wall_only": [
                {"name": n, "elevation_deg": el, "azimuth_deg_from_front": az,
                 "strength": s, "angle_deg": a, "color": list(c)}
                for n, el, az, s, a, c in FILL_LIGHTS
            ],
            "world_light": "none (strength 0)",
            **({
                "ground": "Cycles shadow catcher plane 16 x 16 m at z = 0 (cast shadow kept in the PNG alpha)",
                "cast_shadow_opacity_target": SHADOW_OPACITY,
                "ground_ambient": "shadowless sun linked to the shadow catcher only; sets the shadow opacity",
            } if opts["ground_shadow"] else {
                "ground": "none (no shadow catcher; no cast shadow baked into the PNG)",
            }),
        },
        "render": dict(render_info, resolution_px=[scene.render.resolution_x, scene.render.resolution_y],
                       render_seconds=round(render_seconds, 1)),
        "verification": dict(check, passed=passed, minimum_margin_required_px=16),
        "total_seconds": round(time.time() - t0, 1),
    }
    evaluated.to_mesh_clear()
    out_record.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("[WALLTEST] Record: " + str(out_record))
    print("[WALLTEST] " + json.dumps(record["verification"]))
    if not passed:
        raise RuntimeError("Verification failed; see the record file.")
    print("[WALLTEST] PASS")


main()

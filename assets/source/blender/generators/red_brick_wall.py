"""Red-brick boundary wall: modeled running-bond bricks, plinth, oversail course, rowlock coping.

Modeling and materials only; camera, lights, rendering and export are shared
(pipeline/). Geometry and materials match the approved Milestone G Part 2 test
(scripts/red_brick_wall_test.py) for the default parameters and the same seed.

Frame: the wall runs along X, its front face points to -Y, Z is up, and the origin is
the centre of the footprint on the ground. Dimensions are metres.
"""

import bpy

from pipeline.modeling import (BoxBuilder, ground_grime, map_range, multiply_color,
                               new_material, noise, socket)

COLLECTION_NAME = "RedBrickWall"

DEFAULT_PARAMS = {
    "length": 3.0,
    "thickness": 0.30,
    "height": 2.40,
    # Approximate South-Asian standard brick, 10 mm joints.
    "brick_length": 0.24,
    "brick_height": 0.07,
    "brick_depth": 0.11,
    "joint": 0.01,
    "joint_recess": 0.010,          # mortar sits this far behind the brick face
    "plinth_courses": 3,            # bottom courses project from the face
    "plinth_projection": 0.02,
    "oversail_projection": 0.025,   # last course below the coping
    "body_courses": 28,
    "coping_projection": 0.040,     # rowlock coping overhang on each side
    "coping_units": 35,             # bricks-on-edge along the top
    "bevel_width": 0.004,
}


def _brick_rand(rng):
    # Mostly mid reds; a few dark over-fired and a few pale under-fired bricks.
    r = rng.random()
    if r < 0.06:
        return rng.uniform(0.0, 0.08)
    if r > 0.96:
        return rng.uniform(0.9, 1.0)
    return rng.uniform(0.15, 0.85)


def _add_course(builder, rng, p, z0, face_offset, offset_half):
    """One running-bond course on the front and back skins, periodic over the module length.

    A brick crossing a module end is cut exactly at the end and its other part is placed
    at the opposite end with the same colour and jitter, so identical modules placed end
    to end continue the bond: the two parts form one whole brick across the join.
    """
    joint = p["joint"]
    length = p["length"]
    half = length / 2.0
    pitch = p["brick_length"] + joint
    start = -half - (pitch / 2.0 if offset_half else 0.0)
    for side in (-1, 1):
        face_y = side * (p["thickness"] / 2.0 + face_offset)
        for k in range(round(length / pitch)):
            a = start + k * pitch + joint / 2.0
            b = a + p["brick_length"]
            # Small hand-laid irregularities.
            jitter_out = rng.uniform(-0.0015, 0.0015)
            shrink_l = rng.uniform(0.0, 0.0015)
            shrink_r = rng.uniform(0.0, 0.0015)
            shrink_top = rng.uniform(0.0, 0.001)
            rand = _brick_rand(rng)
            if a < -half:
                pieces = ((-half, b - shrink_r), (a + length + shrink_l, half))
            elif b > half:
                pieces = ((a + shrink_l, half), (-half, b - length - shrink_r))
            else:
                pieces = ((a + shrink_l, b - shrink_r),)
            outer = face_y + side * jitter_out
            inner = face_y - side * p["brick_depth"]
            y0, y1 = sorted((outer, inner))
            for x0, x1 in pieces:
                builder.add(x0, x1, y0, y1, z0, z0 + p["brick_height"] - shrink_top,
                            rand=rand, material_index=0)


def _build_mesh(collection, rng, p):
    builder = BoxBuilder()
    course_h = p["brick_height"] + p["joint"]
    half_l = p["length"] / 2.0
    half_t = p["thickness"] / 2.0
    body = p["body_courses"]

    for course in range(body):
        if course < p["plinth_courses"]:
            face_offset = p["plinth_projection"]
        elif course == body - 1:
            face_offset = p["oversail_projection"]
        else:
            face_offset = 0.0
        _add_course(builder, rng, p, course * course_h, face_offset, offset_half=bool(course % 2))

    # Rowlock coping: bricks on edge spanning the full (projecting) thickness.
    coping_z0 = body * course_h
    coping_half_t = half_t + p["coping_projection"]
    pitch = p["length"] / p["coping_units"]
    for i in range(p["coping_units"]):
        x0 = -half_l + i * pitch + p["joint"] / 2.0
        x1 = x0 + pitch - p["joint"]
        builder.add(x0 + rng.uniform(0, 0.001), x1 - rng.uniform(0, 0.001),
                    -coping_half_t - rng.uniform(-0.001, 0.001),
                    coping_half_t + rng.uniform(-0.001, 0.001),
                    coping_z0, p["height"] - rng.uniform(0.0, 0.0015),
                    rand=_brick_rand(rng), material_index=0)

    # Mortar cores, recessed behind each band of brick faces (material 1).
    plinth_top = p["plinth_courses"] * course_h
    oversail_z0 = (body - 1) * course_h
    for (z0, z1, face) in (
        (0.0, plinth_top, half_t + p["plinth_projection"]),
        (plinth_top, oversail_z0, half_t),
        (oversail_z0, coping_z0, half_t + p["oversail_projection"]),
        (coping_z0, p["height"] - 0.004, coping_half_t),
    ):
        depth = face - p["joint_recess"]
        builder.add(-half_l, half_l, -depth, depth, z0, z1, rand=0.5, material_index=1)

    box_count = builder.box_count - 4
    # Edges lying on the module ends are cuts through a brick or the mortar core, not
    # real corners: no bevel there, so the two parts meet flush at a join.
    mesh = builder.to_mesh("RedBrickWallMesh", flush_x=(-half_l, half_l))
    obj = bpy.data.objects.new("RedBrickWall", mesh)
    collection.objects.link(obj)

    bevel = obj.modifiers.new("BrickBevel", "BEVEL")
    bevel.width = p["bevel_width"]
    bevel.segments = 2
    bevel.limit_method = "WEIGHT"
    bevel.harden_normals = True
    return obj, box_count


def _brick_material():
    mat, nt, bsdf = new_material("BrickRed")
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
    fine = noise(nt, coords, 45.0)
    broad = noise(nt, coords, 2.5, detail=3.0)
    color = multiply_color(nt, ramp.outputs["Color"],
                           map_range(nt, fine.outputs["Fac"], 0.3, 0.7, 0.82, 1.12))
    color = multiply_color(nt, color,
                           map_range(nt, broad.outputs["Fac"], 0.35, 0.65, 0.9, 1.06))
    color = multiply_color(nt, color, ground_grime(nt))

    # Upward-facing brick faces (coping top, ledges) are sun-bleached and dusty.
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    dust = nt.nodes.new("ShaderNodeMix")
    dust.data_type = "RGBA"
    dust.blend_type = "MIX"
    nt.links.new(map_range(nt, sep.outputs["Z"], 0.6, 0.95, 0.0, 0.32),
                 socket(dust.inputs, "Factor_Float"))
    nt.links.new(color, socket(dust.inputs, "A_Color"))
    socket(dust.inputs, "B_Color").default_value = (0.50, 0.30, 0.20, 1.0)
    nt.links.new(socket(dust.outputs, "Result_Color"), bsdf.inputs["Base Color"])

    rough = map_range(nt, fine.outputs["Fac"], 0.3, 0.7, 0.74, 0.92)
    nt.links.new(rough, bsdf.inputs["Roughness"])

    pores = noise(nt, coords, 220.0, detail=4.0, roughness=0.7)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(pores.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _mortar_material():
    mat, nt, bsdf = new_material("Mortar")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (0.40, 0.375, 0.33, 1.0)  # ~ sRGB (0.67, 0.65, 0.61)

    grain = noise(nt, coords, 160.0, detail=5.0)
    color = multiply_color(nt, base.outputs["Color"],
                           map_range(nt, grain.outputs["Fac"], 0.3, 0.7, 0.8, 1.1))
    color = multiply_color(nt, color, ground_grime(nt))
    nt.links.new(color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def build(collection, rng, params):
    p = params
    body_top = p["body_courses"] * (p["brick_height"] + p["joint"])
    if body_top >= p["height"]:
        raise ValueError(f"height {p['height']} m leaves no room for the coping above {body_top:.3f} m of courses")
    pitch = p["brick_length"] + p["joint"]
    if abs(round(p["length"] / pitch) * pitch - p["length"]) > 1e-9:
        raise ValueError(f"length {p['length']} m must be a whole number of brick pitches ({pitch} m) to tile")

    wall, brick_count = _build_mesh(collection, rng, p)
    wall.data.materials.append(_brick_material())
    wall.data.materials.append(_mortar_material())

    hl = p["length"] / 2.0
    ht = p["thickness"] / 2.0
    hb = ht + p["coping_projection"]  # widest part (coping) for framing
    return {
        "objects": [wall],
        "bounds_points_m": [(x, y, z) for x in (-hl, hl) for y in (-hb, hb) for z in (0.0, p["height"])],
        "footprint_m": [-hl, hl, -ht, ht],
        "tile_period_x_m": p["length"],
        "info": {
            "design_size_m": {"length_x": p["length"], "thickness_y": p["thickness"], "height_z": p["height"]},
            "bond": "running (half) bond, front and back skins; periodic over the module length "
                    "(bricks crossing a module end are split between both ends, same colour and jitter)",
            "modeled_brick_boxes": brick_count,
            "materials": ["BrickRed", "Mortar"],
            "bevel": f"modifier, {p['bevel_width'] * 1000:.0f} mm, 2 segments, harden normals; "
                     "no bevel on edges at the module ends (cuts)",
        },
    }

"""Square red-brick veranda pier (column) with plinth, oversail course and rowlock cap.

Two brick lengths square (0.49 m), with courses alternating direction so the corners are
bonded (staggered quoins). Same brick size, joints, plinth, oversail and coping heights as
RedBrickWall3m, so it stands at a wall-module join or free end (centred on the join line)
and covers the joint.

Frame: front faces -Y, Z up, origin = centre of the footprint on the ground, metres.
Modeling and materials only; the shared pipeline renders and exports.
"""

import bpy

from generators.red_brick_wall import DEFAULT_PARAMS as WALL_PARAMS, _brick_material, _brick_rand, _mortar_material
from pipeline.modeling import BoxBuilder

COLLECTION_NAME = "RedBrickPier"

DEFAULT_PARAMS = {
    **{k: WALL_PARAMS[k] for k in ("brick_length", "brick_height", "brick_depth", "joint", "joint_recess",
                                    "plinth_courses", "plinth_projection", "oversail_projection", "bevel_width")},
    "body_courses": 33,          # 2.64 m of courses
    "cap_projection": 0.040,     # rowlock cap overhang on every side (wall coping: 0.040)
    "cap_height": 0.16,          # same as the wall coping
    "cap_units": 7,
}


def _face_offset(p, course):
    if course < p["plinth_courses"]:
        return p["plinth_projection"]
    if course == p["body_courses"] - 1:
        return p["oversail_projection"]
    return 0.0


def _brick(builder, rng, x0, x1, y0, y1, z0, p):
    # Small hand-laid irregularities, as on the wall.
    builder.add(x0 + rng.uniform(0.0, 0.0015), x1 - rng.uniform(0.0, 0.0015),
                y0 - rng.uniform(-0.0015, 0.0015), y1 + rng.uniform(-0.0015, 0.0015),
                z0, z0 + p["brick_height"] - rng.uniform(0.0, 0.001),
                rand=_brick_rand(rng), material_index=0)


def _add_course(builder, rng, p, k, half):
    """Four faces of one course. Even courses: front and back run full width (two stretchers),
    the sides fit between them; odd courses the other way round, so corners interlock."""
    ch = p["brick_height"] + p["joint"]
    j, d = p["joint"], p["brick_depth"]
    h = half + _face_offset(p, k)
    z0 = k * ch
    inner = h - d - j
    full = ((-h, -j / 2.0), (j / 2.0, h))
    for s in (-1, 1):
        outer_band = sorted((s * h, s * (h - d)))
        if k % 2 == 0:
            for x0, x1 in full:                       # front/back stretchers
                _brick(builder, rng, x0, x1, *outer_band, z0, p)
            _brick(builder, rng, *outer_band, -inner, inner, z0, p)   # side brick between them
        else:
            for y0, y1 in full:                       # side stretchers
                _brick(builder, rng, *outer_band, y0, y1, z0, p)
            _brick(builder, rng, -inner, inner, *outer_band, z0, p)


def build(collection, rng, params):
    p = params
    ch = p["brick_height"] + p["joint"]
    body = p["body_courses"]
    half = p["brick_length"] + p["joint"] / 2.0      # 0.245: two bricks and a joint per face
    cap_half = half + p["cap_projection"]
    cap_z0 = body * ch
    top = cap_z0 + p["cap_height"]

    builder = BoxBuilder()
    for k in range(body):
        _add_course(builder, rng, p, k, half)

    pitch = 2.0 * cap_half / p["cap_units"]
    for i in range(p["cap_units"]):
        x0 = -cap_half + i * pitch + p["joint"] / 2.0
        x1 = x0 + pitch - p["joint"]
        builder.add(x0 + rng.uniform(0, 0.001), x1 - rng.uniform(0, 0.001),
                    -cap_half - rng.uniform(-0.001, 0.001), cap_half + rng.uniform(-0.001, 0.001),
                    cap_z0, top - rng.uniform(0.0, 0.0015), rand=_brick_rand(rng), material_index=0)
    brick_count = builder.box_count

    plinth_top = p["plinth_courses"] * ch
    oversail_z0 = (body - 1) * ch
    for (z0, z1, face) in (
        (0.0, plinth_top, half + p["plinth_projection"]),
        (plinth_top, oversail_z0, half),
        (oversail_z0, cap_z0, half + p["oversail_projection"]),
        (cap_z0, top - 0.004, cap_half),
    ):
        c = face - p["joint_recess"]
        builder.add(-c, c, -c, c, z0, z1, rand=0.5, material_index=1)

    mesh = builder.to_mesh("RedBrickPierMesh")
    obj = bpy.data.objects.new("RedBrickPier", mesh)
    collection.objects.link(obj)
    bevel = obj.modifiers.new("BrickBevel", "BEVEL")
    bevel.width = p["bevel_width"]
    bevel.segments = 2
    bevel.limit_method = "WEIGHT"
    bevel.harden_normals = True
    obj.data.materials.append(_brick_material())
    obj.data.materials.append(_mortar_material())

    return {
        "objects": [obj],
        "bounds_points_m": [(x, y, z) for x in (-cap_half, cap_half) for y in (-cap_half, cap_half)
                            for z in (0.0, top)],
        "footprint_m": [-half, half, -half, half],
        "info": {
            "design_size_m": {"width_x": 2 * half, "depth_y": 2 * half, "height_z": round(top, 4)},
            "bond": "square pier, two brick lengths per face; courses alternate direction (bonded corners)",
            "modeled_brick_boxes": brick_count,
            "materials": ["BrickRed", "Mortar"],
            "connection_point": "origin = footprint centre; stand it centred on a RedBrickWall3m join or free "
                                "end (x = k * 96 game px in a run); it is 0.49 m deep vs the wall's 0.30 m",
            "reference": "Docs/map-reference/area1/cds-building*.png (piers between arches; dimensions approximate)",
        },
    }

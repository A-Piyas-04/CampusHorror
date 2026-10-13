"""Pointed-arch doorway module for the red-brick wall run.

A 3.0 m wall module with a walk-through pointed-arch opening (open to the ground) under a
raised brick parapet. Outside |x| < parapet_half_width it is brick-for-brick the
RedBrickWall3m module (same seed, same RNG order), so it joins a wall run seamlessly at the
usual 96 game px spacing.

Proportions follow the CDS arcade photos loosely (plain brick equilateral pointed arch, no
stone trim); they are not surveyed. Modeling and materials only; camera, lights, rendering
and export are shared (pipeline/).
"""

import random

import bpy

from generators import brick_openings as bo
from generators.red_brick_wall import (DEFAULT_PARAMS as WALL_PARAMS, _add_course, _brick_material,
                                       _brick_rand, _mortar_material)
from pipeline.modeling import BoxBuilder

COLLECTION_NAME = "RedBrickArchDoorway"

DEFAULT_PARAMS = dict(
    WALL_PARAMS,
    opening_width=1.40,          # clear span between the jambs
    springing_courses=20,        # arch springs at 20 courses = 1.60 m
    ring_depth=0.235,            # radial depth of the voussoir ring (brick on end)
    ring_proud=0.012,            # ring stands this far proud of both faces
    jamb_widths=[0.11, 0.175],   # full-depth jamb bricks, alternating by course
    parapet_half_width=1.0,      # raised section |x| < this; the wall continues outside
    parapet_courses=12,          # courses above the wall's last course (2.24 m)
    interior_seed=101,           # colours of the bricks inside the raised section
)


def build(collection, rng, params):
    p = params
    ch = bo.course_height(p)
    body = p["body_courses"]
    half_l = p["length"] / 2.0
    half_t = p["thickness"] / 2.0
    cp = p["coping_projection"]
    a = p["opening_width"] / 2.0
    zs = p["springing_courses"] * ch
    ph = p["parapet_half_width"]
    top_course = body + p["parapet_courses"]
    coping_h = p["height"] - body * ch
    top = top_course * ch + coping_h
    arch = bo.PointedArch(a, zs, p["ring_depth"])
    jw = p["jamb_widths"]

    widest = max(a + max(jw), arch.extrados(zs)) + p["joint"]
    if widest >= ph:
        raise ValueError(f"opening and ring ({widest:.3f} m) must stay inside the parapet half-width {ph} m")
    if ph > half_l - 0.25:
        raise ValueError("the wall-identical ends must be at least 0.25 m long for the seam")
    if arch.apex_extrados + ch > top_course * ch:
        raise ValueError(f"ring apex {arch.apex_extrados:.3f} m needs more parapet courses")

    def void(z):
        if z < zs:
            return a + jw[int(z // ch) % len(jw)] + p["joint"]
        e = arch.extrados(z)
        return e + p["joint"] if e > 0.0 else 0.0

    def face_offset(k):
        if k < body:
            return bo.wall_face_offset(p, k)
        return p["oversail_projection"] if k == top_course - 1 else 0.0

    builder = BoxBuilder()
    interior = random.Random(p["interior_seed"])
    ob = bo.OpeningBuilder(builder, interior, ph)

    # Wall courses and coping in the wall's RNG order (identical ends); the middle is clipped.
    ob.void = void
    bo.lay_wall_courses(ob, rng, p)
    ob.void = lambda z: ph
    bo.lay_coping(ob, rng, p, half_l, body * ch, p["height"], p["coping_units"])

    # Raised parapet: the wall's bond continued over |x| < ph, oversail course and coping on top.
    ob.void = void
    parapet = dict(p, length=2.0 * ph)
    for k in range(body, top_course):
        _add_course(ob, interior, parapet, k * ch, face_offset(k), offset_half=bool(k % 2))
    coping_units = round(2.0 * (ph + cp) / (p["length"] / p["coping_units"]))
    bo.lay_coping(ob, interior, p, ph + cp, top_course * ch, top, coping_units)

    jamb_count = bo.lay_jambs(builder, interior, p, a, range(p["springing_courses"]), jw, face_offset)
    voussoirs = arch.lay_ring(builder, half_t + p["ring_proud"], p["joint"], ch, lambda: _brick_rand(interior))

    bo.mortar_bands(builder, p, [(-half_l, -ph), (ph, half_l)])
    # Under the parapet the oversail course is a string course with bricks above it: its core
    # stays at the plain face, or its top would show as a mortar ledge.
    bo.mortar_strips(builder, p, range(top_course), ph,
                     lambda z: a if z < zs else arch.intrados(z),
                     lambda k: 0.0 if k == body - 1 else face_offset(k))
    depth = half_t + cp - p["joint_recess"]
    builder.add(-(ph + cp) + p["joint"], ph + cp - p["joint"], -depth, depth,
                top_course * ch, top - 0.004, rand=0.5, material_index=1)

    box_count = builder.box_count
    mesh = builder.to_mesh("RedBrickArchDoorwayMesh", flush_x=(-half_l, half_l, -ph, ph))
    obj = bpy.data.objects.new("RedBrickArchDoorway", mesh)
    collection.objects.link(obj)
    bevel = obj.modifiers.new("BrickBevel", "BEVEL")
    bevel.width = p["bevel_width"]
    bevel.segments = 2
    bevel.limit_method = "WEIGHT"
    bevel.harden_normals = True
    obj.data.materials.append(_brick_material())
    obj.data.materials.append(_mortar_material())

    hb = half_t + cp
    bounds = [(x, y, z) for x in (-half_l, half_l) for y in (-hb, hb) for z in (0.0, p["height"])]
    bounds += [(x, y, top) for x in (-(ph + cp), ph + cp) for y in (-hb, hb)]
    return {
        "objects": [obj],
        "bounds_points_m": bounds,
        "footprint_m": [-half_l, half_l, -half_t, half_t],
        "tile_period_x_m": p["length"],
        "info": {
            "design_size_m": {"length_x": p["length"], "thickness_y": p["thickness"],
                              "height_at_ends_z": p["height"], "height_at_parapet_z": round(top, 4)},
            "opening_m": {"clear_width": p["opening_width"], "springing_z": round(zs, 4),
                          "apex_clear_height_z": round(arch.apex_intrados, 4),
                          "ring_apex_z": round(arch.apex_extrados, 4), "open_to_ground": True},
            "arch": "equilateral pointed arch (radius = clear span), radial voussoirs through the full "
                    f"wall depth, {voussoirs} pieces incl. keystone, {p['ring_proud'] * 1000:.0f} mm proud",
            "seam": f"identical to red_brick_wall_3m (same seed and RNG order) for |x| >= {ph} m; "
                    "bricks inside are clipped around the opening and recoloured from interior_seed",
            "connection_points_m": {"west_end_x": -half_l, "east_end_x": half_l,
                                    "note": "place in a RedBrickWall3m run at 3.0 m (96 game px) spacing"},
            "modeled_boxes_and_pieces": box_count,
            "jamb_bricks": jamb_count,
            "materials": ["BrickRed", "Mortar"],
            "reference": "Docs/map-reference/area1/cds-building*.png (style only; dimensions approximate)",
        },
    }

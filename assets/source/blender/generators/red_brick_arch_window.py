"""Pointed-arch window module for the red-brick wall run.

A 3.0 m wall module (same height as the wall) with a see-through pointed-arch window: a
projecting brick-on-edge sill, brick jambs, a radial voussoir ring and a dark painted steel
grille set into the brickwork. Outside |x| < middle_half_width it is brick-for-brick the
RedBrickWall3m module (same seed, same RNG order), so it joins a wall run seamlessly.

The arch style loosely follows the CDS photos; the grille is a design choice, not taken
from a reference. Modeling and materials only; the shared pipeline renders and exports.
"""

import random

import bpy

from generators import brick_openings as bo
from generators.red_brick_wall import DEFAULT_PARAMS as WALL_PARAMS, _brick_material, _brick_rand, _mortar_material
from pipeline.modeling import BoxBuilder, map_range, new_material, noise, socket

COLLECTION_NAME = "RedBrickArchWindow"

DEFAULT_PARAMS = dict(
    WALL_PARAMS,
    opening_width=0.80,          # clear span between the jambs
    sill_courses=10,             # opening starts on top of the sill at 10 courses = 0.80 m
    springing_courses=16,        # arch springs at 1.28 m
    ring_depth=0.115,            # radial depth of the voussoir ring (header on edge)
    ring_proud=0.012,
    jamb_widths=[0.11, 0.175],
    sill_projection=0.04,        # sill projects past the front face
    sill_overhang=0.10,          # sill runs past each jamb
    sill_units=12,
    middle_half_width=1.0,       # wall-identical outside |x| >= this
    grille_bar_xs=[-0.30, -0.15, 0.0, 0.15, 0.30],
    grille_bar_size=0.018,
    grille_flat_zs=[1.04, 1.52],
    grille_flat_height=0.04,
    grille_flat_thickness=0.008,
    grille_inset=0.06,           # grille plane behind the front face
    interior_seed=202,
)


def _steel_material():
    mat, nt, bsdf = new_material("PaintedSteel")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    rust = noise(nt, coords, 30.0, detail=4.0)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    nt.links.new(map_range(nt, rust.outputs["Fac"], 0.55, 0.75, 0.0, 0.45), socket(mix.inputs, "Factor_Float"))
    socket(mix.inputs, "A_Color").default_value = (0.022, 0.024, 0.026, 1.0)  # near-black paint
    socket(mix.inputs, "B_Color").default_value = (0.12, 0.045, 0.018, 1.0)   # rust
    nt.links.new(socket(mix.outputs, "Result_Color"), bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = 0.5
    nt.links.new(map_range(nt, rust.outputs["Fac"], 0.4, 0.75, 0.45, 0.85), bsdf.inputs["Roughness"])
    return mat


def build(collection, rng, params):
    p = params
    ch = bo.course_height(p)
    body = p["body_courses"]
    half_l = p["length"] / 2.0
    half_t = p["thickness"] / 2.0
    a = p["opening_width"] / 2.0
    sill_k = p["sill_courses"] - 1          # course replaced by the sill under the opening
    sill_z = p["sill_courses"] * ch
    zs = p["springing_courses"] * ch
    mid = p["middle_half_width"]
    arch = bo.PointedArch(a, zs, p["ring_depth"])
    jw = p["jamb_widths"]
    sill_half = a + p["sill_overhang"]

    widest = max(a + max(jw), sill_half, arch.extrados(zs)) + p["joint"]
    if widest >= mid:
        raise ValueError(f"opening ({widest:.3f} m) must stay inside the middle half-width {mid} m")
    if arch.apex_extrados + p["joint"] > body * ch:
        raise ValueError(f"ring apex {arch.apex_extrados:.3f} m runs into the coping at {body * ch:.3f} m")

    def void(z):
        k = int(z // ch)
        if k < sill_k:
            return 0.0
        if k == sill_k:
            return sill_half + p["joint"]
        if z < zs:
            return a + jw[k % len(jw)] + p["joint"]
        e = arch.extrados(z)
        return e + p["joint"] if e > 0.0 else 0.0

    def core_void(z):
        if z < sill_z:
            return 0.0
        return a if z < zs else arch.intrados(z)

    def face_offset(k):
        return bo.wall_face_offset(p, k)

    builder = BoxBuilder()
    interior = random.Random(p["interior_seed"])
    ob = bo.OpeningBuilder(builder, interior, mid)
    ob.void = void
    bo.lay_wall_courses(ob, rng, p)
    bo.lay_coping(ob, rng, p, half_l, body * ch, p["height"], p["coping_units"])

    # Brick-on-edge sill, projecting at the front; its top stands just above the mortar core
    # so the window bottom reads as brick.
    pitch = 2.0 * sill_half / p["sill_units"]
    for i in range(p["sill_units"]):
        x0 = -sill_half + i * pitch + p["joint"] / 2.0
        builder.add(x0 + interior.uniform(0, 0.001), x0 + pitch - p["joint"] - interior.uniform(0, 0.001),
                    -(half_t + p["sill_projection"]), half_t,
                    sill_k * ch, sill_z + 0.003, rand=_brick_rand(interior), material_index=0)

    jamb_count = bo.lay_jambs(builder, interior, p, a, range(p["sill_courses"], p["springing_courses"]),
                              jw, face_offset)
    voussoirs = arch.lay_ring(builder, half_t + p["ring_proud"], p["joint"], ch, lambda: _brick_rand(interior))

    bo.mortar_bands(builder, p, [(-half_l, -mid), (mid, half_l)])
    bo.mortar_strips(builder, p, range(body), mid, core_void, face_offset)
    depth = half_t + p["coping_projection"] - p["joint_recess"]
    builder.add(-mid, mid, -depth, depth, body * ch, p["height"] - 0.004, rand=0.5, material_index=1)

    # Grille: bars from the sill into the arch ring, two flats into the jambs / ring.
    yg = -half_t + p["grille_inset"]
    s = p["grille_bar_size"] / 2.0
    for x in p["grille_bar_xs"]:
        top = arch.intrados_z(abs(x) + s) + 0.03
        builder.add(x - s, x + s, yg - s, yg + s, sill_z - 0.02, top, rand=0.5, material_index=2)
    ft = p["grille_flat_thickness"] / 2.0
    for z in p["grille_flat_zs"]:
        reach = (a if z < zs else arch.intrados(z + p["grille_flat_height"])) + 0.02
        builder.add(-reach, reach, yg - ft, yg + ft, z, z + p["grille_flat_height"], rand=0.5, material_index=2)

    box_count = builder.box_count
    mesh = builder.to_mesh("RedBrickArchWindowMesh", flush_x=(-half_l, half_l, -mid, mid))
    obj = bpy.data.objects.new("RedBrickArchWindow", mesh)
    collection.objects.link(obj)
    bevel = obj.modifiers.new("BrickBevel", "BEVEL")
    bevel.width = p["bevel_width"]
    bevel.segments = 2
    bevel.limit_method = "WEIGHT"
    bevel.harden_normals = True
    obj.data.materials.append(_brick_material())
    obj.data.materials.append(_mortar_material())
    obj.data.materials.append(_steel_material())

    hb = half_t + p["coping_projection"]
    return {
        "objects": [obj],
        "bounds_points_m": [(x, y, z) for x in (-half_l, half_l) for y in (-hb, hb) for z in (0.0, p["height"])],
        "footprint_m": [-half_l, half_l, -half_t, half_t],
        "tile_period_x_m": p["length"],
        "info": {
            "design_size_m": {"length_x": p["length"], "thickness_y": p["thickness"], "height_z": p["height"]},
            "window_m": {"clear_width": p["opening_width"], "sill_top_z": round(sill_z, 4),
                         "springing_z": round(zs, 4), "apex_clear_height_z": round(arch.apex_intrados, 4),
                         "ring_apex_z": round(arch.apex_extrados, 4), "see_through": True},
            "arch": "equilateral pointed arch (radius = clear span), radial voussoirs through the full "
                    f"wall depth, {voussoirs} pieces incl. keystone, {p['ring_proud'] * 1000:.0f} mm proud",
            "grille": f"{len(p['grille_bar_xs'])} square bars {p['grille_bar_size'] * 1000:.0f} mm and "
                      f"{len(p['grille_flat_zs'])} flats, {p['grille_inset'] * 1000:.0f} mm behind the front face, "
                      "ends built into sill, jambs and ring (design choice, not from a reference)",
            "seam": f"identical to red_brick_wall_3m (same seed and RNG order) for |x| >= {mid} m; "
                    "bricks inside are clipped around the window and recoloured from interior_seed",
            "connection_points_m": {"west_end_x": -half_l, "east_end_x": half_l,
                                    "note": "place in a RedBrickWall3m run at 3.0 m (96 game px) spacing"},
            "modeled_boxes_and_pieces": box_count,
            "jamb_bricks": jamb_count,
            "materials": ["BrickRed", "Mortar", "PaintedSteel"],
            "reference": "Docs/map-reference/area1/cds-building*.png (arch style only; dimensions approximate)",
        },
    }

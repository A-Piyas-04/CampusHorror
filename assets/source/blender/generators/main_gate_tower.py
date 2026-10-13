"""Main Gate tower: the red-brick gatehouse with the large layered white pointed arch.

Reference: Docs/map-reference/area1/mainGate.jpg (front, from the road) and whole view.png
(aerial). The photo is taken from the road, which is the -Y (front) side here and the
camera side in game. Features: a deep red-brick block, a broad projecting light-grey roof
cap whose top is a recessed tray with a raised rim (aerial), a brick cornice band under the
cap, three stepped white arch rings around a tall two-centred pointed passage, a white
crest with a green disc above the left haunch and a round grey medallion on the right, and
an open through-passage (the opening is transparent so the real ground and the player
show through it). The arch is not centred on the block: the west brick margin is wider.

All dimensions are estimated from the photo and the aerial view, not surveyed.

Origin: on the ground at the arch axis, on the front plane of the outer white ring. The
brick face is `front_projection` behind it; the block ends at x = east_x, where the
boundary wall joins (x = 140 game px from the gate axis).
"""

import bmesh

from generators.landmark_common import (arch_apex_z, arch_outline, brick_shader_material, concrete_material,
                                        disc_y, finish_bmesh, finish_boxes, loft_rects, paint_material,
                                        strip_prism)
from pipeline.modeling import BoxBuilder, extreme_points

COLLECTION_NAME = "MainGateTower"

DEFAULT_PARAMS = {
    "west_x": -5.375,             # west face of the brick block (pavilion side)
    "east_x": 4.375,              # east face; boundary wall joins here
    "front_projection": 0.3403,   # outer ring front -> brick face (7 game px of screen depth)
    "depth": 6.40,                # brick face -> back face
    "height": 8.60,               # brick top (under the roof cap)
    "clear_half": 2.38,           # passage half-width
    "springing_z": 3.0,
    "centre_offset": 0.9,         # arc centres across the axis -> pointed apex
    "ring_widths": [0.28, 0.32, 0.42],   # inner, middle, outer white rings
    "ring_fronts": [0.22, 0.11, 0.0],    # stepped: the outer ring projects furthest
    "cornice_z": 7.95,
    "cornice_projection": 0.07,
    "roof_overhang": 1.25,
    "roof_edge_z": 9.25,          # underside of the flared rim edge
    "roof_rim_z": 9.55,           # top of the rim
    "roof_well_z": 9.05,          # recessed flat top
    "roof_rim_inset": 1.0,
}

WHITE = (0.80, 0.79, 0.75)          # linear; weathered white paint
CREST_GREEN = (0.03, 0.16, 0.08)
MEDALLION_GREY = (0.36, 0.36, 0.35)


def build(collection, rng, params):
    p = params
    fp, back = p["front_projection"], p["front_projection"] + p["depth"]
    west, east, top = p["west_x"], p["east_x"], p["height"]
    c, zs, d = p["clear_half"], p["springing_z"], p["centre_offset"]
    brick = brick_shader_material("GateBrick", seed=3.0)
    white = paint_material("GateWhite", WHITE, roughness=0.75, grime_low=0.7)

    # --- brick mass: two piers, the passage roof over the clear arch, cornice band, dentils
    piers = BoxBuilder()
    piers.add(west, -c, fp, back, 0.0, top)
    piers.add(c, east, fp, back, 0.0, top)
    cp = p["cornice_projection"]
    piers.add(west - cp, east + cp, fp - cp, back + cp, p["cornice_z"], top)
    dentil_z0, dentil_z1 = p["cornice_z"] - 0.16, p["cornice_z"] - 0.04
    x = west + 0.08
    while x + 0.12 < east:
        piers.add(x, x + 0.12, fp - 0.035, fp, dentil_z0, dentil_z1)
        x += 0.26
    brick_obj = finish_boxes(collection, "GateBrickMass", piers, [brick], bevel_width=0.008)

    bm = bmesh.new()
    clear = arch_outline(c, zs, d, jambs=False)
    strip_prism(bm, clear, [(x, top) for x, _ in clear], fp, back)
    vault = finish_bmesh(collection, "GatePassageVault", bm, [brick])

    # --- stepped white rings (each a closed band between two concentric pointed outlines)
    bm = bmesh.new()
    inner_half = c
    for width, front in zip(p["ring_widths"], p["ring_fronts"]):
        outer_half = inner_half + width
        strip_prism(bm, arch_outline(inner_half, zs, d), arch_outline(outer_half, zs, d), front, fp + 0.05)
        inner_half = outer_half
    rings = finish_bmesh(collection, "GateArchRings", bm, [white])
    outer_apex = arch_apex_z(inner_half, zs, d)

    # --- crest (white shield with a green disc) and grey medallion on the spandrels
    trim = BoxBuilder()
    cx, cz = -3.65, 6.35
    trim.add_prism_xz([(cx - 0.38, cz + 0.95), (cx + 0.38, cz + 0.95), (cx + 0.38, cz + 0.36),
                       (cx, cz), (cx - 0.38, cz + 0.36)], fp - 0.05, fp + 0.01)
    crest = finish_boxes(collection, "GateCrest", trim, [white], bevel_width=0.01)
    bm = bmesh.new()
    disc_y(bm, cx, cz + 0.56, 0.23, fp - 0.075, fp - 0.04)
    crest_disc = finish_bmesh(collection, "GateCrestDisc", bm,
                              [paint_material("GateCrestGreen", CREST_GREEN, roughness=0.6)], smooth=True)
    bm = bmesh.new()
    disc_y(bm, 3.3, 6.55, 0.34, fp - 0.06, fp + 0.01)
    disc_y(bm, 3.3, 6.55, 0.22, fp - 0.09, fp - 0.05)
    medallion = finish_bmesh(collection, "GateMedallion", bm,
                             [paint_material("GateMedallionGrey", MEDALLION_GREY, roughness=0.5)], smooth=True)

    # --- roof cap: flares out from the brick top, raised rim, recessed tray (aerial view)
    o, inset = p["roof_overhang"], p["roof_rim_inset"]
    bm = bmesh.new()
    loft_rects(bm, [
        (west, east, fp, back, top),
        (west - o, east + o, fp - o, back + o, p["roof_edge_z"]),
        (west - o, east + o, fp - o, back + o, p["roof_rim_z"]),
        (west - o + inset, east + o - inset, fp - o + inset, back + o - inset, p["roof_well_z"]),
    ])
    roof = finish_bmesh(collection, "GateRoofCap", bm, [concrete_material("GateRoofConcrete")])

    objects = [brick_obj, vault, rings, crest, crest_disc, medallion, roof]
    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": [west, east, 0.0, back],
        "info": {
            "design_size_m": {"width_x": round(east - west, 4), "depth_y": round(back, 4),
                              "height_z": p["roof_rim_z"]},
            "passage_clear_width_m": 2 * c,
            "clear_apex_m": round(arch_apex_z(c, zs, d), 3),
            "outer_ring_apex_m": round(outer_apex, 3),
            "materials": ["GateBrick (procedural running bond, RedBrickWall3m colours)", "GateWhite",
                          "GateRoofConcrete", "GateCrestGreen", "GateMedallionGrey"],
            "connection_point": "origin = arch axis on the outer-ring front plane; brick face 7 game px behind "
                                "(place the node 7 px south of the wall line); east face at +140 game px = "
                                "boundary wall start",
            "reference": "Docs/map-reference/area1/mainGate.jpg (front) + whole view.png (aerial); dimensions "
                         "estimated, not surveyed",
        },
    }

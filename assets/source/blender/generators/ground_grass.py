"""Seamless top-down lawn tile, optionally with worn / trampled patches.

One flat 2 m tile with a layered, periodic shader: broad lush/dry colour patches, clump
brightness, blade speckle and a few clover patches, with bump so the clumps catch the shared
key sun. `wear` > 0 mixes in trampled grass and bare soil through a mask that is zero within
`wear_border_m` of the tile edge. The node tree is identical for every `wear` (the mask is
only multiplied by it), so a worn tile's border is pixel-for-pixel the plain grass tile and
the two mix freely in one TileMapLayer.

Frame: tile centred on the origin, Z up; seen straight down. Metres.
"""

from generators.ground_common import (add_bump, border_fade, flat_tile, math_node, mix_color, pnoise, pvoronoi,
                                      tile_result, torus)
from pipeline.modeling import map_range, multiply_color, new_material

COLLECTION_NAME = "GroundGrass"

DEFAULT_PARAMS = {
    "period": 2.0,
    "wear": 0.0,              # 0 = plain lawn; 1 = full worn patches
    "wear_border_m": 0.16,    # no wear this close to the tile edge
    "wear_fade_m": 0.30,
    "wear_offset": 0.0,       # shifts the wear noise (picks a different patch shape)
}

# Linear-space colours (approximate sRGB in comments).
LUSH = (0.060, 0.150, 0.026)      # ~ (0.27, 0.42, 0.18)
DRY = (0.150, 0.175, 0.045)       # ~ (0.42, 0.46, 0.24)
CLOVER = (0.035, 0.115, 0.030)    # ~ (0.21, 0.37, 0.19)
TRAMPLED = (0.170, 0.150, 0.060)  # ~ (0.45, 0.42, 0.27)
SOIL = (0.200, 0.135, 0.070)      # ~ (0.49, 0.40, 0.29)
PEBBLE = (0.330, 0.300, 0.250)    # ~ (0.61, 0.58, 0.54)


def _material(p):
    mat, nt, bsdf = new_material("Lawn")
    t = torus(nt, p["period"])

    # Broad colour patches stay subtle: anything this large repeats every 2 m.
    patches = pnoise(nt, t, 1.0, detail=2.0, offset=1.0)
    color = mix_color(nt, map_range(nt, patches.outputs["Fac"], 0.35, 0.65, 0.05, 0.45), LUSH, DRY)
    clover = pnoise(nt, t, 3.2, detail=2.0, offset=2.0)
    color = mix_color(nt, map_range(nt, clover.outputs["Fac"], 0.60, 0.68, 0.0, 0.7), color, CLOVER)

    # Tufts: Voronoi cells (~10 cm) bright in the middle, dark between, broken up by noise.
    clumps = pnoise(nt, t, 7.0, detail=3.0, roughness=0.6, offset=3.0)
    tufts = pvoronoi(nt, t, 10.0, offset=8.0)
    blades = pvoronoi(nt, t, 38.0, offset=4.0)
    speckle = pnoise(nt, t, 70.0, detail=2.0, offset=5.0)
    color = multiply_color(nt, color, map_range(nt, clumps.outputs["Fac"], 0.3, 0.7, 0.85, 1.1))
    color = multiply_color(nt, color, map_range(nt, tufts.outputs["Distance"], 0.1, 0.75, 1.14, 0.72))
    color = multiply_color(nt, color, map_range(nt, blades.outputs["Distance"], 0.0, 0.8, 1.10, 0.86))
    color = multiply_color(nt, color, map_range(nt, speckle.outputs["Fac"], 0.35, 0.65, 0.88, 1.1))

    # Wear: noise blobs away from the tile border. Low values trample/yellow the grass,
    # high values expose soil with pebbles. Multiplied by `wear` (0 -> identical to the lawn).
    wear_noise = pnoise(nt, t, 1.1, detail=3.0, roughness=0.6, offset=6.0 + p["wear_offset"])
    fade = border_fade(nt, p["period"], p["wear_border_m"], p["wear_fade_m"])
    # 4D noise rarely leaves 0.4-0.6, so the window is narrow to get large, irregular patches.
    raw = map_range(nt, wear_noise.outputs["Fac"], 0.44, 0.53, 0.0, 1.0)
    mask = math_node(nt, "MULTIPLY", math_node(nt, "MULTIPLY", raw, fade), p["wear"])
    # Ragged edge: the blade pattern breaks the mask up so grass tufts survive inside patches.
    ragged = math_node(nt, "SUBTRACT", mask, map_range(nt, blades.outputs["Distance"], 0.0, 0.8, 0.0, 0.35))
    trampled = map_range(nt, mask, 0.0, 0.45, 0.0, 1.0)
    bare = map_range(nt, ragged, 0.4, 0.58, 0.0, 1.0)

    soil = multiply_color(nt, mix_color(nt, map_range(nt, pvoronoi(nt, t, 22.0, offset=7.0).outputs["Distance"],
                                                      0.0, 0.18, 1.0, 0.0), SOIL, PEBBLE),
                          map_range(nt, speckle.outputs["Fac"], 0.3, 0.7, 0.85, 1.1))
    color = mix_color(nt, trampled, color, multiply_color(nt, mix_color(nt, 0.55, color, TRAMPLED),
                                                          map_range(nt, clumps.outputs["Fac"], 0.3, 0.7, 0.9, 1.05)))
    color = mix_color(nt, bare, color, soil)
    nt.links.new(color, bsdf.inputs["Base Color"])
    nt.links.new(map_range(nt, bare, 0.0, 1.0, 0.82, 0.95), bsdf.inputs["Roughness"])

    # Relief: clumps and blades on the grass, flattened where it is worn.
    relief = math_node(nt, "ADD", map_range(nt, tufts.outputs["Distance"], 0.0, 0.8, 1.0, 0.0),
                       math_node(nt, "MULTIPLY", map_range(nt, blades.outputs["Distance"], 0.0, 0.8, 0.6, 0.0), 0.8))
    relief = math_node(nt, "MULTIPLY", relief, map_range(nt, bare, 0.0, 1.0, 1.0, 0.35))
    add_bump(nt, bsdf, relief, 0.55, 0.02)
    return mat


def build(collection, rng, params):
    p = params
    tile = flat_tile(collection, "GroundGrass", p["period"])
    tile.data.materials.append(_material(p))
    return tile_result([tile], p["period"], 0.0, {
        "design_size_m": {"x": p["period"], "y": p["period"]},
        "surface": "flat tile, layered periodic (4D torus) lawn shader with bump",
        "wear": p["wear"],
        "wear_border_m": p["wear_border_m"],
        "materials": ["Lawn"],
    })

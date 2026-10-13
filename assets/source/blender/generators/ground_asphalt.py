"""Seamless top-down road tile: weathered asphalt, no lane markings.

A flat tile with a periodic shader: sun-bleached grey binder, coarse aggregate speckle,
low-contrast darker patching, faint hairline cracks and fine grain bump. Contrast is kept low
so the 2 m repetition doesn't read as a pattern across a road.

Frame: tile centred on the origin, Z up; seen straight down. Metres.
"""

from generators.ground_common import add_bump, flat_tile, math_node, mix_color, pnoise, pvoronoi, tile_result, torus
from pipeline.modeling import map_range, multiply_color, new_material

COLLECTION_NAME = "GroundAsphalt"

DEFAULT_PARAMS = {
    "period": 2.0,
    "crack_amount": 0.85,
}

BINDER = (0.062, 0.062, 0.066)     # ~ sRGB (0.28, 0.28, 0.29)
AGGREGATE = (0.150, 0.145, 0.135)  # ~ sRGB (0.42, 0.42, 0.40)
PATCH = (0.035, 0.035, 0.038)      # ~ sRGB (0.21, 0.21, 0.22)
CRACK = (0.018, 0.018, 0.020)


def _material(p):
    mat, nt, bsdf = new_material("Asphalt")
    t = torus(nt, p["period"])

    # Aggregate is exaggerated (~6 cm speckle) so it survives at 3 cm per pixel.
    stones = pvoronoi(nt, t, 16.0, offset=1.0)
    grain = pnoise(nt, t, 45.0, detail=3.0, offset=2.0)
    # 4D noise / Voronoi have a narrower value range than 3D: remap windows are tighter.
    color = mix_color(nt, map_range(nt, stones.outputs["Distance"], 0.3, 0.6, 0.85, 0.0), BINDER, AGGREGATE)
    color = multiply_color(nt, color, map_range(nt, grain.outputs["Fac"], 0.42, 0.58, 0.72, 1.25))

    broad = pnoise(nt, t, 1.2, detail=3.0, offset=3.0)
    color = multiply_color(nt, color, map_range(nt, broad.outputs["Fac"], 0.42, 0.58, 0.86, 1.08))
    patch = pnoise(nt, t, 0.8, detail=2.0, roughness=0.4, offset=4.0)
    patch_mask = map_range(nt, patch.outputs["Fac"], 0.60, 0.63, 0.0, 0.55)
    color = mix_color(nt, patch_mask, color, multiply_color(nt, mix_color(nt, 0.6, color, PATCH),
                                                              map_range(nt, grain.outputs["Fac"], 0.3, 0.7, 0.9, 1.1)))

    cells = pvoronoi(nt, t, 1.6, feature="DISTANCE_TO_EDGE", offset=5.0)
    crack_line = map_range(nt, cells.outputs["Distance"], 0.0, 0.025, 1.0, 0.0)
    crack_where = map_range(nt, pnoise(nt, t, 2.0, detail=2.0, offset=6.0).outputs["Fac"], 0.52, 0.6, 0.0, 1.0)
    crack = math_node(nt, "MULTIPLY", math_node(nt, "MULTIPLY", crack_line, crack_where), p["crack_amount"])
    color = mix_color(nt, crack, color, CRACK)
    nt.links.new(color, bsdf.inputs["Base Color"])
    nt.links.new(map_range(nt, stones.outputs["Distance"], 0.3, 0.6, 0.7, 0.92), bsdf.inputs["Roughness"])

    relief = math_node(nt, "SUBTRACT", map_range(nt, stones.outputs["Distance"], 0.3, 0.6, 1.0, 0.0),
                       math_node(nt, "MULTIPLY", crack, 1.5))
    add_bump(nt, bsdf, relief, 0.35, 0.006)
    return mat


def build(collection, rng, params):
    p = params
    tile = flat_tile(collection, "GroundAsphalt", p["period"])
    tile.data.materials.append(_material(p))
    return tile_result([tile], p["period"], 0.0, {
        "design_size_m": {"x": p["period"], "y": p["period"]},
        "surface": "flat tile, periodic (4D torus) asphalt shader: aggregate, patching, hairline cracks, bump",
        "markings": "none",
        "materials": ["Asphalt"],
    })

"""Seamless top-down paved walkway tile: 0.5 m slabs in running bond (grey concrete by default;
slab and joint colours are parameters).

Modeled slabs (bevelled boxes, small height and tone jitter per slab) on a dark gritty joint
bed. Slab centres are kept inside [-period/2, period/2) so the slabs that cross a tile edge
are continued, not duplicated, by the neighbour copy the pipeline places one period away.
Rows are offset by half a slab every other row; slab edges sit a quarter slab off the tile
edges, so no joint runs along a tile edge. Ambient occlusion darkens the joints.

Frame: tile centred on the origin, Z up; seen straight down. Metres.
"""

import bpy

from generators.ground_common import add_bump, flat_tile, mix_color, pnoise, tile_result, torus
from pipeline.modeling import BoxBuilder, map_range, multiply_color, new_material

COLLECTION_NAME = "GroundPaving"

DEFAULT_PARAMS = {
    "period": 2.0,
    "slab": 0.5,
    "joint": 0.022,
    "slab_height": 0.05,
    "height_jitter": 0.004,
    "bevel_width": 0.008,
    "slab_color": [0.300, 0.290, 0.262],   # linear RGB; ~ sRGB (0.58, 0.57, 0.55) grey concrete
    "joint_color": [0.060, 0.055, 0.045],  # linear RGB; ~ sRGB (0.27, 0.26, 0.23)
}

MOSS = (0.050, 0.070, 0.025)       # ~ sRGB (0.25, 0.29, 0.17)


def _slab_material(p):
    mat, nt, bsdf = new_material("ConcreteSlab")
    t = torus(nt, p["period"])
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    attr.attribute_name = "brick_rand"
    color = multiply_color(nt, _rgb(nt, p["slab_color"]), map_range(nt, attr.outputs["Fac"], 0.0, 1.0, 0.90, 1.08))

    stains = pnoise(nt, t, 1.6, detail=3.0, offset=1.0)
    mottle = pnoise(nt, t, 9.0, detail=4.0, offset=2.0)
    grit = pnoise(nt, t, 60.0, detail=2.0, offset=3.0)
    color = multiply_color(nt, color, map_range(nt, stains.outputs["Fac"], 0.35, 0.65, 0.88, 1.03))
    color = multiply_color(nt, color, map_range(nt, mottle.outputs["Fac"], 0.3, 0.7, 0.92, 1.06))
    color = multiply_color(nt, color, map_range(nt, grit.outputs["Fac"], 0.3, 0.7, 0.93, 1.05))

    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.05
    ao.samples = 8
    color = multiply_color(nt, color, map_range(nt, ao.outputs["AO"], 0.4, 1.0, 0.72, 1.0))
    nt.links.new(color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    add_bump(nt, bsdf, mottle.outputs["Fac"], 0.25, 0.004)
    return mat


def _joint_material(p):
    mat, nt, bsdf = new_material("JointGrit")
    t = torus(nt, p["period"])
    moss = pnoise(nt, t, 4.0, detail=3.0, offset=4.0)
    color = mix_color(nt, map_range(nt, moss.outputs["Fac"], 0.5, 0.65, 0.0, 0.8), _rgb(nt, p["joint_color"]), MOSS)
    color = multiply_color(nt, color, map_range(nt, pnoise(nt, t, 80.0, offset=5.0).outputs["Fac"], 0.3, 0.7, 0.75, 1.15))
    nt.links.new(color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.97
    return mat


def _rgb(nt, c):
    node = nt.nodes.new("ShaderNodeRGB")
    node.outputs["Color"].default_value = (*c, 1.0)
    return node.outputs["Color"]


def build(collection, rng, params):
    p = params
    period, s, j = p["period"], p["slab"], p["joint"]
    n = round(period / s)
    if abs(n * s - period) > 1e-9:
        raise ValueError("period must be a whole number of slabs")
    half = period / 2.0
    builder = BoxBuilder()
    for row in range(n):
        y_c = -half + s / 4.0 + row * s + s / 2.0          # rows a quarter slab off the tile edge
        x_shift = s / 4.0 + (s / 2.0 if row % 2 else 0.0)  # running bond
        for k in range(n):
            x_c = -half + x_shift + k * s
            if x_c >= half:
                x_c -= period
            if y_c >= half:
                y_c -= period
            top = p["slab_height"] + rng.uniform(-p["height_jitter"], p["height_jitter"])
            builder.add(x_c - s / 2 + j / 2, x_c + s / 2 - j / 2, y_c - s / 2 + j / 2, y_c + s / 2 - j / 2,
                        0.0, top, rand=rng.random(), material_index=0)
    mesh = builder.to_mesh("PavingSlabsMesh")
    slabs = bpy.data.objects.new("PavingSlabs", mesh)
    collection.objects.link(slabs)
    bevel = slabs.modifiers.new("SlabBevel", "BEVEL")
    bevel.width = p["bevel_width"]
    bevel.segments = 2
    bevel.limit_method = "WEIGHT"
    bevel.harden_normals = True
    slabs.data.materials.append(_slab_material(p))

    bed = flat_tile(collection, "JointBed", period, z=0.02)
    bed.data.materials.append(_joint_material(p))
    return tile_result([slabs, bed], period, p["slab_height"] + p["height_jitter"], {
        "design_size_m": {"x": period, "y": period},
        "surface": f"{n * n} modeled {s} m slabs, running bond, {j * 1000:.0f} mm joints, "
                   "bevelled, height/tone jitter per slab; AO-darkened joints",
        "materials": ["ConcreteSlab", "JointGrit"],
    })

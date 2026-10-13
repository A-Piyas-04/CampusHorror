"""Flagpole on a small concrete base (CDS lawn: photo cds-building.png shows two poles in front of
the canteen wing, one with the Bangladesh flag, one with a white flag).

Origin: centre of the base on the ground. The flag hangs from the top towards +X (east) with a
gentle wave, facing the camera (-Y). Dimensions estimated from the photo.
"""

import math

import bmesh

from generators.landmark_common import concrete_material, finish_bmesh, paint_material
from pipeline.modeling import add_lathe, extreme_points, new_material, socket

COLLECTION_NAME = "FlagPole"

DEFAULT_PARAMS = {
    "flag": "bangladesh",      # "bangladesh" (green field, red disc) or "white"
    "height": 6.0,
    "flag_length": 1.5,
    "flag_height": 0.9,        # Bangladesh flag ratio 10:6
    "base_half": 0.25,
    "base_height": 0.25,
    "wave_amplitude": 0.06,
}

GREEN = (0.0, 0.144, 0.077)    # linear of sRGB #006A4E
RED = (0.905, 0.024, 0.052)    # linear of sRGB #F42A41
WHITE = (0.80, 0.80, 0.77)
POLE = (0.62, 0.62, 0.60)


def _bangladesh_material(x0, z_top, length, height):
    """Green field with a red disc centred at 9/20 of the length from the hoist, radius length / 5."""
    mat, nt, bsdf = new_material("FlagBangladesh")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coords, sep.inputs["Vector"])
    flat = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], flat.inputs["X"])
    nt.links.new(sep.outputs["Z"], flat.inputs["Z"])
    dist = nt.nodes.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    nt.links.new(flat.outputs["Vector"], dist.inputs[0])
    dist.inputs[1].default_value = (x0 + length * 0.45, 0.0, z_top - height / 2.0)
    disc = nt.nodes.new("ShaderNodeMath")
    disc.operation = "LESS_THAN"
    nt.links.new(dist.outputs["Value"], disc.inputs[0])
    disc.inputs[1].default_value = length / 5.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(disc.outputs[0], socket(mix.inputs, "Factor_Float"))
    socket(mix.inputs, "A_Color").default_value = (*GREEN, 1.0)
    socket(mix.inputs, "B_Color").default_value = (*RED, 1.0)
    nt.links.new(socket(mix.outputs, "Result_Color"), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def build(collection, rng, params):
    p = params
    h, bh, b = p["height"], p["base_height"], p["base_half"]

    bm = bmesh.new()
    verts = [bm.verts.new(c) for c in ((-b, -b, 0), (b, -b, 0), (b, b, 0), (-b, b, 0),
                                       (-b, -b, bh), (b, -b, bh), (b, b, bh), (-b, b, bh))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)):
        bm.faces.new([verts[i] for i in f])
    base = finish_bmesh(collection, "FlagPoleBase", bm, [concrete_material("FlagPoleBaseConcrete")])

    bm = bmesh.new()
    add_lathe(bm, [(0.05, bh), (0.045, bh + 0.3), (0.03, h), (0.0, h)], sides=12)
    add_lathe(bm, [(0.0, h - 0.01)] + [(0.05 * math.sin(math.pi * k / 6), h + 0.05 - 0.05 * math.cos(math.pi * k / 6))
                                        for k in range(1, 6)] + [(0.0, h + 0.1)], sides=12)
    pole = finish_bmesh(collection, "FlagPolePole", bm,
                        [paint_material("FlagPolePaint", POLE, roughness=0.4, variation=0.04, grime_low=0.9)],
                        smooth=True)

    length, fh, amp = p["flag_length"], p["flag_height"], p["wave_amplitude"]
    x0, z_top = 0.04, h - 0.08
    nu, nv = 24, 8
    bm = bmesh.new()
    grid = [[bm.verts.new((x0 + length * i / nu,
                           amp * (i / nu) * math.sin(2.0 * math.pi * 1.6 * i / nu),
                           z_top - fh * j / nv - 0.05 * (i / nu) ** 2))
             for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]))
    flag_mat = (_bangladesh_material(x0, z_top, length, fh) if p["flag"] == "bangladesh"
                else paint_material("FlagWhite", WHITE, roughness=0.8, variation=0.06, grime_low=1.0))
    flag = finish_bmesh(collection, "FlagCloth", bm, [flag_mat], smooth=True)

    objects = [base, pole, flag]
    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": [-b, b, -b, b],
        "info": {
            "design_size_m": {"pole_height": h, "flag": [length, fh], "base": [2 * b, 2 * b, bh]},
            "flag": p["flag"],
            "materials": ["FlagPoleBaseConcrete", "FlagPolePaint", "FlagBangladesh or FlagWhite"],
            "reference": "Docs/map-reference/area1/cds-building.png (two flagpoles on the canteen lawn); "
                         "dimensions estimated",
        },
    }

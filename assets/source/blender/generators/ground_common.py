"""Helpers shared by the ground-tile generators (not a generator itself).

Ground tiles are one square period centred on the origin; the pipeline renders them straight
down between 8 neighbour copies. Everything here is periodic over that period, so a tile
continues seamlessly into copies of itself:

- `torus()` maps object X and Y onto two circles (a 4D torus) whose circumference is the
  period. 4D noise / Voronoi sampled there is periodic in X and Y, and because the radius is
  period / 2pi, a node's Scale still means features per metre.
- Geometry must either stay inside the period or be built so that whatever crosses an edge is
  continued by the neighbour copy (see ground_paving.py).
"""

import math

import bpy

from pipeline.modeling import map_range, socket

TAU = 2.0 * math.pi


def _math(nt, op, a, b=None):
    node = nt.nodes.new("ShaderNodeMath")
    node.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            node.inputs[i].default_value = v
        else:
            nt.links.new(v, node.inputs[i])
    return node.outputs["Value"]


def torus(nt, period):
    """(vector, w) sockets: object XY wrapped onto a 4D torus with circumference `period`."""
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coords, sep.inputs["Vector"])
    radius = period / TAU
    out = []
    for axis in ("X", "Y"):
        angle = _math(nt, "MULTIPLY", sep.outputs[axis], TAU / period)
        out.append(_math(nt, "MULTIPLY", _math(nt, "COSINE", angle), radius))
        out.append(_math(nt, "MULTIPLY", _math(nt, "SINE", angle), radius))
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, name in enumerate(("X", "Y", "Z")):
        nt.links.new(out[i], comb.inputs[name])
    return comb.outputs["Vector"], out[3]


def _offset(nt, t, offset):
    vec, w = t
    if not offset:
        return vec, w
    add = nt.nodes.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    nt.links.new(vec, add.inputs[0])
    add.inputs[1].default_value = (offset * 1.37, offset * -2.11, offset * 0.73)
    return add.outputs["Vector"], _math(nt, "ADD", w, offset * 3.19)


def pnoise(nt, t, scale, detail=4.0, roughness=0.55, distortion=0.0, offset=0.0):
    """Periodic 4D noise texture node (use .outputs["Fac"])."""
    vec, w = _offset(nt, t, offset)
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = "4D"
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = roughness
    n.inputs["Distortion"].default_value = distortion
    nt.links.new(vec, n.inputs["Vector"])
    nt.links.new(w, n.inputs["W"])
    return n


def pvoronoi(nt, t, scale, feature="F1", randomness=1.0, offset=0.0):
    """Periodic 4D Voronoi texture node (outputs "Distance", "Color")."""
    vec, w = _offset(nt, t, offset)
    v = nt.nodes.new("ShaderNodeTexVoronoi")
    v.voronoi_dimensions = "4D"
    v.feature = feature
    v.inputs["Scale"].default_value = scale
    v.inputs["Randomness"].default_value = randomness
    nt.links.new(vec, v.inputs["Vector"])
    nt.links.new(w, v.inputs["W"])
    return v


def border_fade(nt, period, start_m, width_m):
    """0 within `start_m` of the tile edge, rising to 1 over `width_m` further in."""
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coords, sep.inputs["Vector"])
    edge = _math(nt, "MAXIMUM", _math(nt, "ABSOLUTE", sep.outputs["X"]), _math(nt, "ABSOLUTE", sep.outputs["Y"]))
    inset = _math(nt, "SUBTRACT", period / 2.0, edge)
    return map_range(nt, inset, start_m, start_m + width_m, 0.0, 1.0)


def mix_color(nt, factor, a, b):
    """Linear mix of two colour sockets/values by a factor socket."""
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    for sock, val in ((socket(mix.inputs, "A_Color"), a), (socket(mix.inputs, "B_Color"), b)):
        if isinstance(val, tuple):
            sock.default_value = val if len(val) == 4 else (*val, 1.0)
        else:
            nt.links.new(val, sock)
    if isinstance(factor, (int, float)):
        socket(mix.inputs, "Factor_Float").default_value = factor
    else:
        nt.links.new(factor, socket(mix.inputs, "Factor_Float"))
    return socket(mix.outputs, "Result_Color")


def add_bump(nt, bsdf, height, strength, distance):
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bump


def math_node(nt, op, a, b=None):
    return _math(nt, op, a, b)


def flat_tile(collection, name, period, z=0.0):
    """One quad covering exactly the tile [-period/2, period/2]^2 at height z."""
    h = period / 2.0
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata([(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)], [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def tile_result(objects, period, top_z, info):
    h = period / 2.0
    return {
        "objects": objects,
        "bounds_points_m": [(x, y, z) for x in (-h, h) for y in (-h, h) for z in (0.0, top_z)],
        "footprint_m": [-h, h, -h, h],
        "tile_period_m": period,
        "info": info,
    }

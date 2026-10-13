"""Campus lamp post: concrete plinth, tapered dark-green steel pole with collars and a
four-sided lantern (frosted glass panes, hipped roof). About 4.4 m tall.

The lamp is unlit in the sprite; night light comes from Godot lights (Docs/CONVENTIONS.md §10).

Frame: origin = centre of the plinth on the ground, front faces -Y, Z up, metres.
Modeling and materials only; the shared pipeline renders and exports.
"""

import math

import bmesh
import bpy

from pipeline.modeling import (BoxBuilder, add_lathe, extreme_points, map_range, mesh_object, multiply_color,
                               new_material, noise)

COLLECTION_NAME = "LampPost"

DEFAULT_PARAMS = {
    "plinth_half": 0.15,
    "plinth_height": 0.22,
}

POLE_PROFILE = [(0.10, 0.22), (0.10, 0.30), (0.085, 0.34), (0.07, 0.40), (0.07, 0.70), (0.085, 0.74),
                (0.06, 0.80), (0.05, 2.20), (0.045, 3.50), (0.062, 3.53), (0.062, 3.58), (0.04, 3.62), (0.04, 3.70)]
LANTERN_BASE = [(0.0, 3.70), (0.10, 3.72), (0.14, 3.76)]
LANTERN_GLASS = [(0.14, 3.76), (0.19, 4.08)]
LANTERN_ROOF = [(0.19, 4.08), (0.25, 4.10), (0.25, 4.125), (0.06, 4.30), (0.02, 4.38), (0.0, 4.40)]


def _metal():
    mat, nt, bsdf = new_material("LampMetal")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (0.020, 0.040, 0.028, 1.0)
    wear = noise(nt, coords, 18.0, detail=4.0)
    nt.links.new(multiply_color(nt, base.outputs["Color"], map_range(nt, wear.outputs["Fac"], 0.3, 0.7, 0.8, 1.2)),
                 bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.42
    bsdf.inputs["Metallic"].default_value = 0.35
    return mat


def _glass():
    mat, nt, bsdf = new_material("LampGlass")
    bsdf.inputs["Base Color"].default_value = (0.62, 0.57, 0.44, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.25
    return mat


def _concrete():
    mat, nt, bsdf = new_material("PlinthConcrete")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (0.26, 0.25, 0.23, 1.0)
    n = noise(nt, coords, 30.0, detail=5.0)
    color = multiply_color(nt, base.outputs["Color"], map_range(nt, n.outputs["Fac"], 0.3, 0.7, 0.8, 1.1))
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    color = multiply_color(nt, color, map_range(nt, sep.outputs["Z"], 0.0, 0.15, 0.7, 1.0))
    nt.links.new(color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    return mat


def build(collection, rng, params):
    p = params
    ph, hh = p["plinth_height"], p["plinth_half"]

    plinth_b = BoxBuilder()
    plinth_b.add(-hh, hh, -hh, hh, 0.0, ph - 0.03)
    plinth_b.add(-hh + 0.02, hh - 0.02, -hh + 0.02, hh - 0.02, ph - 0.03, ph)
    mesh = plinth_b.to_mesh("PlinthMesh")
    plinth = bpy.data.objects.new("Plinth", mesh)
    collection.objects.link(plinth)
    bevel = plinth.modifiers.new("Bevel", "BEVEL")
    bevel.width = 0.012
    bevel.segments = 2
    bevel.limit_method = "WEIGHT"
    plinth.data.materials.append(_concrete())

    bm = bmesh.new()
    add_lathe(bm, POLE_PROFILE, sides=16)
    pole = mesh_object(collection, "Pole", bm, [_metal()], smooth=True)

    lb = bmesh.new()
    quarter = math.pi / 4
    for prof, index in ((LANTERN_BASE, 0), (LANTERN_ROOF, 0)):
        add_lathe(lb, prof, sides=4, angle_offset=quarter)
    for f in add_lathe(lb, LANTERN_GLASS, sides=4, angle_offset=quarter):
        f.material_index = 1
    for k in range(4):  # corner posts of the lantern frame
        a = quarter + k * math.pi / 2
        add_lathe(lb, [(0.012, 3.76), (0.012, 4.09)], sides=4,
                  center=(0.165 * math.cos(a), 0.165 * math.sin(a)))
    lantern = mesh_object(collection, "Lantern", lb, [_metal(), _glass()])

    objects = [plinth, pole, lantern]
    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": [-hh, hh, -hh, hh],
        "info": {
            "design_size_m": {"height": LANTERN_ROOF[-1][1], "plinth": 2 * hh},
            "lit": "no (unlit by day; Godot lights provide night light)",
            "materials": ["PlinthConcrete", "LampMetal", "LampGlass"],
        },
    }

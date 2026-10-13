"""Outdoor park bench: weathered wooden slats on a dark-green painted steel frame.

Two end frames (legs, seat rail, foot rail, arm post and armrest) plus a centre support,
four seat slats and a backrest of three slats tilted back 14 degrees. Bevelled boxes
(BoxBuilder); the backrest is its own object rotated about its bottom edge. Faces the
camera (sits facing -Y).

Frame: origin = centre of the footprint on the ground, front faces -Y, Z up, metres.
Modeling and materials only; the shared pipeline renders and exports.
"""

import math

import bpy

from pipeline.modeling import BoxBuilder, extreme_points, map_range, multiply_color, new_material, noise, socket

COLLECTION_NAME = "Bench"

DEFAULT_PARAMS = {
    "length": 1.80,
    "seat_height": 0.455,
    "back_tilt_deg": 14.0,
    "frame_x": 0.78,
    "bevel_width": 0.005,
}


def _wood_material():
    mat, nt, bsdf = new_material("BenchWood")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.6, 30.0, 30.0)    # grain runs along the slats (X)
    nt.links.new(coords, mapping.inputs["Vector"])
    grain = noise(nt, mapping.outputs["Vector"], 3.0, detail=8.0, roughness=0.6)
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    attr.attribute_name = "brick_rand"
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (0.20, 0.105, 0.050, 1.0)   # ~ sRGB (0.49, 0.36, 0.25)
    color = multiply_color(nt, base.outputs["Color"], map_range(nt, grain.outputs["Fac"], 0.3, 0.7, 0.7, 1.15))
    color = multiply_color(nt, color, map_range(nt, attr.outputs["Fac"], 0.0, 1.0, 0.85, 1.1))
    # Sun-greyed upper faces.
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    grey = nt.nodes.new("ShaderNodeMix")
    grey.data_type = "RGBA"
    nt.links.new(map_range(nt, sep.outputs["Z"], 0.5, 1.0, 0.0, 0.3), socket(grey.inputs, "Factor_Float"))
    nt.links.new(color, socket(grey.inputs, "A_Color"))
    socket(grey.inputs, "B_Color").default_value = (0.19, 0.16, 0.13, 1.0)
    nt.links.new(socket(grey.outputs, "Result_Color"), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def _metal_material():
    mat, nt, bsdf = new_material("BenchFrame")
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (0.022, 0.042, 0.030, 1.0)  # ~ sRGB (0.16, 0.23, 0.19)
    wear = noise(nt, coords, 25.0, detail=4.0)
    nt.links.new(multiply_color(nt, base.outputs["Color"], map_range(nt, wear.outputs["Fac"], 0.3, 0.7, 0.8, 1.2)),
                 bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Metallic"].default_value = 0.3
    return mat


def _finish(collection, builder, name, p, materials):
    mesh = builder.to_mesh(name + "Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = p["bevel_width"]
    bevel.segments = 2
    bevel.limit_method = "WEIGHT"
    bevel.harden_normals = True
    for m in materials:
        obj.data.materials.append(m)
    return obj


def build(collection, rng, params):
    p = params
    hl, fx, sh = p["length"] / 2.0, p["frame_x"], p["seat_height"]
    wood, metal = _wood_material(), _metal_material()

    seat = BoxBuilder()
    for i in range(4):
        y0 = -0.245 + i * 0.105
        seat.add(-hl, hl, y0, y0 + 0.088, sh - 0.035, sh + rng.uniform(-0.002, 0.002), rand=rng.random())
    for x in (-fx, fx):
        seat.add(x - 0.025, x + 0.025, -0.245, -0.195, 0.0, sh - 0.035, material_index=1)     # front leg
        seat.add(x - 0.025, x + 0.025, 0.125, 0.175, 0.0, sh - 0.035, material_index=1)       # rear leg
        seat.add(x - 0.02, x + 0.02, -0.255, 0.185, sh - 0.075, sh - 0.035, material_index=1)  # seat rail
        seat.add(x - 0.015, x + 0.015, -0.21, 0.15, 0.06, 0.09, material_index=1)             # foot rail
        seat.add(x - 0.018, x + 0.018, -0.24, -0.205, sh, sh + 0.2, material_index=1)         # arm post
        seat.add(x - 0.03, x + 0.03, -0.285, 0.15, sh + 0.2, sh + 0.23, material_index=1)     # armrest
    seat.add(-0.02, 0.02, -0.235, 0.175, sh - 0.075, sh - 0.035, material_index=1)            # centre rail
    seat.add(-0.02, 0.02, 0.125, 0.165, 0.0, sh - 0.075, material_index=1)                    # centre leg
    seat_obj = _finish(collection, seat, "BenchSeat", p, [wood, metal])

    back = BoxBuilder()
    for x in (-fx, 0.0, fx):
        back.add(x - 0.02, x + 0.02, 0.0, 0.035, 0.0, 0.46, material_index=1)
    for k, (z0, z1) in enumerate(((0.07, 0.16), (0.19, 0.28), (0.31, 0.40))):
        back.add(-hl, hl, -0.032, 0.0, z0, z1 + rng.uniform(-0.002, 0.002), rand=rng.random())
    back_obj = _finish(collection, back, "BenchBack", p, [wood, metal])
    back_obj.location = (0.0, 0.14, sh - 0.035)
    back_obj.rotation_euler = (math.radians(-p["back_tilt_deg"]), 0.0, 0.0)

    objects = [seat_obj, back_obj]
    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": [-0.9, 0.9, -0.3, 0.3],
        "info": {
            "design_size_m": {"length_x": p["length"], "depth_y": 0.6, "seat_height": sh},
            "construction": "4 seat slats, 3 back slats (tilted), 2 end frames with armrests, centre support",
            "materials": ["BenchWood", "BenchFrame"],
        },
    }

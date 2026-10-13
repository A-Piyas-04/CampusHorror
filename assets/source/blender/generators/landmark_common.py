"""Helpers shared by the Main Gate landmark generators (not a generator: no build()).

Large landmark surfaces use a procedural running-bond brick shader instead of modeled bricks:
the same brick size, joints, colour ramp, mottling and ground grime as RedBrickWall3m
(red_brick_wall.py), so the gate reads as the same red-brick family at game scale. Bricks
are laid in object space with the horizontal coordinate x + y, which runs along both the
front (-Y) faces and the side (+-X) faces.

Arches are two-centred pointed arches: each half is an arc centred `d` metres across the
axis on the springing line, radius = half-span + d. Concentric rings share the centres.
"""

import math

import bmesh
import bpy

from generators.red_brick_wall import DEFAULT_PARAMS as WALL
from pipeline.modeling import ground_grime, map_range, multiply_color, new_material, noise, socket

# Linear-space brick colour stops, identical to red_brick_wall._brick_material.
BRICK_STOPS = (
    (0.00, (0.100, 0.016, 0.008)),
    (0.10, (0.240, 0.032, 0.014)),
    (0.45, (0.370, 0.056, 0.022)),
    (0.80, (0.480, 0.095, 0.036)),
    (1.00, (0.540, 0.160, 0.085)),
)
MORTAR_COLOR = (0.40, 0.375, 0.33, 1.0)


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
    return node.outputs[0]


def brick_shader_material(name="LandmarkBrick", seed=0.0):
    """Running bond (half bond) in object space; per-brick colour from a hashed brick index."""
    mat, nt, bsdf = new_material(name)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coords, sep.inputs["Vector"])
    joint = WALL["joint"]
    ch = WALL["brick_height"] + joint
    pitch = WALL["brick_length"] + joint

    along = _math(nt, "ADD", sep.outputs["X"], sep.outputs["Y"])
    zc = _math(nt, "DIVIDE", sep.outputs["Z"], ch)
    course = _math(nt, "FLOOR", zc)
    fz = _math(nt, "SUBTRACT", zc, course)
    shift = _math(nt, "MULTIPLY", _math(nt, "FLOORED_MODULO", course, 2.0), 0.5)
    u = _math(nt, "ADD", _math(nt, "DIVIDE", along, pitch), shift)
    index = _math(nt, "FLOOR", u)
    fu = _math(nt, "SUBTRACT", u, index)
    mortar = _math(nt, "MAXIMUM", _math(nt, "LESS_THAN", fu, joint / pitch), _math(nt, "LESS_THAN", fz, joint / ch))

    cell = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(index, cell.inputs["X"])
    nt.links.new(course, cell.inputs["Y"])
    cell.inputs["Z"].default_value = seed
    hashed = nt.nodes.new("ShaderNodeTexWhiteNoise")
    hashed.noise_dimensions = "3D"
    nt.links.new(cell.outputs["Vector"], hashed.inputs["Vector"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    elements = ramp.color_ramp.elements
    elements[0].position, elements[0].color = BRICK_STOPS[0][0], (*BRICK_STOPS[0][1], 1.0)
    elements[1].position, elements[1].color = BRICK_STOPS[-1][0], (*BRICK_STOPS[-1][1], 1.0)
    for pos, col in BRICK_STOPS[1:-1]:
        elements.new(pos).color = (*col, 1.0)
    nt.links.new(map_range(nt, hashed.outputs["Value"], 0.0, 1.0, 0.04, 0.96), ramp.inputs["Fac"])

    fine = noise(nt, coords, 45.0)
    broad = noise(nt, coords, 2.5, detail=3.0)
    color = multiply_color(nt, ramp.outputs["Color"], map_range(nt, fine.outputs["Fac"], 0.3, 0.7, 0.82, 1.12))
    color = multiply_color(nt, color, map_range(nt, broad.outputs["Fac"], 0.35, 0.65, 0.9, 1.06))

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mortar, socket(mix.inputs, "Factor_Float"))
    nt.links.new(color, socket(mix.inputs, "A_Color"))
    socket(mix.inputs, "B_Color").default_value = MORTAR_COLOR
    color = multiply_color(nt, socket(mix.outputs, "Result_Color"), ground_grime(nt))
    nt.links.new(color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.86

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.008
    nt.links.new(_math(nt, "SUBTRACT", 1.0, mortar), bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def paint_material(name, color, roughness=0.7, variation=0.08, grime_low=0.8):
    """Painted render / plaster: flat colour with soft mottling and darker ground grime."""
    mat, nt, bsdf = new_material(name)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (*color, 1.0)
    mottle = noise(nt, coords, 3.0, detail=4.0)
    out = multiply_color(nt, base.outputs["Color"],
                         map_range(nt, mottle.outputs["Fac"], 0.3, 0.7, 1.0 - variation, 1.0))
    out = multiply_color(nt, out, ground_grime(nt, low=grime_low, height_m=0.8))
    nt.links.new(out, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def concrete_material(name="RoofConcrete"):
    """Weathered light-grey concrete with darker water stains (aerial view of the gate roof)."""
    mat, nt, bsdf = new_material(name)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (0.42, 0.42, 0.40, 1.0)   # ~ sRGB (0.68, 0.68, 0.66)
    stains = noise(nt, coords, 0.9, detail=6.0, roughness=0.65)
    grain = noise(nt, coords, 60.0, detail=3.0)
    out = multiply_color(nt, base.outputs["Color"], map_range(nt, stains.outputs["Fac"], 0.4, 0.65, 0.72, 1.0))
    out = multiply_color(nt, out, map_range(nt, grain.outputs["Fac"], 0.3, 0.7, 0.93, 1.04))
    nt.links.new(out, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat


def steel_material(name="PaintedSteel", color=(0.018, 0.019, 0.02)):
    mat, nt, bsdf = new_material(name)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (*color, 1.0)
    wear = noise(nt, coords, 20.0, detail=4.0)
    nt.links.new(multiply_color(nt, base.outputs["Color"], map_range(nt, wear.outputs["Fac"], 0.3, 0.7, 0.8, 1.3)),
                 bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Metallic"].default_value = 0.4
    return mat


def glass_material(name="WindowGlass"):
    mat, nt, bsdf = new_material(name)
    bsdf.inputs["Base Color"].default_value = (0.012, 0.016, 0.02, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.12
    return mat


def image_material(name, image_path, roughness=0.55):
    """Image texture on UV (sRGB), e.g. the sign face."""
    mat, nt, bsdf = new_material(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(image_path), check_existing=True)
    tex.interpolation = "Cubic"
    tex.extension = "EXTEND"
    uv = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def arch_outline(half_span, springing_z, centre_offset, samples=28, jambs=True):
    """Two-centred pointed arch outline in XZ, left to right. With `jambs` it starts and ends
    on the ground (vertical jambs below the springing line)."""
    r = half_span + centre_offset
    apex = math.acos(centre_offset / r)
    left = [(centre_offset - r * math.cos(apex * i / samples), springing_z + r * math.sin(apex * i / samples))
            for i in range(samples + 1)]
    pts = left + [(-x, z) for x, z in reversed(left[:-1])]
    if jambs:
        pts = [(-half_span, 0.0)] + pts + [(half_span, 0.0)]
    return pts


def arch_apex_z(half_span, springing_z, centre_offset):
    r = half_span + centre_offset
    return springing_z + math.sqrt(r * r - centre_offset * centre_offset)


def strip_prism(bm, lower, upper, y0, y1):
    """Closed solid between two XZ polylines with the same number of points (both left to
    right), extruded from y0 (front) to y1 (back). Normals are fixed by the caller."""
    def ring(pts, y):
        return [bm.verts.new((x, y, z)) for x, z in pts]
    lf, uf, lb, ub = ring(lower, y0), ring(upper, y0), ring(lower, y1), ring(upper, y1)
    n = len(lower)
    for i in range(n - 1):
        bm.faces.new((lf[i], lf[i + 1], uf[i + 1], uf[i]))
        bm.faces.new((ub[i], ub[i + 1], lb[i + 1], lb[i]))
        bm.faces.new((lb[i], lb[i + 1], lf[i + 1], lf[i]))
        bm.faces.new((uf[i], uf[i + 1], ub[i + 1], ub[i]))
    bm.faces.new((lf[0], uf[0], ub[0], lb[0]))
    bm.faces.new((lb[-1], ub[-1], uf[-1], lf[-1]))


def disc_y(bm, cx, cz, radius, y0, y1, sides=32):
    """Cylinder with its axis along Y (a disc or medallion on a front face)."""
    front = [bm.verts.new((cx + radius * math.cos(2 * math.pi * k / sides), y0,
                           cz + radius * math.sin(2 * math.pi * k / sides))) for k in range(sides)]
    back = [bm.verts.new((v.co.x, y1, v.co.z)) for v in front]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for k in range(sides):
        bm.faces.new((front[k], back[k], back[(k + 1) % sides], front[(k + 1) % sides]))


def loft_rects(bm, rects, cap_bottom=True, cap_top=True):
    """Closed solid lofted through axis-aligned rectangles (x0, x1, y0, y1, z), bottom to top."""
    rings = [[bm.verts.new(c) for c in ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))]
             for x0, x1, y0, y1, z in rects]
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
    if cap_bottom:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top:
        bm.faces.new(rings[-1])


def finish_bmesh(collection, name, bm, materials, smooth=False):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name + "Mesh")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.shade_smooth()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def finish_boxes(collection, name, builder, materials, bevel_width=0.006):
    """BoxBuilder -> object with a weight-limited bevel, like the brick generators."""
    obj = bpy.data.objects.new(name, builder.to_mesh(name + "Mesh"))
    collection.objects.link(obj)
    if bevel_width:
        bevel = obj.modifiers.new("Bevel", "BEVEL")
        bevel.width = bevel_width
        bevel.segments = 2
        bevel.limit_method = "WEIGHT"
        bevel.harden_normals = True
    for m in materials:
        obj.data.materials.append(m)
    return obj

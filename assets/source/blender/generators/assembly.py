"""Parametric assembly: any prop or room described as data (decision D19).

One generator, many configs. A config's generator_params describe:

    "mats":    {name: material spec}                       procedural PBR materials (below)
    "objects": {ObjectName: {"parts": [...], "bevel": 0.004, "smooth": false}}
    "footprint_m": [x_min, x_max, y_min, y_max]            design footprint (collision / validation)
    "lights":  [{"at": [x, y, z], "size": [sx, sy], "power": W, "color": [r, g, b], "type": "AREA"|"POINT"}]
    "ceiling_z": metres or null                            camera-invisible lid that blocks the rig's sun (interiors)

Objects become separate Blender objects, so a config's `layers` can split them into Y-sorted sprites.

Part types (metres; frame: origin on the ground, +X right, +Y away from the camera, Z up):
    {"box": [x0, x1, y0, y1, z0, z1]}                     optional "rot": [rx, ry, rz] degrees about "pivot"
                                                          (default: the box centre)
    {"cyl": {"a": [x, y, z], "b": [x, y, z], "r": r, "r2": r_end, "sides": 16}}
    {"tube": [[x, y, z], ...], "r": r or "radii": [...], "sides": 8}
    {"lathe": [[r, z], ...], "at": [x, y], "sides": 24}
    {"blob": [x, y, z], "size": [sx, sy, sz], "lump": 0.25, "subdiv": 3, "seed": 1}
    {"text": "EXIT", "at": [x, y, z], "size": 0.2, "face": "front"|"up", "depth": 0.004, "align": "CENTER"}
    {"prism": [[u, v], ...], "span": [a0, a1], "axis": "y"|"x"|"z"}  polygon in XZ (axis y), YZ (axis x) or XY
                                                          (axis z: flat inlays, rugs), extruded
    {"repeat": n, "step": [dx, dy, dz], "part": {...}}    n copies, each offset by step
    {"mirror_x": true, "part": {...}}                     the part plus its mirror image across x = 0
Any part may also carry "xf": [{"rot": [rx, ry, rz], "pivot": [x, y, z]} | {"move": [dx, dy, dz]}, ...], applied in
order after its own "rot" (this is how authoring scripts place and turn whole pieces of furniture).
Every part takes "mat" (a key of "mats"); cylinders, tubes, lathes and blobs are smooth-shaded.

Material spec keys (colours are sRGB 0..1):
    color, rough (0.6), metal (0), spec (0.5), var (0.12: noise variation), var_scale (6),
    part_var (0.08: per-part tone variation), grime (0: darkening towards the floor), grime_h (0.6),
    stains (0: dark blotches), stain_color, stain_scale (2.5), bump (0: surface relief strength), bump_scale (40),
    emit [r, g, b] + emit_strength, glass (dark reflective glazing), wet (0..1: glossy, darker),
    pattern: {"type": "tiles"|"planks"|"terrazzo"|"stripes"|"grain"|"checker", ...} (see _pattern()).
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

from pipeline.modeling import extreme_points, map_range, multiply_color, new_material, noise, socket

COLLECTION_NAME = "Assembly"

DEFAULT_PARAMS = {
    "mats": {},
    "objects": {},
    "footprint_m": [-0.5, 0.5, -0.5, 0.5],
    "lights": [],
    "ceiling_z": None,
}


# --- Colour helpers ---------------------------------------------------------------------------------------------

def lin(c):
    """sRGB 0..1 -> linear (Blender colour sockets are linear)."""
    out = []
    for v in c[:3]:
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)


def rgb_node(nt, color):
    n = nt.nodes.new("ShaderNodeRGB")
    n.outputs["Color"].default_value = lin(color)
    return n.outputs["Color"]


def mix_color(nt, fac_socket, a_socket, b_socket):
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    if isinstance(fac_socket, (int, float)):
        socket(mix.inputs, "Factor_Float").default_value = fac_socket
    else:
        nt.links.new(fac_socket, socket(mix.inputs, "Factor_Float"))
    nt.links.new(a_socket, socket(mix.inputs, "A_Color"))
    nt.links.new(b_socket, socket(mix.inputs, "B_Color"))
    return socket(mix.outputs, "Result_Color")


# --- Materials ---------------------------------------------------------------------------------------------------

def planar_coords(nt, coords):
    """2D texture coordinates that work on every face of a box: top / bottom faces use (x, y), faces looking
    north or south use (x, z), faces looking east or west use (y, z). Blender's brick and checker textures are
    2D (they ignore the vector's third component), so on vertical faces plain object coordinates freeze one axis
    (a south wall at constant y lands on one brick row, or on a mortar line, and renders flat)."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    n = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], n.inputs["Vector"])
    p = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coords, p.inputs["Vector"])

    def math(op, a, b=None):
        m = nt.nodes.new("ShaderNodeMath")
        m.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                nt.links.new(v, m.inputs[i])
        return m.outputs["Value"]
    ax, ay, az = math("ABSOLUTE", n.outputs["X"]), math("ABSOLUTE", n.outputs["Y"]), math("ABSOLUTE", n.outputs["Z"])
    top = math("GREATER_THAN", az, 0.5)
    not_top = math("SUBTRACT", 1.0, top)
    front = math("MULTIPLY", not_top, math("GREATER_THAN", ay, ax))
    side = math("MULTIPLY", not_top, math("SUBTRACT", 1.0, math("GREATER_THAN", ay, ax)))
    u = math("ADD", math("MULTIPLY", math("ADD", top, front), p.outputs["X"]), math("MULTIPLY", side, p.outputs["Y"]))
    v = math("ADD", math("MULTIPLY", top, p.outputs["Y"]), math("MULTIPLY", math("ADD", front, side), p.outputs["Z"]))
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(u, comb.inputs["X"])
    nt.links.new(v, comb.inputs["Y"])
    return comb.outputs["Vector"]


def _pattern(nt, coords, spec, base):
    """Returns (colour socket, height socket or None) for a pattern over the base colour socket."""
    kind = spec.get("type")
    c2 = rgb_node(nt, spec.get("color2", [0.5, 0.5, 0.5]))
    if kind in ("tiles", "planks"):
        brick = nt.nodes.new("ShaderNodeTexBrick")
        mapping = nt.nodes.new("ShaderNodeMapping")
        nt.links.new(planar_coords(nt, coords), mapping.inputs["Vector"])
        if kind == "tiles":
            size = spec.get("size", 0.3)
            brick.offset = spec.get("offset", 0.0)
            brick.inputs["Brick Width"].default_value = spec.get("bw", 1.0)
            brick.inputs["Row Height"].default_value = 1.0
            mapping.inputs["Scale"].default_value = (1.0 / size, 1.0 / size, 1.0 / size)
        else:
            w, length = spec.get("w", 0.12), spec.get("l", 1.2)
            brick.offset = spec.get("offset", 0.37)
            brick.inputs["Brick Width"].default_value = length / w
            brick.inputs["Row Height"].default_value = 1.0
            axis_scale = (1.0 / w, 1.0 / w, 1.0 / w)
            mapping.inputs["Scale"].default_value = axis_scale
            if spec.get("axis", "x") == "y":
                mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.pi / 2)
        brick.inputs["Scale"].default_value = 1.0
        brick.inputs["Mortar Size"].default_value = spec.get("mortar", 0.03)
        brick.inputs["Mortar Smooth"].default_value = 0.2
        brick.inputs["Bias"].default_value = 0.0
        nt.links.new(mapping.outputs["Vector"], brick.inputs["Vector"])
        nt.links.new(base, brick.inputs["Color1"])
        nt.links.new(c2, brick.inputs["Color2"])
        brick.inputs["Mortar"].default_value = lin(spec.get("mortar_color", [0.25, 0.25, 0.25]))
        return brick.outputs["Color"], map_range(nt, brick.outputs["Fac"], 0.0, 1.0, 1.0, 0.0)
    if kind == "terrazzo":
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.feature = "F1"
        vor.inputs["Scale"].default_value = spec.get("scale", 70.0)
        vor.inputs["Randomness"].default_value = 1.0
        nt.links.new(coords, vor.inputs["Vector"])
        chips = map_range(nt, vor.outputs["Distance"], spec.get("density", 0.18), spec.get("density", 0.18) + 0.02,
                          1.0, 0.0)
        tone = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(vor.outputs["Color"], tone.inputs["Fac"])
        colors = spec.get("chips", [[0.2, 0.2, 0.2], [0.85, 0.85, 0.8], [0.55, 0.35, 0.25]])
        ramp = tone.color_ramp
        ramp.interpolation = "CONSTANT"
        while len(ramp.elements) < len(colors):
            ramp.elements.new(0.5)
        for i, col in enumerate(colors):
            ramp.elements[i].position = i / len(colors)
            ramp.elements[i].color = lin(col)
        return mix_color(nt, chips, base, tone.outputs["Color"]), None
    if kind == "stripes":
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = spec.get("axis", "x").upper()
        wave.inputs["Scale"].default_value = 1.0 / spec.get("period", 0.2)
        nt.links.new(coords, wave.inputs["Vector"])
        sharp = map_range(nt, wave.outputs["Fac"], 0.48, 0.52, 0.0, 1.0)
        return mix_color(nt, sharp, base, c2), None
    if kind == "grain":
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = tuple(spec.get("scale", [0.6, 30.0, 30.0]))
        nt.links.new(coords, mapping.inputs["Vector"])
        g = noise(nt, mapping.outputs["Vector"], 3.0, detail=8.0, roughness=0.6)
        return multiply_color(nt, base, map_range(nt, g.outputs["Fac"], 0.3, 0.7, 0.72, 1.15)), None
    if kind == "checker":
        chk = nt.nodes.new("ShaderNodeTexChecker")
        chk.inputs["Scale"].default_value = 1.0 / spec.get("size", 0.3)
        nt.links.new(planar_coords(nt, coords), chk.inputs["Vector"])
        nt.links.new(base, chk.inputs["Color1"])
        nt.links.new(c2, chk.inputs["Color2"])
        return chk.outputs["Color"], None
    return base, None


def make_material(name, spec):
    mat, nt, bsdf = new_material(name)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = rgb_node(nt, spec.get("color", [0.6, 0.6, 0.6]))
    height = None
    if spec.get("pattern"):
        base, height = _pattern(nt, coords, spec["pattern"], base)
    var = spec.get("var", 0.12)
    if var:
        n = noise(nt, coords, spec.get("var_scale", 6.0), detail=4.0)
        base = multiply_color(nt, base, map_range(nt, n.outputs["Fac"], 0.3, 0.7, 1.0 - var, 1.0 + var))
    part_var = spec.get("part_var", 0.08)
    if part_var:
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_type = "GEOMETRY"
        attr.attribute_name = "part_rand"
        base = multiply_color(nt, base, map_range(nt, attr.outputs["Fac"], 0.0, 1.0, 1.0 - part_var, 1.0 + part_var))
    stains = spec.get("stains", 0.0)
    if stains:
        sn = noise(nt, coords, spec.get("stain_scale", 2.5), detail=6.0, roughness=0.7)
        blot = map_range(nt, sn.outputs["Fac"], 0.62 - 0.2 * stains, 0.7 - 0.2 * stains, 0.0, min(1.0, stains * 1.2))
        base = mix_color(nt, blot, base, rgb_node(nt, spec.get("stain_color", [0.18, 0.14, 0.1])))
    grime = spec.get("grime", 0.0)
    if grime:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
        base = multiply_color(nt, base, map_range(nt, sep.outputs["Z"], 0.0, spec.get("grime_h", 0.6), 1.0 - grime, 1.0))
    wet = spec.get("wet", 0.0)
    if wet:
        base = multiply_color(nt, base, map_range(nt, nt.nodes.new("ShaderNodeValue").outputs["Value"], 0, 1,
                                                  1.0 - 0.35 * wet, 1.0 - 0.35 * wet))
    nt.links.new(base, bsdf.inputs["Base Color"])
    rough = spec.get("rough", 0.6) * (1.0 - 0.8 * wet)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = spec.get("metal", 0.0)
    spec_input = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_input is not None:
        spec_input.default_value = spec.get("spec", 0.5)
    if spec.get("glass"):
        bsdf.inputs["Roughness"].default_value = 0.06
        if spec_input is not None:
            spec_input.default_value = 0.9
    bump_amt = spec.get("bump", 0.0)
    if bump_amt or height is not None:
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = max(bump_amt, 0.25 if height is not None else 0.0)
        bump.inputs["Distance"].default_value = 0.01
        h = height
        if bump_amt:
            bn = noise(nt, coords, spec.get("bump_scale", 40.0), detail=8.0, roughness=0.65)
            h = bn.outputs["Fac"] if h is None else _add(nt, h, bn.outputs["Fac"])
        nt.links.new(h, bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if spec.get("emit"):
        em_in = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        em_in.default_value = lin(spec["emit"])
        bsdf.inputs["Emission Strength"].default_value = spec.get("emit_strength", 2.0)
    return mat


def _add(nt, a, b):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = "ADD"
    nt.links.new(a, m.inputs[0])
    nt.links.new(b, m.inputs[1])
    return m.outputs["Value"]


# --- Geometry --------------------------------------------------------------------------------------------------

class Builder:
    def __init__(self, mat_index_of):
        self.bm = bmesh.new()
        self.rand = self.bm.faces.layers.float.new("part_rand")
        self.mat_index_of = mat_index_of
        self.rng = random.Random(1)

    def _tag(self, faces, part, smooth):
        r = part.get("rand", self.rng.random())
        idx = self.mat_index_of(part.get("mat"))
        for f in faces:
            f[self.rand] = r
            f.material_index = idx
            f.smooth = smooth

    def _new_faces_since(self, count):
        self.bm.faces.ensure_lookup_table()
        return list(self.bm.faces)[count:]

    def _rotate(self, verts, part, centre):
        rot = part.get("rot")
        if not rot:
            return
        pivot = Vector(part.get("pivot", centre))
        m = (Matrix.Rotation(math.radians(rot[2]), 4, "Z") @ Matrix.Rotation(math.radians(rot[1]), 4, "Y")
             @ Matrix.Rotation(math.radians(rot[0]), 4, "X"))
        bmesh.ops.rotate(self.bm, verts=verts, cent=pivot, matrix=m)

    def add(self, part, offset=Vector((0, 0, 0)), mirror=False):
        if "repeat" in part:
            step = Vector(part.get("step", [0, 0, 0]))
            for i in range(int(part["repeat"])):
                self.add(part["part"], offset + step * i, mirror)
            return
        if "mirror_x" in part:
            self.add(part["part"], offset, mirror)
            self.add(part["part"], offset, not mirror)
            return
        before_v = len(self.bm.verts)
        before_f = len(self.bm.faces)
        smooth = False
        centre = (0.0, 0.0, 0.0)
        if "box" in part:
            x0, x1, y0, y1, z0, z1 = part["box"]
            centre = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
            v = [self.bm.verts.new(c) for c in (
                (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
            for f in ((v[0], v[3], v[2], v[1]), (v[4], v[5], v[6], v[7]), (v[0], v[1], v[5], v[4]),
                      (v[2], v[3], v[7], v[6]), (v[1], v[2], v[6], v[5]), (v[3], v[0], v[4], v[7])):
                self.bm.faces.new(f)
        elif "cyl" in part:
            c = part["cyl"]
            a, b = Vector(c["a"]), Vector(c["b"])
            r1, r2 = c["r"], c.get("r2", c["r"])
            centre = tuple((a + b) / 2)
            self._tube([a, b], [r1, r2], c.get("sides", 16), True, True)
            smooth = True
        elif "tube" in part:
            pts = [Vector(p) for p in part["tube"]]
            radii = part.get("radii") or [part.get("r", 0.02)] * len(pts)
            self._tube(pts, radii, part.get("sides", 8), part.get("cap", True), part.get("cap", True))
            smooth = True
        elif "lathe" in part:
            cx, cy = part.get("at", [0.0, 0.0])
            prof = part["lathe"]
            sides = part.get("sides", 24)
            rings = [[self.bm.verts.new((cx + r * math.cos(2 * math.pi * k / sides),
                                         cy + r * math.sin(2 * math.pi * k / sides), z)) for k in range(sides)]
                     for r, z in prof]
            for r0, r1 in zip(rings, rings[1:]):
                for k in range(sides):
                    self.bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
            if prof[0][0] > 0:
                self.bm.faces.new(list(reversed(rings[0])))
            if prof[-1][0] > 0:
                self.bm.faces.new(rings[-1])
            smooth = True
        elif "blob" in part:
            cx, cy, cz = part["blob"]
            sx, sy, sz = part.get("size", [0.3, 0.3, 0.15])
            rng = random.Random(part.get("seed", 1))
            res = bmesh.ops.create_icosphere(self.bm, subdivisions=part.get("subdiv", 3), radius=1.0)
            lump = part.get("lump", 0.25)
            phases = [rng.uniform(0, 6.28) for _ in range(6)]
            for vert in res["verts"]:
                p = vert.co.copy()
                n = (math.sin(p.x * 3.1 + phases[0]) * math.sin(p.y * 2.7 + phases[1])
                     + 0.6 * math.sin(p.z * 4.3 + phases[2]) * math.sin(p.x * 5.1 + phases[3])
                     + 0.35 * math.sin(p.y * 7.9 + phases[4]) * math.sin(p.z * 6.7 + phases[5]))
                k = 1.0 + lump * n / 1.95
                z = cz + p.z * k * sz
                if part.get("flat_bottom", True):
                    z = max(z, part.get("floor", 0.0))
                vert.co = Vector((cx + p.x * k * sx, cy + p.y * k * sy, z))
            smooth = True
        elif "prism" in part:
            # A polygon (concave allowed) extruded: axis "y" = polygon in XZ (a front-facing shape such as a
            # pointed arch), extruded from y0 to y1; axis "x" = polygon in YZ, extruded from x0 to x1.
            pts = part["prism"]
            a0, a1 = part.get("span", [0.0, 0.1])
            axis = part.get("axis", "y")
            if axis == "y":
                front = [self.bm.verts.new((u, a0, v)) for u, v in pts]
                back = [self.bm.verts.new((u, a1, v)) for u, v in pts]
            elif axis == "z":
                front = [self.bm.verts.new((u, v, a0)) for u, v in pts]
                back = [self.bm.verts.new((u, v, a1)) for u, v in pts]
            else:
                front = [self.bm.verts.new((a0, u, v)) for u, v in pts]
                back = [self.bm.verts.new((a1, u, v)) for u, v in pts]
            n = len(pts)
            self.bm.faces.new(front)
            self.bm.faces.new(list(reversed(back)))
            for i in range(n):
                self.bm.faces.new((front[i], front[(i + 1) % n], back[(i + 1) % n], back[i]))
            cu, cv = sum(u for u, _ in pts) / n, sum(v for _, v in pts) / n
            centre = {"y": (cu, (a0 + a1) / 2, cv), "x": ((a0 + a1) / 2, cu, cv), "z": (cu, cv, (a0 + a1) / 2)}[axis]
        elif "text" in part:
            self._text(part)
        else:
            raise ValueError(f"unknown part {part}")
        self.bm.verts.ensure_lookup_table()
        verts = [self.bm.verts[i] for i in range(before_v, len(self.bm.verts))]
        if "text" not in part:
            self._rotate(verts, part, centre)
        for xf in part.get("xf", []):
            if "move" in xf:
                bmesh.ops.translate(self.bm, verts=verts, vec=Vector(xf["move"]))
            else:
                self._rotate(verts, xf, xf.get("pivot", (0.0, 0.0, 0.0)))
        if offset.length > 0:
            bmesh.ops.translate(self.bm, verts=verts, vec=offset)
        if mirror:
            for vert in verts:
                vert.co.x = -vert.co.x
            faces = self._new_faces_since(before_f)
            bmesh.ops.reverse_faces(self.bm, faces=faces)
        self._tag(self._new_faces_since(before_f), part, smooth)

    def _tube(self, pts, radii, sides, cap_start, cap_end):
        tangents = []
        for i in range(len(pts)):
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
            tangents.append((b - a).normalized())
        ref = Vector((1, 0, 0)) if abs(tangents[0].x) < 0.9 else Vector((0, 1, 0))
        side = tangents[0].cross(ref).normalized()
        rings = []
        for i, (p, t, r) in enumerate(zip(pts, tangents, radii)):
            if i:
                side = (side - t * side.dot(t)).normalized()
            other = t.cross(side)
            rings.append([self.bm.verts.new(p + (side * math.cos(a) + other * math.sin(a)) * r)
                          for a in (2 * math.pi * k / sides for k in range(sides))])
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(sides):
                self.bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
        if cap_start:
            self.bm.faces.new(list(reversed(rings[0])))
        if cap_end:
            self.bm.faces.new(rings[-1])

    def _text(self, part):
        """Text is built as a curve, converted to a mesh and merged into this object."""
        curve = bpy.data.curves.new("AsmText", type="FONT")
        curve.body = part["text"]
        curve.size = part.get("size", 0.2)
        curve.extrude = part.get("depth", 0.004)
        curve.align_x = part.get("align", "CENTER")
        curve.align_y = "BOTTOM"
        tmp = bpy.data.objects.new("AsmTextTmp", curve)
        bpy.context.scene.collection.objects.link(tmp)
        x, y, z = part.get("at", [0.0, 0.0, 0.0])
        tmp.location = (x, y, z)
        if part.get("face", "front") == "front":
            tmp.rotation_euler = (math.radians(90), 0.0, 0.0)
        else:
            tmp.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(deps))
        mesh.transform(tmp.matrix_world)
        self.bm.from_mesh(mesh)
        bpy.context.scene.collection.objects.unlink(tmp)
        bpy.data.objects.remove(tmp)
        bpy.data.meshes.remove(mesh)
        bpy.data.curves.remove(curve)

    def to_object(self, collection, name, materials, bevel):
        mesh = bpy.data.meshes.new(name + "Mesh")
        bmesh.ops.recalc_face_normals(self.bm, faces=list(self.bm.faces))
        self.bm.normal_update()
        self.bm.to_mesh(mesh)
        self.bm.free()
        for m in materials:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        if bevel:
            mod = obj.modifiers.new("Bevel", "BEVEL")
            mod.width = bevel
            mod.segments = 2
            mod.limit_method = "ANGLE"
            mod.angle_limit = math.radians(40)
            mod.harden_normals = True
        return obj


def build(collection, rng, params):
    p = params
    mats = {name: make_material(name, spec) for name, spec in p["mats"].items()}
    if not mats:
        mats["Default"] = make_material("Default", {})
    objects = []
    for obj_name, spec in p["objects"].items():
        used = []

        def index_of(mat_name, used=used):
            key = mat_name if mat_name in mats else next(iter(mats))
            if key not in used:
                used.append(key)
            return used.index(key)

        b = Builder(index_of)
        b.rng = random.Random(rng.random())
        for part in spec["parts"]:
            b.add(part)
        obj = b.to_object(collection, obj_name, [mats[k] for k in used], spec.get("bevel", 0.004))
        objects.append(obj)

    for i, light in enumerate(p["lights"]):
        kind = light.get("type", "AREA")
        data = bpy.data.lights.new(f"AsmLight{i}", kind)
        data.energy = light.get("power", 200.0)
        data.color = lin(light.get("color", [1.0, 0.95, 0.85]))[:3]
        if kind == "AREA":
            data.shape = "RECTANGLE"
            sx, sy = light.get("size", [1.0, 1.0])
            data.size, data.size_y = sx, sy
        else:
            data.shadow_soft_size = light.get("radius", 0.1)
        lo = bpy.data.objects.new(f"AsmLight{i}", data)
        lo.location = tuple(light["at"])
        collection.objects.link(lo)

    if p["ceiling_z"] is not None and objects:
        pts = extreme_points(objects, elevations=(90,))
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        cz = p["ceiling_z"]
        bm = bmesh.new()
        x0, x1, y0, y1 = min(xs) - 2, max(xs) + 2, min(ys) - 2, max(ys) + 2
        v = [bm.verts.new(c) for c in ((x0, y0, cz), (x1, y0, cz), (x1, y1, cz), (x0, y1, cz),
                                         (x0, y0, cz + 0.2), (x1, y0, cz + 0.2), (x1, y1, cz + 0.2), (x0, y1, cz + 0.2))]
        for f in ((v[0], v[3], v[2], v[1]), (v[4], v[5], v[6], v[7]), (v[0], v[1], v[5], v[4]),
                  (v[2], v[3], v[7], v[6]), (v[1], v[2], v[6], v[5]), (v[3], v[0], v[4], v[7])):
            bm.faces.new(f)
        mesh = bpy.data.meshes.new("CeilingMesh")
        bm.to_mesh(mesh)
        bm.free()
        lid = bpy.data.objects.new("Ceiling", mesh)
        lid.visible_camera = False
        collection.objects.link(lid)

    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": list(p["footprint_m"]),
        "info": {
            "objects": {o.name: len(o.data.polygons) for o in objects},
            "materials": sorted(mats),
            "lights": len(p["lights"]),
            "ceiling_z": p["ceiling_z"],
        },
    }

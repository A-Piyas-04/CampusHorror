"""Foliage helpers shared by the tree, palm and hedge generators (not a generator itself).

Canopies are built the way stylized-realistic game foliage usually is:
- a dark, lumpy inner volume ("blob") that fills gaps and reads as interior shadow;
- thousands of small leaf cards scattered on its surface, coloured per leaf;
- leaf normals bent towards the volume's outward direction (custom normals), so a canopy
  shades like a soft volume under the shared key sun instead of as noisy flat cards.
Cast shadows inside the canopy and AO still come from the real geometry.

All randomness comes from the generator's `rng`; leaves are sized to stay readable at the
sprite's ~1/7 game scale (a 0.2 m leaf is about 6 game px).
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from pipeline.modeling import map_range, multiply_color, new_material, noise, socket


class Blob:
    """Lumpy sphere: radius(direction) = r * (1 + sum of smooth random bumps)."""

    def __init__(self, rng, center, radius, squash=1.0, lumps=7, lumpiness=0.16):
        self.center = Vector(center)
        self.radius = radius
        self.squash = squash
        self.bumps = []
        for _ in range(lumps):
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
            self.bumps.append((d, rng.uniform(-0.5, 1.0) * lumpiness, rng.uniform(0.5, 0.9)))

    def radius_at(self, direction):
        r = 1.0
        for d, amp, width in self.bumps:
            r += amp * math.exp((direction.dot(d) - 1.0) / (width * 0.35))
        return self.radius * r

    def surface(self, direction):
        p = direction * self.radius_at(direction)
        return self.center + Vector((p.x, p.y, p.z * self.squash))

    def contains(self, point, shrink=1.0):
        rel = point - self.center
        rel = Vector((rel.x, rel.y, rel.z / self.squash))
        if rel.length < 1e-9:
            return True
        return rel.length < self.radius_at(rel.normalized()) * shrink


def add_blob_mesh(bm, blob, subdivisions=3):
    ret = bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=1.0)
    for v in ret["verts"]:
        v.co = blob.surface(v.co.normalized())


def random_direction(rng):
    return Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()


class LeafCards:
    """Accumulates leaf polygons with a per-face random attribute and per-face custom normals."""

    def __init__(self, attribute="leaf_rand"):
        self.bm = bmesh.new()
        self.rand_layer = self.bm.faces.layers.float.new(attribute)
        self.normals = []
        self.count = 0

    def add(self, center, normal, length, width, spin, rand, shading_normal=None, droop=0.0, material_index=0):
        """Diamond-shaped leaf in the plane perpendicular to `normal`, rotated by `spin`."""
        n = Vector(normal).normalized()
        ref = Vector((0, 0, 1)) if abs(n.z) < 0.95 else Vector((1, 0, 0))
        u = n.cross(ref).normalized()
        u = Matrix.Rotation(spin, 3, n) @ u
        v = n.cross(u)
        c = Vector(center)
        tip = c + u * (length * 0.5) - n * droop
        base = c - u * (length * 0.5)
        shade = (shading_normal or n).normalized()
        pts = [base, c + v * (width * 0.5) - u * (length * 0.05), tip, c - v * (width * 0.5) - u * (length * 0.05)]
        self._face(pts, shade, rand, material_index)
        self.count += 1

    def _face(self, pts, shade, rand, material_index):
        # Cycles flips the shading normal of faces seen from behind; winding every face towards
        # its shading normal keeps the outward-facing leaves lit as intended.
        if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(shade) < 0:
            pts = list(reversed(pts))
        face = self.bm.faces.new([self.bm.verts.new(p) for p in pts])
        face[self.rand_layer] = rand
        face.material_index = material_index
        self.normals.append(shade)

    def add_strip(self, points, widths, side, rand, shading_normal, material_index=0):
        """Tapered strip (e.g. a palm leaflet) through `points`, `side` = width direction."""
        side = Vector(side).normalized()
        shade = Vector(shading_normal).normalized()
        left = [Vector(p) + side * (w * 0.5) for p, w in zip(points, widths)]
        right = [Vector(p) - side * (w * 0.5) for p, w in zip(points, widths)]
        for i in range(len(points) - 1):
            quad = [left[i], right[i], right[i + 1], left[i + 1]]
            if (quad[1] - quad[0]).length < 1e-6:
                quad = quad[1:]
            self._face(quad, shade, rand, material_index)
        self.count += 1

    def to_object(self, collection, name, materials):
        mesh = bpy.data.meshes.new(name + "Mesh")
        self.bm.to_mesh(mesh)
        self.bm.free()
        loop_normals = []
        for poly, n in zip(mesh.polygons, self.normals):
            loop_normals += [n] * poly.loop_total
        mesh.normals_split_custom_set(loop_normals)
        for m in materials:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj


def scatter_on_blobs(cards, rng, blobs, density, leaf_len, leaf_w, up_bias=0.35, depth=(0.82, 1.05),
                     crown_center=None, crown_bias=0.0):
    """Leaves over the blob surfaces, skipping points buried inside a neighbouring blob.
    Shading normal = blob outward direction (+ optional crown outward), bent upwards."""
    for i, blob in enumerate(blobs):
        area = 4.0 * math.pi * blob.radius ** 2 * (1.0 + blob.squash) / 2.0
        for _ in range(int(area * density)):
            d = random_direction(rng)
            p = blob.center + (blob.surface(d) - blob.center) * rng.uniform(*depth)
            if any(j != i and other.contains(p, 0.9) for j, other in enumerate(blobs)):
                continue
            shade = d.copy()
            if crown_center is not None:
                shade = shade + (p - Vector(crown_center)).normalized() * crown_bias
            shade = (shade.normalized() + Vector((0, 0, up_bias))).normalized()
            facing = (d + random_direction(rng) * 0.9).normalized()
            s = rng.uniform(0.8, 1.2)
            cards.add(p, facing, leaf_len * s, leaf_w * s, rng.uniform(0, 2 * math.pi), rng.random(),
                      shading_normal=shade, droop=leaf_len * 0.15)


def _ramp(nt, fac_socket, stops):
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1.0)
    el[1].position, el[1].color = stops[-1][0], (*stops[-1][1], 1.0)
    for pos, col in stops[1:-1]:
        el.new(pos).color = (*col, 1.0)
    nt.links.new(fac_socket, ramp.inputs["Fac"])
    return ramp.outputs["Color"]


def leaf_material(name, stops, translucency=0.25, ao_distance=0.6, roughness=0.6, attribute="leaf_rand"):
    """Leaves: colour per leaf from a ramp, darkened in occluded canopy interiors, with some
    back-light translucency."""
    mat, nt, bsdf = new_material(name)
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    attr.attribute_name = attribute
    color = _ramp(nt, attr.outputs["Fac"], stops)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    broad = noise(nt, coords, 0.8, detail=2.0)
    color = multiply_color(nt, color, map_range(nt, broad.outputs["Fac"], 0.35, 0.65, 0.85, 1.12))
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = ao_distance
    ao.samples = 8
    color = multiply_color(nt, color, map_range(nt, ao.outputs["AO"], 0.2, 1.0, 0.45, 1.0))
    nt.links.new(color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness

    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    trans = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(color, trans.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = translucency
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    nt.links.new(trans.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def inner_material(name, color, roughness=0.9):
    """Dark canopy interior behind the leaf cards."""
    mat, nt, bsdf = new_material(name)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    rgb = nt.nodes.new("ShaderNodeRGB")
    rgb.outputs["Color"].default_value = (*color, 1.0)
    n = noise(nt, coords, 6.0, detail=3.0)
    nt.links.new(multiply_color(nt, rgb.outputs["Color"], map_range(nt, n.outputs["Fac"], 0.3, 0.7, 0.7, 1.2)),
                 bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def bark_material(name, base, dark, streak_scale=(6.0, 6.0, 0.8), ring_period=None):
    """Bark: vertical streaks (noise stretched along Z) or, with `ring_period`, horizontal
    growth rings (palm trunk), darkened towards the ground."""
    mat, nt, bsdf = new_material(name)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = streak_scale
    nt.links.new(coords, mapping.inputs["Vector"])
    streak = noise(nt, mapping.outputs["Vector"], 4.0, detail=6.0, roughness=0.65)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(map_range(nt, streak.outputs["Fac"], 0.35, 0.7, 0.0, 1.0), socket(mix.inputs, "Factor_Float"))
    socket(mix.inputs, "A_Color").default_value = (*dark, 1.0)
    socket(mix.inputs, "B_Color").default_value = (*base, 1.0)
    color = socket(mix.outputs, "Result_Color")
    height = streak.outputs["Fac"]
    if ring_period:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coords, sep.inputs["Vector"])
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "Z"
        wave.inputs["Scale"].default_value = (2.0 * math.pi / 20.0) / ring_period  # bands: period 2pi/20 at scale 1
        wave.inputs["Distortion"].default_value = 1.5
        wave.inputs["Detail"].default_value = 2.0
        nt.links.new(coords, wave.inputs["Vector"])
        rings = map_range(nt, wave.outputs["Fac"], 0.0, 0.35, 0.62, 1.0)
        color = multiply_color(nt, color, rings)
        height = wave.outputs["Fac"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep2 = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep2.inputs["Vector"])
    color = multiply_color(nt, color, map_range(nt, sep2.outputs["Z"], 0.0, 0.5, 0.7, 1.0))
    nt.links.new(color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.01
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat

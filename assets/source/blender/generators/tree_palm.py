"""Coconut palm: slightly leaning ringed trunk and a crown of arching pinnate fronds.

The trunk is a tapered tube with a flared base and leaf-scar rings (shader bands + bump).
Each frond is a drooping rachis with paired leaflets (thin tapered strips that rise a little,
then hang); young fronds point up, old ones droop, and two dead brown fronds hang below the
crown with a cluster of coconuts. About 8.5 m tall, crown ~6.5 m across.

Frame: origin = trunk centre on the ground, front faces -Y, Z up, metres.
Modeling and materials only; the shared pipeline renders and exports.
"""

import math

import bmesh
from mathutils import Vector

from generators.foliage import LeafCards, bark_material, leaf_material
from pipeline.modeling import add_tube, extreme_points, mesh_object, new_material

COLLECTION_NAME = "PalmTree"

DEFAULT_PARAMS = {
    "trunk_height": 7.2,
    "base_radius": 0.20,
    "top_radius": 0.14,
    "lean_x": 0.45,
    "lean_y": 0.12,
    "fronds": 16,
    "frond_length": 3.5,
    "leaflet_step": 0.019,     # along the rachis, as a fraction of its length
    "leaflet_length": 0.95,
    "leaflet_width": 0.05,
    "dead_fronds": 2,
    "coconuts": 7,
    "collision_half_m": 0.175,
}

FROND_STOPS = (
    (0.00, (0.045, 0.090, 0.018)),
    (0.50, (0.085, 0.140, 0.026)),
    (1.00, (0.160, 0.195, 0.045)),
)
DEAD_STOPS = (
    (0.00, (0.120, 0.075, 0.035)),
    (1.00, (0.210, 0.140, 0.060)),
)


def _trunk_point(p, z):
    t = z / p["trunk_height"]
    return Vector((p["lean_x"] * t ** 1.6 - 0.06 * math.sin(math.pi * t), p["lean_y"] * t ** 1.8, z))


def _rachis(top, az, el, length, sag, n=12):
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    return [top + d * (s * length) + Vector((0, 0, -sag * length * s * s)) for s in (i / (n - 1) for i in range(n))]


def _sample(points, s):
    f = s * (len(points) - 1)
    i = min(int(f), len(points) - 2)
    a, b = points[i], points[i + 1]
    return a.lerp(b, f - i), (b - a).normalized()


def build(collection, rng, params):
    p = params
    H = p["trunk_height"]

    wood = bmesh.new()
    zs = [0.0, 0.12, 0.4, 1.0, 2.0, 3.2, 4.4, 5.6, 6.6, H]
    radii = [p["base_radius"] * 1.5, p["base_radius"] * 1.15] + [
        p["base_radius"] + (p["top_radius"] - p["base_radius"]) * (z / H) for z in zs[2:]]
    add_tube(wood, [_trunk_point(p, z) for z in zs], radii, sides=14, cap_start=True)
    trunk = mesh_object(collection, "Trunk", wood,
                        [bark_material("PalmBark", (0.17, 0.14, 0.11), (0.07, 0.06, 0.05),
                                       streak_scale=(10.0, 10.0, 2.0), ring_period=0.09)], smooth=True)

    top = _trunk_point(p, H) + Vector((0, 0, 0.1))
    crown_center = top + Vector((0, 0, 0.3))
    cards = LeafCards()
    rachis_bm = bmesh.new()
    n = p["fronds"]
    for i in range(n + p["dead_fronds"]):
        dead = i >= n
        if dead:
            az = rng.uniform(0, 2 * math.pi)
            el = math.radians(rng.uniform(-75, -62))
            length, sag = p["frond_length"] * 0.8, 0.05
        else:
            age = i / (n - 1)
            az = math.radians(i * 137.5 + rng.uniform(-12, 12))
            el = math.radians(58 - 95 * age + rng.uniform(-8, 8))
            length = p["frond_length"] * rng.uniform(0.85, 1.05) * (0.8 if age < 0.15 else 1.0)
            sag = 0.25 + 0.35 * age
        rachis = _rachis(top, az, el, length, sag)
        add_tube(rachis_bm, rachis, [0.05, 0.04, 0.035] + [0.03 - 0.0022 * k for k in range(len(rachis) - 3)],
                 sides=6, cap_end=False)
        frond_rand = rng.random()
        s = 0.12
        while s < 0.97:
            pos, tangent = _sample(rachis, s)
            side = tangent.cross(Vector((0, 0, 1)))
            side = side.normalized() if side.length > 1e-4 else Vector((1, 0, 0))
            l_len = p["leaflet_length"] * math.sin(math.pi * min(s * 1.1, 0.98)) ** 0.5 * (length / p["frond_length"])
            for sign in (-1, 1):
                d = (side * sign * 0.85 + tangent * 0.45).normalized()
                droop = 0.9 if dead else rng.uniform(0.35, 0.6)
                pts = [pos + d * (l_len * k / 3) + Vector((0, 0, l_len * (0.12 * k / 3 - droop * (k / 3) ** 2)))
                       for k in range(4)]
                w = p["leaflet_width"]
                radial = Vector((pos.x - crown_center.x, pos.y - crown_center.y, 0.0))
                radial = radial.normalized() if radial.length > 1e-4 else Vector((0, 0, 0))
                shade = (Vector((0, 0, 1)) * 0.8 + radial * 0.6 + d * 0.2).normalized()
                cards.add_strip(pts, [w * 0.6, w, w * 0.8, w * 0.1], tangent,
                                min(1.0, max(0.0, frond_rand * 0.6 + rng.random() * 0.4)), shade,
                                material_index=1 if dead else 0)
            s += p["leaflet_step"] * rng.uniform(0.85, 1.15)
    rachis_mat, nt, bsdf = new_material("Rachis")
    bsdf.inputs["Base Color"].default_value = (0.13, 0.13, 0.05, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    rachis_obj = mesh_object(collection, "Rachises", rachis_bm, [rachis_mat], smooth=True)
    frond_count = cards.count
    fronds = cards.to_object(collection, "Fronds", [leaf_material("PalmFronds", FROND_STOPS, translucency=0.15,
                                                                  ao_distance=0.8),
                                                    leaf_material("PalmDeadFronds", DEAD_STOPS, translucency=0.05)])

    nuts = bmesh.new()
    for k in range(p["coconuts"]):
        a = 2 * math.pi * k / p["coconuts"] + rng.uniform(-0.2, 0.2)
        c = top + Vector((math.cos(a) * 0.2, math.sin(a) * 0.2, -0.25 + rng.uniform(-0.12, 0.05)))
        ret = bmesh.ops.create_icosphere(nuts, subdivisions=2, radius=0.11)
        for v in ret["verts"]:
            v.co = c + Vector((v.co.x, v.co.y, v.co.z * 1.15))
    nut_mat, nt, bsdf = new_material("Coconut")
    bsdf.inputs["Base Color"].default_value = (0.11, 0.12, 0.03, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55
    coconuts = mesh_object(collection, "Coconuts", nuts, [nut_mat], smooth=True)

    objects = [trunk, rachis_obj, fronds, coconuts]
    h = p["collision_half_m"]
    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": [-h, h, -h, h],
        "info": {
            "design_size_m": {"trunk_height": H, "frond_length": p["frond_length"]},
            "fronds": n,
            "dead_fronds": p["dead_fronds"],
            "leaflets": frond_count,
            "footprint": "trunk base only (collision); fronds have none and Y-sort with the trunk origin",
            "materials": ["PalmBark", "Rachis", "PalmFronds", "PalmDeadFronds", "Coconut"],
        },
    }

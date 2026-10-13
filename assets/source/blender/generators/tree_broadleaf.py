"""Broadleaf shade tree (rain-tree / mango type common on South-Asian campuses).

Tapered trunk with root flares, four main limbs and twigs into a rounded crown made of
overlapping lumpy leaf clusters (see generators/foliage.py). About 6 m tall with a ~4.5 m
crown; the trunk is clear to about 2.5 m so a player can walk past under the canopy edge.

Frame: origin = trunk centre on the ground, front faces -Y, Z up, metres.
Modeling and materials only; the shared pipeline renders and exports.
"""

import math

import bmesh
from mathutils import Vector

from generators.foliage import (Blob, LeafCards, add_blob_mesh, bark_material, inner_material, leaf_material,
                                scatter_on_blobs)
from pipeline.modeling import add_tube, extreme_points, mesh_object

COLLECTION_NAME = "BroadleafTree"

DEFAULT_PARAMS = {
    "trunk_height": 2.3,
    "trunk_radius": 0.19,
    "crown_z": 4.2,
    "crown_rx": 1.2,          # ring of clusters around the crown axis
    "ring_clusters": 6,
    "low_clusters": 3,
    "leaf_length": 0.22,
    "leaf_width": 0.14,
    "leaf_density": 300.0,    # leaves per m2 of cluster surface
    "collision_half_m": 0.25,
}

LEAF_STOPS = (
    (0.00, (0.022, 0.060, 0.012)),
    (0.35, (0.048, 0.115, 0.020)),
    (0.75, (0.085, 0.165, 0.028)),
    (1.00, (0.150, 0.200, 0.040)),
)


def _curve(a, b, lift, n=6):
    """Points from a to b bowed upwards by `lift` at the middle."""
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, t) + Vector((0, 0, lift * math.sin(math.pi * t))) for t in (i / (n - 1) for i in range(n))]


def build(collection, rng, params):
    p = params
    crown = Vector((0.0, 0.0, p["crown_z"]))
    blobs = [Blob(rng, crown, 1.15, squash=0.9),
             Blob(rng, crown + Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.1, 0.2), 0.85)), 1.0, squash=0.9)]
    for k in range(p["ring_clusters"]):
        a = 2 * math.pi * k / p["ring_clusters"] + rng.uniform(-0.25, 0.25)
        rad = p["crown_rx"] * rng.uniform(0.85, 1.05)
        blobs.append(Blob(rng, (math.cos(a) * rad, math.sin(a) * rad, p["crown_z"] + rng.uniform(-0.2, 0.35)),
                          rng.uniform(0.92, 1.12), squash=0.85))
    for k in range(p["low_clusters"]):
        a = 2 * math.pi * (k + 0.5) / p["low_clusters"] + rng.uniform(-0.3, 0.3)
        rad = p["crown_rx"] * 0.6
        blobs.append(Blob(rng, (math.cos(a) * rad, math.sin(a) * rad, p["crown_z"] - 0.75), 0.82, squash=0.8))

    # Wood: trunk with a flared base, limbs to the ring clusters, twigs to the others.
    wood = bmesh.new()
    th, tr = p["trunk_height"], p["trunk_radius"]
    lean = Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.05, 0.05), 0.0))
    trunk_pts = [Vector((0, 0, z)) + lean * (z / th) ** 2 for z in (0.0, 0.15, 0.5, 1.2, 1.9, th, th + 0.5)]
    add_tube(wood, trunk_pts, [tr * 1.6, tr * 1.2, tr * 1.05, tr, tr * 0.95, tr * 0.88, tr * 0.6], sides=12,
             cap_start=True)
    top = trunk_pts[-2]
    for k in range(5):
        a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        add_tube(wood, [d * tr * 0.7 + Vector((0, 0, 0.28)), d * (tr + 0.12) + Vector((0, 0, 0.06)),
                        d * (tr + 0.28) + Vector((0, 0, -0.02))], [0.11, 0.07, 0.03], sides=6)
    for i, blob in enumerate(blobs[2:]):
        start = top + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), rng.uniform(-0.3, 0.2)))
        end = blob.center * 0.92 + Vector((0, 0, -0.2))
        limb = i < p["ring_clusters"]
        pts = _curve(start, end, rng.uniform(0.15, 0.4))
        add_tube(wood, pts, [r * (0.13 if limb else 0.08) for r in (1.0, 0.85, 0.7, 0.55, 0.42, 0.3)], sides=8)
        if limb:
            mid = pts[3]
            twig_end = blob.center + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0.4))
            add_tube(wood, _curve(mid, twig_end, 0.1, n=4), [0.05, 0.04, 0.03, 0.02], sides=6)
    trunk = mesh_object(collection, "Trunk", wood,
                        [bark_material("Bark", (0.105, 0.085, 0.065), (0.035, 0.028, 0.022))], smooth=True)

    inner = bmesh.new()
    for blob in blobs:
        add_blob_mesh(inner, blob, subdivisions=3)
    canopy_inner = mesh_object(collection, "CanopyInner", inner,
                               [inner_material("CanopyShade", (0.006, 0.016, 0.005))], smooth=True)

    cards = LeafCards()
    scatter_on_blobs(cards, rng, blobs, p["leaf_density"], p["leaf_length"], p["leaf_width"],
                     up_bias=0.45, depth=(0.94, 1.12), crown_center=crown + Vector((0, 0, 0.3)), crown_bias=0.8)
    leaf_count = cards.count
    leaves = cards.to_object(collection, "Leaves", [leaf_material("Leaves", LEAF_STOPS, translucency=0.12)])

    objects = [trunk, canopy_inner, leaves]
    h = p["collision_half_m"]
    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": [-h, h, -h, h],
        "info": {
            "design_size_m": {"trunk_clear_height_approx": round(p["crown_z"] - 0.75 - 0.82, 2),
                              "crown_width_approx": round(2 * (p["crown_rx"] * 1.05 + 1.12), 2)},
            "leaf_cards": leaf_count,
            "clusters": len(blobs),
            "footprint": "trunk only (collision); the canopy has none and Y-sorts with the trunk origin",
            "materials": ["Bark", "CanopyShade", "Leaves"],
        },
    }

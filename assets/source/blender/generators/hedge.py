"""Trimmed hedge section: a seamless 2 m module along X (like the wall modules).

A lumpy inner body (open tube along X with a rounded, trimmed cross-section) covered in small
leaf cards. Every irregularity is periodic over the module length (integer sine harmonics; leaves
scattered over x in [-L/2, L/2) only), so modules placed end to end form one continuous hedge.
The pipeline renders it between neighbour copies and keeps the bleed columns, as for the wall.

Frame: hedge runs along X, front faces -Y, Z up, origin = centre of the footprint on the
ground, metres. Modeling and materials only; the shared pipeline renders and exports.
"""

import math

import bmesh
from mathutils import Vector

from generators.foliage import LeafCards, inner_material, leaf_material, random_direction
from pipeline.modeling import extreme_points, mesh_object

COLLECTION_NAME = "Hedge"

DEFAULT_PARAMS = {
    "length": 2.0,
    "depth": 0.70,
    "height": 1.00,
    "corner_radius": 0.16,
    "leaf_length": 0.085,
    "leaf_width": 0.055,
    "leaf_density": 950.0,   # leaves per m2 of hedge surface
    "segments_x": 48,
}

LEAF_STOPS = (
    (0.00, (0.030, 0.080, 0.016)),
    (0.40, (0.055, 0.135, 0.024)),
    (0.80, (0.095, 0.185, 0.032)),
    (1.00, (0.160, 0.230, 0.045)),
)


def _profile(p):
    """Closed-top cross-section (y, z), front bottom -> top -> back bottom, with outward normals."""
    hd, h, r = p["depth"] / 2.0, p["height"], p["corner_radius"]
    pts = [(-hd + 0.04, 0.0), (-hd, 0.25)]
    for k in range(5):  # front top corner
        a = math.pi - (math.pi / 2) * k / 4
        pts.append((-hd + r + r * math.cos(a) + 0.03 * (k / 4), h - r + r * math.sin(a)))
    for k in range(5):  # back top corner
        a = math.pi / 2 - (math.pi / 2) * k / 4
        pts.append((hd - r + r * math.cos(a) - 0.03 * (1 - k / 4), h - r + r * math.sin(a)))
    pts += [(hd, 0.25), (hd - 0.04, 0.0)]
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    return pts, cum


def _at(pts, cum, s):
    """Point and outward normal at arc length s."""
    s = min(max(s, 0.0), cum[-1] - 1e-9)
    i = next(k for k in range(len(cum) - 1) if cum[k + 1] > s)
    t = (s - cum[i]) / (cum[i + 1] - cum[i])
    (y0, z0), (y1, z1) = pts[i], pts[i + 1]
    dy, dz = y1 - y0, z1 - z0
    ln = math.hypot(dy, dz)
    return (y0 + dy * t, z0 + dz * t), (-dz / ln, dy / ln)


def build(collection, rng, params):
    p = params
    L = p["length"]
    pts, cum = _profile(p)
    total = cum[-1]
    harmonics = [(rng.choice((1, 2, 3, 4, 5)), rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi),
                  rng.uniform(0.006, 0.018), rng.choice((2, 3, 4))) for _ in range(6)]

    def bulge(x, s):
        # Periodic in x (integer harmonics of L); fades out at the ground.
        v = sum(a * math.sin(2 * math.pi * m * x / L + ph) * math.sin(2 * math.pi * q * s / total + ps)
                for m, ph, ps, a, q in harmonics)
        return v * min(1.0, s / 0.3, (total - s) / 0.3)

    def surface(x, s, out=0.0):
        (y, z), (ny, nz) = _at(pts, cum, s)
        d = bulge(x, s) + out
        return Vector((x, y + ny * d, z + nz * d)), Vector((0.0, ny, nz))

    body = bmesh.new()
    nx, ns = p["segments_x"], 40
    grid = [[body.verts.new(surface(-L / 2 + L * i / nx, total * j / ns, -0.03)[0]) for j in range(ns + 1)]
            for i in range(nx + 1)]
    for i in range(nx):
        for j in range(ns):
            body.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    inner = mesh_object(collection, "HedgeInner", body, [inner_material("HedgeShade", (0.006, 0.017, 0.005))],
                        smooth=True)

    cards = LeafCards()
    area = L * total
    for _ in range(int(area * p["leaf_density"])):
        x = rng.uniform(-L / 2, L / 2)
        s = rng.uniform(0.02, total - 0.02)
        pos, n = surface(x, s, rng.uniform(-0.015, 0.03))
        shade = (n + Vector((0, 0, 0.6))).normalized()
        facing = (n + random_direction(rng) * 0.8).normalized()
        k = rng.uniform(0.8, 1.2)
        cards.add(pos, facing, p["leaf_length"] * k, p["leaf_width"] * k, rng.uniform(0, 2 * math.pi), rng.random(),
                  shading_normal=shade, droop=0.01)
    leaf_count = cards.count
    leaves = cards.to_object(collection, "HedgeLeaves", [leaf_material("HedgeLeaves", LEAF_STOPS, translucency=0.1,
                                                                       ao_distance=0.1)])
    objects = [inner, leaves]
    hl, hd = L / 2.0, p["depth"] / 2.0
    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": [-hl, hl, -hd, hd],
        "tile_period_x_m": L,
        "info": {
            "design_size_m": {"length_x": L, "depth_y": p["depth"], "height_z": p["height"]},
            "leaf_cards": leaf_count,
            "tiling": "periodic over the module length (integer harmonics; leaves only in [-L/2, L/2))",
            "materials": ["HedgeShade", "HedgeLeaves"],
        },
    }

"""Main Gate leaves: the pair of closed black steel gate leaves across the passage.

Reference: Docs/map-reference/area1/mainGate.jpg (dark leaves with close vertical bars low
down and open bracing above) and whole view.png (diagonal braces visible from above). In
reality the leaves stand part-way into the passage; in game they sit at the gate stop line
so the existing collision stop is preserved (an approximation). Dimensions estimated.

Origin: on the ground at the gate axis, centre of the leaf thickness. The leaves span the
clear passage width of MainGateTower (x = +-clear_half).
"""

import math

from generators.landmark_common import finish_boxes, steel_material
from pipeline.modeling import BoxBuilder

COLLECTION_NAME = "MainGateLeaves"

DEFAULT_PARAMS = {
    "clear_half": 2.38,
    "height": 2.5,
    "thickness": 0.06,
    "frame": 0.08,
    "mid_rail_z": 1.05,
    "bar_pitch": 0.12,
    "bar_width": 0.025,
    "upper_bar_pitch": 0.36,
    "brace_width": 0.06,
    "jamb_gap": 0.02,
    "meeting_gap": 0.01,
}


def _bar(builder, x0, z0, x1, z1, width, y0, y1):
    """A straight flat bar between two points in the XZ plane."""
    length = math.hypot(x1 - x0, z1 - z0)
    nx, nz = -(z1 - z0) / length * width / 2.0, (x1 - x0) / length * width / 2.0
    builder.add_prism_xz([(x0 - nx, z0 - nz), (x1 - nx, z1 - nz), (x1 + nx, z1 + nz), (x0 + nx, z0 + nz)], y0, y1)


def build(collection, rng, params):
    p = params
    t, f, h = p["thickness"] / 2.0, p["frame"], p["height"]
    mid = p["mid_rail_z"]
    b = BoxBuilder()
    for side in (-1.0, 1.0):
        inner, outer = p["meeting_gap"] / 2.0, p["clear_half"] - p["jamb_gap"]
        x0, x1 = (inner, outer) if side > 0 else (-outer, -inner)
        b.add(x0, x0 + f, -t, t, 0.0, h)                       # stiles
        b.add(x1 - f, x1, -t, t, 0.0, h)
        for z0, z1 in ((0.04, 0.04 + f), (mid, mid + f), (h - f, h)):   # rails
            b.add(x0 + f, x1 - f, -t, t, z0, z1)
        x = x0 + f + p["bar_pitch"] / 2.0                      # close bars, lower panel
        while x + p["bar_width"] < x1 - f:
            b.add(x, x + p["bar_width"], -t * 0.6, t * 0.6, 0.04 + f, mid)
            x += p["bar_pitch"]
        x = x0 + f + p["upper_bar_pitch"] / 2.0                # sparse bars, upper panel
        while x + p["bar_width"] < x1 - f:
            b.add(x, x + p["bar_width"], -t * 0.6, t * 0.6, mid + f, h - f)
            x += p["upper_bar_pitch"]
        # diagonal brace: low at the hinge side, high at the meeting stiles
        hinge_x, meet_x = (x1 - f, x0 + f) if side > 0 else (x0 + f, x1 - f)
        _bar(b, hinge_x, mid + f, meet_x, h - f, p["brace_width"], -t * 0.8, t * 0.8)
        _bar(b, hinge_x, h - f, (hinge_x + meet_x) / 2.0, mid + f, p["brace_width"] * 0.8, -t * 0.7, t * 0.7)
    leaves = finish_boxes(collection, "GateLeaves", b, [steel_material("GateSteel")], bevel_width=0.004)

    half = p["clear_half"]
    return {
        "objects": [leaves],
        "bounds_points_m": [(x, y, z) for x in (-half, half) for y in (-t, t) for z in (0.0, h)],
        "footprint_m": [-half, half, -t, t],
        "info": {
            "design_size_m": {"width_x": 2 * half, "depth_y": 2 * t, "height_z": h},
            "materials": ["GateSteel"],
            "connection_point": "origin = gate axis at the leaf plane; spans MainGateTower's clear passage",
            "reference": "Docs/map-reference/area1/mainGate.jpg + whole view.png; leaves are set back in "
                         "reality, placed at the gate stop line in game (approximation)",
        },
    }

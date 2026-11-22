"""Map v2 infrastructure modules (D46): the modelled edges of the lakes, the causeways and the canal bridge.

    python assets/source/blender/tools/author_infra_v2.py            # write configs
    python assets/source/blender/tools/author_infra_v2.py --list

Two module kinds, each 4 m long, rendered in the four directions the campus's water edges run (the camera never
turns, so a diagonal edge needs its own render):
  v2_parapet_*   the lakes' low brick parapet: a 0.65 m wall with a moulded coping, piers every 2 m, weep holes
  v2_bridge_*    the causeways' bridge balustrade (photo 02): brick piers, an arched brick screen between them, a
                 coping, and a painted steel rail on top
Suffixes: ew (runs east-west), ns (north-south), se (towards the south-east, the diagonal causeway), ne.
tools/zones/campus_world.py places them along every water edge from the layout.
"""

import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from author_lib import MATS, box, cyl, mats_for, prism, rotated_z, write_config  # noqa: E402
import author_campus_v2  # noqa: E402,F401  (registers the v2 materials in MATS)

CATEGORY = "campus_v2"
LENGTH = 4.0
DIRS = {"ew": 0.0, "ns": 90.0, "se": -45.0, "ne": 45.0}   # Blender degrees about Z (Y is north)
ASSETS = []


def parapet():
    """Along +X, centred on the origin: low brick wall, coping, piers, weep holes."""
    L, t, h = LENGTH, 0.36, 0.65
    P = [box(-L / 2, L / 2, -t / 2, t / 2, 0.0, h, "v2_brick"),
         box(-L / 2 - 0.02, L / 2 + 0.02, -t / 2 - 0.06, t / 2 + 0.06, h, h + 0.1, "v2_coping"),
         box(-L / 2 - 0.02, L / 2 + 0.02, -t / 2 - 0.03, t / 2 + 0.03, h + 0.1, h + 0.14, "v2_coping")]
    for x in (-L / 2 + 0.25, 0.0, L / 2 - 0.25):
        P += [box(x - 0.24, x + 0.24, -t / 2 - 0.08, t / 2 + 0.08, 0.0, h + 0.18, "v2_brick"),
              box(x - 0.28, x + 0.28, -t / 2 - 0.12, t / 2 + 0.12, h + 0.18, h + 0.28, "v2_coping")]
    for x in (-1.0, 1.0):
        P.append(box(x - 0.05, x + 0.05, -t / 2 - 0.01, t / 2 + 0.01, 0.08, 0.16, "v2_void"))
    return P, h + 0.28


def bridge():
    """Along +X: brick piers every 2 m, an arched brick screen, a coping, a steel rail on posts."""
    L, t, h = LENGTH, 0.3, 0.95
    P = []
    for x in (-L / 2 + 0.22, 0.0, L / 2 - 0.22):
        P += [box(x - 0.22, x + 0.22, -t / 2 - 0.05, t / 2 + 0.05, 0.0, h + 0.15, "v2_brick"),
              box(x - 0.26, x + 0.26, -t / 2 - 0.09, t / 2 + 0.09, h + 0.15, h + 0.24, "v2_coping")]
    for xa, xb in ((-L / 2 + 0.44, -0.22), (0.22, L / 2 - 0.44)):
        cx, hw = (xa + xb) / 2, (xb - xa) / 2
        spring, crown = 0.35, 0.35 + hw * 0.8
        arc = [(cx + hw * math.cos(math.pi * k / 14), spring + (crown - spring) * math.sin(math.pi * k / 14)) for k in range(15)]
        screen = [(xa, 0.0), (xb, 0.0), (xb, spring)] + arc + [(xa, spring), (xa, h), (xb, h)]
        screen = [(xa, 0.0), (xa, h), (xb, h), (xb, 0.0), (xb, spring)] + arc[1:-1] + [(xa, spring)]
        # the arched opening as a gap: build the screen as the two spandrels plus the band over the crown
        left = [(xa, spring), (xa, h), (cx, h), (cx, crown)] + [p for p in reversed(arc) if p[0] <= cx + 1e-6][1:]
        right = [(cx, crown), (cx, h), (xb, h), (xb, spring)] + [p for p in arc if p[0] >= cx - 1e-6][1:-1]
        P += [prism(left, [-t / 2, t / 2], "v2_brick"), prism(right, [-t / 2, t / 2], "v2_brick"),
              box(xa, xb, -t / 2, t / 2, 0.0, 0.12, "v2_brick")]
    P += [box(-L / 2, L / 2, -t / 2 - 0.06, t / 2 + 0.06, h, h + 0.09, "v2_coping")]
    for x in (-L / 2 + 0.22, -1.0, 0.0, 1.0, L / 2 - 0.22):
        P.append(cyl([x, 0.0, h + 0.09], [x, 0.0, h + 0.62], 0.025, "v2_frame_green", sides=8))
    P += [cyl([-L / 2, 0.0, h + 0.62], [L / 2, 0.0, h + 0.62], 0.035, "v2_frame_green", sides=10),
          cyl([-L / 2, 0.0, h + 0.38], [L / 2, 0.0, h + 0.38], 0.02, "v2_frame_green", sides=8)]
    return P, h + 0.7


def boundary_wall():
    """Along +X: the campus wall: 2.4 m brick on a plinth, pilasters with caps every 2 m, concrete coping, angled
    iron posts carrying barbed wire, a moss-dark base."""
    L, t, h = LENGTH, 0.25, 2.4
    P = [box(-L / 2, L / 2, -t / 2 - 0.08, t / 2 + 0.08, 0.0, 0.35, "v2_concrete"),
         box(-L / 2, L / 2, -t / 2, t / 2, 0.35, h, "v2_brick_old"),
         box(-L / 2 - 0.02, L / 2 + 0.02, -t / 2 - 0.07, t / 2 + 0.07, h, h + 0.1, "v2_coping")]
    for x in (-L / 2 + 0.2, 0.0, L / 2 - 0.2):
        P += [box(x - 0.2, x + 0.2, -t / 2 - 0.1, t / 2 + 0.1, 0.0, h + 0.15, "v2_brick_old"),
              box(x - 0.24, x + 0.24, -t / 2 - 0.14, t / 2 + 0.14, h + 0.15, h + 0.27, "v2_coping")]
        P.append(box(x - 0.025, x + 0.025, -0.025, 0.025, h + 0.27, h + 0.75, "v2_steel",
                     rot=[-35, 0, 0], pivot=[x, 0.0, h + 0.27]))
    for k, (dz, dy) in enumerate(((0.15, -0.1), (0.3, -0.2), (0.45, -0.3))):
        P.append(cyl([-L / 2, dy, h + 0.27 + dz], [L / 2, dy, h + 0.27 + dz], 0.012, "v2_rail", sides=6))
    return P, h + 0.8


def main():
    for kind, fn, desc in (("wall", boundary_wall, "the campus boundary wall with barbed wire"),
                           ("parapet", parapet, "the lakes' low brick parapet with its coping and piers"),
                           ("bridge", bridge, "the causeways' arched brick balustrade with a steel rail (photo 02)")):
        parts, h = fn()
        for suffix, deg in DIRS.items():
            asset_id = f"v2_{kind}_{suffix}"
            p = rotated_z(parts, deg) if deg else parts
            r = LENGTH / 2 + 0.3
            objects = {"Base": {"parts": [box(-0.1, 0.1, -0.1, 0.1, 0.0, 0.01, "v2_concrete")], "bevel": 0.0},
                       "Wall": {"parts": p, "bevel": 0.008}}
            layers = [{"name": "Wall", "objects": ["Wall"], "sort_y_m": 0.0,
                       "fade": {"rects_m": {"Behind": [-r, r, 0.3, r + 1.19 * h]}, "alpha": 0.4, "seconds": 0.3}}]
            ASSETS.append(asset_id)
            if "--list" in sys.argv:
                continue
            params = {"mats": mats_for(objects), "objects": objects, "footprint_m": [-r, r, -r, r], "lights": [],
                      "ceiling_z": None}
            scene = "V2" + "".join(w.capitalize() for w in f"{kind}_{suffix}".split("_"))
            write_config(asset_id, CATEGORY, scene, f"{kind} module ({suffix}): {desc}.", params, px_per_m=96.0,
                         samples=128, layers=layers, collision={"enabled": False})
    if "--list" in sys.argv:
        print("\n".join(ASSETS))
    else:
        print(f"infra v2: {len(ASSETS)} module configs")


if __name__ == "__main__":
    main()

"""Map v2 sports courts (D46): the courts strip by the Main Gate and the Female Hall's court, modelled.

    python assets/source/blender/tools/author_courts_v2.py            # write configs
    python assets/source/blender/tools/author_courts_v2.py --list

Each court is one asset centred on its concrete pad (data/campus/campus_layout.json):
  Base (sprite z -9, on the ground band, under the player): the pad, the acrylic playing surface with its real
       line markings, wear near the baselines
  layers (Y-sorted 3D): the chain-link fence runs, the net and its winding posts, the goals and the hoops
tools/zones/campus_world.py places them; the flat court polygons stay only as footstep surfaces.
"""

import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from author_lib import MATS, box, cyl, mats_for, write_config  # noqa: E402
import author_campus_v2  # noqa: E402,F401  (the v2 materials)

ROOT = Path(__file__).resolve().parents[4]
CATEGORY = "campus_v2"
MANIFEST = ROOT / "data/campus/court_assets.json"
MATS.update({
    "v2_acrylic_green": {"color": [0.2, 0.42, 0.34], "rough": 0.55, "var": 0.08, "var_scale": 1.5, "stains": 0.25,
                         "stain_color": [0.16, 0.3, 0.25], "bump": 0.08, "bump_scale": 120},
    "v2_acrylic_blue": {"color": [0.17, 0.3, 0.42], "rough": 0.55, "var": 0.08, "var_scale": 1.5, "stains": 0.25,
                        "stain_color": [0.14, 0.22, 0.3], "bump": 0.08, "bump_scale": 120},
    "v2_acrylic_red": {"color": [0.5, 0.2, 0.15], "rough": 0.55, "var": 0.08, "var_scale": 1.5, "stains": 0.3,
                       "stain_color": [0.38, 0.16, 0.12], "bump": 0.08, "bump_scale": 120},
    "v2_line": {"color": [0.9, 0.9, 0.86], "rough": 0.5, "var": 0.05, "stains": 0.2, "stain_color": [0.6, 0.6, 0.55]},
    "v2_net": {"color": [0.1, 0.1, 0.1], "rough": 0.8,
               "pattern": {"type": "checker", "size": 0.05, "color2": [0.35, 0.35, 0.33]}},
    "v2_net_band": {"color": [0.92, 0.92, 0.9], "rough": 0.5},
    "v2_post_green": {"color": [0.15, 0.3, 0.22], "rough": 0.4, "metal": 0.5, "stains": 0.3, "stain_color": [0.4, 0.25, 0.12]},
    "v2_backboard": {"color": [0.88, 0.88, 0.86], "rough": 0.4, "stains": 0.3, "stain_color": [0.55, 0.55, 0.5]},
    "v2_hoop": {"color": [0.85, 0.3, 0.08], "rough": 0.4, "metal": 0.5},
})
ASSETS = []


def lines_rect(x0, x1, y0, y1, w=0.06, z=0.031):
    return [box(x0, x1, y0, y0 + w, 0.0, z, "v2_line"), box(x0, x1, y1 - w, y1, 0.0, z, "v2_line"),
            box(x0, x0 + w, y0, y1, 0.0, z, "v2_line"), box(x1 - w, x1, y0, y1, 0.0, z, "v2_line")]


def fence_run(xa, ya, xb, yb, h=3.2):
    """Chain-link: galvanised posts every 2.5 m, a top rail, the mesh as a thin chequered panel."""
    P = []
    L = math.hypot(xb - xa, yb - ya)
    n = max(1, int(L // 2.5))
    horiz = abs(yb - ya) < 1e-6
    for k in range(n + 1):
        t = k / n
        x, y = xa + (xb - xa) * t, ya + (yb - ya) * t
        P.append(cyl([x, y, 0.0], [x, y, h], 0.04, "v2_steel", sides=8))
    P.append(cyl([xa, ya, h], [xb, yb, h], 0.03, "v2_steel", sides=8))
    if horiz:
        P.append(box(min(xa, xb), max(xa, xb), ya - 0.01, ya + 0.01, 0.05, h, "v2_fence"))
    else:
        P.append(box(xa - 0.01, xa + 0.01, min(ya, yb), max(ya, yb), 0.05, h, "v2_fence"))
    return P


def court(asset_id, scene, desc, pad, court_rect, surface, kind):
    """pad / court_rect in layout metres [x0, y0, x1, y1]; Blender frame centred on the pad (Y north)."""
    cx, cy = (pad[0] + pad[2]) / 2, (pad[1] + pad[3]) / 2
    R = lambda r: (r[0] - cx, r[2] - cx, cy - r[3], cy - r[1])  # noqa: E731
    PX0, PX1, PY0, PY1 = R(pad)
    X0, X1, Y0, Y1 = R(court_rect)
    base = [box(PX0, PX1, PY0, PY1, -0.05, 0.02, "v2_concrete"), box(X0 - 1.0, X1 + 1.0, Y0 - 1.5, Y1 + 1.5, 0.0, 0.028, surface)]
    base += lines_rect(X0, X1, Y0, Y1)
    mx, my = (X0 + X1) / 2, (Y0 + Y1) / 2
    layers = []
    if kind == "tennis":
        sw = (X1 - X0) * 0.125                                   # singles sidelines and the service boxes
        base += [box(X0 + sw, X0 + sw + 0.05, Y0, Y1, 0.0, 0.031, "v2_line"), box(X1 - sw - 0.05, X1 - sw, Y0, Y1, 0.0, 0.031, "v2_line")]
        for s in (-1, 1):
            yy = my + s * (Y1 - Y0) * 0.27
            base.append(box(X0 + sw, X1 - sw, yy - 0.03, yy + 0.03, 0.0, 0.031, "v2_line"))
        base.append(box(mx - 0.03, mx + 0.03, my - (Y1 - Y0) * 0.27, my + (Y1 - Y0) * 0.27, 0.0, 0.031, "v2_line"))
        net = [cyl([X0 - 0.5, my, 0], [X0 - 0.5, my, 1.07], 0.05, "v2_post_green", sides=10),
               cyl([X1 + 0.5, my, 0], [X1 + 0.5, my, 1.07], 0.05, "v2_post_green", sides=10),
               box(X0 - 0.5, X1 + 0.5, my - 0.01, my + 0.01, 0.15, 0.95, "v2_net"),
               box(X0 - 0.5, X1 + 0.5, my - 0.03, my + 0.03, 0.92, 1.0, "v2_net_band"),
               box(mx - 0.03, mx + 0.03, my - 0.02, my + 0.02, 0.0, 0.92, "v2_net_band")]
        layers.append(("Net", net, my, 1.1))
    elif kind in ("futsal", "badminton"):
        base.append(box(X0, X1, my - 0.03, my + 0.03, 0.0, 0.031, "v2_line"))
        rr = min(1.8, (X1 - X0) * 0.15)
        for k in range(28):                                      # centre circle as short dashes of line
            a0, a1 = 2 * math.pi * k / 28, 2 * math.pi * (k + 0.8) / 28
            base.append(box(mx + rr * math.cos(a0) - 0.04, mx + rr * math.cos(a0) + 0.04,
                            my + rr * math.sin(a0) - 0.04, my + rr * math.sin(a0) + 0.04, 0.0, 0.031, "v2_line"))
        if kind == "futsal":
            for end, s in ((Y0, 1), (Y1, -1)):
                gy = end
                goal = [box(mx - 1.5, mx - 1.42, gy - 0.04, gy + 0.04, 0, 2.0, "v2_line"),
                        box(mx + 1.42, mx + 1.5, gy - 0.04, gy + 0.04, 0, 2.0, "v2_line"),
                        box(mx - 1.5, mx + 1.5, gy - 0.04, gy + 0.04, 1.94, 2.02, "v2_line"),
                        box(mx - 1.5, mx + 1.5, gy - s * 1.0 - 0.01, gy - s * 1.0 + 0.01, 0.1, 1.9, "v2_net"),
                        box(mx - 1.5, mx + 1.5, min(gy, gy - s * 1.0), max(gy, gy - s * 1.0), 1.95, 1.97, "v2_net")]
                hoop_y = gy - s * 1.6
                goal += [cyl([mx, hoop_y, 0], [mx, hoop_y, 3.4], 0.08, "v2_steel", sides=10),
                         box(mx - 0.9, mx + 0.9, hoop_y + s * 1.0 - 0.03, hoop_y + s * 1.0 + 0.03, 2.9, 3.95, "v2_backboard"),
                         box(mx - 0.05, mx + 0.05, hoop_y, hoop_y + s * 1.0, 3.3, 3.4, "v2_steel"),
                         {"tube": [[mx + 0.23 * math.cos(2 * math.pi * k / 12), hoop_y + s * 1.25 + 0.23 * math.sin(2 * math.pi * k / 12), 3.05]
                                   for k in range(13)], "r": 0.012, "mat": "v2_hoop", "sides": 6}]
                layers.append(("GoalSouth" if s == 1 else "GoalNorth", goal, min(gy, hoop_y) - 0.2, 4.0))
        else:
            net = [cyl([X0 - 0.3, my, 0], [X0 - 0.3, my, 1.55], 0.04, "v2_post_green", sides=10),
                   cyl([X1 + 0.3, my, 0], [X1 + 0.3, my, 1.55], 0.04, "v2_post_green", sides=10),
                   box(X0 - 0.3, X1 + 0.3, my - 0.01, my + 0.01, 0.8, 1.52, "v2_net"),
                   box(X0 - 0.3, X1 + 0.3, my - 0.025, my + 0.025, 1.5, 1.55, "v2_net_band")]
            layers.append(("Net", net, my, 1.6))
    if kind != "badminton":
        layers.append(("FenceSouth", fence_run(PX0, PY0, PX1, PY0), PY0, 3.2))
        layers.append(("FenceNorth", fence_run(PX0, PY1, PX1, PY1), PY1 - 0.05, 3.2))
        layers.append(("FenceWest", fence_run(PX0, PY0, PX0, PY1), PY0 + 0.02, 3.2))
        layers.append(("FenceEast", fence_run(PX1, PY0, PX1, PY1), PY0 + 0.03, 3.2))
    objects = {"Base": {"parts": base, "bevel": 0.0}}
    lay = []
    for name, parts, sort_y, h in layers:
        objects[name] = {"parts": parts, "bevel": 0.004}
        lay.append({"name": name, "objects": [name], "sort_y_m": round(sort_y, 3),
                    "fade": {"rects_m": {"Behind": [round(PX0 - 0.5, 3), round(PX1 + 0.5, 3), round(sort_y + 0.4, 3),
                                                    round(sort_y + 0.4 + 1.19 * h, 3)]}, "alpha": 0.45, "seconds": 0.3}})
    ASSETS.append({"asset_id": asset_id, "scene": scene, "centre_m": [cx, cy], "pad": pad})
    if "--list" in sys.argv:
        return
    params = {"mats": mats_for(objects), "objects": objects, "footprint_m": [PX0, PX1, PY0, PY1], "lights": [], "ceiling_z": None}
    write_config(asset_id, CATEGORY, scene, desc, params, px_per_m=64.0, samples=128, layers=lay,
                 collision={"enabled": False}, sprite_z_index=-9)


def football_goal(asset_id, scene, centre, facing_south):
    """A full-size goal (7.32 x 2.44 m): white posts and crossbar, a net box 2 m deep, back stanchions."""
    s = -1.0 if facing_south else 1.0          # the side the net box extends to (north for the north goal)
    hw, h, d = 3.66, 2.44, 2.0
    P = [cyl([-hw, 0, 0], [-hw, 0, h], 0.06, "v2_line", sides=12), cyl([hw, 0, 0], [hw, 0, h], 0.06, "v2_line", sides=12),
         cyl([-hw - 0.06, 0, h], [hw + 0.06, 0, h], 0.06, "v2_line", sides=12),
         cyl([-hw, s * d, 0], [-hw, s * d, h * 0.6], 0.03, "v2_steel", sides=8), cyl([hw, s * d, 0], [hw, s * d, h * 0.6], 0.03, "v2_steel", sides=8),
         box(-hw, hw, s * d - 0.01, s * d + 0.01, 0.0, h * 0.6, "v2_net"),
         box(-hw, hw, min(0, s * d), max(0, s * d), h - 0.01, h + 0.01, "v2_net"),
         box(-hw - 0.01, -hw + 0.01, min(0, s * d), max(0, s * d), 0.0, h, "v2_net"),
         box(hw - 0.01, hw + 0.01, min(0, s * d), max(0, s * d), 0.0, h, "v2_net")]
    objects = {"Base": {"parts": [box(-0.2, 0.2, -0.2, 0.2, 0.0, 0.01, "v2_line")], "bevel": 0.0},
               "Goal": {"parts": P, "bevel": 0.004}}
    sort_y = min(0.0, s * d)
    lay = [{"name": "Goal", "objects": ["Goal"], "sort_y_m": round(sort_y, 3),
            "fade": {"rects_m": {"Behind": [-hw - 0.5, hw + 0.5, sort_y + 0.3, sort_y + 0.3 + 1.19 * h]}, "alpha": 0.5, "seconds": 0.3}}]
    ASSETS.append({"asset_id": asset_id, "scene": scene, "centre_m": centre, "pad": None})
    if "--list" in sys.argv:
        return
    params = {"mats": mats_for(objects), "objects": objects, "footprint_m": [-hw, hw, -d, d], "lights": [], "ceiling_z": None}
    write_config(asset_id, CATEGORY, scene, "Football goal on the Central Field.", params, px_per_m=96.0, samples=128,
                 layers=lay, collision={"enabled": False})


def main():
    lay = json.loads((ROOT / "data/campus/campus_layout.json").read_text(encoding="utf-8"))
    g = {x["id"]: x for x in lay["ground"]}
    court("v2_court_tennis", "V2CourtTennis", "The tennis court by the Main Gate: green acrylic, white lines, net, chain-link fence.",
          g["tennis_pad"]["rect"], g["tennis_court"]["rect"], "v2_acrylic_green", "tennis")
    court("v2_court_futsal", "V2CourtFutsal", "The futsal / basketball court by the Main Gate: blue acrylic, goals with nets, hoops, fence.",
          g["futsal_pad"]["rect"], g["futsal_court"]["rect"], "v2_acrylic_blue", "futsal")
    fh = g["female_hall_court"]["rect"]
    court("v2_court_badminton", "V2CourtBadminton", "The Female Hall's badminton court in its compound: red acrylic, white lines, net.",
          [fh[0] - 0.8, fh[1] - 0.8, fh[2] + 0.8, fh[3] + 0.8], fh, "v2_acrylic_red", "badminton")
    pitch = next(f for f in lay["features"] if f.get("kind") == "pitch")["rect"]
    gx = (pitch[0] + pitch[2]) / 2
    football_goal("v2_goal_north", "V2GoalNorth", [gx, pitch[1]], True)
    football_goal("v2_goal_south", "V2GoalSouth", [gx, pitch[3]], False)
    if "--list" in sys.argv:
        print("\n".join(a["asset_id"] for a in ASSETS))
        return
    MANIFEST.write_text(json.dumps({"assets": [{"asset_id": a["asset_id"], "scene": f"res://scenes/props/{CATEGORY}/{a['scene']}.tscn",
                                                 "centre_m": a["centre_m"], "pad": a["pad"]} for a in ASSETS]}, indent=1) + "\n",
                        encoding="utf-8")
    print(f"courts v2: {len(ASSETS)} court configs; manifest data/campus/court_assets.json")


if __name__ == "__main__":
    main()

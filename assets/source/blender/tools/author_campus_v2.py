"""Map v2 campus buildings (D42-D47): every site of data/campus/campus_layout.json as a detailed Blender model.

    python assets/source/blender/tools/author_campus_v2.py            # write / refresh every config + manifest
    python assets/source/blender/tools/author_campus_v2.py --list     # asset ids

Then render: python assets/source/blender/build_asset.py <ids>  (or tools/campus/build_buildings.py for all).

The camera looks north at 40 degrees, so the SOUTH face and the ROOF of every building are what the player sees:
they carry the detail. Nothing is a bare slab:
  facades   real piers, spandrels, sills and recessed glazing (openings have depth and cast shadow), mullions,
            curtains behind some panes, rain pipes; brick from a CC0 photo texture with mortar relief
  arcades   arch-cut spandrels (round or pointed) over piers, a deep veranda behind with doors and windows
  towers    brick cylinders with slit windows on the camera side, concrete coping rings
  roofs     slab, brick parapet, concrete coping, black water tanks on brick stands, stair heads with doors,
            AC condensers, vent pipes; sawtooth north-light roofs on the workshops; red sheet roofs on Academic 3
  doors     steps, concrete surround, panelled double doors, a canopy on brackets, a lit name board
Frame (Blender): origin on the ground at the asset's centre, +X east, +Y north (layout y is south, so Y = cy - y),
Z up, metres. Each footprint part is its own object and sorted layer (it Y-sorts on its own south edge and fades
when the player is behind it, D31). Collision comes from the layout (tools/zones/campus_world.py), not the render.
Writes data/campus/building_assets.json: which asset stands where, for the campus generator.
"""

import hashlib
import json
import math
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from author_lib import MATS, box, cyl, lathe, mats_for, pointed_arch, half_disc, prism, rotated_z, text, write_config  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
LAYOUT = ROOT / "data/campus/campus_layout.json"
MANIFEST = ROOT / "data/campus/building_assets.json"
CATEGORY = "campus_v2"
PX = 64.0
SAMPLES = 160
TEX = "assets/source/textures"

# --- materials (photo-textured where it shows) -----------------------------------------------------------------
BRICK_IMG = {"type": "image", "albedo": f"{TEX}/red_brick_03/red_brick_03_diffuse_2k.jpg", "tile_m": 1.0}
CONC_IMG = {"type": "image", "albedo": f"{TEX}/concrete_floor_01/concrete_floor_01_diffuse_2k.jpg", "tile_m": 2.4}
MATS.update({
    "v2_brick": {"color": [1.0, 0.86, 0.78], "rough": 0.85, "var": 0.07, "var_scale": 1.2, "pattern": BRICK_IMG,
                 "stains": 0.22, "stain_color": [0.3, 0.16, 0.12], "stain_scale": 0.5, "grime": 0.18, "grime_h": 1.2},
    "v2_brick_reveal": {"color": [0.78, 0.66, 0.6], "rough": 0.88, "var": 0.05, "pattern": BRICK_IMG},
    "v2_brick_old": {"color": [0.9, 0.74, 0.66], "rough": 0.9, "var": 0.12, "pattern": BRICK_IMG,
                     "stains": 0.45, "stain_color": [0.22, 0.2, 0.15], "stain_scale": 0.4, "grime": 0.3, "grime_h": 1.5},
    "v2_concrete": {"color": [0.92, 0.9, 0.86], "rough": 0.85, "var": 0.1, "pattern": CONC_IMG,
                    "stains": 0.42, "stain_color": [0.36, 0.35, 0.31], "stain_scale": 0.7},
    "v2_roof": {"color": [0.52, 0.51, 0.48], "rough": 0.9, "var": 0.2, "var_scale": 0.9, "part_var": 0.0,
                "pattern": {"type": "tiles", "size": 0.6, "color2": [0.45, 0.44, 0.41], "mortar": 0.018,
                            "mortar_color": [0.4, 0.39, 0.36]},
                "stains": 0.6, "stain_color": [0.22, 0.23, 0.2], "stain_scale": 0.45, "bump": 0.1, "bump_scale": 18},
    "v2_roof_patch": {"color": [0.42, 0.42, 0.41], "rough": 0.7, "var": 0.12, "var_scale": 2.0, "stains": 0.4,
                      "stain_color": [0.26, 0.26, 0.24], "bump": 0.2, "bump_scale": 30},
    "v2_streak": {"color": [0.26, 0.24, 0.21], "rough": 0.9, "var": 0.3, "var_scale": 4.0},
    "v2_coping": {"color": [0.6, 0.58, 0.54], "rough": 0.85, "var": 0.1, "var_scale": 3.0, "stains": 0.3,
                  "stain_color": [0.4, 0.38, 0.34], "stain_scale": 4.0, "bump": 0.15},
    "v2_plaster": {"color": [0.86, 0.8, 0.66], "rough": 0.85, "var": 0.08, "stains": 0.5, "stain_color": [0.5, 0.47, 0.36],
                   "stain_scale": 0.9, "bump": 0.1, "bump_scale": 25, "grime": 0.2, "grime_h": 1.0},
    "v2_plaster_white": {"color": [0.9, 0.89, 0.85], "rough": 0.85, "var": 0.06, "stains": 0.5,
                         "stain_color": [0.48, 0.48, 0.42], "stain_scale": 0.8, "bump": 0.08},
    "v2_glass": {"color": [0.07, 0.09, 0.11], "glass": True, "var": 0.0, "part_var": 0.0},
    "v2_glass_sky": {"color": [0.22, 0.27, 0.32], "glass": True, "var": 0.0, "part_var": 0.0},
    "v2_curtain_a": {"color": [0.55, 0.5, 0.38], "rough": 0.9, "var": 0.05},
    "v2_curtain_b": {"color": [0.32, 0.4, 0.5], "rough": 0.9, "var": 0.05},
    "v2_curtain_c": {"color": [0.55, 0.28, 0.24], "rough": 0.9, "var": 0.05},
    "v2_frame": {"color": [0.3, 0.31, 0.32], "rough": 0.4, "metal": 0.6, "var": 0.04},
    "v2_frame_green": {"color": [0.16, 0.3, 0.24], "rough": 0.45, "metal": 0.3, "var": 0.05, "stains": 0.2},
    "v2_void": {"color": [0.025, 0.022, 0.022], "rough": 0.95, "var": 0.0, "part_var": 0.0},
    "v2_door": {"color": [0.36, 0.21, 0.12], "rough": 0.5, "stains": 0.2, "pattern": {"type": "grain", "scale": [30, 0.6, 30]}},
    "v2_door_steel": {"color": [0.3, 0.4, 0.36], "rough": 0.5, "metal": 0.4, "stains": 0.35, "stain_color": [0.36, 0.22, 0.14]},
    "v2_floor_tile": {"color": [0.66, 0.6, 0.52], "rough": 0.35, "var": 0.06, "stains": 0.3,
                      "pattern": {"type": "tiles", "size": 0.45, "color2": [0.6, 0.55, 0.48], "mortar": 0.02,
                                  "mortar_color": [0.4, 0.37, 0.33]}},
    "v2_tank": {"color": [0.06, 0.06, 0.065], "rough": 0.45, "var": 0.04, "stains": 0.2, "stain_color": [0.3, 0.28, 0.24]},
    "v2_tank_blue": {"color": [0.12, 0.3, 0.55], "rough": 0.45, "var": 0.04},
    "v2_ac": {"color": [0.86, 0.86, 0.83], "rough": 0.5, "var": 0.04, "stains": 0.3, "stain_color": [0.5, 0.45, 0.35]},
    "v2_ac_grille": {"color": [0.2, 0.2, 0.2], "rough": 0.6, "metal": 0.4,
                     "pattern": {"type": "stripes", "period": 0.04, "color2": [0.45, 0.45, 0.44], "axis": "x"}},
    "v2_pipe": {"color": [0.78, 0.78, 0.75], "rough": 0.5, "var": 0.05, "stains": 0.3},
    "v2_pipe_dark": {"color": [0.2, 0.2, 0.21], "rough": 0.5, "metal": 0.3},
    # corrugated iron (CI sheet, the Bangladeshi workshop roof): real ribs in the bump, a patchwork of ages
    "v2_sheet": {"color": [0.55, 0.55, 0.54], "rough": 0.42, "metal": 0.6, "stains": 0.35, "stain_color": [0.42, 0.28, 0.18],
                 "pattern": {"type": "corrugated", "period": 0.1, "axis": "x"}, "height_strength": 0.9,
                 "bump_distance": 0.02},
    "v2_sheet_old": {"color": [0.43, 0.42, 0.4], "rough": 0.62, "metal": 0.4, "stains": 0.6, "stain_scale": 1.6,
                     "stain_color": [0.4, 0.24, 0.13], "var": 0.18, "var_scale": 2.0,
                     "pattern": {"type": "corrugated", "period": 0.1, "axis": "x"}, "height_strength": 0.9,
                     "bump_distance": 0.02},
    "v2_sheet_rust": {"color": [0.47, 0.27, 0.15], "rough": 0.82, "metal": 0.15, "stains": 0.55, "stain_scale": 2.2,
                      "stain_color": [0.26, 0.13, 0.07], "var": 0.25, "var_scale": 3.0,
                      "pattern": {"type": "corrugated", "period": 0.1, "axis": "x"}, "height_strength": 0.9,
                      "bump_distance": 0.02},
    "v2_skylight": {"color": [0.8, 0.78, 0.64], "rough": 0.5, "var": 0.12, "var_scale": 2.0, "stains": 0.35,
                    "stain_color": [0.5, 0.46, 0.34], "emit": [1.0, 0.95, 0.8], "emit_strength": 0.08,
                    "pattern": {"type": "corrugated", "period": 0.1, "axis": "x", "depth": 0.08}, "height_strength": 0.7,
                    "bump_distance": 0.02},
    "v2_turbine": {"color": [0.74, 0.75, 0.74], "rough": 0.3, "metal": 0.85, "stains": 0.25, "stain_color": [0.4, 0.3, 0.2],
                   "pattern": {"type": "stripes", "period": 0.05, "color2": [0.3, 0.31, 0.31], "axis": "x"}},
    "v2_sheet_red": {"color": [0.58, 0.17, 0.13], "rough": 0.5, "metal": 0.3, "stains": 0.35, "stain_color": [0.32, 0.12, 0.1],
                     "pattern": {"type": "corrugated", "period": 0.1, "axis": "y"}, "height_strength": 0.9,
                     "bump_distance": 0.02},
    "v2_sheet_blue": {"color": [0.2, 0.36, 0.55], "rough": 0.5, "metal": 0.3, "stains": 0.4, "stain_color": [0.35, 0.25, 0.18],
                      "pattern": {"type": "corrugated", "period": 0.1, "axis": "x"}, "height_strength": 0.9,
                      "bump_distance": 0.02},
    "v2_steel": {"color": [0.32, 0.34, 0.33], "rough": 0.45, "metal": 0.6, "stains": 0.3, "stain_color": [0.38, 0.22, 0.12]},
    "v2_rail": {"color": [0.12, 0.14, 0.13], "rough": 0.4, "metal": 0.6},
    "v2_sign_green": {"color": [0.08, 0.3, 0.18], "rough": 0.45, "stains": 0.2},
    "v2_sign_text": {"color": [0.95, 0.94, 0.88], "rough": 0.4, "emit": [1.0, 0.96, 0.85], "emit_strength": 0.15},
    "v2_lamp": {"color": [0.95, 0.92, 0.85], "rough": 0.2, "emit": [1.0, 0.9, 0.7], "emit_strength": 1.2},
    "v2_bamboo": {"color": [0.62, 0.5, 0.3], "rough": 0.7, "var": 0.2, "var_scale": 3.0},
    "v2_net": {"color": [0.1, 0.3, 0.18], "rough": 0.9,
               "pattern": {"type": "stripes", "period": 0.08, "color2": [0.06, 0.2, 0.12], "axis": "x"}},
    "v2_crane": {"color": [0.85, 0.62, 0.1], "rough": 0.5, "metal": 0.4, "stains": 0.3, "stain_color": [0.4, 0.25, 0.1]},
    "v2_sand": {"color": [0.72, 0.6, 0.42], "rough": 0.95, "bump": 0.3, "bump_scale": 40, "var": 0.1},
    "v2_brick_pile": {"color": [0.58, 0.28, 0.18], "rough": 0.9, "var": 0.15,
                      "pattern": {"type": "tiles", "size": 0.12, "offset": 0.5, "color2": [0.5, 0.22, 0.14], "mortar": 0.05,
                                  "mortar_color": [0.35, 0.2, 0.14]}},
    "v2_transformer": {"color": [0.42, 0.46, 0.44], "rough": 0.5, "metal": 0.5, "stains": 0.3, "stain_color": [0.3, 0.2, 0.12]},
    "v2_insulator": {"color": [0.55, 0.3, 0.2], "rough": 0.25, "spec": 0.8},
    "v2_fence": {"color": [0.45, 0.47, 0.46], "rough": 0.5, "metal": 0.5,
                 "pattern": {"type": "checker", "size": 0.06, "color2": [0.2, 0.22, 0.21]}},
    "v2_car_red": {"color": [0.55, 0.06, 0.06], "rough": 0.25, "metal": 0.5, "spec": 0.8},
    "v2_car_white": {"color": [0.86, 0.86, 0.84], "rough": 0.25, "metal": 0.4, "spec": 0.8},
    "v2_car_silver": {"color": [0.6, 0.62, 0.63], "rough": 0.25, "metal": 0.7, "spec": 0.8},
    "v2_car_black": {"color": [0.06, 0.06, 0.07], "rough": 0.2, "metal": 0.5, "spec": 0.8},
    "v2_tyre": {"color": [0.04, 0.04, 0.04], "rough": 0.8},
    "v2_taillight": {"color": [0.5, 0.03, 0.02], "rough": 0.2, "emit": [1.0, 0.08, 0.04], "emit_strength": 0.6},
    "v2_rust": {"color": [0.42, 0.2, 0.1], "rough": 0.8, "var": 0.3, "var_scale": 6.0},
    "v2_dome": {"color": [0.66, 0.64, 0.6], "rough": 0.7, "var": 0.1, "var_scale": 2.0, "stains": 0.45,
                "stain_color": [0.42, 0.41, 0.37], "stain_scale": 1.2, "bump": 0.1},
})

ASSETS = []          # dicts: asset_id, scene, desc, site, centre_m, objects, layers


def rng_for(key):
    return random.Random(int(hashlib.md5(key.encode()).hexdigest()[:8], 16))


# --- building blocks (Blender frame) ---------------------------------------------------------------------------

def facade(X0, X1, Y0, depth, z0, z1, storeys, bay, style, rng, glaze=True, keep_clear=None):
    """A south facade between X0..X1 whose outer face is at Y0, `depth` deep (openings recess by `depth`).
    Styles: hall (deep vertical windows), academic (wide windows with concrete sunshades), plaster (rendered
    walls, framed windows), workshop (a clerestory band), slits (narrow vertical slots), blank."""
    P = []
    W = X1 - X0
    H = z1 - z0
    nb = max(1, int(W // bay))
    margin = (W - nb * bay) / 2.0
    sh = H / storeys
    wall = "v2_plaster" if style == "plaster" else "v2_brick"
    reveal = "v2_plaster" if style == "plaster" else "v2_brick_reveal"
    Yb = Y0 + depth                      # back of the openings (glazing line)
    if style == "blank":
        P.append(box(X0, X1, Y0, Yb, z0, z1, wall))
        for k in range(1, nb):           # pilasters give the blank wall relief
            x = X0 + margin + k * bay
            P.append(box(x - 0.25, x + 0.25, Y0 - 0.12, Y0, z0, z1, wall))
        return P
    # end returns (close the facade at both ends)
    P.append(box(X0, X0 + margin + 0.3, Y0, Yb, z0, z1, wall))
    P.append(box(X1 - margin - 0.3, X1, Y0, Yb, z0, z1, wall))
    if style == "workshop":
        P.append(box(X0, X1, Y0, Yb, z0, z1 - 1.6, wall))
        P.append(box(X0, X1, Y0, Yb, z1 - 0.5, z1, wall))
        for k in range(nb + 1):
            x = X0 + margin + k * bay
            P.append(box(x - 0.35, x + 0.35, Y0 - 0.15, Yb, z0, z1, wall))
        P.append(box(X0, X1, Yb - 0.05, Yb, z1 - 1.6, z1 - 0.5, "v2_glass_sky"))
        for k in range(nb * 3):
            x = X0 + margin + (k + 0.5) * bay / 3
            P.append(box(x - 0.03, x + 0.03, Yb - 0.09, Yb - 0.04, z1 - 1.6, z1 - 0.5, "v2_frame"))
        return P
    for s in range(storeys):
        zs = z0 + s * sh
        sill, head = (0.9, sh - 0.55) if style != "slits" else (0.5, sh - 0.4)
        if style == "academic":
            sill, head = 0.85, sh - 0.7
        P.append(box(X0, X1, Y0, Yb, zs, zs + sill, wall))                 # sill band
        P.append(box(X0, X1, Y0, Yb, zs + head, zs + sh, wall))            # head band
        P.append(box(X0, X1, Y0 - 0.06, Y0 + 0.02, zs + sill - 0.08, zs + sill, "v2_coping"))  # sill lip
        if style == "academic":                                            # sunshade over each window row
            P.append(box(X0 + margin, X1 - margin, Y0 - 0.55, Y0, zs + head, zs + head + 0.14, "v2_concrete"))
        # glazing at the back of the recess, pane by pane (some with curtains drawn)
        for k in range(nb):
            xa = X0 + margin + k * bay + 0.3
            xb = xa + bay - 0.6
            if style == "slits":
                cx = (xa + xb) / 2
                xa, xb = cx - 0.25, cx + 0.25
            r = rng.random()
            mat = ("v2_curtain_a" if r < 0.12 else "v2_curtain_b" if r < 0.2 else "v2_curtain_c" if r < 0.26
                   else ("v2_glass_sky" if r < 0.55 else "v2_glass"))
            if glaze:
                P.append(box(xa, xb, Yb - 0.04, Yb, zs + sill, zs + head, mat))
                P.append(box((xa + xb) / 2 - 0.03, (xa + xb) / 2 + 0.03, Yb - 0.08, Yb - 0.04, zs + sill, zs + head,
                             "v2_frame_green" if style == "plaster" else "v2_frame"))
                P.append(box(xa, xb, Yb - 0.08, Yb - 0.04, zs + head - (head - sill) * 0.3 - 0.03,
                             zs + head - (head - sill) * 0.3 + 0.03, "v2_frame"))
            else:
                P.append(box(xa, xb, Yb - 0.04, Yb, zs + sill, zs + head, "v2_void"))
            # recess side faces in the darker reveal brick
            P.append(box(xa - 0.02, xa, Y0, Yb, zs + sill, zs + head, reveal))
            P.append(box(xb, xb + 0.02, Y0, Yb, zs + sill, zs + head, reveal))
        for k in range(nb + 1):                                            # piers between the openings
            x = X0 + margin + k * bay
            P.append(box(x - 0.3, x + 0.3, Y0, Yb, zs + sill, zs + head, wall))
    # rain pipes down the facade every few bays
    for k in range(1, nb, max(3, nb // 4)):
        x = X0 + margin + k * bay + 0.42
        if keep_clear is not None and abs(x - keep_clear) < 3.2:
            continue                       # no rain pipe down through the entrance canopy
        P.append(cyl([x, Y0 - 0.12, z0 + 0.1], [x, Y0 - 0.12, z1 + 0.3], 0.07, "v2_pipe", sides=10))
    return P


def arch_outline(cx, hw, zs, zc, pointed):
    pts = []
    if pointed:
        out = pointed_arch(cx, hw * 2, zs, zs, zc, steps=10)
        arc = [p for p in out if p[1] >= zs - 1e-6]
        arc = arc[2:]                    # from the right springing over to the left one
        return [(cx + hw, zs)] + arc + [(cx - hw, zs)]
    for k in range(0, 17):
        a = math.pi * k / 16
        pts.append((cx + hw * math.cos(a), zs + (zc - zs) * math.sin(a)))
    return pts


def arcade(X0, X1, Y0, z0, z1, bay, rng, pointed=False, depth=2.6, front=0.6, back_style="doors"):
    """A ground-floor arcade: piers and arch-cut spandrels at Y0, a tiled veranda and a back wall `depth` behind."""
    P = []
    W = X1 - X0
    nb = max(1, int(round(W / bay)))
    bay = W / nb
    hw = bay * 0.34
    spring = z0 + (z1 - z0) * 0.55
    crown = spring + hw * (1.25 if pointed else 1.0)
    crown = min(crown, z1 - 0.45)
    for k in range(nb):
        cx = X0 + (k + 0.5) * bay
        xl, xr = X0 + k * bay, X0 + (k + 1) * bay
        arc = arch_outline(cx, hw, spring, crown, pointed)
        poly = [(xl, spring), (cx - hw, spring)] + list(reversed(arc)) + [(cx + hw, spring), (xr, spring), (xr, z1), (xl, z1)]
        # dedupe consecutive points
        clean = []
        for p in poly:
            if not clean or abs(clean[-1][0] - p[0]) + abs(clean[-1][1] - p[1]) > 1e-4:
                clean.append(p)
        P.append(prism(clean, [Y0, Y0 + front], "v2_brick"))
        P.append(box(xl, cx - hw, Y0, Y0 + front, z0, spring, "v2_brick"))
        P.append(box(cx + hw, xr, Y0, Y0 + front, z0, spring, "v2_brick"))
        # back wall of the veranda: a door or a window in every other bay
        if back_style == "doors" and k % 2 == 0:
            P.append(box(cx - 0.75, cx + 0.75, Y0 + depth - 0.06, Y0 + depth, z0, z0 + 2.4, "v2_door"))
            P.append(box(cx - 0.9, cx + 0.9, Y0 + depth - 0.1, Y0 + depth - 0.06, z0 + 2.4, z0 + 2.55, "v2_concrete"))
        else:
            P.append(box(cx - 0.8, cx + 0.8, Y0 + depth - 0.05, Y0 + depth, z0 + 0.9, z0 + 2.3, "v2_glass"))
            P.append(box(cx - 0.03, cx + 0.03, Y0 + depth - 0.09, Y0 + depth - 0.05, z0 + 0.9, z0 + 2.3, "v2_frame"))
    P.append(box(X0, X1, Y0 + depth, Y0 + depth + 0.3, z0, z1, "v2_brick_reveal"))     # back wall
    P.append(box(X0, X1, Y0 - 0.3, Y0 + depth, z0 - 0.15, z0, "v2_floor_tile"))          # veranda floor
    P.append(box(X0, X1, Y0 - 0.06, Y0 + front, z1 - 0.25, z1, "v2_coping"))             # string course
    return P


def tower(cx, cy, r, h, rng):
    """Round brick stair tower: slit windows on the camera side, coping ring, roof cap."""
    P = [cyl([cx, cy, 0.0], [cx, cy, h], r, "v2_brick", sides=32),
         cyl([cx, cy, 0.0], [cx, cy, 0.45], r + 0.1, "v2_concrete", sides=32),
         cyl([cx, cy, h - 0.3], [cx, cy, h + 0.25], r + 0.14, "v2_coping", sides=32),
         cyl([cx, cy, h + 0.25], [cx, cy, h + 0.4], r - 0.2, "v2_roof", sides=24)]
    for a in (-55.0, -20.0, 20.0, 55.0):
        t = math.radians(a)
        x, y = cx + (r - 0.02) * math.sin(t), cy - (r - 0.02) * math.cos(t)
        P.append(box(x - 0.13, x + 0.13, y - 0.05, y + 0.05, 1.2, h - 1.0, "v2_glass", rot=[0, 0, a], pivot=[x, y, 0]))
        for z in range(3, int(h - 1), 3):
            P.append(box(x - 0.16, x + 0.16, y - 0.07, y + 0.03, z, z + 0.25, "v2_brick", rot=[0, 0, a], pivot=[x, y, 0]))
    return P


def roof(X0, X1, Y0, Y1, z, rng, kit=True, parapet_h=0.95, mat_wall="v2_brick"):
    """Flat roof: slab, parapet, coping, and the clutter of a real Dhaka roof (tanks, stair head, ACs, pipes)."""
    t = 0.3
    P = [box(X0, X1, Y0, Y1, z - 0.3, z + 0.04, "v2_roof"),
         box(X0, X1, Y0, Y0 + t, z, z + parapet_h, mat_wall), box(X0, X1, Y1 - t, Y1, z, z + parapet_h, mat_wall),
         box(X0, X0 + t, Y0, Y1, z, z + parapet_h, mat_wall), box(X1 - t, X1, Y0, Y1, z, z + parapet_h, mat_wall),
         box(X0 - 0.06, X1 + 0.06, Y0 - 0.06, Y0 + t + 0.06, z + parapet_h, z + parapet_h + 0.12, "v2_coping"),
         box(X0 - 0.06, X1 + 0.06, Y1 - t - 0.06, Y1 + 0.06, z + parapet_h, z + parapet_h + 0.12, "v2_coping"),
         box(X0 - 0.06, X0 + t + 0.06, Y0, Y1, z + parapet_h, z + parapet_h + 0.12, "v2_coping"),
         box(X1 - t - 0.06, X1 + 0.06, Y0, Y1, z + parapet_h, z + parapet_h + 0.12, "v2_coping")]
    W, D = X1 - X0, Y1 - Y0
    for k in range(1, int(W // 10.0) + 1):                  # expansion joints in big roofs
        x = X0 + k * W / (int(W // 10.0) + 1)
        P.append(box(x - 0.06, x + 0.06, Y0 + t, Y1 - t, z + 0.04, z + 0.09, "v2_roof_patch"))
    for k in range(int(W * D // 220)):                      # tar-patched repairs
        px_, py_ = X0 + 1 + rng.random() * max(0.1, W - 4), Y0 + 1 + rng.random() * max(0.1, D - 4)
        P.append(box(px_, px_ + rng.uniform(1.2, 3.5), py_, py_ + rng.uniform(0.8, 2.6), z + 0.04, z + 0.055, "v2_roof_patch"))
    for k in range(int(W // 8.0) + 1):                      # spouts through the south parapet, streaks below
        x = X0 + 2.0 + k * 8.0
        if x > X1 - 1.0:
            break
        P.append(box(x - 0.08, x + 0.08, Y0 - 0.35, Y0 + 0.3, z + 0.05, z + 0.2, "v2_pipe"))
    if not kit:
        return P
    if W < 6 or D < 5:
        return P
    # stair head: a small brick room with a door facing south
    sx = X0 + W * rng.uniform(0.15, 0.7)
    sy = Y0 + D * rng.uniform(0.35, 0.6)
    sw, sd = min(4.2, W * 0.3), min(4.0, D * 0.4)
    P += [box(sx, sx + sw, sy, sy + sd, z, z + 2.7, mat_wall),
          box(sx - 0.15, sx + sw + 0.15, sy - 0.15, sy + sd + 0.15, z + 2.7, z + 2.9, "v2_coping"),
          box(sx + sw * 0.3, sx + sw * 0.3 + 0.9, sy - 0.05, sy, z, z + 2.1, "v2_door_steel")]
    # water tanks on brick stands (the black tanks of every Bangladeshi roof)
    n = max(1, int(W * D / 160))
    for k in range(min(n, 6)):
        tx = X0 + 1.2 + rng.random() * max(0.1, W - 2.4)
        ty = Y0 + D * 0.55 + rng.random() * max(0.1, D * 0.4 - 1.2)
        rr = rng.choice([0.55, 0.65, 0.75])
        mat = "v2_tank" if rng.random() < 0.8 else "v2_tank_blue"
        P += [box(tx - rr - 0.1, tx + rr + 0.1, ty - rr - 0.1, ty + rr + 0.1, z, z + 0.55, "v2_brick_old"),
              cyl([tx, ty, z + 0.55], [tx, ty, z + 0.55 + rr * 2.1], rr, mat, sides=20),
              cyl([tx, ty, z + 0.55 + rr * 2.1], [tx, ty, z + 0.65 + rr * 2.1], rr * 0.35, mat, sides=12)]
    # AC condensers along the south parapet, with their pipes
    for k in range(int(W // 9)):
        ax = X0 + 1.5 + k * 9 + rng.random() * 3
        if ax > X1 - 2:
            break
        P += [box(ax, ax + 0.9, Y0 + 0.5, Y0 + 0.85, z, z + 0.65, "v2_ac"),
              box(ax + 0.05, ax + 0.85, Y0 + 0.47, Y0 + 0.5, z + 0.08, z + 0.6, "v2_ac_grille"),
              cyl([ax + 0.45, Y0 + 0.85, z + 0.3], [ax + 0.45, Y0 + 1.6, z + 0.3], 0.04, "v2_pipe_dark", sides=8)]
    # vent pipes
    for k in range(rng.randint(1, 3)):
        vx, vy = X0 + rng.random() * W, Y0 + D * (0.3 + 0.6 * rng.random())
        P.append(cyl([vx, vy, z], [vx, vy, z + 1.4], 0.06, "v2_pipe", sides=8))
    return P


def entrance(cx, Y0, depth, label=None, w=2.6, h=3.0, mat_frame="v2_concrete"):
    """Steps, a framed panelled double door at the back of the facade recess, a canopy on brackets, a name board."""
    P = []
    for k, (dy, dz) in enumerate(((1.4, 0.15), (1.0, 0.3), (0.6, 0.45))):
        P.append(box(cx - w / 2 - 0.9 + 0.2 * k, cx + w / 2 + 0.9 - 0.2 * k, Y0 - dy, Y0 + depth, 0.0, dz, "v2_concrete"))
    yb = Y0 + depth
    P += [box(cx - w / 2 - 0.35, cx - w / 2, Y0 - 0.1, yb, 0.45, h + 0.6, mat_frame),
          box(cx + w / 2, cx + w / 2 + 0.35, Y0 - 0.1, yb, 0.45, h + 0.6, mat_frame),
          box(cx - w / 2 - 0.35, cx + w / 2 + 0.35, Y0 - 0.1, yb, h + 0.45, h + 0.75, mat_frame),
          box(cx - w / 2, cx + w / 2, yb - 0.06, yb, 0.45, h + 0.45, "v2_void")]
    for side in (-1, 1):                                      # two door leaves, each with two raised panels
        xa = cx if side > 0 else cx - w / 2
        xb = cx + w / 2 if side > 0 else cx
        P.append(box(xa + 0.03, xb - 0.03, yb - 0.12, yb - 0.06, 0.45, h + 0.4, "v2_door"))
        for pz in ((0.65, 1.6), (1.85, h + 0.2)):
            P.append(box(xa + 0.15, xb - 0.15, yb - 0.15, yb - 0.12, pz[0], pz[1], "v2_door"))
        P.append(box(cx + side * 0.12 - 0.02, cx + side * 0.12 + 0.02, yb - 0.2, yb - 0.15, 1.5, 1.75, "v2_frame"))
    P += [box(cx - w / 2 - 1.0, cx + w / 2 + 1.0, Y0 - 1.6, Y0 + 0.2, h + 0.9, h + 1.12, "v2_concrete"),
          box(cx - w / 2 - 1.0, cx + w / 2 + 1.0, Y0 - 1.66, Y0 - 1.6, h + 0.85, h + 1.18, "v2_coping")]
    for side in (-1, 1):
        bx = cx + side * (w / 2 + 0.7)
        P.append(prism([(Y0 - 1.4, h + 0.9), (Y0, h + 0.9), (Y0, h - 0.1)], [bx - 0.08, bx + 0.08], "v2_concrete", axis="x"))
    if label:
        P += [box(cx - w / 2 - 0.8, cx + w / 2 + 0.8, Y0 - 1.72, Y0 - 1.66, h + 1.2, h + 1.75, "v2_sign_green"),
              text(label, [cx, Y0 - 1.74, h + 1.36], 0.32, "v2_sign_text")]
    P.append(cyl([cx, Y0 - 1.3, h + 0.84], [cx, Y0 - 1.3, h + 0.9], 0.18, "v2_lamp", sides=12))
    return P


def block(X0, X1, Y0, Y1, H, style, rng, storeys, *, bay=2.4, ground=None, arch_pointed=False, entrance_x=None,
          label=None, roof_style="flat", depth=0.5, kit=True):
    """A whole building part: core mass, the south facade (+ ground-floor arcade), roof and entrance."""
    P = []
    wall = "v2_plaster" if style == "plaster" else "v2_brick"
    gh = 0.0
    if ground == "arcade":
        gh = min(4.2, H / max(storeys, 1) + 0.6) if storeys > 1 else H - 0.8
        P += arcade(X0, X1, Y0, 0.0, gh, 3.6 if not arch_pointed else 4.2, rng, pointed=arch_pointed)
        P.append(box(X0, X1, Y0 + 2.9, Y1, 0.0, gh, wall))
    P.append(box(X0, X1, Y0 + depth, Y1, gh, H, wall))              # core behind the facade
    P.append(box(X0 - 0.12, X1 + 0.12, Y0 - 0.12, Y1 + 0.12, 0.0, 0.42, "v2_concrete"))   # plinth
    if H - gh > 1.5:
        st = max(1, storeys - (1 if ground == "arcade" else 0))
        P += facade(X0, X1, Y0, depth, gh, H, st, bay, style, rng, keep_clear=entrance_x)
    if roof_style == "flat":
        P += roof(X0, X1, Y0, Y1, H, rng, kit=kit, mat_wall=wall)
    elif roof_style == "red":
        P += pitched_roof(X0, X1, Y0, Y1, H, "v2_sheet_red")
    elif roof_style == "sawtooth":
        P += sawtooth(X0, X1, Y0, Y1, H, rng)
    elif roof_style == "slab":
        P += [box(X0 - 0.2, X1 + 0.2, Y0 - 0.2, Y1 + 0.2, H - 0.25, H + 0.05, "v2_roof"),
              box(X0 - 0.26, X1 + 0.26, Y0 - 0.26, Y0 - 0.2, H - 0.3, H + 0.08, "v2_coping")]
    if entrance_x is not None:
        P += entrance(entrance_x, Y0, depth, label)
    return P


def pitched_roof(X0, X1, Y0, Y1, z, mat):
    rise = min(3.2, (Y1 - Y0) * 0.28)
    ym = (Y0 + Y1) / 2
    P = [box(X0, X1, Y0, Y1, z - 0.3, z, "v2_roof"),
         prism([(Y0 - 0.5, z - 0.1), (ym, z + rise), (Y1 + 0.5, z - 0.1), (Y1 + 0.5, z + 0.05), (ym, z + rise + 0.15),
                (Y0 - 0.5, z + 0.05)], [X0 - 0.4, X1 + 0.4], mat, axis="x"),
         prism([(Y0, z), (ym, z + rise - 0.1), (Y1, z)], [X0 - 0.3, X0 - 0.2], "v2_brick", axis="x"),
         prism([(Y0, z), (ym, z + rise - 0.1), (Y1, z)], [X1 + 0.2, X1 + 0.3], "v2_brick", axis="x"),
         box(X0 - 0.4, X1 + 0.4, ym - 0.12, ym + 0.12, z + rise + 0.05, z + rise + 0.25, "v2_steel")]
    return P


def sawtooth(X0, X1, Y0, Y1, z, rng=None):
    """North-light roof. Corrugated sheets slope up to the north, each tooth a patchwork of newer, older and rusted
    sheets with a few translucent skylight sheets (laps alternate a hair proud, so every sheet edge catches light);
    the glazed vertical faces look north (away from the camera); steel ridge flashing, a gutter in every valley,
    turbine ventilators along the ridges; brick gable ends stepped to the saw profile with a coping."""
    rng = rng or random.Random(int(abs(X0 * 7 + Y0 * 13)) + 5)
    P = [box(X0, X1, Y0, Y1, z - 0.25, z, "v2_roof")]
    rise = 1.7
    n = max(1, round((Y1 - Y0) / 3.2))
    step = (Y1 - Y0) / n
    xa, xb = X0 + 0.25, X1 - 0.25
    for k in range(n):
        y = Y0 + k * step
        x, j = xa, 0
        while x < xb - 0.05:
            w = min(rng.choice([0.9, 1.8, 1.8, 2.7, 3.6, 3.6]), xb - x)
            if xb - (x + w) < 0.6:
                w = xb - x
            r = rng.random()
            mat = ("v2_sheet" if r < 0.5 else "v2_sheet_old" if r < 0.78 else "v2_sheet_rust" if r < 0.92
                   else "v2_skylight")
            dz = 0.018 * (j % 2)
            P.append(prism([(y, z + dz), (y + step, z + dz), (y + step, z + rise + dz)], [x, x + w], mat, axis="x"))
            x += w
            j += 1
        P.append(box(X0, X1, y + step - 0.06, y + step, z, z + rise - 0.15, "v2_glass_sky"))
        P.append(prism([(y + step - 0.16, z + rise - 0.08), (y + step + 0.06, z + rise - 0.2),
                        (y + step + 0.06, z + rise + 0.06), (y + step - 0.16, z + rise + 0.08)],
                       [X0, X1], "v2_steel", axis="x"))                         # ridge flashing, bent over
        if k > 0:
            P.append(box(X0, X1, y - 0.04, y + 0.24, z - 0.02, z + 0.12, "v2_pipe_dark"))   # valley gutter
        vx = X0 + 3.0 + rng.uniform(0.0, 2.0)
        while vx < X1 - 2.5:
            if rng.random() < 0.6:                                              # turbine ventilator on the slope top
                vy, vz = y + step - 0.55, z + rise * (step - 0.55) / step
                P.append(cyl([vx, vy, vz - 0.05], [vx, vy, vz + 0.22], 0.17, "v2_steel", sides=12))
                P.append(lathe([(0.2, vz + 0.22), (0.3, vz + 0.3), (0.31, vz + 0.52), (0.26, vz + 0.62),
                                (0.15, vz + 0.7), (0.0, vz + 0.73)], [vx, vy], "v2_turbine", sides=16))
            vx += rng.uniform(5.0, 8.0)
    for x in (X0, X1):                                                          # brick gable ends, stepped
        for k in range(n):
            y = Y0 + k * step
            P.append(prism([(y, z - 0.25), (y + step, z - 0.25), (y + step, z + rise + 0.18), (y, z + 0.18)],
                           [x - 0.22, x + 0.22], "v2_brick", axis="x"))
            P.append(prism([(y - 0.02, z + 0.16), (y + step + 0.02, z + rise + 0.16), (y + step + 0.02, z + rise + 0.26),
                            (y - 0.02, z + 0.26)], [x - 0.27, x + 0.27], "v2_coping", axis="x"))
    return P


# --- assets ----------------------------------------------------------------------------------------------------

class Site:
    def __init__(self, site):
        self.site = site
        polys = []
        for p in site.get("parts", []):
            if "rect" in p:
                x0, y0, x1, y1 = p["rect"]
                polys += [(x0, y0), (x1, y1)]
            elif "circle" in p:
                (cx, cy), r = p["circle"]["centre"], p["circle"]["r"]
                polys += [(cx - r, cy - r), (cx + r, cy + r)]
            elif "square" in p:
                (cx, cy), s = p["square"]["centre"], p["square"]["size"] * 0.75
                polys += [(cx - s, cy - s), (cx + s, cy + s)]
        if "monument" in site:
            cx, cy = site["monument"]["centre"]
            polys += [(cx - 8, cy - 8), (cx + 8, cy + 8)]
        xs = [p[0] for p in polys]
        ys = [p[1] for p in polys]
        self.cx, self.cy = round((min(xs) + max(xs)) / 2, 2), round((min(ys) + max(ys)) / 2, 2)

    def rect(self, r):
        x0, y0, x1, y1 = r
        return (x0 - self.cx, x1 - self.cx, self.cy - y1, self.cy - y0)   # X0, X1, Y0 (south), Y1

    def pt(self, x, y):
        return (x - self.cx, self.cy - y)


def add_asset(site, key, desc, groups, centre=None, fade=True):
    """groups: [(layer name, parts, (X0, X1, Y0, Y1), height)]. fade=False: no D31 fade (thin things the player is
    never lost behind; the occlusion ghosts show the player through them anyway)."""
    sid = site.site["id"]
    asset_id = f"v2_{sid}{('_' + key) if key else ''}"
    groups = merge_embedded(groups)
    scene = "V2" + "".join(w.capitalize() for w in (sid + ("_" + key if key else "")).split("_"))
    objects, layers = {}, []
    seen = set()
    for name, parts, (X0, X1, Y0, Y1), h in groups:
        name = "".join(c for c in name if c.isalnum())
        name = (name[:1].upper() + name[1:]) or "Part"
        while name in seen or name in ("Body", "Sprite"):
            name += "X"
        seen.add(name)
        objects[name] = {"parts": parts, "bevel": 0.012}
        layers.append({"name": name, "objects": [name], "sort_y_m": round(Y0, 3),
                       "fade": {"rects_m": {"Behind": [round(X0 - 0.5, 3), round(X1 + 0.5, 3), round(Y0 + 0.6, 3),
                                                       round(Y1 + 1.19 * h, 3)]}, "alpha": 0.3, "seconds": 0.35}
                       if fade else None})
    # A layer partly buried in one that sorts behind it (a stair tower half inside its wing) is cut by that layer,
    # so its buried faces vanish instead of rendering unlit and black over the wing; the wing behind stays whole,
    # which keeps the D31 fade honest (fading the tower shows the full wing).
    rects = [g[2] for g in groups]
    for i, li in enumerate(layers):
        ax0, ax1, ay0, ay1 = rects[i]
        li["holdouts"] = [lk["name"] for k, lk in enumerate(layers) if k != i and lk["sort_y_m"] > li["sort_y_m"] + 1e-6
                          and (min(ax1, rects[k][1]) - max(ax0, rects[k][0])) > 0.05
                          and (min(ay1, rects[k][3]) - max(ay0, rects[k][2])) > 0.05]
        # ...and a layer with others standing against its front (wings on a main block) renders twice, so what they
        # hide is lit brick when they fade over the player, not the black of a face no light reaches (layer_fill.py)
        li["covered_by"] = [lk["name"] for k, lk in enumerate(layers) if k != i and lk["sort_y_m"] < li["sort_y_m"] - 1e-6
                            and (min(ax1, rects[k][1]) - max(ax0, rects[k][0])) > -0.3
                            and (min(ay1, rects[k][3]) - max(ay0, rects[k][2])) > -0.3]
    # the base sprite (outside every layer, required by the pipeline): a small pad hidden under the first part
    X0, X1, Y0, Y1 = groups[0][2]
    mx, my = (X0 + X1) / 2, (Y0 + Y1) / 2
    objects["Base"] = {"parts": [box(mx - 0.3, mx + 0.3, my - 0.3, my + 0.3, 0.0, 0.01, "v2_concrete")], "bevel": 0.0}
    ASSETS.append({"asset_id": asset_id, "scene": scene, "desc": desc, "site": sid,
                   "centre_m": [site.cx, site.cy] if centre is None else centre, "objects": objects, "layers": layers})


def merge_embedded(groups):
    """A part standing mostly inside another (the Cafeteria's stair tower and annex, the Main Gate's pylons under its
    beam, the minaret and mihrab against the Mosque) joins that part's layer. Separate sprites can't show one volume
    rising out of another, and rendering them apart leaves the buried faces black (D46)."""
    groups = [list(g) for g in groups]
    changed = True
    while changed:
        changed = False
        for i in range(len(groups)):
            for j in range(len(groups)):
                if i == j:
                    continue
                (ax0, ax1, ay0, ay1), (bx0, bx1, by0, by1) = groups[i][2], groups[j][2]
                area_b = max(1e-6, (bx1 - bx0) * (by1 - by0))
                ox = max(0.0, min(ax1, bx1) - max(ax0, bx0))
                oy = max(0.0, min(ay1, by1) - max(ay0, by0))
                if ox * oy / area_b >= 0.6 and (ax1 - ax0) * (ay1 - ay0) >= area_b:
                    groups[i][1] = groups[i][1] + groups[j][1]
                    groups[i][2] = (min(ax0, bx0), max(ax1, bx1), min(ay0, by0), max(ay1, by1))
                    groups[i][3] = max(groups[i][3], groups[j][3])
                    del groups[j]
                    changed = True
                    break
            if changed:
                break
    return [tuple(g) for g in groups]


def part_rects(site, roles=None):
    out = []
    for i, p in enumerate(site.site.get("parts", [])):
        if roles and p.get("role") not in roles:
            continue
        out.append((i, p))
    return out


def entrance_x_for(site, X0, X1, Y0):
    for e in site.site.get("entrances", []):
        ex, ey = site.pt(*e["at"])
        if X0 - 0.5 <= ex <= X1 + 0.5 and abs(ey - Y0) < 2.5 and e.get("face", "south") == "south":
            return ex, e.get("place")
    return None, None


def generic_site(site, style, storeys, *, bay=2.4, ground=None, pointed=False, roof_style="flat", towers=True,
                 desc="", key_prefix=""):
    """One asset per site: every rect part a facade block, every circle a stair tower."""
    rng = rng_for(site.site["id"])
    groups = []
    parts_all = site.site.get("parts", [])
    # a stair tower is a capsule in the layout (a rect neck + a circle): build it as one round tower
    necks = [p for p in parts_all if "rect" in p and "stair tower" in p.get("role", "")]
    for i, p in enumerate(parts_all):
        h = p.get("h", 6.0)
        role = p.get("role", "") or f"part{i}"
        name = f"P{i}_" + "".join(c for c in role.title() if c.isalnum())[:18]
        if "rect" in p and "stair tower" in role:
            continue
        if "rect" in p:
            X0, X1, Y0, Y1 = site.rect(p["rect"])
            ex, label = entrance_x_for(site, X0, X1, Y0)
            if "canopy" in role:
                parts = shed(X0, X1, Y0, Y1, h, rng, cars=False)
            elif "bridge" in role:
                parts = [box(X0, X1, Y0 + 0.2, Y1 - 0.2, h - 1.2, h, "v2_concrete"),
                         box(X0, X1, Y0 + 0.1, Y0 + 0.3, h, h + 1.0, "v2_brick"),
                         box(X0, X1, Y0 + 0.32, Y0 + 0.36, h - 1.0, h - 0.3, "v2_glass")]
            else:
                st = max(1, int(round(h / 3.4))) if storeys is None else storeys
                if h < 4.5:
                    st = 1
                parts = block(X0, X1, Y0, Y1, h, style, rng, st, bay=bay,
                              ground=ground if h > 6 else None, arch_pointed=pointed, entrance_x=ex,
                              label=(label or site.site["name"]).upper() if ex is not None else None,
                              roof_style=roof_style if h > 4.5 else "slab")
            groups.append((name, parts, (X0, X1, Y0, Y1), h))
        elif "circle" in p and towers:
            (cx, cy), r = p["circle"]["centre"], p["circle"]["r"]
            X, Y = site.pt(cx, cy)
            parts = tower(X, Y, r, h, rng)
            bx = (X - r, X + r, Y - r, Y + r)
            for nk in necks:
                x0, y0, x1, y1 = nk["rect"]
                if x0 - 0.1 <= cx <= x1 + 0.1 and abs(y1 - cy) < 0.2:
                    NX0, NX1, NY0, NY1 = site.rect(nk["rect"])
                    parts = [box(NX0, NX1, NY0, NY1, 0.0, h, "v2_brick"),
                             box(NX0 - 0.1, NX1 + 0.1, NY0, NY1, h - 0.3, h + 0.25, "v2_coping")] + parts
                    bx = (min(bx[0], NX0), max(bx[1], NX1), bx[2], max(bx[3], NY1))
            groups.append((name, parts, bx, h))
    add_asset(site, key_prefix, desc or site.site["name"], groups)


def shed(X0, X1, Y0, Y1, h, rng, cars=True):
    """Steel parking shed: columns, beams, a sloped maroon sheet roof; parked cars below."""
    P = []
    n = max(2, int((X1 - X0) // 5) + 1)
    for k in range(n):
        x = X0 + 0.3 + k * (X1 - X0 - 0.6) / (n - 1)
        for y in (Y0 + 0.3, Y1 - 0.3):
            P.append(box(x - 0.1, x + 0.1, y - 0.1, y + 0.1, 0.0, h - (0.25 if y < Y1 - 1 else 0.0), "v2_steel"))
    P.append(box(X0, X1, Y0 + 0.2, Y0 + 0.4, h - 0.45, h - 0.25, "v2_steel"))
    P.append(box(X0, X1, Y1 - 0.4, Y1 - 0.2, h - 0.2, h, "v2_steel"))
    P.append(prism([(Y0 - 0.4, h - 0.3), (Y1 + 0.3, h + 0.05), (Y1 + 0.3, h + 0.12), (Y0 - 0.4, h - 0.23)],
                   [X0 - 0.3, X1 + 0.3], "v2_sheet_red", axis="x"))
    P.append(box(X0, X1, Y0 - 0.1, Y1 + 0.1, 0.0, 0.08, "v2_concrete"))
    slope = (0.35 + 0.05) / (Y1 - Y0 + 0.7)
    for k in range(int((X1 - X0) // 2.5) + 1):                 # purlin lines and rust where the sheets overlap
        x = X0 + k * 2.5
        zz = h - 0.3
        P.append(prism([(Y0 - 0.4, zz + 0.075), (Y1 + 0.3, h + 0.125), (Y1 + 0.3, h + 0.15), (Y0 - 0.4, zz + 0.1)],
                       [x - 0.04, x + 0.04], "v2_steel", axis="x"))
        if rng.random() < 0.45:
            ry = Y0 + rng.random() * (Y1 - Y0 - 1.5)
            P.append(prism([(ry, zz + 0.075 + (ry - Y0 + 0.4) * slope * 0.9), (ry + 1.4, zz + 0.075 + (ry + 1.8 - Y0) * slope * 0.9),
                            (ry + 1.4, zz + 0.09 + (ry + 1.8 - Y0) * slope * 0.9), (ry, zz + 0.09 + (ry - Y0 + 0.4) * slope * 0.9)],
                           [x + 0.3, x + 0.3 + rng.uniform(0.6, 1.8)], "v2_rust", axis="x"))
    if cars:
        k = 0
        x = X0 + 1.0
        while x + 2.0 < X1:
            if rng.random() < 0.7:
                P += car(x + 1.0, (Y0 + Y1) / 2, rng, k)
            x += 2.7
            k += 1
    return P


def car(cx, cy, rng, k):
    """A small parked sedan facing north: body and cabin as profiles, wheels, glazing, lights."""
    mat = rng.choice(["v2_car_white", "v2_car_silver", "v2_car_red", "v2_car_black", "v2_car_white"])
    L, Wd = 4.3, 1.75
    y0 = cy - L / 2
    body = [(y0, 0.32), (y0 + L, 0.32), (y0 + L, 0.75), (y0 + L - 0.25, 0.86), (y0 + 0.2, 0.86), (y0, 0.72)]
    cab = [(y0 + 1.05, 0.86), (y0 + L - 1.1, 0.86), (y0 + L - 1.55, 1.4), (y0 + 1.5, 1.4)]
    P = [prism(body, [cx - Wd / 2, cx + Wd / 2], mat, axis="x"),
         prism(cab, [cx - Wd / 2 + 0.12, cx + Wd / 2 - 0.12], mat, axis="x"),
         prism([(y0 + 1.12, 0.9), (y0 + 1.5, 1.36), (y0 + L - 1.58, 1.36), (y0 + L - 1.18, 0.9)],
               [cx - Wd / 2 + 0.1, cx + Wd / 2 - 0.1], "v2_glass", axis="x")]
    for wy in (y0 + 0.8, y0 + L - 0.8):
        for sx in (-1, 1):
            P.append(cyl([cx + sx * (Wd / 2 - 0.12), wy, 0.32], [cx + sx * (Wd / 2 + 0.02), wy, 0.32], 0.32, "v2_tyre", sides=16))
    P += [box(cx - 0.75, cx - 0.45, y0 - 0.02, y0 + 0.02, 0.55, 0.68, "v2_taillight"),   # the camera sees the rear
          box(cx + 0.45, cx + 0.75, y0 - 0.02, y0 + 0.02, 0.55, 0.68, "v2_taillight"),
          box(cx - 0.5, cx + 0.5, y0 - 0.03, y0 + 0.01, 0.4, 0.52, "v2_steel")]
    return P


# --- the special buildings -------------------------------------------------------------------------------------

def mosque(site):
    s = site.site
    rng = rng_for(s["id"])
    sq = s["parts"][0]["square"]
    C = site.pt(*sq["centre"])
    a = sq["size"] / 2
    H = s["parts"][0]["h"]
    # body built square, then turned to the qibla (layout turns clockwise on screen; Blender's Y is up)
    body = [box(-a, a, -a, a, 0.0, H, "v2_brick"),
            box(-a - 0.4, a + 0.4, -a - 0.4, a + 0.4, 0.0, 0.5, "v2_concrete")]
    body += roof(-a, a, -a, a, H, rng, kit=False, parapet_h=1.1)
    body += [cyl([0, 0, H], [0, 0, H + 1.6], 6.2, "v2_brick", sides=48),
             {"lathe": [[0.0, H + 1.6 + 2.6], [2.4, H + 1.6 + 2.4], [4.3, H + 1.6 + 1.8], [5.6, H + 1.6 + 0.9],
                        [6.3, H + 1.6]], "at": [0.0, 0.0], "mat": "v2_dome", "sides": 48},
             cyl([0, 0, H + 1.6 + 2.5], [0, 0, H + 1.6 + 3.8], 0.08, "v2_frame", sides=8)]
    # the great half-disc RECESS with stepped glazing on the south face (and on the entrance face, east): the outer
    # 0.9 m of wall is built as two concave prisms that leave the half-disc open; the glazing steps inside it
    R, zt, dep = 8.4, H - 2.2, 0.9

    def recess_face():
        arc_l = [(-R * math.sin(math.pi / 2 * k / 12), zt - R * math.cos(math.pi / 2 * k / 12)) for k in range(13)]
        left = [(-a, 0.0), (0.0, 0.0)] + arc_l + [(0.0, zt), (0.0, H), (-a, H)]
        right = [(-x, z) for x, z in left]
        part = [prism(left, [-a, -a + dep], "v2_brick"), prism(list(reversed(right)), [-a, -a + dep], "v2_brick"),
                box(-R, R, -a + dep, -a + dep + 0.05, zt - R, zt, "v2_brick_reveal")]
        for hw, z0 in ((6.2, zt - 4.2), (4.6, zt - 5.8), (3.0, zt - 7.2), (1.4, zt - 8.2)):
            part.append(box(-hw, hw, -a + dep - 0.04, -a + dep, z0, zt - 0.1, "v2_glass"))
        for x in (-6.2, -4.6, -3.0, -1.4, 0.0, 1.4, 3.0, 4.6, 6.2):
            part.append(box(x - 0.06, x + 0.06, -a + dep - 0.1, -a + dep - 0.04, zt - 8.2, zt - 0.1, "v2_frame"))
        for z in (zt - 7.2, zt - 5.8, zt - 4.2, zt - 2.4):
            part.append(box(-6.2, 6.2, -a + dep - 0.1, -a + dep - 0.04, z - 0.05, z + 0.05, "v2_frame"))
        part.append(box(-R - 0.1, R + 0.1, -a - 0.12, -a + dep, zt, zt + 0.25, "v2_coping"))
        part += [box(-0.75, 0.75, -a - 0.03, -a + 0.5, 0.5, 3.4, "v2_void"),
                 prism(pointed_arch(0.0, 1.5, 3.3, 3.3, 4.3), [-a - 0.04, -a + 0.5], "v2_void"),
                 box(-1.6, 1.6, -a - 1.5, -a, 0.0, 0.5, "v2_concrete")]
        return part
    body = [q for q in body if not (q.get("box") and q["box"][2] == -a and q["box"][5] == H and q["mat"] == "v2_brick")]
    body.insert(0, box(-a + dep, a, -a + dep, a - dep, 0.0, H, "v2_brick"))
    body += recess_face()
    body += rotated_z(recess_face(), 90.0)
    body += [box(-a, a, a - dep, a, 0.0, H, "v2_brick"), box(-a, -a + dep, -a + dep, a - dep, 0.0, H, "v2_brick")]
    body = rotated_z(body, -sq.get("rot_deg", 0.0))
    body = [dict(q, xf=q.get("xf", []) + [{"move": [round(C[0], 3), round(C[1], 3), 0]}]) for q in body]
    groups = [("Mosque", body, (C[0] - a * 1.15, C[0] + a * 1.15, C[1] - a * 1.15, C[1] + a * 1.15), H + 6.0)]
    for i, p in enumerate(s["parts"][1:], start=1):
        role = p.get("role", "")
        if "minaret" in role:
            X0, X1, Y0, Y1 = site.rect(p["rect"])
            mx, my = (X0 + X1) / 2, (Y0 + Y1) / 2
            m = [cyl([mx, my, 0], [mx, my, p["h"] - 4.5], 1.7, "v2_brick", sides=32),
                 cyl([mx, my, 0], [mx, my, 0.5], 2.0, "v2_concrete", sides=32)]
            c = 2.0
            m += [box(mx - c, mx + c, my - c, my + c, p["h"] - 4.5, p["h"] - 4.0, "v2_brick"),
                  box(mx - c, mx + c, my - c, my + c, p["h"] - 0.6, p["h"], "v2_brick"),
                  box(mx - c - 0.1, mx + c + 0.1, my - c - 0.1, my + c + 0.1, p["h"], p["h"] + 0.15, "v2_coping")]
            for sx in (-1, 1):
                for sy in (-1, 1):
                    m.append(box(mx + sx * c - (0.5 if sx > 0 else 0), mx + sx * c + (0.5 if sx < 0 else 0),
                                 my + sy * c - (0.5 if sy > 0 else 0), my + sy * c + (0.5 if sy < 0 else 0),
                                 p["h"] - 4.0, p["h"] - 0.6, "v2_brick"))
            m.append(prism(half_disc(mx, p["h"] - 0.6, 1.3), [my - c - 0.02, my - c + 0.1], "v2_brick_reveal"))
            m.append(cyl([mx, my, p["h"] - 3.6], [mx, my, p["h"] - 2.6], 0.5, "v2_lamp", sides=12))
            groups.append(("Minaret", m, (mx - c, mx + c, my - c, my + c), p["h"]))
        elif "circle" in p:
            (cx, cy), r = p["circle"]["centre"], p["circle"]["r"]
            X, Y = site.pt(cx, cy)
            if "mihrab" in role:
                parts = [cyl([X, Y, 0], [X, Y, p["h"]], r, "v2_brick", sides=32),
                         cyl([X, Y, p["h"]], [X, Y, p["h"] + 0.2], r + 0.1, "v2_coping", sides=32)]
            else:          # the three cylinders standing in the water below the half-disc
                parts = [cyl([X, Y, -0.6], [X, Y, p["h"]], r, "v2_brick", sides=32),
                         cyl([X, Y, p["h"]], [X, Y, p["h"] + 0.22], r + 0.12, "v2_coping", sides=32),
                         cyl([X, Y, p["h"] + 0.22], [X, Y, p["h"] + 0.3], r - 0.3, "v2_roof", sides=24)]
            groups.append((f"P{i}_" + "".join(c for c in role.title() if c.isalnum()), parts, (X - r, X + r, Y - r, Y + r), p["h"]))
    add_asset(site, "", "IUT Mosque, turned to the qibla in the lake: brick cube, great half-disc windows with stepped "
                        "glazing, low dome, minaret with its cage top, mihrab, the three cylinders at the water.", groups)


def auditorium(site):
    s = site.site
    rng = rng_for(s["id"])
    X0, X1, Y0, Y1 = site.rect(s["parts"][0]["rect"])
    H = s["parts"][0]["h"]
    P = [box(X0, X1, Y0 + 3.2, Y1, 0.0, H, "v2_brick"),
         box(X0 - 0.2, X1 + 0.2, Y0 - 0.2, Y1 + 0.2, -0.8, 0.4, "v2_concrete")]
    # the lake loggia: five great pointed arches, a deep shadowed gallery behind
    P += arcade(X0, X1, Y0, 0.4, 9.6, (X1 - X0) / 5, rng, pointed=True, depth=3.2, front=0.9, back_style="windows")
    P += [box(X0, X1, Y0, Y0 + 3.2, 9.6, H, "v2_brick")]
    for k in range(12):                     # a band of tall slits over the loggia
        x = X0 + 1.8 + k * (X1 - X0 - 3.6) / 11
        P += [box(x - 0.2, x + 0.2, Y0 - 0.02, Y0 + 0.4, 10.4, H - 1.2, "v2_void"),
              box(x - 0.24, x + 0.24, Y0 - 0.08, Y0, 10.3, 10.4, "v2_coping")]
    P += roof(X0, X1, Y0, Y1, H, rng, kit=False, parapet_h=1.2)
    for k in range(3):                      # roof lanterns over the hall
        cx = X0 + (X1 - X0) * (0.3 + 0.2 * k)
        P += [box(cx - 2.5, cx + 2.5, Y0 + 9, Y0 + 20, H, H + 1.4, "v2_brick"),
              box(cx - 2.5, cx + 2.5, Y0 + 8.95, Y0 + 9.0, H + 0.3, H + 1.2, "v2_glass_sky"),
              box(cx - 2.7, cx + 2.7, Y0 + 8.8, Y0 + 20.2, H + 1.4, H + 1.6, "v2_roof")]
    fx0, fx1, fy0 = X0 + 8.0, X1 - 8.0, Y1 - 13.0   # the stage's fly tower
    P += [box(fx0, fx1, fy0, Y1 - 1.0, H, H + 7.0, "v2_brick")]
    P += facade(fx0, fx1, fy0, 0.4, H + 1.0, H + 7.0, 1, 3.0, "slits", rng)
    P += roof(fx0, fx1, fy0, Y1 - 1.0, H + 7.0, rng, kit=False, parapet_h=0.7)
    add_asset(site, "", "Auditorium: brick mass on the lake, a loggia of five great pointed arches.",
              [("Auditorium", P, (X0, X1, Y0, Y1), H)])


def cafeteria(site):
    s = site.site
    rng = rng_for(s["id"])
    groups = []
    for i, p in enumerate(s["parts"]):
        X0, X1, Y0, Y1 = site.rect(p["rect"])
        H = p["h"]
        role = p.get("role", "")
        if not role:
            P = [box(X0, X1, Y0 + 3.0, Y1, 0.0, 6.0, "v2_brick")]
            P += arcade(X0, X1, Y0, 0.0, 6.0, (X1 - X0) / 6, rng, pointed=False, depth=3.0, front=0.8)
            P.append(box(X0, X1, Y0 + 0.5, Y1, 6.0, H, "v2_brick"))
            P += facade(X0, X1, Y0, 0.5, 6.0, H, 2, 1.6, "slits", rng)
            P += roof(X0, X1, Y0, Y1, H, rng)
            ex, label = entrance_x_for(site, X0, X1, Y0)
            if ex is not None:
                P += entrance(ex, Y0 - 0.0, 0.5, "CAFETERIA")
            name = "Cafeteria"
        else:
            P = block(X0, X1, Y0, Y1, H, "slits" if "tower" in role else "hall", rng, max(1, int(H // 3.5)), bay=1.6)
            name = f"P{i}_" + "".join(c for c in role.title() if c.isalnum())
        groups.append((name, P, (X0, X1, Y0, Y1), H))
    add_asset(site, "", "Cafeteria / Library: a ground-floor arcade of round arches over the east lake, slit windows above.", groups)


def five_fundamentals(site):
    m = site.site["monument"]
    C = site.pt(*m["centre"])
    P = []
    n, L, T, sp, gap, h = m["walls"], m["wall_len"], m["wall_thick"], m["spacing"], m.get("passage", 2.2), m["h"]
    for i in range(n):
        o = (i - (n - 1) / 2.0) * sp
        heights = h - abs(i - (n - 1) / 2.0) * 0.6          # stepped: the middle fin stands tallest
        y0, y1 = o - T / 2, o + T / 2
        r, zs = gap / 2, 2.5                                 # round-arched passage, springing at 2.5 m
        arch = [(-r, heights), (-r, zs)] + [(r * math.cos(math.pi * (1 - k / 12)), zs + r * math.sin(math.pi * (1 - k / 12)))
                                             for k in range(1, 12)] + [(r, zs), (r, heights)]
        wall = [box(-L / 2 - 0.12, L / 2 + 0.12, y0 - 0.12, y1 + 0.12, 0.0, 0.45, "v2_concrete"),   # plinth
                box(-L / 2, -r, y0, y1, 0.45, heights, "v2_brick"),
                box(r, L / 2, y0, y1, 0.45, heights, "v2_brick"),
                prism(arch, [y0, y1], "v2_brick", axis="y"),
                prism([(-r - 0.22, zs - 0.05)] + [((r + 0.22) * math.cos(math.pi * (1 - k / 12)),
                                                   zs + (r + 0.22) * math.sin(math.pi * (1 - k / 12))) for k in range(1, 12)]
                      + [(r + 0.22, zs - 0.05), (r, zs)] + [(r * math.cos(math.pi * k / 12), zs + r * math.sin(math.pi * k / 12))
                                                          for k in range(1, 12)] + [(-r, zs)],
                      [y0 - 0.05, y1 + 0.05], "v2_brick_reveal", axis="y"),                      # brick voussoir ring
                box(-L / 2 - 0.05, L / 2 + 0.05, y0 - 0.05, y1 + 0.05, heights, heights + 0.12, "v2_coping"),
                box(-L / 2 - 0.12, L / 2 + 0.12, y0 - 0.12, y1 + 0.12, heights + 0.12, heights + 0.24, "v2_coping")]
        for zc in (1.6, heights - 2.2):                      # projecting string courses
            wall += [box(-L / 2 - 0.04, -r - 0.25, y0 - 0.04, y1 + 0.04, zc, zc + 0.1, "v2_coping"),
                     box(r + 0.25, L / 2 + 0.04, y0 - 0.04, y1 + 0.04, zc, zc + 0.1, "v2_coping")]
        for sx in (-1, 1):                                   # recessed panels either side of the passage, both faces
            xa, xb = sorted((sx * (r + 0.7), sx * (L / 2 - 0.6)))
            for yy in (y0 - 0.001, y1 - 0.06):
                wall.append(box(xa, xb, yy, yy + 0.061, 2.0, heights - 2.6, "v2_brick_reveal"))
        P += wall
    P.append(box(-L / 2 - 0.5, L / 2 + 0.5, -(n * sp) / 2 - 0.5, (n * sp) / 2 + 0.5, -0.3, 0.05, "v2_floor_tile"))
    # the fins stand across the causeway: walls run along local x, the causeway along local y; turn to the axis
    deg = 90.0 - m["axis_deg"]             # layout axis (clockwise from east, y down) -> Blender
    P = rotated_z(P, -deg + 90.0)
    P = [dict(q, xf=q.get("xf", []) + [{"move": [round(C[0], 3), round(C[1], 3), 0]}]) for q in P]
    add_asset(site, "", "Five Fundamentals: five stepped brick fins across the diagonal causeway, each on a concrete "
                        "plinth, pierced by a round-arched passage with a brick voussoir ring, string courses and "
                        "recessed panels.", [("Fins", P, (C[0] - 7, C[0] + 7, C[1] - 7, C[1] + 7), h)], fade=False)


def workshops(site):
    rng = rng_for(site.site["id"])
    groups = []
    for i, p in enumerate(site.site["parts"]):
        X0, X1, Y0, Y1 = site.rect(p["rect"])
        H = p["h"]
        if "link" in p.get("role", ""):
            P = block(X0, X1, Y0, Y1, H, "blank", rng, 1, bay=2.0, roof_style="flat", kit=False)
            P += [box(X0 + 1.0, X1 - 1.0, Y0 - 0.06, Y0 + 0.3, 0.0, 4.4, "v2_door_steel")]
            for k in range(8):
                z = 0.4 + k * 0.5
                P.append(box(X0 + 1.0, X1 - 1.0, Y0 - 0.1, Y0 - 0.06, z, z + 0.05, "v2_steel"))
        else:
            P = block(X0, X1, Y0, Y1, H, "workshop", rng, 1, bay=6.0, roof_style="sawtooth")
            ex, _ = entrance_x_for(site, X0, X1, Y0)
            for dx in ((X0 + X1) / 2 - 8, (X0 + X1) / 2 + 8):           # big steel sliding doors with tracks
                P += [box(dx - 2.2, dx + 2.2, Y0 - 0.1, Y0 + 0.02, 0.0, 4.6, "v2_door_steel"),
                      box(dx - 4.6, dx + 4.6, Y0 - 0.22, Y0 - 0.1, 4.6, 4.8, "v2_steel")]
                for k in range(9):
                    P.append(box(dx - 2.2, dx + 2.2, Y0 - 0.14, Y0 - 0.1, 0.3 + k * 0.5, 0.34 + k * 0.5, "v2_steel"))
        groups.append((f"P{i}", P, (X0, X1, Y0, Y1), H + 1.8))
    add_asset(site, "", site.site["name"] + ": brick hall, clerestory band, sliding steel doors, sawtooth north-light roof.", groups)


def parking(site):
    rng = rng_for(site.site["id"])
    groups = []
    for i, p in enumerate(site.site["parts"]):
        X0, X1, Y0, Y1 = site.rect(p["rect"])
        groups.append((f"Shed{i}", shed(X0, X1, Y0, Y1, p["h"], rng), (X0, X1, Y0, Y1), p["h"]))
    add_asset(site, "", "Car parking: steel sheds with maroon sheet roofs, cars parked beneath.", groups)


def substation(site):
    rng = rng_for(site.site["id"])
    groups = []
    for i, p in enumerate(site.site["parts"]):
        X0, X1, Y0, Y1 = site.rect(p["rect"])
        H = p["h"]
        if "yard" in p.get("role", ""):
            P = [box(X0, X1, Y0, Y1, 0.0, 0.1, "v2_concrete")]
            for k in range(2):                                   # transformers: tank, cooling fins, bushings
                tx = X0 + 2.5 + k * 4.5
                ty = (Y0 + Y1) / 2
                P += [box(tx - 1.0, tx + 1.0, ty - 0.8, ty + 0.8, 0.3, 2.2, "v2_transformer"),
                      box(tx - 1.2, tx + 1.2, ty - 1.0, ty + 1.0, 0.1, 0.3, "v2_concrete"),
                      cyl([tx - 0.9, ty + 0.9, 2.5], [tx + 0.9, ty + 0.9, 2.5], 0.3, "v2_transformer", sides=16)]
                for f in range(7):
                    fx = tx - 0.9 + f * 0.3
                    P.append(box(fx - 0.03, fx + 0.03, ty - 1.15, ty - 0.8, 0.5, 2.0, "v2_transformer"))
                for b in range(3):
                    bx = tx - 0.6 + b * 0.6
                    P += [cyl([bx, ty, 2.2], [bx, ty, 3.0], 0.09, "v2_insulator", sides=10),
                          cyl([bx, ty, 2.45], [bx, ty, 2.5], 0.16, "v2_insulator", sides=10),
                          cyl([bx, ty, 2.7], [bx, ty, 2.75], 0.16, "v2_insulator", sides=10)]
            for (xa, ya, xb, yb) in ((X0, Y0, X1, Y0), (X0, Y1, X1, Y1), (X0, Y0, X0, Y1), (X1, Y0, X1, Y1)):
                P.append(box(min(xa, xb) - 0.02, max(xa, xb) + 0.02, min(ya, yb) - 0.02, max(ya, yb) + 0.02, 0.0, 2.2, "v2_fence"))
                L = max(abs(xb - xa), abs(yb - ya))
                for k in range(int(L // 2.5) + 1):
                    t = k / max(1, int(L // 2.5))
                    P.append(cyl([xa + (xb - xa) * t, ya + (yb - ya) * t, 0], [xa + (xb - xa) * t, ya + (yb - ya) * t, 2.4],
                                 0.05, "v2_steel", sides=8))
        else:
            P = block(X0, X1, Y0, Y1, H, "blank", rng, 1, bay=3.0, roof_style="slab")
            for k in range(int((X1 - X0) // 3)):                 # louvres and steel doors
                x = X0 + 1.5 + k * 3
                P += [box(x - 0.6, x + 0.6, Y0 - 0.05, Y0 + 0.02, 2.6, 3.6, "v2_ac_grille"),
                      box(x - 0.55, x + 0.55, Y0 - 0.05, Y0 + 0.02, 0.0, 2.2, "v2_door_steel")]
        groups.append((f"P{i}", P, (X0, X1, Y0, Y1), H))
    add_asset(site, "", "Electrical Substation: concrete switch rooms with louvres, transformers in a fenced gravel yard.", groups)


def construction(site):
    """#25: a ten-storey concrete frame, brick infill rising floor by floor, bamboo scaffolding, nets, a tower crane."""
    rng = rng_for(site.site["id"])
    groups = []
    for i, p in enumerate(site.site["parts"]):
        X0, X1, Y0, Y1 = site.rect(p["rect"])
        H = p["h"]
        storeys = 10
        sh = H / storeys
        P = []
        for s in range(storeys + 1):
            z = s * sh
            P.append(box(X0, X1, Y0, Y1, z - 0.22, z, "v2_concrete"))
        nx = max(2, int((X1 - X0) // 4.5) + 1)
        ny = max(2, int((Y1 - Y0) // 4.5) + 1)
        for a in range(nx):
            for b in range(ny):
                x = X0 + 0.25 + a * (X1 - X0 - 0.5) / (nx - 1)
                y = Y0 + 0.25 + b * (Y1 - Y0 - 0.5) / (ny - 1)
                P.append(box(x - 0.25, x + 0.25, y - 0.25, y + 0.25, 0.0, H, "v2_concrete"))
        infill = rng.randint(5, 8)
        for s in range(infill):
            z = s * sh
            P += [box(X0 + 0.3, X1 - 0.3, Y0 + 0.05, Y0 + 0.3, z, z + sh - 0.22, "v2_brick_old"),
                  box(X0 + 0.3, X1 - 0.3, Y1 - 0.3, Y1 - 0.05, z, z + sh - 0.22, "v2_brick_old")]
            for a in range(nx - 1):
                x = X0 + 0.25 + (a + 0.5) * (X1 - X0 - 0.5) / (nx - 1)
                P.append(box(x - 0.6, x + 0.6, Y0 - 0.02, Y0 + 0.32, z + 0.9, z + 2.2, "v2_void"))
        # bamboo scaffolding on the south face, green safety netting over part of it
        sy = Y0 - 1.0
        for a in range(int((X1 - X0) // 1.8) + 1):
            x = X0 + a * 1.8
            P.append(cyl([x, sy, 0], [x, sy + rng.uniform(-0.05, 0.05), H + 1.5], 0.05, "v2_bamboo", sides=6))
        for s in range(int(H // 1.7) + 1):
            z = s * 1.7
            P.append(cyl([X0, sy - 0.05, z], [X1, sy - 0.05, z + rng.uniform(-0.1, 0.1)], 0.04, "v2_bamboo", sides=6))
        nx0 = X0 + (X1 - X0) * rng.uniform(0.1, 0.4)
        P.append(box(nx0, nx0 + (X1 - X0) * 0.45, sy - 0.12, sy - 0.1, sh * infill, H, "v2_net"))
        if i == 0:                                                     # the tower crane
            cx, cy = (X0 + X1) / 2, Y1 + 4.0
            mast = H + 12
            for k in range(int(mast // 1.5)):
                z = k * 1.5
                P += [box(cx - 0.8, cx + 0.8, cy - 0.8, cy + 0.8, z, z + 0.12, "v2_crane")]
            for sx in (-1, 1):
                for sy2 in (-1, 1):
                    P.append(box(cx + sx * 0.75 - 0.07, cx + sx * 0.75 + 0.07, cy + sy2 * 0.75 - 0.07, cy + sy2 * 0.75 + 0.07,
                                 0, mast, "v2_crane"))
            P += [box(cx - 26, cx + 9, cy - 0.5, cy + 0.5, mast, mast + 1.2, "v2_crane"),
                  box(cx + 5, cx + 9, cy - 1.2, cy + 1.2, mast - 1.8, mast, "v2_concrete"),
                  box(cx - 1.2, cx + 1.2, cy - 1.0, cy + 1.0, mast - 2.6, mast, "v2_crane"),
                  box(cx - 0.9, cx + 0.9, cy - 1.02, cy - 0.98, mast - 2.2, mast - 1.0, "v2_glass"),
                  cyl([cx - 18, cy, mast], [cx - 18, cy, mast - 14], 0.02, "v2_rail", sides=6),
                  box(cx - 18.6, cx - 17.4, cy - 0.6, cy + 0.6, mast - 14.6, mast - 14.0, "v2_crane")]
        groups.append((f"P{i}", P, (X0, X1, Y0 - 1.2, Y1), H + (14 if i == 0 else 2)))
    add_asset(site, "", "New Male Hall, under construction: concrete frame, rising brick infill, bamboo scaffolding, "
                        "safety nets and a tower crane.", groups)


def plot(site):
    """#26 / #27 (proposed): a corrugated-sheet hoarding with posts, survey stakes, a site board, sand and bricks."""
    s = site.site
    rng = rng_for(s["id"])
    x0, y0, x1, y1 = s["plot"]
    X0, X1, Y0, Y1 = site.rect([x0, y0, x1, y1])
    P = []
    gate = (X0 + X1) / 2
    runs = [((X0, Y1), (X1, Y1)), ((X0, Y0), (X0, Y1)), ((X1, Y0), (X1, Y1)), ((X0, Y0), (gate - 2.2, Y0)), ((gate + 2.2, Y0), (X1, Y0))]
    for (xa, ya), (xb, yb) in runs:
        horiz = abs(yb - ya) < 1e-6
        if horiz:
            P.append(box(min(xa, xb), max(xa, xb), ya - 0.04, ya + 0.02, 0.0, 2.0, "v2_sheet_blue"))
        else:
            P.append(box(xa - 0.04, xa + 0.02, min(ya, yb), max(ya, yb), 0.0, 2.0, "v2_sheet_blue"))
        L = math.hypot(xb - xa, yb - ya)
        n = int(L // 2.4)
        for k in range(n + 1):
            t = k / max(1, n)
            px, py = xa + (xb - xa) * t, ya + (yb - ya) * t
            P.append(box(px - 0.05, px + 0.05, py - 0.12, py - 0.04, 0.0, 2.1, "v2_steel"))
    for (fx, fy) in [site.pt(*q) for q in LAYOUT_SITE_POLY(s)]:
        P += [box(fx - 0.03, fx + 0.03, fy - 0.03, fy + 0.03, 0.0, 1.1, "v2_door"),
              box(fx - 0.035, fx + 0.035, fy - 0.035, fy + 0.035, 0.9, 1.05, "v2_crane")]
    bx = gate + 4.5
    P += [box(bx - 0.06, bx + 0.06, Y0 - 0.3, Y0 - 0.2, 0.0, 2.6, "v2_steel"), box(bx + 3.0 - 0.06, bx + 3.0 + 0.06, Y0 - 0.3, Y0 - 0.2, 0.0, 2.6, "v2_steel"),
          box(bx - 0.2, bx + 3.2, Y0 - 0.36, Y0 - 0.3, 1.4, 3.0, "v2_plaster_white"),
          text("PROPOSED", [bx + 1.5, Y0 - 0.37, 2.55], 0.3, "v2_rail"),
          text(s["name"].replace(" (Proposed)", "").upper(), [bx + 1.5, Y0 - 0.37, 2.1], 0.18, "v2_rail"),
          text("ISLAMIC UNIVERSITY OF TECHNOLOGY", [bx + 1.5, Y0 - 0.37, 1.6], 0.14, "v2_rail")]
    for k in range(3):
        px, py = X0 + (X1 - X0) * rng.uniform(0.2, 0.8), Y0 + (Y1 - Y0) * rng.uniform(0.3, 0.8)
        P.append({"blob": [round(px, 2), round(py, 2), 0.4], "size": [2.4, 2.0, 0.9], "lump": 0.25, "subdiv": 3,
                  "seed": k + 3, "mat": "v2_sand"})
        P.append(box(px + 3, px + 5.2, py, py + 1.2, 0.0, 1.0, "v2_brick_pile"))
    add_asset(site, "", s["name"] + ": a fenced, staked plot with its site board (D47).", [("Plot", P, (X0, X1, Y0, Y1), 3.0)])


def LAYOUT_SITE_POLY(s):
    x0, y0, x1, y1 = s["parts"][0]["rect"]
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def main_gate(site):
    rng = rng_for(site.site["id"])
    groups = []
    for i, p in enumerate(site.site["parts"]):
        X0, X1, Y0, Y1 = site.rect(p["rect"])
        role = p.get("role", "")
        H = p["h"]
        if "pylon" in role:
            P = [box(X0, X1, Y0, Y1, 0.0, H, "v2_brick"),
                 box(X0 - 0.2, X1 + 0.2, Y0 - 0.2, Y1 + 0.2, 0.0, 0.6, "v2_concrete"),
                 box(X0 - 0.15, X1 + 0.15, Y0 - 0.15, Y1 + 0.15, H - 0.4, H, "v2_coping"),
                 prism(half_disc((X0 + X1) / 2, H - 1.0, 1.8), [Y0 - 0.02, Y0 + 0.4], "v2_brick_reveal")]
            if "south" in role:
                P += [box(X0 + 0.6, X1 - 0.6, Y0 - 0.08, Y0, 2.6, 4.4, "v2_sign_green"),
                      text("IUT", [(X0 + X1) / 2, Y0 - 0.1, 3.7], 0.6, "v2_sign_text"),
                      text("ISLAMIC UNIVERSITY", [(X0 + X1) / 2, Y0 - 0.1, 3.2], 0.24, "v2_sign_text"),
                      text("OF TECHNOLOGY", [(X0 + X1) / 2, Y0 - 0.1, 2.85], 0.24, "v2_sign_text")]
            for z in (1.8, 4.2):
                P.append(cyl([(X0 + X1) / 2, Y0 - 0.25, z], [(X0 + X1) / 2, Y0 - 0.25, z + 0.3], 0.15, "v2_lamp", sides=12))
        elif "beam" in role:
            P = [box(X0, X1, Y0, Y1, H - 1.6, H, "v2_brick"),
                 box(X0 - 0.12, X1 + 0.12, Y0, Y1, H - 1.75, H - 1.6, "v2_coping"),
                 box(X0 - 0.12, X1 + 0.12, Y0, Y1, H, H + 0.15, "v2_coping")]
            for k in range(6):
                y = Y0 + 1.5 + k * (Y1 - Y0 - 3.0) / 5
                P.append(box(X0 - 0.02, X1 + 0.02, y - 0.3, y + 0.3, H - 1.3, H - 0.3, "v2_brick_reveal"))
            # the iron gate leaves, folded open against the pylons, and a boom barrier across the road
            P += [box(X0 + 0.3, X0 + 0.4, Y0 + 3.6, Y0 + 6.2, 0.0, 2.2, "v2_rail"),
                  box(X0 + 0.3, X0 + 0.4, Y1 - 6.2, Y1 - 3.6, 0.0, 2.2, "v2_rail"),
                  box(X0 - 2.0, X0 - 1.6, Y0 + 3.6, Y0 + 4.0, 0.0, 1.1, "v2_crane"),
                  box(X0 - 1.85, X0 - 1.75, Y0 + 4.0, Y1 - 3.8, 0.95, 1.05, "v2_crane")]
        else:
            P = block(X0, X1, Y0, Y1, H, "plaster", rng, 1, bay=2.0, roof_style="slab")
            P += [box(X0 + 0.8, X0 + 1.8, Y0 - 0.05, Y0 + 0.5, 0.0, 2.1, "v2_door_steel")]
        groups.append((f"P{i}_" + "".join(c for c in role.title() if c.isalnum()), P, (X0, X1, Y0, Y1), H))
    add_asset(site, "", "IUT Main Gate on the highway: brick pylons with half-disc reliefs, the coffered beam over the "
                        "gate road, folded iron leaves, a boom barrier, the security booth.", groups)


# --- recipes per site -----------------------------------------------------------------------------------------

def build_all(lay):
    ASSETS.clear()
    for s in lay["sites"]:
        site = Site(s)
        sid = s["id"]
        if sid == "mosque":
            mosque(site)
        elif sid == "auditorium":
            auditorium(site)
        elif sid == "cafeteria_library":
            cafeteria(site)
        elif sid == "five_fundamentals":
            five_fundamentals(site)
        elif sid in ("southern_workshop", "middle_workshop", "northern_workshop"):
            workshops(site)
        elif sid == "car_parking":
            parking(site)
        elif sid == "substation":
            substation(site)
        elif sid == "new_male_hall":
            construction(site)
        elif s.get("status") == "proposed":
            plot(site)
        elif sid == "main_gate":
            main_gate(site)
        elif sid in ("south_hall", "north_hall", "female_hall", "ub_hall"):
            generic_site(site, "hall", 5 if sid != "female_hall" else 4, bay=2.4)
        elif sid in ("academic_1", "academic_2"):
            generic_site(site, "academic", 6, bay=3.0)
        elif sid == "academic_3":
            generic_site(site, "academic", 4, bay=3.0, roof_style="red")
        elif sid == "admin":
            generic_site(site, "slits", 3, bay=1.6, ground="arcade", pointed=True)
        elif sid in ("cds", "indoor_sports"):
            generic_site(site, "hall" if sid == "cds" else "slits", 2 if sid == "cds" else 1, bay=3.0, ground="arcade")
        elif sid in ("vc_residence", "f_type_bungalow", "d_type_building", "medical_laundry"):
            generic_site(site, "plaster", None, bay=3.2)
        else:
            generic_site(site, "hall", None)
    for s in lay.get("structures", []):
        site = Site(s)
        generic_site(site, "plaster" if "room" in s["id"] or "hut" in s["id"] or "shelter" in s["id"] else "blank", 1, bay=2.4)


def main():
    lay = json.loads(LAYOUT.read_text(encoding="utf-8"))
    build_all(lay)
    if "--list" in sys.argv:
        for a in ASSETS:
            print(a["asset_id"])
        return
    changed = 0
    for a in ASSETS:
        params = {"mats": mats_for(a["objects"]), "objects": a["objects"], "footprint_m": [-1, 1, -1, 1], "lights": [],
                  "ceiling_z": None}
        changed += write_config(a["asset_id"], CATEGORY, a["scene"], a["desc"], params, px_per_m=PX, samples=SAMPLES,
                                layers=a["layers"], collision={"enabled": False},
                                render_extra={"window_mask": True})   # lit windows at night (tools/campus/night_windows.py)
    MANIFEST.write_text(json.dumps({
        "note": "Which rendered building stands where (Map v2). Written by assets/source/blender/tools/author_campus_v2.py; "
                "read by tools/zones/campus_world.py, which places a site's asset once its scene exists.",
        "assets": [{"site": a["site"], "asset_id": a["asset_id"], "scene": f"res://scenes/props/{CATEGORY}/{a['scene']}.tscn",
                    "centre_m": a["centre_m"], "layers": [l["name"] for l in a["layers"]]} for a in ASSETS]},
        indent=1) + "\n", encoding="utf-8")
    print(f"campus v2: {len(ASSETS)} building assets ({changed} configs changed); manifest data/campus/building_assets.json")


if __name__ == "__main__":
    main()

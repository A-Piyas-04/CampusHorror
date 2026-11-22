"""Writes the whole-campus exterior building configs (assembly generator), from Docs/map-reference/campus/.

    python assets/source/blender/tools/author_campus.py            # write / refresh every config
    python assets/source/blender/tools/author_campus.py --list     # asset ids

Plan and orientation: Docs/CAMPUS_BUILD.md (decisions D25, D26: iconic facades face south, the -Y face, which
is the one the camera sees). Frame: origin on the ground at the footprint centre, +X east, +Y north, Z up, m.
Big buildings render at 48-64 px/m (1:1 or better at the default zoom 2); long north-south blocks are built as
segments so each sorts on its own south edge.
"""

import math
import sys

sys.dont_write_bytecode = True
from author_lib import (MATS, blob, box, cbox, cyl, half_disc, leg, mats_for, moved, pointed_arch,  # noqa: E402
                        prism, rotated_z, text, tube, write_config)

MATS.update({
    "brick_wall": {"color": [0.56, 0.25, 0.17], "rough": 0.85, "var": 0.12, "var_scale": 2.0,
                   "pattern": {"type": "tiles", "size": 0.075, "bw": 3.0, "offset": 0.5, "color2": [0.5, 0.21, 0.14],
                               "mortar": 0.05, "mortar_color": [0.6, 0.52, 0.46]},
                   "stains": 0.3, "stain_color": [0.36, 0.17, 0.12], "stain_scale": 0.6},
    "brick_shade": {"color": [0.42, 0.18, 0.12], "rough": 0.85, "var": 0.1,
                    "pattern": {"type": "tiles", "size": 0.075, "bw": 3.0, "offset": 0.5, "color2": [0.38, 0.16, 0.1],
                                "mortar": 0.05, "mortar_color": [0.45, 0.4, 0.36]}},
    "void": {"color": [0.03, 0.025, 0.025], "rough": 0.95, "var": 0.0, "part_var": 0.0},
    "roof_slab": {"color": [0.42, 0.4, 0.37], "rough": 0.9, "var": 0.25, "var_scale": 1.5, "stains": 0.5,
                  "stain_color": [0.26, 0.25, 0.23], "stain_scale": 0.5, "bump": 0.2},
    "globe": {"color": [0.95, 0.95, 0.92], "rough": 0.2, "emit": [1.0, 0.97, 0.9], "emit_strength": 0.8},
    "ac_unit": {"color": [0.86, 0.86, 0.84], "rough": 0.5, "var": 0.04},
    "roof_red": {"color": [0.62, 0.16, 0.12], "rough": 0.6, "var": 0.06},
    "tin_roof": {"color": [0.5, 0.5, 0.48], "rough": 0.5, "metal": 0.6,
                 "pattern": {"type": "stripes", "period": 0.25, "color2": [0.44, 0.44, 0.42], "axis": "x"}},
    "lattice": {"color": [0.1, 0.1, 0.1], "rough": 0.6, "metal": 0.5},
    "coping": {"color": [0.78, 0.76, 0.7], "rough": 0.7, "stains": 0.4, "stain_color": [0.5, 0.48, 0.42]},
    "door_wood": {"color": [0.35, 0.2, 0.11], "rough": 0.55, "stains": 0.2,
                  "pattern": {"type": "grain", "scale": [30, 0.6, 30]}},
    "sign_green": {"color": [0.1, 0.33, 0.2], "rough": 0.5, "stains": 0.3},
    "sign_white": {"color": [0.92, 0.91, 0.86], "rough": 0.5},
})

ASSETS = {}


def asset(asset_id, scene, desc, objects, footprint, *, px=48.0, collision=None, layers=None, z_index=0,
          samples=192):
    params = {"mats": mats_for(objects), "objects": objects, "footprint_m": footprint, "lights": [],
              "ceiling_z": None}
    col = {"enabled": True, "source": "rects_m", "rects_m": collision, "depth_mode": "projected"} if collision \
        else {"enabled": False}
    ASSETS[asset_id] = dict(scene=scene, desc=desc, params=params, px=px, collision=col, layers=layers,
                            z_index=z_index, samples=samples)


def one(parts, bevel=0.01):
    return {"Main": {"parts": parts, "bevel": bevel}}


def S(y_face):
    """Span for a south-face opening: just proud of the wall, a little into it."""
    return [y_face - 0.02, y_face + 0.25]


def parapet(x0, x1, y0, y1, z, mat="brick_wall", h=0.9, t=0.3):
    return [box(x0, x1, y0, y0 + t, z, z + h, mat), box(x0, x1, y1 - t, y1, z, z + h, mat),
            box(x0, x0 + t, y0, y1, z, z + h, mat), box(x1 - t, x1, y0, y1, z, z + h, mat),
            box(x0 - 0.05, x1 + 0.05, y0 - 0.05, y0 + t + 0.05, z + h, z + h + 0.12, "coping")]


def flat_roof(x0, x1, y0, y1, z):
    return [box(x0, x1, y0, y1, z - 0.3, z + 0.03, "roof_slab")] + parapet(x0, x1, y0, y1, z + 0.03)


# --- The Central Plaza ---------------------------------------------------------------------------------------

def plaza():
    # Mosque: windowless brick cube, the great half-disc recess with stepped glazing, a small arched door.
    W, D, H = 18.0, 18.0, 15.0
    y0 = -D / 2
    m = [box(-W / 2, W / 2, -D / 2, D / 2, 0.0, H, "brick_wall")]
    m += flat_roof(-W / 2, W / 2, -D / 2, D / 2, H)
    m.append(prism(half_disc(0.0, 12.8, 7.2), [y0 - 0.03, y0 + 0.6], "brick_shade"))
    for k, (hw, z0) in enumerate(((5.2, 11.2), (3.8, 9.6), (2.4, 8.0), (1.1, 6.6))):
        m.append(box(-hw, hw, y0 - 0.05, y0 + 0.2, z0, 12.4, "glass"))
    for x in (-5.2, -3.8, -2.4, -1.1, 0.0, 1.1, 2.4, 3.8, 5.2):
        m.append(box(x - 0.05, x + 0.05, y0 - 0.07, y0 - 0.04, 6.6, 12.4, "metal_dark"))
    m.append(box(-0.5, 0.5, y0 - 0.03, y0 + 0.2, 3.1, 5.7, "brick_shade"))
    m.append(prism(pointed_arch(0.0, 1.5, 0.0, 2.2, 3.0), S(y0), "void"))
    m.append(box(1.2, 2.0, y0 - 0.05, y0, 0.0, 2.6, "door_wood"))
    m.append(box(-W / 2 - 0.3, W / 2 + 0.3, -D / 2 - 0.3, D / 2 + 0.3, 0.0, 0.3, "coping"))
    for x in (-6.0, 6.0):
        m.append(cbox(x, y0 - 0.15, 0.25, 0.3, 4.2, 4.5, "white_paint"))
    asset("plaza_mosque", "PlazaMosque", "IUT Central Mosque: brick cube, great half-disc window with stepped glazing "
          "facing the plaza (south, D26), small arched door.", one(m), [-9, 9, -9, 9], px=48.0,
          collision={"Mass": [-9.3, 9.3, -9.3, 9.3]})

    # Minaret ("Pillars"): brick cylinder, square cage top cut by half-discs on every face.
    r = 1.7
    mn = [cyl([0, 0, 0], [0, 0, 25.5], r, "brick_wall", sides=24),
          cyl([0, 0, 0], [0, 0, 0.4], r + 0.3, "coping", sides=24)]
    c = 2.0
    mn += [box(-c, c, -c, c, 25.5, 26.0, "brick_wall"), box(-c, c, -c, c, 29.4, 30.0, "brick_wall")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            xa, xb = (-c, -c + 0.5) if sx < 0 else (c - 0.5, c)
            ya, yb = (-c, -c + 0.5) if sy < 0 else (c - 0.5, c)
            mn.append(box(xa, xb, ya, yb, 26.0, 29.4, "brick_wall"))
    for face in (-1, 1):
        y = face * c
        mn.append(box(-c, c, y - 0.25, y + 0.25, 28.0, 29.4, "brick_wall"))
        mn.append(prism(half_disc(0.0, 28.0, 1.3), [y - 0.26, y + 0.26], "brick_wall"))
    for face in (-1, 1):
        x = face * c
        mn.append(box(x - 0.25, x + 0.25, -c, c, 28.0, 29.4, "brick_wall"))
        mn.append(prism(half_disc(0.0, 28.0, 1.3), [x - 0.26, x + 0.26], "brick_wall", axis="x"))
    mn.append(cyl([0, 0, 26.0], [0, 0, 27.6], 0.6, "metal_dark", sides=12))
    asset("plaza_minaret", "PlazaMinaret", "The Central Plaza minaret ('Pillars'): brick cylinder with a square cage "
          "top cut by half-discs, loudspeaker horns inside.", one(mn), [-2.0, 2.0, -2.0, 2.0], px=56.0,
          collision={"Shaft": [-1.8, 1.8, -1.8, 1.8]})

    # Central Cafe: low block, four tall pointed arches over a recessed arcade on the south.
    W, D, H = 30.0, 16.0, 9.0
    y0 = -D / 2
    cf = [box(-W / 2, W / 2, -D / 2 + 3.0, D / 2, 0.0, H, "brick_wall"),
          box(-W / 2, W / 2, -D / 2, -D / 2 + 3.0, 7.6, H, "brick_wall")]
    cf += flat_roof(-W / 2, W / 2, -D / 2, D / 2, H)
    for k in range(5):
        x = -W / 2 + k * (W / 4)
        cf.append(box(x - 0.6 if k else x, x + 0.6 if k < 4 else x, y0, y0 + 3.0, 0.0, 7.6, "brick_wall"))
    for k in range(4):
        cx = -W / 2 + W / 8 + k * W / 4
        cf.append(prism(pointed_arch(cx, 5.6, 0.0, 4.6, 7.2), [y0 - 0.02, y0 + 0.4], "void"))
        cf.append(box(cx - 2.0, cx + 2.0, y0 + 3.0, y0 + 3.05, 0.0, 2.6, "glass"))
        cf.append(box(cx - 2.8, cx + 2.8, y0 + 0.4, y0 + 3.0, 0.0, 0.05, "coping"))
    cf.append(text("CENTRAL CAFETERIA", [0.0, y0 - 0.03, 8.0], 0.55, "white_paint"))
    asset("plaza_central_cafe", "PlazaCentralCafe", "IUT Central Cafeteria: four tall pointed arches over a recessed "
          "arcade on the plaza side (south, D26).", one(cf), [-15, 15, -8, 8], px=48.0,
          collision={"Mass": [-15, 15, -5, 8], "PierW": [-15, -14.4, -8, -5], "PierE": [14.4, 15, -8, -5]})

    # Admin building: three storeys of deep vertical brick fins, ground-floor pointed arches, AC units.
    W, D, H = 40.0, 16.0, 12.0
    y0 = -D / 2
    ad = [box(-W / 2, W / 2, y0 + 1.2, D / 2, 0.0, H, "brick_wall")]
    ad += flat_roof(-W / 2, W / 2, y0, D / 2, H)
    bays = 12
    bw = W / bays
    for k in range(bays + 1):
        x = -W / 2 + k * bw
        ad.append(box(x - 0.35, x + 0.35, y0, y0 + 1.2, 0.0, H, "brick_wall"))
    for k in range(bays):
        cx = -W / 2 + bw * (k + 0.5)
        ad.append(prism(pointed_arch(cx, bw - 0.9, 0.0, 2.4, 3.4), [y0 + 1.15, y0 + 1.3], "void"))
        for f in range(1, 3):
            z = f * 4.0
            ad.append(box(cx - (bw - 0.9) / 2, cx + (bw - 0.9) / 2, y0 + 1.1, y0 + 1.25, z + 0.6, z + 3.0, "glass"))
            ad.append(box(cx - (bw - 0.7) / 2, cx + (bw - 0.7) / 2, y0, y0 + 1.2, z, z + 0.25, "brick_shade"))
            if k % 3 == 1:
                ad.append(box(cx - 0.45, cx + 0.45, y0 + 0.5, y0 + 1.1, z + 0.4, z + 1.0, "ac_unit"))
    ad.append(text("ADMINISTRATIVE BUILDING", [0.0, y0 - 0.02, 11.2], 0.45, "white_paint"))
    asset("plaza_admin", "PlazaAdmin", "IUT Administrative Building: deep vertical brick fins, three storeys, "
          "ground-floor pointed arches, AC units (south face, D26).", one(ad), [-20, 20, -8, 8], px=44.0,
          collision={"Mass": [-20, 20, -6.8, 8], "Fins": [-20.4, 20.4, -8, -6.8]})

    # Auditorium: big box with a pointed-arch arcade on the south and stair heads on the roof.
    W, D, H = 34.0, 26.0, 12.0
    y0 = -D / 2
    au = [box(-W / 2, W / 2, y0 + 3.5, D / 2, 0.0, H, "brick_wall"),
          box(-W / 2, W / 2, y0, y0 + 3.5, 7.2, H, "brick_wall")]
    au += flat_roof(-W / 2, W / 2, y0, D / 2, H)
    n = 6
    for k in range(n + 1):
        x = -W / 2 + k * W / n
        au.append(box(x - 0.55, x + 0.55, y0, y0 + 3.5, 0.0, 7.2, "brick_wall"))
    for k in range(n):
        cx = -W / 2 + W / n * (k + 0.5)
        au.append(prism(pointed_arch(cx, W / n - 1.1, 0.0, 4.2, 6.6), [y0 - 0.02, y0 + 0.35], "void"))
    au.append(box(-3.0, 3.0, y0 + 3.45, y0 + 3.55, 0.0, 3.0, "door_wood"))
    for x, y in ((-10, 4), (9, -2)):
        au += [box(x - 2.5, x + 2.5, y - 2.0, y + 2.0, H, H + 3.0, "brick_wall")] + parapet(x - 2.5, x + 2.5, y - 2, y + 2, H + 3.0, h=0.5)
    au.append(text("AUDITORIUM", [0.0, y0 - 0.02, 10.8], 0.6, "white_paint"))
    asset("plaza_auditorium", "PlazaAuditorium", "IUT Auditorium: a big brick box with a deep pointed-arch arcade "
          "(south, D26) and stair heads on the roof; the AV hall is inside (D27).", one(au), [-17, 17, -13, 13],
          px=44.0, collision={"Mass": [-17, 17, -9.5, 13], "Piers": [-17.5, 17.5, -13, -12.4]})

    # Five Pillars: five parallel brick walls, a pointed arch through them, stepped edges.
    fp = []
    for k in range(5):
        y = -1.8 + k * 0.9
        x0, x1 = -4.6 + k * 0.25, 4.0 + k * 0.15
        fp.append(prism([(x0, 0.0), (-1.8, 0.0)] + list(reversed(pointed_arch(0.0, 3.6, 0.0, 5.6, 8.2)[2:-1])) +
                        [(1.8, 0.0), (x1, 0.0), (x1, 11.0 - k * 0.2), (x0, 11.0 - k * 0.2)],
                        [y, y + 0.45], "brick_wall"))
    fp.append(box(-5.5, 5.5, -2.6, 2.6, -0.6, 0.0, "coping"))
    asset("five_pillars", "FivePillars", "The Five Pillars gate at the lake corner: five parallel brick walls with a "
          "pointed arch through them.", one(fp), [-5.5, 5.5, -2.6, 2.6], px=56.0,
          collision={"WestWalls": [-5.0, -1.9, -2.0, 2.0], "EastWalls": [1.9, 4.8, -2.0, 2.0]})

    # Plaza lamp: black pole with five white globes.
    lp = [cyl([0, 0, 0], [0, 0, 4.4], 0.07, "metal_dark", sides=10),
          cyl([0, 0, 0], [0, 0, 0.5], 0.14, "metal_dark", sides=10)]
    for k in range(4):
        a = math.pi / 2 * k + math.pi / 4
        lp.append(tube([[0, 0, 4.1], [0.35 * math.cos(a), 0.35 * math.sin(a), 4.25]], 0.025, "metal_dark"))
        lp.append(blob(0.4 * math.cos(a), 0.4 * math.sin(a), 4.45, 0.17, 0.17, 0.17, "globe", lump=0.0, subdiv=3,
                       floor=-1.0))
    lp.append(blob(0, 0, 4.75, 0.18, 0.18, 0.18, "globe", lump=0.0, subdiv=3, floor=-1.0))
    asset("plaza_lamp", "PlazaLamp", "Central Plaza lamp: black pole with a cluster of five white globes.", one(lp, 0.0),
          [-0.5, 0.5, -0.5, 0.5], px=120.0, collision={"Pole": [-0.15, 0.15, -0.15, 0.15]})

    # Lake bridge module (12 m along X): deck, arched brick railings, steel lattice under the deck edge.
    L, Wd = 12.0, 4.0
    br = [box(-L / 2, L / 2, -Wd / 2, Wd / 2, 0.55, 0.85, "brick_wall")]
    for side in (-1, 1):
        y = side * (Wd / 2 - 0.15)
        rail = [(-L / 2, 0.85), (L / 2, 0.85), (L / 2, 1.9), (-L / 2, 1.9)]
        br.append(box(-L / 2, L / 2, y - 0.15, y + 0.15, 1.65, 1.95, "brick_wall"))
        for k in range(7):
            x = -L / 2 + k * L / 6
            br.append(box(x - 0.18, x + 0.18, y - 0.15, y + 0.15, 0.85, 1.65, "brick_wall"))
        for k in range(6):
            cx = -L / 2 + L / 6 * (k + 0.5)
            br.append(prism([(cx - 0.82, 1.65), (cx - 0.82, 1.35), (cx - 0.4, 1.58), (cx, 1.63), (cx + 0.4, 1.58),
                             (cx + 0.82, 1.35), (cx + 0.82, 1.65)], [y - 0.15, y + 0.15], "brick_wall"))
        for k in range(10):
            x = -L / 2 + 0.6 + k * 1.2
            br.append(tube([[x - 0.6, y, 0.0], [x, y, 0.55], [x + 0.6, y, 0.0]], 0.03, "lattice", cap=False))
    asset("lake_bridge", "LakeBridge", "Lake bridge module, 12 m: brick deck, arched brick railings, steel lattice "
          "below (photo 02).", one(br), [-6, 6, -2, 2], px=64.0,
          collision={"RailS": [-6, 6, -2, -1.7], "RailN": [-6, 6, 1.7, 2]})

    # North-south bridge (10 m along Y, crossing the lake ring's north / south strips): railings edge-on, so
    # the deck, the railing tops and the lattice show.
    Lb, Wb = 10.0, 4.0
    bn = [box(-Wb / 2, Wb / 2, -Lb / 2, Lb / 2, 0.55, 0.85, "brick_wall"),
          box(-Wb / 2 - 0.1, Wb / 2 + 0.1, -Lb / 2 - 0.4, -Lb / 2, 0.0, 0.85, "brick_wall"),
          box(-Wb / 2 - 0.1, Wb / 2 + 0.1, Lb / 2, Lb / 2 + 0.4, 0.0, 0.85, "brick_wall")]
    for side in (-1, 1):
        x = side * (Wb / 2 - 0.15)
        bn.append(box(x - 0.15, x + 0.15, -Lb / 2, Lb / 2, 1.65, 1.95, "brick_wall"))
        for k in range(6):
            y = -Lb / 2 + k * Lb / 5
            bn.append(box(x - 0.15, x + 0.15, y - 0.18, y + 0.18, 0.85, 1.65, "brick_wall"))
        for k in range(5):
            cy = -Lb / 2 + Lb / 5 * (k + 0.5)
            bn.append(prism([(cy - 0.82, 1.65), (cy - 0.82, 1.35), (cy - 0.4, 1.58), (cy, 1.63), (cy + 0.4, 1.58),
                             (cy + 0.82, 1.35), (cy + 0.82, 1.65)], [x - 0.15, x + 0.15], "brick_wall", axis="x"))
    asset("lake_bridge_ns", "LakeBridgeNs", "Lake bridge running north-south, 10 m: brick deck and arched railings.",
          one(bn), [-2, 2, -5.4, 5.4], px=64.0, collision={"RailW": [-2.1, -1.7, -5, 5], "RailE": [1.7, 2.1, -5, 5]})

    # Lake edge module (6 m): brick retaining wall with coping, the water side darker.
    le = [box(-3, 3, -0.3, 0.3, -0.6, 0.45, "brick_wall"), box(-3.02, 3.02, -0.34, 0.34, 0.45, 0.55, "coping"),
          box(-3, 3, -0.32, -0.3, -0.6, 0.2, "brick_shade")]
    asset("lake_edge", "LakeEdge", "Lake retaining edge, 6 m module: brick with a light coping.", one(le, 0.005),
          [-3, 3, -0.34, 0.34], px=80.0, collision={"Edge": [-3, 3, -0.34, 0.34]})


# --- Halls ------------------------------------------------------------------------------------------------------

def hall_segment(asset_id, scene, desc, *, length=30.0, width=20.0, height=16.0, style="south", entrance=False,
                 cylinders=2):
    """One north-south segment of a hall block (long axis along Y). The long faces (east/west, seen edge-on) get
    projecting brick cylinders that read from above; the south face carries the hall's signature openings."""
    W, L, H = width, length, height
    p = [box(-W / 2, W / 2, -L / 2, L / 2, 0.0, H, "brick_wall")]
    p += flat_roof(-W / 2, W / 2, -L / 2, L / 2, H)
    y0 = -L / 2
    floors = 5
    fh = H / floors
    if style == "south":
        cols = 6
        for f in range(1, floors):
            for k in range(cols):
                cx = -W / 2 + W / cols * (k + 0.5)
                z = f * fh
                if entrance and abs(cx) < 2.4:
                    continue
                if (k + f) % 2:
                    p.append(prism(pointed_arch(cx, 1.3, z + 0.4, z + 1.6, z + 2.4), S(y0), "void"))
                else:
                    p.append(cyl([cx, y0 - 0.02, z + 1.4], [cx, y0 + 0.2, z + 1.4], 0.55, "void", sides=16))
    else:
        cols = 4
        for f in range(floors):
            for k in range(cols):
                cx = -W / 2 + W / cols * (k + 0.5)
                z = f * fh
                if entrance and abs(cx) < 2.9:
                    continue
                p.append(prism(pointed_arch(cx, 2.4, z + 0.3, z + 1.7, z + 2.9), S(y0), "void"))
    if entrance:
        p.append(box(-1.6, 1.6, y0 - 0.02, y0 + 0.4, 0.0, H - 1.0, "void"))
        for f in range(1, floors):
            p.append(box(-1.7, 1.7, y0 - 0.25, y0 + 0.4, f * fh - 0.2, f * fh, "brick_wall"))
        p.append(box(-2.4, 2.4, y0 - 1.6, y0 - 1.3, 0.0, 1.2, "brick_wall"))
        p.append(box(-2.2, 2.2, y0 - 1.64, y0 - 1.6, 0.2, 1.0, "sign_green"))
        p.append(text("SOUTH HALL OF RESIDENCE" if style == "south" else "NORTH HALL OF RESIDENCE",
                      [0.0, y0 - 1.66, 0.48], 0.17, "sign_white"))
    for side in (-1, 1):
        for k in range(cylinders):
            y = -L / 2 + L / cylinders * (k + 0.5)
            x = side * (W / 2 + 1.0)
            p.append(cyl([x, y, 0.0], [x, y, H + 0.6], 1.6, "brick_wall", sides=24))
            p.append(cyl([x, y, H + 0.6], [x, y, H + 0.75], 1.65, "coping", sides=24))
    for k in range(3):
        p.append(box(-W / 2 + 2 + k * 6, -W / 2 + 3.5 + k * 6, -2, 1, H, H + 1.2, "roof_slab"))
    asset(asset_id, scene, desc, one(p), [-W / 2 - 2.6, W / 2 + 2.6, -L / 2, L / 2], px=40.0,
          collision={"Mass": [-W / 2 - 2.6, W / 2 + 2.6, -L / 2, L / 2]})


def halls():
    hall_segment("south_hall_front", "SouthHallFront", "South Hall, south segment: grid of pointed-arch and round "
                 "windows, the entrance slot and sign (photo 11; south face, D26).", style="south", entrance=True)
    hall_segment("south_hall_wing", "SouthHallWing", "South Hall, middle segment: brick cylinders on both long faces.",
                 style="south")
    hall_segment("north_hall_front", "NorthHallFront", "North Hall, south segment: tall pointed arches and the "
                 "entrance (photos 06, 07).", style="north", entrance=True)
    hall_segment("north_hall_wing", "NorthHallWing", "North Hall, middle segment: brick cylinders, pointed arches.",
                 style="north")
    # UB Hall: east-west block closing the courtyard's south end, rows of small pointed arches on its south face.
    W, D, H = 70.0, 18.0, 16.0
    y0 = -D / 2
    ub = [box(-W / 2, W / 2, -D / 2, D / 2, 0.0, H, "brick_wall")]
    ub += flat_roof(-W / 2, W / 2, -D / 2, D / 2, H)
    for f in range(5):
        for k in range(22):
            cx = -W / 2 + W / 22 * (k + 0.5)
            z = f * 3.2
            if (k + f) % 3 == 0:
                ub.append(cyl([cx, y0 - 0.02, z + 1.6], [cx, y0 + 0.2, z + 1.6], 0.45, "void", sides=14))
            else:
                ub.append(prism(pointed_arch(cx, 1.1, z + 0.6, z + 1.7, z + 2.4), S(y0), "void"))
    for x in (-W / 2 - 1.0, W / 2 + 1.0, -12.0, 12.0):
        ub.append(cyl([x, y0 + (0 if abs(x) > 30 else -1.0), 0.0], [x, y0 + (0 if abs(x) > 30 else -1.0), H + 0.6],
                      1.7, "brick_wall", sides=24))
    asset("ub_hall", "UbHall", "UB Hall: the block closing the halls' courtyard, rows of small pointed arches and round "
          "windows (photos 06, 08).", one(ub), [-36, 36, -9, 9], px=40.0, collision={"Mass": [-36.5, 36.5, -10.5, 9]})
    # Halls gate + arcade wall (photo 07): low arcade wall with a central gate arch.
    L = 40.0
    gw = [box(-L / 2, L / 2, -0.4, 0.4, 0.0, 0.5, "brick_wall"), box(-L / 2, L / 2, -0.45, 0.45, 3.0, 3.4, "brick_wall")]
    for k in range(17):
        x = -L / 2 + k * L / 16
        if abs(x) < 2.6:
            continue
        gw.append(box(x - 0.3, x + 0.3, -0.4, 0.4, 0.5, 3.0, "brick_wall"))
    for k in range(16):
        cx = -L / 2 + L / 16 * (k + 0.5)
        if abs(cx) < 2.6:
            continue
        gw.append(prism([(cx - 0.95, 3.0), (cx - 0.95, 2.3), (cx - 0.5, 2.8), (cx, 2.95), (cx + 0.5, 2.8),
                         (cx + 0.95, 2.3), (cx + 0.95, 3.0)], [-0.4, 0.4], "brick_wall"))
        gw.append(box(cx - 0.9, cx + 0.9, -0.05, 0.05, 0.5, 2.4, "lattice"))
    gw += [box(-2.8, -2.0, -0.6, 0.6, 0.0, 4.6, "brick_wall"), box(2.0, 2.8, -0.6, 0.6, 0.0, 4.6, "brick_wall"),
           box(-2.8, 2.8, -0.6, 0.6, 4.6, 5.2, "brick_wall"),
           prism([(-2.0, 4.6), (-2.0, 3.4), (-1.0, 4.2), (0.0, 4.5), (1.0, 4.2), (2.0, 3.4), (2.0, 4.6)], [-0.6, 0.6],
                 "brick_wall")]
    asset("halls_gate_wall", "HallsGateWall", "The halls' gate: a low brick arcade wall with lattice infill and a "
          "central gate arch (photo 07).", one(gw), [-20, 20, -0.6, 0.6], px=56.0,
          collision={"West": [-20, -2.8, -0.45, 0.45], "East": [2.8, 20, -0.45, 0.45]})


# --- Academic area ------------------------------------------------------------------------------------------------

def grid_block(asset_id, scene, desc, *, W, D, H, floors, bays, cylinders=(), roof_band=None, px=36.0):
    """An academic block: deep brick grid frame on the south face (each cell a window with an AC unit sometimes),
    brick stair cylinders, flat roof with plant."""
    y0 = -D / 2
    p = [box(-W / 2, W / 2, y0 + 0.9, D / 2, 0.0, H, "brick_wall")]
    p += flat_roof(-W / 2, W / 2, y0, D / 2, H)
    fh = H / floors
    for k in range(bays + 1):
        x = -W / 2 + k * W / bays
        p.append(box(x - 0.25, x + 0.25, y0, y0 + 0.9, 0.0, H, "brick_wall"))
    for f in range(floors + 1):
        p.append(box(-W / 2, W / 2, y0, y0 + 0.9, f * fh - 0.2, f * fh + 0.1, "brick_wall"))
    for f in range(floors):
        for k in range(bays):
            cx = -W / 2 + W / bays * (k + 0.5)
            z = f * fh
            p.append(box(cx - W / bays / 2 + 0.3, cx + W / bays / 2 - 0.3, y0 + 0.85, y0 + 0.95, z + 0.5, z + fh - 0.4,
                         "glass" if f else "void"))
            if (k * 7 + f * 3) % 5 == 0:
                p.append(box(cx - 0.4, cx + 0.4, y0 + 0.3, y0 + 0.85, z + 0.3, z + 0.9, "ac_unit"))
    for x, y, r in cylinders:
        p.append(cyl([x, y, 0.0], [x, y, H + 2.0], r, "brick_wall", sides=28))
        p.append(cyl([x, y, H + 2.0], [x, y, H + 2.2], r + 0.05, "coping", sides=28))
    if roof_band:
        p.append(box(-W / 2, W / 2, y0, y0 + 0.6, H - 1.2, H, roof_band))
    p.append(box(-3, 3, -2, 2, H, H + 2.5, "roof_slab"))
    cyl_rects = {f"Tower{i}": [x - r, x + r, y - r, y + r] for i, (x, y, r) in enumerate(cylinders)}
    asset(asset_id, scene, desc, one(p), [-W / 2 - 3, W / 2 + 3, -D / 2 - 3, D / 2 + 3], px=px,
          collision={"Mass": [-W / 2, W / 2, -D / 2, D / 2], **cyl_rects})


def academic():
    grid_block("academic_1", "Academic1", "Academic Building 1: six storeys of deep brick grid with AC units, two brick "
               "stair cylinders (photos 05, 09).", W=50, D=20, H=22, floors=6, bays=14,
               cylinders=((-27.5, 2, 2.6), (27.5, -2, 2.6)))
    grid_block("academic_2", "Academic2", "Academic Building 2: eight storeys of brick grid crowded with AC units, "
               "giant brick cylinders (photos 03, 04).", W=40, D=22, H=30, floors=8, bays=11,
               cylinders=((-23, -3, 3.4), (8, -13.5, 3.4)), px=32.0)
    grid_block("academic_3", "Academic3", "Academic Building 3: a long low block with a red roof band (photo 12).",
               W=70, D=14, H=8, floors=2, bays=20, roof_band="roof_red")
    # ME workshop: long shed, pitched tin roof on brick walls, big doors.
    W, D, H = 50.0, 14.0, 5.0
    me = [box(-W / 2, W / 2, -D / 2, D / 2, 0.0, H, "brick_wall")]
    me.append(prism([(-D / 2 - 0.5, H), (D / 2 + 0.5, H), (0.0, H + 2.4)], [-W / 2 - 0.4, W / 2 + 0.4], "tin_roof",
                    axis="x"))
    for k in range(5):
        cx = -W / 2 + W / 5 * (k + 0.5)
        me.append(box(cx - 1.8, cx + 1.8, -D / 2 - 0.05, -D / 2 + 0.1, 0.0, 3.6, "steel_grey"))
        me.append(box(cx - 3.6, cx - 2.4, -D / 2 - 0.05, -D / 2 + 0.1, 1.6, 3.4, "glass"))
    me.append(text("ME WORKSHOP", [0.0, -D / 2 - 0.08, 4.0], 0.5, "white_paint"))
    asset("me_workshop", "MeWorkshop", "Mechanical engineering workshop: long brick shed, pitched tin roof, steel "
          "doors (photos 03, 12).", one(me), [-25.4, 25.4, -7.5, 7.5], px=40.0,
          collision={"Mass": [-25, 25, -7, 7]})
    # Garage canopy.
    gc = [box(-12, 12, -4, 4, 2.8, 2.95, "tin_roof")]
    for x in (-11, -5.5, 0, 5.5, 11):
        gc += [leg(x, -3.5, 0.0, 2.8, 0.08, "steel_grey"), leg(x, 3.5, 0.0, 2.8, 0.08, "steel_grey")]
    asset("garage_canopy", "GarageCanopy", "Garage shade canopy on steel posts (photos 03, 05).", one(gc),
          [-12, 12, -4, 4], px=48.0, collision={f"Post{i}": [x - 0.15, x + 0.15, -3.65, 3.65] for i, x in
                                                enumerate((-11, -5.5, 0, 5.5, 11))})
    # Tall street lamp (curved arm).
    sl = [cyl([0, 0, 0], [0, 0, 7.5], 0.09, "steel_grey", sides=10),
          tube([[0, 0, 7.5], [0.4, 0, 7.9], [1.4, 0, 8.0]], 0.05, "steel_grey"),
          box(1.2, 1.9, -0.15, 0.15, 7.85, 8.0, "steel_grey"), box(1.25, 1.85, -0.12, 0.12, 7.82, 7.86, "globe")]
    asset("street_lamp_tall", "StreetLampTall", "Tall campus street lamp with a curved arm (photos 06, 11).", one(sl),
          [-0.3, 2.0, -0.3, 0.3], px=96.0, collision={"Pole": [-0.15, 0.15, -0.15, 0.15]})


def define():
    plaza()
    halls()
    academic()


def main():
    define()
    if "--list" in sys.argv:
        print("\n".join(ASSETS))
        return
    changed = []
    for aid, a in ASSETS.items():
        if write_config(aid, "campus", a["scene"], a["desc"], a["params"], px_per_m=a["px"], samples=a["samples"],
                        layers=a["layers"], collision=a["collision"], z_index=a["z_index"]):
            changed.append(aid)
    print(f"{len(ASSETS)} campus configs; changed: {' '.join(changed) if changed else 'none'}")


if __name__ == "__main__":
    main()

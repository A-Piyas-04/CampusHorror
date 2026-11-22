"""Authoring helpers for assembly configs (plain Python, no bpy): a shared material library and part builders.

Used by tools/author_props.py and tools/author_rooms.py, which write assets/source/blender/configs/*.json for
the `assembly` generator. Those scripts are the source of truth for the Chapter 1 props and interiors: edit them
and re-run, never the generated configs.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONFIG_DIR = ROOT / "assets/source/blender/configs"
DEPTH = 0.643  # projected ground depth factor (sin 40 deg)

# --- Material library (sRGB) -----------------------------------------------------------------------------------
MATS = {
    "laminate": {"color": [0.80, 0.78, 0.72], "rough": 0.35, "var": 0.05, "stains": 0.25,
                 "stain_color": [0.55, 0.5, 0.42]},
    "wood": {"color": [0.46, 0.29, 0.16], "rough": 0.5, "pattern": {"type": "grain", "scale": [0.6, 30, 30]}},
    "wood_dark": {"color": [0.26, 0.16, 0.09], "rough": 0.5, "pattern": {"type": "grain", "scale": [0.6, 30, 30]}},
    "steel_blue": {"color": [0.22, 0.33, 0.45], "rough": 0.45, "metal": 0.3, "var": 0.1, "stains": 0.3,
                   "stain_color": [0.35, 0.25, 0.18]},
    "steel_green": {"color": [0.25, 0.38, 0.30], "rough": 0.45, "metal": 0.3, "var": 0.1, "stains": 0.3,
                    "stain_color": [0.35, 0.25, 0.18]},
    "steel_grey": {"color": [0.52, 0.53, 0.52], "rough": 0.4, "metal": 0.4, "var": 0.08, "stains": 0.2},
    "metal_dark": {"color": [0.16, 0.16, 0.17], "rough": 0.4, "metal": 0.6},
    "chrome": {"color": [0.75, 0.75, 0.77], "rough": 0.22, "metal": 1.0, "var": 0.03},
    "aluminium": {"color": [0.68, 0.68, 0.66], "rough": 0.35, "metal": 1.0, "var": 0.08},
    "plastic_red": {"color": [0.66, 0.12, 0.10], "rough": 0.38, "var": 0.04, "part_var": 0.1},
    "plastic_green": {"color": [0.16, 0.45, 0.25], "rough": 0.38, "var": 0.04, "part_var": 0.1},
    "plastic_blue": {"color": [0.12, 0.3, 0.6], "rough": 0.38, "var": 0.04},
    "plastic_white": {"color": [0.85, 0.85, 0.82], "rough": 0.4, "var": 0.04, "stains": 0.2},
    "rubber": {"color": [0.06, 0.06, 0.06], "rough": 0.8},
    "tt_blue": {"color": [0.08, 0.2, 0.42], "rough": 0.3, "var": 0.05},
    "white_paint": {"color": [0.92, 0.92, 0.9], "rough": 0.5},
    "net": {"color": [0.1, 0.1, 0.1], "rough": 0.9},
    "paper": {"color": [0.93, 0.91, 0.85], "rough": 0.8, "var": 0.04},
    "paper_old": {"color": [0.84, 0.79, 0.64], "rough": 0.8, "var": 0.1, "stains": 0.3},
    "cork": {"color": [0.55, 0.38, 0.22], "rough": 0.9, "bump": 0.3, "bump_scale": 120},
    "fabric_blue": {"color": [0.13, 0.19, 0.3], "rough": 0.9, "bump": 0.1, "bump_scale": 200},
    "fabric_khaki": {"color": [0.42, 0.38, 0.26], "rough": 0.9, "bump": 0.1, "bump_scale": 200},
    "fabric_red": {"color": [0.45, 0.1, 0.1], "rough": 0.9, "bump": 0.1, "bump_scale": 200},
    "mattress": {"color": [0.55, 0.5, 0.38], "rough": 0.9, "stains": 0.5, "stain_color": [0.4, 0.33, 0.2]},
    "screen_dark": {"color": [0.02, 0.025, 0.03], "rough": 0.1, "spec": 0.8},
    "screen_glow": {"color": [0.05, 0.1, 0.08], "rough": 0.2, "emit": [0.4, 0.75, 0.55], "emit_strength": 1.2},
    "glass": {"color": [0.05, 0.07, 0.1], "glass": True, "var": 0.0, "part_var": 0.0},
    "exit_green": {"color": [0.1, 0.6, 0.25], "rough": 0.3, "emit": [0.2, 1.0, 0.4], "emit_strength": 2.5},
    "blood": {"color": [0.30, 0.015, 0.015], "rough": 0.15, "var": 0.25, "var_scale": 12, "spec": 0.7},
    "blood_dry": {"color": [0.22, 0.05, 0.035], "rough": 0.5, "var": 0.3, "var_scale": 10},
    "growth": {"color": [0.22, 0.24, 0.19], "rough": 0.35, "var": 0.35, "var_scale": 9, "bump": 0.6,
               "bump_scale": 25, "stains": 0.4, "stain_color": [0.3, 0.17, 0.18], "spec": 0.7},
    "growth_glow": {"color": [0.28, 0.42, 0.36], "rough": 0.3, "var": 0.3, "var_scale": 14,
                    "emit": [0.35, 1.0, 0.8], "emit_strength": 0.6},
    "flesh": {"color": [0.55, 0.32, 0.3], "rough": 0.3, "var": 0.3, "var_scale": 8, "bump": 0.4, "spec": 0.7,
              "stains": 0.5, "stain_color": [0.3, 0.05, 0.06]},
    "concrete": {"color": [0.55, 0.54, 0.51], "rough": 0.85, "bump": 0.25, "bump_scale": 60, "stains": 0.35,
                 "stain_color": [0.38, 0.36, 0.32]},
    "plaster": {"color": [0.80, 0.78, 0.71], "rough": 0.85, "var": 0.06, "stains": 0.45,
                "stain_color": [0.55, 0.5, 0.4], "stain_scale": 1.6, "bump": 0.08, "bump_scale": 30},
    "dado_green": {"color": [0.30, 0.43, 0.36], "rough": 0.35, "var": 0.06, "stains": 0.3,
                   "stain_color": [0.22, 0.25, 0.2], "grime": 0.25, "grime_h": 0.4},
    "dado_blue": {"color": [0.28, 0.38, 0.5], "rough": 0.35, "var": 0.06, "stains": 0.3,
                  "stain_color": [0.2, 0.22, 0.25], "grime": 0.25, "grime_h": 0.4},
    "brick": {"color": [0.55, 0.24, 0.16], "rough": 0.85,
              "pattern": {"type": "tiles", "size": 0.08, "offset": 0.5, "color2": [0.48, 0.2, 0.13],
                          "mortar": 0.08, "mortar_color": [0.62, 0.58, 0.52]}},
    "terrazzo": {"color": [0.6, 0.58, 0.53], "rough": 0.35, "var": 0.06, "stains": 0.3,
                 "stain_color": [0.42, 0.4, 0.36],
                 "pattern": {"type": "terrazzo", "scale": 80, "density": 0.16,
                             "chips": [[0.3, 0.3, 0.3], [0.85, 0.84, 0.8], [0.5, 0.36, 0.28], [0.65, 0.63, 0.6]]}},
    "tile_floor": {"color": [0.74, 0.72, 0.66], "rough": 0.3, "var": 0.05, "stains": 0.35,
                   "stain_color": [0.5, 0.46, 0.38],
                   "pattern": {"type": "tiles", "size": 0.6, "color2": [0.7, 0.68, 0.62], "mortar": 0.012,
                               "mortar_color": [0.42, 0.4, 0.36]}},
    "court_wood": {"color": [0.74, 0.52, 0.31], "rough": 0.3, "var": 0.08, "stains": 0.25,
                   "stain_color": [0.5, 0.33, 0.2],
                   "pattern": {"type": "planks", "w": 0.09, "l": 2.4, "color2": [0.68, 0.46, 0.27],
                               "mortar": 0.012, "mortar_color": [0.4, 0.28, 0.17], "axis": "y"}},
    "court_line": {"color": [0.92, 0.9, 0.84], "rough": 0.3},
    "court_line_red": {"color": [0.65, 0.12, 0.1], "rough": 0.3},
    "court_paint": {"color": [0.55, 0.22, 0.16], "rough": 0.3, "var": 0.06},
    "rug_green": {"color": [0.12, 0.3, 0.2], "rough": 0.95, "bump": 0.15, "bump_scale": 300},
    "soil": {"color": [0.3, 0.24, 0.17], "rough": 0.95, "bump": 0.4},
    "bag_black": {"color": [0.09, 0.09, 0.1], "rough": 0.7, "bump": 0.1, "bump_scale": 150},
    "orange": {"color": [0.85, 0.42, 0.1], "rough": 0.5},
    "yellow": {"color": [0.9, 0.72, 0.15], "rough": 0.45},
    "brass": {"color": [0.75, 0.58, 0.28], "rough": 0.3, "metal": 1.0},
    "skin_pale": {"color": [0.62, 0.58, 0.52], "rough": 0.5},
    "black_paint": {"color": [0.08, 0.08, 0.085], "rough": 0.4},
    "red_paint": {"color": [0.6, 0.1, 0.08], "rough": 0.4},
}


def mats(*names):
    return {n: MATS[n] for n in names}


def mats_for(objects):
    """Only the library materials the objects' parts use."""
    used = set()

    def walk(parts):
        for p in parts:
            if "part" in p:
                walk([p["part"]])
            elif "mat" in p:
                used.add(p["mat"])
    for spec in objects.values():
        walk(spec["parts"])
    return {n: MATS[n] for n in sorted(used)}


# --- Part builders ------------------------------------------------------------------------------------------------

def box(x0, x1, y0, y1, z0, z1, mat, **kw):
    d = {"box": [round(x0, 4), round(x1, 4), round(y0, 4), round(y1, 4), round(z0, 4), round(z1, 4)], "mat": mat}
    d.update(kw)
    return d


def cbox(cx, cy, w, d, z0, z1, mat, **kw):
    """Box by centre and size."""
    return box(cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, z0, z1, mat, **kw)


def cyl(a, b, r, mat, r2=None, sides=16, **kw):
    c = {"a": [round(v, 4) for v in a], "b": [round(v, 4) for v in b], "r": r, "sides": sides}
    if r2 is not None:
        c["r2"] = r2
    d = {"cyl": c, "mat": mat}
    d.update(kw)
    return d


def leg(x, y, z0, z1, r, mat, sides=10):
    return cyl([x, y, z0], [x, y, z1], r, mat, sides=sides)


def tube(points, r, mat, sides=8, **kw):
    d = {"tube": [[round(v, 4) for v in p] for p in points], "r": r, "mat": mat, "sides": sides}
    d.update(kw)
    return d


def blob(x, y, z, sx, sy, sz, mat, lump=0.25, seed=1, subdiv=3, floor=0.0, **kw):
    d = {"blob": [x, y, z], "size": [sx, sy, sz], "lump": lump, "seed": seed, "subdiv": subdiv, "floor": floor,
         "mat": mat}
    d.update(kw)
    return d


def prism(points, span, mat, axis="y", **kw):
    d = {"prism": [[round(u, 4), round(v, 4)] for u, v in points], "span": [round(span[0], 4), round(span[1], 4)],
         "axis": axis, "mat": mat}
    d.update(kw)
    return d


def pointed_arch(cx, width, z0, spring, peak, steps=8):
    """Outline (XZ, counter-clockwise) of a pointed (two-centred) arch opening: sides from z0 to `spring`, then two
    arcs meeting at `peak`."""
    hw = width / 2.0
    rise = peak - spring
    # Two-centred arch: each arc centred on the opposite springing line, radius r with r^2 = (r - hw)^2 + rise^2.
    r = (hw * hw + rise * rise) / (2.0 * hw) if hw > 0 else rise
    pts = [(cx - hw, z0), (cx + hw, z0), (cx + hw, spring)]
    for k in range(1, steps + 1):          # right arc, centre at (cx + hw - r, spring)
        a = math.asin(min(1.0, rise * k / steps / r))
        pts.append((cx + hw - r + r * math.cos(a), spring + r * math.sin(a)))
    pts[-1] = (cx, peak)
    for k in range(steps - 1, 0, -1):      # left arc, mirror
        a = math.asin(min(1.0, rise * k / steps / r))
        pts.append((cx - hw + r - r * math.cos(a), spring + r * math.sin(a)))
    pts.append((cx - hw, spring))
    return pts


def half_disc(cx, z_top, radius, steps=24):
    """Lower half of a disc (XZ), flat side on top at z_top: the Mosque's great window."""
    pts = [(cx + radius, z_top)]
    for k in range(1, steps):
        a = math.pi * k / steps
        pts.append((cx + radius * math.cos(a), z_top - radius * math.sin(a)))
    pts.append((cx - radius, z_top))
    return pts


def text(s, at, size, mat, face="front", depth=0.004, align="CENTER"):
    return {"text": s, "at": list(at), "size": size, "mat": mat, "face": face, "depth": depth, "align": align}


def lathe(profile, at, mat, sides=24):
    return {"lathe": [list(p) for p in profile], "at": list(at), "mat": mat, "sides": sides}


def _with_xf(parts, xf):
    out = []
    for p in parts:
        q = json.loads(json.dumps(p))
        if "part" in q:
            q["part"] = _with_xf([q["part"]], xf)[0]
        else:
            q["xf"] = q.get("xf", []) + [xf]
        out.append(q)
    return out


def moved(parts, dx=0.0, dy=0.0, dz=0.0):
    """Copies of `parts` translated."""
    return _with_xf(parts, {"move": [round(dx, 4), round(dy, 4), round(dz, 4)]})


def rotated_z(parts, deg, pivot=(0.0, 0.0)):
    """Copies of `parts` turned about a vertical axis through `pivot`."""
    return _with_xf(parts, {"rot": [0, 0, deg], "pivot": [pivot[0], pivot[1], 0.0]})


def rotated(parts, rot, pivot=(0.0, 0.0, 0.0)):
    """Copies of `parts` turned by [rx, ry, rz] degrees about `pivot`."""
    return _with_xf(parts, {"rot": list(rot), "pivot": list(pivot)})


# --- Config writer ---------------------------------------------------------------------------------------------

def write_config(asset_id, category, scene_name, description, params, *, px_per_m=150.0, samples=192,
                 layers=None, collision=None, z_index=0, sprite_z_index=0, seed=20261121, crop_layers=None,
                 max_texture_px=None, width_px=None):
    cfg = {
        "asset_id": asset_id,
        "category": category,
        "generator": "assembly",
        "description": description + " GENERATED by assets/source/blender/tools/author_*.py: edit that, not this.",
        "seed": seed,
        "generator_params": params,
        "render": ({"px_per_m": px_per_m} if px_per_m else {"width_px": width_px}) | {
            "samples": samples, "elevation_deg": 40.0, "azimuth_deg": 0.0},
        "godot": {"scene_name": scene_name, "z_index": z_index, "sprite_offset_adjust_px": [0.0, 0.0],
                  "preview_scene": False},
        "collision": collision or {"enabled": False},
    }
    if sprite_z_index:
        cfg["godot"]["sprite_z_index"] = sprite_z_index
    if layers:
        cfg["layers"] = layers
        cfg["render"]["crop_layers"] = True if crop_layers is None else crop_layers
    if max_texture_px:
        cfg["render"]["max_texture_px"] = max_texture_px
    path = CONFIG_DIR / f"{asset_id}.json"
    text_out = json.dumps(cfg, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != text_out:
        path.write_text(text_out, encoding="utf-8")
        return True
    return False

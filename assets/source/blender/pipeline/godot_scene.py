"""Godot PackedScene writer for rendered sprites. Plain Python (no bpy, no Godot needed).

The generated prop scene is a pure function of the asset config and the render record:

    <SceneName> (Node2D)          origin = ground-footprint origin of the Blender model
    ├── Sprite (Sprite2D)         centered = false; offset puts the footprint origin pixel on (0, 0);
    │                             uniform scale = GAME_PX_PER_M / render px-per-metre
    └── Body (StaticBody2D)       optional collision stage (config "collision"), never derived from alpha
        └── Collision (CollisionShape2D, RectangleShape2D from the declared footprint)

Asset-specific adjustments (z_index, sprite_offset_adjust_px, collision rect, light mask)
live in the config, so regenerating never loses them. A scene changed by hand since the
last generation is not overwritten (use --force-scene after moving the edits into the config).
"""

import hashlib
import json
import re
import struct

from pipeline import assetconfig, conventions as C


class SceneError(Exception):
    pass


def fnum(v):
    """Shortest decimal that round-trips as float32, like Godot writes floats."""
    f32 = struct.unpack("f", struct.pack("f", float(v)))[0]
    for digits in range(1, 10):
        s = f"{f32:.{digits}g}"
        if struct.unpack("f", struct.pack("f", float(s)))[0] == f32:
            break
    if "e" in s:
        s = repr(f32)
    return s[:-2] if s.endswith(".0") else s


def vec2(x, y):
    return f"Vector2({fnum(x)}, {fnum(y)})"


def packed_vec2(points):
    return "PackedVector2Array(" + ", ".join(f"{fnum(x)}, {fnum(y)}" for x, y in points) + ")"


def gd_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------------------
# Geometry derived from the render record
# ---------------------------------------------------------------------------

def layout(cfg, record):
    """All Godot-side numbers for the asset, in texture px and game px."""
    proj = record["projection"]
    ppm = proj["px_per_m"]
    scale = C.GAME_PX_PER_M / ppm
    ox, oy = proj["origin_px"]
    adj_x, adj_y = cfg["godot"]["sprite_offset_adjust_px"]
    offset = (-ox + adj_x / scale, -oy + adj_y / scale)
    footprint_game = [((x - ox) * scale + adj_x, (y - oy) * scale + adj_y)
                      for x, y in proj["footprint_corners_px"]]
    w, h = proj["image_px"]
    return {
        "render_px_per_m": ppm,
        "game_px_per_m": C.GAME_PX_PER_M,
        "sprite_scale": scale,
        "sprite_offset_px": list(offset),
        "origin_px": [ox, oy],
        "sprite_rect_game_px": [offset[0] * scale, offset[1] * scale, w * scale, h * scale],
        "footprint_game_px": [list(p) for p in footprint_game],
        "ground_depth_factor": abs(proj["up"][1]),
    }


def collision_rect(cfg, record, lay):
    """Collision stage: (center, size) in game px from the declared footprint, or None."""
    col = cfg["collision"]
    if not col["enabled"]:
        return None
    if abs(cfg["render"]["azimuth_deg"]) > 1e-6:
        raise SceneError("Rectangle collision needs azimuth 0 (the footprint is a parallelogram otherwise)")
    if col["source"] == "rect_m":
        x0, x1, y0, y1 = col["rect_m"]
    else:
        fp = record["footprint_m"]
        x0, x1, y0, y1 = fp["x_min"], fp["x_max"], fp["y_min"], fp["y_max"]
    depth = lay["ground_depth_factor"] if col["depth_mode"] == "projected" else 1.0
    k = C.GAME_PX_PER_M
    # Blender -Y (front) is screen-down (+Y) in Godot.
    center = ((x0 + x1) / 2.0 * k, -(y0 + y1) / 2.0 * k * depth)
    size = ((x1 - x0) * k, (y1 - y0) * k * depth)
    return {"center": center, "size": size, "source": col["source"], "depth_mode": col["depth_mode"],
            "metres": [x0, x1, y0, y1], "layer": col["layer"], "mask": col["mask"]}


# ---------------------------------------------------------------------------
# Existing-scene handling
# ---------------------------------------------------------------------------

_HEADER_UID = re.compile(r'^\[gd_scene[^\]]*\buid="([^"]+)"', re.M)
_NODE_ID = re.compile(r'^\[node name="([^"]+)"([^\]]*?)\bunique_id=(\d+)', re.M)
_PARENT = re.compile(r'parent="([^"]*)"')


def existing_ids(text):
    uid = _HEADER_UID.search(text)
    nodes = {}
    for m in _NODE_ID.finditer(text):
        parent = _PARENT.search(m.group(2))
        nodes[(parent.group(1) if parent else "", m.group(1))] = m.group(3)
    return (uid.group(1) if uid else None), nodes


def semantic_hash(text):
    """Hash that ignores what Godot adds or reorders when it re-saves an unchanged scene."""
    sections, current = [], None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("["):
            line = re.sub(r'\s(uid="[^"]*"|unique_id=\d+|load_steps=\d+)', "", line)
            current = [line, []]
            sections.append(current)
        elif current is not None:
            key, _, value = line.partition(" = ")
            value = re.sub(r"-?\d+\.\d+(e-?\d+)?", lambda m: f"{float(m.group(0)):.3f}", value)
            current[1].append(f"{key}={value}")
    canon = sorted(h + "\n" + "\n".join(sorted(props)) for h, props in sections)
    return hashlib.sha256("\n".join(canon).encode()).hexdigest()


def check_writable(path, previous_hash, force):
    """Only overwrite scenes this pipeline generated and nobody edited since."""
    if assetconfig.rel(path) in assetconfig.PROTECTED:
        raise SceneError(f"{assetconfig.rel(path)} is protected")
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if f'metadata/generated_by = "{C.PIPELINE_MARKER}"' not in text:
        raise SceneError(f"{assetconfig.rel(path)} exists and was not generated by the pipeline; refusing to overwrite.")
    if previous_hash and semantic_hash(text) != previous_hash and not force:
        raise SceneError(f"{assetconfig.rel(path)} was edited after generation. Move the edits into the config "
                         f"(godot.* / collision.*) and re-run with --force-scene, or keep the scene as is.")


def texture_uid(png_path):
    imp = png_path.with_name(png_path.name + ".import")
    if imp.is_file():
        m = re.search(r'^uid="([^"]+)"', imp.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    return None


def ensure_texture_import(png_path):
    """First import uses mipmaps (the sprite is drawn at ~1/7 scale). Existing .import files are kept."""
    imp = png_path.with_name(png_path.name + ".import")
    if imp.exists():
        return False
    imp.write_text('[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\n\n'
                   '[params]\n\nmipmaps/generate=true\nprocess/fix_alpha_border=true\n', encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _node(name, type_, parent, ids, props, instance=None):
    key = ("" if parent is None else parent, name)
    head = f'[node name="{name}"'
    if type_:
        head += f' type="{type_}"'
    if parent is not None:
        head += f' parent="{parent}"'
    if instance:
        head += f" instance={instance}"
    if key in ids:
        head += f" unique_id={ids[key]}"
    lines = [head + "]"]
    lines += [f"{k} = {v}" for k, v in props]
    return "\n".join(lines) + "\n"


def build_prop_scene(cfg, record, existing_text=None):
    out = cfg["outputs"]
    lay = layout(cfg, record)
    col = collision_rect(cfg, record, lay)
    uid, ids = existing_ids(existing_text) if existing_text else (None, {})
    g = cfg["godot"]
    scene = g["scene_name"]

    header = "[gd_scene format=3" + (f' uid="{uid}"' if uid else "") + "]\n"
    tex_uid = texture_uid(out["png"])
    ext = (f'[ext_resource type="Texture2D"' + (f' uid="{tex_uid}"' if tex_uid else "")
           + f' path="{assetconfig.res_path(out["png"])}" id="1_sprite"]\n')
    parts = [header, ext]
    if col:
        parts.append('[sub_resource type="RectangleShape2D" id="RectangleShape2D_footprint"]\n'
                     f'size = {vec2(*col["size"])}\n')

    desc = (f"GENERATED by the asset pipeline from {cfg['_config_path']} "
            f"({record['outputs']['record']}). Don't edit by hand: change the config and re-run "
            f"assets/source/blender/build_asset.py. Origin = ground-footprint origin of the Blender model. "
            f"Sprite scale = {C.GAME_PX_PER_M:g} game px/m / {lay['render_px_per_m']:.2f} render px/m.")
    root_props = [("editor_description", gd_string(desc))]
    if g["z_index"]:
        root_props.append(("z_index", str(g["z_index"])))
    root_props += [("metadata/asset_id", gd_string(cfg["asset_id"])),
                   ("metadata/generated_by", gd_string(C.PIPELINE_MARKER))]
    parts.append(_node(scene, "Node2D", None, ids, root_props))

    sprite_props = []
    if g["light_mask"] != 1:
        sprite_props.append(("light_mask", str(g["light_mask"])))
    sprite_props += [
        ("texture_filter", str(g["texture_filter"])),
        ("scale", vec2(lay["sprite_scale"], lay["sprite_scale"])),
        ("texture", 'ExtResource("1_sprite")'),
        ("centered", "false"),
        ("offset", vec2(*lay["sprite_offset_px"])),
    ]
    parts.append(_node("Sprite", "Sprite2D", ".", ids, sprite_props))

    if col:
        body_props = []
        if col["layer"] != 1:
            body_props.append(("collision_layer", str(col["layer"])))
        if col["mask"] != 1:
            body_props.append(("collision_mask", str(col["mask"])))
        parts.append(_node("Body", "StaticBody2D", ".", ids, body_props))
        shape_props = []
        if any(abs(c) > 1e-9 for c in col["center"]):
            shape_props.append(("position", vec2(*col["center"])))
        shape_props.append(("shape", 'SubResource("RectangleShape2D_footprint")'))
        parts.append(_node("Collision", "CollisionShape2D", "Body", ids, shape_props))
    return "\n".join(parts), lay, col


def build_preview_scene(cfg, record, lay, existing_text=None):
    out = cfg["outputs"]
    uid, ids = existing_ids(existing_text) if existing_text else (None, {})
    name = cfg["godot"]["scene_name"] + "Preview"
    fp = lay["footprint_game_px"]
    xs = [p[0] for p in fp]
    rx, ry, rw, rh = lay["sprite_rect_game_px"]
    width = max(xs) - min(xs)
    tile = cfg["godot"]["preview_tile_x"]

    header = "[gd_scene format=3" + (f' uid="{uid}"' if uid else "") + "]\n"
    ext = f'[ext_resource type="PackedScene" path="{assetconfig.res_path(out["scene"])}" id="1_asset"]\n'
    parts = [header, ext]
    parts.append(_node(name, "Node2D", None, ids, [
        ("editor_description", gd_string(
            f"GENERATED TEST PREVIEW for {cfg['asset_id']} (not part of the game; regenerated by the asset pipeline). "
            "Blue = 32x64 player-sized reference with feet at its origin. Red = declared ground footprint "
            "projected through the render camera, in game px. Yellow dot = asset origin. Camera zoom 4 for inspection.")),
        ("y_sort_enabled", "true"),
        ("metadata/generated_by", gd_string(C.PIPELINE_MARKER)),
    ]))
    pad = 64.0
    parts.append(_node("Ground", "Polygon2D", ".", ids, [
        ("z_index", "-10"),
        ("color", "Color(0.42, 0.42, 0.39, 1)"),
        ("polygon", packed_vec2([(rx - pad, ry - pad), (rx + rw * (2 if tile else 1) + pad, ry - pad),
                                 (rx + rw * (2 if tile else 1) + pad, ry + rh + pad), (rx - pad, ry + rh + pad)])),
    ]))
    parts.append(_node("Asset", None, ".", ids, [], instance='ExtResource("1_asset")'))
    if tile:
        parts.append(_node("AssetTiledNeighbour", None, ".", ids, [("position", vec2(width, 0))],
                           instance='ExtResource("1_asset")'))
    parts.append(_node("ScaleReference", "Polygon2D", ".", ids, [
        ("position", vec2(min(xs) - 24.0, 0)),
        ("color", "Color(0.2, 0.35, 0.8, 1)"),
        ("polygon", packed_vec2([(-16, -64), (16, -64), (16, 0), (-16, 0)])),
    ]))
    parts.append(_node("FootprintGuide", "Line2D", ".", ids, [
        ("points", packed_vec2(fp)),
        ("closed", "true"),
        ("width", "0.5"),
        ("default_color", "Color(1, 0.2, 0.2, 0.9)"),
    ]))
    parts.append(_node("OriginMarker", "Polygon2D", ".", ids, [
        ("color", "Color(1, 0.9, 0.1, 1)"),
        ("polygon", packed_vec2([(0, -1), (1, 0), (0, 1), (-1, 0)])),
    ]))
    cam_x = (width / 2.0) if tile else 0.0
    parts.append(_node("Camera", "Camera2D", ".", ids, [
        ("position", vec2(cam_x, ry + rh / 2.0)),
        ("zoom", vec2(4, 4)),
    ]))
    return "\n".join(parts)


def write_scene(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return semantic_hash(text)


def record_summary(lay, col):
    return json.loads(json.dumps({"layout": lay, "collision": col}))

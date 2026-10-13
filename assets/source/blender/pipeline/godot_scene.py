"""Godot PackedScene writer for rendered sprites. Plain Python (no bpy, no Godot needed).

The generated prop scene is a pure function of the asset config and the render record:

    <SceneName> (Node2D)          origin = ground-footprint origin of the Blender model
    ├── Sprite (Sprite2D)         centered = false; offset puts the footprint origin pixel on (0, 0);
    │                             uniform scale = GAME_PX_PER_M / render px-per-metre
    ├── <Layer> (Sprite2D)        one per config layer, same pixels-to-origin mapping; positioned on its
    │                             Y-sort point (the root is then y_sort_enabled), optional z_index
    ├── <Layer>Fade (Area2D)      OverheadVisibility: fades <Layer> while the player stands in its rects
    │   └── Shape<Name> (CollisionShape2D)
    └── Body (StaticBody2D)       optional collision stage (config "collision"), never derived from alpha
        └── Collision (CollisionShape2D, RectangleShape2D from the declared footprint;
                       or one Collision<Name> per rectangle of collision.rects_m)

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
    depth = abs(proj["up"][1])
    layers = []
    for layer in cfg.get("layers", []):
        # Ground y (metres, +Y = back) -> game px (screen-down); the offset compensates the position.
        sort_y = -layer["sort_y_m"] * C.GAME_PX_PER_M * depth
        fade = None
        if layer["fade"]:
            fade = {"node": layer["name"] + "Fade", "alpha": layer["fade"]["alpha"],
                    "seconds": layer["fade"]["seconds"],
                    "shapes": [_ground_rect(f"Shape{n}", f"RectangleShape2D_{layer['name']}Fade{n}", r, depth)
                               for n, r in layer["fade"]["rects_m"].items()]}
        layers.append({
            "name": layer["name"],
            "position_game_px": [0.0, sort_y],
            "sprite_offset_px": [offset[0], offset[1] - sort_y / scale],
            "z_index": layer["z_index"],
            "fade": fade,
        })
    return {
        "render_px_per_m": ppm,
        "game_px_per_m": C.GAME_PX_PER_M,
        "sprite_scale": scale,
        "sprite_offset_px": list(offset),
        "origin_px": [ox, oy],
        "sprite_rect_game_px": [offset[0] * scale, offset[1] * scale, w * scale, h * scale],
        "footprint_game_px": [list(p) for p in footprint_game],
        "ground_depth_factor": depth,
        "layers": layers or None,
    }


def _ground_rect(node, res_id, rect_m, depth):
    """Ground rectangle [x_min, x_max, y_min, y_max] in metres -> projected game px (Blender -Y = screen-down)."""
    x0, x1, y0, y1 = rect_m
    k = C.GAME_PX_PER_M
    return {"node": node, "resource_id": res_id,
            "center": ((x0 + x1) / 2.0 * k, -(y0 + y1) / 2.0 * k * depth),
            "size": ((x1 - x0) * k, (y1 - y0) * k * depth),
            "metres": [x0, x1, y0, y1]}


def collision_rect(cfg, record, lay):
    """Collision stage: rectangles in game px from the declared footprint or config, or None.

    One rectangle -> node `Collision`; `rects_m` -> one `Collision<Name>` node per named
    rectangle (e.g. the two jambs of a doorway, leaving the opening free)."""
    col = cfg["collision"]
    if not col["enabled"]:
        return None
    if abs(cfg["render"]["azimuth_deg"]) > 1e-6:
        raise SceneError("Rectangle collision needs azimuth 0 (the footprint is a parallelogram otherwise)")
    if col["source"] == "rects_m":
        rects = [(f"Collision{name}", f"RectangleShape2D_{name}", r) for name, r in col["rects_m"].items()]
    elif col["source"] == "rect_m":
        rects = [("Collision", "RectangleShape2D_footprint", col["rect_m"])]
    else:
        fp = record["footprint_m"]
        rects = [("Collision", "RectangleShape2D_footprint", [fp["x_min"], fp["x_max"], fp["y_min"], fp["y_max"]])]
    depth = lay["ground_depth_factor"] if col["depth_mode"] == "projected" else 1.0
    k = C.GAME_PX_PER_M
    shapes = []
    for node, res_id, (x0, x1, y0, y1) in rects:
        # Blender -Y (front) is screen-down (+Y) in Godot.
        shapes.append({"node": node, "resource_id": res_id,
                       "center": ((x0 + x1) / 2.0 * k, -(y0 + y1) / 2.0 * k * depth),
                       "size": ((x1 - x0) * k, (y1 - y0) * k * depth),
                       "metres": [x0, x1, y0, y1]})
    result = {"source": col["source"], "depth_mode": col["depth_mode"],
              "layer": col["layer"], "mask": col["mask"], "shapes": shapes}
    if len(shapes) == 1:
        result.update(center=shapes[0]["center"], size=shapes[0]["size"], metres=shapes[0]["metres"])
    return result


# ---------------------------------------------------------------------------
# Existing-scene handling
# ---------------------------------------------------------------------------

_HEADER_UID = re.compile(r'^\[gd_(?:scene|resource)[^\]]*\buid="([^"]+)"', re.M)
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


def ensure_texture_import(png_path, mipmaps=True):
    """First import settings. Sprites use mipmaps (drawn at ~1/7 scale); ground tiles are drawn 1:1
    by a TileMapLayer and don't. Existing .import files are kept."""
    imp = png_path.with_name(png_path.name + ".import")
    if imp.exists():
        return False
    imp.write_text('[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\n\n'
                   f'[params]\n\nmipmaps/generate={"true" if mipmaps else "false"}\n'
                   'process/fix_alpha_border=true\n', encoding="utf-8")
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
    layers = lay["layers"] or []
    layer_pngs = cfg.get("layer_outputs", {})
    for i, layer in enumerate(layers):
        png = layer_pngs[layer["name"]]
        uid_l = texture_uid(png)
        ext += (f'[ext_resource type="Texture2D"' + (f' uid="{uid_l}"' if uid_l else "")
                + f' path="{assetconfig.res_path(png)}" id="{i + 2}_{layer["name"]}"]\n')
    if any(layer["fade"] for layer in layers):
        ext += f'[ext_resource type="Script" path="{C.OVERHEAD_FADE_SCRIPT}" id="overhead_visibility"]\n'
    parts = [header, ext]
    if col:
        for shape in col["shapes"]:
            parts.append(f'[sub_resource type="RectangleShape2D" id="{shape["resource_id"]}"]\n'
                         f'size = {vec2(*shape["size"])}\n')
    for layer in layers:
        for shape in (layer["fade"] or {}).get("shapes", []):
            parts.append(f'[sub_resource type="RectangleShape2D" id="{shape["resource_id"]}"]\n'
                         f'size = {vec2(*shape["size"])}\n')

    desc = (f"GENERATED by the asset pipeline from {cfg['_config_path']} "
            f"({record['outputs']['record']}). Don't edit by hand: change the config and re-run "
            f"assets/source/blender/build_asset.py. Origin = ground-footprint origin of the Blender model. "
            f"Sprite scale = {C.GAME_PX_PER_M:g} game px/m / {lay['render_px_per_m']:.2f} render px/m.")
    if layers:
        desc += (" Layers (" + ", ".join(l["name"] for l in layers) + ") are separate renders from the same camera"
                 "; a <Layer>Fade area (OverheadVisibility) fades its layer while the player stands under it.")
    root_props = [("editor_description", gd_string(desc))]
    if g["z_index"]:
        root_props.append(("z_index", str(g["z_index"])))
    if any(abs(l["position_game_px"][1]) > 1e-9 for l in layers):
        root_props.append(("y_sort_enabled", "true"))
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

    for i, layer in enumerate(layers):
        props = []
        if layer["z_index"]:
            props.append(("z_index", str(layer["z_index"])))
        if g["light_mask"] != 1:
            props.append(("light_mask", str(g["light_mask"])))
        if abs(layer["position_game_px"][1]) > 1e-9:
            props.append(("position", vec2(*layer["position_game_px"])))
        props += [
            ("texture_filter", str(g["texture_filter"])),
            ("scale", vec2(lay["sprite_scale"], lay["sprite_scale"])),
            ("texture", f'ExtResource("{i + 2}_{layer["name"]}")'),
            ("centered", "false"),
            ("offset", vec2(*layer["sprite_offset_px"])),
        ]
        parts.append(_node(layer["name"], "Sprite2D", ".", ids, props))
    for layer in layers:
        fade = layer["fade"]
        if not fade:
            continue
        parts.append(_node(fade["node"], "Area2D", ".", ids, [
            ("collision_layer", "0"),
            ("collision_mask", str(1 << (C.PLAYER_COLLISION_LAYER - 1))),
            ("monitorable", "false"),
            ("script", 'ExtResource("overhead_visibility")'),
            ("target_paths", f'Array[NodePath]([NodePath("../{layer["name"]}")])'),
            ("faded_alpha", fnum(fade["alpha"])),
            ("fade_seconds", fnum(fade["seconds"])),
        ]))
        for shape in fade["shapes"]:
            parts.append(_node(shape["node"], "CollisionShape2D", fade["node"], ids, [
                ("position", vec2(*shape["center"])),
                ("shape", f'SubResource("{shape["resource_id"]}")'),
            ]))

    if col:
        body_props = []
        if col["layer"] != 1:
            body_props.append(("collision_layer", str(col["layer"])))
        if col["mask"] != 1:
            body_props.append(("collision_mask", str(col["mask"])))
        parts.append(_node("Body", "StaticBody2D", ".", ids, body_props))
        for shape in col["shapes"]:
            shape_props = []
            if any(abs(c) > 1e-9 for c in shape["center"]):
                shape_props.append(("position", vec2(*shape["center"])))
            shape_props.append(("shape", f'SubResource("{shape["resource_id"]}")'))
            parts.append(_node(shape["node"], "CollisionShape2D", "Body", ids, shape_props))
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


# ---------------------------------------------------------------------------
# Ground tiles: shared TileSet + TileMapLayer preview
# ---------------------------------------------------------------------------

def vec2i(x, y):
    return f"Vector2i({int(x)}, {int(y)})"


def tile_map_data(cells):
    """TileMapLayer.tile_map_data for [(x, y, source_id), ...], atlas tile (0, 0), alternative 0.

    Godot's format 0: uint16 format version, then 12 bytes per cell (little endian):
    int16 x, int16 y, uint16 source_id, uint16 atlas x, uint16 atlas y, uint16 alternative.
    """
    data = struct.pack("<H", 0)
    for x, y, source in cells:
        data += struct.pack("<hhHHHH", x, y, source, 0, 0, 0)
    return "PackedByteArray(" + ", ".join(str(b) for b in data) + ")"


def build_tileset(tileset_name, members, tile_px, existing_text=None):
    """One TileSetAtlasSource (a single 1x1 tile) per ground-tile config whose PNG exists."""
    uid, _ = existing_ids(existing_text) if existing_text else (None, {})
    header = "[gd_resource type=\"TileSet\" format=3" + (f' uid="{uid}"' if uid else "") + "]\n"
    parts, sources, included = [header], [], []
    for cfg in members:
        png = cfg["outputs"]["png"]
        if not png.is_file():
            continue
        aid, sid = cfg["asset_id"], cfg["ground"]["source_id"]
        tex_uid = texture_uid(png)
        parts.append(f'[ext_resource type="Texture2D"' + (f' uid="{tex_uid}"' if tex_uid else "")
                     + f' path="{assetconfig.res_path(png)}" id="{sid}_{aid}"]\n')
        sources.append((sid, aid))
        included.append({"source_id": sid, "asset_id": aid, "png": assetconfig.rel(png)})
    for sid, aid in sources:
        parts.append(f'[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_{aid}"]\n'
                     f'resource_name = "{aid}"\n'
                     f'texture = ExtResource("{sid}_{aid}")\n'
                     f'texture_region_size = {vec2i(tile_px, tile_px)}\n'
                     '0:0/0 = 0\n')
    desc = (f"GENERATED by the asset pipeline (assets/source/blender/build_asset.py) from every ground_tile "
            f"config with ground.tileset = \"{tileset_name}\". Don't edit by hand. Source id = ground.source_id; "
            f"each source is one seamless {tile_px} x {tile_px} px tile (2 m at 32 px/m, top-down). No physics.")
    res = ["[resource]", f"resource_name = {gd_string(tileset_name)}", f"tile_size = {vec2i(tile_px, tile_px)}"]
    res += [f'sources/{sid} = SubResource("TileSetAtlasSource_{aid}")' for sid, aid in sources]
    res += [f"metadata/editor_description = {gd_string(desc)}",
            f"metadata/generated_by = {gd_string(C.PIPELINE_MARKER)}"]
    parts.append("\n".join(res) + "\n")
    return "\n".join(parts), included


def ground_preview_cells(cfg, reference_source=None):
    """6 x 4 cells of the tile; a variant with a border-match reference is laid out in a
    checkerboard with it, so the preview shows the two tiles mixing."""
    sid = cfg["ground"]["source_id"]
    cells = []
    for y in range(-2, 2):
        for x in range(-3, 3):
            use_ref = reference_source is not None and (x + y) % 2 != 0
            cells.append((x, y, reference_source if use_ref else sid))
    return cells


def build_ground_preview_scene(cfg, cells, tile_px, existing_text=None):
    out = cfg["outputs"]
    uid, ids = existing_ids(existing_text) if existing_text else (None, {})
    name = cfg["godot"]["scene_name"] + "Preview"
    header = "[gd_scene format=3" + (f' uid="{uid}"' if uid else "") + "]\n"
    ext = f'[ext_resource type="TileSet" path="{assetconfig.res_path(out["scene"])}" id="1_tileset"]\n'
    parts = [header, ext]
    parts.append(_node(name, "Node2D", None, ids, [
        ("editor_description", gd_string(
            f"GENERATED TEST PREVIEW for the ground tile {cfg['asset_id']} (not part of the game; regenerated by "
            "the asset pipeline). A 6 x 4 TileMapLayer of the tile (checkerboard with its border-match base tile "
            "if it has one) for checking seams and repetition. Blue = 32x64 player-sized reference. Camera zoom 2.")),
        ("metadata/generated_by", gd_string(C.PIPELINE_MARKER)),
    ]))
    parts.append(_node("Tiles", "TileMapLayer", ".", ids, [
        ("z_index", "-10"),
        ("tile_map_data", tile_map_data(cells)),
        ("tile_set", 'ExtResource("1_tileset")'),
    ]))
    parts.append(_node("ScaleReference", "Polygon2D", ".", ids, [
        ("position", vec2(tile_px / 2.0, tile_px / 2.0)),
        ("color", "Color(0.2, 0.35, 0.8, 0.8)"),
        ("polygon", packed_vec2([(-16, -64), (16, -64), (16, 0), (-16, 0)])),
    ]))
    parts.append(_node("Camera", "Camera2D", ".", ids, [("zoom", vec2(2, 2))]))
    return "\n".join(parts)


def write_scene(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return semantic_hash(text)


def record_summary(lay, col):
    return json.loads(json.dumps({"layout": lay, "collision": col}))

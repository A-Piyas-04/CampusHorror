"""Asset config loading and output naming. Plain Python (no bpy).

One JSON file per asset in assets/source/blender/configs/<asset_id>.json. All output
paths are derived from `asset_id`, `category` and `godot.scene_name`; configs never
contain output paths, so naming stays predictable.
"""

import json
import re

from pipeline import conventions as C

ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SCENE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")

# Hand-made files that the pipeline must never write, whatever a config says.
PROTECTED = {
    "assets/source/blender/campus_asset_workshop.blend",
    "assets/source/blender/red_brick_wall_test.blend",
    "assets/source/blender/red_brick_wall_test.render.json",
    "assets/source/blender/red_brick_wall_angle_test.render.json",
    "assets/source/blender/red_brick_wall_grid_test.render.json",
    "assets/sprites/architecture/red_brick_wall_test.png",
    "assets/sprites/architecture/red_brick_wall_angle_test.png",
    "assets/sprites/architecture/red_brick_wall_grid_test.png",
    "scenes/tests/WallAssetPreview.tscn",
    "scenes/core/Main.tscn",
}


class ConfigError(Exception):
    pass


def rel(path):
    return path.resolve().relative_to(C.PROJECT_ROOT).as_posix()


def res_path(path):
    return "res://" + rel(path)


def load(asset_id_or_path):
    path = C.PROJECT_ROOT / asset_id_or_path if asset_id_or_path.endswith(".json") \
        else C.CONFIG_DIR / f"{asset_id_or_path}.json"
    if not path.is_file():
        raise ConfigError(f"Config not found: {path}")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["_config_path"] = rel(path)

    for key in ("asset_id", "category", "generator"):
        if not isinstance(cfg.get(key), str) or not ID_RE.match(cfg[key]):
            raise ConfigError(f"{key!r} must be snake_case (got {cfg.get(key)!r})")
    if path.stem != cfg["asset_id"]:
        raise ConfigError(f"Config file name {path.name} must equal asset_id {cfg['asset_id']!r}")
    if not (C.GENERATOR_DIR / f"{cfg['generator']}.py").is_file():
        raise ConfigError(f"Generator not found: generators/{cfg['generator']}.py")

    cfg.setdefault("seed", 1)
    cfg.setdefault("generator_params", {})
    kind = cfg.setdefault("kind", "sprite")
    if kind not in ("sprite", "ground_tile"):
        raise ConfigError("kind must be 'sprite' or 'ground_tile'")
    ground = kind == "ground_tile"
    render = cfg.setdefault("render", {})
    render.setdefault("width_px", C.RENDER_WIDTH_PX)
    render.setdefault("samples", C.SAMPLES)
    render.setdefault("elevation_deg", C.GROUND_ELEVATION_DEG if ground else C.CAMERA_ELEVATION_DEG)
    render.setdefault("azimuth_deg", C.CAMERA_AZIMUTH_DEG)
    if ground:
        render.setdefault("tile_px", C.GROUND_TILE_PX)
        render.setdefault("overscan_px", C.GROUND_OVERSCAN_PX)
        if render["elevation_deg"] != C.GROUND_ELEVATION_DEG or render["azimuth_deg"] != 0:
            raise ConfigError("ground tiles are rendered straight down (elevation 90, azimuth 0)")
        g = cfg.get("ground")
        if not isinstance(g, dict) or not isinstance(g.get("tileset"), str) or not ID_RE.match(g["tileset"]):
            raise ConfigError("ground_tile configs need ground.tileset (snake_case TileSet name)")
        if not isinstance(g.get("source_id"), int) or g["source_id"] < 0:
            raise ConfigError("ground.source_id must be a non-negative integer (TileSet atlas source id)")
        g.setdefault("period_m", C.GROUND_TILE_PERIOD_M)
        g.setdefault("border_match", None)
    render.setdefault("tile_bleed_px", C.TILE_BLEED_PX)
    ppm = render.get("px_per_m")
    if ppm is not None and not (isinstance(ppm, (int, float)) and ppm > 0):
        raise ConfigError("render.px_per_m must be a positive number (fixed render scale; omit to use width_px)")

    godot = cfg.setdefault("godot", {})
    if not isinstance(godot.get("scene_name"), str) or not SCENE_RE.match(godot["scene_name"]):
        raise ConfigError("godot.scene_name must be PascalCase (Docs/CONVENTIONS.md §5)")
    godot.setdefault("z_index", 0)
    godot.setdefault("light_mask", C.UPRIGHT_LIGHT_MASK)
    godot.setdefault("texture_filter", C.SPRITE_TEXTURE_FILTER)
    godot.setdefault("sprite_offset_adjust_px", [0.0, 0.0])
    godot.setdefault("preview_scene", True)
    godot.setdefault("preview_tile_x", False)

    col = cfg.setdefault("collision", {})
    col.setdefault("enabled", False)
    if ground and col["enabled"]:
        raise ConfigError("ground tiles have no collision (add physics to the TileSet by hand if a surface ever needs it)")
    col.setdefault("source", "design_footprint")
    col.setdefault("depth_mode", "projected")
    col.setdefault("layer", C.WORLD_COLLISION_LAYER)
    col.setdefault("mask", 0)
    if col["source"] not in ("design_footprint", "rect_m", "rects_m"):
        raise ConfigError("collision.source must be 'design_footprint', 'rect_m' or 'rects_m'")
    if col["source"] == "rect_m" and len(col.get("rect_m", [])) != 4:
        raise ConfigError("collision.rect_m must be [x_min, x_max, y_min, y_max] in metres")
    if col["source"] == "rects_m":
        rects = col.get("rects_m")
        if not isinstance(rects, dict) or not rects or any(
                not SCENE_RE.match(n) or len(r) != 4 for n, r in rects.items()):
            raise ConfigError("collision.rects_m must map PascalCase names to [x_min, x_max, y_min, y_max] in metres")
    if col["depth_mode"] not in ("projected", "top_down"):
        raise ConfigError("collision.depth_mode must be 'projected' or 'top_down'")

    cfg["layers"] = _load_layers(cfg, ground)

    cfg["outputs"] = outputs(cfg)
    cfg["layer_outputs"] = layer_outputs(cfg)
    for key, p in list(cfg["outputs"].items()) + list(cfg["layer_outputs"].items()):
        if rel(p) in PROTECTED:
            raise ConfigError(f"Output {key} would overwrite protected file {rel(p)}")
    return cfg


def _load_layers(cfg, ground):
    """Optional extra sprites rendered from the same camera (e.g. a roof that fades over the player).

    Each layer: {"name": PascalCase, "objects": [generator object names], "sort_y_m": ground y in
    metres of its Y-sort point (default 0 = the asset origin), "z_index": int (default 0),
    "fade": optional {"rects_m": {Name: [x_min, x_max, y_min, y_max]}, "alpha": 0.35, "seconds": 0.25}}.
    Objects not listed in any layer form the base `Sprite`."""
    layers = cfg.get("layers", [])
    if not layers:
        return []
    if ground:
        raise ConfigError("ground tiles have no layers")
    if not isinstance(layers, list):
        raise ConfigError("layers must be a list")
    names, objects = set(), set()
    for layer in layers:
        name = layer.get("name")
        if not isinstance(name, str) or not SCENE_RE.match(name) or name in names or name in RESERVED_NODE_NAMES:
            raise ConfigError(f"layer name {name!r} must be unique PascalCase and not one of {sorted(RESERVED_NODE_NAMES)}")
        names.add(name)
        objs = layer.get("objects")
        if not isinstance(objs, list) or not objs or not all(isinstance(o, str) for o in objs):
            raise ConfigError(f"layer {name}: objects must be a non-empty list of object names")
        if objects & set(objs):
            raise ConfigError(f"layer {name}: objects {sorted(objects & set(objs))} are already in another layer")
        objects |= set(objs)
        layer.setdefault("sort_y_m", 0.0)
        layer.setdefault("z_index", 0)
        if not isinstance(layer["sort_y_m"], (int, float)) or not isinstance(layer["z_index"], int):
            raise ConfigError(f"layer {name}: sort_y_m must be a number and z_index an integer")
        fade = layer.setdefault("fade", None)
        if fade is not None:
            rects = fade.get("rects_m")
            if not isinstance(rects, dict) or not rects or any(
                    not SCENE_RE.match(n) or len(r) != 4 or r[0] >= r[1] or r[2] >= r[3] for n, r in rects.items()):
                raise ConfigError(f"layer {name}: fade.rects_m must map PascalCase names to "
                                  "[x_min, x_max, y_min, y_max] in metres")
            fade.setdefault("alpha", C.OVERHEAD_FADED_ALPHA)
            fade.setdefault("seconds", C.OVERHEAD_FADE_SECONDS)
            if not 0.0 <= fade["alpha"] < 1.0 or fade["seconds"] < 0.0:
                raise ConfigError(f"layer {name}: fade.alpha must be in [0, 1) and fade.seconds >= 0")
    return layers


# Node names the generated prop scene already uses; a layer can't take them.
RESERVED_NODE_NAMES = {"Sprite", "Body"}


def layer_outputs(cfg):
    """Layer PNGs sit next to the base PNG: <asset_id>__<layer_snake>.png."""
    base = outputs(cfg)["png"]
    return {layer["name"]: base.with_name(f"{cfg['asset_id']}__{snake(layer['name'])}.png")
            for layer in cfg.get("layers", [])}


def snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def read_record(cfg):
    path = cfg["outputs"]["record"]
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def check_render_outputs_owned(cfg):
    """Refuse to overwrite a .blend/PNG that this pipeline did not produce for this asset."""
    record = read_record(cfg)
    owned = (record is not None and record.get("pipeline") == C.PIPELINE_MARKER
             and record.get("asset") == cfg["asset_id"])
    for p in [cfg["outputs"][key] for key in ("blend", "png", "record")] + list(cfg["layer_outputs"].values()):
        if p.exists() and not owned:
            raise ConfigError(f"{rel(p)} exists but was not produced by the pipeline for "
                              f"{cfg['asset_id']!r}; refusing to overwrite it.")


def outputs(cfg):
    """Ground tiles have no prop scene: their "scene" output is the shared TileSet they belong to."""
    aid, cat, scene = cfg["asset_id"], cfg["category"], cfg["godot"]["scene_name"]
    root = C.PROJECT_ROOT
    if cfg.get("kind") == "ground_tile":
        scene_path = root / C.GROUND_TILESET_DIR / f"{cfg['ground']['tileset']}.tres"
    else:
        scene_path = root / f"scenes/props/{cat}/{scene}.tscn"
    return {
        "blend": root / f"assets/source/blender/{cat}/{aid}.blend",
        "record": root / f"assets/source/blender/{cat}/{aid}.render.json",
        "png": root / f"assets/sprites/{cat}/{aid}.png",
        "scene": scene_path,
        "preview": root / f"scenes/tests/asset_previews/{scene}Preview.tscn",
    }


def tileset_members(tileset):
    """Every ground-tile config that belongs to `tileset`, sorted by source id."""
    members = []
    for path in sorted(C.CONFIG_DIR.glob("*.json")):
        cfg = load(path.stem)
        if cfg["kind"] == "ground_tile" and cfg["ground"]["tileset"] == tileset:
            members.append(cfg)
    ids = [c["ground"]["source_id"] for c in members]
    if len(ids) != len(set(ids)):
        raise ConfigError(f"duplicate ground.source_id in TileSet {tileset!r}: {ids}")
    return sorted(members, key=lambda c: c["ground"]["source_id"])

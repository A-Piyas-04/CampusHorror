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
    render = cfg.setdefault("render", {})
    render.setdefault("width_px", C.RENDER_WIDTH_PX)
    render.setdefault("samples", C.SAMPLES)
    render.setdefault("elevation_deg", C.CAMERA_ELEVATION_DEG)
    render.setdefault("azimuth_deg", C.CAMERA_AZIMUTH_DEG)
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

    cfg["outputs"] = outputs(cfg)
    for key, p in cfg["outputs"].items():
        if rel(p) in PROTECTED:
            raise ConfigError(f"Output {key} would overwrite protected file {rel(p)}")
    return cfg


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
    for key in ("blend", "png", "record"):
        p = cfg["outputs"][key]
        if p.exists() and not owned:
            raise ConfigError(f"{rel(p)} exists but was not produced by the pipeline for "
                              f"{cfg['asset_id']!r}; refusing to overwrite it.")


def outputs(cfg):
    aid, cat, scene = cfg["asset_id"], cfg["category"], cfg["godot"]["scene_name"]
    root = C.PROJECT_ROOT
    return {
        "blend": root / f"assets/source/blender/{cat}/{aid}.blend",
        "record": root / f"assets/source/blender/{cat}/{aid}.render.json",
        "png": root / f"assets/sprites/{cat}/{aid}.png",
        "scene": root / f"scenes/props/{cat}/{scene}.tscn",
        "preview": root / f"scenes/tests/asset_previews/{scene}Preview.tscn",
    }

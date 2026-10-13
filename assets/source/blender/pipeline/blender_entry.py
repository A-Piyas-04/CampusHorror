"""Blender side of the asset pipeline: model -> shared rig -> save .blend -> render PNG -> record.

Normally launched by build_asset.py. Direct invocation (from the project root):

    "F:\\bbbb\\blender.exe" --background --factory-startup --python-exit-code 1 ^
        --python assets/source/blender/pipeline/blender_entry.py -- --config red_brick_wall_3m [--cpu] [--samples N]

The generator module (generators/<name>.py) only builds geometry and materials. It must
define DEFAULT_PARAMS and build(collection, rng, params) returning a dict with:
    "bounds_points_m": points (metres) that must be framed, e.g. the bounding-box corners
    "footprint_m":     [x_min, x_max, y_min, y_max] ground footprint around the origin
    "objects":         the asset objects (for evaluated bounds in the record)
    "info":            asset-specific description copied into the record
    "tile_period_x_m": optional; the model repeats seamlessly along X with this period
                       (rendered between neighbour copies, bleed columns kept, rest cut)
"""

import importlib
import json
import math
import random
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from pipeline import assetconfig, conventions as C, pngcheck, rig  # noqa: E402

LOG = "[PIPELINE]"


def parse_args():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"config": None, "cpu": False, "samples": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--cpu":
            opts["cpu"] = True
        elif a == "--config":
            opts["config"] = args[i + 1]
            i += 1
        elif a == "--samples":
            opts["samples"] = int(args[i + 1])
            i += 1
        else:
            raise SystemExit(f"Unknown argument: {a}")
        i += 1
    if not opts["config"]:
        raise SystemExit("--config <asset_id> is required")
    return opts


def main():
    opts = parse_args()
    t0 = time.time()
    if bpy.data.filepath:
        raise SystemExit("Run with --factory-startup and no .blend loaded; the pipeline builds a fresh scene.")

    cfg = assetconfig.load(opts["config"])
    assetconfig.check_render_outputs_owned(cfg)
    out = cfg["outputs"]
    render_cfg = cfg["render"]
    samples = opts["samples"] or render_cfg["samples"]

    generator = importlib.import_module(f"generators.{cfg['generator']}")
    params = dict(generator.DEFAULT_PARAMS)
    unknown = set(cfg["generator_params"]) - set(params)
    if unknown:
        raise SystemExit(f"Unknown generator_params for {cfg['generator']}: {sorted(unknown)}")
    params.update(cfg["generator_params"])

    scene = rig.reset_scene(cfg["asset_id"])
    asset_coll = rig.new_collection(scene, getattr(generator, "COLLECTION_NAME", "Asset"))
    rig_coll = rig.new_collection(scene, "RenderRig")

    built = generator.build(asset_coll, random.Random(cfg["seed"]), params)
    bounds = [Vector(p) for p in built["bounds_points_m"]]

    # Horizontally tileable assets: neighbour copies one period to each side give the module
    # ends the shadows, occlusion and bounce of a continuous run, and supply the bleed columns.
    period = built.get("tile_period_x_m")
    if period:
        for obj in built["objects"]:
            for name, dx in (("TileWest", -period), ("TileEast", period)):
                dup = obj.copy()
                dup.name = f"{obj.name}_{name}"
                dup.location.x += dx
                asset_coll.objects.link(dup)

    lighting_info = rig.setup_lighting(scene, rig_coll, asset_coll)
    camera_info, projection = rig.setup_camera(
        scene, rig_coll, bounds, render_cfg["elevation_deg"], render_cfg["azimuth_deg"], render_cfg["width_px"])
    render_info = rig.setup_render(scene, samples, opts["cpu"])

    for p in (out["blend"], out["png"], out["record"]):
        p.parent.mkdir(parents=True, exist_ok=True)
    for stale in (out["blend"], out["blend"].with_suffix(".blend1")):
        if stale.exists():
            stale.unlink()
    # Relative path so the saved .blend re-renders to the same PNG from its own location.
    rel_png = Path(*[".."] * (len(out["blend"].parent.relative_to(C.PROJECT_ROOT).parts))) / assetconfig.rel(out["png"])
    scene.render.filepath = "//" + rel_png.as_posix()
    bpy.ops.wm.save_as_mainfile(filepath=str(out["blend"]), check_existing=False,
                                relative_remap=True, compress=True)
    print(f"{LOG} Saved source: {out['blend']}")

    t_render = time.time()
    bpy.ops.render.render(write_still=True)
    render_seconds = time.time() - t_render
    if not out["png"].exists():
        raise RuntimeError(f"Render finished but {out['png']} was not written.")
    print(f"{LOG} Rendered: {out['png']} in {render_seconds:.1f} s")

    x0, x1, y0, y1 = built["footprint_m"]
    tiling = None
    if period:
        bleed = render_cfg["tile_bleed_px"]
        end_l = rig.project(projection, (x0, 0.0, 0.0))[0]
        end_r = rig.project(projection, (x1, 0.0, 0.0))[0]
        keep = [int(math.floor(end_l - bleed)), int(math.ceil(end_r + bleed))]
        pngcheck.keep_columns(out["png"], *keep)
        tiling = {
            "axis": "x",
            "period_m": period,
            "period_px": period * projection["px_per_m"],
            "footprint_end_columns_px": [end_l, end_r],
            "bleed_px": bleed,
            "kept_columns_px": keep,
            "note": ("rendered between camera-visible neighbour copies at +-period; columns outside "
                     "kept_columns are cleared by the pipeline (a manual re-render of the .blend is not cut)"),
        }
        print(f"{LOG} Tiling cut: kept columns {keep}")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects_info = []
    for obj in built["objects"]:
        ev = obj.evaluated_get(depsgraph)
        mesh = ev.to_mesh()
        objects_info.append({
            "object": obj.name,
            "evaluated_bounds_m": {"x": round(ev.dimensions.x, 4), "y": round(ev.dimensions.y, 4),
                                   "z": round(ev.dimensions.z, 4)},
            "evaluated_faces": len(mesh.polygons),
        })
        ev.to_mesh_clear()

    footprint_corners = [(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)]
    bounds_px = [rig.project(projection, p) for p in bounds]
    bbox_px = [min(p[0] for p in bounds_px), min(p[1] for p in bounds_px),
               max(p[0] for p in bounds_px), max(p[1] for p in bounds_px)]
    if tiling:
        bbox_px[0], bbox_px[2] = tiling["kept_columns_px"]
    record = {
        "pipeline": C.PIPELINE_MARKER,
        "pipeline_version": C.PIPELINE_VERSION,
        "asset": cfg["asset_id"],
        "category": cfg["category"],
        "description": cfg.get("description", ""),
        "config": cfg["_config_path"],
        "generator": f"assets/source/blender/generators/{cfg['generator']}.py",
        "generator_params": params,
        "random_seed": cfg["seed"],
        "blender_version": bpy.app.version_string,
        "outputs": {k: assetconfig.rel(v) for k, v in out.items()},
        "origin": "ground-footprint origin at z = 0 (Blender world origin); front faces -Y",
        "footprint_m": {"x_min": x0, "x_max": x1, "y_min": y0, "y_max": y1},
        "model": dict(built["info"], objects=objects_info),
        "camera": camera_info,
        "lighting": lighting_info,
        "render": dict(render_info, resolution_px=[scene.render.resolution_x, scene.render.resolution_y],
                       render_seconds=round(render_seconds, 1)),
        "projection": {
            "note": "texture px, top-left origin: x = W/2 + (p.right - cx)*ppm, y = H/2 - (p.up - cy)*ppm",
            **projection,
            "origin_px": list(rig.project(projection, (0.0, 0.0, 0.0))),
            "footprint_corners_px": [list(rig.project(projection, p)) for p in footprint_corners],
            "design_bounds_bbox_px": bbox_px,
        },
        "tiling": tiling,
        "total_seconds": round(time.time() - t0, 1),
    }
    out["record"].write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"{LOG} Record: {out['record']}")
    print(f"{LOG} DONE")


main()

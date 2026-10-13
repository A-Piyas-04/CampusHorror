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
    "tile_period_m":   ground tiles (config kind "ground_tile") only; the model is one square
                       period centred on the origin, rendered straight down between 8 copies

Config "layers" split the render: the base PNG shows every object not in a layer, then each
layer PNG shows only its own objects. All renders use the same camera, so they share the
origin pixel. Hidden objects are only hidden from camera rays: they still cast shadows and
bounce light, so each layer is lit exactly as in the combined model.
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


def world_vertices(objects):
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in objects:
        ev = obj.evaluated_get(deps)
        mesh = ev.to_mesh()
        mw = obj.matrix_world
        pts += [tuple(mw @ v.co) for v in mesh.vertices]
        ev.to_mesh_clear()
    return pts


def set_occluder(obj, occluder):
    """render.occlusion: objects outside the sprite being rendered are holdouts, so the sprite keeps
    only the pixels where its own objects are the nearest surface. Objects flagged `seam_overlap`
    (strips that run under a neighbour to hide the join) are hidden instead, so the neighbour's own
    surface still renders under them. Holdouts still cast shadows and bounce light."""
    if occluder and obj.get("seam_overlap"):
        obj.visible_camera, obj.is_holdout = False, False
    else:
        obj.visible_camera, obj.is_holdout = True, occluder


def check_crop_size(png, rect):
    if rect is None:
        return
    got = list(pngcheck.size(png))
    if got != rect[2:]:
        raise RuntimeError(f"{png}: cropped render is {got}, expected {rect[2:]} (border {rect})")


def trim_to_alpha(png, rect, pad):
    """Shrinks a cropped render to its alpha bbox + pad (inside the original crop). Returns the new rect."""
    a = pngcheck.analyse(png)
    if a["content_bbox_px"] is None:
        return rect
    x0, y0, x1, y1 = a["content_bbox_px"]
    w, h = rect[2], rect[3]
    nx0, ny0 = max(0, x0 - pad), max(0, y0 - pad)
    nx1, ny1 = min(w, x1 + 1 + pad), min(h, y1 + 1 + pad)
    if [nx0, ny0, nx1, ny1] != [0, 0, w, h]:
        pngcheck.crop(png, nx0, ny0, nx1 - nx0, ny1 - ny0)
    return [rect[0] + nx0, rect[1] + ny0, nx1 - nx0, ny1 - ny0]


def build_context(scene, cfg):
    """Neighbouring assets built camera-invisible: they shadow and light this asset but aren't rendered."""
    coll = rig.new_collection(scene, "Context")
    info = []
    for ctx in cfg["context_assets"]:
        ctx_cfg = assetconfig.load(ctx["asset_id"])
        gen = importlib.import_module(f"generators.{ctx_cfg['generator']}")
        params = dict(gen.DEFAULT_PARAMS)
        params.update(ctx_cfg["generator_params"])
        sub = bpy.data.collections.new(f"Context_{ctx['asset_id']}")
        coll.children.link(sub)
        built = gen.build(sub, random.Random(ctx_cfg["seed"]), params)
        for obj in sub.all_objects:
            obj.location += Vector(ctx["offset_m"])
            if cfg["render"]["occlusion"]:
                set_occluder(obj, True)
            else:
                obj.visible_camera = False
        info.append({"asset_id": ctx["asset_id"], "offset_m": ctx["offset_m"],
                     "objects": len(built["objects"]), "note": "camera-invisible; casts shadows and bounce light"})
        print(f"{LOG} Context asset {ctx['asset_id']} at {ctx['offset_m']} ({len(built['objects'])} objects)")
    return info


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
    context_info = build_context(scene, cfg) if cfg["context_assets"] else None
    ground = cfg["kind"] == "ground_tile"

    # Horizontally tileable assets: neighbour copies one period to each side give the module
    # ends the shadows, occlusion and bounce of a continuous run, and supply the bleed columns.
    period = None if ground else built.get("tile_period_x_m")
    by_name = {obj.name: obj for obj in built["objects"]}
    layer_objects = {}
    for layer in cfg["layers"]:
        missing = [n for n in layer["objects"] if n not in by_name]
        if missing:
            raise SystemExit(f"layer {layer['name']}: unknown objects {missing}; generator objects: {sorted(by_name)}")
        layer_objects[layer["name"]] = [by_name[n] for n in layer["objects"]]
    if layer_objects and period:
        raise SystemExit("layers are not supported on tileable assets")
    layered = {obj.name for objs in layer_objects.values() for obj in objs}
    if layer_objects and not [o for o in built["objects"] if o.name not in layered]:
        raise SystemExit("every object is in a layer; the base Sprite would be empty")

    occlusion = render_cfg.get("occlusion")

    def show_only(visible):
        for obj in built["objects"]:
            if occlusion:
                set_occluder(obj, obj not in visible)
            else:
                obj.visible_camera = obj in visible

    if layer_objects or occlusion:
        show_only([o for o in built["objects"] if o.name not in layered])

    if period:
        for obj in built["objects"]:
            for name, dx in (("TileWest", -period), ("TileEast", period)):
                dup = obj.copy()
                dup.name = f"{obj.name}_{name}"
                dup.location.x += dx
                asset_coll.objects.link(dup)

    # Ground tiles: the 8 surrounding copies make the rendered area one continuous, periodic
    # surface, so relief and shading at the tile edges match the opposite edges.
    ground_period = None
    if ground:
        ground_period = built.get("tile_period_m")
        if abs((ground_period or 0) - cfg["ground"]["period_m"]) > 1e-9:
            raise SystemExit(f"generator tile_period_m {ground_period} != config ground.period_m "
                             f"{cfg['ground']['period_m']}")
        for obj in built["objects"]:
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    if i == 0 and j == 0:
                        continue
                    dup = obj.copy()
                    dup.name = f"{obj.name}_Tile{i:+d}{j:+d}"
                    dup.location.x += i * ground_period
                    dup.location.y += j * ground_period
                    asset_coll.objects.link(dup)

    lighting_info = rig.setup_lighting(scene, rig_coll, asset_coll)
    if ground:
        lighting_info["ground"] = "none (the tile is the ground; no cast shadow from other objects)"
        camera_info, projection = rig.setup_ground_camera(
            scene, rig_coll, ground_period, render_cfg["tile_px"], render_cfg["overscan_px"],
            max(p.z for p in bounds))
    else:
        camera_info, projection = rig.setup_camera(
            scene, rig_coll, bounds, render_cfg["elevation_deg"], render_cfg["azimuth_deg"], render_cfg["width_px"],
            render_cfg.get("px_per_m"), render_cfg.get("pixel_anchor_m"))
    render_info = rig.setup_render(scene, samples, opts["cpu"])

    # Cropped sprites: each render covers only its own objects' projected vertices (+ pad).
    crops = {}
    if render_cfg.get("crop_layers"):
        pad = render_cfg["crop_pad_px"]
        base_objects = [o for o in built["objects"] if o.name not in layered]
        crops[None] = rig.crop_rect(projection, world_vertices(base_objects), pad)
        for name, objs in layer_objects.items():
            crops[name] = rig.crop_rect(projection, world_vertices(objs), pad)
        rig.set_border(scene, crops[None])

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
    check_crop_size(out["png"], crops.get(None))
    if crops:
        crops[None] = trim_to_alpha(out["png"], crops[None], render_cfg["crop_pad_px"])
    print(f"{LOG} Rendered: {out['png']} in {render_seconds:.1f} s")

    layers_info = []
    for layer in cfg["layers"]:
        png = cfg["layer_outputs"][layer["name"]]
        show_only(layer_objects[layer["name"]])
        if crops:
            rig.set_border(scene, crops[layer["name"]])
        scene.render.filepath = str(png)
        t_layer = time.time()
        bpy.ops.render.render(write_still=True)
        if not png.exists():
            raise RuntimeError(f"Render finished but {png} was not written.")
        check_crop_size(png, crops.get(layer["name"]))
        if crops:
            crops[layer["name"]] = trim_to_alpha(png, crops[layer["name"]], render_cfg["crop_pad_px"])
        seconds = time.time() - t_layer
        render_seconds += seconds
        print(f"{LOG} Rendered layer {layer['name']}: {png} in {seconds:.1f} s")
        info = {
            "name": layer["name"],
            "png": assetconfig.rel(png),
            "objects": layer["objects"],
            "sort_y_m": layer["sort_y_m"],
            "z_index": layer["z_index"],
            "fade": layer["fade"],
            "render_seconds": round(seconds, 1),
        }
        if crops:
            info["crop_px"] = crops[layer["name"]]
        layers_info.append(info)

    ground_info = None
    if ground:
        ov, tile = render_cfg["overscan_px"], render_cfg["tile_px"]
        pngcheck.crop(out["png"], ov, ov, tile, tile)
        ground_info = {
            "period_m": ground_period,
            "tile_px": tile,
            "overscan_px": ov,
            "tileset": cfg["ground"]["tileset"],
            "source_id": cfg["ground"]["source_id"],
            "border_match": cfg["ground"]["border_match"],
            "note": ("rendered straight down between 8 neighbour copies with overscan_px on every side; "
                     "the pipeline crops the overscan (a manual re-render of the .blend is not cropped)"),
        }
        print(f"{LOG} Ground tile: cropped {ov} px overscan -> {tile}x{tile}")

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
            **({"crop_px": crops[None]} if crops else {}),
        },
        "tiling": tiling,
        "layers": layers_info or None,
        **({"context_assets": context_info} if context_info else {}),
        **({"seams": cfg["seams"]} if cfg["seams"] else {}),
        "kind": cfg["kind"],
        "ground_tile": ground_info,
        "total_seconds": round(time.time() - t0, 1),
    }
    out["record"].write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"{LOG} Record: {out['record']}")
    print(f"{LOG} DONE")


main()

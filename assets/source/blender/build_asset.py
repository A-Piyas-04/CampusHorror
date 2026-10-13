"""Build one 2.5D asset: Blender render -> validation -> Godot scene (+ optional collision) -> Godot check.

From the project root (any Python 3.10+, standard library only):

    python assets/source/blender/build_asset.py red_brick_wall_3m
    python assets/source/blender/build_asset.py asset_a asset_b      (small batch, built one after another)
    python assets/source/blender/build_asset.py --all                (every config in configs/)

Options:
    --steps render,validate,scene,preview,godot   subset to run (default: all, in this order)
    --cpu / --samples N                           Blender render overrides (not stored in the config)
    --no-collision                                skip the collision stage even if the config enables it
    --compare-to PATH                             also report pixel differences against another PNG
    --force-scene                                 overwrite a generated scene that was edited by hand
    --blender PATH / --godot PATH                 executables (defaults: env BLENDER_EXE / GODOT_EXE,
                                                  then the paths in pipeline/conventions.py)
Exit code 0 only if every requested step passed. Logs: assets/source/blender/logs/.
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import assetconfig, conventions as C, godot_scene, pngcheck  # noqa: E402

ALL_STEPS = ["render", "validate", "scene", "preview", "godot"]
CHECK_SCRIPT = "res://scenes/tests/asset_previews/asset_scene_check.gd"
GROUND_CHECK_SCRIPT = "res://scenes/tests/asset_previews/ground_tile_check.gd"
# Blender lines that look like problems but aren't.
BLENDER_NOISE = re.compile(r"^\[PIPELINE\]|Fra:\d+|^Saved:|^Time:|^Blender quit")
PROBLEM = re.compile(r"(?i)\b(error|warning|traceback|exception)\b|^WARN")


def say(msg):
    print(f"[BUILD] {msg}", flush=True)


def run(cmd, log_path, timeout):
    say("$ " + subprocess.list2cmdline(cmd))
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=C.PROJECT_ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    output = proc.stdout + ("\n--- stderr ---\n" + proc.stderr if proc.stderr.strip() else "")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    return proc.returncode, output, time.time() - t0


def problems(output, noise=None):
    lines = []
    for line in output.splitlines():
        s = line.strip()
        if s and PROBLEM.search(s) and not (noise and noise.search(s)):
            lines.append(s)
    return lines


class Report:
    def __init__(self):
        self.checks, self.warnings, self.failed = [], [], False

    def check(self, ok, what):
        self.checks.append(("PASS" if ok else "FAIL", what))
        say(("ok    " if ok else "FAIL  ") + what)
        self.failed |= not ok
        return ok

    def warn(self, what):
        self.warnings.append(what)
        say("WARN  " + what)


# ---------------------------------------------------------------------------

def step_render(cfg, args, rep):
    assetconfig.check_render_outputs_owned(cfg)
    # Godot must not import generated .blend sources (it would launch Blender on every change).
    src_dir = cfg["outputs"]["blend"].parent
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / ".gdignore").touch()
    # A running editor imports a new PNG with its defaults (no mipmaps) as soon as it appears;
    # writing the first-import settings before the render wins that race.
    for png in [cfg["outputs"]["png"]] + list(cfg["layer_outputs"].values()):
        if not png.exists():
            png.parent.mkdir(parents=True, exist_ok=True)
            if godot_scene.ensure_texture_import(png, mipmaps=cfg["kind"] != "ground_tile"):
                say(f"wrote first-import settings before rendering: {assetconfig.rel(png)}.import")
    blender = args.blender or os.environ.get("BLENDER_EXE") or C.DEFAULT_BLENDER_EXE
    cmd = [blender, "--background", "--factory-startup", "--python-exit-code", "1",
           "--python", str(C.BLENDER_ROOT / "pipeline/blender_entry.py"), "--", "--config", cfg["asset_id"]]
    if args.cpu:
        cmd.append("--cpu")
    if args.samples:
        cmd += ["--samples", str(args.samples)]
    code, output, secs = run(cmd, C.LOG_DIR / f"{cfg['asset_id']}.blender.log", timeout=3600)
    rep.check(code == 0 and "[PIPELINE] DONE" in output, f"Blender exited {code} after {secs:.1f} s")
    found = problems(output, BLENDER_NOISE)
    for line in found:
        rep.warn("Blender: " + line)
    fatal = [s for s in found if re.search(r"(?i)traceback|^error|\| error", s)]
    rep.check(not fatal, f"Blender: {len(fatal)} error line(s), {len(found) - len(fatal)} warning line(s)")
    return {"exit_code": code, "seconds": round(secs, 1), "problem_lines": found}


def _check_record(cfg, rep):
    out = cfg["outputs"]
    record = assetconfig.read_record(cfg)
    if not rep.check(record is not None, f"record readable: {assetconfig.rel(out['record'])}"):
        return None
    rep.check(record.get("pipeline") == C.PIPELINE_MARKER and record.get("asset") == cfg["asset_id"],
              "record pipeline marker and asset id")
    for key in ("outputs", "projection", "camera", "render", "footprint_m", "lighting", "model", "blender_version"):
        rep.check(key in record, f"record has '{key}'")
    rep.check(str(record.get("blender_version", "")).startswith("5.2"),
              f"rendered with Blender 5.2 ({record.get('blender_version')})")
    rep.check(record["outputs"] == {k: assetconfig.rel(v) for k, v in out.items()},
              "record output paths match the naming convention")
    for key in ("blend", "png"):
        rep.check(out[key].is_file(), f"{key} exists: {assetconfig.rel(out[key])}")
    recorded = [(l["name"], l["png"]) for l in record.get("layers") or []]
    wanted = [(name, assetconfig.rel(p)) for name, p in cfg["layer_outputs"].items()]
    if recorded or wanted:
        rep.check(recorded == wanted, f"record layers {recorded} match the config {wanted}")
        for name, p in cfg["layer_outputs"].items():
            rep.check(p.is_file(), f"layer {name} png exists: {assetconfig.rel(p)}")
    rep.check((C.PROJECT_ROOT / record["generator"]).is_file() and (C.PROJECT_ROOT / record["config"]).is_file(),
              "generator and config referenced by the record exist")
    return record


def step_validate(cfg, args, rep):
    if cfg["kind"] == "ground_tile":
        return step_validate_ground(cfg, args, rep)
    out = cfg["outputs"]
    record = _check_record(cfg, rep)
    if record is None:
        return None

    cam, proj = record["camera"], record["projection"]
    rep.check(abs(cam["elevation_deg"] - cfg["render"]["elevation_deg"]) < 1e-6
              and abs(cam["azimuth_deg"] - cfg["render"]["azimuth_deg"]) < 1e-6 and cam["type"] == "ORTHO",
              f"camera ortho, elevation {cam['elevation_deg']}, azimuth {cam['azimuth_deg']}")
    rep.check("none" in record["lighting"]["ground"], "no ground plane / baked ground shadow")
    w, h = proj["image_px"]
    rep.check(abs(proj["px_per_m"] - w / cam["ortho_scale_m"]) < 1e-3, f"px/m {proj['px_per_m']:.3f} = width / ortho scale")

    try:
        png = pngcheck.analyse(out["png"])
    except pngcheck.PngError as exc:
        rep.check(False, f"PNG readable as 8-bit RGBA: {exc}")
        return None
    rep.check(True, "PNG is 8-bit RGBA, non-interlaced")
    rep.check(png["size_px"] == [w, h] == record["render"]["resolution_px"],
              f"PNG size {png['size_px']} matches record {record['render']['resolution_px']}")
    rep.check(png["content_bbox_px"] is not None and png["opaque_pixels"] > 0,
              f"content present ({png['opaque_pixels']} opaque, {png['partially_transparent_pixels']} partial px)")
    rep.check(png["fully_transparent_pixels"] > 0, f"transparent background ({png['fully_transparent_pixels']} px)")
    rep.check(png["max_alpha_on_image_border"] <= C.MAX_BORDER_ALPHA,
              f"image border fully transparent (max alpha {png['max_alpha_on_image_border']})")
    m = png["margins_px"] or {}
    rep.check(bool(m) and min(m.values()) >= C.MIN_MARGIN_PX, f"margins {m} >= {C.MIN_MARGIN_PX} px")

    # Layers: same canvas as the base; together they make up the whole model.
    bboxes = [png["content_bbox_px"]]
    layer_pngs = {}
    for name, path in cfg["layer_outputs"].items():
        try:
            lp = pngcheck.analyse(path)
        except pngcheck.PngError as exc:
            rep.check(False, f"layer {name} PNG readable as 8-bit RGBA: {exc}")
            return None
        lm = lp["margins_px"] or {}
        rep.check(lp["size_px"] == [w, h] and lp["content_bbox_px"] is not None and lp["opaque_pixels"] > 0
                  and lp["max_alpha_on_image_border"] <= C.MAX_BORDER_ALPHA
                  and bool(lm) and min(lm.values()) >= C.MIN_MARGIN_PX,
                  f"layer {name}: {lp['size_px']} like the base, {lp['opaque_pixels']} opaque px, "
                  f"transparent border, margins {lm}")
        bboxes.append(lp["content_bbox_px"])
        layer_pngs[name] = lp

    # Alpha bbox vs the design bounds projected through the camera -> framing + origin alignment.
    x0, y0 = min(b[0] for b in bboxes), min(b[1] for b in bboxes)
    x1, y1 = max(b[2] for b in bboxes), max(b[3] for b in bboxes)
    actual = [x0, y0, x1 + 1, y1 + 1]
    expected = proj["design_bounds_bbox_px"]
    dev = [round(a - e, 2) for a, e in zip(actual, expected)]
    rep.check(max(abs(d) for d in dev) <= C.CONTENT_BBOX_TOLERANCE_PX,
              f"alpha bbox{' (base + layers)' if layer_pngs else ''} {actual} vs projected design bounds "
              f"{[round(e, 2) for e in expected]} "
              f"(deviation {dev}, tolerance {C.CONTENT_BBOX_TOLERANCE_PX} px)")
    ox, oy = proj["origin_px"]
    rep.check(0 <= ox <= w and 0 <= oy <= h, f"footprint origin pixel ({ox:.2f}, {oy:.2f}) inside the image")
    seam = check_tiling(out["png"], record.get("tiling"), rep) if record.get("tiling") else None

    rep.check(out["png"].resolve().is_relative_to(C.PROJECT_ROOT / "assets/sprites"),
              f"Godot texture path {assetconfig.res_path(out['png'])}")
    imp = out["png"].with_name(out["png"].name + ".import")
    if imp.exists():
        text = imp.read_text(encoding="utf-8")
        rep.check(f'source_file="{assetconfig.res_path(out["png"])}"' in text or "source_file" not in text,
                  ".import source_file matches the PNG path")
        if "mipmaps/generate=true" not in text:
            rep.warn(".import has mipmaps off; the sprite is drawn at ~1/7 scale with a mipmap filter")

    verification = {"png": png, "bbox_deviation_px": dev, "minimum_margin_required_px": C.MIN_MARGIN_PX,
                    "tiling": seam, "layers": layer_pngs or None}
    if args.compare_to:
        diff = pngcheck.compare(out["png"], Path(args.compare_to))
        say(f"compare to {args.compare_to}: {diff}")
        verification["compare_to"] = {"path": args.compare_to, **diff}
    return verification


def step_validate_ground(cfg, args, rep):
    """Seamless top-down ground tile: opaque, exact tile size, no wrap-around seam, no lighting
    gradient, and (for variants) a border that matches the base tile."""
    out = cfg["outputs"]
    record = _check_record(cfg, rep)
    if record is None:
        return None
    cam, proj, g = record["camera"], record["projection"], record.get("ground_tile") or {}
    tile = cfg["render"]["tile_px"]
    rep.check(cam["type"] == "ORTHO" and abs(cam["elevation_deg"] - C.GROUND_ELEVATION_DEG) < 1e-6,
              f"camera ortho, straight down (elevation {cam['elevation_deg']})")
    rep.check(g.get("tile_px") == tile and abs(g.get("period_m", 0) - cfg["ground"]["period_m"]) < 1e-9,
              f"record ground tile {g.get('tile_px')} px / {g.get('period_m')} m matches the config")
    rep.check(abs(proj["px_per_m"] - tile / cfg["ground"]["period_m"]) < 1e-6,
              f"render scale {proj['px_per_m']:.3f} px/m = tile_px / period")
    try:
        png = pngcheck.analyse(out["png"])
    except pngcheck.PngError as exc:
        rep.check(False, f"PNG readable as 8-bit RGBA: {exc}")
        return None
    rep.check(True, "PNG is 8-bit RGBA, non-interlaced")
    rep.check(png["size_px"] == [tile, tile] == proj["image_px"], f"PNG size {png['size_px']} = {tile} x {tile}")
    rep.check(png["opaque_pixels"] == tile * tile,
              f"fully opaque ({png['opaque_pixels']} of {tile * tile} px at alpha 255)")

    seams = pngcheck.wrap_seam_metrics(out["png"])
    for axis, s in seams.items():
        limit = C.GROUND_SEAM_RATIO_MAX * s["interior_mean_step"] + C.GROUND_SEAM_SLACK
        rep.check(s["wrap_step"] <= limit,
                  f"seamless along {axis}: wrap-around step {s['wrap_step']:.2f} vs interior mean "
                  f"{s['interior_mean_step']:.2f} / max {s['interior_max_step']:.2f} (limit {limit:.2f})")
    halves = pngcheck.luma_halves(out["png"])
    rep.check(halves["max_half_difference"] <= C.GROUND_GRADIENT_MAX,
              f"no lighting gradient: luma halves L/R {halves['left']}/{halves['right']}, "
              f"T/B {halves['top']}/{halves['bottom']} (max diff {halves['max_half_difference']}, "
              f"limit {C.GROUND_GRADIENT_MAX})")
    border = None
    ref_id = cfg["ground"]["border_match"]
    if ref_id:
        ref = assetconfig.load(ref_id)
        if rep.check(ref["outputs"]["png"].is_file(), f"border-match base tile exists: {ref_id}"):
            border = pngcheck.border_band_diff(out["png"], ref["outputs"]["png"], C.GROUND_BORDER_BAND_PX)
            rep.check(border["same_size"] and border["mean_rgb_diff"] <= C.GROUND_BORDER_MATCH_MAX,
                      f"border band ({C.GROUND_BORDER_BAND_PX} px) matches {ref_id}: mean RGB diff "
                      f"{border.get('mean_rgb_diff')}, max {border.get('max_rgb_diff')} "
                      f"(limit mean {C.GROUND_BORDER_MATCH_MAX})")
    rep.check(out["png"].resolve().is_relative_to(C.PROJECT_ROOT / "assets/sprites"),
              f"Godot texture path {assetconfig.res_path(out['png'])}")
    imp = out["png"].with_name(out["png"].name + ".import")
    if imp.exists() and "mipmaps/generate=true" in imp.read_text(encoding="utf-8"):
        rep.warn(".import has mipmaps on; ground tiles are drawn 1:1")
    return {"png": png, "seams": seams, "luma_halves": halves, "border_match": border}


def step_tileset(cfg, args, rep):
    out = cfg["outputs"]
    godot_scene.check_writable(out["scene"], None, False)
    if godot_scene.ensure_texture_import(out["png"], mipmaps=False):
        say(f"wrote first-import settings (mipmaps off): {assetconfig.rel(out['png'])}.import")
    name = cfg["ground"]["tileset"]
    members = assetconfig.tileset_members(name)
    tile = cfg["render"]["tile_px"]
    rep.check(all(m["render"]["tile_px"] == tile for m in members), f"every tile in TileSet {name} is {tile} px")
    existing = out["scene"].read_text(encoding="utf-8") if out["scene"].exists() else None
    text, included = godot_scene.build_tileset(name, members, tile, existing)
    godot_scene.write_scene(out["scene"], text)
    say(f"wrote {assetconfig.rel(out['scene'])} ({len(included)} source(s): "
        + ", ".join(f"{s['source_id']}={s['asset_id']}" for s in included) + ")")
    rep.check(any(s["asset_id"] == cfg["asset_id"] for s in included), f"TileSet {name} has {cfg['asset_id']}")
    for res in re.findall(r'path="(res://[^"]+)"', text):
        rep.check((C.PROJECT_ROOT / res[len("res://"):]).is_file(), f"TileSet resource exists: {res}")
    return {
        "tileset": assetconfig.rel(out["scene"]),
        "scene_name": cfg["godot"]["scene_name"],
        "source_id": cfg["ground"]["source_id"],
        "tile_size_px": tile,
        "tileset_sources": included,
        "collision": None,
    }


def step_ground_preview(cfg, args, rep, record):
    out = cfg["outputs"]
    godot_scene.check_writable(out["preview"], None, False)
    ref_id = cfg["ground"]["border_match"]
    ref_source = assetconfig.load(ref_id)["ground"]["source_id"] if ref_id else None
    cells = godot_scene.ground_preview_cells(cfg, ref_source)
    existing = out["preview"].read_text(encoding="utf-8") if out["preview"].exists() else None
    godot_scene.write_scene(out["preview"], godot_scene.build_ground_preview_scene(
        cfg, cells, cfg["render"]["tile_px"], existing))
    record["godot"]["preview_cells"] = [list(c) for c in cells]
    say(f"wrote {assetconfig.rel(out['preview'])} ({len(cells)} cells)")
    return assetconfig.rel(out["preview"])


def check_tiling(png_path, tiling, rep):
    """Join quality of a horizontally tileable sprite, measured on the texture itself."""
    width, height, _, rows = pngcheck.read_rgba(png_path)
    end_l, end_r = tiling["footprint_end_columns_px"]
    bleed = tiling["bleed_px"]
    period = tiling["period_px"]
    # Rows that are solid wall across both end strips (skips the silhouette's top/bottom edges).
    # Only the ends are sampled, so a module with an opening in its middle (doorway) still has rows.
    lo, hi = math.floor(end_l - bleed / 2), math.ceil(end_r + bleed / 2)
    strip = math.ceil(bleed / 2 + period / 6)
    sampled = list(range(lo, lo + strip, 4)) + list(range(hi - strip, hi, 4)) + [hi - 1]
    ok = [all(r[x * 4 + 3] == 255 for x in sampled) for r in rows]
    # Rows next to a non-solid row are silhouette edges (coping joints), not part of a join.
    solid = [r for y, r in enumerate(rows) if 0 < y < len(rows) - 1 and ok[y - 1] and ok[y] and ok[y + 1]]
    rep.check(len(solid) >= 10, f"{len(solid)} solid wall rows found for the join checks")
    edge_cols = list(range(lo, math.ceil(end_l + bleed / 2))) + list(range(math.floor(end_r - bleed / 2), hi))
    fringe = sum(1 for r in solid for x in edge_cols if r[x * 4 + 3] != 255)
    rep.check(fringe == 0, f"no alpha fringe from {bleed // 2} px outside to inside both footprint ends "
                           f"(columns {lo}..{hi - 1}): {fringe} non-opaque px")
    # The bleed past one end must repeat the texels just inside the other end (same world point mod period).
    shift = round(period)
    diffs = []
    for r in solid:
        for x in range(math.floor(end_l - bleed / 2), math.ceil(end_l + bleed / 2)):
            for c in range(3):
                diffs.append(abs(r[x * 4 + c] - r[(x + shift) * 4 + c]))
    mean = sum(diffs) / len(diffs)
    rep.check(mean <= C.TILE_MATCH_MEAN_MAX, f"bleed matches the opposite end (shift {shift} px, period "
                                             f"{period:.2f} px): mean RGB diff {mean:.2f}, max {max(diffs)} "
                                             f"(limit mean {C.TILE_MATCH_MEAN_MAX})")
    kept = tiling["kept_columns_px"]
    outside = sum(1 for r in rows for x in list(range(0, kept[0])) + list(range(kept[1], width)) if r[x * 4 + 3])
    rep.check(outside == 0, f"nothing outside the kept columns {kept}: {outside} px")
    return {"solid_rows": len(solid), "fringe_px_at_ends": fringe, "end_match_mean_rgb_diff": round(mean, 3),
            "end_match_max_rgb_diff": max(diffs), "shift_px": shift}


def step_scene(cfg, args, rep, record):
    out = cfg["outputs"]
    prev = (record.get("godot") or {}).get("scene_semantic_sha256")
    godot_scene.check_writable(out["scene"], prev, args.force_scene)
    for png in [out["png"]] + list(cfg["layer_outputs"].values()):
        if godot_scene.ensure_texture_import(png):
            say(f"wrote first-import settings (mipmaps on): {assetconfig.rel(png)}.import")
    existing = out["scene"].read_text(encoding="utf-8") if out["scene"].exists() else None
    if args.no_collision:
        cfg["collision"]["enabled"] = False
    text, lay, col = godot_scene.build_prop_scene(cfg, record, existing)
    digest = godot_scene.write_scene(out["scene"], text)
    say(f"wrote {assetconfig.rel(out['scene'])} (sprite scale {lay['sprite_scale']:.6f}, "
        f"offset {[round(v, 3) for v in lay['sprite_offset_px']]}, collision {'on' if col else 'off'})")

    for res in re.findall(r'path="(res://[^"]+)"', text):
        rep.check((C.PROJECT_ROOT / res[len("res://"):]).is_file(), f"scene resource exists: {res}")
    fp = lay["footprint_game_px"]
    length = fp[1][0] - fp[0][0]
    want = (record["footprint_m"]["x_max"] - record["footprint_m"]["x_min"]) * C.GAME_PX_PER_M
    rep.check(abs(length - want) < 0.01, f"footprint {length:.3f} game px wide = {want:.3f} ({C.GAME_PX_PER_M:g} px/m)")
    return {
        "scene": assetconfig.rel(out["scene"]),
        "scene_name": cfg["godot"]["scene_name"],
        "scene_semantic_sha256": digest,
        "sprite_offset_adjust_px": cfg["godot"]["sprite_offset_adjust_px"],
        **godot_scene.record_summary(lay, col),
    }


def step_preview(cfg, args, rep, record):
    out = cfg["outputs"]
    if not cfg["godot"]["preview_scene"]:
        say("preview scene disabled in config")
        return None
    godot_scene.check_writable(out["preview"], None, False)
    existing = out["preview"].read_text(encoding="utf-8") if out["preview"].exists() else None
    lay = record["godot"]["layout"]
    godot_scene.write_scene(out["preview"], godot_scene.build_preview_scene(cfg, record, lay, existing))
    say(f"wrote {assetconfig.rel(out['preview'])}")
    return assetconfig.rel(out["preview"])


def godot_exe(args):
    return args.godot or os.environ.get("GODOT_EXE") or C.DEFAULT_GODOT_EXE


def import_is_current(png):
    """True if Godot's imported texture was made from the PNG as it is now (source_md5 matches)."""
    imp = png.with_name(png.name + ".import")
    if not imp.exists():
        return False
    m = re.search(r'^dest_files=\["res://([^"]+)\.ctex"', imp.read_text(encoding="utf-8"), re.M)
    md5_file = C.PROJECT_ROOT / (m.group(1) + ".md5") if m else None
    if md5_file is None or not md5_file.exists():
        return False
    stored = re.search(r'source_md5="([0-9a-f]+)"', md5_file.read_text(encoding="utf-8"))
    return bool(stored) and stored.group(1) == hashlib.md5(png.read_bytes()).hexdigest()


def step_import(cfg, args, rep):
    """Make sure Godot has imported the PNG (headless --import) so scenes can load it."""
    pngs = [cfg["outputs"]["png"]] + list(cfg["layer_outputs"].values())
    if all(import_is_current(p) for p in pngs):
        return {"already_imported": True}
    code, output, secs = run([godot_exe(args), "--headless", "--path", str(C.PROJECT_ROOT), "--import"],
                             C.LOG_DIR / f"{cfg['asset_id']}.godot_import.log", timeout=600)
    found = problems(output)
    for line in found:
        rep.warn("Godot import: " + line)
    rep.check(code == 0 and all(import_is_current(p) for p in pngs),
              f"Godot imported the current texture{'s' if len(pngs) > 1 else ''} (exit {code}, {secs:.1f} s)")
    return {"exit_code": code, "problem_lines": found}


def step_godot(cfg, args, rep):
    godot = godot_exe(args)
    out = cfg["outputs"]
    ground = cfg["kind"] == "ground_tile"
    result = {}
    for scene_key in ("scene", "preview"):
        if scene_key == "preview" and not cfg["godot"]["preview_scene"]:
            continue
        scene_res = assetconfig.res_path(out[scene_key])
        if scene_key == "scene" and ground:
            script_args = [scene_res, str(out["record"]), assetconfig.res_path(out["preview"])]
            script = GROUND_CHECK_SCRIPT
        else:
            script_args = [scene_res, str(out["record"])] if scene_key == "scene" else None
            script = CHECK_SCRIPT
        if script_args:
            cmd = [godot, "--headless", "--path", str(C.PROJECT_ROOT), "--script", script, "--", *script_args]
        else:
            cmd = [godot, "--headless", "--path", str(C.PROJECT_ROOT), "--quit-after", "2", scene_res]
        code, output, secs = run(cmd, C.LOG_DIR / f"{cfg['asset_id']}.godot_{scene_key}.log", timeout=300)
        found = problems(output)
        for line in found:
            rep.warn(f"Godot ({scene_key}): " + line)
        if scene_key == "scene":
            tag = "[GROUNDCHECK]" if ground else "[ASSETCHECK]"
            rep.check(code == 0 and f"{tag} PASS" in output, f"Godot {'TileSet' if ground else 'scene'} check exit {code}")
            for line in output.splitlines():
                if line.startswith(tag):
                    print("   " + line)
        else:
            rep.check(code == 0, f"Godot ran the preview scene headless (exit {code})")
        rep.check(not found, f"Godot {scene_key}: {len(found)} error/warning line(s)")
        result[scene_key] = {"exit_code": code, "problem_lines": found}
    return result


# ---------------------------------------------------------------------------

def build_one(asset, steps, args):
    try:
        cfg = assetconfig.load(asset)
    except assetconfig.ConfigError as exc:
        say(f"CONFIG ERROR: {exc}")
        return False

    rep = Report()
    say(f"asset {cfg['asset_id']} ({cfg['_config_path']}), steps {steps}")
    try:
        if "render" in steps:
            blender = step_render(cfg, args, rep)
            if rep.failed:
                raise SystemExit(1)
        record = assetconfig.read_record(cfg)
        if record is None:
            rep.check(False, "render record exists (run the render step first)")
            raise SystemExit(1)
        if "render" in steps:
            record["blender_run"] = blender
        if "validate" in steps:
            record["verification"] = dict(step_validate(cfg, args, rep) or {}, passed=not rep.failed)
        imported = False
        ground = cfg["kind"] == "ground_tile"
        scene_step = step_tileset if ground else (lambda c, a, r: step_scene(c, a, r, record))
        if "scene" in steps and not rep.failed:
            record["godot"] = scene_step(cfg, args, rep)
            if "godot" in steps and not rep.failed:
                record["godot_import"] = step_import(cfg, args, rep)
                imported = True
                uids = [godot_scene.texture_uid(p)
                        for p in [cfg["outputs"]["png"]] + list(cfg["layer_outputs"].values())]
                scene_text = cfg["outputs"]["scene"].read_text(encoding="utf-8")
                if not rep.failed and any(u and u not in scene_text for u in uids):
                    say("embedding the texture uid Godot just assigned")
                    record["godot"] = scene_step(cfg, args, rep)
        if "preview" in steps and not rep.failed and record.get("godot"):
            preview_step = step_ground_preview if ground else step_preview
            record["godot"]["preview_scene"] = preview_step(cfg, args, rep, record)
        cfg["outputs"]["record"].write_text(json.dumps(record, indent=2), encoding="utf-8")
        if "godot" in steps and not rep.failed:
            if not imported:
                record["godot_import"] = step_import(cfg, args, rep)
            if not rep.failed:
                record["godot_check"] = step_godot(cfg, args, rep)
            cfg["outputs"]["record"].write_text(json.dumps(record, indent=2), encoding="utf-8")
    except (assetconfig.ConfigError, godot_scene.SceneError) as exc:
        rep.check(False, str(exc))
    except SystemExit:
        pass

    passed = sum(1 for s, _ in rep.checks if s == "PASS")
    say(f"{cfg['asset_id']}: {'FAILED' if rep.failed else 'PASS'}: {passed}/{len(rep.checks)} checks, "
        f"{len(rep.warnings)} warning(s)")
    return not rep.failed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("assets", nargs="*", help="asset_id(s) (configs/<asset_id>.json) or config paths")
    ap.add_argument("--all", action="store_true", help="build every config in assets/source/blender/configs/")
    ap.add_argument("--steps", default=",".join(ALL_STEPS))
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--samples", type=int)
    ap.add_argument("--no-collision", action="store_true")
    ap.add_argument("--compare-to")
    ap.add_argument("--force-scene", action="store_true")
    ap.add_argument("--blender")
    ap.add_argument("--godot")
    args = ap.parse_args()

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    bad = [s for s in steps if s not in ALL_STEPS]
    if bad:
        ap.error(f"unknown steps {bad}; choose from {ALL_STEPS}")
    assets = list(args.assets)
    if args.all:
        assets += sorted(p.stem for p in C.CONFIG_DIR.glob("*.json"))
    if not assets:
        ap.error("give at least one asset_id, or --all")
    if args.compare_to and len(assets) > 1:
        ap.error("--compare-to works with one asset only")

    results = {a: build_one(a, steps, args) for a in dict.fromkeys(assets)}
    if len(results) > 1:
        say("batch: " + ", ".join(f"{a} {'PASS' if ok else 'FAILED'}" for a, ok in results.items()))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

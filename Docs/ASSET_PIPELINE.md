# Blender → Godot 2.5D asset pipeline

Snapshot: 13 October 2026 • Milestone G Part 2

Turns a Python asset generator into a validated transparent sprite plus a reusable Godot scene. Validated on the red-brick wall (`red_brick_wall_3m`) and the first architecture batch (doorway, window, pier; see "First architecture batch"). The first version regenerated the approved `red_brick_wall_grid_test` render pixel-for-pixel. The current version is a seamless tiling module (see "Seamless horizontal modules"), so its bricks differ from that test. The wall is a **pipeline proof**, not approval of final artwork. Camera, light and scale values are the approved test values; `Docs/ART_STYLE.md` still lists the exact angle, resolution and world scale as undecided.

## One command

From the project root (any Python 3.10+; standard library only, no extra packages):

```powershell
python assets/source/blender/build_asset.py red_brick_wall_3m
```

It runs these steps in order and stops at the first failure (exit code 0 only if every check passed):

| Step | What it does |
|---|---|
| `render` | Runs `F:\bbbb\blender.exe --background --factory-startup` with `pipeline/blender_entry.py`: the generator builds the model, the shared rig adds camera/lights/render settings, the `.blend` is saved, the PNG rendered and a `.render.json` record written. Blender's output is scanned for errors/warnings. |
| `validate` | Pure-Python PNG check: 8-bit RGBA, size equals the record, transparent background, fully transparent image border, margins ≥ 16 px, alpha bounding box within 4 px of the design bounds projected through the camera (proves framing and origin alignment), record fields, Blender 5.2, output naming, Godot `res://` texture path. |
| `scene` | Writes `scenes/props/<category>/<SceneName>.tscn` (Sprite2D with footprint origin + optional collision). Writes first-import settings for a new PNG (mipmaps on). |
| `preview` | Writes a test-only preview `scenes/tests/asset_previews/<SceneName>Preview.tscn` (player-sized reference, footprint outline, origin dot, zoom-4 camera; optional tiled neighbour). |
| `godot` | Runs Godot 4.7.2 headless: imports the PNG if Godot's stored source MD5 doesn't match the current file, loads the prop scene with `asset_scene_check.gd` (texture size, scale, origin, footprint corners, collision vs the record), and runs the preview scene for 2 frames. Godot's errors/warnings are reported. |

Options: `--steps validate,scene,preview,godot` (skip the render), `--cpu`, `--samples N`, `--no-collision`, `--compare-to <png>`, `--force-scene`, `--blender PATH`, `--godot PATH` (or env `BLENDER_EXE` / `GODOT_EXE`). Logs: `assets/source/blender/logs/<asset_id>.*.log` (not tracked by Git).

The editor can stay open; afterwards it picks up the new files on focus (or MCP `rescan_filesystem`).

## Layout

```text
assets/source/blender/
├── build_asset.py              host command (the only entry point you need)
├── configs/<asset_id>.json     one config per asset: generator, seed, params, Godot + collision settings
├── generators/<family>.py      modeling + materials only (no camera/light/render/export code)
├── generators/brick_openings.py  helpers shared by the doorway and window generators (not a generator)
├── pipeline/                   shared code
│   ├── conventions.py          camera 40°/0°, sun, fills, margins, 32 game px/m, thresholds, exe paths
│   ├── assetconfig.py          config loading, output naming, protected files, ownership checks
│   ├── rig.py                  (Blender) scene reset, lights, ortho camera framing, Cycles/compositor, projection
│   ├── modeling.py             (Blender) BoxBuilder, shader-node helpers
│   ├── blender_entry.py        (Blender) generator → rig → .blend → PNG → record
│   ├── pngcheck.py             PNG reader, alpha/margin analysis, image compare
│   └── godot_scene.py          .tscn writer, collision stage, preview scene, edit detection
├── <category>/                 generated sources (has .gdignore so Godot doesn't import the .blend)
│   ├── <asset_id>.blend
│   └── <asset_id>.render.json  record: settings, projection, verification, Godot layout
├── logs/                       build logs (ignored)
└── scripts/red_brick_wall_test.py   original one-off test script (kept unchanged)
assets/sprites/<category>/<asset_id>.png (+ .import)
scenes/props/<category>/<SceneName>.tscn
scenes/tests/asset_previews/<SceneName>Preview.tscn, asset_scene_check.gd
```

Output paths are derived only from `asset_id`, `category` and `godot.scene_name`; configs never contain paths.

## Coordinate and scale conventions

- Blender: metres, Z up, the visible front faces −Y, **asset origin = ground-footprint origin at z = 0** (for the wall: centre of the footprint).
- Camera: orthographic, elevation 40°, azimuth 0°, frames the generator's `bounds_points_m` plus an 8 % margin, width 768 px → the render scale (px/m) follows from the asset size (wall: 220.69 px/m). With `"render": {"px_per_m": 220.689655}` in a config the scale is fixed instead and the image width follows from the asset size; the batch assets use this so every module has the wall's texel density. No ground plane, no shadow catcher, **no baked ground shadow**.
- Projection (stored in the record): texture px `x = W/2 + (p·right − cx)·ppm`, `y = H/2 − (p·up − cy)·ppm`.
- Godot: `Sprite2D` with `centered = false`, `offset = −origin_px`, uniform `scale = 32 / render px-per-metre`. The scene root's origin is exactly the Blender origin, so Y-sorting uses the ground footprint (Docs/CONVENTIONS.md §3–4). The root transform stays identity; place instances by moving the root.
- Ground depth on screen is foreshortened by the camera (`sin 40° = 0.643`): a 0.30 m deep footprint is 6.17 game px tall, 3.0 m long is 96 game px.

Generated scene:

```text
RedBrickWall3m (Node2D)        metadata asset_id / generated_by; origin = footprint origin
├── Sprite (Sprite2D)          light mask 2 (§10), texture filter linear + mipmaps
└── Body (StaticBody2D)        only if collision is enabled; layer 1 "world", mask 0
    └── Collision (CollisionShape2D, RectangleShape2D)
                               with collision.rects_m: one Collision<Name> per rectangle instead
```

## Seamless horizontal modules (tiling)

A generator that returns `"tile_period_x_m": <metres>` declares that its model repeats seamlessly along X with that period (the wall: 3.0 m = 12 brick pitches). The generator must make the geometry periodic. In `red_brick_wall.py`, a brick crossing a module end is cut exactly at the end and its other part is placed at the opposite end with the same colour and jitter. Edges lying on the end planes get bevel weight 0 (`BoxBuilder.to_mesh(flush_x=...)`), so the parts meet flush.

The shared pipeline then:

1. Renders the module between camera-visible copies of itself at ±period. The ends get the shadows, occlusion and bounce of a continuous run, so no lit end face is rendered.
2. Keeps `tile_bleed_px` (default 16) texels of that neighbour continuation past each footprint end, and clears everything else to transparent (`kept_columns_px` in the record). Two modules placed one period apart overlap only in the bleed, with matching pixels. At the join, each sprite is fully opaque, so mipmapped and linear sampling show no alpha fringe or background.
3. Validates the join: no non-opaque pixel in solid wall rows from `bleed/2` outside to inside each end; the bleed past one end matches the texels inside the other end (mean RGB difference ≤ 3); nothing outside the kept columns. "Solid rows" are rows that are opaque across both end strips (`bleed/2` + one sixth of the period at each end) and whose neighbour rows are too, so a module with an opening in its middle (the doorway) is checked the same way and silhouette edge rows are skipped.

Placement is unchanged: same scale, same origin, instances exactly one footprint length apart (96 px for the wall). Don't move sprites to hide joins.

Known limits: the free ends of a run show the bleed (2.3 game px past the footprint, a hard cut through the bond), and identical modules repeat their brick colours every 3 m. Fixing either needs separate variants: an end-cap module with a finished end and no bleed on that side, and A/B modules that share the bricks crossing their ends but have different interiors. Neither is built yet.

## Collision (optional, separate stage)

Collision is never derived from the sprite's alpha. It is off unless the config enables it:

```json
"collision": { "enabled": true, "source": "design_footprint", "depth_mode": "projected" }
```

- `source`: `design_footprint` (the generator's declared ground footprint), `rect_m` with `"rect_m": [x_min, x_max, y_min, y_max]` in metres, or `rects_m` with named rectangles, e.g. the doorway's `"rects_m": {"WestJamb": [-1.5, -0.7, -0.15, 0.15], "EastJamb": [0.7, 1.5, -0.15, 0.15]}` → nodes `Body/CollisionWestJamb` and `Body/CollisionEastJamb`, nothing across the opening.
- `depth_mode`: `projected` (matches the drawn footprint, ×0.643) or `top_down` (metres × 32 unchanged).
- Rectangles only, and only for azimuth 0. `--no-collision` skips the stage for one run.

## Regeneration and safety rules

- Files the pipeline never writes: the original wall `.blend`, its three PNGs and records, `campus_asset_workshop.blend`, `WallAssetPreview.tscn`, `Main.tscn` (list in `pipeline/assetconfig.py`).
- A `.blend`/PNG/record is only overwritten if its record says the pipeline produced it for the same `asset_id`.
- A scene is only overwritten if it carries `metadata/generated_by = "campus_asset_pipeline"`. If it was **edited by hand** since generation (semantic hash in the record; Godot's own re-save with UIDs/`unique_id`s is tolerated), the build stops. Put the change in the config (`godot.z_index`, `godot.sprite_offset_adjust_px` in game px, `godot.light_mask`, `collision.*`) and run with `--force-scene`.
- On regeneration the scene's `uid` and node `unique_id`s are kept, so instances in zones keep their references and overrides.
- An existing `.png.import` is never rewritten.
- Nothing is committed automatically.

## Adding a new asset generator

1. Create `assets/source/blender/generators/<family>.py`:

   ```python
   import bpy
   from pipeline.modeling import BoxBuilder, new_material  # shared helpers, optional

   COLLECTION_NAME = "MyAsset"
   DEFAULT_PARAMS = {"width": 1.0, "height": 2.0}

   def build(collection, rng, params):
       # Model around the origin: front faces -Y, ground at z = 0. Use only `rng` for randomness.
       obj = ...  # create objects, link them to `collection`, assign materials
       hw = params["width"] / 2
       return {
           "objects": [obj],
           "bounds_points_m": [(x, y, z) for x in (-hw, hw) for y in (-0.2, 0.2) for z in (0, params["height"])],
           "footprint_m": [-hw, hw, -0.2, 0.2],   # declared ground footprint (used by collision)
           "info": {"design_size_m": {...}},       # anything worth recording
       }
   ```

   No camera, lights, render settings, file paths or saving: the shared pipeline owns those. `bounds_points_m` must enclose everything visible (overhangs included), or the bbox check fails.
2. Create `assets/source/blender/configs/<asset_id>.json` (copy `red_brick_wall_3m.json`): `asset_id` (snake_case, equals the file name), `category`, `generator`, `seed`, `generator_params` (only keys from `DEFAULT_PARAMS`), `godot.scene_name` (PascalCase), `collision`.
3. Run `python assets/source/blender/build_asset.py <asset_id>`.
4. Open `scenes/tests/asset_previews/<SceneName>Preview.tscn` and look at it (manual visual check).

A variant of an existing family (e.g. a 1.5 m wall) needs only a new config, e.g. `"generator": "red_brick_wall", "generator_params": {"length": 1.5, "coping_units": 18}`.

## Small batches

```powershell
python assets/source/blender/build_asset.py asset_a asset_b asset_c   # one after another, summary at the end
python assets/source/blender/build_asset.py --all                     # every config
python assets/source/blender/build_asset.py --all --steps validate,scene,preview,godot   # re-check without rendering
```

Each asset is about 6 s of Blender (RTX 3050, OptiX, 256 samples) plus about 3 s of Godot checks.

## First architecture batch (13 October 2026)

```powershell
python assets/source/blender/build_asset.py red_brick_arch_doorway_3m red_brick_arch_window_3m red_brick_veranda_pier
```

| Asset (config) | Generator | Scene | Size | Collision |
|---|---|---|---|---|
| `red_brick_arch_doorway_3m` | `red_brick_arch_doorway` | `RedBrickArchDoorway3m` | 3.0 × 0.30 m; 2.40 m at the ends, 3.36 m parapet; opening 1.40 m clear, apex 2.81 m, open to the ground | `rects_m`: two jambs (25.6 px each), 44.8 px opening free |
| `red_brick_arch_window_3m` | `red_brick_arch_window` | `RedBrickArchWindow3m` | 3.0 × 0.30 × 2.40 m; window 0.80 m clear, sill 0.80 m, apex 2.05 m, steel grille | full footprint |
| `red_brick_veranda_pier` | `red_brick_pier` | `RedBrickVerandaPier` | 0.49 × 0.49 × 2.80 m | full footprint (15.7 × 10.1 px) |

- All three use the wall's camera, lights, bricks, mortar and bevel (`_brick_material`, `_mortar_material`, `DEFAULT_PARAMS` imported from `red_brick_wall.py`) and `render.px_per_m` 220.689655, so the sprite scale is 0.145 like the wall.
- **Joining the wall.** The doorway and window are 3.0 m wall modules: they lay their courses and coping with the wall generator's own code, the wall's seed (20261013) and the same RNG order, so for |x| ≥ 1.0 m they are brick-for-brick the wall. Only bricks inside |x| < 1.0 m are clipped around the opening (wedge pieces follow the arch) and recoloured from `interior_seed`. Place them in a `RedBrickWall3m` run at 96 px spacing, like another wall module. Measured on the PNGs at the join columns (±8 px at both ends) against `red_brick_wall_3m.png`: window mean RGB difference 0.80, doorway 2.19 (it sits 0.148 px off the wall's pixel grid; resampling alone gives 1.00), brightness offset under 1/255.
- **Pier.** Origin at the footprint centre; stand it centred on a wall join or free end (x = k · 96 px in a run). It covers the join and the free-end bleed. Its origin Y equals the wall's, so give it a later tree position than the walls to draw on top.
- `generators/brick_openings.py`: clipping wrapper for the wall's course code, equilateral pointed arch (radius = clear span) with radial voussoirs and keystone, jamb returns, mortar core per course. `BoxBuilder.add_prism_xz` builds the wedge pieces; `bevel=False` pieces (the mortar strips) get no bevel.
- Gallery (TEMPORARY): `scenes/tests/asset_previews/ArchitectureGalleryTest.tscn` (zoom 1) with `architecture_gallery_test.gd`, which sweeps the player's 28 × 12 px footprint across the run and prints `[GALLERY]` results (doorway passes, wall / window / pier / jamb block).

## What still needs eyes

The checks prove geometry, scale, alignment, transparency and loading. They do not judge art quality: open the preview scene and check the look, the edge quality at game scale, and how modules join.

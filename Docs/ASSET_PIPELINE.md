# Blender → Godot 2.5D asset pipeline

Snapshot: 13 October 2026 • Milestone G Part 2 + first architecture and environment batches

Turns a Python asset generator into a validated transparent sprite plus a reusable Godot scene, or (config `"kind": "ground_tile"`) into a seamless top-down ground tile in a shared TileSet. Validated on the red-brick wall (`red_brick_wall_3m`), the first architecture batch (doorway, window, pier; see "First architecture batch") and the first environment batch (4 ground tiles, 2 trees, hedge, bench, lamp post; see "First environment batch"). The first version regenerated the approved `red_brick_wall_grid_test` render pixel-for-pixel. The current version is a seamless tiling module (see "Seamless horizontal modules"), so its bricks differ from that test. The wall is a **pipeline proof**, not approval of final artwork. Camera, light and scale values are the approved test values; `Docs/ART_STYLE.md` still lists the exact angle, resolution and world scale as undecided.

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
| `scene` | Writes `scenes/props/<category>/<SceneName>.tscn` (Sprite2D with footprint origin + optional collision); for ground tiles, rewrites the shared TileSet instead. First-import settings for a new PNG (mipmaps on for sprites, off for ground tiles) are written before the render, so an open editor can't import it with its defaults first. |
| `preview` | Writes a test-only preview `scenes/tests/asset_previews/<SceneName>Preview.tscn` (player-sized reference, footprint outline, origin dot, zoom-4 camera; optional tiled neighbour). |
| `godot` | Runs Godot 4.7.2 headless: imports the PNG if Godot's stored source MD5 doesn't match the current file, loads the prop scene with `asset_scene_check.gd` (texture size, mipmaps, scale, origin, footprint corners, collision vs the record) or, for ground tiles, the TileSet and preview with `ground_tile_check.gd`, and runs the preview scene for 2 frames. Godot's errors/warnings are reported. |

Options: `--steps validate,scene,preview,godot` (skip the render), `--cpu`, `--samples N`, `--no-collision`, `--compare-to <png>`, `--force-scene`, `--blender PATH`, `--godot PATH` (or env `BLENDER_EXE` / `GODOT_EXE`). Logs: `assets/source/blender/logs/<asset_id>.*.log` (not tracked by Git).

The editor can stay open; afterwards it picks up the new files on focus (or MCP `rescan_filesystem`).

## Layout

```text
assets/source/blender/
├── build_asset.py              host command (the only entry point you need)
├── configs/<asset_id>.json     one config per asset: generator, seed, params, Godot + collision settings
├── generators/<family>.py      modeling + materials only (no camera/light/render/export code)
├── generators/brick_openings.py  helpers shared by the doorway and window generators (not a generator)
├── generators/ground_common.py   periodic (4D torus) noise/Voronoi, tile quad (ground generators; not a generator)
├── generators/foliage.py         canopy blobs, leaf cards with custom normals, leaf/bark materials (not a generator)
├── tools/environment_gallery.py  TEMPORARY: writes EnvironmentGalleryTest.tscn
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
scenes/props/<category>/<SceneName>.tscn          sprites
assets/tilesets/<tileset>.tres                     ground tiles (one shared TileSet per ground.tileset)
scenes/tests/asset_previews/<SceneName>Preview.tscn, asset_scene_check.gd, ground_tile_check.gd
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

## Ground tiles (`"kind": "ground_tile"`)

Ground is drawn by a `TileMapLayer`, not by sprites. A ground-tile config differs from a sprite config in three places:

```json
"kind": "ground_tile",
"render": { "samples": 256, "tile_px": 64 },
"ground": { "tileset": "campus_ground", "source_id": 1, "border_match": "grass_ground_tile" }
```

- **Size (Proposed, not decided):** one tile = 2 × 2 m = 64 × 64 px, drawn 1:1 (32 game px/m, no scaling). `Docs/ART_STYLE.md` still lists the final world scale as undecided.
- **Camera:** orthographic, straight down (elevation 90°, azimuth 0°; anything else is rejected). The ground is **not** foreshortened like the 40° sprites: a tile is a flat top-down texture. No perspective, no cast shadows, no lighting gradient (the same sun and fills as the sprites, but a flat surface gets even light).
- **Seamless by construction:** the generator returns `"tile_period_m": 2.0` and must make the material periodic. `generators/ground_common.py` maps X and Y each onto a circle (radius = period / 2π) and feeds the 4D point to Noise/Voronoi, so every pattern repeats exactly once per tile. 4D noise has a narrower value range than 3D: remap windows are about 0.42–0.58 for noise and 0.3–0.6 for Voronoi F1 distance.
- **Render:** the tile is rendered among its 8 neighbour copies with an 8 px overscan on each side, then cropped to 64 × 64. Edge pixels therefore get the same AO, bevels and filtering as interior pixels.
- **Validation (`step_validate_ground`):** 64 × 64, fully opaque; per axis, the wrap-around step (last column → first column) must be ≤ 1.5 × the interior mean step + 1; the luma difference between the left/right and top/bottom halves must be ≤ 6 (no gradient); with `border_match`, the outer 3 px band must match that tile (mean RGB diff ≤ 2.5), so variants mix with it in any order.
- **Godot:** all configs with the same `ground.tileset` share one `assets/tilesets/<tileset>.tres` (`TileSet`, tile size 64 × 64, no physics layers), with one `TileSetAtlasSource` per tile at its `source_id` (atlas coords 0,0). The `scene` step rebuilds the whole TileSet from every member config and keeps its `uid`. Tile PNGs are imported **without** mipmaps (drawn 1:1). Ground tiles never get collision. The preview `<SceneName>Preview.tscn` is a 6 × 4 `TileMapLayer` (z −10); variants are checkerboarded with their `border_match` tile.
- **Godot check:** `ground_tile_check.gd` (tile size, no physics, source ids, texture paths and sizes, no mipmaps, full opacity; preview layer, its TileSet, z index and every cell's source).

Seeing the repeat: `python assets/source/blender/logs/tile_sheet.py <png> [zoom]` writes a 3 × 3 sheet (logs/ is not tracked).

## Collision (optional, separate stage)

Collision is never derived from the sprite's alpha. It is off unless the config enables it:

```json
"collision": { "enabled": true, "source": "design_footprint", "depth_mode": "projected" }
```

- `source`: `design_footprint` (the generator's declared ground footprint), `rect_m` with `"rect_m": [x_min, x_max, y_min, y_max]` in metres, or `rects_m` with named rectangles, e.g. the doorway's `"rects_m": {"WestJamb": [-1.5, -0.7, -0.15, 0.15], "EastJamb": [0.7, 1.5, -0.15, 0.15]}` → nodes `Body/CollisionWestJamb` and `Body/CollisionEastJamb`, nothing across the opening.
- `depth_mode`: `projected` (matches the drawn footprint, ×0.643) or `top_down` (metres × 32 unchanged).
- Rectangles only, and only for azimuth 0. `--no-collision` skips the stage for one run.

## Render layers (optional, Batch 3A)

One sprite Y-sorts at one point. A building with parts that must sort or draw differently (a roof that should cover the player north of the building, a room behind a porch) lists them as layers:

```json
"layers": [
  { "name": "Roof", "objects": ["GateRoofCap"], "z_index": 10,
    "fade": { "rects_m": { "Behind": [-7.125, 6.125, 6.7403, 18.6] }, "alpha": 0.35, "seconds": 0.25 } },
  { "name": "Room", "objects": ["PavilionBrickMass", "..."], "sort_y_m": 2.8197 }
]
```

- `name`: PascalCase, unique, not `Sprite` / `Body`. `objects`: generator object names; an object belongs to at most one layer. Everything not in a layer stays in the base `Sprite`, which must not end up empty. Not allowed on tileable assets.
- **Render:** the base PNG is rendered with the layered objects hidden from the camera (`visible_camera = False`, so they still cast shadows and bounce light), then each layer is rendered alone from the same camera into `<asset_id>__<snake_name>.png` (same size and projection). Stacking the layers over the base gives the full render.
- **Godot:** each layer is a `Sprite2D` named after it, at position `(0, −sort_y_m × 32 × 0.643)` (its Y-sort point; 0 = the asset origin) with the offset compensated so its pixels land exactly where the base's do. `z_index` defaults to 0. If any layer sorts away from the origin, the root gets `y_sort_enabled = true` so the layer sorts on its own line in the zone.
- **Fade (`fade`, optional):** adds `<Name>Fade` (`Area2D` with `scripts/components/overhead_visibility.gd`, collision layer 0, mask 2 = player, not monitorable) whose `target_paths` is the layer sprite. `rects_m` are ground rectangles `[x_min, x_max, y_min, y_max]` in metres (y positive = north, like collision `projected`), one `Shape<Name>` each. `alpha` defaults to 0.35 and `seconds` to 0.25 (`pipeline/conventions.py`). Size a rect to the ground where the layer covers at least a quarter of the 64 px player, plus 0.5 m for the player's half-width.
- **Holdout under roofs:** a top face directly under an overhead layer is in that layer's full shadow and renders black. `landmark_common.cutaway_top_faces(obj, top_z, holdout_material(...))` makes such faces transparent in the base sprite, so the faded roof shows the ground and the player instead of a black slab. With the roof opaque the composite is unchanged.
- **Validation:** each layer PNG must have the base's size, opaque content and a transparent border; margins and the alpha bbox are checked on the union. `asset_scene_check.gd` checks each layer sprite and fade area.

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

## First environment batch (13 October 2026)

```powershell
python assets/source/blender/build_asset.py grass_ground_tile grass_worn_tile paved_walkway_tile asphalt_road_tile broadleaf_tree palm_tree hedge_section_2m outdoor_bench lamp_post
```

Ground tiles (`assets/sprites/ground/`, TileSet `assets/tilesets/campus_ground.tres`):

| Asset (config) | Generator | Source id | Notes |
|---|---|---|---|
| `grass_ground_tile` | `ground_grass` | 0 | Lawn: tuft cells, small colour patches |
| `grass_worn_tile` | `ground_grass` (`wear` 1.0) | 1 | Trampled grass and bare soil in the middle; border matches grass (mean diff 0.09) |
| `paved_walkway_tile` | `ground_paving` | 2 | 0.5 m dusty clay-red pavers with dark joints (config `slab_color` / `joint_color`, linear RGB; the generator default is grey concrete), running bond, joints a quarter slab away from the tile edges. Muted and pinker than the orange-red wall bricks so the two read apart |
| `asphalt_road_tile` | `ground_asphalt` | 3 | Aggregate, worn patches, fine cracks; no road markings |

Standing sprites (40° camera, footprint origin, transparent PNG, mipmaps):

| Asset (config) | Generator | Scene | Size | Collision |
|---|---|---|---|---|
| `broadleaf_tree` | `tree_broadleaf` | `vegetation/BroadleafTree` | crown about 4.8 m wide, crown centre at 4.2 m, 2.6 m clear under it | trunk only, 0.5 × 0.5 m (16 × 10.3 px) |
| `palm_tree` | `tree_palm` | `vegetation/CoconutPalm` | 7.2 m trunk, 3.5 m fronds, coconuts | trunk only, 0.35 m (11.2 × 7.2 px) |
| `hedge_section_2m` | `hedge` | `vegetation/HedgeSection2m` | 2.0 × 0.7 × 1.0 m, seamless along X (place 64 px apart) | full footprint (64 × 14.4 px) |
| `outdoor_bench` | `bench` | `street_furniture/OutdoorBench` | 1.8 × 0.6 m, seat 0.455 m, wooden slats on a dark-green steel frame | full footprint (57.6 × 12.3 px) |
| `lamp_post` | `lamp_post` | `street_furniture/LampPost` | 4.4 m, plinth, lantern | plinth only, 0.3 m (9.6 × 6.2 px) |

- Trees, palm, hedge, bench and lamp use `render.px_per_m` 220.689655 (sprite scale 0.145) like the architecture, except the hedge: **220.5** px/m, so its 2 m period is exactly 441 texture px. A fractional period put the join off by a sub-pixel and failed the join check (mean diff 3.33 → 1.23).
- Foliage (`generators/foliage.py`): lumpy inner volumes in a darker shade plus thousands of leaf cards. Leaf normals are bent outward and up (custom normals), and each leaf face is wound towards that normal: Cycles flips the shading normal on back-facing faces, which made half the leaves black.
- Trees are independent scenes: move the root, and the Y-sort point is the trunk base. The canopy has no collision and no overhead layer.
- **Import race (fixed):** an open editor imported four new PNGs with its defaults (mipmaps off) before the pipeline wrote their `.import`. `step_render` now writes the `.import` before Blender runs, and both Godot checks fail if mipmaps don't match (`texture.get_image().has_mipmaps()`; `Texture2D.has_mipmaps()` is always false headless).
- Gallery (TEMPORARY): `scenes/tests/asset_previews/EnvironmentGalleryTest.tscn`, written by `assets/source/blender/tools/environment_gallery.py`. One `TileMapLayer` (grass, worn patches, walkway, road) under the brick run, trees, palms, a hedge row, benches and lamps at zoom 1. `environment_gallery_test.gd` sweeps the player's 28 × 12 px footprint (9 cases: trunks, bench, lamp plinth and hedge block; canopy, ground tiles, the hedge gap and the doorway don't) and with `-- --screenshot=<path>` saves a screenshot.

Known limits of this batch:

- Ground is top-down while sprite footprints are foreshortened (×0.643). It reads fine at game zoom but is a deliberate mismatch.
- No transition or edge tiles (grass/path, path/road, kerbs). Every tile change is a hard 2 m square edge.
- The pattern repeats every 2 m, and all worn tiles are the same tile. A/B variants would help.
- The hedge has no end caps; a run ends in the 16 px bleed.
- No contact shadows under props and trees (by convention none are baked), so they look slightly floating on the ground.
- Tree canopies Y-sort at the trunk: the player draws behind the whole canopy when north of the trunk.
- 64 px tiles are magnified on windows larger than the base resolution (`canvas_items` stretch) and look soft.

## Main Gate landmark (Milestone G Batch 3, 13 October 2026)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File assets/source/blender/tools/main_gate_sign_texture.ps1
python assets/source/blender/build_asset.py main_gate_tower main_gate_leaves main_gate_pavilion
```

Reconstructed from `Docs/map-reference/area1/mainGate.jpg` (plus `whole view.png` for placement). Category `landmarks`; 220.689655 px/m like the architecture.

| Asset (config) | Generator | Scene | Size | Collision |
|---|---|---|---|---|
| `main_gate_tower` | `main_gate_tower` | `landmarks/MainGateTower` | 9.75 × 6.4 m brick tower, 8.6 m, roof tray to 9.55 m with 1.25 m overhang; 4.76 m passage under three white pointed rings (clear apex ≈ 6.15 m); crest shield and medallion | `rects_m`: `WestPier`, `EastPier` (projected); passage free |
| `main_gate_leaves` | `main_gate_leaves` | `landmarks/MainGateLeaves` | two steel-frame leaves, 4.76 × 2.5 m | `rect_m` across the opening (top-down, 10 px deep) |
| `main_gate_pavilion` | `main_gate_pavilion` | `landmarks/MainGatePavilion` | brick room 5.9 × 6.8 × 3.3 m with two pointed windows, canopy slab on five white columns, 9.3 × 1.65 m green bilingual sign, stub wall | `rects_m`: `Room` (projected); porch free |

- `generators/landmark_common.py`: shared procedural brick shader (object-space running bond, same palette as the walls), paint/concrete/steel/glass/image materials, the two-centred pointed-arch outline, and small bmesh builders. New landmark generators should reuse it.
- `tools/main_gate_sign_texture.ps1` (WPF text rendering, so the Bengali line is shaped correctly) writes `textures/main_gate_sign.png`; `textures/` has a `.gdignore`. The pavilion generator maps it onto the sign face. Rebuild the pavilion after changing the sign.
- The landmark is placed and checked in the zone, not in the gallery: see `Docs/CAMPUS_MAP.md` ("Main Gate landmark") and `scenes/tests/environment_previews/MainGateLandmarkCheck.tscn`.
- **Batch 3A layers** (see "Render layers"):

| Asset | PNGs | Layers |
|---|---|---|
| `main_gate_tower` | `main_gate_tower.png`, `main_gate_tower__roof.png` (3143 × 3188) | `Roof` = `GateRoofCap`, z 10, `RoofFade` (`Behind`). Brick and vault top faces are holdout (`GateRoofCutaway`) |
| `main_gate_pavilion` | `main_gate_pavilion.png` (columns), `__room.png`, `__room_roof.png`, `__canopy.png` (2451 × 2356) | `Room` (brick mass, window frames, sills, glass, grilles) and `RoomRoof` (`PavilionRoomRoof`, `RoomRoofFade`) at `sort_y_m` 2.8197 = the room's north face; `Canopy` (`PavilionPorchSlab`, sign board and face; `CanopyFade` over the porch). The old single slab is split into `PavilionPorchSlab` and `PavilionRoomRoof`; brick-mass and column tops are holdout |

  `main_gate_leaves` has no layers and is unchanged.

## What still needs eyes

The checks prove geometry, scale, alignment, transparency and loading. They do not judge art quality: open the preview scene and check the look, the edge quality at game scale, and how modules join.

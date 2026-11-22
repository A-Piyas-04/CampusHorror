# Map v2: the campus rebuilt from the official IUT board

**Resume here after any break or context loss.** This file is the checklist and log for the redesign that started on
22 November 2026, when the owner supplied `map-design/actual-map/` (a 4K photo of the official IUT campus board,
plus its legend 1–27) and called it the absolute truth. Approved plan:
`C:\Users\ACER\.claude\plans\analyze-map-design-actual-map-synthetic-graham-of-479e8dbf-52e9-4220-8314-fed978539615.md`.

Standing rules:
- Never ask the owner for decisions (D16). Record each one in `Docs/DECISIONS.md` instead.
- Never commit; checkpoint with `tools/checkpoint.sh <name>`. The pre-redesign state is `refs/checkpoints/pre-map-v2`.
- Visual smoothness ranks above feature count.

## What the board says (summary)

- The board is printed south-up. North-up, the highway is on the east, the Main Gate is at the SE corner ("You are
  here"), and the Southern Field lies to the south. Aerial 12 looks north; aerial 08 looks east to UB Hall (#9).
- Scale is 0.23 m per pixel of the north-up half-size photo; the campus is about 470 × 300 m.
- **Truth file:** `data/campus/campus_layout.json`. Tools:
  - `python tools/campus/layout_tools.py validate`: schema and sanity checks.
  - `... overlay`: `map-design/reference/board_overlay.png`.
  - `... check`: IoU of each site against the board's roof pixels. 24 of 27 sites score ≥ 0.77. The rest are
    UB Hall's gate canopy, #25's crenellations and #26's proposed-plot outline.
- **Cut off by the photo:** the NW corner (#24) and the SE corner (#1 Main Gate). Both are placeholders; a photo has
  been requested from the owner.

## Decisions (in `Docs/DECISIONS.md`)

| Decision | Summary |
|---|---|
| D42 | True north-up; supersedes D25 and retires D26 |
| D43 | True scale from the board |
| D44 | One seamless outdoor zone `campus`, built from the layout file; supersedes D28 |
| D45 | Explore mode; story parked behind `STORY_ENABLED` |
| D46 | Render contract v2 |
| D47 | Proposed sites are plots; #25 is a construction site |

## Checklist

### M0: Safety
- [x] Checkpoint `pre-map-v2` (137 uncommitted files preserved).
- [x] `map-design/.gdignore`: Godot no longer imports the 18 MB board photo. Stale `.import` files removed.
- [x] This file, and the memory pointer.

### M1: Layout file and map-design
- [x] `data/campus/campus_layout.json` (schema 1):
  - boundary, canal, ground, roads, 27 sites and 7 unlabelled structures;
  - trees (177), features, spawn.
- [x] `tools/campus/layout.py` (library) and `layout_tools.py` (validate / overlay / check).
- [x] `tools/campus/map_render.py`: board-style raster render, shared by the map-design PNG and the in-game map.
- [x] `tools/zones/export_map_design.py` rewritten:
  - draws from the layout plus the game scenes (campus doors, spawns and collision; interiors);
  - SVG layers include the aligned board reference;
  - JSON schema 2.
- [x] `map-design/README.md` and `new-areas/README.md` rewritten.
- [x] Decisions D42–D47 written into `Docs/DECISIONS.md`.

### M2: Explore mode (basic mechanics)
- [x] `Game.explore()` → start mode `"explore"` in `main.gd`; title menu shows Explore / Continue / Settings / Quit
  (`STORY_ENABLED = false` hides the chapters).
- [x] No director:
  - doors ignore locks;
  - lamps follow time of day;
  - stamina is off;
  - the lantern burns no fuel.
- [x] `SAVE_VERSION` 3. An explore save is the zone plus position.
- [x] `M` key: campus map screen (`assets/ui/campus_map.png` from `map_render`) with a you-are-here marker.
- [x] `T` key: time of day (dawn / day / golden / dusk / night), tweened.
- [x] Wheel: smooth zoom between 1.5 and 2.5.
- [x] `run_checks.sh`: story suites moved to `LEGACY_CHECKS`; feel suites and the validator self-test point at
  `campus`.

### M3: Visual pipeline v2
- [ ] Blender rig:
  - AgX;
  - normal pass → `_n.png` (2D tangent space);
  - shadow catcher → `_shadow.png`;
  - window mask → `_emit.png`.
- [ ] Scene writer:
  - `CanvasTexture` (diffuse + normal);
  - shadow sprite on the ground band;
  - `NightWindows` emit sprite.
- [x] Photo PBR textures (CC0) in `assets/source/textures/` with `LICENSES.md`.
- [x] `ground_splat.gdshader` and `tools/zones/ground_mask.py`:
  - splat masks at 4 px/m;
  - hex tiling;
  - kerbs;
  - AO;
  - ×0.643 foreshortening.
- [x] `water.gdshader` v2, with reflection sprites.
- [ ] Foliage:
  - species set;
  - `foliage_sway.gdshader`;
  - canopy / trunk split.
- [ ] Atmosphere:
  - `world_tint.gd` v2 (time of day) and moon light;
  - cloud shadows, fog, fireflies;
  - `post_grade.gdshader` with a Low / High setting.
- [ ] Player re-rendered with a normal pass.

### M4: The campus world
- [x] `tools/zones/campus_world.py` → `scenes/world/Campus.tscn`, plus its profile, manifest and registry entry. Buildings are massing models (`scripts/world/campus_massing.gd`) until their art lands.
- [ ] Ground, water, canal, wall and gates, roads, buildings (collision + fade), trees, props, doors, spawns.
- [x] Old exteriors retired:
  - unregistered;
  - scenes, manifests and baselines moved to `legacy/`;
  - `campus_zones.py` moved to `tools/zones/legacy/`.
- [ ] Building art in `author_campus.py` v2:
  - Tier A (photo-backed);
  - Tier B (from the aerials);
  - Tier C (plots).

### M5: Interiors reconnected
- [x] `campus_interiors.py` exits → `campus:<spawn>`; Chapter 1 rooms patched.
- [ ] `cds_veranda` regenerated running east–west.

### M6: Verify and hand over
- [ ] `run_checks.sh` green.
- [x] `CampusWorldCheck` (12 checks: wiring, swept flood fill, round trips through 11 doors, Explore basics).
- [ ] FeelProbe on `campus`: median ≤ 6.9 ms, p99 ≤ 10 ms.
- [ ] Captures in `Docs/screenshots/map_v2/`.
- [ ] Docs and memories updated.

## Log

- 22 Nov 2026: Board analysed; plan approved.
  - M0 done.
  - M1:
    - layout file traced, and checked against the board by IoU;
    - map-design regenerated from it (SVG with the aligned board reference, PNG, JSON v2, interiors with host
      buildings);
    - both READMEs rewritten.
- 22 Nov 2026: M2 and the first M4/M5 pass.
  - **Explore mode**: `Game.explore()`, `Game.story_active`, and doors, lamps and stamina gated on it.
  - **Time of day**: `world_tint.gd` v2 with five phases, tweened; `darkness` drives the lamps and the lantern.
  - **Map screen**: `scripts/ui/campus_map_screen.gd`, from `tools/campus/ui_map.py`.
  - **Wheel zoom**, and **save v3** (saved on quit in Explore).
  - The **title menu** shows Explore campus, Continue, Settings and Quit.
  - **`campus` zone generated**: ground polygons; lakes, canal and wall as collision (canal gaps at road crossings); a
    massing model per footprint part; 177 trees; 76 lamps that follow time of day; 11 doors; benches.
  - **Old exteriors** moved to `scenes/world/legacy/`. The validator self-test still mutates the legacy Main Gate
    scene as its fixture.
  - **Interiors** exit to `campus:<old spawn id>`.
  - **Checks**: the feel suites were retargeted to campus anchors and the story suites moved to `LEGACY`; the default
    suites all pass. Checkpoint `map-v2-m2-explore`.
- 22 Nov 2026: M3 and M4 visuals, after the owner insisted on real geometry and textures everywhere ("not a bunch of
  squares").
  - **Ground**: one splat shader with CC0 photo materials (Poly Haven) in texture arrays.
    - Stochastic hex tiling, height blending, per-layer grading, macro variation.
    - Baked sun shadows and AO from the layout; drifting cloud shadows.
    - Modelled kerbs (top, a sunlit face where the paving lies south, joints, contact shadow).
    - Lake and canal copings; the plaza's prayer-row grid.
  - **Water**: `water_v2` with masonry bank faces where the shore is north, and depth from a baked shore-distance
    texture (`campus_water.png`). Lakeside buildings are mirrored as reflections clipped to the lakes.
  - **Buildings**: `author_campus_v2.py`. The assembly generator gained photo-texture materials. The Mosque has a
    true half-disc recess; roofs are terrace tiles with clutter.
  - **Edges**: modelled modules for the boundary wall, lake parapets and bridge balustrades (`author_infra_v2.py`).
  - **Trees**: seven species configs.
  - **Post-processing**: grade, bloom, vignette, grain, with a Settings toggle.
  - Next: finish rendering the buildings, infrastructure and trees; regenerate `campus`; captures; re-run the
    checks and re-dump baselines.
  - Later: night-window variants (lit rooms) and hedges and flower beds along building fronts.
- 22 Nov 2026: Art batches and the first in-game review (v3 captures).
  - **Rendered**: all 34 buildings, 12 edge modules (wall, parapet, bridge in four directions), 5 court assets,
    7 tree species. `merge_embedded` joins a part standing mostly inside another into its layer.
  - **Black faces found and fixed in the pipeline** (`assets/source/blender/pipeline/`).
    - A layer partly buried in a layer behind it (a stair tower half inside its wing) rendered its buried faces
      unlit and black, drawn over the wing. The new per-layer `holdouts` let the layer behind cut it.
    - Wings standing against a main block left the block's hidden facade black. That only showed when a wing faded
      over the player (D31). Such a layer now has `covered_by` and renders twice: the exposed surfaces with real
      shadows, and the hidden ones lit as if open. `layer_fill.py` composites the first pass over the second.
    - The author script computes both from footprint overlaps and sort order.
  - **Stale-render tool**: `tools/campus/stale_renders.py` compares each config with its render record
    (generator parameters, layers, holdouts and covered_by), not file times. The author script also no longer
    rewrites every config on each run.
  - **Orphaned sprites**: `tools/campus/clean_sprites.py` removes layer PNGs, masks and night PNGs that no config
    renders any more.
  - **Ground**:
    - Brick paving is procedural, in real 240 × 115 mm bricks: herringbone on the plaza, 45° herringbone bond (the
      LGED HBB road) on brick roads and paths. Mortar or dirt joints, per-brick colour (over-burnt and pale ones),
      bevel normals; the photo is kept as grain. This removes the lattice of pale specks the non-stochastic photo
      showed.
    - Concrete is cast in 1.2 m slabs.
    - A per-layer `contrast` setting calms the busy concrete and asphalt photos.
  - **Roads**:
    - The Dhaka–Mymensingh highway runs outside the east wall (layout `highway`): two lanes each way, a median and
      earth shoulders.
    - Worn road paint (`road_paint.gdshader`): lane and edge lines, a zebra crossing and a speed breaker inside the
      Main Gate. Pitch lines use the same paint.
    - Asphalt kerbs are painted black and white.
    - Outside the wall is rough verge, not asphalt.
  - **Workshops**: corrugated-iron roofs (a new `corrugated` pattern with real bump). Each sawtooth is a patchwork
    of new, old and rusted sheets with translucent skylights, plus valley gutters, turbine ventilators and brick
    gable ends stepped to the profile.
  - **Five Fundamentals**:
    - plinths, round-arched passages with brick voussoirs, string courses and panels;
    - no fade, because the ghosts already show the player through thin fins.
  - **Doors**: the flat brick "threshold slabs" in front of every entrance are gone. The art models the steps.
  - **Capture tour**: three shots stood inside buildings (auditorium, Academic 1, South Hall), and that faded them.
    They are re-aimed, and close-ups of the plaza and the workshop roofs were added.

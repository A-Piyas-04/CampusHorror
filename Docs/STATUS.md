# Project status

Last updated: 13 October 2026

## Summary

Environment and Cursor ↔ Godot MCP connection are **verified**. Milestone 0 conventions are **Confirmed**, registered in `project.godot`, and **verified** by an automated test scene (6/6 checks, 0 errors, 0 warnings).

Milestone A is **verified through the MCP**: `scenes/core/Main.tscn` is the main scene and owns one placeholder `Player` (4-direction movement, `Camera2D`) inside a temporary walled test room. Movement, diagonal normalization, wall collision and camera follow passed with 0 errors / 0 warnings. A manual play-test with a real keyboard/gamepad is still pending.

Milestone B is **verified through the MCP**: a reusable `Interactable` component (`scenes/components/Interactable.tscn`), a player interaction sensor, an on-screen prompt, and one placeholder `InteractionTestBox` in the test room. Prompt show/hide, in-range-only triggering and the temporary result (colour toggle + Output message) passed with 0 errors / 0 warnings.

Milestone C is **verified through the MCP**: two placeholder zones (`TestZoneA`, `TestZoneB`), reusable `Door` and `SpawnMarker` components, and a minimal zone registry + swap in `Main`. A → B and B → A travel, correct spawn markers, one surviving Player instance over 4 round trips, prompts, camera and wall collision passed with 0 errors / 0 warnings.

Milestone D is **verified through the MCP**: a minimal in-memory `GameState` autoload (one set of collected IDs), a reusable `Pickup` component that uses the existing `Interactable`, and one placeholder pickup `test_pickup_01` in Test Zone A. Collecting records the ID and removes the pickup; after leaving Zone A and returning it stays gone. One Player, zone transitions and interaction still work; 0 errors / 0 warnings. Nothing is written to disk.

Milestone E is **verified through the MCP** (implemented on 8 October 2026, after Milestone F): a `SaveService` autoload writes one versioned JSON save (`user://save.json`) with the current zone ID, the player's feet position and the collected IDs, and loads it back into the same persistent Player. Temporary developer keys: F6 save, F9 load. Save → stop → restart → load restored the zone, exact position and collected pickup; doors still use their spawn markers afterwards. Missing, malformed, unsupported-version and invalid saves are reported and change nothing. 0 errors / 0 warnings in the normal flow.

Milestone F is **verified through the MCP** (rendering proof only, Compatibility renderer unchanged): a temporary `CanvasModulate` day/night tint in `Main` (toggled with a temporary F2 debug action), a temporary `PointLight2D` lantern inside the Player (toggled by the `lantern` action), and a `LightOccluder2D` on the Zone A pillar base. Day and night states, the light following the player, the toggle, ground shadows behind the pillar, an undarkened UI prompt, and movement/collision/interaction/zones all passed with 0 errors / 0 warnings. No lantern mechanics, day/night timing or gameplay effects exist.

Milestone G Part 1 (real campus map **blockout** + visual direction) is **verified through the MCP**: the game now starts in `main_gate_exterior`, an editable placeholder blockout of the real Main Gate area (gate, central field, paths, sports courts, CDS exterior, vegetation, south wall and road), connected by a door to `cds_veranda`, the covered CDS walkway with placeholder fronts for the three future CDS rooms. It reuses the existing Player, zones/doors/spawns, GameState, SaveService and lighting without changes. Layout and sizes are **approximate** and need the user's review (`Docs/CAMPUS_MAP.md`); visual direction is recorded in `Docs/ART_STYLE.md`. Navigation, the CDS round trip, camera, save/load, lighting and Y-sort passed with 0 errors / 0 warnings. **No final art exists**; this is not the art sample.

Milestone G Part 1 is accepted as a **structural prototype only**. An **editability cleanup** followed (no new art, no layout change): each logical landmark (Main Gate, CDS, each sports court, the veranda arcade) is now one parent node that owns all of its visual layers, including roofs/arches/canopies (a landmark `Overhead` child at z 10) and its own paving (z −9), plus the door/spawn it serves. Moving that one parent moves the whole landmark. Every blockout-only visual is marked as a placeholder (group `blockout_placeholder` + an `editor_description`). Collision, transitions, save/load and lighting were re-tested: identical results, 0 errors / 0 warnings.

Milestone G Part 2 (Blender → Godot asset pipeline) is **verified on one asset** (13 October 2026): the one-off red-brick wall test script was split into shared pipeline code (`assets/source/blender/pipeline/`), a wall generator (`generators/red_brick_wall.py`) and a per-asset config (`configs/red_brick_wall_3m.json`). One command (`python assets/source/blender/build_asset.py red_brick_wall_3m`) renders with Blender 5.2.2 LTS, validates the PNG and record, writes the reusable prop scene `scenes/props/architecture/RedBrickWall3m.tscn` (Sprite2D with footprint origin + optional collision) and a test preview, and checks both in Godot 4.7.2 headless. Result: 36/36 checks; the new PNG matches the approved `red_brick_wall_grid_test.png` (identical alpha, mean colour difference 0.08/255); Godot 0 errors / 0 warnings (headless and in the editor via MCP). Gameplay scenes, the original wall files and `WallAssetPreview.tscn` are unchanged. Guide: `Docs/ASSET_PIPELINE.md`. The wall is a pipeline proof, not approved final art.

Milestone G first architecture asset batch is **verified (automated)** on 13 October 2026, **pending visual approval**. Three new reusable asset types come from the same pipeline in one command (`build_asset.py red_brick_arch_doorway_3m red_brick_arch_window_3m red_brick_veranda_pier`): a pointed-arch brick doorway module (`RedBrickArchDoorway3m`, 1.40 m walk-through opening under a raised parapet), a pointed-arch window facade module (`RedBrickArchWindow3m`, see-through window with brick sill and steel grille), and a square veranda pier (`RedBrickVerandaPier`). They use the wall's camera, lights, materials and 220.69 px/m render scale (sprite scale 0.145). The doorway and window are brick-for-brick identical to `RedBrickWall3m` at their ends and drop into a wall run at 96 px spacing; the pier stands on joins and free ends. Result: 41/41, 41/41 and 37/37 checks, Godot 0 errors / 0 warnings. The doorway's collision leaves its 44.8 px opening free (a 28 px player footprint passes; walls, window, pier and jambs block). The wall still passes 41/41, re-renders identically (alpha identical, mean colour difference 0.08/255) and its files are unchanged. Proportions are approximate (CDS photo style), not surveyed; this is not approved final art.

## Environment — Verified

| Item | Value | Evidence |
|---|---|---|
| OS | Windows 10/11 (build 26100) | Cursor environment |
| Godot | **4.7.2 stable** (official, build `ed1daf0bf`) | MCP `get_runtime_status`; engine log |
| Renderer | **Compatibility** (`gl_compatibility`, OpenGL 3.3, NVIDIA GeForce RTX 3050 Laptop GPU) | `project.godot`; engine log |
| Node.js / npm / Git | v22.14.0 / 11.18.0 / 2.45.1 | Terminal |
| Godot MCP | `godot-mcp-server` via `npx` (server reported version 0.6.0); editor add-on `addons/godot_mcp`; WebSocket port 6505 | MCP `get_godot_status` |
| Project name | `CampusHorror` | `project.godot` |

## Verification log

| Date | Check | Result |
|---|---|---|
| 2026-10-07 | MCP read-only inspection (project, version, scene tree) | Pass |
| 2026-10-07 | MCPCheck integration test (`scenes/tests/MCPCheck.tscn`) | Pass: launched, rectangle visible, 0 errors / 0 warnings |
| 2026-10-07 | Milestone 0 test (`scenes/tests/Milestone0Test.tscn`), run alone through MCP | **Pass: 6/6 automated checks, 0 errors / 0 warnings.** Screenshots confirm behind-prop, in-front-of-prop, under-canopy and against-wall poses. |
| 2026-10-07 | Main scene setting | Set to `res://scenes/core/Main.tscn` (Milestone A) |
| 2026-10-07 | Display / renderer settings | Unchanged |
| 2026-10-07 | Milestone A test: `Main.tscn` run through MCP (as a specific scene and as the main scene) | **Pass: all checks below, 0 errors / 0 warnings** |
| 2026-10-07 | Milestone B test: `Main.tscn` run through MCP | **Pass: all checks below, 0 errors / 0 warnings.** A first run was discarded because the game window was also being played by hand at the same time; the clean re-run is what is recorded. |
| 2026-10-07 | Milestone C test: `Main.tscn` run through MCP | **Pass: all checks below, 0 errors / 0 warnings.** |
| 2026-10-07 | Milestone D test: `Main.tscn` run through MCP | **Pass: all checks below, 0 errors / 0 warnings.** |
| 2026-10-08 | Milestone E save/load test: `Main.tscn` run 3 times through MCP (save, restart, load; failure cases in a separate run) | **Pass: all checks below, 0 errors / 0 warnings in the normal flow; 3 intended errors in the failure-case run.** |
| 2026-10-07 | Milestone F lighting test: `Main.tscn` run through MCP (renderer still `gl_compatibility`) | **Pass: all checks below, 0 errors / 0 warnings.** A first run showed the pillar's own body darkened by its base shadow; fixed with the light-mask split (see `Docs/CONVENTIONS.md` §10) and fully re-run. |
| 2026-10-08 | Milestone G Part 1 blockout test: `Main.tscn` run 3 times through MCP (full test run; two short re-runs after a veranda label fix) | **Pass: all checks below, 0 errors / 0 warnings in every run.** |
| 2026-10-08 | Milestone G Part 1 editability cleanup regression: `Main.tscn` run 2 times through MCP (collision/transitions/landmark-move test; fresh run for save/load and lighting) | **Pass: all checks below, 0 errors / 0 warnings.** |
| 2026-10-13 | Milestone G architecture batch: `build_asset.py` batch of 3 assets; wall regression; `WallSeamTest.tscn` headless; `ArchitectureGalleryTest.tscn` headless and through MCP | **Pass: all checks below, 0 errors / 0 warnings.** |

Milestone G architecture batch checks (13 October 2026; logs in `assets/source/blender/logs/`, not tracked; screenshots in `addons/godot_mcp/cache/screenshots/architecture_gallery_*.png`, not tracked):

| Check | Result |
|---|---|
| Batch build (render 256 samples, validate, scene, preview, Godot headless): doorway 41/41, window 41/41, pier 37/37. Godot scene and preview loads: 0 error/warning lines. Build warnings: Blender HIP (known), `.import` mipmaps off (editor import race; fixed, recheck without render passes with no mipmap warning), Godot import notices about `addons/godot_mcp/cache/undo` copies (MCP tooling, not the assets) | Pass |
| All three: camera ortho 40° / 0°, no ground shadow, 220.690 px/m, sprite scale 0.145000, transparent border, margins ≥ 16 px, alpha bbox within 2.2 px of the projected design bounds | Pass |
| Doorway and window tiling checks: 0 fringe px at both ends, bleed matches the opposite end (mean RGB diff 1.08 / 1.07) | Pass |
| Doorway collision: `CollisionWestJamb` / `CollisionEastJamb` 25.6 × 6.17 px at x ∓35.2, nothing across the opening (asset check) | Pass |
| Join with the existing wall, measured on the PNGs (±8 px at both module ends vs `red_brick_wall_3m.png`): window mean RGB diff 0.80; doorway 2.19 (0.148 px off the wall's pixel grid, resampling floor 1.00); brightness offset < 1/255 | Pass |
| Wall regression: `build_asset.py red_brick_wall_3m --compare-to` the pre-batch PNG: 41/41, alpha identical, mean RGB diff 0.078 (max 1); scene and preview byte-identical. The wall `.blend`/PNG/record were then restored from Git (render noise only); the committed record still passes 37/37 with the updated check script | Pass |
| `WallSeamTest.tscn` headless | Pass: exit 0, no errors |
| Gallery footprint sweep (28 × 12 px, `test_move` 40 px north): doorway centre and 6 px off centre pass; wall, window, pier at join and doorway jamb (16 px off centre) block | Pass: 7/7 |
| Gallery through MCP at zoom 1, 2.5 and 5 (bare doorway/wall join with the pier hidden: no visible seam) | Pass: 0 errors (screenshots) |

Milestone 0 automated checks:

| Check | Result |
|---|---|
| 7 input actions registered | Pass |
| Physics layers 1–5 named `world`, `player`, `interactable`, `enemy`, `trigger` | Pass |
| Test character on layer 2 / mask 1; wall and prop on layer 1 / mask 0 | Pass |
| Feet origin (visual bottom and footprint bottom at y = 0; footprint 12 of 64 px tall) | Pass |
| Draw-order setup (ground z −10, Y-sorted objects z 0, overhead z 10) | Pass |
| Wall blocks character (travelled 86 of 300 px; footprint stopped at wall face x = 860) | Pass |

Milestone A checks (synthetic input through MCP; `move_speed` = 200):

| Check | Result |
|---|---|
| `move_right` / `move_left` / `move_up` / `move_down` actions → velocity (200, 0) / (−200, 0) / (0, −200) / (0, 200) | Pass |
| Diagonal (down + right actions; W + A keys) → velocity (±141.42, ±141.42), length 200 | Pass (normalized) |
| Releasing input → velocity (0, 0) | Pass |
| Synthetic `W` / `A` key events drive movement (physical-key bindings) | Pass |
| South-east corner: stopped at (786.0, 599.9) = east wall face 800 − 14 (half footprint), south wall face 600 | Pass |
| North-west corner: stopped at (−786.0, −588.0) = west wall face −800 + 14, north wall face −600 + 12 (footprint height) | Pass |
| Pillar base (collision 80 × 40 at the base only): walking up stopped at y = 12; player drawn in front of pillar | Pass |
| Camera: `Player/Camera` is current, zoom 1, no offset/smoothing; screen centre equals player feet position at both corners | Pass |
| Exactly one `CharacterBody2D` in the running tree (`/root/Main/World/Player`); root children are only `MCPRuntime` and `Main` | Pass |
| Player layer 2 / mask 1, `motion_mode` Floating; walls/pillar layer 1 / mask 0 | Pass |

Milestone B checks (player spawns at (0, 200); test box at (−250, 200); sensor radius 24 + interactable radius 32 → in range when the sensor centre is within 56 px of the box origin):

| Check | Result |
|---|---|
| Layers: `Player/InteractionArea` layer 0 / mask 4 (layer 3), monitoring on, monitorable off; `Interactable` layer 4 (layer 3) / mask 0, monitoring off, monitorable on | Pass |
| At spawn (250 px away): prompt hidden, no overlapping areas; `interact` action press → use count stays 0 | Pass |
| Approaching, still out of range (x = −140, 110 px away): prompt hidden, no overlap | Pass |
| At the box (x = −212, stopped by the box's 48 × 16 base collision): sensor overlaps `InteractionTestBox/Interactable`; prompt visible with text "Press E to interact" | Pass (screenshot) |
| `E` key press + release in range → exactly one use (count 1), box purple → yellow, `[INTERACT] InteractionTestBox used by Player (count 1)` printed | Pass (screenshot) |
| Leaving range (x = −125): prompt hidden; `E` press → count stays 1 | Pass (screenshot) |
| Re-entering range: prompt visible again; `interact` action → count 2, box back to purple, second `[INTERACT]` line | Pass |

Milestone C checks (Player instance ID recorded at start: `30953965084`). Some approaches used a test-only `set_global_position` to stand near a door; walking and wall stops were also tested directly.

| Check | Result |
|---|---|
| Start: `World` children = `TestZoneA`, `Player`; player at `start` marker (0, 150); `[ZONE] Entered 'test_zone_a' at spawn 'start'.` | Pass |
| Walking up to the A → B door: stopped by Zone A north wall at y = −288 (wall face −300 + 12 px footprint); prompt "Press E to enter Test Zone B" | Pass (screenshot) |
| `E` at the door → `World` children = `TestZoneB`, `Player`; player at (0, 170) = `by_south_door` (not `center`, which is first in the tree); same instance ID; prompt hidden; camera centre (0, 170) | Pass (screenshot) |
| Walking down in Zone B: stopped by south wall at y = 249.9 (wall face 250); prompt "Press E to return to Test Zone A"; camera follows | Pass (screenshot) |
| `interact` at the B → A door → `TestZoneA` loaded; player at (−250, −220) = `by_north_door` (not `start`); same instance ID | Pass (screenshot) |
| 3 more A → B → A round trips (8 transitions total): each `[ZONE]` line names the correct zone and spawn | Pass |
| After repeated transitions: exactly one `CharacterBody2D` (`/root/Main/World/Player`), same instance ID `30953965084`; `World` has exactly one zone + Player; nodes 43 / objects 1629 / orphans 0, identical to after the first round trip (old zones are freed) | Pass |
| Milestone B regression in reloaded Zone A: test box base stops player at y = 112; prompt "Press E to interact"; `E` → use count 1, box turns yellow; camera centre = player | Pass (screenshot) |
| Y-sort across Main/zone: player hidden behind the Zone B door when standing just above its base; drawn in front of the Zone A test box when below it | Pass (screenshots) |

Milestone D checks (Player instance ID recorded: `31306286622`). Synthetic movement input arrived with too much latency for precise approaches (holding a direction overshot across the room), so the player was placed next to the pickup and doors with the test-only `Player.teleport()`; every collection and door use went through a real synthetic `E` key press.

| Check | Result |
|---|---|
| `/root` children: `MCPRuntime`, `GameState`, `Main`; `GameState.get_collected_ids()` = `[]` at start | Pass |
| First visit: `TestZoneA/Objects/TestPickup01` exists at (120, 200), `pickup_id` `test_pickup_01`, visible | Pass (screenshot) |
| 90 px below the pickup: prompt hidden. In range: prompt "Press E to pick up" | Pass |
| `E` in range → `[PICKUP] Collected 'test_pickup_01'.`; `GameState.get_collected_ids()` = `["test_pickup_01"]`; `TestPickup01` removed from `Objects`; prompt hidden although the player didn't move (freed target dropped) | Pass |
| Zone A door with `E` → `TestZoneB` at `by_south_door` (0, 170); Zone B door with `E` → `TestZoneA` at `by_north_door` (−250, −220) | Pass |
| After returning: `Objects` has no `TestPickup01`; GameState still `["test_pickup_01"]`; standing at the old spot shows no pickup and no prompt | Pass (screenshot) |
| Milestone B regression in the reloaded Zone A: test box prompt "Press E to interact"; `E` → `[INTERACT] InteractionTestBox used by Player (count 1)` | Pass |
| 2 more A → B → A round trips via `Main.change_zone` (6 zone changes total): pickup still absent; `World` = `TestZoneA` + `Player`; same Player instance ID; nodes 44 (Milestone C's 43 + `GameState`), orphans 0 | Pass |
| Errors / warnings during and after the run | 0 / 0 |

Milestone F checks (screenshots in `addons/godot_mcp/cache/screenshots/mf_*.png`, not tracked by Git). Approaches again used `Player.teleport()`; toggles used synthetic `F2` / `F` key presses and the matching actions.

| Check | Result |
|---|---|
| Start: `DayNightTint` color white, `is_night` false; `Player/Lantern` enabled, shadows on, at feet + (0, −16) | Pass |
| Day state: world at normal brightness, lantern adds a warm glow around the player | Pass (screenshot) |
| `F2` → `[LIGHTING] Night tint.`; tint (0.1, 0.11, 0.2); world dark except the lantern pool | Pass (screenshot) |
| Lantern follows the player: light at (0, 134) / (70, −16) / (162, 194) for feet (0, 150) / (70, 0) / (162, 210) | Pass |
| `F` → `[LIGHTING] Lantern off.`, `enabled` false, only the dim tint remains; `lantern` action → `Lantern on.` | Pass (screenshot) |
| Occlusion: player west of the pillar → shadow wedge on the ground east of the pillar base; pillar body itself fully lit (light mask 2) | Pass (screenshot) |
| Player south of the pillar → pillar front lit, not blacked out by its own base shadow | Pass (screenshot) |
| UI at night: prompt "Press E to pick up" drawn full white (Label modulate 1,1,1,1), not tinted | Pass (screenshot) |
| Interaction at night: `E` → `[PICKUP] Collected 'test_pickup_01'.`, GameState `["test_pickup_01"]` | Pass |
| Zones at night: A → B (`by_south_door`) and B → A (`by_north_door`) through doors with `E`; night tint and lantern persist in Zone B; pickup still absent on return | Pass (screenshot) |
| Movement/collision: holding `move_up` from (−250, −220) stopped at y = −287.9 (north wall face −300 + 12 px footprint), velocity 0 | Pass |
| `debug_toggle_night` action → back to day (white) | Pass |
| `World` = one zone + `Player`; nodes 47 (44 + `DayNightTint`, `Lantern`, `Occluder`), orphans 0 | Pass |
| Save/load regression | Not run at the time (Milestone E didn't exist yet); covered by the Milestone E checks below |
| Errors / warnings | 0 / 0 |

Milestone E checks (3 runs of `Main.tscn`; no save file existed beforehand). Approaches used `Player.teleport()`; the saved position itself came from walking into a wall.

| Check | Result |
|---|---|
| `/root` children: `MCPRuntime`, `GameState`, `SaveService`, `Main`; 0 errors at startup | Pass |
| Load with no save file → `[SAVE] No save file at '…'; nothing loaded.`, returns false, no crash, nothing changed | Pass |
| Run 1: collect `test_pickup_01` with `E`; Zone A door with `E` → Zone B; holding `move_left` stopped the player at the west wall (−285.92, −100) | Pass |
| `F6` → save file written with `save_version` 1, `zone_id` `test_zone_b`, `player_position` (−285.924011230469, −100.0), `collected_ids` `["test_pickup_01"]`; 0 errors | Pass |
| Stop the game; run 2 starts fresh: Zone A at `start` (0, 150), pickup present, GameState empty | Pass |
| `F9` → `[SAVE] Loaded 'test_zone_b' at (-285.924, -100.0) with 1 collected id(s).`; `World` = `TestZoneB` + `Player`; feet at exactly (−285.924, −100); camera centred on the player; GameState `["test_pickup_01"]` | Pass (screenshot) |
| Same Player instance before and after load (instance ID unchanged within the run); exactly one Player | Pass |
| Door rule after load: Zone B door with `E` → Zone A at the `by_north_door` marker (−250, −220), not the saved position; `TestPickup01` absent | Pass |
| Loading again from Zone A → back in Zone B at the saved position; nodes 39, orphans 0 | Pass |
| Run 2 errors / warnings | 0 / 0 |
| Run 3 (failure handling; these errors are expected): truncated JSON → `malformed JSON …`; `save_version` 2 → `unsupported save_version 2 (this build reads version 1)`; `zone_id` "nowhere" → `'zone_id' "nowhere" is not a known zone`; each ends with `Nothing was changed.`, returns false; Zone A, player (0, 150) and empty GameState untouched afterwards | Pass (3 intended errors) |
| Restored the good save, `debug_load` then `debug_save` actions → loaded and re-saved identically; file now lists `save_version` first; 0 errors after the failure tests | Pass |

Milestone G Part 1 checks (Player instance ID recorded: `32514246182`; screenshots in `addons/godot_mcp/cache/screenshots/`, not tracked by Git; overview: `screenshot_20260.png`). Approaches used `Player.teleport()`; stops were reached by holding a move action; doors used synthetic `E` key presses.

| Check | Result |
|---|---|
| Startup: `[ZONE] Entered 'main_gate_exterior' at spawn 'main_gate_entry'.`; `World` = `MainGateExterior` + `Player`; `/root` = `MCPRuntime`, `GameState`, `SaveService`, `Main`; 0 errors | Pass (screenshot) |
| Gate: `move_down` from (−1390, 1300) in the gate passage stopped at y = 1389.9 (closed gate leaves at 1390); player drawn behind the see-through gate leaves; lantern light passes between the piers | Pass (screenshot) |
| CDS wall: `move_right` from (1400, −700) stopped at x = 1466.0 (veranda face 1480 − 14) | Pass (screenshot) |
| Court fence: `move_down` inside the futsal court stopped at y = 1144.0 (south fence 1150 − 6); player drawn behind the fence | Pass (screenshot) |
| At `outside_cds_entrance` (1380, −200): prompt hidden. Walking right stopped at x = 1465.9 by the door: prompt "Press E to enter the CDS veranda" | Pass (screenshot) |
| `E` → `World` = `CdsVeranda` + `Player`; player at `inside_cds_entry` (0, −50); same instance ID | Pass (screenshot) |
| Veranda: `move_left` stopped at x = −115.9 (parapet face −130 + 14); prompt "Press E to go out to the field"; the overhead roof edge covers the player | Pass (screenshot) |
| `E` → `MainGateExterior` at `outside_cds_entrance` (1380, −200); same instance ID; camera screen centre (1380, −200) | Pass |
| Save/load: save at (300, 200) in the exterior → go to the veranda → `F9` → `main_gate_exterior` at (300, 200). Save at (50, 400) in the veranda → load from the exterior → `cds_veranda` at (50, 400). Save in `test_zone_a` at `start` → load from the exterior → `TestZoneA` at (0, 150) | Pass |
| Lighting: `F2` → `is_night` true, tint (0.1, 0.11, 0.2); lantern pool follows the player and lights the CDS roof without cutting it off at the building edge (light mask 2); `F` → lantern `enabled` false; night tint persists in `cds_veranda`; prompt Label drawn white (modulate 1,1,1,1) at night; `debug_toggle_night` → day | Pass (screenshots) |
| Y-sort: player north of a palm (y −20 vs trunk y 0) drawn behind the trunk; south of it (y 40) drawn in front; tree south of the player at CDS drawn over the player | Pass (screenshots) |
| After about 12 zone changes and loads: `World` = one zone + `Player`; nodes 329, orphans 0; 145 fps | Pass |
| Errors / warnings in all 3 runs | 0 / 0 |

Milestone G Part 1 editability cleanup checks (same approach as above; the user's `save.json` was backed up before the save tests and restored afterwards, still `test_zone_a` (0, 150)):

| Check | Result |
|---|---|
| Scene files parse (MCP `read_scene`); after the runs `git status` shows only the 5 edited scenes changed (no editor re-saves) | Pass |
| Startup: `main_gate_exterior` at `main_gate_entry` (−1390, 960), now `MainGateLandmark/SpawnMainGateEntry`; gate roof, "MAIN GATE" label, arch and pavilion canopy look identical to before | Pass (screenshot) |
| Gate: `move_down` from (−1390, 1250) stopped at y = 1389.9, same as before | Pass (screenshot) |
| `DoorCdsMainEntry` (now under `CDSExterior/TableTennis`) at world (1452, −200), destination `cds_veranda` / `inside_cds_entry`; `SpawnOutsideCdsEntrance` at world (1380, −200): unchanged world positions | Pass |
| CDS wall: `move_right` from the spawn stopped at x = 1465.9; prompt "Press E to enter the CDS veranda"; forecourt and entrance canopy drawn as before | Pass (screenshot) |
| `E` → `cds_veranda` at (0, −50). Veranda: `move_left` stopped at x = −115.9; roof edge (now `Objects/Arcade/Overhead`) covers the player; prompt "Press E to go out to the field"; `E` → `main_gate_exterior` at (1380, −200) | Pass (screenshots) |
| Court fence: `move_down` from (−200, 1050) stopped at y = 1143.9, same as before; court surface (now z −9) drawn normally | Pass (screenshot) |
| **Move test** (runtime `set_position` on the parent only): `FutsalCourt` → (−600, −500), north of the zone origin: apron, surface, markings and fences all moved and the surface stays visible above the field; fence collision moved too (stop at y = −356.1 = −500 + 143.9) | Pass (screenshot) |
| **Move test**: `MainGateLandmark` → (−600, 500): piers, leaves, pavilion, columns, plaza, roof, label, arch and canopy all moved together | Pass (screenshot) |
| **Move test**: `CDSExterior` → (1275, −300): all sections, forecourt, entrance canopy and door moved; the door prompt still appears at the new place | Pass (screenshot) |
| Save/load: save at (1000, 300) in the exterior → change to the veranda → load → `main_gate_exterior` (1000, 300). Save at (20, 400) in the veranda → change to the exterior → load → `cds_veranda` (20, 400) | Pass |
| Lighting: `F2` night at the CDS entrance: tint applied, lantern pool follows the player, CDS wall occludes the light behind it, prompt stays white | Pass (screenshot) |
| Placeholder groups at runtime: `MainGateLandmark/PierWest` (from `BlockoutBlock.tscn`) and `MainGateLandmark/Overhead` are in `blockout_placeholder`; the gate overhead has `z_index` 10 | Pass |
| Performance / errors: 145 fps, orphans 0, errors / warnings 0 / 0 | Pass |

## Milestones

| Milestone | Status |
|---|---|
| Environment / MCP setup | **Verified** |
| 0. Project conventions | **Verified** (automated). Conventions Confirmed in `Docs/CONVENTIONS.md`; input actions + layer names registered; test scene passes. Manual real-device input check pending. |
| A. Main, placeholder player, movement, camera | **Verified** (automated, via MCP). Manual real-device play-test pending. |
| B. Interaction | **Verified** (automated, via MCP). Manual play-test pending. |
| C. Zones, doors, spawn markers | **Verified** (automated, via MCP). Manual play-test pending; new conventions in `Docs/CONVENTIONS.md` §3 and §8 are Proposed. |
| D. GameState + persistent pickup | **Verified** (automated, via MCP). In-memory only. Manual play-test pending; new convention in `Docs/CONVENTIONS.md` §9 is Proposed. |
| E. SaveService | **Verified** (automated, via MCP). One JSON save, version 1; temporary F6/F9 keys. Manual play-test pending; new convention in `Docs/CONVENTIONS.md` §11 is Proposed. |
| F. Lighting test | **Verified** (automated, via MCP). Rendering proof only; temporary tint/lantern scripts. Manual visual check pending; new convention in `Docs/CONVENTIONS.md` §10 is Proposed. |
| G Part 1. Real campus blockout (Main Gate area) + visual direction | **Verified** (automated, via MCP) as a **blockout only**; accepted as a structural prototype. Editability cleanup done and regression-tested (landmarks movable from one parent, placeholders marked). Layout approximate, pending the user's map review (`Docs/CAMPUS_MAP.md`). Convention `Docs/CONVENTIONS.md` §12 (amended by the cleanup) is Proposed. |
| G Part 2. Blender → Godot 2.5D asset pipeline | **Verified** (automated) on the red-brick wall only. Pipeline proof; art not approved. Convention `Docs/CONVENTIONS.md` §13 is Proposed. Manual visual check pending. |
| G. First architecture asset batch (doorway, window, pier) | **Verified** (automated + MCP gallery). Visual approval pending (manual check 20). Not placed in any zone; the blockout is unchanged. |
| G. Custom art sample / final campus art | Not started |
| H. Desktop export | Not started |

### Manual checks for the user

1. Open `scenes/tests/Milestone0Test.tscn`, press F6, and press W/A/S/D, the arrow keys, E, F and Escape (and a gamepad, if available). Each should appear in the top-left "Actions pressed" readout. If a real device doesn't register, see the device note in `Docs/CONVENTIONS.md` §1.
2. Watch the pose cycle (every 2 s) and confirm the draw order looks right to you.
3. Press F5 (runs `Main.tscn`, starting in Test Zone A). Walk with WASD, the arrow keys and a gamepad (stick + D-pad); check the feel of the speed (200 px/s, adjustable as `move_speed` on the Player in the Inspector), that walls and the orange pillar block you, that you can walk behind/in front of the pillar, and that the camera follows.
4. Open the hand-written scenes (`Main.tscn`, `Player.tscn`, `Interactable.tscn`, `InteractionPrompt.tscn`, `InteractionTestBox.tscn`, `Door.tscn`, `SpawnMarker.tscn`, `TestZoneA.tscn`, `TestZoneB.tscn`) in the editor once and save them (Ctrl+S) so Godot writes their `uid` headers (they load fine either way).
5. Milestone B: walk to the purple box in Zone A. Check the prompt appears/disappears at a distance that feels right, E (and the gamepad's bottom face button) toggles the box colour and prints `[INTERACT] …` in Output, and nothing happens when pressing E away from the box. The prompt text says "E" even when using a gamepad (placeholder text).
6. Milestone C: in Zone A walk to the brown door on the north wall (upper left) and press E → Zone B (blue-grey floor), arriving just above its south-wall door. Press E at that door → back to Zone A, arriving just below the north door. Repeat a few times; check the change feels acceptable (it is an instant cut, no fade), the Output shows matching `[ZONE] …` lines, and nothing is left over from the previous zone. Open `TestZoneA.tscn`/`TestZoneB.tscn` and check the doors' and markers' Inspector fields.
7. Review the Proposed conventions in `Docs/CONVENTIONS.md` §3 (zone/player Y-sort) and §8 (zones, doors, spawn markers) and confirm or change them.
8. Milestone D: press F5, walk right of the start position to the small yellow diamond, check the "Press E to pick up" prompt and press E. It should vanish, the prompt should disappear immediately, and Output should show `[PICKUP] Collected 'test_pickup_01'.` Go through the north door to Zone B and back; the diamond must not reappear. Stop and restart the game without loading: it **does** reappear (a fresh start doesn't load the save automatically). Open `TestZoneA.tscn`, select `Objects/TestPickup01` and check `Pickup Id` / `Prompt Text` in the Inspector; open and save `Pickup.tscn` once (Ctrl+S) so Godot writes its `uid` header. Check Project Settings → Globals → Autoload lists `GameState`.
9. Review the Proposed convention in `Docs/CONVENTIONS.md` §9 (GameState and persistent pickups).
10. Milestone F: press F5 and click into the game window. Press **F2** to switch day ↔ night and **F** (or the gamepad's left face button) to switch the lantern on/off. At night walk around: the warm light should follow you smoothly; walk to the left of the orange pillar and check its shadow falls on the floor to the right while the pillar itself stays lit; stand by the yellow pickup and check the "Press E to pick up" prompt stays bright white. Judge whether the night colour, lantern radius (~256 px) and warmth are acceptable as placeholders; they are exported on `Main/DayNightTint` (`night_color`) and `Player/Lantern` (`color`, `texture_scale`, `energy`). Go through both doors at night. Also check F2 doesn't trigger anything in the editor while the game window is focused.
11. Review the Proposed convention in `Docs/CONVENTIONS.md` §10 (lighting) and the temporary `debug_toggle_night` action in §1.
12. Milestone E: press F5 and click into the game window. Collect the yellow diamond, walk somewhere recognizable (e.g. into a corner of Zone B), press **F6**; Output shows `[SAVE] Saved …` with the file path. Open that file (`%APPDATA%\Godot\app_userdata\CampusHorror\save.json`) and check it's readable. Stop and restart (you start in Zone A with the diamond back), press **F9**: you should appear in the saved spot, and the diamond must stay gone when you walk back to Zone A through the door (arriving at the door, not the saved spot). Also try F9 after deleting the file (message, no crash) and after breaking the JSON by hand (clear error, nothing changes). The machine already has a save from the MCP test (Zone B west wall, pickup collected); delete it if you want a clean start.
13. Review the Proposed convention in `Docs/CONVENTIONS.md` §11 (save/load) and the temporary `debug_save` / `debug_load` actions in §1.
14. Since Milestone G Part 1 the game starts at the Main Gate, and the test zones are no longer reachable by walking. For checks 3–12, temporarily set `Start Zone Id` = `test_zone_a` and `Start Spawn Id` = `start` on the `Main` node in the Inspector (don't save, or set them back to `main_gate_exterior` / `main_gate_entry`). The existing save file on this machine now points to `test_zone_a` (0, 150) from the MCP test; F9 still works with it.
15. Milestone G Part 1 map review: press F5 and walk the area: north up the palm path from the gate, around the field, past the courts, to the CDS forecourt on the east side. Press E at the brown door on CDS, walk the veranda, and go back out. Compare everything with the real campus and with the "Needs the user's campus knowledge" list in `Docs/CAMPUS_MAP.md` (section F). Fix what's wrong directly in `scenes/world/MainGateExterior.tscn` / `CdsVeranda.tscn` (see "How to edit the map in Godot" in that doc) or list corrections for the next task.
16. Open `MainGateExterior.tscn` in the editor once and save it (Ctrl+S). The same applies to `CdsVeranda.tscn`, `BlockoutBlock.tscn`, `PalmTree.tscn` and `Tree.tscn`; saving writes their `uid` headers. Select a CDS block and change `Footprint Size` / `Wall Height` to confirm the shape and collision preview update live.
17. Review `Docs/ART_STYLE.md` and the Proposed convention in `Docs/CONVENTIONS.md` §12 (map blockout pieces).
18. Editability cleanup: open `MainGateExterior.tscn`, select `Objects/Buildings/MainGateLandmark` and drag it. Roof, arch, label, canopy, plaza and arrival spawn should all follow; press Ctrl+Z afterwards. Do the same with `CDSExterior` and a court. In the Scene dock, hover a node to see its "BLOCKOUT PLACEHOLDER" description, and check Node panel > Groups for `blockout_placeholder`. Review the amended §12 rules (landmark `Overhead` child, landmark ground at z −9, doors/spawns inside landmarks, placeholder group).
19. Milestone G Part 2: open `scenes/tests/asset_previews/RedBrickWall3mPreview.tscn` and press F6. Check that the wall's base sits on the red footprint outline, that the yellow origin dot is at the footprint centre, that the wall's height looks right next to the blue 2 m reference, and how the two side-by-side modules join (a thin light line is visible at the seam). Open `scenes/props/architecture/RedBrickWall3m.tscn` in the editor once. Optionally run `python assets/source/blender/build_asset.py red_brick_wall_3m` yourself (about 15 s).
20. Architecture batch: open `scenes/tests/asset_previews/ArchitectureGalleryTest.tscn` and press F6 (zoom 1 = gameplay scale; Output shows `[GALLERY] PASS (7/7)`). Judge the doorway, window and pier next to the wall: proportions against the real CDS arches, the raised parapet over the doorway, the grille, the pier height, and the joins (wall | window at x 48 and 144 are bare joins). Open the per-asset previews `RedBrickArchDoorway3mPreview.tscn`, `RedBrickArchWindow3mPreview.tscn`, `RedBrickVerandaPierPreview.tscn` (zoom 4) for the footprint and origin. Approve, or list changes as config/generator parameters (e.g. `opening_width`, `parapet_courses`, `body_courses`).

## Project contents

- `scenes/tests/MCPCheck.tscn`: temporary MCP test scene. Not the main scene; safe to delete later.
- `scenes/tests/Milestone0Test.tscn` + `milestone_0_test.gd`: Milestone 0 conventions test (placeholder shapes; character moved by the test, not by player input). Not the main scene.
- `addons/godot_mcp/`: MCP editor add-on (registers the `MCPRuntime` autoload used for runtime inspection/screenshots).
- `project.godot`: 7 input actions + 3 TEMPORARY debug actions (`debug_toggle_night` F2, `debug_save` F6, `debug_load` F9) and 5 named 2D physics layers registered; main scene = `res://scenes/core/Main.tscn`; autoloads `MCPRuntime` (MCP add-on), `GameState`, `SaveService`. Renderer unchanged (`gl_compatibility`).
- `scripts/core/save_service.gd` (autoload `SaveService`, no `class_name`): the only code that touches the save file. `SAVE_PATH` = `user://save.json` (on this machine `C:/Users/ACER/AppData/Roaming/Godot/app_userdata/CampusHorror/save.json`), `SAVE_VERSION` = 1. `save_game() -> bool` reads the zone ID and feet position from `Main` and the collected IDs from `GameState`, writes tab-indented JSON. `load_game() -> bool` validates the whole file (JSON object, whole-number `save_version` equal to 1, known `zone_id`, numeric `player_position.x/y`, array of non-empty string `collected_ids`), then `GameState.restore_collected_ids()` and `Main.enter_zone_at_position()`. Any problem → `push_error("[SAVE] Can't load …: <reason>. Nothing was changed.")`, returns false. No file → prints a note, returns false. `has_save()`. TEMPORARY: `debug_save` / `debug_load` actions call save/load from `_unhandled_input`. Save format:

  ```json
  {
  	"save_version": 1,
  	"zone_id": "test_zone_b",
  	"player_position": { "x": -285.924011230469, "y": -100.0 },
  	"collected_ids": ["test_pickup_01"]
  }
  ```
- `scripts/lighting/day_night_test_tint.gd` (TEMPORARY, on `Main/DayNightTint`, `CanvasModulate`): exported `day_color` (white), `night_color` (0.1, 0.11, 0.2), `is_night` (default false; setter applies the colour). `debug_toggle_night` flips it and prints `[LIGHTING] Day/Night tint.` No clock, no transitions.
- `scripts/lighting/lantern_test_light.gd` (TEMPORARY, on `Player/Lantern`, `PointLight2D`): the `lantern` action flips `enabled` and prints `[LIGHTING] Lantern on/off.` Nothing else.
- `scripts/core/game_state.gd` (autoload `GameState`, no `class_name` so it doesn't clash with the autoload name): in-memory only. `_collected_ids: Dictionary[String, bool]` used as a set. `mark_collected(id)` (empty id → error), `is_collected(id)`, `get_collected_ids()`, `restore_collected_ids(ids)` (replaces the whole set; used by loading). Starts empty on every launch; no disk I/O (SaveService does that).
- `scenes/components/Pickup.tscn` + `scripts/components/pickup.gd` (`class_name Pickup`, `Node2D`): yellow 20×24 diamond `Body` above the origin + `Interactable` child, no collision. Exported `pickup_id` (stable ID, set in the Inspector) and `prompt_text`. `_ready`: empty id → error; already collected in GameState → `queue_free()` before the player can see or reach it. On `interacted`: `GameState.mark_collected(pickup_id)`, prints `[PICKUP] Collected '<id>'.`, `queue_free()`.
- `scenes/core/Main.tscn`: main scene. Tree:

  ```text
  Main (Node2D, scripts/core/main.gd)
  ├── DayNightTint (CanvasModulate, TEMPORARY day_night_test_tint.gd)   tints the whole world canvas; UI layers unaffected
  ├── World (Node2D, y_sort_enabled)          world container; the current zone is added here at runtime
  │   └── Player (instance of Player.tscn)    the one persistent player
  └── UI (Node)
      └── InteractionPrompt (instance of scenes/ui/InteractionPrompt.tscn, CanvasLayer 10)
  ```

  Connection in `Main.tscn`: `World/Player.interaction_target_changed` → `UI/InteractionPrompt._on_player_interaction_target_changed`.

- `scripts/core/main.gd` (`class_name Main`, added in Milestone E so SaveService can type it): owns zone switching. `ZONE_SCENES` (`zone_id` → scene path) is the whole zone registry. Exported `start_zone_id` / `start_spawn_id` (script defaults `test_zone_a` / `start`; `Main.tscn` sets `main_gate_exterior` / `main_gate_entry` since Milestone G Part 1). `change_zone(zone_id, spawn_id)` validates the zone and spawn before touching anything, removes + frees the old zone, adds the new one as `World`'s first child, connects its doors' `travel_requested`, calls `Player.teleport(marker.global_position)` and prints `[ZONE] Entered '<zone>' at spawn '<spawn>'.` Door requests are applied deferred (end of frame) and always use `change_zone()`. `enter_zone_at_position(zone_id, feet_position) -> bool` does the same swap but teleports to a saved global feet position (used only by loading; prints `[ZONE] Entered '<zone>' at position (x, y).`). Also `has_zone()`, `get_current_zone_id()`, `get_player_feet_position()`. The game always starts fresh at `start_zone_id`/`start_spawn_id`; it never loads automatically.
- `scenes/world/TestZoneA.tscn` (`zone_id` `test_zone_a`): green 800×600 room (interior x −400..400, y −300..300), walls, orange pillar at (200, 0) (`Body` light mask 2; `Occluder` = `LightOccluder2D` covering the 80×40 base), `InteractionTestBox` at (−200, 100), TEMPORARY `TestPickup01` (`pickup_id` `test_pickup_01`, prompt "Press E to pick up") at (120, 200), `DoorToZoneB` at (−250, −300) on the north wall → `test_zone_b` / `by_south_door`, spawns `start` (0, 150) and `by_north_door` (−250, −220).
- `scenes/world/MainGateExterior.tscn` (`zone_id` `main_gate_exterior`, Milestone G Part 1): real-campus blockout of the Main Gate area. `Ground` (shared terrain only: field, paths, road, sidewalk), `Objects/SportsCourts` (`FutsalCourt`, `TennisCourt`: each owns its z −9 apron/surface, markings and fences), `Objects/Buildings/MainGateLandmark` (piers, leaves, pavilion, z −9 `GatePlaza`, spawn `main_gate_entry` (−1390, 960), `Overhead` z 10 with roof/label/arch/pavilion canopy) and `CDSExterior` (sections `Canteen`, `TableTennis`, `IndoorBasketball`; `TableTennis` also owns the z −9 `Forecourt`, `DoorCdsMainEntry` → `cds_veranda` / `inside_cds_entry`, spawn `outside_cds_entrance` (1380, −200) and `Overhead/EntranceCanopy`), `Objects/Boundary` (south wall, prototype edges), `Objects/Vegetation` (27 palms, 15 trees). No zone-level `Overhead`, `Transitions` or `SpawnMarkers` nodes any more. Full layout, accuracy and editing guide in `Docs/CAMPUS_MAP.md`.
- `scenes/world/CdsVeranda.tscn` (`zone_id` `cds_veranda`): covered walkway (x −150..120, y −850..850), CDS building mass to the east, end walls, west parapet + 10 arcade columns, non-interactive `FutureFronts` (canteen, table tennis, indoor basketball), `DoorCdsExitToField` → `main_gate_exterior` / `outside_cds_entrance`, spawn `inside_cds_entry` (0, −50), roof edge at `Objects/Arcade/Overhead/VerandaRoofEdge` (z 10, moves with the arcade). `Ground`, `FutureFronts` and the arcade `Overhead` are marked placeholders.
- `scenes/world/blockout/BlockoutBlock.tscn` + `scripts/world/blockout_block.gd` (`@tool`, `class_name BlockoutBlock`, `StaticBody2D` layer 1 / mask 0, light mask 2): faux-3D placeholder block. Exports `footprint_size`, `wall_height`, `wall_color`, `roof_color`, `arch_count`, `arch_color`, `casts_shadow`. Draws the roof above the footprint plus the front face (with optional pointed arches); creates its collision rectangle and `LightOccluder2D` from the footprint as internal (unsaved) children, so they update in the editor. Scene root is in group `blockout_placeholder`, so every instance is marked.
- `scenes/props/PalmTree.tscn`, `scenes/props/Tree.tscn`: placeholder vegetation (`StaticBody2D`, trunk-base origin, small circle collision, trunk + canopy `Polygon2D`s on light mask 2, no occluder). Roots in group `blockout_placeholder`.
- Placeholder marking (editability cleanup): node group `blockout_placeholder` + `editor_description` "BLOCKOUT PLACEHOLDER: …" on every blockout-only visual (the group covers descendants). Landmark parents carry a "Logical landmark root" description instead; they are structure, not placeholders. Nothing in code reads the group yet; it is for finding/replacing placeholders in the editor.
- `scenes/world/TestZoneB.tscn` (`zone_id` `test_zone_b`): blue-grey 600×500 room (interior x −300..300, y −250..250), walls, spawns `center` (0, 0) and `by_south_door` (0, 170), `DoorToZoneA` at (0, 250) on the south wall → `test_zone_a` / `by_north_door`.
- `scripts/world/zone.gd` (`class_name Zone`): exported `zone_id`; `find_spawn_marker(spawn_id)`, `get_spawn_markers()`, `get_doors()`; reports empty/duplicate `spawn_id`s as errors on `_ready`.
- `scenes/components/Door.tscn` + `scripts/components/door.gd` (`class_name Door`, `Node2D`): brown 48×64 placeholder `Body` + `Interactable` child. Exported `destination_zone_id`, `destination_spawn_id`, `prompt_text` (copied into its Interactable if not empty). On `interacted` it emits `travel_requested(destination_zone_id, destination_spawn_id)`; it has no other logic.
- `scenes/components/SpawnMarker.tscn` + `scripts/components/spawn_marker.gd` (`class_name SpawnMarker`, `Marker2D`): exported `spawn_id`; its position is the arrival feet position. Editor-only gizmo, invisible in game.

- `scenes/player/Player.tscn`: reusable placeholder player. Root `Player` (`CharacterBody2D`, layer 2 / mask 1, Floating, origin = feet), `Body` (blue 32×64 `Polygon2D` above the origin), `FeetMarker` (red dot at origin), `Collision` (28×12 footprint, bottom at y = 0), `InteractionArea` (`Area2D`, layer none / mask 3 `interactable`, monitorable off; circle radius 24 centred on the footprint at (0, −6)), `Camera` (`Camera2D`, at origin, defaults), `Lantern` (TEMPORARY `PointLight2D` at (0, −16); placeholder radial `GradientTexture2D` 256 px, `texture_scale` 2, warm colour (1, 0.85, 0.6), energy 1, shadows on with PCF5, `range_item_cull_mask` 3 = lights layers 1 and 2, `shadow_item_cull_mask` 1 = shadows only layer 1).
- `scripts/player/player.gd` (`class_name Player`): exported `move_speed` (200 px/s); `Input.get_vector` on the four `move_*` actions → `velocity` → `move_and_slide()`. Each physics frame it picks the nearest `Interactable` overlapping `InteractionArea` and emits `interaction_target_changed(target)` (null when none) only when the target changes. On the `interact` action (in `_unhandled_input`) it calls `target.interact(self)` if a target is in range. While a target is set it listens to the target's `tree_exiting`, so a target that is freed (collected pickup) or removed (zone change) is dropped and the prompt hides. `teleport(position)` moves the feet instantly, zeroes velocity, clears the interaction target (hides the prompt) and resets camera smoothing.
- `scenes/components/Interactable.tscn` + `scripts/components/interactable.gd` (`class_name Interactable`, `Area2D`): reusable interaction component. Layer 3 `interactable`, mask none, monitoring off (passive). Exported `prompt_text` (default "Press E to interact"); signal `interacted(interactor)`; method `interact(interactor)`. Default range shape: circle radius 32 at the component's origin. Usage: instance it as a child of any object (origin at the object's ground point), set `prompt_text`, and connect `interacted` to the object's own script. To change the range for one object, enable "Editable Children" on the instance and resize its `Collision`.
- `scenes/ui/InteractionPrompt.tscn` + `scripts/ui/interaction_prompt.gd`: `CanvasLayer` (layer 10) with a bottom-centre `Label`; shows the target's `prompt_text`, hides when the target is null.
- `scenes/tests/InteractionTestBox.tscn` + `interaction_test_box.gd`: TEMPORARY placeholder interactable (purple 48×48 box, `StaticBody2D` layer 1 with 48×16 base collision, child `Interactable`). On `interacted` it toggles purple ↔ yellow and prints `[INTERACT] InteractionTestBox used by <name> (count N)`. Now placed in `TestZoneA`; its state resets whenever Zone A is reloaded (no persistence yet). Delete it when real interactables exist.
- The Milestone A/B `TestRoom` in `Main.tscn` was removed; the test zones replace it.
- Asset pipeline (Milestone G Part 2, guide in `Docs/ASSET_PIPELINE.md`): `assets/source/blender/build_asset.py` (host command), `pipeline/` (shared conventions, rig, modeling helpers, Blender entry, PNG checks, scene writer), `generators/red_brick_wall.py`, `configs/red_brick_wall_3m.json`, generated `architecture/red_brick_wall_3m.blend` + `.render.json` (folder has `.gdignore`), `logs/` (ignored). Outputs: `assets/sprites/architecture/red_brick_wall_3m.png` (768×566, 220.69 px/m, mipmapped import), `scenes/props/architecture/RedBrickWall3m.tscn` (Node2D root at the footprint centre; `Sprite` scale 0.145, offset (−384, −485.87); `Body`/`Collision` 96 × 6.17 px, layer 1 / mask 0), `scenes/tests/asset_previews/RedBrickWall3mPreview.tscn` + `asset_scene_check.gd` (test only). The original `scripts/red_brick_wall_test.py`, its `.blend`, PNGs and records are kept unchanged.
- Architecture batch (Milestone G): generators `red_brick_arch_doorway.py`, `red_brick_arch_window.py`, `red_brick_pier.py` + helper `brick_openings.py`; configs `red_brick_arch_doorway_3m.json`, `red_brick_arch_window_3m.json`, `red_brick_veranda_pier.json`. Outputs per asset: `.blend` + `.render.json` in `assets/source/blender/architecture/`, PNG in `assets/sprites/architecture/` (doorway 768×728, window 768×566, pier 214×642; mipmapped import), scene in `scenes/props/architecture/` (`RedBrickArchDoorway3m` offset (−384, −648.02), two jamb collision shapes; `RedBrickArchWindow3m` offset (−384, −485.87), 96 × 6.17 px collision; `RedBrickVerandaPier` offset (−107, −557.68), 15.68 × 10.08 px collision), preview in `scenes/tests/asset_previews/`. Pipeline additions: optional `render.px_per_m`, `collision.source = "rects_m"`, `BoxBuilder.add_prism_xz` / `bevel=False`, tiling join rows taken from the end strips. TEMPORARY gallery: `scenes/tests/asset_previews/ArchitectureGalleryTest.tscn` + `architecture_gallery_test.gd`.
- No dialogue, inventory, inventory UI, enemies, story flags, puzzle state, save UI, save slots, autosave or other managers yet.

## Still undecided

Final base resolution, tile size, art style (pixel vs stylized/vector vs rendered), texture filter, integer scaling/pixel snap, final camera tuning, target platform, mechanic-specific controls and collision rules. Full list in `Docs/CONVENTIONS.md` → "Still undecided".

## Known issues / notes

- `config/features` in `project.godot` still says `"Forward Plus"` (creation-time label); the active renderer is Compatibility.
- Input events registered by the MCP tool use device `16` (keyboard) / `0` (first gamepad) instead of the editor's "All Devices". Synthetic input works; real-device check pending.
- `addons/godot_mcp/cache/undo/stack.json` and `entry_000001/` were committed before `addons/godot_mcp/cache/` was added to `.gitignore`, so Git still tracks them and shows them as modified. Untracking them needs `git rm -r --cached addons/godot_mcp/cache` (not done).
- The docs folder is `Docs/` (capital D) while the blueprint refers to `docs/`. Windows treats them as the same; on case-sensitive systems paths must match `Docs/`.
- Y-sort between Main's player and zone objects: implemented and verified in Milestone C (Y-sorted `World` → Y-sorted zone root → Y-sorted `Objects`). Recorded as **Proposed** in `Docs/CONVENTIONS.md` §3, waiting for approval.
- The Zone B door sits on the south wall, so a player standing right at it is drawn completely behind the door body. That is correct Y-sorting for the placeholder shapes; real south-facing doors will need art designed for it.
- Zone changes are an instant cut (no fade). Zones are `load()`ed on demand each time (cached by Godot's resource cache after the first load). Only objects that check `GameState` keep their state across reloads (currently just pickups); the test box colour still resets, by design.
- Save/load: the game never loads on start; a fresh launch begins in Zone A with an empty GameState until F9 is pressed. Saves are written in place (no temp file + rename), so a crash mid-write could leave a broken file; loading would then refuse it safely. Only zone, feet position and collected IDs are saved; anything else (test box colour, lantern on/off, day/night tint) resets on load. Saving is allowed anywhere, any time (no checkpoint rules decided).
- Save JSON error messages report Godot's JSON parser line number as-is.
- `validate_script` gives a generic code-43 result for `main.gd` and code 36 for `save_service.gd`; the editor shows 0 errors and both run correctly (same isolated-parser issue as `player.gd`).
- `test_pickup_01` doesn't follow the `<zone_id>_<object>` persistent-ID pattern from `Docs/CONVENTIONS.md` §5; it's a clearly temporary test ID. Real pickups must follow the pattern.
- Duplicate `pickup_id`s are not detected yet. Two pickups sharing an ID would both disappear when one is collected.
- MCP `validate_script` reports the same generic code-43 false positive for `pickup.gd` as for `player.gd`; the game runs it without errors.
- MCP synthetic movement input has high, variable latency between press and release (a 200 ms hold moved the player ~500 px), so precise walking tests use `Player.teleport()` to approach targets.
- MCP testing: tool calls sent in parallel are not guaranteed to run in order. A "press → wait → release" sequence must be sent as separate, sequential calls.
- Tall vertical placeholder walls (`WallWest`/`WallEast`) have their origin at the bottom of the whole wall, so they Y-sort in front of the player along their full length (visible only as a 2 px overlap where the 32 px body is wider than the 28 px footprint). Harmless for the test room; real walls will come from tiles.
- MCP `validate_script` reports a generic parse error (code 43, no details) for `player.gd`. This is a false positive of its isolated parser with `class_name` scripts: the editor shows 0 errors and the script runs correctly.
- Camera zoom/smoothing/limits/offset are left at defaults; final tuning remains Undecided.

- Interaction prompt text is a plain string per object, so "Press E to interact" doesn't adapt to gamepad or rebinding. Input-aware prompts are not built (out of scope).
- MCP synthetic input and real input both reach the running game. If the game window is played by hand during an MCP test run, results are mixed and must be discarded.
- Lighting (Milestone F): `CanvasModulate` doesn't tint the viewport clear colour, so the grey area outside a room stays grey at night. Real zones should fill the view (or the clear colour be set per zone) later.
- Lighting: the lantern adds light in day too (warm glow around the player). Whether the lantern is usable/visible in daylight is a mechanic decision, not made.
- Lighting: shadows are cast from base footprints in flat 2D, so they're a ground-plane approximation (a tall pillar casts the same shadow as a low box with the same base). Good enough for the proof; final look depends on the art style.
- Compatibility renderer: no limitation was hit with one light and one occluder. The project has Compatibility caps `rendering/limits/opengl/max_lights_per_object` = 8 and `max_renderable_lights` = 32 (defaults); whether and how they constrain 2D lights wasn't tested. Revisit when a zone needs many lights.
- `debug_toggle_night` (F2) and both `scripts/lighting/*_test_*.gd` scripts are temporary and should be removed or replaced when real day/night and lantern behaviour are designed.
- `debug_save` (F6) / `debug_load` (F9) and their handler in `SaveService._unhandled_input` are temporary until a save UI exists.
- Milestone order: E was implemented after F (on 8 October 2026). F's lighting state is deliberately not saved.
- Milestone G Part 1: no annotated / hand-drawn map was found in `Docs/map-reference/area1/`; the layout follows the aerial photo `whole view.png`. `field+cds.jpg` is actually a WebP file (it imports fine in Godot).
- Milestone G Part 1: west-facing doors (the CDS door, the veranda exit) are drawn as upright placeholder doors standing in front of the wall, and the player overlaps them when standing at them. The top-down angle only shows south faces, so final art needs a decided way to show side-facing entrances.
- Milestone G Part 1: like the test-room walls, long north–south blocks (CDS veranda frontage, prototype edges, veranda parapet) Y-sort by their south end, so the player's 32 px body overlaps them by 2 px when touching their west/east face.
- Milestone G Part 1 cleanup: overhead pieces now live inside their landmark (`<Landmark>/Overhead`, z 10), so moving the landmark moves them. The old note "moving the gate means moving `Overhead/MainGateOverhead` too" no longer applies.
- Milestone G Part 1 cleanup: shared paths under `Ground/Paths` (west palm path, north/east/south paths) are not part of any landmark. If the gate or CDS is moved, the paths leading to them must be adjusted by hand. The same goes for the tree rows near them (`GateTrees`, `CdsTrees`), which are kept as landscape groups.
- Milestone G Part 1 cleanup: landmark-owned ground (court surfaces, gate plaza, CDS forecourt) uses `z_index = -9` instead of −10. With −10 it would Y-sort against the zone `Ground` and disappear if the landmark were moved north of y = 0 (verified by moving a court to y −500).
- Milestone G Part 1: in the veranda the roof edge hides most of the arcade columns; this is expected for a roof seen from above but makes the arcade hard to read in the blockout.
- Milestone G Part 1: `MainGateExterior` has 27 `BlockoutBlock`s, each with an occluder. 13 cast shadows (gate piers, pavilion and columns, CDS sections, south wall); fences, hedges and gate leaves have `casts_shadow` off. Trees and palms have no occluders. There were no performance problems (145 fps), and no light limit was hit with one lantern.
- `Docs/map-reference/` images sit inside the Godot project, so Godot imports them (`.import` files, `.godot/imported` cache). Add a `.gdignore` file to that folder if they shouldn't be imported.

- Milestone G Part 2 seam fix (13 October 2026): the wall is now a seamless tiling module, fixed in the generator and shared pipeline (periodic bond with split boundary bricks, no bevel on cuts, rendered between neighbour copies, 16-texel bleed, new join checks; `Docs/ASSET_PIPELINE.md`). In `WallSeamTest.tscn` at zoom 1, the join columns went from +16.1 luminance (7.2 standard deviations) and a desaturated grey column to −0.5…−4.3 (≤ 2.0 SD, normal saturation): no visible seam. Scene file, scale 0.145, offset, collision and 96 px spacing unchanged. Remaining: the outer free ends of a run show the bleed (about 3 px past the footprint), and modules repeat every 3 m; an end-cap and A/B variants are proposed, not built. History of the seam:
- Milestone G Part 2: when two wall modules are placed 96 px apart, a thin light vertical line shows at the join (module end faces / edge anti-aliasing). Needs a visual decision before walls are tiled in zones (e.g. end treatment in the generator, or a 1 px overlap via `sprite_offset_adjust_px`). Seam test `scenes/tests/asset_previews/WallSeamTest.tscn` (TEMPORARY, zoom 1): footprints and collision meet exactly at x = 0 (no gap, no overlap). The seam is 2 screen px: one greyish column (background showing through the two semi-transparent edge fringes) and one about 24 % brighter column (pale mortar/bevel at the sunlit left end of the east module). Cause: each module ends in a half head joint of exposed mortar in every course and in the coping, so the join forms one continuous straight vertical joint instead of a staggered bond, plus about 1 texture px of anti-aliased alpha at each end.
- Milestone G Part 2: the scale reference (player placeholder 64 px = 2 m) is not foreshortened, while rendered heights are (×cos 40° on screen). Character art drawn for the same view will need to match.
- Milestone G Part 2: the uncommitted `WallAssetPreview.tscn` change (offset −202.862, footprint guide ±331.03 × ±21.28) is correct for 220.69 px/m, but its `scale` 0.143 and description (224.5 px/m) are stale; the pipeline uses 32 / 220.69 = 0.145. Left untouched as instructed.
- Milestone G Part 2: Godot's headless `--import` reports two warnings about `addons/godot_mcp/cache/undo/` (a nested `project.godot` and a duplicate UID of `MCPCheck.tscn`). They come from the MCP undo cache, not from the pipeline.
- Milestone G Part 2: Blender prints `WARNING HIPEW initialization failed` (AMD HIP library missing). It's harmless on this NVIDIA machine; rendering uses OptiX.
- Architecture batch limitations (13 October 2026):
  - Proportions are approximate, loosely following the CDS photos (plain brick equilateral pointed arches). Nothing is surveyed. The steel grille is a design choice; no reference photo shows one.
  - Each sprite bakes only its own shading. The doorway parapet's shadow falls on its own coping but not on a neighbouring wall sprite, and the parapet doesn't occlude light on the neighbour.
  - A pier and a wall share the same origin Y, so tree order decides which draws on top (place piers after the walls). Its 0.49 m footprint overlaps the wall collision, which is harmless.
  - The doorway and window interiors are recoloured, but their ends and all wall modules still repeat the same bricks every 3 m.
  - The doorway module only provides the opening and its collision. It isn't a `Door` interactable or a zone transition; add a `Door` instance separately if needed.
  - The parapet's side faces and the pier's side faces aren't visible at azimuth 0, so their ends are only roughly finished (cut bricks).
  - With the editor open, Godot imported the new PNGs before the pipeline wrote its first-import settings, so mipmaps were off. They were switched on in the three `.import` files and re-imported. Close the editor, or check the `.import` warning, when adding assets.
  - The scale reference (64 px = 2 m) is not foreshortened, while rendered heights are (×cos 40°). So the 2.81 m doorway apex is 69 screen px, only slightly above the 64 px reference.

## Next task

Review the architecture batch in `ArchitectureGalleryTest.tscn` (manual check 20) and approve or adjust it before any blockout replacement. Review the Milestone G Part 2 pipeline output (manual check 19) and decide the wall module seam and §13 conventions; then the next assets can be added as new generators/configs (`Docs/ASSET_PIPELINE.md`). Review the Milestone G Part 1 blockout against the real campus (manual check 15) and correct the layout. Decide the open art questions in `Docs/ART_STYLE.md` with a small art test (one CDS section, one palm, one path tile) before producing final assets. Also review the diff and commit the Milestone G Part 1 editability cleanup (5 scenes and 4 docs; not committed).

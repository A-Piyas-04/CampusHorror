# Project status

Last updated: 7 October 2026

## Summary

Environment and Cursor ↔ Godot MCP connection are **verified**. Milestone 0 conventions are **Confirmed**, registered in `project.godot`, and **verified** by an automated test scene (6/6 checks, 0 errors, 0 warnings).

Milestone A is **verified through the MCP**: `scenes/core/Main.tscn` is the main scene and owns one placeholder `Player` (4-direction movement, `Camera2D`) inside a temporary walled test room. Movement, diagonal normalization, wall collision and camera follow passed with 0 errors / 0 warnings. A manual play-test with a real keyboard/gamepad is still pending.

Milestone B is **verified through the MCP**: a reusable `Interactable` component (`scenes/components/Interactable.tscn`), a player interaction sensor, an on-screen prompt, and one placeholder `InteractionTestBox` in the test room. Prompt show/hide, in-range-only triggering and the temporary result (colour toggle + Output message) passed with 0 errors / 0 warnings.

Milestone C is **verified through the MCP**: two placeholder zones (`TestZoneA`, `TestZoneB`), reusable `Door` and `SpawnMarker` components, and a minimal zone registry + swap in `Main`. A → B and B → A travel, correct spawn markers, one surviving Player instance over 4 round trips, prompts, camera and wall collision passed with 0 errors / 0 warnings.

Milestone D is **verified through the MCP**: a minimal in-memory `GameState` autoload (one set of collected IDs), a reusable `Pickup` component that uses the existing `Interactable`, and one placeholder pickup `test_pickup_01` in Test Zone A. Collecting records the ID and removes the pickup; after leaving Zone A and returning it stays gone. One Player, zone transitions and interaction still work; 0 errors / 0 warnings. Nothing is written to disk. No dialogue, inventory, enemies, story flags or saving exists.

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

## Milestones

| Milestone | Status |
|---|---|
| Environment / MCP setup | **Verified** |
| 0. Project conventions | **Verified** (automated). Conventions Confirmed in `Docs/CONVENTIONS.md`; input actions + layer names registered; test scene passes. Manual real-device input check pending. |
| A. Main, placeholder player, movement, camera | **Verified** (automated, via MCP). Manual real-device play-test pending. |
| B. Interaction | **Verified** (automated, via MCP). Manual play-test pending. |
| C. Zones, doors, spawn markers | **Verified** (automated, via MCP). Manual play-test pending; new conventions in `Docs/CONVENTIONS.md` §3 and §8 are Proposed. |
| D. GameState + persistent pickup | **Verified** (automated, via MCP). In-memory only. Manual play-test pending; new convention in `Docs/CONVENTIONS.md` §9 is Proposed. |
| E. SaveService | Not started |
| F. Lighting test | Not started |
| G. Custom art sample | Not started |
| H. Desktop export | Not started |

### Manual checks for the user

1. Open `scenes/tests/Milestone0Test.tscn`, press F6, and press W/A/S/D, the arrow keys, E, F and Escape (and a gamepad, if available). Each should appear in the top-left "Actions pressed" readout. If a real device doesn't register, see the device note in `Docs/CONVENTIONS.md` §1.
2. Watch the pose cycle (every 2 s) and confirm the draw order looks right to you.
3. Press F5 (runs `Main.tscn`, starting in Test Zone A). Walk with WASD, the arrow keys and a gamepad (stick + D-pad); check the feel of the speed (200 px/s, adjustable as `move_speed` on the Player in the Inspector), that walls and the orange pillar block you, that you can walk behind/in front of the pillar, and that the camera follows.
4. Open the hand-written scenes (`Main.tscn`, `Player.tscn`, `Interactable.tscn`, `InteractionPrompt.tscn`, `InteractionTestBox.tscn`, `Door.tscn`, `SpawnMarker.tscn`, `TestZoneA.tscn`, `TestZoneB.tscn`) in the editor once and save them (Ctrl+S) so Godot writes their `uid` headers (they load fine either way).
5. Milestone B: walk to the purple box in Zone A. Check the prompt appears/disappears at a distance that feels right, E (and the gamepad's bottom face button) toggles the box colour and prints `[INTERACT] …` in Output, and nothing happens when pressing E away from the box. The prompt text says "E" even when using a gamepad (placeholder text).
6. Milestone C: in Zone A walk to the brown door on the north wall (upper left) and press E → Zone B (blue-grey floor), arriving just above its south-wall door. Press E at that door → back to Zone A, arriving just below the north door. Repeat a few times; check the change feels acceptable (it is an instant cut, no fade), the Output shows matching `[ZONE] …` lines, and nothing is left over from the previous zone. Open `TestZoneA.tscn`/`TestZoneB.tscn` and check the doors' and markers' Inspector fields.
7. Review the Proposed conventions in `Docs/CONVENTIONS.md` §3 (zone/player Y-sort) and §8 (zones, doors, spawn markers) and confirm or change them.
8. Milestone D: press F5, walk right of the start position to the small yellow diamond, check the "Press E to pick up" prompt and press E. It should vanish, the prompt should disappear immediately, and Output should show `[PICKUP] Collected 'test_pickup_01'.` Go through the north door to Zone B and back; the diamond must not reappear. Stop and restart the game: it **does** reappear (in-memory only, by design until Milestone E). Open `TestZoneA.tscn`, select `Objects/TestPickup01` and check `Pickup Id` / `Prompt Text` in the Inspector; open and save `Pickup.tscn` once (Ctrl+S) so Godot writes its `uid` header. Check Project Settings → Globals → Autoload lists `GameState`.
9. Review the Proposed convention in `Docs/CONVENTIONS.md` §9 (GameState and persistent pickups).

## Project contents

- `scenes/tests/MCPCheck.tscn`: temporary MCP test scene. Not the main scene; safe to delete later.
- `scenes/tests/Milestone0Test.tscn` + `milestone_0_test.gd`: Milestone 0 conventions test (placeholder shapes; character moved by the test, not by player input). Not the main scene.
- `addons/godot_mcp/`: MCP editor add-on (registers the `MCPRuntime` autoload used for runtime inspection/screenshots).
- `project.godot`: 7 input actions and 5 named 2D physics layers registered; main scene = `res://scenes/core/Main.tscn`; autoloads `MCPRuntime` (MCP add-on) and `GameState`.
- `scripts/core/game_state.gd` (autoload `GameState`, no `class_name` so it doesn't clash with the autoload name): in-memory only. `_collected_ids: Dictionary[String, bool]` used as a set. `mark_collected(id)` (empty id → error), `is_collected(id)`, `get_collected_ids()`. Resets when the game restarts; no disk I/O.
- `scenes/components/Pickup.tscn` + `scripts/components/pickup.gd` (`class_name Pickup`, `Node2D`): yellow 20×24 diamond `Body` above the origin + `Interactable` child, no collision. Exported `pickup_id` (stable ID, set in the Inspector) and `prompt_text`. `_ready`: empty id → error; already collected in GameState → `queue_free()` before the player can see or reach it. On `interacted`: `GameState.mark_collected(pickup_id)`, prints `[PICKUP] Collected '<id>'.`, `queue_free()`.
- `scenes/core/Main.tscn`: main scene. Tree:

  ```text
  Main (Node2D, scripts/core/main.gd)
  ├── World (Node2D, y_sort_enabled)          world container; the current zone is added here at runtime
  │   └── Player (instance of Player.tscn)    the one persistent player
  └── UI (Node)
      └── InteractionPrompt (instance of scenes/ui/InteractionPrompt.tscn, CanvasLayer 10)
  ```

  Connection in `Main.tscn`: `World/Player.interaction_target_changed` → `UI/InteractionPrompt._on_player_interaction_target_changed`.

- `scripts/core/main.gd`: owns zone switching. `ZONE_SCENES` (`zone_id` → scene path) is the whole zone registry. Exported `start_zone_id` (`test_zone_a`) / `start_spawn_id` (`start`). `change_zone(zone_id, spawn_id)` validates the zone and spawn before touching anything, removes + frees the old zone, adds the new one as `World`'s first child, connects its doors' `travel_requested`, calls `Player.teleport(marker.global_position)` and prints `[ZONE] Entered '<zone>' at spawn '<spawn>'.` Door requests are applied deferred (end of frame).
- `scenes/world/TestZoneA.tscn` (`zone_id` `test_zone_a`): green 800×600 room (interior x −400..400, y −300..300), walls, orange pillar at (200, 0), `InteractionTestBox` at (−200, 100), TEMPORARY `TestPickup01` (`pickup_id` `test_pickup_01`, prompt "Press E to pick up") at (120, 200), `DoorToZoneB` at (−250, −300) on the north wall → `test_zone_b` / `by_south_door`, spawns `start` (0, 150) and `by_north_door` (−250, −220).
- `scenes/world/TestZoneB.tscn` (`zone_id` `test_zone_b`): blue-grey 600×500 room (interior x −300..300, y −250..250), walls, spawns `center` (0, 0) and `by_south_door` (0, 170), `DoorToZoneA` at (0, 250) on the south wall → `test_zone_a` / `by_north_door`.
- `scripts/world/zone.gd` (`class_name Zone`): exported `zone_id`; `find_spawn_marker(spawn_id)`, `get_spawn_markers()`, `get_doors()`; reports empty/duplicate `spawn_id`s as errors on `_ready`.
- `scenes/components/Door.tscn` + `scripts/components/door.gd` (`class_name Door`, `Node2D`): brown 48×64 placeholder `Body` + `Interactable` child. Exported `destination_zone_id`, `destination_spawn_id`, `prompt_text` (copied into its Interactable if not empty). On `interacted` it emits `travel_requested(destination_zone_id, destination_spawn_id)`; it has no other logic.
- `scenes/components/SpawnMarker.tscn` + `scripts/components/spawn_marker.gd` (`class_name SpawnMarker`, `Marker2D`): exported `spawn_id`; its position is the arrival feet position. Editor-only gizmo, invisible in game.

- `scenes/player/Player.tscn`: reusable placeholder player. Root `Player` (`CharacterBody2D`, layer 2 / mask 1, Floating, origin = feet), `Body` (blue 32×64 `Polygon2D` above the origin), `FeetMarker` (red dot at origin), `Collision` (28×12 footprint, bottom at y = 0), `InteractionArea` (`Area2D`, layer none / mask 3 `interactable`, monitorable off; circle radius 24 centred on the footprint at (0, −6)), `Camera` (`Camera2D`, at origin, defaults).
- `scripts/player/player.gd` (`class_name Player`): exported `move_speed` (200 px/s); `Input.get_vector` on the four `move_*` actions → `velocity` → `move_and_slide()`. Each physics frame it picks the nearest `Interactable` overlapping `InteractionArea` and emits `interaction_target_changed(target)` (null when none) only when the target changes. On the `interact` action (in `_unhandled_input`) it calls `target.interact(self)` if a target is in range. While a target is set it listens to the target's `tree_exiting`, so a target that is freed (collected pickup) or removed (zone change) is dropped and the prompt hides. `teleport(position)` moves the feet instantly, zeroes velocity, clears the interaction target (hides the prompt) and resets camera smoothing.
- `scenes/components/Interactable.tscn` + `scripts/components/interactable.gd` (`class_name Interactable`, `Area2D`): reusable interaction component. Layer 3 `interactable`, mask none, monitoring off (passive). Exported `prompt_text` (default "Press E to interact"); signal `interacted(interactor)`; method `interact(interactor)`. Default range shape: circle radius 32 at the component's origin. Usage: instance it as a child of any object (origin at the object's ground point), set `prompt_text`, and connect `interacted` to the object's own script. To change the range for one object, enable "Editable Children" on the instance and resize its `Collision`.
- `scenes/ui/InteractionPrompt.tscn` + `scripts/ui/interaction_prompt.gd`: `CanvasLayer` (layer 10) with a bottom-centre `Label`; shows the target's `prompt_text`, hides when the target is null.
- `scenes/tests/InteractionTestBox.tscn` + `interaction_test_box.gd`: TEMPORARY placeholder interactable (purple 48×48 box, `StaticBody2D` layer 1 with 48×16 base collision, child `Interactable`). On `interacted` it toggles purple ↔ yellow and prints `[INTERACT] InteractionTestBox used by <name> (count N)`. Now placed in `TestZoneA`; its state resets whenever Zone A is reloaded (no persistence yet). Delete it when real interactables exist.
- The Milestone A/B `TestRoom` in `Main.tscn` was removed; the test zones replace it.
- No dialogue, inventory, inventory UI, enemies, story flags, puzzle state, saving or other managers yet.

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
- GameState is in memory only: quitting/restarting the game resets it and the test pickup reappears. Save/load is Milestone E.
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

## Next task

Do the Milestone D manual checks above (item 8), review the Proposed convention in `Docs/CONVENTIONS.md` §9, review the diff and commit Milestone D. Then start Milestone E (SaveService: write/read GameState to disk).

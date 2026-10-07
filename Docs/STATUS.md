# Project status

Last updated: 7 October 2026

## Summary

Environment and Cursor ↔ Godot MCP connection are **verified**. Milestone 0 conventions are **Confirmed**, registered in `project.godot`, and **verified** by an automated test scene (6/6 checks, 0 errors, 0 warnings).

Milestone A is **verified through the MCP**: `scenes/core/Main.tscn` is the main scene and owns one placeholder `Player` (4-direction movement, `Camera2D`) inside a temporary walled test room. Movement, diagonal normalization, wall collision and camera follow passed with 0 errors / 0 warnings. A manual play-test with a real keyboard/gamepad is still pending.

Milestone B is **verified through the MCP**: a reusable `Interactable` component (`scenes/components/Interactable.tscn`), a player interaction sensor, an on-screen prompt, and one placeholder `InteractionTestBox` in the test room. Prompt show/hide, in-range-only triggering and the temporary result (colour toggle + Output message) passed with 0 errors / 0 warnings. No other gameplay (dialogue, inventory, pickups, doors, zones, enemies, state, saving) exists.

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

## Milestones

| Milestone | Status |
|---|---|
| Environment / MCP setup | **Verified** |
| 0. Project conventions | **Verified** (automated). Conventions Confirmed in `Docs/CONVENTIONS.md`; input actions + layer names registered; test scene passes. Manual real-device input check pending. |
| A. Main, placeholder player, movement, camera | **Verified** (automated, via MCP). Manual real-device play-test pending. |
| B. Interaction | **Verified** (automated, via MCP). Manual play-test pending. |
| C. Zones, doors, spawn markers | Not started |
| D. GameState + persistent pickup | Not started |
| E. SaveService | Not started |
| F. Lighting test | Not started |
| G. Custom art sample | Not started |
| H. Desktop export | Not started |

### Manual checks for the user

1. Open `scenes/tests/Milestone0Test.tscn`, press F6, and press W/A/S/D, the arrow keys, E, F and Escape (and a gamepad, if available). Each should appear in the top-left "Actions pressed" readout. If a real device doesn't register, see the device note in `Docs/CONVENTIONS.md` §1.
2. Watch the pose cycle (every 2 s) and confirm the draw order looks right to you.
3. Press F5 (runs `Main.tscn`). Walk with WASD, the arrow keys and a gamepad (stick + D-pad); check the feel of the speed (200 px/s, adjustable as `move_speed` on the Player in the Inspector), that walls and the orange pillar block you, that you can walk behind/in front of the pillar, and that the camera follows.
4. Open the hand-written scenes (`Main.tscn`, `Player.tscn`, `Interactable.tscn`, `InteractionPrompt.tscn`, `InteractionTestBox.tscn`) in the editor once and save them (Ctrl+S) so Godot writes their `uid` headers (they load fine either way).
5. Milestone B: press F5, walk to the purple box left of the spawn. Check the prompt appears/disappears at a distance that feels right, E (and the gamepad's bottom face button) toggles the box colour and prints `[INTERACT] …` in Output, and nothing happens when pressing E away from the box. The prompt text says "E" even when using a gamepad (placeholder text).

## Project contents

- `scenes/tests/MCPCheck.tscn`: temporary MCP test scene. Not the main scene; safe to delete later.
- `scenes/tests/Milestone0Test.tscn` + `milestone_0_test.gd`: Milestone 0 conventions test (placeholder shapes; character moved by the test, not by player input). Not the main scene.
- `addons/godot_mcp/`: MCP editor add-on (registers the `MCPRuntime` autoload used for runtime inspection/screenshots).
- `project.godot`: 7 input actions and 5 named 2D physics layers registered; main scene = `res://scenes/core/Main.tscn`.
- `scenes/core/Main.tscn`: main scene. Tree:

  ```text
  Main (Node2D)
  ├── World (Node2D, y_sort_enabled)          world container
  │   ├── TestRoom (Node2D, y_sort_enabled)   TEMPORARY test room, replaced by zones in Milestone C
  │   │   ├── Ground, GroundStripe (Polygon2D, z_index -10)
  │   │   ├── WallNorth / WallSouth / WallWest / WallEast (StaticBody2D, layer 1, mask 0; room interior x −800..800, y −600..600)
  │   │   ├── Pillar (StaticBody2D, layer 1, mask 0; collision on its 80×40 base only)
  │   │   └── InteractionTestBox (instance of scenes/tests/InteractionTestBox.tscn, at (−250, 200))
  │   └── Player (instance of Player.tscn, spawned at (0, 200))
  └── UI (Node)
      └── InteractionPrompt (instance of scenes/ui/InteractionPrompt.tscn, CanvasLayer 10)
  ```

  Connection in `Main.tscn`: `World/Player.interaction_target_changed` → `UI/InteractionPrompt._on_player_interaction_target_changed`.

- `scenes/player/Player.tscn`: reusable placeholder player. Root `Player` (`CharacterBody2D`, layer 2 / mask 1, Floating, origin = feet), `Body` (blue 32×64 `Polygon2D` above the origin), `FeetMarker` (red dot at origin), `Collision` (28×12 footprint, bottom at y = 0), `InteractionArea` (`Area2D`, layer none / mask 3 `interactable`, monitorable off; circle radius 24 centred on the footprint at (0, −6)), `Camera` (`Camera2D`, at origin, defaults).
- `scripts/player/player.gd` (`class_name Player`): exported `move_speed` (200 px/s); `Input.get_vector` on the four `move_*` actions → `velocity` → `move_and_slide()`. Each physics frame it picks the nearest `Interactable` overlapping `InteractionArea` and emits `interaction_target_changed(target)` (null when none) only when the target changes. On the `interact` action (in `_unhandled_input`) it calls `target.interact(self)` if a target is in range.
- `scenes/components/Interactable.tscn` + `scripts/components/interactable.gd` (`class_name Interactable`, `Area2D`): reusable interaction component. Layer 3 `interactable`, mask none, monitoring off (passive). Exported `prompt_text` (default "Press E to interact"); signal `interacted(interactor)`; method `interact(interactor)`. Default range shape: circle radius 32 at the component's origin. Usage: instance it as a child of any object (origin at the object's ground point), set `prompt_text`, and connect `interacted` to the object's own script. To change the range for one object, enable "Editable Children" on the instance and resize its `Collision`.
- `scenes/ui/InteractionPrompt.tscn` + `scripts/ui/interaction_prompt.gd`: `CanvasLayer` (layer 10) with a bottom-centre `Label`; shows the target's `prompt_text`, hides when the target is null.
- `scenes/tests/InteractionTestBox.tscn` + `interaction_test_box.gd`: TEMPORARY placeholder interactable (purple 48×48 box, `StaticBody2D` layer 1 with 48×16 base collision, child `Interactable`). On `interacted` it toggles purple ↔ yellow and prints `[INTERACT] InteractionTestBox used by <name> (count N)`. Delete it (and its instance in `Main.tscn`) when real interactables exist.
- No dialogue, inventory, pickups, doors, zones, enemies, GameState, saving or managers yet.

## Still undecided

Final base resolution, tile size, art style (pixel vs stylized/vector vs rendered), texture filter, integer scaling/pixel snap, final camera tuning, target platform, mechanic-specific controls and collision rules. Full list in `Docs/CONVENTIONS.md` → "Still undecided".

## Known issues / notes

- `config/features` in `project.godot` still says `"Forward Plus"` (creation-time label); the active renderer is Compatibility.
- Input events registered by the MCP tool use device `16` (keyboard) / `0` (first gamepad) instead of the editor's "All Devices". Synthetic input works; real-device check pending.
- `addons/godot_mcp/cache/undo/stack.json` and `entry_000001/` were committed before `addons/godot_mcp/cache/` was added to `.gitignore`, so Git still tracks them and shows them as modified. Untracking them needs `git rm -r --cached addons/godot_mcp/cache` (not done).
- The docs folder is `Docs/` (capital D) while the blueprint refers to `docs/`. Windows treats them as the same; on case-sensitive systems paths must match `Docs/`.
- Y-sort between Main's player and zone objects (listed as Undecided in `Docs/CONVENTIONS.md`): Milestone A uses a Y-sorted `World` holding both the Y-sorted test room and the Player, and the test showed the player sorting correctly against the room's pillar. This is a working setup, not yet a confirmed convention; finalize it with the zone system in Milestone C.
- Tall vertical placeholder walls (`WallWest`/`WallEast`) have their origin at the bottom of the whole wall, so they Y-sort in front of the player along their full length (visible only as a 2 px overlap where the 32 px body is wider than the 28 px footprint). Harmless for the test room; real walls will come from tiles.
- MCP `validate_script` reports a generic parse error (code 43, no details) for `player.gd`. This is a false positive of its isolated parser with `class_name` scripts: the editor shows 0 errors and the script runs correctly.
- Camera zoom/smoothing/limits/offset are left at defaults; final tuning remains Undecided.

- Interaction prompt text is a plain string per object, so "Press E to interact" doesn't adapt to gamepad or rebinding. Input-aware prompts are not built (out of scope).
- MCP synthetic input and real input both reach the running game. If the game window is played by hand during an MCP test run, results are mixed and must be discarded.

## Next task

Do the manual checks above (Milestone B play-test), review the diff and commit Milestone B. Then start Milestone C (Zones, doors, spawn markers).

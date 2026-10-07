# Project technical conventions (Milestone 0)

Snapshot: 7 October 2026 • Godot 4.7.2 stable • Compatibility renderer

These rules keep scenes, scripts and assets consistent before gameplay exists. They describe how future work must be built; they do not create any gameplay, managers or autoloads.

## Status vocabulary

| Label | Meaning |
|---|---|
| **Confirmed** | Adopted by the user. |
| **Proposed** | Recommended; waiting for the user's approval. |
| **Undecided** | Depends on a decision not yet made (art style, target platform, etc.). |
| **Verified** | Observed in the actual project or proven by a test. |

On 7 October 2026 the user approved the core conventions in sections 1–5 as the initial project baseline. They are **Confirmed**. The items listed in [Still undecided](#still-undecided) are deliberately **not** finalized.

Input actions and physics layer names are registered in `project.godot`. The conventions were checked by `scenes/tests/Milestone0Test.tscn` (see [Verification](#verification)).

---

## 1. Input actions — Confirmed (registered)

Game code must read input **only through these action names**, never through raw key codes. Rebinding then only touches the Input Map.

| Action | Purpose | Keyboard | Gamepad |
|---|---|---|---|
| `move_up` | Walk up (screen -Y) | `W`, `Up` | Left stick up, D-pad up |
| `move_down` | Walk down (screen +Y) | `S`, `Down` | Left stick down, D-pad down |
| `move_left` | Walk left | `A`, `Left` | Left stick left, D-pad left |
| `move_right` | Walk right | `D`, `Right` | Left stick right, D-pad right |
| `interact` | Use / talk / pick up the nearest interactable | `E` | Bottom face button (A / Cross) |
| `lantern` | Reserved for the lantern | `F` | Left face button (X / Square) |
| `pause` | Open/close the pause menu | `Escape` | Start / Menu |

Rules:

- Action names are lowercase `snake_case` verbs or nouns.
- Movement uses `Input.get_vector("move_left", "move_right", "move_up", "move_down")` so diagonal speed is normalized and stick deadzones apply.
- Menus keep using Godot's built-in `ui_*` actions (`ui_accept`, `ui_cancel`, …). Do not repurpose `ui_*` actions for gameplay.
- New actions are added to this table before they are used in code.
- What `lantern` does (toggle, hold, fuel), and any other mechanic-specific control, is **Undecided**.

Registration details (Verified in `project.godot`):

- Deadzone 0.5 on every action (Godot default).
- Keyboard bindings are stored as **physical keys** (key position), so WASD stays in the same place on non-QWERTY layouts.
- The MCP tool stored keyboard events with device `16` and gamepad events with device `0` (first controller), rather than the editor's "All Devices" (`-1`). Synthetic key input matched the actions in the test, but a real keyboard/gamepad check is still a manual step. If a real device doesn't trigger an action, set each event's Device to "All Devices" in Project Settings → Input Map.

## 2. Collision layers — Confirmed (registered)

Godot 2D physics has 32 layers. A node's **layer** says "what I am"; its **mask** says "what I detect or collide with". Layer numbers below are the 1-based numbers shown in the Inspector.

| # | Name | What lives on it |
|---|---|---|
| 1 | `world` | Walls, buildings, furniture, water edges, TileMapLayer collision |
| 2 | `player` | The player's body |
| 3 | `interactable` | Areas that can be used with `interact` (doors, notes, pickups) |
| 4 | `enemy` | Enemy bodies |
| 5 | `trigger` | Invisible areas that react when the player enters them (zone exits, cutscene/story triggers) |
| 6–32 | — | Unassigned. Reserve before use; never renumber an existing layer. |

Baseline layer/mask assignments:

| Object (node type) | Layer | Mask | Notes |
|---|---|---|---|
| World geometry (`StaticBody2D` / TileMapLayer physics) | 1 `world` | none | Static things don't need to detect anything. |
| Player body (`CharacterBody2D`) | 2 `player` | 1 `world` | Blocked by walls. |
| Player interaction sensor (`Area2D`, child of player) | none | 3 `interactable` | Finds what the player can use. |
| Interactable (`Area2D`) | 3 `interactable` | none | Passive; the player's sensor finds it. |
| Enemy body (`CharacterBody2D`) | 4 `enemy` | 1 `world` | Enemy perception is separate gameplay logic, not collision. |
| Trigger (`Area2D`) | 5 `trigger` | 2 `player` | Fires when the player body enters. |

Rules:

- Use one purpose per layer. Don't put an object on several layers to "make it work"; adjust masks instead.
- In code, refer to layers through named constants or the Inspector, not magic bit values.
- Top-down characters use `CharacterBody2D.motion_mode = Floating` (no gravity/floor concept).
- Lighting occluders (`LightOccluder2D`) use **light masks**, which are separate from physics layers.
- Mechanic-specific collision rules are **Undecided**: whether enemies block the player, hazards, damage/hurtboxes, and so on.

## 3. Top-down visual ordering — Confirmed

Godot 2D draws using, in priority order: **CanvasLayer**, then **`z_index`**, then **Y-sort** (inside a `y_sort_enabled` parent), then **tree order**. We use each for one job:

| Band | What | Mechanism | `z_index` |
|---|---|---|---|
| Ground | Floor, grass, roads, water surface, ground decals | TileMapLayers drawn first | `-10` |
| World objects | Walls with height, trees, furniture, props | Children of the Y-sorted world | `0` |
| Characters | Player, NPCs, enemies | Same Y-sorted world as objects | `0` |
| Overhead | Roofs, tree canopies, archways, ceiling beams the player walks *under* | Separate node above the world | `10` |
| Lighting | Night tint, lantern, lamps | `CanvasModulate` + `PointLight2D`; these tint the world, they are not a draw band | n/a |
| UI | HUD, prompts, menus, dialogue | `CanvasLayer` (`layer` ≥ 10), never inside the world | n/a |

How it works:

- Objects and characters share **one** Y-sorted space, so whatever is lower on screen (larger Y) draws in front. This is what lets the player walk both in front of and behind a tree.
- Y-sort compares each node's **origin**. That's why character and object origins must sit on their ground contact point (see section 4).
- Ground stays below everything through `z_index = -10`, not through tree order, because zones will be swapped inside a shared world container later.
- Overhead pieces use `z_index = 10` and are not Y-sorted, so they always cover characters.
- `CanvasModulate` and lights affect world canvas items only. UI on its own `CanvasLayer` is not darkened at night.
- Use `z_index` only for the bands above. Don't use ad-hoc values like `z_index = 3` on a single prop to fix a sorting problem; fix its origin instead.

Zone layout (the two test zones use placeholder `Polygon2D` ground instead of TileMapLayers):

```text
Zone (Node2D, zone.gd)             y_sort_enabled = true
├── Ground (TileMapLayer)          z_index -10
├── GroundDetail (TileMapLayer)    z_index -10, drawn after Ground
├── Objects (Node2D)               y_sort_enabled = true
│   ├── Walls (TileMapLayer)       y_sort_enabled = true
│   └── … props, doors, spawn markers …
└── Overhead (Node2D)              z_index 10
```

Merging zone objects with Main's persistent player — **Proposed** (implemented and verified in Milestone C): Main's `World` container is Y-sorted and holds the loaded zone and the `Player` as siblings. The zone root **and** its `Objects` node are both `y_sort_enabled`, so Godot's nested Y-sort sorts every child of `Objects` together with the Player. Verified: the player draws behind the Zone B door (its feet are higher on screen) and in front of the Zone A test box. Any node between `World` and a sorted object must also have `y_sort_enabled = true`, or that branch is drawn as one block.

## 4. Character origin convention — Confirmed

Every character's **root node origin (0, 0) is the centre of its feet on the ground**.

```text
        ┌───┐
        │ ☺ │   ← sprite drawn ABOVE the origin (negative Y offset)
        │/█\│
        │/ \│
    ────┴─●─┴────  ← origin (0,0) = feet / ground contact
       [=====]     ← collision footprint: small shape around the feet
```

| Part | Rule |
|---|---|
| Root (`CharacterBody2D`) | Origin = feet centre. Its `position` *is* the logical ground position. |
| Sprite (`Sprite2D` / `AnimatedSprite2D`) | Offset upward so the bottom edge of the feet sits at y = 0. Either `centered = false` with a negative `offset.y`, or `centered = true` with `offset.y = -height/2`. |
| Movement collision (`CollisionShape2D`) | Small footprint around the feet only (roughly the bottom 1/4–1/3 of the sprite), with its bottom edge at y = 0. Not the whole body. Lets the head overlap walls visually, as top-down games expect. |
| Y-sorting | Uses the root origin, so it automatically uses the feet. |
| Spawn markers, save positions, door destinations | Store the **feet** position. |
| Interaction sensor / future hurtboxes | May be larger or higher than the footprint; positioned relative to the feet origin. |
| Camera | Follows the root (feet). Offset, zoom, smoothing and limits are **Undecided** (final camera tuning). |

The same rule applies to **world objects**: a tree's or lamp-post's origin is where its trunk meets the ground, and its collision covers only the base.

## 5. Naming conventions — Confirmed

| Thing | Style | Examples |
|---|---|---|
| Folders | lowercase `snake_case` | `scenes/world/`, `assets/sprites/`, `scripts/components/` |
| Scene files (`.tscn`) | `PascalCase`, same as the root node's name | `Main.tscn`, `Player.tscn`, `Milestone0Test.tscn` |
| Script files (`.gd`) | `snake_case` | `player.gd`, `door.gd`, `milestone_0_test.gd` |
| `class_name` | `PascalCase` | `class_name Door` |
| Resources (`.tres`) | `snake_case` | `hospital_key.tres` |
| Nodes in a scene | `PascalCase`, named by role | `Body`, `Collision`, `InteractionArea`, `Ground`, `Objects` |
| Functions, variables, signals | `snake_case` (GDScript style guide) | `move_speed`, `interacted`, `_on_body_entered` |
| Constants, enum values | `CONSTANT_CASE` | `MAX_SPEED` |
| Input actions | `snake_case` | `move_up`, `interact` |
| Stable IDs | `snake_case` (see below) | `campus_gate`, `hospital_basement_key` |

Folders follow the layout proposed in `Godot_AI_Campus_Setup_Blueprint_UPDATED.md`, section 7. Create a folder only when the first file that belongs in it is added. Test-only scripts live next to their test scene in `scenes/tests/`.

Node rules:

- Never leave default names such as `Node2D2` or `Sprite2D3`.
- Don't rename nodes that scripts or other scenes reference without updating those references in the same change.
- A scene's root node name equals its file name (`Player.tscn` → root `Player`).

### Stable IDs

Stable IDs are permanent string identifiers used for saves, doors, flags and content. They are **not** node names or node paths.

| ID type | Uniqueness | Pattern | Example |
|---|---|---|---|
| `zone_id` | Global | `<place>[_<sub_place>]` | `campus_gate`, `hospital_reception` |
| `spawn_id` | Within its zone | `<descriptive_place>` | `main_entrance`, `outside_hospital` |
| `item_id` | Global | `<descriptive_noun>` | `hospital_basement_key` |
| `clue_id` | Global | `<descriptive_noun>` | `torn_lab_notice` |
| Story flag | Global | `<subject>_<state>` (past tense / state) | `hospital_power_restored` |
| Persistent object ID | Global | `<zone_id>_<object>` | `hospital_reception_fuse_box` |

Rules:

- Lowercase letters, digits and underscores only; start with a letter.
- Set through exported Inspector properties, never derived from node names or paths.
- **Once an ID ships in a save or is referenced by content, never rename or reuse it.** Retire it and create a new one instead.
- IDs are registered in the relevant doc (`CAMPUS_MAP.md` for zones/spawns, `CONTENT.md` for items/clues/flags) when those docs exist.
- The IDs above are format examples, not approved story content.

## 6. Resolution and stretch

Inspected through the Godot MCP on 7 October 2026. **No display settings were changed.**

### Currently configured — Verified

| Setting | Value | Source |
|---|---|---|
| Base viewport | 1152 × 648 (16:9) | Godot default; not set explicitly in `project.godot` |
| Stretch mode | `canvas_items` | Set in `project.godot` |
| Stretch aspect | `expand` | Set in `project.godot` |
| Stretch scale / scale mode | `1.0` / `fractional` | Defaults |
| Window | Windowed, resizable, centred on primary screen | Defaults |
| V-Sync | Enabled | Default |
| Default canvas texture filter | Linear | Default |
| 2D transform / vertex pixel snap | Off / Off | Defaults |
| Physics tick rate | 60 Hz | Default |

### Policy

| Item | Status | Notes |
|---|---|---|
| Keep the current settings unchanged until the art-style decision | Confirmed (interim) | Fine for placeholder art. |
| `canvas_items` + `expand` as the working stretch setup | Confirmed (interim) | May be revisited together with the base resolution. |
| Final base resolution | **Undecided** | Depends on the art style. Pixel art usually wants a smaller base (e.g. 640×360 or 480×270) with integer scaling; stylized/vector art can stay at 1152×648 or move to 1920×1080. |
| Texture filter (Linear vs Nearest) | **Undecided** | Nearest only if pixel art is chosen. |
| Integer scaling / pixel snap | **Undecided** | Pixel-art decision. |
| Tile size | **Undecided** | Choose after the art-style test (blueprint §9). Don't assume 32×32. |
| Camera | Confirmed: one `Camera2D` following the player's feet. Tuning **Undecided**. | Zoom, smoothing, limits and offset are tuned later. |
| Target platform | **Undecided** | Desktop is assumed for the prototype. Mobile/web would affect UI scale, renderer and resolution. |

## 7. Renderer — Verified

| Setting | Value |
|---|---|
| `rendering/renderer/rendering_method` | **`gl_compatibility`** (active) |
| Compatibility driver (Windows) | `opengl3` (OpenGL 3.3 on the test machine's NVIDIA GeForce RTX 3050 Laptop GPU) |
| `rendering/renderer/rendering_method.web` | `gl_compatibility` (forced by Godot) |
| `rendering/renderer/rendering_method.mobile` | `mobile` (Godot default) |

Notes. None of these were changed.

- `config/features` in `project.godot` still lists `"Forward Plus"` from project creation. It's a Project Manager label; the active method is `gl_compatibility`, confirmed by the engine log.
- `rendering_device/driver.windows = "d3d12"` only applies to the Forward+/Mobile renderers and is unused under Compatibility.
- If a mobile export is ever made, the `.mobile` override would switch to the Mobile renderer. Revisit once the target platform is decided.
- Final renderer choice stays tied to the lighting test (Milestone F) and the target platform.

## 8. Zones, doors and spawn markers — Proposed

Introduced in Milestone C. Waiting for the user's approval.

| Rule | Detail |
|---|---|
| Zone scene | Lives in `scenes/world/`. Root is a `Node2D` with `scripts/world/zone.gd` (`class_name Zone`) and an exported `zone_id`, laid out as in section 3. |
| No player in zones | Zones never contain a Player, camera or UI. Main owns one persistent Player and moves it on arrival. |
| Zone registry | Every reachable zone is listed in `ZONE_SCENES` in `scripts/core/main.gd` (`zone_id` → scene path). The key must equal the zone root's `zone_id`; Main refuses to load a mismatch. |
| Spawn marker | Instance `scenes/components/SpawnMarker.tscn` (`Marker2D`, `class_name SpawnMarker`) inside `Objects`. Its position is the player's **feet** position on arrival. Set `spawn_id` (unique within the zone; the zone reports empty/duplicate IDs as errors). |
| Door | Instance `scenes/components/Door.tscn` (`class_name Door`) inside `Objects`, origin on the ground where the player stands to use it. Set `destination_zone_id`, `destination_spawn_id` and optionally `prompt_text`. Doors use the standard `Interactable`; they have no collision of their own (the wall behind them blocks). |
| Arrival spot | Put the destination spawn marker outside the arrival door's interaction range (more than 56 px from the door origin with the current shapes), so the player doesn't arrive with a door prompt already showing. |
| Transition | Main swaps zones at the end of the frame: the old zone is removed from the tree and freed, the new one is added to `World`, its doors are connected, and the Player is moved with `Player.teleport()`, which also resets the camera smoothing and the interaction target. If the zone or spawn doesn't exist, Main logs an error and keeps the current zone. |

---

## Still undecided

These are intentionally **not** finalized and must not be treated as settled by future work:

- Final base resolution
- Tile size
- Art style: pixel art vs stylized/vector vs rendered 2D
- Texture filter
- Integer scaling / pixel snap
- Final camera tuning (zoom, smoothing, limits, offset)
- Final target platform
- Mechanic-specific controls (lantern behaviour, any extra actions) and mechanic-specific collision rules (enemy blocking, hazards, damage)
- Zone transition presentation (fade, loading screen) and whether zones are preloaded or cached. Currently an instant swap with `load()` on demand.

## Verification

`scenes/tests/Milestone0Test.tscn` (script `milestone_0_test.gd`) is a placeholder-only test scene. It contains a ground polygon, a Y-sorted `Objects` node with a wall, a prop and a feet-origin `TestCharacter`, an `Overhead` canopy, and a debug readout of pressed actions. The script moves the character itself; there is no player control.

Result on 7 October 2026 (run through the Godot MCP): **6/6 automated checks passed, 0 errors, 0 warnings.**

| Check | Result |
|---|---|
| All 7 input actions registered | Pass |
| Physics layers 1–5 named | Pass |
| Character layer 2 / mask 1; wall and prop layer 1 / mask 0 | Pass |
| Feet origin: visual spans y −64..0, footprint bottom at y = 0, footprint 12 of 64 px tall | Pass |
| Draw-order setup: ground z −10, Y-sorted objects z 0, overhead z 10 | Pass |
| Wall blocks character: pushed right for 1 s, travelled 86 of 300 px, footprint stopped at wall face x = 860 | Pass |
| Screenshots: character behind prop / in front of prop / under canopy / against wall | Visually correct |
| Synthetic `E` key press → `interact` shown as pressed | Pass |

To re-run: open `scenes/tests/Milestone0Test.tscn` and press F6 (Run Current Scene). Results print as `[M0TEST]` lines in the Output panel; poses then cycle every 2 seconds. Press keys or gamepad buttons to see the pressed actions in the top-left readout.

## Change log

| Date | Change |
|---|---|
| 2026-10-07 | Initial Milestone 0 conventions drafted (all Proposed). |
| 2026-10-07 | Core conventions (sections 1–5) approved as Confirmed baseline; input actions and physics layer names registered; Milestone 0 test scene passed. Undecided items listed explicitly. |
| 2026-10-07 | Milestone C: zone layout updated (zone root also Y-sorted); zone/player Y-sort merge and section 8 (zones, doors, spawn markers) added as Proposed. |

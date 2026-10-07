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

Nothing below is Confirmed yet. Everything is either Verified (an observed fact about the current project) or Proposed. Move items to Confirmed only after the user approves them.

None of these conventions has been registered in `project.godot` yet (no input actions, no layer names). Registering them is a separate, approval-gated step; see [Applying these conventions](#applying-these-conventions).

---

## 1. Input actions — Proposed

Game code must read input **only through these action names**, never through raw key codes. Rebinding then only touches the Input Map.

| Action | Purpose | Keyboard (Proposed) | Gamepad (Proposed) |
|---|---|---|---|
| `move_up` | Walk up (screen -Y) | `W`, `Up` | Left stick up, D-pad up |
| `move_down` | Walk down (screen +Y) | `S`, `Down` | Left stick down, D-pad down |
| `move_left` | Walk left | `A`, `Left` | Left stick left, D-pad left |
| `move_right` | Walk right | `D`, `Right` | Left stick right, D-pad right |
| `interact` | Use / talk / pick up the nearest interactable | `E` | Bottom face button (A / Cross) |
| `lantern` | Lantern action (behaviour undecided) | `F` | Left face button (X / Square) |
| `pause` | Open/close the pause menu | `Escape` | Start / Menu |

Rules:

- Action names are lowercase `snake_case` verbs or nouns.
- Movement uses `Input.get_vector("move_left", "move_right", "move_up", "move_down")` so diagonal speed is normalized and stick deadzones apply.
- Menus keep using Godot's built-in `ui_*` actions (`ui_accept`, `ui_cancel`, …). Do not repurpose `ui_*` actions for gameplay.
- `lantern` is reserved only as an input name. What it does (toggle, hold, fuel) is **Undecided**.
- New actions are added to this table before they are used in code.

## 2. Collision layers — Proposed

Godot 2D physics has 32 layers. A node's **layer** says "what I am"; its **mask** says "what I detect or collide with". Layer numbers below are the 1-based numbers shown in the Inspector.

| # | Name | What lives on it |
|---|---|---|
| 1 | `world` | Walls, buildings, furniture, water edges, TileMapLayer collision |
| 2 | `player` | The player's body |
| 3 | `interactable` | Areas that can be used with `interact` (doors, notes, pickups) |
| 4 | `enemy` | Enemy bodies |
| 5 | `trigger` | Invisible areas that react when the player enters them (zone exits, cutscene/story triggers) |
| 6–32 | — | Unassigned. Reserve before use; never renumber an existing layer. |

Initial layer/mask assignments:

| Object (node type) | Layer | Mask | Notes |
|---|---|---|---|
| World geometry (`StaticBody2D` / TileMapLayer physics) | 1 `world` | none | Static things don't need to detect anything. |
| Player body (`CharacterBody2D`) | 2 `player` | 1 `world` | Blocked by walls. Whether enemies physically block the player is **Undecided**. |
| Player interaction sensor (`Area2D`, child of player) | none | 3 `interactable` | Finds what the player can use. |
| Interactable (`Area2D`) | 3 `interactable` | none | Passive; the player's sensor finds it. |
| Enemy body (`CharacterBody2D`) | 4 `enemy` | 1 `world` | Enemy perception is separate gameplay logic, not collision. |
| Trigger (`Area2D`) | 5 `trigger` | 2 `player` | Fires when the player body enters. |

Rules:

- Use one purpose per layer. Don't put an object on several layers to "make it work"; adjust masks instead.
- In code, refer to layers through named constants or the Inspector, not magic bit values.
- Lighting occluders (`LightOccluder2D`) use **light masks**, which are separate from physics layers.

## 3. Top-down visual ordering — Proposed

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

Planned zone layout. This is a convention for future scenes; none of them exist yet:

```text
Zone (Node2D)
├── Ground (TileMapLayer)          z_index -10
├── GroundDetail (TileMapLayer)    z_index -10, drawn after Ground
├── Objects (Node2D)               y_sort_enabled = true
│   ├── Walls (TileMapLayer)       y_sort_enabled = true
│   └── … props, spawn markers …
└── Overhead (Node2D)              z_index 10
```

How a zone's `Objects` merges with the persistent player owned by Main is **Undecided**. It must be proved with a test scene before Milestone A/C relies on it.

## 4. Character origin convention — Proposed

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
| Movement collision (`CollisionShape2D`) | Small footprint around the feet only (roughly the bottom 1/4–1/3 of the sprite), not the whole body. Lets the head overlap walls visually, as top-down games expect. |
| Y-sorting | Uses the root origin, so it automatically uses the feet. |
| Spawn markers, save positions, door destinations | Store the **feet** position. |
| Interaction sensor / future hurtboxes | May be larger or higher than the footprint; positioned relative to the feet origin. |
| Camera | Follows the root (feet). A small upward offset may be added later if framing looks low. |

The same rule applies to **world objects**: a tree's or lamp-post's origin is where its trunk meets the ground, and its collision covers only the base.

## 5. Naming conventions — Proposed

| Thing | Style | Examples |
|---|---|---|
| Folders | lowercase `snake_case` | `scenes/world/`, `assets/sprites/`, `scripts/components/` |
| Scene files (`.tscn`) | `PascalCase`, same as the root node's name | `Main.tscn`, `Player.tscn`, `MCPCheck.tscn` |
| Script files (`.gd`) | `snake_case` | `player.gd`, `door.gd` |
| `class_name` | `PascalCase` | `class_name Door` |
| Resources (`.tres`) | `snake_case` | `hospital_key.tres` |
| Nodes in a scene | `PascalCase`, named by role | `Sprite`, `Collision`, `InteractionArea`, `Ground`, `Objects` |
| Functions, variables, signals | `snake_case` (GDScript style guide) | `move_speed`, `interacted`, `_on_body_entered` |
| Constants, enum values | `CONSTANT_CASE` | `MAX_SPEED` |
| Input actions | `snake_case` | `move_up`, `interact` |
| Stable IDs | `snake_case` (see below) | `campus_gate`, `hospital_basement_key` |

Folders follow the layout proposed in `Godot_AI_Campus_Setup_Blueprint_UPDATED.md`, section 7. Create a folder only when the first file that belongs in it is added.

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

Inspected through the Godot MCP on 7 October 2026.

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
| Keep the current settings unchanged for Milestones 0–A | Proposed | Fine for placeholder art. Nothing was changed. |
| `canvas_items` + `expand` | Proposed | Scales UI and world crisply; `expand` shows extra world on wider/taller screens instead of black bars. |
| Final base resolution | **Undecided** | Depends on the art style. Pixel art usually wants a smaller base (e.g. 640×360 or 480×270) with integer scaling. Stylized/vector art can stay at 1152×648 or move to 1920×1080. |
| Texture filter (Linear vs Nearest) | **Undecided** | Switch to Nearest only if pixel art is chosen. |
| Integer scaling / pixel snap | **Undecided** | Pixel-art decision. |
| Tile size | **Undecided** | Choose after the art-style test (blueprint §9). Don't assume 32×32. |
| Camera | Proposed | One `Camera2D` following the player's feet, zoom 1.0. Limits, smoothing and zoom decided in Milestone A. |
| Target platform | **Undecided** | Desktop is assumed for the prototype. Mobile/web would affect UI scale, renderer and resolution. |

## 7. Renderer — Verified

| Setting | Value |
|---|---|
| `rendering/renderer/rendering_method` | **`gl_compatibility`** (active) |
| Compatibility driver (Windows) | `opengl3` (OpenGL 3.3 on the test machine's NVIDIA GeForce RTX 3050 Laptop GPU) |
| `rendering/renderer/rendering_method.web` | `gl_compatibility` (forced by Godot) |
| `rendering/renderer/rendering_method.mobile` | `mobile` (Godot default) |

Notes. None of these were changed.

- `config/features` in `project.godot` still lists `"Forward Plus"` from project creation. It's a Project Manager label; the active method is `gl_compatibility`, confirmed by the engine log during the MCPCheck run.
- `rendering_device/driver.windows = "d3d12"` only applies to the Forward+/Mobile renderers and is unused under Compatibility.
- If a mobile export is ever made, the `.mobile` override would switch to the Mobile renderer. Revisit once the target platform is decided.
- Final renderer choice stays tied to the lighting test (Milestone F) and the target platform.

---

## Applying these conventions

Approval-gated follow-up steps. None have been done yet:

1. Register the seven input actions with the bindings in section 1 (Project Settings → Input Map).
2. Name 2D physics layers 1–5 as in section 2 (Project Settings → Layer Names → 2D Physics).
3. Build a tiny test scene in `scenes/tests/` with placeholder rectangles to check the Milestone 0 acceptance criterion: a feet-origin character footprint is blocked by a wall, sorts in front of/behind a prop by Y, and passes under an overhead piece.

## Change log

| Date | Change |
|---|---|
| 2026-10-07 | Initial Milestone 0 conventions drafted (all Proposed). |

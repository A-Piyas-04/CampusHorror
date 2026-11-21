# Chapter 1: Lights Out (the playable slice)

Decisions D16 to D24 (`Docs/DECISIONS.md`). This is the first complete, finishable piece of *The Quiet Hours*:
title screen, intro, a goal, a puzzle chain, a creature, checkpoints, an ending. It is built only in the mapped
area (Main Gate, the field, the CDS block). Everything else waits for more map references (`Docs/MAP_INTAKE.md`).

## Playing it

Run the project (F5): the title screen is the main scene. **New game** plays the intro; **Continue** resumes the
last checkpoint. Running `scenes/core/Main.tscn` directly (F6) still gives the old daylight sandbox with no story,
which is what the tests use.

| Action | Keyboard | Gamepad |
|---|---|---|
| Move | WASD / arrows | left stick (half tilt = sneak) |
| Sneak (quiet) / Run (loud, stamina) | hold Ctrl / hold Shift | left shoulder / left stick click |
| Interact (hold where the ring shows) | E | A / Cross |
| Lantern: Full, Low, Off | F | X / Square |
| Pause, journal, settings | Esc | Start |

## The chapter, beat by beat (spoilers)

| # | Where | What happens | Flag / item |
|---|---|---|---|
| 1 | CDS canteen (dark) | Intro card. You wake at your table. Only the organism's glow is visible. Find the hurricane lantern on the serving counter (moonlight from the north windows falls on it). | `got_lantern` |
| 2 | Canteen | Optional: the notice board (needs light) says the hall is closed and the master key is with security; kerosene on a table. | `canteen_notice` note |
| 3 | Veranda, field | Out through the veranda's arcade gap. Dead lamps, a few solar ones flickering; crows; a covered body; a dropped phone with Rumana's last messages; glowing trails. A figure stands under the gate lamp, staring up into it, and is gone. | `apparition_gate` |
| 4 | Main Gate | Chained shut, from the outside. | `gate_seen` |
| 5 | Security office (pavilion, door on its campus side) | The guard's logbook (the whole backstory in seven entries), the CCTV frame, the dead phone, kerosene, and the **CDS master key** in the key cabinet. Taking the key wakes the Night Guard. | `logbook_read`, item `cds_master_key`, `guard_awake` |
| 6 | Field | The Night Guard patrols between the gate and the CDS. Full light is seen from 28 m, low light from 13 m, darkness only up close; sprinting on paving is loud, sneaking on grass is silent; crows give you away. Caught = blackout, back to the last checkpoint. | |
| 7 | Table-tennis room | Karim's note: put the light out and look at the wall. With the lantern **off**, the code glows on the north wall: **2704**. A locker to hide in. | `code_seen` |
| 8 | Indoor games hall | The master key opens it. Breaker keypad, code 2704: the lights stutter on, the floor hatch by the court bursts open, and the guard comes through the door. Run for the hatch. | `power_on`, `hatch_open` |
| 9 | The hatch | "Climb down": end card, back to the title. | `chapter1_done` |

A careful first playthrough takes 20 to 30 minutes.

## Systems built for it

| System | Where | Notes |
|---|---|---|
| Title screen, start modes | `scenes/core/MainMenu.tscn`, `scripts/ui/main_menu.gd`, autoload `Game` (`scripts/core/game_flow.gd`) | `new` / `continue` / sandbox |
| Story director | `scripts/story/chapter_1.gd` | beats, objectives, hints, checkpoints, blackout, finale, ending |
| Game state v2 | `scripts/core/game_state.gd` | flags, items, notes (with text, for the journal), objective, lantern fuel |
| Saves v2 | `scripts/core/save_service.gd` | atomic write, autosave `checkpoint()`, `load_at_start()`, redirectable `save_path` for tests |
| Lantern v2 | `scripts/lighting/player_lantern.gd` | Full / Low / Off, kerosene burns (Full 6 min, Low 17 min), gutters below 15 % |
| Lamps | `scripts/lighting/lamp_light.gd` | steady / flickering / dead, `needs_power`, mood-only lights (`gameplay = false`) |
| Organism glow | `scripts/world/glow_mark.gd`, `glow_layer.gd` | visible only in the dark; spots, trails, glowing writing that can be "read" |
| The Night Guard | `scripts/creatures/night_guard.gd`, `scenes/creatures/NightGuard.tscn` | light / sight / sound senses, patrol, suspicious, investigate, chase, search |
| Navigation | `scripts/world/nav_builder.gd` | baked from the zone's colliders on entry (story mode) |
| Composure | `scripts/player/composure.gd`, `assets/shaders/composure.gdshader` | no bar: vignette, colour drain, heartbeat, breathing, camera tightening; zero = faint |
| Hiding | `scripts/components/hide_spot.gd` | lockers; seen getting in = dragged out |
| Crows, apparition | `scripts/world/crow_flock.gd`, `apparition.gd` | spotters; one-time foreshadowing |
| UI | `scripts/ui/hud.gd`, `note_viewer.gd`, `keypad_ui.gd`, `pause_menu.gd` (journal, settings), `story_card.gd`, `settings_panel.gd`, `ui_style.gd` | |
| Components | `Readable`, `Examine`, `Keypad`, `HideSpot`, `Pickup` v2, `Door` v2 | `scenes/components/` |
| Sound | `assets/source/audio/generate_sfx.py` -> `assets/audio/sfx/` | 21 one-shots + 3 tension loops, all generated, replaceable |

## Art built for it (all Blender, one pipeline)

- **`assembly` generator** (`assets/source/blender/generators/assembly.py`): any prop or room as data (boxes,
  cylinders, tubes, lathes, blobs, text, procedural PBR materials).
- **Props**: `tools/author_props.py` writes 43 configs: canteen table sets, chairs, table-tennis tables, lockers,
  benches, security desk, cot, almirah, key cabinet, notice board, breaker panel, floor hatch (closed / open),
  drums, crates, pots, bins, organism growth and pods, blood, dropped belongings, crows, the gate chain, the
  hurricane lantern, kerosene, the master key.
- **Rooms**: `tools/author_rooms.py` writes the room shells: security office, canteen, table-tennis room, indoor
  games hall, and the veranda in three sections. Each is a cutaway diorama: floor and walls under everything, a
  knee-high south wall in front, its own soft interior lighting, collision for walls and fixed pieces.
- **The Night Guard**: `assets/source/blender/characters/night_guard.py`, a variant of the player generator (same
  rig, scale and eight facings; khaki uniform, cap, grey skin, hunched; idle, dragging walk, reaching run).

## Known limits

- The interiors are invented (no interior references yet). Walls running north to south are seen edge-on, so
  doors in them are marked by door leaves, signs and light rather than visible door faces.
- The guard only exists on the field and in the finale; he does not follow you indoors.
- No clock, no Chapter 0, no control remapping yet (`Docs/ROADMAP.md`, Chapter 1 slice table).
- Sounds are synthesised placeholders; replace any by dropping a recording at the same path.

## Extending it

- **A new prop**: add a function in `tools/author_props.py`, run it, then
  `python assets/source/blender/build_asset.py <asset_id>`; instance `scenes/props/<category>/<Scene>.tscn`.
- **A new room**: add a `Room(...)` in `tools/author_rooms.py` (size, floor and wall materials, openings, fixed
  dressing, layers for anything the player can walk behind), build it, then make a zone scene with the room at
  the origin plus props, doors, spawns, lights and glow; add the zone to `data/zones/zone_registry.tres`, a profile
  in `data/zones/profiles/`, and a manifest + reviewed baseline for the validator.
- **Story**: flags are free-form strings in `GameState`; the director reacts to them. Notes are `Readable` nodes;
  their text lives in the zone scene, so writers can edit it in the inspector.

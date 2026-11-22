# Testing

Snapshot: 21 November 2026 • Phase H4, extended in Phase I (feel suites)

Audience: anyone (person or AI session) who changes a zone, a component, a prop or the player.

Since Phase H4 every zone is checked by **one data-driven validator** plus **one session check**. They
replace the 9 per-batch Main Gate check scenes and their 6 versioned baselines (retired on 21 November
2026; they remain in git history and in the private ref `refs/checkpoints/h245-preedit`).

---

## 0. Map v2 (22 November 2026)

The default suites are: Scripts, Validator, GameSession, Character, Movement, Audio, Camera, Transition,
Occlusion, Interaction, and **CampusWorld**.

`scenes/tests/zone_validation/campus_world_check.gd` covers the new campus:
- layout entrances against doors and spawns;
- every interior exit landing on a campus spawn;
- a 1.25 m swept flood fill from the Main Gate that must reach every entrance and landmark, and must not reach the
  far side of the wall or the lakes;
- round trips through every door;
- Explore basics: unlocked doors, time of day driving the lamps, the lantern by day and night, and the map screen.

**Retargeted suites.** The feel suites now use campus anchors: the Central Field, the plaza pavers, the CDS door
`Objects/Doors/Door_cds_veranda`, and a halls-avenue palm.

**Parked suites.** The story suites (Chapter1–5, DebugKeys, Campus) drive the retired exteriors:

    CHECKS="Chapter1 Chapter2 Chapter3 Chapter4 Chapter5 DebugKeys Campus" tools/run_checks.sh

**Validator self-test.** It mutates the legacy `scenes/world/legacy/MainGateExterior.tscn` as a fixture; its
manifest and baseline stay in place.

## 1. The suites

Run all of them before every commit that touches `scenes/`, `scripts/`, `data/` or `project.godot`:

    tools/run_checks.sh                        # every suite, one summary line each
    CHECKS="Chapter1 Validator" tools/run_checks.sh
    VARGS=--dump-baseline CHECKS=Validator tools/run_checks.sh   # refresh baselines (review the diff first)

Logs land in `tools/.check-logs/<label>/` (git-ignored). Override the executable with `GODOT=...`; the default
is `F:\App Installers\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe`.

| Suite | Command (headless; exit 0 = pass) | What it proves |
|---|---|---|
| **Zone validator** | `<godot> --headless --path . res://scenes/tests/zone_validation/ZoneValidator.tscn -- --quit-after-checks --self-test` | Every zone's structure, collision, reachability, ground and fades (§2) |
| **Session check** | `<godot> --headless --path . res://scenes/tests/zone_validation/GameSessionCheck.tscn -- --quit-after-checks` | The real `Main.tscn`: boot, presentation contract, every spawn, every door, save/load, a refused bad save, debug keys |
| **Character check** | `… res://scenes/tests/character_previews/PlayerCharacterCheck.tscn -- --quit-after-checks` | The 4 cycle sheets x 8 facings (288 frames: anchoring, scale, measured cycle speeds), all 8 input directions, facing hysteresis, run / sneak cycles, phase kept through turns, footsteps only on heel-strike frames, the Player surviving a trip |
| **Movement** (Phase I) | `… res://scenes/tests/feel/MovementCheck.tscn -- --quit-after-checks` | Speeds per mode, acceleration / stop times, input on the same tick, diagonal normalisation, analog sneak, the stamina cycle, 0 % foot slide, footstep cadence, `surface_at` (known spots, plus 500 random points against an independent oracle), the input lock |
| **Audio** (Phase I) | `… res://scenes/tests/feel/AudioCheck.tscn -- --quit-after-checks` | Bus layout and reverb, ambience per zone (looping), reverb following the profile, listener, footstep set coverage, footsteps per surface and gait, ducking during travel |
| **Camera** (Phase I) | `… res://scenes/tests/feel/CameraCheck.tscn -- --quit-after-checks` | Zoom and limits from the profile, no void at the corners / centre / spawns of the playable area, look-ahead leads and settles, teleport snaps, shake decays |
| **Transition** (Phase I) | `… res://scenes/tests/feel/TransitionCheck.tscn -- --quit-after-checks` | Door trips swap only while fully black, input locked throughout, 0.62 s door to control, overlapping travel refused, kept scenes for return trips, `travel_to_position`, an unknown zone refused |
| **Occlusion** (Phase I) | `… res://scenes/tests/feel/OcclusionCheck.tscn -- --quit-after-checks` (add `--pixels` and drop `--headless` for the rendering proof) | Occluder index = independent count; the right items carry ghosts (dead band, tree, wall) and none in front; ghost state, clip modes restored, pool stable, zone changes, cost per tick; windowed: ghost pixels drawn at the dead band, 0 difference in front of an overlapping tree |
| **Interaction** (Phase I) | `… res://scenes/tests/feel/InteractionCheck.tscn -- --quit-after-checks` | The prompt (verb, name, glyph, exact position, fades), gamepad / keyboard glyph switching, live rebinding, hold-to-interact, the prompt hidden during travel, every interactable has a verb |
| **Chapter 1** (story) | `… res://scenes/tests/story/Chapter1Check.tscn -- --quit-after-checks` | A NEW story game played end to end with real input: intro card, the dark canteen, the lantern, notes in the light, every door of the chapter, the chained gate, logbook and master key, the guard waking, patrolling, seeing the lantern, chasing and catching (blackout, checkpoint reload), the dark-only wall code, the locker, the hall's keypad, the finale, the hatch, the end card and the title screen. Saves to its own file. |
| **Chapter 2** (story) | `… res://scenes/tests/story/Chapter2Check.tscn -- --quit-after-checks` | Chapter 2 started fresh (start mode `chapter:2`): the manhole arrival, the guard's plaza patrol and baked navigation, the locked north gate, the Mosque note, the Admin memo and a wrong safe code, the AV hall date, the safe (1911), being caught (blackout -> checkpoint), the north road, the end card and Chapter 3 taking over |
| **Chapter 3** (story) | `… res://scenes/tests/story/Chapter3Check.tscn -- --quit-after-checks` | Chapter 3 fresh: students awake and sound-tuned, the dead shutter, the keyless generator, lab log, room 304's board, the key box (wrong code, 4501), a student hearing a sprint, the generator (academic circuit live), the run to the halls, Chapter 4 taking over |
| **Chapter 4** (story) | `… res://scenes/tests/story/Chapter4Check.tscn -- --quit-after-checks` | Chapter 4 fresh: three sleepwalkers, light draws them far more than footsteps, the barricaded stair, the radio, room 203's diary, Rafi and the lift key, the survivors, the end card and the title |
| **Chapter 5** (story) | `… res://scenes/tests/story/Chapter5Check.tscn -- --quit-after-checks` | Chapter 5 fresh: the powered workshop door, the pit lift (Rafi's key) to Site 7, technicians awake (and Chapter 3's students not), the dead B2 lift, the director's log, the card-locked switchboard, the host report and the staff card, the switchboard rousing every technician, the B2 lift, the colony, the end card and the title |
| **Campus** (traversal) | `… res://scenes/tests/story/CampusTraversalCheck.tscn -- --quit-after-checks` | Static: every door and edge of every zone resolves; no edge lands inside an edge strip; every open way has a way back. Live: the real Main tours every edge (walking into the strip) and door (interact), checking each arrival, that each edge has its own collision shape, and the locked stairwell |
| **Debug keys** | `… res://scenes/tests/story/DebugKeysCheck.tscn -- --quit-after-checks` | The developer keys that drive Chapter 1: F3 steps through every beat (granting what each assumes), F4 switches the guard off and on, F7 fills the lantern |
| **Scripts** | `… res://scenes/tests/scripts/ScriptCompileCheck.tscn` | Every script under `res://scripts` compiles with the autoloads present (a parse error otherwise hangs only the scene that loads it) |
| **Feel probe** (windowed only) | `<godot> --path . res://scenes/tests/feel/FeelProbe.tscn -- --quit-after-checks` (no `--headless`) | Real GPU and vsync: scripted play plus 2 door trips; median / p99 / worst frame; no frame over 2x the median while the world is visible |

Asset changes additionally run the pipeline: `python assets/source/blender/build_asset.py --all --steps validate,scene,preview,godot`
(`Docs/ASSET_PIPELINE.md`). A failing script never quits on its own, so wrap runs in a timeout. **A
parse error makes a scene hang, not fail.**

Expected output after the Chapter 1 slice (21 November 2026): scripts **53/53**, validator **89/89**
(8 zones), session **15/15**, character **13/13**, movement **24/24**, audio **19/19**, camera **9/9**,
transition **13/13**, occlusion **14/14** (update 0.105 ms per tick over 204 occluders, grid-indexed),
interaction **12/12**, chapter 1 **48/48**, debug keys **12/12**, pipeline validate **71/71 assets**. The chapter 1 check ends with
one `WARNING: 2 ObjectDB instances were leaked at exit` (suspended coroutine states left when the test changes
scene to the title and quits; test-only).

Expected output after Phase I (21 November 2026): validator **49/49**, session **15/15**, character
**13/13**, movement **24/24**, audio **19/19**, camera **9/9**, transition **13/13**, occlusion **14/14** (windowed `--pixels` **17/17**), interaction **12/12**, feel probe **4/4**
(144 Hz display: median 6.94 ms, p99 about 9 ms), pipeline **21/21 assets**, ambience generator check
**PASS**. Exactly two `ERROR` lines are intended: the session check's refused unknown-zone save, and the
transition check's "Unknown zone_id 'no_such_zone'". Any other `ERROR` or `WARNING` line is a problem.

Headless runs use the Dummy audio driver, which never mixes. Game code then tracks the sounds it would play
instead of playing them (otherwise every playback would leak at exit), and the audio suite asserts that state.
Listen for the sound itself during the manual check.

Two lessons from Phase I, now rules: in a lambda, never assign to a captured local (GDScript captures
locals by value; use a dictionary). `physics_frame` is emitted *before* that tick's physics runs, so in
callback *i* of a hold, exactly *i* ticks have been processed.

From I6 / I7:
- A screenshot comparison must freeze animations and let fades and physics settle first.
- Anything that runs on real time (animation, tweens) must be measured in its own units, not in physics
  ticks.
- A script that fails to parse makes its test scene hang instead of fail. Always run under a timeout, and
  type variables explicitly (this project treats Variant inference as an error).

The session check backs up `user://save.json` byte for byte and restores it (verified). The
validator never touches the save.

## 2. Zone validator rules

Generic rules: they apply to every zone in `data/zones/zone_registry.tres` with no per-zone code.

| Rule | Checks |
|---|---|
| `identity` | The scene's `Zone` root has the registry key as its `zone_id` |
| `graph` | Spawn IDs are unique and non-empty; every `Door` leads to a registered zone **and** a spawn that exists there |
| `conventions` | `Docs/CONVENTIONS.md`: static bodies on layer 1 / mask none; `Interactable` layer 3 / mask none; `OverheadVisibility` layer none / mask 2; no unclassified `Area2D`; occluders on light mask 1 (or 0 = shadow deliberately off); prop sprites on light mask 2; `ContactShadow` at effective z −9 with no collision; **every placed prop has only Y-sorted `Node2D` ancestors**; zone ground at z −10, not Y-sorted |
| `snapshot` | Every node, including internal children, equals the baseline: global transform, z, Y-sort, light mask, modulate, textures, `texture_scale`, polygons, collision layers / shapes, occluders, lights, TileMapLayer cells (hash per cell), exported script values (door destinations, spawn IDs, fade settings, …) |
| `ground` | An 8 px material lattice over the manifest's ground rectangle equals the baseline. Materials are texture file stems, so re-rendering a texture at another resolution keeps the lattice identical (this is how H2 was verified: 316,575 samples, 0 changed) |
| `probes` | For **every** rectangle collision shape of every static body (any layer): the real player footprint walking at it from the south and from the north stops at its face, or earlier at a neighbour, and **never passes through** |
| `reach` | Flood fill (8 px grid, real 28 × 12 footprint) from the zone's first spawn: no standable position outside the manifest's `playable_bounds` (no leaks), every spawn reachable, every door reachable close enough to interact |
| `cases` | The manifest's specific walks (expected stop point or free path) |
| `fades` | Every `OverheadVisibility`: never collides; lasts at least 0.15 s; entering fades exactly its targets to `faded_alpha` and nothing else; the alpha never changes faster per frame than its sine ease allows for that frame's real delta (a snap fails by ~3.5×); leaving restores them. Plus the manifest's fade cases (where each layer must or must not be faded) |
| `self-test` | (`--self-test`) mutates `main_gate_exterior` in memory 9 ways (palm moved, cell repainted, body on the wrong layer, trunk off the world layer, south wall removed, door to a missing spawn, a fade that never fades, a 0 s fade, a fade rewired to snap) and requires each rule to catch its own mutation. **A validator that can't fail proves nothing.** |

Measured cost: about 20 s for the four zones' rules (ground lattice 5 s, fades 11 s, reach 2 s), plus
the self-test.

## 3. Per-zone data

`scenes/tests/zone_validation/manifests/<zone_id>.json`: **every registered zone needs one**.

| Key | Meaning |
|---|---|
| `playable_bounds` | `[x, y, w, h]` feet rectangle the player must never leave (required for `reach`) |
| `ground` | `{ "node": "Ground", "rect": [x, y, w, h] }`; omit for zones without textured ground |
| `walks` | `[{ name, from, motion, expect: "stop" | "free", stop, tol }]` measured stop lines worth pinning |
| `fade_layers`, `fade_cases` | Layer paths, and `[{ name, feet, faded: [...] }]` positions where they must (not) be faded |

`scenes/tests/zone_validation/baselines/<zone_id>.json`: the recorded state (written by the tool, never
by hand).

## 4. Changing a zone on purpose: the baseline workflow

1. Make the change.
2. Run the validator. `snapshot` / `ground` list **every** difference (`changed: <node> [fields]`,
   `added`, `removed`, `ground at (x, y): a -> b`). Every other rule must still pass.
3. **Read the list.** It must contain only what you meant to change. If anything else is listed, stop:
   that is a regression.
4. Refresh only that zone's baseline: `… ZoneValidator.tscn -- --dump-baseline --zone=<zone_id>`. It
   prints the same diff again before writing.
5. Re-run the validator (pass), and commit the baseline **in the same commit** as the change, saying
   what the diff was.

Example (H2, 21 November 2026): exactly 21 differences, 20 × `["texture_scale"]` on ground-textured
polygons and `./Ground/Tiles ["xform", "tile_size"]`, and 0 ground samples changed. Refreshed.

New zone: add it to the registry, write its manifest, run `--dump-baseline --zone=<id>`, review the
validator's output (stats line, reach area, probes), then commit.

## 5. Coverage of the retired suites

| Retired suite (checks) | Now covered by |
|---|---|
| `MainGateGroundCheck` (16) | `ground` (same 316,575-point lattice), `snapshot` (cells hash, strips, markings, every other node), `conventions` (ground z / Y-sort) |
| `MainGateVegetationCheck` (18) | `probes` (every trunk, both sides; was 84 probes, now every shape in the zone), `conventions` (Y-sort chain, light masks, contact shadows), `snapshot` |
| `MainGateBoundaryCheck` (26) | `reach` (any gap in the wall is a leak to the road), `probes`, `snapshot` (37 + 38 run, run collision, occluder), manifest walk (stop line y 1394.96) |
| `MainGateLandmarkCheck` (33) | `snapshot` (layers, sort points, occluders), `fades`, manifest walk (gate-leaves stop y 1390) |
| `MainGateOverheadCheck` (14) | `fades` (generic per area, plus the same 11 positions as manifest fade cases), manifest walk (fade areas never block) |
| `MainGateCdsCheck` (22) | `snapshot`, `probes`, `reach` (door, flagpoles and lamp don't block), `fades` (canteen roof); texture budget stays in the pipeline (`max_texture_px`) |
| `MainGateSessionCheck` (11) | `GameSessionCheck` (14), now for every zone, door and spawn instead of one hand-picked route |
| `MainGatePlayableTest` (24), `MainGateCompositionTest` (27) | Retired without replacement: they tested a separate review scene that the real zone has superseded. Their manual approvals (checks 22, 23) are obsolete |

**Intentionally not carried over:**
- One-time acceptance diffs between historical batch baselines (e.g. "batch 2 differs from batch 1B
  only inside SouthWall"). They proved past batches, and git history keeps them.
- The ±2 px jitter test on one fade edge (flicker at the boundary). The rate rule catches snaps but
  not repeated toggling. **Known gap:** add a jitter case to the `fades` rule if fade hysteresis
  ever changes.
- The 1,100 samples 0.5 px either side of each original surface edge: replaced by the exact snapshot
  of every strip vertex and every tile cell, which is stricter.

## 6. Other test scenes

| Scene | Use |
|---|---|
| `scenes/tests/environment_previews/ZoneCapture.tscn` | Windowed screenshots of the real game (`--shots=name@x,y[,zoom=..][,night][,walk=dir][,gait=sprint|sneak]…`). Needs a window. |
| `scenes/tests/renderer_stress/RendererStressTest.tscn` | Windowed lighting cost and correctness probe (`--stack=N`). The frame-time budget probe is `FeelProbe.tscn` |
| `assets/source/audio/generate_ambience.py --check` | Checks the ambience beds: loop points, seam vs the local signal, loudness, peak |
| `scenes/tests/asset_previews/*` | Written by the asset pipeline; run by its `godot` step |
| `MCPCheck`, `Milestone0Test`, `WallAssetPreview`, galleries | Historical; not part of any regression |

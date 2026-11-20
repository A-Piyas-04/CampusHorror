# Project review — November 2026

Snapshot: 20 November 2026 • written after a ~5 week pause (last commit `d76443d`, 14 October 2026)

Audience: the project owner, and any AI session resuming work on this repo. Read this before
`Docs/ROADMAP.md`, `Docs/GAME_DESIGN.md` and `Docs/NEXT_ACTIONS.md`.

This document replaces guesswork about "where did I leave off". It is an assessment, not a status
log — `Docs/STATUS.md` remains the authoritative per-batch verification record.

---

## 1. Verdict in one paragraph

The project is in excellent technical health and is **not** where its own documentation implies it
is. Seven months of milestone labels (0, A–G) suggest a game two thirds built. In reality the repo
contains a **world-class custom asset factory and one beautiful, partly finished outdoor zone, with
almost no game attached**. There are 7,831 lines of Python driving a Blender→Godot 2.5D asset
pipeline, and 659 lines of GDScript implementing the entire game: walk, interact, walk through a
door, remember a collected ID, write a JSON file, tint the screen blue. There is no enemy, no fear
system, no puzzle, no inventory, no dialogue, no menu, no objective, and **zero audio files**. The
correct next move is therefore not "build more campus" — it is to stop expanding the map and build
the game that the map is for.

---

## 2. Re-verified today (20 November 2026)

The pause caused no rot. Everything below was re-run today, not read from the old log:

| Check | Result |
|---|---|
| Blender | `F:\bbbb\blender.exe` → **5.2.2 LTS** (build 2026-09-15) present |
| Godot | `F:\App Installers\Godot_v4.7.2-stable_win64.exe\...console.exe` → **4.7.2.stable.official.ed1daf0bf** present |
| Python | 3.12.2 on PATH (pipeline needs 3.10+, stdlib only) |
| Asset pipeline, all 21 configs | `build_asset.py --all --steps validate` → **21/21 PASS** |
| The real game runs | `PlayerCharacterCheck.tscn` headless against the real `Main.tscn` → **19/19 PASS, exit 0**, user's `save.json` untouched |
| Working tree | Clean except `temp_prompt.txt` (modified) and `master_prompt.txt` (untracked) — both scratch session prompts, not project files |

**Nothing is broken and nothing is uncommitted.** Contrary to the "Next task" section at the bottom
of `Docs/STATUS.md`, the player character batch *was* committed (in `d76443d`). You can resume cold.

Note: neither Blender nor Godot is on `PATH`; the pipeline hardcodes both paths in
`assets/source/blender/pipeline/conventions.py` (`DEFAULT_BLENDER_EXE`, `DEFAULT_GODOT_EXE`). If the
`F:` drive is ever reorganised, those two constants are the only things to fix (or set `BLENDER_EXE`
/ `GODOT_EXE`).

---

## 3. What actually exists

### 3a. The asset factory — the project's crown jewel

One command (`python assets/source/blender/build_asset.py <asset_id>`) takes a Python generator plus
a JSON config and produces a validated transparent sprite, a reusable Godot prop scene with
collision, a preview scene, and a machine-readable render record — then verifies all of it in Godot
headless. It supports render layers, content cropping, inter-object occlusion holdouts, shared texel
grids across multi-part buildings, neighbour context lighting, seam validation between adjacent
slices, texture budgets, and seamless horizontal tiling modules.

21 production assets exist: 4 ground tiles in a shared TileSet, 4 brick architecture modules,
3 vegetation, 4 street furniture (incl. 2 flagpoles), 6 landmark props (Main Gate tower / leaves /
pavilion, CDS canteen / table-tennis / indoor-basketball), plus a rigged, animated player character
(18-bone armature, 8 animations, 64 frames, feet-anchored on every frame).

This is the hard part of making a custom-looking game, and it is solved and reproducible.

### 3b. The map — one zone, ~85% production art

`main_gate_exterior` (355 nodes) is genuinely impressive: real tiled ground with off-grid edge
strips, 42 production trees/palms, a 37-module red-brick road wall with 38 pilasters, the
reconstructed Main Gate from photographs, and the full CDS exterior in three sections. Still
blockout inside it: the two sports courts, the three `PrototypeEdge*` boundary hedges, and the field
line markings.

`cds_veranda` is the only interior and is **100% blockout**. `test_zone_a` / `test_zone_b` are
Milestone C–F test rooms still in the registry.

### 3c. The game — a thin prototype

All 659 lines, honestly summarised:

| System | State |
|---|---|
| Movement | 4-direction, constant 200 px/s, `move_and_slide`, no acceleration, no run/sneak |
| Animation | Reads velocity, picks one of 8 clips, dominant-axis facing. Clean, works. |
| Interaction | Nearest `Interactable` in a 24 px radius, one prompt label, `E` to fire a signal |
| Zones | 4 registered in a `const Dictionary` in `main.gd`; hard-cut swap via blocking `load()` |
| Persistence | `GameState` = one in-memory set of collected IDs |
| Save | One slot, `user://save.json`, 4 fields: version, zone id, player x/y, collected ids |
| Lighting | Two scripts both named `*_test_*` and marked TEMPORARY: a `CanvasModulate` toggled by F2, and a `PointLight2D` toggled by F |
| Overhead | `OverheadVisibility` — fades roofs to 35% alpha while the player is under them |
| UI | One `Label` in a `CanvasLayer` |

### 3d. What does not exist at all

Enemies. Enemy AI, perception, navigation (no `NavigationRegion2D` anywhere). Fear/sanity. Stealth
or sound propagation. Puzzles or puzzle state. Story flags. Inventory. Items. Dialogue. Notes or a
journal. Objectives. A main menu. A pause menu (`pause` is registered as an action and unused).
Settings. Keybinding UI. Save slots, autosave, or a save UI. Death or respawn. A real day/night
clock. **Audio of any kind — 0 sound files, no `AudioStreamPlayer` anywhere, no audio buses.** Any
interior room. Any second floor. Any underground or underwater area. Any NPC. Any export preset.

---

## 4. The core finding: a 12:1 investment inversion

```
Asset pipeline (Python) ███████████████████████████████████████ 7,831 lines
Game logic (GDScript)   ███                                        659 lines
Test/check code (GDScript, 17 files)  ██████████████████████    ~2,000+ lines
Audio                                                                0 files
```

This is not a criticism of the past work — building the factory first was a defensible call, and the
factory is the reason this game can look like IUT instead of like an asset pack. But the consequence
must be faced: **the project has proven it can produce a beautiful campus, and has not yet produced
one minute of gameplay.** Every further zone built before the game systems exist is a zone that will
need retrofitting later for navigation meshes, sound emitters, light volumes, enemy spawn data, save
hooks and occlusion handling.

---

## 5. Risk register — fix before scaling, not after

Ordered by how expensive each becomes if deferred.

### R1 — Presentation contract is still undecided, and every asset depends on it 🔴

> **Update, 20 November 2026: decided, and corrected.** The contract is now Confirmed in
> `Docs/PRESENTATION.md`. Measuring every asset showed that the claim below, that the whole library
> needs re-rendering for sharpness, **was wrong**. Every sprite is already rendered at 3–7× density
> and mipmapped down. **Only the 4 ground tiles are drawn 1:1**, and that is the softness the old
> notes describe. The fix shrinks to re-rendering 4 tiles (roadmap H2). The "layout-neutral" claim
> below was proven true by an experiment: doubling `px_per_m` left footprint, collision and origin
> byte-identical. **Applied 21 November 2026 (H2)**, verified by the zone validator and before/after
> screenshots.
`Docs/ART_STYLE.md` and `Docs/CONVENTIONS.md` both still list base resolution, tile size, texture
filter, integer scaling and camera tuning as **Undecided** — after 21 assets and 355 placed nodes
were authored against them. `project.godot` sets no viewport size at all (so 1152×648 default) with
`canvas_items` / `expand` stretch, and `Docs/STATUS.md` already records the symptom: *"64 px tiles
are drawn 1:1; on windows larger than the base resolution the `canvas_items` stretch magnifies them
and they look soft."* Soft, magnified tiles are the direct opposite of the stated top priority
(clean, crisp visuals). This must be locked now.

**The good news — this is cheap today and brutal later.** Texture density is `px_per_m` in each
config, and the pipeline derives sprite scale as `32 / render_px_per_m`. So raising `px_per_m`
raises texel density while the sprite's *world* footprint stays identical, and collision comes from
metres (`rects_m`), untouched. Doubling texture sharpness across the whole asset library should
therefore be ~21 config edits plus one batch re-render, with **zero** layout, collision or
coordinate changes. Verify that claim on one asset before trusting it — but if it holds, the
sharpness decision costs an afternoon now and a full re-layout later.

Cost of waiting: ×4 texture memory and render time per doubling (the 3 CDS sections alone are
already 12.88 Mpx), so pick the target deliberately against `max_texture_px`.

### R2 — Renderer may not survive the horror design 🔴

> **Update, 20 November 2026: retired.** A stress test in the real zone (30 shadow-casting lights
> plus up to 48 stacked) found Compatibility's lighting identical to Forward+'s to four decimal
> places at every light count. The feared 8-lights-per-object cap does not apply to 2D lighting.
> Cost was 2.62 ms per frame at 1080p. Decision: stay on Compatibility. Evidence is in
> `Docs/DECISIONS.md` D3.
Active renderer is **Compatibility** (OpenGL 3.3) with default caps
`max_lights_per_object = 8` and `max_renderable_lights = 32`. `Docs/STATUS.md` admits these were
never tested: *"no limitation was hit with one light and one occluder."* A night campus with a
lantern, lamp posts, window glow, torch beams and flickering corridors will exceed 8 lights touching
one object immediately. `config/features` in `project.godot` still carries the `"Forward Plus"`
creation label, `rendering_device/driver.windows` is already `d3d12`, and the GPU is an RTX 3050 —
so switching is realistic. Decide with a 30-light stress test **before** lighting becomes a core
mechanic, because 2D lighting behaviour differs between the two renderers.

### R3 — Movement feel contradicts the top priority 🟠

> **Update, 21 November 2026: resolved (I1, I2).** Three gaits at stride-matched speeds (measured 0 % foot
> slide), eased acceleration, stamina, 8 facings. Evidence: `MovementCheck` 24/24 and `Docs/PRESENTATION.md` §4.
`move_speed = 200` px/s at 32 px/m is **6.25 m/s** — a hard sprint, as the one and only speed. The
walk cycle covers roughly 2 m/s, so the feet visibly slide (already logged under "Player character
findings"). The user's stated #1 priority is smooth, clean movement; the current controller has one
constant speed, no acceleration, no deceleration, 4 facings, and no footstep sound. This is the
single most felt flaw in the build and is cheap to fix properly.

### R4 — Zone transitions will hitch on real zones 🟠

> **Update, 21 November 2026: resolved (I5).** Faded travel with a threaded load; the swap happens only while
> the screen is black; FeelProbe shows no visible hitch. Background prefetch was tried and removed (deadlock).
`main.gd` calls blocking `load()` on the main thread inside `change_zone()`, then hard-cuts. At 355
nodes it is survivable; at a multi-floor building with hundreds of lit props it will stall visibly.
Needs `ResourceLoader.load_threaded_request` plus a fade. `Docs/CONVENTIONS.md` lists transition
presentation as Undecided — decide it with the loader.

### R5 — The verification harness grows linearly with the map 🟠

> **Update, 21 November 2026: resolved (H4).** One data-driven validator with generic rules, a small
> manifest and one baseline per zone replaces the 9 bespoke scenes and 6 versioned baselines. Its
> self-test proves each rule catches a regression. See `Docs/TESTING.md`.
One zone has produced 17 check scripts, 9 bespoke check scenes and **6 versioned baseline JSON
files** (`main_gate_ground_baseline*.json`, one per batch). The rigor is a real asset and should be
kept — but the pattern means any future edit to `MainGateExterior.tscn` fails several checks until a
new baseline is dumped and hand-verified. At 30 zones this collapses. Generalise to one data-driven
zone validator plus a documented baseline-refresh workflow.

### R6 — Occlusion is handled per-building by hand 🟡

> **Update, 21 November 2026: resolved (I6).** A clipped player silhouette is attached to whatever draws over
> the player, so no area is hand-placed and there is no dead band. Proven at the pixel level (`OcclusionCheck --pixels`).
Buildings are single big sprites that Y-sort on one line, so the player vanishes behind facades.
Batch 3A's answer was hand-placed `OverheadVisibility` fade areas per roof — plus a known residual
dead band ~3 m deep behind the tower piers where the player is simply invisible. Every future
building inherits this problem and this manual cost. A systemic answer (a silhouette drawn through
occluding art, or a depth-aware cutout shader) solves it once.

### R7 — The save system cannot hold a game 🟡
Four fields. No flags, inventory, world deltas, enemy state, time of day, or slots. It writes in
place with no temp-file-and-rename, so a crash mid-write corrupts the slot (loading then refuses it
safely, which is good). Content built before the save architecture exists is content that cannot be
saved — so this must land before the narrative phase, not after.

### R8 — Reference material exists for one area only 🔴 (external blocker)
The entire pipeline is photograph-driven, and `Docs/map-reference/` contains **one folder,
`area1`**, covering the Main Gate / field / courts / CDS. There are no references for the academic
buildings, halls of residence, mosque, library, auditorium, labs or the hospital. Campus expansion
is hard-blocked on a reference-gathering trip, not on code. See `Docs/NEXT_ACTIONS.md` for the shot
list. `Docs/CAMPUS_MAP.md` also still notes that no annotated or hand-drawn campus map was ever
supplied — so all layout outside area1 is currently unknowable.

### R9 — 10+ visual approvals are open and stale 🟡
`Docs/STATUS.md` tracks "manual check" numbers up to 30; checks ~19–30 (architecture batch,
environment batch, composition test, playable test, Batches 1B, 2, 3, 3A, 4, player character) are
all recorded as **"verified (automated), pending visual approval"** and were never closed. Reviewing
them one at a time after a five-week gap is a waste of a session. Collapse them into one guided
approval pass (see `Docs/NEXT_ACTIONS.md` §1).

### R10 — Housekeeping 🟢

> **Update, 21 November 2026: resolved (H5).** Debug keys quarantined in `DebugTools`, lighting
> scripts renamed PROVISIONAL, MCP cache untracked, `.gdignore` added, the label fixed, the scratch
> prompts deleted, and the zone registry moved to a resource.
`addons/godot_mcp/cache/` is still Git-tracked despite being gitignored (needs
`git rm -r --cached`). `Docs/map-reference/` has no `.gdignore`, so Godot imports every reference
photo. `config/features` misreports the renderer. Two `*_test_*.gd` lighting scripts and three debug
input actions (F2/F6/F9) are marked TEMPORARY and still load in the shipping main scene.

---

## 6. Methodology: keep, change, add

**Keep.** The batch discipline — pre-edit checkpoint, automated proof, headless exit codes, explicit
"Known issues" written down and *not* silently fixed, byte-exact diffing of untouched nodes. This is
better engineering practice than most solo game projects ever reach, and it is why a five-week gap
cost nothing. Keep the "this is not approved final art" honesty too.

**Change.** Three things:
1. **Generalise verification** (R5) — one zone validator, not one per batch.
2. **Separate "approved" from "verified"** — the backlog in R9 happened because automated passing
   and human approval were tracked in the same column. Give approval its own small ledger.
3. **Shrink the status document.** `Docs/STATUS.md` is 820 lines and growing per batch; its own
   "Next task" section was out of date. Split it: a short living status, and an append-only
   `Docs/VERIFICATION_LOG.md` for batch tables.

**Add.** Two gaps the current method does not cover:
1. **Nothing tests how the game *feels*.** Every check asserts geometry, pixels and collision
   positions. None asserts frame time, input latency, transition hitch, or audio. Add a performance
   and feel budget to the acceptance criteria (target frame time, max transition stall, max input-to-
   animation delay) — otherwise "clean and smooth" stays an aspiration nobody can fail.
2. **De-risk interiors early.** All 21 assets are exteriors, and the one interior zone is blockout.
   Interiors are the largest unbuilt category *and* the one with no proven pipeline. Prove a modular
   interior kit on one real room before planning any building, rather than discovering the problem
   at campus scale.

---

## 7. Answers to the questions you asked

**"What dimension are we building?"** 2D engine, 2.5D presentation — and it is working. Godot 2D
physics, `CharacterBody2D`, Y-sorted top-down world, 2D lights. The 3D look comes entirely from
assets rendered in Blender through a fixed orthographic camera at 40° elevation / 0° azimuth, at 32
game px per metre. Height reads upward on screen, depth is foreshortened ×0.643. This is settled,
proven across 21 assets, and is the right choice — do not revisit it.

**"Were we just building the map and assets?"** Yes, exactly that — plus the factory to build them.
Milestones A–F were one-day foundation proofs in early October; everything from 8 October onward
(Milestone G, Parts 1–2 and Batches 1A–4) was art pipeline and map.

**"What's left?"** The game. Sections 3d and 5 above are the honest list. See `Docs/ROADMAP.md`.

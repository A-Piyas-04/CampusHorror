# Roadmap — Milestones H onward

Snapshot: 20 November 2026 • **Status: PROPOSED**

Audience: the project owner, and any AI session picking the next batch of work.

Supersedes the Phase 3 milestone table in
`Docs/initial-context-source/05_SETUP_AND_IMPLEMENTATION_PLAN.md`, which ended at *"G — small campus
patch and one room; H — desktop export"*. Milestones 0 and A–G are done or in progress; this
document defines **H through N**.

Read `Docs/PROJECT_REVIEW_2026-11.md` (state and risks) and `Docs/GAME_DESIGN.md` (the game being
built) first. Risk IDs below (R1–R10) refer to the review.

---

## Operating principles

1. **Stop expanding the map until the game loop exists.** The hardest and most valuable rule here.
   Every zone built before enemies, audio, navigation and the real save system exists is a zone that
   must be reopened later to add nav meshes, sound emitters, light volumes, spawn data and save
   hooks. One zone of production art is *enough* to build and prove the entire game. Phase 4 is
   where the campus grows — not before.
2. **Lock the foundation contracts first** (Phase H). Resolution, texel density, renderer, world
   scale and movement feel are referenced by every asset and every zone. They are nearly free to
   change today and very expensive after the second zone.
3. **De-risk the unproven, not the comfortable.** Interiors, audio, enemy AI and navigation have
   zero prior art in this repo. The asset pipeline has 21 successes. Spend the risk budget on the
   former — prove each new discipline on exactly one small case before planning at scale.
4. **Every phase ends playable.** No phase may leave the game broken or unlaunchable.
5. **Keep the batch method, generalise its tooling.** Pre-edit checkpoint → implement → automated
   proof with a headless exit code → written "Known issues" → commit. But fix R5 first, or the
   harness cost grows with every zone.
6. **Add feel budgets to acceptance criteria.** From Phase H on, every batch asserts frame time,
   transition stall and input latency alongside geometry. Otherwise "clean and smooth" is something
   no test can fail.

### Phase overview

| Phase | Name | Theme | Gate out |
|---|---|---|---|
| **H** | Foundation Lock | Decide what everything depends on | Contracts locked and proven; harness generalised |
| **I** | Game Feel | Movement, camera, transitions, **audio from zero** | Walking around Main Gate feels great |
| **J** | The Horror Core | Lantern, night, enemy, stealth, fear | One genuinely frightening loop |
| **K** | Systems & Chapter 1 | Save v2, inventory, journal, puzzles, UI | A 20–30 min playable chapter |
| **L** | Campus Industrialisation | Interior kits, multi-floor, zone tooling, the real campus | Recognisable IUT, explorable |
| **M** | Mirror Campus & Secrets | Shifted world, tunnels, labs, set-pieces | The full game's content |
| **N** | Production | Performance, export, settings, localisation, release | Shipped |

Phases H–J are the critical path and should be done in order. K–N have parallelisable batches.

---

## Phase H — Foundation Lock

**Goal:** answer every question that later work would otherwise have to guess, and pay down the
risks that get more expensive with each zone. Small, unglamorous, highest return in the document.

| Batch | Work | Addresses |
|---|---|---|
| **H1** | **Approval sweep.** Guided pass over the ~12 open visual approvals (`Docs/STATUS.md` manual checks 19–30) in one sitting, with a capture script driving the poses. Record approve / change-list per item. Split `STATUS.md` into a short living status + append-only `VERIFICATION_LOG.md`. Start an approval ledger. | R9, method |
| **H2** | **Presentation contract.** Decide and lock base resolution, stretch mode, texel density target, camera zoom, texture filter and pixel-snap policy. Write `Docs/PRESENTATION.md` as **Confirmed**, update `ART_STYLE.md` / `CONVENTIONS.md`. Prove on one asset that raising `px_per_m` raises sharpness with zero layout or collision change, then batch re-render the library to the chosen density. | R1 |
| **H3** | **Renderer decision.** Stress-test Compatibility vs Forward+ with ~30 dynamic lights, occluders and the real zone at night. Measure frame time on the RTX 3050. Decide and record. Fix the `config/features` label. | R2 |
| **H4** | **Zone validator.** Replace the 9 bespoke check scenes and 6 versioned baselines with one data-driven validator taking a zone id + manifest, plus a documented baseline-refresh workflow. Retire the per-batch baselines once it reproduces their assertions. | R5 |
| **H5** | **Housekeeping.** Remove the three TEMPORARY debug actions and both `*_test_*.gd` lighting scripts from the shipping path (replaced properly in I/J). `git rm -r --cached addons/godot_mcp/cache`. `.gdignore` in `Docs/map-reference/`. Retire `test_zone_a` / `test_zone_b` or move them behind a debug flag. Delete the stale `temp_prompt.txt` / `master_prompt.txt`. Move the zone registry out of a `const` in `main.gd` into a resource. | R10 |

**Exit:** no Undecided item remains that an asset or zone depends on; one validator covers the zone;
the shipping main scene contains nothing named `_test_`.

---

## Phase I — Game Feel

**Goal:** the stated top priority, built properly. Nothing new to *do* in the game yet — but moving
through the existing campus should feel excellent. This is also where audio starts existing.

| Batch | Work | Addresses |
|---|---|---|
| **I1** | **Player controller v2.** Acceleration / deceleration curves, turn response, walk / jog / sneak states with speeds matched to stride length (fixing the 6.25 m/s single speed), 8-direction facing, stamina, and surface awareness reading the ground TileSet. | R3 |
| **I2** | **Animation v2.** Re-render the character for 8 directions, add sneak and jog cycles, a turn transition, and idle variations. Lock footstep events to animation frames. Generator parameters only — the pipeline already does this. | R3 |
| **I3** | **Audio foundation — from zero.** Buses (master / ambience / SFX / footsteps / music / UI), 2D positional audio, per-zone ambience beds and reverb profiles, surface-aware footsteps wired to I2's events, and an audio settings resource. The largest missing discipline in the project. | §6 of design |
| **I4** | **Camera v2.** Deadzone, directional look-ahead, smoothing, per-zone bounds and zoom, state-driven zoom changes, shake. Replace the rigid feet-lock. | design §8 |
| **I5** | **Transition system.** Threaded zone loading, fade in / out, a loading state, and a measured stall budget. Decide transition presentation (currently Undecided). | R4 |
| **I6** | **Occlusion system.** One systemic solution for the player disappearing behind building art — a silhouette through occluders or a depth-aware cutout — retiring hand-placed fade areas and closing the dead band behind the Main Gate tower. | R6 |
| **I7** | **Interaction v2 + prompt UX.** Context-sensitive verbs, hold-to-interact, world-space markers instead of one bottom-centre label, and input-glyph-aware prompts (keyboard vs gamepad — a known gap). | — |

**Exit:** a 5-minute unscripted walk through `main_gate_exterior` and `cds_veranda` with sound, no
hitching, no disappearing player, and movement that reads as weighted. Frame-time and latency
budgets recorded and met.

---

## Phase J — The Horror Core

**Goal:** make it a horror game. The first phase that adds *gameplay*.

| Batch | Work |
|---|---|
| **J1** | **Day/night for real.** A persistent clock, per-zone lighting profiles, a true night pass over Main Gate, `LightOccluder2D` coverage on every prop (currently missing on trees, palms and all pipeline props), and working lamp posts. Retires `day_night_test_tint.gd`. |
| **J2** | **Lantern as a mechanic.** Three-state light (off / low / full), fuel, flicker, refuel stations, reveal-in-light and reveal-in-dark content channels. Retires `lantern_test_light.gd`. |
| **J3** | **Navigation + enemy framework.** `NavigationRegion2D` baked per zone (none exists today), a reusable perception module (light / sound / line-of-sight, weighted) and the `patrol → suspicious → investigate → chase → search → lose` state machine. |
| **J4** | **The Watcher.** First enemy, light-hunting, in night Main Gate. Blender-pipeline character using the proven player-character rig path. |
| **J5** | **Stealth and sound propagation.** Noise radius from surface × speed, hide spots, breath-holding, throwable distractions. Makes the existing ground TileSet a mechanic. |
| **J6** | **Composure + death loop.** Diegetic fear expression (audio, camera, input), the non-death failure state, checkpoints and respawn. |
| **J7** | **The Lister.** Second enemy, sound-hunting — validates that J3 is genuinely reusable rather than one-off. |

**Exit:** a repeatable night loop in one zone that is actually frightening to a first-time player,
with a fail state and a recovery. Playtest it on someone who did not build it.

---

## Phase K — Systems & Chapter 1

**Goal:** the scaffolding content needs, then the first real content built on it. Save architecture
must land **before** content, or the content cannot be saved.

| Batch | Work | Addresses |
|---|---|---|
| **K1** | **Save v2.** Full state (flags, inventory, world deltas, time, enemy state, composure), slots, autosave, atomic temp-file-and-rename writes, versioned migration. | R7 |
| **K2** | **Flags and world state.** A story-flag service and persistent per-object state, so an opened door or a solved puzzle survives a zone reload. Fixes the known "test box colour resets" class of problem. | — |
| **K3** | **Inventory and items.** Data-driven item definitions, carry rules, an examine/inspect view, and key items. |
| **K4** | **Notes, journal and clue system.** Clue IDs, chapter gating, readable notes, a journal UI. Data-driven and localisation-ready from day one. |
| **K5** | **Puzzle framework.** Multi-step puzzle state machines, reusable puzzle objects, editor wiring, and the three puzzle classes from the design doc. |
| **K6** | **Full UI/UX.** Main menu, pause (the `pause` action is registered and unused), settings (audio, video, keybinds, brightness, accessibility), save/load UI, and the diegetic HUD policy. |
| **K7** | **Interior kit proof.** One modular interior kit (floor, wall, door, window, corner, ceiling, stair modules) proven on one real CDS room. **De-risks all of Phase L** — do not skip to L without it. | method |
| **K8** | **Chapter 1.** Assemble a 20–30 minute playable chapter in the existing Main Gate / CDS cluster using everything above. |

**Exit:** a stranger can launch the game from a menu, play Chapter 1 start to finish, save, quit,
reload, and finish. **This is the first build worth showing anyone.**

---

## Phase L — Campus Industrialisation

**Goal:** now grow the campus — every new zone inherits a complete game. Blocked on the reference
trip (R8), so start gathering during Phase I.

| Batch | Work |
|---|---|
| **L1** | **Interior kit production.** Scale K7 into full kits: institutional corridor, classroom, lab, dorm room, stairwell, bathroom, office. Assembly, not bespoke renders — this is the cost model that makes a campus of interiors possible. |
| **L2** | **Multi-floor system.** Floor switching, stairwells, a vertical zone graph, per-floor save state, and camera handling across floors. |
| **L3** | **Zone authoring tooling.** A zone template scene, automated nav baking, automated light placement, automated validator registration. Target: a new blockout zone in hours, not days. |
| **L4** | **Campus layout pass.** From the reference trip: a measured or paced master layout of IUT with zone IDs and a connection graph. Extend `Docs/CAMPUS_MAP.md` beyond area1. |
| **L5+** | **Zone batches**, roughly one landmark cluster each, in the existing Milestone-G batch style: academic buildings, halls of residence, mosque, Five Pillars, library, cafeteria, auditorium, labs, hospital, sports complex. Each: blockout → production exterior → interiors → populate. |
| **Lx** | **Performance at scale.** Culling, LOD, texture budget enforcement, zone splitting or streaming where needed. |

**Exit:** an IUT student recognises the campus, walks it end to end, and enters the buildings that matter.

---

## Phase M — Mirror Campus & Secrets

**Goal:** the content multiplier. Cheap per hour of play *because* Phase L built the geometry.

| Batch | Work |
|---|---|
| **M1** | **Mirror system.** Per-zone shifted variants: lighting and fog profiles, prop substitution and damage variants, altered signage, inverted audio beds, and threshold crossings. |
| **M2** | **Mirror zone batches.** Shifted versions of the highest-recognition zones first (Main Gate, CDS, the academic building). |
| **M3** | **Underground.** Service tunnels beneath the campus — darkness as the default state, no landmarks. |
| **M4** | **The secret lab.** The story's payload. |
| **M5** | **The Follower + set-pieces.** Scripted chases, timed sequences, the finale. |
| **M6** | **Chapters 2–7.** Full narrative assembly, multiple endings. |
| **M7** | **Optional: underwater.** Only if the main line is complete — it needs its own controls, physics and art rules. |

---

## Phase N — Production

Performance pass against the Phase H budgets. Desktop export (the original Milestone H — export
templates still need installing). Settings and accessibility completeness. Localisation (English /
Bengali). Photo mode polish. Credits. External playtesting. Store page, trailer, release.

---

## Sequencing notes

- **The reference trip (R8) gates Phase L and nothing earlier.** Do it during Phase I or J so it
  never becomes the blocker.
- **Audio (I3) is on the critical path, not a polish item.** Phase J's fear design depends on it;
  retrofitting sound into finished systems costs more than building it alongside.
- **K7 before L1, always.** Interiors are the biggest unbuilt category with no proven pipeline.
- **Phases H and I together are roughly one Milestone-G-sized effort** and will produce no new
  content — only a game that feels good. That is the correct trade, and it is worth saying out loud
  before starting, so the lack of visible new buildings does not read as lack of progress.

# Roadmap — Milestones H onward

Snapshot: 20 November 2026 • v2, after decisions D0–D12 (`Docs/DECISIONS.md`)

Audience: the project owner, and any AI session choosing the next batch of work.

Supersedes the Phase 3 milestone table in
`Docs/initial-context-source/05_SETUP_AND_IMPLEMENTATION_PLAN.md`, which ended at "G — small campus
patch and one room; H — desktop export". Milestones 0 and A–G are done. This document defines
**H through N** for ***The Quiet Hours***, a finishable 2–4 hour horror game (D0).

Read first: `Docs/PROJECT_REVIEW_2026-11.md` (state and risks R1–R10), `Docs/GAME_DESIGN.md` (the
game), `Docs/PRESENTATION.md` (the visual and motion contract).

---

## Operating principles

1. **Don't expand the map until the game loop exists.** One zone of production art is enough to
   build and prove the whole game. Zones built now would be reopened later for navigation meshes,
   sound emitters, light volumes and save hooks. The campus grows in Phase L, not before.
2. **The foundation contracts are now decided.** The presentation contract was Confirmed on
   20 November 2026 (`PRESENTATION.md`). Phase H *applies* it. It no longer has to decide it.
3. **Prove anything new on one small case first.** Interiors, audio, creature AI and navigation have
   no prior work in this repo. The asset pipeline has 21 successes. Spend the risk on the new parts,
   one small proof each, before scaling.
4. **Every phase ends playable.** No phase may leave the game unable to launch.
5. **Keep the batch method; generalise its tooling.** Pre-edit checkpoint → implement → automated
   proof with a headless exit code → written Known issues → commit. Fix R5 early.
6. **Smoothness budgets are acceptance criteria** (`PRESENTATION.md` §5), the same as geometry checks.

### Phase overview

| Phase | Name | Theme | Gate out |
|---|---|---|---|
| **H** | Foundation | Apply the presentation contract, generalise the harness, clean house | Crisp at 1080p zoom 2, one zone validator, nothing `_test_` left in the shipping scene |
| **I** | Game feel | Movement, camera, transitions, **audio from zero**, occlusion | Walking around Main Gate feels excellent |
| **J** | The horror core | Night, lantern, navigation, **the Night Guard**, stealth, composure | One genuinely frightening loop |
| **K** | Systems & Chapters 0–1 | Save v2, flags, items, journal, puzzles, UI, the interior kit proof | A stranger plays 35 min start to finish |
| **L** | The surface campus | Interior kits, multiple floors, zone tooling, Chapters 2–3, **the strays** | The recognisable IUT, explorable |
| **M** | Below & the Mirror | Facility art set, Chapters 4–6, Mirror Campus, the source, endings | The whole game, start to finish |
| **N** | Release | Performance, export, settings, playtests, store | Shipped |

H → I → J is the critical path, in that order. K–N contain batches that can run in parallel.

---

## Phase H — Foundation

| Batch | Work | Addresses | Status |
|---|---|---|---|
| **H1** | **Approval sweep.** One guided sitting through the ~12 open visual approvals (`NEXT_ACTIONS.md` §3), with `ZoneCapture.tscn` driving the poses. Split `STATUS.md` into a short living status and an append-only `VERIFICATION_LOG.md`. | R9 | Needs the owner |
| **H2** | **Apply the presentation contract.** 1920 × 1080 base, `canvas_items` / `expand`, fractional scaling, no pixel snap, physics interpolation (with `reset_physics_interpolation()` on every teleport), camera zoom 2. **Re-render the 4 ground tiles at 4× density** (256 px per 2 m cell), with the TileMapLayer at scale 0.25, edge-strip `texture_scale` 4 and mipmaps on. No sprite re-render is needed (measured). Accept on: ground check 316,575 samples, all zone checks, screenshots at 1080p and 1440p. | R1 | **Done 21 Nov** |
| **H3** | ~~Renderer decision~~ **Done 20 Nov 2026: stay on Compatibility** (`DECISIONS.md` D3). What's left: turn `RendererStressTest.tscn` into the reusable frame-time probe for the budgets, and fix the `"Forward Plus"` label in `config/features`. | R2 retired | Mostly done |
| **H4** | **Zone validator.** Replace 9 bespoke check scenes and 6 versioned baselines with one data-driven validator (zone id + manifest) and a documented baseline-refresh workflow. Retire the old baselines once it reproduces their assertions. | R5 | **Done 21 Nov** |
| **H5** | **Housekeeping.** Take the three TEMPORARY debug actions and both `*_test_*.gd` lighting scripts out of the shipping path. `git rm -r --cached addons/godot_mcp/cache`. Add `.gdignore` to `Docs/map-reference/`. Put test zones A/B behind a debug flag. Delete `temp_prompt.txt` and `master_prompt.txt`. Move the zone registry from a `const` in `main.gd` into a resource. | R10 | **Done 21 Nov** |

**H2 + H4 + H5 were done as one batch on 21 November 2026** (`Docs/STATUS.md`, `Docs/TESTING.md`). Phase H still has H1 (needs you at the screen) and the H3 remainder (turning the stress test into a frame-time probe; it fits naturally into I5).

---

## Phase I — Game feel

| Batch | Work | Addresses |
|---|---|---|
| **I1** | **Player controller v2.** Sneak 32 / walk 62 / sprint 154 px/s (`PRESENTATION.md` §4), acceleration and deceleration curves, stamina, 8-direction movement, surface detection from the ground TileSet, physics interpolation checked at 60 and 144 Hz. | R3 |
| **I2** | **Animation v2.** Re-render the character for 8 directions, plus crouched-sneak and run cycles, a turn transition and idle variations. Playback rate follows speed (clamped 0.75–1.25). Footstep events locked to frames. All of it is generator parameters, since the pipeline already does this. | R3 |
| **I3** | **Audio foundation, from zero.** Buses (master / ambience / SFX / footsteps / music / UI), 2D positional audio, ambience beds and reverb per zone, surface-aware footsteps wired to I2's events, an audio settings resource. Source: free CC0 libraries plus your own recordings on campus (see `NEXT_ACTIONS.md` §2, which is free and authentic). | design §6 |
| **I4** | **Camera v2.** Deadzone, look-ahead, easing, per-zone zoom (1.5–2.5) and bounds from data, shake. | design §8 |
| **I5** | **Transitions.** Threaded zone loading behind a fade, a loading state, a measured stall budget (0 visible frames). | R4 |
| **I6** | **Occlusion system.** One systemic answer to the player vanishing behind buildings (a silhouette shown through occluding art, or a depth-aware cutout). Retires the hand-placed fade areas and closes the dead band behind the Main Gate tower. | R6 |
| **I7** | **Interaction v2.** Context verbs, hold-to-interact, prompts placed in the world, keyboard and gamepad glyphs. | — |

**Status 21 November 2026: Phase I complete (I1–I7)** (`Docs/STATUS.md`, Phase I batches 1 and 2). Remaining:
the owner's five-minute feel check below.

**Exit:** a five-minute free walk through `main_gate_exterior` and `cds_veranda`, with sound, no
hitches, the player never vanishing, and movement that feels weighted. Budgets recorded and met.

---

## Chapter 1 slice (21 November 2026, decisions D16–D24): J and K pulled forward

The owner asked for a complete playable piece of the mapped area. It was built by taking the first usable
version of most J and K batches at once (details: `Docs/CHAPTER1.md`). What is done and what remains:

| Batch | Delivered in the slice | Still open |
|---|---|---|
| J1 Night | Story-mode night per zone (`ZoneProfile.night_ambient`), lamps (steady / flickering / dead / needs power), moonlight and exit signs | The clock (11 pm to 4 am), occluders on trees, palms and props |
| J2 Lantern | Off / Low / Full, kerosene, flicker, refuels, reveal-in-light notes, glow-in-dark traces and writing | Fuel shown on the lamp art (D20 uses a small gauge for now) |
| J3 Navigation + creatures | Baked navigation per zone, light / sight / sound perception, the full state machine | A shared creature base class once creature 2 exists |
| J4 Night Guard | Rendered (idle, walk, run, 8 facings), patrol, chase, catch | |
| J5 Stealth and sound | Noise = surface x gait, hide spots (lockers, hedges), crows as spotters | Holding breath, throwables |
| J6 Composure + failure | Vignette, colour drain, heartbeat, breathing, camera; faint and caught -> blackout -> checkpoint | Input lag at low composure, "lose something" on fainting |
| K1 Save v2 | Full story state, autosave checkpoints, atomic writes, v1 saves still load | Slots, migration beyond v1 |
| K2 Flags | Story flags, doors that stay unlocked, collected pickups | |
| K3 Items | Key items (master key), kerosene | Inventory / examine screen, photo mode |
| K4 Notes and journal | Readables, glow writing, journal in the pause menu with the full text | |
| K5 Puzzles | Keypad component, a two-mechanic chain (light reveals / dark reveals) | A general multi-step puzzle framework |
| K6 UI | Title screen, pause, journal, settings (volumes, fullscreen), story cards, HUD (objective, toasts, lantern gauge) | Control remapping, brightness, accessibility options, save / load UI |
| K7 Interior kit | Replaced by the room-shell method (D22): five rooms built from data | Multi-storey rooms, ceilings seen from inside |
| K8 Chapters 0–1 | Chapter 1 complete | Chapter 0 (dusk, before the power fails) |

---

## Whole campus + Chapters 2–4 (22 November 2026, decisions D25–D38): most of Phase L pulled forward

The owner's 12 annotated campus photos (`Docs/map-reference/campus/`) became the whole surface campus and three
more chapters, built autonomously under D16 (decisions D25–D38, plan and log: `Docs/CAMPUS_BUILD.md`).

| Area | What exists |
|---|---|
| Exteriors (4, one shared frame, D28) | `main_gate_exterior` (field, CDS, gate: Chapter 1), `central_plaza` (lake ring, island plaza, Mosque + minaret, Auditorium, Admin, Central Cafe, Five Pillars, three bridges), `halls_exterior` (South / North Hall, palm courtyard, UB Hall, halls gate), `academic_exterior` (Academic 1–3, ME workshops, garage, main road). Walk-off edges join them (`ZoneEdge`). |
| Interiors (12 new concepts) | Academic 1 corridor + room 304, Academic 2 EEE lab, Admin lobby + registrar's office, Mosque prayer hall, Auditorium + AV hall, Central Cafeteria, South Hall corridor + room 203, North Hall common room |
| Art | 22 campus buildings (`author_campus.py`; big ones fade when you walk behind them, D31), 19 interior props, 12 room shells, a diesel generator |
| Chapters | 1 Lights Out -> 2 The Plaza -> 3 Lecture Hall -> 4 The Halls, chained in one session (D32); title menu "Chapters" starts any of them |
| Threats | Night Guard (light + sound), crows (spotters), students (sound hunters, D36), sleepwalkers (drawn to light, D37) |
| Tests | 16 suites, all passing: validator 239/239 (21 zones), Campus traversal 120/120 (every door and edge, live), Chapter 1 49, Chapter 2 41, Chapter 3 27, Chapter 4 22, plus the feel / session / character suites |

Regenerate the campus from its scripts (never hand-edit those scenes): `python tools/zones/campus_zones.py`
(exteriors), `python tools/zones/campus_interiors.py` (interiors), `python tools/zones/map_registry.py`
(the registry in `Docs/CAMPUS_MAP.md`). Next: Chapter 5 "Below" (the facility under the ME workshops) needs a
facility art set; then Chapter 6 (the Mirror Campus) and the endings.

Still open from Phase L: per-building interior accuracy (needs interior photos), more night dressing in the new exteriors, a chapter-select unlock rule for release (today every built chapter is listed).

## Done: Chapter 5 "Below" + the editable map (22 November 2026) — built autonomously, verified, not committed

- **Chapter 5, "Below"** (D40): the ME workshop floor and Site 7 under it (B1 corridor, control room, containment
  lab, the B2 turbine hall). New facility art set (hazard stripes, facility paint, specimen tanks, control desks,
  lathes, workbenches, the caged pit lift). Technicians (former staff; light and sound). The truth about
  Organism 7 (director's log) and the Night Guard (host report). Chapters now chain 1 -> 5; after Chapter 5 the game
  returns to the title. Test: `Chapter5Check`.
- **`map-design/`** (D41): the whole campus as an editable plan (SVG in metres with layers, interior floor plans,
  JSON, PNG previews, a `new-areas/` folder for the owner's photos and notes). Generated from the game; layers
  named `owner...` survive regeneration. See `map-design/README.md`.
- The game stays 2.5D (D39); a realism pass can come later as a re-render.

## Phase J — The horror core

| Batch | Work |
|---|---|
| **J1** | **Night, for real.** A persistent clock (11 pm → 4 am), per-zone lighting profiles, `LightOccluder2D` on every prop (none of the trees, palms or pipeline props has one today), working lamp posts, emergency lighting. Retires the provisional `world_tint.gd` (formerly `day_night_test_tint.gd`). |
| **J2** | **The lantern.** Off / low / full, fuel shown on the lamp, flicker, refuel stations. **Two content channels**: *reveal-in-light* (physical detail) and *glow-in-dark* (bioluminescent traces that wash out under the lantern). Retires the provisional `player_lantern.gd` (formerly `lantern_test_light.gd`). |
| **J3** | **Navigation + creature framework.** `NavigationRegion2D` baked per zone (there is none today), a perception module (light, sound and sight, weighted per creature), the `patrol → suspicious → investigate → chase → search → lose` state machine. Built to be reused by every later creature. |
| **J4** | **The Night Guard.** The first and, for now, only creature (D9). A phototropic host on the real patrol route around the Main Gate and field. Rigged and rendered through the proven player-character pipeline. |
| **J5** | **Stealth and sound.** Noise = surface × mode, hide spots, holding breath, throwable distractions. |
| **J6** | **Composure + failure loop.** Fear expressed through the world (audio, camera, input), the no-death failure state, checkpoints. |

**Exit:** a repeatable night loop in Main Gate that genuinely frightens a first-time player, with
failure and recovery. **Playtest it on someone who didn't build it.**

---

## Phase K — Systems & Chapters 0–1

Save architecture comes **before** content, because content built first can't be saved.

| Batch | Work | Addresses |
|---|---|---|
| **K1** | **Save v2.** Full state (flags, inventory, world changes, clock, creature state, composure), slots, autosave at checkpoints, atomic temp-file-and-rename writes, versioned migration. | R7 |
| **K2** | **Flags and world state.** Story flags and persistent per-object state: doors stay open and solved puzzles stay solved across reloads. | — |
| **K3** | **Items and inventory.** Data-driven item definitions, an examine view, key items, the photo-mode camera. | — |
| **K4** | **Notes, journal, clues.** Clue IDs, chapter gating, readable notes, the journal UI. English only, but the text lives in data. | D11 |
| **K5** | **Puzzle framework.** Multi-step puzzle state machines, reusable puzzle objects wired in the editor, information-trail support for the local's-advantage rule. | D10 |
| **K6** | **UI and UX.** Main menu, pause (the `pause` action is registered and unused), settings (audio, video, controls, brightness, accessibility), save and load UI. | — |
| **K7** | **Interior kit proof.** One modular kit (floor, wall, door, window, corner, ceiling, stair modules) proven on one real CDS room. **Do not start Phase L without it.** | method |
| **K8** | **Chapters 0 and 1.** Assemble them in the Main Gate / CDS cluster. | — |

**Exit:** a stranger launches from the menu, plays about 35 minutes, saves, quits, reloads and
finishes. **The first build worth showing anyone.**

---

## Phase L — The surface campus (Chapters 2–3)

Blocked on the reference-photo trip (R8). Gather photos during Phase I or J.

| Batch | Work |
|---|---|
| **L1** | **Interior kit production.** Scale K7 up into kits for institutional corridor, classroom, lecture hall, dorm room, stairwell, bathroom, office and medical ward. Built by assembly, not bespoke renders. |
| **L2** | **Multiple floors.** Floor switching, stairwells, a vertical zone graph, per-floor save state, the camera across floors. |
| **L3** | **Zone tooling.** A zone template scene, automatic navigation baking, light placement and validator registration. A new blockout zone in hours, not days. |
| **L4** | **Campus layout.** A measured or paced master layout from the reference trip: zone IDs and the hub-and-spoke connection graph. Extend `CAMPUS_MAP.md` beyond area1. |
| **L5** | **Exterior zones.** About 4 new ones: mosque / Five Pillars approach, academic quad, halls area, lakeside, in the Milestone-G batch style. Every unvisited building stands on the map, dark and locked. |
| **L6** | **Chapter 2**: an academic building, 2–3 floors, power puzzles, the crows. |
| **L7** | **The strays**, creature 2, on the J3 framework. Proves the framework is truly reusable. |
| **L8** | **Chapter 3**: a hall of residence and the medical centre. |
| **Lx** | **Performance at scale**: culling, texture budget enforcement, splitting zones where needed. |

**Exit:** an IUT student recognises the campus, walks the hub, and enters every building the story
needs.

---

## Phase M — Below & the Mirror (Chapters 4–6)

| Batch | Work |
|---|---|
| **M1** | **Facility art set.** A new pipeline family: concrete, steel, labs, containment, organism growth. Same camera, light and density contract. |
| **M2** | **Chapter 4: Below.** 2 facility levels, entered from the medical centre's service level. |
| **M3** | **Mirror system.** Per-zone colonised variants: lighting and fog profiles, overgrowth props, damaged prop re-renders through config parameters, altered signage, audio beds, foreshadowing hooks placed back into Chapters 0–3. |
| **M4** | **Chapter 5: The Turning.** Mirror versions of Main Gate, CDS and the academic building, with heavy backtracking. |
| **M5** | **The source + Chapter 6.** The deepest level, the final chase, the Mirror Main Gate finale, 2–3 endings. |
| **M6** | *Optional:* the underwater / flooded facility level, only if the main line is finished. |

---

## Phase N — Release

Performance pass against the budgets on a defined minimum-spec machine. Desktop export (the original
Milestone H; export templates still need installing). Settings and accessibility completeness. Photo
mode polish. Credits. External playtests (IUT students *and* people who have never seen the campus,
to check D10 from both sides). Store page, trailer, release. **No localisation (D11).**

---

## Sequencing notes

- **The reference trip gates Phase L only.** Do it during I or J so it never becomes the blocker.
  Record campus sound on the same trip.
- **Audio (I3) is on the critical path.** Phase J's fear design depends on it.
- **K7 always comes before L1.** Interiors are the largest unbuilt category and have no proven
  pipeline yet.
- **Phases H and I add no new buildings.** That is the right trade, and it is stated here so the lack
  of new buildings doesn't read as lack of progress.

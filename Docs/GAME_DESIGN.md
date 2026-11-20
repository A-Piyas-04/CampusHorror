# Game design

Snapshot: 20 November 2026 • **Status: PROPOSED — nothing here is approved or implemented**

Audience: the project owner, and any AI session implementing gameplay in this repo.

`Docs/initial-context-source/01_GAME_IDEA_AND_GOALS.md` listed "day/night, enemies, puzzles, a
lantern system and mystery" and then correctly recorded: *"Their exact behavior, narrative purpose
and balance have not been specified."* Fourteen months later that is still true, and it is now the
single biggest blocker — you cannot build systems for a game whose verbs you have not chosen.

This document proposes those verbs. It deliberately goes beyond the original prototype brief, as
requested. Mark each section **Confirmed** / **Changed** / **Rejected** as you read; nothing should
be built from a **Proposed** section.

---

## 1. Design pillars

Four rules that settle arguments later. Everything below serves these.

1. **The campus is the character.** Recognition is the primary emotion. A player who studied at IUT
   should feel their stomach drop when they round the CDS corner. This is the one thing no commercial
   horror game can copy, so it gets priority over every other feature.
2. **Light is the core tension, not a utility.** Light must *cost* something. If the lantern is
   purely beneficial, darkness is just an inconvenience. See §3.
3. **Clean, quiet, readable.** No HUD clutter, no screen-filling UI, no jump-scare spam. The
   presentation goal is a calm, crisp, almost beautiful campus that becomes *wrong*. Fear comes from
   composition, sound and silence — the engineering corollary is in §8.
4. **The player is not a fighter.** A student with a lantern. The skill ceiling is in routing,
   timing, observation and nerve — never in combat.

---

## 2. Premise and setting

**Working title:** *IUT: Night Shift* (alternatives: *Ghazipur*, *The Long Semester*, *Lights Out*).

You are an IUT student who stays late on campus to finish work before a deadline. A power failure
drops the campus into darkness. When the lights return, the campus is empty — and subtly, then
grossly, not the campus you know. You cannot leave: the Main Gate is shut, and the road beyond it
goes nowhere.

The story answer to *why* is deliberately left to you to decide; the structure below works with any
of: a research project that went wrong in a lab that officially does not exist; something buried
under the campus during construction; a recurring night that has trapped other students before.
**Pick one before Phase 3** — the journal, notes and endings all key off it.

### The Mirror Campus — the single highest-leverage idea in this document

Build each real zone once. Then present it a second time **shifted**: the same geometry with
different lighting, fog, damaged/overgrown props, altered signage, inverted sound, and enemies.
Crossing over happens through specific thresholds (a particular doorway, the arch passage at night,
a stairwell that goes one floor too far).

Why this matters more than any other proposal here:

- **It roughly doubles content from built assets** — the expensive part (geometry, layout, collision)
  is reused, and the pipeline's existing `layers` / config-parameter system can re-render a variant
  of a prop with different colours and damage cheaply.
- **It is the horror.** Recognition inverted is far more frightening than any monster design,
  and it leans directly on Pillar 1.
- **It makes real-campus accuracy a gameplay mechanic**, not just set dressing — the player navigates
  the dark version using knowledge of the real one.
- **It gives puzzles a natural shape**: observe in one world, act in the other.

Treat the Mirror Campus as the spine of the game, not a bonus area.

---

## 3. The lantern — making light cost something

The lantern is the core verb. Proposed rules:

| Property | Rule |
|---|---|
| Fuel | Finite and visible *on the lamp itself*, never as a HUD bar. Refuel at stations (labs, maintenance rooms, generators). |
| Reveals | Some things exist only in light — safe paths, written clues, physical damage, the true state of a room. |
| Hides | Some things exist only in darkness — certain creatures, certain writing, the Mirror threshold. The player must choose to be blind. |
| Attracts | Light is the primary enemy perception channel. Carrying it lit is loud, in the visual sense. |
| Modes | Off / low (dim, short radius, quiet) / full (bright, wide, attracts at range). A three-state verb, not a toggle. |
| Failure | Fuel exhaustion is survivable but terrifying, never an instant death. |

This single mechanic generates the game's entire moment-to-moment decision loop: *do I light this
corridor and be seen, or cross it blind and miss what is written on the wall?* Everything else —
stealth, puzzles, fear — hangs off it.

**Implementation note:** `Docs/CONVENTIONS.md` already reserves the `lantern` input action and the
`Player/Lantern` attachment point, and `Docs/STATUS.md` flags the open question *"whether the lantern
is usable/visible in daylight"* — answer: yes, visible, but pointless and fuel-wasting. The existing
`PointLight2D` proof is the right technical base; replace `lantern_test_light.gd` outright.

---

## 4. Fear, not jump scares

A **composure** system (avoid the word "sanity" — it is overused and implies mental illness as a
mechanic). Composure drains in darkness, near entities, and at story beats; it recovers in light,
in safe rooms, and on progress.

Expressed **only diegetically** — this is where Pillar 3 is won or lost:

- Breathing and heartbeat in the audio mix (the primary channel, and the cheapest to build).
- Camera: subtle drift, slower recentering, tightening zoom.
- Movement: slight input latency and overshoot at low composure — *the controls themselves get scared*.
- Visuals: desaturation, vignette, edge-of-screen motion that is not there.
- At zero composure: not death. The screen goes quiet and the player is somewhere else, having lost
  something (fuel, progress on a puzzle, an item), with time having passed.

No composure meter is ever drawn. If the player has to read a number to know they are scared, it failed.

---

## 5. Enemies — three kinds, not a bestiary

Deliberately small. Three well-built entities beat ten shallow ones, and each one teaches a
different lesson about the lantern.

1. **The Watcher** — static or slow-patrolling, hunts *light*. Teaches lantern discipline. Introduced
   first, in Main Gate at night.
2. **The Lister** — blind, hunts *sound*. Teaches surface awareness and speed control. Makes the
   existing ground TileSet a gameplay system (see §6).
3. **The Follower** — a scripted, inevitable, story-tied presence. Cannot be defeated or hidden
   from, only outpaced and routed around. Used for set-piece chases and the finale.

Shared AI contract (one reusable system, three configurations): perception (light / sound /
line-of-sight, weighted per entity), and states `patrol → suspicious → investigate → chase → search
→ lose`. Search behaviour must be good — the terror is in *being hunted*, not in being caught.

**Stealth verbs:** hide spots (under tables, in cupboards, behind the CDS arcade piers, in the gate
passage), breath-holding, and throwing an object to pull a Lister off a route.

---

## 6. Sound as a mechanic — and the map you already built becomes a system

`assets/tilesets/campus_ground.tres` already distinguishes **grass, worn grass, paved walkway and
asphalt**, and `Docs/CAMPUS_MAP.md` records where each one is painted. Make that acoustic:

| Surface | Noise radius | Consequence |
|---|---|---|
| Grass | smallest | the safe route, but slow and exposed in the open field |
| Worn grass | small | desire lines — the natural quiet path |
| Paved walkway | medium | fast, and audible |
| Asphalt road | largest | fastest, loudest, and in the open |

Noise radius = f(surface, speed). Walking is quiet; sprinting on asphalt is a dinner bell. The
player's route choice across the central field at night becomes a real decision, using a map that is
**already built and verified**. This is the cheapest meaningful mechanic available to this project —
it is pure gameplay value extracted from completed work.

Audio is currently 0 files. See `Docs/ROADMAP.md` Phase 1 — it is the largest single missing
discipline in the entire project, and for a horror game it carries more fear than the visuals do.

---

## 7. Puzzles and the skill layer

Three classes, in ascending order of how special they are to this project:

**(a) Environmental / systemic.** Restore power to a wing; route a generator; manipulate doors and
light. Uses the lantern and the world, needs no bespoke art. The workhorse.

**(b) Observation and cross-world.** Read something in the Mirror Campus, act on it in the real one
(or the reverse). A code written on a wall that only exists in the dark. A room whose real layout you
must infer from its shifted twin. This is where the Mirror Campus pays off.

**(c) Campus-knowledge puzzles — the signature.** Puzzles whose key is the *real* IUT: building and
room numbering, department layout, the Bengali signage, where a particular tree or plaque actually
stands, the order of the CDS sections. A real IUT student solves these from memory and feels
brilliant; anyone else solves them by exploring and observing, and feels like they learned the
campus. **No other game can have this feature.** Lean on it hard. Keep every one of them solvable by
observation so outsiders are never hard-walled.

**The skill layer** (the "skill-based" part of the original brief) lives in: routing under pressure,
light discipline, timing a crossing, fuel economy, chase navigation, and breath/noise management —
not in reflex tests or combat. A confident player should clear a zone faster and quieter, never by
fighting.

### Proposed ambition add-ons

- **Photo mode as a mechanic** 🟢 — a camera item used to capture anomalies, needed to progress, and
  doubling as a built-in screenshot/marketing tool. High value, low cost, strongly on-theme.
- **Time-of-day as a progression axis** 🟢 — dusk / night / dead-of-night, each changing rules and
  enemy behaviour. Reuses zones; needs the day/night clock the blueprint already reserved.
- **Bilingual English/Bengali** 🟢 — authentic, a genuine differentiator, and already technically
  proven: `main_gate_sign_texture.ps1` shapes Bengali correctly via DirectWrite. Decide early,
  because retrofitting localisation into hardcoded strings is miserable.
- **Found-note voice logs** 🟡 — cheap if you record them yourself; expensive if cast.
- **Co-op / multiplayer** 🔴 — **explicitly out of scope.** It would multiply the cost of every
  system in this document. Recorded here only so the idea stays killed.
- **Procedural campus** 🔴 — rejected. It directly contradicts Pillar 1.

---

## 8. Presentation principles

These are design constraints, not art notes, and they encode the stated top priority.

- **No HUD by default.** Fuel on the lamp, composure in the audio and camera, objectives in the
  journal the player chooses to open. The screen shows the campus.
- **The camera is a cinematographer.** Deadzone, look-ahead in the movement direction, smoothing,
  and per-zone zoom and bounds. Never a rigid lock to the feet (which is what exists today).
- **Motion must be weighted.** Acceleration and deceleration, a turn response, footstep timing
  locked to the animation, and speeds that match stride length (see `Docs/PROJECT_REVIEW_2026-11.md`
  R3 — the current 6.25 m/s single speed is the biggest felt flaw in the build).
- **Crisp, never magnified.** Lock the resolution and texel density contract before more assets
  exist (R1). Softness from stretch-magnified tiles is the specific failure mode to avoid.
- **One light direction, always.** Already enforced by the pipeline — protect it.
- **Transitions are never a hitch.** Threaded load behind a fade; a stall reads as a bug, and
  destroys the calm the horror depends on.

---

## 9. Chapter structure

A frame for scope, not a script. Each chapter = a zone cluster + one new verb + one escalation.

| Ch | Zone cluster | New verb | Escalation |
|---|---|---|---|
| 0 | Main Gate at dusk | Walk, interact, lantern basics | The gate shuts |
| 1 | Main Gate night, CDS exterior + veranda, one CDS room | Light discipline, hiding | The Watcher |
| 2 | An academic building, multi-floor | Sound and surfaces, power puzzles | The Lister |
| 3 | First Mirror crossing of an already-known zone | Cross-world observation | Recognition inverted |
| 4 | Halls of residence / mosque / library cluster | Campus-knowledge puzzles | The campus is populated — wrongly |
| 5 | Underground service tunnels | Vertical routing, no landmarks | Darkness as default |
| 6 | The secret lab | The truth; the game's thesis | The Follower |
| 7 | Mirror Main Gate | Everything | Finale and endings |

The underwater area from the original brief is deferred to a post-launch or Chapter 5½ slot — it
needs its own controls, physics and art rules, and should not block the main line.

**Chapter 1 is the vertical slice**, and it is the right one: the Main Gate and CDS exterior are
*already production art*, so a vertical slice there can look finished rather than greyboxed. No
other project this early can say that.

---

## 10. Decisions this document needs from you

Nothing in `Docs/ROADMAP.md` Phase 2 onward can start until these are answered. They are repeated
with space to answer in `Docs/NEXT_ACTIONS.md`.

1. The premise's *why* (§2) — which explanation?
2. Lantern rules (§3) — accept the three-state cost model, or simplify?
3. Composure (§4) — in, or cut? (Cutting it is a legitimate, cheaper game.)
4. Mirror Campus (§2) — the spine, or a late-game area, or cut?
5. Enemy count — three, or start with one and expand?
6. Campus-knowledge puzzles (§7c) — how central? They are the differentiator but they narrow the
   audience if overused.
7. Bilingual — now, or English-only?
8. Target: a finishable 2–4 hour game, or an open-ended campus to expand forever? **This one changes
   every phase in the roadmap** — answer it first.

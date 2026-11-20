# Next actions — what is needed to continue

Snapshot: 20 November 2026 • updated after decisions D0–D12

Audience: the project owner. This is the only document here with homework in it.

Everything in `Docs/ROADMAP.md` is blocked on one of three things: a **decision** only you can make,
**reference material** only you can gather, or an **approval** only you can give. This document lists
all three, plus the first batch that can start immediately.

---

## 0. State of the repo

21 November 2026: Phase H is committed; **Phase I batches I1–I5 are done and verified, but not committed**:
- Movement with sneak / walk / sprint and stamina.
- 8-direction run and sneak animations whose feet don't slide.
- Footsteps, ambience and reverb.
- A camera that leads.
- Faded door transitions.

Suites: validator 49/49, session 15/15, character 13/13, movement 24/24, audio 19/19, camera 9/9,
transition 13/13, windowed feel probe 3/3. Details are in `Docs/STATUS.md`; checkpoint
`refs/checkpoints/phase-i-preedit`.

## 1. Decisions — all answered (20 November 2026)

All thirteen (D0–D12) are answered and recorded in **`Docs/DECISIONS.md`**, the single source of
truth. In short: a finishable 2–4 h game with backtracking; an underground bio-organism facility as
the premise; horror, not action; light reveals, hides and attracts; composure in; the Mirror Campus
as the late-game spine; one creature first; a local's advantage that is never a wall; English only;
title ***The Quiet Hours***.

The four technical decisions were delegated to Claude and settled **by measurement**, not opinion:
stay on the Compatibility renderer (stress test: identical lighting to Forward+ at 8–48 lights,
steadier frame pacing); 1080p base, camera zoom 2; only the 4 ground tiles need re-rendering
(measured: every sprite is already 3–7× oversampled); sneak 32 / walk 62 / sprint 154 px/s. Full
numbers are in `Docs/DECISIONS.md` and `Docs/PRESENTATION.md`.

**Your remaining review:** the PROPOSED sections of `Docs/GAME_DESIGN.md`: the organism's biology,
the Night Guard, the later creatures, the seven chapters and the ~25–30 zone scope. None of it blocks
Phase H or I. It needs your yes / change list before Phase J (creatures) and Phase K (chapters).

## 2. Reference material — the hard blocker on campus expansion

`Docs/map-reference/` contains exactly one folder, `area1`: the Main Gate, field, courts and CDS.
There is **no reference for anything else on campus**, and `Docs/CAMPUS_MAP.md` records that no
annotated or hand-drawn campus map was ever supplied. The pipeline is photograph-driven, so Phase L
is blocked on a gathering trip, not on code.

Do this during Phase I or J so it never becomes the critical path. Suggested shot list per building:

- **Elevations:** each face straight-on, from far enough back to avoid perspective distortion. The
  south face matters most — it is what the 40° camera shows.
- **Obliques:** both front corners, to recover depth the elevations hide.
- **Verticals:** a full-height shot including the roofline and any parapet or coping.
- **Details:** entrance, windows, arches, signage (both languages), roof plant, drainpipes, railings,
  brick bond, and anything carved or painted.
- **Scale anchor:** one shot with a person, door or your own stride in frame — the pipeline needs
  real metres, and `Docs/STATUS.md` repeatedly flags "approximate, not surveyed" as the main accuracy
  limit on everything built so far.
- **Interiors:** corridor looking both ways, one classroom, one lab, one stairwell, one bathroom,
  floor and ceiling materials. Interiors are the biggest unbuilt category and have **no** references.
- **Ground:** the actual surfaces — brick paving, concrete, tile, grass, dirt paths.
- **Night:** at least a few of each landmark after dark, plus lamp positions and what the lighting
  actually looks like. Phase J needs this and it does not exist.

- **Sound (new, for audio batch I3):** record on your phone at night: wind across the field, the road
  beyond the gate, footsteps on each real surface (grass, brick paving, asphalt, corridor tile,
  stairs), doors, fans, a corridor's room tone, crows, distant dogs. Free, and authentic in a way no
  sound library can be.

Plus, campus-wide:

- An **aerial or satellite image** of the whole campus at usable resolution (the one existing
  `whole view.png` covers area1 only).
- A **layout sketch with distances** — paced is fine. Hundreds of metres of guessed layout is the
  single largest accuracy risk in the project.
- Building and room **numbering**, and department locations — required for the campus-knowledge
  puzzles (D10).

Priority order: the academic building you know best (it becomes Chapter 2), then the mosque and
Five Pillars, then halls of residence, then the library and cafeteria.

---

## 3. Approval backlog

`Docs/STATUS.md` tracks "manual check" numbers to 30. Checks ~19–30 are all recorded as *verified
(automated), pending visual approval* and none were ever closed:

| Check | Item |
|---|---|
| 19 | Asset pipeline output / wall module seam |
| 20 | Architecture batch (doorway, window, pier) |
| 21 | Environment batch (4 ground tiles, trees, hedge, bench, lamp) |
| 22 | Main Gate composition test |
| 23 | Main Gate playable test |
| 25 | Batch 1B — production vegetation |
| 26 | Batch 2 — south boundary wall |
| 27 | Batch 3 — Main Gate landmark |
| 28 | Batch 3A — gate correction and overhead fades |
| 29 | Batch 4 — CDS exterior |
| 30 | Player character |

**Update 21 November 2026:** checks 22 and 23 are obsolete; their scenes were retired in H4. The rest stand, and the ground (checks 21 and 25–29) now looks sharper than when they were recorded.

Do **not** work through these one at a time — that is what stalled before the pause. Batch H1 in the
roadmap collapses them into one guided sitting using `ZoneCapture.tscn` (which already exists and
takes `--shots=` poses) to drive the camera through every item while you approve or list changes.

Carried-over questions worth deciding in that same sitting, from the old "Next task" notes:

- Foot sliding — lower `move_speed`, faster cycle, or a separate run cycle? (Now folded into D4.)
- Which deferred Main Gate details to build: notice pillar, green picket fence, planted strip,
  chain barriers, posters, the east canopy.
- Tower/pavilion roofs read as large flat grey masses — shrink the roof overhang, or accept?
- The residual ~3 m band behind the tower piers where the player is invisible. (Phase I's I6 solves
  this systemically; decide whether to wait for that.)
- Worn-grass variants and hedge end caps — two known composition fixes.

---

## 4. What can start right now

1. **You: the five-minute feel check, with sound on.** Press F5. Walk, sprint (Shift) and sneak (Ctrl)
   across the field, the palm path and the road edge, and through the CDS door and back. Listen to the
   footsteps change between grass and paving, and to the veranda's echo. Watch the camera lead and the door
   fades. Then look at the new sheets (`assets/sprites/characters/player_character_run.png`, `_sneak.png`).
   Anything that feels off is a parameter: speeds, acceleration, look-ahead, fade time, footstep gains.
2. **Next prompt: I6 + I7.** Systemic occlusion (the player is never lost behind a building; this retires
   the hand-placed roof fades and the dead band behind the Main Gate tower) and interaction v2 (prompts placed
   in the world, hold-to-interact, keyboard / gamepad glyphs). That completes Phase I.
3. **Then Phase J:** night, the real lantern, the Night Guard.

**Still yours, any time:** the H1 approval sitting, the photo and sound trip (§2), and the PROPOSED
sections of `Docs/GAME_DESIGN.md` (needed before Phase J).

## 5. Honest expectation setting

Phases H and I together are roughly the size of Milestone G and will add **no new buildings**. What
they produce is a game that feels good to move around in, with sound, that loads without hitching,
on a locked visual contract. Everything after that is cheaper and faster because of it.

If that trade is unacceptable and you want visible new campus sooner, the minimum safe subset is
**H2 + H3 + H5** (lock the presentation contract and the renderer, clean house) before any new zone
work — otherwise every zone built now gets re-cut later.

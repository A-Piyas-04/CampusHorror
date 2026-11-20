# Next actions — what is needed to continue

Snapshot: 20 November 2026

Audience: the project owner. This is the only document here with homework in it.

Everything in `Docs/ROADMAP.md` is blocked on one of three things: a **decision** only you can make,
**reference material** only you can gather, or an **approval** only you can give. This document lists
all three, plus the first batch that can start immediately.

---

## 0. State of the repo, in one line

Nothing is broken, nothing is uncommitted, the toolchain works (Blender 5.2.2, Godot 4.7.2,
Python 3.12), all 21 assets validate, and the real game runs 19/19 headless. Re-verified today.
You can resume cold. Full detail: `Docs/PROJECT_REVIEW_2026-11.md` §2.

Two scratch files should be deleted when convenient: `temp_prompt.txt`, `master_prompt.txt`.

---

## 1. Blocking decisions

### The one that changes everything

**D0. Is this a finishable 2–4 hour horror game, or an open-ended campus to expand forever?**

Answer this before anything else. It changes the shape of every phase in the roadmap. A finishable
game means scope discipline, an ending, and a release. An open-ended campus means tooling investment,
a content pipeline, and no deadline. Both are valid; they are not compatible plans.

### Presentation (blocks Phase H, which blocks everything else)

| # | Decision | Why it cannot wait |
|---|---|---|
| D1 | Base resolution and stretch mode | Not set at all today (defaults to 1152×648 with `expand`); causes the known tile-softness problem, which is the opposite of your stated top priority |
| D2 | Texel density / camera zoom | The character is ~45 px tall on screen; faces only read at zoom 2+. Cheap to change now (one config value per asset), expensive after more zones exist |
| D3 | Renderer: stay on Compatibility or move to Forward+ | Compatibility caps at 8 lights per object / 32 renderable, never tested. A night horror campus will exceed that |
| D4 | Movement speeds | Current single speed is 6.25 m/s — a sprint — which is why the feet slide. Pick walk / jog / sneak values |

Recommendation for D1–D2: lock an explicit base resolution, then raise texture density so the
default camera zoom is texel-exact. Verify on one asset first — the pipeline derives sprite scale
from `px_per_m`, so this *should* cost nothing in layout or collision.

### Game design (blocks Phase J onward)

These are the eight questions at the end of `Docs/GAME_DESIGN.md`. Summarised:

| # | Decision |
|---|---|
| D5 | The premise — *why* is the campus wrong? |
| D6 | Lantern: accept the three-state cost model (light reveals, hides and attracts), or simplify? |
| D7 | Composure/fear system: in or cut? |
| D8 | **Mirror Campus: the spine of the game, a late-game area, or cut?** The highest-leverage call after D0 |
| D9 | Enemies: build all three, or start with one? |
| D10 | Campus-knowledge puzzles: how central? (The differentiator, but it narrows the audience) |
| D11 | Bilingual English/Bengali, or English only? Decide before any string is written |
| D12 | Title |

---

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

## 4. What can start right now, with no decisions from you

If you want progress today, these are unblocked:

1. **H1's mechanical half** — split `Docs/STATUS.md` into a short living status plus an append-only
   `VERIFICATION_LOG.md`, and set up the approval ledger.
2. **H4 — the zone validator.** Replace 9 bespoke check scenes and 6 versioned baselines with one
   data-driven validator. Pure refactor of test tooling, no game or asset changes, and it removes a
   cost that otherwise grows with every future zone.
3. **H5 — housekeeping.** Untrack the MCP cache, add the `.gdignore` to `Docs/map-reference/`, fix
   the `config/features` renderer label, delete the scratch prompt files, move the zone registry out
   of a `const` in `main.gd`, and quarantine the TEMPORARY debug scripts and actions.
4. **H3's measurement half** — build the 30-light stress scene and gather the numbers, so D3 becomes
   a decision with data behind it rather than a guess.

Recommended first prompt: **H4 + H5 together**, then the H1 sitting and the H3 stress test, then
D1–D4 with real measurements in hand.

---

## 5. Honest expectation setting

Phases H and I together are roughly the size of Milestone G and will add **no new buildings**. What
they produce is a game that feels good to move around in, with sound, that loads without hitching,
on a locked visual contract. Everything after that is cheaper and faster because of it.

If that trade is unacceptable and you want visible new campus sooner, the minimum safe subset is
**H2 + H3 + H5** (lock the presentation contract and the renderer, clean house) before any new zone
work — otherwise every zone built now gets re-cut later.

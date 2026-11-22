# Next actions — what is needed to continue

## Map v2: what the owner can do now (22 November 2026)

1. **Play it.** F5, then **Explore campus**.
   - Keys: `M` campus map, `T` time of day, `F` lantern, mouse wheel zoom, `Shift` run.
   - The campus is the official board's layout at true scale, north up. The Main Gate is at the bottom-right
     (south-east).
2. **Check the layout against your board.**
   - Open `map-design/reference/board_overlay.png` (the game's layout over your photo) or `map-design/campus_map.svg`
     (switch on its "Reference" layer).
   - Corrections go in an `owner` layer, or as notes.
3. **Send one more photo.** Your board photo cuts off two corners:
   - the **north-west**, where #24 Medical Center/Laundry runs off the edge;
   - the **south-east**, where the Main Gate (#1) is.

   Please photograph those two corners of the board.
4. **Send photos of buildings built only from the aerials** (list in `map-design/new-areas/README.md`):
   - 3rd Academic, the workshops, the Female Hall, the VC Residence;
   - the staff quarters, the Medical Center, the New Male Hall site.
5. **Commit** when you are happy. Nothing has been committed; private checkpoints are `pre-map-v2` and
   `map-v2-m2-explore`.


Snapshot: 20 November 2026 • updated after decisions D0–D12

Audience: the project owner. This is the only document here with homework in it.

Everything in `Docs/ROADMAP.md` is blocked on one of three things: a **decision** only you can make,
**reference material** only you can gather, or an **approval** only you can give. This document lists
all three, plus the first batch that can start immediately.

---

## 0. State of the repo

22 November 2026: **the whole surface campus and Chapters 1–5 are playable**, chained from the title screen
(Chapter 1's hatch leads into Chapter 2, and so on; after Chapter 5 the game returns to the title). Everything
since the last commit is in the working tree; private checkpoints: `chapter2-playable`, `chapter3-playable`,
`chapter4-playable`, `chapter5-playable` (`tools/checkpoint.sh`). All 16 test suites pass (`bash tools/run_checks.sh`).

What to do now, in order:
1. **Play it**: F5 (title screen), sound on. "Chapters" on the title menu starts any chapter (1-5) directly
   (it replaces your save). Debug build keys: F3 next beat, F4 guard off/on, F7 refill the lantern.
2. **Tell me what to change**: the campus layout (positions are approximate, from the photos), the interiors
   (all concepts), difficulty, story text.
3. **Commit** when you're happy.
4. **Add to the map**: draw new areas in an `owner` layer of `map-design/campus_map.svg`, or drop photos and
   notes in `map-design/new-areas/` (see `map-design/README.md`), then tell me.
5. **Optional references** that would raise accuracy: photos of any interiors you want matched; the area
   beyond the lake (west) and beyond the ME workshops (north), currently the campus edge.

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

## 2. Reference material — the rest of the campus

Only area1 (Main Gate, field, courts, CDS) exists. **`Docs/MAP_INTAKE.md` says exactly when, what and how to
send the rest.** In short:
- **Now:** a whole-campus aerial view plus a labelled sketch (about 30 minutes).
- **Before Phase L:** photo sets for the Chapter 2 and 3 areas.
- **After that:** one area ahead of each campus batch.

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

1. **You: the feel check, with sound on (about 10 minutes).** F5, then:
   - Walk, sprint (Shift) and sneak (Ctrl).
   - Walk behind the gate tower and the trees (silhouette).
   - Walk up to the CDS door (prompt), and use it with a gamepad if you have one (glyph switches).
   Anything that feels off is a parameter.
2. **You: the whole-campus layout** (`Docs/MAP_INTAKE.md` stage 1), whenever you can.
3. **You, before Phase J:** approve or change the PROPOSED parts of `Docs/GAME_DESIGN.md`: the organism, the
   Night Guard, the chapters. Phase J builds them.
4. **Next prompt: Phase J (the horror core).** A real night clock and lighting, the lantern as a mechanic,
   navigation and the creature framework, the Night Guard, stealth and sound, composure. That is where it
   becomes a horror game.

**Still yours, any time:** the H1 approval sitting.

## 5. Honest expectation setting

Phases H and I together are roughly the size of Milestone G and will add **no new buildings**. What
they produce is a game that feels good to move around in, with sound, that loads without hitching,
on a locked visual contract. Everything after that is cheaper and faster because of it.

If that trade is unacceptable and you want visible new campus sooner, the minimum safe subset is
**H2 + H3 + H5** (lock the presentation contract and the renderer, clean house) before any new zone
work — otherwise every zone built now gets re-cut later.

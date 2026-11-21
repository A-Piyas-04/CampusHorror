# Map intake — how to give Claude the rest of the campus

Snapshot: 21 November 2026 (updated after the Chapter 1 slice)

Audience: the project owner. What to collect, when it's needed, and how to hand it over.

So far the game has references for **one area only**: `Docs/map-reference/area1/` (Main Gate, central field,
sports courts, CDS). Everything else of IUT is still to come. The asset pipeline builds from photographs, so
new campus areas can't be built until their references exist. This document turns that into a simple
routine.

---

## 1. When

| Stage | What | Needed by | Your time |
|---|---|---|---|
| **1. Now** | The **whole-campus layout**: an aerial / satellite view plus a labelled sketch (§2.1) | Before Phase K's chapter work. It decides the hub-and-spoke map, the zone boundaries, the backtracking routes and where the existing Main Gate area connects. Cheap to give, and it shapes everything after it | About 30 minutes, from home |
| **1b. Now, optional, quick win** | **Inside the rooms already built** for Chapter 1: the CDS canteen, the table-tennis room, the indoor games hall, the CDS veranda and the Main Gate security office. These interiors were *invented* (only exteriors had references). Per room: one photo from each corner, the floor and wall finishes up close, the furniture, signs and notice boards, and rough sizes (paces are fine) | Any time: I rebuild a room from its data file (`assets/source/blender/tools/author_rooms.py`) in one batch | One visit, about 20 minutes |
| **2. Before Phase L** (about two big batches from now, after Phases J and K) | **Full photo sets for the first two areas the story uses**: the academic building for Chapter 2 and its surroundings, then the hall of residence and medical centre for Chapter 3 (§2.2) | The first Phase L batch | One campus visit |
| **3. Rolling** | Each further area, **one batch ahead** of the batch that builds it (mosque / Five Pillars approach, library, cafeteria, lakeside, …) | I'll ask for the next area at the end of each campus batch | One visit per area or two |

You don't need everything at once, and you don't need to finish an area to start sending it. I'll keep
asking for the next concrete set before it becomes a blocker.

---

## 2. What

### 2.1 Stage 1: the whole-campus layout

1. **Aerial view.** One or more screenshots of the whole campus from a satellite map (zoom so the whole
   campus fits, plus a closer screenshot per quarter if detail is lost). Include the Main Gate, so I can
   line it up with what's already built.
2. **A labelled sketch.** Draw over a printout or a screenshot, or draw on paper and photograph it. Mark
   every building with its real name, the main paths and roads, gates, the lake or ponds, fields, and the
   approximate number of floors per building. It doesn't need to be neat; it needs to be **named**.
3. **A short list in `notes.md`** (template in §3): the buildings that matter most to you and to students,
   which ones you know inside well, and any places only a local would recognise (good for the
   local-knowledge puzzles, decision D10).

### 2.2 Stage 2+: one area's photo set

For each building or place in the area:

- **Elevations:** each outside face, straight on, far enough back to see the whole face. The **south face
  matters most**, because it's what the game camera shows.
- **Both front corners**, to show depth.
- **Full height:** roofline, parapet, water tanks, anything on the roof.
- **Details:** entrances, windows, arches, signs (both languages), railings, pipes, plaques, brick or tile
  patterns, bins, benches, lamps.
- **Scale anchor:** at least one photo with a person, a door, or your own shoes in it.
- **Ground:** the real surfaces underfoot (paving, concrete, grass, gravel, tiles).
- **Night:** a few photos after dark (where the lights are and what they light). Phase J needs this.
- **Interiors** (only buildings the story enters): the corridor looking both ways, one typical room,
  stairwell, toilets, floor and ceiling. Room numbering and what's on the doors.
- **Sound** (phone voice recorder, about a minute each): footsteps on each surface, the corridor's room
  tone, doors, fans, outdoor night ambience, crows, distant dogs. Your recordings replace the
  placeholders (`assets/audio/CREDITS.md`).

Practical tips:
- Phone photos are perfect. Don't crop or edit them.
- Avoid identifiable people's faces where you can; the repository may be shared one day.
- Anything you can't photograph, just describe in chat. That's useful too.

---

## 3. How

1. Make a folder per area: `Docs/map-reference/<areaN>_<short_name>/`, for example
   `area2_academic_1/`. Inside, use any of: `aerial/`, `exterior/`, `interior/`, `night/`, `sound/`.
   Unsorted is fine too; I'll sort it.
2. Add `notes.md` to the folder:

   ```markdown
   # <Area name>
   Buildings: <name> (<floors> floors), <name> ...
   Must be recognisable: <what a student would notice first>
   Entered in the game: <which buildings / rooms, if you know>
   Local knowledge: <room numbering, nicknames, things only students know>
   Not in the photos: <anything missing or changed recently>
   ```
3. Tell me in chat: **"area2 is in"** (plus anything you want to point out).
4. I'll check the set against §2.2 and tell you what's missing (if anything) before building.
5. **Size:** `Docs/map-reference/` is ignored by Godot (it has a `.gdignore`), but it is in git. Phone photo
   sets get big. If an area is over about 100 MB, tell me, and I'll keep the originals out of git and commit
   downscaled copies.

The current area1 references stay as they are.

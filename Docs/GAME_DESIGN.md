# The Quiet Hours — game design

Snapshot: 20 November 2026 • v1

Audience: the project owner, and any AI session building gameplay in this repo.

**Status key.** Sections marked **CONFIRMED** follow the owner's decisions (D0–D12, recorded in
`Docs/DECISIONS.md`). Sections marked **PROPOSED** are Claude's working design built on those
decisions: story beats, creature details, chapter contents. They are ready to build from once the
owner approves them or asks for changes.

---

## 1. Design pillars — CONFIRMED in spirit

1. **The campus is the character.** Recognition is the main emotion. A player who studied at IUT
   should feel their stomach drop when they round the CDS corner at night. No other game can copy
   this, so it takes priority over every other feature.
2. **Light is the core tension, not a tool.** Light reveals, hides and attracts (D6). Every choice
   about light has a cost.
3. **Clean, quiet, readable.** No HUD clutter, no screen-filling UI, no jump-scare spam. A calm, crisp,
   almost beautiful campus that turns wrong. Fear comes from composition, sound and silence.
4. **The player never fights (D5).** A student with a lantern. The skill is in routing, timing,
   observation and nerve. There are no weapons, ever.

---

## 2. Premise — CONFIRMED (D5); story beats PROPOSED

**Title: *The Quiet Hours*** (D12; reasoning in `Docs/DECISIONS.md`).

**The facility (confirmed).** Under the campus is an underground research facility, unknown to the
students, where experiments with a bio-organism went wrong. The organism has changed humans and
animals into horrifying creatures. This is horror, not action: the creatures are to be avoided,
understood and escaped, never fought.

**The organism (proposed): it explains the core mechanic biologically.** It is **phototropic** and
**bioluminescent**:

- Its hosts are **drawn to light**. That is why light *attracts*.
- Its growth, trails and markings **glow faintly in the dark** and wash out under a lantern. That is
  why light *hides*.
- Under light, the physical world shows plainly: blood, damage, writing, the real state of a room.
  That is why light *reveals*.

So all three rules of the lantern come from one piece of biology, and none is an arbitrary game rule.
Players who work that out play better, and that is the kind of understanding horror should reward.

**Opening (proposed).** You are a student who stayed on campus past quiet hours to finish a project
before a deadline. At 11 pm the power fails across the campus. When the emergency lights come up, the
campus is empty: no guards at the gate, no one in the halls. The Main Gate is chained shut from
outside. Something is moving on the security guard's patrol route, and it is still in uniform.

### How the Mirror Campus is both late and the spine (D8)

The owner chose: *the spine of the game, a late-game area*. This design reconciles the two by making
the game's whole shape **surface → below → back to a changed surface**:

1. **First half: the real campus.** You learn IUT at night, as it really is. You are learning a map
   the game will later use against you.
2. **The middle: the facility.** You go below and learn what the organism is.
3. **The second half: the Mirror Campus.** You come back up and the campus has been *colonised*. The
   same buildings, paths and rooms you learned, now grown over, glowing, rearranged and inhabited.
   Every route you memorised is now a question.

It is the spine because the first half exists to set up the second. It is late because you only
cross into it after the facility. It is **foreshadowed from the first minutes**, so its arrival feels
inevitable rather than random: a doorway that is wrong for one frame, faint bioluminescence in the
wrong place, a notice board whose text changes when you look back at it.

**Production benefit.** Mirror zones reuse built geometry, collision and layout. They differ in
lighting profile, overgrowth props, damaged prop variants (a re-render through the existing config
system), altered signage and audio. That roughly doubles playable space from the same assets, and it
also justifies the backtracking D0 asks for.

---

## 3. The lantern — CONFIRMED (D6), tuning PROPOSED

| Property | Rule |
|---|---|
| Three states | **Off** (blind, invisible, bioluminescence visible) · **Low** (short radius, quiet) · **Full** (wide, attracts hosts from a distance) |
| Reveals | Physical detail: writing, blood, damage, the true layout of a room, readable notes |
| Hides | Bioluminescent traces: organism trails that mark safe routes and where hosts nest, and messages written in growth |
| Attracts | Hosts are phototropic, so light is their main sense. Full light is loud in the visual sense. |
| Fuel | Finite, and shown **on the lamp itself** (flame size, flicker, colour), never as a HUD bar. Refuelled at maintenance rooms, labs and generators. |
| Running out | Survivable and terrifying, never an instant death |

The moment-to-moment decision this creates: *light this corridor and be seen, or cross it blind and
follow the glow?*

Implementation: replaces the PROVISIONAL `scripts/lighting/player_lantern.gd` (renamed from `lantern_test_light.gd` in H5). It keeps the reserved `lantern`
action and the `Player/Lantern` attachment point. The lantern works in daylight but is pointless and
wastes fuel.

---

## 4. Composure — CONFIRMED (D7), expression PROPOSED

Composure drains in darkness, near creatures, and at story moments. It recovers in light, in safe
rooms, and when you make progress. It is never drawn on screen. It is expressed only through the
world:

- **Audio** (the main channel): breathing, heartbeat, the ambience narrowing.
- **Camera**: slight drift, slower recentring, zoom tightening within the zone's allowed range.
- **Movement**: slight input lag and overshoot at low composure. The controls themselves get scared.
- **Visuals**: desaturation, vignette, movement at the edge of the screen that isn't there.
- **At zero**: no death. The screen goes quiet and you come to somewhere nearby, having lost
  something (fuel, an item, puzzle progress), with time having passed.

---

## 5. Creatures — CONFIRMED (D9: start with one); details PROPOSED

**One reusable AI framework** handles perception (light, sound, line of sight, each weighted per
creature) and the states `patrol → suspicious → investigate → chase → search → lose`. Searching must
feel thorough. The fear is in being hunted, not in being caught.

**Creature 1, built first: the Night Guard.** The campus security guard, still in uniform, still
walking his patrol route around the Main Gate and the field, now a phototropic host. He hunts
**light** above everything, which teaches lantern discipline from the first encounter. He is grounded
in the real campus (IUT has guards at the gate), and his patrol gives the first zone a rhythm the
player can learn. He appears in Chapter 1 and is the vertical slice's only creature.

**Later creatures**, built on the same framework once it is proven:

- **The strays.** Campus dogs, changed. They hunt in a pack by **sound and scent**, and they make the
  ground surfaces matter (§6). Animal mutation, per D5. Appear in Chapter 3.
- **The crows.** Not chasers: spotters. A disturbed flock alerts nearby hosts. Cheap to build and
  deeply unsettling. Ambient from Chapter 2.
- **The source.** The organism's origin in the deepest facility level. It is unavoidable and cannot
  be hidden from, only escaped, and it drives the final chase. Chapter 6.

**Stealth verbs**: hide spots (under tables, in cupboards, behind the CDS arcade piers, in the gate
passage), holding your breath (costs composure), and throwing an object to pull a creature off its
route.

---

## 6. Sound as a mechanic — PROPOSED

The ground TileSet already distinguishes grass, worn grass, paved walkway and asphalt, and they are
painted across the built zone. Make them acoustic:

| Surface | Noise | | Mode | Multiplier |
|---|---|---|---|---|
| Grass | lowest | | Sneak | 0.4× |
| Worn grass | low | | Walk | 1× |
| Paved walkway | medium | | Sprint | 3× |
| Asphalt / tile / metal grating (facility) | highest | | | |

Noise radius = surface × mode. Sprinting on asphalt rings the dinner bell. Crossing the central field
at night becomes a real routing decision on a map that is **already built and verified**.

Audio today is 0 files. For a horror game it carries more fear than the visuals do, so it is on the
critical path (roadmap I3), not polish.

---

## 7. Puzzles and the local's advantage — CONFIRMED rules (D10, D11); content PROPOSED

**The rule (D10): campus knowledge is a shortcut, never a wall.**

- **Every** puzzle has an in-game information trail: signs, notice boards, timetables, department
  maps, room-number plaques, notes, a campus map you can find. A newcomer always has enough to solve
  it by looking.
- A real IUT student can **skip the trail**: they already know which building is which, how rooms are
  numbered, where the side path is, what the sign says. They solve it faster, and that is the reward.
- **Local privileges** (optional, never required): real shortcuts only a local would try (the actual
  gap in the hedge, the real side entrance); secret spots and lore at places only a local would
  recognise; recognition achievements.
- A newcomer must never feel locked out, and a local must regularly feel *seen*.

**Three puzzle classes:**

- **Environmental and systemic.** Restore power to a wing, route a generator, work doors and light.
  The workhorse.
- **Light-state.** Read something in the dark that light erases, then act on it in the light, or the
  reverse. Uses the D6 rules directly.
- **Campus knowledge.** Keyed to real IUT layout, numbering and signage, always solvable from the
  information trail too.

**Language (D11): English only** for all text, UI and notes. The Bengali signage stays as authentic
environment art, as the Main Gate sign already is. Keep text in data files anyway (cheap, and it
keeps editing easy), but don't build a translation pipeline.

**Skill** shows in: routing under pressure, light discipline, fuel economy, timing a crossing, chase
navigation, managing noise and breath. A confident player clears an area faster and more quietly,
never by fighting.

### Add-ons kept from the earlier proposal

- **Photo mode as a mechanic** 🟢: a camera item to document anomalies. Some progress depends on it,
  and it doubles as a screenshot tool.
- **Time of night as a progression axis** 🟢: 11 pm → 2 am → 4 am, each changing creature behaviour
  and light levels.
- **Shortcuts** 🟢: unlockable routes that shrink backtracking as the map opens, as in the best
  exploration games.
- **Out of scope**: co-op or multiplayer, procedural campus, combat, localisation.

---

## 8. Presentation principles — CONFIRMED

Exact values are in `Docs/PRESENTATION.md`: 1080p base, camera zoom 2, sneak, walk and sprint
speeds, physics interpolation, frame-time budgets.

- **No HUD by default.** Fuel shows on the lamp, composure in the audio and camera, objectives in a
  journal the player chooses to open.
- **The camera is a cinematographer**: deadzone, look-ahead, easing, per-zone framing.
- **Movement has weight**: acceleration, footsteps locked to the animation, speeds matched to the
  stride.
- **Crisp, never magnified. Smooth, never hitching.**

---

## 9. Structure and scope — CONFIRMED shape (D0: 2–4 h with backtracking); chapters PROPOSED

**The campus is a hub with spokes.** The Main Gate and central field (already built) are the hub.
Buildings branch off it. Locked doors, dead power and blocked paths open up over time, so you return
through known spaces by new routes. Shortcuts keep backtracking quick.

| Ch | Title | Where | New verb or threat | Approx. |
|---|---|---|---|---|
| 0 | Quiet Hours | Main Gate at dusk, CDS | Walk, interact, lantern; the power fails | 10 min |
| 1 | Lights Out | Main Gate at night, field, CDS veranda and one CDS room | Light discipline, hiding, **the Night Guard** | 25 min |
| 2 | Lecture Hall | An academic building, 2–3 floors | Restoring power, sound, the crows | 30 min |
| 3 | The Halls | A hall of residence and the medical centre | Composure under pressure, **the strays** | 30 min |
| 4 | Below | Into the facility through the medical centre's service level, 2 facility levels | The truth: what the organism is | 35 min |
| 5 | The Turning | **Back to the surface, into the Mirror Campus**: Main Gate, CDS, academic building, colonised | Every known route changed; heavy backtracking | 35 min |
| 6 | Source | The deepest facility level, then the Mirror Main Gate | **The source**: final chase and endings | 25 min |

**Total: about 3 h 10 min**, inside the 2–4 h target, with room to cut or grow. Two or three endings,
keyed to what you discovered and who you helped.

**Scope this implies (it keeps the game finishable):**

| Zone type | Count | Notes |
|---|---|---|
| Exterior zones | ~5 | Main Gate and field (built), plus mosque / Five Pillars approach, academic quad, halls area, lakeside. Exteriors are cheaper to build and are where exploration happens. |
| Interior zones | ~10–14 | **Curated**: only the buildings the story enters. Other buildings stand on the map, recognisable but dark and locked (natural for a campus at night). |
| Facility levels | 3–4 | New art set: concrete, steel, labs, containment |
| Mirror variants | ~4–5 | Reuse geometry |
| **Total zone scenes** | **~25–30** | |

This is an important consequence of D0. The original "90 % exact copy of the campus" survives as the
**exterior**: walkable, recognisable, accurate. Interiors are curated to the story. Every unvisited
building is still present on the map, so the campus still reads as complete.

**Underwater** (from the original brief): an optional flooded facility level connected to the pond
west of the palm path, if time allows after the main line. It needs its own controls and art rules,
so it never blocks the main line.

---

## 10. Open design questions — for later, not blocking

These do not block Phases H–J and can be answered when Chapter 1 is playable:

- What the player character is called, and whether they speak (notes and thoughts only, or voice).
- The ending conditions.
- Whether there are other survivors (NPCs) at all, or the campus is truly empty.
- Whether the crows also appear outside the Mirror Campus. Proposed: yes, as ambient dread from
  Chapter 2.

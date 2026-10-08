# Campus map

Snapshot: 8 October 2026 • Milestone G Part 1 (blockout)

This document records the real-campus areas built in the game, their stable IDs and how accurate their layout is. Everything here is a **blockout**: placeholder shapes that prove layout, scale and navigation. Final 2.5D art comes later (see `Docs/ART_STYLE.md`).

Status vocabulary for accuracy (section F):

| Label | Meaning |
|---|---|
| **Known** | Stated by the user or directly visible in the supplied references. |
| **Approximate** | Placed or sized by eye from the references; expected to be corrected. |
| **Undecided** | Not known yet; a placeholder choice was made only so the game runs. |
| **Adjustable** | Built so the user can move/resize it in the Godot editor without code changes. Everything in the blockout is Adjustable. |

## References used

All in `Docs/map-reference/area1/`:

| File | What it shows | Used for |
|---|---|---|
| `whole view.png` | Aerial view from the road side: Main Gate bottom-left, road along the bottom, courts between field and road, CDS on the right, palm path along the left and top | **Primary layout reference** (relative positions) |
| `field+cds(upper portion).jpg` | Aerial of the palm-lined path, the field and the CDS building with its forecourt | Palm path, CDS forecourt, low arcade section |
| `field.jpg` | Panorama across the field with courts on the right and red-brick buildings behind | Court strip, field openness |
| `field+cds.jpg` (a WebP file with a `.jpg` name) | Ground-level photo of CDS across the field | CDS massing, arches |
| `cds-building.png`, `cds-building2.png` | CDS facade: low arched section with a paved forecourt, taller section with large pointed arches, bushes along the front | CDS massing, arches, forecourt, greenery |
| `tennis+futsal court.png` | Fenced courts beside the field | Court fences and surfaces |
| `mainGate.jpg` | Main Gate: red-brick mass, tall opening with layered white pointed arch, large overhanging roof, a columned side pavilion with a green sign, low brick wall, planted frontage | Main Gate massing |

No annotated / hand-drawn map is in the reference folder. The layout is therefore based on `whole view.png` plus the written description in the Milestone G brief. **If a hand-drawn map exists, it should replace these assumptions.**

## A. Prototype scope

Boundary: the **Main Gate area only**. The playable rectangle is closed by the south boundary wall (with the gate) and by three hedge-like `PrototypeEdge*` blocks on the west, north and east. These edges are prototype limits, **not** real campus boundaries.

Included:

- Main Gate landmark (piers, arch, roof slab, side pavilion with columns, closed gate leaves)
- Road and sidewalk outside the south wall (visible, not walkable)
- Central grass field with placeholder line markings
- Paths: west palm path from the gate northwards, north path, east path beside CDS, south path between field and courts, gate plaza, CDS forecourt
- Sports-court strip: one futsal/basketball court and one tennis court, fenced
- CDS exterior: canteen (north), table-tennis (middle) and indoor-basketball (south) sections, each with a lower veranda frontage on the west
- CDS veranda (separate zone): covered walkway with placeholder fronts for the three future rooms
- Vegetation: palms along the west and north paths, trees beside CDS, near the gate and along the south wall

Explicitly excluded:

- Everything outside the edges above, including the water/pond visible west of the palm path in `field+cds(upper portion).jpg` and the buildings beyond the north path
- CDS interiors (canteen, table-tennis room, indoor basketball court) and any room mechanics
- NPCs, story content, sports gameplay, lamp-post lights

## B. Zone registry

| zone_id | Name | Scene | Purpose | Main contents | Connections | Status |
|---|---|---|---|---|---|---|
| `main_gate_exterior` | Main Gate exterior | `scenes/world/MainGateExterior.tscn` | First real playable area; game start zone | Gate, field, paths, courts, CDS exterior, vegetation, south wall, road | `DoorCdsMainEntry` → `cds_veranda` | Blockout, verified via MCP |
| `cds_veranda` | CDS veranda | `scenes/world/CdsVeranda.tscn` | Covered walkway along the CDS west facade | Floor, arcade columns, parapet, roof edge, three future-room fronts | `DoorCdsExitToField` → `main_gate_exterior` | Blockout, verified via MCP |
| `test_zone_a`, `test_zone_b` | Test zones | `scenes/world/TestZoneA.tscn`, `TestZoneB.tscn` | Milestone C–F test rooms | — | Each other | Kept registered for tests and old saves; no longer the start zone |

`Main` starts in `main_gate_exterior` at `main_gate_entry` (`start_zone_id` / `start_spawn_id` on the `Main` node).

## C. Spawn registry

| spawn_id | Zone | Position (feet) | Purpose / location |
|---|---|---|---|
| `main_gate_entry` | `main_gate_exterior` | (−1390, 960) | Game start. On the west palm path just inside (north of) the Main Gate, clear of the gate roof. |
| `outside_cds_entrance` | `main_gate_exterior` | (1380, −200) | On the CDS forecourt, 72 px west of the CDS main door. Arrival when leaving the veranda. |
| `inside_cds_entry` | `cds_veranda` | (0, −50) | In the middle of the veranda walkway, 90 px east of the exit door. Arrival when entering CDS. |

`cds_exit_spawn` (proposed in the brief) was **not created**: `outside_cds_entrance` already serves as the exit arrival point. The ID stays free for later use.

## D. Door / transition registry

Doors have no ID property in the current architecture (`Door` exports only `destination_zone_id`, `destination_spawn_id`, `prompt_text`). The transition IDs below are recorded here and used as the door's node name.

| Source zone | Transition ID | Door node | Destination zone | Destination spawn | Prompt |
|---|---|---|---|---|---|
| `main_gate_exterior` | `cds_main_entry` | `Objects/Transitions/DoorCdsMainEntry` at (1452, −200), on the west face of the CDS table-tennis veranda | `cds_veranda` | `inside_cds_entry` | "Press E to enter the CDS veranda" |
| `cds_veranda` | `cds_exit_to_field` | `Objects/Transitions/DoorCdsExitToField` at (−90, −50), against the west parapet | `main_gate_exterior` | `outside_cds_entrance` | "Press E to go out to the field" |

Reserved future IDs (documented only, **not implemented**; the matching fronts in `cds_veranda` are non-interactive):

| Future transition ID | Planned from | Leads to |
|---|---|---|
| `cds_canteen_entry` | `cds_veranda` (`CanteenFront`) | Future canteen zone |
| `cds_table_tennis_entry` | `cds_veranda` (`TableTennisFront`) | Future table-tennis room zone |
| `cds_indoor_basketball_entry` | `cds_veranda` (`IndoorBasketballFront`) | Future indoor basketball zone |

## E. Area relationships

Coordinates are `main_gate_exterior` pixels; +x = east (screen right), +y = south (screen down). The field centre is near (0, −50).

```text
                 north hedge (prototype edge)
      palms ......................................... palms
   +--------------------- north path -------------------+  +-----+
   |                                                    |  | CDS |  canteen
 w |                                                    | e|     |
 e |                 CENTRAL FIELD                      | a|     |  table tennis  <- door cds_main_entry
 s |                                                    | s|     |                  (forecourt to the west)
 t |                                                    | t|     |
   +--------------------- south path -------------------+  |     |  indoor basketball
 palm      [ futsal/basketball ]   [ tennis ]              +-----+
 path        trees along the south wall
 [MAIN GATE]=========== south boundary wall ===========================
 ------------------------------- road --------------------------------
```

| Element | Relationship | Accuracy |
|---|---|---|
| Main Gate | South-west corner of the area, opening south onto the road; the west palm path leads north from it | Known (relative position); Approximate (exact offset) |
| Road | Runs east–west along the south, outside the boundary wall | Known (relative); Approximate (width) |
| Central field | Dominant open area in the centre, east–west long axis | Known (dominance, position); Approximate (size, orientation of markings) |
| Sports courts | South of the field, between field and road, east of the gate; futsal/basketball west, tennis east | Known (strip position); Approximate (sizes, gap, order) |
| CDS | East of the field, long north–south mass; canteen north, table tennis middle, indoor basketball south | Known (east side, section order from the brief); Approximate (all dimensions) |
| CDS veranda | Covered frontage along the CDS west facade, facing the field | Known (exists, faces field); Approximate (depth, length); Undecided (whether it runs the whole length) |
| CDS main entrance | Middle of the west facade (table-tennis section) with a paved forecourt | Approximate / Undecided — position chosen for the blockout |
| West palm path | From the gate north along the west side of the field, palms on both sides | Known (from aerials); Approximate (width, palm spacing) |
| North path | Along the north edge of the field, palms on its north side | Approximate (inferred from `whole view.png`) |
| East and south paths | Connect the west path to the CDS forecourt around the field | Approximate / Undecided — added for circulation |
| Trees | Bushes/trees in front of CDS, trees along the south wall, two near the gate | Approximate |

## F. Accuracy status

| Item | Value used | Status |
|---|---|---|
| Scale | Roughly 32 px ≈ 1 m (player body 64 px ≈ 2 m), **compressed**: real distances are larger | Undecided |
| Field | 2400 × 1500 px at x −1200..1200, y −800..700 | Approximate |
| Paths | ~120 px wide (west/north), ~80–100 px (south/east) | Approximate |
| Courts | Each 600 × 300 px including apron, centres (−200, 1000) and (550, 1000); fences 70 px high with a 100 px gap on the north side | Approximate; gap positions Undecided |
| CDS footprint | 450 × 1700 px at x 1550..2000, y −1000..700; canteen 550 deep, table tennis 450, indoor basketball 700 | Approximate |
| CDS heights | Canteen/table tennis 110 px, indoor basketball 170 px, veranda 80 px | Approximate (the taller section is assumed to be the basketball hall) |
| CDS veranda frontage | 70 px deep along the whole west facade | Approximate |
| Main Gate | Piers 80 × 160 px, 220 px high, opening 120 px wide; side pavilion 220 × 140 px to the west | Approximate |
| South wall | y = 1400, 70 px high | Approximate |
| Prototype edges | x −1700, y −1350, x 2250 | Undecided (prototype limits only) |
| Veranda zone | 270 × 1700 px walkway, columns every 170 px | Approximate |
| Vegetation | 27 palms, 15 trees | Approximate (rhythm only, not real tree positions) |

Needs the user's campus knowledge:

1. Where exactly the gate sits relative to the field's south-west corner, and whether the palm path starts right at the gate.
2. The real order, sizes and spacing of the courts, and where their gates are.
3. Whether the CDS sections are in the right order and roughly the right relative lengths; which section is taller.
4. Where the real CDS entrance used by players is, and whether the veranda runs along the whole west side.
5. Whether a north path and an east path exist as built, or should be moved/removed.
6. Field orientation (direction of play) and size relative to the CDS length.

## How to edit the map in Godot

- Each area is a separate node: `Ground/Field`, `Ground/Paths/*`, `Ground/Roads/*`, `Objects/SportsCourts/<Court>`, `Objects/Buildings/MainGateLandmark`, `Objects/Buildings/CDSExterior/<Section>`, `Objects/Boundary/*`, `Objects/Vegetation/<Group>/*`.
- Ground surfaces are `Polygon2D`s: select one and drag its vertices.
- Moving a court, a CDS section or the gate: move its parent node; surfaces, fences and blocks move together.
- Buildings, walls, fences and hedges are `BlockoutBlock` instances: change `Footprint Size`, `Wall Height`, colours and `Arch Count` in the Inspector; collision and shadows follow automatically.
- Trees and palms are instances of `scenes/props/Tree.tscn` / `PalmTree.tscn`: duplicate (Ctrl+D) and move.
- Overhead pieces (`Overhead/MainGateOverhead`, `Overhead/CdsEntranceCanopy`) are **not** children of the buildings (see `Docs/CONVENTIONS.md` §3). When moving the gate, move `Overhead/MainGateOverhead` by the same amount (both sit at (−1390, 1400)).
- Doors and spawn markers: move them, keep their IDs. Keep each arrival spawn more than 56 px from the door it lands next to.

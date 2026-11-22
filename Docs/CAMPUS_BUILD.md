# Campus build: the whole-campus master plan and progress log

**RESUME HERE.** This file is the single source of truth for the whole-campus build that started 22 November
2026. Any session (or a session after context compaction) continues from the checklist in section 7. Update
the checklist as each stage lands. Owner's standing instruction: **take every decision yourself, never ask,
never commit (the owner commits), deliver the ultimate final version.** Decisions here are recorded in
`Docs/DECISIONS.md` as D25+.

## 1. Inputs

- `Docs/map-reference/campus/01..12-*.png`: the owner's annotated photos of the rest of IUT (copied from
  `new-full-map/`, which the owner may delete). `12-whole-campus-aerial-labelled.png` is the master aerial.
- Already built (Chapter 1, commit 754bcf4): `main_gate_exterior` (central field, CDS block, Main Gate,
  courts, south road wall), CDS interiors (canteen, table tennis, indoor games hall, veranda), Main Gate
  security office.
- Owner: areas beyond the lake (west) and beyond the ME workshops (north) are NOT photographed; leave them as
  the campus edge. Interiors of academic buildings, admin, mosque, auditorium, north hall, south hall, AV hall
  are to be **designed as concepts** (no interior references).

## 2. Reference analysis (what each photo shows)

| # | Shows | Use |
|---|---|---|
| 01 | Central Plaza at ground level: herringbone red brick paving with white grid lines; Admin building (left, 3 storeys, deep vertical brick fins, AC units, ground-floor arches); Central Cafe ahead (low block, 4 tall pointed arches over a recessed arcade); the minaret ("Pillars": tall brick cylinder with a square cage top cut by semicircles); Mosque (right, brick cube with a huge semicircular cut window); plaza lamps (black poles, cluster of 5 white globes); a road runs north between Admin and Cafe | Plaza ground, cafe, admin, minaret, mosque, lamps |
| 02 | Mosque front: windowless brick cube, a giant half-disc recess with stepped (ziggurat) dark glazing, small arched door under it; arched brick bridge railing over the lake on the left; minaret right | Mosque facade, lake bridge |
| 03 | Aerial: Academic Building 2 (8+ storeys, deep grid facade full of AC units, huge brick cylinder towers), garage (two long shade canopies over parking), ME workshops (low sheds among trees), Academic Building 3 beyond | Academic 2, garage, ME workshops |
| 04 | From Academic 2's roof: North Hall left, UB Hall at the far end, South Hall right, a dense tree/palm courtyard between, a small arched gatehouse | Halls layout |
| 05 | Aerial: Academic Building 1 (grid facade, 6 storeys), garage, South Hall corner | Academic 1 |
| 06 | Halls courtyard at ground level: brick path between palms, North Hall left (huge brick cylinders, round and pointed-arch openings), UB Hall at the far end, South Hall right (grid windows) | Halls courtyard |
| 07 | Opposite direction: path to a low arcade wall with a central gate arch, South Hall left, North Hall right | Halls gate + arcade wall |
| 08 | Aerial of the halls: three long blocks around a garden courtyard, UB Hall closing one end, a big field beyond | Halls massing |
| 09 | From South Hall's roof: Central field left, pillars + Central Cafe + Admin + Auditorium + Academic 1 beyond | Relative positions |
| 10 | Same area: Central Cafe, Admin, Auditorium, Academic 1 and 2, South Hall's two wings around a garden | Relative positions |
| 11 | South Hall front: entrance under a tall slot of open storeys, brick cylinders, pointed-arch and circular windows, green sign "South Hall of Residence", lawn, street lamp | South Hall facade |
| 12 | Whole campus aerial: lake complex (Auditorium, Mosque, Admin, Pillars/minaret, Central Cafe, 5 Pillars gate in the lake, bridges, three lake lobes), CDS + Indoor games beside the Central field, South Hall row and North Hall row with UB Hall at the end, Academic 1/2/3 and ME workshops behind | Master layout |

**Orientation (decision D25).** The game's compass is the existing one (Main Gate south-west, road south, CDS
east of the field, canteen at CDS's north end). Matching photo 12 and `area1/field+cds(upper portion).jpg` to
that: the camera of photo 12 looks **east**. So, in game directions:
- the palm path from the 5 Pillars to the CDS canteen is the existing **north path** (field to its south, lake
  complex to its north); the 5 Pillars stands at the lake's corner by the junction of the west palm path and
  the north path;
- the **lake complex (Central Plaza)** lies **north of the field**;
- **South Hall** and **North Hall** are long north–south blocks **east of the CDS** (South Hall nearer the CDS,
  North Hall further east), the palm courtyard between them, **UB Hall closing the south end**, the halls'
  gate and arcade wall at the north end (photos 04, 06, 07 agree);
- **Academic Buildings 1 and 2** stand north of the halls / north-east of the plaza, **Academic 3** and the
  **ME workshops** further north-west; the **garage** between Academic 2 and the plaza.
The names "North" / "South" Hall don't match these game directions; that is fine (the real campus is rotated
relative to the game's arbitrary compass).

**Readability concession (D26).** The camera only ever sees south faces. Iconic facades are turned to face
south where the real building faces another way: the Mosque's half-disc, the Central Cafe's arches, the Admin
fins, the Auditorium's arcade, the hall entrances. Adjacencies are kept.

## 3. The campus world plan (game px; the `main_gate_exterior` frame; +x east, +y south; 32 px/m across,
20.576 px/m in depth)

```
 y
-5400 ............ campus edge (unmapped beyond ME workshops) ..............................
        [ME workshop A]   [Academic 3 (long, low)]
-4700   [ME workshop B]                 [Academic 2]   [garage]
                         [Academic 1]                    ┌ halls gate + arcade wall ┐
-3300  .............. lake north bank ........  road N   │                          │
        ~~~~~~~~~~~~~~~ LAKE ~~~~~~~~~~~~~~~~~~~~~~~      │ South   palm    North    │
        ~ [Admin]   road  [Central Cafe]       ~         │ Hall    court   Hall     │
        ~        PLAZA (grid paving, lamps)     ~         │ (N–S)   yard    (N–S)    │
        ~ [Mosque][minaret]      [Auditorium]   ~         │                          │
-1180   ~[5P]~~~~~~~~ bridge ~~~~~~~~~~~~~~~~~~~~         │                          │
-1115  ── north path (palms) ─────────────► [CDS canteen]  │                          │
         CENTRAL FIELD (built)               [CDS table tennis]                       │
-50                                           [CDS indoor games]    └──── UB Hall ─────┘
 1400  [MAIN GATE]═══════════ south wall ═══════════════════════════════════════════════
         x: -1350          0              1480    2000   2300                       3900
```

| Zone (zone_id) | Frame offset | Extent (campus px) | Contents | Edges |
|---|---|---|---|---|
| `main_gate_exterior` (built) | 0, 0 | x -2400..3000, y -1800..1950 | field, CDS, gate, courts | north edge (y -1650, x -1300..1600) -> plaza; east edge (x 2900, y -1000..900) -> halls |
| `central_plaza` | its own frame, origin = campus (150, -2250) | campus x -1500..1800, y -3500..-1150 | lake ring, island plaza, 5 Pillars, Mosque, minaret, Admin, Central Cafe, Auditorium, bridges, plaza lamps, palms | south bridge -> field; north bridge/road -> academic; east path -> halls |
| `halls_exterior` | origin = campus (3100, -800) | campus x 2200..4000, y -3000..1300 | South Hall, North Hall, UB Hall, courtyard, halls gate + arcade wall, street lamps | west -> field (CDS side); north gate -> academic |
| `academic_exterior` | origin = campus (1500, -4300) | campus x -1500..4000, y -5400..-3300 | Academic 1, 2, 3, ME workshops A/B, garage, roads | south road -> plaza; south-east -> halls gate |

**Decision (S5): every exterior zone uses the shared campus frame above directly (no offsets)**, so a position means the
same place in every zone. Plaza layout (campus px): lake outer x -1420..1720, y -3500..-1500; island deck x -1100..1400,
y -3294..-1706; south bank y -1500..-1250; Mosque centre (-650,-2050); minaret (-230,-1930); Auditorium (760,-2100);
Admin (-455,-2950); Central Cafe (850,-2950); road north between them x 185..370 over a north bridge; south bridge
x -500 (to the field side); east bridge y -2500 (to the halls side); 5 Pillars (-1190,-1600) in the lake's SW corner.
Field <-> plaza edges: three segments at y -1330 (main_gate_exterior) / y -1300 (central_plaza), arrival spawns at
y -1200 (field) and y -1420 (plaza).

Zones meet at **edge transitions** (walk into a trigger strip at the zone edge -> faded travel to the matching
spawn in the neighbour). Interiors use the existing interact-doors.

## 4. Art to build (Blender pipeline; authoring scripts in the repo under `assets/source/blender/tools/`)

Exterior buildings (one asset each, Y-sorted layers + fades for anything tall the player walks behind):

| asset_id | From | Size (m, approx) | Notes |
|---|---|---|---|
| `plaza_mosque` | 01, 02, 12 | 18 x 18 x 15 | brick cube, south half-disc recess with stepped dark glazing, arched door |
| `plaza_minaret` | 01, 02 | 3.4 dia x 30 | brick cylinder, square cage top with semicircle cuts |
| `plaza_central_cafe` | 01, 12 | 30 x 16 x 9 | four tall pointed arches on the south face, recessed arcade, flat roof |
| `plaza_admin` | 01, 12 | 40 x 16 x 12 | 3 storeys, deep vertical fins, ground arches, AC units |
| `plaza_auditorium` | 12 | 34 x 26 x 12 | big box, pointed-arch arcade on the south, roof stair heads |
| `five_pillars` | area1, 12 | 9 x 4 x 11 | five parallel brick walls, a pointed arch through them |
| `lake_bridge` | 02, 12 | modular | brick causeway with arched railings and steel lattice under |
| `plaza_lamp` | 01 | 4.5 tall | black pole, 5 white globes |
| `south_hall` | 06, 07, 08, 11 | 22 x 120 x 16 (N–S) | sliced; south front with entrance slot, cylinders, arch + round windows |
| `north_hall` | 06, 07, 08 | 22 x 120 x 16 (N–S) | sliced; big cylinders, pointed arches, round windows |
| `ub_hall` | 06, 08 | 70 x 18 x 16 (E–W) | many small pointed arches on its north (courtyard) and south faces |
| `halls_gate_wall` | 07 | 40 x 1 x 3.5 | low arcade wall with a central gate arch |
| `academic_1` | 05, 09 | 50 x 20 x 22 | grid facade, AC units, two brick stair cylinders |
| `academic_2` | 03, 04 | 40 x 22 x 30 | taller grid facade, giant cylinders |
| `academic_3` | 03, 12 | 70 x 14 x 8 | long low block, red roof band |
| `me_workshop` | 03, 12 | 50 x 14 x 7 | long shed, pitched roof (two instances) |
| `garage_canopy` | 03, 05 | 24 x 8 x 3 | shade canopy on steel posts |
| `street_lamp_tall` | 06, 11 | 8 tall | curved-arm street lamp |

Ground: a plaza paving tile (herringbone brick with a white grid) and water (Polygon2D + water shader).

Interior concepts (room shells, `author_rooms.py`):

| Room asset | Building | Concept |
|---|---|---|
| `academic_corridor_room` | Academic 1 | long corridor, classroom doors, notice boards, stair cylinder |
| `academic_classroom_room` | Academic 1 | rows of benches, whiteboard, projector |
| `academic_lab_room` | Academic 2 | electronics lab benches, scopes, cabinets |
| `admin_lobby_room` | Admin | reception, waiting benches, registrar counter, portraits |
| `admin_office_room` | Admin | officer desks, files, safe (story key) |
| `mosque_prayer_hall_room` | Mosque | carpet rows, mihrab, minbar, Quran stands, the half-disc window light |
| `auditorium_hall_room` | Auditorium | raked seats, stage, curtains, projection booth |
| `av_hall_room` | Auditorium wing (D27: AV hall is the Auditorium's audio-visual hall) | projector screen, seats, control desk |
| `central_cafe_room` | Central Cafe | food court counters, long tables |
| `hall_corridor_room` | South Hall | dorm corridor, room doors, laundry lines, water filter |
| `hall_room_room` | South Hall | dorm room: beds, desks, lockers |
| `hall_common_room` | North Hall | TV room, carrom boards, newspapers |

Props (new, `author_props.py`): classroom bench-desk, whiteboard, projector + screen, lab bench, oscilloscope,
office desk, file cabinet, safe, reception counter, prayer carpet row, Quran stand (rehal), minbar, auditorium
seat row, stage, dorm bed, study desk, wardrobe, carrom board, TV, plaza bench, parked car, motorbike, bins,
signboards.

## 5. The game across the campus (chapters; extends `Docs/GAME_DESIGN.md` section 9)

| Ch | Title | Where | Goal / verbs | New threat |
|---|---|---|---|---|
| 1 | Lights Out (built) | CDS, field, Main Gate | find a light, the gate is chained, the breaker, the hatch | Night Guard |
| 2 | The Plaza | 5 Pillars bridge, Central Plaza, Mosque, Central Cafe, Admin | Below the hatch is a flooded service tunnel that surfaces in the plaza's lake pump room. Find the Admin's master plan of the campus; the Mosque is the safe room (no host enters a mosque: lights, the imam's note); the Central Cafe's cold room; the Admin safe needs the registrar's code from the Auditorium | the crows (spotters), the Night Guard follows |
| 3 | Lecture Hall | Academic 1 and 2, garage | Power the academic wing from the generator by the garage; the electronics lab; the projector puzzle in the AV hall reveals a recorded lecture about the organism | sound-hunting hosts (the "students") |
| 4 | The Halls | South Hall, courtyard, North Hall, UB Hall | Find the survivors' radio in North Hall's common room; escort / hide; the strays in the courtyard | the strays (dog pack) |
| 5 | Below | facility under the ME workshops (the workshops' pit lift) | what the organism is; the source of the power | facility hosts |
| 6 | The Turning / Source | the Mirror Campus (plaza, halls, field reused, colonised), then the Main Gate | escape; endings | the source |

Chapters 2–4 are buildable from these references; 5–6 need a facility art set (concept, no references).

## 6. Engineering rules for this build

- Authoring scripts live **in the repo** (the scratchpad was wiped once): zone scene writers go in
  `tools/zones/`, asset authoring in `assets/source/blender/tools/`.
- Checks: `tools/run_checks.sh` (all suites). Checkpoints: `tools/checkpoint.sh <name>` before each stage.
- Every new zone: registry entry, profile (`data/zones/profiles/`), validator manifest + reviewed baseline.
- Never commit. Never ask. Record decisions as D25+.

## 7. Checklist (update as you go)

- [x] S0 Copy references to `Docs/map-reference/campus/`; checkpoint `campus-start`
- [x] S1 This plan
- [~] S2 Decisions (D25–D30 done) D25–D30 in `Docs/DECISIONS.md`; `Docs/CAMPUS_MAP.md` section for the whole campus; `GAME_DESIGN.md` chapter table refresh; memory pointer to this file
- [~] S3 Engine: `ZoneEdge` (scripts/components/zone_edge.gd + scenes/components/ZoneEdge.tscn, validator rule) DONE; water shader (assets/shaders/water.gdshader) DONE; plaza ground = existing paved_walkway tile + white Line2D grid (decided); ZoneEdge test TODO
- [x] S4 (ALL 22 campus assets BUILT + validated, 22 Nov) Exterior building assets: `assets/source/blender/tools/author_campus.py` writes 21 configs (category `campus`); `assembly` gained a `prism` part, author_lib gained `prism`, `pointed_arch`, `half_disc`. Batch build log: tools/.check-logs/campus_build1.log. Next: inspect renders (assets/sprites/campus/*.png), fix, then S5
- [~] S5 tools/zones/campus_zones.py WRITTEN and RUN: scenes/world/CentralPlaza.tscn, profile, manifest, registry entry, CampusEdges block in MainGateExterior.tscn (3 edges to plaza + EdgeToHalls + arrival spawns). Plaza edges point at `academic_exterior` and `halls_exterior` which DO NOT EXIST YET: build S6/S7 zones before running the validator. Then: run validator, review, dump baselines. Zone `central_plaza` (+ edge from `main_gate_exterior`), profile, manifest, baseline
- [~] S6 Zone `halls_exterior`: GENERATED by campus_zones.py (South Hall x 3400, North Hall x 4935, 4 segments each from y 615 north; UB Hall (4170,900); gate wall; palms; lamps; edges to field/plaza/academic). Validator + baseline TODO
- [~] S7 Zone `academic_exterior`: GENERATED (Academic1 (1700,-4320), Academic2 (3500,-4620), Academic3 (500,-5180), ME workshops (-850,-4320/-4800), garage canopies (2720,-3720/-3430), main road y -3940; edges to plaza/halls). Validator + baseline TODO
- [ ] S8 New props for interiors
- [ ] S9 Interior rooms + zones + doors (section 4 table)
- [ ] S10 Night dressing for the new exteriors (lamps, glow, horror props, crows)
- [ ] S11 Chapter 2 director + content; then Chapter 3, Chapter 4
- [ ] S12 Tests (validator, a campus traversal check, chapter checks), docs, final report

## 8. Log

- 22 Nov 2026: S0, S1 done. D25–D30 recorded. ZoneEdge + water shader written. author_campus.py (21 assets: plaza_mosque,
  plaza_minaret, plaza_central_cafe, plaza_admin, plaza_auditorium, five_pillars, plaza_lamp, lake_bridge, lake_edge,
  south_hall_front/wing, north_hall_front/wing, ub_hall, halls_gate_wall, academic_1/2/3, me_workshop, garage_canopy,
  street_lamp_tall) written; first batch build launched.
- 22 campus assets all PASS (campus_build2 + campus_build3).
- Rebuild list after campus_build2 (DONE): plaza_auditorium (stale blend removed), lake_bridge_ns (new), south_hall_front + north_hall_front (window/entrance overlap fixed).
- S6/S7: halls_exterior and academic_exterior generated; all edges now have destinations. NEXT: wait for campus_build2 batch, rebuild plaza_auditorium + lake_bridge_ns (+ any FAILED), Godot import, run validator on the 3 new zones + main gate, fix, dump baselines, windowed captures.
- S5: plaza zone generated (151 nodes); lake_bridge_ns asset added (22 configs). Validator NOT yet run.
- Fix: Blender's brick/checker textures are 2D, so vertical faces froze one axis (walls rendered as flat mortar grey).
  `assembly.planar_coords()` now projects (x,y) on top faces, (x,z) on north/south faces, (y,z) on east/west faces;
  tiles take `bw` (brick width / row height; brick_wall uses 3.0). Roof slabs sit 3 cm proud of the wall top.
  Mosque re-render verified (red brick, half-disc, stepped glazing, arched door). Full batch relaunched:
  tools/.check-logs/campus_build2.log.

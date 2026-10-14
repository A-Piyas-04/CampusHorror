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
| `mainGate.jpg` | Main Gate: red-brick mass, tall opening with layered white pointed arch, large overhanging roof, a columned side pavilion with a green sign, low brick wall, planted frontage | **Main Gate truth** (user, Batch 3): the production gate is reconstructed from this photo plus the aerial `whole view.png`. Not to be confused with the Five Pillars (`5-pillars*.png`), a different landmark |

No annotated / hand-drawn map is in the reference folder. The layout is therefore based on `whole view.png` plus the written description in the Milestone G brief. **If a hand-drawn map exists, it should replace these assumptions.**

## A. Prototype scope

Boundary: the **Main Gate area only**. The playable rectangle is closed by the south boundary wall (with the gate) and by three hedge-like `PrototypeEdge*` blocks on the west, north and east. These edges are prototype limits, **not** real campus boundaries. The south boundary wall is the real campus road wall. Since Milestone G Batch 2 it is a production red-brick run with pilasters, and since Batch 3 the Main Gate is production art; the prototype edges are still blockout.

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
| `main_gate_exterior` | Main Gate exterior | `scenes/world/MainGateExterior.tscn` | First real playable area; game start zone | Gate, field, paths, courts, CDS exterior, vegetation, south wall, road | `DoorCdsMainEntry` → `cds_veranda` | Blockout with production ground (Batch 1A), vegetation (Batch 1B), south road wall (Batch 2), Main Gate (Batch 3) and CDS exterior (Batch 4); verified via MCP; courts and prototype edges still blockout |
| `cds_veranda` | CDS veranda | `scenes/world/CdsVeranda.tscn` | Covered walkway along the CDS west facade | Floor, arcade columns, parapet, roof edge, three future-room fronts | `DoorCdsExitToField` → `main_gate_exterior` | Blockout, verified via MCP |
| `test_zone_a`, `test_zone_b` | Test zones | `scenes/world/TestZoneA.tscn`, `TestZoneB.tscn` | Milestone C–F test rooms | — | Each other | Kept registered for tests and old saves; no longer the start zone |

`Main` starts in `main_gate_exterior` at `main_gate_entry` (`start_zone_id` / `start_spawn_id` on the `Main` node).

## C. Spawn registry

| spawn_id | Zone | Position (feet) | Purpose / location |
|---|---|---|---|
| `main_gate_entry` | `main_gate_exterior` | (−1390, 960) | Game start. On the west palm path just inside (north of) the Main Gate, clear of the gate roof. Node: `Objects/Buildings/MainGateLandmark/SpawnMainGateEntry` (moves with the gate). |
| `outside_cds_entrance` | `main_gate_exterior` | (1380, −200) | On the CDS forecourt, 72 px west of the CDS main door. Arrival when leaving the veranda. Node: `Objects/Buildings/CDSExterior/TableTennis/SpawnOutsideCdsEntrance` (moves with CDS). |
| `inside_cds_entry` | `cds_veranda` | (0, −50) | In the middle of the veranda walkway, 90 px east of the exit door. Arrival when entering CDS. |

`cds_exit_spawn` (proposed in the brief) was **not created**: `outside_cds_entrance` already serves as the exit arrival point. The ID stays free for later use.

## D. Door / transition registry

Doors have no ID property in the current architecture (`Door` exports only `destination_zone_id`, `destination_spawn_id`, `prompt_text`). The transition IDs below are recorded here and used as the door's node name.

| Source zone | Transition ID | Door node | Destination zone | Destination spawn | Prompt |
|---|---|---|---|---|---|
| `main_gate_exterior` | `cds_main_entry` | `Objects/Buildings/CDSExterior/TableTennis/DoorCdsMainEntry` at world (1452, −200), on the west face of the CDS table-tennis veranda | `cds_veranda` | `inside_cds_entry` | "Press E to enter the CDS veranda" |
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
| South boundary wall | Continuous, solid, low red-brick wall between the campus and the road, from the Main Gate east past both courts (and further east in reality); a tree band stands just inside it, and the court fences are a separate layer north of the trees. Pilasters about every 3 m (user) | Known (continuity, material, order field → court fence → trees → wall → road, pilasters); Approximate (height, line, pilaster spacing, east end) |
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
| CDS footprint | 450 × 1700 px at x 1550..2000, y −1000..700 plus the 70 px veranda frontage (facade line x 1480); canteen 550 deep, table tennis 450, indoor basketball 700. Unchanged by Batch 4 (collision = the blockout rectangles) | Approximate |
| CDS heights | Production since Batch 4: low block (canteen, table tennis) 4.2 m to the coping, hall 8.8 m | Known: the hall is the taller section (photos). Approximate: both heights (estimated) |
| CDS west facade | Canteen: arcade of 8 pointed arches with low sill walls in front of the covered veranda; table tennis: 5 arch bays with the open entrance bay at the door (y −200) and a plain wall with vents; hall: 9 tall bays. Edge-on from the 40° / 0° camera, so only the coping line along x 1480 shows | Known (photos): arcades, materials. Approximate: bay counts and spacing. Inferred: the parts hidden in the photos |
| CDS hall south face | 4 blind pointed-arch bays with steel grille windows and a plinth | Inferred (plan default; the south face is not in the photos) |
| CDS roofs | Low block: dark bitumen with patches, 2 satellite dishes near the west parapet; hall: light-grey concrete; brick parapets with light coping | Known (photos): materials, dishes. Approximate: parapet heights, dish positions |
| CDS dressing | Bangladesh and white flagpoles on the lawn west of the canteen (world (1426, −482) / (1426, −516)), lamp at the forecourt's north-west corner (1356, −326), red paved forecourt | Known (photo): flags, lamp, forecourt paving. Approximate: positions |
| CDS veranda frontage | 70 px deep along the whole west facade | Approximate |
| Main Gate | Production since Batch 3 (`MainGateTower`, `MainGateLeaves`, `MainGatePavilion`); roofs split into faded overhead layers in Batch 3A (geometry unchanged). Tower local x −172..140 (9.75 m), 6.74 m deep (to local y −131.6), brick 8.6 m, roof rim 9.55 m, roof overhang 1.25 m; passage local x ±76.16 (4.76 m clear), clear apex ≈ 6.15 m, three white rings 0.28 / 0.32 / 0.42 m; leaves 2.5 m high at the wall line (stop y 1390); pavilion room local x −360..−172, y −140..0, 3.3 m high, canopy x −407..−109 on five columns at local y +58, sign 9.3 × 1.65 m | Known (photo + aerial): features, materials, arrangement (pavilion west, arch off-centre to the east, roof tray). Approximate: every dimension (estimated, not surveyed); leaves at the wall line instead of set back; tower and room footprints kept to the blockout's extents (wall join at +140, room to −360). Not built: notice pillar, green fence, planted strip, chain barriers, posters, passage inner columns, east canopy |
| South wall | Production run since Batch 2: line y 1400 (footprint centre), x −1250..2302, 37 `RedBrickWall3m` modules (3 m = 96 px, 2.4 m ≈ 70 px high) and 38 `RedBrickVerandaPier` pilasters (2.8 m) on every join and both ends; player stops at feet y ≈ 1394.96 | Known: continuous low red-brick road wall with coping and pilasters (references + user). Approximate: height and coping profile (fixed by the generated module), pilaster spacing exactly 3 m, line y 1400 and start x −1250 (inherited from the blockout), end x 2302 (closes the prototype; the real wall continues east). Not built: road-facing banners/posters, gate-like elements, wall variations |
| Prototype edges | x −1700, y −1350, x 2250 | Undecided (prototype limits only) |
| Veranda zone | 270 × 1700 px walkway, columns every 170 px | Approximate |
| Vegetation | 27 palms, 15 trees (production `CoconutPalm` / `BroadleafTree` since Batch 1B, same positions) | Approximate (rhythm only, not real tree positions) |

Needs the user's campus knowledge:

1. Where exactly the gate sits relative to the field's south-west corner, and whether the palm path starts right at the gate.
2. The real order, sizes and spacing of the courts, and where their gates are.
3. Whether the CDS sections are in the right order and roughly the right relative lengths; which section is taller.
4. Where the real CDS entrance used by players is, and whether the veranda runs along the whole west side.
5. Whether a north path and an east path exist as built, or should be moved/removed.
6. Field orientation (direction of play) and size relative to the CDS length.

## How to edit the map in Godot

- Each area is a separate node: `Objects/SportsCourts/<Court>`, `Objects/Buildings/MainGateLandmark`, `Objects/Buildings/CDSExterior/<Section>`, `Objects/Boundary/*` (`SouthWall` road-wall run, `PrototypeEdgeWest/North/East`), `Objects/Vegetation/<Group>/*`. Shared ground is under `Ground` (see below).
- `cds_veranda` ground surfaces are still `Polygon2D`s: select one and drag its vertices.

### Main Gate ground (`main_gate_exterior`, Milestone G Batch 1A)

The shared ground uses the production `campus_ground` tiles. `Ground` (z −10, not Y-sorted) draws its children in tree order:

| Node | What it is | How to edit |
|---|---|---|
| `Ground/Tiles` | `TileMapLayer` on `assets/tilesets/campus_ground.tres` (grass 0, worn grass 1, walkway 2, asphalt 3), at the world origin so cells sit on world multiples of 64 px. Cells x −38..46, y −29..30. Every 64 px cell that lies fully inside a surface uses that surface's tile; everything else is grass; four worn-grass cells at the west palm path's ends. | TileMap panel: select `Ground/Tiles`, pick a source, paint. |
| `Ground/EdgeStrips/<Surface>/<Top\|Bottom\|West\|East\|Full>` | `Polygon2D` strips textured with the same production PNG (`texture_repeat` Enabled, no UV, polygon at the origin, so the texture continues the tiles' pattern without a seam). They fill the parts of each surface that don't cover a whole cell, so every surface keeps its exact original edges below. 17 strips. | Drag vertices. Keep the node at the origin with no `uv` / `texture_offset`, or the pavers stop lining up with the tiles. |
| `Ground/Markings` | `Field/Outline`, `HalfwayLine`, `CentreCircle` and `Road/LaneMarking` (`Line2D`, placeholders). | Drag points; they are drawn over the tiles and strips. |

Exact surface rectangles (world px), unchanged from the blockout: ground fill x −2400..3000, y −1800..1950; field x −1200..1200, y −800..700; west palm path x −1450..−1330, y −1080..1400; north path x −1450..1360, y −1080..−960; east path x 1260..1360, y −1080..800; south path x −1450..1360, y 720..800; sidewalk x −2400..3000, y 1400..1460; main road x −2400..3000, y 1460..1800. Field and grass are both grass tiles; the field is defined by its markings.

To move or resize a path or road: repaint the full cells it now covers in `Ground/Tiles` (and repaint grass where it left), then move the strip vertices to the new edges; strips are only needed where an edge isn't on a multiple of 64. `scenes/tests/environment_previews/MainGateGroundCheck.tscn` checks the ground against the rectangles above (constants in `main_gate_ground_check.gd`); update those constants together with an intentional layout change.

Landmark ground under each landmark is at z −9. The gate's `GatePlaza` and `PassageFloor` (Batch 3) and the CDS `Forecourt` (Batch 4) use the walkway texture; the court aprons/surfaces are still flat-coloured blockout.
- **Moving a landmark: move only its parent node.** Every layer it owns is inside it (see `Docs/CONVENTIONS.md` §12):

| Landmark (move this node) | Contains |
|---|---|
| `Objects/Buildings/MainGateLandmark` | `Tower`, `GateLeaves`, `Pavilion` (production props with contact shadows), `GatePlaza` and `PassageFloor` (z −9), `ShadowOccluderWest` / `East`, `SpawnMainGateEntry`. No `Overhead`: the rendered roofs are render layers inside the props (tower `Roof` at z 10, pavilion `RoomRoof` / `Canopy`) with fade areas (see "Main Gate landmark" below) |
| `Objects/Buildings/CDSExterior` | Sections `Canteen`, `TableTennis`, `IndoorBasketball`, each with its production prop, `Collision`, `ShadowOccluder` and contact shadows (see "CDS exterior" below). `TableTennis` also holds the entrance: `Forecourt` (z −9), `DoorCdsMainEntry`, `SpawnOutsideCdsEntrance`, `LampForecourt`; `Canteen` holds the flagpoles. No `Overhead`: the canteen's north roof slice fades instead. |
| `Objects/SportsCourts/FutsalCourt`, `TennisCourt` | `Apron` and `Surface` (z −9) with line markings, fence blocks |
| `cds_veranda`: `Objects/Arcade` | Columns 01–10 and `Overhead/VerandaRoofEdge` (z 10) |

- Shared terrain that belongs to no landmark (field, palm/north/east/south paths, road, sidewalk) stays under the zone's `Ground` and is edited separately (tiles + edge strips, see above). Paths that lead to a moved landmark have to be adjusted by hand.
- Court fences, hedges and the prototype edges are `BlockoutBlock` instances (the gate and the CDS are production props since Batches 3 and 4): change `Footprint Size`, `Wall Height`, colours and `Arch Count` in the Inspector; collision and shadows follow automatically. The south wall is not a `BlockoutBlock` any more (see below).
- South boundary wall (`main_gate_exterior`, Milestone G Batch 2): `Objects/Boundary/SouthWall` is a Y-sorted `Node2D` at (−1250, 1400) holding:

  | Child | What it is |
  |---|---|
  | `Wall01..Wall37` | `scenes/props/architecture/RedBrickWall3m.tscn` instances at local (48 + 96k, 0), with origin at the footprint centre |
  | `Pier00..Pier37` | `RedBrickVerandaPier.tscn` instances at local (96k, 0), listed after the walls so they draw on top |
  | `ContactShadow` | One child under each wall and pier instance |
  | `RunCollision` | `StaticBody2D` on layer 1. `Shape` is 3552 × 10.07891 at local (1776, 0). `EastEdgeJoin` is a temporary 30 × 20 shape under `PrototypeEdgeEast` |
  | `ShadowOccluder` | `LightOccluder2D` on light mask 1, same rectangle as `Shape` |

  - **Move the run:** move `SouthWall`. If you move it, check `EastEdgeJoin` still closes the corner at the east edge.
  - **Extend east:** duplicate the last wall and the last pier (Ctrl+D, so the shadow comes along) and add 96 to their x. Then add 96 to `Shape`'s width, add 48 to its x, and move the `ShadowOccluder` polygon's east points 96 px east. Shortening works the same way in reverse.
  - Never scale, cut or overlap a module.
  - `MainGateBoundaryCheck.tscn` and `MainGateGroundCheck.tscn` expect the current 37 + 38 layout. After an intentional change, update the boundary check's constants. Then dump a new ground baseline deliberately and verify the difference (see `Docs/STATUS.md`, Batch 2).
- Main Gate landmark (`main_gate_exterior`, Milestone G Batch 3): `Objects/Buildings/MainGateLandmark` at (−1390, 1400) (gate axis on the wall line) holds:

  | Child | Local position | What it is |
  |---|---|---|
  | `GatePlaza` | — | Walkway-textured `Polygon2D` (z −9) x −170..140, y −280..−160; `texture_offset` (18, 56) keeps it on the world tile grid |
  | `PassageFloor` | — | Same texture, x ±76.16, y −160..0 (seen through the arch) |
  | `GateLeaves` | (0, −5) | `scenes/props/landmarks/MainGateLeaves.tscn`; collision 152.32 × 10 at y −10..0 = the gate stop (player feet y 1390) |
  | `Tower` | (0, 7) | `MainGateTower.tscn`; origin on the outer white ring's front plane, so the brick face is on the wall line; pier collisions x −172..−76.16 and 76.16..140, y −131.6..+7; passage open. Children `ContactShadowWest` / `East` |
  | `Pavilion` | (−172, 58) | `MainGatePavilion.tscn`; origin on the column line at the tower's west face; room collision x −360..−172, y −140..0. Children `ContactShadowRoom` / `Porch` |
  | `ShadowOccluderWest` / `East` | — | Light mask 1 occluders over the west pier + room and the east pier |
  | `SpawnMainGateEntry` | (0, −440) | Arrival spawn `main_gate_entry`, unchanged |

  - **Move the gate:** move `MainGateLandmark`. Its east face at local +140 must stay on `SouthWall`'s origin (`Pier00` sits half behind the tower), and the room's north face (local y −140) must meet `PrototypeEdgeWest`'s south end (y 1260) or the corner opens.
  - **Change the art:** edit `assets/source/blender/generators/main_gate_*.py` (or the config's `generator_params`) and run `python assets/source/blender/build_asset.py main_gate_tower main_gate_leaves main_gate_pavilion`. The scenes are rewritten in place, so the instances keep working. If a footprint changes, move the instance and update the occluder polygons, `PassageFloor` and the expected rectangles in `main_gate_landmark_check.gd`.
  - **Change the sign text:** edit `assets/source/blender/tools/main_gate_sign_texture.ps1` and run it with `powershell -NoProfile -ExecutionPolicy Bypass -File assets/source/blender/tools/main_gate_sign_texture.ps1`, then rebuild `main_gate_pavilion`.
  - Y-sort: the leaves (y 1395) draw before the tower (y 1407); the tower draws over `Pier00` (y 1400). Keep those orders if you move a child.
  - Overhead layers (Batch 3A): the tower's `Roof` is a separate sprite at z 10, so it always draws over the pavilion and the player. The pavilion root is Y-sorted: its `Room` and `RoomRoof` sort at local y −58 inside the prop (the room's north face, world y 1400), the columns and `Canopy` at the prop origin. `RoofFade`, `RoomRoofFade` and `CanopyFade` (`OverheadVisibility` areas, no collision) fade only their layer while the player stands on the ground it hides. They are generated from the configs' `layers[].fade.rects_m`; change them there and rebuild, never by hand.
  - The porch (south of the room, under the canopy) is south of the leaves and the wall, so normal play cannot reach it; the pavilion windows show only when `CanopyFade` fades the canopy.
  - Directly behind the tower piers (feet y ≈ 1200..1268) the solid brick facade still covers the player. That is expected; the facade is never faded.
  - `MainGateLandmarkCheck.tscn` (33 checks), `MainGateOverheadCheck.tscn` (14 checks: fade per position, smoothness, no flicker, no blocking, in the real zone with the real player) and `MainGateGroundCheck.tscn` (baseline `main_gate_ground_baseline_batch4.json`) expect this layout. After an intentional change, update the landmark and overhead checks' constants, dump a new ground baseline deliberately and verify the difference (see `Docs/STATUS.md`, Batch 3 and 3A).
- CDS exterior (`main_gate_exterior`, Milestone G Batch 4): `Objects/Buildings/CDSExterior` at (1775, 0) (centre of the main mass's x range; y 0 = the table-tennis south face) holds three Y-sorted section nodes. Each section's origin is the centre of its south edge (main mass x −225..225, veranda frontage x −295..−225):

  | Section (position) | Children |
  |---|---|
  | `Canteen` (0, −450), 550 deep | `CdsCanteen` (`scenes/props/landmarks/CdsCanteen.tscn`: `Sprite`, `Slice2` sorted at local y −208.56, `NorthRoof` at −407.87 with `NorthRoofFade`), `Collision` (`Mass` 450 × 550, `Veranda` 70 × 550), `ShadowOccluder`, `ContactShadowWest` / `East`, `FlagPoleBangladesh` (−349, −32), `FlagPoleWhite` (−349, −66) |
  | `TableTennis` (0, 0), 450 deep | `CdsTableTennis` (`Sprite`, `Slice2` at −283.33), `Collision` (450 × 450, 70 × 450), `ShadowOccluder`, `Forecourt` (walkway texture, `texture_offset` (47, 0)), `ContactShadowWest` / `East`, `DoorCdsMainEntry` (−323, −200), `SpawnOutsideCdsEntrance` (−395, −200), `LampForecourt` (−419, −326) |
  | `IndoorBasketball` (0, 700), 700 deep | `CdsIndoorBasketball` (`Sprite`, `Slice2` at −237.45, `Slice3` at −462.55), `Collision` (450 × 700, 70 × 700), `ShadowOccluder`, `ContactShadowWest` / `East` / `South` |

  - **Move the CDS:** move `CDSExterior` only. The three props share one texel grid and their seams are matched, so keep the sections at (0, −450), (0, 0) and (0, 700). After a move set the `Forecourt`'s `texture_offset` to its new global position mod 64.
  - **Change the art:** edit `assets/source/blender/generators/cds_common.py` / `cds_section.py` or the configs' `generator_params` (bay counts, slice bounds, dish positions) and run `python assets/source/blender/build_asset.py cds_indoor_basketball cds_canteen cds_table_tennis` in this order (the table tennis's cross-section seam check reads the canteen's record). The prop scenes are rewritten in place. A footprint or section-depth change needs the `Collision` shapes, occluder polygons and the expected values in `main_gate_cds_check.gd` updated too.
  - Slices: each long section is cut north–south into slice sprites that sort at their own south edge, so the player walks between them in the right order. Only the canteen's north slice fades (behind the canteen, where the roof would hide the player); change its rectangle in `cds_canteen.json` (`layers[].fade.rects_m`) and rebuild, never by hand.
  - The props have no collision of their own. `Collision` keeps the former blockout rectangles: the west facade stops the player at x 1465.6.
  - `MainGateCdsCheck.tscn` (22 checks, including the stop lines measured on the pre-edit zone) and `MainGateGroundCheck.tscn` (baseline `main_gate_ground_baseline_batch4.json`) expect this layout. After an intentional change, update the CDS check's constants, dump a new ground baseline deliberately and verify the difference (see `Docs/STATUS.md`, Batch 4).
- Trees and palms (Milestone G Batch 1B) are instances of the production `scenes/props/vegetation/BroadleafTree.tscn` / `CoconutPalm.tscn` (origin at the trunk base, trunk footprint collision), each with a `ContactShadow` child (`scenes/props/common/ContactShadow.tscn`; tree scale (1.1, 0.4), palm (0.6, 0.24)). Duplicate (Ctrl+D) the instance so the shadow comes with it, and move it. Tree rows (`CdsTrees`, `GateTrees`, …) are landscape groups, not part of the buildings they stand near. `scenes/tests/environment_previews/MainGateVegetationCheck.tscn` (Batch 1B acceptance) and `MainGateGroundCheck.tscn` expect exactly the 42 original names and positions, so an intentional vegetation change makes both fail until a new baseline is dumped and verified (see `Docs/STATUS.md`, Batch 1B).
- Doors and spawn markers: move them, keep their IDs (node names / `spawn_id`). Keep each arrival spawn more than 56 px from the door it lands next to. Moving the gate or CDS moves their door/spawn too; saves are unaffected (they store zone ID + position, not node paths).
- Placeholders: every blockout-only visual is in node group `blockout_placeholder` (Node panel > Groups) and its `editor_description` (hover the node in the Scene dock) starts with "BLOCKOUT PLACEHOLDER". The group covers all descendants. These are replaced by production art later; the landmark parents, collision footprints, doors and spawns are the structure that stays.

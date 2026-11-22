"""Writes the whole-campus exterior zones (Docs/CAMPUS_BUILD.md). Regenerate after changing this script:

    python tools/zones/campus_zones.py

All exterior zones share the campus frame (game px of main_gate_exterior: +x east, +y south). Writes the zone
scenes, their profiles and validator manifests, registers them, and adds the edge transitions + arrival spawns to
main_gate_exterior (idempotent: its block is replaced, never duplicated).
"""

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene_lib import (ASPHALT, C, EDGE, GRASS, ROOT, SPAWN, V, WALKWAY, WATER, ZoneScene, campus, register_zones,  # noqa: E402
                       veg, write_profile)

MANIFESTS = ROOT / "scenes/tests/zone_validation/manifests"
PALM = veg("CoconutPalm")
TREE = veg("BroadleafTree")


def manifest(zone_id, notes, bounds):
    (MANIFESTS / f"{zone_id}.json").write_text(json.dumps(
        {"zone_id": zone_id, "notes": notes, "playable_bounds": bounds, "walks": []}, indent="\t") + "\n",
        encoding="utf-8")


# --- Central Plaza --------------------------------------------------------------------------------------------

LAKE = (-1420, -3500, 1720, -1500)      # outer bank x0, y0, x1, y1
ISLAND = (-1100, -3294, 1400, -1706)
SOUTH_BRIDGE_X = -500
NORTH_ROAD = (185, 370)
EAST_BRIDGE_Y = -2500


def central_plaza():
    z = ZoneScene("CentralPlaza", "central_plaza")
    # Ground: grass everywhere, the paved island deck, a paved promenade on the south bank, water in the ring.
    z.ground_rect("Grass", -2420, -4080, 2780, -950, texture=GRASS)
    z.ground_rect("Promenade", -1420, -1500, 1720, -1390, texture=WALKWAY)
    z.ground_rect("NorthBank", NORTH_ROAD[0] - 40, -3800, NORTH_ROAD[1] + 40, -3500, texture=WALKWAY)
    z.ground_rect("EastBank", 1720, EAST_BRIDGE_Y - 70, 2300, EAST_BRIDGE_Y + 70, texture=WALKWAY)
    lx0, ly0, lx1, ly1 = LAKE
    ix0, iy0, ix1, iy1 = ISLAND
    for name, r in (("WaterSouth", (lx0, iy1, lx1, ly1)), ("WaterNorth", (lx0, ly0, lx1, iy0)),
                    ("WaterWest", (lx0, iy0, ix0, iy1)), ("WaterEast", (ix1, iy0, lx1, iy1))):
        z.ground_rect(name, *r, shader=WATER)
    # Brick embankment bands (the lake edges) and the island deck.
    for name, r in (("BankS", (lx0 - 16, ly1, lx1 + 16, ly1 + 16)), ("BankN", (lx0 - 16, ly0 - 16, lx1 + 16, ly0)),
                    ("BankW", (lx0 - 16, ly0, lx0, ly1)), ("BankE", (lx1, ly0, lx1 + 16, ly1))):
        z.ground_rect(name, *r, color=(0.5, 0.25, 0.18))
    z.ground_rect("Island", ix0 - 16, iy0 - 16, ix1 + 16, iy1 + 16, color=(0.5, 0.25, 0.18))
    z.ground_rect("Deck", ix0, iy0, ix1, iy1, texture=WALKWAY)
    # The white grid on the plaza paving (photo 01), every 6 m.
    gx0, gx1, gy0, gy1 = -260, ix1 - 40, iy0 + 360, iy1 - 60
    x = gx0
    k = 0
    while x <= gx1:
        z.line(f"GridV{k}", [(x, gy0), (x, gy1)], 2.5)
        x += 192
        k += 1
    y = gy0
    k = 0
    while y <= gy1:
        z.line(f"GridH{k}", [(gx0, y), (gx1, y)], 2.5)
        y += 123
        k += 1
    # Bridges (deck over water): south (to the bank), north (the road to the academic area), east (to the halls side).
    for name, xc in (("BridgeSouth", SOUTH_BRIDGE_X), ("BridgeNorthRoad", sum(NORTH_ROAD) / 2)):
        z.ground_rect(name + "Deck", xc - 64, (ly1 if name == "BridgeSouth" else ly0) - 0,
                      xc + 64, (iy1 if name == "BridgeSouth" else iy0), texture=WALKWAY)
    z.ground_rect("BridgeEastDeck", ix1, EAST_BRIDGE_Y - 64, lx1, EAST_BRIDGE_Y + 64, texture=WALKWAY)
    z.place("BridgeSouth", campus("LakeBridgeNs"), SOUTH_BRIDGE_X, (ly1 + iy1) / 2)
    z.place("BridgeNorthRoad", campus("LakeBridgeNs"), sum(NORTH_ROAD) / 2, (ly0 + iy0) / 2)
    z.place("BridgeEast", campus("LakeBridge"), (ix1 + lx1) / 2, EAST_BRIDGE_Y)
    # Buildings.
    z.place("Mosque", campus("PlazaMosque"), -650, -2050)
    z.place("Minaret", campus("PlazaMinaret"), -230, -1930)
    z.place("Auditorium", campus("PlazaAuditorium"), 760, -2100)
    z.place("Admin", campus("PlazaAdmin"), -455, -2950)
    z.place("CentralCafe", campus("PlazaCentralCafe"), 850, -2950)
    z.place("FivePillars", campus("FivePillars"), -1190, -1600)
    # Plaza lamps.
    for i, (lx, ly) in enumerate(((-160, -2600), (220, -2600), (600, -2600), (1000, -2600), (-160, -2300),
                                  (1150, -2300), (-120, -1800), (300, -1780), (1250, -1780))):
        z.place(f"Lamp{i + 1}", campus("PlazaLamp"), lx, ly, parent="Objects/Props", shadow=(0.4, 0.2))
        z.lamp_light(f"LampLight{i + 1}", lx, ly, color=(1.0, 0.92, 0.8), energy=0.8, scale=2.2,
                     needs_power=True, mode=1 if i == 3 else 0)
    # Palms along the south bank promenade and the outer banks; broadleaf trees at the corners.
    x = lx0 + 60
    k = 0
    while x < lx1 - 40:
        if abs(x - SOUTH_BRIDGE_X) > 120:
            z.place(f"PalmS{k}", PALM, x, -1420, parent="Objects/Vegetation", shadow=(0.6, 0.3))
        x += 256
        k += 1
    for i, (tx, ty) in enumerate(((-1700, -3600), (2050, -3650), (-1750, -1700), (2050, -1650), (-1700, -2600),
                                  (2100, -3100))):
        z.place(f"Tree{i + 1}", TREE, tx, ty, parent="Objects/Vegetation", shadow=(1.2, 0.6))
    # Water is impassable: collision over the ring with gaps at the three bridges (bridge railings collide too).
    sb0, sb1 = SOUTH_BRIDGE_X - 56, SOUTH_BRIDGE_X + 56
    nr0, nr1 = NORTH_ROAD[0] + 36, NORTH_ROAD[1] - 36
    z.wall("WaterSouthW", lx0, iy1, sb0, ly1)
    z.wall("WaterSouthE", sb1, iy1, lx1, ly1)
    z.wall("WaterNorthW", lx0, ly0, nr0, iy0)
    z.wall("WaterNorthE", nr1, ly0, lx1, iy0)
    z.wall("WaterWest", lx0, iy0, ix0, iy1)
    z.wall("WaterEastN", ix1, iy0, lx1, EAST_BRIDGE_Y - 56)
    z.wall("WaterEastS", ix1, EAST_BRIDGE_Y + 56, lx1, iy1)
    # Zone bounds (the campus edge west and north; unmapped beyond, Docs/CAMPUS_BUILD.md section 1).
    z.wall("BoundSouth", -1950, -1255, 2300, -1215)
    z.wall("BoundWest", -1950, -3800, -1880, -950)
    z.wall("BoundEast", 2240, -3800, 2300, -950)
    z.wall("BoundNorthW", -1950, -3820, NORTH_ROAD[0] - 40, -3760)
    z.wall("BoundNorthE", NORTH_ROAD[1] + 40, -3820, 2300, -3760)
    # Edges: back to the field (three segments), north to the academic area, east to the halls.
    for i, (x0, x1) in enumerate(((-1880, -300), (-300, 700), (700, 2240))):
        z.edge(f"EdgeToField{i + 1}", (x0 + x1) / 2, -1300, x1 - x0, 50, "main_gate_exterior", f"field_from_plaza_{i + 1}",
               "The field")
        z.spawn(f"plaza_from_field_{i + 1}", (x0 + x1) / 2 if i != 0 else SOUTH_BRIDGE_X, -1440)
    z.edge("EdgeToAcademic", sum(NORTH_ROAD) / 2, -3740, NORTH_ROAD[1] - NORTH_ROAD[0] + 80, 40, "academic_exterior",
           "academic_from_plaza", "Academic buildings")
    z.spawn("plaza_from_academic", sum(NORTH_ROAD) / 2, -3640)
    z.edge("EdgeToHalls", 2200, EAST_BRIDGE_Y, 40, 140, "halls_exterior", "halls_from_plaza", "The halls")
    z.spawn("plaza_from_halls", 2080, EAST_BRIDGE_Y)
    z.spawn("plaza_center", 400, -2450)
    z.write()
    write_profile("central_plaza", zoom=2.0, limits=(-2400, -4060, 5160, 3110), surface="paving",
                  ambience="night_field", vol=-5.0, night=(0.19, 0.21, 0.31))
    manifest("central_plaza", "Central Plaza: lake ring around the island plaza (Mosque, minaret, Auditorium, Admin, "
             "Central Cafe), 5 Pillars, three bridges. Campus frame (Docs/CAMPUS_BUILD.md).",
             [-1880, -3760, 4120, 2510])


# --- Halls ------------------------------------------------------------------------------------------------------
# South Hall (x 3400) and North Hall (x 4935) run north-south with the palm courtyard between them, UB Hall closes
# the south end, the halls' gate and arcade wall close the north end (photos 04, 06, 07, 08, 11; decision D25).
SEG = 617.3            # one 30 m hall segment in game px of depth
HALL_SOUTH_FACE = 615  # y of the halls' south faces (a passage runs between them and UB Hall)


def halls_exterior():
    z = ZoneScene("HallsExterior", "halls_exterior")
    z.ground_rect("Grass", 2280, -3260, 6120, 1570, texture=GRASS)
    z.ground_rect("WestRoad", 2860, -2950, 2990, 1300, texture=WALKWAY)
    z.ground_rect("CourtPath", 4105, -2950, 4235, 660, texture=WALKWAY)
    z.ground_rect("Passage", 2860, 640, 5600, 720, texture=WALKWAY)
    for name, xc, front, wing in (("SouthHall", 3400, "SouthHallFront", "SouthHallWing"),
                                  ("NorthHall", 4935, "NorthHallFront", "NorthHallWing")):
        for k in range(4):
            yc = HALL_SOUTH_FACE - SEG / 2 - k * SEG
            z.place(f"{name}{k + 1}", campus(front if k == 0 else wing), xc, yc)
    z.place("UbHall", campus("UbHall"), 4170, 900)
    z.place("HallsGate", campus("HallsGateWall"), 4170, HALL_SOUTH_FACE - 4 * SEG - 110)
    # Courtyard palms in two rows beside the path, trees on the lawns, street lamps.
    k = 0
    for y in range(-1800, 560, 210):
        for x in (3990, 4350):
            z.place(f"Palm{k}", PALM, x, y, parent="Objects/Vegetation", shadow=(0.6, 0.3))
            k += 1
    for i, (tx, ty) in enumerate(((3920, -1300), (4420, -600), (3930, 200), (2700, -2600), (5400, -2500),
                                  (2650, 1200), (5450, 1250))):
        z.place(f"Tree{i + 1}", TREE, tx, ty, parent="Objects/Vegetation", shadow=(1.2, 0.6))
    for i, (lx, ly) in enumerate(((2920, -2400), (2920, -1400), (2920, -400), (2920, 600), (4170, -2400),
                                  (4070, -900), (4270, 300))):
        z.place(f"StreetLamp{i + 1}", campus("StreetLampTall"), lx, ly, parent="Objects/Props", shadow=(0.3, 0.15))
        z.lamp_light(f"StreetLight{i + 1}", lx + 50, ly, energy=0.9, scale=2.6, needs_power=i not in (0, 4),
                     mode=1 if i == 2 else 0)
    z.wall("BoundWestEdge", 2760, -3200, 2800, 1560)
    z.wall("BoundEast", 5600, -3200, 5680, 1560)
    z.wall("BoundSouth", 2380, 1300, 6100, 1360)
    z.wall("BoundNorthW", 2380, -3010, 3900, -2950)
    z.wall("BoundNorthE", 4440, -3010, 6100, -2950)
    z.edge("EdgeToField", 2830, 75, 50, 2350, "main_gate_exterior", "field_from_halls", "The field")
    z.spawn("halls_from_field", 2960, -150)
    z.edge("EdgeToPlaza", 2830, -2000, 50, 1700, "central_plaza", "plaza_from_halls", "Central Plaza")
    z.spawn("halls_from_plaza", 2960, -2500)
    z.edge("EdgeToAcademic", 4170, -2925, 540, 40, "academic_exterior", "academic_from_halls", "Academic buildings")
    z.spawn("halls_from_academic", 4170, -2780)
    z.write()
    write_profile("halls_exterior", zoom=2.0, limits=(2300, -3240, 3800, 4800), surface="grass",
                  ambience="night_field", vol=-5.0, night=(0.18, 0.2, 0.3))
    manifest("halls_exterior", "Halls: South Hall and North Hall (four 30 m segments each), the palm courtyard, UB "
             "Hall, the halls' gate. Campus frame.", [2800, -2950, 2800, 4250])


# --- Academic area ------------------------------------------------------------------------------------------------

def academic_exterior():
    z = ZoneScene("AcademicExterior", "academic_exterior")
    z.ground_rect("Grass", -2160, -5940, 5520, -2640, texture=GRASS)
    z.ground_rect("MainRoad", -1600, -4000, 5000, -3880, texture=ASPHALT)
    z.ground_rect("PlazaRoad", 185, -3880, 370, -3500, texture=WALKWAY)
    z.ground_rect("HallsRoad", 4105, -3880, 4235, -2950, texture=WALKWAY)
    z.ground_rect("GarageApron", 2300, -3860, 3150, -3300, texture=WALKWAY)
    z.place("Academic1", campus("Academic1"), 1700, -4320)
    z.place("Academic2", campus("Academic2"), 3500, -4620)
    z.place("Academic3", campus("Academic3"), 500, -5180)
    z.place("MeWorkshopA", campus("MeWorkshop"), -850, -4320)
    z.place("MeWorkshopB", campus("MeWorkshop"), -850, -4800)
    z.place("GarageCanopyA", campus("GarageCanopy"), 2720, -3720)
    z.place("GarageCanopyB", campus("GarageCanopy"), 2720, -3430)
    for i, (tx, ty) in enumerate(((-1500, -5500), (-1600, -3700), (2600, -5300), (4600, -5200), (4700, -4000),
                                  (1200, -3650), (-200, -3650), (3300, -3200))):
        z.place(f"Tree{i + 1}", TREE, tx, ty, parent="Objects/Vegetation", shadow=(1.2, 0.6))
    for i, (lx, ly) in enumerate(((-1000, -3830), (300, -3830), (1600, -3830), (2900, -3830), (4200, -3830))):
        z.place(f"StreetLamp{i + 1}", campus("StreetLampTall"), lx, ly, parent="Objects/Props", shadow=(0.3, 0.15))
        z.lamp_light(f"StreetLight{i + 1}", lx + 50, ly, energy=0.9, scale=2.6, needs_power=i % 2 == 0,
                     mode=1 if i == 3 else 0)
    z.wall("BoundWest", -1700, -5900, -1640, -2680)
    z.wall("BoundNorth", -2000, -5700, 6100, -5640)
    z.wall("BoundEast", 5000, -5900, 5060, -2680)
    z.wall("BoundSouthW", -2000, -3780, 120, -3720)
    z.wall("BoundSouthM", 435, -3780, 2300, -3720)
    z.wall("BoundSouthE", 3150, -3100, 4040, -3040)
    z.wall("BoundSouthE2", 4300, -3100, 6100, -3040)
    z.wall("BoundGarageW", 2240, -3780, 2300, -3040)
    z.wall("BoundPlazaGap", 100, -3670, 460, -3640)
    z.wall("BoundHallsGap", 4020, -2985, 4320, -2955)
    z.edge("EdgeToPlaza", 277, -3700, 260, 40, "central_plaza", "plaza_from_academic", "Central Plaza")
    z.spawn("academic_from_plaza", 277, -3840)
    z.edge("EdgeToHalls", 4170, -3010, 260, 40, "halls_exterior", "halls_from_academic", "The halls")
    z.spawn("academic_from_halls", 4170, -3150)
    z.write()
    write_profile("academic_exterior", zoom=2.0, limits=(-2140, -5920, 7640, 3260), surface="grass",
                  ambience="night_field", vol=-5.0, night=(0.17, 0.19, 0.29))
    manifest("academic_exterior", "Academic area: Academic 1, 2, 3, ME workshops A/B, the garage, the main road. "
             "Campus frame.", [-1640, -5640, 6640, 2690])


def main_gate_edges():
    """Edges from the field north to the plaza (three segments) and their arrival spawns, as one marked block."""
    p = ROOT / "scenes/world/MainGateExterior.tscn"
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"\n\[node name=\"CampusEdges\".*?(?=\n\[node name=\"(?!Edge|Spawn)|\n\[connection|\Z)", "", s,
               flags=re.S)
    if 'id="campus_edge"' not in s:
        lines = s.split("\n")
        last = max(i for i, l in enumerate(lines) if l.startswith("[ext_resource"))
        lines.insert(last + 1, f'[ext_resource type="PackedScene" path="{EDGE}" id="campus_edge"]')
        s = "\n".join(lines)
    block = ['[node name="CampusEdges" type="Node2D" parent="Objects"]\ny_sort_enabled = true\n'
             'editor_description = "Generated by tools/zones/campus_zones.py: the walk-off transitions to the rest of '
             'the campus (decision D28) and their arrival spawns."\n']
    for i, (x0, x1) in enumerate(((-1880, -300), (-300, 700), (700, 2240))):
        block.append(f'[node name="EdgeToPlaza{i + 1}" parent="Objects/CampusEdges" instance=ExtResource("campus_edge")]\n'
                     f'position = {V((x0 + x1) / 2, -1330)}\ndestination_zone_id = "central_plaza"\n'
                     f'destination_spawn_id = "plaza_from_field_{i + 1}"\nsize = {V(x1 - x0, 50)}\n'
                     f'place_name = "Central Plaza"\n')
        block.append(f'[node name="SpawnFieldFromPlaza{i + 1}" parent="Objects/CampusEdges" instance=ExtResource("2_spawn")]\n'
                     f'position = {V((x0 + x1) / 2 if i else -500, -1200)}\nspawn_id = "field_from_plaza_{i + 1}"\n')
    block.append(f'[node name="EdgeToHalls" parent="Objects/CampusEdges" instance=ExtResource("campus_edge")]\n'
                 f'position = {V(2215, -150)}\ndestination_zone_id = "halls_exterior"\n'
                 f'destination_spawn_id = "halls_from_field"\nsize = {V(50, 1500)}\nplace_name = "The halls"\n')
    block.append(f'[node name="SpawnFieldFromHalls" parent="Objects/CampusEdges" instance=ExtResource("2_spawn")]\n'
                 f'position = {V(2110, -150)}\nspawn_id = "field_from_halls"\n')
    text = "\n".join(block)
    i = s.find("\n[connection")
    s = (s.rstrip() + "\n\n" + text) if i == -1 else (s[:i] + "\n\n" + text + s[i:])
    p.write_text(s, encoding="utf-8")
    print("patched main_gate_exterior: CampusEdges")


if __name__ == "__main__":
    central_plaza()
    halls_exterior()
    academic_exterior()
    main_gate_edges()
    register_zones({"central_plaza": "res://scenes/world/CentralPlaza.tscn",
                    "halls_exterior": "res://scenes/world/HallsExterior.tscn",
                    "academic_exterior": "res://scenes/world/AcademicExterior.tscn"})

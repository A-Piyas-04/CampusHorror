"""Writes the whole-campus interior zones (room shells from author_rooms.campus_rooms; Docs/CAMPUS_BUILD.md S9).

    python tools/zones/campus_interiors.py

Room frame: origin at the inner face of the south wall, x east, y north, metres (P() converts). Each zone: the room
at the origin, furniture, doors (back outside / between rooms), spawns, mood lights, power lights, organism glow.
Exterior doors into these rooms are written by tools/zones/campus_world.py from the layout's site entrances.
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene_lib import DOOR, P, PV2, ROOT, S, SPAWN, STUDENT, V, Scene, register_zones, sleepwalker_props, student_props, technician_props, write_profile  # noqa: E402

DEPTH = 20.576
SHADOW = "res://scenes/props/common/ContactShadow.tscn"
GLOW = "res://scripts/world/glow_mark.gd"
LAMP = "res://scripts/lighting/lamp_light.gd"
LIGHT_TEX = "res://data/lighting/light_soft.tres"
READ = "res://scenes/components/Readable.tscn"
MANIFESTS = ROOT / "scenes/tests/zone_validation/manifests"
MOON = (0.55, 0.65, 1.0)
## Each building's lights are on its area's circuit (scripts/lighting/lamp_light.gd `power_flag`).
CIRCUITS = {"academic": "power_academic", "admin": "power_plaza", "mosque": "power_plaza", "auditorium": "power_plaza",
            "av": "power_plaza", "central": "power_plaza", "hall": "power_halls", "me": "power_academic",
            "facility": "power_facility"}


def F(name):
    return f"res://scenes/props/{name if '/' in name else 'furniture/' + name}.tscn"


class Room:
    def __init__(self, zone_id, scene_name, room_scene, W, D, H, zoom):
        self.zone_id, self.W, self.D, self.H, self.zoom = zone_id, W, D, H, zoom
        self.s = Scene()
        self.s.node(scene_name, "Node2D", None, props={
            "y_sort_enabled": "true", "script": self.s.res("res://scripts/world/zone.gd"), "zone_id": S(zone_id),
            "profile": self.s.res(f"res://data/zones/profiles/{zone_id}.tres", "Resource")})
        self.s.node("Objects", "Node2D", props={"y_sort_enabled": "true"})
        for g in ("Props", "Story", "Lights", "Doors", "SpawnMarkers", "Glow"):
            self.s.node(g, "Node2D", "Objects", props={"y_sort_enabled": "true"})
        self.s.node("Room", None, "Objects", instance=f"res://scenes/props/interiors/{room_scene}.tscn")
        self.scene_name = scene_name

    def prop(self, name, scene, xm, ym, shadow=None):
        path = self.s.node(name, None, "Objects/Props", instance=F(scene), props={"position": P(xm, ym)})
        if shadow:
            self.s.node("ContactShadow", None, path, instance=SHADOW, props={"scale": V(*shadow)})

    def door(self, name, xm, ym, dest_zone, dest_spawn, verb, place, **kw):
        props = {"position": P(xm, ym), "destination_zone_id": S(dest_zone), "destination_spawn_id": S(dest_spawn),
                 "verb": S(verb), "place_name": S(place), "show_placeholder": "false"}
        for k, v in kw.items():
            props[k] = S(v)
        self.s.node(name, None, "Objects/Doors", instance=DOOR, props=props)

    def spawn(self, spawn_id, xm, ym):
        self.s.node("Spawn_" + spawn_id, None, "Objects/SpawnMarkers", instance=SPAWN,
                    props={"position": P(xm, ym), "spawn_id": S(spawn_id)})

    def light(self, name, xm, ym, color, energy, scale, *, needs_power=False, gameplay=True, mode=0):
        props = {
            "position": P(xm, ym), "color": f"Color({color[0]}, {color[1]}, {color[2]}, 1)", "energy": str(energy),
            "range_item_cull_mask": "3", "texture": self.s.res(LIGHT_TEX, "Texture2D"), "texture_scale": str(scale),
            "script": self.s.res(LAMP), "mode": str(mode), "needs_power": "true" if needs_power else "false",
            "base_energy": str(energy), "gameplay": "true" if gameplay else "false"}
        if needs_power:
            props["power_flag"] = S(CIRCUITS[self.zone_id.split("_")[0]])
        self.s.node(name, "PointLight2D", "Objects/Lights", props=props)

    def glow(self, name, xm, ym, spots=(), trail_to=None, intensity=0.8):
        props = {"position": P(xm, ym), "script": self.s.res(GLOW), "color": "Color(0.45, 1, 0.82, 1)",
                 "intensity": str(intensity), "pulse_speed": "0.5"}
        if spots:
            props["spots"] = "PackedVector3Array(" + ", ".join(f"{a}, {b}, {c}" for a, b, c in spots) + ")"
        if trail_to:
            props["trail_to"] = V(*trail_to)
        self.s.node(name, "Node2D", "Objects/Glow", props=props)

    def note(self, name, xm, ym, note_id, title, body, light=True):
        self.s.node(name, None, "Objects/Story", instance=READ, props={
            "position": P(xm, ym), "note_id": S(note_id), "title": S(title), "body": S(body),
            "requires_light": "true" if light else "false"})

    def keypad(self, name, xm, ym, code, title, flag, message):
        self.s.node(name, None, "Objects/Story", instance="res://scenes/components/Keypad.tscn", props={
            "position": P(xm, ym), "code": S(code), "title": S(title), "solved_flag": S(flag),
            "solved_message": S(message), "not_ready_message": S("")})

    def pickup(self, name, xm, ym, pickup_id, item_name, visual, *, fuel=0.0, item_id="", verb="Pick up"):
        path = self.s.node(name, None, "Objects/Story", instance="res://scenes/components/Pickup.tscn", props={
            "position": P(xm, ym), "pickup_id": S(pickup_id), "verb": S(verb), "item_name": S(item_name),
            "show_placeholder": "false", "y_sort_enabled": "true", "fuel": str(fuel), "item_id": S(item_id)})
        self.s.node("Visual", None, path, instance=F(visual), props={"position": V(0, -18)})

    def hide(self, name, xm, ym, place):
        self.s.node(name, None, "Objects/Story", instance="res://scenes/components/HideSpot.tscn", props={
            "position": P(xm, ym), "verb": S("Hide"), "place_name": S(place), "exit_offset": V(0, 22)})

    def student(self, name, xm, ym, patrol_m):
        x, y = xm * 32.0, -ym * DEPTH
        pts = [(a * 32.0, -b * DEPTH) for a, b in patrol_m]
        self.s.node(name, None, "Objects/Story", instance=STUDENT, props=student_props(x, y, pts))

    def sleepwalker(self, name, xm, ym, patrol_m):
        x, y = xm * 32.0, -ym * DEPTH
        pts = [(a * 32.0, -b * DEPTH) for a, b in patrol_m]
        self.s.node(name, None, "Objects/Story", instance=STUDENT, props=sleepwalker_props(x, y, pts))

    def technician(self, name, xm, ym, patrol_m):
        x, y = xm * 32.0, -ym * DEPTH
        pts = [(a * 32.0, -b * DEPTH) for a, b in patrol_m]
        self.s.node(name, None, "Objects/Story", instance=STUDENT, props=technician_props(x, y, pts))

    def examine(self, name, xm, ym, obj, message, *, verb="Look", sets_flag="", requires_flag="", not_ready=""):
        props = {"position": P(xm, ym), "verb": S(verb), "object_name": S(obj), "message": S(message)}
        if sets_flag:
            props["sets_flag"] = S(sets_flag)
        if requires_flag:
            props["requires_flag"] = S(requires_flag)
            props["not_ready_message"] = S(not_ready)
        self.s.node(name, None, "Objects/Story", instance="res://scenes/components/Examine.tscn", props=props)

    def write(self):
        self.s.write(f"scenes/world/{self.scene_name}.tscn")
        W, D, H, t = self.W, self.D, self.H, 0.3
        vw, vh = 1920.0 / self.zoom, 1080.0 / self.zoom
        x0, x1 = -(W / 2 + t) * 32, (W / 2 + t) * 32
        y0, y1 = -(D + t) * DEPTH - H * 24.5, t * DEPTH
        # Playable: the floor, plus 8 px south (a south door's recess in the wall's thickness is standable).
        bx0, bx1, by0, by1 = -W * 16, W * 16, -D * DEPTH, 8.0

        def axis(lo, hi, blo, bhi, view):
            if hi - lo <= view:
                c = (lo + hi) / 2
                return c - view / 2, view
            return min(lo, blo - view / 2) - 4, max(hi, bhi + view / 2) - min(lo, blo - view / 2) + 8
        lx, lw = axis(x0, x1, bx0, bx1, vw)
        ly, lh = axis(y0, y1, by0, by1, vh)
        write_profile(self.zone_id, zoom=self.zoom, limits=(round(lx), round(ly), round(lw) + 1, round(lh) + 1),
                      surface="concrete", ambience="arcade_night", vol=-10.0, room=0.4, damp=0.5, wet=0.15,
                      night=(0.09, 0.095, 0.13), look=24.0)
        (MANIFESTS / f"{self.zone_id}.json").write_text(json.dumps({
            "zone_id": self.zone_id, "notes": f"Interior concept (Docs/CAMPUS_BUILD.md S9), {W:g} x {D:g} m.",
            "playable_bounds": [round(bx0), round(by0), round(bx1 - bx0), round(by1 - by0)], "walks": []},
            indent="\t") + "\n", encoding="utf-8")


def rooms():
    out = {}

    r = Room("academic_corridor", "AcademicCorridor", "AcademicCorridorRoom", 30, 5, 3.4, 2.4)
    r.door("DoorOut", -12.0, 0.35, "campus", "outside_academic_1", "Go out", "The road")
    r.spawn("corridor_from_outside", -12.0, 1.4)
    r.door("DoorClassroom", 4.5, 4.7, "academic_classroom", "classroom_from_corridor", "Enter", "Room 304")
    r.spawn("corridor_from_classroom", 4.5, 3.6)
    r.door("DoorStairs", 14.7, 2.5, "campus", "outside_academic_1", "Open", "Stairwell",
           requires_flag="academic_stairs_open", locked_message="The stairwell doors are chained shut from inside.")
    r.prop("Bin", "TrashBin", -6.0, 4.5, (0.35, 0.25))
    r.prop("Bench", "GymBench", 9.0, 4.4, (1.2, 0.25))
    r.light("Exit", -12.0, 1.0, (0.35, 1.0, 0.5), 0.45, 0.6, gameplay=False)
    for i, x in enumerate((-12.0, -3.0, 6.0)):
        r.light(f"Tube{i}", x, 3.5, (0.95, 0.97, 1.0), 0.8, 2.0, needs_power=True)
    r.glow("Trail", 5.2, 1.4, trail_to=(-60, -60))
    r.student("Student", 8.0, 2.5, [(-10.0, 2.6), (12.0, 2.4)])
    r.write()
    out[r.zone_id] = r

    r = Room("academic_classroom", "AcademicClassroom", "AcademicClassroomRoom", 13, 10, 3.4, 2.8)
    r.door("DoorOut", -6.2, 1.5, "academic_corridor", "corridor_from_classroom", "Go out", "Corridor")
    r.spawn("classroom_from_corridor", -5.3, 1.5)
    r.prop("Whiteboard", "Whiteboard", 0.0, 10.0)
    for row in range(4):
        for col in (-3.2, 0.0, 3.2):
            if (row, col) != (2, 3.2):
                r.prop(f"Desk{row}_{int(col * 10)}", "BenchDesk", col, 2.0 + row * 1.7, (0.9, 0.35))
    r.prop("Papers", "horror/PapersScattered", 3.0, 5.6)
    r.note("Board", 0.0, 9.5, "classroom_board", "The whiteboard",
           "CSE 4501, Digital Systems.\n\nUnder the lecture, in a different hand, pressed so hard the marker tore:\n\n"
           "DO NOT TURN OFF THE LIGHTS\nIT CAN'T SEE YOU IN THE LIGHT\nNO\nIT SEES THE LIGHT")
    r.light("MoonW", -4.5, 8.8, MOON, 0.35, 1.6, gameplay=False)
    r.light("MoonE", 4.5, 8.8, MOON, 0.35, 1.6, gameplay=False)
    r.write()
    out[r.zone_id] = r

    r = Room("academic_lab", "AcademicLab", "AcademicLabRoom", 14, 10, 3.4, 2.7)
    r.door("DoorOut", -6.7, 1.6, "campus", "outside_academic_2", "Go out", "The road")
    r.spawn("lab_from_outside", -5.8, 1.6)
    for k, (x, y) in enumerate(((-3.0, 3.0), (3.0, 3.0), (-3.0, 6.0), (3.0, 6.0))):
        r.prop(f"Bench{k}", "LabBench", x, y, (1.5, 0.45))
    r.note("Log", -3.0, 2.4, "lab_logbook", "Lab logbook",
           "EEE Lab 2, night shift log.\n\n22:40 Phase test on the generator feed from the workshops. The meters "
           "read power going DOWN into the ground, not out of it.\n\n23:10 Something is drawing current under the "
           "ME workshops. A lot of it.\n\n23:58 The scopes show a heartbeat on the mains. I've locked the genset key "
           "in the key box. Code: the course number of my night class, room 304. Nobody runs that generator.")
    r.prop("KeyCabinet", "KeyCabinet", 5.6, 9.85)
    r.keypad("KeyBox", 5.6, 9.5, "4501", "LAB KEY BOX", "keybox_open",
             "The key box swings open. One key left, on a red tag: GENSET - GARAGE.")
    for i, (x, y) in enumerate(((-3.0, 4.5), (3.0, 4.5))):
        r.light(f"Tube{i}", x, y, (0.95, 0.97, 1.0), 0.8, 2.2, needs_power=True)
    r.light("ScopeGlow", 0.0, 3.2, (0.5, 1.0, 0.7), 0.4, 0.8, gameplay=False)
    r.glow("Growth", 5.5, 2.0, spots=((0, 0, 8), (12, -6, 5), (-10, 4, 6)))
    r.write()
    out[r.zone_id] = r

    r = Room("admin_lobby", "AdminLobby", "AdminLobbyRoom", 16, 10, 3.6, 2.6)
    r.door("DoorOut", 0.0, 0.35, "campus", "outside_admin", "Go out", "The plaza")
    r.spawn("lobby_from_outside", 0.0, 1.4)
    r.door("DoorOffice", 7.7, 7.0, "admin_office", "office_from_lobby", "Enter", "Registrar")
    r.spawn("lobby_from_office", 6.8, 7.0)
    r.prop("Reception", "ReceptionCounter", 0.0, 6.0, (2.2, 0.45))
    for k, x in enumerate((-5.5, -3.0, 3.0, 5.5)):
        r.prop(f"Bench{k}", "PlazaBench", x, 2.6, (1.0, 0.25))
    r.note("Visitors", -0.8, 5.5, "admin_visitors", "Visitors' register",
           "The last entry, 23:20, signed by the night guard:\n\n'Delivered the hall breaker code to the registrar's "
           "safe as ordered. The plant room under CDS is not ours. It was never ours.'")
    r.light("Exit", 0.0, 1.0, (0.35, 1.0, 0.5), 0.45, 0.6, gameplay=False)
    r.light("TubeW", -4.0, 7.0, (0.95, 0.97, 1.0), 0.8, 2.2, needs_power=True)
    r.light("TubeE", 4.0, 7.0, (0.95, 0.97, 1.0), 0.8, 2.2, needs_power=True)
    r.write()
    out[r.zone_id] = r

    r = Room("admin_office", "AdminOffice", "AdminOfficeRoom", 8, 7, 3.2, 3.0)
    r.door("DoorOut", -3.7, 1.4, "admin_lobby", "lobby_from_office", "Go out", "Lobby")
    r.spawn("office_from_lobby", -2.9, 1.4)
    r.prop("Desk", "OfficeDesk", 0.8, 3.6, (0.9, 0.4))
    r.prop("Safe", "OfficeSafe", 3.2, 6.4, (0.5, 0.3))
    r.prop("Cabinet1", "FileCabinet", -3.2, 6.6, (0.35, 0.25))
    r.prop("Cabinet2", "FileCabinet", -2.5, 6.6, (0.35, 0.25))
    r.note("Memo", 0.8, 3.0, "registrar_memo", "Memo on the desk",
           "From the Registrar, to the night guard. CONFIDENTIAL.\n\nSheet 7 of the 1984 master plan (the service "
           "tunnels) and the north gate key are in my safe. Nobody goes down there until the faculty decide.\n\n"
           "The safe code is the date of the closed seminar, day then month. You were at the door; you know it.")
    r.keypad("SafeDial", 3.2, 6.0, "1911", "REGISTRAR'S SAFE", "safe_open",
             "The dial clicks round. The safe door swings open: a rolled plan, and a heavy key on a tag: NORTH GATE.")
    r.light("Moon", 1.5, 6.0, MOON, 0.35, 1.2, gameplay=False)
    r.write()
    out[r.zone_id] = r

    r = Room("mosque_prayer_hall", "MosquePrayerHall", "MosquePrayerHallRoom", 18, 16, 8.0, 2.3)
    r.door("DoorOut", 0.0, 0.35, "campus", "outside_mosque", "Go out", "The plaza")
    r.spawn("mosque_from_plaza", 0.0, 1.6)
    for row in range(5):
        for k, x in enumerate((-6.2, 0.0, 6.2)):
            r.prop(f"Rugs{row}_{k}", "PrayerRugs", x, 4.0 + row * 2.0)
    r.prop("Minbar", "Minbar", 2.6, 14.6, (0.6, 0.4))
    for k, x in enumerate((-6.0, -2.0, 6.0)):
        r.prop(f"Rehal{k}", "Rehal", x, 2.5)
    r.note("Imam", -2.0, 2.3, "imam_note", "A note tucked in a Quran stand",
           "To whoever comes in after me: stay. They do not come in here. I have watched them stop at the door, "
           "like the light from the great window holds them back.\n\nRest. Then go and find the others in the halls. "
           "- the muezzin")
    r.light("GreatWindow", 0.0, 3.0, (0.6, 0.7, 1.0), 0.7, 3.2, gameplay=True)
    r.light("Mihrab", 0.0, 14.8, (1.0, 0.85, 0.6), 0.5, 1.2, gameplay=True)
    r.write()
    out[r.zone_id] = r

    r = Room("auditorium_hall", "AuditoriumHall", "AuditoriumHallRoom", 24, 20, 8.0, 2.2)
    r.door("DoorOut", -4.0, 0.35, "campus", "outside_auditorium", "Go out", "The plaza")
    r.spawn("auditorium_from_plaza", -4.0, 1.6)
    r.door("DoorAv", -11.7, 4.0, "av_hall", "av_from_auditorium", "Enter", "AV hall")
    r.spawn("auditorium_from_av", -10.8, 4.0)
    r.prop("Stage", "StagePlatform", 0.0, 17.8)
    for row in range(6):
        r.prop(f"SeatsW{row}", "SeatRow", -5.0, 4.0 + row * 1.8)
        r.prop(f"SeatsE{row}", "SeatRow", 5.0, 4.0 + row * 1.8)
    r.light("StageSpot", 0.0, 17.0, (1.0, 0.9, 0.7), 0.6, 2.6, needs_power=True, mode=1)
    r.light("Exit", -4.0, 1.0, (0.35, 1.0, 0.5), 0.45, 0.6, gameplay=False)
    r.glow("Curtain", 3.0, 18.5, spots=((0, -10, 9), (14, -30, 6), (-8, -44, 7), (20, -60, 5)))
    r.write()
    out[r.zone_id] = r

    r = Room("av_hall", "AvHall", "AvHallRoom", 14, 11, 4.0, 2.7)
    r.door("DoorOut", -6.7, 2.0, "auditorium_hall", "auditorium_from_av", "Go out", "Auditorium")
    r.spawn("av_from_auditorium", -5.8, 2.0)
    r.prop("Screen", "ProjectorScreen", 0.0, 11.0)
    for row in range(4):
        r.prop(f"Seats{row}", "SeatRow", 0.5, 3.0 + row * 1.8)
    r.note("Projector", 0.0, 1.0, "av_projector", "The projector's last slide",
           "Still burned into the screen: 'ORGANISM 7 - PHOTOTROPIC RESPONSE IN HOST TISSUE. Faculty seminar, "
           "19 November, closed session.' Under it, a photo of the CDS plant room hatch, open, and light coming up from below.",
           light=False)
    r.light("Screen", 0.0, 9.5, (0.7, 0.8, 1.0), 0.5, 2.0, gameplay=False)
    r.write()
    out[r.zone_id] = r

    r = Room("central_cafe", "CentralCafe", "CentralCafeRoom", 24, 12, 4.0, 2.3)
    r.door("DoorOut", -6.0, 0.35, "campus", "outside_cafe", "Go out", "The plaza")
    r.spawn("cafe_from_plaza", -6.0, 1.6)
    for k, (x, y, sc) in enumerate(((-8.0, 4.0, "CanteenTableSetA"), (-3.0, 4.0, "CanteenTableSetB"),
                                    (3.0, 4.0, "CanteenTableSetC"), (8.0, 4.0, "CanteenTableSetA"),
                                    (-8.0, 7.5, "CanteenTableSetB"), (3.0, 7.5, "CanteenTableSetA"),
                                    (8.0, 7.5, "CanteenTableSetB"))):
        r.prop(f"Table{k}", sc, x, y, (1.0, 0.55))
    r.prop("Crates", "CrateStack", 10.8, 10.5, (0.6, 0.3))
    r.pickup("Oil", 9.6, 10.6, "cafe_oil", "Lamp kerosene", "OilBottle", fuel=0.35)
    r.hide("ColdRoom", -10.6, 10.9, "The cold room")
    r.light("Moon", 0.0, 2.0, MOON, 0.4, 2.5, gameplay=False)
    r.glow("Spill", -0.5, 10.6, spots=((0, 0, 10), (-14, 6, 7), (16, 4, 6), (4, 14, 5)))
    r.write()
    out[r.zone_id] = r

    r = Room("hall_corridor", "HallCorridor", "HallCorridorRoom", 26, 4.5, 3.2, 2.4)
    r.door("DoorOut", -12.7, 2.2, "campus", "outside_south_hall", "Go out", "South Hall entrance")
    r.spawn("hallcorr_from_outside", -11.8, 2.2)
    r.door("DoorRoom", 0.0, 4.2, "hall_room", "room_from_corridor", "Enter", "Room 203")
    r.sleepwalker("Sleeper", 8.0, 2.2, [(4.0, 2.2), (12.0, 2.3)])
    r.spawn("hallcorr_from_room", 0.0, 3.2)
    r.prop("Drum", "WaterDrum", 12.0, 3.9, (0.4, 0.3))
    r.light("Exit", -12.0, 3.0, (0.35, 1.0, 0.5), 0.45, 0.6, gameplay=False)
    r.light("Tube", 6.0, 3.6, (0.95, 0.97, 1.0), 0.8, 2.0, needs_power=True, mode=1)
    r.write()
    out[r.zone_id] = r

    r = Room("hall_room", "HallRoom", "HallRoomRoom", 6, 5, 3.2, 3.0)
    r.door("DoorOut", -1.8, 0.35, "hall_corridor", "hallcorr_from_room", "Go out", "Corridor")
    r.spawn("room_from_corridor", -1.8, 1.3)
    r.prop("BedW", "DormBed", -1.9, 3.8, (1.0, 0.45))
    r.prop("BedE", "DormBed", 1.9, 3.8, (1.0, 0.45))
    r.prop("Desk", "StudyTable", 0.0, 4.55, (0.6, 0.3))
    r.prop("Almirah", "SteelAlmirah", 2.3, 1.0, (0.55, 0.3))
    r.note("Diary", 0.0, 4.15, "dorm_diary", "A diary open on the desk",
           "Nov 20. The dogs behind UB Hall have stopped barking. They just stand at the fence and look at the "
           "lights.\n\nNov 21. Dr. Karim gave Rafi the key to the workshop lift ('if anything happens, it goes to "
           "the roof people'). Tonight the residents started walking in their sleep, all towards the light. Rafi "
           "went out to the courtyard with his phone torch to find his roommate. He hasn't come back.")
    r.light("Moon", 0.0, 4.4, MOON, 0.35, 1.2, gameplay=False)
    r.write()
    out[r.zone_id] = r

    r = Room("hall_common", "HallCommon", "HallCommonRoom", 12, 9, 3.4, 2.8)
    r.door("DoorOut", -5.7, 1.6, "campus", "outside_north_hall", "Go out", "North Hall entrance")
    r.spawn("common_from_outside", -4.8, 1.6)
    r.prop("Tv", "TvStand", 0.0, 8.5, (0.6, 0.3))
    r.prop("Carrom", "CarromBoard", 2.5, 4.0, (0.5, 0.5))
    for k, (x, y) in enumerate(((-2.0, 5.5), (-3.5, 3.5), (4.0, 6.5))):
        r.prop(f"Chair{k}", "ChairStack" if k == 2 else "CanteenTableSetB", x, y, (0.9, 0.5) if k < 2 else (0.4, 0.3))
    r.note("Radio", 0.0, 7.9, "common_radio", "A walkie-talkie on the TV",
           "It crackles. A voice, very faint: '...anyone in the halls, we're on the UB roof, back stair... the "
           "sleepwalkers go for any light, keep it OFF... Rafi from South Hall, room 203, has the workshop lift key. "
           "He went out an hour ago. If you find him, bring the key. Knock three short, three long.'", light=False)
    r.light("TvGlow", 0.0, 7.8, (0.6, 0.8, 1.0), 0.5, 1.4, gameplay=False)
    r.write()
    out[r.zone_id] = r

    # --- Chapter 5 "Below": the ME workshop floor and Site 7 (D40) -------------------------------------------
    RED = (1.0, 0.18, 0.12)
    GREEN = (0.4, 1.0, 0.75)
    r = Room("me_workshop", "MeWorkshopFloor", "MeWorkshopRoom", 24, 12, 5.0, 2.3)
    r.door("DoorOut", -8.0, 0.35, "campus", "outside_workshop", "Go out", "The road")
    r.spawn("workshop_from_outside", -8.0, 1.5)
    r.door("DoorPitLift", 9.0, 7.65, "facility_corridor", "corridor_from_lift", "Ride down", "Pit lift",
           required_item="lift_key", locked_message="The lift's key switch is locked. Rafi had the key.")
    r.spawn("workshop_from_lift", 9.0, 6.4)
    for k, (x, y) in enumerate(((-6.0, 5.0), (-1.0, 5.0))):
        r.prop(f"Lathe{k}", "Lathe", x, y, (1.1, 0.4))
    for k, x in enumerate((-9.0, -4.0)):
        r.prop(f"Bench{k}", "Workbench", x, 11.35, (1.1, 0.45))
    r.prop("Crates", "CrateStack", 4.0, 2.0, (0.6, 0.3))
    r.prop("Drum", "WaterDrum", 11.0, 2.0, (0.4, 0.3))
    r.note("JobCard", -4.0, 10.8, "workshop_job_card", "A job card on the bench",
           "WORKSHOP JOB CARD 07.\n\nService the pit lift (B2). Authorised: the Registrar. Do NOT enter this job in the "
           "log book.\n\nKeys: Dr. Karim only.\n\nSomeone has added in pencil: 'what is B2 for?'")
    r.light("TubeW", -6.0, 6.0, (0.95, 0.97, 1.0), 0.75, 2.6, needs_power=True)
    r.light("TubeE", 4.0, 6.0, (0.95, 0.97, 1.0), 0.75, 2.6, needs_power=True, mode=1)
    r.glow("LiftGrowth", 9.0, 7.2, spots=((0, 0, 8), (-14, 6, 6), (12, 4, 5)))
    r.write()
    out[r.zone_id] = r

    r = Room("facility_corridor", "FacilityCorridor", "FacilityCorridorRoom", 30, 4.5, 3.2, 2.4)
    r.door("DoorLift", -14.7, 2.2, "me_workshop", "workshop_from_lift", "Ride up", "ME workshop")
    r.spawn("corridor_from_lift", -13.8, 2.2)
    r.door("DoorControl", -6.0, 4.2, "facility_control", "control_from_corridor", "Enter", "Control room")
    r.spawn("corridor_from_control", -6.0, 3.2)
    r.door("DoorLab", 6.0, 4.2, "facility_lab", "lab_from_corridor", "Enter", "Containment")
    r.spawn("corridor_from_lab", 6.0, 3.2)
    r.door("DoorB2", 14.7, 2.2, "facility_chamber", "chamber_from_lift", "Ride down", "Lift to B2",
           requires_flag="b2_lift_powered",
           locked_message="The B2 lift is dead: no current reaches it. The control room routes the power.")
    r.spawn("corridor_from_b2", 13.8, 2.2)
    r.note("Notice", -11.5, 3.9, "site7_notice", "Staff notice",
           "SITE 7 - STAFF NOTICE.\n\nLights on the colony side of B2 stay OFF at all times. It grows towards light. "
           "It feeds on current.\n\nIf the feed is ever interrupted it will reach for ANY other source.")
    r.technician("Technician1", -4.0, 2.2, [(-11.0, 2.0), (11.0, 2.4)])
    r.technician("Technician2", 10.0, 1.6, [(12.0, 1.5), (2.0, 1.6)])
    for k, x in enumerate((-12.0, -2.0, 10.0)):
        r.light(f"Red{k}", x, 3.9, RED, 0.5, 1.4, gameplay=False)
    r.glow("Growth", 9.5, 3.0, spots=((0, 0, 9), (-16, 6, 6), (18, -4, 7)))
    r.write()
    out[r.zone_id] = r

    r = Room("facility_control", "FacilityControl", "FacilityControlRoom", 12, 8, 3.2, 2.8)
    r.door("DoorOut", -4.0, 0.35, "facility_corridor", "corridor_from_control", "Go out", "B1 corridor")
    r.spawn("control_from_corridor", -4.0, 1.4)
    r.prop("DeskW", "ControlDesk", -2.5, 5.0, (1.1, 0.45))
    r.prop("DeskE", "ControlDesk", 4.2, 3.0, (1.1, 0.45))
    r.prop("Chair", "OfficeChairFallen", -1.0, 3.2, (0.4, 0.3))
    r.prop("Cabinet", "FileCabinet", 5.4, 7.2, (0.35, 0.25))
    r.note("DirectorLog", -2.5, 4.4, "director_log", "Director's log, Site 7",
           "1984. The tunnel crew broke into a cavity under the workshops full of soft green light. Organism 7: one "
           "colony, kilometres of it, feeding on light and on current.\n\n1991. The University agreed to keep it fed "
           "from the campus grid. In return, the research. In return, silence.\n\n2026. It takes more every year. "
           "Tonight it took everything: the whole campus went dark at 11:04.\n\nThe feed routing is on the "
           "switchboard. Staff card only. If the feed is cut, God help whoever is holding a light.")
    r.examine("Switchboard", 2.5, 7.15, "Feed routing",
              "You swipe the card. One by one you throw the breakers from ORGANISM FEED to LIFT B2. Far below, "
              "something shifts in the dark, and every light on B1 dims.",
              verb="Route", sets_flag="b2_lift_powered", requires_flag="has_facility_card",
              not_ready="The switchboard is locked behind a card reader. STAFF CARD ONLY.")
    r.light("Crt", -3.0, 7.0, (0.55, 0.9, 0.7), 0.45, 1.8, gameplay=False)
    r.light("Red", 3.3, 7.4, RED, 0.4, 1.0, gameplay=False)
    r.write()
    out[r.zone_id] = r

    r = Room("facility_lab", "FacilityLab", "FacilityLabRoom", 14, 10, 3.4, 2.7)
    r.door("DoorOut", 4.0, 0.35, "facility_corridor", "corridor_from_lab", "Go out", "B1 corridor")
    r.spawn("lab_from_corridor", 4.0, 1.4)
    for k, x in enumerate((-5.5, -3.0, 3.0, 5.5)):
        r.prop(f"Tank{k}", "SpecimenTank", x, 9.3, (0.6, 0.35))
        r.light(f"TankGlow{k}", x, 9.0, GREEN, 0.4, 1.1, gameplay=False)
    r.prop("BenchW", "LabBench", -3.0, 4.5, (1.5, 0.45))
    r.prop("BenchE", "LabBench", 2.0, 6.2, (1.5, 0.45))
    r.prop("Body", "horror/CoveredShape", 5.2, 3.0)
    r.pickup("Card", 5.9, 2.7, "tech_card", "Staff card (Site 7)", "MasterKey", item_id="facility_card", verb="Take")
    r.note("HostReport", -3.0, 3.9, "host_report", "Incident report H-12",
           "Subject: night guard, Main Gate. Exposed to the colony's light for forty minutes during the 23:00 "
           "inspection.\n\nAfter exposure: walks towards any light; ignores speech; answers only to his own name. "
           "Reclassified: HOST.\n\nRecommendation: none. Site 7 is to be sealed.")
    r.technician("Technician", -1.0, 6.5, [(-5.0, 6.8), (5.0, 7.2)])
    r.glow("Spill", -3.5, 6.5, spots=((0, 0, 10), (-20, 8, 7), (22, -6, 6), (6, 18, 5)))
    r.write()
    out[r.zone_id] = r

    r = Room("facility_chamber", "FacilityChamber", "FacilityChamberRoom", 22, 18, 8.0, 2.2)
    r.door("DoorLift", -10.7, 3.0, "facility_corridor", "corridor_from_b2", "Ride up", "B1 corridor")
    r.spawn("chamber_from_lift", -9.8, 3.0)
    r.examine("Colony", 0.0, 7.0, "The colony",
              "It fills the turbine hall: it has grown into the generators, and the generators into it. Every light on "
              "campus has been feeding this. Deep in the mass something opens, the size of a door, and turns towards "
              "your lantern.", sets_flag="colony_seen")
    r.light("ColonyLight", 0.0, 12.0, GREEN, 1.1, 6.0, gameplay=False)
    r.light("ColonyLightW", -7.0, 10.0, GREEN, 0.6, 3.0, gameplay=False)
    r.light("ColonyLightE", 7.0, 10.0, GREEN, 0.6, 3.0, gameplay=False)
    r.glow("Floor", 0.0, 8.0, spots=((0, 0, 12), (-60, 10, 9), (70, -8, 8), (-120, 30, 7), (130, 20, 7)))
    r.write()
    out[r.zone_id] = r
    return out


if __name__ == "__main__":
    built = rooms()
    register_zones({zid: f"res://scenes/world/{r.scene_name}.tscn" for zid, r in built.items()})
    # Keep the generated docs in step with the scenes: the registry in Docs/CAMPUS_MAP.md and map-design/.
    import map_registry
    import export_map_design
    map_registry.main()
    export_map_design.main()

"""Tiny .tscn writer for authoring zone scenes from Python (decision D30: lives in the repo).

Zone scenes written with it are the source of truth afterwards only if their authoring script says so; the
campus zones (tools/zones/campus_zones.py) are regenerated from their script, so edit the script, not the scene.
Coordinates: helpers take metres in a zone-local ground frame (x east, y north) and convert to game px
(32 px/m across, 20.576 px/m in depth); or pass game px directly with V().
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPTH = 32.0 * 0.643


def fnum(v):
    v = round(float(v), 4)
    return str(int(v)) if v == int(v) else repr(v)


def V(x, y):
    return f"Vector2({fnum(x)}, {fnum(y)})"


def P(xm, ym):
    return V(xm * 32.0, -ym * DEPTH)


def S(s):
    return json.dumps(s, ensure_ascii=False)


def C(r, g, b, a=1.0):
    return f"Color({fnum(r)}, {fnum(g)}, {fnum(b)}, {fnum(a)})"


def PV2(points):
    return "PackedVector2Array(" + ", ".join(f"{fnum(x)}, {fnum(y)}" for x, y in points) + ")"


def PV3(points):
    return "PackedVector3Array(" + ", ".join(f"{fnum(x)}, {fnum(y)}, {fnum(z)}" for x, y, z in points) + ")"


class Scene:
    def __init__(self):
        self.ext = {}
        self.subs = []
        self.nodes = []
        self.conns = []
        self._n = 0

    def res(self, path, type_=None):
        if path not in self.ext:
            t = type_ or ("PackedScene" if path.endswith(".tscn") else "Script" if path.endswith(".gd")
                          else "Shader" if path.endswith(".gdshader") else "Resource")
            self.ext[path] = (t, f"{len(self.ext) + 1}_r")
        return f'ExtResource("{self.ext[path][1]}")'

    def sub(self, type_, props):
        self._n += 1
        sid = f"{type_}_{self._n}"
        body = "\n".join(f"{k} = {v}" for k, v in props.items())
        self.subs.append(f'[sub_resource type="{type_}" id="{sid}"]\n{body}\n')
        return f'SubResource("{sid}")'

    def node(self, name, type_=None, parent=".", instance=None, props=None, groups=None):
        head = f'[node name="{name}"'
        if type_:
            head += f' type="{type_}"'
        if parent is not None:
            head += f' parent="{parent}"'
        if instance:
            head += f" instance={self.res(instance)}"
        if groups:
            head += " groups=[" + ", ".join(S(g) for g in groups) + "]"
        head += "]"
        body = "\n".join(f"{k} = {v}" for k, v in (props or {}).items())
        self.nodes.append(head + ("\n" + body if body else "") + "\n")
        return name if parent in (None, ".") else f"{parent}/{name}"

    def text(self):
        out = ["[gd_scene format=3]\n"]
        for path, (t, i) in self.ext.items():
            out.append(f'[ext_resource type="{t}" path="{path}" id="{i}"]')
        out.append("")
        out += self.subs
        out += self.nodes
        out += self.conns
        return "\n".join(out).rstrip() + "\n"

    def write(self, rel):
        (ROOT / rel).write_text(self.text(), encoding="utf-8")
        print("wrote", rel)


SHADOW = "res://scenes/props/common/ContactShadow.tscn"
DOOR = "res://scenes/components/Door.tscn"
SPAWN = "res://scenes/components/SpawnMarker.tscn"
EDGE = "res://scenes/components/ZoneEdge.tscn"
READ = "res://scenes/components/Readable.tscn"
EXAMINE = "res://scenes/components/Examine.tscn"
PICKUP = "res://scenes/components/Pickup.tscn"
GLOW = "res://scripts/world/glow_mark.gd"
LAMP = "res://scripts/lighting/lamp_light.gd"
LIGHT_TEX = "res://data/lighting/light_soft.tres"
WATER = "res://assets/shaders/water.gdshader"
WALKWAY = "res://assets/sprites/ground/paved_walkway_tile.png"
GRASS = "res://assets/sprites/ground/grass_ground_tile.png"
ASPHALT = "res://assets/sprites/ground/asphalt_road_tile.png"


def campus(scene):
    return f"res://scenes/props/campus/{scene}.tscn"


def veg(scene):
    return f"res://scenes/props/vegetation/{scene}.tscn"


class ZoneScene:
    """A zone root with Ground (z -10) and a Y-sorted Objects tree; positions in game px of the zone frame."""

    def __init__(self, name, zone_id):
        self.s = Scene()
        self.zone_id = zone_id
        self.s.node(name, "Node2D", None, props={
            "y_sort_enabled": "true", "script": self.s.res("res://scripts/world/zone.gd"), "zone_id": S(zone_id),
            "profile": self.s.res(f"res://data/zones/profiles/{zone_id}.tres", "Resource")})
        self.s.node("Ground", "Node2D", props={"z_index": "-10"})
        self.s.node("Objects", "Node2D", props={"y_sort_enabled": "true"})
        for g in ("Buildings", "Props", "Vegetation", "Lights", "Doors", "SpawnMarkers", "Story", "Glow", "Bounds"):
            self.s.node(g, "Node2D", "Objects", props={"y_sort_enabled": "true"})
        self._mat = {}

    # Ground --------------------------------------------------------------------------------------------------
    def ground_poly(self, name, points, texture=None, color=None, shader=None):
        props = {"polygon": PV2(points)}
        if texture:
            props.update({"texture": self.s.res(texture, "Texture2D"), "texture_repeat": "2",
                          "texture_scale": V(4, 4)})
        if color:
            props["color"] = C(*color)
        if shader:
            if shader not in self._mat:
                self._mat[shader] = self.s.sub("ShaderMaterial", {"shader": self.s.res(shader)})
            props["material"] = self._mat[shader]
        props["light_mask"] = "1"
        self.s.node(name, "Polygon2D", "Ground", props=props)

    def ground_rect(self, name, x0, y0, x1, y1, **kw):
        self.ground_poly(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)

    def line(self, name, points, width=3.0, color=(0.92, 0.9, 0.84, 0.85), parent="Ground", closed=False):
        props = {"points": PV2(points), "width": fnum(width), "default_color": C(*color)}
        if closed:
            props["closed"] = "true"
        self.s.node(name, "Line2D", parent, props=props)

    # Objects -------------------------------------------------------------------------------------------------
    def place(self, name, scene_path, x, y, parent="Objects/Buildings", shadow=None, extra=None):
        props = {"position": V(x, y)}
        props.update(extra or {})
        path = self.s.node(name, None, parent, instance=scene_path, props=props)
        if shadow:
            self.s.node("ContactShadow", None, path, instance=SHADOW, props={"scale": V(*shadow)})
        return path

    def wall(self, name, x0, y0, x1, y1):
        """An invisible collision rectangle (zone bounds, water)."""
        shape = self.s.sub("RectangleShape2D", {"size": V(abs(x1 - x0), abs(y1 - y0))})
        body = self.s.node(name, "StaticBody2D", "Objects/Bounds", props={"collision_mask": "0"})
        self.s.node("Shape", "CollisionShape2D", body,
                    props={"position": V((x0 + x1) / 2, (y0 + y1) / 2), "shape": shape})

    def edge(self, name, x, y, w, h, dest_zone, dest_spawn, place_name="", **kw):
        props = {"position": V(x, y), "destination_zone_id": S(dest_zone), "destination_spawn_id": S(dest_spawn),
                 "size": V(w, h), "place_name": S(place_name)}
        props.update({k: S(v) for k, v in kw.items()})
        self.s.node(name, None, "Objects/Doors", instance=EDGE, props=props)

    def door(self, name, x, y, dest_zone, dest_spawn, verb, place, **kw):
        props = {"position": V(x, y), "destination_zone_id": S(dest_zone), "destination_spawn_id": S(dest_spawn),
                 "verb": S(verb), "place_name": S(place), "show_placeholder": "false"}
        for k, v in kw.items():
            props[k] = S(v) if isinstance(v, str) else fnum(v)
        self.s.node(name, None, "Objects/Doors", instance=DOOR, props=props)

    def spawn(self, spawn_id, x, y):
        self.s.node("Spawn_" + spawn_id, None, "Objects/SpawnMarkers", instance=SPAWN,
                    props={"position": V(x, y), "spawn_id": S(spawn_id)})

    def lamp_light(self, name, x, y, color=(1.0, 0.85, 0.6), energy=0.9, scale=2.4, mode=0, needs_power=True,
                   parent="Objects/Lights", circuit="power_on"):
        props = {
            "position": V(x, y), "color": C(*color), "energy": fnum(energy), "range_item_cull_mask": "3",
            "texture": self.s.res(LIGHT_TEX, "Texture2D"), "texture_scale": fnum(scale),
            "script": self.s.res(LAMP), "mode": str(mode), "needs_power": "true" if needs_power else "false",
            "base_energy": fnum(energy)}
        if needs_power:
            props["power_flag"] = S(circuit)
        self.s.node(name, "PointLight2D", parent, props=props)

    def glow(self, name, x, y, spots=(), trail_to=None, intensity=0.8, pulse=0.5):
        props = {"position": V(x, y), "script": self.s.res(GLOW), "color": C(0.45, 1.0, 0.82),
                 "intensity": fnum(intensity), "pulse_speed": fnum(pulse)}
        if spots:
            props["spots"] = PV3(spots)
        if trail_to:
            props["trail_to"] = V(*trail_to)
        self.s.node(name, "Node2D", "Objects/Glow", props=props)

    def write(self):
        self.s.write(f"scenes/world/{''.join(w.capitalize() for w in self.zone_id.split('_'))}.tscn")


STUDENT = "res://scenes/creatures/NightGuard.tscn"


def student_props(x, y, patrol):
    """A "student" (Chapter 3's sound-hunting host): the NightGuard brain tuned to hear far, see little, ignore the
    lantern, move slowly; pale, wet-looking. Dormant until a chapter's _patrol_active() wakes it."""
    return {"position": V(x, y), "patrol_points": PV2(patrol), "active": "false", "visible": "false",
            "sight_radius": "70.0", "close_sense_radius": "44.0", "light_sensitivity": "0.2", "hearing": "1.8",
            "patrol_speed": "30.0", "investigate_speed": "52.0", "chase_speed": "118.0",
            "modulate": C(0.72, 0.86, 0.78), "metadata/role": S("patrol"), "metadata/chapter": "3"}


def sleepwalker_props(x, y, patrol):
    """A "sleepwalker" (Chapter 4's host): hall residents drawn to light (D37): very light-sensitive, hard of
    hearing, slow until they see a light, then fast. Dormant until a chapter's _patrol_active() wakes it."""
    return {"position": V(x, y), "patrol_points": PV2(patrol), "active": "false", "visible": "false",
            "sight_radius": "110.0", "close_sense_radius": "40.0", "light_sensitivity": "2.2", "hearing": "0.6",
            "patrol_speed": "26.0", "investigate_speed": "60.0", "chase_speed": "128.0",
            "modulate": C(0.86, 0.83, 0.96), "metadata/role": S("patrol"), "metadata/chapter": "4"}


def technician_props(x, y, patrol):
    """A "technician" (Chapter 5's host, Site 7's former staff): sees and hears about as well as the Night Guard,
    a little faster. Dormant until Chapter 5's director wakes it."""
    return {"position": V(x, y), "patrol_points": PV2(patrol), "active": "false", "visible": "false",
            "sight_radius": "140.0", "close_sense_radius": "60.0", "light_sensitivity": "1.0", "hearing": "1.3",
            "patrol_speed": "34.0", "investigate_speed": "60.0", "chase_speed": "132.0",
            "modulate": C(0.8, 0.95, 0.85), "metadata/role": S("patrol"), "metadata/chapter": "5"}


def write_profile(zone_id, *, zoom, limits, surface, ambience, vol=-6.0, room=0.15, damp=0.7, wet=0.05,
                  night=(0.18, 0.2, 0.3), look=48.0):
    text = ('[gd_resource type="Resource" script_class="ZoneProfile" format=3]\n\n'
            '[ext_resource type="Script" path="res://scripts/world/zone_profile.gd" id="1_profile"]\n'
            f'[ext_resource type="AudioStream" path="res://assets/audio/ambience/{ambience}.wav" id="2_ambience"]\n'
            '\n[resource]\nscript = ExtResource("1_profile")\n'
            f'camera_zoom = {zoom}\ncamera_limits = Rect2({limits[0]}, {limits[1]}, {limits[2]}, {limits[3]})\n'
            f'look_ahead_px = {look}\nnight_ambient = Color({night[0]}, {night[1]}, {night[2]}, 1)\n'
            f'default_surface = &"{surface}"\nambience = ExtResource("2_ambience")\nambience_volume_db = {vol}\n'
            f'reverb_room_size = {room}\nreverb_damping = {damp}\nreverb_wet = {wet}\n')
    (ROOT / f"data/zones/profiles/{zone_id}.tres").write_text(text, encoding="utf-8")
    print("wrote profile", zone_id)


def register_zones(entries):
    """Adds zone_id -> scene path entries to data/zones/zone_registry.tres (keeps the rest)."""
    p = ROOT / "data/zones/zone_registry.tres"
    s = p.read_text(encoding="utf-8")
    start = s.index("zones = Dictionary[String, String]({") + len("zones = Dictionary[String, String]({")
    end = s.index("})", start)
    current = {}
    for line in s[start:end].strip().splitlines():
        line = line.strip().rstrip(",")
        if line:
            k, v = line.split(":", 1)
            current[json.loads(k.strip())] = json.loads(v.strip())
    current.update(entries)
    body = "\n" + ",\n".join(f"{json.dumps(k)}: {json.dumps(v)}" for k, v in sorted(current.items())) + "\n"
    p.write_text(s[:start] + body + s[end:], encoding="utf-8")
    print("registry:", ", ".join(sorted(current)))

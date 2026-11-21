"""Writes the Chapter 1 interior configs (assembly generator): the room shells. Run from anywhere:

    python assets/source/blender/tools/author_rooms.py           # write / refresh every room config
    python assets/source/blender/tools/author_rooms.py --list    # print the asset ids

How an interior is drawn (Docs/CONVENTIONS.md, interiors):
- Room frame: x in [-W/2, W/2] (metres, +X right), y in [0, D] (y = 0 is the inner face of the south wall, +Y north,
  away from the camera), z up. In Godot the room scene sits at the zone origin: x_px = 32 x, y_px = -20.57 y.
- Base sprite (`sprite_z_index` -10, like ground): floor, the north wall (its inner face is what the camera sees), the side walls
  (seen edge-on: only their tops show) and everything fixed flush against them. Every Y-sorted thing draws over it.
- Layer `SouthWall`: the south wall, cut down to a knee-high section so the room stays visible (a cutaway), sorted
  at its south face: always in front of the player.
- Other layers: free-standing fixed pieces (door leaves standing open, projecting signs), each sorted at its own
  front edge.
- Lighting: a camera-invisible ceiling blocks the rig's sun; soft area lights under it light the room as if its
  tube lights were on. The game then darkens it (night) and the lantern / emergency lights relight it.
- Collision: walls (with gaps at doors) and fixed pieces, as named rectangles.
"""

import json
import math
import random
import sys

sys.dont_write_bytecode = True
from author_lib import (MATS, blob, box, cbox, cyl, lathe, leg, moved, rotated, rotated_z, text,  # noqa: E402
                        tube, write_config)

MATS.update({
    "red_oxide": {"color": [0.52, 0.2, 0.15], "rough": 0.3, "var": 0.1, "var_scale": 3, "stains": 0.4,
                  "stain_color": [0.36, 0.15, 0.12], "stain_scale": 1.2, "bump": 0.05,
                  "pattern": {"type": "tiles", "size": 1.2, "color2": [0.5, 0.19, 0.14], "mortar": 0.006,
                              "mortar_color": [0.3, 0.12, 0.1]}},
    "grass_dark": {"color": [0.2, 0.3, 0.13], "rough": 0.95, "var": 0.25, "var_scale": 3, "bump": 0.6,
                   "bump_scale": 90},
    "coping": {"color": [0.78, 0.76, 0.7], "rough": 0.7, "stains": 0.4, "stain_color": [0.5, 0.48, 0.42]},
    "blackboard": {"color": [0.07, 0.1, 0.08], "rough": 0.7, "stains": 0.3, "stain_color": [0.2, 0.22, 0.2]},
    "chalk": {"color": [0.85, 0.85, 0.8], "rough": 0.9},
    "sign_green": {"color": [0.1, 0.33, 0.2], "rough": 0.5, "stains": 0.3},
    "sign_white": {"color": [0.92, 0.91, 0.86], "rough": 0.5},
    "door_wood": {"color": [0.35, 0.2, 0.11], "rough": 0.55, "stains": 0.2,
                  "pattern": {"type": "grain", "scale": [30, 0.6, 30]}},
    "orange_hoop": {"color": [0.9, 0.35, 0.08], "rough": 0.4, "metal": 0.4},
    "glass_board": {"color": [0.55, 0.62, 0.66], "glass": True},
    "tube_light": {"color": [0.9, 0.92, 0.95], "rough": 0.3, "emit": [1.0, 1.0, 0.95], "emit_strength": 0.0},
})

ROOMS = {}
DEPTH = 0.643


def mats_used(objects):
    used = set()

    def walk(parts):
        for p in parts:
            if "part" in p:
                walk([p["part"]])
            elif "mat" in p:
                used.add(p["mat"])
    for spec in objects.values():
        walk(spec["parts"])
    return {n: MATS[n] for n in sorted(used)}


class Room:
    def __init__(self, asset_id, scene, desc, W, D, H, *, wall_t=0.25, floor="tile_floor", wall="plaster",
                 dado="dado_green", dado_h=1.2, south_h=0.9, px_per_m=100.0, light_power=None, samples=256):
        self.asset_id, self.scene, self.desc = asset_id, scene, desc
        self.W, self.D, self.H, self.t = W, D, H, wall_t
        self.floor_mat, self.wall_mat, self.dado_mat, self.dado_h = floor, wall, dado, dado_h
        self.south_h = south_h
        self.px_per_m, self.samples = px_per_m, samples
        self.openings = {"N": [], "S": [], "W": [], "E": []}
        self.base = []           # extra base parts (fixed things flush to walls, floor dressing)
        self.layers = []         # (name, parts, sort_y_m, fade_rects or None)
        self.collision = {}
        self.lights = []
        self.light_power = light_power
        self.no_wall = set()     # walls not built (open sides)

    def opening(self, wall, at, width, z0=0.0, z1=2.1, kind="door", frame="door_wood"):
        self.openings[wall].append(dict(at=at, w=width, z0=z0, z1=z1, kind=kind, frame=frame))

    def layer(self, name, parts, sort_y, fade=None, collide=None):
        self.layers.append((name, parts, sort_y, fade))
        if collide:
            self.collision[name] = collide

    # --- walls --------------------------------------------------------------------------------------------------

    def _wall_x(self, y0, y1, x0, x1, h, ops, along="x", lo=None, hi=None):
        """Wall along X (north/south walls) from lo to hi in x, thickness y0..y1, with openings cut."""
        parts = []
        lo = lo if lo is not None else x0
        hi = hi if hi is not None else x1
        cuts = sorted(ops, key=lambda o: o["at"])
        cursor = lo
        for o in cuts:
            a, b = o["at"] - o["w"] / 2, o["at"] + o["w"] / 2
            if a > cursor:
                parts.append(box(cursor, a, y0, y1, 0.0, h, self.wall_mat))
            if o["z0"] > 0:
                parts.append(box(a, b, y0, y1, 0.0, min(o["z0"], h), self.wall_mat))
            if o["z1"] < h:
                parts.append(box(a, b, y0, y1, o["z1"], h, self.wall_mat))
            cursor = b
        if cursor < hi:
            parts.append(box(cursor, hi, y0, y1, 0.0, h, self.wall_mat))
        return parts

    def _wall_y(self, x0, x1, lo, hi, h, ops):
        parts = []
        cursor = lo
        for o in sorted(ops, key=lambda o: o["at"]):
            a, b = o["at"] - o["w"] / 2, o["at"] + o["w"] / 2
            if a > cursor:
                parts.append(box(x0, x1, cursor, a, 0.0, h, self.wall_mat))
            if o["z0"] > 0:
                parts.append(box(x0, x1, a, b, 0.0, min(o["z0"], h), self.wall_mat))
            if o["z1"] < h:
                parts.append(box(x0, x1, a, b, o["z1"], h, self.wall_mat))
            cursor = b
        if cursor < hi:
            parts.append(box(x0, x1, cursor, hi, 0.0, h, self.wall_mat))
        return parts

    def _north_trim(self):
        """Dado band, skirting and window / door dressing on the north wall's inner face."""
        W, D = self.W, self.D
        parts = []
        cuts = sorted(self.openings["N"], key=lambda o: o["at"])
        trim_cuts = [o for o in cuts if o["kind"] == "door" or o["z0"] < self.dado_h + 0.05]
        cursor = -W / 2
        spans = []
        for o in trim_cuts:
            a, b = o["at"] - o["w"] / 2, o["at"] + o["w"] / 2
            if a > cursor:
                spans.append((cursor, a))
            cursor = b
        if cursor < W / 2:
            spans.append((cursor, W / 2))
        for a, b in spans:
            if self.dado_mat:
                parts.append(box(a, b, D - 0.012, D, 0.0, self.dado_h, self.dado_mat))
                parts.append(box(a, b, D - 0.02, D, self.dado_h, self.dado_h + 0.04, "coping"))
            parts.append(box(a, b, D - 0.025, D, 0.0, 0.1, "metal_dark" if not self.dado_mat else self.dado_mat))
        for o in cuts:
            a, b = o["at"] - o["w"] / 2, o["at"] + o["w"] / 2
            fr = o["frame"]
            if o["kind"] == "window":
                parts += [box(a - 0.06, b + 0.06, D - 0.05, D + 0.02, o["z0"] - 0.06, o["z0"], "coping"),
                          box(a - 0.06, b + 0.06, D - 0.03, D, o["z1"], o["z1"] + 0.06, fr),
                          box(a - 0.06, a, D - 0.03, D, o["z0"], o["z1"], fr),
                          box(b, b + 0.06, D - 0.03, D, o["z0"], o["z1"], fr),
                          box(a, b, D + self.t * 0.5, D + self.t * 0.5 + 0.01, o["z0"], o["z1"], "glass")]
                n = max(2, int(o["w"] / 0.15))
                for k in range(1, n):
                    x = a + (b - a) * k / n
                    parts.append(cyl([x, D + 0.02, o["z0"]], [x, D + 0.02, o["z1"]], 0.008, "metal_dark", sides=6))
                parts.append(box(a, b, D + 0.01, D + 0.03, (o["z0"] + o["z1"]) / 2 - 0.015,
                                 (o["z0"] + o["z1"]) / 2 + 0.015, "metal_dark"))
            else:
                parts += [box(a - 0.08, a, D - 0.04, D + 0.02, 0.0, o["z1"] + 0.08, fr),
                          box(b, b + 0.08, D - 0.04, D + 0.02, 0.0, o["z1"] + 0.08, fr),
                          box(a - 0.08, b + 0.08, D - 0.04, D + 0.02, o["z1"], o["z1"] + 0.08, fr)]
                if o.get("closed", True):
                    parts.append(box(a, b, D + 0.05, D + 0.09, 0.0, o["z1"], "door_wood"))
                    parts.append(box(b - 0.15, b - 0.09, D - 0.0, D + 0.05, 1.0, 1.06, "brass"))
                else:
                    parts.append(box(a, b, D + self.t, D + self.t + 0.05, 0.0, o["z1"], "black_paint"))
        return parts

    def build(self):
        W, D, H, t = self.W, self.D, self.H, self.t
        floor = [box(-W / 2 - t, W / 2 + t, -t, D + t, -0.15, 0.0, self.floor_mat)]
        base = list(floor)
        if "N" not in self.no_wall:
            base += self._wall_x(D, D + t, -W / 2 - t, W / 2 + t, H, self.openings["N"])
            base += self._north_trim()
        if "W" not in self.no_wall:
            base += self._wall_y(-W / 2 - t, -W / 2, -t, D + t, H, self.openings["W"])
            base.append(box(-W / 2, -W / 2 + 0.02, 0.0, D, 0.0, 0.1, self.dado_mat or "metal_dark"))
        if "E" not in self.no_wall:
            base += self._wall_y(W / 2, W / 2 + t, -t, D + t, H, self.openings["E"])
            base.append(box(W / 2 - 0.02, W / 2, 0.0, D, 0.0, 0.1, self.dado_mat or "metal_dark"))
        # Door openings in the side walls get a threshold and a dark jamb so the gap reads from above.
        for side, x0 in (("W", -W / 2 - t), ("E", W / 2)):
            for o in self.openings[side]:
                a, b = o["at"] - o["w"] / 2, o["at"] + o["w"] / 2
                if o["kind"] == "door":
                    base.append(box(x0 - 0.05, x0 + t + 0.05, a, b, 0.0, 0.02, "coping"))
                    base.append(box(x0, x0 + t, a - 0.06, a, 0.0, o["z1"], o["frame"]))
                    base.append(box(x0, x0 + t, b, b + 0.06, 0.0, o["z1"], o["frame"]))
        base += self.base
        objects = {"Base": {"parts": base, "bevel": 0.006}}
        layers = []
        if "S" not in self.no_wall:
            south = self._wall_x(-t, 0.0, -W / 2 - t, W / 2 + t, self.south_h, self.openings["S"])
            south.append(box(-W / 2 - t - 0.02, W / 2 + t + 0.02, -t - 0.02, 0.02, self.south_h, self.south_h + 0.05,
                             "coping"))
            objects["SouthWall"] = {"parts": south, "bevel": 0.006}
            layers.append({"name": "SouthWall", "objects": ["SouthWall"], "sort_y_m": -t})
        for name, parts, sort_y, fade in self.layers:
            objects[name] = {"parts": parts, "bevel": 0.005}
            layer = {"name": name, "objects": [name], "sort_y_m": round(sort_y, 4)}
            if fade:
                layer["fade"] = {"rects_m": fade, "alpha": 0.35, "seconds": 0.25}
            layers.append(layer)
        # Collision: walls with door gaps.
        col = dict(self.collision)
        if "N" not in self.no_wall:
            col["WallN"] = [-W / 2 - t, W / 2 + t, D, D + t]
        if "S" not in self.no_wall:
            col.update(self._gapped("WallS", "x", -t, 0.0, -W / 2 - t, W / 2 + t, self.openings["S"]))
        if "W" not in self.no_wall:
            col.update(self._gapped("WallW", "y", -W / 2 - t, -W / 2, -t, D + t, self.openings["W"]))
        if "E" not in self.no_wall:
            col.update(self._gapped("WallE", "y", W / 2, W / 2 + t, -t, D + t, self.openings["E"]))
        # A door gap leads to another zone, not outside: a blocker just beyond each side-wall door keeps the player
        # in the doorway (where the door's prompt is).
        for side, xa, xb in (("W", -W / 2 - t - 0.5, -W / 2 - t), ("E", W / 2 + t, W / 2 + t + 0.5)):
            for i, o in enumerate(o for o in self.openings[side] if o["kind"] == "door"):
                col[f"DoorStop{side}{i + 1}"] = [xa, xb, o["at"] - o["w"] / 2 - 0.1, o["at"] + o["w"] / 2 + 0.1]
        # Lights: a grid of soft panels just under the ceiling.
        nx, ny = max(1, round(W / 4.5)), max(1, round(D / 4.5))
        # Exposure: about 5.5 W of area light per square metre of floor (the security office was tuned by eye);
        # `light_power` scales that (1.0 = the default level).
        power = 5.5 * W * D / (nx * ny) * (self.light_power or 1.0)
        lights = list(self.lights)
        for i in range(nx):
            for j in range(ny):
                lights.append({"at": [-W / 2 + W * (i + 0.5) / nx, D * (j + 0.5) / ny, H - 0.1], "size": [1.6, 0.4],
                               "power": power, "color": [1.0, 0.96, 0.88]})
        params = {"mats": mats_used(objects), "objects": objects, "footprint_m": [-W / 2 - t, W / 2 + t, -t, D + t],
                  "lights": lights, "ceiling_z": H + 0.05}
        collision = {"enabled": True, "source": "rects_m",
                     "rects_m": {k: [round(v, 4) for v in r] for k, r in col.items()}, "depth_mode": "projected"}
        ROOMS[self.asset_id] = dict(scene=self.scene, desc=self.desc, params=params, layers=layers,
                                    collision=collision, px_per_m=self.px_per_m, samples=self.samples)

    def _gapped(self, name, axis, a0, a1, lo, hi, ops):
        rects, cursor, k = {}, lo, 0
        for o in sorted([o for o in ops if o["kind"] == "door"], key=lambda o: o["at"]):
            a, b = o["at"] - o["w"] / 2, o["at"] + o["w"] / 2
            if a > cursor:
                k += 1
                rects[f"{name}{k}"] = [a0, a1, cursor, a] if axis == "y" else [cursor, a, a0, a1]
            cursor = b
        if cursor < hi:
            k += 1
            rects[f"{name}{k}"] = [a0, a1, cursor, hi] if axis == "y" else [cursor, hi, a0, a1]
        return rects


# --- Shared dressing --------------------------------------------------------------------------------------------

def wall_clock(x, D, z, hour=11, minute=4):
    parts = [cyl([x, D, z], [x, D - 0.04, z], 0.17, "white_paint", sides=28),
             cyl([x, D - 0.04, z], [x, D - 0.045, z], 0.15, "paper", sides=28)]
    ha = math.radians(90 - (hour % 12 + minute / 60) * 30)
    ma = math.radians(90 - minute * 6)
    parts.append(tube([[x, D - 0.05, z], [x + 0.08 * math.cos(ha), D - 0.05, z + 0.08 * math.sin(ha)]], 0.006,
                      "black_paint"))
    parts.append(tube([[x, D - 0.052, z], [x + 0.12 * math.cos(ma), D - 0.052, z + 0.12 * math.sin(ma)]], 0.004,
                      "black_paint"))
    return parts


def wall_text_board(x, D, z, w, h, lines, board="blackboard", ink="chalk", size=0.11):
    parts = [box(x - w / 2, x + w / 2, D - 0.04, D, z, z + h, "wood_dark"),
             box(x - w / 2 + 0.04, x + w / 2 - 0.04, D - 0.045, D - 0.04, z + 0.04, z + h - 0.04, board)]
    for i, line in enumerate(lines):
        parts.append(text(line, [x, D - 0.05, z + h - 0.12 - i * size * 1.45], size, ink))
    return parts


def tube_light(x, D, z, w=1.2):
    return [box(x - w / 2, x + w / 2, D - 0.08, D, z, z + 0.05, "white_paint"),
            cyl([x - w / 2 + 0.03, D - 0.05, z - 0.02], [x + w / 2 - 0.03, D - 0.05, z - 0.02], 0.016, "tube_light",
                sides=8)]


def growth_spill(cx, cy, r, seed, glow=True):
    rng = random.Random(seed)
    parts = [blob(cx, cy, 0.0, r, r * 0.8, 0.035, "growth", lump=0.55, seed=seed, subdiv=4)]
    for k in range(int(14 * r)):
        a, d = rng.uniform(0, 6.28), rng.uniform(0.1, 0.9) * r
        s = rng.uniform(0.03, 0.08)
        parts.append(blob(cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8, s * 0.5, s, s, s * 1.2,
                          "growth_glow" if glow and k % 3 == 0 else "growth", lump=0.3, seed=seed + k, subdiv=2))
    for k in range(6):
        a = rng.uniform(0, 6.28)
        pts = [[cx, cy, 0.01]]
        for j in range(1, 5):
            pts.append([cx + math.cos(a) * r * 0.45 * j + rng.uniform(-0.1, 0.1),
                        cy + math.sin(a) * r * 0.45 * j + rng.uniform(-0.1, 0.1), 0.01])
        parts.append(tube(pts, 0.02, "growth", radii=[0.035, 0.028, 0.02, 0.013, 0.006]))
    return parts


def blood_smear(x0, y0, x1, y1, seed, n=None, w=0.14):
    """A drag mark: a continuous streak (overlapping flat strips along the path, thinning out) with clots and a
    little spatter, rather than separate footprints."""
    rng = random.Random(seed)
    length = math.hypot(x1 - x0, y1 - y0)
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    parts = []
    segs = max(2, int(length / 0.35))
    for k in range(segs):
        f = (k + 0.5) / segs
        cx = x0 + (x1 - x0) * f + rng.uniform(-0.02, 0.02)
        cy = y0 + (y1 - y0) * f + rng.uniform(-0.02, 0.02)
        half = length / segs * 0.62
        width = w * (1.7 - 0.9 * f) * rng.uniform(0.6, 1.25)
        parts.append(box(cx - half, cx + half, cy - width / 2, cy + width / 2, 0.0, 0.002 + 0.0005 * (k % 3),
                         "blood_dry", rot=[0, 0, ang + rng.uniform(-14, 14)], pivot=[cx, cy, 0.0]))
    for k in range(int(length / 0.12)):
        f = rng.random() ** 0.8
        cx, cy = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        s_ = w * rng.uniform(0.35, 0.95) * (1.0 - 0.5 * f)
        parts.append(blob(cx + rng.uniform(-0.08, 0.08), cy + rng.uniform(-0.08, 0.08), 0.0, s_, s_ * 0.7, 0.004,
                          "blood" if k % 3 == 0 else "blood_dry", lump=0.5, seed=seed + k, subdiv=2))
    for k in range(6):
        f = rng.random()
        cx = x0 + (x1 - x0) * f + rng.uniform(-0.3, 0.3)
        cy = y0 + (y1 - y0) * f + rng.uniform(-0.3, 0.3)
        s_ = rng.uniform(0.012, 0.03)
        parts.append(blob(cx, cy, 0.0, s_, s_, 0.003, "blood", lump=0.3, seed=seed + 100 + k, subdiv=1))
    return parts


def loose_papers(cx, cy, seed, n=4):
    rng = random.Random(seed)
    out = []
    for k in range(n):
        x, y = cx + rng.uniform(-0.35, 0.35), cy + rng.uniform(-0.25, 0.25)
        out.append(box(x - 0.105, x + 0.105, y - 0.148, y + 0.148, 0.001 * k, 0.001 * k + 0.002,
                       "paper" if k % 2 else "paper_old", rot=[0, 0, rng.uniform(0, 180)], pivot=[x, y, 0.0]))
    return out


# --- Rooms ---------------------------------------------------------------------------------------------------------

def security_office():
    r = Room("security_office_room", "SecurityOfficeRoom",
             "Main Gate security office interior (west pavilion): tiled floor, green dado, door and window in the "
             "north (campus-side) wall, stopped clock, calendar, knee-high cut of the south wall with its window sills.",
             5.4, 6.0, 3.0, floor="tile_floor", dado="dado_green", px_per_m=130.0, light_power=1.0)
    r.opening("N", 0.75, 1.0, 0.0, 2.1, "door")
    r.openings["N"][-1]["closed"] = False
    r.opening("N", -1.6, 1.2, 1.0, 2.2, "window")
    r.opening("S", -1.3, 1.1, 0.8, 2.3, "window")
    r.opening("S", 1.3, 1.1, 0.8, 2.3, "window")
    D = r.D
    r.base += wall_clock(-0.45, D, 2.45)
    cal = [box(2.05, 2.55, D - 0.01, D, 1.4, 2.05, "paper")]
    for i in range(5):
        for j in range(6):
            cal.append(box(2.09 + j * 0.075, 2.14 + j * 0.075, D - 0.012, D - 0.01, 1.47 + i * 0.08, 1.5 + i * 0.08,
                           "paper_old"))
    cal.append(box(2.05, 2.55, D - 0.012, D, 1.88, 2.05, "red_paint"))
    r.base += cal
    r.base += tube_light(-0.2, D, 2.7)
    r.base += blood_smear(1.0, 3.6, 0.7, 5.7, 300, n=12)
    r.base += loose_papers(-2.0, 1.3, 310)
    r.build()


def canteen():
    r = Room("cds_canteen_room", "CdsCanteenRoom",
             "CDS canteen interior: 600 mm floor tiles, green dado, serving counter with display case and pots along "
             "the north wall, kitchen door, menu board, wash basins, windows; door in the west wall from the veranda; "
             "organism growth spilling out of the kitchen.",
             15.0, 13.0, 3.4, floor="tile_floor", dado="dado_green", px_per_m=100.0, light_power=0.9)
    W, D = r.W, r.D
    r.opening("W", 1.6, 1.6, 0.0, 2.2, "door")
    r.opening("N", 5.3, 1.1, 0.0, 2.1, "door")
    r.openings["N"][-1]["closed"] = False
    r.opening("N", -5.5, 1.6, 1.1, 2.4, "window")
    r.opening("N", -2.6, 1.6, 1.1, 2.4, "window")
    # Serving counter along the north wall (x -0.6 .. 4.4).
    c0, c1, cd = -0.6, 4.4, 0.8
    counter = [box(c0, c1, D - cd, D, 0.0, 0.95, "steel_grey"),
               box(c0 - 0.03, c1 + 0.03, D - cd - 0.04, D, 0.95, 1.0, "laminate"),
               box(c0, c1, D - cd - 0.01, D - cd, 0.05, 0.9, "steel_blue")]
    counter += [box(c0 + 0.1, c0 + 1.7, D - cd + 0.05, D - 0.1, 1.0, 1.5, "glass"),
                box(c0 + 0.1, c0 + 1.7, D - cd + 0.05, D - 0.1, 1.5, 1.53, "chrome"),
                box(c0 + 0.15, c0 + 1.65, D - cd + 0.1, D - 0.15, 1.18, 1.2, "chrome")]
    for k in range(5):
        counter.append(blob(c0 + 0.35 + k * 0.28, D - 0.42, 1.22, 0.07, 0.05, 0.04, "orange", lump=0.2, seed=400 + k,
                            subdiv=2, floor=1.2))
    for k, x in enumerate((2.0, 2.75, 3.6)):
        counter.append(lathe([[0.0, 0.0], [0.22, 0.0], [0.25, 0.04], [0.27, 0.28], [0.28, 0.3], [0.0, 0.05]],
                             [x, D - 0.4], "aluminium", sides=24))
        counter[-1]["xf"] = [{"move": [0, 0, 1.0]}]
    counter.append(lathe([[0.0, 0.0], [0.16, 0.0], [0.17, 0.5], [0.12, 0.6], [0.0, 0.62]], [c1 - 0.3, D - 0.35],
                         "chrome", sides=20))
    counter[-1]["xf"] = [{"move": [0, 0, 1.0]}]
    for k in range(6):
        counter.append(lathe([[0.0, 0.0], [0.028, 0.0], [0.034, 0.07], [0.0, 0.01]], [c0 + 1.95 + k * 0.09,
                                                                                     D - cd + 0.1], "plastic_white",
                             sides=12))
        counter[-1]["xf"] = [{"move": [0, 0, 1.0]}]
    counter.append(box(c1 - 0.9, c1 - 0.55, D - cd + 0.05, D - cd + 0.3, 1.0, 1.12, "metal_dark"))
    r.base += counter
    r.collision["Counter"] = [c0 - 0.03, c1 + 0.03, D - cd - 0.04, D]
    # Menu board above the counter, the canteen sign, a clock, tube lights.
    r.base += wall_text_board(1.9, D, 2.0, 2.6, 1.05,
                              ["CDS CANTEEN", "TEA ........ 10", "SINGARA ..... 10", "KHICHURI .... 60",
                               "EGG ROLL .... 30"], size=0.12)
    r.base += wall_clock(-4.1, D, 2.65)
    r.base += tube_light(-4.0, D, 2.95) + tube_light(1.9, D, 3.15) + tube_light(5.8, D, 2.95)
    # Wash basins along the north wall, west end.
    for k, x in enumerate((-6.8, -6.1)):
        r.base += [box(x - 0.25, x + 0.25, D - 0.45, D, 0.8, 0.88, "plastic_white"),
                   cyl([x, D - 0.1, 0.0], [x, D - 0.1, 0.8], 0.05, "plastic_white", sides=10),
                   cyl([x, D - 0.05, 1.0], [x, D - 0.2, 1.0], 0.012, "chrome", sides=8),
                   box(x - 0.2, x + 0.2, D - 0.02, D, 1.15, 1.65, "glass")]
    r.collision["Basins"] = [-7.1, -5.8, D - 0.45, D]
    # Organism spilling from the kitchen door, a dropped tray, blood.
    r.base += growth_spill(5.3, D - 0.8, 1.3, 420) + growth_spill(6.4, D - 2.3, 0.6, 440)
    r.base += [box(3.2, 3.65, 8.4, 8.75, 0.0, 0.015, "aluminium", rot=[0, 0, 20], pivot=[3.42, 8.57, 0.0])]
    r.base += blood_smear(4.8, D - 1.5, 3.0, 8.2, 450, n=14, w=0.16)
    r.build()


def table_tennis():
    r = Room("cds_table_tennis_room", "CdsTableTennisRoom",
             "CDS table-tennis room interior: wooden floor, blue dado, high windows, a trophy shelf and scoreboard on "
             "the north wall; door in the west wall from the veranda.",
             13.0, 11.0, 3.6, floor="court_wood", dado="dado_blue", px_per_m=100.0, light_power=0.9)
    W, D = r.W, r.D
    r.opening("W", 5.0, 1.6, 0.0, 2.2, "door")
    for x in (-4.2, -1.4, 1.4, 4.2):
        r.opening("N", x, 1.8, 2.2, 3.1, "window")
    shelf = [box(-1.0, 1.0, D - 0.3, D, 1.5, 1.54, "wood_dark")]
    for k, x in enumerate((-0.7, -0.25, 0.25, 0.7)):
        h = 0.28 + 0.08 * (k % 2)
        shelf += [cbox(x, D - 0.15, 0.12, 0.12, 1.54, 1.6, "wood_dark"),
                  lathe([[0.0, 0.0], [0.04, 0.0], [0.03, h * 0.6], [0.08, h], [0.0, h]], [x, D - 0.15], "brass",
                        sides=16)]
        shelf[-1]["xf"] = [{"move": [0, 0, 1.6]}]
    r.base += shelf
    r.base += wall_text_board(-4.6, D, 1.2, 1.6, 0.9, ["HOME   GUEST", "  7      11"], board="black_paint", size=0.16)
    r.base += wall_text_board(4.6, D, 1.25, 1.4, 0.8, ["RULES", "NO SHOES", "ON THE FLOOR"], board="sign_white",
                              ink="black_paint", size=0.1)
    r.base += tube_light(-2.8, D, 3.3) + tube_light(2.8, D, 3.3)
    r.base += blood_smear(-6.0, 2.0, -4.0, 6.5, 500, n=10)
    r.build()


def basketball_hall():
    r = Room("cds_indoor_basketball_room", "CdsIndoorBasketballRoom",
             "CDS indoor games hall: sprung wooden court with painted lines, a wall-mounted backboard and hoop on the "
             "north wall, high windows, a generator-room door, timber bleachers along the east wall; door in the "
             "west wall from the veranda.",
             18.0, 20.0, 6.0, floor="court_wood", dado="dado_green", dado_h=1.5, px_per_m=80.0, light_power=1.5,
             south_h=1.0)
    W, D = r.W, r.D
    r.opening("W", 3.0, 2.0, 0.0, 2.6, "door")
    r.opening("N", -6.5, 1.2, 0.0, 2.2, "door")          # generator / plant room (closed)
    for x in (-3.0, 3.0, 7.0):
        r.opening("N", x, 2.4, 3.6, 5.2, "window")
    # Court lines (15 x 18 m inside the hall), keys, centre circle, three-point arcs.
    lw = 0.05
    cx0, cx1, cy0, cy1 = -7.5, 6.0, 1.0, 19.0
    lines = [box(cx0, cx1, cy0, cy0 + lw, 0.0, 0.002, "court_line"), box(cx0, cx1, cy1 - lw, cy1, 0.0, 0.002, "court_line"),
             box(cx0, cx0 + lw, cy0, cy1, 0.0, 0.002, "court_line"), box(cx1 - lw, cx1, cy0, cy1, 0.0, 0.002, "court_line"),
             box(cx0, cx1, (cy0 + cy1) / 2 - lw / 2, (cy0 + cy1) / 2 + lw / 2, 0.0, 0.002, "court_line")]
    mx, my = (cx0 + cx1) / 2, (cy0 + cy1) / 2
    ring = [[mx + 1.8 * math.cos(2 * math.pi * k / 40), my + 1.8 * math.sin(2 * math.pi * k / 40), 0.001]
            for k in range(41)]
    lines.append(tube(ring, 0.025, "court_line", sides=4, cap=False))
    for yb, sgn in ((cy1, -1), (cy0, 1)):
        lines.append(box(mx - 2.45, mx + 2.45, min(yb, yb + sgn * 5.8), max(yb, yb + sgn * 5.8), 0.0, 0.0015,
                         "court_paint"))
        arc = [[mx + 6.0 * math.cos(math.radians(a)), yb + sgn * 6.0 * math.sin(math.radians(a)) + sgn * 0.3, 0.001]
               for a in range(10, 171, 8)]
        lines.append(tube(arc, 0.025, "court_line", sides=4, cap=False))
    r.base += lines
    # Backboard and hoop on the north wall.
    bb = [box(mx - 0.06, mx + 0.06, D - 1.2, D, 2.95, 3.05, "metal_dark"),
          box(mx - 0.9, mx + 0.9, D - 1.25, D - 1.2, 2.9, 3.95, "glass_board"),
          box(mx - 0.3, mx + 0.3, D - 1.255, D - 1.25, 3.05, 3.5, "white_paint")]
    hoop = [[mx + 0.23 * math.cos(2 * math.pi * k / 24), D - 1.5 + 0.23 * math.sin(2 * math.pi * k / 24), 3.05]
            for k in range(25)]
    bb.append(tube(hoop, 0.012, "orange_hoop", sides=6, cap=False))
    for k in range(8):
        a = 2 * math.pi * k / 8
        bb.append(tube([[mx + 0.22 * math.cos(a), D - 1.5 + 0.22 * math.sin(a), 3.04],
                        [mx + 0.13 * math.cos(a + 0.4), D - 1.5 + 0.13 * math.sin(a + 0.4), 2.65]], 0.004,
                       "paper", sides=4))
    r.layer("Backboard", bb, D - 1.6)
    # Bleachers along the east wall, touching the north wall (nobody gets behind them).
    bl = []
    for step in range(3):
        x0 = W / 2 - 1.8 + step * 0.6
        bl += [box(x0, W / 2, 2.0, D, 0.0, 0.4 + step * 0.4, "wood"),
               box(x0 - 0.02, x0 + 0.3, 2.0, D, 0.4 + step * 0.4, 0.44 + step * 0.4, "wood_dark")]
    r.base += bl
    r.collision["Bleachers"] = [W / 2 - 1.8, W / 2, 2.0, D]
    r.base += tube_light(-3.0, D, 5.6, 1.6) + tube_light(3.0, D, 5.6, 1.6)
    r.base += wall_text_board(-6.5, D, 2.45, 1.2, 0.35, ["PLANT ROOM"], board="sign_white", ink="red_paint", size=0.12)
    # The organism has taken the north-east corner; a trail leads from the plant-room door to the middle.
    r.base += growth_spill(-6.5, D - 1.2, 1.5, 600) + growth_spill(-3.5, D - 2.5, 0.8, 620)
    r.base += blood_smear(-6.0, D - 2.0, -1.0, 12.5, 630, n=16, w=0.18)
    r.build()


def veranda_section(name, scene, desc, y_span, door_y, door_open, sign, *, north_end=False, south_end=False,
                    entrance=False, extra=None, seed=0):
    """One third of the CDS west veranda: red-oxide floor, the building's brick wall on the east (door to a room),
    the brick arcade on the west (piers, sill walls), a grass strip outside. The sections join at their ends."""
    D = y_span
    r = Room(name, scene, desc, 4.0, D, 3.4, floor="red_oxide", wall="brick", dado=None, px_per_m=90.0,
             light_power=1.0, south_h=1.0, wall_t=0.3)
    r.no_wall |= {"W"}
    if not north_end:
        r.no_wall.add("N")
    if not south_end:
        r.no_wall.add("S")
    if north_end:
        r.opening("N", 0.0, 1.4, 1.1, 2.4, "window")
    r.opening("E", door_y, 1.8, 0.0, 2.3, "door", frame="wood_dark")
    rng = random.Random(seed)
    # Arcade: brick piers every ~2.75 m with knee-high sill walls between, a lintel and eave strip on top.
    x0, x1 = -2.0 - 0.45, -2.0
    n = max(2, round(D / 2.75))
    piers = []
    for k in range(n + 1):
        y = D * k / n
        piers.append(box(x0, x1, max(-0.3, y - 0.22), min(D + 0.3, y + 0.22), 0.0, 3.0, "brick"))
        piers.append(box(x0 - 0.04, x1 + 0.04, max(-0.3, y - 0.26), min(D + 0.3, y + 0.26), 0.0, 0.25, "coping"))
    gap = None
    if entrance:
        gap = (D / 2 - 1.2, D / 2 + 1.2)
    for k in range(n):
        ya, yb = D * k / n + 0.22, D * (k + 1) / n - 0.22
        if gap and yb > gap[0] and ya < gap[1]:
            if ya < gap[0]:
                piers.append(box(x0 + 0.05, x1 - 0.05, ya, gap[0], 0.0, 0.85, "brick"))
                piers.append(box(x0, x1, ya, gap[0], 0.85, 0.92, "coping"))
            if yb > gap[1]:
                piers.append(box(x0 + 0.05, x1 - 0.05, gap[1], yb, 0.0, 0.85, "brick"))
                piers.append(box(x0, x1, gap[1], yb, 0.85, 0.92, "coping"))
            continue
        piers.append(box(x0 + 0.05, x1 - 0.05, ya, yb, 0.0, 0.85, "brick"))
        piers.append(box(x0, x1, ya, yb, 0.85, 0.92, "coping"))
    piers.append(box(x0 - 0.05, x1 + 0.05, -0.3, D + 0.3, 3.0, 3.25, "brick"))
    piers.append(box(x0 - 0.15, x1 + 0.05, -0.3, D + 0.3, 3.25, 3.35, "coping"))
    r.base += piers
    if gap:
        r.collision["ArcadeA"] = [x0, x1, -0.3, gap[0]]
        r.collision["ArcadeB"] = [x0, x1, gap[1], D + 0.3]
        r.base.append(box(x0 - 0.1, x1 + 0.1, gap[0], gap[1], 0.0, 0.02, "coping"))
    else:
        r.collision["Arcade"] = [x0, x1, -0.3, D + 0.3]
    # Grass strip outside the arcade, with a path at the entrance.
    r.base.append(box(-6.0, x0, -0.3, D + 0.3, -0.12, -0.02, "grass_dark"))
    if gap:
        r.base.append(box(-6.0, x0, gap[0] + 0.2, gap[1] - 0.2, -0.02, -0.005, "concrete"))
    for k in range(int(D / 3)):
        y = rng.uniform(0.5, D - 0.5)
        if gap and gap[0] - 0.8 < y < gap[1] + 0.8:
            continue
        r.base.append(blob(rng.uniform(-5.2, -3.2), y, 0.0, rng.uniform(0.3, 0.6), rng.uniform(0.3, 0.5),
                           rng.uniform(0.25, 0.5), "grass_dark", lump=0.4, seed=seed + 50 + k, subdiv=3))
    # East wall dressing: a wall lamp by the door, a bench, a bin.
    E = 2.0
    r.base += [box(E - 0.12, E, door_y + 1.2, door_y + 1.45, 2.5, 2.75, "white_paint"),
               cbox(E - 0.1, door_y + 1.32, 0.1, 0.18, 2.52, 2.73, "tube_light")]
    # Door leaf: open (swung into the veranda, facing the camera) or shut and chained.
    a, b = door_y - 0.9, door_y + 0.9
    if door_open:
        leaf = [box(E - 0.9, E, b - 0.05, b, 0.0, 2.25, "door_wood"),
                box(E - 0.85, E - 0.05, b - 0.055, b - 0.05, 1.3, 2.1, "glass"),
                box(E - 0.8, E - 0.7, b - 0.07, b - 0.055, 1.0, 1.05, "brass")]
        r.layer("DoorLeaf", leaf, b - 0.05, collide=[E - 0.9, E, b - 0.06, b])
    else:
        r.base += [box(E, E + 0.06, a, b, 0.0, 2.3, "door_wood"),
                   box(E - 0.02, E, door_y - 0.25, door_y + 0.25, 1.0, 1.1, "chrome")]
    # Projecting sign over the door (faces the camera), on a bracket from the wall.
    sx0 = E - 1.1
    sgn = [box(E - 1.15, E, door_y - 1.05, door_y - 1.0, 2.75, 2.8, "metal_dark"),
           box(sx0, E - 0.15, door_y - 1.06, door_y - 1.0, 2.3, 2.72, "sign_green"),
           text(sign, [(sx0 + E - 0.15) / 2, door_y - 1.07, 2.43], 0.13, "sign_white")]
    r.layer("Sign", sgn, door_y - 1.0)
    if extra:
        extra(r)
    r.build()


def verandas():
    # The veranda zone is 82.6 m long (y -850..850 game px) and is built from three 27.5 m sections, north to south.
    def north_extra(r):
        r.base += growth_spill(1.0, 3.0, 0.7, 710)
        r.base += loose_papers(-1.0, 20.0, 720, 5)

    def middle_extra(r):
        r.base += blood_smear(1.6, 23.0, -0.4, 26.5, 730, n=8)

    def south_extra(r):
        r.base += growth_spill(1.5, 13.2, 1.1, 740) + blood_smear(1.7, 12.0, 0.2, 6.0, 750, n=12, w=0.16)
        r.base += [box(-0.6, 0.6, 15.2, 15.25, 0.0, 1.1, "sign_white", rot=[0, 0, 0])]
    veranda_section("cds_veranda_north", "CdsVerandaNorth", "CDS west veranda, north section (canteen door).",
                    27.53, 13.4, True, "CANTEEN", north_end=True, extra=north_extra, seed=700)
    veranda_section("cds_veranda_middle", "CdsVerandaMiddle",
                    "CDS west veranda, middle section (table-tennis door, the arcade entrance from the field).",
                    27.53, 17.9, True, "TABLE TENNIS", entrance=True, extra=middle_extra, seed=760)
    veranda_section("cds_veranda_south", "CdsVerandaSouth", "CDS west veranda, south section (indoor games hall).",
                    27.53, 13.0, False, "INDOOR GAMES", south_end=True, extra=south_extra, seed=780)


def define():
    security_office()
    canteen()
    table_tennis()
    basketball_hall()
    verandas()


def main():
    define()
    if "--list" in sys.argv:
        print("\n".join(ROOMS))
        return
    changed = []
    for aid, r in ROOMS.items():
        if write_config(aid, "interiors", r["scene"], r["desc"], r["params"], px_per_m=r["px_per_m"],
                        samples=r["samples"], layers=r["layers"], collision=r["collision"], sprite_z_index=-10,
                        max_texture_px=16000000):
            changed.append(aid)
    print(f"{len(ROOMS)} room configs; changed: {' '.join(changed) if changed else 'none'}")


if __name__ == "__main__":
    main()

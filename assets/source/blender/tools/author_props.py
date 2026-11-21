"""Writes the Chapter 1 prop configs (assembly generator). Run from anywhere:

    python assets/source/blender/tools/author_props.py            # write / refresh every prop config
    python assets/source/blender/tools/author_props.py --list     # print the asset ids

Then build: python assets/source/blender/build_asset.py <asset_id> [...]
Frame: origin on the ground at the footprint centre, +X right, +Y away from the camera (north), Z up, metres.
Flat ground dressing (blood, growth mats, papers) uses `z_index` -1: drawn under everything that stands.
"""

import math
import random
import sys

sys.dont_write_bytecode = True
from author_lib import (blob, box, cbox, cyl, lathe, leg, mats_for, moved, rotated, rotated_z, text,  # noqa: E402
                        tube, write_config)

PROPS = {}


def prop(asset_id, scene, category, desc, objects, footprint, *, collision_rect=None, px_per_m=150.0,
         samples=192, lights=None, z_index=0, layers=None, collision_rects=None, min_px=0.0, tall=False):
    params = {"mats": mats_for(objects), "objects": objects, "footprint_m": footprint, "lights": lights or [],
              "ceiling_z": None}
    if collision_rects:
        collision = {"enabled": True, "source": "rects_m", "rects_m": collision_rects, "depth_mode": "projected"}
    elif collision_rect:
        collision = {"enabled": True, "source": "rect_m", "rect_m": collision_rect, "depth_mode": "projected"}
    else:
        collision = {"enabled": False}
    # The pipeline frames every asset with a margin of 8 % of its larger extent and requires >= 16 px:
    # small props need a finer render scale. `tall` props (whose height, not footprint, sets the frame) and wide
    # ones keep the base scale.
    # Very small props render at a fixed image width instead (the px/m consistency check loses precision far
    # above ~700 px/m).
    fw, fd = footprint[1] - footprint[0], footprint[3] - footprint[2]
    needed = 0.0 if tall else 260.0 / max(fw, fd, 0.05)
    width_px = None
    if needed > 700.0:
        px_per_m, width_px = None, 320
    else:
        px_per_m = round(max(px_per_m, needed, min_px), 3)
    PROPS[asset_id] = dict(category=category, scene_name=scene, description=desc, params=params,
                           px_per_m=px_per_m, width_px=width_px, samples=samples, collision=collision,
                           z_index=z_index, layers=layers)


def one(parts, bevel=0.005):
    return {"Main": {"parts": parts, "bevel": bevel}}


# --- Furniture pieces (local frames) ------------------------------------------------------------------------------

def monobloc_chair(mat="plastic_red", tilt=10.0):
    """Plastic monobloc chair facing -Y (towards the camera), centred on the origin."""
    parts = [cbox(0, 0, 0.44, 0.42, 0.42, 0.455, mat)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cyl([sx * 0.19, sy * 0.18, 0.43], [sx * 0.215, sy * 0.205, 0.0], 0.022, mat, r2=0.017,
                             sides=10))
    parts.append(box(-0.21, 0.21, 0.18, 0.21, 0.45, 0.86, mat, rot=[-tilt, 0, 0], pivot=[0, 0.2, 0.45]))
    parts.append(box(-0.21, 0.21, 0.175, 0.215, 0.80, 0.86, mat, rot=[-tilt, 0, 0], pivot=[0, 0.2, 0.45]))
    for sx in (-1, 1):
        parts.append(box(sx * 0.215 - 0.02, sx * 0.215 + 0.02, -0.17, 0.2, 0.62, 0.65, mat))
        parts.append(cyl([sx * 0.215, -0.15, 0.455], [sx * 0.215, -0.15, 0.63], 0.016, mat, sides=8))
    return parts


def canteen_table(w=1.5, d=0.75, h=0.75):
    parts = [cbox(0, 0, w, d, h - 0.03, h, "laminate"),
             cbox(0, 0, w - 0.04, d - 0.04, h - 0.07, h - 0.03, "steel_grey")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(leg(sx * (w / 2 - 0.07), sy * (d / 2 - 0.07), 0.0, h - 0.06, 0.022, "steel_grey"))
    parts.append(cbox(0, 0, w - 0.16, 0.03, 0.12, 0.15, "steel_grey"))
    return parts


def table_set(chair_mat="plastic_red", knocked=False, seed=0, extras=()):
    parts = canteen_table()
    spots = [(-0.38, -0.66, 0), (0.38, -0.66, 0), (-0.38, 0.66, 180), (0.38, 0.66, 180)]
    for i, (x, y, rot) in enumerate(spots):
        jitter = ((seed * 7 + i * 13) % 11 - 5) * 1.5
        if knocked and i == 1:
            fallen = rotated(monobloc_chair(chair_mat), [-82, 0, 0], [0, 0.22, 0.0])
            parts += moved(rotated_z(fallen, 20), x + 0.1, y - 0.25, 0.0)
            continue
        parts += moved(rotated_z(monobloc_chair(chair_mat), rot + jitter), x, y + (0.05 if rot == 0 else -0.05))
    return parts + list(extras)


def tea_cup(x, y, z, mat="plastic_white"):
    return [lathe([[0.0, 0.0], [0.028, 0.0], [0.034, 0.07], [0.03, 0.07], [0.0, 0.01]], [x, y], mat, sides=16)]


def plate(x, y, z, mat="aluminium", r=0.12):
    return moved([lathe([[0.0, 0.0], [r * 0.7, 0.0], [r, 0.02], [r * 0.95, 0.022], [0.0, 0.006]], [x, y], mat)],
                 dz=z)


def laptop(x, y, z, open_deg=105):
    base = [box(-0.17, 0.17, -0.12, 0.12, 0.0, 0.018, "metal_dark")]
    lid = rotated([box(-0.17, 0.17, 0.11, 0.122, 0.018, 0.25, "metal_dark"),
                   box(-0.155, 0.155, 0.108, 0.111, 0.03, 0.235, "screen_dark")], [-(open_deg - 90), 0, 0],
                  [0, 0.12, 0.018])
    return moved(base + lid, x, y, z)


def backpack(x, y, z=0.0, mat="fabric_blue", lying=False):
    parts = [blob(0, 0, 0.2, 0.17, 0.11, 0.21, mat, lump=0.12, seed=3, floor=0.0),
             blob(0, -0.1, 0.13, 0.12, 0.05, 0.1, mat, lump=0.1, seed=4, floor=0.0),
             tube([[-0.1, 0.09, 0.05], [-0.12, 0.12, 0.25], [-0.08, 0.1, 0.38]], 0.02, "bag_black"),
             tube([[0.1, 0.09, 0.05], [0.12, 0.12, 0.25], [0.08, 0.1, 0.38]], 0.02, "bag_black")]
    if lying:
        parts = rotated(parts, [-85, 0, 25], [0, 0, 0.0])
        parts = moved(parts, dz=0.12)
    return moved(parts, x, y, z)


# --- Props ------------------------------------------------------------------------------------------------------

def furniture():
    for variant, chair, knocked, extras in (
            ("a", "plastic_red", False, moved(tea_cup(0, 0, 0), -0.3, 0.1, 0.75) + plate(0.35, -0.05, 0.75)),
            ("b", "plastic_green", False, moved(tea_cup(0, 0, 0), 0.4, -0.15, 0.75)),
            ("c", "plastic_red", True, plate(-0.2, 0.0, 0.75) + plate(0.15, 0.1, 0.752))):
        prop(f"canteen_table_set_{variant}", f"CanteenTableSet{variant.upper()}", "furniture",
             "Canteen table (laminate top, steel legs) with four plastic monobloc chairs"
             + (", one knocked over" if knocked else "") + ".",
             one(table_set(chair, knocked, seed=ord(variant), extras=extras), 0.006),
             [-0.8, 0.8, -0.86, 0.86], collision_rect=[-0.8, 0.8, -0.8, 0.8], tall=True)

    # The player's own table at the start: laptop, notebook, backpack on a chair.
    start = table_set("plastic_red", False, seed=9, extras=laptop(-0.25, -0.05, 0.75)
                      + [cbox(0.3, 0.0, 0.21, 0.29, 0.75, 0.765, "paper", rot=[0, 0, 12])]
                      + moved(tea_cup(0, 0, 0), 0.55, 0.15, 0.75))
    start += backpack(0.38, 0.62, 0.45, "fabric_blue")
    prop("canteen_table_start", "CanteenTableStart", "furniture",
         "The player's table: laptop (dead), notebook, cold tea, a backpack on the chair.",
         one(start, 0.006), [-0.8, 0.8, -0.86, 0.86], collision_rect=[-0.8, 0.8, -0.8, 0.8], tall=True)

    stack = []
    for i in range(6):
        stack += moved(monobloc_chair("plastic_red" if i % 3 else "plastic_green"), 0, -0.02 * i, 0.06 * i)
    prop("chair_stack", "ChairStack", "furniture", "Six stacked plastic chairs.", one(stack),
         [-0.25, 0.25, -0.3, 0.25], collision_rect=[-0.25, 0.25, -0.28, 0.22])

    # Table-tennis table: 2.74 x 1.525 m, 0.76 m high, blue with white lines, net across X = 0.
    tt = [cbox(0, 0, 2.74, 1.525, 0.735, 0.76, "tt_blue"),
          box(-1.37, 1.37, -0.7625, -0.7425, 0.7601, 0.7605, "white_paint"),
          box(-1.37, 1.37, 0.7425, 0.7625, 0.7601, 0.7605, "white_paint"),
          box(-1.37, -1.35, -0.7625, 0.7625, 0.7601, 0.7605, "white_paint"),
          box(1.35, 1.37, -0.7625, 0.7625, 0.7601, 0.7605, "white_paint"),
          box(-1.37, 1.37, -0.0015, 0.0015, 0.7601, 0.7605, "white_paint"),
          cbox(0, 0, 0.012, 1.83, 0.76, 0.913, "net"),
          cbox(0, 0, 0.02, 1.83, 0.9, 0.915, "white_paint")]
    for sy in (-1, 1):
        tt.append(cyl([0, sy * 0.915, 0.7], [0, sy * 0.915, 0.92], 0.012, "metal_dark"))
    for sx in (-1, 1):
        tt.append(cbox(sx * 0.9, 0, 0.06, 1.2, 0.62, 0.70, "metal_dark"))
        for sy in (-1, 1):
            tt.append(leg(sx * 0.9, sy * 0.55, 0.06, 0.72, 0.022, "metal_dark"))
            tt.append(cyl([sx * 0.9, sy * 0.55, 0.06], [sx * 0.9, sy * 0.55, 0.0], 0.04, "rubber", sides=12))
    prop("tt_table", "TableTennisTable", "furniture", "Table-tennis table with net, blue top, white lines.",
         one(tt, 0.004), [-1.37, 1.37, -0.77, 0.77], collision_rect=[-1.37, 1.37, -0.76, 0.76])

    lockers = []
    for i in range(3):
        x0 = -0.45 + i * 0.3
        lockers.append(box(x0 + 0.005, x0 + 0.295, -0.22, 0.22, 0.08, 1.85, "steel_grey"))
        door = [box(x0 + 0.01, x0 + 0.29, -0.235, -0.22, 0.1, 1.83, "steel_grey")]
        for k in range(4):
            door.append(box(x0 + 0.08, x0 + 0.22, -0.237, -0.234, 1.55 + k * 0.05, 1.57 + k * 0.05, "metal_dark"))
        door.append(box(x0 + 0.24, x0 + 0.26, -0.25, -0.235, 0.95, 1.05, "chrome"))
        if i == 2:
            door = rotated(door, [0, 0, -70], [x0 + 0.01, -0.235, 0])
        lockers += door
    lockers.append(box(-0.46, 0.46, -0.23, 0.23, 0.0, 0.08, "metal_dark"))
    lockers.append(box(-0.46, 0.46, -0.23, 0.23, 1.85, 1.88, "steel_grey"))
    lockers.append(cbox(0.3, -0.05, 0.22, 0.3, 0.12, 0.17, "fabric_red"))  # a towel inside the open one
    prop("locker_bank", "LockerBank", "furniture", "Three steel lockers; the right door hangs open.",
         one(lockers, 0.003), [-0.46, 0.46, -0.24, 0.23], collision_rect=[-0.46, 0.46, -0.24, 0.23], tall=True)

    bench = [box(-1.0, 1.0, -0.15, 0.15, 0.42, 0.46, "wood")]
    for sx in (-0.85, 0.85):
        bench += [box(sx - 0.03, sx + 0.03, -0.13, 0.13, 0.0, 0.42, "steel_blue")]
    prop("gym_bench", "GymBench", "furniture", "Long wooden bench on blue steel legs.", one(bench),
         [-1.0, 1.0, -0.15, 0.15], collision_rect=[-1.0, 1.0, -0.15, 0.15])

    # Security desk: steel desk, three monitors, logbook, phone, radio, tea.
    desk = [box(-0.7, 0.7, -0.35, 0.35, 0.72, 0.75, "wood"),
            box(0.2, 0.68, -0.33, 0.33, 0.06, 0.72, "steel_green"),
            box(-0.68, -0.6, -0.33, 0.33, 0.0, 0.72, "steel_green"),
            box(-0.6, 0.2, 0.3, 0.33, 0.3, 0.72, "steel_green")]
    for k in range(3):
        desk.append(box(0.25, 0.63, -0.345, -0.33, 0.12 + k * 0.2, 0.3 + k * 0.2, "steel_green"))
        desk.append(box(0.38, 0.5, -0.36, -0.345, 0.2 + k * 0.2, 0.22 + k * 0.2, "chrome"))
    for i, x in enumerate((-0.42, 0.0, 0.42)):
        mon = [box(x - 0.19, x + 0.19, 0.05, 0.3, 0.75, 1.07, "metal_dark"),
               box(x - 0.16, x + 0.16, 0.035, 0.05, 0.78, 1.04, "screen_glow" if i == 1 else "screen_dark")]
        desk += mon
    desk += [box(-0.35, 0.05, -0.28, -0.02, 0.75, 0.775, "paper_old", rot=[0, 0, -6]),
             box(-0.35, -0.15, -0.28, -0.02, 0.775, 0.777, "red_paint", rot=[0, 0, -6]),
             cbox(0.45, -0.2, 0.18, 0.12, 0.75, 0.8, "black_paint"),
             cbox(0.2, -0.18, 0.08, 0.04, 0.75, 0.93, "black_paint"),
             cyl([0.22, -0.18, 0.93], [0.22, -0.18, 1.05], 0.006, "black_paint")]
    desk += moved(tea_cup(0, 0, 0), -0.55, -0.2, 0.75)
    prop("security_desk", "SecurityDesk", "furniture",
         "Security desk: three CCTV monitors (one still glowing), the open logbook, phone, radio, tea.",
         one(desk, 0.004), [-0.7, 0.7, -0.36, 0.35], collision_rect=[-0.7, 0.7, -0.36, 0.35], tall=True)

    chair = [cbox(0, 0, 0.46, 0.46, 0.44, 0.5, "fabric_blue"),
             box(-0.22, 0.22, 0.2, 0.26, 0.5, 0.95, "fabric_blue", rot=[-8, 0, 0], pivot=[0, 0.23, 0.5]),
             cyl([0, 0, 0.1], [0, 0, 0.44], 0.03, "chrome")]
    for k in range(5):
        a = 2 * math.pi * k / 5
        chair.append(tube([[0, 0, 0.1], [0.28 * math.cos(a), 0.28 * math.sin(a), 0.05]], 0.02, "metal_dark"))
        chair.append(cyl([0.28 * math.cos(a), 0.28 * math.sin(a), 0.05], [0.28 * math.cos(a), 0.28 * math.sin(a), 0.0],
                         0.025, "rubber", sides=8))
    prop("office_chair_fallen", "OfficeChairFallen", "furniture", "Office chair tipped on its side.",
         one(moved(rotated(chair, [0, 85, 30], [0, 0, 0]), 0, 0, 0.27)), [-0.5, 0.5, -0.35, 0.35],
         collision_rect=[-0.45, 0.45, -0.3, 0.3])

    cot = [box(-0.95, 0.95, -0.4, 0.4, 0.38, 0.4, "steel_green")]
    for sx in (-0.85, 0.85):
        cot.append(tube([[sx, -0.4, 0.0], [sx, 0.4, 0.38]], 0.015, "steel_green"))
        cot.append(tube([[sx, 0.4, 0.0], [sx, -0.4, 0.38]], 0.015, "steel_green"))
    cot.append(box(-0.92, 0.92, -0.37, 0.37, 0.4, 0.48, "mattress"))
    cot.append(blob(0.1, 0.0, 0.5, 0.6, 0.33, 0.08, "fabric_khaki", lump=0.35, seed=7, floor=0.47))
    cot.append(blob(-0.7, 0.05, 0.52, 0.17, 0.25, 0.06, "paper", lump=0.2, seed=8, floor=0.47))
    cot.append(blob(0.35, -0.15, 0.49, 0.25, 0.12, 0.02, "blood_dry", lump=0.5, seed=21, floor=0.48))
    prop("folding_cot", "FoldingCot", "furniture", "Guard's folding cot: stained mattress, a crumpled blanket.",
         one(cot), [-0.95, 0.95, -0.4, 0.4], collision_rect=[-0.95, 0.95, -0.4, 0.4])

    alm = [box(-0.45, 0.45, -0.25, 0.25, 0.05, 1.9, "steel_grey"),
           box(-0.44, -0.005, -0.265, -0.25, 0.08, 1.87, "steel_grey"),
           box(0.005, 0.44, -0.265, -0.25, 0.08, 1.87, "steel_grey"),
           box(-0.03, -0.01, -0.28, -0.265, 0.95, 1.15, "chrome"),
           box(0.01, 0.03, -0.28, -0.265, 0.95, 1.15, "chrome"),
           box(-0.45, 0.45, -0.25, 0.25, 0.0, 0.05, "metal_dark")]
    prop("steel_almirah", "SteelAlmirah", "furniture", "Grey steel cupboard (almirah), double doors.",
         one(alm, 0.003), [-0.45, 0.45, -0.27, 0.25], collision_rect=[-0.45, 0.45, -0.27, 0.25])

    # Wall items (placed flush against a north wall; footprint is their wall-depth strip).
    kc = [box(-0.3, 0.3, -0.03, 0.0, 0.0, 0.09, "metal_dark"),
          box(-0.3, 0.3, -0.08, 0.0, 1.2, 1.95, "wood_dark"),
          box(-0.27, 0.27, -0.085, -0.08, 1.23, 1.92, "steel_grey")]
    rng = random.Random(4)
    for row in range(4):
        for col in range(5):
            x, z = -0.2 + col * 0.1, 1.83 - row * 0.17
            kc.append(cyl([x, -0.085, z], [x, -0.115, z], 0.005, "brass", sides=6))
            if not (row == 1 and col == 2) and rng.random() < 0.75:
                kc.append(cbox(x, -0.115, 0.02, 0.006, z - 0.09, z - 0.01, "brass" if rng.random() < 0.6 else "chrome"))
                kc.append(cbox(x, -0.118, 0.03, 0.004, z - 0.13, z - 0.08, rng.choice(["red_paint", "yellow", "plastic_blue"])))
    prop("key_cabinet", "KeyCabinet", "furniture", "Wall key cabinet, door open, rows of hooks; one hook empty.",
         one(kc, 0.002), [-0.3, 0.3, -0.12, 0.0], px_per_m=200.0)

    nb = [box(-0.75, 0.75, -0.03, 0.0, 0.0, 0.09, "metal_dark"),
          box(-0.75, 0.75, -0.04, 0.0, 0.95, 1.95, "wood_dark"), box(-0.71, 0.71, -0.045, -0.04, 0.99, 1.91, "cork")]
    rng = random.Random(11)
    for k in range(9):
        x, z = rng.uniform(-0.6, 0.6), rng.uniform(1.1, 1.8)
        w, h = rng.uniform(0.16, 0.26), rng.uniform(0.2, 0.3)
        nb.append(box(x - w / 2, x + w / 2, -0.05, -0.046, z - h / 2, z + h / 2, "paper" if k % 3 else "paper_old",
                      rot=[0, rng.uniform(-6, 6), 0]))
        nb.append(cbox(x, -0.052, 0.012, 0.004, z + h / 2 - 0.015, z + h / 2 - 0.003, "red_paint"))
    nb.append(box(-0.2, 0.25, -0.051, -0.047, 1.35, 1.7, "yellow"))
    prop("notice_board", "NoticeBoard", "furniture", "Cork notice board with pinned papers and a yellow memo.",
         one(nb, 0.002), [-0.75, 0.75, -0.06, 0.0], px_per_m=200.0)

    bp = [box(-0.35, 0.35, -0.03, 0.0, 0.0, 0.09, "metal_dark"),
          cyl([0.2, -0.05, 0.0], [0.2, -0.05, 0.9], 0.025, "steel_grey"),
          box(-0.35, 0.35, -0.2, 0.0, 0.9, 1.9, "steel_grey"),
          box(-0.33, 0.33, -0.205, -0.2, 0.92, 1.88, "steel_grey"),
          box(-0.12, 0.12, -0.215, -0.205, 1.15, 1.45, "metal_dark"),
          box(-0.1, 0.1, -0.218, -0.215, 1.38, 1.43, "screen_glow"),
          box(-0.25, 0.25, -0.212, -0.205, 1.6, 1.78, "yellow"),
          text("DANGER", [0.0, -0.215, 1.66], 0.07, "black_paint"),
          cyl([-0.25, -0.1, 1.9], [-0.25, -0.1, 3.0], 0.03, "steel_grey"),
          cyl([0.0, -0.1, 1.9], [0.0, -0.1, 3.0], 0.03, "steel_grey"),
          cyl([0.25, -0.1, 1.9], [0.25, -0.1, 3.0], 0.03, "steel_grey")]
    for r in range(3):
        for c in range(3):
            bp.append(cbox(-0.06 + c * 0.06, -0.214, 0.04, 0.006, 1.31 - r * 0.06, 1.35 - r * 0.06, "plastic_white"))
    prop("breaker_panel", "BreakerPanel", "furniture",
         "Main breaker panel with a code keypad, DANGER sign and conduit to the ceiling.",
         one(bp, 0.002), [-0.35, 0.35, -0.22, 0.0], px_per_m=200.0)

    # Floor hatch (indoor hall): closed (flush plate) and open (lid up, shaft, ladder, a glow far below).
    hatch_frame = [box(-0.7, 0.7, -0.7, -0.6, 0.0, 0.03, "metal_dark"), box(-0.7, 0.7, 0.6, 0.7, 0.0, 0.03, "metal_dark"),
                   box(-0.7, -0.6, -0.6, 0.6, 0.0, 0.03, "metal_dark"), box(0.6, 0.7, -0.6, 0.6, 0.0, 0.03, "metal_dark")]
    lid = [box(-0.6, 0.6, -0.6, 0.6, 0.0, 0.04, "steel_grey")]
    for k in range(6):
        lid.append(box(-0.55, 0.55, -0.5 + k * 0.2, -0.46 + k * 0.2, 0.04, 0.05, "steel_grey"))
    lid += [box(-0.12, 0.12, -0.5, -0.46, 0.05, 0.1, "chrome")]
    prop("floor_hatch_closed", "FloorHatchClosed", "furniture", "Steel floor hatch, closed, ribbed plate.",
         one(hatch_frame + lid, 0.003), [-0.7, 0.7, -0.7, 0.7], z_index=-1)
    shaft = [box(-0.6, 0.6, -0.6, 0.6, -1.6, -1.55, "growth_glow"),
             box(-0.62, -0.6, -0.6, 0.6, -1.6, 0.0, "concrete"), box(0.6, 0.62, -0.6, 0.6, -1.6, 0.0, "concrete"),
             box(-0.6, 0.6, 0.6, 0.62, -1.6, 0.0, "concrete"), box(-0.6, 0.6, -0.62, -0.6, -1.6, 0.0, "concrete")]
    for k in range(7):
        shaft.append(cyl([-0.25, 0.55, -0.2 - k * 0.2], [0.25, 0.55, -0.2 - k * 0.2], 0.015, "steel_grey", sides=8))
    shaft += [cyl([-0.27, 0.56, -1.6], [-0.27, 0.56, 0.4], 0.02, "steel_grey", sides=8),
              cyl([0.27, 0.56, -1.6], [0.27, 0.56, 0.4], 0.02, "steel_grey", sides=8)]
    open_lid = rotated(lid, [100, 0, 0], [0, 0.6, 0.04])
    prop("floor_hatch_open", "FloorHatchOpen", "furniture",
         "Floor hatch thrown open: lid standing up, ladder down a concrete shaft, faint green glow below.",
         {"Shaft": {"parts": hatch_frame + shaft, "bevel": 0.003}, "Lid": {"parts": open_lid, "bevel": 0.003}},
         [-0.7, 0.7, -0.7, 0.75], z_index=-1,
         layers=[{"name": "LidUp", "objects": ["Lid"], "sort_y_m": 0.7, "z_index": 1}])

    drum = [lathe([[0.0, 0.0], [0.27, 0.0], [0.29, 0.05], [0.29, 0.85], [0.27, 0.9], [0.0, 0.9]], [0, 0], "plastic_blue"),
            cyl([0.1, 0.05, 0.9], [0.1, 0.05, 0.93], 0.04, "plastic_white")]
    prop("water_drum", "WaterDrum", "furniture", "Blue plastic water drum.", one(drum), [-0.29, 0.29, -0.29, 0.29],
         collision_rect=[-0.28, 0.28, -0.28, 0.28])

    crates = []
    for i, (x, y, z) in enumerate(((-0.22, 0, 0), (0.22, 0, 0), (0.0, 0.0, 0.3))):
        crates += [box(x - 0.21, x + 0.21, y - 0.15, y + 0.15, z, z + 0.29, "plastic_red" if i < 2 else "plastic_green")]
        for bx in range(4):
            for by in range(2):
                crates.append(cyl([x - 0.15 + bx * 0.1, y - 0.06 + by * 0.12, z + 0.2],
                                  [x - 0.15 + bx * 0.1, y - 0.06 + by * 0.12, z + 0.33], 0.025, "glass", sides=8))
    prop("crate_stack", "CrateStack", "furniture", "Soft-drink crates with empty bottles.", one(crates),
         [-0.43, 0.43, -0.16, 0.16], collision_rect=[-0.43, 0.43, -0.16, 0.16])

    pot = [lathe([[0.0, 0.0], [0.24, 0.0], [0.28, 0.05], [0.3, 0.3], [0.31, 0.32], [0.29, 0.32], [0.0, 0.05]], [0, 0],
                 "aluminium", sides=28),
           tube([[-0.31, 0, 0.25], [-0.36, 0, 0.27], [-0.31, 0, 0.29]], 0.01, "aluminium"),
           tube([[0.31, 0, 0.25], [0.36, 0, 0.27], [0.31, 0, 0.29]], 0.01, "aluminium")]
    prop("degchi_pot", "DegchiPot", "furniture", "Big aluminium cooking pot (degchi).", one(pot),
         [-0.32, 0.32, -0.32, 0.32], collision_rect=[-0.3, 0.3, -0.3, 0.3])

    bin_ = [lathe([[0.0, 0.0], [0.17, 0.0], [0.2, 0.55], [0.21, 0.56], [0.0, 0.56]], [0, 0], "plastic_green"),
            blob(0.0, 0.0, 0.58, 0.17, 0.17, 0.06, "paper", lump=0.4, seed=5, floor=0.54)]
    prop("trash_bin", "TrashBin", "furniture", "Green plastic bin, overflowing with paper.", one(bin_),
         [-0.21, 0.21, -0.21, 0.21], collision_rect=[-0.2, 0.2, -0.2, 0.2])


def horror():
    # Ground growth mats: low, wet, lumpy organism film with nodules; some glow (bioluminescent).
    for name, seed, sx, sy, glow in (("a", 31, 1.6, 1.1, True), ("b", 32, 2.4, 1.4, True), ("c", 33, 1.1, 0.8, False)):
        rng = random.Random(seed)
        parts = [blob(0, 0, 0.0, sx / 2, sy / 2, 0.05, "growth", lump=0.5, seed=seed, subdiv=4, floor=0.0)]
        for k in range(int(10 * sx)):
            a, r = rng.uniform(0, 6.28), rng.uniform(0.1, 0.42)
            x, y = math.cos(a) * r * sx, math.sin(a) * r * sy
            s = rng.uniform(0.03, 0.09)
            parts.append(blob(x, y, s * 0.6, s, s, s * rng.uniform(0.8, 1.6),
                              "growth_glow" if glow and k % 3 == 0 else "growth", lump=0.3, seed=seed + k,
                              subdiv=2, floor=0.0))
        for k in range(5):
            a = rng.uniform(0, 6.28)
            pts = [[0.0, 0.0, 0.02]]
            for j in range(1, 5):
                pts.append([math.cos(a) * sx * 0.25 * j + rng.uniform(-0.1, 0.1),
                            math.sin(a) * sy * 0.25 * j + rng.uniform(-0.1, 0.1), 0.015])
            parts.append(tube(pts, 0.018, "growth", radii=[0.03, 0.025, 0.018, 0.012, 0.006]))
        prop(f"growth_patch_{name}", f"GrowthPatch{name.upper()}", "horror",
             "Organism growth on the ground: a wet film with nodules and runners" + (", some glowing." if glow else "."),
             one(parts, 0.0), [-sx / 2, sx / 2, -sy / 2, sy / 2], z_index=-1, px_per_m=120.0)

    rng = random.Random(41)
    pods = [blob(0, 0, 0.0, 0.5, 0.4, 0.06, "growth", lump=0.5, seed=41, subdiv=4)]
    for k in range(7):
        a, r = rng.uniform(0, 6.28), rng.uniform(0.0, 0.3)
        x, y = math.cos(a) * r, math.sin(a) * r * 0.8
        h = rng.uniform(0.25, 0.7)
        pods.append(blob(x, y, h * 0.5, 0.08 + h * 0.1, 0.08 + h * 0.1, h * 0.55, "flesh" if k % 2 else "growth",
                         lump=0.2, seed=50 + k, subdiv=3))
        pods.append(blob(x, y - 0.02, h * 0.85, 0.05, 0.05, 0.07, "growth_glow", lump=0.2, seed=60 + k, subdiv=2,
                         floor=0.0))
    prop("growth_pods", "GrowthPods", "horror", "A cluster of pale fleshy pods with glowing tips.", one(pods, 0.0),
         [-0.5, 0.5, -0.4, 0.4], collision_rect=[-0.4, 0.4, -0.3, 0.3], px_per_m=140.0)

    pool = [blob(0, 0, 0.0, 0.55, 0.4, 0.012, "blood", lump=0.45, seed=71, subdiv=4)]
    for k in range(6):
        pool.append(blob(rng.uniform(-0.8, 0.8), rng.uniform(-0.6, 0.6), 0.0, 0.05, 0.05, 0.008, "blood",
                         lump=0.4, seed=72 + k, subdiv=2))
    prop("blood_pool", "BloodPool", "horror", "A pool of blood with spatter.", one(pool, 0.0), [-0.8, 0.8, -0.6, 0.6],
         z_index=-1, px_per_m=120.0)

    trail = []
    for k in range(14):
        x = -1.6 + k * 0.24
        trail.append(blob(x, math.sin(k * 0.7) * 0.08, 0.0, 0.16, 0.08 + 0.03 * math.sin(k), 0.006,
                          "blood_dry" if k % 4 else "blood", lump=0.5, seed=80 + k, subdiv=2))
    for k in range(3):
        trail.append(blob(-1.5 + k * 1.2, 0.12, 0.0, 0.06, 0.03, 0.005, "blood", lump=0.3, seed=95 + k, subdiv=2))
    prop("blood_trail", "BloodTrail", "horror", "A smeared blood trail, something dragged left to right.",
         one(trail, 0.0), [-1.8, 1.8, -0.25, 0.25], z_index=-1, px_per_m=120.0)

    prop("backpack_dropped", "BackpackDropped", "horror", "A student's backpack dropped on the ground.",
         one(backpack(0, 0, 0, "fabric_red", lying=True)), [-0.3, 0.3, -0.25, 0.25], z_index=-1, min_px=600.0)

    papers = []
    rng = random.Random(101)
    for k in range(11):
        x, y = rng.uniform(-0.9, 0.9), rng.uniform(-0.55, 0.55)
        papers.append(box(x - 0.105, x + 0.105, y - 0.148, y + 0.148, 0.0, 0.003, "paper" if k % 4 else "paper_old",
                          rot=[0, 0, rng.uniform(0, 180)]))
    papers.append(blob(0.3, 0.1, 0.0, 0.15, 0.1, 0.006, "blood_dry", lump=0.5, seed=103, subdiv=2))
    prop("papers_scattered", "PapersScattered", "horror", "Loose papers blown across the ground.", one(papers, 0.0),
         [-1.0, 1.0, -0.7, 0.7], z_index=-1, px_per_m=120.0)

    shoe = [blob(0, 0, 0.04, 0.05, 0.13, 0.045, "plastic_white", lump=0.1, seed=110), box(-0.05, 0.05, -0.13, 0.13, 0.0, 0.02, "rubber")]
    prop("shoe_single", "ShoeSingle", "horror", "A single sneaker, laces undone.", one(rotated_z(shoe, 35)),
         [-0.15, 0.15, -0.15, 0.15], z_index=-1)

    umb = rotated([lathe([[0.0, 0.5], [0.15, 0.48], [0.35, 0.42], [0.5, 0.33], [0.52, 0.31], [0.0, 0.31]], [0, 0],
                         "black_paint", sides=8),
                   cyl([0, 0, 0.0], [0, 0, 0.55], 0.008, "chrome", sides=6),
                   tube([[0, 0, 0.0], [0, -0.03, -0.05], [0.04, -0.06, -0.05]], 0.01, "wood_dark")],
                  [72, 0, 30], [0, 0, 0.31])
    prop("umbrella_fallen", "UmbrellaFallen", "horror", "A black umbrella lying open on its side.",
         one(moved(umb, 0, 0, 0.2), 0.0), [-0.55, 0.55, -0.55, 0.55], z_index=-1)

    phone = [box(-0.04, 0.04, -0.08, 0.08, 0.0, 0.01, "metal_dark"),
             box(-0.035, 0.035, -0.072, 0.072, 0.01, 0.011, "screen_glow")]
    prop("phone_dropped", "PhoneDropped", "horror", "A phone face up, its cracked screen still lit.",
         one(rotated_z(phone, 20), 0.0), [-0.1, 0.1, -0.1, 0.1], z_index=-1, px_per_m=200.0)

    # Bicycle on its side.
    bike = []
    for cx in (-0.52, 0.52):
        ring = [[cx + 0.33 * math.cos(2 * math.pi * k / 20), 0.0, 0.33 + 0.33 * math.sin(2 * math.pi * k / 20)]
                for k in range(21)]
        bike.append(tube(ring, 0.018, "rubber", sides=6, cap=False))
        bike.append(cyl([cx, -0.03, 0.33], [cx, 0.03, 0.33], 0.03, "chrome", sides=8))
    bike += [tube([[-0.52, 0, 0.33], [-0.1, 0, 0.33], [0.3, 0, 0.62], [-0.15, 0, 0.62], [-0.1, 0, 0.33]], 0.018,
                  "red_paint"),
             tube([[0.3, 0, 0.62], [0.52, 0, 0.33]], 0.016, "red_paint"),
             tube([[0.3, 0, 0.62], [0.33, 0, 0.75], [0.3, -0.25, 0.78], [0.3, 0.25, 0.78]], 0.012, "chrome"),
             cbox(-0.18, 0, 0.18, 0.08, 0.66, 0.7, "black_paint")]
    bike = rotated(bike, [88, 0, 0], [0, 0, 0])
    prop("bicycle_fallen", "BicycleFallen", "horror", "A bicycle lying on its side.",
         one(moved(rotated_z(bike, 15), 0, 0, 0.04), 0.0), [-0.9, 0.9, -0.5, 0.5], z_index=-1)

    # A shape under a sheet, stained through.
    shape = [blob(0, 0, 0.12, 0.9, 0.32, 0.16, "paper", lump=0.25, seed=120, subdiv=4),
             blob(-0.75, 0.0, 0.14, 0.18, 0.18, 0.13, "paper", lump=0.15, seed=121, subdiv=3),
             blob(0.6, -0.12, 0.08, 0.3, 0.12, 0.08, "paper", lump=0.2, seed=122, subdiv=3),
             blob(0.6, 0.14, 0.08, 0.3, 0.12, 0.08, "paper", lump=0.2, seed=123, subdiv=3),
             blob(0.1, 0.05, 0.24, 0.25, 0.18, 0.03, "blood_dry", lump=0.5, seed=124, subdiv=3, floor=0.15),
             blob(0.2, -0.38, 0.0, 0.35, 0.2, 0.008, "blood", lump=0.5, seed=125, subdiv=3)]
    prop("covered_shape", "CoveredShape", "horror", "Something human-sized under a stained sheet.",
         one(shape, 0.0), [-1.0, 1.0, -0.6, 0.4], collision_rect=[-0.95, 0.95, -0.3, 0.3], px_per_m=130.0)

    cap = [lathe([[0.0, 0.1], [0.1, 0.1], [0.11, 0.05], [0.105, 0.0], [0.0, 0.0]], [0, 0], "fabric_blue", sides=20),
           box(-0.09, 0.09, -0.2, -0.05, 0.0, 0.01, "black_paint"),
           cbox(0.0, -0.105, 0.04, 0.01, 0.05, 0.08, "brass")]
    prop("guard_cap", "GuardCap", "horror", "The guard's peaked cap, dropped.", one(rotated_z(cap, 30), 0.0),
         [-0.15, 0.15, -0.2, 0.12], z_index=-1, px_per_m=200.0)

    torch = [cyl([-0.12, 0, 0.03], [0.1, 0, 0.03], 0.025, "black_paint"),
             cyl([0.1, 0, 0.03], [0.15, 0, 0.03], 0.04, "chrome", r2=0.045)]
    prop("torch_dropped", "TorchDropped", "horror", "A dropped torch, dead.", one(rotated_z(torch, -25), 0.0),
         [-0.15, 0.15, -0.1, 0.1], z_index=-1, px_per_m=200.0)

    # Crows: perched, wings up, wings down (two-frame flap).
    def crow(wing):
        c = [blob(0, 0, 0.12, 0.07, 0.13, 0.07, "black_paint", lump=0.1, seed=130, subdiv=3),
             blob(0, -0.12, 0.19, 0.045, 0.05, 0.045, "black_paint", lump=0.05, seed=131, subdiv=2),
             cyl([0, -0.16, 0.19], [0, -0.22, 0.18], 0.017, "metal_dark", r2=0.002, sides=6),
             box(-0.035, 0.035, 0.1, 0.24, 0.11, 0.13, "black_paint", rot=[-15, 0, 0])]
        if wing is None:
            c += [leg(-0.025, 0.0, 0.0, 0.07, 0.006, "metal_dark", 6), leg(0.025, 0.0, 0.0, 0.07, 0.006, "metal_dark", 6)]
        else:
            for s in (-1, 1):
                c.append(box(0.0, 0.26, -0.06, 0.08, 0.14, 0.15, "black_paint",
                             rot=[0, -s * wing, 0], pivot=[0, 0, 0.14], xf=[{"rot": [0, 0, 0 if s > 0 else 180],
                                                                               "pivot": [0, 0.01, 0.0]}]))
        return c
    prop("crow_perched", "CrowPerched", "horror", "A crow standing.", one(crow(None), 0.0), [-0.1, 0.1, -0.1, 0.1],
         px_per_m=200.0)
    prop("crow_wings_up", "CrowWingsUp", "horror", "A crow in flight, wings up.", one(crow(-35), 0.0),
         [-0.1, 0.1, -0.1, 0.1], px_per_m=200.0)
    prop("crow_wings_down", "CrowWingsDown", "horror", "A crow in flight, wings down.",
         one(crow(30), 0.0), [-0.1, 0.1, -0.1, 0.1], px_per_m=200.0)

    # A chained, padlocked gate chain (draped over the gate leaves' meeting point).
    chain = []
    for k in range(16):
        x = -0.4 + k * 0.053
        z = 1.1 - 0.25 * math.sin(math.pi * k / 15)
        chain.append(cyl([x, -0.02, z], [x + 0.04, -0.02, z - 0.015 * math.cos(math.pi * k / 15)], 0.009, "chrome",
                         sides=6))
    for k in range(9):
        z = 0.7 - k * 0.08
        chain.append(cyl([0.38 + 0.01 * (k % 2), -0.02, z], [0.38 - 0.01 * (k % 2), -0.02, z - 0.07], 0.009, "chrome",
                         sides=6))
    chain.append(cyl([0.3, -0.02, 0.0], [0.42, -0.02, 0.01], 0.009, "chrome", sides=6))
    chain += [box(-0.04, 0.04, -0.04, -0.01, 0.72, 0.8, "brass"),
              tube([[-0.025, -0.025, 0.8], [-0.025, -0.025, 0.84], [0.025, -0.025, 0.84], [0.025, -0.025, 0.8]], 0.007,
                   "chrome", cap=False)]
    prop("gate_chain", "GateChain", "horror", "Heavy chain and padlock across the gate.", one(chain, 0.0),
         [-0.45, 0.45, -0.05, 0.02], px_per_m=200.0)

    # Hurricane lantern (the canteen's load-shedding lamp) on the counter / in hand pickups.
    lamp = [lathe([[0.0, 0.0], [0.08, 0.0], [0.09, 0.03], [0.085, 0.07], [0.05, 0.08], [0.0, 0.08]], [0, 0], "red_paint"),
            lathe([[0.0, 0.08], [0.045, 0.08], [0.065, 0.15], [0.06, 0.2], [0.035, 0.24], [0.0, 0.24]], [0, 0], "glass"),
            lathe([[0.0, 0.24], [0.07, 0.24], [0.05, 0.28], [0.0, 0.3]], [0, 0], "red_paint"),
            tube([[-0.07, 0, 0.05], [-0.075, 0, 0.27], [0.0, 0, 0.34], [0.075, 0, 0.27], [0.07, 0, 0.05]], 0.005,
                 "metal_dark", cap=False)]
    prop("hurricane_lantern", "HurricaneLantern", "furniture", "Red hurricane (kerosene) lantern.", one(lamp, 0.0),
         [-0.1, 0.1, -0.1, 0.1], px_per_m=220.0)

    oil = [lathe([[0.0, 0.0], [0.08, 0.0], [0.085, 0.2], [0.03, 0.26], [0.03, 0.3], [0.0, 0.3]], [0, 0], "yellow"),
           cbox(0.0, -0.075, 0.08, 0.02, 0.07, 0.16, "paper")]
    prop("oil_bottle", "OilBottle", "furniture", "A bottle of lamp kerosene.", one(oil, 0.0), [-0.09, 0.09, -0.09, 0.09],
         px_per_m=220.0)

    key = [cyl([-0.04, 0, 0.005], [0.04, 0, 0.005], 0.004, "brass", sides=6),
           lathe([[0.0, 0.0], [0.022, 0.0], [0.022, 0.006], [0.0, 0.006]], [-0.06, 0], "brass", sides=14),
           cbox(0.0, 0.0, 0.03, 0.04, 0.0, 0.003, "red_paint")]
    prop("master_key", "MasterKey", "furniture", "Brass master key on a red tag.", one(rotated_z(key, 25), 0.0),
         [-0.09, 0.09, -0.05, 0.05], px_per_m=260.0, z_index=-1)


def define():
    furniture()
    horror()


def main():
    define()
    if "--list" in sys.argv:
        print("\n".join(PROPS))
        return
    changed = []
    for aid, p in PROPS.items():
        if write_config(aid, p["category"], p["scene_name"], p["description"], p["params"], px_per_m=p["px_per_m"],
                        samples=p["samples"], layers=p["layers"], collision=p["collision"], z_index=p["z_index"],
                        width_px=p["width_px"]):
            changed.append(aid)
    print(f"{len(PROPS)} prop configs; changed: {' '.join(changed) if changed else 'none'}")


if __name__ == "__main__":
    main()

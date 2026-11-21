"""The Night Guard (Docs/GAME_DESIGN.md section 5): the campus security guard, still in uniform, now a host.

    "F:\\bbbb\\blender.exe" --background --factory-startup --python assets/source/blender/characters/night_guard.py

A variant of player_character.py (same body, rig, camera, light, grounding and stride measurement), so the guard
shares the player's scale, feet anchor and eight facings exactly. Differences:
- Look: khaki uniform shirt, dark brown trousers, black boots, a dark peaked cap, grey-pale skin, milky eyes.
- Posture: hunched, head lolling to one side; the walk drags the right leg; the run lurches forward with the
  arms reaching out in front.
- Cycles: idle (swaying, a head twitch), walk (patrol, 1.3 m/s) and run (chase, 4.2 m/s: slower than the player's
  sprint, so a sprinting player can break away while their stamina lasts).

Writes assets/sprites/characters/night_guard_<cycle>.png, scenes/creatures/night_guard_frames.tres and
assets/source/blender/characters/night_guard.render.json (+ .blend).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
SOURCE = (HERE / "player_character.py").read_text(encoding="utf-8")
# Load the player generator without running it (its last line calls main()).
ns = {"__file__": str(HERE / "player_character.py"), "__name__": "player_character_variant"}
body, tail = SOURCE.rstrip().rsplit("\n", 1)
assert tail.strip() == "main()", "player_character.py must end with main()"
exec(compile(body, str(HERE / "player_character.py"), "exec"), ns)

ROOT = ns["ROOT"]
ns["BLEND_PATH"] = HERE / "night_guard.blend"
ns["RECORD_PATH"] = HERE / "night_guard.render.json"
ns["FRAMES_DIR"] = ns["C"].LOG_DIR / "night_guard_frames"
ns["SHEET_REL"] = "assets/sprites/characters/night_guard_{cycle}.png"
ns["OLD_SHEET_REL"] = "assets/sprites/characters/night_guard_unused_sheet.png"
ns["FRAMES_TRES_REL"] = "scenes/creatures/night_guard_frames.tres"
(ROOT / "scenes/creatures").mkdir(parents=True, exist_ok=True)
ns["SAMPLES"] = 96
ns["TARGET_SPEED_M_S"] = {"walk": 42.0 / 32.0, "run": 134.0 / 32.0}

# Linear colours.
ns["SKIN"] = (0.30, 0.29, 0.25)           # grey-white, bloodless
ns["HAIR"] = (0.02, 0.02, 0.02)
ns["JACKET"] = (0.20, 0.17, 0.095)        # khaki uniform shirt
ns["JACKET_TRIM"] = (0.13, 0.11, 0.06)
ns["SHIRT"] = (0.17, 0.145, 0.08)
ns["TROUSERS"] = (0.045, 0.035, 0.025)    # dark brown
ns["SHOE"] = (0.015, 0.015, 0.015)        # black boots
ns["SOLE"] = (0.03, 0.03, 0.03)
ns["SHOE_ACCENT"] = (0.01, 0.01, 0.01)
ns["EYE"] = (0.55, 0.57, 0.5)             # milky

side = ns["side"]
_build_face_details = ns["build_face_details"]


def build_face_details(coll):
    """Eyes and brows, plus the guard's peaked cap (follows the head bone, drawn with the dark hair material)."""
    objs = _build_face_details(coll)
    bm = bmesh.new()
    # Crown: a short cylinder slightly wider at the top, tilted back a little.
    bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.104, radius2=0.112, depth=0.075)
    for v in bm.verts:
        v.co.z += 1.765
        v.co.y += 0.012
    # Brim: a short, narrow peak at the front (a wide brim hides the whole face from the 40 deg camera).
    brim = bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.085, radius2=0.085, depth=0.008)
    for v in brim["verts"]:
        v.co.z += 1.74
        v.co.y = min(v.co.y, 0.0) * 0.55 - 0.075
        v.co.x *= 0.95
    mesh = bpy.data.meshes.new("CapMesh")
    bm.to_mesh(mesh)
    bm.free()
    cap = bpy.data.objects.new("Cap", mesh)
    navy = bpy.data.materials.new("CapNavy")
    navy.use_nodes = True
    bsdf = navy.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.025, 0.035, 0.07, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    mesh.materials.append(navy)    # slot 0; main() appends the hair material after it, unused
    coll.objects.link(cap)
    with bpy.context.temp_override(object=cap, active_object=cap, selected_objects=[cap],
                                   selected_editable_objects=[cap]):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for p in cap.data.polygons:
        p.use_smooth = True
    objs.append(cap)
    return objs


ns["build_face_details"] = build_face_details

swing = ns["swing"]
pose_walk, pose_idle, pose_run = ns["pose_walk"], ns["pose_idle"], ns["pose_run"]


def add(arm, signs, name, deg, axis="x"):
    pb = arm.pose.bones[name]
    if axis == "x":
        pb.rotation_euler.x += signs[name] * math.radians(deg)
    else:
        pb.rotation_euler.y += math.radians(deg)


def hunch(arm, signs, lean=1.0):
    add(arm, signs, "spine", 12.0 * lean)
    add(arm, signs, "chest", 8.0 * lean)
    add(arm, signs, "neck", 6.0 * lean)
    add(arm, signs, "head", 16.0, axis="y")      # head lolls to one side


def pose_idle_g(arm, signs, phase):
    pose_idle(arm, signs, phase)
    t = 2 * math.pi * phase
    hunch(arm, signs)
    arm.pose.bones["pelvis"].location.x = 0.02 * math.sin(t)          # slow sway
    add(arm, signs, "head", 7.0 * max(0.0, math.sin(t * 2.0)) ** 6, axis="y")   # a twitch
    for n in ("L", "R"):
        swing(arm, signs, f"upper_arm.{n}", 4.0)
        swing(arm, signs, f"forearm.{n}", 3.0)


def pose_walk_g(arm, signs, phase):
    pose_walk(arm, signs, phase)
    t = 2 * math.pi * phase
    hunch(arm, signs)
    # The right leg drags: a shorter swing and almost no knee bend.
    swing(arm, signs, "thigh.R", 12.0 * math.sin(t + math.pi))
    swing(arm, signs, "shin.R", -(3.0 + 10.0 * max(0.0, math.cos(t + math.pi))))
    # Arms hang, barely swinging.
    for n, off in (("L", 0.0), ("R", math.pi)):
        swing(arm, signs, f"upper_arm.{n}", -5.0 * math.sin(t + off) + 3.0)
        swing(arm, signs, f"forearm.{n}", 4.0)
    arm.pose.bones["pelvis"].rotation_euler.y += math.radians(4.0) * math.sin(t)


def pose_run_g(arm, signs, phase):
    pose_run(arm, signs, phase)
    t = 2 * math.pi * phase
    hunch(arm, signs, 1.4)
    add(arm, signs, "neck", -16.0)             # head up, looking ahead
    for n, off in (("L", 0.0), ("R", math.pi)):
        swing(arm, signs, f"upper_arm.{n}", -62.0 + 8.0 * math.sin(t + off))   # reaching forward
        swing(arm, signs, f"forearm.{n}", 18.0)


ns["CYCLES"] = (("idle", 1, 8, pose_idle_g), ("walk", 101, 8, pose_walk_g), ("run", 201, 8, pose_run_g))

ns["main"]()

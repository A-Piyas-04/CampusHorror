"""Player character: modelled, rigged and animated in Blender, rendered to a 2.5D sprite sheet.

    "F:\\bbbb\\blender.exe" --background --factory-startup --python assets/source/blender/characters/player_character.py

PROVISIONAL neutral university-student look (open overshirt over a plain shirt, chinos, sneakers, short hair).
Not character canon; change the constants below and re-run.

Pipeline:
1. Model: one connected body mesh (skin modifier over a joint graph + subdivision; jaw, nose, ears, brows,
   eyes), fitted clothing meshes (overshirt with open front and collar, chinos, sneakers) and a hair cap.
   Clothing colours come from per-vertex colour masks painted in the rest pose, so they follow the deformation.
2. Rig: armature (root, pelvis, spine, chest, neck, head, arms, legs, feet). The body is skinned with Blender's
   automatic (bone heat) weights; the clothing copies the body's weights from the nearest body vertices; hair,
   eyes and brows follow the head bone.
3. Animation: one action `PlayerCycles` with an 8-frame idle (breathing) at frames 1-8 and an 8-frame walk
   at frames 101-108, both exact loops (phase i / 8). Every frame is grounded: the pelvis is moved so the lowest
   evaluated shoe vertex is exactly at z = 0 (no floating, no penetration).
4. Render: the shared pipeline camera (orthographic 40 deg / azimuth 0) and lights (pipeline/rig.py). The
   figure turns for the four facings; camera, sun and frame bounds stay fixed, so scale and the feet anchor
   are identical in every cell.

Writes:
- assets/source/blender/characters/player_character.blend (model, rig, action, camera, lights)
- assets/sprites/characters/player_character_sheet.png (+ .import with mipmaps, written before the render)
- scenes/player/player_character_frames.tres (SpriteFrames: idle_/walk_ down/up/left/right)
- assets/source/blender/characters/player_character.render.json (record: cells, origin pixel, timing, ...)
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, kdtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import conventions as C  # noqa: E402
from pipeline import rig  # noqa: E402

ROOT = C.PROJECT_ROOT
HERE = Path(__file__).resolve().parent
BLEND_PATH = HERE / "player_character.blend"
RECORD_PATH = HERE / "player_character.render.json"
FRAMES_DIR = C.LOG_DIR / "player_character_frames"
SHEET_REL = "assets/sprites/characters/player_character_sheet.png"
FRAMES_TRES_REL = "scenes/player/player_character_frames.tres"

PX_PER_M = 96.0                  # drawn at 32 / 96 in Godot (3x supersampled, mipmapped)
SAMPLES = 96
FACINGS = (("down", 0.0), ("up", 180.0), ("left", -90.0), ("right", 90.0))
IDLE_FRAMES = 8
WALK_FRAMES = 8
IDLE_FPS = 3.0                   # one breath in 2.7 s
WALK_FPS = 12.0                  # 1.5 strides per second
IDLE_START = 1
WALK_START = 101
FRAME_BOUNDS = [Vector((x, y, z)) for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (0.0, 1.86)]

# Linear base colours.
SKIN = (0.32, 0.175, 0.105)
HAIR = (0.016, 0.011, 0.008)
JACKET = (0.045, 0.075, 0.12)        # muted navy overshirt
JACKET_TRIM = (0.03, 0.05, 0.08)
SHIRT = (0.68, 0.67, 0.62)           # off-white inner shirt
TROUSERS = (0.29, 0.25, 0.18)        # beige-grey chinos
SHOE = (0.62, 0.62, 0.6)
SOLE = (0.85, 0.84, 0.8)
SHOE_ACCENT = (0.08, 0.09, 0.1)
EYE = (0.02, 0.015, 0.012)

# --- Rest skeleton (metres; Z up; the figure faces -Y; +X is the figure's left) ----------------------------

def side(p, s):
    return (p[0] * s, p[1], p[2])


BONES = {
    # name: (head, tail, parent)
    "root": ((0, 0, 0), (0, 0.25, 0), None),
    "pelvis": ((0, 0, 0.95), (0, 0, 1.10), "root"),
    "spine": ((0, 0, 1.10), (0, 0.005, 1.28), "pelvis"),
    "chest": ((0, 0.005, 1.28), (0, 0.01, 1.45), "spine"),
    "neck": ((0, 0.01, 1.45), (0, 0.005, 1.56), "chest"),
    "head": ((0, 0.005, 1.56), (0, 0.005, 1.80), "neck"),
}
for _s, _n in ((1, "L"), (-1, "R")):
    BONES[f"upper_arm.{_n}"] = (side((0.175, 0.01, 1.42), _s), side((0.235, 0.02, 1.155), _s), "chest")
    BONES[f"forearm.{_n}"] = (side((0.235, 0.02, 1.155), _s), side((0.265, -0.005, 0.925), _s), f"upper_arm.{_n}")
    BONES[f"hand.{_n}"] = (side((0.265, -0.005, 0.925), _s), side((0.275, -0.02, 0.83), _s), f"forearm.{_n}")
    BONES[f"thigh.{_n}"] = (side((0.095, 0, 0.95), _s), side((0.1, -0.012, 0.52), _s), "pelvis")
    BONES[f"shin.{_n}"] = (side((0.1, -0.012, 0.52), _s), side((0.1, 0.02, 0.095), _s), f"thigh.{_n}")
    BONES[f"foot.{_n}"] = (side((0.1, 0.02, 0.095), _s), side((0.1, -0.11, 0.03), _s), f"shin.{_n}")


def skin_mesh(coll, name, verts, edges, radii, subsurf=2):
    """Connected mesh from a joint graph: skin modifier + subdivision, applied."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([Vector(v) for v in verts], edges, [])
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    skin = obj.modifiers.new("Skin", "SKIN")
    skin.use_smooth_shade = True
    skin.branch_smoothing = 0.6
    for i, r in enumerate(radii):
        sv = mesh.skin_vertices[0].data[i]
        sv.radius = r
        sv.use_root = i == 0
    sub = obj.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = subsurf
    sub.render_levels = subsurf
    _apply_modifiers(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def _apply_modifiers(obj):
    view_layer = bpy.context.view_layer
    view_layer.objects.active = obj
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)


class Graph:
    def __init__(self):
        self.verts, self.radii, self.edges, self.ids = [], [], [], {}

    def v(self, key, pos, radius):
        self.ids[key] = len(self.verts)
        self.verts.append(pos)
        self.radii.append(radius)
        return key

    def chain(self, *keys):
        for a, b in zip(keys, keys[1:]):
            self.edges.append((self.ids[a], self.ids[b]))


def build_body(coll):
    g = Graph()
    g.v("pelvis", (0, 0.0, 0.97), (0.135, 0.092))
    g.v("waist", (0, 0.004, 1.12), (0.118, 0.082))
    g.v("chest", (0, 0.008, 1.30), (0.142, 0.092))
    g.v("upper", (0, 0.01, 1.41), (0.13, 0.082))
    g.v("neck", (0, 0.012, 1.49), (0.048, 0.048))
    g.v("neck_top", (0, 0.008, 1.545), (0.05, 0.052))
    g.v("jaw", (0, -0.012, 1.585), (0.066, 0.072))
    g.v("skull", (0, 0.0, 1.665), (0.087, 0.1))
    g.v("crown", (0, 0.006, 1.745), (0.076, 0.088))
    g.v("top", (0, 0.008, 1.79), (0.035, 0.035))
    g.chain("pelvis", "waist", "chest", "upper", "neck", "neck_top", "jaw", "skull", "crown", "top")
    g.v("nose", (0, -0.1, 1.652), (0.013, 0.013))
    g.chain("skull", "nose")
    for s, n in ((1, "L"), (-1, "R")):
        g.v(f"ear{n}", side((0.09, 0.008, 1.66), s), (0.012, 0.022))
        g.chain("skull", f"ear{n}")
        g.v(f"shoulder{n}", side((0.17, 0.01, 1.415), s), (0.058, 0.055))
        g.v(f"elbow{n}", side((0.235, 0.02, 1.155), s), (0.038, 0.038))
        g.v(f"wrist{n}", side((0.265, -0.005, 0.925), s), (0.028, 0.025))
        g.v(f"palm{n}", side((0.27, -0.012, 0.875), s), (0.034, 0.018))
        g.v(f"fingers{n}", side((0.274, -0.02, 0.83), s), (0.026, 0.014))
        g.chain("upper", f"shoulder{n}", f"elbow{n}", f"wrist{n}", f"palm{n}", f"fingers{n}")
        g.v(f"hip{n}", side((0.092, 0, 0.93), s), (0.078, 0.08))
        g.v(f"knee{n}", side((0.1, -0.012, 0.52), s), (0.05, 0.052))
        g.v(f"ankle{n}", side((0.1, 0.02, 0.095), s), (0.034, 0.036))
        g.v(f"toe{n}", side((0.1, -0.1, 0.035), s), (0.035, 0.022))
        g.chain("pelvis", f"hip{n}", f"knee{n}", f"ankle{n}", f"toe{n}")
    return skin_mesh(coll, "Body", g.verts, g.edges, g.radii)


def build_jacket(coll):
    g = Graph()
    g.v("hem", (0, 0.0, 0.83), (0.15, 0.104))
    g.v("pelvis", (0, 0.0, 0.97), (0.148, 0.104))
    g.v("waist", (0, 0.004, 1.12), (0.135, 0.098))
    g.v("chest", (0, 0.008, 1.30), (0.16, 0.106))
    g.v("upper", (0, 0.01, 1.41), (0.148, 0.097))
    g.v("collar", (0, 0.016, 1.49), (0.068, 0.066))
    g.chain("hem", "pelvis", "waist", "chest", "upper", "collar")
    for s, n in ((1, "L"), (-1, "R")):
        g.v(f"shoulder{n}", side((0.172, 0.01, 1.415), s), (0.07, 0.066))
        g.v(f"elbow{n}", side((0.235, 0.02, 1.155), s), (0.05, 0.05))
        g.v(f"cuff{n}", side((0.262, -0.002, 0.95), s), (0.04, 0.038))
        g.chain("upper", f"shoulder{n}", f"elbow{n}", f"cuff{n}")
    obj = skin_mesh(coll, "Overshirt", g.verts, g.edges, g.radii)

    def colour(p, n):
        front = p.y < -0.02
        placket = abs(p.x) < 0.035 + max(0.0, p.z - 1.3) * 0.25
        if front and placket and 0.86 < p.z < 1.47 and abs(p.x) < 0.12:
            return SHIRT if abs(p.x) > 0.008 or p.z > 1.38 else (0.55, 0.54, 0.5)
        if p.z > 1.465 or p.z < 0.855 or (abs(p.x) > 0.2 and p.z < 0.99):
            return JACKET_TRIM
        return JACKET
    paint(obj, colour)
    return obj


def build_trousers(coll):
    g = Graph()
    g.v("waist", (0, 0.0, 1.0), (0.142, 0.1))
    for s, n in ((1, "L"), (-1, "R")):
        g.v(f"hip{n}", side((0.093, 0, 0.92), s), (0.088, 0.088))
        g.v(f"knee{n}", side((0.1, -0.012, 0.52), s), (0.06, 0.062))
        g.v(f"hem{n}", side((0.1, 0.018, 0.13), s), (0.052, 0.054))
        g.chain("waist", f"hip{n}", f"knee{n}", f"hem{n}")
    obj = skin_mesh(coll, "Chinos", g.verts, g.edges, g.radii)
    paint(obj, lambda p, n: (0.2, 0.17, 0.12) if p.z > 0.975 else TROUSERS)
    return obj


def build_shoes(coll):
    objs = []
    for s, n in ((1, "L"), (-1, "R")):
        g = Graph()
        g.v("collar", side((0.1, 0.02, 0.105), s), (0.044, 0.046))
        g.v("instep", side((0.1, -0.035, 0.055), s), (0.05, 0.046))
        g.v("toe", side((0.1, -0.12, 0.04), s), (0.043, 0.034))
        g.v("heel", side((0.1, 0.06, 0.048), s), (0.042, 0.042))
        g.chain("collar", "instep", "toe")
        g.chain("collar", "heel")
        obj = skin_mesh(coll, f"Sneaker.{n}", g.verts, g.edges, g.radii)

        def colour(p, nrm):
            if p.z < 0.022:
                return SOLE
            if p.z < 0.034:
                return SHOE_ACCENT if abs(p.y + 0.03) < 0.06 else SOLE
            return SHOE
        paint(obj, colour)
        objs.append(obj)
    return objs


def build_hair(coll):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=24, radius=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Hair"
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    centre = Vector((0, 0.008, 1.678))
    scale = Vector((0.094, 0.106, 0.11))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    kill = []
    for v in bm.verts:
        p = Vector((v.co.x * scale.x, v.co.y * scale.y, v.co.z * scale.z)) + centre
        face = p.y < centre.y - 0.035 and p.z < 1.725 - 0.02 * abs(p.x) / 0.1
        below = p.z < (1.615 if p.y > 0.03 else 1.66)
        if face or below:
            kill.append(v)
        else:
            # a little volume on top and at the back, a short fringe
            lift = 0.006 * max(0.0, (p.z - 1.7) / 0.09) + 0.004 * max(0.0, p.y / 0.11)
            v.co = p + (p - centre).normalized() * lift
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    sol = obj.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.012
    sol.offset = 1.0
    sub = obj.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    _apply_modifiers(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def build_face_details(coll):
    objs = []
    for s, n in ((1, "L"), (-1, "R")):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.011,
                                             location=side((0.031, -0.083, 1.685), s))
        eye = bpy.context.active_object
        eye.name = f"Eye.{n}"
        eye.scale = (1.0, 0.6, 0.8)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=side((0.033, -0.088, 1.708), s))
        brow = bpy.context.active_object
        brow.name = f"Brow.{n}"
        brow.scale = (0.028, 0.008, 0.006)
        brow.rotation_euler = (0, s * math.radians(-8), 0)
        for o in (eye, brow):
            for c in list(o.users_collection):
                c.objects.unlink(o)
            coll.objects.link(o)
            bpy.context.view_layer.objects.active = o
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            objs.append(o)
    return objs


def paint(obj, fn):
    attr = obj.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for v in obj.data.vertices:
        c = fn(v.co, v.normal)
        attr.data[v.index].color = (*c, 1.0)


# --- Materials -------------------------------------------------------------------------------------------

def material(name, color=None, roughness=0.7, bump=0.0, bump_scale=200.0, sheen=0.0):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    if color is None:
        attr = nodes.new("ShaderNodeAttribute")
        attr.attribute_name = "Col"
        links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    if sheen:
        bsdf.inputs["Sheen Weight"].default_value = sheen
    if bump:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = bump_scale
        noise.inputs["Detail"].default_value = 4.0
        bmp = nodes.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump
        bmp.inputs["Distance"].default_value = 0.002
        links.new(noise.outputs["Fac"], bmp.inputs["Height"])
        links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# --- Rig -------------------------------------------------------------------------------------------------

def build_armature(coll):
    data = bpy.data.armatures.new("PlayerRig")
    arm = bpy.data.objects.new("PlayerRig", data)
    coll.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (head, tail, parent) in BONES.items():
        eb = data.edit_bones.new(name)
        eb.head, eb.tail = Vector(head), Vector(tail)
        eb.align_roll(Vector((0, -1, 0)) if abs(eb.vector.normalized().y) < 0.9 else Vector((0, 0, 1)))
        if parent:
            eb.parent = data.edit_bones[parent]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def skin_to_rig(arm, body, followers, head_parts):
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (arm, body))
    bpy.context.view_layer.objects.active = arm
    with bpy.context.temp_override(active_object=arm, object=arm, selected_objects=[body, arm],
                                   selected_editable_objects=[body, arm]):
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    names = [b.name for b in arm.data.bones]
    weights = [dict() for _ in body.data.vertices]
    group_names = {g.index: g.name for g in body.vertex_groups}
    for v in body.data.vertices:
        for ge in v.groups:
            if ge.weight > 1e-4:
                weights[v.index][group_names[ge.group]] = ge.weight
    unweighted = sum(1 for w in weights if not w)
    tree = kdtree.KDTree(len(body.data.vertices))
    for v in body.data.vertices:
        tree.insert(v.co, v.index)
    tree.balance()
    for obj in followers:
        groups = {n: obj.vertex_groups.new(name=n) for n in names}
        for v in obj.data.vertices:
            acc = {}
            for co, idx, dist in tree.find_n(v.co, 6):
                w = 1.0 / (dist + 0.004) ** 2
                for g, gw in weights[idx].items():
                    acc[g] = acc.get(g, 0.0) + w * gw
            total = sum(acc.values()) or 1.0
            for g, gw in acc.items():
                groups[g].add([v.index], gw / total, "REPLACE")
        _attach(obj, arm)
    for obj in head_parts:
        obj.vertex_groups.new(name="head").add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
        _attach(obj, arm)
    _hide_covered_skin(body)
    return unweighted


def _hide_covered_skin(body):
    """Delete the body surface that the clothes cover (after skinning, so the weights stay): only the neck,
    head and hands remain, so skin can never poke through the overshirt or chinos."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    def keep(p):
        neck = p.z >= 1.44 and abs(p.x) < 0.06
        head = p.z >= 1.52
        hand = abs(p.x) > 0.2 and p.z < 0.965
        return neck or head or hand
    kill = [v for v in bm.verts if not keep(v.co)]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()


def _attach(obj, arm):
    obj.parent = arm
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm


def calibrate(arm):
    """Sign per limb bone so that +angle about the bone's local X swings its tail forward (-Y)."""
    signs = {}
    for name in BONES:
        if name.split(".")[0] not in ("upper_arm", "forearm", "hand", "thigh", "shin", "foot", "spine", "chest", "neck", "head"):
            continue
        pb = arm.pose.bones[name]
        bpy.context.view_layer.update()
        before = (arm.matrix_world @ pb.tail).y
        pb.rotation_euler.x = math.radians(10)
        bpy.context.view_layer.update()
        after = (arm.matrix_world @ pb.tail).y
        pb.rotation_euler.x = 0.0
        signs[name] = 1.0 if after < before else -1.0
    bpy.context.view_layer.update()
    return signs


# --- Animation -------------------------------------------------------------------------------------------

def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)


def swing(arm, signs, name, deg):
    arm.pose.bones[name].rotation_euler.x = signs[name] * math.radians(deg)


def pose_walk(arm, signs, phase):
    t = 2 * math.pi * phase
    for s, n, off in ((1, "L", 0.0), (-1, "R", math.pi)):
        a = t + off
        thigh = 21.0 * math.sin(a)
        knee = 4.0 + 40.0 * max(0.0, math.cos(a)) ** 1.4       # bends while the leg swings forward
        swing(arm, signs, f"thigh.{n}", thigh)
        swing(arm, signs, f"shin.{n}", -knee)
        toe_off = 16.0 * max(0.0, -math.sin(a)) * max(0.0, -math.cos(a)) * 2.0
        lift = 8.0 * max(0.0, math.cos(a))
        swing(arm, signs, f"foot.{n}", -(thigh - knee) - toe_off + lift)
        arm_swing = -17.0 * math.sin(a)
        swing(arm, signs, f"upper_arm.{n}", arm_swing)
        swing(arm, signs, f"forearm.{n}", 10.0 + 9.0 * max(0.0, math.sin(-a)))
        arm.pose.bones[f"upper_arm.{n}"].rotation_euler.y = s * math.radians(2.0)
    pelvis = arm.pose.bones["pelvis"]
    pelvis.location.x = -0.012 * math.cos(t)                      # weight over the stance leg
    pelvis.rotation_euler.y = math.radians(3.0) * math.sin(t)     # pelvis twist with the swinging leg
    arm.pose.bones["chest"].rotation_euler.y = -math.radians(4.0) * math.sin(t)
    arm.pose.bones["neck"].rotation_euler.y = math.radians(1.0) * math.sin(t)
    swing(arm, signs, "spine", 3.0)                               # slight forward lean


def pose_idle(arm, signs, phase):
    t = 2 * math.pi * phase
    breath = math.sin(t)
    swing(arm, signs, "chest", -1.0 * breath)
    swing(arm, signs, "head", 0.7 * breath)
    for s, n in ((1, "L"), (-1, "R")):
        swing(arm, signs, f"upper_arm.{n}", 1.5 + 0.8 * breath)
        swing(arm, signs, f"forearm.{n}", 8.0)
        arm.pose.bones[f"upper_arm.{n}"].rotation_euler.y = s * math.radians(3.0 + 0.6 * breath)
        swing(arm, signs, f"thigh.{n}", 0.0)
    arm.pose.bones["pelvis"].location.x = 0.004 * math.sin(t)


def ground(arm, shoes):
    """Move the pelvis so the lowest evaluated shoe vertex sits exactly on z = 0."""
    deps = bpy.context.evaluated_depsgraph_get()
    for _ in range(2):
        bpy.context.view_layer.update()
        deps.update()
        low = min((o.evaluated_get(deps).matrix_world @ v.co).z
                  for o in shoes for v in o.evaluated_get(deps).data.vertices)
        arm.pose.bones["pelvis"].location.y -= low
    bpy.context.view_layer.update()
    deps.update()
    return min((o.evaluated_get(deps).matrix_world @ v.co).z for o in shoes for v in o.evaluated_get(deps).data.vertices)


def bake(arm, signs, shoes):
    arm.animation_data_create()
    action = bpy.data.actions.new("PlayerCycles")
    arm.animation_data.action = action
    scene = bpy.context.scene
    lows = {}
    for label, start, count, fn in (("idle", IDLE_START, IDLE_FRAMES, pose_idle), ("walk", WALK_START, WALK_FRAMES, pose_walk)):
        scene.timeline_markers.new(label, frame=start)
        for i in range(count):
            reset_pose(arm)
            fn(arm, signs, i / count)
            lows[f"{label}{i}"] = round(ground(arm, shoes), 5)
            for pb in arm.pose.bones:
                pb.keyframe_insert("location", frame=start + i)
                pb.keyframe_insert("rotation_euler", frame=start + i)
    scene.frame_start, scene.frame_end = IDLE_START, WALK_START + WALK_FRAMES - 1
    return lows


# --- Output ----------------------------------------------------------------------------------------------

def write_import(png_rel):
    path = ROOT / (png_rel + ".import")
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\n\n[params]\n\n'
                    "compress/mode=0\nmipmaps/generate=true\nmipmaps/limit=-1\n"
                    "process/fix_alpha_border=true\nprocess/premult_alpha=false\ndetect_3d/compress_to=1\n",
                    encoding="utf-8")


ROWS = [(f"idle_{f}", f, "idle") for f, _ in FACINGS] + [(f"walk_{f}", f, "walk") for f, _ in FACINGS]


def write_frames_tres(cell):
    cols = max(IDLE_FRAMES, WALK_FRAMES)
    subs, anims = [], []
    for row, (anim, facing, kind) in enumerate(ROWS):
        count = IDLE_FRAMES if kind == "idle" else WALK_FRAMES
        ids = []
        for col in range(count):
            sid = f"Atlas_{anim}_{col}"
            ids.append(sid)
            subs += [f'[sub_resource type="AtlasTexture" id="{sid}"]', 'atlas = ExtResource("1_sheet")',
                     f"region = Rect2({col * cell[0]}, {row * cell[1]}, {cell[0]}, {cell[1]})", ""]
        frames = ", ".join('{\n"duration": 1.0,\n"texture": SubResource("%s")\n}' % i for i in ids)
        fps = IDLE_FPS if kind == "idle" else WALK_FPS
        anims.append('{\n"frames": [%s],\n"loop": true,\n"name": &"%s",\n"speed": %.1f\n}' % (frames, anim, fps))
    lines = ['[gd_resource type="SpriteFrames" format=3]', "",
             f'[ext_resource type="Texture2D" path="res://{SHEET_REL}" id="1_sheet"]', ""] + subs
    lines += ["[resource]", "animations = [%s]" % ", ".join(anims), ""]
    (ROOT / FRAMES_TRES_REL).write_text("\n".join(lines), encoding="utf-8")
    return cols


def main():
    scene = rig.reset_scene("PlayerCharacter")
    for block in list(bpy.data.actions):
        bpy.data.actions.remove(block)
    rig_coll = rig.new_collection(scene, "Rig")
    char = rig.new_collection(scene, "Character")

    body = build_body(char)
    jacket = build_jacket(char)
    trousers = build_trousers(char)
    shoes = build_shoes(char)
    hair = build_hair(char)
    details = build_face_details(char)

    mats = {
        "skin": material("Skin", SKIN, roughness=0.55, bump=0.05, bump_scale=400.0),
        "cloth": material("Cloth", None, roughness=0.85, bump=0.15, bump_scale=600.0, sheen=0.3),
        "shoe": material("Sneaker", None, roughness=0.6),
        "hair": material("Hair", HAIR, roughness=0.45, bump=0.4, bump_scale=900.0),
        "eye": material("Eye", EYE, roughness=0.2),
    }
    body.data.materials.append(mats["skin"])
    for o in (jacket, trousers):
        o.data.materials.append(mats["cloth"])
    for o in shoes:
        o.data.materials.append(mats["shoe"])
    hair.data.materials.append(mats["hair"])
    for o in details:
        o.data.materials.append(mats["eye"] if o.name.startswith("Eye") else mats["hair"])

    arm = build_armature(char)
    unweighted = skin_to_rig(arm, body, [jacket, trousers, *shoes], [hair, *details])
    signs = calibrate(arm)
    lows = bake(arm, signs, shoes)

    lighting = rig.setup_lighting(scene, rig_coll, char)
    camera, projection = rig.setup_camera(scene, rig_coll, FRAME_BOUNDS, C.CAMERA_ELEVATION_DEG,
                                          C.CAMERA_AZIMUTH_DEG, 0, px_per_m=PX_PER_M, anchor=(0.0, 0.0, 0.0))
    render = rig.setup_render(scene, SAMPLES, use_cpu=False)
    cell = projection["image_px"]
    origin_px = [round(v) for v in rig.project(projection, (0.0, 0.0, 0.0))]

    for stale in (BLEND_PATH, BLEND_PATH.with_suffix(".blend1")):
        if stale.exists():
            stale.unlink()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False, compress=True)
    write_import(SHEET_REL)

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    cols = max(IDLE_FRAMES, WALK_FRAMES)
    sheet = np.zeros((len(ROWS) * cell[1], cols * cell[0], 4), dtype=np.float32)
    for row, (anim, facing, kind) in enumerate(ROWS):
        arm.rotation_euler.z = math.radians(dict(FACINGS)[facing])
        start, count = (IDLE_START, IDLE_FRAMES) if kind == "idle" else (WALK_START, WALK_FRAMES)
        for col in range(count):
            scene.frame_set(start + col)
            out = FRAMES_DIR / f"{anim}_{col}.png"
            scene.render.filepath = str(out)
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(str(out))
            px = np.array(img.pixels[:], dtype=np.float32).reshape(cell[1], cell[0], 4)[::-1]
            bpy.data.images.remove(img)
            sheet[row * cell[1]:(row + 1) * cell[1], col * cell[0]:(col + 1) * cell[0]] = px
        print(f"[PLAYER_CHAR] rendered {anim} ({count} frames)")
    arm.rotation_euler.z = 0.0

    border = np.concatenate([sheet[r * cell[1]] for r in range(len(ROWS))] + [sheet[(r + 1) * cell[1] - 1] for r in range(len(ROWS))])
    max_border_alpha = float(np.max(border[:, 3])) if border.size else 0.0
    for c in range(cols):
        max_border_alpha = max(max_border_alpha, float(np.max(sheet[:, c * cell[0], 3])), float(np.max(sheet[:, (c + 1) * cell[0] - 1, 3])))

    out_img = bpy.data.images.new("PlayerCharacterSheet", sheet.shape[1], sheet.shape[0], alpha=True)
    out_img.pixels[:] = sheet[::-1].ravel()
    out_img.filepath_raw = str(ROOT / SHEET_REL)
    out_img.file_format = "PNG"
    (ROOT / SHEET_REL).parent.mkdir(parents=True, exist_ok=True)
    out_img.save()
    write_frames_tres(cell)

    record = {
        "status": "PROVISIONAL neutral student look; not character canon",
        "generator": "assets/source/blender/characters/player_character.py",
        "blend": "assets/source/blender/characters/player_character.blend",
        "sheet": SHEET_REL, "frames": FRAMES_TRES_REL,
        "sheet_px": [sheet.shape[1], sheet.shape[0]], "cell_px": cell, "origin_px_in_cell": origin_px,
        "rows": [r[0] for r in ROWS], "idle_frames": IDLE_FRAMES, "walk_frames": WALK_FRAMES,
        "idle_fps": IDLE_FPS, "walk_fps": WALK_FPS,
        "px_per_m": PX_PER_M, "godot_scale": C.GAME_PX_PER_M / PX_PER_M, "figure_height_m": 1.80,
        "action": "PlayerCycles (idle frames %d-%d, walk frames %d-%d)" % (IDLE_START, IDLE_START + IDLE_FRAMES - 1, WALK_START, WALK_START + WALK_FRAMES - 1),
        "lowest_shoe_z_per_frame_m": lows, "body_vertices_without_weights": unweighted,
        "max_cell_border_alpha": max_border_alpha, "rotation_signs": signs,
        "mesh_vertices": {o.name: len(o.data.vertices) for o in char.objects if o.type == "MESH"},
        "camera": camera, "lighting": lighting, "render": render,
    }
    RECORD_PATH.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"[PLAYER_CHAR] sheet {sheet.shape[1]}x{sheet.shape[0]} cell {cell} origin {origin_px} "
          f"unweighted {unweighted} border_alpha {max_border_alpha:.4f} lows {min(lows.values())}..{max(lows.values())}")


main()

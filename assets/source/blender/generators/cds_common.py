"""Building blocks for the CDS (Central Dining / sports building) reconstruction (not a generator).

Reference photos: Docs/map-reference/area1/cds-building.png, cds-building2.png (looking east
from the field: left = north). Two masses in red brick with light concrete coping:
  * the low block (canteen to the north, table tennis to the south): one storey, flat dark
    bitumen roof, brick parapet; its west face is an arcade of pointed arches with a low sill
    in front of a covered veranda, the table-tennis part ends in a plain wall with six small
    square vents;
  * the tall indoor-basketball hall (south): blind pointed-arch recesses with a grilled window
    band, a deep brick parapet band and a light-grey flat roof.
All dimensions are estimates from the photos, fitted to the existing blockout footprints.

CDS frame (metres): x = east (0 = the CDSExterior node, world x 1775), y = north, with y = 0 on
the table-tennis south face (world y 0). Every section is modelled in its own local frame
(y = 0 on its south face, the prop origin), but mesh vertices are written in the CDS frame and
the objects moved back by the section's y0, so object-space textures (bricks, roof stains)
continue across sections and slices.

The game camera (orthographic, 40 deg, azimuth 0) sees only top faces and south faces: the
west arcades are edge-on, so on screen the CDS reads through its roofs, parapets, coping,
roof items and the south face of the hall.
"""

import math

import bmesh
import bpy

from generators.landmark_common import (arch_apex_z, arch_outline, brick_shader_material, concrete_material,
                                        glass_material, paint_material, steel_material)
from pipeline.modeling import add_lathe, map_range, multiply_color, new_material, noise

# Ground metres per game px of screen depth (32 px/m * sin 40 deg); the blockout footprints are game px.
DEPTH_PX_PER_M = 32.0 * math.sin(math.radians(40.0))
X_WEST = -295.0 / 32.0          # west face = blockout veranda west edge (world x 1480)
X_EAST = 225.0 / 32.0           # east face (world x 2000)
X_VERANDA_BACK = -225.0 / 32.0  # blockout veranda / mass line (world x 1550)

# Section south face (CDS frame y) and depth, from the blockout (game px / DEPTH_PX_PER_M).
SECTIONS = {
    "indoor_basketball": {"y0": -700.0 / DEPTH_PX_PER_M, "depth": 700.0 / DEPTH_PX_PER_M, "kind": "hall"},
    "table_tennis": {"y0": 0.0, "depth": 450.0 / DEPTH_PX_PER_M, "kind": "low"},
    "canteen": {"y0": 450.0 / DEPTH_PX_PER_M, "depth": 550.0 / DEPTH_PX_PER_M, "kind": "low"},
}

# Vertical sections (z, metres).
# west_depth = arcade / blind-bay wall depth; parapet_depth = the thinner parapet above it (west and,
# on the hall, south), whose coping is the light line the camera sees along the facade.
LOW = {"wall_top": 3.35, "slab_top": 3.60, "parapet_top": 4.15, "coping_top": 4.22,
       "west_depth": 0.45, "parapet_depth": 0.30, "east_depth": 0.30, "end_depth": 0.30}
HALL = {"wall_top": 7.75, "slab_top": 8.00, "parapet_top": 8.75, "coping_top": 8.82,
        "west_depth": 0.85, "parapet_depth": 0.40, "east_depth": 0.40, "end_depth": 0.40}
COPING_INNER_OVERHANG = 0.03     # the coping never projects past the outer (collision) line
OVERLAP_LIFT = 0.0005            # seam strips sit just above the neighbour's surface

# Low-block arcade bays (two-centred pointed arches).
ARCADE = {"canteen": {"half_span": 1.05, "springing": 1.85, "offset": 0.35},
          "table_tennis": {"half_span": 0.95, "springing": 1.75, "offset": 0.30}}
SILL_Z = 0.60
# Hall blind arches: inner recess outline, a stepped outer reveal and a window band.
BLIND = {"half_span": 1.30, "reveal": 0.15, "springing": 5.0, "offset": 0.45, "reveal_depth": 0.10,
         "recess_depth": 0.45, "plinth_z": 0.45, "window_z": (2.90, 3.80), "mullion_pitch": 0.32}

# Linear colours.
COPING_COLOR = (0.50, 0.48, 0.44)
DISH_COLOR = (0.62, 0.62, 0.60)
DARK_COLOR = (0.012, 0.011, 0.010)


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def bitumen_material(name="CdsBitumen"):
    """Dark tar / bitumen roof (photo: near-black, stained, with lighter weathered patches)."""
    mat, nt, bsdf = new_material(name)
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs["Color"].default_value = (0.040, 0.040, 0.041, 1.0)
    patches = noise(nt, coords, 0.35, detail=4.0, roughness=0.55)
    stains = noise(nt, coords, 1.6, detail=8.0, roughness=0.7)
    grain = noise(nt, coords, 70.0, detail=2.0)
    out = multiply_color(nt, base.outputs["Color"], map_range(nt, patches.outputs["Fac"], 0.42, 0.68, 0.9, 2.7))
    out = multiply_color(nt, out, map_range(nt, stains.outputs["Fac"], 0.35, 0.65, 0.75, 1.15))
    out = multiply_color(nt, out, map_range(nt, grain.outputs["Fac"], 0.3, 0.7, 0.9, 1.08))
    nt.links.new(out, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.88
    return mat


def materials():
    """One shared material set per build (names are fixed; context builds get Blender suffixes)."""
    return {
        "brick": brick_shader_material("CdsBrick", seed=11.0),
        "coping": paint_material("CdsCoping", COPING_COLOR, roughness=0.85, variation=0.12, grime_low=1.0),
        "dark": paint_material("CdsDarkRecess", DARK_COLOR, roughness=0.9, variation=0.0, grime_low=1.0),
        "glass": glass_material("CdsWindowGlass"),
        "bitumen": bitumen_material("CdsBitumen"),
        "hall_roof": concrete_material("CdsHallRoof"),
        "dish": paint_material("CdsDish", DISH_COLOR, roughness=0.5, variation=0.05, grime_low=1.0),
        "steel": steel_material("CdsSteel"),
    }


# ---------------------------------------------------------------------------
# Geometry: per-slice mesh parts
# ---------------------------------------------------------------------------

class Part:
    """One object's bmesh. Coordinates passed in are section-local; vertices are stored in the
    CDS frame (y + y0) and the object is moved by -y0, so object space = CDS frame."""

    def __init__(self, y0):
        self.bm = bmesh.new()
        self.mats = []
        self.y0 = y0

    def _mat(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _v(self, x, y, z):
        return self.bm.verts.new((x, y + self.y0, z))

    def box(self, x0, x1, y0, y1, z0, z1, mat):
        if x1 - x0 < 1e-6 or y1 - y0 < 1e-6 or z1 - z0 < 1e-6:
            return
        v = [self._v(*c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        index = self._mat(mat)
        for f in ((v[0], v[3], v[2], v[1]), (v[4], v[5], v[6], v[7]), (v[0], v[1], v[5], v[4]),
                  (v[2], v[3], v[7], v[6]), (v[1], v[2], v[6], v[5]), (v[3], v[0], v[4], v[7])):
            self.bm.faces.new(f).material_index = index

    def strip(self, frame, lower, upper, v0, v1, mat):
        """Closed solid between two (u, z) polylines with equal point counts, from depth v0 to v1;
        `frame(u, v, z)` maps facade coordinates to section-local (x, y, z)."""
        def ring(pts, v):
            return [self._v(*frame(u, v, z)) for u, z in pts]
        lf, uf, lb, ub = ring(lower, v0), ring(upper, v0), ring(lower, v1), ring(upper, v1)
        index = self._mat(mat)
        faces = []
        for i in range(len(lower) - 1):
            faces += [(lf[i], lf[i + 1], uf[i + 1], uf[i]), (ub[i], ub[i + 1], lb[i + 1], lb[i]),
                      (lb[i], lb[i + 1], lf[i + 1], lf[i]), (uf[i], uf[i + 1], ub[i + 1], ub[i])]
        faces += [(lf[0], uf[0], ub[0], lb[0]), (lb[-1], ub[-1], uf[-1], lf[-1])]
        for f in faces:
            self.bm.faces.new(f).material_index = index

    def lathe(self, profile, center, z0, mat, sides=20, tilt=None):
        index = self._mat(mat)
        start = len(self.bm.verts)
        for f in add_lathe(self.bm, [(r, z) for r, z in profile], sides=sides):
            f.material_index = index
        self.bm.verts.ensure_lookup_table()
        cx, cy = center
        for v in self.bm.verts[start:]:
            x, y, z = v.co.x, v.co.y, v.co.z
            if tilt:
                # Rotate about the x axis through the profile base (dish facing south-up).
                c, s = math.cos(tilt), math.sin(tilt)
                y, z = y * c - z * s, y * s + z * c
            v.co = (x + cx, y + cy + self.y0, z + z0)

    def finish(self, collection, name):
        if not self.bm.verts:
            self.bm.free()
            return None
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        mesh = bpy.data.meshes.new(name + "Mesh")
        self.bm.normal_update()
        self.bm.to_mesh(mesh)
        self.bm.free()
        for m in self.mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(name, mesh)
        obj.location.y = -self.y0
        collection.objects.link(obj)
        return obj


class Slices:
    """Section geometry split into north-south slices; each slice has its own parts
    ("walls", "roof", "items", "overlap") so the pipeline can render them as separate layers."""

    KINDS = ("walls", "roof", "items", "overlap")

    def __init__(self, bounds, y0):
        self.bounds = bounds        # section-local y: [0, b1, ..., depth]
        self.y0 = y0
        self.parts = {}

    def part(self, i, kind):
        key = (i, kind)
        if key not in self.parts:
            self.parts[key] = Part(self.y0)
        return self.parts[key]

    def index(self, y):
        for i in range(len(self.bounds) - 1):
            if y < self.bounds[i + 1]:
                return i
        return len(self.bounds) - 2

    def box(self, kind, x0, x1, y0, y1, z0, z1, mat):
        """Axis-aligned box, cut at the slice boundaries it crosses."""
        for i in range(len(self.bounds) - 1):
            a, b = max(y0, self.bounds[i]), min(y1, self.bounds[i + 1])
            if b - a > 1e-6:
                self.part(i, kind).box(x0, x1, a, b, z0, z1, mat)

    def finish(self, collection, overlap_flags):
        objects, names = [], {}
        for (i, kind) in sorted(self.parts, key=lambda k: (k[0], self.KINDS.index(k[1]))):
            name = f"S{i + 1}{kind.capitalize()}"
            obj = self.parts[(i, kind)].finish(collection, name)
            if obj is None:
                continue
            if kind == "overlap":
                overlap_flags(obj)
            objects.append(obj)
            names.setdefault(f"Slice{i + 1}", []).append(name)
        return objects, names


def mark_seam_overlap(obj):
    """Camera-only strip: no shadows, no bounce, so the lighting equals the neighbour's own render.
    The pipeline hides it (instead of holding it out) in every other sprite's render."""
    obj["seam_overlap"] = True
    obj.visible_shadow = False
    obj.visible_diffuse = False
    obj.visible_glossy = False
    obj.visible_transmission = False
    obj.visible_volume_scatter = False


# ---------------------------------------------------------------------------
# Facade frames: (u along the facade, v depth into the building, z) -> section-local (x, y, z)
# ---------------------------------------------------------------------------

def west_frame(u, v, z):
    return (X_WEST + v, u, z)


def south_frame(u, v, z):
    return (u, v, z)


def pier_gaps(start, end, openings):
    """Solid intervals of a facade run between `openings` [(u0, u1), ...] (sorted)."""
    gaps, u = [], start
    for a, b in openings:
        if a - u > 1e-6:
            gaps.append((u, a))
        u = b
    if end - u > 1e-6:
        gaps.append((u, end))
    return gaps


def run_box(sl, kind, frame, u0, u1, v0, v1, z0, z1, mat, slice_index=None):
    """Box given in facade coordinates; west-facade boxes are cut at slice boundaries."""
    (xa, ya, _), (xb, yb, _) = frame(u0, v0, z0), frame(u1, v1, z1)
    x0, x1, y0, y1 = min(xa, xb), max(xa, xb), min(ya, yb), max(ya, yb)
    if slice_index is None:
        sl.box(kind, x0, x1, y0, y1, z0, z1, mat)
    else:
        sl.part(slice_index, kind).box(x0, x1, y0, y1, z0, z1, mat)


# ---------------------------------------------------------------------------
# Bays
# ---------------------------------------------------------------------------

def arcade_bay(sl, m, centre, arch, wall_top, depth, sill=True, slice_index=None):
    """Open pointed arch in the low block's west wall: spandrel up to the slab, an optional low
    sill wall with a concrete cap (photo: every arcade bay but the entrance has one)."""
    h, zs, d = arch["half_span"], arch["springing"], arch["offset"]
    i = sl.index(centre) if slice_index is None else slice_index
    part = sl.part(i, "walls")
    outline = [(centre + u, z) for u, z in arch_outline(h, zs, d, jambs=False)]
    part.strip(west_frame, outline, [(u, wall_top) for u, _ in outline], 0.0, depth, m["brick"])
    if sill:
        part.box(X_WEST + 0.08, X_WEST + depth - 0.08, centre - h, centre + h, 0.0, SILL_Z, m["brick"])
        part.box(X_WEST + 0.05, X_WEST + depth - 0.05, centre - h, centre + h, SILL_Z, SILL_Z + 0.06, m["coping"])
    else:
        # Entrance: a single step inside the wall line, up to the veranda floor.
        part.box(X_WEST + 0.02, X_WEST + depth, centre - h, centre + h, 0.0, 0.15, m["coping"])
    return (centre - h, centre + h)


def blind_bay(sl, m, frame, centre, wall_top, depth, slice_index, mullions=True):
    """Hall bay: stepped outer reveal and a deep blind pointed recess with a plinth and a band of
    grilled windows (photo: dark windows with vertical bars at about a third of the height)."""
    b = BLIND
    h, r, zs, d = b["half_span"], b["reveal"], b["springing"], b["offset"]
    rd, rec = b["reveal_depth"], b["recess_depth"]
    walls = sl.part(slice_index, "walls")
    outer = [(centre + u, z) for u, z in arch_outline(h + r, zs, d, jambs=False)]
    walls.strip(frame, outer, [(u, wall_top) for u, _ in outer], 0.0, depth, m["brick"])
    walls.strip(frame, [(centre + u, z) for u, z in arch_outline(h, zs, d)],
                [(centre + u, z) for u, z in arch_outline(h + r, zs, d)], rd, depth, m["brick"])
    apex = arch_apex_z(h, zs, d)
    inner = [(centre + u, z) for u, z in arch_outline(h, zs, d, jambs=False)]
    walls.strip(frame, [(u, 0.0) for u, _ in inner], inner, rec, depth, m["brick"])
    run_box(sl, "walls", frame, centre - h, centre + h, rec - 0.25, rec, 0.0, b["plinth_z"], m["brick"], slice_index)
    run_box(sl, "walls", frame, centre - h, centre + h, rec - 0.27, rec, b["plinth_z"], b["plinth_z"] + 0.05,
            m["coping"], slice_index)
    w0, w1 = b["window_z"]
    run_box(sl, "walls", frame, centre - h + 0.12, centre + h - 0.12, rec - 0.03, rec + 0.02, w0, w1,
            m["glass"], slice_index)
    run_box(sl, "walls", frame, centre - h, centre + h, rec - 0.10, rec, w0 - 0.08, w0, m["coping"], slice_index)
    run_box(sl, "walls", frame, centre - h, centre + h, rec - 0.06, rec, w1, w1 + 0.08, m["coping"], slice_index)
    if mullions:
        span = 2 * (h - 0.12)
        n = max(2, round(span / b["mullion_pitch"]))
        for k in range(1, n):
            u = centre - (h - 0.12) + span * k / n
            run_box(sl, "walls", frame, u - 0.025, u + 0.025, rec - 0.05, rec, w0, w1, m["coping"], slice_index)
    return (centre - h - r, centre + h + r), apex


# ---------------------------------------------------------------------------
# Roof
# ---------------------------------------------------------------------------

def roof_band(part, m, y0, y1, spec, membrane, lift=0.0, x_west=X_WEST, x_east=X_EAST):
    """Everything seen from above between y0 and y1: the roof slab (membrane on top) and the west
    and east coping. `lift` raises a seam-overlap copy just above the neighbour's surface."""
    pd, ed = spec["parapet_depth"], spec["east_depth"]
    part.box(x_west + pd, x_east - ed, y0, y1, spec["wall_top"] + lift, spec["slab_top"] + lift, membrane)
    part.box(x_west, x_west + pd + COPING_INNER_OVERHANG, y0, y1, spec["parapet_top"] + lift,
             spec["coping_top"] + lift, m["coping"])
    part.box(x_east - ed - COPING_INNER_OVERHANG, x_east, y0, y1, spec["parapet_top"] + lift,
             spec["coping_top"] + lift, m["coping"])


def parapet_sides(sl, m, y0, y1, spec, z0):
    """West (fascia) and east brick parapets from z0 to the parapet top, cut per slice."""
    sl.box("roof", X_WEST, X_WEST + spec["parapet_depth"], y0, y1, z0, spec["parapet_top"], m["brick"])
    sl.box("roof", X_EAST - spec["east_depth"], X_EAST, y0, y1, z0, spec["parapet_top"], m["brick"])


def end_wall(sl, m, y0, y1, spec, coping=True):
    """Full-width brick end wall (north or south end of a section) with its coping."""
    sl.box("walls", X_WEST, X_EAST, y0, y1, 0.0, spec["wall_top"], m["brick"])
    sl.box("roof", X_WEST, X_EAST, y0, y1, spec["wall_top"], spec["parapet_top"], m["brick"])
    if coping:
        sl.box("roof", X_WEST, X_EAST, y0, y1, spec["parapet_top"], spec["coping_top"], m["coping"])


def satellite_dish(part, m, x, y, z0, radius=0.42):
    """Pole-mounted dish tilted towards the south-west sky (photo: dishes near the west parapet)."""
    part.box(x - 0.03, x + 0.03, y - 0.03, y + 0.03, z0, z0 + 0.60, m["steel"])
    part.box(x - 0.18, x + 0.18, y - 0.18, y + 0.18, z0, z0 + 0.04, m["steel"])
    depth = radius * 0.32
    back = [(max(0.02, radius * k / 6), depth * (k / 6) ** 2) for k in range(7)]
    profile = back + [(r, z + 0.015) for r, z in reversed(back)]
    part.lathe(profile, (x, y + 0.05), z0 + 0.62, m["dish"], tilt=math.radians(55.0))

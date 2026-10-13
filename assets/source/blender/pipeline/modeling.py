"""Reusable modeling and shader-node helpers for asset generators (runs inside Blender)."""

import math

import bmesh
import bpy
from mathutils import Vector


def add_tube(bm, points, radii, sides=8, cap_start=False, cap_end=True):
    """Tapered tube along a polyline (rings kept perpendicular by parallel transport).
    Returns the list of rings (lists of BMVerts)."""
    pts = [Vector(p) for p in points]
    tangents = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        tangents.append((b - a).normalized())
    ref = Vector((1, 0, 0)) if abs(tangents[0].x) < 0.9 else Vector((0, 1, 0))
    side = tangents[0].cross(ref).normalized()
    rings = []
    for i, (p, t, r) in enumerate(zip(pts, tangents, radii)):
        if i:
            side = (side - t * side.dot(t)).normalized()
        other = t.cross(side)
        ring = [bm.verts.new(p + (side * math.cos(a) + other * math.sin(a)) * r)
                for a in (2 * math.pi * k / sides for k in range(sides))]
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    if cap_start:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end:
        bm.faces.new(rings[-1])
    return rings


def add_lathe(bm, profile, sides=16, angle_offset=0.0, center=(0.0, 0.0)):
    """Surface of revolution around the Z axis through `center` from a (radius, z) profile,
    bottom to top. A radius of 0 at either end closes it with a fan."""
    cx, cy = center
    rings = []
    for r, z in profile:
        rings.append([bm.verts.new((cx + r * math.cos(angle_offset + 2 * math.pi * k / sides),
                                    cy + r * math.sin(angle_offset + 2 * math.pi * k / sides), z))
                      for k in range(sides)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            faces.append(bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k])))
    if profile[0][0] > 0:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if profile[-1][0] > 0:
        faces.append(bm.faces.new(rings[-1]))
    return faces


def mesh_object(collection, name, bm, materials=(), smooth=False):
    mesh = bpy.data.meshes.new(name + "Mesh")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.shade_smooth()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def extreme_points(objects, elevations=range(0, 91, 5)):
    """A few evaluated vertices (world space) that bound the objects as seen by the asset camera
    (azimuth 0) at any of `elevations`: extremes along X and along the camera's screen-up axis.
    Use as `bounds_points_m` for rounded shapes, where bounding-box corners would over-frame."""
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in objects:
        ev = obj.evaluated_get(deps)
        mesh = ev.to_mesh()
        mw = obj.matrix_world
        pts += [mw @ v.co for v in mesh.vertices]
        ev.to_mesh_clear()
    keys = [lambda p: p.x, lambda p: p.y, lambda p: p.z]
    for el in elevations:
        s, c = math.sin(math.radians(el)), math.cos(math.radians(el))
        keys.append(lambda p, s=s, c=c: p.y * s + p.z * c)
    chosen = {}
    for key in keys:
        for p in (min(pts, key=key), max(pts, key=key)):
            chosen[tuple(round(v, 6) for v in p)] = None
    return list(chosen)


class BoxBuilder:
    """Accumulates axis-aligned boxes into one bmesh with a per-face random attribute."""

    def __init__(self, rand_attribute="brick_rand"):
        self.bm = bmesh.new()
        self.rand_layer = self.bm.faces.layers.float.new(rand_attribute)
        self.no_bevel_layer = None
        self.box_count = 0

    def _faces(self, faces, rand, material_index, bevel):
        if not bevel and self.no_bevel_layer is None:
            self.no_bevel_layer = self.bm.faces.layers.int.new("no_bevel")
        for f in faces:
            face = self.bm.faces.new(f)
            face[self.rand_layer] = rand
            face.material_index = material_index
            if not bevel:
                face[self.no_bevel_layer] = 1
        self.box_count += 1

    def add(self, x0, x1, y0, y1, z0, z1, rand=0.0, material_index=0, bevel=True):
        v = [self.bm.verts.new(c) for c in (
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        )]
        faces = (
            (v[0], v[3], v[2], v[1]),  # bottom
            (v[4], v[5], v[6], v[7]),  # top
            (v[0], v[1], v[5], v[4]),  # -Y (front)
            (v[2], v[3], v[7], v[6]),  # +Y (back)
            (v[1], v[2], v[6], v[5]),  # +X
            (v[3], v[0], v[4], v[7]),  # -X
        )
        self._faces(faces, rand, material_index, bevel)

    def add_prism_xz(self, poly_xz, y0, y1, rand=0.0, material_index=0, bevel=True):
        """Convex polygon in the XZ plane (front view), extruded from y0 (front) to y1 (back).
        Used for wedge-shaped pieces: arch voussoirs and bricks cut along an arch."""
        pts = list(poly_xz)
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
        if area < 0:
            pts.reverse()  # counter-clockwise seen from the front (x right, z up)
        front = [self.bm.verts.new((x, y0, z)) for x, z in pts]
        back = [self.bm.verts.new((x, y1, z)) for x, z in pts]
        n = len(pts)
        faces = [tuple(front), tuple(reversed(back))]
        faces += [(front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]) for i in range(n)]
        self._faces(faces, rand, material_index, bevel)

    def to_mesh(self, name, flush_x=None):
        """Writes the mesh. Every edge gets bevel weight 1 (use Bevel limit "WEIGHT"), except
        edges lying entirely on one of the `flush_x` planes (module ends that must meet flush)
        and edges of pieces added with bevel=False."""
        weight = self.bm.edges.layers.float.new("bevel_weight_edge")
        for edge in self.bm.edges:
            on_end = flush_x is not None and any(
                all(abs(v.co.x - x) < 1e-6 for v in edge.verts) for x in flush_x)
            flat = self.no_bevel_layer is not None and any(
                f[self.no_bevel_layer] for f in edge.link_faces)
            edge[weight] = 0.0 if on_end or flat else 1.0
        mesh = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(mesh)
        self.bm.free()
        return mesh


def socket(sockets, identifier):
    return next(s for s in sockets if s.identifier == identifier)


def new_material(name):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf


def noise(nt, coords, scale, detail=6.0, roughness=0.6):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = roughness
    nt.links.new(coords, n.inputs["Vector"])
    return n


def map_range(nt, value_socket, from_min, from_max, to_min, to_max, clamp=True):
    m = nt.nodes.new("ShaderNodeMapRange")
    m.clamp = clamp
    m.inputs["From Min"].default_value = from_min
    m.inputs["From Max"].default_value = from_max
    m.inputs["To Min"].default_value = to_min
    m.inputs["To Max"].default_value = to_max
    nt.links.new(value_socket, m.inputs["Value"])
    return m.outputs["Result"]


def multiply_color(nt, color_socket, factor_socket):
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    socket(mix.inputs, "Factor_Float").default_value = 1.0
    nt.links.new(color_socket, socket(mix.inputs, "A_Color"))
    nt.links.new(factor_socket, socket(mix.inputs, "B_Color"))
    return socket(mix.outputs, "Result_Color")


def ground_grime(nt, low=0.72, height_m=0.6):
    """Darkening factor: `low` at the ground, 1.0 from `height_m` up."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    return map_range(nt, sep.outputs["Z"], 0.0, height_m, low, 1.0)

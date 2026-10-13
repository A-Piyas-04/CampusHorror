"""Reusable modeling and shader-node helpers for asset generators (runs inside Blender)."""

import bmesh
import bpy


class BoxBuilder:
    """Accumulates axis-aligned boxes into one bmesh with a per-face random attribute."""

    def __init__(self, rand_attribute="brick_rand"):
        self.bm = bmesh.new()
        self.rand_layer = self.bm.faces.layers.float.new(rand_attribute)
        self.box_count = 0

    def add(self, x0, x1, y0, y1, z0, z1, rand=0.0, material_index=0):
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
        for f in faces:
            face = self.bm.faces.new(f)
            face[self.rand_layer] = rand
            face.material_index = material_index
        self.box_count += 1

    def to_mesh(self, name):
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

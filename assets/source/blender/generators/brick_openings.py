"""Shared helpers for red-brick wall modules with an opening (pointed-arch doorway and window).

Not a generator (no build()). Courses and coping are laid by the wall generator's own code,
with the wall's seed and in the wall's RNG order, so every brick outside the module middle
is identical to RedBrickWall3m: the modules drop into a wall run and join it seamlessly.
Bricks in the middle are clipped around the opening and recoloured from a separate RNG.

Frame as in red_brick_wall.py: X along the wall, front faces -Y, Z up, origin at the centre
of the footprint on the ground, metres.
"""

import math

from generators.red_brick_wall import _add_course, _brick_rand

MIN_PIECE_M = 0.02  # narrower cut pieces are dropped; the mortar core fills the gap


def course_height(p):
    return p["brick_height"] + p["joint"]


def wall_face_offset(p, course):
    """Face projection of a wall course, exactly as in red_brick_wall._build_mesh."""
    if course < p["plinth_courses"]:
        return p["plinth_projection"]
    if course == p["body_courses"] - 1:
        return p["oversail_projection"]
    return 0.0


# ---------------------------------------------------------------------------
# Clipping
# ---------------------------------------------------------------------------

def _clip(poly, inside):
    """Sutherland-Hodgman clip of a convex XZ polygon against a linear half-plane (inside >= 0)."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        fp, fq = inside(p), inside(q)
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            s = fp / (fp - fq)
            out.append((p[0] + s * (q[0] - p[0]), p[1] + s * (q[1] - p[1])))
    clean = []
    for p in out:
        if not clean or abs(p[0] - clean[-1][0]) > 1e-7 or abs(p[1] - clean[-1][1]) > 1e-7:
            clean.append(p)
    if len(clean) > 1 and abs(clean[0][0] - clean[-1][0]) < 1e-7 and abs(clean[0][1] - clean[-1][1]) < 1e-7:
        clean.pop()
    return clean


def clip_box(x0, x1, z0, z1, void):
    """XZ pieces of a box outside the symmetric void |x| < void(z).

    The void edge is taken as straight across the box height (one brick course), between its
    values just above the bottom and just below the top, so steps at course joints are exact.
    """
    rect = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    vb, vt = void(z0 + 1e-6), void(z1 - 1e-6)
    if vb <= 0.0 and vt <= 0.0:
        return [rect]

    def edge(z):
        return vb + (vt - vb) * (z - z0) / (z1 - z0)

    pieces = [_clip(rect, lambda p: -edge(p[1]) - p[0]), _clip(rect, lambda p: p[0] - edge(p[1]))]
    return [q for q in pieces
            if len(q) >= 3 and max(x for x, _ in q) - min(x for x, _ in q) > MIN_PIECE_M]


def add_piece(builder, poly, y0, y1, rand, material_index, bevel=True):
    xs, zs = sorted({round(x, 9) for x, _ in poly}), sorted({round(z, 9) for _, z in poly})
    if len(poly) == 4 and len(xs) == 2 and len(zs) == 2:
        builder.add(xs[0], xs[1], y0, y1, zs[0], zs[1], rand=rand, material_index=material_index, bevel=bevel)
    else:
        builder.add_prism_xz(poly, y0, y1, rand=rand, material_index=material_index, bevel=bevel)


class OpeningBuilder:
    """Stands in for BoxBuilder when the wall generator lays courses: each box is clipped
    against `void` (set per phase), and bricks lying wholly inside |x| < middle_half get a
    colour from `interior_rng`. The wall RNG is consumed exactly as for the plain wall."""

    def __init__(self, builder, interior_rng, middle_half):
        self.builder = builder
        self.interior_rng = interior_rng
        self.middle_half = middle_half
        self.void = lambda z: 0.0

    def add(self, x0, x1, y0, y1, z0, z1, rand=0.0, material_index=0):
        if -self.middle_half < x0 and x1 < self.middle_half:
            rand = _brick_rand(self.interior_rng)
        for poly in clip_box(x0, x1, z0, z1, self.void):
            add_piece(self.builder, poly, y0, y1, rand, material_index)


# ---------------------------------------------------------------------------
# Wall courses, coping and mortar (same layout as red_brick_wall._build_mesh)
# ---------------------------------------------------------------------------

def lay_wall_courses(builder, rng, p):
    ch = course_height(p)
    for course in range(p["body_courses"]):
        _add_course(builder, rng, p, course * ch, wall_face_offset(p, course), offset_half=bool(course % 2))


def lay_coping(builder, rng, p, half_l, z0, top, units):
    """Rowlock coping; for the wall's own half length and unit count it draws the same
    random numbers in the same order as red_brick_wall._build_mesh."""
    coping_half_t = p["thickness"] / 2.0 + p["coping_projection"]
    pitch = 2.0 * half_l / units
    for i in range(units):
        x0 = -half_l + i * pitch + p["joint"] / 2.0
        x1 = x0 + pitch - p["joint"]
        builder.add(x0 + rng.uniform(0, 0.001), x1 - rng.uniform(0, 0.001),
                    -coping_half_t - rng.uniform(-0.001, 0.001),
                    coping_half_t + rng.uniform(-0.001, 0.001),
                    z0, top - rng.uniform(0.0, 0.0015),
                    rand=_brick_rand(rng), material_index=0)


def mortar_bands(builder, p, x_ranges):
    """The wall's four recessed mortar cores, limited to the given x ranges (module ends)."""
    ch = course_height(p)
    body = p["body_courses"]
    half_t = p["thickness"] / 2.0
    plinth_top = p["plinth_courses"] * ch
    oversail_z0 = (body - 1) * ch
    coping_z0 = body * ch
    for (z0, z1, face) in (
        (0.0, plinth_top, half_t + p["plinth_projection"]),
        (plinth_top, oversail_z0, half_t),
        (oversail_z0, coping_z0, half_t + p["oversail_projection"]),
        (coping_z0, p["height"] - 0.004, half_t + p["coping_projection"]),
    ):
        depth = face - p["joint_recess"]
        for x0, x1 in x_ranges:
            builder.add(x0, x1, -depth, depth, z0, z1, rand=0.5, material_index=1)


def mortar_strips(builder, p, courses, half_x, void, face_offset):
    """Recessed mortar core one course at a time over |x| < half_x, clipped to the opening.
    No bevel: the strips must read as one continuous core."""
    ch = course_height(p)
    half_t = p["thickness"] / 2.0
    for k in courses:
        depth = half_t + face_offset(k) - p["joint_recess"]
        for poly in clip_box(-half_x, half_x, k * ch, (k + 1) * ch, void):
            add_piece(builder, poly, -depth, depth, 0.5, 1, bevel=False)


def lay_jambs(builder, rng, p, half_span, courses, widths, face_offset):
    """Full-depth brick returns lining both jambs; widths alternate by course so joints stagger."""
    ch = course_height(p)
    half_t = p["thickness"] / 2.0
    count = 0
    for k in courses:
        w = widths[k % len(widths)]
        y = half_t + face_offset(k)
        for side in (-1, 1):
            x0, x1 = sorted((side * half_span, side * (half_span + w)))
            builder.add(x0, x1, -y, y, k * ch, k * ch + p["brick_height"], rand=_brick_rand(rng), material_index=0)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Pointed arch
# ---------------------------------------------------------------------------

class PointedArch:
    """Equilateral pointed arch: clear span 2a, springing at height zs, each half an arc of
    radius 2a centred on the opposite springing point; voussoir ring of radial depth t."""

    def __init__(self, half_span, springing_z, ring_depth):
        self.a, self.zs, self.t = half_span, springing_z, ring_depth
        self.r = 2.0 * half_span
        self.apex_intrados = springing_z + math.sqrt(self.r ** 2 - half_span ** 2)
        self.apex_extrados = springing_z + math.sqrt((self.r + ring_depth) ** 2 - half_span ** 2)

    def _half_width(self, radius, z):
        dz = z - self.zs
        if dz < 0.0:
            return radius - self.a
        if dz >= radius:
            return 0.0
        return max(0.0, math.sqrt(radius * radius - dz * dz) - self.a)

    def intrados(self, z):
        """Half-width of the clear opening at height z (z >= springing)."""
        return self._half_width(self.r, z)

    def extrados(self, z):
        """Half-width of the opening plus ring at height z (z >= springing)."""
        return self._half_width(self.r + self.t, z)

    def intrados_z(self, x):
        """Height of the intrados soffit above |x| <= a."""
        return self.zs + math.sqrt(max(0.0, self.r ** 2 - (abs(x) + self.a) ** 2))

    def lay_ring(self, builder, y_half, joint, pitch, rand_fn):
        """Radial voussoirs through the full wall depth (brick soffit), meeting at a keystone."""
        a, r, t, zs = self.a, self.r, self.t, self.zs
        theta_apex = math.acos(a / r)
        n = max(3, round(r * theta_apex / pitch))
        step = theta_apex / n
        dj = joint / (r + t / 2.0)
        count = 0
        for side in (-1, 1):
            def pt(radius, th):
                return (side * (radius * math.cos(th) - a), zs + radius * math.sin(th))
            for k in range(n):
                t0 = k * step + (dj / 2.0 if k else 0.0)
                t1 = (k + 1) * step - dj / 2.0
                poly = [pt(r, t0), pt(r, t1), pt(r + t, t1), pt(r + t, t0)]
                builder.add_prism_xz(poly, -y_half, y_half, rand=rand_fn(), material_index=0)
                count += 1
        z_out = zs + (r + t) * math.sin(theta_apex)
        key = [(0.0, self.apex_intrados), (t / 2.0, z_out), (0.0, self.apex_extrados), (-t / 2.0, z_out)]
        builder.add_prism_xz(key, -y_half, y_half, rand=rand_fn(), material_index=0)
        return count + 1

"""The campus layout (data/campus/campus_layout.json): loading, validation and geometry helpers.

The layout is the single source of truth for the campus (decision D44): the map-design export, the ground masks and
the `campus` zone generator all read it through this module. Metres, x east, y south, north up.
"""

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / "data/campus/campus_layout.json"
PX_X = 32.0
PX_Y = 20.576  # 32 x 0.643 (sin 40 degrees, rounded as everywhere else in the project)

SURFACES = {
    # id: (preview colour, walk surface for footsteps, description)
    "grass": ("#7fae4a", "grass", "mown lawn"),
    "meadow": ("#5f8a3c", "grass", "rough field grass"),
    "field": ("#4f8a3a", "grass", "sports turf"),
    "forest_floor": ("#56703a", "grass", "leaf litter under trees"),
    "compound": ("#6e6560", "paving", "residential paving"),
    "pavers": ("#a4594a", "paving", "red brick pavers (herringbone)"),
    "pavers_dark": ("#7a4a40", "paving", "dark brick paving"),
    "brick_road": ("#b8705c", "paving", "red brick road"),
    "brick_path": ("#9c5a48", "paving", "narrow brick path"),
    "asphalt": ("#55575b", "asphalt", "asphalt road"),
    "concrete": ("#b9b6ad", "paving", "concrete"),
    "court_tennis": ("#3f6f62", "paving", "tennis court"),
    "court_futsal": ("#3b5a52", "paving", "futsal court"),
    "gravel": ("#8d877a", "gravel", "gravel"),
    "dirt": ("#9a7b56", "dirt", "bare earth"),
    "water": ("#3d6f86", "water", "lake water"),
}
STATUS = ("built", "under_construction", "proposed")


def load(path=LAYOUT):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --- geometry ------------------------------------------------------------------------------------------------

def rect_poly(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def square_poly(c, size, rot_deg):
    """A square turned rot_deg clockwise on the map (screen, y down)."""
    h = size / 2.0
    t = math.radians(rot_deg)
    ct, st = math.cos(t), math.sin(t)
    return [(c[0] + x * ct - y * st, c[1] + x * st + y * ct) for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))]


def circle_poly(c, r, n=20):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def part_poly(p):
    if "rect" in p:
        return rect_poly(p["rect"])
    if "square" in p:
        s = p["square"]
        return square_poly(s["centre"], s["size"], s.get("rot_deg", 0.0))
    if "circle" in p:
        return circle_poly(p["circle"]["centre"], p["circle"]["r"])
    if "poly" in p:
        return [tuple(q) for q in p["poly"]]
    raise ValueError(f"unknown part shape: {p}")


def monument_polys(m):
    """The Five Fundamentals: n walls across an axis (axis_deg clockwise from east), each cut by a central passage."""
    cx, cy = m["centre"]
    a = math.radians(m["axis_deg"])
    ax, ay = math.cos(a), math.sin(a)          # along the causeway
    px, py = -ay, ax                           # across it
    n, L, T, sp, gap = m["walls"], m["wall_len"], m["wall_thick"], m["spacing"], m.get("passage", 0.0)
    out = []
    for i in range(n):
        o = (i - (n - 1) / 2.0) * sp
        wx, wy = cx + ax * o, cy + ay * o
        for s0, s1 in ((-L / 2, -gap / 2), (gap / 2, L / 2)) if gap else ((-L / 2, L / 2),):
            pts = []
            for u, v in ((s0, -T / 2), (s1, -T / 2), (s1, T / 2), (s0, T / 2)):
                pts.append((wx + px * u + ax * v, wy + py * u + ay * v))
            out.append(pts)
    return out


def site_polys(site):
    if "monument" in site:
        return monument_polys(site["monument"])
    return [part_poly(p) for p in site.get("parts", [])]


def ground_poly(g, layout):
    if g.get("poly") == "boundary":
        return [tuple(q) for q in layout["boundary"]["points"]]
    if "rect" in g:
        return rect_poly(g["rect"])
    return [tuple(q) for q in g["poly"]]


def bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def polyline_length(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def along(pts, spacing, offset=0.0):
    """Points every `spacing` metres along a polyline (both ends included when they fit)."""
    total = polyline_length(pts)
    if total <= 0:
        return [tuple(pts[0])]
    n = max(1, int(round(total / spacing)))
    step = total / n
    out = []
    for k in range(n + 1):
        d = k * step + offset
        acc = 0.0
        for i in range(len(pts) - 1):
            seg = math.dist(pts[i], pts[i + 1])
            if acc + seg >= d - 1e-9:
                t = 0.0 if seg == 0 else (d - acc) / seg
                out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
                break
            acc += seg
    return out


def road_poly(road):
    """A road centreline widened into one polygon per segment (corners filled by the round joins at draw time)."""
    w = road["width"] / 2.0
    pts = road["points"]
    out = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L * w, dx / L * w
        out.append([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)])
    return out


def point_in_poly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def grove_points(g):
    """Deterministic Poisson-ish scatter for a grove (seeded, min-gap rejection)."""
    rnd = random.Random(g.get("seed", 0))
    x0, y0, x1, y1 = g["rect"]
    pts = []
    tries = 0
    species = g["species"] if isinstance(g["species"], list) else [g["species"]]
    while len(pts) < g["count"] and tries < g["count"] * 400:
        tries += 1
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if any(a[0] <= x <= a[2] and a[1] <= y <= a[3] for a in g.get("avoid", [])):
            continue
        if all(math.dist((x, y), (p[0], p[1])) >= g["min_gap"] for p in pts):
            pts.append((round(x, 2), round(y, 2), species[rnd.randrange(len(species))]))
    return pts


def all_trees(layout):
    """Every tree as (x, y, species, source)."""
    t = layout.get("trees", {})
    out = []
    for row in t.get("rows", []):
        for x, y in along(row["points"], row["spacing"]):
            out.append((round(x, 2), round(y, 2), row["species"], row["id"]))
    for g in t.get("groves", []):
        for x, y, sp in grove_points(g):
            out.append((x, y, sp, g["id"]))
    for p in t.get("points", []):
        out.append((p["at"][0], p["at"][1], p["species"], "point"))
    return out


# --- transforms ----------------------------------------------------------------------------------------------

def to_px(x, y):
    """Metres -> campus zone px (the 40 degree camera)."""
    return (x * PX_X, y * PX_Y)


def board_px(layout, x, y, scale=1.0):
    """Metres -> pixel in the north-up half-size board image (2048 x 1536), times `scale`."""
    b = layout["board"]
    s = b["m_per_px"]
    ox, oy = b["origin_px"]
    return ((x / s + ox) * scale, (y / s + oy) * scale)


def north_up_board(layout):
    """The board photo turned north-up and halved (2048 x 1536), as a PIL image."""
    from PIL import Image
    im = Image.open(ROOT / layout["board"]["image"]).convert("RGB").rotate(90, expand=True)
    return im.resize((im.size[0] // 2, im.size[1] // 2), Image.LANCZOS)


# --- validation ----------------------------------------------------------------------------------------------

def validate(layout):
    """Returns a list of problems (empty = valid)."""
    errs = []
    nums = sorted(s["num"] for s in layout["sites"])
    if nums != list(range(1, 28)):
        errs.append(f"sites must be numbered 1..27 exactly once (got {nums})")
    ids = [s["id"] for s in layout["sites"]] + [s["id"] for s in layout.get("structures", [])]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errs.append(f"duplicate ids: {sorted(dup)}")
    for s in layout["sites"]:
        if s.get("status") not in STATUS:
            errs.append(f"#{s['num']} {s['id']}: status must be one of {STATUS}")
        if not s.get("parts") and "monument" not in s:
            errs.append(f"#{s['num']} {s['id']}: no parts")
        for p in s.get("parts", []):
            try:
                pts = part_poly(p)
            except ValueError as e:
                errs.append(f"#{s['num']} {s['id']}: {e}")
                continue
            x0, y0, x1, y1 = bbox(pts)
            if x1 - x0 <= 0 or y1 - y0 <= 0:
                errs.append(f"#{s['num']} {s['id']}: degenerate part {p}")
            if p.get("h", 0) < 0:
                errs.append(f"#{s['num']} {s['id']}: negative height")
        for e in s.get("entrances", []):
            if not (isinstance(e.get("at"), list) and len(e["at"]) == 2 and e.get("to")):
                errs.append(f"#{s['num']} {s['id']}: entrance needs 'to' and 'at' [x, y]")
    for g in layout["ground"]:
        if g["surface"] not in SURFACES:
            errs.append(f"ground {g['id']}: unknown surface {g['surface']}")
    for r in layout["roads"]:
        if r["surface"] not in SURFACES:
            errs.append(f"road {r['id']}: unknown surface {r['surface']}")
        if len(r["points"]) < 2 or r["width"] <= 0:
            errs.append(f"road {r['id']}: needs >= 2 points and a positive width")
    boundary = layout["boundary"]["points"]
    for sp in layout.get("spawns", []):
        if not point_in_poly(*sp["at"], boundary):
            errs.append(f"spawn {sp['id']} is outside the campus wall")
    for s in layout["sites"]:
        for e in s.get("entrances", []):
            if not point_in_poly(*e["at"], boundary):
                errs.append(f"#{s['num']} entrance to {e['to']} is outside the campus wall")
    return errs


# --- canal: cut at road crossings (culverts) -------------------------------------------------------------------

def _seg_intersect(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-9:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return None


def road_crossings(layout):
    """[(point, half_gap)] where a road crosses the canal: a culvert carries the road over it."""
    out = []
    for r in layout["roads"]:
        for c in layout["canal"]:
            for i in range(len(r["points"]) - 1):
                for j in range(len(c["points"]) - 1):
                    p = _seg_intersect(r["points"][i], r["points"][i + 1], c["points"][j], c["points"][j + 1])
                    if p:
                        out.append((p, r["width"] / 2 + 0.6))
    return out


def split_for_gaps(a, b, crossings):
    pieces = [(tuple(a), tuple(b))]
    for (cx, cy), half in crossings:
        nxt = []
        for p, q in pieces:
            L = math.dist(p, q)
            if L < 1e-6:
                continue
            ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
            t = (cx - p[0]) * ux + (cy - p[1]) * uy
            perp = abs((cx - p[0]) * uy - (cy - p[1]) * ux)
            if perp < 2.0 and -half < t < L + half:
                if t - half > 0.3:
                    nxt.append((p, (p[0] + ux * (t - half), p[1] + uy * (t - half))))
                if L - (t + half) > 0.3:
                    nxt.append(((p[0] + ux * (t + half), p[1] + uy * (t + half)), q))
            else:
                nxt.append((p, q))
        pieces = nxt
    return pieces


def canal_pieces(layout):
    """Canal segments as (canal id, a, b, width), with gaps where roads cross."""
    crossings = road_crossings(layout)
    out = []
    for c in layout["canal"]:
        pts = c["points"]
        for i in range(len(pts) - 1):
            for a, b in split_for_gaps(pts[i], pts[i + 1], crossings):
                out.append((c["id"], a, b, c["width"]))
    return out


def canal_polys(layout):
    """Water polygons of the canal (each piece widened, with small overlaps so bends stay closed)."""
    polys = []
    for _cid, a, b, w in canal_pieces(layout):
        L = math.dist(a, b) or 1.0
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        a2 = (a[0] - ux * w * 0.5, a[1] - uy * w * 0.5)
        b2 = (b[0] + ux * w * 0.5, b[1] + uy * w * 0.5)
        polys += road_poly({"points": [a2, b2], "width": w})
    return polys

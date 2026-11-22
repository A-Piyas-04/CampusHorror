"""Writes the `campus` zone: the whole IUT campus as one seamless outdoor zone, from data/campus/campus_layout.json.

    python tools/zones/campus_world.py

Decisions D42-D44 (Docs/MAP_V2.md): north up, true scale, one zone. The layout file is the only input; edit it,
not the generated scene (scenes/world/Campus.tscn). Writes the scene, its profile, its validator manifest and the
registry entry, then regenerates the in-game map (assets/ui/campus_map.*), Docs/CAMPUS_MAP.md's registry and
map-design/.

Frame: layout metres (x east, y south) -> zone px (x * 32, y * 20.576); the zone origin is the layout origin.
Buildings: a site whose art exists (ART below) is placed as that prop; every other site is drawn by
scripts/world/campus_massing.gd from its real footprint and height, so the whole campus is walkable at true size.
"""

import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "campus"))
import layout as LAY  # noqa: E402
from scene_lib import (ASPHALT, DOOR, GRASS, LAMP, LIGHT_TEX, ROOT, SPAWN, WALKWAY, WATER, C, PV2, S, Scene,  # noqa: E402
                       V, fnum, register_zones, write_profile)

ZONE = "campus"
SCENE = "scenes/world/Campus.tscn"
WORN = "res://assets/sprites/ground/grass_worn_tile.png"
MASSING = "res://scripts/world/campus_massing.gd"
PALM = "res://scenes/props/vegetation/CoconutPalm.tscn"
BROADLEAF = "res://scenes/props/vegetation/BroadleafTree.tscn"
STREET_LAMP = "res://scenes/props/campus/StreetLampTall.tscn"
PLAZA_LAMP = "res://scenes/props/campus/PlazaLamp.tscn"
BENCH = "res://scenes/props/street_furniture/OutdoorBench.tscn"
MANIFEST = ROOT / "scenes/tests/zone_validation/manifests/campus.json"
## Rendered building art (Map v2 M4): data/campus/building_assets.json, written by
## assets/source/blender/tools/author_campus_v2.py. A site whose scene exists is placed as its art, with collision
## from the layout's exact footprints; any other site is still a massing model.
ASSET_MANIFEST = ROOT / "data/campus/building_assets.json"


def load_art():
    if not ASSET_MANIFEST.exists():
        return {}
    out = {}
    for a in json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))["assets"]:
        if (ROOT / a["scene"].replace("res://", "")).exists():
            out[a["site"]] = a
    return out


ART = load_art()

# surface -> (texture or None, tint, footstep surface via the texture)
GROUND = {
    "grass": (GRASS, (0.93, 1.0, 0.88)), "meadow": (GRASS, (0.80, 0.90, 0.72)), "field": (GRASS, (0.80, 0.97, 0.74)),
    "forest_floor": (WORN, (0.78, 0.84, 0.66)), "compound": (WALKWAY, (0.62, 0.58, 0.58)),
    "pavers": (WALKWAY, (1.0, 1.0, 1.0)), "pavers_dark": (WALKWAY, (0.80, 0.70, 0.68)),
    "brick_road": (WALKWAY, (1.0, 0.94, 0.90)), "brick_path": (WALKWAY, (0.92, 0.86, 0.82)), "asphalt": (ASPHALT, (1, 1, 1)),
    "concrete": (WALKWAY, (0.78, 0.80, 0.80)), "court_tennis": (None, (0.25, 0.44, 0.39)),
    "court_futsal": (None, (0.23, 0.37, 0.34)), "gravel": (WORN, (0.70, 0.68, 0.62)), "dirt": (WORN, (0.78, 0.62, 0.44)),
}
PALMS = {"coconut_palm", "areca_palm"}


def px(x, y):
    return (x * LAY.PX_X, y * LAY.PX_Y)


def pts_px(points):
    return [px(x, y) for x, y in points]


def offset_line(points, d):
    """The polyline moved d metres to the left of its direction of travel (mitred at the bends)."""
    def nrm(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        return (-dy / L, dx / L)
    out = []
    for i, p in enumerate(points):
        if i == 0:
            nx, ny = nrm(points[0], points[1])
        elif i == len(points) - 1:
            nx, ny = nrm(points[-2], points[-1])
        else:
            a, b = nrm(points[i - 1], p), nrm(p, points[i + 1])
            mx, my = a[0] + b[0], a[1] + b[1]
            ml = math.hypot(mx, my) or 1.0
            mx, my = mx / ml, my / ml
            k = 1.0 / max(mx * a[0] + my * a[1], 0.3)
            nx, ny = mx * k, my * k
        out.append((p[0] + nx * d, p[1] + ny * d))
    return out


def stripes(points, width, dash=None, gap=None, trim=(0.0, 0.0)):
    """Quads (metres) along a polyline: one per segment if continuous, else dash / gap by arc length (a dash over a
    bend splits in two). trim: metres left bare at the start and the end."""
    segs, total = [], 0.0
    for a, b in zip(points, points[1:]):
        L = math.dist(a, b)
        segs.append((a, b, total, L))
        total += L
    s0, s1 = trim[0], total - trim[1]
    if dash is None:
        spans = [(s0, s1)]
    else:
        spans, s = [], s0
        while s < s1:
            spans.append((s, min(s + dash, s1)))
            s += dash + gap
    quads = []
    for a, b, t0, L in segs:
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = -uy * width / 2, ux * width / 2
        for u0, u1 in spans:
            lo, hi = max(u0, t0), min(u1, t0 + L)
            if hi - lo < 0.05:
                continue
            p0 = (a[0] + ux * (lo - t0), a[1] + uy * (lo - t0))
            p1 = (a[0] + ux * (hi - t0), a[1] + uy * (hi - t0))
            quads.append([(p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny), (p0[0] - nx, p0[1] - ny)])
    return quads


class Campus:
    def __init__(self, lay):
        self.lay = lay
        self.s = Scene()
        self.s.node("Campus", "Node2D", None, props={
            "y_sort_enabled": "true", "script": self.s.res("res://scripts/world/zone.gd"), "zone_id": S(ZONE),
            "profile": self.s.res(f"res://data/zones/profiles/{ZONE}.tres", "Resource")})
        self.s.node("Ground", "Node2D", props={"z_index": "-10"})
        # Splat = what you see (one shader quad, D46); SurfaceLookup = invisible textured polygons that only tell the
        # footsteps (SurfaceMap) what is underfoot; Water and Overlays draw over the splat.
        self.s.node("Splat", "Polygon2D", "Ground")
        self.s.node("SurfaceLookup", "Node2D", "Ground", props={"visible": "false"})
        for g in ("Base", "Surfaces", "Roads"):
            self.s.node(g, "Node2D", "Ground/SurfaceLookup")
        self.s.node("Water", "Node2D", "Ground", props={"script": self.s.res("res://scripts/world/water_surface.gd")})
        self.s.node("Markings", "Node2D", "Ground")
        self.s.node("Objects", "Node2D", props={"y_sort_enabled": "true"})
        for g in ("Buildings", "Walls", "Props", "Vegetation", "Lights", "Doors", "SpawnMarkers", "Bounds"):
            self.s.node(g, "Node2D", "Objects", props={"y_sort_enabled": "true"})
        self._water_mat = None
        self._n = 0

    def uid(self, base):
        self._n += 1
        return f"{base}{self._n}"

    # --- ground ----------------------------------------------------------------------------------------------
    def poly(self, parent, name, points_m, surface):
        if surface == "water":
            if self._water_mat is None:
                meta = json.loads((ROOT / "assets/textures/ground/campus_ground.json").read_text(encoding="utf-8"))
                G = "res://assets/textures/ground/"
                self._water_mat = self.s.sub("ShaderMaterial", {
                    "shader": self.s.res("res://assets/shaders/water_v2.gdshader"),
                    "shader_parameter/water_tex": self.s.res(G + "campus_water.png", "Texture2D"),
                    "shader_parameter/brick_tex": self.s.res(G + "bank_brick.jpg", "Texture2D"),
                    "shader_parameter/noise_tex": self.s.res(G + "ground_noise.png", "Texture2D"),
                    "shader_parameter/mask_origin_m": V(meta["x0"], meta["y0"]),
                    "shader_parameter/mask_px_per_m": fnum(meta["water_px_per_m"]),
                    "shader_parameter/mask_size_px": V(*meta["water_size"])})
            self.s.node(name, "Polygon2D", parent, props={"polygon": PV2(pts_px(points_m)), "material": self._water_mat,
                                                           "light_mask": "1"})
            return
        tex, tint = GROUND[surface]
        props = {"polygon": PV2(pts_px(points_m)), "color": C(*tint), "light_mask": "1"}
        if tex:
            props.update({"texture": self.s.res(tex, "Texture2D"), "texture_repeat": "2", "texture_scale": V(4, 4)})
        self.s.node(name, "Polygon2D", parent, props=props)

    def splat(self):
        meta = json.loads((ROOT / "assets/textures/ground/campus_ground.json").read_text(encoding="utf-8"))
        x0, y0 = meta["x0"], meta["y0"]
        x1, y1 = x0 + meta["size"][0] / meta["px_per_m"], y0 + meta["size"][1] / meta["px_per_m"]
        G = "res://assets/textures/ground/"
        mat = self.s.sub("ShaderMaterial", {
            "shader": self.s.res("res://assets/shaders/ground_splat.gdshader"),
            "shader_parameter/albedo_array": self.s.res(G + "ground_albedo_array.jpg", "Texture2DArray"),
            "shader_parameter/normal_array": self.s.res(G + "ground_normal_array.jpg", "Texture2DArray"),
            "shader_parameter/splat_a": self.s.res(G + "campus_splat_a.png", "Texture2D"),
            "shader_parameter/splat_b": self.s.res(G + "campus_splat_b.png", "Texture2D"),
            "shader_parameter/shade_tex": self.s.res(G + "campus_shade.png", "Texture2D"),
            "shader_parameter/noise_tex": self.s.res(G + "ground_noise.png", "Texture2D"),
            "shader_parameter/water_tex": self.s.res(G + "campus_water.png", "Texture2D"),
            "shader_parameter/kerb_tex": self.s.res(G + "campus_kerb.png", "Texture2D")})
        # rewrite the placeholder node written in __init__ with its real properties
        self.s.nodes = [n for n in self.s.nodes if not n.startswith('[node name="Splat" type="Polygon2D" parent="Ground"]')]
        idx = next(i for i, n in enumerate(self.s.nodes) if n.startswith('[node name="Ground"'))
        props = {"polygon": PV2(pts_px([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])), "material": mat,
                 "script": self.s.res("res://scripts/world/ground_splat.gd"), "light_mask": "1"}
        body = "\n".join(f"{k} = {v}" for k, v in props.items())
        self.s.nodes.insert(idx + 1, f'[node name="Splat" type="Polygon2D" parent="Ground"]\n{body}\n')

    def ground(self):
        self.splat()
        for g in self.lay["ground"]:
            if g["surface"] in ("court_tennis", "court_futsal"):
                self.poly("Ground/Markings", "G_" + g["id"], LAY.ground_poly(g, self.lay), g["surface"])
                continue
            parent = "Ground/Water" if g["surface"] == "water" else "Ground/SurfaceLookup/Surfaces"
            self.poly(parent, "G_" + g["id"], LAY.ground_poly(g, self.lay), g["surface"])
        for i, seg in enumerate(LAY.canal_polys(self.lay)):        # cut where roads cross (culverts)
            self.poly("Ground/Water", f"Canal{i}", seg, "water")
        for r in self.lay["roads"]:
            for i, seg in enumerate(LAY.road_poly(r)):
                self.poly("Ground/SurfaceLookup/Roads", f"Road_{r['id']}_{i}", seg, r["surface"])
            for j, (x, y) in enumerate(r["points"][1:-1]):
                self.poly("Ground/SurfaceLookup/Roads", f"Road_{r['id']}_j{j}", LAY.circle_poly((x, y), r["width"] / 2, 12), r["surface"])
        self.markings()

    def markings(self):
        white = (0.95, 0.95, 0.92, 0.85)
        for f in self.lay.get("features", []):
            if f.get("kind") == "pitch":
                x0, y0, x1, y1 = f["rect"]
                self.line("Pitch", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], white, 2.5, closed=True)
                cy = (y0 + y1) / 2
                cx = (x0 + x1) / 2
                self.line("PitchHalf", [(x0, cy), (x1, cy)], white, 2.5)
                self.line("PitchCircle", LAY.circle_poly((cx, cy), 9.15, 28), white, 2.5, closed=True)
                for yy, s in ((y0, 1), (y1, -1)):
                    self.line("Box", [(cx - 20.15, yy), (cx - 20.15, yy + 16.5 * s), (cx + 20.15, yy + 16.5 * s), (cx + 20.15, yy)], white, 2.5)
                    self.line("Goal", [(cx - 3.66, yy), (cx - 3.66, yy - 1.2 * s), (cx + 3.66, yy - 1.2 * s), (cx + 3.66, yy)], (1, 1, 1, 1), 3.0)
            elif f.get("kind") == "worn_strip":
                self.poly("Ground/SurfaceLookup/Surfaces", "CricketStrip", LAY.rect_poly(f["rect"]), "dirt")
        for g in self.lay["ground"]:
            if g["surface"] in ("court_tennis", "court_futsal"):
                x0, y0, x1, y1 = g["rect"]
                self.line("Court", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], white, 2.0, closed=True)
                cy = (y0 + y1) / 2
                self.line("CourtNet" if g["surface"] == "court_tennis" else "CourtHalf", [(x0, cy), (x1, cy)], white, 2.0)
        self.road_paint()

    def paint(self, name, quads_m, color):
        """One antialiased Polygon2D holding many painted quads (metres), in worn road paint."""
        if not quads_m:
            return
        verts, polys = [], []
        for q in quads_m:
            polys.append("PackedInt32Array(" + ", ".join(str(len(verts) + k) for k in range(len(q))) + ")")
            verts += q
        self.s.node(name, "Polygon2D", "Ground/Markings", props={
            "polygon": PV2(pts_px(verts)), "polygons": "[" + ", ".join(polys) + "]", "color": C(*color),
            "antialiased": "true", "material": self.paint_mat(), "light_mask": "1"})

    def road_paint(self):
        """Paint on the asphalt (the gate road and the highway outside the wall): lane and edge lines, a zebra
        crossing and a speed breaker just inside the Main Gate. Brick roads carry no paint."""
        white, yellow, black = (0.93, 0.93, 0.88, 0.92), (0.93, 0.72, 0.12, 0.92), (0.07, 0.07, 0.07, 0.9)
        for r in self.lay["roads"]:
            if r["surface"] != "asphalt":
                continue
            pts, hw = r["points"], r["width"] / 2
            self.paint(f"Paint_{r['id']}_centre", stripes(pts, 0.12, 3.0, 4.5, trim=(5.0, 3.0)), white)
            edges = stripes(offset_line(pts, hw - 0.3), 0.1, trim=(5.0, 3.0)) + \
                stripes(offset_line(pts, -(hw - 0.3)), 0.1, trim=(5.0, 3.0))
            self.paint(f"Paint_{r['id']}_edges", edges, white)
        r4 = next((r for r in self.lay["roads"] if r["id"] == "R4"), None)
        if r4:
            y, hw = r4["points"][-1][1], r4["width"] / 2
            zx = 457.0                                            # zebra crossing in front of the security booth
            zebra = [[(zx, y + o - 0.25), (zx + 3.0, y + o - 0.25), (zx + 3.0, y + o + 0.25), (zx, y + o + 0.25)]
                     for o in [k - (hw - 0.6) for k in range(int(2 * (hw - 0.6)) + 1)]]
            self.paint("Paint_R4_zebra", zebra, white)
            bx = 449.0                                            # speed breaker: yellow and black bands
            ys = [y - hw + 0.2 + k * 0.6 for k in range(int((2 * hw - 0.4) / 0.6))]
            self.paint("Paint_R4_breaker_y", [[(bx, a), (bx + 1.2, a), (bx + 1.2, a + 0.6), (bx, a + 0.6)] for a in ys[0::2]], yellow)
            self.paint("Paint_R4_breaker_k", [[(bx, a), (bx + 1.2, a), (bx + 1.2, a + 0.6), (bx, a + 0.6)] for a in ys[1::2]], black)
        hwy = self.lay.get("highway")
        if hwy:
            pts, W, M = hwy["points"], hwy["width"] / 2, hwy.get("median", 1.4) / 2
            c = (hwy["width"] - hwy.get("median", 1.4)) / 2
            for s, side in ((1, "E"), (-1, "W")):
                self.paint(f"Paint_HWY_median_{side}", stripes(offset_line(pts, s * (M + 0.25)), 0.12), yellow)
                self.paint(f"Paint_HWY_lanes_{side}", stripes(offset_line(pts, s * (M + c / 2)), 0.15, 3.0, 6.0), white)
                self.paint(f"Paint_HWY_edge_{side}", stripes(offset_line(pts, s * (W - 0.3)), 0.15), white)

    def paint_mat(self):
        if getattr(self, "_paint_mat", None) is None:
            self._paint_mat = self.s.sub("ShaderMaterial", {
                "shader": self.s.res("res://assets/shaders/road_paint.gdshader"),
                "shader_parameter/noise_tex": self.s.res("res://assets/textures/ground/ground_noise.png", "Texture2D")})
        return self._paint_mat

    def line(self, base, points_m, color, width, closed=False):
        props = {"points": PV2(pts_px(points_m)), "width": fnum(width), "default_color": C(*color), "light_mask": "1",
                 "material": self.paint_mat(), "antialiased": "true"}
        if closed:
            props["closed"] = "true"
        self.s.node(self.uid(base), "Line2D", "Ground/Markings", props=props)

    # --- solids ----------------------------------------------------------------------------------------------
    def seg_wall(self, name, a, b, thickness_m=0.6, parent="Objects/Bounds"):
        (ax, ay), (bx, by) = px(*a), px(*b)
        L = math.hypot(bx - ax, by - ay)
        if L < 1.0:
            return
        shape = self.s.sub("RectangleShape2D", {"size": V(L, thickness_m * LAY.PX_X)})
        body = self.s.node(name, "StaticBody2D", parent, props={"collision_mask": "0"})
        self.s.node("Shape", "CollisionShape2D", body, props={
            "position": V((ax + bx) / 2, (ay + by) / 2), "rotation": fnum(math.atan2(by - ay, bx - ax)), "shape": shape})

    def solids(self):
        b = self.lay["boundary"]["points"]
        body = self.s.node("CampusWall", "StaticBody2D", "Objects/Bounds", props={"collision_mask": "0"})
        self.s.node("Shape", "CollisionPolygon2D", body, props={"build_mode": "1", "polygon": PV2(pts_px(b))})
        for g in self.lay["ground"]:
            if g["surface"] == "water":
                wb = self.s.node("Lake_" + g["id"], "StaticBody2D", "Objects/Bounds", props={"collision_mask": "0"})
                self.s.node("Shape", "CollisionPolygon2D", wb, props={"polygon": PV2(pts_px(LAY.ground_poly(g, self.lay)))})
        crossings = road_crossings(self.lay)
        for c in self.lay["canal"]:
            pts = c["points"]
            for i in range(len(pts) - 1):
                for j, (a, bb) in enumerate(split_for_gaps(pts[i], pts[i + 1], crossings)):
                    self.seg_wall(f"Canal_{c['id']}_{i}_{j}", a, bb, c["width"])
        # the visible campus wall: modelled brick-and-barbed-wire modules (author_infra_v2.py) every 4 m along it,
        # oriented to each run; massing until those renders exist. The Main Gate's opening stays clear.
        gate = next((s for s in self.lay["sites"] if s["id"] == "main_gate"), None)
        gate_box = LAY.bbox([q for poly in LAY.site_polys(gate) for q in poly]) if gate else None
        n = 0
        for i in range(len(b)):
            a, bb = b[i], b[(i + 1) % len(b)]
            L = math.dist(a, bb)
            if L < 0.5:
                continue
            ux, uy = (bb[0] - a[0]) / L, (bb[1] - a[1]) / L
            d = "ew" if abs(uy) < 0.38 else "ns" if abs(ux) < 0.38 else ("se" if ux * uy > 0 else "ne")
            path = f"scenes/props/campus_v2/V2Wall{d.capitalize()}.tscn"
            if not (ROOT / path).exists():
                self.massing(f"Wall{i}", "Objects/Walls", wall_poly(a, bb, 0.45), 2.4, "plain_brick", casts_shadow=False, solid=False)
                continue
            count = max(1, math.ceil(L / 4.0))
            for k in range(count):
                s = (k + 0.5) / count
                x, y = a[0] + (bb[0] - a[0]) * s, a[1] + (bb[1] - a[1]) * s
                if gate_box and gate_box[0] - 3 <= x <= gate_box[2] + 6 and gate_box[1] + 1.5 <= y <= gate_box[3] - 1.5:
                    continue
                n += 1
                self.s.node(f"Wall{n}", None, "Objects/Walls", instance="res://" + path, props={"position": V(*px(x, y))})
        # fences around proposed plots, with a gate gap on the south side
        for st in self.lay["sites"]:
            if st.get("status") == "proposed" and st.get("plot"):
                x0, y0, x1, y1 = st["plot"]
                cx = (x0 + x1) / 2
                for k, (a, bb) in enumerate([((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x0, y0), (x0, y1)),
                                              ((x0, y1), (cx - 2.0, y1)), ((cx + 2.0, y1), (x1, y1))]):
                    self.seg_wall(f"PlotFence_{st['id']}_{k}", a, bb, 0.3)

    # --- buildings -------------------------------------------------------------------------------------------
    def massing(self, name, parent, poly_m, height_m, style, status="built", casts_shadow=True, solid=True, label=""):
        pp = pts_px(poly_m)
        sx = sum(p[0] for p in pp) / len(pp)
        sy = max(p[1] for p in pp)
        local = [(x - sx, y - sy) for x, y in pp]
        props = {"position": V(sx, sy), "script": self.s.res(MASSING), "footprint": PV2(local), "height_m": fnum(height_m),
                 "style": f'&"{style}"', "status": f'&"{status}"'}
        if not casts_shadow:
            props["casts_shadow"] = "false"
        if not solid:
            props["solid"] = "false"
        if label:
            props["label"] = S(label)
        return self.s.node(name, "Node2D", parent, props=props)

    def art(self, st, group):
        """The rendered building, plus collision from the layout's own footprints (exact, not the render's)."""
        a = ART[st["id"]]
        self.s.node("Art", None, group, instance=a["scene"], props={"position": V(*px(*a["centre_m"]))})
        if st.get("status") == "proposed" or st["id"] == "car_parking":
            return                       # plots are fenced by solids(); the sheds are walked under
        parts = st.get("parts") or []
        for i, poly in enumerate(LAY.site_polys(st)):
            part = parts[i] if i < len(parts) else {}
            if part.get("solid") is False:
                continue
            body = self.s.node(f"Solid{i}", "StaticBody2D", group, props={"collision_mask": "0"})
            self.s.node("Shape", "CollisionPolygon2D", body, props={"polygon": PV2(pts_px(poly))})

    def buildings(self):
        for st in self.lay["sites"] + self.lay.get("structures", []):
            sid = "".join(w.capitalize() for w in st["id"].split("_"))
            if st["id"] in ART:
                group = self.s.node(sid, "Node2D", "Objects/Buildings", props={
                    "y_sort_enabled": "true", "metadata/site": S(st["id"]), "metadata/num": str(st.get("num", 0)),
                    "metadata/name": S(st["name"])})
                self.art(st, group)
                continue
            group = self.s.node(sid, "Node2D", "Objects/Buildings", props={
                "y_sort_enabled": "true", "metadata/site": S(st["id"]), "metadata/num": str(st.get("num", 0)),
                "metadata/name": S(st["name"])})
            style = st.get("style", "plain_brick")
            status = st.get("status", "built")
            if status == "proposed":
                plot = st.get("plot") or LAY.bbox([p for q in LAY.site_polys(st) for p in q])
                self.massing("Plot", group, LAY.rect_poly(plot), 1.9, "plot", status, casts_shadow=False, solid=False,
                             label=st["name"])
                continue
            parts = st.get("parts") or []
            polys = LAY.site_polys(st)
            for i, poly in enumerate(polys):
                part = parts[i] if i < len(parts) else {}
                h = part.get("h", st.get("monument", {}).get("h", 6.0))
                pstyle = "monument" if "monument" in st else style
                role = part.get("role", "")
                if "canopy" in role or "bridge" in role:
                    pstyle = "utility" if "bridge" in role else "metal_canopy"
                self.massing(f"Part{i}", group, poly, h, pstyle, status, label=f"{st['name']} {role}".strip())

    # --- vegetation, lights, doors ---------------------------------------------------------------------------
    def trees(self):
        """Each layout species gets its own rendered tree (variants mixed for palms); a species whose render doesn't
        exist yet falls back to the classic palm / broadleaf."""
        rnd = __import__("random").Random(42)
        veg = "scenes/props/vegetation/"
        species = {"coconut_palm": ["CoconutPalm", "PalmLeaning", "PalmTall"], "areca_palm": ["PalmAreca"],
                   "rain_tree": ["TreeRain"], "mahogany": ["TreeMahogany"], "mango": ["TreeMango"],
                   "krishnachura": ["TreeKrishnachura"]}
        for i, (x, y, sp, src) in enumerate(LAY.all_trees(self.lay)):
            options = [s for s in species.get(sp, []) if (ROOT / f"{veg}{s}.tscn").exists()]
            if not options:
                options = ["CoconutPalm"] if "palm" in sp else ["BroadleafTree"]
            scene = "res://" + veg + rnd.choice(options) + ".tscn"
            s = rnd.uniform(0.88, 1.12)
            props = {"position": V(*px(x, y)), "scale": V(s * (-1 if rnd.random() < 0.5 else 1), s)}
            self.s.node(f"Tree{i}_{sp}", None, "Objects/Vegetation", instance=scene, props=props)

    def lamp(self, name, x, y, scene=STREET_LAMP, color=(1.0, 0.80, 0.55), energy=0.95, scale=3.0, height=220.0):
        """A lamp post and its light. `height` (px) lifts the light above the ground so it rakes across the
        normal-mapped ground, kerbs and water instead of grazing them flat (2D normal mapping needs it)."""
        self.s.node(name, None, "Objects/Props", instance=scene, props={"position": V(*px(x, y))})
        self.s.node(name + "Light", "PointLight2D", "Objects/Lights", props={
            "height": fnum(height),
            "position": V(*px(x, y)), "color": C(*color), "energy": fnum(energy), "range_item_cull_mask": "3",
            "texture": self.s.res(LIGHT_TEX, "Texture2D"), "texture_scale": fnum(scale), "script": self.s.res(LAMP),
            "needs_power": "false", "base_energy": fnum(energy)})

    def lamps(self):
        n = 0
        for r in self.lay["roads"]:
            if r["id"][0] not in "RL" or r["surface"] == "concrete":
                continue
            spacing = 26.0 if r["id"].startswith("R") else 34.0
            for k, (x, y) in enumerate(LAY.along(r["points"], spacing)[1:-1]):
                dx, dy = road_dir(r["points"], (x, y))
                side = 1 if k % 2 == 0 else -1
                off = r["width"] / 2 + 0.9
                lx, ly = x - dy * off * side, y + dx * off * side
                if self.blocked(lx, ly):
                    continue
                n += 1
                self.lamp(f"Lamp{n}", lx, ly)
        # the plaza: low lamps around the Mosque forecourt
        for k, (x, y) in enumerate([(205, 125), (262, 147), (268, 185), (233, 156), (190, 140), (300, 118)]):
            self.lamp(f"PlazaLamp{k}", x, y, PLAZA_LAMP, (1.0, 0.86, 0.66), 0.8, 2.2, height=150.0)
        # a warm light over every entrance, so doors read at night
        for st in self.lay["sites"]:
            for e in st.get("entrances", []):
                x, y = e["at"]
                self.s.node(f"EntryLight_{e['to']}", "PointLight2D", "Objects/Lights", props={
                    "position": V(*px(x, y)), "height": "110", "color": C(1.0, 0.88, 0.68), "energy": "0.7", "range_item_cull_mask": "3",
                    "texture": self.s.res(LIGHT_TEX, "Texture2D"), "texture_scale": "1.3", "script": self.s.res(LAMP),
                    "needs_power": "false", "base_energy": "0.7", "gameplay": "false"})

    def blocked(self, x, y):
        for st in self.lay["sites"] + self.lay.get("structures", []):
            for poly in LAY.site_polys(st):
                bx0, by0, bx1, by1 = LAY.bbox(poly)
                if bx0 - 1.0 <= x <= bx1 + 1.0 and by0 - 1.0 <= y <= by1 + 1.0:
                    return True
        for g in self.lay["ground"]:
            if g["surface"] == "water" and LAY.point_in_poly(x, y, LAY.ground_poly(g, self.lay)):
                return True
        return not LAY.point_in_poly(x, y, self.lay["boundary"]["points"])

    def doors(self):
        for st in self.lay["sites"]:
            for e in st.get("entrances", []):
                if not e.get("spawn"):
                    continue
                x, y = e["at"]
                ox, oy = {"south": (0, 1.8), "north": (0, -1.8), "east": (1.8, 0), "west": (-1.8, 0)}[e.get("face", "south")]
                self.s.node("Door_" + e["to"], None, "Objects/Doors", instance=DOOR, props={
                    "position": V(*px(x, y)), "destination_zone_id": S(e["to"]), "destination_spawn_id": S(e["spawn"]),
                    "verb": S(e.get("verb", "Enter")), "place_name": S(e.get("place", st["name"])), "show_placeholder": "false"})
                self.spawn(e["exit_spawn"], x + ox, y + oy)
                # (no threshold slab: every entrance is modelled in the building art, with its own stepped plinth)
        for sp in self.lay.get("spawns", []):
            self.spawn(sp["id"], *sp["at"])

    def spawn(self, sid, x, y):
        self.s.node("Spawn_" + sid, None, "Objects/SpawnMarkers", instance=SPAWN, props={"position": V(*px(x, y)), "spawn_id": S(sid)})

    def infra(self):
        """Modelled water edges (author_infra_v2.py): bridge balustrades along the causeways, a low brick parapet
        along every other lake edge, on the land side; none where a building stands in the water."""
        def scene(kind, d):
            path = f"scenes/props/campus_v2/V2{kind.capitalize()}{d.capitalize()}.tscn"
            return "res://" + path if (ROOT / path).exists() else None
        causeways = [poly for r in self.lay["roads"] if r["id"].startswith("C") for poly in LAY.road_poly(r)]
        footprints = [poly for st in self.lay["sites"] for poly in LAY.site_polys(st)]
        n = 0
        for g in self.lay["ground"]:
            if g["surface"] != "water":
                continue
            poly = LAY.ground_poly(g, self.lay)
            for i in range(len(poly)):
                a, b = poly[i], poly[(i + 1) % len(poly)]
                L = math.dist(a, b)
                if L < 2.0:
                    continue
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                nx, ny = -uy, ux
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                if LAY.point_in_poly(mx + nx * 0.5, my + ny * 0.5, poly):
                    nx, ny = -nx, -ny                       # point the normal at the land
                lx, ly = mx + nx * 0.8, my + ny * 0.8
                if any(LAY.point_in_poly(lx, ly, f) for f in footprints):
                    continue
                kind = "bridge" if any(LAY.point_in_poly(lx, ly, c) for c in causeways) else "parapet"
                d = "ew" if abs(uy) < 0.2 else "ns" if abs(ux) < 0.2 else ("se" if ux * uy > 0 else "ne")
                sc = scene(kind, d)
                if sc is None:
                    continue
                count = max(1, math.ceil(L / 4.0))
                for k in range(count):
                    s = (k + 0.5) / count
                    px_, py_ = a[0] + (b[0] - a[0]) * s + nx * 0.22, a[1] + (b[1] - a[1]) * s + ny * 0.22
                    n += 1
                    self.s.node(f"Edge{n}", None, "Objects/Walls", instance=sc, props={"position": V(*px(px_, py_))})
        for (cx, cy), half in LAY.road_crossings(self.lay):          # the canal bridge's balustrades
            sc = scene("bridge", "ew")
            if sc:
                for side in (-1, 1):
                    n += 1
                    self.s.node(f"Edge{n}", None, "Objects/Walls", instance=sc,
                                props={"position": V(*px(cx, cy + side * 1.75))})
        print(f"campus: {n} water-edge modules")

    def reflections(self):
        """Lakeside buildings mirrored in the water: each layer sprite of their rendered scene copied upside down
        about its own base line (lowered by twice the bank, the water sits 0.6 m under the land), as a child of every
        lake polygon it overlaps, which clips it (CanvasItem.clip_children)."""
        import re as _re
        sites = {"mosque", "auditorium", "cafeteria_library", "five_fundamentals"}
        lakes = [g for g in self.lay["ground"] if g["surface"] == "water"]
        mat = None
        n = 0
        for sid in sites:
            a = ART.get(sid)
            if a is None:
                continue
            text = (ROOT / a["scene"].replace("res://", "")).read_text(encoding="utf-8")
            ext = dict((m.group(2), m.group(1)) for m in _re.finditer(r'\[ext_resource [^\]]*path="([^"]+)" id="([^"]+)"\]', text))
            ax, ay = px(*a["centre_m"])
            for blk in _re.split(r"\n(?=\[node )", text):
                m = _re.match(r'\[node name="([^"]+)" type="Sprite2D" parent="\."\]', blk)
                if not m or m.group(1) == "Sprite":
                    continue
                pos = _re.search(r"position = Vector2\(([-\d.e]+), ([-\d.e]+)\)", blk)
                off = _re.search(r"offset = Vector2\(([-\d.e]+), ([-\d.e]+)\)", blk)
                sc = _re.search(r"scale = Vector2\(([-\d.e]+), ([-\d.e]+)\)", blk)
                tex = _re.search(r'texture = ExtResource\("([^"]+)"\)', blk)
                if not (off and sc and tex):
                    continue
                ly = float(pos.group(2)) if pos else 0.0
                base_x, base_y = ax, ay + ly + 2 * 0.6 * 24.513
                k = float(sc.group(1))
                h_px = -float(off.group(2)) * k
                for lake in lakes:
                    x0, y0, x1, y1 = LAY.bbox(LAY.ground_poly(lake, self.lay))
                    (lx0, ly0), (lx1, ly1) = px(x0, y0), px(x1, y1)
                    w_px = -float(off.group(1)) * k
                    if base_x + w_px < lx0 - 50 or base_x - w_px - 4000 > lx1 or base_y > ly1 or base_y + h_px < ly0:
                        continue
                    if mat is None:
                        mat = self.s.sub("ShaderMaterial", {"shader": self.s.res("res://assets/shaders/reflection.gdshader")})
                    n += 1
                    self.s.node(f"Reflection{n}", "Sprite2D", f"Ground/Water/G_{lake['id']}", props={
                        "position": V(base_x, base_y), "scale": V(k, -k), "centered": "false",
                        "offset": V(float(off.group(1)), float(off.group(2))),
                        "texture": self.s.res(ext[tex.group(1)], "Texture2D"), "material": mat, "light_mask": "1",
                        "texture_filter": "4"})
        if n:
            for lake in lakes:   # the lake polygons clip their reflections
                tag = f'[node name="G_{lake["id"]}" type="Polygon2D" parent="Ground/Water"]'
                self.s.nodes = [nd.replace(tag, tag + "\nclip_children = 2") if nd.startswith(tag) else nd
                                for nd in self.s.nodes]
        print(f"campus: {n} reflections")

    def night_windows(self):
        """Lit windows: every building layer whose `<layer>_night.png` exists (tools/campus/night_windows.py) gets it as
        a child sprite with the unshaded night_windows material, faded in by the global `night_level`."""
        import re as _re
        mat = None
        n = 0
        for sid, a in ART.items():
            st = next((s for s in self.lay["sites"] + self.lay.get("structures", []) if s["id"] == sid), None)
            if st is None:
                continue
            group = "Objects/Buildings/" + "".join(w.capitalize() for w in sid.split("_")) + "/Art"
            text = (ROOT / a["scene"].replace("res://", "")).read_text(encoding="utf-8")
            ext = dict((m.group(2), m.group(1)) for m in _re.finditer(r'\[ext_resource [^\]]*path="([^"]+)" id="([^"]+)"\]', text))
            for blk in _re.split(r"\n(?=\[node )", text):
                m = _re.match(r'\[node name="([^"]+)" type="Sprite2D" parent="\."\]', blk)
                if not m or m.group(1) == "Sprite":
                    continue
                off = _re.search(r"offset = Vector2\(([-\d.e]+), ([-\d.e]+)\)", blk)
                tex = _re.search(r'texture = ExtResource\("([^"]+)"\)', blk)
                if not (off and tex):
                    continue
                night = ext[tex.group(1)].replace(".png", "_night.png")
                if not (ROOT / night.replace("res://", "")).exists():
                    continue
                if mat is None:
                    mat = self.s.sub("ShaderMaterial", {"shader": self.s.res("res://assets/shaders/night_windows.gdshader")})
                n += 1
                self.s.node("NightWindows", "Sprite2D", f"{group}/{m.group(1)}", props={
                    "centered": "false", "offset": V(float(off.group(1)), float(off.group(2))),
                    "texture": self.s.res(night, "Texture2D"), "material": mat, "texture_filter": "4"})
        print(f"campus: {n} night-window sprites")

    def ambience(self):
        """Fireflies after dusk over the woods, the lake edges and the halls' lawn; leaves drifting from the woods by day
        (scripts/world/ambient_particles.gd)."""
        glow = self.s.sub("CanvasItemMaterial", {"blend_mode": "1", "light_mode": "1"})     # additive, unshaded
        leaf_mat = self.s.sub("CanvasItemMaterial", {})
        ramp = self.s.sub("Gradient", {"offsets": "PackedFloat32Array(0, 0.2, 0.75, 1)",
                                       "colors": "PackedColorArray(0.7, 1, 0.4, 0, 0.85, 1, 0.45, 1, 0.75, 1, 0.4, 0.9, 0.6, 0.9, 0.3, 0)"})
        leaf_ramp = self.s.sub("Gradient", {"offsets": "PackedFloat32Array(0, 0.15, 0.85, 1)",
                                            "colors": "PackedColorArray(0.45, 0.36, 0.16, 0, 0.5, 0.4, 0.18, 1, 0.42, 0.3, 0.14, 1, 0.4, 0.3, 0.14, 0)"})
        tex = self.s.res(LIGHT_TEX, "Texture2D")
        spots = [((128, 175), (30, 58), 70), ((60, 75), (24, 22), 24), ((245, 236), (70, 3), 30), ((300, 140), (20, 4), 16),
                 ((350, 51), (70, 6), 34), ((390, 200), (45, 45), 30), ((60, 260), (30, 15), 18)]
        for k, ((cx, cy), (hx, hy), amount) in enumerate(spots):
            self.s.node(f"Fireflies{k}", "CPUParticles2D", "Objects/Props", props={
                "position": V(*px(cx, cy)), "z_index": "5", "material": glow, "amount": str(amount), "lifetime": "7.0",
                "preprocess": "7.0", "texture": tex, "emission_shape": "3", "emission_rect_extents": V(hx * 32, hy * 20.576),
                "direction": V(0, -1), "spread": "180.0", "gravity": V(0, 0), "initial_velocity_min": "4.0",
                "initial_velocity_max": "12.0", "angular_velocity_min": "-30.0", "angular_velocity_max": "30.0",
                "scale_amount_min": "0.025", "scale_amount_max": "0.05", "color_ramp": ramp,
                "script": self.s.res("res://scripts/world/ambient_particles.gd"), "when": "0"})
        for k, (cx, cy) in enumerate([(110, 140), (140, 180), (120, 220), (150, 125), (60, 70)]):
            self.s.node(f"Leaves{k}", "CPUParticles2D", "Objects/Props", props={
                "position": V(*px(cx, cy - 6)), "z_index": "5", "material": leaf_mat, "amount": "10", "lifetime": "9.0",
                "preprocess": "9.0", "texture": tex, "emission_shape": "3", "emission_rect_extents": V(14 * 32, 6 * 20.576),
                "direction": V(0.4, 1), "spread": "25.0", "gravity": V(3, 9), "initial_velocity_min": "6.0",
                "initial_velocity_max": "14.0", "angular_velocity_min": "-90.0", "angular_velocity_max": "90.0",
                "scale_amount_min": "0.02", "scale_amount_max": "0.035", "color_ramp": leaf_ramp,
                "script": self.s.res("res://scripts/world/ambient_particles.gd"), "when": "1"})

    def courts(self):
        """The modelled courts (author_courts_v2.py): their surface lies on the ground band, nets, goals and fences
        Y-sort. The flat court polygons are then dropped from the visible ground."""
        mf = ROOT / "data/campus/court_assets.json"
        if not mf.exists():
            return
        placed = 0
        for a in json.loads(mf.read_text(encoding="utf-8"))["assets"]:
            if (ROOT / a["scene"].replace("res://", "")).exists():
                self.s.node(a["asset_id"].replace("v2_", "").title().replace("_", ""), None, "Objects/Props",
                            instance=a["scene"], props={"position": V(*px(*a["centre_m"]))})
                placed += 1
        if placed:
            self.s.nodes = [n for n in self.s.nodes if not (n.startswith('[node name="G_') and 'parent="Ground/Markings"' in n
                                                            and ("court" in n.split('"')[1]))]
            self.s.nodes = [n for n in self.s.nodes if not ((n.startswith('[node name="Court') or n.startswith('[node name="Goal'))
                                                            and 'parent="Ground/Markings"' in n)]
        print(f"campus: {placed} courts")

    def benches(self):
        spots = [(300, 47.0), (350, 47.0), (395, 47.0), (300, 55.4), (350, 55.4), (395, 55.4),  # halls avenue
                 (190, 246.5), (240, 246.5), (290, 246.5),                                       # boulevard
                 (215, 118.0), (285, 117.5)]                                                     # plaza
        for k, (x, y) in enumerate(spots):
            self.s.node(f"Bench{k}", None, "Objects/Props", instance=BENCH, props={"position": V(*px(x, y))})

    def write(self):
        self.s.write(SCENE)


# --- geometry helpers ----------------------------------------------------------------------------------------

def segments(points, width):
    return LAY.road_poly({"points": points, "width": width})


def wall_poly(a, b, t):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * t / 2, dx / L * t / 2
    return [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]


def road_dir(points, at):
    best, d = None, 1e9
    for i in range(len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dd = math.dist((mx, my), at)
        if dd < d:
            L = math.hypot(x1 - x0, y1 - y0) or 1.0
            best, d = ((x1 - x0) / L, (y1 - y0) / L), dd
    return best


def seg_intersect(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-9:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return None


def road_crossings(lay):
    """Points where a road crosses the canal (a culvert / bridge: the canal's collision leaves a gap there)."""
    out = []
    for r in lay["roads"]:
        for c in lay["canal"]:
            for i in range(len(r["points"]) - 1):
                for j in range(len(c["points"]) - 1):
                    p = seg_intersect(r["points"][i], r["points"][i + 1], c["points"][j], c["points"][j + 1])
                    if p:
                        out.append((p, r["width"] / 2 + 0.6))
    return out


def split_for_gaps(a, b, crossings):
    pieces = [(a, b)]
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


def main():
    lay = LAY.load()
    errs = LAY.validate(lay)
    if errs:
        raise SystemExit("layout problems:\n  " + "\n  ".join(errs))
    z = Campus(lay)
    z.ground()
    z.solids()
    z.buildings()
    z.trees()
    z.lamps()
    z.benches()
    z.infra()
    z.reflections()
    z.night_windows()
    z.ambience()
    z.courts()
    z.doors()
    z.write()
    bx0, by0, bx1, by1 = LAY.bbox(lay["boundary"]["points"])
    (px0, py0), (px1, py1) = px(bx0, by0), px(bx1, by1)
    pb = [int(px0), int(py0), int(px1 - px0), int(py1 - py0)]
    m = 700
    write_profile(ZONE, zoom=2.0, limits=(pb[0] - m, pb[1] - m, pb[2] + 2 * m, pb[3] + 2 * m), surface="grass",
                  ambience="night_field", vol=-8.0, night=(0.13, 0.15, 0.26), look=56.0)
    MANIFEST.write_text(json.dumps({
        "zone_id": ZONE,
        "notes": "The whole IUT campus as one seamless outdoor zone (Map v2, D44), generated by tools/zones/campus_world.py "
                 "from data/campus/campus_layout.json. North up, true scale (D42, D43).",
        "playable_bounds": pb, "walks": []}, indent="\t") + "\n", encoding="utf-8")
    register_zones({ZONE: "res://" + SCENE})
    import map_registry
    import export_map_design
    import ui_map
    ui_map.main()
    map_registry.main()
    export_map_design.main()


if __name__ == "__main__":
    main()

"""Exports the whole campus as an editable design into map-design/.

    python tools/zones/export_map_design.py

Source of truth: data/campus/campus_layout.json (traced from the official IUT campus board, D42-D44). The generated
game scenes add what only the game knows: doors, spawns and collision of the `campus` zone, and every interior room.

Writes map-design/campus_map.svg (true scale, 1 unit = 1 m, north up, one layer per kind of thing), interiors.svg,
campus_map.json (the same data as text) and campus_map.png (preview). **Owner layers survive**: any top-level SVG
layer whose id or label starts with "owner" is read from the existing file and written back unchanged; so is the
"owner_additions" list in campus_map.json.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "campus"))
from map_registry import nodes, registry, unq  # noqa: E402
import layout as LAY  # noqa: E402
import map_render  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "map-design"
PX_X, PX_Y = LAY.PX_X, LAY.PX_Y
EXTERIORS = {"campus"}
LEGACY_EXTERIORS = {"main_gate_exterior", "central_plaza", "halls_exterior", "academic_exterior"}
SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"
XL_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("inkscape", INK_NS)
ET.register_namespace("xlink", XL_NS)


def hexc(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])


SURF_HEX = {k: hexc(v) for k, v in map_render.COL.items() if isinstance(v, tuple)}


def V(s):
    mm = re.match(r"Vector2\(([-\d.e]+),\s*([-\d.e]+)\)", s or "")
    return (float(mm.group(1)), float(mm.group(2))) if mm else (0.0, 0.0)


def PV(s):
    nums = [float(x) for x in re.findall(r"[-\d.e]+", (s or "").split("(", 1)[-1])]
    return list(zip(nums[0::2], nums[1::2]))


def m(x, y):
    return (round(x / PX_X, 2), round(y / PX_Y, 2))


def config_index():
    idx = {}
    for p in (ROOT / "assets/source/blender/configs").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        g = d.get("godot", {})
        scene = f"res://scenes/props/{d.get('category')}/{g.get('scene_name')}.tscn"
        fp = d.get("generator_params", {}).get("footprint_m") or d.get("footprint_m")
        idx[scene] = {"asset": d["asset_id"], "category": d.get("category"), "footprint": fp, "desc": d.get("description", "")}
    return idx


def walk(scene_path):
    """Every node of a zone scene with its zone-local position (parents' positions summed)."""
    pos = {}
    out = []
    for name, parent, inst, props in nodes(scene_path):
        path = "." if parent is None else (name if parent == "." else f"{parent}/{name}")
        base = (0.0, 0.0) if parent in (None, ".") else pos.get(parent, (0.0, 0.0))
        lx, ly = V(props.get("position"))
        pos[path] = (base[0] + lx, base[1] + ly)
        out.append({"name": name, "path": path, "parent": parent, "inst": inst, "props": props, "pos": pos[path]})
    return out


# --- collect (game side) -----------------------------------------------------------------------------------

def collect_game():
    reg = registry()
    cfg = config_index()
    game = {"zones": [], "doors": [], "spawns": [], "solids": [], "interiors": []}
    for zid, scene in sorted(reg.items()):
        p = ROOT / scene.replace("res://", "")
        if not p.exists():
            continue
        exterior = zid in EXTERIORS
        kind = "exterior" if exterior else ("legacy exterior (retired, D44)" if zid in LEGACY_EXTERIORS else "interior")
        game["zones"].append({"id": zid, "kind": kind, "scene": scene.replace("res://", "")})
        if zid in LEGACY_EXTERIORS:
            continue
        text = p.read_text(encoding="utf-8")
        shapes = dict((mm.group(1), V(mm.group(2))) for mm in re.finditer(
            r'\[sub_resource type="RectangleShape2D" id="([^"]+)"\]\s*size = (Vector2\([^)]*\))', text))
        room = None if exterior else {"zone": zid, "props": [], "doors": [], "spawns": [], "story": [], "threats": []}
        for it in walk(p):
            inst, props, (px, py) = it["inst"], it["props"], it["pos"]
            rec = {"zone": zid, "name": it["name"]}
            sh = re.search(r'SubResource\("([^"]+)"\)', props.get("shape", ""))
            if exterior and sh and sh.group(1) in shapes:
                w, h = shapes[sh.group(1)]
                game["solids"].append({"name": it["path"].replace("Objects/", ""),
                                       "rect_m": [*m(px - w / 2, py - h / 2), *m(px + w / 2, py + h / 2)]})
                continue
            if inst and inst.endswith("Door.tscn"):
                rec.update(at_m=list(m(px, py)), place=unq(props.get("place_name", '""')),
                           to=f"{unq(props.get('destination_zone_id'))}:{unq(props.get('destination_spawn_id'))}",
                           lock=unq(props.get("required_item", '""')) or unq(props.get("requires_flag", '""')))
                (game["doors"] if exterior else room["doors"]).append(rec)
            elif inst and inst.endswith("SpawnMarker.tscn"):
                rec.update(spawn=unq(props.get("spawn_id")), at_m=list(m(px, py)))
                (game["spawns"] if exterior else room["spawns"]).append(rec)
            elif room is not None and inst and any(inst.endswith(k) for k in ("Readable.tscn", "Examine.tscn", "Pickup.tscn",
                                                                             "Keypad.tscn", "HideSpot.tscn")):
                label = unq(props.get("title") or props.get("object_name") or props.get("item_name")
                            or props.get("place_name") or '""') or it["name"]
                rec.update(kind=Path(inst).stem.lower(), label=label, at_m=list(m(px, py)))
                room["story"].append(rec)
            elif room is not None and inst and inst.endswith("NightGuard.tscn"):
                pts = [m(px, py)] if not props.get("patrol_points") else [m(a, b) for a, b in PV(props["patrol_points"])]
                rec.update(at_m=list(m(px, py)), patrol_m=[list(q) for q in pts],
                           chapter=int(unq(props.get("metadata/chapter", "1")) or 1))
                room["threats"].append(rec)
            elif room is not None and inst and inst in cfg:
                c = cfg[inst]
                fp = c["footprint"] or [-0.5, 0.5, -0.5, 0.5]
                cx, cy = px / PX_X, py / PX_Y
                rect = [round(cx + fp[0], 2), round(cy - fp[3], 2), round(cx + fp[1], 2), round(cy - fp[2], 2)]
                rec.update(asset=c["asset"], category=c["category"], rect_m=rect, desc=c["desc"])
                if c["category"] == "interiors":
                    room.update(asset=c["asset"], rect_m=rect, desc=c["desc"],
                                size_m=[round(fp[1] - fp[0], 2), round(fp[3] - fp[2], 2)])
                else:
                    room["props"].append(rec)
        if room is not None and room.get("asset"):
            game["interiors"].append(room)
    return game


def host_index(lay):
    """interior zone id -> the campus site whose entrance leads into it."""
    out = {}
    for s in lay["sites"]:
        for e in s.get("entrances", []):
            if e.get("to"):
                out[e["to"]] = f"#{s['num']} {s['name']}"
    return out


# --- SVG ---------------------------------------------------------------------------------------------------

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def owner_layers(path):
    if not path.exists():
        return []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        print(f"WARNING: {path.name} could not be parsed; owner layers were NOT carried over (a copy is kept)")
        path.with_suffix(".unreadable.svg").write_bytes(path.read_bytes())
        return []
    keep = []
    for g in tree.getroot():
        ident = (g.get("id") or "") + " " + (g.get(f"{{{INK_NS}}}label") or "")
        if g.tag == f"{{{SVG_NS}}}g" and re.search(r"(^|\s)owner", ident, re.I):
            keep.append(ET.tostring(g, encoding="unicode"))
    return keep


def layer(ident, label, body, hidden=False, extra=""):
    style = ' style="display:none"' if hidden else ""
    return (f'<g id="{ident}" inkscape:groupmode="layer" inkscape:label="{esc(label)}"{style}{extra}>\n'
            + "\n".join(body) + "\n</g>")


def pts_attr(pts):
    return " ".join(f"{a:.2f},{b:.2f}" for a, b in pts)


def poly(pts, fill, stroke="none", sw=0.0, extra="", title=None):
    t = f"<title>{esc(title)}</title>" if title else ""
    return f'<polygon points="{pts_attr(pts)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}>{t}</polygon>'


def rect(r, fill, stroke="none", sw=0.0, extra=""):
    x0, y0, x1, y1 = r
    return (f'<rect x="{min(x0, x1):.2f}" y="{min(y0, y1):.2f}" width="{abs(x1 - x0):.2f}" height="{abs(y1 - y0):.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>')


def label(x, y, s, size=2.2, fill="#111", anchor="middle", weight="normal", extra=""):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, sans-serif" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{extra}>{esc(s)}</text>')


def campus_svg(lay, game):
    x0, y0, x1, y1 = map_render.extent(lay)
    panel = 92.0
    W, H = (x1 - x0) + panel, (y1 - y0)
    b = lay["board"]
    s = b["m_per_px"]
    bx, by = -b["origin_px"][0] * s, -b["origin_px"][1] * s
    L = {}
    L["reference"] = [f'<image xlink:href="reference/board_north_up.jpg" href="reference/board_north_up.jpg" x="{bx:.2f}" '
                      f'y="{by:.2f}" width="{2048 * s:.2f}" height="{1536 * s:.2f}" preserveAspectRatio="none" opacity="0.55">'
                      '<title>The official IUT campus board (photo), turned north-up and aligned</title></image>']
    L["ground"] = [rect([x0, y0, x1, y1], SURF_HEX["outside"])]
    for g in lay["ground"]:
        if g["surface"] == "water":
            continue
        L["ground"].append(poly(LAY.ground_poly(g, lay), SURF_HEX.get(g["surface"], "#7fae4a"),
                                title=f'{g.get("name") or g["id"]} ({LAY.SURFACES[g["surface"]][2]})'))
    for f in lay.get("features", []):
        if f.get("kind") == "pitch":
            r = f["rect"]
            L["ground"].append(rect(r, "none", "#f0f0f0", 0.25))
            cy = (r[1] + r[3]) / 2
            L["ground"].append(f'<path d="M{r[0]},{cy} H{r[2]}" stroke="#f0f0f0" stroke-width="0.25"/>')
            L["ground"].append(f'<circle cx="{(r[0] + r[2]) / 2}" cy="{cy}" r="9.15" fill="none" stroke="#f0f0f0" stroke-width="0.25"/>')
        elif f.get("kind") == "worn_strip":
            L["ground"].append(rect(f["rect"], SURF_HEX["dirt"]))
    L["water"] = []
    for g in lay["ground"]:
        if g["surface"] == "water":
            L["water"].append(poly(LAY.ground_poly(g, lay), SURF_HEX["water"], SURF_HEX["water_edge"], 0.5, title=g.get("name")))
    for c in lay["canal"]:
        L["water"].append(f'<polyline points="{pts_attr(c["points"])}" fill="none" stroke="{SURF_HEX["canal"]}" '
                          f'stroke-width="{c["width"]}" stroke-linejoin="round"><title>Canal ({c["id"]})</title></polyline>')
    L["roads"] = []
    for r in lay["roads"]:
        L["roads"].append(f'<polyline points="{pts_attr(r["points"])}" fill="none" stroke="{SURF_HEX.get(r["surface"])}" '
                          f'stroke-width="{r["width"]}" stroke-linejoin="round" stroke-linecap="butt">'
                          f'<title>{esc(r["id"] + ": " + r["name"] + " (" + LAY.SURFACES[r["surface"]][2] + f", {r['width']} m)")}</title></polyline>')
    L["trees"] = []
    for x, y, sp, src in LAY.all_trees(lay):
        palm = sp in map_render.PALMS
        L["trees"].append(f'<circle cx="{x}" cy="{y}" r="{2.6 if palm else 3.6}" fill="{"#4e9646" if palm else "#346832"}" '
                          f'opacity="0.9"><title>{esc(sp.replace("_", " "))} ({esc(src)})</title></circle>')
    L["buildings"] = []
    for st in lay["sites"] + lay.get("structures", []):
        status = st.get("status", "built")
        fill = {"proposed": "#ba78c8", "under_construction": "#c49654"}.get(status, SURF_HEX["roof"])
        desc = f'{"#" + str(st["num"]) + " " if "num" in st else ""}{st["name"]} - {status.replace("_", " ")}'
        for i, pp in enumerate(LAY.site_polys(st)):
            part = (st.get("parts") or [{}] * 99)[i] if i < len(st.get("parts") or []) else {}
            h = part.get("h") if isinstance(part, dict) else None
            role = part.get("role") if isinstance(part, dict) else None
            t = desc + (f"; {role}" if role else "") + (f"; height {h:g} m" if h else "") + (f'. {st["note"]}' if st.get("note") else "")
            extra = ' fill-opacity="0.55" stroke-dasharray="1.2,0.8"' if status == "proposed" else ""
            L["buildings"].append(poly(pp, fill, SURF_HEX["roof_edge"], 0.3, extra, t))
        if st.get("plot"):
            L["buildings"].append(rect(st["plot"], "none", "#8c3ca0", 0.35, ' stroke-dasharray="2,1.2"'))
    bpts = lay["boundary"]["points"]
    L["boundary"] = [f'<polygon points="{pts_attr(bpts)}" fill="none" stroke="#f0f0ec" stroke-width="1.0" stroke-dasharray="2.2,1.2">'
                     '<title>Campus wall (east side: the Dhaka-Mymensingh highway)</title></polygon>']
    L["doors"] = []
    for st in lay["sites"]:
        for e in st.get("entrances", []):
            x, y = e["at"]
            L["doors"].append(f'<circle cx="{x}" cy="{y}" r="1.1" fill="#ffd23f" stroke="#000" stroke-width="0.2">'
                              f'<title>Entrance: #{st["num"]} {esc(st["name"])} -> {esc(e["to"])}</title></circle>')
    for dd in game["doors"]:
        x, y = dd["at_m"]
        L["doors"].append(f'<circle cx="{x}" cy="{y}" r="0.6" fill="#ff9f1c" stroke="#000" stroke-width="0.15">'
                          f'<title>Game door {esc(dd["name"])} -> {esc(dd["to"])}</title></circle>')
    L["spawns"] = []
    for sp in lay.get("spawns", []) + [{"id": s["spawn"], "at": s["at_m"]} for s in game["spawns"]]:
        x, y = sp["at"]
        L["spawns"].append(f'<path d="M{x - 0.8},{y} h1.6 M{x},{y - 0.8} v1.6" stroke="#ff4fd8" stroke-width="0.3"><title>{esc(sp["id"])}</title></path>')
    L["solids"] = [rect(q["rect_m"], "#000000", "#000000", 0.15, ' fill-opacity="0.22"').replace(
        "/>", f"><title>{esc(q['name'])}</title></rect>") for q in game["solids"]]
    L["labels"] = []
    for g in lay["ground"]:
        if g.get("name") and g["surface"] in ("field", "meadow"):
            gx0, gy0, gx1, gy1 = LAY.bbox(LAY.ground_poly(g, lay))
            L["labels"].append(label((gx0 + gx1) / 2, (gy0 + gy1) / 2, g["name"].upper(), 6, "#ffffff", weight="bold", extra=' opacity="0.85"'))
    for st in lay["sites"]:
        allp = [pt for q in LAY.site_polys(st) for pt in q]
        sx0, sy0, sx1, sy1 = LAY.bbox(allp)
        cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
        L["labels"].append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="3.0" fill="#ffffff" stroke="#60301e" stroke-width="0.3"/>')
        L["labels"].append(label(cx, cy + 1.25, str(st["num"]), 3.4, "#3c1e18", weight="bold"))
    legend = [rect([x1 + 4, y0 + 8, x1 + panel - 4, y0 + 8 + 4 + 3.6 * 34], "#ffffff", "#000", 0.3, ' opacity="0.95"'),
              label(x1 + 7, y0 + 14, "IUT campus - from the official board", 3.0, "#000", "start", "bold")]
    yy = y0 + 20
    for st in sorted(lay["sites"], key=lambda q: q["num"]):
        legend.append(label(x1 + 7, yy, f'{st["num"]}. {st["name"]}', 2.4, "#000", "start"))
        yy += 3.6
    yy += 2
    for c, t in ((SURF_HEX["roof"], "building"), ("#c49654", "under construction"), ("#ba78c8", "proposed (plot)"),
                 ("#ffd23f", "entrance into a building"), ("#ff4fd8", "spawn (arrival point)"), (SURF_HEX["canal"], "canal")):
        legend += [rect([x1 + 7, yy - 2.2, x1 + 10, yy + 0.4], c, "#000", 0.15), label(x1 + 12, yy, t, 2.3, "#000", "start")]
        yy += 3.6
    yy += 4
    legend += [f'<path d="M{x1 + 7},{yy} h50" stroke="#fff" stroke-width="0.8"/>', label(x1 + 32, yy - 1.5, "50 m", 2.6, "#fff"),
               f'<path d="M{x1 + 75},{yy + 14} l3,-9 l3,9 l-3,-2 z" fill="#fff"/>', label(x1 + 78, yy + 18, "N (true north)", 2.4, "#fff")]
    grid = []
    for gx in range(int(x0 // 50) * 50, int(x1) + 1, 50):
        grid.append(f'<path d="M{gx},{y0} V{y1}" stroke="#ffffff" stroke-width="0.15" opacity="0.3"/>')
        grid.append(label(gx + 0.5, y0 + 3, f"{gx} m", 1.8, "#ffffff", "start"))
    for gy in range(int(y0 // 50) * 50, int(y1) + 1, 50):
        grid.append(f'<path d="M{x0},{gy} H{x1}" stroke="#ffffff" stroke-width="0.15" opacity="0.3"/>')
        grid.append(label(x0 + 0.5, gy - 0.5, f"{gy} m", 1.8, "#ffffff", "start"))
    order = [("layer-ground", "Ground", "ground", False), ("layer-water", "Water and canal", "water", False),
             ("layer-roads", "Roads and paths", "roads", False), ("layer-trees", "Trees", "trees", False),
             ("layer-buildings", "Buildings (numbered as on the board)", "buildings", False),
             ("layer-boundary", "Campus wall", "boundary", False),
             ("layer-reference", "Reference: official board (photo, aligned; switch on to compare)", "reference", True),
             ("layer-solids", "Game: collision", "solids", True), ("layer-doors", "Entrances and game doors", "doors", False),
             ("layer-spawns", "Spawns", "spawns", False), ("layer-labels", "Labels and numbers", "labels", False)]
    body = [layer(i, lab, L[k], hidden) for i, lab, k, hidden in order]
    body.append(layer("layer-grid", "Grid (50 m)", grid))
    body.append(layer("layer-legend", "Legend", legend))
    return W, H, x0, y0, body


def write_svg(path, W, H, x0, y0, body, title):
    owners = owner_layers(path)
    if not owners:
        owners = [layer("owner-additions", "Owner additions (yours: never overwritten)",
                        ['<desc>Draw new areas, buildings and notes in this layer, or add more layers whose name starts with "owner".</desc>'])]
    svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="{SVG_NS}" xmlns:inkscape="{INK_NS}" xmlns:xlink="{XL_NS}" '
           f'width="{W * 5:.0f}" height="{H * 5:.0f}" viewBox="{x0:.2f} {y0:.2f} {W:.2f} {H:.2f}">\n'
           f'<title>{esc(title)}</title>\n' + "\n".join(body) + "\n" + "\n".join(owners) + "\n</svg>\n")
    path.write_text(svg, encoding="utf-8")


def interiors_svg(rooms, hosts):
    cols, gap = 4, 8.0
    x, y, row_h = 0.0, 0.0, 0.0
    placed = []
    for i, r in enumerate(rooms):
        w, dpt = r["size_m"]
        if i and i % cols == 0:
            x, y, row_h = 0.0, y + row_h + gap + 8, 0.0
        placed.append((r, x, y))
        x += max(w, 18) + gap
        row_h = max(row_h, dpt)
    body = []
    for r, ox, oy in placed:
        rx0, ry0, rx1, ry1 = r["rect_m"]

        def T(px, py):
            return (ox + (px - rx0), oy + 6 + (py - ry0))
        a, b = T(rx0, ry0)
        c, dd = T(rx1, ry1)
        body.append(rect([a, b, c, dd], "#e9e4d8", "#222", 0.25))
        body.append(label(a, b - 2.6, f'{r["zone"]}  ({r["size_m"][0]:g} x {r["size_m"][1]:g} m)', 1.6, "#000", "start", "bold"))
        body.append(label(a, b - 0.8, "in " + hosts.get(r["zone"], "(reached from another room)"), 1.2, "#5a3a20", "start"))
        for p in r["props"]:
            pr = p["rect_m"]
            p0, p1 = T(pr[0], pr[1]), T(pr[2], pr[3])
            body.append(rect([*p0, *p1], "#9a8f7a", "#444", 0.08).replace("/>", f"><title>{esc(p['asset'])}</title></rect>"))
        for door in r["doors"]:
            px, py = T(*door["at_m"])
            body.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="0.45" fill="#ffd23f" stroke="#000" stroke-width="0.1"/>')
            body.append(label(px, py - 0.7, door["to"].split(":")[0] + (" (locked in story mode)" if door["lock"] else ""), 0.8, "#7a5a00"))
        for st in r["story"]:
            px, py = T(*st["at_m"])
            body.append(f'<path d="M{px:.2f},{py - 0.5:.2f} l0.5,0.5 l-0.5,0.5 l-0.5,-0.5 z" fill="#ff8c42"/>')
            body.append(label(px, py + 1.2, st["label"], 0.7, "#8a3a00"))
    W = cols * (30 + gap)
    H = max((oy for _, _, oy in placed), default=0) + 40
    return W, H, -4.0, -6.0, [layer("layer-rooms", "Rooms (generated from the game)", body)]


# --- JSON --------------------------------------------------------------------------------------------------

def campus_json(lay, game, hosts):
    sites = []
    for st in sorted(lay["sites"], key=lambda q: q["num"]):
        parts = st.get("parts") or []
        sites.append({"num": st["num"], "id": st["id"], "name": st["name"], "status": st["status"],
                      "aka": st.get("aka"), "height_m": max((p.get("h", 0) for p in parts), default=None),
                      "footprints_m": [[[round(a, 2), round(b, 2)] for a, b in q] for q in LAY.site_polys(st)],
                      "entrances": st.get("entrances", []), "note": st.get("note"), "placeholder": st.get("placeholder", False)})
    return {
        "schema": 2,
        "generated_by": "tools/zones/export_map_design.py from data/campus/campus_layout.json and the game scenes",
        "frame": lay["frame"], "board": lay["board"], "boundary": lay["boundary"], "canal": lay["canal"],
        "sites": sites, "structures": lay.get("structures", []), "ground": lay["ground"], "roads": lay["roads"],
        "trees": [{"at_m": [x, y], "species": sp, "group": src} for x, y, sp, src in LAY.all_trees(lay)],
        "features": lay.get("features", []), "spawns": lay.get("spawns", []),
        "zones": game["zones"],
        "game": {"campus_doors": game["doors"], "campus_spawns": game["spawns"], "campus_solids": game["solids"]},
        "interiors": [dict(r, host=hosts.get(r["zone"])) for r in game["interiors"]],
    }


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "new-areas").mkdir(exist_ok=True)
    (OUT / "reference").mkdir(exist_ok=True)
    lay = LAY.load()
    errs = LAY.validate(lay)
    if errs:
        print("layout problems:\n  " + "\n  ".join(errs))
    if not (OUT / "reference/board_north_up.jpg").exists():
        LAY.north_up_board(lay).save(OUT / "reference/board_north_up.jpg", quality=88)
    game = collect_game()
    hosts = host_index(lay)
    W, H, x0, y0, body = campus_svg(lay, game)
    write_svg(OUT / "campus_map.svg", W, H, x0, y0, body, "IUT campus - map design (generated from the board layout; owner layers kept)")
    iw, ih, ix0, iy0, ibody = interiors_svg(game["interiors"], hosts)
    write_svg(OUT / "interiors.svg", iw, ih, ix0, iy0, ibody, "IUT campus - interiors (generated; owner layers kept)")
    jpath = OUT / "campus_map.json"
    owner = []
    if jpath.exists():
        try:
            owner = json.loads(jpath.read_text(encoding="utf-8")).get("owner_additions", [])
        except json.JSONDecodeError:
            jpath.with_suffix(".unreadable.json").write_bytes(jpath.read_bytes())
            print("WARNING: campus_map.json could not be parsed; kept a copy, owner_additions reset")
    data = campus_json(lay, game, hosts)
    data["owner_additions"] = owner or [{"example": "delete me", "name": "New area name", "kind": "building | area | path | note",
                                         "rect_m": [0, 0, 10, 10], "notes": "what it is, photos in map-design/new-areas/"}]
    jpath.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    img, _ = map_render.render(lay, px_per_m=4.0, legend=True, title="IUT campus - map design")
    img.save(OUT / "campus_map.png")
    print(f"map-design: {len(lay['sites'])} sites, {len(lay.get('structures', []))} structures, {len(lay['roads'])} roads, "
          f"{len(data['trees'])} trees; game: {len(game['zones'])} zones, {len(game['doors'])} campus doors, "
          f"{len(game['interiors'])} interiors")


if __name__ == "__main__":
    main()

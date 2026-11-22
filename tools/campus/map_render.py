"""Renders the campus layout as a clean, board-style raster map (PIL, supersampled).

Used for map-design/campus_map.png (the preview) and for the in-game campus map screen (assets/ui/campus_map.png),
so both always show the same campus as data/campus/campus_layout.json.
"""

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402

# board-like palette (the official board: brown roofs, beige roads, bright lawns, blue water)
COL = {
    "outside": (46, 52, 54), "outside_hatch": (58, 64, 66),
    "grass": (132, 186, 74), "meadow": (86, 136, 66), "field": (74, 128, 58), "forest_floor": (104, 146, 70),
    "compound": (108, 98, 92), "pavers": (150, 86, 70), "pavers_dark": (112, 70, 60),
    "brick_road": (232, 214, 196), "brick_path": (196, 150, 128), "asphalt": (92, 94, 98), "concrete": (206, 204, 196),
    "court_tennis": (64, 110, 98), "court_futsal": (58, 92, 84), "gravel": (150, 144, 132), "dirt": (168, 138, 100),
    "water": (74, 132, 176), "water_edge": (140, 190, 220), "canal": (70, 170, 215),
    "wall": (240, 240, 236), "roof": (178, 104, 86), "roof_edge": (96, 52, 42), "roof_tall": (160, 88, 72),
    "proposed": (186, 120, 200), "construction": (196, 150, 84), "shadow": (0, 0, 0, 70),
    "tree": (52, 104, 50), "tree_edge": (28, 64, 30), "palm": (78, 150, 70), "label": (255, 255, 255),
    "badge": (255, 255, 255), "badge_text": (60, 30, 24), "lines": (240, 240, 240),
}
PALMS = {"coconut_palm", "areca_palm"}


def _font(size, bold=False):
    from PIL import ImageFont
    for name in (("arialbd.ttf", "DejaVuSans-Bold.ttf") if bold else ("arial.ttf", "DejaVuSans.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def extent(lay, margin=12.0):
    xs = [p[0] for p in lay["boundary"]["points"]]
    ys = [p[1] for p in lay["boundary"]["points"]]
    return min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin


def render(lay=None, px_per_m=4.0, labels=True, numbers=True, legend=False, ss=2, title=None):
    """Returns (PIL image RGB, (x0, y0, px_per_m)) so callers can map metres to pixels: px = (x - x0) * k."""
    from PIL import Image, ImageDraw, ImageFilter
    lay = lay or L.load()
    x0, y0, x1, y1 = extent(lay)
    k = px_per_m * ss
    panel = 82.0 if legend else 0.0             # legend column to the east of the map, never over it
    W, H = int((x1 - x0 + panel) * k), int((y1 - y0) * k)
    im = Image.new("RGB", (W, H), COL["outside"])
    d = ImageDraw.Draw(im, "RGBA")

    def P(pts):
        return [((x - x0) * k, (y - y0) * k) for x, y in pts]

    # outside: faint diagonal hatch (the town beyond the wall)
    for i in range(-H, W, int(6 * k)):
        d.line([(i, 0), (i + H, H)], fill=COL["outside_hatch"], width=max(1, int(0.6 * k)))
    # ground, painter's order
    for g in lay["ground"]:
        d.polygon(P(L.ground_poly(g, lay)), fill=COL.get(g["surface"], COL["grass"]))
    # pitch lines
    for f in lay.get("features", []):
        if f.get("kind") == "pitch":
            r = f["rect"]
            lw = max(1, int(0.25 * k))
            d.rectangle(P([(r[0], r[1]), (r[2], r[3])]), outline=COL["lines"], width=lw)
            cy = (r[1] + r[3]) / 2
            d.line(P([(r[0], cy), (r[2], cy)]), fill=COL["lines"], width=lw)
            cx = (r[0] + r[2]) / 2
            rr = 9.15 * k
            ccx, ccy = (cx - x0) * k, (cy - y0) * k
            d.ellipse([ccx - rr, ccy - rr, ccx + rr, ccy + rr], outline=COL["lines"], width=lw)
            for yy, s in ((r[1], 1), (r[3], -1)):
                d.rectangle(P([(cx - 20.15, yy), (cx + 20.15, yy + s * 16.5)]) if s > 0 else
                            P([(cx - 20.15, yy + s * 16.5), (cx + 20.15, yy)]), outline=COL["lines"], width=lw)
        elif f.get("kind") == "worn_strip":
            d.rectangle(P([(f["rect"][0], f["rect"][1]), (f["rect"][2], f["rect"][3])]), fill=COL["dirt"])
    # water edge highlight
    for g in lay["ground"]:
        if g["surface"] == "water":
            d.polygon(P(L.ground_poly(g, lay)), outline=COL["water_edge"], width=max(1, int(0.5 * k)))
    # canal
    for c in lay["canal"]:
        d.line(P(c["points"]), fill=COL["canal"], width=max(1, int(c["width"] * k)), joint="curve")
    # roads (polygons + round joins)
    for r in lay["roads"]:
        col = COL.get(r["surface"], COL["brick_road"])
        for poly in L.road_poly(r):
            d.polygon(P(poly), fill=col)
        rad = r["width"] / 2 * k
        for x, y in r["points"][1:-1]:          # round joins only; road ends stay square
            cx, cy = (x - x0) * k, (y - y0) * k
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=col)
    # building drop shadows (soft, to the south-east as on the board)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    off = 1.4 * k
    for s in lay["sites"] + lay.get("structures", []):
        if s.get("status") == "proposed":
            continue
        for poly in L.site_polys(s):
            sd.polygon([(a + off, b + off) for a, b in P(poly)], fill=(0, 0, 0, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(1.2 * k))
    im.paste(sh, (0, 0), sh)
    d = ImageDraw.Draw(im, "RGBA")
    # trees (under roofs is wrong; trees go over ground, under labels)
    for x, y, sp, _src in L.all_trees(lay):
        cx, cy = (x - x0) * k, (y - y0) * k
        if sp in PALMS:
            rr = 2.6 * k
            for a in range(6):
                t = a * math.pi / 3
                d.line([(cx, cy), (cx + math.cos(t) * rr, cy + math.sin(t) * rr)], fill=COL["palm"], width=max(1, int(0.9 * k)))
            d.ellipse([cx - 0.6 * k, cy - 0.6 * k, cx + 0.6 * k, cy + 0.6 * k], fill=COL["tree_edge"])
        else:
            rr = 3.6 * k
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=COL["tree"], outline=COL["tree_edge"], width=max(1, int(0.4 * k)))
    # buildings
    for s in lay["sites"] + lay.get("structures", []):
        st = s.get("status", "built")
        fill = {"proposed": COL["proposed"] + (110,), "under_construction": COL["construction"] + (255,)}.get(st, COL["roof"] + (255,))
        for p, poly in zip(s.get("parts", []) or [{}] * 99, L.site_polys(s)):
            tall = p.get("h", 0) >= 20 if isinstance(p, dict) else False
            f = (COL["roof_tall"] + (255,)) if (tall and st == "built") else fill
            if st == "proposed":
                d.polygon(P(poly), fill=f, outline=(140, 70, 160, 255), width=max(1, int(0.35 * k)))
            else:
                d.polygon(P(poly), fill=f, outline=COL["roof_edge"] + (255,), width=max(1, int(0.3 * k)))
    # boundary wall
    b = lay["boundary"]["points"]
    d.line(P(b + [b[0]]), fill=COL["wall"], width=max(1, int(1.0 * k)), joint="curve")
    # labels
    if labels:
        big = _font(int(5.5 * k), bold=True)
        for g in lay["ground"]:
            if g.get("name") and g["surface"] in ("field", "meadow", "water"):
                bx0, by0, bx1, by1 = L.bbox(L.ground_poly(g, lay))
                txt = g["name"].upper().replace("LAKE (", "LAKE  (") if g["surface"] != "water" else "LAKE"
                d.text((((bx0 + bx1) / 2 - x0) * k, ((by0 + by1) / 2 - y0) * k), txt, fill=(255, 255, 255, 220),
                       font=big, anchor="mm", stroke_width=max(1, int(0.3 * k)), stroke_fill=(0, 0, 0, 120))
    if numbers:
        fnt = _font(int(3.6 * k), bold=True)
        for s in lay["sites"]:
            polys = L.site_polys(s)
            if s.get("parts"):
                main = max(polys, key=lambda q: (L.bbox(q)[2] - L.bbox(q)[0]) * (L.bbox(q)[3] - L.bbox(q)[1]))
            else:
                main = [pt for q in polys for pt in q]
            bx0, by0, bx1, by1 = L.bbox(main)
            cx, cy = ((bx0 + bx1) / 2 - x0) * k, ((by0 + by1) / 2 - y0) * k
            rr = 3.0 * k
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=COL["badge"] + (235,), outline=COL["roof_edge"] + (255,), width=max(1, int(0.3 * k)))
            d.text((cx, cy), str(s["num"]), fill=COL["badge_text"], font=fnt, anchor="mm")
    if title:
        d.text((int(4 * k), int(3 * k)), title, fill=(255, 255, 255), font=_font(int(6 * k), bold=True))
    if legend:
        _legend(d, lay, k, W, H)
    if ss > 1:
        im = im.resize((W // ss, H // ss), Image.LANCZOS)
    return im, (x0, y0, px_per_m)


def _legend(d, lay, k, W, H):
    fnt = _font(int(2.6 * k))
    rows = [f"{s['num']}. {s['name']}" for s in sorted(lay["sites"], key=lambda s: s["num"])]
    lh = 3.4 * k
    bw, bh = 76 * k, (len(rows) + 2) * lh
    x, y = W - bw - 3 * k, 10 * k
    d.rectangle([x, y, x + bw, y + bh], fill=(255, 255, 255, 225), outline=(0, 0, 0, 255))
    d.text((x + 2 * k, y + 1.2 * k), "IUT campus (from the official board)", fill=(0, 0, 0), font=_font(int(2.8 * k), bold=True))
    for i, t in enumerate(rows):
        d.text((x + 2 * k, y + (i + 1.5) * lh), t, fill=(0, 0, 0), font=fnt)


if __name__ == "__main__":
    img, frame = render(legend=True, title="IUT campus")
    out = L.ROOT / "map-design/campus_map.png"
    img.save(out)
    print("wrote", out, img.size, frame)

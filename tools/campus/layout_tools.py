"""Campus layout tools.

    python tools/campus/layout_tools.py validate   # schema and sanity checks
    python tools/campus/layout_tools.py overlay    # map-design/reference/board_overlay.png (layout over the board)
    python tools/campus/layout_tools.py check      # per-site agreement with the board's building pixels (IoU)

`check` exits 1 when a built site measured on the board scores below --min-iou (default 0.75).
"""

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402

OUT_DIR = L.ROOT / "map-design/reference"
SKIP_CHECK = {"main_gate", "medical_laundry", "five_fundamentals"}  # off the photo, or not a solid footprint


def cmd_validate(lay, _args):
    errs = L.validate(lay)
    for e in errs:
        print("ERROR:", e)
    trees = L.all_trees(lay)
    print(f"layout: {len(lay['sites'])} sites, {len(lay.get('structures', []))} structures, {len(lay['roads'])} roads, "
          f"{len(lay['ground'])} ground regions, {len(trees)} trees -> {'OK' if not errs else f'{len(errs)} problem(s)'}")
    return 1 if errs else 0


def _draw_layout(lay, im, scale=1.0, fill_alpha=70):
    from PIL import ImageDraw, ImageFont
    over = im.convert("RGBA")
    layer = __import__("PIL.Image", fromlist=["Image"]).new("RGBA", over.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    P = lambda pts: [L.board_px(lay, x, y, scale) for x, y in pts]  # noqa: E731
    try:
        font = ImageFont.truetype("arialbd.ttf", int(15 * scale))
    except OSError:
        font = ImageFont.load_default()
    d.line(P(lay["boundary"]["points"] + [lay["boundary"]["points"][0]]), fill=(255, 255, 255, 255), width=max(1, int(3 * scale)))
    for c in lay["canal"]:
        d.line(P(c["points"]), fill=(0, 200, 255, 255), width=max(1, int(2 * scale)))
    for r in lay["roads"]:
        for poly in L.road_poly(r):
            d.polygon(P(poly), outline=(255, 230, 0, 230))
    for g in lay["ground"]:
        if g["surface"] == "water":
            d.polygon(P(L.ground_poly(g, lay)), outline=(0, 90, 255, 255))
    for s in lay["sites"] + lay.get("structures", []):
        colour = {"under_construction": (255, 150, 0), "proposed": (200, 0, 255)}.get(s.get("status"), (255, 0, 60))
        for poly in L.site_polys(s):
            d.polygon(P(poly), outline=colour + (255,), fill=colour + (fill_alpha,))
        if "num" in s:
            xs = [x for poly in L.site_polys(s) for x, _ in poly]
            ys = [y for poly in L.site_polys(s) for _, y in poly]
            cx, cy = L.board_px(lay, (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, scale)
            d.text((cx, cy), str(s["num"]), fill=(255, 255, 0, 255), font=font, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for x, y, _sp, _src in L.all_trees(lay):
        cx, cy = L.board_px(lay, x, y, scale)
        rr = 1.6 * scale
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(0, 255, 120, 255))
    for e in [e for s in lay["sites"] for e in s.get("entrances", [])]:
        cx, cy = L.board_px(lay, *e["at"], scale)
        rr = 3 * scale
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 220, 0, 255), outline=(0, 0, 0, 255))
    over.alpha_composite(layer)
    return over.convert("RGB")


def cmd_overlay(lay, args):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    board = L.north_up_board(lay)
    out = _draw_layout(lay, board)
    path = OUT_DIR / "board_overlay.png"
    out.save(path)
    board.save(OUT_DIR / "board_north_up.jpg", quality=88)
    print(f"wrote {path.relative_to(L.ROOT)} and board_north_up.jpg ({board.size[0]}x{board.size[1]})")
    return 0


def board_building_mask(board):
    import cv2
    import numpy as np
    a = np.asarray(board).astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    # roof browns range from terracotta (5, 8) to pale tan (10, 11, 21, 22): warm, not green, not road beige
    bld = (R >= 120) & (R <= 222) & (R - G >= 10) & (R - B >= 15) & (G <= 172) & (np.abs(G - B) <= 42)
    red = (R >= 110) & (R <= 175) & (G <= 70) & (B <= 75) & (R - G >= 60)
    text = (R >= 225) & (G >= 225) & (B >= 225)
    m = ((bld | red).astype("uint8")) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), "uint8"))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), "uint8"))
    return m > 0, text


def cmd_check(lay, args):
    import cv2
    import numpy as np
    board = L.north_up_board(lay)
    mask, _text = board_building_mask(board)
    H, W = mask.shape
    worst = []
    print(f"{'#':>3} {'site':28} {'IoU':>5}  {'cover':>5}  {'fill':>5}")
    for s in lay["sites"]:
        if s["id"] in SKIP_CHECK:
            continue
        foot = np.zeros((H, W), "uint8")
        polys = L.site_polys(s)
        for poly in polys:
            pts = np.array([L.board_px(lay, x, y) for x, y in poly], dtype=np.int32)
            cv2.fillPoly(foot, [pts], 1)
        xs = [L.board_px(lay, x, y)[0] for poly in polys for x, y in poly]
        ys = [L.board_px(lay, x, y)[1] for poly in polys for x, y in poly]
        pad = 6
        x0, x1 = max(0, int(min(xs)) - pad), min(W, int(max(xs)) + pad)
        y0, y1 = max(0, int(min(ys)) - pad), min(H, int(max(ys)) + pad)
        f = foot[y0:y1, x0:x1] > 0
        b = mask[y0:y1, x0:x1]
        inter = (f & b).sum()
        union = (f | b).sum()
        iou = inter / union if union else 0.0
        cover = inter / f.sum() if f.sum() else 0.0
        fill = inter / b.sum() if b.sum() else 0.0
        flag = "" if iou >= args.min_iou else "  <-- low"
        print(f"{s['num']:>3} {s['id']:28} {iou:5.2f}  {cover:5.2f}  {fill:5.2f}{flag}")
        if iou < args.min_iou:
            worst.append(s["id"])
    print("check:", "OK" if not worst else f"{len(worst)} site(s) below {args.min_iou}: {', '.join(worst)}")
    return 1 if worst and args.strict else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["validate", "overlay", "check"])
    ap.add_argument("--min-iou", type=float, default=0.75)
    ap.add_argument("--strict", action="store_true", help="exit 1 when any site is below --min-iou")
    args = ap.parse_args()
    lay = L.load()
    return {"validate": cmd_validate, "overlay": cmd_overlay, "check": cmd_check}[args.command](lay, args)


if __name__ == "__main__":
    sys.exit(main())

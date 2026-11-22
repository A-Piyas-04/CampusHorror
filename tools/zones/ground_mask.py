"""Bakes the campus ground masks for assets/shaders/ground_splat.gdshader (Map v2, D46) from the layout.

    python tools/zones/ground_mask.py

Writes, at 4 px per metre over the campus plus a margin (assets/textures/ground/):
  campus_splat_a.png  RGBA = weights of layers 0-3 (lawn, turf, leaf litter, herringbone pavers)
  campus_splat_b.png  RGBA = weights of layers 4-7 (brick road, asphalt, concrete, earth)
  campus_shade.png    R = sun shadow (buildings, trees, wall; soft penumbra), G = ambient occlusion (contact
                      darkness at walls and under crowns), B = damp rim along the water, A = wear / patchiness
  campus_ground.json  {x0, y0, px_per_m, size, layers[]} for the shader's uniforms
The sun matches the baked sprite light (55 degrees up, from the south-west): shadows fall north-east, 0.70 m per metre
of height. Painting order is the layout's; roads go over the ground; water is left to the water polygons (the
splat under it is earth, so banks read as mud).
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campus"))
import layout as LAY  # noqa: E402

OUT = LAY.ROOT / "assets/textures/ground"
PPM = 4.0          # output pixels per metre
SS = 2             # supersampling while rasterising
MARGIN = 40.0
LAYERS = ["lawn", "turf", "leaf_litter", "herringbone", "brick_road", "asphalt", "concrete", "earth"]
SURF_LAYER = {"grass": 0, "meadow": 1, "field": 1, "forest_floor": 2, "pavers": 3, "pavers_dark": 3, "brick_road": 4,
              "brick_path": 4, "asphalt": 5, "concrete": 6, "compound": 6, "court_tennis": 6, "court_futsal": 6,
              "gravel": 7, "dirt": 7, "water": 7}
SOFT = {0: 1.6, 1: 1.6, 2: 2.2, 7: 0.9}   # blur (m) per layer: organic edges for grass and earth; paving stays crisp
SHADOW_PER_M = (0.40, -0.57)              # ground displacement of a shadow per metre of height (towards NE)
TREE_H = {"coconut_palm": 13.0, "areca_palm": 9.0, "rain_tree": 11.0, "mahogany": 12.0, "mango": 8.0, "krishnachura": 8.5}
TREE_R = {"coconut_palm": 2.6, "areca_palm": 1.6, "rain_tree": 4.5, "mahogany": 3.6, "mango": 3.2, "krishnachura": 3.6}


class Raster:
    def __init__(self, x0, y0, x1, y1, ppm):
        self.x0, self.y0, self.k = x0, y0, ppm
        self.w, self.h = int(math.ceil((x1 - x0) * ppm)), int(math.ceil((y1 - y0) * ppm))

    def P(self, pts):
        return [((x - self.x0) * self.k, (y - self.y0) * self.k) for x, y in pts]

    def blank(self, mode="L", v=0):
        return Image.new(mode, (self.w, self.h), v)

    def sigma(self, metres):
        return metres * self.k


def poly_mask(r, polys):
    im = r.blank()
    d = ImageDraw.Draw(im)
    for p in polys:
        d.polygon(r.P(p), fill=255)
    return np.asarray(im, dtype=np.float32) / 255.0


def noise(shape, scale_px, seed, octaves=3):
    rng = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(1, int(scale_px / (2 ** o)))
        small = rng.random((shape[0] // s + 2, shape[1] // s + 2)).astype(np.float32)
        big = ndimage.zoom(small, s, order=3)[: shape[0], : shape[1]]
        out += big * amp
        tot += amp
        amp *= 0.5
    out /= tot
    return (out - out.min()) / max(1e-6, out.max() - out.min())


def tileable_noise(size, cells, seed):
    """Value noise that wraps at the edges (cubic interpolation on a wrapped grid), 0..1."""
    rng = np.random.default_rng(seed)
    small = rng.random((cells, cells)).astype(np.float32)
    big = ndimage.zoom(small, size / cells, order=3, mode="grid-wrap", grid_mode=True)
    big = big[:size, :size]
    return (big - big.min()) / max(1e-6, big.max() - big.min())


def write_noise():
    """assets/textures/ground/ground_noise.png: R fine, G medium, B large (macro tone), A cloud shapes; all tile."""
    S = 512
    r = tileable_noise(S, 64, 1) * 0.6 + tileable_noise(S, 128, 2) * 0.4
    g = tileable_noise(S, 16, 3) * 0.7 + tileable_noise(S, 32, 4) * 0.3
    b = tileable_noise(S, 6, 5) * 0.75 + tileable_noise(S, 12, 6) * 0.25
    a = tileable_noise(S, 5, 7) * 0.6 + tileable_noise(S, 10, 8) * 0.3 + tileable_noise(S, 20, 9) * 0.1
    rgba = np.stack([r, g, b, a], -1)
    Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA").save(OUT / "ground_noise.png", optimize=True)


def main():
    lay = LAY.load()
    bx0, by0, bx1, by1 = LAY.bbox(lay["boundary"]["points"])
    x0, y0, x1, y1 = bx0 - MARGIN, by0 - MARGIN, bx1 + MARGIN, by1 + MARGIN
    hi = Raster(x0, y0, x1, y1, PPM * SS)
    lo = Raster(x0, y0, x1, y1, PPM)
    print(f"ground masks: {lo.w} x {lo.h} px at {PPM:g} px/m (campus + {MARGIN:g} m)")

    # --- splat: painter's order into a label image, then soft one-hot weights --------------------------------
    label = Image.new("L", (hi.w, hi.h), 1)            # beyond the wall: rough verge (earth patches added below)
    d = ImageDraw.Draw(label)
    hw = lay.get("highway")
    if hw:                                               # the highway outside the east wall: shoulders, asphalt, median
        def strip(width, fill):
            road = {"points": hw["points"], "width": width}
            for seg in LAY.road_poly(road):
                d.polygon(hi.P(seg), fill=fill)
            for x, y in hw["points"][1:-1]:
                d.polygon(hi.P(LAY.circle_poly((x, y), width / 2, 16)), fill=fill)
        strip(hw["width"] + 2 * hw.get("shoulder", 2.5), 7)
        strip(hw["width"], 5)
        strip(hw.get("median", 1.4), 6)
    for g in lay["ground"]:
        d.polygon(hi.P(LAY.ground_poly(g, lay)), fill=SURF_LAYER[g["surface"]])
    for r in lay["roads"]:
        for seg in LAY.road_poly(r):
            d.polygon(hi.P(seg), fill=SURF_LAYER[r["surface"]])
        for x, y in r["points"][1:-1]:
            d.polygon(hi.P(LAY.circle_poly((x, y), r["width"] / 2, 16)), fill=SURF_LAYER[r["surface"]])
    for f in lay.get("features", []):
        if f.get("kind") == "worn_strip":
            d.polygon(hi.P(LAY.rect_poly(f["rect"])), fill=7)
    lab = np.asarray(label).copy()
    inside = poly_mask(hi, [lay["boundary"]["points"]]) > 0.5
    # outside the wall the verge is patchy: trodden earth through the rough grass (never on the highway itself)
    rough = noise(lab.shape, hi.sigma(4.0), 11)
    lab[(~inside) & (lab == 1) & (rough > 0.6)] = 7
    paved = np.isin(lab, [3, 4, 5, 6])
    # wear: grass right beside paving is trodden to earth in a noisy band; a few desire paths cut the lawns
    grassy = np.isin(lab, [0, 1])
    near_paved = ndimage.distance_transform_edt(~paved) / hi.k
    n_fine = noise(lab.shape, hi.sigma(3.0), 7)
    worn_band = grassy & inside & (near_paved < 0.25 + 0.75 * n_fine) & (n_fine > 0.42)
    weights = []
    # soft layers blur outwards for organic edges, but never into paving: paving keeps its crisp edge (and kerb)
    paved_soft = ndimage.gaussian_filter(paved.astype(np.float32), hi.sigma(0.18))
    for i in range(len(LAYERS)):
        oh = (lab == i).astype(np.float32)
        if i == 7:
            oh = np.maximum(oh, worn_band.astype(np.float32) * 0.85)
        if i in (0, 1):
            oh = oh * (1.0 - worn_band * 0.85)
        oh = ndimage.gaussian_filter(oh, hi.sigma(SOFT.get(i, 0.18)))
        if i in SOFT:
            oh = oh * (1.0 - paved_soft)
        weights.append(oh)
    W = np.stack(weights, -1)
    W /= np.maximum(W.sum(-1, keepdims=True), 1e-6)
    W = W.reshape(lo.h, SS, lo.w, SS, len(LAYERS)).mean((1, 3)) if (hi.h == lo.h * SS and hi.w == lo.w * SS) else \
        np.stack([np.asarray(Image.fromarray((W[..., i] * 255).astype(np.uint8)).resize((lo.w, lo.h), Image.BILINEAR)) / 255.0
                  for i in range(len(LAYERS))], -1)

    # --- shade: sun shadow, AO, damp rim, wear -----------------------------------------------------------------
    sun = hi.blank()
    ds = ImageDraw.Draw(sun)
    ao_src = hi.blank()
    da = ImageDraw.Draw(ao_src)
    sx, sy = SHADOW_PER_M
    for st in lay["sites"] + lay.get("structures", []):
        if st.get("status") == "proposed":
            continue
        parts = st.get("parts") or []
        for i, poly in enumerate(LAY.site_polys(st)):
            h = (parts[i].get("h", 6.0) if i < len(parts) else st.get("monument", {}).get("h", 6.0))
            if h <= 0.5:
                continue
            off = [(x + sx * h, y + sy * h) for x, y in poly]
            hull = convex_hull(poly + off)
            ds.polygon(hi.P(hull), fill=255)
            da.polygon(hi.P(poly), fill=255)
    b = lay["boundary"]["points"]
    for i in range(len(b)):                                  # the 2.4 m campus wall
        a, c = b[i], b[(i + 1) % len(b)]
        ds.polygon(hi.P(convex_hull([a, c, (a[0] + sx * 2.4, a[1] + sy * 2.4), (c[0] + sx * 2.4, c[1] + sy * 2.4)])), fill=255)
    tree_sh = hi.blank()
    dt = ImageDraw.Draw(tree_sh)
    tree_ao = hi.blank()
    dta = ImageDraw.Draw(tree_ao)
    for x, y, sp, _src in LAY.all_trees(lay):
        h, r = TREE_H.get(sp, 9.0), TREE_R.get(sp, 3.0)
        cx, cy = x + sx * h, y + sy * h
        dt.polygon(hi.P(LAY.circle_poly((cx, cy), r, 24)), fill=255)
        dta.polygon(hi.P(LAY.circle_poly((x, y), r * 0.55, 16)), fill=255)
    sun_a = np.asarray(sun, np.float32) / 255.0
    sun_a = ndimage.gaussian_filter(sun_a, hi.sigma(0.35))
    leafy = noise(lab.shape, hi.sigma(0.9), 11, 2)            # dappled crowns
    tree_a = (np.asarray(tree_sh, np.float32) / 255.0) * (0.55 + 0.45 * (leafy > 0.38))
    tree_a = ndimage.gaussian_filter(tree_a, hi.sigma(0.5)) * 0.8
    shadow = np.clip(np.maximum(sun_a, tree_a), 0, 1)
    foot = np.asarray(ao_src, np.float32) / 255.0
    ao = ndimage.gaussian_filter(foot, hi.sigma(1.1)) * (1.0 - foot)
    ao = np.clip(ao * 1.6 + ndimage.gaussian_filter(np.asarray(tree_ao, np.float32) / 255.0, hi.sigma(1.2)) * 0.5, 0, 1)
    ao = np.maximum(ao, ndimage.gaussian_filter((~inside).astype(np.float32), hi.sigma(1.5)) * 0.75)  # the town, dimmer
    water = poly_mask(hi, [LAY.ground_poly(g, lay) for g in lay["ground"] if g["surface"] == "water"] + LAY.canal_polys(lay))
    damp = ndimage.gaussian_filter(water, hi.sigma(1.2)) * (1.0 - water)
    damp = np.clip(damp * 2.2, 0, 1)
    patch = noise(lab.shape, hi.sigma(18.0), 3, 4)
    wear = np.clip(0.55 * patch + 0.45 * worn_band, 0, 1)
    shade = np.stack([shadow, ao, damp, wear], -1)
    shade = shade.reshape(lo.h, SS, lo.w, SS, 4).mean((1, 3))

    OUT.mkdir(parents=True, exist_ok=True)
    write_noise()
    to8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)  # noqa: E731
    Image.fromarray(to8(W[..., 0:4]), "RGBA").save(OUT / "campus_splat_a.png", optimize=True)
    Image.fromarray(to8(W[..., 4:8]), "RGBA").save(OUT / "campus_splat_b.png", optimize=True)
    Image.fromarray(to8(shade), "RGBA").save(OUT / "campus_shade.png", optimize=True)
    write_water(lay, hi, OUT)
    write_kerbs(lab, water, hi, OUT, inside)
    meta = {"x0": x0, "y0": y0, "px_per_m": PPM, "size": [lo.w, lo.h], "layers": LAYERS, "water_px_per_m": PPM * SS,
            "water_size": [hi.w, hi.h],
            "source": "data/campus/campus_layout.json via tools/zones/ground_mask.py"}
    (OUT / "campus_ground.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    # a quick look for humans
    prev = np.zeros((lo.h, lo.w, 3), np.float32)
    cols = np.array([[0.45, 0.66, 0.30], [0.33, 0.55, 0.25], [0.40, 0.42, 0.22], [0.62, 0.32, 0.25], [0.70, 0.45, 0.36],
                     [0.33, 0.34, 0.36], [0.70, 0.70, 0.66], [0.55, 0.42, 0.28]], np.float32)
    prev = W @ cols
    prev *= (1.0 - 0.5 * shade[..., 0:1]) * (1.0 - 0.4 * shade[..., 1:2])
    Image.fromarray(to8(prev)).save(OUT.parent.parent.parent / "map-design/reference/ground_masks_preview.png")
    print("wrote campus_splat_a/b.png, campus_shade.png, campus_ground.json (+ map-design/reference/ground_masks_preview.png)")


def write_kerbs(lab, water, r, out, inside=None):
    """campus_kerb.png at the hi raster (8 px/m), the paving edges for the shader's modelled kerbs:
    R = signed distance to the nearest paving edge (+ into the paving, -0.5..+0.5 m), G / B = that edge's normal
    (x, y; pointing into the paving; 0.5 = 0), A = no kerb here: the edge is water (the lake copings take over) or
    outside the campus wall (the highway's asphalt just breaks into its earth shoulder)."""
    paved = np.isin(lab, [3, 4, 5, 6])
    din, (iy, ix) = ndimage.distance_transform_edt(paved, return_indices=True)
    dout, (oy, ox) = ndimage.distance_transform_edt(~paved, return_indices=True)
    h, w = paved.shape
    yy, xx = np.mgrid[0:h, 0:w]
    nx = np.where(paved, xx - ix, ox - xx).astype(np.float32)
    ny = np.where(paved, yy - iy, oy - yy).astype(np.float32)
    ln = np.maximum(np.hypot(nx, ny), 1e-6)
    nx /= ln
    ny /= ln
    sd = np.where(paved, din, -dout) / r.k
    wet = np.where(paved, water[iy, ix] > 0.5, water > 0.5)
    if inside is not None:
        wet |= ~inside
    rgba = np.stack([np.clip(sd + 0.5, 0, 1), nx * 0.5 + 0.5, ny * 0.5 + 0.5, wet.astype(np.float32)], -1)
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save(out / "campus_kerb.png", optimize=True)


def write_water(lay, r, out):
    """campus_water.png at the hi raster (8 px/m): R = signed distance to the shore (+ in water, +-4 m), G = distance
    from a water pixel north to its shore, B = south to its shore (0..2 m), A = canal. The water shader draws the
    masonry bank face where the shore is just north (the face looks at the camera) and the raised coping where it is
    just south; the ground shader lays the coping stones on the land side."""
    lakes = poly_mask(r, [LAY.ground_poly(g, lay) for g in lay["ground"] if g["surface"] == "water"]) > 0.5
    canal = poly_mask(r, LAY.canal_polys(lay)) > 0.5
    water = lakes | canal
    sd = (ndimage.distance_transform_edt(water) - ndimage.distance_transform_edt(~water)) / r.k
    h, w = water.shape
    dn = np.zeros((h, w), np.float32)
    ds = np.zeros((h, w), np.float32)
    run = np.zeros(w, np.float32)
    for y in range(h):
        run = np.where(water[y], run + 1.0, 0.0)
        dn[y] = run
    run[:] = 0.0
    for y in range(h - 1, -1, -1):
        run = np.where(water[y], run + 1.0, 0.0)
        ds[y] = run
    dn /= r.k
    ds /= r.k
    rgba = np.stack([np.clip(sd / 8.0 + 0.5, 0, 1), np.clip(dn / 2.0, 0, 1), np.clip(ds / 2.0, 0, 1), canal.astype(np.float32)], -1)
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save(out / "campus_water.png", optimize=True)


def convex_hull(points):
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


if __name__ == "__main__":
    main()

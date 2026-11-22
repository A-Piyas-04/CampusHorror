"""Builds the night-window art of the Map v2 buildings from their window masks.

    python tools/campus/night_windows.py            # every *_mask.png in assets/sprites/campus_v2/

The Blender pipeline (render.window_mask) writes, next to each building layer PNG, `<layer>_mask.png`:
R = window glass and curtains, G = lamps and lit signs, rendered with the same camera and crop. This tool turns a
mask into `<layer>_night.png`: about a third of the panes lit (seeded per sprite, so the campus is stable), each
one a real light colour (warm incandescent, cool tube light, a curtain glowing through), plus every lamp. The game
draws it unshaded over the building, faded in by the global shader parameter `night_level` (D46).
"""

import hashlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
SPRITES = ROOT / "assets/sprites/campus_v2"
LIT_FRACTION = 0.32
COLOURS = [(1.0, 0.78, 0.46), (1.0, 0.82, 0.55), (0.86, 0.93, 1.0), (0.93, 0.97, 1.0), (1.0, 0.62, 0.36), (0.98, 0.9, 0.7)]


def build(mask_path):
    m = np.asarray(Image.open(mask_path).convert("RGBA")).astype(np.float32) / 255.0
    glass = (m[..., 0] > 0.5) & (m[..., 3] > 0.5)
    lamps = (m[..., 1] > 0.5) & (m[..., 3] > 0.5)
    rng = np.random.default_rng(int(hashlib.md5(mask_path.name.encode()).hexdigest()[:8], 16))
    labels, n = ndimage.label(glass)
    out = np.zeros(m.shape[:2] + (4,), np.float32)
    if n:
        lit = rng.random(n + 1) < LIT_FRACTION
        lit[0] = False
        cols = np.array(COLOURS, np.float32)[rng.integers(0, len(COLOURS), n + 1)]
        bright = rng.uniform(0.75, 1.0, n + 1)
        on = lit[labels]
        out[on, :3] = cols[labels[on]] * bright[labels[on], None]
        out[on, 3] = 1.0
    out[lamps, :3] = (1.0, 0.88, 0.62)
    out[lamps, 3] = 1.0
    # a soft halo around every light so it reads as glowing, not painted
    alpha = out[..., 3]
    halo = ndimage.gaussian_filter(alpha, 2.0) * 0.55
    rgb = out[..., :3]
    blur = np.stack([ndimage.gaussian_filter(rgb[..., c] * alpha, 2.0) for c in range(3)], -1)
    keep = alpha > 0
    rgb = np.where(keep[..., None], rgb, blur / np.maximum(ndimage.gaussian_filter(alpha, 2.0)[..., None], 1e-4))
    alpha = np.maximum(alpha, halo)
    img = np.dstack([np.clip(rgb, 0, 1), np.clip(alpha, 0, 1)])
    out_path = mask_path.with_name(mask_path.name.replace("_mask.png", "_night.png"))
    Image.fromarray((img * 255 + 0.5).astype(np.uint8), "RGBA").save(out_path, optimize=True)
    return out_path, int(lit.sum()) if n else 0, n


def main():
    masks = sorted(SPRITES.glob("*_mask.png"))
    for mp in masks:
        out, lit, n = build(mp)
        print(f"{out.name}: {lit}/{n} panes lit")
    print(f"night windows: {len(masks)} sprites")


if __name__ == "__main__":
    sys.exit(main())

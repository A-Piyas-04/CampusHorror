"""Packs the CC0 ground textures into two Texture2DArray atlases for assets/shaders/ground_splat.gdshader.

    python tools/textures/build_ground_arrays.py

assets/textures/ground/ground_albedo_array.jpg   1024 x (1024 * 8), one layer per ground material, colour
assets/textures/ground/ground_normal_array.jpg   same layout, OpenGL tangent-space normals
Each JPG gets a .import that makes Godot import it as a 2D texture array (8 vertical slices, mipmaps, VRAM-compressed). Layer order is
tools/zones/ground_mask.py's LAYERS. Every layer is made seamless-safe (the sources already tile) and its average
colour is recorded in ground_layers.json, which the shader's macro variation uses to keep colours stable.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets/source/textures"
OUT = ROOT / "assets/textures/ground"
SIZE = 1024
# layer -> (Poly Haven id, real-world tile size in metres)
LAYERS = [("leafy_grass", 2.0), ("sparse_grass", 2.0), ("forest_leaves_02", 3.0), ("herringbone_brick", 1.8),
          ("brick_pavement", 2.0), ("asphalt_02", 3.0), ("concrete_floor_02", 2.0), ("dirt", 2.0)]

IMPORT = """[remap]

importer="2d_array_texture"
type="CompressedTexture2DArray"
path="res://.godot/imported/{name}-{tag}.ctexarray"

[deps]

source_file="res://assets/textures/ground/{name}"
dest_files=["res://.godot/imported/{name}-{tag}.ctexarray"]

[params]

compress/mode={mode}
compress/high_quality=false
compress/lossy_quality=0.7
compress/hdr_compression=1
compress/channel_pack=0
mipmaps/generate=true
mipmaps/limit=-1
slices/horizontal=1
slices/vertical={n}
"""


def load(tid, kind):
    p = next((SRC / tid).glob(f"{tid}_{kind}_*.*"), None)
    if p is None:
        raise SystemExit(f"missing {tid} {kind}; run tools/textures/fetch_cc0.py")
    im = Image.open(p).convert("RGB")
    return im.resize((SIZE, SIZE), Image.LANCZOS) if im.size != (SIZE, SIZE) else im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    albedo = Image.new("RGB", (SIZE, SIZE * len(LAYERS)))
    normal = Image.new("RGB", (SIZE, SIZE * len(LAYERS)))
    info = []
    for i, (tid, tile_m) in enumerate(LAYERS):
        a = load(tid, "diffuse")
        n = load(tid, "nor_gl")
        albedo.paste(a, (0, i * SIZE))
        normal.paste(n, (0, i * SIZE))
        mean = (np.asarray(a, np.float32) / 255.0).reshape(-1, 3).mean(0)
        info.append({"layer": i, "texture": tid, "tile_m": tile_m, "mean_rgb": [round(float(v), 4) for v in mean]})
    for old in OUT.glob("ground_*_array.png*"):
        old.unlink()
    albedo.save(OUT / "ground_albedo_array.jpg", quality=93, subsampling=0)
    normal.save(OUT / "ground_normal_array.jpg", quality=95, subsampling=0)
    for name, tag, mode in (("ground_albedo_array.jpg", "albedo", 2), ("ground_normal_array.jpg", "normal", 2)):
        imp = OUT / f"{name}.import"
        imp.write_text(IMPORT.format(name=name, tag=tag, mode=mode, n=len(LAYERS)), encoding="utf-8")
    (OUT / "ground_layers.json").write_text(json.dumps({"size": SIZE, "layers": info,
                                                        "license": "CC0 (Poly Haven), see assets/source/textures/LICENSES.md"},
                                                       indent=1) + "\n", encoding="utf-8")
    print(f"wrote ground_albedo_array.jpg and ground_normal_array.jpg ({len(LAYERS)} layers of {SIZE}px) + .import + ground_layers.json")


if __name__ == "__main__":
    sys.exit(main())

"""Godot import settings for the Map v2 sprites (D46).

    python tools/campus/import_settings.py

- Building, infrastructure and night-window sprites in assets/sprites/campus_v2/: VRAM-compressed, high quality
  (BPTC on desktop), mipmaps. Uncompressed they would need well over half a gigabyte of video memory.
- Window masks (*_mask.png) are only build inputs: they get the cheapest import (no mipmaps, lossless, never loaded).
Existing .import files keep their uid; only [params] change. Godot re-imports on the next editor or --import run.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPRITES = ROOT / "assets/sprites/campus_v2"

TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://{rel}"

[params]

{params}
"""


def params(mode, hq, mipmaps):
    return "\n".join([
        f"compress/mode={mode}", f"compress/high_quality={'true' if hq else 'false'}", "compress/lossy_quality=0.7",
        "compress/uastc_level=0", "compress/rdo_quality_loss=0.0", "compress/hdr_compression=1", "compress/normal_map=0",
        "compress/channel_pack=0", f"mipmaps/generate={'true' if mipmaps else 'false'}", "mipmaps/limit=-1",
        "roughness/mode=0", 'roughness/src_normal=""', "process/channel_remap/red=0", "process/channel_remap/green=1",
        "process/channel_remap/blue=2", "process/channel_remap/alpha=3", "process/fix_alpha_border=true",
        "process/premult_alpha=false", "process/normal_map_invert_y=false", "process/hdr_as_srgb=false",
        "process/hdr_clamp_exposure=false", "process/size_limit=0", "detect_3d/compress_to=1"])


def main():
    n = 0
    for png in sorted(SPRITES.glob("*.png")):
        mask = png.name.endswith("_mask.png")
        want = params(0, False, False) if mask else params(2, True, True)
        imp = png.with_name(png.name + ".import")
        rel = png.relative_to(ROOT).as_posix()
        if imp.exists():
            text = imp.read_text(encoding="utf-8")
            new = re.sub(r"\[params\].*", "[params]\n\n" + want + "\n", text, flags=re.S)
            # a changed compression means a different imported file: drop the stale remap so Godot rebuilds it
            new = re.sub(r'\npath="[^"]*"', "", new)
            new = re.sub(r"\ndest_files=\[[^\]]*\]", "", new)
            new = re.sub(r'metadata=\{[^}]*\}\n', "", new)
        else:
            new = TEMPLATE.format(rel=rel, params=want)
        if not imp.exists() or imp.read_text(encoding="utf-8") != new:
            imp.write_text(new, encoding="utf-8")
            n += 1
    print(f"import settings: {n} .import files written in {SPRITES.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())

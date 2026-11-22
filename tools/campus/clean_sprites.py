"""Delete Map v2 sprite files that no current config renders any more (D46).

A layer that was merged, renamed or dropped (merge_embedded, a recipe change) leaves its PNG, window mask, night
PNG and their .import files behind in assets/sprites/<category>/. Godot keeps importing them and night_windows.py
keeps processing them. This lists, and with --delete removes, every file there that isn't the base PNG, a layer PNG,
a layer's _mask.png / _night.png (or the .import of one of those) of a config in that category.

    python tools/campus/clean_sprites.py                 # dry run, campus_v2
    python tools/campus/clean_sprites.py --delete
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "assets/source/blender"))
from pipeline import assetconfig  # noqa: E402


def expected(category):
    keep = set()
    for p in sorted((ROOT / "assets/source/blender/configs").glob("*.json")):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if raw.get("category") != category:
            continue
        cfg = assetconfig.load(p.stem)
        keep.add(cfg["outputs"]["png"].name)
        for png in cfg["layer_outputs"].values():
            keep |= {png.name, png.stem + "_mask.png", png.stem + "_night.png"}
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="campus_v2")
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()
    folder = ROOT / "assets/sprites" / args.category
    keep = expected(args.category)
    gone = []
    for f in sorted(folder.iterdir()):
        name = f.name[:-len(".import")] if f.name.endswith(".import") else f.name
        if f.is_file() and name.endswith(".png") and name not in keep:
            gone.append(f)
    for f in gone:
        print(("deleted " if args.delete else "stale   ") + f.relative_to(ROOT).as_posix())
        if args.delete:
            f.unlink()
    print(f"{len(gone)} stale file(s) in {folder.relative_to(ROOT).as_posix()} ({len(keep)} expected names)")


if __name__ == "__main__":
    main()

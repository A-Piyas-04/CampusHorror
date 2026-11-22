"""Fetches the CC0 photo textures used by Map v2 (D46) from Poly Haven into assets/source/textures/.

    python tools/textures/fetch_cc0.py            # download what is missing
    python tools/textures/fetch_cc0.py --force    # download everything again

Every texture here is CC0 (public domain, https://polyhaven.com/license): no attribution required, but each one is
credited in assets/source/textures/LICENSES.md anyway. Only image files are downloaded; nothing is executed.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "assets/source/textures"
UA = {"User-Agent": "campus-texture-fetch/1.0"}

# id -> (resolution, maps, what it is used for)
TEXTURES = {
    "leafy_grass": ("1k", ["Diffuse", "nor_gl"], "ground: mown lawn"),
    "sparse_grass": ("1k", ["Diffuse", "nor_gl"], "ground: sports turf and rough field grass"),
    "forest_leaves_02": ("1k", ["Diffuse", "nor_gl"], "ground: leaf litter under the woods"),
    "herringbone_brick": ("1k", ["Diffuse", "nor_gl"], "ground: the plaza's herringbone brick pavers"),
    "brick_pavement": ("1k", ["Diffuse", "nor_gl"], "ground: red brick roads and paths"),
    "asphalt_02": ("1k", ["Diffuse", "nor_gl"], "ground: the asphalt gate road"),
    "concrete_floor_02": ("1k", ["Diffuse", "nor_gl"], "ground: concrete paths, courts' surrounds, compounds"),
    "dirt": ("1k", ["Diffuse", "nor_gl"], "ground: bare earth, plots, worn patches"),
    "red_brick_03": ("2k", ["Diffuse", "nor_gl", "Rough", "AO"], "buildings: IUT exposed red brick (Blender)"),
    "concrete_floor_01": ("2k", ["Diffuse", "nor_gl", "Rough"], "buildings: weathered flat roofs (Blender)"),
}


def get(url, tries=4):
    """curl (with retries) rather than urllib: some networks break Python's TLS against the CDN."""
    import subprocess
    import time
    for k in range(tries):
        r = subprocess.run(["curl", "-sSfL", "--retry", "3", "-m", "120", "-A", UA["User-Agent"], url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"download failed: {url}: {r.stderr.decode(errors='replace').strip()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for tid, (res, maps, use) in TEXTURES.items():
        info = json.loads(get(f"https://api.polyhaven.com/info/{tid}"))
        files = json.loads(get(f"https://api.polyhaven.com/files/{tid}"))
        out_dir = DEST / tid
        out_dir.mkdir(exist_ok=True)
        got = []
        for mp in maps:
            entry = files.get(mp, {}).get(res, {})
            fmt = "jpg" if "jpg" in entry else ("png" if "png" in entry else None)
            if fmt is None:
                print(f"  {tid}: no {mp} at {res}")
                continue
            out = out_dir / f"{tid}_{mp.lower()}_{res}.{fmt}"
            if out.exists() and not args.force:
                got.append(out.name)
                continue
            out.write_bytes(get(entry[fmt]["url"]))
            got.append(out.name)
            print(f"  {tid}: {out.name} ({out.stat().st_size // 1024} KB)")
        authors = ", ".join(info.get("authors", {}).keys()) or "Poly Haven"
        dims = info.get("dimensions")
        scale = f"{dims[0] / 1000:g} x {dims[1] / 1000:g} m" if dims else "unknown"
        rows.append(f"| `{tid}` | {use} | {scale} | {authors} | https://polyhaven.com/a/{tid} |")
        (out_dir / "meta.json").write_text(json.dumps({"id": tid, "resolution": res, "files": got, "use": use,
                                                       "dimensions_mm": dims, "authors": list(info.get("authors", {}).keys()),
                                                       "license": "CC0 1.0 (https://polyhaven.com/license)"}, indent=1) + "\n", encoding="utf-8")
    (DEST / "LICENSES.md").write_text(
        "# Photo textures (CC0)\n\nAll textures in this folder come from [Poly Haven](https://polyhaven.com) and are released under\n"
        "**CC0 1.0** (public domain; https://polyhaven.com/license). No attribution is required; the authors are credited\n"
        "here anyway. Fetched by `tools/textures/fetch_cc0.py` (decision D46).\n\n"
        "| Texture | Used for | Real-world size | Author(s) | Source |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n",
        encoding="utf-8")
    print(f"textures: {len(rows)} sets in {DEST.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())

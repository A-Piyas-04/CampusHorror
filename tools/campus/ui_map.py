"""Writes the in-game campus map (the `map` key's screen) from the layout.

    python tools/campus/ui_map.py

assets/ui/campus_map.png   board-style render with the legend 1-27
assets/ui/campus_map.json  {x0, y0, px_per_m, world_px_per_m, entrances: {zone_id: [x_m, y_m]}} so the screen can
                           place the "you are here" marker from the player's position (campus px -> metres -> map px)
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402
import map_render  # noqa: E402

OUT = L.ROOT / "assets/ui"


def main():
    lay = L.load()
    OUT.mkdir(parents=True, exist_ok=True)
    img, (x0, y0, k) = map_render.render(lay, px_per_m=3.2, legend=True, numbers=True, labels=True)
    img.save(OUT / "campus_map.png", optimize=True)
    entrances = {}
    for s in lay["sites"]:
        for e in s.get("entrances", []):
            if e.get("to"):
                entrances[e["to"]] = [e["at"][0], e["at"][1], f'{s["name"]}']
    meta = {"x0": x0, "y0": y0, "px_per_m": k, "world_px_per_m": [L.PX_X, L.PX_Y], "size": list(img.size),
            "map_width_px": round((map_render.extent(lay)[2] - x0) * k), "entrances": entrances,
            "source": "data/campus/campus_layout.json via tools/campus/ui_map.py"}
    (OUT / "campus_map.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(f"wrote assets/ui/campus_map.png {img.size} and campus_map.json ({len(entrances)} entrances)")


if __name__ == "__main__":
    main()

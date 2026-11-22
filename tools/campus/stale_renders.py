"""List Map v2 assets whose render is out of date with their config (D46).

Compares each config's generator params, layers and render settings with what its render record says was rendered,
so it doesn't matter when a config file was last touched. Prints the stale asset ids on one line (feed them to
assets/source/blender/build_asset.py).

    python tools/campus/stale_renders.py                 # every campus_v2 config
    python tools/campus/stale_renders.py --category campus_v2 --verbose
"""
import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
BL = ROOT / "assets/source/blender"


def norm(v):
    return json.loads(json.dumps(v, sort_keys=True))


def why_stale(cfg_path):
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    rec_path = BL / cfg["category"] / f"{cfg['asset_id']}.render.json"
    if not rec_path.exists():
        return "never rendered"
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    if norm(rec.get("generator_params")) != norm(cfg.get("generator_params")):
        a, b = rec.get("generator_params") or {}, cfg.get("generator_params") or {}
        keys = sorted(k for k in set(a) | set(b) if norm(a.get(k)) != norm(b.get(k)))
        return "generator params differ: " + ", ".join(keys)
    want = [l["name"] for l in cfg.get("layers", [])]
    have = [l.get("name") for l in rec.get("layers", [])] if isinstance(rec.get("layers"), list) else want
    if want and want != have:
        return f"layers differ: {have} -> {want}"
    rec_layers = {l.get("name"): l for l in rec.get("layers", [])} if isinstance(rec.get("layers"), list) else {}
    for l in cfg.get("layers", []):
        for key in ("holdouts", "covered_by"):
            if sorted(l.get(key, [])) != sorted(rec_layers.get(l["name"], {}).get(key, [])):
                return f"layer {l['name']}: {key} differ"
    for k in ("px_per_m", "samples", "window_mask"):
        if k in cfg.get("render", {}) and rec.get("render", {}).get(k, cfg["render"][k]) != cfg["render"][k]:
            return f"render.{k} differs"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="campus_v2")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    stale = []
    for p in sorted((BL / "configs").glob("*.json")):
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if cfg.get("category") != args.category:
            continue
        why = why_stale(p)
        if why:
            stale.append(cfg["asset_id"])
            if args.verbose:
                print(f"  {cfg['asset_id']}: {why}")
    print(" ".join(stale))


if __name__ == "__main__":
    main()

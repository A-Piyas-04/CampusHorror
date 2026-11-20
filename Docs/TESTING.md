# Testing

Snapshot: 21 November 2026 • Phase H4

Audience: anyone (person or AI session) who changes a zone, a component, a prop or the player.

Since Phase H4 every zone is checked by **one data-driven validator** plus **one session check**. They
replace the 9 per-batch Main Gate check scenes and their 6 versioned baselines (retired on 21 November
2026; they remain in git history and in the private ref `refs/checkpoints/h245-preedit`).

---

## 1. The three suites

Run all of them before every commit that touches `scenes/`, `scripts/`, `data/` or `project.godot`.
Godot path: `F:\App Installers\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe`.

| Suite | Command (headless; exit 0 = pass) | What it proves |
|---|---|---|
| **Zone validator** | `<godot> --headless --path . res://scenes/tests/zone_validation/ZoneValidator.tscn -- --quit-after-checks --self-test` | Every zone's structure, collision, reachability, ground and fades (§2) |
| **Session check** | `<godot> --headless --path . res://scenes/tests/zone_validation/GameSessionCheck.tscn -- --quit-after-checks` | The real `Main.tscn`: boot, presentation contract, every spawn, every door, save/load, a refused bad save, debug keys |
| **Character check** | `<godot> --headless --path . res://scenes/tests/character_previews/PlayerCharacterCheck.tscn -- --quit-after-checks` | The player character's frames, anchoring, animation logic, and movement physics |

Asset changes additionally run the pipeline: `python assets/source/blender/build_asset.py --all --steps validate,scene,preview,godot`
(`Docs/ASSET_PIPELINE.md`). A failing script never quits on its own, so wrap runs in a timeout. **A
parse error makes a scene hang, not fail.**

Expected output on 21 November 2026: validator **PASS (45/45)**, session **PASS (14/14)**, character
**PASS (19/19)**, pipeline **21/21 assets, 789/789 checks**. The session check prints exactly one
intended `ERROR` line (the refused unknown-zone save); any other `ERROR` or `WARNING` line is a
problem.

The session check backs up `user://save.json` byte for byte and restores it (verified). The
validator never touches the save.

## 2. Zone validator rules

Generic rules: they apply to every zone in `data/zones/zone_registry.tres` with no per-zone code.

| Rule | Checks |
|---|---|
| `identity` | The scene's `Zone` root has the registry key as its `zone_id` |
| `graph` | Spawn IDs are unique and non-empty; every `Door` leads to a registered zone **and** a spawn that exists there |
| `conventions` | `Docs/CONVENTIONS.md`: static bodies on layer 1 / mask none; `Interactable` layer 3 / mask none; `OverheadVisibility` layer none / mask 2; no unclassified `Area2D`; occluders on light mask 1 (or 0 = shadow deliberately off); prop sprites on light mask 2; `ContactShadow` at effective z −9 with no collision; **every placed prop has only Y-sorted `Node2D` ancestors**; zone ground at z −10, not Y-sorted |
| `snapshot` | Every node, including internal children, equals the baseline: global transform, z, Y-sort, light mask, modulate, textures, `texture_scale`, polygons, collision layers / shapes, occluders, lights, TileMapLayer cells (hash per cell), exported script values (door destinations, spawn IDs, fade settings, …) |
| `ground` | An 8 px material lattice over the manifest's ground rectangle equals the baseline. Materials are texture file stems, so re-rendering a texture at another resolution keeps the lattice identical (this is how H2 was verified: 316,575 samples, 0 changed) |
| `probes` | For **every** rectangle collision shape of every static body (any layer): the real player footprint walking at it from the south and from the north stops at its face, or earlier at a neighbour, and **never passes through** |
| `reach` | Flood fill (8 px grid, real 28 × 12 footprint) from the zone's first spawn: no standable position outside the manifest's `playable_bounds` (no leaks), every spawn reachable, every door reachable close enough to interact |
| `cases` | The manifest's specific walks (expected stop point or free path) |
| `fades` | Every `OverheadVisibility`: never collides; lasts at least 0.15 s; entering fades exactly its targets to `faded_alpha` and nothing else; the alpha never changes faster per frame than its sine ease allows for that frame's real delta (a snap fails by ~3.5×); leaving restores them. Plus the manifest's fade cases (where each layer must or must not be faded) |
| `self-test` | (`--self-test`) mutates `main_gate_exterior` in memory 9 ways (palm moved, cell repainted, body on the wrong layer, trunk off the world layer, south wall removed, door to a missing spawn, a fade that never fades, a 0 s fade, a fade rewired to snap) and requires each rule to catch its own mutation. **A validator that can't fail proves nothing.** |

Measured cost: about 20 s for the four zones' rules (ground lattice 5 s, fades 11 s, reach 2 s), plus
the self-test.

## 3. Per-zone data

`scenes/tests/zone_validation/manifests/<zone_id>.json`: **every registered zone needs one**.

| Key | Meaning |
|---|---|
| `playable_bounds` | `[x, y, w, h]` feet rectangle the player must never leave (required for `reach`) |
| `ground` | `{ "node": "Ground", "rect": [x, y, w, h] }`; omit for zones without textured ground |
| `walks` | `[{ name, from, motion, expect: "stop" | "free", stop, tol }]` measured stop lines worth pinning |
| `fade_layers`, `fade_cases` | Layer paths, and `[{ name, feet, faded: [...] }]` positions where they must (not) be faded |

`scenes/tests/zone_validation/baselines/<zone_id>.json`: the recorded state (written by the tool, never
by hand).

## 4. Changing a zone on purpose: the baseline workflow

1. Make the change.
2. Run the validator. `snapshot` / `ground` list **every** difference (`changed: <node> [fields]`,
   `added`, `removed`, `ground at (x, y): a -> b`). Every other rule must still pass.
3. **Read the list.** It must contain only what you meant to change. If anything else is listed, stop:
   that is a regression.
4. Refresh only that zone's baseline: `… ZoneValidator.tscn -- --dump-baseline --zone=<zone_id>`. It
   prints the same diff again before writing.
5. Re-run the validator (pass), and commit the baseline **in the same commit** as the change, saying
   what the diff was.

Example (H2, 21 November 2026): exactly 21 differences, 20 × `["texture_scale"]` on ground-textured
polygons and `./Ground/Tiles ["xform", "tile_size"]`, and 0 ground samples changed. Refreshed.

New zone: add it to the registry, write its manifest, run `--dump-baseline --zone=<id>`, review the
validator's output (stats line, reach area, probes), then commit.

## 5. Coverage of the retired suites

| Retired suite (checks) | Now covered by |
|---|---|
| `MainGateGroundCheck` (16) | `ground` (same 316,575-point lattice), `snapshot` (cells hash, strips, markings, every other node), `conventions` (ground z / Y-sort) |
| `MainGateVegetationCheck` (18) | `probes` (every trunk, both sides; was 84 probes, now every shape in the zone), `conventions` (Y-sort chain, light masks, contact shadows), `snapshot` |
| `MainGateBoundaryCheck` (26) | `reach` (any gap in the wall is a leak to the road), `probes`, `snapshot` (37 + 38 run, run collision, occluder), manifest walk (stop line y 1394.96) |
| `MainGateLandmarkCheck` (33) | `snapshot` (layers, sort points, occluders), `fades`, manifest walk (gate-leaves stop y 1390) |
| `MainGateOverheadCheck` (14) | `fades` (generic per area, plus the same 11 positions as manifest fade cases), manifest walk (fade areas never block) |
| `MainGateCdsCheck` (22) | `snapshot`, `probes`, `reach` (door, flagpoles and lamp don't block), `fades` (canteen roof); texture budget stays in the pipeline (`max_texture_px`) |
| `MainGateSessionCheck` (11) | `GameSessionCheck` (14), now for every zone, door and spawn instead of one hand-picked route |
| `MainGatePlayableTest` (24), `MainGateCompositionTest` (27) | Retired without replacement: they tested a separate review scene that the real zone has superseded. Their manual approvals (checks 22, 23) are obsolete |

**Intentionally not carried over:**
- One-time acceptance diffs between historical batch baselines (e.g. "batch 2 differs from batch 1B
  only inside SouthWall"). They proved past batches, and git history keeps them.
- The ±2 px jitter test on one fade edge (flicker at the boundary). The rate rule catches snaps but
  not repeated toggling. **Known gap:** add a jitter case to the `fades` rule if fade hysteresis
  ever changes.
- The 1,100 samples 0.5 px either side of each original surface edge: replaced by the exact snapshot
  of every strip vertex and every tile cell, which is stricter.

## 6. Other test scenes

| Scene | Use |
|---|---|
| `scenes/tests/environment_previews/ZoneCapture.tscn` | Windowed screenshots of the real game (`--shots=name@x,y[,zoom=..][,night]…`). Needs a window. |
| `scenes/tests/renderer_stress/RendererStressTest.tscn` | Windowed lighting cost and correctness probe (`--stack=N`). TEMPORARY until it becomes the frame-time budget probe (roadmap H3 remainder) |
| `scenes/tests/asset_previews/*` | Written by the asset pipeline; run by its `godot` step |
| `MCPCheck`, `Milestone0Test`, `WallAssetPreview`, galleries | Historical; not part of any regression |

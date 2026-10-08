# Art style direction

Snapshot: 8 October 2026 • Milestone G Part 1

This records the visual direction agreed so far. It is a direction, not a finished style guide; nothing below has final assets yet. The current map is a blockout made of placeholder shapes (see `Docs/CAMPUS_MAP.md`).

## Current direction

The user has stated that the map should **not** look like a flat coloured diagram.

| Topic | Direction |
|---|---|
| Engine / gameplay | Stays 2D: 2D physics, `CharacterBody2D` movement, 2D lights, Y-sorted top-down world. |
| Presentation | The world should **look** three-dimensional. |
| Viewpoint | Slightly angled top-down: ground seen from above, south-facing walls visible, building height shown upward on screen. |
| Visual language | 2.5D / faux-3D assets drawn for that angle. |
| Recognisability | Real campus proportions and landmarks: Main Gate, central field, courts, CDS. |
| Height | Walls and buildings show visible height; roofs read as raised above their footprint. |
| Architecture | Red-brick institutional architecture is the core identity, with pointed arches where the real buildings have them (CDS arcades, Main Gate arch). |
| Vegetation | Volumetric-looking trees and palms; greenery close to brick buildings, tree-lined paths. |
| Light | One consistent light/shadow direction across all assets. |
| Composition | Manually editable and modular: buildings, props, surfaces and vegetation stay separate pieces that can be moved in the editor. |

## How the blockout already follows this

- Every placeholder building is a `BlockoutBlock`: a roof drawn above its ground footprint plus a front wall face, so height reads on screen while collision stays at the base (`Docs/CONVENTIONS.md` §3–4).
- Arches are hinted on visible south faces (`arch_count`).
- Trees and palms draw their canopy above a small trunk footprint and Y-sort with the player.
- Overhead pieces (gate roof/arch, veranda roof edge, CDS entrance canopy) cover the player as roofs would.

These are placeholders to prove scale and layering only; none of their colours, shapes or sizes are art decisions.

## Not yet decided

Do not lock these until an art test is approved:

- Exact asset resolution
- Final tile size
- Exact camera angle
- Exact pixels-per-unit / world scale
- Final shadow softness
- Exact stylization amount
- Final character style
- Asset pipeline: Blender-rendered vs illustrated / vector
- Final texture filtering

Related open items in `Docs/CONVENTIONS.md` → "Still undecided" (base resolution, integer scaling / pixel snap, camera tuning) depend on the same decision.

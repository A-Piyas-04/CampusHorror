# Project status

Last updated: 7 October 2026

## Summary

Environment and Cursor ↔ Godot MCP connection are **verified**. Milestone 0 conventions are **drafted and awaiting approval**. No gameplay has been implemented.

## Environment — Verified

| Item | Value | Evidence |
|---|---|---|
| OS | Windows 10/11 (build 26100) | Cursor environment |
| Godot | **4.7.2 stable** (official, build `ed1daf0bf`) | MCP `get_runtime_status`; engine log |
| Renderer | **Compatibility** (`gl_compatibility`, OpenGL 3.3, NVIDIA GeForce RTX 3050 Laptop GPU) | `project.godot`; engine log |
| Node.js / npm / Git | v22.14.0 / 11.18.0 / 2.45.1 | Terminal |
| Godot MCP | `godot-mcp-server` via `npx` (server reported version 0.6.0); editor add-on `addons/godot_mcp`; WebSocket port 6505 | MCP `get_godot_status` |
| Project name | `CampusHorror` | `project.godot` |

## Verification log

| Date | Check | Result |
|---|---|---|
| 2026-10-07 | MCP read-only inspection (project, version, scene tree) | Pass |
| 2026-10-07 | MCPCheck integration test: created `scenes/tests/MCPCheck.tscn` (Node2D root + red `ColorRect`), ran only that scene, read runtime tree, captured screenshot | Pass: launched, rectangle visible, 0 errors / 0 warnings |
| 2026-10-07 | Main scene setting | Unchanged (empty) |

## Milestones

| Milestone | Status |
|---|---|
| Environment / MCP setup | **Verified** |
| 0. Project conventions | **In progress.** Documented in `Docs/CONVENTIONS.md`, all items Proposed. Not yet registered in project settings, and the test scene for collisions/draw order isn't built. |
| A. Main, placeholder player, movement, camera | Not started |
| B. Interaction | Not started |
| C. Zones, doors, spawn markers | Not started |
| D. GameState + persistent pickup | Not started |
| E. SaveService | Not started |
| F. Lighting test | Not started |
| G. Custom art sample | Not started |
| H. Desktop export | Not started |

### Milestone 0 remaining steps

1. User reviews `Docs/CONVENTIONS.md` and approves or changes the Proposed items.
2. Register the approved input actions and 2D physics layer names in `project.godot`.
3. Build a small placeholder test scene in `scenes/tests/` proving wall collision, Y-sort order and overhead layering with the feet-origin convention.
4. Mark Milestone 0 Verified after that scene passes.

## Project contents

- `scenes/tests/MCPCheck.tscn`: temporary MCP test scene. Not the main scene; safe to delete later.
- `addons/godot_mcp/`: MCP editor add-on (registers the `MCPRuntime` autoload used for runtime inspection/screenshots).
- No gameplay scenes, scripts, input actions, collision layer names or main scene yet.

## Known issues / notes

- `config/features` in `project.godot` still says `"Forward Plus"` (creation-time label); the active renderer is Compatibility.
- The docs folder is `Docs/` (capital D) while the blueprint refers to `docs/`. Windows treats them as the same; on case-sensitive systems paths must match `Docs/`. Renaming it is optional and undecided.

## Next task

Approve or revise `Docs/CONVENTIONS.md`, then complete the Milestone 0 remaining steps above.

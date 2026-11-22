# Map design: the whole IUT campus, editable

This folder is the campus as the game builds it, drawn as an editable plan. Everything here now comes from **the
official IUT campus board** you photographed (`actual-map/`), which is the absolute truth for the layout.
Nothing in this folder can break the game.

| File | What it is | Open with |
|---|---|---|
| `actual-map/` | Your photos of the official campus board and its legend (the source of truth) | any image viewer |
| `campus_map.svg` | The whole campus, top-down, **north up**, true scale (1 unit = 1 metre), in layers | Inkscape (free), Illustrator, Affinity, Figma, or a web browser to view |
| `campus_map.png` | Quick picture of the same map, with the board's legend 1–27 | any image viewer |
| `campus_map.json` | The same data as text: sites 1–27 with footprints and heights, roads, ground, water, trees, entrances, rooms | any text editor |
| `interiors.svg` | Floor plan of every enterable room, and which building it is in | same as the SVG |
| `reference/board_north_up.jpg` | Your board photo turned so north is up (the board itself is printed south-up) | any image viewer |
| `reference/board_overlay.png` | The game's layout drawn over the board photo, to check that they match | any image viewer |
| `new-areas/` | Where you put photos and notes for buildings and rooms you want detailed | see `new-areas/README.md` |

## How the board was read

- The board is printed **upside down compared with a normal map**: its compass has S at the top and N at the
  bottom. The game and these files use **north up**: the highway runs along the east (right) side and the Main
  Gate is at the bottom-right corner, where the board's "You are here" pin is.
- Scale: the tennis and futsal courts, and the CDS + Indoor Sports block (83 m, the same as the earlier game),
  set it at 0.23 m per pixel of the turned photo. The campus is about **470 m east–west and 300 m north–south**.
- Every building on the board's legend is placed at its measured position and size. The game also adds the
  heights, read from the aerial photos.
- **Two corners of the board are cut off in the photo**: the far north-west (#24 Medical Center / Laundry runs off
  the edge) and the far south-east (the Main Gate, #1). Both are placeholders until a photo of those corners
  arrives.
- **#26 Studio Apartments and #27 New Academic Building** are marked *proposed* on the board. They are drawn as
  fenced plots, purple and dashed. **#25 New Male Hall** is *under construction* and drawn in tan.

## The layers in `campus_map.svg`

Ground, Water and canal, Roads and paths, Trees, Buildings (numbered as on the board), Campus wall,
**Reference: official board** (hidden; switch it on to see your photo under the plan), Game: collision (hidden),
Entrances and game doors (yellow dots lead into buildings), Spawns, Labels and numbers, Grid (50 m), Legend, and
**Owner additions**.

Hover over anything in Inkscape or a browser to see its name, status and height.

## How to add or correct things

**Draw in the "Owner additions" layer**, or create more layers whose name starts with `owner`
(for example `owner - library details`, `owner - fix the gate`). Anything goes: shapes for buildings, paths,
text notes, arrows, pasted photos. Label things so I know what they are.

- Keep the scale: the grid is in metres, so a 30 m building is 30 units wide.
- To change something that already exists, draw the corrected version in an owner layer and add a note
  (for example "the Admin building is 5 m further east"). Don't edit the generated layers.
- You can also add entries to `owner_additions` in `campus_map.json` if you prefer text.

## What happens to your edits

This folder is regenerated whenever the campus changes (`python tools/zones/export_map_design.py`).
**Every layer whose name starts with "owner", in both SVG files, and the `owner_additions` list in the JSON are
kept exactly as you left them.** All other layers are redrawn, so edits made in them would be lost. If a file
can't be read, a copy is saved as `*.unreadable.*` instead of being thrown away.

The single source the game builds from is `data/campus/campus_layout.json`. When you send a correction, I update
that file. The game world and this folder then both follow it.

## Coordinates (for the curious)

Metres, x towards east, y towards south (as in the SVG), north up. The origin is the board photo's west edge at
the line of the north wall, so a few metres of the cut-off north-west corner are negative. Inside the game,
1 m = 32 px across and 20.576 px in depth, because the camera looks down at 40°.

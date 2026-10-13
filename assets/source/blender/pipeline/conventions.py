"""Shared 2.5D asset conventions. Plain Python (no bpy): used inside Blender and by the host tool.

Values come from the approved red-brick wall pipeline test (Milestone G Part 2,
`red_brick_wall_grid_test`). Change them only as a deliberate art-direction decision:
every asset rendered afterwards changes with them.
"""

from pathlib import Path

PIPELINE_VERSION = 1
PIPELINE_MARKER = "campus_asset_pipeline"

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BLENDER_ROOT = PROJECT_ROOT / "assets/source/blender"
CONFIG_DIR = BLENDER_ROOT / "configs"
GENERATOR_DIR = BLENDER_ROOT / "generators"
LOG_DIR = BLENDER_ROOT / "logs"

DEFAULT_BLENDER_EXE = r"F:\bbbb\blender.exe"
DEFAULT_GODOT_EXE = r"F:\App Installers\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe"

# Camera: orthographic, looking at the asset's front (-Y) face.
CAMERA_ELEVATION_DEG = 40.0
CAMERA_AZIMUTH_DEG = 0.0
FRAME_MARGIN_FRACTION = 0.08        # transparent margin per side, fraction of the larger content extent

# Render.
RENDER_WIDTH_PX = 768
SAMPLES = 256
MAX_BOUNCES = 6
FILTER_SIZE_PX = 1.5
# Tileable assets keep this many texels of the neighbour continuation past each footprint end,
# so mipmapped/linear sampling at a join reads opaque, identical pixels from both sprites.
# 16 texels covers mip level 3 (8-texel blocks, used at the ~0.145 sprite scale) plus bilinear reach.
TILE_BLEED_PX = 16

# Key sun from the front-left and above; one light direction for every asset.
SUN_ELEVATION_DEG = 55.0
SUN_AZIMUTH_FROM_FRONT_DEG = -35.0  # negative = from the viewer's left
SUN_STRENGTH = 3.2
SUN_ANGLE_DEG = 3.0
SUN_COLOR = (1.0, 0.96, 0.9)
# (name, elevation, azimuth from front, strength, angle, colour); light-linked to the asset only.
FILL_LIGHTS = (
    ("SkyFill", 70.0, 20.0, 0.8, 90.0, (0.75, 0.85, 1.0)),
    ("GroundBounce", -25.0, 10.0, 0.35, 90.0, (1.0, 0.8, 0.65)),
)

# Game scale (Docs/CAMPUS_MAP.md: roughly 32 px = 1 m; still Undecided in Docs/ART_STYLE.md).
GAME_PX_PER_M = 32.0

# Ground tiles (config "kind": "ground_tile"). Rendered straight down and drawn 1:1 by a
# TileMapLayer, so the texture is the tile at game resolution. Proposed tile size: 2 m = 64 px.
GROUND_ELEVATION_DEG = 90.0
GROUND_TILE_PERIOD_M = 2.0
GROUND_TILE_PX = 64
# Rendered past every tile edge (between neighbour copies) and cropped off afterwards, so the
# pixel filter and the denoiser never see an image edge inside the kept tile.
GROUND_OVERSCAN_PX = 8
# Wrap-around seam: mean RGB step across the opposite edges vs the mean step between
# neighbouring interior columns/rows. A seam shows up as a step clearly above the interior.
GROUND_SEAM_RATIO_MAX = 1.5
GROUND_SEAM_SLACK = 1.0
# Lighting gradient: mean luma difference between opposite halves of the tile (0-255).
GROUND_GRADIENT_MAX = 6.0
# Variant tiles that must blend with a base tile: mean RGB diff along the shared border band.
GROUND_BORDER_BAND_PX = 3
GROUND_BORDER_MATCH_MAX = 2.5
GROUND_TILESET_DIR = "assets/tilesets"

# Validation thresholds.
MIN_MARGIN_PX = 16
MAX_BORDER_ALPHA = 1.0 / 255.0
CONTENT_BBOX_TOLERANCE_PX = 4.0     # alpha bbox vs projected design bounds
TILE_MATCH_MEAN_MAX = 3.0           # mean RGB diff (0-255) between the bleed and the opposite end

# Godot.
SPRITE_TEXTURE_FILTER = 4           # CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS (texture imported with mipmaps)
UPRIGHT_LIGHT_MASK = 2              # Docs/CONVENTIONS.md §10: lit but not shadowed
WORLD_COLLISION_LAYER = 1           # "world"
PLAYER_COLLISION_LAYER = 2          # Player.tscn body layer (layer number); overhead fade areas mask it
OVERHEAD_FADE_SCRIPT = "res://scripts/components/overhead_visibility.gd"
OVERHEAD_FADED_ALPHA = 0.35         # layer "fade" default: overhead alpha while the player is under it
OVERHEAD_FADE_SECONDS = 0.25

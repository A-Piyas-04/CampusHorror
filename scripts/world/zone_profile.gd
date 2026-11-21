class_name ZoneProfile
extends Resource

## How a zone feels: camera framing, the surface underfoot where no ground texture decides it, ambience
## and acoustics. One per zone in `data/zones/profiles/<zone_id>.tres`, assigned on the zone root's
## `profile`. Data, not code: a Mirror Campus variant of a zone is a different profile on the same geometry.

@export_group("Camera")
## Default camera zoom in this zone (Docs/PRESENTATION.md: 2.0; exteriors 1.5 to 2.5; small interiors up to 3.0,
## where the player sprite is drawn exactly 1:1 (decision D21)).
@export_range(1.5, 3.0, 0.05) var camera_zoom: float = 2.0
## World-px rectangle the camera view must stay inside (the zone's authored area).
## Zero size = no limits (debug test rooms only; the validator requires limits for shipping zones).
@export var camera_limits: Rect2 = Rect2()
## How far ahead (game px) the camera leads at full sprint; scales with speed, 0 when standing.
@export_range(0.0, 96.0, 1.0) var look_ahead_px: float = 48.0

@export_group("Night")
## The world tint at night in story mode (CanvasModulate): how dark the zone is before any light.
@export var night_ambient: Color = Color(0.15, 0.16, 0.24)

@export_group("Ground")
## Surface for footsteps wherever no ground texture covers the feet (blockout floors, interiors).
@export var default_surface: StringName = &"grass"

@export_group("Audio")
## Looping ambience bed for this zone (crossfaded by AudioDirector on entry). Empty = silence.
@export var ambience: AudioStream
@export_range(-40.0, 6.0, 0.5) var ambience_volume_db: float = -6.0
## Reverb on the World bus (footsteps and world sounds) while in this zone.
@export_range(0.0, 1.0, 0.01) var reverb_room_size: float = 0.15
@export_range(0.0, 1.0, 0.01) var reverb_damping: float = 0.7
@export_range(0.0, 1.0, 0.01) var reverb_wet: float = 0.05

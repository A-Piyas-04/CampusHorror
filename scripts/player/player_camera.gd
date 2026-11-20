extends Camera2D
## Player camera v2 (roadmap I4), on `Player/Camera`.
## - Eased follow: built-in position smoothing (physics process: the project uses physics interpolation).
## - Look-ahead: `offset` leads in the movement direction, proportional to speed (the zone profile's
##   `look_ahead_px` at a sprint, 0 standing), eased so direction changes never jolt the view.
## - Zoom and limits from the zone's ZoneProfile (`apply_profile`, called by Main on every zone entry), so the
##   view never shows outside the zone's authored area.
## - `shake(amount)`: trauma-based shake for later scares (roadmap J); decays on its own.
## - `snap()`: called by Player.teleport(); no drift after spawning, loading or travelling.

## Position smoothing speed (higher = tighter).
@export var follow_speed: float = 6.0
## How quickly the look-ahead offset settles (per second).
@export var look_ahead_ease: float = 2.5
@export var max_shake_px: float = 10.0
## Trauma lost per second.
@export var shake_decay: float = 1.6

var look_ahead_px: float = 48.0
var _look := Vector2.ZERO
var _trauma := 0.0
var _shake_t := 0.0

@onready var _body := get_parent() as Player


func _ready() -> void:
	process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS
	position_smoothing_enabled = true
	position_smoothing_speed = follow_speed
	limit_smoothed = true


func _physics_process(delta: float) -> void:
	var v := _body.velocity
	var target := Vector2.ZERO
	if v.length() > 1.0:
		target = v.normalized() * look_ahead_px * clampf(v.length() / maxf(_body.sprint_speed, 1.0), 0.0, 1.0)
	_look = _look.lerp(target, 1.0 - exp(-look_ahead_ease * delta))
	var shake := Vector2.ZERO
	if _trauma > 0.0:
		_shake_t += delta
		var k := _trauma * _trauma * max_shake_px
		shake = Vector2(sin(_shake_t * 47.0) + sin(_shake_t * 23.0), cos(_shake_t * 41.0) + sin(_shake_t * 29.0)) * 0.5 * k
		_trauma = maxf(_trauma - shake_decay * delta, 0.0)
	offset = _look + shake


## Zoom, limits and look-ahead for the zone being entered.
func apply_profile(profile: ZoneProfile) -> void:
	zoom = Vector2.ONE * profile.camera_zoom
	look_ahead_px = profile.look_ahead_px
	var r := profile.camera_limits
	if r.size.x > 0.0 and r.size.y > 0.0:
		limit_left = floori(r.position.x)
		limit_top = floori(r.position.y)
		limit_right = ceili(r.end.x)
		limit_bottom = ceili(r.end.y)
	else:
		limit_left = -10000000
		limit_top = -10000000
		limit_right = 10000000
		limit_bottom = 10000000
	snap()


## Puts the view exactly on the player now: no smoothing drift, no leftover look-ahead or shake, and no
## physics-interpolated slide from the old position (the camera has its own interpolation state; resetting the
## Player's alone left a one-frame slide plus a sub-pixel settle over ~8 frames, seen in Phase I testing).
func snap() -> void:
	_look = Vector2.ZERO
	_trauma = 0.0
	offset = Vector2.ZERO
	position_smoothing_enabled = false
	force_update_scroll()
	reset_smoothing()
	reset_physics_interpolation()
	position_smoothing_enabled = true


## Adds screen shake (0..1 trauma; it is squared, so small values stay subtle).
func shake(amount: float) -> void:
	_trauma = clampf(_trauma + amount, 0.0, 1.0)


## World rectangle the camera currently shows (for tests and later culling).
func get_view_rect() -> Rect2:
	var size := get_viewport_rect().size / zoom
	return Rect2(get_screen_center_position() - size * 0.5, size)

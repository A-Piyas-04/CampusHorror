extends AnimatedSprite2D
## Plays the player's animations from the parent Player's velocity and gait (roadmap I2). Visual only, except
## that it tells the Player when a foot strikes the ground (`Player.emit_footstep()`), so footsteps match the
## legs exactly.
##
## - Animation = <set>_<facing>: set is idle / sneak / walk / run, facing one of 8 directions.
## - Facing: the 45-degree sector of the velocity, with hysteresis so a wobbling stick doesn't flicker; it
##   persists when the player stops.
## - Playback rate: `speed_scale = speed / cycle speed`, where the cycle speed is MEASURED in Blender from the
##   planted foot (SpriteFrames metadata `cycles`, written by player_character.py), clamped to 0.75..1.25 so
##   acceleration never slides the feet. A turn or gait change keeps the cycle's phase.
## - Footsteps: on the cycle's heel-strike frames (`contact_frames` in the same metadata).
## Falls back gracefully to frames that only have 4 facings or only idle / walk.

## Below this speed (px/s, after move_and_slide) the player idles.
const WALK_THRESHOLD := 5.0
## Degrees past a sector edge before the facing changes (stops flicker on exact diagonals and stick noise).
const HYSTERESIS_DEG := 10.0
## Screen-space facing for each 45-degree sector of atan2(v.y, v.x) (y down): 0 = right, clockwise.
const SECTORS := ["right", "down_right", "down", "down_left", "left", "up_left", "up", "up_right"]
## Used when the frames have no `cycles` metadata (walk cycle: 1.3 m per 8 frames at 12 fps).
const FALLBACK_CYCLES := {"idle": {"speed_px_s": 0.0, "contact_frames": []},
	"walk": {"speed_px_s": 62.0, "contact_frames": [2, 6]}}

var facing := "down"
## Current animation set: "idle", "sneak", "walk" or "run".
var anim_set := "idle"

var _cycles: Dictionary = {}
var _switching := false

@onready var _body := get_parent() as Player


func _ready() -> void:
	_cycles = sprite_frames.get_meta("cycles", FALLBACK_CYCLES) if sprite_frames != null else FALLBACK_CYCLES
	frame_changed.connect(_on_frame_changed)
	play(_anim_name("idle", facing))


func _physics_process(_delta: float) -> void:
	var v := _body.velocity
	var speed := v.length()
	var moving := speed > WALK_THRESHOLD
	if moving:
		facing = _facing_for(v)
	var new_set: String = String(_body.gait) if moving else "idle"
	var anim := _anim_name(new_set, facing)
	if animation != anim:
		var was_moving := anim_set != "idle"
		var keep_phase := float(frame + frame_progress) / maxf(float(sprite_frames.get_frame_count(animation)), 1.0)
		_switching = true
		play(anim)
		if moving and was_moving:
			var n := sprite_frames.get_frame_count(anim)
			var f := keep_phase * n
			set_frame_and_progress(int(f) % n, f - floorf(f))
		_switching = false
	anim_set = new_set
	speed_scale = _speed_scale(new_set, anim, speed)


## The facing changes only once the velocity is clearly inside another sector.
func _facing_for(v: Vector2) -> String:
	var angle := rad_to_deg(atan2(v.y, v.x))
	var current := SECTORS.find(facing)
	if current != -1:
		var off := absf(wrapf(angle - current * 45.0, -180.0, 180.0))
		if off <= 22.5 + HYSTERESIS_DEG:
			return facing
	return SECTORS[posmod(roundi(angle / 45.0), 8)]


## Best available animation: the exact one, else the same set with the facing's horizontal (then vertical)
## component, else walk.
func _anim_name(set_name: String, dir: String) -> StringName:
	for s in [set_name, "walk" if set_name != "idle" else "idle"]:
		var candidates := [dir]
		if dir.contains("_"):
			candidates.append(dir.get_slice("_", 1))
			candidates.append(dir.get_slice("_", 0))
		for d in candidates:
			var name := StringName("%s_%s" % [s, d])
			if sprite_frames.has_animation(name):
				return name
	return StringName("idle_down")


func _speed_scale(set_name: String, anim: StringName, speed: float) -> float:
	if set_name == "idle":
		return 1.0
	var playing_set := String(anim).get_slice("_", 0)
	var cycle_speed := float((_cycles.get(playing_set, {}) as Dictionary).get("speed_px_s", 0.0))
	if cycle_speed <= 0.0:
		return 1.0
	# The proper cycle for this gait: stay within +-25 %. A stand-in cycle (no run / sneak frames yet) may
	# stretch further so the feet still don't slide.
	if playing_set == set_name:
		return clampf(speed / cycle_speed, 0.75, 1.25)
	return clampf(speed / cycle_speed, 0.4, 2.6)


func _on_frame_changed() -> void:
	if _switching or anim_set == "idle":
		return
	var playing_set := String(animation).get_slice("_", 0)
	var contacts: Array = (_cycles.get(playing_set, {}) as Dictionary).get("contact_frames", [])
	if contacts.has(frame):
		_body.emit_footstep()

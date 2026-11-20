extends AudioStreamPlayer2D

## The player's footsteps (roadmap I3), on `Player/Footsteps`, bus Footsteps (sent through World's reverb).
## Plays one take on every heel strike the animator reports (`Player.footstep`), chosen by the surface
## under the feet, and louder or quieter by gait. Sound set: data/audio/footsteps.tres.

const SET_PATH := "res://data/audio/footsteps.tres"

## The last step played, for tests: {surface, gait, volume_db, pitch_scale}.
var last_step: Dictionary = {}
var steps_played := 0

var _set: FootstepSet


func _ready() -> void:
	_set = load(SET_PATH) as FootstepSet
	(get_parent() as Player).footstep.connect(_on_footstep)


func _on_footstep(surface: StringName, gait: StringName, _at: Vector2) -> void:
	if _set == null:
		return
	var s := _set.resolved(surface)
	var take := _set.stream_for(s)
	if take == null:
		return
	if stream != take:
		stream = take
	volume_db = float(_set.gain_db.get(s, 0.0)) + float(_set.gait_gain_db.get(gait, 0.0))
	pitch_scale = float(_set.pitch.get(s, 1.0))
	if AudioDirector.can_play():
		play()
	steps_played += 1
	last_step = {"surface": s, "gait": gait, "volume_db": volume_db, "pitch_scale": pitch_scale}

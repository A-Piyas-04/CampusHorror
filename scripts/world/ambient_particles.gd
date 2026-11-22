class_name AmbientParticles
extends CPUParticles2D

## Map v2 ambient life (D46): fireflies over the woods, the lakes and the lawns after dusk, leaves drifting down
## from the big trees by day. Follows the time of day (Main/DayNightTint): emits only in its part of the day and
## fades its modulate in and out, so nothing pops. Fireflies are unshaded, so they glow through the night tint.

enum When { NIGHT, DAY }

@export var when: When = When.NIGHT

var _target := 0.0


func _ready() -> void:
	var tint := get_tree().get_first_node_in_group("world_tint")
	if tint != null and tint.has_signal("phase_changed"):
		tint.connect("phase_changed", _on_phase)
		_on_phase(0, float(tint.get("darkness")))
	else:
		_on_phase(0, 0.0)
	modulate.a = _target
	emitting = _target > 0.01


func _on_phase(_phase: int, darkness: float) -> void:
	_target = smoothstep(0.45, 0.9, darkness) if when == When.NIGHT else 1.0 - smoothstep(0.1, 0.5, darkness)


func _process(delta: float) -> void:
	if absf(modulate.a - _target) > 0.001:
		modulate.a = move_toward(modulate.a, _target, delta * 0.4)
	var want := _target > 0.01
	if emitting != want:
		emitting = want

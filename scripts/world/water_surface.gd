extends Node2D

## Map v2 water (on `Ground/Water`): the lakes' and canal's shared water_v2 material follows the time of day (sun
## glints and sky streaks fade at dusk; lamps and the lantern still catch the ripples through the normal map).


func _ready() -> void:
	var tint := get_tree().get_first_node_in_group("world_tint")
	if tint != null and tint.has_signal("phase_changed"):
		tint.connect("phase_changed", _on_phase)
		_on_phase(0, float(tint.get("darkness")))


func _on_phase(_phase: int, darkness: float) -> void:
	for c in get_children():
		var m := (c as CanvasItem).material as ShaderMaterial if c is CanvasItem else null
		if m != null:
			m.set_shader_parameter("daylight", clampf(1.0 - darkness * 1.2, 0.0, 1.0))
			return   # one shared material

class_name PostFx
extends CanvasLayer

## Map v2 post-processing (D46): a full-screen grade + bloom + vignette + grain over the world (below the HUD), its
## look eased with the time of day (Main/DayNightTint). `Settings.post_fx` turns it off for slow machines.

const SHADER := preload("res://assets/shaders/post_grade.gdshader")
## Per phase (dawn, day, golden hour, dusk, night): lift, gamma, gain, saturation, contrast, bloom, vignette.
const LOOKS := [
	[Vector3(0.02, 0.02, 0.05), Vector3(1.0, 1.0, 1.04), Vector3(1.0, 0.98, 1.02), 0.92, 1.0, 0.14, 0.26],
	[Vector3(0.0, 0.0, 0.01), Vector3(1.02, 1.0, 0.98), Vector3(1.03, 1.02, 0.98), 1.06, 1.06, 0.12, 0.2],
	[Vector3(0.02, 0.0, 0.0), Vector3(1.05, 1.0, 0.92), Vector3(1.06, 0.98, 0.88), 1.08, 1.05, 0.2, 0.26],
	[Vector3(0.0, 0.01, 0.05), Vector3(0.96, 0.98, 1.08), Vector3(0.96, 0.98, 1.06), 0.85, 1.04, 0.24, 0.32],
	[Vector3(0.0, 0.02, 0.04), Vector3(0.94, 1.0, 1.06), Vector3(1.0, 1.0, 1.05), 0.78, 1.08, 0.34, 0.4],
]

var _rect: ColorRect
var _mat: ShaderMaterial
var _tween: Tween


func _ready() -> void:
	layer = 9        # over the world, under the glow layer, HUD, menus and the transition fade
	_rect = ColorRect.new()
	_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_mat = ShaderMaterial.new()
	_mat.shader = SHADER
	_rect.material = _mat
	add_child(_rect)
	visible = Settings.post_fx
	Settings.changed.connect(func() -> void: visible = Settings.post_fx)
	var tint := get_tree().get_first_node_in_group("world_tint")
	if tint != null and tint.has_signal("phase_changed"):
		tint.connect("phase_changed", _on_phase)
		_apply(int(tint.get("phase")), true)


func _on_phase(phase: int, _darkness: float) -> void:
	_apply(phase, false)


func _apply(phase: int, instant: bool) -> void:
	var l: Array = LOOKS[clampi(phase, 0, LOOKS.size() - 1)]
	var keys := ["lift", "gamma", "gain", "saturation", "contrast", "bloom_strength", "vignette"]
	if _tween != null and _tween.is_valid():
		_tween.kill()
	if instant:
		for i in keys.size():
			_mat.set_shader_parameter(keys[i], l[i])
		return
	_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE)
	for i in keys.size():
		var from: Variant = _mat.get_shader_parameter(keys[i])
		if from == null:
			from = l[i]
		_tween.tween_method(func(v: Variant) -> void: _mat.set_shader_parameter(keys[i], v), from, l[i], 2.5)

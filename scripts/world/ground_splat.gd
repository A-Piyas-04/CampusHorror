class_name GroundSplat
extends Polygon2D

## The campus floor (Map v2, D46): one quad with assets/shaders/ground_splat.gdshader. Reads the baked masks'
## frame (assets/textures/ground/campus_ground.json) and the texture layers' measured colours
## (ground_layers.json), grades every layer towards its target colour, follows the time of day (sun shadows and
## clouds fade at dusk) and drifts the cloud shadows slowly across the campus.

const GROUND_META := "res://assets/textures/ground/campus_ground.json"
const LAYER_META := "res://assets/textures/ground/ground_layers.json"
## Per layer: target average colour (the photo is graded to it), saturation, stochastic tiling, height contrast.
## lawn, turf, leaf litter, herringbone pavers, brick road, asphalt, concrete, earth.
const TARGET := [Color(0.34, 0.47, 0.19), Color(0.28, 0.40, 0.17), Color(0.36, 0.34, 0.19), Color(0.50, 0.27, 0.19),
	Color(0.50, 0.30, 0.23), Color(0.31, 0.31, 0.32), Color(0.58, 0.57, 0.54), Color(0.47, 0.36, 0.25)]
const SATURATION := [1.1, 1.05, 1.0, 0.95, 0.9, 0.6, 0.5, 1.0]
## Brick and concrete are procedural in the shader (laid brick, cast slabs); their photos are only grain, so they
## tile stochastically too (a non-stochastic photo showed its blemishes on a lattice).
const STOCHASTIC := [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
## Photo detail kept around the target colour (1 = all of it).
const CONTRAST := [1.0, 1.0, 1.0, 1.0, 1.0, 0.6, 0.55, 0.85]
const HEIGHT_GAIN := [0.25, 0.25, 0.3, 0.15, 0.15, 0.08, 0.1, 0.18]
## Cloud drift, metres per second (a light south-westerly breeze).
const CLOUD_WIND := Vector2(1.6, -0.7)

var _cloud := Vector2.ZERO
var _mat: ShaderMaterial


func _ready() -> void:
	_mat = material as ShaderMaterial
	if _mat == null:
		return
	var g: Variant = JSON.parse_string(FileAccess.get_file_as_string(GROUND_META))
	var l: Variant = JSON.parse_string(FileAccess.get_file_as_string(LAYER_META))
	if g is Dictionary:
		_mat.set_shader_parameter("mask_origin_m", Vector2(float(g.x0), float(g.y0)))
		_mat.set_shader_parameter("mask_px_per_m", float(g.px_per_m))
		_mat.set_shader_parameter("mask_size_px", Vector2(float(g.size[0]), float(g.size[1])))
		_mat.set_shader_parameter("water_px_per_m", float(g.get("water_px_per_m", 8.0)))
		var ws: Array = g.get("water_size", [4096, 2048])
		_mat.set_shader_parameter("water_size_px", Vector2(float(ws[0]), float(ws[1])))
	var tiles := PackedFloat32Array()
	var tints := PackedVector3Array()
	var targets := PackedVector3Array()
	for i in TARGET.size():
		var info: Dictionary = (l.layers[i] if l is Dictionary and i < l.layers.size() else {})
		tiles.append(float(info.get("tile_m", 2.0)))
		var m: Array = info.get("mean_rgb", [0.5, 0.5, 0.5])
		tints.append(_grade(Color(float(m[0]), float(m[1]), float(m[2])), TARGET[i], SATURATION[i]))
		targets.append(Vector3(TARGET[i].r, TARGET[i].g, TARGET[i].b))
	_mat.set_shader_parameter("tile_m", tiles)
	_mat.set_shader_parameter("tint", tints)
	_mat.set_shader_parameter("saturation", PackedFloat32Array(SATURATION))
	_mat.set_shader_parameter("stochastic", PackedFloat32Array(STOCHASTIC))
	_mat.set_shader_parameter("height_gain", PackedFloat32Array(HEIGHT_GAIN))
	_mat.set_shader_parameter("target", targets)
	_mat.set_shader_parameter("contrast", PackedFloat32Array(CONTRAST))
	# the mosque plaza (the lake block's brick-paved island), for the prayer-row grid
	_mat.set_shader_parameter("plaza_rect", Vector4(169.0, 112.5, 325.0, 234.5))
	var tint := get_tree().get_first_node_in_group("world_tint")
	if tint != null and tint.has_signal("phase_changed"):
		tint.connect("phase_changed", _on_phase)
		_on_phase(0, float(tint.get("darkness")))


## The per-channel multiplier that takes a layer's average colour, after the saturation change, to `target`.
static func _grade(mean: Color, target: Color, sat: float) -> Vector3:
	var lum := mean.r * 0.2126 + mean.g * 0.7152 + mean.b * 0.0722
	var after := Vector3(lerpf(lum, mean.r, sat), lerpf(lum, mean.g, sat), lerpf(lum, mean.b, sat))
	return Vector3(target.r / maxf(after.x, 0.02), target.g / maxf(after.y, 0.02), target.b / maxf(after.z, 0.02))


func _on_phase(_phase: int, darkness: float) -> void:
	if _mat != null:
		_mat.set_shader_parameter("daylight", clampf(1.0 - darkness * 1.25, 0.0, 1.0))


func _process(delta: float) -> void:
	if _mat == null:
		return
	_cloud += CLOUD_WIND * delta
	_mat.set_shader_parameter("cloud_offset", _cloud)

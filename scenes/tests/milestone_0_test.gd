extends Node2D
## Milestone 0 conventions test: input/layer registration, feet origin,
## wall collision, Y-sort and overhead layering. Placeholder shapes only;
## the character is moved by this test, not by player input.

const ACTIONS: Array[StringName] = [
	&"move_up", &"move_down", &"move_left", &"move_right",
	&"interact", &"lantern", &"pause",
]
const LAYER_NAMES: Array[String] = ["world", "player", "interactable", "enemy", "trigger"]
const LAYER_WORLD := 1
const LAYER_PLAYER := 2

const WALL_PUSH_START := Vector2(760.0, 330.0)
const WALL_PUSH_SPEED := 300.0
const WALL_PUSH_FRAMES := 60

const POSES := {
	&"behind_prop": Vector2(360.0, 335.0),
	&"in_front_of_prop": Vector2(360.0, 385.0),
	&"under_overhead": Vector2(660.0, 250.0),
}
const TOUR: Array[StringName] = [&"against_wall", &"behind_prop", &"in_front_of_prop", &"under_overhead"]

var _results: Dictionary = {}
var _push_frames_left := 0
var _wall_contact := false
var _wall_rest_position := Vector2.ZERO
var _tour_index := 0

@onready var _ground: Polygon2D = $Ground
@onready var _objects: Node2D = $Objects
@onready var _wall: StaticBody2D = $Objects/Wall
@onready var _wall_collision: CollisionShape2D = $Objects/Wall/Collision
@onready var _prop: StaticBody2D = $Objects/Prop
@onready var _character: CharacterBody2D = $Objects/TestCharacter
@onready var _character_body: Polygon2D = $Objects/TestCharacter/Body
@onready var _character_collision: CollisionShape2D = $Objects/TestCharacter/Collision
@onready var _overhead: Node2D = $Overhead
@onready var _canopy: Polygon2D = $Overhead/Canopy
@onready var _input_label: Label = $DebugUI/InputLabel
@onready var _tour_timer: Timer = $TourTimer


func _ready() -> void:
	_check_project_setup()
	_check_feet_origin()
	_check_draw_order_setup()
	_start_wall_test()


func _physics_process(_delta: float) -> void:
	if _push_frames_left <= 0:
		return
	_character.velocity = Vector2.RIGHT * WALL_PUSH_SPEED
	_character.move_and_slide()
	if _character.is_on_wall():
		_wall_contact = true
	_push_frames_left -= 1
	if _push_frames_left == 0:
		_finish_wall_test()


func _process(_delta: float) -> void:
	var pressed: PackedStringArray = []
	for action in ACTIONS:
		if Input.is_action_pressed(action):
			pressed.append(action)
	_input_label.text = "Actions pressed: %s" % (", ".join(pressed) if not pressed.is_empty() else "(none)")


## Stops the automatic tour and holds the character at one pose (for screenshots).
func show_pose(pose: StringName) -> void:
	_tour_timer.stop()
	_place_character(pose)


func get_results() -> Dictionary:
	return _results


func _check_project_setup() -> void:
	var missing: PackedStringArray = []
	for action in ACTIONS:
		if not InputMap.has_action(action):
			missing.append(action)
	_report(&"input_actions_registered", missing.is_empty(),
		"all 7 present" if missing.is_empty() else "missing: " + ", ".join(missing))

	var wrong: PackedStringArray = []
	for i in LAYER_NAMES.size():
		var key := "layer_names/2d_physics/layer_%d" % (i + 1)
		if ProjectSettings.get_setting(key, "") != LAYER_NAMES[i]:
			wrong.append(key)
	_report(&"physics_layer_names", wrong.is_empty(),
		"layers 1-5 named" if wrong.is_empty() else "wrong: " + ", ".join(wrong))

	var world_bit := _layer_bit(LAYER_WORLD)
	var player_bit := _layer_bit(LAYER_PLAYER)
	var layers_ok := (
		_character.collision_layer == player_bit and _character.collision_mask == world_bit
		and _wall.collision_layer == world_bit and _wall.collision_mask == 0
		and _prop.collision_layer == world_bit and _prop.collision_mask == 0
	)
	_report(&"collision_layers_assigned", layers_ok,
		"character layer=%d mask=%d, wall layer=%d mask=%d, prop layer=%d mask=%d" % [
			_character.collision_layer, _character.collision_mask,
			_wall.collision_layer, _wall.collision_mask,
			_prop.collision_layer, _prop.collision_mask,
		])


func _check_feet_origin() -> void:
	var shape := _character_collision.shape as RectangleShape2D
	var footprint_bottom := _character_collision.position.y + shape.size.y / 2.0
	var body_top := INF
	var body_bottom := -INF
	for point in _character_body.polygon:
		body_top = minf(body_top, point.y)
		body_bottom = maxf(body_bottom, point.y)
	var body_height := body_bottom - body_top
	var ok := (
		is_zero_approx(footprint_bottom)
		and is_zero_approx(body_bottom)
		and body_top < 0.0
		and shape.size.y <= body_height / 3.0
	)
	_report(&"feet_origin", ok,
		"visual spans y %.0f..%.0f, footprint bottom y=%.0f, footprint height %.0f of %.0f" % [
			body_top, body_bottom, footprint_bottom, shape.size.y, body_height,
		])


func _check_draw_order_setup() -> void:
	var under_pose: Vector2 = POSES[&"under_overhead"]
	var ok := (
		_objects.y_sort_enabled
		and _character.get_parent() == _objects and _prop.get_parent() == _objects
		and _ground.z_index < _objects.z_index and _objects.z_index < _overhead.z_index
		and not _overhead.y_sort_enabled
		and POSES[&"behind_prop"].y < _prop.position.y
		and POSES[&"in_front_of_prop"].y > _prop.position.y
		and Geometry2D.is_point_in_polygon(under_pose - _canopy.position, _canopy.polygon)
	)
	_report(&"draw_order_setup", ok,
		"ground z=%d, objects z=%d (y_sort=%s), overhead z=%d; prop feet y=%.0f" % [
			_ground.z_index, _objects.z_index, _objects.y_sort_enabled,
			_overhead.z_index, _prop.position.y,
		])


func _start_wall_test() -> void:
	_character.position = WALL_PUSH_START
	_wall_contact = false
	_push_frames_left = WALL_PUSH_FRAMES


func _finish_wall_test() -> void:
	_character.velocity = Vector2.ZERO
	_wall_rest_position = _character.position
	var wall_shape := _wall_collision.shape as RectangleShape2D
	var wall_face_x := _wall_collision.global_position.x - wall_shape.size.x / 2.0
	var character_shape := _character_collision.shape as RectangleShape2D
	var footprint_right := _character_collision.global_position.x + character_shape.size.x / 2.0
	var travelled := _character.position.x - WALL_PUSH_START.x
	var unblocked_distance := WALL_PUSH_SPEED * WALL_PUSH_FRAMES / Engine.physics_ticks_per_second
	var ok := (
		_wall_contact
		and travelled > 0.0
		and travelled < unblocked_distance
		and footprint_right <= wall_face_x + 1.0
	)
	_report(&"wall_blocks_character", ok,
		"travelled %.1f of %.1f px, footprint right x=%.1f, wall face x=%.1f" % [
			travelled, unblocked_distance, footprint_right, wall_face_x,
		])

	var failed := _results.values().count(false)
	print("[M0TEST] SUMMARY %d/%d checks passed" % [_results.size() - failed, _results.size()])

	_place_character(TOUR[0])
	_tour_timer.start()


func _place_character(pose: StringName) -> void:
	_character.velocity = Vector2.ZERO
	if pose == &"against_wall":
		_character.position = _wall_rest_position
	else:
		_character.position = POSES[pose]


func _on_tour_timer_timeout() -> void:
	_tour_index = (_tour_index + 1) % TOUR.size()
	_place_character(TOUR[_tour_index])


func _report(check: StringName, passed: bool, detail: String) -> void:
	_results[check] = passed
	var line := "[M0TEST] %s %s: %s" % ["PASS" if passed else "FAIL", check, detail]
	if passed:
		print(line)
	else:
		push_error(line)


func _layer_bit(layer_number: int) -> int:
	return 1 << (layer_number - 1)

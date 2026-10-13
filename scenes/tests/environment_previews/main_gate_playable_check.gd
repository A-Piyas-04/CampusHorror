extends Node2D
## TEMPORARY Milestone G playable integration check for MainGatePlayableTest.tscn. Drives the real
## Player (Player.tscn / player.gd) only through Input.action_press/release and Player.teleport():
## free walking over each ground type, stops against every prop type from both sides, the Y-sort
## order at each stop and the camera following the feet. Then returns the player to the spawn and
## leaves the scene playable. Optional: `-- --quit-after-checks` quits with exit code 0 (pass) / 1.

const SPAWN := Vector2(0, -170)
const PLAYER_SCENE := "res://scenes/player/Player.tscn"
const FOOTPRINT_HEIGHT := 12.0
const STOP_TOLERANCE := 1.5
const MIN_TRAVEL_RATIO := 0.9
const PX_PER_FRAME := 200.0 / 60.0
const SOURCE_NAMES := {0: "grass", 1: "worn grass", 2: "walkway", 3: "asphalt"}

## [start, action, physics frames, expected ground source at the end, label]
var _walks: Array = [
	[Vector2(0, -180), "move_up", 40, 2, "north along the red walkway"],
	[Vector2(-300, -400), "move_right", 40, 0, "east across grass"],
	[Vector2(0, 40), "move_up", 30, 2, "north through the gate gap from the sidewalk"],
	[Vector2(260, -340), "move_right", 30, 1, "east onto the worn-grass patch"],
	[Vector2(600, 120), "move_left", 30, 3, "west along the road"],
]

## [prop path under Objects, start, action, label]. move_up stops on the prop's south face (player
## in front), move_down on its north face (player behind).
var _stops: Array = [
	["BoundaryWall/WallE400", Vector2(400, 40), "move_up", "boundary wall from the sidewalk"],
	["BoundaryWall/PierE256", Vector2(256, 40), "move_up", "join pier from the sidewalk"],
	["BoundaryWall/GatePierWest", Vector2(-64, 40), "move_up", "west gate pier from the sidewalk"],
	["Vegetation/SouthRowTree01", Vector2(290, -40), "move_up", "south-row tree trunk from the south"],
	["Vegetation/PalmPathEast", Vector2(95, -300), "move_up", "palm trunk from the south"],
	["StreetFurniture/BenchPlazaWest", Vector2(-128, -190), "move_up", "plaza bench from the south"],
	["StreetFurniture/LampSidewalk", Vector2(480, 100), "move_up", "sidewalk lamp plinth from the south"],
	["Vegetation/HedgeE448", Vector2(448, -60), "move_up", "hedge from the south"],
	["BoundaryWall/WallE400", Vector2(400, -40), "move_down", "boundary wall from the campus side"],
	["Vegetation/SouthRowTree01", Vector2(290, -140), "move_down", "south-row tree trunk from the north"],
	["StreetFurniture/BenchPlazaWest", Vector2(-128, -290), "move_down", "plaza bench from the north"],
	["Vegetation/HedgeE448", Vector2(448, -160), "move_down", "hedge from the north"],
	["StreetFurniture/LampPlazaEast", Vector2(176, -190), "move_down", "plaza lamp plinth from the north"],
]

var _failures := 0
var _checks := 0

@onready var _player: Player = $Player
@onready var _ground: TileMapLayer = $Ground
@onready var _objects: Node2D = $Objects


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[PLAYABLE] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	await get_tree().physics_frame
	await get_tree().process_frame
	_check_setup()
	for walk: Array in _walks:
		await _check_walk(walk[0], walk[1], walk[2], walk[3], walk[4])
	for stop: Array in _stops:
		await _check_stop(stop[0], stop[1], stop[2], stop[3])
	await _check_bounds()
	_player.teleport(SPAWN)
	print("[PLAYABLE] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if "--quit-after-checks" in OS.get_cmdline_user_args():
		get_tree().quit(0 if _failures == 0 else 1)


func _check_setup() -> void:
	var bodies := get_tree().root.find_children("*", "CharacterBody2D", true, false)
	_check(bodies.size() == 1 and bodies[0] == _player and _player.scene_file_path == PLAYER_SCENE,
		"exactly one CharacterBody2D, the Player.tscn instance (%d found)" % bodies.size())
	_check(_player.collision_layer == 2 and _player.collision_mask == 1,
		"Player layer 2 / mask 1 (got %d / %d)" % [_player.collision_layer, _player.collision_mask])
	var camera := _player.get_node("Camera") as Camera2D
	_check(camera.is_current() and camera.zoom == Vector2.ONE,
		"Player/Camera is current at zoom 1 (current %s, zoom %s)" % [camera.is_current(), camera.zoom])
	_check(not ($Camera as Camera2D).enabled, "inherited review Camera disabled")
	var bad_scope := 0
	for group in _objects.get_children():
		if not (group as Node2D).y_sort_enabled:
			bad_scope += 1
	_check(y_sort_enabled and _objects.y_sort_enabled and bad_scope == 0 and _player.get_parent() == self
		and _player.z_index == 0 and _player.z_as_relative,
		"Player shares the Y-sorted scope with every prop group at z 0")


func _walk(start: Vector2, action: String, frames: int) -> Vector2:
	_player.teleport(start)
	await get_tree().physics_frame
	Input.action_press(action)
	for i in frames:
		await get_tree().physics_frame
	Input.action_release(action)
	await get_tree().physics_frame
	await get_tree().process_frame
	return _player.global_position


func _camera_follows() -> bool:
	var camera := _player.get_node("Camera") as Camera2D
	return camera.get_screen_center_position().distance_to(_player.global_position) <= 1.0


func _source_at(feet: Vector2) -> int:
	return _ground.get_cell_source_id(_ground.local_to_map(_ground.to_local(feet + Vector2(0, -1))))


func _check_walk(start: Vector2, action: String, frames: int, source: int, label: String) -> void:
	var start_source := _source_at(start)
	var end := await _walk(start, action, frames)
	var travel := start.distance_to(end)
	var expected := frames * PX_PER_FRAME
	var end_source := _source_at(end)
	_check(travel >= expected * MIN_TRAVEL_RATIO and end_source == source and _camera_follows(),
		"walk %s: %s -> %s, %.1f of %.1f px, ground %s -> %s, camera follows %s" % [
			label, start, end, travel, expected, SOURCE_NAMES.get(start_source, start_source),
			SOURCE_NAMES.get(end_source, end_source), _camera_follows()])


func _check_stop(prop_path: String, start: Vector2, action: String, label: String) -> void:
	var prop := _objects.get_node(prop_path) as Node2D
	var collision := prop.get_node("Body/Collision") as CollisionShape2D
	var half_height := (collision.shape as RectangleShape2D).size.y / 2.0
	var from_south := action == "move_up"
	var face_y := collision.global_position.y + (half_height if from_south else -half_height)
	var expected_y := face_y + (FOOTPRINT_HEIGHT if from_south else 0.0)
	var end := await _walk(start, action, 30)
	var stopped := absf(end.y - expected_y) <= STOP_TOLERANCE and absf(end.x - start.x) <= 0.5
	var in_front := end.y > prop.global_position.y
	var order_ok := in_front == from_south
	_check(stopped and order_ok and _camera_follows(),
		"stop at %s: feet %s, expected y %.2f; player drawn %s (feet y %.2f vs prop y %.2f); camera follows %s" % [
			label, end, expected_y, "in front" if in_front else "behind", end.y,
			prop.global_position.y, _camera_follows()])


func _check_bounds() -> void:
	var end := await _walk(Vector2(-340, -400), "move_left", 30)
	_check(absf(end.x - (-370.0)) <= STOP_TOLERANCE,
		"test bounds stop the player at the west ground edge (feet x %.2f, expected -370)" % end.x)

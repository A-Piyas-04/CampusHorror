extends Node2D
## TEMPORARY Milestone G composition check for MainGateCompositionTest.tscn. Verifies the ground
## (every cell filled from campus_ground), draw-order bands, that props are instances of the
## reusable prop scenes with a ContactShadow child, and sweeps a player-sized footprint
## (28 x 12 px, the Player's collision) north past the gate gap, wall and props.
## Optional: run windowed with `-- --screenshot=<absolute png path>` to save the view and quit.

const FOOTPRINT := Vector2(28, 12)
const SWEEP := Vector2(0, -40)
const GROUND_RECT := Rect2i(-6, -8, 20, 12)
const TILESET_PATH := "res://assets/tilesets/campus_ground.tres"
const SHADOW_SCENE := "res://scenes/props/common/ContactShadow.tscn"
const PROP_DIR := "res://scenes/props/"

## [start position (probe feet), expect_blocked, label]
var _cases: Array = [
	[Vector2(0, 40), false, "through the gate gap from the sidewalk"],
	[Vector2(-40, 40), false, "gate gap, 24 px from the west pier"],
	[Vector2(400, 40), true, "boundary wall from the sidewalk"],
	[Vector2(256, 40), true, "pier on a wall join"],
	[Vector2(-64, 40), true, "west gate pier"],
	[Vector2(290, -70), true, "south-row tree trunk"],
	[Vector2(320, -70), false, "under the south-row canopy, beside the trunk (and its shadow)"],
	[Vector2(95, -330), true, "palm trunk"],
	[Vector2(-128, -220), true, "plaza bench"],
	[Vector2(176, -110), true, "lamp post plinth"],
	[Vector2(448, -90), true, "hedge module between the south-row trees"],
	[Vector2(-128, -90), true, "hedge beside the path, west of the gate"],
	[Vector2(0, -90), false, "palm path between the gate hedges"],
	[Vector2(0, -300), false, "palm path north of the plaza"],
	[Vector2(288, -270), false, "worn-grass desire line"],
]

var _failures := 0
var _checks := 0


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[COMPOSITION] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	_check_ground()
	_check_objects()
	await _check_collisions()
	print("[COMPOSITION] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	await _maybe_screenshot()


func _check_ground() -> void:
	var ground := get_node("Ground") as TileMapLayer
	_check(ground != null and ground.tile_set != null and ground.tile_set.resource_path == TILESET_PATH,
		"Ground is a TileMapLayer using %s" % TILESET_PATH)
	_check(ground.z_index == -10, "Ground z_index -10 (got %d)" % ground.z_index)
	var missing := 0
	var bad := 0
	var counts := {}
	for y in range(GROUND_RECT.position.y, GROUND_RECT.end.y):
		for x in range(GROUND_RECT.position.x, GROUND_RECT.end.x):
			var source := ground.get_cell_source_id(Vector2i(x, y))
			if source == -1:
				missing += 1
			elif not ground.tile_set.has_source(source):
				bad += 1
			else:
				counts[source] = counts.get(source, 0) + 1
	_check(missing == 0 and bad == 0, "every Ground cell in %s filled (missing %d, invalid %d)" % [GROUND_RECT, missing, bad])
	_check(ground.get_used_cells().size() == GROUND_RECT.get_area(), "no cells outside the rectangle (%d used)" % ground.get_used_cells().size())
	_check(counts.size() == 4, "all four ground types used: %s" % counts)


func _check_objects() -> void:
	var objects := get_node("Objects") as Node2D
	_check(y_sort_enabled and objects.y_sort_enabled, "scene root and Objects are Y-sorted")
	var props := 0
	var not_instanced := 0
	var no_shadow := 0
	var bad_shadow := 0
	var bad_z := 0
	for group in objects.get_children():
		_check((group as Node2D).y_sort_enabled, "%s is Y-sorted" % group.name)
		for prop: Node2D in group.get_children():
			props += 1
			if not prop.scene_file_path.begins_with(PROP_DIR):
				not_instanced += 1
			if prop.z_index != 0:
				bad_z += 1
			var shadow := prop.get_node_or_null("ContactShadow") as Sprite2D
			if shadow == null:
				no_shadow += 1
			elif shadow.scene_file_path != SHADOW_SCENE or shadow.z_index != -9 \
					or shadow.position != Vector2.ZERO or shadow.get_child_count() != 0:
				bad_shadow += 1
	_check(props > 0 and not_instanced == 0, "%d props, all instances of scenes under %s (%d not)" % [props, PROP_DIR, not_instanced])
	_check(bad_z == 0, "every prop at z_index 0 (%d not)" % bad_z)
	_check(no_shadow == 0 and bad_shadow == 0, "every prop has a ContactShadow child at its origin, z -9, no collision (missing %d, wrong %d)" % [no_shadow, bad_shadow])


func _check_collisions() -> void:
	var probe := CharacterBody2D.new()
	probe.name = "FootprintProbe"
	probe.collision_layer = 0
	probe.collision_mask = 1
	probe.motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = FOOTPRINT
	shape.shape = rect
	shape.position = Vector2(0, -FOOTPRINT.y / 2.0)
	probe.add_child(shape)
	add_child(probe)
	await get_tree().physics_frame
	await get_tree().physics_frame
	for c: Array in _cases:
		var blocked := probe.test_move(Transform2D(0.0, c[0]), SWEEP)
		_check(blocked == c[1], "%s at %s: %s" % [c[2], c[0], "blocked" if blocked else "passes"])
	probe.queue_free()


func _maybe_screenshot() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--screenshot="):
			for i in 8:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			var path := arg.trim_prefix("--screenshot=")
			var err := get_viewport().get_texture().get_image().save_png(path)
			print("[COMPOSITION] screenshot %s -> %s" % [path, error_string(err)])
			get_tree().quit(0 if err == OK and _failures == 0 else 1)

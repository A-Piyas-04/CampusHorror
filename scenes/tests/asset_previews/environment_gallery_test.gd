extends Node2D
## TEMPORARY Milestone G gallery check for the first environment batch: sweeps a player-sized
## footprint (28 x 12 px, the Player's collision) north past each object and reports where it is
## blocked. Trunks, bench, lamp plinth and hedge must block; the tree canopy, ground tiles and the
## doorway opening must not.
## Optional: run windowed with `-- --screenshot=<absolute png path>` to save the view and quit.

const FOOTPRINT := Vector2(28, 12)
const SWEEP := Vector2(0, -40)

## [start position (probe feet), expect_blocked, label]
var _cases: Array = [
	[Vector2(256, -90), true, "broadleaf trunk"],
	[Vector2(316, -90), false, "under the broadleaf canopy, beside the trunk"],
	[Vector2(432, -100), true, "palm trunk"],
	[Vector2(-224, 62), true, "bench (from the walkway)"],
	[Vector2(-416, 80), true, "lamp post plinth"],
	[Vector2(-480, 254), true, "hedge module"],
	[Vector2(0, 254), false, "gap between the hedge runs (grass verge)"],
	[Vector2(320, 130), false, "walkway and grass (ground tiles have no collision)"],
	[Vector2(-160, -180), false, "through the doorway on the N-S path"],
]


func _ready() -> void:
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

	var failures := 0
	for c: Array in _cases:
		var blocked := probe.test_move(Transform2D(0.0, c[0]), SWEEP)
		var ok: bool = blocked == c[1]
		failures += 0 if ok else 1
		print("[GALLERY] %s %s at %s: %s" % ["ok  " if ok else "FAIL", c[2], c[0], "blocked" if blocked else "passes"])
	probe.queue_free()
	print("[GALLERY] %s (%d/%d)" % ["PASS" if failures == 0 else "FAIL", _cases.size() - failures, _cases.size()])

	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--screenshot="):
			for i in 8:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			var path := arg.trim_prefix("--screenshot=")
			var err := get_viewport().get_texture().get_image().save_png(path)
			print("[GALLERY] screenshot %s -> %s" % [path, error_string(err)])
			get_tree().quit(0 if err == OK and failures == 0 else 1)

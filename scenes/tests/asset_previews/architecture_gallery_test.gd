extends Node2D
## TEMPORARY Milestone G gallery check: sweeps a player-sized footprint (28 x 12 px, the
## Player's collision) north across the wall run and reports where it is blocked.
## The doorway opening must let it through; wall, window and pier sections must block it.

const FOOTPRINT := Vector2(28, 12)
const SWEEP := Vector2(0, -40)

## [x position, expect_blocked, label]
var _cases: Array = [
	[-96.0, false, "doorway opening centre"],
	[-96.0 + 6.0, false, "doorway opening, 6 px off centre"],
	[-192.0, true, "wall west of the doorway"],
	[0.0, true, "wall between doorway and window"],
	[96.0, true, "window module (sill blocks)"],
	[-144.0, true, "pier at the wall/doorway join"],
	[-96.0 + 16.0, true, "doorway jamb (footprint overlaps the east jamb)"],
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
		var start := Vector2(c[0], 20.0)
		var blocked := probe.test_move(Transform2D(0.0, start), SWEEP)
		var ok: bool = blocked == c[1]
		failures += 0 if ok else 1
		print("[GALLERY] %s %s at x=%.1f: %s" % ["ok  " if ok else "FAIL", c[2], c[0], "blocked" if blocked else "passes"])
	probe.queue_free()
	print("[GALLERY] %s (%d/%d)" % ["PASS" if failures == 0 else "FAIL", _cases.size() - failures, _cases.size()])

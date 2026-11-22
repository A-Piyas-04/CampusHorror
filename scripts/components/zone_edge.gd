class_name ZoneEdge
extends Area2D

## A walk-off transition between two exterior zones (decision D28): when the player walks into this strip at
## the zone's edge, Main runs the usual faded travel to `destination_spawn_id` in `destination_zone_id`.
## Place the destination spawn a few metres inside the neighbour zone (never inside its own edge strip), facing
## away from the edge, so arriving never triggers the way back. Layer 5 "trigger", mask 2 "player".

@export var destination_zone_id: String = ""
@export var destination_spawn_id: String = ""
## Size of the trigger strip in game px (centred on this node).
@export var size: Vector2 = Vector2(64, 400):
	set(value):
		size = value
		_apply_size()
## Shown in the editor and by tests.
@export var place_name: String = ""
## Optional story lock (like Door): in story mode the way is shut until the player holds this item / this
## GameState flag is set. The sandbox (no story director) ignores it.
@export var required_item: String = ""
@export var requires_flag: String = ""
## Toast shown when the locked strip is walked into (at most every few seconds).
@export var locked_message: String = "The way is blocked."

var _last_locked_toast := -100.0

var _shape: CollisionShape2D


func _ready() -> void:
	collision_layer = 16
	collision_mask = 2
	monitoring = true
	monitorable = false
	_shape = get_node_or_null("Shape") as CollisionShape2D
	# The scene's RectangleShape2D is one resource shared by every instance: take a private copy, or every edge
	# would end up the size of whichever edge ran _ready last.
	if _shape != null and _shape.shape != null:
		_shape.shape = _shape.shape.duplicate()
	_apply_size()
	body_entered.connect(_on_body_entered)


func _apply_size() -> void:
	if _shape == null:
		return
	var rect := _shape.shape as RectangleShape2D
	if rect == null:
		rect = RectangleShape2D.new()
		_shape.shape = rect
	rect.size = size


func _on_body_entered(body: Node) -> void:
	if not (body is Player) or not (body as Player).input_enabled:
		return
	var main := get_tree().get_first_node_in_group("main") as Main
	if main == null or main.is_transitioning():
		return
	# Locks are story locks: the sandbox (editor runs, tests) walks everywhere.
	if not is_open() and main.get_director() != null:
		var now := Time.get_ticks_msec() / 1000.0
		if now - _last_locked_toast > 4.0:
			_last_locked_toast = now
			var hud := get_tree().get_first_node_in_group("hud")
			if hud != null:
				hud.call("toast", locked_message)
		return
	main.travel(destination_zone_id, destination_spawn_id)


func is_open() -> bool:
	var has_item := required_item == "" or GameState.has_item(required_item)
	return has_item and (requires_flag == "" or GameState.has_flag(requires_flag))

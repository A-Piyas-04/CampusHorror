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

var _shape: CollisionShape2D


func _ready() -> void:
	collision_layer = 16
	collision_mask = 2
	monitoring = true
	monitorable = false
	_shape = get_node_or_null("Shape") as CollisionShape2D
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
	main.travel(destination_zone_id, destination_spawn_id)

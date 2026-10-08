@tool
class_name BlockoutBlock
extends StaticBody2D

## Placeholder faux-3D block for map blockouts (buildings, walls, fences, hedges).
## Origin = centre of the footprint's front (south, bottom-on-screen) edge, so it Y-sorts like any prop.
## Draws a roof raised by `wall_height` above the footprint plus the front wall face.
## Collision and the light occluder are generated from `footprint_size`; they are not saved in scenes.

## Ground footprint (width, depth). The footprint spans x -w/2..w/2, y -depth..0.
@export var footprint_size := Vector2(128, 64):
	set(value):
		footprint_size = value.max(Vector2.ONE)
		_update()
## Visual height of the front face in pixels. Has no effect on collision.
@export var wall_height := 64.0:
	set(value):
		wall_height = maxf(value, 0.0)
		_update()
@export var wall_color := Color(0.62, 0.28, 0.2):
	set(value):
		wall_color = value
		queue_redraw()
@export var roof_color := Color(0.45, 0.42, 0.4):
	set(value):
		roof_color = value
		queue_redraw()
## Pointed arches drawn evenly along the front face (0 = none).
@export_range(0, 32) var arch_count := 0:
	set(value):
		arch_count = value
		queue_redraw()
@export var arch_color := Color(0.22, 0.11, 0.08):
	set(value):
		arch_color = value
		queue_redraw()
## Whether the footprint casts 2D light shadows (occluder light mask 1).
@export var casts_shadow := true:
	set(value):
		casts_shadow = value
		_update()

var _collision := CollisionShape2D.new()
var _occluder := LightOccluder2D.new()


func _init() -> void:
	_collision.shape = RectangleShape2D.new()
	_occluder.occluder = OccluderPolygon2D.new()
	add_child(_collision, false, Node.INTERNAL_MODE_FRONT)
	add_child(_occluder, false, Node.INTERNAL_MODE_FRONT)
	_update()


func _update() -> void:
	if _collision == null:
		return
	var half_width := footprint_size.x / 2.0
	(_collision.shape as RectangleShape2D).size = footprint_size
	_collision.position = Vector2(0, -footprint_size.y / 2.0)
	_occluder.occluder.polygon = PackedVector2Array([
		Vector2(-half_width, -footprint_size.y), Vector2(half_width, -footprint_size.y),
		Vector2(half_width, 0), Vector2(-half_width, 0),
	])
	_occluder.occluder_light_mask = 1 if casts_shadow else 0
	queue_redraw()


func _draw() -> void:
	var width := footprint_size.x
	var depth := footprint_size.y
	var roof := Rect2(-width / 2.0, -depth - wall_height, width, depth)
	draw_rect(roof, roof_color)
	draw_rect(roof, roof_color.darkened(0.3), false, 2.0)
	draw_rect(Rect2(-width / 2.0, -wall_height, width, wall_height), wall_color)
	draw_line(Vector2(-width / 2.0, -wall_height), Vector2(width / 2.0, -wall_height), wall_color.darkened(0.4), 2.0)
	if arch_count <= 0 or wall_height < 8.0:
		return
	var bay := width / arch_count
	var arch_width := bay * 0.6
	var arch_height := wall_height * 0.72
	var base := -wall_height * 0.06
	for i in arch_count:
		var x := -width / 2.0 + bay * (i + 0.5)
		var spring := base - arch_height * 0.6
		var apex := base - arch_height
		draw_colored_polygon(PackedVector2Array([
			Vector2(x - arch_width / 2.0, base),
			Vector2(x - arch_width / 2.0, spring),
			Vector2(x - arch_width * 0.3, spring - (spring - apex) * 0.65),
			Vector2(x, apex),
			Vector2(x + arch_width * 0.3, spring - (spring - apex) * 0.65),
			Vector2(x + arch_width / 2.0, spring),
			Vector2(x + arch_width / 2.0, base),
		]), arch_color)

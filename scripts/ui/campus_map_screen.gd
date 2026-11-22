class_name CampusMapScreen
extends CanvasLayer

## The campus map (`map`: M / View), Explore mode's way-finding (D45). A board-style render of
## data/campus/campus_layout.json (assets/ui/campus_map.png, written by tools/campus/ui_map.py) with a pulsing
## "You are here" pin, like the official board at the Main Gate. Outdoors the pin follows the player's feet; inside a
## building it sits on that building's entrance. The game pauses while the map is open.

const MAP_TEXTURE := "res://assets/ui/campus_map.png"
const MAP_META := "res://assets/ui/campus_map.json"

var _root: Control
var _map: TextureRect
var _pin: Control
var _where: Label
var _meta: Dictionary = {}
var _open := false
var _last_campus_m := Vector2(466.0, 266.8)
var _t := 0.0


func _ready() -> void:
	layer = 38
	process_mode = Node.PROCESS_MODE_ALWAYS
	add_to_group("campus_map")
	if FileAccess.file_exists(MAP_META):
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MAP_META))
		if parsed is Dictionary:
			_meta = parsed
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.visible = false
	_root.modulate.a = 0.0
	add_child(_root)
	_root.add_child(UIStyle.dim(0.78))
	_map = TextureRect.new()
	_map.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_map.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_map.set_anchors_preset(Control.PRESET_FULL_RECT)
	_map.offset_left = 60
	_map.offset_right = -60
	_map.offset_top = 70
	_map.offset_bottom = -60
	if ResourceLoader.exists(MAP_TEXTURE):
		_map.texture = load(MAP_TEXTURE)
	_root.add_child(_map)
	_pin = Control.new()
	_pin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_pin.draw.connect(_draw_pin)
	_root.add_child(_pin)
	var title := UIStyle.label("IUT CAMPUS", 22, UIStyle.ACCENT)
	title.position = Vector2(64, 26)
	_root.add_child(title)
	_where = UIStyle.label("", 20, UIStyle.TEXT)
	_where.position = Vector2(260, 28)
	_root.add_child(_where)
	var hint := UIStyle.label("M / Esc  close", 15, UIStyle.TEXT_DIM)
	hint.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	hint.position = Vector2(-220, 30)
	_root.add_child(hint)


func is_open() -> bool:
	return _open


func open() -> void:
	if _open or _map.texture == null:
		return
	_open = true
	_refresh_where()
	_root.visible = true
	get_tree().paused = true
	create_tween().tween_property(_root, "modulate:a", 1.0, 0.18)


func close() -> void:
	if not _open:
		return
	_open = false
	get_tree().paused = false
	var tw := create_tween()
	tw.tween_property(_root, "modulate:a", 0.0, 0.15)
	tw.tween_callback(func() -> void: _root.visible = _open)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("map"):
		if _open:
			close()
		elif not _blocked():
			open()
		get_viewport().set_input_as_handled()
	elif _open and (event.is_action_pressed("pause") or event.is_action_pressed("ui_cancel")):
		close()
		get_viewport().set_input_as_handled()


func _blocked() -> bool:
	var main := get_tree().current_scene as Main
	if main == null or main.is_transitioning():
		return true
	var pause := get_tree().get_first_node_in_group("pause_menu")
	return pause != null and bool(pause.call("is_open"))


func _process(delta: float) -> void:
	var main := get_tree().current_scene as Main
	if main != null and main.get_current_zone_id() == "campus":
		var feet := main.get_player_feet_position()
		var ppm: Array = _meta.get("world_px_per_m", [32.0, 20.576])
		_last_campus_m = Vector2(feet.x / float(ppm[0]), feet.y / float(ppm[1]))
	if _open:
		_t += delta
		_pin.queue_redraw()


func _refresh_where() -> void:
	var main := get_tree().current_scene as Main
	var zone := main.get_current_zone_id() if main != null else ""
	var entrances: Dictionary = _meta.get("entrances", {})
	if zone != "campus" and entrances.has(zone):
		var e: Array = entrances[zone]
		_last_campus_m = Vector2(float(e[0]), float(e[1]))
		_where.text = "·  inside: %s" % e[2]
	elif zone != "campus" and not zone.is_empty():
		_where.text = "·  inside a building"
	else:
		_where.text = ""


## Metres -> screen position of the map texture as drawn (keep-aspect, centred).
func _to_screen(m: Vector2) -> Vector2:
	var tex := _map.texture
	if tex == null:
		return Vector2.ZERO
	var box := _map.get_global_rect()
	var ts := Vector2(tex.get_size())
	var s := minf(box.size.x / ts.x, box.size.y / ts.y)
	var origin := box.position + (box.size - ts * s) * 0.5
	var k := float(_meta.get("px_per_m", 3.2))
	var px := Vector2((m.x - float(_meta.get("x0", 0.0))) * k, (m.y - float(_meta.get("y0", 0.0))) * k)
	return origin + px * s


func _draw_pin() -> void:
	var p := _to_screen(_last_campus_m)
	var pulse := 0.5 + 0.5 * sin(_t * 4.0)
	_pin.draw_circle(p, 10.0 + pulse * 10.0, Color(0.85, 0.12, 0.12, 0.25 * (1.0 - pulse) + 0.1))
	# the board's red teardrop pin
	var tip := p
	var head := p + Vector2(0, -26)
	_pin.draw_colored_polygon(PackedVector2Array([tip, head + Vector2(-11, 4), head + Vector2(11, 4)]), Color(0.72, 0.1, 0.12))
	_pin.draw_circle(head, 11.5, Color(0.72, 0.1, 0.12))
	_pin.draw_circle(head, 5.0, Color(0.12, 0.02, 0.02))
	var font := ThemeDB.fallback_font
	_pin.draw_string_outline(font, head + Vector2(16, 6), "YOU ARE HERE", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, 4, Color(0, 0, 0, 0.8))
	_pin.draw_string(font, head + Vector2(16, 6), "YOU ARE HERE", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(1, 1, 1))

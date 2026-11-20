extends CanvasLayer

## World-space interaction prompt (roadmap I7), on `Main/UI/InteractionPrompt`.
## - Floats above the current target (Interactable.global_position + prompt_offset) and moves exactly with the
##   world: this layer uses `follow_viewport_enabled`, so it is drawn through the same camera transform as the
##   world (including interpolated camera motion), but it is its own canvas, so the night tint never darkens it.
## - Constant on-screen size at any zoom (scaled by 1 / camera zoom), kept inside the screen edges.
## - Shows the device's glyph for `interact` (InputGlyphs; switches between keyboard and gamepad on real use,
##   follows rebinding), the verb and the object name, and a ring that fills while a hold is in progress.
## - Fades in and out (0.12 s) instead of popping.

const FADE := 0.12
const RISE := 6.0
const EDGE_MARGIN := 16.0      # screen px

var _target: Interactable
var _tween: Tween
## Extra downward offset (screen px) that eases to 0 when the prompt appears.
var _rise := 0.0
var _anchor: Node2D
var _panel: PanelContainer
var _glyph: GlyphIcon
var _verb: Label
var _name: Label


func _ready() -> void:
	layer = 10
	follow_viewport_enabled = true
	_build()
	_anchor.visible = false
	_anchor.modulate.a = 0.0


func _build() -> void:
	_anchor = Node2D.new()
	_anchor.name = "Anchor"
	add_child(_anchor)
	_panel = PanelContainer.new()
	_panel.name = "Panel"
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.04, 0.04, 0.05, 0.72)
	sb.set_corner_radius_all(7)
	sb.content_margin_left = 10
	sb.content_margin_right = 14
	sb.content_margin_top = 6
	sb.content_margin_bottom = 6
	sb.anti_aliasing = true
	_panel.add_theme_stylebox_override("panel", sb)
	_anchor.add_child(_panel)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_child(row)
	_glyph = GlyphIcon.new()
	_glyph.name = "Glyph"
	row.add_child(_glyph)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", -2)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(col)
	_verb = _label(22, Color(0.98, 0.97, 0.94))
	_name = _label(16, Color(0.78, 0.77, 0.73))
	col.add_child(_verb)
	col.add_child(_name)


func _label(size: int, color: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.6))
	l.add_theme_constant_override("outline_size", 3)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _input(event: InputEvent) -> void:
	if InputGlyphs.note_event(event):
		_glyph.glyph = InputGlyphs.glyph(&"interact")


func _on_player_interaction_target_changed(target: Interactable) -> void:
	_target = target
	_glyph.progress = 0.0
	if target == null:
		_fade(false)
		return
	_verb.text = target.verb
	_name.text = target.object_name
	_name.visible = not target.object_name.is_empty()
	_glyph.glyph = InputGlyphs.glyph(&"interact")
	_panel.reset_size()
	_place()
	_fade(true)


func _on_player_interaction_hold_changed(progress: float) -> void:
	_glyph.progress = progress


func _process(_delta: float) -> void:
	if _anchor.visible and is_instance_valid(_target):
		_place()


## Puts the panel's bottom centre on the target's prompt point, at constant screen size, inside the screen.
func _place() -> void:
	var cam := get_viewport().get_camera_2d()
	var zoom := cam.zoom if cam != null else Vector2.ONE
	_anchor.scale = Vector2.ONE / zoom
	var world := _target.global_position + _target.prompt_offset
	var size := _panel.size / zoom
	if cam != null and cam.has_method("get_view_rect"):
		var view: Rect2 = cam.call("get_view_rect")
		var m := EDGE_MARGIN / zoom.x
		world.x = clampf(world.x, view.position.x + m + size.x * 0.5, view.end.x - m - size.x * 0.5)
		world.y = clampf(world.y, view.position.y + m + size.y, view.end.y - m)
	_anchor.position = world
	_panel.position = Vector2(-_panel.size.x * 0.5, -_panel.size.y + _rise)


func _fade(show: bool) -> void:
	if _tween != null:
		_tween.kill()
	if show:
		_anchor.visible = true
		_rise = RISE
	_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_tween.tween_property(_anchor, "modulate:a", 1.0 if show else 0.0, FADE)
	if show:
		_tween.tween_property(self, "_rise", 0.0, FADE)
	else:
		_tween.chain().tween_callback(func(): _anchor.visible = false)


# --- For tests -----------------------------------------------------------------------------------------------

func get_alpha() -> float:
	return _anchor.modulate.a if _anchor.visible else 0.0


func get_shown_target() -> Interactable:
	return _target


func get_texts() -> Array:
	return [_verb.text, _name.text if _name.visible else ""]


func get_glyph() -> Dictionary:
	return _glyph.glyph


func get_progress() -> float:
	return _glyph.progress


## World point the panel's bottom centre sits on.
func get_anchor_world() -> Vector2:
	return _anchor.position

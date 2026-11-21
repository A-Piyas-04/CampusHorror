class_name StoryCard
extends CanvasLayer

## Full-screen story cards (group "story_card"): the intro, chapter titles, blackouts and the chapter end.
## `play(lines, hold)` fades to black, types each line out in a serif face, holds, then fades away; await
## `finished`. While a card is up the world is paused and nothing else opens. Any interact / accept press
## completes the current line at once (and skips the hold), so a returning player is never stuck reading.

signal finished

const CHARS_PER_SECOND := 38.0

var _root: Control
var _bg: ColorRect
var _label: Label
var _sub: Label
var _open := false
var _skip := false


func _ready() -> void:
	layer = 50
	process_mode = Node.PROCESS_MODE_ALWAYS
	add_to_group("story_card")
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.visible = false
	add_child(_root)
	_bg = ColorRect.new()
	_bg.color = Color.BLACK
	_bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(_bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 26)
	center.add_child(col)
	_label = UIStyle.label("", 34, UIStyle.TEXT, true)
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_label.custom_minimum_size = Vector2(1200, 0)
	col.add_child(_label)
	_sub = UIStyle.label("", 16, UIStyle.TEXT_DIM)
	_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(_sub)


func is_open() -> bool:
	return _open


## Shows `lines` one after another. `keep_black`: stay black at the end (the caller fades out later via
## `fade_out()`), e.g. to swap zones behind the card.
func play(lines: Array, hold: float = 2.2, keep_black: bool = false, subtitle: String = "") -> void:
	var already_black := _root.visible and _bg.modulate.a > 0.99
	_open = true
	get_tree().paused = true
	_root.visible = true
	_label.text = ""
	_sub.text = subtitle
	_label.modulate.a = 1.0
	if not already_black:
		_bg.modulate.a = 0.0
		var t := create_tween()
		t.tween_property(_bg, "modulate:a", 1.0, 0.8)
		await t.finished
	for line: String in lines:
		_skip = false
		_label.text = line
		_label.visible_characters = 0
		var shown := 0.0
		while _label.visible_characters < line.length() and not _skip:
			shown += get_process_delta_time() * CHARS_PER_SECOND
			_label.visible_characters = mini(int(shown), line.length())
			await get_tree().process_frame
		_label.visible_characters = -1
		_skip = false
		var waited := 0.0
		while waited < hold + line.length() * 0.012 and not _skip:
			waited += get_process_delta_time()
			await get_tree().process_frame
		var out := create_tween()
		out.tween_property(_label, "modulate:a", 0.0, 0.5)
		await out.finished
		_label.modulate.a = 1.0
		_label.text = ""
	_sub.text = ""
	if not keep_black:
		await fade_out()
	else:
		finished.emit()


## Fades a black card away and gives the world back.
func fade_out(seconds: float = 1.2) -> void:
	get_tree().paused = false
	var t := create_tween()
	t.tween_property(_bg, "modulate:a", 0.0, seconds)
	await t.finished
	_root.visible = false
	_open = false
	finished.emit()


## Instant black (e.g. the moment of a blackout); call `fade_out()` later.
func black() -> void:
	_root.visible = true
	_bg.modulate.a = 1.0
	_label.text = ""
	_open = true


func _unhandled_input(event: InputEvent) -> void:
	if not _open:
		return
	if event.is_action_pressed("interact") or event.is_action_pressed("ui_accept"):
		_skip = true
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("pause") or event.is_action_pressed("ui_cancel"):
		get_viewport().set_input_as_handled()

extends CanvasLayer

## Reads notes, logbooks and signs (group "note_viewer"). The world pauses while a note is open (fair in a horror
## game: you are never caught while reading). A paper panel with a serif title and body; any of interact /
## ui_cancel / pause closes it. Notes are added to the journal by GameState.mark_note_read.

signal closed

var _root: Control
var _title: Label
var _body: Label
var _open := false
var _opened_frame := 0


func _ready() -> void:
	layer = 30
	process_mode = Node.PROCESS_MODE_ALWAYS
	add_to_group("note_viewer")
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.visible = false
	add_child(_root)
	_root.add_child(UIStyle.dim(0.55))
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var paper := PanelContainer.new()
	var sb := UIStyle.panel_style(UIStyle.PAPER, 3, 46)
	sb.shadow_color = Color(0, 0, 0, 0.5)
	sb.shadow_size = 18
	paper.add_theme_stylebox_override("panel", sb)
	paper.custom_minimum_size = Vector2(720, 0)
	center.add_child(paper)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 18)
	paper.add_child(col)
	_title = UIStyle.label("", 30, UIStyle.INK, true)
	col.add_child(_title)
	_body = UIStyle.label("", 21, UIStyle.INK, true)
	_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_body.custom_minimum_size = Vector2(628, 0)
	col.add_child(_body)
	var hint := UIStyle.label("Close", 15, Color(UIStyle.INK, 0.6))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	col.add_child(hint)


func is_open() -> bool:
	return _open


func get_text() -> Array:
	return [_title.text, _body.text]


func show_note(title: String, body: String) -> void:
	_title.text = title
	_body.text = body
	_root.visible = true
	_root.modulate.a = 0.0
	create_tween().tween_property(_root, "modulate:a", 1.0, 0.18)
	_open = true
	AudioDirector.play_ui(&"paper", -6.0)
	_opened_frame = Engine.get_process_frames()
	get_tree().paused = true


func close() -> void:
	if not _open:
		return
	_open = false
	_root.visible = false
	get_tree().paused = false
	closed.emit()


func _unhandled_input(event: InputEvent) -> void:
	if not _open or Engine.get_process_frames() - _opened_frame < 2:
		return
	if event.is_action_pressed("interact") or event.is_action_pressed("ui_cancel") or event.is_action_pressed("pause") \
			or event.is_action_pressed("ui_accept"):
		close()
		get_viewport().set_input_as_handled()

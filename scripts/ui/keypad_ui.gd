class_name KeypadUI
extends CanvasLayer

## Number keypad screen (group "keypad_ui") used by Keypad components (breaker panels, key boxes).
## `ask(title, length)` pauses the world and returns the code the player typed ("" if they backed out).
## Mouse, keyboard digits / Backspace / Enter, and gamepad focus all work.

signal _done(code: String)

var _root: Control
var _title: Label
var _display: Label
var _message: Label
var _length := 4
var _code := ""
var _open := false
var _first: Button


func _ready() -> void:
	layer = 35
	process_mode = Node.PROCESS_MODE_ALWAYS
	add_to_group("keypad_ui")
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.visible = false
	add_child(_root)
	_root.add_child(UIStyle.dim(0.5))
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var panel := PanelContainer.new()
	var sb := UIStyle.panel_style(Color(0.09, 0.095, 0.1, 0.97), 6, 30)
	sb.border_color = Color(0.35, 0.35, 0.33)
	sb.set_border_width_all(2)
	panel.add_theme_stylebox_override("panel", sb)
	center.add_child(panel)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 16)
	panel.add_child(col)
	_title = UIStyle.label("", 20, UIStyle.TEXT_DIM)
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(_title)
	var screen := PanelContainer.new()
	screen.add_theme_stylebox_override("panel", UIStyle.panel_style(Color(0.05, 0.12, 0.07), 4, 12))
	col.add_child(screen)
	_display = UIStyle.label("", 44, Color(0.45, 1.0, 0.55))
	_display.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_display.custom_minimum_size = Vector2(300, 0)
	screen.add_child(_display)
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	col.add_child(grid)
	for key in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "OK"]:
		var b := Button.new()
		b.text = key
		b.custom_minimum_size = Vector2(92, 64)
		b.focus_mode = Control.FOCUS_ALL
		b.add_theme_font_size_override("font_size", 26)
		var normal := UIStyle.panel_style(Color(0.2, 0.2, 0.2), 6, 6)
		var focus := UIStyle.panel_style(Color(0.32, 0.3, 0.26), 6, 6)
		focus.border_color = UIStyle.ACCENT
		focus.set_border_width_all(2)
		b.add_theme_stylebox_override("normal", normal)
		b.add_theme_stylebox_override("hover", focus)
		b.add_theme_stylebox_override("focus", focus)
		b.add_theme_stylebox_override("pressed", UIStyle.panel_style(Color(0.4, 0.36, 0.28), 6, 6))
		b.pressed.connect(_press.bind(key))
		grid.add_child(b)
		if _first == null:
			_first = b
	_message = UIStyle.label("Esc to step back", 15, UIStyle.TEXT_DIM)
	_message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(_message)


func is_open() -> bool:
	return _open


func ask(title: String, length: int = 4) -> String:
	_title.text = title
	_length = length
	_code = ""
	_refresh()
	_message.text = "Esc to step back"
	_open = true
	_root.visible = true
	get_tree().paused = true
	_first.grab_focus()
	var code: String = await _done
	return code


## Shows a result line under the keypad for a moment, then closes (the component decides what it means).
func flash(text: String, good: bool) -> void:
	_message.text = text
	_display.add_theme_color_override("font_color", Color(0.45, 1.0, 0.55) if good else Color(1.0, 0.35, 0.3))


func _press(key: String) -> void:
	AudioDirector.play_ui(&"keypad_beep", -8.0)
	match key:
		"C":
			_code = ""
		"OK":
			_finish(_code)
			return
		_:
			if _code.length() < _length:
				_code += key
	_refresh()
	if _code.length() == _length:
		await get_tree().create_timer(0.25, true, false, true).timeout
		if _open and _code.length() == _length:
			_finish(_code)


func _refresh() -> void:
	_display.add_theme_color_override("font_color", Color(0.45, 1.0, 0.55))
	var s := ""
	for i in _length:
		s += (_code[i] if i < _code.length() else "_") + (" " if i < _length - 1 else "")
	_display.text = s


func _finish(code: String) -> void:
	if not _open:
		return
	_open = false
	_root.visible = false
	get_tree().paused = false
	_done.emit(code)


func _unhandled_input(event: InputEvent) -> void:
	if not _open:
		return
	if event.is_action_pressed("ui_cancel") or event.is_action_pressed("pause"):
		_finish("")
		get_viewport().set_input_as_handled()
		return
	var key := event as InputEventKey
	if key != null and key.pressed and not key.echo:
		if key.keycode >= KEY_0 and key.keycode <= KEY_9:
			_press(str(key.keycode - KEY_0))
			get_viewport().set_input_as_handled()
		elif key.keycode >= KEY_KP_0 and key.keycode <= KEY_KP_9:
			_press(str(key.keycode - KEY_KP_0))
			get_viewport().set_input_as_handled()
		elif key.keycode == KEY_BACKSPACE:
			_code = _code.substr(0, maxi(_code.length() - 1, 0))
			_refresh()
			get_viewport().set_input_as_handled()

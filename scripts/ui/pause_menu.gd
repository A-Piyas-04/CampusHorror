extends CanvasLayer

## Pause menu (group "pause_menu"): Resume, Journal, Settings, Quit to title, Quit game.
## `pause` (Esc / Start) opens and closes it. It never opens over a note, a keypad, a story card or a zone travel.
## The journal shows the current objective and every note read so far (open one to read it again).

var _root: Control
var _buttons: VBoxContainer
var _content: PanelContainer
var _open := false
var _first: Button


func _ready() -> void:
	layer = 40
	process_mode = Node.PROCESS_MODE_ALWAYS
	add_to_group("pause_menu")
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.visible = false
	add_child(_root)
	_root.add_child(UIStyle.dim(0.62))
	var row := HBoxContainer.new()
	row.set_anchors_preset(Control.PRESET_FULL_RECT)
	row.offset_left = 120
	row.offset_top = 150
	row.offset_right = -120
	row.offset_bottom = -120
	row.add_theme_constant_override("separation", 60)
	_root.add_child(row)
	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(340, 0)
	left.add_theme_constant_override("separation", 10)
	row.add_child(left)
	left.add_child(UIStyle.label("The Quiet Hours", 40, UIStyle.TEXT, true))
	left.add_child(UIStyle.label("PAUSED", 14, UIStyle.ACCENT))
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 30)
	left.add_child(spacer)
	_buttons = VBoxContainer.new()
	_buttons.add_theme_constant_override("separation", 6)
	left.add_child(_buttons)
	_first = _add_button("Resume", close)
	_add_button("Journal", _show_journal)
	_add_button("Settings", _show_settings)
	_add_button("Quit to title", func() -> void:
		close()
		_save_explore()
		Game.quit_to_title())
	_add_button("Quit game", func() -> void:
		_save_explore()
		get_tree().quit())
	_content = PanelContainer.new()
	_content.add_theme_stylebox_override("panel", UIStyle.panel_style(UIStyle.PANEL, 10, 30))
	_content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_content.visible = false
	row.add_child(_content)


## Explore mode keeps the walk: leaving saves where you are, so Continue brings you back (D45).
func _save_explore() -> void:
	var main := get_tree().current_scene as Main
	if main != null and main.is_explore() and not main.is_transitioning():
		SaveService.save_game()


func _add_button(text: String, action: Callable) -> Button:
	var b := UIStyle.button(text, 28)
	b.pressed.connect(action)
	_buttons.add_child(b)
	return b


func is_open() -> bool:
	return _open


func open() -> void:
	if _open:
		return
	_open = true
	_root.visible = true
	_content.visible = false
	get_tree().paused = true
	_first.grab_focus()


func close() -> void:
	if not _open:
		return
	_open = false
	_root.visible = false
	get_tree().paused = false


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed("pause"):
		if _open and event.is_action_pressed("ui_cancel"):
			close()
			get_viewport().set_input_as_handled()
		return
	if _open:
		close()
		get_viewport().set_input_as_handled()
		return
	if _blocked():
		return
	open()
	get_viewport().set_input_as_handled()


## Something else owns the screen: a note, the keypad, a story card, a travel fade, or the game is paused already.
func _blocked() -> bool:
	if get_tree().paused:
		return true
	for group in ["note_viewer", "keypad_ui", "story_card"]:
		var n := get_tree().get_first_node_in_group(group)
		if n != null and n.has_method("is_open") and bool(n.call("is_open")):
			return true
	var main := get_tree().get_first_node_in_group("main") as Main
	return main != null and main.is_transitioning()


func _clear_content() -> void:
	for c in _content.get_children():
		c.queue_free()
	_content.visible = true


func _show_settings() -> void:
	_clear_content()
	var panel := SettingsPanel.new()
	_content.add_child(panel)
	await get_tree().process_frame
	if panel.first_focus != null:
		panel.first_focus.grab_focus()


func _show_journal() -> void:
	_clear_content()
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 12)
	_content.add_child(col)
	col.add_child(UIStyle.label("OBJECTIVE", 14, UIStyle.ACCENT))
	var obj := UIStyle.label(GameState.objective if not GameState.objective.is_empty() else "—", 24, UIStyle.TEXT, true)
	obj.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	col.add_child(obj)
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 16)
	col.add_child(gap)
	col.add_child(UIStyle.label("NOTES", 14, UIStyle.ACCENT))
	var split := HBoxContainer.new()
	split.add_theme_constant_override("separation", 30)
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(split)
	var list := VBoxContainer.new()
	list.custom_minimum_size = Vector2(320, 0)
	split.add_child(list)
	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	split.add_child(scroll)
	var text := UIStyle.label("", 19, UIStyle.TEXT, true)
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(text)
	var notes := GameState.get_read_notes()
	if notes.is_empty():
		list.add_child(UIStyle.label("Nothing yet.", 20, UIStyle.TEXT_DIM))
	var first: Button = null
	for id in notes:
		var t: Array = GameState.get_note_text(id)
		var b := UIStyle.button(t[0] if not String(t[0]).is_empty() else id, 20)
		b.focus_entered.connect(func() -> void: text.text = "%s\n\n%s" % [t[0], t[1]])
		list.add_child(b)
		if first == null:
			first = b
	await get_tree().process_frame
	if first != null:
		first.grab_focus()

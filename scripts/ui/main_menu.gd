extends Control

## Title screen (the project's main scene): New game, Continue, Settings, Quit over a slow night shot of the campus.
## The background is assets/ui/title_background.png (a capture of the night Main Gate) drifting very slowly, with a
## vignette and a faint flicker, so the screen is alive but calm. Starting a game hands over to `Game`.

const BACKGROUND := "res://assets/ui/title_background.png"

var _bg: TextureRect
var _menu: VBoxContainer
var _side: PanelContainer
var _t := 0.0
var _confirm: VBoxContainer


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var base := ColorRect.new()
	base.color = Color(0.02, 0.022, 0.03)
	base.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(base)
	_bg = TextureRect.new()
	_bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_bg.pivot_offset = Vector2(960, 540)
	if ResourceLoader.exists(BACKGROUND):
		_bg.texture = load(BACKGROUND)
	add_child(_bg)
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = load("res://assets/shaders/title_vignette.gdshader")
	shade.material = mat
	add_child(shade)

	var col := VBoxContainer.new()
	col.position = Vector2(150, 250)
	col.add_theme_constant_override("separation", 6)
	add_child(col)
	var title := UIStyle.label("The Quiet Hours", 84, UIStyle.TEXT, true)
	title.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	title.add_theme_constant_override("shadow_offset_y", 4)
	col.add_child(title)
	col.add_child(UIStyle.label("CHAPTER 1  ·  LIGHTS OUT", 18, UIStyle.ACCENT))
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 70)
	col.add_child(gap)
	_menu = VBoxContainer.new()
	_menu.add_theme_constant_override("separation", 8)
	col.add_child(_menu)
	var has_save := SaveService.has_save()
	var cont := _add("Continue", Game.continue_game)
	cont.disabled = not has_save
	cont.visible = has_save
	_add("New game", _on_new_game)
	_add("Settings", _toggle_settings)
	_add("Quit", func() -> void: get_tree().quit())

	_side = PanelContainer.new()
	_side.add_theme_stylebox_override("panel", UIStyle.panel_style(UIStyle.PANEL, 10, 30))
	_side.position = Vector2(820, 330)
	_side.visible = false
	add_child(_side)

	var foot := UIStyle.label("Headphones recommended.  Islamic University of Technology, Gazipur, after midnight.", 15,
		UIStyle.TEXT_DIM)
	foot.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	foot.position = Vector2(150, -70)
	add_child(foot)
	# The night outside, quietly, under the menu.
	var bed := ZoneProfile.new()
	bed.ambience = load("res://assets/audio/ambience/night_field.wav") as AudioStream
	bed.ambience_volume_db = -12.0
	AudioDirector.apply_profile(bed)
	modulate.a = 0.0
	create_tween().tween_property(self, "modulate:a", 1.0, 1.4)
	await get_tree().process_frame
	(_menu.get_child(0 if has_save else 1) as Button).grab_focus()


func _add(text: String, action: Callable) -> Button:
	var b := UIStyle.button(text, 32)
	b.pressed.connect(action)
	_menu.add_child(b)
	return b


func _on_new_game() -> void:
	if not SaveService.has_save():
		_start_new()
		return
	_side.visible = true
	for c in _side.get_children():
		c.queue_free()
	_confirm = VBoxContainer.new()
	_confirm.add_theme_constant_override("separation", 12)
	_side.add_child(_confirm)
	var q := UIStyle.label("Start over? Your saved progress will be replaced.", 22, UIStyle.TEXT, true)
	_confirm.add_child(q)
	var yes := UIStyle.button("Start a new game", 26)
	yes.pressed.connect(_start_new)
	_confirm.add_child(yes)
	var no := UIStyle.button("Back", 26)
	no.pressed.connect(func() -> void:
		_side.visible = false
		(_menu.get_child(1) as Button).grab_focus())
	_confirm.add_child(no)
	await get_tree().process_frame
	no.grab_focus()


func _start_new() -> void:
	var t := create_tween()
	t.tween_property(self, "modulate", Color.BLACK, 0.8)
	await t.finished
	Game.new_game()


func _toggle_settings() -> void:
	for c in _side.get_children():
		c.queue_free()
	_side.visible = not _side.visible
	if _side.visible:
		var panel := SettingsPanel.new()
		_side.add_child(panel)
		await get_tree().process_frame
		if panel.first_focus != null:
			panel.first_focus.grab_focus()


func _unhandled_input(event: InputEvent) -> void:
	if _side.visible and (event.is_action_pressed("ui_cancel") or event.is_action_pressed("pause")):
		_side.visible = false
		(_menu.get_child(1) as Button).grab_focus()
		get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	_t += delta
	var s := 1.06 + 0.02 * sin(_t * 0.05)
	_bg.scale = Vector2(s, s)
	_bg.position = Vector2(sin(_t * 0.031) * 14.0, cos(_t * 0.023) * 8.0)
	var flick := 1.0 - 0.05 * maxf(sin(_t * 23.0) * sin(_t * 1.7) * sin(_t * 0.37), 0.0)
	_bg.modulate = Color(flick, flick, flick)

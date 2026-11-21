class_name SettingsPanel
extends VBoxContainer

## Volume sliders and the fullscreen switch, shared by the title screen and the pause menu.
## Every change applies at once and is saved by the `Settings` autoload.

const ROWS := [["master", "Master volume"], ["music", "Music"], ["ambience", "Ambience"],
	["effects", "Effects"], ["ui", "Interface"]]

var first_focus: Control


func _ready() -> void:
	add_theme_constant_override("separation", 14)
	add_child(UIStyle.label("SETTINGS", 14, UIStyle.ACCENT))
	for row: Array in ROWS:
		var line := HBoxContainer.new()
		line.add_theme_constant_override("separation", 18)
		var name_label := UIStyle.label(row[1], 20)
		name_label.custom_minimum_size = Vector2(220, 0)
		line.add_child(name_label)
		var slider := HSlider.new()
		slider.min_value = 0.0
		slider.max_value = 1.0
		slider.step = 0.05
		slider.custom_minimum_size = Vector2(300, 28)
		slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		slider.value = float(Settings.volumes.get(row[0], 1.0))
		slider.focus_mode = Control.FOCUS_ALL
		var key: String = row[0]
		var pct := UIStyle.label("%d%%" % roundi(slider.value * 100.0), 18, UIStyle.TEXT_DIM)
		pct.custom_minimum_size = Vector2(60, 0)
		slider.value_changed.connect(func(v: float) -> void:
			Settings.set_volume(key, v)
			pct.text = "%d%%" % roundi(v * 100.0))
		line.add_child(slider)
		line.add_child(pct)
		add_child(line)
		if first_focus == null:
			first_focus = slider
	var fs := CheckButton.new()
	fs.text = "Fullscreen"
	fs.button_pressed = Settings.fullscreen
	fs.add_theme_font_size_override("font_size", 20)
	fs.add_theme_color_override("font_color", UIStyle.TEXT)
	fs.add_theme_color_override("font_focus_color", UIStyle.ACCENT)
	fs.add_theme_color_override("font_hover_color", UIStyle.TEXT)
	fs.toggled.connect(func(on: bool) -> void: Settings.set_fullscreen(on))
	add_child(fs)
	var hint := UIStyle.label("Move: WASD / stick   Sprint: Shift   Sneak: Ctrl   Lantern: F   Interact: E   Pause: Esc",
		15, UIStyle.TEXT_DIM)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.custom_minimum_size = Vector2(600, 0)
	add_child(hint)

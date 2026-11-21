extends Node

## Autoload `Settings`: player preferences, saved to user://settings.cfg and applied at start.
## Volumes are linear 0..1 per bus; fullscreen on / off.

const PATH := "user://settings.cfg"
const BUSES := {"master": &"Master", "music": &"Music", "ambience": &"Ambience", "effects": &"World", "ui": &"UI"}

var volumes := {"master": 0.9, "music": 0.8, "ambience": 0.8, "effects": 0.9, "ui": 0.8}
var fullscreen := false


func _ready() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) == OK:
		for k in volumes:
			volumes[k] = float(cfg.get_value("audio", k, volumes[k]))
		fullscreen = bool(cfg.get_value("video", "fullscreen", fullscreen))
	apply()


func apply() -> void:
	for k in volumes:
		var idx := AudioServer.get_bus_index(BUSES[k])
		if idx != -1:
			var db := linear_to_db(maxf(float(volumes[k]), 0.0001))
			AudioServer.set_bus_volume_db(idx, db)
			AudioDirector.set_bus_base(BUSES[k], db)
	if DisplayServer.get_name() != "headless":
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED)


func set_volume(key: String, value: float) -> void:
	volumes[key] = clampf(value, 0.0, 1.0)
	apply()
	save()


func set_fullscreen(on: bool) -> void:
	fullscreen = on
	apply()
	save()


func save() -> void:
	var cfg := ConfigFile.new()
	for k in volumes:
		cfg.set_value("audio", k, volumes[k])
	cfg.set_value("video", "fullscreen", fullscreen)
	cfg.save(PATH)

extends Node

## Writes the persistent game state to disk as JSON and loads it back. Registered as the `SaveService` autoload.
## One save file; no slots, autosave or migrations.

const SAVE_PATH := "user://save.json"
## Bump when the save format changes. Files with any other version are refused.
const SAVE_VERSION := 1


func _unhandled_input(event: InputEvent) -> void:
	# TEMPORARY developer controls until a save UI exists.
	if event.is_action_pressed("debug_save"):
		save_game()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("debug_load"):
		load_game()
		get_viewport().set_input_as_handled()


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func save_game() -> bool:
	var main := _get_main()
	if main == null:
		return false
	var zone_id := main.get_current_zone_id()
	if zone_id.is_empty():
		push_error("[SAVE] No zone is loaded; nothing saved.")
		return false
	var feet := main.get_player_feet_position()
	var data := {
		"save_version": SAVE_VERSION,
		"zone_id": zone_id,
		"player_position": {"x": feet.x, "y": feet.y},
		"collected_ids": Array(GameState.get_collected_ids()),
	}
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file == null:
		push_error("[SAVE] Can't write '%s': %s." % [_display_path(), error_string(FileAccess.get_open_error())])
		return false
	file.store_string(JSON.stringify(data, "\t", false))
	var write_error := file.get_error()
	file.close()
	if write_error != OK:
		push_error("[SAVE] Writing '%s' failed: %s." % [_display_path(), error_string(write_error)])
		return false
	print("[SAVE] Saved '%s' at %s to '%s'." % [zone_id, feet, _display_path()])
	return true


## Restores GameState, the zone and the player's feet position from the save file.
## Validates the whole file first; on any problem it reports why and changes nothing.
func load_game() -> bool:
	var main := _get_main()
	if main == null:
		return false
	if not has_save():
		print("[SAVE] No save file at '%s'; nothing loaded." % _display_path())
		return false
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		return _reject("can't open it (%s)" % error_string(FileAccess.get_open_error()))
	var text := file.get_as_text()
	file.close()

	var json := JSON.new()
	if json.parse(text) != OK:
		return _reject("malformed JSON at line %d (%s)" % [json.get_error_line(), json.get_error_message()])
	if not (json.data is Dictionary):
		return _reject("the top level is not a JSON object")
	var data: Dictionary = json.data

	var version: Variant = data.get("save_version")
	if not (version is float or version is int) or version != floorf(version):
		return _reject("'save_version' is missing or not a whole number")
	if int(version) != SAVE_VERSION:
		return _reject("unsupported save_version %d (this build reads version %d)" % [int(version), SAVE_VERSION])

	var zone_id: Variant = data.get("zone_id")
	if not (zone_id is String) or not main.has_zone(zone_id):
		return _reject("'zone_id' %s is not a known zone" % JSON.stringify(zone_id))

	var position_data: Variant = data.get("player_position")
	if not (position_data is Dictionary) \
			or not (position_data.get("x") is float or position_data.get("x") is int) \
			or not (position_data.get("y") is float or position_data.get("y") is int):
		return _reject("'player_position' must be an object with numeric 'x' and 'y'")
	var feet := Vector2(position_data["x"], position_data["y"])

	var ids_data: Variant = data.get("collected_ids")
	if not (ids_data is Array):
		return _reject("'collected_ids' must be an array")
	var collected_ids := PackedStringArray()
	for id: Variant in ids_data:
		if not (id is String) or id.is_empty():
			return _reject("'collected_ids' contains %s, which is not a non-empty string" % JSON.stringify(id))
		collected_ids.append(id)

	GameState.restore_collected_ids(collected_ids)
	if not main.enter_zone_at_position(zone_id, feet):
		return false
	print("[SAVE] Loaded '%s' at %s with %d collected id(s)." % [zone_id, feet, collected_ids.size()])
	return true


func _reject(reason: String) -> bool:
	push_error("[SAVE] Can't load '%s': %s. Nothing was changed." % [_display_path(), reason])
	return false


func _get_main() -> Main:
	var main := get_tree().current_scene as Main
	if main == null:
		push_error("[SAVE] Save/load only works while Main is the current scene.")
	return main


func _display_path() -> String:
	return ProjectSettings.globalize_path(SAVE_PATH)

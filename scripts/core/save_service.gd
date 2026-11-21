extends Node

## Writes the persistent game state to disk as JSON and loads it back. Registered as the `SaveService` autoload.
## One save file, written atomically (temp file + rename, so a crash mid-write can't corrupt it). Version 2 adds the
## whole GameState (flags, items, notes, objective, lantern fuel); version 1 files still load (no flags then).
## `checkpoint()` is the autosave used by story beats and zone entries. F6 / F9 developer keys live in
## `scripts/debug/debug_tools.gd` (debug builds only).

## A save was written (`auto` = checkpoint rather than a manual save). The HUD shows a quiet "Progress saved".
signal saved(auto: bool)

const SAVE_PATH := "user://save.json"
## The file actually used. Tests point it elsewhere (and back) so they never touch the player's save.
var save_path := SAVE_PATH
## Bump when the save format changes. Versions in READABLE_VERSIONS load; anything else is refused.
const SAVE_VERSION := 2
const READABLE_VERSIONS := [1, 2]


func has_save() -> bool:
	return FileAccess.file_exists(save_path)


## Autosave at a story beat or zone entry (no-op while a travel is running or no zone is loaded).
func checkpoint() -> bool:
	var main := _get_main()
	if main == null or main.is_transitioning() or main.get_current_zone_id().is_empty():
		return false
	return _write(true)


func save_game() -> bool:
	return _write(false)


func _write(auto: bool) -> bool:
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
		"state": GameState.to_dict(),
	}
	var tmp_path := save_path + ".tmp"
	var file := FileAccess.open(tmp_path, FileAccess.WRITE)
	if file == null:
		push_error("[SAVE] Can't write '%s': %s." % [_display_path(), error_string(FileAccess.get_open_error())])
		return false
	file.store_string(JSON.stringify(data, "\t", false))
	var write_error := file.get_error()
	file.close()
	if write_error != OK:
		push_error("[SAVE] Writing '%s' failed: %s." % [_display_path(), error_string(write_error)])
		return false
	var rename_error := DirAccess.rename_absolute(ProjectSettings.globalize_path(tmp_path), ProjectSettings.globalize_path(save_path))
	if rename_error != OK:
		push_error("[SAVE] Replacing '%s' failed: %s." % [_display_path(), error_string(rename_error)])
		return false
	print("[SAVE] %s '%s' at %s to '%s'." % ["Checkpoint" if auto else "Saved", zone_id, feet, _display_path()])
	saved.emit(auto)
	return true


## Restores GameState, the zone and the player's feet position from the save file.
## Validates the whole file first; on any problem it reports why and changes nothing.
func load_game() -> bool:
	var main := _get_main()
	if main == null:
		return false
	var save := _read_valid(main)
	if save.is_empty():
		return false
	if main.is_transitioning():
		return _reject("a zone travel is already in progress")
	_restore_state(save)
	# Faded travel (roadmap I5); the swap happens behind the black screen a moment later.
	if not main.travel_to_position(save.zone_id, save.feet):
		return false
	print("[SAVE] Loaded '%s' at %s with %d collected id(s)." % [save.zone_id, save.feet, save.collected_ids.size()])
	return true


## Game start in "continue" mode: restores the save instantly (the screen is still black). False = no usable save.
func load_at_start(main: Main) -> bool:
	if not has_save():
		return false
	var save := _read_valid(main)
	if save.is_empty():
		return false
	_restore_state(save)
	print("[SAVE] Continuing '%s' at %s." % [save.zone_id, save.feet])
	return main.enter_zone_at_position(save.zone_id, save.feet)


func _restore_state(save: Dictionary) -> void:
	GameState.restore_collected_ids(save.collected_ids)
	GameState.from_dict(save.state)


## Reads and validates the save file: {zone_id, feet, collected_ids, state}, or {} after reporting why not.
func _read_valid(main: Main) -> Dictionary:
	if not has_save():
		print("[SAVE] No save file at '%s'; nothing loaded." % _display_path())
		return {}
	var file := FileAccess.open(save_path, FileAccess.READ)
	if file == null:
		return _fail("can't open it (%s)" % error_string(FileAccess.get_open_error()))
	var text := file.get_as_text()
	file.close()

	var json := JSON.new()
	if json.parse(text) != OK:
		return _fail("malformed JSON at line %d (%s)" % [json.get_error_line(), json.get_error_message()])
	if not (json.data is Dictionary):
		return _fail("the top level is not a JSON object")
	var data: Dictionary = json.data

	var version: Variant = data.get("save_version")
	if not (version is float or version is int) or version != floorf(version):
		return _fail("'save_version' is missing or not a whole number")
	if not READABLE_VERSIONS.has(int(version)):
		return _fail("unsupported save_version %d (this build reads versions %s)" % [int(version), READABLE_VERSIONS])

	var zone_id: Variant = data.get("zone_id")
	if not (zone_id is String) or not main.has_zone(zone_id):
		return _fail("'zone_id' %s is not a known zone" % JSON.stringify(zone_id))

	var position_data: Variant = data.get("player_position")
	if not (position_data is Dictionary) \
			or not (position_data.get("x") is float or position_data.get("x") is int) \
			or not (position_data.get("y") is float or position_data.get("y") is int):
		return _fail("'player_position' must be an object with numeric 'x' and 'y'")
	var feet := Vector2(position_data["x"], position_data["y"])

	var ids_data: Variant = data.get("collected_ids")
	if not (ids_data is Array):
		return _fail("'collected_ids' must be an array")
	var collected_ids := PackedStringArray()
	for id: Variant in ids_data:
		if not (id is String) or id.is_empty():
			return _fail("'collected_ids' contains %s, which is not a non-empty string" % JSON.stringify(id))
		collected_ids.append(id)

	var state: Variant = data.get("state", {})
	if not (state is Dictionary):
		return _fail("'state' must be an object")
	return {"zone_id": zone_id, "feet": feet, "collected_ids": collected_ids, "state": state}


func _fail(reason: String) -> Dictionary:
	_reject(reason)
	return {}


func _reject(reason: String) -> bool:
	push_error("[SAVE] Can't load '%s': %s. Nothing was changed." % [_display_path(), reason])
	return false


func _get_main() -> Main:
	var main := get_tree().current_scene as Main
	if main == null:
		push_error("[SAVE] Save/load only works while Main is the current scene.")
	return main


func _display_path() -> String:
	return ProjectSettings.globalize_path(save_path)

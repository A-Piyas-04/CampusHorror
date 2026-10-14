extends Node
## TEMPORARY overnight-session check (test-only): runs the real scenes/core/Main.tscn as the current scene and
## drives it like a player would, through input actions and the real SaveService:
## - Main starts in main_gate_exterior at main_gate_entry.
## - CDS door round trip: at the CDS door the prompt targets DoorCdsMainEntry; "interact" enters cds_veranda at
##   inside_cds_entry; DoorCdsExitToField returns to main_gate_exterior at outside_cds_entrance (1380, -200).
## - Walking (move_down / move_up actions) inside the tennis court stops at the fence lines.
## - Save / load in a court: save_game() writes the zone and feet; after moving away load_game() restores them.
## - Night tint and the lantern toggle still work.
## The user's save file (user://save.json) is backed up byte for byte first and restored (or removed again if
## there was none) at the end, and the restore is verified.
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail).

const MAIN_SCENE := "res://scenes/core/Main.tscn"
const SAVE_PATH := "user://save.json"
const CDS_DOOR := "Objects/Buildings/CDSExterior/TableTennis/DoorCdsMainEntry"
const EXPECTED_CHECKS := 10

var _failures := 0
var _checks := 0
var _save_backup: PackedByteArray
var _had_save := false


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[SESSION] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	_had_save = FileAccess.file_exists(SAVE_PATH)
	if _had_save:
		_save_backup = FileAccess.get_file_as_bytes(SAVE_PATH)
	print("[SESSION] user save %s (%d bytes backed up)" % ["present" if _had_save else "absent", _save_backup.size()])
	_start.call_deferred()


func _start() -> void:
	var main := (load(MAIN_SCENE) as PackedScene).instantiate()
	get_tree().root.add_child(main)
	get_tree().current_scene = main
	await _frames(10)
	await _run()
	_restore_save()
	_check(_checks == EXPECTED_CHECKS, "all %d checks ran (%d)" % [EXPECTED_CHECKS, _checks])
	print("[SESSION] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _run() -> void:
	var main := get_tree().current_scene as Main
	_check(main != null and main.get_current_zone_id() == "main_gate_exterior"
		and main.get_player_feet_position().is_equal_approx(Vector2(-1390, 960)),
		"Main is the current scene and starts in main_gate_exterior at main_gate_entry (-1390, 960)")
	if main == null:
		return
	var player := main.get_node("World/Player") as CharacterBody2D

	# CDS door round trip.
	player.call("teleport", Vector2(1440, -200))
	await _frames(6)
	var door := _zone(main).get_node(CDS_DOOR)
	var target: Variant = player.get("_interaction_target")
	_check(target == door.get_node("Interactable"), "at (1440, -200) the interaction target is DoorCdsMainEntry")
	await _press("interact")
	_check(main.get_current_zone_id() == "cds_veranda" and _at_spawn(main, "inside_cds_entry"),
		"interact enters cds_veranda at inside_cds_entry %s" % main.get_player_feet_position())
	var exit_door: Node2D = null
	for d in (_zone(main) as Zone).get_doors():
		if d.destination_zone_id == "main_gate_exterior":
			exit_door = d
	_check(exit_door != null, "cds_veranda has a door back to main_gate_exterior (%s)" % (exit_door.name if exit_door else "none"))
	if exit_door != null:
		player.call("teleport", exit_door.global_position)
		await _frames(6)
		await _press("interact")
	_check(main.get_current_zone_id() == "main_gate_exterior" and main.get_player_feet_position().is_equal_approx(Vector2(1380, -200)),
		"the exit door returns to main_gate_exterior at outside_cds_entrance %s" % main.get_player_feet_position())

	# Court fence collision through real input.
	player.call("teleport", Vector2(550, 1000))
	await _frames(3)
	var south := await _walk(player, "move_down", 60)
	player.call("teleport", Vector2(400, 1000))
	await _frames(3)
	var north := await _walk(player, "move_up", 60)
	_check(absf(south.y - 1143.75) <= 1.5 and absf(north.y - 862.5) <= 1.5,
		"walking inside the tennis court stops at the south fence (y %.2f, want 1143.75) and the north fence (y %.2f, want 862.5)" % [south.y, north.y])

	# Save / load inside a court.
	player.call("teleport", Vector2(550, 1050))
	await _frames(3)
	var saved := bool(SaveService.call("save_game"))
	var data = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH)) if FileAccess.file_exists(SAVE_PATH) else null
	_check(saved and data is Dictionary and data.get("zone_id") == "main_gate_exterior"
		and is_equal_approx(float(data.player_position.x), 550.0) and is_equal_approx(float(data.player_position.y), 1050.0),
		"save_game() in the tennis court writes main_gate_exterior at (550, 1050)")
	player.call("teleport", Vector2(-1390, 960))
	await _frames(3)
	var loaded := bool(SaveService.call("load_game"))
	await _frames(6)
	_check(loaded and main.get_current_zone_id() == "main_gate_exterior" and main.get_player_feet_position().is_equal_approx(Vector2(550, 1050)),
		"load_game() after moving away restores main_gate_exterior at (550, 1050) (now %s)" % main.get_player_feet_position())

	# Night tint and lantern.
	var tint := main.get_node("DayNightTint") as CanvasModulate
	var lantern := player.get_node("Lantern") as PointLight2D
	await _press("debug_toggle_night")
	var night := tint.color
	var lantern_before := lantern.enabled
	await _press("lantern")
	var lantern_toggled := lantern.enabled != lantern_before
	await _press("lantern")
	await _press("debug_toggle_night")
	_check(night == tint.get("night_color") and tint.color == tint.get("day_color") and lantern_toggled and lantern.enabled == lantern_before,
		"debug_toggle_night switches the tint to night and back; the lantern action toggles the lantern and back")


func _zone(main: Node) -> Node:
	return main.get_node("World").get_child(0)


func _at_spawn(main: Main, spawn_id: String) -> bool:
	var marker := (_zone(main) as Zone).find_spawn_marker(spawn_id)
	return marker != null and main.get_player_feet_position().is_equal_approx(marker.global_position)


func _press(action: String) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	await _frames(2)
	ev = InputEventAction.new()
	ev.action = action
	ev.pressed = false
	Input.parse_input_event(ev)
	await _frames(8)


func _walk(player: Node2D, action: String, frames: int) -> Vector2:
	Input.action_press(action)
	for i in frames:
		await get_tree().physics_frame
	Input.action_release(action)
	await _frames(2)
	return player.global_position


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame
	await get_tree().process_frame


func _restore_save() -> void:
	if _had_save:
		var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
		file.store_buffer(_save_backup)
		file.close()
	elif FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))
	var restored := FileAccess.get_file_as_bytes(SAVE_PATH) == _save_backup if _had_save else not FileAccess.file_exists(SAVE_PATH)
	_check(restored, "the user's save file is restored exactly (%s)" % ("same bytes" if _had_save else "removed again, there was none"))

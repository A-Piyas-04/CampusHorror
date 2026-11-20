extends Node
## Phase H4: generic session check (test-only). Runs the REAL scenes/core/Main.tscn and drives it through
## input actions and the real SaveService, for every zone in data/zones/zone_registry.tres:
##   boot        Main starts at its start_zone_id / start_spawn_id; one Player; its camera is current
##   presentation  the Confirmed contract in Docs/PRESENTATION.md is applied (base 1920x1080, canvas_items /
##               expand, fractional scaling, no pixel snap, physics interpolation, camera zoom 2)
##   spawns      every spawn of every zone is enterable and puts the feet exactly on the marker
##   profiles    every shipping zone has a ZoneProfile
##   doors       at every door of every zone the prompt targets that door; "interact" travels (faded, roadmap
##               I5) to the destination zone's spawn; still exactly one Player and no leaked nodes afterwards
##   save/load   F6 saves the zone and feet, F9 restores them after travelling elsewhere; a save naming an
##               unknown zone is refused and changes nothing (one intended ERROR line)
##   debug keys  F2 flips the night tint (DebugTools), the lantern action toggles the lantern
## The user's save (user://save.json) is backed up byte for byte first and restored (or removed again) at
## the end; the restore is verified.
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail).

const MAIN_SCENE := "res://scenes/core/Main.tscn"
const SAVE_PATH := "user://save.json"
const ZOOM := Vector2(2, 2)

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
	await _run(main as Main)
	_restore_save()
	print("[SESSION] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _run(main: Main) -> void:
	_check(main != null, "Main.tscn is the current scene")
	if main == null:
		return
	var player := main.get_node("World/Player") as Player
	var camera := player.get_node("Camera") as Camera2D
	var registry := main.zone_registry

	# --- boot
	_check(main.get_current_zone_id() == main.start_zone_id and _at_spawn(main, main.start_spawn_id),
		"boots into '%s' at spawn '%s' %s" % [main.start_zone_id, main.start_spawn_id, main.get_player_feet_position()])
	_check(_player_count() == 1 and camera.is_current(), "exactly one Player, and its Camera is the current camera")
	_check(main.get_node_or_null("DebugTools") != null, "DebugTools is present in this debug build")

	# --- presentation contract (Docs/PRESENTATION.md)
	var ps := {
		"display/window/size/viewport_width": 1920,
		"display/window/size/viewport_height": 1080,
		"display/window/stretch/mode": "canvas_items",
		"display/window/stretch/aspect": "expand",
		"display/window/stretch/scale_mode": "fractional",
		"rendering/2d/snap/snap_2d_transforms_to_pixel": false,
		"rendering/2d/snap/snap_2d_vertices_to_pixel": false,
		"physics/common/physics_interpolation": true,
		"rendering/renderer/rendering_method": "gl_compatibility",
	}
	var wrong := []
	for key: String in ps:
		if ProjectSettings.get_setting(key) != ps[key]:
			wrong.append("%s = %s (want %s)" % [key, ProjectSettings.get_setting(key), ps[key]])
	_check(wrong.is_empty(), "project settings match the presentation contract (%s)" % (", ".join(wrong) if not wrong.is_empty() else "%d settings" % ps.size()))
	_check(camera.zoom.is_equal_approx(ZOOM), "player camera zoom in the start zone %s (want %s)" % [camera.zoom, ZOOM])
	var missing := []
	for zid in registry.zones.keys():
		var z := (load(registry.get_scene_path(zid)) as PackedScene).instantiate() as Zone
		if z.profile == null:
			missing.append(zid)
		z.free()
	_check(missing.is_empty(), "every shipping zone has a ZoneProfile (missing %s)" % [missing])

	# --- every spawn of every zone
	var bad_spawns := []
	var n_spawns := 0
	for zone_id in registry.get_zone_ids():
		for sid in _spawn_ids(registry, zone_id):
			n_spawns += 1
			main.change_zone(zone_id, sid)
			await _frames(2)
			if main.get_current_zone_id() != zone_id or not _at_spawn(main, sid):
				bad_spawns.append("%s/%s" % [zone_id, sid])
	_check(n_spawns > 0 and bad_spawns.is_empty(), "%d spawns across %d zones put the feet exactly on their marker (bad %s)" % [n_spawns, registry.get_zone_ids().size(), bad_spawns])

	# --- every door of every zone, walked through with the real interact action
	var orphans_before := Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)
	var n_doors := 0
	var bad_doors := []
	for zone_id in registry.get_zone_ids():
		var spawn_ids := _spawn_ids(registry, zone_id)
		if spawn_ids.is_empty():
			continue
		main.change_zone(zone_id, spawn_ids[0])
		await _frames(2)
		var door_paths := []
		for d in (_zone(main) as Zone).get_doors():
			door_paths.append(_zone(main).get_path_to(d))
		for dp in door_paths:
			main.change_zone(zone_id, spawn_ids[0])
			await _frames(2)
			var door := _zone(main).get_node(dp) as Door
			var area := door.get_node("Interactable") as Interactable
			player.teleport(area.global_position + Vector2(0, 6))
			await _frames(4)
			var target: Variant = player.get("_interaction_target")
			if target != area:
				bad_doors.append("%s/%s: prompt targets %s" % [zone_id, dp, target])
				continue
			# Read the destination now: the zone change frees this door.
			var dest_zone := door.destination_zone_id
			var dest_spawn := door.destination_spawn_id
			await _press("interact")
			await _await_travel(main)
			n_doors += 1
			if main.get_current_zone_id() != dest_zone:
				bad_doors.append("%s/%s: expected '%s', in '%s'" % [zone_id, dp, dest_zone, main.get_current_zone_id()])
			elif not _at_spawn(main, dest_spawn):
				bad_doors.append("%s/%s: not at spawn '%s' %s" % [zone_id, dp, dest_spawn, main.get_player_feet_position()])
	await _frames(6)
	var orphans_after := Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)
	_check(n_doors > 0 and bad_doors.is_empty(), "%d doors: the prompt targets each one and interact arrives at its destination spawn (bad %s)" % [n_doors, bad_doors])
	_check(_player_count() == 1 and orphans_after <= orphans_before, "after all transitions: one Player, orphan nodes %d -> %d (no leak)" % [orphans_before, orphans_after])

	# --- save / load through the debug keys (DebugTools -> SaveService)
	var start_zone := main.start_zone_id
	main.change_zone(start_zone, main.start_spawn_id)
	await _frames(2)
	var spot := main.get_player_feet_position() + Vector2(40, -20)
	player.teleport(spot)
	await _frames(2)
	await _press("debug_save")
	var saved: Variant = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH)) if FileAccess.file_exists(SAVE_PATH) else null
	_check(saved is Dictionary and saved.get("zone_id") == start_zone and Vector2(saved.player_position.x, saved.player_position.y).is_equal_approx(spot),
		"F6 writes the zone '%s' and feet %s" % [start_zone, spot])
	var other := ""
	for zid in registry.get_zone_ids():
		if zid != start_zone and not _spawn_ids(registry, zid).is_empty():
			other = zid
			break
	if other != "":
		main.change_zone(other, _spawn_ids(registry, other)[0])
		await _frames(2)
	await _press("debug_load")
	await _await_travel(main)
	_check(main.get_current_zone_id() == start_zone and main.get_player_feet_position().is_equal_approx(spot),
		"after travelling to '%s', F9 restores '%s' at %s (got %s %s)" % [other, start_zone, spot, main.get_current_zone_id(), main.get_player_feet_position()])

	# --- a save naming an unknown zone is refused and changes nothing
	var bad := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	bad.store_string(JSON.stringify({"save_version": 1, "zone_id": "no_such_zone", "player_position": {"x": 0, "y": 0}, "collected_ids": []}))
	bad.close()
	print("[SESSION] (one intended ERROR line follows: the unknown-zone save is refused)")
	var before_zone := main.get_current_zone_id()
	var before_pos := main.get_player_feet_position()
	var loaded := SaveService.load_game()
	_check(not loaded and main.get_current_zone_id() == before_zone and main.get_player_feet_position().is_equal_approx(before_pos),
		"a save naming an unknown zone is refused and changes nothing")

	# --- debug keys
	var tint := main.get_node("DayNightTint") as CanvasModulate
	var lantern := player.get_node("Lantern") as PointLight2D
	var day := tint.color
	await _press("debug_toggle_night")
	var night := tint.color
	await _press("debug_toggle_night")
	var lantern_was := lantern.enabled
	await _press("lantern")
	var lantern_flipped := lantern.enabled != lantern_was
	await _press("lantern")
	_check(night != day and tint.color == day and lantern_flipped and lantern.enabled == lantern_was,
		"F2 flips the night tint and back; the lantern action toggles the lantern and back")


## Waits (at most 5 s) until a faded travel has finished and the player has control again.
func _await_travel(main: Main) -> void:
	var start := Time.get_ticks_msec()
	while main.is_transitioning() and Time.get_ticks_msec() - start < 5000:
		await get_tree().process_frame
	await _frames(2)


func _spawn_ids(registry: ZoneRegistry, zone_id: String) -> Array:
	var ids := []
	var z := (load(registry.get_scene_path(zone_id)) as PackedScene).instantiate() as Zone
	for m in z.get_spawn_markers():
		ids.append(String(m.spawn_id))
	z.free()
	return ids


func _player_count() -> int:
	var n := 0
	for node in get_tree().root.find_children("*", "CharacterBody2D", true, false):
		if node is Player:
			n += 1
	return n


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

extends "res://scenes/tests/feel/feel_check_base.gd"

## Chapter 1 playthrough (test-only): starts a NEW story game (Game start mode "new") on the real Main.tscn and
## plays the whole chapter through the real systems with real input: intro card, the dark canteen, the lantern,
## the notice board, the veranda, the chained gate, the security office (logbook, master key), the guard waking
## and catching the player (blackout -> checkpoint reload), the table-tennis room's dark-only code, the locked hall,
## the breaker keypad, the finale and the hatch, the end card and the return to the title screen.
## Saves go to user://test_chapter1_save.json (removed afterwards); the player's own save is never touched.

const TEST_SAVE := "user://test_chapter1_save.json"


func _start() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	tag = "CHAPTER1"
	SaveService.save_path = TEST_SAVE
	_remove_test_save()
	Game.set("_start_mode", "new")
	await super._start()


func _remove_test_save() -> void:
	for p in [TEST_SAVE, TEST_SAVE + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))


func _run() -> void:
	await _intro()
	await _canteen()
	await _to_field()
	await _gate_and_security()
	await _caught_and_reload()
	await _table_tennis()
	await _hall_and_ending()
	_remove_test_save()
	SaveService.save_path = SaveService.SAVE_PATH


# --- helpers -------------------------------------------------------------------------------------------------

func zone_node(path: String) -> Node2D:
	return main.get_current_zone().get_node_or_null(path) as Node2D


func use(node: Node2D, offset := Vector2(0, 14)) -> void:
	await place(node.global_position + offset)
	await frames(4)
	await press("interact")
	await frames(4)


func card_open() -> bool:
	# After the end card the game changes scene to the title, freeing Main.
	return is_instance_valid(main) and bool(main.get_node("UI/StoryCard").call("is_open"))


func skip_card(max_presses := 14) -> void:
	for i in max_presses:
		if not card_open():
			return
		await press("interact")
		await seconds(0.3)
	var start := Time.get_ticks_msec()
	while card_open() and Time.get_ticks_msec() - start < 8000:
		await get_tree().process_frame


func close_note() -> void:
	var viewer := main.get_node("UI/NoteViewer")
	if bool(viewer.call("is_open")):
		await press("interact")
		await frames(4)


func travel_through(door_path: String) -> void:
	await use(zone_node(door_path))
	await frames(2)
	await await_travel()
	await frames(6)


func lantern() -> Node:
	return player.get_node("Lantern")


func set_lantern(target: int) -> void:
	for i in 4:
		if int(lantern().get("state")) == target:
			return
		await press("lantern")


# --- the chapter ---------------------------------------------------------------------------------------------

func _intro() -> void:
	await frames(4)
	check(card_open(), "a new game opens on the intro card (the world is paused)")
	check(get_tree().paused, "the tree is paused under the intro card")
	await skip_card()
	await seconds(0.5)
	check(not card_open() and not get_tree().paused, "the intro card can be skipped with interact and gives the world back")
	check(main.get_current_zone_id() == "cds_canteen", "the story starts in the CDS canteen (got %s)" % main.get_current_zone_id())
	check(GameState.has_flag("night") and GameState.has_flag("lantern_missing"), "night and no lantern at the start")
	check(GameState.objective == "Find a light.", "first objective: find a light (got '%s')" % GameState.objective)
	var tint := main.get_node("DayNightTint") as CanvasModulate
	check(tint.color.v < 0.25, "the canteen is dark at night (tint %s)" % tint.color)
	check(SaveService.has_save(), "a checkpoint was written at the start")


func _canteen() -> void:
	await press("lantern")
	check(int(lantern().get("state")) == 0, "without a lantern the lantern key does nothing")
	await use(zone_node("Objects/Story/Lantern"), Vector2(0, 16))
	check(GameState.has_flag("got_lantern") and not GameState.has_flag("lantern_missing"), "the hurricane lantern is taken")
	check(int(lantern().get("state")) == 2, "the lantern comes on at full")
	check(GameState.objective.begins_with("Get off campus"), "objective: get off campus (got '%s')" % GameState.objective)
	await use(zone_node("Objects/Story/Notice"), Vector2(0, 16))
	var viewer := main.get_node("UI/NoteViewer")
	check(bool(viewer.call("is_open")) and String(viewer.call("get_text")[0]) == "Notice board",
		"the notice board reads by lantern light")
	await close_note()
	check(GameState.has_read_note("canteen_notice"), "the notice is in the journal")
	await use(zone_node("Objects/Story/Oil"), Vector2(0, 16))
	check(GameState.is_collected("canteen_oil"), "the kerosene is picked up")


func _to_field() -> void:
	await travel_through("Objects/Doors/DoorToVeranda")
	check(main.get_current_zone_id() == "cds_veranda", "the canteen door leads to the veranda")
	await travel_through("Objects/Doors/DoorToField")
	check(main.get_current_zone_id() == "main_gate_exterior", "the arcade gap leads out to the field")
	var guard := zone_node("Objects/Chapter1/Creatures/NightGuard") as NightGuard
	check(guard != null and not guard.active and not guard.visible, "the guard is not on the field yet")
	check(zone_node("BakedNavigation") != null, "the field's navigation was baked on entry")


func _gate_and_security() -> void:
	await use(zone_node("Objects/Chapter1/Story/ExamineGate"), Vector2(0, -18))
	check(GameState.has_flag("gate_seen"), "the chained gate is tried")
	check(GameState.objective.contains("security office"), "objective: the security office (got '%s')" % GameState.objective)
	await travel_through("Objects/Chapter1/Story/DoorSecurity")
	check(main.get_current_zone_id() == "main_gate_security", "the pavilion door leads into the security office")
	await use(zone_node("Objects/Story/Logbook"), Vector2(0, 16))
	await close_note()
	check(GameState.has_flag("logbook_read"), "the logbook is read")
	await use(zone_node("Objects/Story/MasterKey"), Vector2(0, 30))
	check(GameState.has_item("cds_master_key"), "the master key is taken")
	check(GameState.has_flag("guard_awake"), "taking the key wakes the guard")
	check(GameState.objective.contains("table-tennis"), "objective points to the table-tennis room (got '%s')" % GameState.objective)
	await use(zone_node("Objects/Story/Oil"), Vector2(0, 16))
	await seconds(2.0)
	await travel_through("Objects/Doors/DoorToField")
	var guard := zone_node("Objects/Chapter1/Creatures/NightGuard") as NightGuard
	check(guard != null and guard.active and guard.visible, "back outside, the guard is on patrol")
	var p0 := guard.global_position
	await seconds(2.0)
	check(guard.global_position.distance_to(p0) > 20.0, "the guard walks his route (moved %.0f px)" % guard.global_position.distance_to(p0))


func _caught_and_reload() -> void:
	var guard := zone_node("Objects/Chapter1/Creatures/NightGuard") as NightGuard
	await set_lantern(2)
	await place(guard.global_position + Vector2(140, 0))
	var start := Time.get_ticks_msec()
	while not card_open() and Time.get_ticks_msec() - start < 12000:
		await get_tree().process_frame
	check(card_open(), "standing in his light, the guard sees, chases and catches the player (blackout card)")
	await skip_card()
	var t2 := Time.get_ticks_msec()
	while (card_open() or main.is_transitioning()) and Time.get_ticks_msec() - t2 < 10000:
		await get_tree().process_frame
	await seconds(0.5)
	check(main.get_current_zone_id() == "main_gate_exterior" and GameState.has_item("cds_master_key"),
		"after the blackout the last checkpoint is back (field, key kept)")
	check(player.input_enabled, "the player has control again")


func _table_tennis() -> void:
	# Out of the guard's way: straight to the CDS door.
	var guard := zone_node("Objects/Chapter1/Creatures/NightGuard") as NightGuard
	if guard != null:
		guard.active = false
	await travel_through("Objects/Buildings/CDSExterior/TableTennis/DoorCdsMainEntry")
	check(main.get_current_zone_id() == "cds_veranda", "back into the veranda")
	await travel_through("Objects/Doors/DoorTableTennis")
	check(main.get_current_zone_id() == "cds_table_tennis", "into the table-tennis room")
	var mark := zone_node("Objects/Glow/WallCode") as GlowMark
	await set_lantern(2)
	await place(mark.global_position + Vector2(0, 14))
	await seconds(1.0)
	check(mark.visibility < 0.2, "under the lantern the wall writing is invisible (visibility %.2f)" % mark.visibility)
	await press("interact")
	await frames(4)
	check(not GameState.has_flag("code_seen"), "it can't be read in the light")
	await set_lantern(0)
	await seconds(1.2)
	check(mark.visibility > 0.8, "with the lantern off the writing glows (visibility %.2f)" % mark.visibility)
	await press("interact")
	await frames(4)
	await close_note()
	check(GameState.has_flag("code_seen"), "the code is read in the dark")
	check(GameState.objective.contains("2704"), "objective carries the code (got '%s')" % GameState.objective)
	await set_lantern(2)
	await use(zone_node("Objects/Story/HideLocker"), Vector2(0, 18))
	check(player.concealed and not player.get_node("Sprite").visible, "the locker hides the player")
	await seconds(0.5)
	await press("interact")
	await frames(6)
	check(not player.concealed and player.get_node("Sprite").visible, "and lets them out again")


func _hall_and_ending() -> void:
	await travel_through("Objects/Doors/DoorToVeranda")
	await travel_through("Objects/Doors/DoorHall")
	check(main.get_current_zone_id() == "cds_indoor_basketball", "the master key opens the indoor games hall")
	await use(zone_node("Objects/Story/Breaker"), Vector2(0, 16))
	var ui := main.get_node("UI/KeypadUi")
	check(bool(ui.call("is_open")), "the breaker opens the keypad")
	for d in [KEY_2, KEY_7, KEY_0, KEY_4]:
		var ev := InputEventKey.new()
		ev.keycode = d
		ev.pressed = true
		Input.parse_input_event(ev)
		await frames(2)
		ev = InputEventKey.new()
		ev.keycode = d
		ev.pressed = false
		Input.parse_input_event(ev)
		await frames(2)
	await seconds(0.6)
	check(GameState.has_flag("power_on"), "2704 turns the power on")
	await seconds(5.0)
	check(GameState.has_flag("hatch_open") and zone_node("Objects/FloorHatchOpen").visible, "the floor hatch opens")
	var fg := zone_node("Objects/FinaleGuard") as NightGuard
	check(fg != null and fg.active and fg.state == NightGuard.State.CHASE, "the guard comes through the door, chasing")
	if fg != null:
		fg.active = false
	await use(zone_node("Objects/ClimbDown"), Vector2(0, 10))
	check(GameState.has_flag("chapter1_done"), "climbing down the hatch ends the chapter")
	await frames(10)
	check(card_open(), "the end card plays")
	await skip_card(20)
	var start := Time.get_ticks_msec()
	while Time.get_ticks_msec() - start < 8000:
		var cs := get_tree().current_scene
		if cs != null and cs.name == "MainMenu":
			break
		await get_tree().process_frame
	await frames(5)
	check(get_tree().current_scene != null and get_tree().current_scene.name == "MainMenu",
		"after the end card the game returns to the title screen")

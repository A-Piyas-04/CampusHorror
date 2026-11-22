extends "res://scenes/tests/story/story_check_base.gd"

## Chapter 3 playthrough (test-only): starts Chapter 3 fresh (Game start mode "chapter:3") on the real Main.tscn
## and plays it through the real systems with real input: the students on the road, the dead workshop shutter, the
## empty generator key switch, the lab log (the key box), room 304's whiteboard (CSE 4501), the key box, the
## generator (the academic lights come on, the students come for the noise), a student hearing a sprint, and the
## run east to the halls, the end card and Chapter 4 taking over. Saves go to user://test_chapter3_save.json (removed afterwards).

const TEST_SAVE_3 := "user://test_chapter3_save.json"


func _start() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	tag = "CHAPTER3"
	SaveService.save_path = TEST_SAVE_3
	_remove_save_3()
	Game.set("_start_mode", "chapter:3")
	await super._start()


func _remove_save_3() -> void:
	for p in [TEST_SAVE_3, TEST_SAVE_3 + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))


func _run() -> void:
	await _arrival()
	await _shutter_and_generator()
	await _lab_and_classroom()
	await _keybox()
	await _hearing()
	await _generator_and_escape()
	_remove_save_3()
	SaveService.save_path = SaveService.SAVE_PATH


func students() -> Array[NightGuard]:
	var out: Array[NightGuard] = []
	var zone := main.get_current_zone()
	for g in get_tree().get_nodes_in_group("creatures"):
		if g is NightGuard and zone.is_ancestor_of(g):
			out.append(g as NightGuard)
	return out


func calm() -> void:
	for s in students():
		s.active = false


func read(path: String, offset := Vector2(0, 16)) -> void:
	await use(zone_node(path), offset)
	await close_note()


func type_code(code: String) -> void:
	for ch in code:
		for down in [true, false]:
			var ev := InputEventKey.new()
			ev.keycode = KEY_0 + int(ch)
			ev.pressed = down
			Input.parse_input_event(ev)
			await frames(2)
	await seconds(0.6)


func close_popups() -> void:
	var ui := main.get_node("UI/KeypadUi")
	for i in 3:
		if bool(ui.call("is_open")) or card_open():
			await press("interact")
			await frames(6)


# --- the chapter ---------------------------------------------------------------------------------------------

func _arrival() -> void:
	await frames(4)
	check(card_open(), "Chapter 3 opens on its intro card")
	await skip_card()
	await seconds(0.5)
	check(main.get_director() is Chapter3 and int(GameState.get_flag("chapter", 0)) == 3, "the Chapter 3 director runs")
	check(main.get_current_zone_id() == "academic_exterior", "it begins in the academic area (got %s)" % main.get_current_zone_id())
	check(GameState.has_item("north_gate_key") and GameState.has_flag("chapter2_done"), "Chapter 2's key carries over")
	var st := students()
	check(st.size() == 2 and st.all(func(s: NightGuard) -> bool: return s.active and s.visible),
		"two students walk the road (%d)" % st.size())
	check(st.size() > 0 and st[0].light_sensitivity < 0.5 and st[0].hearing > 1.0,
		"students hunt by sound: deaf to the lantern, sharp of hearing")
	check(GameState.objective.contains("workshops"), "objective: the ME workshops (got '%s')" % GameState.objective)
	check(SaveService.has_save(), "the chapter start is saved")
	calm()


func _shutter_and_generator() -> void:
	await use(zone_node("Objects/Chapter3/Story/WorkshopShutter"), Vector2(0, 14))
	await close_popups()
	check(GameState.has_flag("workshop_seen"), "the workshop shutter is dead: it runs on the generator")
	await use(zone_node("Objects/Chapter3/Story/GeneratorPanel"), Vector2(0, 14))
	await close_popups()
	check(not GameState.has_flag("generator_on"), "the generator will not start without its key")
	check(GameState.objective.contains("EEE lab"), "objective: the EEE lab (got '%s')" % GameState.objective)


func _lab_and_classroom() -> void:
	await travel_through("Objects/Doors/DoorAcademic2")
	check(main.get_current_zone_id() == "academic_lab", "into the EEE lab")
	await read("Objects/Story/Log")
	check(GameState.has_flag("lab_log_read"), "the lab log is read: the key box code is the 304 course number")
	await travel_through("Objects/Doors/DoorOut")
	calm()
	await travel_through("Objects/Doors/DoorAcademic1")
	check(main.get_current_zone_id() == "academic_corridor", "into the Academic 1 corridor")
	var st := students()
	check(st.size() == 1 and st[0].active, "a student walks the corridor")
	calm()
	await travel_through("Objects/Doors/DoorStairs")
	check(main.get_current_zone_id() == "academic_corridor", "the stairwell is chained shut")
	await travel_through("Objects/Doors/DoorClassroom")
	check(main.get_current_zone_id() == "academic_classroom", "into room 304")
	await read("Objects/Story/Board", Vector2(0, 20))
	check(GameState.has_flag("board_seen") and GameState.objective.contains("4501"),
		"the whiteboard gives CSE 4501 (objective '%s')" % GameState.objective)
	await travel_through("Objects/Doors/DoorOut")
	calm()
	await travel_through("Objects/Doors/DoorOut")
	check(main.get_current_zone_id() == "academic_exterior", "back out on the road")
	calm()


func _keybox() -> void:
	await travel_through("Objects/Doors/DoorAcademic2")
	await use(zone_node("Objects/Story/KeyBox"), Vector2(0, 16))
	await type_code("1234")
	check(not GameState.has_flag("keybox_open"), "a wrong code does not open the key box")
	var ui := main.get_node("UI/KeypadUi")
	if bool(ui.call("is_open")):
		await press("ui_cancel")
		await frames(4)
	await use(zone_node("Objects/Story/KeyBox"), Vector2(0, 16))
	await type_code("4501")
	check(GameState.has_flag("keybox_open") and GameState.has_item("generator_key"), "4501 opens the key box: the genset key")
	await close_popups()
	await travel_through("Objects/Doors/DoorOut")
	calm()


func _hearing() -> void:
	# A student hears a sprint at a distance it would never see the player from.
	var s := students()[0]
	s.active = true
	s.reset_brain()
	s.global_position = player.global_position + Vector2(200, 0)
	var before := s.awareness
	await hold(["sprint", "move_left"], 40)
	check(s.awareness > before + 0.2, "a student hears the player run (awareness %.2f -> %.2f)" % [before, s.awareness])
	calm()


func _generator_and_escape() -> void:
	await use(zone_node("Objects/Chapter3/Story/GeneratorPanel"), Vector2(0, 14))
	await close_popups()
	check(GameState.has_flag("generator_on") and GameState.has_flag("power_academic"),
		"the genset key starts the generator: the academic circuit is live")
	check(GameState.objective.contains("halls"), "objective: run to the halls (got '%s')" % GameState.objective)
	var edge := zone_node("Objects/Doors/EdgeToHalls") as ZoneEdge
	release_all()
	player.teleport(edge.global_position)
	await frames(6)
	await await_travel()
	check(GameState.has_flag("chapter3_done"), "reaching the halls ends the chapter (zone %s)" % main.get_current_zone_id())
	await frames(10)
	check(card_open(), "the end card plays")
	await skip_card(20)
	var start := Time.get_ticks_msec()
	while Time.get_ticks_msec() - start < 10000:
		if is_instance_valid(main) and main.get_director() is Chapter4:
			break
		await get_tree().process_frame
	check(is_instance_valid(main) and main.get_director() is Chapter4 and main.get_current_zone_id() == "halls_exterior"
		and int(GameState.get_flag("chapter", 0)) == 4,
		"after the end card Chapter 4 begins in the halls (chapter flag 4)")

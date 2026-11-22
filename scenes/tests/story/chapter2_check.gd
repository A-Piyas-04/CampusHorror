extends "res://scenes/tests/story/story_check_base.gd"

## Chapter 2 playthrough (test-only): starts Chapter 2 fresh (Game start mode "chapter:2", the chapter select) on
## the real Main.tscn and plays it through the real systems with real input: the manhole on the lake bank, the
## locked north gate, the Mosque (the muezzin's note), the Admin lobby and the registrar's office (the memo, a
## wrong code on the safe), the Auditorium and the AV hall (the seminar date), the safe (1911: the north gate
## key and the tunnel plan), being caught by the guard (blackout -> checkpoint), the north road to the academic
## area, the end card and Chapter 3 taking over. Saves go to user://test_chapter2_save.json (removed afterwards).

const TEST_SAVE_2 := "user://test_chapter2_save.json"


func _start() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	tag = "CHAPTER2"
	SaveService.save_path = TEST_SAVE_2
	_remove_save_2()
	Game.set("_start_mode", "chapter:2")
	await super._start()


func _remove_save_2() -> void:
	for p in [TEST_SAVE_2, TEST_SAVE_2 + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))


func _run() -> void:
	await _arrival()
	await _mosque()
	await _admin()
	await _av_hall()
	await _safe()
	await _caught()
	await _north_road()
	_remove_save_2()
	SaveService.save_path = SaveService.SAVE_PATH


func guard() -> NightGuard:
	return zone_node("Objects/Chapter2/Creatures/NightGuard") as NightGuard


func read(path: String, offset := Vector2(0, 16)) -> void:
	await use(zone_node(path), offset)
	var viewer := main.get_node("UI/NoteViewer")
	check(bool(viewer.call("is_open")), "%s opens in the note viewer" % path.get_file())
	await close_note()


func type_code(code: String) -> void:
	for ch in code:
		var ev := InputEventKey.new()
		ev.keycode = KEY_0 + int(ch)
		ev.pressed = true
		Input.parse_input_event(ev)
		await frames(2)
		ev = InputEventKey.new()
		ev.keycode = KEY_0 + int(ch)
		ev.pressed = false
		Input.parse_input_event(ev)
		await frames(2)
	await seconds(0.6)


# --- the chapter ---------------------------------------------------------------------------------------------

func _arrival() -> void:
	await frames(4)
	check(card_open(), "Chapter 2 opens on its intro card")
	await skip_card()
	await seconds(0.5)
	check(main.get_director() is Chapter2 and int(GameState.get_flag("chapter", 0)) == 2, "the Chapter 2 director runs")
	check(main.get_current_zone_id() == "central_plaza", "it begins in the Central Plaza (got %s)" % main.get_current_zone_id())
	var spawn := main.get_current_zone().find_spawn_marker("plaza_from_tunnel")
	check(spawn != null and player.global_position.distance_to(spawn.global_position) < 4.0, "on the lake bank by the manhole")
	check(GameState.has_flag("got_lantern") and GameState.has_flag("chapter1_done") and int(lantern().get("state")) == 2,
		"Chapter 1's lantern carries over, lit")
	check(GameState.objective.contains("Mosque"), "objective: shelter in the Mosque (got '%s')" % GameState.objective)
	check(SaveService.has_save(), "the chapter start is saved")
	var g := guard()
	check(g != null and g.active and g.visible, "the Night Guard patrols the plaza")
	check(main.get_current_zone().get_node_or_null("BakedNavigation") != null, "the plaza's navigation is baked for him")
	if g != null:
		g.active = false
	# The north gate is locked without the key (a story lock on the edge).
	var edge := zone_node("Objects/Doors/EdgeToAcademic") as ZoneEdge
	release_all()
	player.teleport(edge.global_position)
	await frames(6)
	await await_travel()
	check(main.get_current_zone_id() == "central_plaza" and not main.is_transitioning(), "the north gate is padlocked without the key")


func _mosque() -> void:
	await travel_through("Objects/Doors/DoorMosque")
	check(main.get_current_zone_id() == "mosque_prayer_hall", "the Mosque door leads into the prayer hall")
	await read("Objects/Story/Imam")
	check(GameState.has_flag("mosque_rest"), "the muezzin's note lets you rest")
	check(GameState.objective.contains("Admin"), "objective: the Admin building (got '%s')" % GameState.objective)
	await travel_through("Objects/Doors/DoorOut")
	check(main.get_current_zone_id() == "central_plaza", "back out to the plaza")
	if guard() != null:
		guard().active = false


func _admin() -> void:
	await travel_through("Objects/Doors/DoorAdmin")
	check(main.get_current_zone_id() == "admin_lobby", "into the Admin lobby")
	await read("Objects/Story/Visitors")
	await travel_through("Objects/Doors/DoorOffice")
	check(main.get_current_zone_id() == "admin_office", "into the registrar's office")
	await read("Objects/Story/Memo")
	check(GameState.has_flag("memo_read"), "the registrar's memo is read")
	check(GameState.objective.contains("AV hall"), "objective: the AV hall (got '%s')" % GameState.objective)
	await use(zone_node("Objects/Story/SafeDial"), Vector2(0, 16))
	var ui := main.get_node("UI/KeypadUi")
	check(bool(ui.call("is_open")), "the safe opens the keypad")
	await type_code("1234")
	check(not GameState.has_flag("safe_open"), "a wrong code does not open the safe")
	if bool(ui.call("is_open")):
		await press("ui_cancel")
		await frames(4)
	check(not bool(ui.call("is_open")), "the keypad closes again")
	await travel_through("Objects/Doors/DoorOut")
	await travel_through("Objects/Doors/DoorOut")
	check(main.get_current_zone_id() == "central_plaza", "back out to the plaza")
	if guard() != null:
		guard().active = false


func _av_hall() -> void:
	await travel_through("Objects/Doors/DoorAuditorium")
	check(main.get_current_zone_id() == "auditorium_hall", "into the Auditorium")
	await travel_through("Objects/Doors/DoorAv")
	check(main.get_current_zone_id() == "av_hall", "through to the AV hall")
	await read("Objects/Story/Projector")
	check(GameState.has_flag("seminar_seen"), "the projector's last slide gives the seminar date")
	check(GameState.objective.contains("1911"), "objective: the code 1911 (got '%s')" % GameState.objective)


func _safe() -> void:
	await travel_through("Objects/Doors/DoorOut")
	await travel_through("Objects/Doors/DoorOut")
	if guard() != null:
		guard().active = false
	await travel_through("Objects/Doors/DoorAdmin")
	await travel_through("Objects/Doors/DoorOffice")
	await use(zone_node("Objects/Story/SafeDial"), Vector2(0, 16))
	await type_code("1911")
	check(GameState.has_flag("safe_open"), "1911 opens the registrar's safe")
	check(GameState.has_item("north_gate_key") and GameState.has_read_note("tunnel_plan"),
		"the north gate key and the tunnel plan are taken")
	check(GameState.objective.contains("north road"), "objective: the north road (got '%s')" % GameState.objective)
	var ui := main.get_node("UI/KeypadUi")
	for i in 3:
		if bool(ui.call("is_open")) or card_open():
			await press("interact")
			await frames(6)
	await travel_through("Objects/Doors/DoorOut")
	await travel_through("Objects/Doors/DoorOut")
	check(main.get_current_zone_id() == "central_plaza", "back in the plaza with the key")
	await seconds(0.3)


func _caught() -> void:
	var g := guard()
	check(g != null, "the guard is in the plaza")
	if g == null:
		return
	g.active = true
	g.global_position = player.global_position + Vector2(40, 0)
	g.reset_brain()
	var start := Time.get_ticks_msec()
	while not card_open() and Time.get_ticks_msec() - start < 8000:
		await get_tree().physics_frame
	check(card_open(), "the guard catches the player (blackout)")
	start = Time.get_ticks_msec()
	while Time.get_ticks_msec() - start < 15000:
		if card_open():
			await press("interact")
			await seconds(0.3)
		elif player.input_enabled:
			break
		else:
			await get_tree().process_frame
	await seconds(0.4)
	check(player.input_enabled and GameState.has_item("north_gate_key"), "back at the last checkpoint, still holding the key")
	if guard() != null:
		guard().active = false


func _north_road() -> void:
	if main.get_current_zone_id() != "central_plaza":
		var z := main.get_current_zone()
		while z != null and z.zone_id != "central_plaza":
			var out := z.find_child("DoorOut", true, false)
			if out == null:
				break
			await travel_through(str(z.get_path_to(out)))
			z = main.get_current_zone()
	var edge := zone_node("Objects/Doors/EdgeToAcademic") as ZoneEdge
	release_all()
	player.teleport(edge.global_position + Vector2(0, 60))
	await frames(3)
	player.teleport(edge.global_position)
	await frames(6)
	await await_travel()
	check(GameState.has_flag("chapter2_done"), "with the key the north road leads on: the chapter ends (got zone %s)" % main.get_current_zone_id())
	await frames(10)
	check(card_open(), "the end card plays")
	await skip_card(20)
	var start := Time.get_ticks_msec()
	while Time.get_ticks_msec() - start < 10000:
		if is_instance_valid(main) and main.get_director() is Chapter3:
			break
		await get_tree().process_frame
	check(is_instance_valid(main) and main.get_director() is Chapter3 and main.get_current_zone_id() == "academic_exterior"
		and int(GameState.get_flag("chapter", 0)) == 3,
		"after the end card Chapter 3 begins in the academic area (chapter flag 3)")
	start = Time.get_ticks_msec()
	while Time.get_ticks_msec() - start < 20000:
		if card_open():
			await press("interact")
			await seconds(0.3)
		elif player.input_enabled:
			break
		else:
			await get_tree().process_frame
	check(player.input_enabled and GameState.has_flag("ch3_started"), "Chapter 3's intro hands control back on the north road")

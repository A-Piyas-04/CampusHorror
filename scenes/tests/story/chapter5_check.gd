extends "res://scenes/tests/story/story_check_base.gd"

## Chapter 5 playthrough (test-only): starts Chapter 5 fresh (Game start mode "chapter:5") on the real Main.tscn
## and plays it through the real systems with real input: the workshop side door, the pit lift with Rafi's key,
## Site 7's B1 corridor and its technicians, the dead B2 lift, the control room (the director's log, the locked
## switchboard), the containment lab (the host report, the staff card), the switchboard, the B2 lift, the colony,
## the end card and the return to the title screen. Saves go to user://test_chapter5_save.json (removed after).

const TEST_SAVE_5 := "user://test_chapter5_save.json"


func _start() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	tag = "CHAPTER5"
	SaveService.save_path = TEST_SAVE_5
	_remove_save_5()
	Game.set("_start_mode", "chapter:5")
	await super._start()


func _remove_save_5() -> void:
	for p in [TEST_SAVE_5, TEST_SAVE_5 + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))


func _run() -> void:
	await _arrival()
	await _down()
	await _control_room()
	await _lab()
	await _switchboard()
	await _colony()
	_remove_save_5()
	SaveService.save_path = SaveService.SAVE_PATH


func hosts() -> Array[NightGuard]:
	var out: Array[NightGuard] = []
	var zone := main.get_current_zone()
	for g in get_tree().get_nodes_in_group("creatures"):
		if g is NightGuard and zone.is_ancestor_of(g):
			out.append(g as NightGuard)
	return out


func calm() -> void:
	for h in hosts():
		h.active = false


func close_popups() -> void:
	for i in 3:
		if card_open():
			await press("interact")
			await frames(6)


func read(path: String, offset := Vector2(0, 16)) -> void:
	await use(zone_node(path), offset)
	await close_note()


# --- the chapter ---------------------------------------------------------------------------------------------

func _arrival() -> void:
	await frames(4)
	check(card_open(), "Chapter 5 opens on its intro card")
	await skip_card()
	await seconds(0.5)
	check(main.get_director() is Chapter5 and int(GameState.get_flag("chapter", 0)) == 5, "the Chapter 5 director runs")
	check(main.get_current_zone_id() == "academic_exterior", "it begins outside the ME workshops (got %s)" % main.get_current_zone_id())
	check(GameState.has_item("lift_key") and GameState.has_flag("generator_on"), "Rafi's key and the running generator carry over")
	check(hosts().all(func(h: NightGuard) -> bool: return not h.active), "Chapter 3's students stay dormant in Chapter 5")
	check(SaveService.has_save(), "the chapter start is saved")


func _down() -> void:
	await travel_through("Objects/Doors/DoorWorkshop")
	check(main.get_current_zone_id() == "me_workshop", "the powered side door opens onto the workshop floor")
	check(GameState.objective.contains("pit lift"), "objective: the pit lift (got '%s')" % GameState.objective)
	await read("Objects/Story/JobCard", Vector2(0, -16))
	await travel_through("Objects/Doors/DoorPitLift")
	check(main.get_current_zone_id() == "facility_corridor", "Rafi's key takes the pit lift down to Site 7, B1")
	check(GameState.has_flag("b1_reached") and GameState.objective.contains("control room"),
		"objective: the control room (got '%s')" % GameState.objective)
	var hs := hosts()
	check(hs.size() == 2 and hs.all(func(h: NightGuard) -> bool: return h.active and int(h.get_meta("chapter", 1)) == 5),
		"two technicians walk the B1 corridor (%d)" % hs.size())
	calm()
	await travel_through("Objects/Doors/DoorB2")
	check(main.get_current_zone_id() == "facility_corridor", "the B2 lift is dead without power")


func _control_room() -> void:
	await travel_through("Objects/Doors/DoorControl")
	check(main.get_current_zone_id() == "facility_control", "into the control room")
	await read("Objects/Story/DirectorLog")
	check(GameState.has_flag("log_read") and GameState.objective.contains("staff card"),
		"the director's log: Organism 7; the switchboard needs a card (objective '%s')" % GameState.objective)
	await use(zone_node("Objects/Story/Switchboard"), Vector2(0, 16))
	await close_popups()
	check(not GameState.has_flag("b2_lift_powered"), "the switchboard stays locked without the staff card")
	await travel_through("Objects/Doors/DoorOut")
	calm()


func _lab() -> void:
	await travel_through("Objects/Doors/DoorLab")
	check(main.get_current_zone_id() == "facility_lab", "into the containment lab")
	check(hosts().size() == 1, "a technician walks the lab")
	calm()
	await read("Objects/Story/HostReport")
	check(GameState.has_flag("host_report_read"), "the host report: the Night Guard was its host")
	await use(zone_node("Objects/Story/Card"), Vector2(0, 14))
	check(GameState.has_item("facility_card") and GameState.has_flag("has_facility_card"), "the dead technician's staff card is taken")
	await travel_through("Objects/Doors/DoorOut")
	calm()


func _switchboard() -> void:
	await travel_through("Objects/Doors/DoorControl")
	await use(zone_node("Objects/Story/Switchboard"), Vector2(0, 16))
	await close_popups()
	check(GameState.has_flag("b2_lift_powered"), "the card opens the switchboard: the feed is routed to the B2 lift")
	check(GameState.objective.contains("B2"), "objective: down to B2 (got '%s')" % GameState.objective)
	await use(zone_node("Objects/Doors/DoorOut"))
	await await_travel()
	var roused := 0
	for h in hosts():
		if h.awareness >= 0.6 or h.state in [NightGuard.State.INVESTIGATE, NightGuard.State.CHASE]:
			roused += 1
	check(roused == hosts().size() and roused > 0, "the breakers rouse every technician on B1 (%d)" % roused)
	calm()
	await frames(6)
	await travel_through("Objects/Doors/DoorB2")
	check(main.get_current_zone_id() == "facility_chamber", "the powered lift goes down to B2")


func _colony() -> void:
	await use(zone_node("Objects/Story/Colony"), Vector2(0, -14))
	await frames(4)
	check(GameState.has_flag("colony_seen") and GameState.has_flag("chapter5_done"), "seeing the colony ends the chapter")
	await frames(10)
	check(card_open(), "the end card plays")
	await skip_card(24)
	var start := Time.get_ticks_msec()
	while Time.get_ticks_msec() - start < 8000:
		var cs := get_tree().current_scene
		if cs != null and cs.name == "MainMenu":
			break
		await get_tree().process_frame
	await frames(5)
	check(get_tree().current_scene != null and get_tree().current_scene.name == "MainMenu",
		"after the last built chapter the game returns to the title screen")

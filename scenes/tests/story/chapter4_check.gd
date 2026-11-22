extends "res://scenes/tests/story/story_check_base.gd"

## Chapter 4 playthrough (test-only): starts Chapter 4 fresh (Game start mode "chapter:4") on the real Main.tscn
## and plays it through the real systems with real input: the sleepwalkers (drawn to light, hard of hearing), only
## this chapter's creatures awake, the barricaded UB back stair, the North Hall radio, room 203's diary, Rafi and
## the lift key on the courtyard path, the back stair, the end card and Chapter 5 taking over.
## Saves go to user://test_chapter4_save.json (removed afterwards).

const TEST_SAVE_4 := "user://test_chapter4_save.json"


func _start() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	tag = "CHAPTER4"
	SaveService.save_path = TEST_SAVE_4
	_remove_save_4()
	Game.set("_start_mode", "chapter:4")
	await super._start()


func _remove_save_4() -> void:
	for p in [TEST_SAVE_4, TEST_SAVE_4 + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))


func _run() -> void:
	await _arrival()
	await _senses()
	await _stair_locked()
	await _radio_and_diary()
	await _rafi()
	await _survivors()
	_remove_save_4()
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


# --- the chapter ---------------------------------------------------------------------------------------------

func _arrival() -> void:
	await frames(4)
	check(card_open(), "Chapter 4 opens on its intro card")
	await skip_card()
	await seconds(0.5)
	check(main.get_director() is Chapter4 and int(GameState.get_flag("chapter", 0)) == 4, "the Chapter 4 director runs")
	check(main.get_current_zone_id() == "halls_exterior", "it begins in the halls (got %s)" % main.get_current_zone_id())
	check(GameState.has_flag("chapter3_done") and GameState.has_item("generator_key"), "earlier chapters' state carries over")
	var hs := hosts()
	check(hs.size() == 3 and hs.all(func(h: NightGuard) -> bool: return h.active and h.visible),
		"three sleepwalkers walk the courtyard (%d)" % hs.size())
	check(hs.size() > 0 and hs[0].light_sensitivity > 1.5 and hs[0].hearing < 1.0, "sleepwalkers follow light, barely hear")
	check(GameState.objective.contains("radio"), "objective: the radio (got '%s')" % GameState.objective)
	check(SaveService.has_save(), "the chapter start is saved")
	calm()


func _senses() -> void:
	# Only this chapter's creatures wake: the academic corridor's student (Chapter 3's) stays dormant now.
	var s := hosts()[0]
	s.active = true
	s.reset_brain()
	# Walking (not running) 160 px away: a sleepwalker barely hears it...
	s.global_position = player.global_position + Vector2(160, 0)
	await set_lantern(0)
	await hold(["move_left"], 30)
	var heard := s.awareness
	s.reset_brain()
	s.global_position = player.global_position + Vector2(160, 0)
	# ...but a full lantern in its line of sight draws it at once.
	await set_lantern(2)
	await frames(30)
	var seen := s.awareness
	check(seen > heard + 0.3, "a full lantern draws a sleepwalker far more than footsteps (light %.2f vs walking %.2f)" % [seen, heard])
	calm()
	s.reset_brain()


func _stair_locked() -> void:
	await use(zone_node("Objects/Chapter4/Story/UbBackStair"), Vector2(0, -14))
	await close_popups()
	check(not GameState.has_flag("ch4_survivors"), "the UB back stair stays barricaded without the key")


func _radio_and_diary() -> void:
	await travel_through("Objects/Doors/DoorNorthHall")
	check(main.get_current_zone_id() == "hall_common", "into the North Hall common room")
	await use(zone_node("Objects/Story/Radio"), Vector2(0, 16))
	await close_note()
	check(GameState.has_flag("radio_heard") and GameState.objective.contains("203"),
		"the radio points at Rafi, room 203 (objective '%s')" % GameState.objective)
	await travel_through("Objects/Doors/DoorOut")
	calm()
	await travel_through("Objects/Doors/DoorSouthHall")
	check(main.get_current_zone_id() == "hall_corridor", "into the South Hall corridor")
	var sl := hosts()
	check(sl.size() == 1 and sl[0].active, "a sleepwalker stands in the corridor")
	calm()
	await travel_through("Objects/Doors/DoorRoom")
	check(main.get_current_zone_id() == "hall_room", "into room 203")
	await use(zone_node("Objects/Story/Diary"), Vector2(0, -16))
	await close_note()
	check(GameState.has_flag("diary_read") and GameState.objective.contains("courtyard"),
		"the diary sends you to the courtyard (objective '%s')" % GameState.objective)
	await travel_through("Objects/Doors/DoorOut")
	calm()
	await travel_through("Objects/Doors/DoorOut")
	check(main.get_current_zone_id() == "halls_exterior", "back out in the courtyard")
	calm()


func _rafi() -> void:
	await use(zone_node("Objects/Chapter4/Story/RafiLook"), Vector2(0, 14))
	await close_popups()
	await use(zone_node("Objects/Chapter4/Story/LiftKey"), Vector2(0, 14))
	check(GameState.has_flag("lift_key_found") and GameState.has_item("lift_key"), "Rafi's lift key is taken")
	check(GameState.objective.contains("back stair"), "objective: the back stair (got '%s')" % GameState.objective)


func _survivors() -> void:
	calm()
	await use(zone_node("Objects/Chapter4/Story/UbBackStair"), Vector2(0, -14))
	check(GameState.has_flag("ch4_survivors") and GameState.has_flag("chapter4_done"),
		"with the key the survivors let you in: the chapter ends")
	await frames(10)
	check(card_open(), "the end card plays")
	await skip_card(24)
	var start := Time.get_ticks_msec()
	while Time.get_ticks_msec() - start < 10000:
		if is_instance_valid(main) and main.get_director() is Chapter5:
			break
		await get_tree().process_frame
	check(is_instance_valid(main) and main.get_director() is Chapter5 and main.get_current_zone_id() == "academic_exterior"
		and int(GameState.get_flag("chapter", 0)) == 5,
		"after the end card Chapter 5 begins at the ME workshops (chapter flag 5)")

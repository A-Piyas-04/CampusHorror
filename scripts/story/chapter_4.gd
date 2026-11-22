class_name Chapter4
extends StoryDirector

## Chapter 4, "The Halls" (D29, D37): the story director. Begins right after Chapter 3 (the player has fled the
## generator's noise into the halls), or fresh from the chapter select.
##
## The beat sheet (flags in GameState, so a save restores the exact point):
## 1. The halls' courtyard at night. A torch blinks on UB Hall's roof. The residents sleepwalk, and every one of
##    them turns towards a light: the lantern is a liability here (they barely hear).
## 2. North Hall common room: the walkie-talkie (common_radio -> radio_heard). Survivors on the UB roof; Rafi of
##    South Hall room 203 has the workshop lift key; knock three short, three long at the back stair.
## 3. South Hall, room 203: Rafi's roommate's diary (dorm_diary -> diary_read): he went into the courtyard with his
##    phone torch.
## 4. The courtyard path: Rafi under a sheet, the lift key by his hand (lift_key_found).
## 5. UB Hall's back stair (ch4_survivors): the survivors let you in. End of the chapter (chapter4_done).
## Every arrival and beat autosaves. Caught / fainted -> blackout -> last save.

const START_ZONE := "halls_exterior"
const START_SPAWN := "halls_from_academic"

const INTRO := [
	"The halls of residence. Two long brick blocks, a courtyard of palms between them, UB Hall closing the far end.",
	"Figures stand on the lawns in their sleeping clothes, swaying, faces turned up to nothing.",
	"On UB Hall's roof a torch blinks. Three short. Three long.",
]
const ENDING := [
	"UB Hall's roof: six students and a lab assistant under a blanket, around one shaded candle.",
	"Rafi's key fits the workshop lift, they say. It goes down to B2, where the power goes.\nIn the morning. Nobody believes there will be a morning.",
	"End of Chapter 4: The Halls",
]


func chapter_number() -> int:
	return 4


## Chapter select / tests: what Chapters 1–3 leave behind, then the same start as from the academic road.
func begin_new() -> void:
	GameState.reset()
	for f in ["night", "got_lantern", "gate_seen", "logbook_read", "guard_awake", "code_seen", "power_on",
			"hatch_open", "chapter1_done", "ch2_surfaced", "mosque_rest", "memo_read", "seminar_seen", "safe_open",
			"chapter2_done", "ch3_started", "workshop_seen", "lab_log_read", "board_seen", "keybox_open",
			"has_generator_key", "generator_on", "power_academic", "chapter3_done"]:
		GameState.set_flag(f)
	for item in ["cds_master_key", "north_gate_key", "generator_key"]:
		GameState.add_item(item)
	GameState.set_fuel(0.6)
	player.get_node("Lantern").call("set_state", 2)
	await begin_from_previous()


func begin_from_previous() -> void:
	GameState.set_flag("chapter", 4)
	player.input_enabled = false
	_card.black()
	if main.get_current_zone_id() != START_ZONE:
		main.change_zone(START_ZONE, START_SPAWN)
	await get_tree().process_frame
	await _card.play(INTRO, 2.6, true)
	get_tree().paused = false
	GameState.set_flag("ch4_started")
	_wire_creatures(main.get_current_zone())
	SaveService.checkpoint()
	await _card.fade_out(2.0)
	composure.enabled = true
	player.input_enabled = true
	_update_objective()
	_hint("ch4_start", "The sleepwalkers turn towards any light. F to dim or put out the lantern; they barely hear.")


# --- Zone setup ------------------------------------------------------------------------------------------------

func _patrol_active() -> bool:
	return GameState.has_flag("ch4_started") and not GameState.has_flag("chapter4_done")


func _busy() -> bool:
	return GameState.has_flag("chapter4_done")


func _restart_point() -> Array:
	return [START_ZONE, START_SPAWN]


func _on_zone_entered(_zone_id: String) -> void:
	var zone := main.get_current_zone()
	if zone == null:
		return
	_wire_creatures(zone)


# --- Beats -----------------------------------------------------------------------------------------------------

func _on_note_read(id: String) -> void:
	match id:
		"common_radio":
			GameState.set_flag("radio_heard")
		"dorm_diary":
			GameState.set_flag("diary_read")


func _on_flag_changed(id: String, value: Variant) -> void:
	if not bool(value):
		return
	match id:
		"radio_heard", "diary_read":
			composure.steady(0.1)
			_update_objective()
		"lift_key_found":
			composure.shock(0.1, 2.5)
			_update_objective()
			_hint("key", "The lift key. UB Hall's back stair is at the south end of the courtyard path.")
			SaveService.checkpoint()
		"ch4_survivors":
			GameState.set_flag("chapter4_done")
		"chapter4_done":
			_chapter_end(ENDING, 5)


func _update_objective() -> void:
	if GameState.has_flag("lift_key_found"):
		GameState.set_objective("Take Rafi's key to UB Hall's back stair. Knock three short, three long.")
	elif GameState.has_flag("diary_read"):
		GameState.set_objective("Rafi went into the courtyard with a torch. Find him. Keep your own light low.")
	elif GameState.has_flag("radio_heard"):
		GameState.set_objective("Rafi has the lift key: South Hall, room 203. Start there.")
	else:
		GameState.set_objective("Someone is signalling from UB Hall's roof. The North Hall common room has a radio.")


# --- Debug -----------------------------------------------------------------------------------------------------

func debug_next_beat() -> String:
	if not GameState.has_flag("radio_heard"):
		GameState.mark_note_read("common_radio", "A walkie-talkie on the TV", "(skipped with the debug key)")
		GameState.set_flag("radio_heard")
		_go("hall_common", _spawn("hall_common", "common_from_outside"))
		return "Beat 2: the radio is heard (common room)"
	if not GameState.has_flag("diary_read"):
		GameState.mark_note_read("dorm_diary", "A diary open on the desk", "(skipped with the debug key)")
		GameState.set_flag("diary_read")
		_go("hall_room", _spawn("hall_room", "room_from_corridor"))
		return "Beat 3: the diary is read (room 203)"
	if not GameState.has_flag("lift_key_found"):
		GameState.add_item("lift_key")
		GameState.mark_collected("rafi_lift_key")
		GameState.set_flag("lift_key_found")
		_go("halls_exterior", Vector2(4170, -1000))
		return "Beat 4: the lift key taken (courtyard)"
	if not GameState.has_flag("chapter4_done"):
		_go("halls_exterior", Vector2(4170, 660))
		return "Beat 5: at UB Hall's back stair (knock to end the chapter)"
	return "Chapter 4 is at its end"

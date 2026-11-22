class_name Chapter3
extends StoryDirector

## Chapter 3, "Lecture Hall" (D29, D36): the story director. Begins right after Chapter 2 (the player has just
## come up the north road into the academic area), or fresh from the chapter select.
##
## The beat sheet (flags in GameState, so a save restores the exact point):
## 1. The academic area at night. The students (sound-hunting hosts) walk the road; sneaking is the answer.
##    The tunnel plan ended at the ME workshops: their roller shutter is dead (workshop_seen): it runs on the
##    academic standby generator by the garage.
## 2. The generator's key switch is empty: the EEE lab in Academic 2 keeps its key (the lab log, lab_logbook).
## 3. The lab key box's code is the course number of the night class in room 304 (Academic 1): the whiteboard
##    reads CSE 4501 (classroom_board). Key box 4501 (keybox_open) -> the genset key (has_generator_key).
## 4. The generator (generator_on) lights the academic wing (power_academic), but its roar draws every student:
##    run east to the halls. Reaching the halls ends the chapter (chapter3_done).
## Every arrival and beat autosaves. Caught / fainted -> blackout -> last save.

const START_ZONE := "academic_exterior"
const START_SPAWN := "academic_from_plaza"
const KEYBOX_CODE := "4501"

const INTRO := [
	"The academic blocks stand in rows along the road, every window black.",
	"Something walks the road between them. Slowly. Head tilted, listening.",
	"The tunnel plan's red line ends at the ME workshops. LIFT - B2.",
]
const ENDING := [
	"Behind you the generator roars on alone, and the academic blocks fill with light, and with the things that came for the noise.",
	"Ahead, the halls of residence. High on UB Hall's roof, a torch blinks: three short, three long.",
	"End of Chapter 3: Lecture Hall",
]


func chapter_number() -> int:
	return 3


## Chapter select / tests: what Chapters 1 and 2 leave behind, then the same start as from the north road.
func begin_new() -> void:
	GameState.reset()
	for f in ["night", "got_lantern", "gate_seen", "logbook_read", "guard_awake", "code_seen", "power_on",
			"hatch_open", "chapter1_done", "ch2_surfaced", "mosque_rest", "memo_read", "seminar_seen", "safe_open",
			"chapter2_done"]:
		GameState.set_flag(f)
	GameState.add_item("cds_master_key")
	GameState.add_item("north_gate_key")
	GameState.set_fuel(0.7)
	player.get_node("Lantern").call("set_state", 2)
	await begin_from_previous()


func begin_from_previous() -> void:
	GameState.set_flag("chapter", 3)
	player.input_enabled = false
	_card.black()
	if main.get_current_zone_id() != START_ZONE:
		main.change_zone(START_ZONE, START_SPAWN)
	await get_tree().process_frame
	await _card.play(INTRO, 2.6, true)
	get_tree().paused = false
	GameState.set_flag("ch3_started")
	_wire_creatures(main.get_current_zone())
	SaveService.checkpoint()
	await _card.fade_out(2.0)
	composure.enabled = true
	player.input_enabled = true
	_update_objective()
	_hint("ch3_start", "The students hunt by sound. Hold Ctrl to sneak; never run near them. Light hardly bothers them.")


# --- Zone setup ------------------------------------------------------------------------------------------------

func _patrol_active() -> bool:
	return GameState.has_flag("ch3_started") and not GameState.has_flag("chapter3_done")


func _busy() -> bool:
	return GameState.has_flag("chapter3_done")


func _restart_point() -> Array:
	return [START_ZONE, START_SPAWN]


func _on_zone_entered(zone_id: String) -> void:
	var zone := main.get_current_zone()
	if zone == null:
		return
	_wire_creatures(zone)
	match zone_id:
		"academic_corridor":
			_hint("corridor", "A student is in the corridor. Sneak past while its back is turned.")
		"academic_exterior":
			if GameState.has_flag("generator_on"):
				_rouse_students()
		"halls_exterior":
			if GameState.has_flag("generator_on") and not GameState.has_flag("chapter3_done"):
				GameState.set_flag("chapter3_done")


# --- Beats -----------------------------------------------------------------------------------------------------

func _on_note_read(id: String) -> void:
	match id:
		"lab_logbook":
			GameState.set_flag("lab_log_read")
		"classroom_board":
			GameState.set_flag("board_seen")


func _on_flag_changed(id: String, value: Variant) -> void:
	if not bool(value):
		return
	match id:
		"workshop_seen", "lab_log_read", "board_seen":
			composure.steady(0.05)
			_update_objective()
		"keybox_open":
			GameState.add_item("generator_key")
			GameState.set_flag("has_generator_key")
			composure.steady(0.1)
			_update_objective()
			_hint("genkey", "The genset key. The generator is in the garage, east along the road.")
			SaveService.checkpoint()
		"generator_on":
			GameState.set_flag("power_academic")
			AudioDirector.play_at(&"power_hum_up", player.global_position, 2.0)
			composure.shock(0.12, 3.0)
			var cam := player.get_node("Camera")
			cam.call("shake", 0.35)
			_rouse_students()
			_update_objective()
			_hint("run", "Every student heard that. Run east to the halls!")
			SaveService.checkpoint()
		"chapter3_done":
			_chapter_end(ENDING, 4)


func _update_objective() -> void:
	if GameState.has_flag("generator_on"):
		GameState.set_objective("They are coming for the noise. Get out east, to the halls.")
	elif GameState.has_flag("has_generator_key"):
		GameState.set_objective("Start the generator in the garage, east along the road. It will be loud.")
	elif GameState.has_flag("lab_log_read") and GameState.has_flag("board_seen"):
		GameState.set_objective("The lab key box code is the night class's course number: CSE %s." % KEYBOX_CODE)
	elif GameState.has_flag("lab_log_read"):
		GameState.set_objective("The key box code is the course number of the night class in room 304, Academic 1.")
	elif GameState.has_flag("workshop_seen"):
		GameState.set_objective("The workshops run on the generator by the garage. Its key: the EEE lab, Academic 2.")
	else:
		GameState.set_objective("Reach the ME workshops at the west end of the road. Sneak: the students listen.")


## The generator roars: every student in the zone comes to the garage.
func _rouse_students() -> void:
	var zone := main.get_current_zone()
	for g in get_tree().get_nodes_in_group("creatures"):
		var host := g as NightGuard
		if host != null and host.active and zone.is_ancestor_of(host):
			host._last_known = Vector2(3030, -3600)
			host.awareness = maxf(host.awareness, 0.9)
			host._set_state(NightGuard.State.INVESTIGATE)


# --- Debug -----------------------------------------------------------------------------------------------------

func debug_next_beat() -> String:
	if not GameState.has_flag("workshop_seen"):
		GameState.set_flag("workshop_seen")
		_go("academic_exterior", Vector2(-850, -4130))
		return "Beat 1: at the dead workshop shutter"
	if not GameState.has_flag("lab_log_read"):
		GameState.mark_note_read("lab_logbook", "Lab logbook", "(skipped with the debug key)")
		GameState.set_flag("lab_log_read")
		_go("academic_lab", _spawn("academic_lab", "lab_from_outside"))
		return "Beat 2: the lab log is read (the key box)"
	if not GameState.has_flag("board_seen"):
		GameState.mark_note_read("classroom_board", "The whiteboard", "CSE 4501")
		GameState.set_flag("board_seen")
		_go("academic_classroom", _spawn("academic_classroom", "classroom_from_corridor"))
		return "Beat 3: the whiteboard is read (4501)"
	if not GameState.has_flag("has_generator_key"):
		GameState.set_flag("keybox_open")
		_go("academic_exterior", Vector2(3030, -3540))
		return "Beat 4: the genset key taken, at the garage"
	if not GameState.has_flag("generator_on"):
		GameState.set_flag("generator_on")
		return "Beat 5: the generator is on (run east)"
	if not GameState.has_flag("chapter3_done"):
		_go("academic_exterior", _spawn("academic_exterior", "academic_from_halls"))
		return "Beat 6: at the halls road (walk through to end the chapter)"
	return "Chapter 3 is at its end"

class_name Chapter2
extends StoryDirector

## Chapter 2, "The Plaza" (D29, D32): the story director. Begins right after Chapter 1's hatch (same session), or
## fresh from the chapter select with what Chapter 1 grants (the lantern, night, the guard awake).
##
## The beat sheet (flags in GameState, so a save restores the exact point):
## 1. The hatch's service tunnel comes up through a manhole on the lake's south bank (ch2_surfaced). The Night
##    Guard has followed: he patrols the island plaza; crows on the lamps scatter and call him.
## 2. The Mosque is the safe room: its great window is lit. The muezzin's note (imam_note -> mosque_rest) steadies
##    the player and points at the Admin building, which keeps the campus plans and keys.
## 3. The registrar's office (Admin): the memo (registrar_memo -> memo_read) says the tunnel plan and the north
##    gate key are in the safe, and the code is the date of the closed faculty seminar (DDMM).
## 4. The AV hall inside the Auditorium: the projector's last slide (av_projector -> seminar_seen) gives the date,
##    19 November: 1911.
## 5. The safe (keypad, safe_open): the north gate key and the tunnel plan (the current runs on, under the ME
##    workshops). The guard hears the safe and comes to the plaza's north side.
## 6. The north road edge opens with the key: reaching the academic area ends the chapter (chapter2_done).
## Every arrival and beat autosaves. Caught / fainted -> blackout -> last save.

const START_ZONE := "central_plaza"
const START_SPAWN := "plaza_from_tunnel"
const SAFE_CODE := "1911"

const INTRO := [
	"The ladder ends in a service tunnel, knee-deep in warm water.\nYou follow it north for a long time.",
	"It comes up through a manhole on the bank of the lake.\nThe Central Plaza. No lights anywhere.",
	"Except one: high in the Mosque, the great window is glowing.",
]
const ENDING := [
	"Beyond the north bridge, the road runs on between the dark academic blocks.",
	"Under your feet the tunnel plan's red line runs the same way:\nnorth, towards the ME workshops.",
	"End of Chapter 2: The Plaza",
]

var _guard_alerted := false


func chapter_number() -> int:
	return 2


## Chapter select / tests: what Chapter 1 leaves behind, then the same start as from the hatch.
func begin_new() -> void:
	GameState.reset()
	for f in ["night", "got_lantern", "gate_seen", "logbook_read", "guard_awake", "code_seen", "power_on",
			"hatch_open", "chapter1_done"]:
		GameState.set_flag(f)
	GameState.add_item("cds_master_key")
	GameState.set_fuel(0.7)
	var lantern := player.get_node("Lantern")
	lantern.call("set_state", 2)
	await begin_from_previous()


func begin_from_previous() -> void:
	GameState.set_flag("chapter", 2)
	player.input_enabled = false
	_card.black()
	main.change_zone(START_ZONE, START_SPAWN)
	await get_tree().process_frame
	await _card.play(INTRO, 2.6, true)
	get_tree().paused = false
	GameState.set_flag("ch2_surfaced")
	_wire_creatures(main.get_current_zone())
	SaveService.checkpoint()
	await _card.fade_out(2.0)
	composure.enabled = true
	player.input_enabled = true
	GameState.set_objective("Find shelter. A light is on in the Mosque.")
	_hint("ch2_start", "The Night Guard came through the tunnel too. Keep to the dark; crows give you away.")


# --- Zone setup ------------------------------------------------------------------------------------------------

func _patrol_active() -> bool:
	return GameState.has_flag("ch2_surfaced") and not GameState.has_flag("chapter2_done")


## After the last beat nothing saves: Continue replays the walk north rather than loading a finished chapter.
func _busy() -> bool:
	return GameState.has_flag("chapter2_done")


func _restart_point() -> Array:
	return [START_ZONE, START_SPAWN]


func _on_zone_entered(zone_id: String) -> void:
	var zone := main.get_current_zone()
	if zone == null:
		return
	_wire_creatures(zone)
	match zone_id:
		"mosque_prayer_hall":
			composure.steady(0.25)
			if not GameState.has_flag("mosque_rest"):
				_hint("mosque", "Nothing follows you in here. Read the note in the Quran stand.")
		"academic_exterior":
			if GameState.has_item("north_gate_key") and not GameState.has_flag("chapter2_done"):
				GameState.set_flag("chapter2_done")
		"central_plaza":
			if _guard_alerted:
				_guard_alerted = false
				_send_guard_to(Vector2(277, -3400))


# --- Beats -----------------------------------------------------------------------------------------------------

func _on_note_read(id: String) -> void:
	match id:
		"imam_note":
			GameState.set_flag("mosque_rest")
		"registrar_memo":
			GameState.set_flag("memo_read")
		"av_projector":
			GameState.set_flag("seminar_seen")


func _on_flag_changed(id: String, value: Variant) -> void:
	if not bool(value):
		return
	match id:
		"mosque_rest":
			composure.steady(0.5)
			GameState.set_fuel(maxf(GameState.lantern_fuel, 0.6))
			SaveService.checkpoint()
			_update_objective()
		"memo_read", "seminar_seen":
			composure.steady(0.1)
			_update_objective()
		"safe_open":
			GameState.add_item("north_gate_key")
			GameState.mark_note_read("tunnel_plan", "Campus master plan, sheet 7",
				"Service tunnels (not for publication), 1984.\n\nA tunnel runs from the CDS plant room under the field to "
				+ "the lake pump house, and on, under the north road, to the ME workshops. There it ends in a square "
				+ "marked only 'LIFT - B2'.\n\nSomeone has traced the whole route in red pen, and written beside the "
				+ "workshops: 'the power goes DOWN here.'")
			composure.shock(0.08, 2.0)
			AudioDirector.play_at(&"metal_bang", player.global_position + Vector2(300, -200), 0.0, 0.9)
			_guard_alerted = true
			_update_objective()
			_hint("key", "The north gate key. The road north crosses the lake beside the Admin building.")
			SaveService.checkpoint()
		"chapter2_done":
			_chapter_end(ENDING, 3)


func _update_objective() -> void:
	if GameState.has_item("north_gate_key"):
		GameState.set_objective("Take the north road across the lake to the academic buildings. The key opens the gate.")
	elif GameState.has_flag("memo_read") and GameState.has_flag("seminar_seen"):
		GameState.set_objective("The registrar's safe: the code is the seminar date, 19 November. %s." % SAFE_CODE)
	elif GameState.has_flag("memo_read"):
		GameState.set_objective("The safe's code is the date of the closed seminar. The AV hall is inside the Auditorium.")
	elif GameState.has_flag("seminar_seen"):
		GameState.set_objective("A seminar on 19 November about the organism. The Admin building keeps the campus plans.")
	elif GameState.has_flag("mosque_rest"):
		GameState.set_objective("Find out where the tunnel goes. The Admin building keeps the campus plans.")
	else:
		GameState.set_objective("Find shelter. A light is on in the Mosque.")


## The guard heard something: he walks over to look (INVESTIGATE at `pos`) if he is in this zone.
func _send_guard_to(pos: Vector2) -> void:
	for g in get_tree().get_nodes_in_group("creatures"):
		var guard := g as NightGuard
		if guard != null and guard.active and main.get_current_zone().is_ancestor_of(guard):
			guard._last_known = pos
			guard.awareness = maxf(guard.awareness, 0.6)
			guard._set_state(NightGuard.State.INVESTIGATE)


# --- Debug -----------------------------------------------------------------------------------------------------

func debug_next_beat() -> String:
	if not GameState.has_flag("mosque_rest"):
		GameState.mark_note_read("imam_note", "A note tucked in a Quran stand", "(skipped with the debug key)")
		GameState.set_flag("mosque_rest")
		_go("mosque_prayer_hall", _spawn("mosque_prayer_hall", "mosque_from_plaza"))
		return "Beat 2: rested in the Mosque"
	if not GameState.has_flag("memo_read"):
		GameState.mark_note_read("registrar_memo", "Memo on the desk", "(skipped with the debug key)")
		GameState.set_flag("memo_read")
		_go("admin_office", _spawn("admin_office", "office_from_lobby"))
		return "Beat 3: the registrar's memo is read"
	if not GameState.has_flag("seminar_seen"):
		GameState.mark_note_read("av_projector", "The projector's last slide", "19 November, closed session")
		GameState.set_flag("seminar_seen")
		_go("av_hall", _spawn("av_hall", "av_from_auditorium"))
		return "Beat 4: the seminar date is seen (1911)"
	if not GameState.has_flag("safe_open"):
		if main.get_current_zone_id() != "admin_office":
			_go("admin_office", _spawn("admin_office", "office_from_lobby"))
			return "Beat 5: in the registrar's office (press again to open the safe)"
		GameState.set_flag("safe_open")
		return "Beat 5: the safe is open, the north gate key taken"
	if not GameState.has_flag("chapter2_done"):
		_go("central_plaza", _spawn("central_plaza", "plaza_from_academic"))
		return "Beat 6: at the north road (walk north through the gate)"
	return "Chapter 2 is at its end"

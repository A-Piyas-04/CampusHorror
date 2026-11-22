class_name Chapter5
extends StoryDirector

## Chapter 5, "Below" (D40): the story director. Begins right after Chapter 4 (before dawn, with Rafi's lift key),
## or fresh from the chapter select.
##
## The beat sheet (flags in GameState, so a save restores the exact point):
## 1. The ME workshops: the side door runs on the generator (on since Chapter 3); the caged pit lift takes Rafi's
##    key (lift_key) down to Site 7, level B1 (b1_reached). Technicians (former staff, light + sound) walk B1.
## 2. The control room: the director's log (director_log -> log_read): Organism 7, found in 1984, kept fed on the
##    campus grid since 1991; tonight it took everything. The feed routing switchboard needs a staff card.
## 3. The containment lab: the host report (the Night Guard was its host) and a dead technician's staff card
##    (has_facility_card).
## 4. The switchboard (b2_lift_powered): the feed goes to the B2 lift; every technician comes to look.
## 5. B2: the turbine hall the colony has grown over (colony_seen). End of the chapter (chapter5_done).
## Every arrival and beat autosaves. Caught / fainted -> blackout -> last save.

const START_ZONE := "academic_exterior"
const START_SPAWN := "outside_workshop"

const INTRO := [
	"4:40 am. You don't wait for the morning.",
	"Rafi's key is cold in your hand. Across the road the generator still roars, and the workshop's side door hums.",
	"Whatever is drinking the campus dry is down there. LIFT - B2.",
]
const ENDING := [
	"Organism 7 has lived under the campus since 1984. Every lamp, every fan, every laptop left charging overnight has been feeding it.",
	"Tonight it took everything. And now the feed runs to the lift you came down in, and the thing in the turbine hall knows the way up.",
	"End of Chapter 5: Below",
	"Chapter 6, \"The Turning\", is not built yet. Thank you for playing.",
]


func chapter_number() -> int:
	return 5


## Chapter select / tests: what Chapters 1–4 leave behind, then the same start as from the UB roof.
func begin_new() -> void:
	GameState.reset()
	for f in ["night", "got_lantern", "gate_seen", "logbook_read", "guard_awake", "code_seen", "power_on",
			"hatch_open", "chapter1_done", "ch2_surfaced", "mosque_rest", "memo_read", "seminar_seen", "safe_open",
			"chapter2_done", "ch3_started", "workshop_seen", "lab_log_read", "board_seen", "keybox_open",
			"has_generator_key", "generator_on", "power_academic", "chapter3_done", "ch4_started", "radio_heard",
			"diary_read", "lift_key_found", "ch4_survivors", "chapter4_done"]:
		GameState.set_flag(f)
	for item in ["cds_master_key", "north_gate_key", "generator_key", "lift_key"]:
		GameState.add_item(item)
	GameState.set_fuel(0.75)
	player.get_node("Lantern").call("set_state", 2)
	await begin_from_previous()


func begin_from_previous() -> void:
	GameState.set_flag("chapter", 5)
	player.input_enabled = false
	_card.black()
	main.change_zone(START_ZONE, START_SPAWN)
	await get_tree().process_frame
	await _card.play(INTRO, 2.6, true)
	get_tree().paused = false
	GameState.set_flag("ch5_started")
	GameState.set_fuel(maxf(GameState.lantern_fuel, 0.75))
	_wire_creatures(main.get_current_zone())
	SaveService.checkpoint()
	await _card.fade_out(2.0)
	composure.enabled = true
	player.input_enabled = true
	_update_objective()


# --- Zone setup ------------------------------------------------------------------------------------------------

func _patrol_active() -> bool:
	return GameState.has_flag("ch5_started") and not GameState.has_flag("chapter5_done")


func _busy() -> bool:
	return GameState.has_flag("chapter5_done")


func _restart_point() -> Array:
	return [START_ZONE, START_SPAWN]


func _on_zone_entered(zone_id: String) -> void:
	var zone := main.get_current_zone()
	if zone == null:
		return
	_wire_creatures(zone)
	match zone_id:
		"me_workshop":
			_update_objective()
		"facility_corridor":
			if not GameState.has_flag("b1_reached"):
				GameState.set_flag("b1_reached")
			_hint("technicians", "The technicians see light and hear footsteps. Lantern low, sneak, use the doors.")
			if GameState.has_flag("b2_lift_powered"):
				# The old feed line at the west end went dead when the power was rerouted: they go to look,
				# and the player has to slip past them east to the B2 lift.
				_send_technicians_to(Vector2(-13.5 * 32.0, -2.2 * 20.576))
		"facility_chamber":
			composure.shock(0.15, 4.0)


# --- Beats -----------------------------------------------------------------------------------------------------

func _on_note_read(id: String) -> void:
	match id:
		"director_log":
			GameState.set_flag("log_read")
		"host_report":
			GameState.set_flag("host_report_read")


func _on_inventory_changed() -> void:
	if GameState.has_item("facility_card") and not GameState.has_flag("has_facility_card"):
		GameState.set_flag("has_facility_card")


func _on_flag_changed(id: String, value: Variant) -> void:
	if not bool(value):
		return
	match id:
		"b1_reached", "log_read", "host_report_read":
			composure.steady(0.05)
			_update_objective()
		"has_facility_card":
			composure.steady(0.1)
			_update_objective()
			SaveService.checkpoint()
		"b2_lift_powered":
			AudioDirector.play_at(&"breaker_clunk", player.global_position, 4.0)
			composure.shock(0.1, 3.0)
			var cam := player.get_node("Camera")
			cam.call("shake", 0.3)
			_update_objective()
			_hint("alarm", "The technicians go to the dead feed line, west. Slip past them, light low, to the B2 lift east.")
			SaveService.checkpoint()
		"colony_seen":
			GameState.set_flag("chapter5_done")
		"chapter5_done":
			_chapter_end(ENDING, 6)


func _update_objective() -> void:
	if GameState.has_flag("b2_lift_powered"):
		GameState.set_objective("The B2 lift has power. East end of the B1 corridor. Go down.")
	elif GameState.has_flag("has_facility_card"):
		GameState.set_objective("Route the power to the B2 lift: the switchboard in the control room.")
	elif GameState.has_flag("log_read"):
		GameState.set_objective("The switchboard needs a staff card. Try the containment lab.")
	elif GameState.has_flag("b1_reached"):
		GameState.set_objective("Site 7. The B2 lift is dead. Find where the power is routed: the control room.")
	elif main.get_current_zone_id() == "me_workshop":
		GameState.set_objective("The caged pit lift in the far corner. Rafi's key.")
	else:
		GameState.set_objective("The ME workshop side door, then the pit lift. Rafi's key.")


## The breakers were heard: every technician in the corridor goes to look (INVESTIGATE at `pos`).
func _send_technicians_to(pos: Vector2) -> void:
	var zone := main.get_current_zone()
	for g in get_tree().get_nodes_in_group("creatures"):
		var host := g as NightGuard
		if host != null and host.active and zone.is_ancestor_of(host):
			host._last_known = pos
			host.awareness = maxf(host.awareness, 0.8)
			host._set_state(NightGuard.State.INVESTIGATE)


# --- Debug -----------------------------------------------------------------------------------------------------

func debug_next_beat() -> String:
	if not GameState.has_flag("b1_reached"):
		_go("facility_corridor", _spawn("facility_corridor", "corridor_from_lift"))
		return "Beat 1: down the pit lift to B1"
	if not GameState.has_flag("log_read"):
		GameState.mark_note_read("director_log", "Director's log, Site 7", "(skipped with the debug key)")
		GameState.set_flag("log_read")
		_go("facility_control", _spawn("facility_control", "control_from_corridor"))
		return "Beat 2: the director's log is read (control room)"
	if not GameState.has_flag("has_facility_card"):
		GameState.add_item("facility_card")
		GameState.mark_collected("tech_card")
		_go("facility_lab", _spawn("facility_lab", "lab_from_corridor"))
		return "Beat 3: the staff card taken (containment lab)"
	if not GameState.has_flag("b2_lift_powered"):
		GameState.set_flag("b2_lift_powered")
		_go("facility_control", _spawn("facility_control", "control_from_corridor"))
		return "Beat 4: the feed routed to the B2 lift"
	if not GameState.has_flag("chapter5_done"):
		_go("facility_chamber", _spawn("facility_chamber", "chamber_from_lift"))
		return "Beat 5: in the B2 turbine hall (look at the colony to end the chapter)"
	return "Chapter 5 is at its end"

extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I transition suite (I5), on the real Main.tscn: a door trip fades out, swaps the zone only while the
## screen is fully black, keeps the player locked, fades in, and hands control back; travels can't overlap;
## return trips find the scene kept in memory; travel_to_position (loading) works the same way.

const CDS_DOOR := "Objects/Buildings/CDSExterior/TableTennis/DoorCdsMainEntry"

var _alpha_at_entry := -1.0
var _started := 0
var _finished := 0
## Feet position at the instant transition_finished fires (input has just been unlocked, no tick has run yet).
var _pos_at_finish := Vector2.INF


func _run() -> void:
	tag = "TRANSITION"
	var layer := main.get_node("UI/TransitionLayer") as TransitionLayer
	main.zone_entered.connect(func(_z): _alpha_at_entry = layer.get_alpha())
	main.transition_started.connect(func(_z): _started += 1)
	main.transition_finished.connect(func(_z):
		_finished += 1
		_pos_at_finish = player.global_position
		Input.action_release("move_left"))
	check(layer.get_alpha() == 0.0 and layer.layer >= 50, "the fade overlay starts clear, above all UI (layer %d)" % layer.layer)

	# --- through the CDS door with the real interact action
	var door := main.get_current_zone().get_node(CDS_DOOR) as Door
	await place((door.get_node("Interactable") as Node2D).global_position + Vector2(0, 6))
	await frames(3)
	var t0 := Time.get_ticks_msec()
	await press("interact")
	check(main.is_transitioning() and not player.input_enabled and _started == 1, "interact at the CDS door starts a travel and locks the player")
	check(not main.travel("main_gate_exterior", "main_gate_entry"), "a second travel while one runs is refused")
	Input.action_press("move_left")
	var before_swap := player.global_position
	var moved_before_swap := 0.0
	var visible_stalls := []
	var last := Time.get_ticks_usec()
	while main.is_transitioning():
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		if layer.get_alpha() < 0.999 and (now - last) > 100000:
			visible_stalls.append("%.0f ms at alpha %.2f" % [(now - last) / 1000.0, layer.get_alpha()])
		last = now
		if main.get_current_zone_id() == "main_gate_exterior":
			moved_before_swap = maxf(moved_before_swap, player.global_position.distance_to(before_swap))
	var elapsed := (Time.get_ticks_msec() - t0) / 1000.0
	Input.action_release("move_left")
	var spawn := main.get_current_zone().find_spawn_marker("inside_cds_entry")
	check(_alpha_at_entry >= 0.999, "the zone swapped while the screen was fully black (alpha %.3f at the swap)" % _alpha_at_entry)
	check(moved_before_swap < 0.01 and spawn != null and _pos_at_finish.is_equal_approx(spawn.global_position),
		"held movement was ignored throughout (moved %.2f px before the swap; still exactly on inside_cds_entry when control returned)" % moved_before_swap)
	check(elapsed >= 0.55 and elapsed <= 1.5 and _finished == 1 and player.input_enabled and layer.get_alpha() == 0.0,
		"door to control in %.2f s (fade 0.3 s out + 0.3 s in); faded back to clear; input restored" % elapsed)
	check(visible_stalls.is_empty(), "no frame over 100 ms while any of the world was visible (headless CPU check; windowed budget in FeelProbe) %s" % [visible_stalls])

	# --- the return trip finds the scene kept in memory
	var back := main.zone_registry.get_scene_path("main_gate_exterior")
	check(ResourceLoader.has_cached(back), "main_gate_exterior's scene is still in memory, so the way back loads instantly")
	var exit_door: Door = main.get_current_zone().get_doors()[0]
	await place((exit_door.get_node("Interactable") as Node2D).global_position + Vector2(0, 6))
	await frames(3)
	_alpha_at_entry = -1.0
	await press("interact")
	await await_travel()
	check(main.get_current_zone_id() == "main_gate_exterior" and _alpha_at_entry >= 0.999 and _finished == 2,
		"back through the veranda exit to main_gate_exterior, swapped while black")

	# --- travel_to_position (used by loading a save) and an unknown zone
	_alpha_at_entry = -1.0
	check(main.travel_to_position("cds_veranda", Vector2(0, 200)), "travel_to_position starts a faded travel")
	await await_travel()
	check(main.get_current_zone_id() == "cds_veranda" and player.global_position.is_equal_approx(Vector2(0, 200)) and _alpha_at_entry >= 0.999,
		"travel_to_position lands exactly at (0, 200) in cds_veranda, swapped while black")
	check(not main.travel("no_such_zone", "x") and not main.is_transitioning(), "an unknown zone is refused before anything fades")
	main.change_zone("main_gate_exterior", "main_gate_entry")
	await frames(2)
	check(main.get_current_zone_id() == "main_gate_exterior" and not main.is_transitioning(), "instant change_zone() still works for tests and debug")

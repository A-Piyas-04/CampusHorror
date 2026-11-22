extends "res://scenes/tests/feel/feel_check_base.gd"

## The developer keys that drive Chapter 1 (DebugTools): F3 jumps to the next beat, F4 switches the Night Guard
## off and on, F7 fills the lantern. They are how the owner tests a late beat without replaying the chapter, so
## they are checked like any other feature. Starts a NEW story game; uses its own save file.

const TEST_SAVE := "user://test_debug_keys_save.json"


func _start() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	tag = "DEBUGKEYS"
	SaveService.save_path = TEST_SAVE
	Game.set("_start_mode", "new")
	await super._start()
	for p in [TEST_SAVE, TEST_SAVE + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))
	SaveService.save_path = SaveService.SAVE_PATH


func _run() -> void:
	var card := main.get_node("UI/StoryCard") as StoryCard
	for i in 14:
		if not card.is_open():
			break
		await press("interact")
		await seconds(0.3)
	while card.is_open():
		await get_tree().process_frame
	await seconds(0.5)
	check(main.get_node_or_null("DebugTools") != null, "DebugTools is present in a debug build")

	await press("debug_next_beat")
	check(GameState.has_flag("got_lantern"), "F3 once: the lantern is granted")
	await _beat()
	check(main.get_current_zone_id() == "main_gate_exterior" and GameState.has_flag("gate_seen"),
		"F3 again: at the Main Gate, gate seen (in %s)" % main.get_current_zone_id())
	await _beat()
	check(GameState.has_item("cds_master_key") and GameState.has_flag("guard_awake"),
		"F3 again: master key taken and the guard awake")
	await _beat()
	check(main.get_current_zone_id() == "cds_table_tennis" and GameState.has_flag("code_seen"),
		"F3 again: in the table-tennis room with the code read (in %s)" % main.get_current_zone_id())
	await _beat()
	check(main.get_current_zone_id() == "cds_indoor_basketball", "F3 again: in the indoor games hall (in %s)"
		% main.get_current_zone_id())
	await _beat()
	check(GameState.has_flag("power_on"), "F3 again: the power is on")
	await seconds(5.0)
	check(GameState.has_flag("hatch_open"), "the finale runs from the jump: the hatch opens")

	var guard: NightGuard = null
	for g in get_tree().get_nodes_in_group("creatures"):
		if String((g as Node).get_meta("role", "")) == "finale":
			guard = g as NightGuard
	check(guard != null and guard.active, "the finale guard is hunting")
	await press("debug_toggle_guard")
	check(guard != null and not guard.active, "F4: the guard ignores you")
	await press("debug_toggle_guard")
	check(main.get_director().debug_guard_off == false, "F4 again: hunting resumes")

	GameState.set_fuel(0.1)
	await press("debug_refill")
	# The lit lantern burns oil every frame, so "full" is a shade under 1.0 by the time this runs.
	check(GameState.lantern_fuel > 0.98, "F7: the lantern is filled (%.4f)" % GameState.lantern_fuel)


func _beat() -> void:
	await press("debug_next_beat")
	await await_travel()
	await seconds(0.4)

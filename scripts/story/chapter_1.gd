class_name Chapter1
extends Node

## Chapter 1, "Lights Out" (decision D18): the story director. Main adds it in story mode (new game / continue).
## It owns the objectives, the scripted beats, checkpoints, and what happens when the player is caught or faints.
##
## The beat sheet (flags in GameState, so a save restores the exact point):
## 1. Wake in the dark CDS canteen (intro card). Find a light: the hurricane lantern on the counter (got_lantern).
## 2. "Get off campus": the Main Gate is chained from the outside (gate_seen).
## 3. The security office beside the gate: the guard's logbook (logbook_read) and the CDS master key (item
##    cds_master_key). Taking the key wakes the Night Guard on the field (guard_awake).
## 4. The breaker in the indoor games hall needs a code. Karim scratched it on the table-tennis room wall in the
##    organism's glow: readable only in the dark (code_seen).
## 5. The hall (master key) -> breaker keypad (power_on): the lights stutter on, the floor hatch opens, the guard
##    comes through the door. The only way is down the hatch (chapter1_done) -> end card -> title.
## Every zone entry and every beat autosaves (SaveService.checkpoint). Caught / fainted -> blackout -> last save.

const START_ZONE := "cds_canteen"
const START_SPAWN := "canteen_wake"
const BREAKER_CODE := "2704"

const INTRO := [
	"Islamic University of Technology, Gazipur.\nThursday night, exam week.",
	"You stayed in the CDS canteen to finish a project due at nine.\nYou must have fallen asleep at the table.",
	"11:04 pm.\nThe power is out across the whole campus.",
]
const ENDING := [
	"The ladder goes down much further than the building is tall.",
	"Somewhere below the campus, something is breathing in the dark.\nIt is waiting for the light.",
	"End of Chapter 1: Lights Out",
]

var main: Main
var player: Player
var composure: Composure
var _card: StoryCard
var _hud: Node
var _blacking := false
var _hints_shown := {}
var _finale_running := false


func setup(p_main: Main) -> void:
	main = p_main
	player = main.get_node("World/Player") as Player
	composure = main.get_node("Composure") as Composure
	_card = main.get_node("UI/StoryCard") as StoryCard
	_hud = main.get_node("UI/Hud")
	main.zone_entered.connect(_on_zone_entered)
	main.transition_finished.connect(_on_transition_finished)
	GameState.flag_changed.connect(_on_flag_changed)
	GameState.inventory_changed.connect(_on_inventory_changed)
	GameState.note_read.connect(_on_note_read)
	composure.fainted.connect(func() -> void: blackout("Everything goes quiet.\nYou come to on the floor, shaking."))
	composure.enabled = true


## New game: intro card, then the player wakes at the table in the dark canteen.
func begin_new() -> void:
	GameState.reset()
	GameState.set_flag("night")
	GameState.set_flag("lantern_missing")
	GameState.set_fuel(0.55)
	player.input_enabled = false
	_card.black()
	main.change_zone(START_ZONE, START_SPAWN)
	await get_tree().process_frame
	await _card.play(INTRO, 2.4, true)
	get_tree().paused = false
	SaveService.checkpoint()
	await _card.fade_out(2.0)
	player.input_enabled = true
	GameState.set_objective("Find a light.")
	_hint("start", "WASD / left stick to move. E to interact. Esc for the journal.")


## Continue: the save is already loaded by Main; just fade in.
func begin_continue() -> void:
	_card.black()
	await get_tree().process_frame
	_on_zone_entered(main.get_current_zone_id())
	await _card.fade_out(1.5)
	if not GameState.objective.is_empty():
		_hud.call("show_objective", GameState.objective)


# --- Zone setup ------------------------------------------------------------------------------------------------

func _on_zone_entered(zone_id: String) -> void:
	var zone := main.get_current_zone()
	if zone == null:
		return
	main.bake_navigation()
	for g in get_tree().get_nodes_in_group("creatures"):
		if not zone.is_ancestor_of(g):
			continue
		var guard := g as NightGuard
		if guard == null:
			continue
		guard.set_player(player)
		if not guard.caught.is_connected(_on_caught):
			guard.caught.connect(_on_caught)
		var role := String(guard.get_meta("role", "patrol"))
		if role == "patrol":
			guard.active = GameState.has_flag("guard_awake") and not GameState.has_flag("chapter1_done")
			guard.visible = guard.active
		elif role == "finale":
			guard.active = false
			guard.visible = false
	match zone_id:
		"main_gate_exterior":
			if not GameState.has_flag("field_seen"):
				GameState.set_flag("field_seen")
				_hint("sneak", "Hold Ctrl to sneak (quiet), Shift to run (loud). Light carries a long way.")
		"cds_table_tennis":
			if GameState.has_item("cds_master_key") and not GameState.has_flag("code_seen"):
				_hint("dark", "Some things only show in the dark. F cycles the lantern: Full, Low, Off.")
		"cds_indoor_basketball":
			if GameState.has_flag("power_on") and not GameState.has_flag("chapter1_done"):
				_start_finale.call_deferred(true)


func _on_transition_finished(_zone_id: String) -> void:
	if not _blacking and not _finale_running:
		SaveService.checkpoint()


# --- Beats -----------------------------------------------------------------------------------------------------

func _on_flag_changed(id: String, value: Variant) -> void:
	if not bool(value):
		return
	match id:
		"got_lantern":
			GameState.set_flag("lantern_missing", false)
			var lantern := player.get_node("Lantern")
			lantern.call("set_state", 2)
			composure.steady(0.2)
			GameState.set_objective("Get off campus. Head to the Main Gate.")
			_hint("lantern", "F cycles the lantern: Full, Low, Off. Full light is seen from far away. Oil runs out.")
		"gate_seen":
			if not GameState.has_item("cds_master_key"):
				GameState.set_objective("The gate is chained from outside. Try the security office beside it.")
		"logbook_read":
			_update_objective()
		"code_seen":
			composure.steady(0.1)
			_update_objective()
		"power_on":
			_start_finale(false)
		"chapter1_done":
			_ending()


func _on_inventory_changed() -> void:
	if GameState.has_item("cds_master_key") and not GameState.has_flag("guard_awake"):
		GameState.set_flag("guard_awake")
		_update_objective()
		await get_tree().create_timer(1.5).timeout
		AudioDirector.play_at(&"guard_shriek", player.global_position + Vector2(-500, -300), -6.0, 0.7)
		composure.shock(0.1, 3.0)
		SaveService.checkpoint()


func _on_note_read(id: String) -> void:
	match id:
		"tt_wall_code":
			GameState.set_flag("code_seen")
		"security_logbook":
			GameState.set_flag("logbook_read")


func _update_objective() -> void:
	if GameState.has_flag("power_on"):
		return
	if GameState.has_item("cds_master_key"):
		if GameState.has_flag("code_seen"):
			GameState.set_objective("Restore the power: the breaker in the CDS indoor games hall. The code is 2704.")
		elif GameState.has_flag("logbook_read"):
			GameState.set_objective("The hall breaker needs a code. Karim hid in the table-tennis room. Look there, in the dark.")
		else:
			GameState.set_objective("Read the guard's logbook on the desk.")
	elif GameState.has_flag("logbook_read"):
		GameState.set_objective("Take the CDS master key from the key cabinet.")


func _hint(key: String, text: String) -> void:
	if _hints_shown.has(key):
		return
	_hints_shown[key] = true
	if _hud != null:
		_hud.call("toast", text)


# --- Finale ----------------------------------------------------------------------------------------------------

func _start_finale(resumed: bool) -> void:
	if _finale_running or main.get_current_zone_id() != "cds_indoor_basketball":
		return
	_finale_running = true
	var zone := main.get_current_zone()
	GameState.set_objective("Get to the hatch!")
	if not resumed:
		AudioDirector.play_at(&"breaker_clunk", player.global_position, 4.0)
		await get_tree().create_timer(0.6).timeout
		AudioDirector.play_ui(&"power_hum_up", -4.0)
		var tint := main.get_node("DayNightTint") as CanvasModulate
		var t := create_tween()
		for i in 5:
			t.tween_property(tint, "color", Color(0.75, 0.74, 0.68), 0.05)
			t.tween_property(tint, "color", Color(0.08, 0.085, 0.11), 0.08 + i * 0.03)
		t.tween_property(tint, "color", Color(0.62, 0.6, 0.55), 0.4)
		await t.finished
		await get_tree().create_timer(0.8).timeout
	if zone.has_method("open_hatch"):
		zone.call("open_hatch")
	AudioDirector.play_at(&"hatch_open", zone.get("hatch_position") if zone.get("hatch_position") != null
		else player.global_position, 6.0)
	composure.shock(0.12, 4.0)
	var cam := player.get_node("Camera")
	cam.call("shake", 0.5)
	SaveService.checkpoint()
	await get_tree().create_timer(1.6).timeout
	AudioDirector.play_at(&"metal_bang", player.global_position + Vector2(-260, 0), 6.0, 0.8)
	for g in get_tree().get_nodes_in_group("creatures"):
		var guard := g as NightGuard
		if guard != null and String(guard.get_meta("role", "")) == "finale" and zone.is_ancestor_of(guard):
			guard.visible = true
			guard.active = true
			guard.set_player(player)
			guard.awareness = 1.2
			guard._last_known = player.global_position
			guard._set_state(NightGuard.State.CHASE)
	_hint("hatch", "Run. Shift.")
	_finale_running = false


func _ending() -> void:
	player.input_enabled = false
	composure.enabled = false
	for g in get_tree().get_nodes_in_group("creatures"):
		(g as Node).set("active", false)
	AudioDirector.set_tension(0.0)
	# No checkpoint here: "Continue" afterwards replays the run to the hatch rather than loading a finished chapter.
	await _card.play(ENDING, 2.8, true)
	await get_tree().create_timer(1.0, true, false, true).timeout
	Game.quit_to_title()


# --- Debug helpers (DebugTools only; never reachable in a release build) ----------------------------------------

## Jumps to the start of the next beat, granting whatever that beat assumes: for testing the chapter without
## replaying it. Returns a line describing what it did.
func debug_next_beat() -> String:
	if not GameState.has_flag("got_lantern"):
		GameState.set_flag("got_lantern")
		GameState.mark_collected("canteen_hurricane_lantern")
		return "Beat 1: lantern granted (canteen)"
	if not GameState.has_flag("gate_seen"):
		GameState.set_flag("gate_seen")
		_go("main_gate_exterior", Vector2(-1390, 1240))
		return "Beat 2: at the chained Main Gate"
	if not GameState.has_item("cds_master_key"):
		GameState.set_flag("logbook_read")
		GameState.mark_note_read("security_logbook", "Security logbook, Main Gate", "(skipped with the debug key)")
		GameState.add_item("cds_master_key")
		GameState.mark_collected("security_master_key")
		_go("main_gate_exterior", Vector2(-1632, 1226))
		return "Beat 3: logbook read, master key taken, the guard is awake"
	if not GameState.has_flag("code_seen"):
		GameState.set_flag("code_seen")
		GameState.mark_note_read("tt_wall_code", "Numbers on the wall", "2 7 0 4")
		_go("cds_table_tennis", _spawn("cds_table_tennis", "tt_from_veranda"))
		return "Beat 4: the code (2704) is read, in the table-tennis room"
	if not GameState.has_flag("power_on"):
		if main.get_current_zone_id() != "cds_indoor_basketball":
			_go("cds_indoor_basketball", _spawn("cds_indoor_basketball", "hall_from_veranda"))
			return "Beat 5: in the indoor games hall (press again for the finale)"
		GameState.set_flag("power_on")
		return "Beat 6: power on, the hatch opens, the guard is coming"
	return "Chapter 1 is at its last beat: climb down the hatch"


## True while the guard is switched off (free exploration).
var debug_guard_off := false


func debug_toggle_guard() -> String:
	debug_guard_off = not debug_guard_off
	for g in get_tree().get_nodes_in_group("creatures"):
		var guard := g as NightGuard
		if guard == null:
			continue
		if debug_guard_off:
			guard.active = false
		elif String(guard.get_meta("role", "patrol")) == "patrol":
			guard.active = GameState.has_flag("guard_awake")
			guard.visible = guard.active
			guard.reset_brain()
	return "The guard ignores you" if debug_guard_off else "The guard is hunting again"


func _spawn(zone_id: String, spawn_id: String) -> Vector2:
	var packed := load(main.zone_registry.get_scene_path(zone_id)) as PackedScene
	var probe := packed.instantiate() as Zone
	var marker := probe.find_spawn_marker(spawn_id)
	var at := marker.position if marker != null else Vector2.ZERO
	probe.free()
	return at


func _go(zone_id: String, feet: Vector2) -> void:
	if main.get_current_zone_id() == zone_id:
		player.teleport(feet)
	else:
		main.travel_to_position(zone_id, feet)


# --- Failure ---------------------------------------------------------------------------------------------------

func _on_caught() -> void:
	blackout("Cold hands. The smell of wet earth.\nThen nothing.")


func blackout(message: String) -> void:
	if _blacking:
		return
	_blacking = true
	player.input_enabled = false
	AudioDirector.play_ui(&"stinger", 0.0)
	await _card.play([message], 1.6, true)
	get_tree().paused = false
	composure.reset(0.75)
	if not SaveService.load_game():
		main.change_zone(START_ZONE, START_SPAWN)
	else:
		await main.transition_finished
	_finale_running = false
	await _card.fade_out(1.2)
	player.input_enabled = true
	_blacking = false

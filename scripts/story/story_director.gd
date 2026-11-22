class_name StoryDirector
extends Node

## Base of the chapter directors (D18, D32). Main adds exactly one in story mode: the chapter the save is in
## (GameState flag `chapter`), or Chapter 1 for a new game. When a chapter ends, its director calls
## `main.start_chapter(n + 1)` and the next chapter begins in the same session (`begin_from_previous`).
## This class owns what every chapter shares: wiring to Main and GameState, hints, creature wiring on zone entry,
## checkpoints on arrival, the blackout (caught / fainted -> back to the last save) and the debug guard switch.
## A chapter overrides the hooks: begin_new / begin_from_previous, _on_zone_entered, _on_flag_changed,
## _on_inventory_changed, _on_note_read, _patrol_active, _restart_point, debug_next_beat.

var main: Main
var player: Player
var composure: Composure
var _card: StoryCard
var _hud: Node
var _blacking := false
var _hints_shown := {}
## True while the guard is switched off (free exploration; F4 in a debug build).
var debug_guard_off := false


## This chapter's number (stored in GameState as `chapter`, so Continue knows which director to start).
func chapter_number() -> int:
	return 0


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


## A fresh start of this chapter (new game for Chapter 1; chapter select / tests for later chapters).
func begin_new() -> void:
	pass


## The previous chapter just ended in this session: carry on from where it left the player.
func begin_from_previous() -> void:
	pass


## Continue: the save is already loaded by Main; just fade in.
func begin_continue() -> void:
	_card.black()
	await get_tree().process_frame
	_on_zone_entered(main.get_current_zone_id())
	await _card.fade_out(1.5)
	if not GameState.objective.is_empty():
		_hud.call("show_objective", GameState.objective)


# --- Hooks -----------------------------------------------------------------------------------------------------

func _on_zone_entered(_zone_id: String) -> void:
	pass


func _on_transition_finished(_zone_id: String) -> void:
	if not _blacking and not _busy():
		SaveService.checkpoint()


## True while a scripted sequence runs (no checkpoint on arrival then).
func _busy() -> bool:
	return false


func _on_flag_changed(_id: String, _value: Variant) -> void:
	pass


func _on_inventory_changed() -> void:
	pass


func _on_note_read(_id: String) -> void:
	pass


## Whether the zone's patrolling creatures hunt right now.
func _patrol_active() -> bool:
	return false


## Where to put the player after a blackout when there is no save to load: [zone_id, spawn_id].
func _restart_point() -> Array:
	return ["main_gate_exterior", "main_gate_entry"]


## Runs after the blackout has reloaded the last save, before the fade-in.
func _after_blackout() -> void:
	pass


# --- Shared helpers --------------------------------------------------------------------------------------------

## Points every creature of the current zone at the player and switches patrols on or off (_patrol_active()).
## Creatures with the `role` meta "finale" stay dormant until their chapter wakes them.
func _wire_creatures(zone: Zone) -> void:
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
			guard.active = _patrol_active() and not debug_guard_off
			guard.visible = guard.active
		elif role == "finale":
			guard.active = false
			guard.visible = false


func _hint(key: String, text: String) -> void:
	if _hints_shown.has(key):
		return
	_hints_shown[key] = true
	if _hud != null:
		_hud.call("toast", text)


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


## Plays an end card, then hands over to the next chapter (or the title screen after the last one).
func _chapter_end(lines: Array, next_chapter: int) -> void:
	player.input_enabled = false
	composure.enabled = false
	for g in get_tree().get_nodes_in_group("creatures"):
		(g as Node).set("active", false)
	AudioDirector.set_tension(0.0)
	await _card.play(lines, 2.8, true)
	await get_tree().create_timer(1.0, true, false, true).timeout
	if next_chapter > 0 and main.has_chapter(next_chapter):
		main.start_chapter.call_deferred(next_chapter)
	else:
		Game.quit_to_title()


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
		var at := _restart_point()
		main.change_zone(at[0], at[1])
	else:
		await main.transition_finished
	_after_blackout()
	await _card.fade_out(1.2)
	player.input_enabled = true
	_blacking = false


# --- Debug (DebugTools only; never reachable in a release build) -----------------------------------------------

## Jumps to the start of the next beat. Returns a line describing what it did.
func debug_next_beat() -> String:
	return "No debug beats in this chapter"


func debug_toggle_guard() -> String:
	debug_guard_off = not debug_guard_off
	for g in get_tree().get_nodes_in_group("creatures"):
		var guard := g as NightGuard
		if guard == null:
			continue
		if debug_guard_off:
			guard.active = false
		elif String(guard.get_meta("role", "patrol")) == "patrol":
			guard.active = _patrol_active()
			guard.visible = guard.active
			guard.reset_brain()
	return "The guard ignores you" if debug_guard_off else "The guard is hunting again"

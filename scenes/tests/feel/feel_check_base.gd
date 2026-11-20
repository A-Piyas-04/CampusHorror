extends Node
## Shared harness for the Phase I feel suites (test-only). Boots the REAL scenes/core/Main.tscn as the current
## scene and drives it like a player: input actions (Input.action_press / parse_input_event), the real
## Player, camera, audio and travel code. A suite extends this script, sets `tag` and implements `_run()`.
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (all pass) / 1.
## Never saves; never touches user://save.json.

const MAIN_SCENE := "res://scenes/core/Main.tscn"
const MOVE_ACTIONS := ["move_up", "move_down", "move_left", "move_right", "sprint", "sneak"]

var tag := "FEEL"
var main: Main
var player: Player
var _failures := 0
var _checks := 0


func _ready() -> void:
	_start.call_deferred()


func _start() -> void:
	main = (load(MAIN_SCENE) as PackedScene).instantiate() as Main
	get_tree().root.add_child(main)
	get_tree().current_scene = main
	player = main.get_node("World/Player") as Player
	await frames(10)
	await _run()
	release_all()
	print("[%s] %s (%d/%d)" % [tag, "PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


## Override in the suite.
func _run() -> void:
	pass


func check(ok: bool, label: String) -> bool:
	_checks += 1
	_failures += 0 if ok else 1
	print("[%s] %s %s" % [tag, "ok  " if ok else "FAIL", label])
	return ok


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame
	await get_tree().process_frame


func seconds(s: float) -> void:
	await frames(int(round(s * Engine.physics_ticks_per_second)))


func release_all() -> void:
	for a in MOVE_ACTIONS:
		Input.action_release(a)


## Holds `actions` (with an optional analog strength) for `n` physics frames, calling `each` every frame.
func hold(actions: Array, n: int, strength := 1.0, each: Callable = Callable()) -> void:
	for a in actions:
		Input.action_press(a, strength)
	for i in n:
		await get_tree().physics_frame
		if each.is_valid():
			each.call(i)
	for a in actions:
		Input.action_release(a)


## A one-shot press of an action that the game reads in _unhandled_input (interact, debug keys).
func press(action: String) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	await frames(2)
	ev = InputEventAction.new()
	ev.action = action
	ev.pressed = false
	Input.parse_input_event(ev)
	await frames(2)


## Teleports the feet, lets physics and the camera settle and the player come to rest.
func place(pos: Vector2) -> void:
	release_all()
	player.teleport(pos)
	await frames(3)


## Waits (at most 5 s) until a faded travel has finished.
func await_travel() -> void:
	var start := Time.get_ticks_msec()
	while main.is_transitioning() and Time.get_ticks_msec() - start < 5000:
		await get_tree().process_frame
	await frames(2)


func approx(a: float, b: float, tol: float) -> bool:
	return absf(a - b) <= tol

extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I windowed feel probe (the H3 remainder; Docs/PRESENTATION.md section 5 budgets). Run it WINDOWED:
## headless has no GPU work and no vsync, so its frame times mean nothing.
##   <godot> --path . res://scenes/tests/feel/FeelProbe.tscn -- --quit-after-checks
## Plays a scripted session on the real Main.tscn (walk, sprint, sneak, turns, two faded door trips) and records
## every frame's real duration and the fade overlay's opacity. A "hitch" is a frame longer than twice the median
## frame while any of the world is visible (overlay below fully black). Stalls behind the black screen are
## allowed (that is what the fade is for) and reported separately.

const FIELD := Vector2(-1000, -200)
const CDS_DOOR := "Objects/Buildings/CDSExterior/TableTennis/DoorCdsMainEntry"

var _samples: Array = []   # [ms, alpha]
var _recording := false
var _last_us := 0


func _process(_delta: float) -> void:
	if not _recording:
		return
	var now := Time.get_ticks_usec()
	if _last_us > 0:
		var layer := main.get_node("UI/TransitionLayer") as TransitionLayer
		_samples.append([(now - _last_us) / 1000.0, layer.get_alpha()])
	_last_us = now


func _run() -> void:
	tag = "FEELPROBE"
	if DisplayServer.get_name() == "headless":
		check(false, "the feel probe must run windowed (no GPU work or vsync headless)")
		return
	await seconds(1.0)                       # let shaders and the first frames settle
	_recording = true
	await place(FIELD)
	await hold(["move_right"], 120)
	await hold(["move_right", "sprint"], 120)
	await hold(["move_down", "sneak"], 60)
	await hold(["move_left", "move_up"], 90)
	await hold(["move_up", "sprint"], 60)
	for trip in 2:
		var door: Door = main.get_current_zone().get_node(CDS_DOOR) if trip == 0 else main.get_current_zone().get_doors()[0]
		await place((door.get_node("Interactable") as Node2D).global_position + Vector2(0, 6))
		await frames(2)
		await press("interact")
		await await_travel()
		await hold(["move_down"], 90)
	_recording = false
	_report()


func _report() -> void:
	var visible := []
	var hidden_max := 0.0
	for s in _samples:
		if s[1] < 0.999:
			visible.append(s[0])
		else:
			hidden_max = maxf(hidden_max, s[0])
	visible.sort()
	var n := visible.size()
	var median: float = visible[n / 2]
	var avg := 0.0
	for v in visible:
		avg += v
	avg /= maxf(n, 1)
	var p99: float = visible[mini(n - 1, int(n * 0.99))]
	var worst: float = visible[n - 1]
	var hitches := visible.filter(func(v): return v > 2.0 * median)
	var hz := DisplayServer.screen_get_refresh_rate()
	print("[FEELPROBE] display %.0f Hz, vsync %s, window %s, renderer %s" % [hz, DisplayServer.window_get_vsync_mode() != DisplayServer.VSYNC_DISABLED,
		DisplayServer.window_get_size(), ProjectSettings.get_setting("rendering/renderer/rendering_method")])
	print("[FEELPROBE] %d visible frames: median %.2f ms, avg %.2f ms, p99 %.2f ms, worst %.2f ms; behind the black fade worst %.2f ms" % [n, median, avg, p99, worst, hidden_max])
	check(n > 300, "recorded %d visible frames of scripted play (walk, sprint, sneak, turns, 2 door trips)" % n)
	check(hitches.is_empty(), "no visible hitch: no frame over 2x the median (%.2f ms) while the world is on screen (hitches %s)" % [2.0 * median, hitches.slice(0, 6)])
	check(worst <= 16.7, "worst visible frame %.2f ms is within the 60 Hz budget (16.7 ms); 144 Hz budget is 6.9 ms" % worst)

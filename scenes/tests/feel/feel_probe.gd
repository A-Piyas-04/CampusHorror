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

var _samples: Array = []   # [ms, alpha, phase]
var _phase := "start"
var _recording := false
var _last_us := 0


func _process(_delta: float) -> void:
	if not _recording:
		return
	var now := Time.get_ticks_usec()
	if _last_us > 0:
		var layer := main.get_node("UI/TransitionLayer") as TransitionLayer
		_samples.append([(now - _last_us) / 1000.0, layer.get_alpha(), _phase])
	_last_us = now


func _run() -> void:
	tag = "FEELPROBE"
	if DisplayServer.get_name() == "headless":
		check(false, "the feel probe must run windowed (no GPU work or vsync headless)")
		return
	await seconds(1.0)                       # let shaders and the first frames settle
	_recording = true
	_phase = "field walk / sprint / sneak"
	await place(FIELD)
	await hold(["move_right"], 120)
	await hold(["move_right", "sprint"], 120)
	await hold(["move_down", "sneak"], 60)
	await hold(["move_left", "move_up"], 90)
	await hold(["move_up", "sprint"], 60)
	# Through the old dead band behind the gate tower: occlusion ghosts attach and detach while walking (I6).
	_phase = "behind the gate tower (ghosts)"
	await place(Vector2(-1500, 1250))
	await hold(["move_right"], 150)
	for trip in 2:
		var door: Door = main.get_current_zone().get_node(CDS_DOOR) if trip == 0 else main.get_current_zone().get_doors()[0]
		_phase = "door %d: prompt appears" % (trip + 1)
		await place((door.get_node("Interactable") as Node2D).global_position + Vector2(0, 6))
		await frames(2)
		_phase = "door %d: travel" % (trip + 1)
		await press("interact")
		await await_travel()
		_phase = "after door %d" % (trip + 1)
		await hold(["move_down"], 90)
	_recording = false
	_report()
	await _teleport_snap()


## Regression (I6 work, 21 Nov 2026): the camera has its own physics-interpolation state; before snap() reset it,
## the first rendered frame after a teleport showed the view halfway between the old and new positions, then it
## crept for ~8 frames. Only visible with real interpolated rendering, so it is checked here, windowed.
func _teleport_snap() -> void:
	var cam := player.get_node("Camera") as Camera2D
	await place(Vector2(-1000, -200))
	await seconds(0.5)
	var dest := Vector2(-500, -300)
	player.teleport(dest)
	var centres := []
	for i in 4:
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		centres.append(cam.get_screen_center_position())
	var worst := 0.0
	for c in centres:
		worst = maxf(worst, (c as Vector2).distance_to(dest))
	check(worst < 0.5, "a teleport shows the new view from the very first rendered frame and stays put (largest offset from the feet over 4 frames: %.2f px)" % worst)


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
	for s in _samples:
		if s[1] < 0.999 and s[0] > 2.0 * median:
			print("[FEELPROBE] hitch %.2f ms during '%s'" % [s[0], s[2]])
	var hz := DisplayServer.screen_get_refresh_rate()
	print("[FEELPROBE] display %.0f Hz, vsync %s, window %s, renderer %s" % [hz, DisplayServer.window_get_vsync_mode() != DisplayServer.VSYNC_DISABLED,
		DisplayServer.window_get_size(), ProjectSettings.get_setting("rendering/renderer/rendering_method")])
	print("[FEELPROBE] %d visible frames: median %.2f ms, avg %.2f ms, p99 %.2f ms, worst %.2f ms; behind the black fade worst %.2f ms" % [n, median, avg, p99, worst, hidden_max])
	check(n > 300, "recorded %d visible frames of scripted play (walk, sprint, sneak, turns, 2 door trips)" % n)
	check(hitches.is_empty(), "no visible hitch: no frame over 2x the median (%.2f ms) while the world is on screen (hitches %s)" % [2.0 * median, hitches.slice(0, 6)])
	check(worst <= 16.7, "worst visible frame %.2f ms is within the 60 Hz budget (16.7 ms); 144 Hz budget is 6.9 ms" % worst)

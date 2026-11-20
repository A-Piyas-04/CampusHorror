extends Node2D

## TEMPORARY (Phase H / decision D3): measures 2D lighting correctness and cost in the real
## `main_gate_exterior` zone, so the Compatibility vs Forward+ choice is made with data.
##
## Run WINDOWED (headless has no GPU work, so frame times are meaningless):
##   <godot> --path . res://scenes/tests/renderer_stress/RendererStressTest.tscn -- --quit-after-checks
##
## Reports:
##   1. CORRECTNESS: luminance at a point covered by STACK_LIGHTS overlapping lights. Compatibility
##      defaults to `rendering/limits/opengl/max_lights_per_object = 8`; if it silently drops the
##      extra lights, this number stays dark while Forward+ saturates.
##   2. COST: frame time over MEASURE_FRAMES with SCATTER_LIGHTS shadow-casting lights in the zone.
## It never writes to the project or the save file.

const ZONE_PATH := "res://scenes/world/MainGateExterior.tscn"

const SCATTER_LIGHTS := 30      ## shadow-casting lights spread over the zone (the cost test)
const STACK_LIGHTS_DEFAULT := 12   ## lights stacked on one spot (the per-object cap test)
## Low enough that 8 lights do NOT saturate, so a per-object cap shows as a luminance difference
## between `--stack=8` and `--stack=12`. At 0.18 both counts clip to the same value and prove nothing.
const STACK_ENERGY := 0.05
const STACK_POINT := Vector2(-200.0, 1340.0)   ## on the south boundary wall run (lit brick, has occluders)
const CAMERA_POINT := Vector2(-200.0, 1100.0)  ## fixed view so both renderers draw the same content

const WARMUP_FRAMES := 90
const MEASURE_FRAMES := 300

var _frames := 0
var _samples: Array[float] = []
var _zone: Node2D
var _done := false
var _stack_count := STACK_LIGHTS_DEFAULT


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--stack="):
			_stack_count = int(a.trim_prefix("--stack="))
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0

	_zone = (load(ZONE_PATH) as PackedScene).instantiate()
	add_child(_zone)

	# Night, so the lights are the only illumination and the cap is visible.
	var tint := CanvasModulate.new()
	tint.color = Color(0.1, 0.11, 0.2)
	add_child(tint)

	var cam := Camera2D.new()
	cam.process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS  # physics interpolation is on
	cam.position = CAMERA_POINT
	cam.zoom = Vector2.ONE
	add_child(cam)
	cam.make_current()

	_add_scatter_lights()
	_add_stack_lights()

	print("[STRESS] renderer=%s  scatter=%d (shadows on)  stacked=%d  max_lights_per_object=%s" % [
		ProjectSettings.get_setting("rendering/renderer/rendering_method"),
		SCATTER_LIGHTS, _stack_count,
		ProjectSettings.get_setting("rendering/limits/opengl/max_lights_per_object", "default(8)"),
	])


func _light_texture(radius_px: float) -> GradientTexture2D:
	var grad := Gradient.new()
	grad.set_color(0, Color(1, 1, 1, 1))
	grad.set_color(1, Color(1, 1, 1, 0))
	var tex := GradientTexture2D.new()
	tex.gradient = grad
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = int(radius_px)
	tex.height = int(radius_px)
	return tex


func _make_light(pos: Vector2, energy: float, shadows: bool, radius_px: float) -> PointLight2D:
	var l := PointLight2D.new()
	l.texture = _light_texture(radius_px)
	l.texture_scale = 2.0
	l.color = Color(1.0, 0.85, 0.6)
	l.energy = energy
	l.position = pos
	l.shadow_enabled = shadows
	if shadows:
		l.shadow_filter = Light2D.SHADOW_FILTER_PCF5
	# Mirror the player lantern: light sprite layers 1+2, shadow only from layer-1 occluders.
	l.range_item_cull_mask = 3
	l.shadow_item_cull_mask = 1
	return l


## 30 shadow-casting lights along the wall / court strip, where the zone has real occluders.
func _add_scatter_lights() -> void:
	for i in SCATTER_LIGHTS:
		var t := float(i) / float(SCATTER_LIGHTS - 1)
		var pos := Vector2(lerpf(-1200.0, 2200.0, t), 1340.0 if i % 2 == 0 else 1050.0)
		add_child(_make_light(pos, 0.9, true, 256.0))


## 12 lights on one point. Low energy each, so only an uncapped renderer reaches full brightness.
func _add_stack_lights() -> void:
	for i in _stack_count:
		var jitter := Vector2(cos(i * 0.7) * 6.0, sin(i * 0.7) * 6.0)
		add_child(_make_light(STACK_POINT + jitter, STACK_ENERGY, false, 192.0))


func _process(delta: float) -> void:
	if _done:
		return
	_frames += 1
	if _frames > WARMUP_FRAMES:
		_samples.append(delta * 1000.0)
	if _frames >= WARMUP_FRAMES + MEASURE_FRAMES:
		_done = true
		_report()


func _report() -> void:
	_samples.sort()
	var n := _samples.size()
	var total := 0.0
	for s in _samples:
		total += s
	var avg := total / float(n)
	var p50 := _samples[n / 2]
	var p99 := _samples[mini(n - 1, int(n * 0.99))]

	print("[STRESS] COST  frames=%d  avg=%.2f ms (%.0f fps)  p50=%.2f ms  p99=%.2f ms  worst=%.2f ms" % [
		n, avg, 1000.0 / avg, p50, p99, _samples[n - 1]])
	print("[STRESS] COST  draw_calls=%d  objects=%d" % [
		Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)])

	# Correctness: sample the lit brick under the stacked lights.
	var img := get_viewport().get_texture().get_image()
	var cam_screen := get_viewport().get_visible_rect().size * 0.5
	var px := cam_screen + (STACK_POINT - CAMERA_POINT)
	var x := clampi(int(px.x), 0, img.get_width() - 1)
	var y := clampi(int(px.y), 0, img.get_height() - 1)
	var patch := 0.0
	var count := 0
	for dy in range(-6, 7):
		for dx in range(-6, 7):
			var sx := clampi(x + dx, 0, img.get_width() - 1)
			var sy := clampi(y + dy, 0, img.get_height() - 1)
			patch += img.get_pixel(sx, sy).get_luminance()
			count += 1
	print("[STRESS] CORRECTNESS  luminance under %d stacked lights = %.4f (sampled %d px at %d,%d)" % [
		_stack_count, patch / float(count), count, x, y])
	print("[STRESS] DONE")

	if "--quit-after-checks" in OS.get_cmdline_user_args():
		get_tree().quit(0)

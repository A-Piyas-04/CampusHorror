extends CanvasLayer

## The minimal HUD (group "hud"). Nothing is on screen by default (Docs/GAME_DESIGN.md: "no HUD by default"):
## - Objective: top-left, appears for a few seconds when the objective changes (always readable in the journal).
## - Toasts: one quiet line at the bottom ("Progress saved", "Picked up: Master key").
## - Lantern gauge: a small drawn lantern and fuel bar, bottom-left, shown while the lantern is on and for a moment
##   after the fuel changes; it pulses when fuel is low (decision D20).

const OBJECTIVE_SECONDS := 6.0
const TOAST_SECONDS := 2.4

var _objective_box: VBoxContainer
var _objective: Label
var _toast: Label
var _gauge: LanternGauge
var _obj_tween: Tween
var _toast_tween: Tween
var _gauge_hold := 0.0


func _ready() -> void:
	layer = 20
	add_to_group("hud")
	_objective_box = VBoxContainer.new()
	_objective_box.position = Vector2(48, 40)
	_objective_box.add_theme_constant_override("separation", 2)
	_objective_box.modulate.a = 0.0
	add_child(_objective_box)
	_objective_box.add_child(UIStyle.label("OBJECTIVE", 13, UIStyle.ACCENT))
	_objective = UIStyle.label("", 24, UIStyle.TEXT, true)
	_objective.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.7))
	_objective.add_theme_constant_override("outline_size", 4)
	_objective_box.add_child(_objective)
	_toast = UIStyle.label("", 18, UIStyle.TEXT)
	_toast.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.position = Vector2(-300, -110)
	_toast.size = Vector2(600, 30)
	_toast.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.75))
	_toast.add_theme_constant_override("outline_size", 4)
	_toast.modulate.a = 0.0
	add_child(_toast)
	_gauge = LanternGauge.new()
	_gauge.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_gauge.position = Vector2(44, -100)
	_gauge.modulate.a = 0.0
	add_child(_gauge)
	GameState.objective_changed.connect(show_objective)
	GameState.fuel_changed.connect(func(_f): _gauge_hold = 2.5)
	SaveService.saved.connect(func(auto: bool): toast("Progress saved" if auto else "Game saved"))


func show_objective(text: String) -> void:
	if _obj_tween != null:
		_obj_tween.kill()
	if text.is_empty():
		_objective_box.modulate.a = 0.0
		return
	_objective.text = text
	_obj_tween = create_tween()
	_obj_tween.tween_property(_objective_box, "modulate:a", 1.0, 0.5)
	_obj_tween.tween_interval(OBJECTIVE_SECONDS)
	_obj_tween.tween_property(_objective_box, "modulate:a", 0.0, 1.2)


func toast(text: String) -> void:
	if _toast_tween != null:
		_toast_tween.kill()
	_toast.text = text
	_toast_tween = create_tween()
	_toast_tween.tween_property(_toast, "modulate:a", 1.0, 0.2)
	_toast_tween.tween_interval(TOAST_SECONDS)
	_toast_tween.tween_property(_toast, "modulate:a", 0.0, 0.6)


func get_objective_text() -> String:
	return _objective.text if _objective_box.modulate.a > 0.0 else ""


func get_toast_text() -> String:
	return _toast.text if _toast.modulate.a > 0.0 else ""


func _process(delta: float) -> void:
	var lantern := get_tree().get_first_node_in_group("player_lantern")
	var on := lantern != null and bool(lantern.get("is_lit"))
	_gauge_hold = maxf(_gauge_hold - delta, 0.0)
	var want := 1.0 if (on or _gauge_hold > 0.0) and Game.story_active else 0.0   # Explore mode: no fuel to show
	_gauge.modulate.a = move_toward(_gauge.modulate.a, want, delta * 3.0)
	_gauge.fuel = GameState.lantern_fuel
	_gauge.lit = on


## Small vector lantern with a fuel bar.
class LanternGauge extends Control:
	var fuel := 1.0:
		set(v):
			fuel = v
			queue_redraw()
	var lit := false
	var _t := 0.0

	func _ready() -> void:
		custom_minimum_size = Vector2(130, 56)
		size = custom_minimum_size
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _process(delta: float) -> void:
		_t += delta
		if fuel < 0.2:
			queue_redraw()

	func _draw() -> void:
		var frame := Color(0.85, 0.82, 0.74, 0.9)
		var glow := Color(1.0, 0.78, 0.42, 0.95 if lit else 0.25)
		if fuel < 0.2 and lit:
			glow.a *= 0.55 + 0.45 * sin(_t * 9.0)
		# lantern: handle, cap, glass, base
		draw_arc(Vector2(20, 12), 9.0, PI, TAU, 16, frame, 2.0, true)
		draw_rect(Rect2(10, 14, 20, 5), frame)
		draw_rect(Rect2(12, 19, 16, 22), glow)
		draw_rect(Rect2(12, 19, 16, 22), frame, false, 1.5)
		draw_rect(Rect2(9, 41, 22, 5), frame)
		# fuel bar
		var bar := Rect2(44, 26, 80, 6)
		draw_rect(bar, Color(0, 0, 0, 0.55))
		var col := UIStyle.ACCENT if fuel >= 0.2 else Color(0.95, 0.4, 0.3)
		draw_rect(Rect2(bar.position, Vector2(bar.size.x * fuel, bar.size.y)), col)
		draw_rect(bar, frame, false, 1.0)

class_name Composure
extends CanvasLayer

## Composure (Docs/GAME_DESIGN.md section 4, decision D7): never a bar on screen; it shows in the world.
## - Drains in darkness (slowly), near a host (with its threat), and at scripted frights (`shock()`).
## - Recovers in light, while hidden and unseen, and with progress (`steady()`).
## - Expressed as: a vignette that closes in, colour draining out, film grain, a pulse with the heartbeat (this
##   layer's shader); heartbeat, breathing and a low drone (AudioDirector tension); the camera tightening
##   (PlayerCamera.tension).
## - At zero: `fainted` (the chapter director blacks out and returns the player to the last checkpoint).
## Only active while `enabled` (story mode); tests and the sandbox start leave it off.

signal fainted

const DARK_DRAIN := 1.0 / 240.0      # four minutes of total darkness from calm to nothing
const THREAT_DRAIN := 0.075          # per second at threat 1
const LIGHT_RECOVER := 1.0 / 70.0
const HIDDEN_RECOVER := 1.0 / 90.0

var enabled := false
var value := 1.0
var threat := 0.0
## Seconds of fright left from the last shock (adds to the tension).
var _shock := 0.0
var _rect: ColorRect
var _mat: ShaderMaterial
var _tension := 0.0
var _beat_t := 0.0
var _fainting := false


func _ready() -> void:
	layer = 15
	add_to_group("composure")
	_rect = ColorRect.new()
	_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_mat = ShaderMaterial.new()
	_mat.shader = load("res://assets/shaders/composure.gdshader")
	_rect.material = _mat
	add_child(_rect)
	_rect.visible = false


func reset(to: float = 1.0) -> void:
	value = to
	threat = 0.0
	_shock = 0.0
	_fainting = false


## A sudden fright: drops composure and spikes the tension for a few seconds.
func shock(amount: float = 0.15, seconds: float = 3.0) -> void:
	if not enabled:
		return
	value = clampf(value - amount, 0.0, 1.0)
	_shock = maxf(_shock, seconds)
	var cam := _camera()
	if cam != null:
		cam.call("shake", 0.35)


## Progress, a safe moment: composure comes back a little.
func steady(amount: float = 0.2) -> void:
	value = clampf(value + amount, 0.0, 1.0)


func get_tension() -> float:
	return _tension


func _camera() -> Node:
	var p := get_tree().get_first_node_in_group("player") as Node
	return p.get_node_or_null("Camera") if p != null else null


func _process(delta: float) -> void:
	var player := get_tree().get_first_node_in_group("player") as Player
	if not enabled or player == null or get_tree().paused:
		_rect.visible = enabled and _tension > 0.01
		if not enabled:
			_tension = move_toward(_tension, 0.0, delta)
			AudioDirector.set_tension(0.0)
		return
	# Threat: the strongest from any host (group "threats", method threat_to(position) -> 0..1).
	threat = 0.0
	for t in get_tree().get_nodes_in_group("threats"):
		if t.has_method("threat_to"):
			threat = maxf(threat, float(t.call("threat_to", player.global_position)))
	var lit := LightQuery.light_level(get_tree(), player.global_position)
	var main := get_tree().get_first_node_in_group("main") as Main
	var transitioning := main != null and main.is_transitioning()
	if not transitioning:
		if threat > 0.05:
			value -= THREAT_DRAIN * threat * delta
		elif player.concealed:
			value += HIDDEN_RECOVER * delta
		elif lit > 0.15:
			value += LIGHT_RECOVER * delta
		else:
			value -= DARK_DRAIN * delta
	value = clampf(value, 0.0, 1.0)
	_shock = maxf(_shock - delta, 0.0)
	var want := maxf(1.0 - value, threat)
	want = maxf(want, minf(_shock / 3.0, 1.0) * 0.8)
	_tension = move_toward(_tension, want, delta * (1.2 if want > _tension else 0.35))
	AudioDirector.set_tension(_tension)
	var cam := player.get_node_or_null("Camera")
	if cam != null:
		cam.set("tension", _tension)
	_beat_t += delta * (0.9 + _tension * 1.4)
	_rect.visible = _tension > 0.01
	_mat.set_shader_parameter("tension", _tension)
	_mat.set_shader_parameter("desat", clampf((1.0 - value) * 0.8, 0.0, 0.8))
	_mat.set_shader_parameter("beat", pow(maxf(sin(_beat_t * TAU), 0.0), 8.0))
	if value <= 0.0 and not _fainting:
		_fainting = true
		fainted.emit()

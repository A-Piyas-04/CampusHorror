extends PointLight2D

## The player's lantern (roadmap J2; Docs/GAME_DESIGN.md section 3: light reveals, hides and attracts).
## - `lantern` (F) cycles Full -> Low -> Off -> Full. Full: wide and bright, burns oil fast (about 6 min from
##   full). Low: short and dim, about 17 min. Off: dark, and the only way to see the organism's glow.
## - Oil lives in GameState.lantern_fuel (saved). Below 15 % the flame gutters; at 0 it goes out.
## - Gameplay light: `illuminates()` / `light_level_at()` (LightQuery). Creatures read `visibility()`: how far away
##   the lantern can be seen.
## - Changes ease over 0.15 s; the flame always breathes a little, so the light never looks electric.

signal state_changed(state: int)

enum State { OFF, LOW, FULL }

const FULL_SCALE := 2.2
const LOW_SCALE := 1.15
const FULL_ENERGY := 1.15
const LOW_ENERGY := 0.75
## Fuel used per second.
const BURN := {State.LOW: 1.0 / 1000.0, State.FULL: 1.0 / 360.0}

@export var start_state: State = State.FULL
## Off in daylight scenes and tests: fuel only burns while this is true.
@export var burns_fuel: bool = false

var state: State = State.FULL
var is_lit: bool:
	get: return state != State.OFF
var _scale_target := FULL_SCALE
var _energy_target := FULL_ENERGY
var _t := 0.0


func _ready() -> void:
	# carried at the hip: lifted off the ground so it rakes across normal-mapped ground (Map v2, D46)
	if height <= 0.0:
		height = 55.0
	add_to_group("player_lantern")
	add_to_group("gameplay_lights")
	_set_state(start_state, true)
	GameState.flag_changed.connect(func(id: String, v: Variant) -> void:
		if id == "lantern_missing" and bool(v):
			_set_state(State.OFF, true))


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed("lantern"):
		return
	var player := get_parent() as Player
	if player != null and not player.input_enabled:
		return
	if GameState.has_flag("lantern_missing"):
		var h := get_tree().get_first_node_in_group("hud")
		if h != null:
			h.call("toast", "You have no light.")
		get_viewport().set_input_as_handled()
		return
	match state:
		State.OFF:
			if GameState.lantern_fuel <= 0.0:
				var hud := get_tree().get_first_node_in_group("hud")
				if hud != null:
					hud.call("toast", "The lantern is out of oil.")
			else:
				_set_state(State.FULL)
		State.FULL:
			_set_state(State.LOW)
		State.LOW:
			_set_state(State.OFF)
	AudioDirector.play_at(&"lantern_off" if state == State.OFF else &"lantern_on", global_position, -6.0)
	print("[LIGHTING] Lantern %s." % ["off", "low", "full"][state])
	get_viewport().set_input_as_handled()


func set_state(s: State) -> void:
	_set_state(s)


func _set_state(s: State, instant: bool = false) -> void:
	state = s
	_scale_target = FULL_SCALE if s == State.FULL else LOW_SCALE
	_energy_target = FULL_ENERGY if s == State.FULL else (LOW_ENERGY if s == State.LOW else 0.0)
	if s != State.OFF:
		enabled = true
	if instant:
		texture_scale = _scale_target
		energy = _energy_target
		enabled = s != State.OFF
	state_changed.emit(s)


func _process(delta: float) -> void:
	_t += delta
	if is_lit and burns_fuel:
		GameState.set_fuel(GameState.lantern_fuel - BURN[state] * delta)
		if GameState.lantern_fuel <= 0.0:
			_set_state(State.OFF)
	var k := 1.0 - exp(-12.0 * delta)
	texture_scale = lerpf(texture_scale, _scale_target, k)
	var flicker := 1.0 + 0.025 * sin(_t * 13.0) + 0.02 * sin(_t * 7.3 + 1.7)
	if is_lit and GameState.lantern_fuel < 0.15:
		flicker *= 0.55 + 0.45 * absf(sin(_t * 23.0) * sin(_t * 3.1))
	energy = lerpf(energy, _energy_target * flicker * _ambient_scale(), k)
	if not is_lit and energy < 0.02:
		enabled = false


## Explore mode (D45): a flame is lost in daylight, so its strength follows the time of day's darkness.
func _ambient_scale() -> float:
	if Game.story_active:
		return 1.0
	var tint := get_tree().get_first_node_in_group("world_tint")
	return lerpf(0.18, 1.0, float(tint.get("darkness"))) if tint != null else 1.0


## World-space radius the light reaches at the current state.
func radius() -> float:
	var w := float(texture.get_width()) if texture != null else 256.0
	return w * _scale_target * 0.5


func illuminates(world_pos: Vector2) -> bool:
	return is_lit and global_position.distance_to(world_pos) < radius() * 0.75


func light_level_at(world_pos: Vector2) -> float:
	if not is_lit:
		return 0.0
	return clampf(1.0 - global_position.distance_to(world_pos) / radius(), 0.0, 1.0) * (_energy_target / FULL_ENERGY)


## How far (game px) a watcher can notice this lantern: the core of "light attracts".
func visibility() -> float:
	match state:
		State.FULL:
			return 900.0
		State.LOW:
			return 420.0
	return 0.0

class_name LampLight
extends PointLight2D

## A fixed light in the world: a street lamp, a tube light, an emergency lamp (roadmap J1).
## - `mode`: STEADY, FLICKER (a failing tube / sodium lamp: long bright spells, sudden stutters) or DEAD (off).
## - `needs_power`: only lit once GameState flag "power_on" is set (the breaker in the hall; Chapter 1). Emergency
##   lights don't need it. When the power comes back the lamp stutters on over a second.
## - While lit it is a gameplay light (group "gameplay_lights"): it reveals notes, hides the organism's glow and draws
##   phototropic hosts (LightQuery, NightGuard). A lit lamp is also a safe pool for composure.

enum Mode { STEADY, FLICKER, DEAD }

@export var mode: Mode = Mode.STEADY
@export var needs_power: bool = false
## Gameplay radius in game px (how far it "illuminates" for LightQuery); 0 = from the texture.
@export var gameplay_radius: float = 0.0
@export var base_energy: float = 1.0
## False for mood light (moonlight through a window, an exit sign): it lights the picture but not the gameplay
## (doesn't reveal notes, hide glow or draw hosts).
@export var gameplay: bool = true

var _t := 0.0
var _rng := RandomNumberGenerator.new()
var _next_stutter := 0.0
var _stutter_left := 0.0
var _powering := 0.0


func _ready() -> void:
	_rng.seed = hash(str(get_path())) if is_inside_tree() else 1
	_t = _rng.randf() * 10.0
	_next_stutter = _rng.randf_range(1.0, 6.0)
	if needs_power:
		GameState.flag_changed.connect(_on_flag)
	_refresh(true)


func is_on() -> bool:
	if mode == Mode.DEAD:
		return false
	return not needs_power or GameState.has_flag("power_on")


func _on_flag(id: String, _v: Variant) -> void:
	if id == "power_on" and is_on():
		_powering = 1.2
	_refresh(false)


func _refresh(_instant: bool) -> void:
	var on := is_on()
	enabled = on
	if on and gameplay:
		add_to_group("gameplay_lights")
	elif is_in_group("gameplay_lights"):
		remove_from_group("gameplay_lights")


func _process(delta: float) -> void:
	if not enabled:
		return
	_t += delta
	var e := base_energy * (1.0 + 0.02 * sin(_t * 7.0))
	if _powering > 0.0:
		_powering -= delta
		e *= 1.0 if fmod(_t * 13.0, 1.0) > 0.5 + _powering * 0.3 else 0.1
	elif mode == Mode.FLICKER:
		_next_stutter -= delta
		if _next_stutter <= 0.0:
			_stutter_left = _rng.randf_range(0.15, 0.9)
			_next_stutter = _rng.randf_range(2.0, 9.0)
		if _stutter_left > 0.0:
			_stutter_left -= delta
			e *= 0.08 if sin(_t * 61.0) * sin(_t * 23.0) > 0.0 else 0.85
	energy = e


func radius() -> float:
	if gameplay_radius > 0.0:
		return gameplay_radius
	var w := float(texture.get_width()) if texture != null else 256.0
	return w * texture_scale * 0.5


func illuminates(world_pos: Vector2) -> bool:
	return enabled and energy > 0.3 * base_energy and global_position.distance_to(world_pos) < radius() * 0.7


func light_level_at(world_pos: Vector2) -> float:
	if not enabled:
		return 0.0
	return clampf(1.0 - global_position.distance_to(world_pos) / radius(), 0.0, 1.0) * clampf(energy, 0.0, 1.0)


## Phototropic hosts notice a lamp from this far (they wander towards lit lamps).
func visibility() -> float:
	return radius() * 2.0 if enabled else 0.0

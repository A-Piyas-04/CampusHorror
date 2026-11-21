class_name NightGuard
extends CharacterBody2D

## The Night Guard (Docs/GAME_DESIGN.md section 5): the campus security guard, still walking his patrol, now a
## phototropic host. Not fought, only avoided.
##
## Senses (checked 10 times a second; walls block them):
## - LIGHT, above all: a lit lantern is seen from lantern.visibility() (Full 900 px, Low 420 px, Off 0).
## - SIGHT: an unlit player only up close, mostly in front of him.
## - SOUND: footsteps carry by surface and gait (sprinting on asphalt rings the bell; sneaking on grass is nearly
##   silent).
## States: PATROL (walks the route, lingers at points) -> SUSPICIOUS (stops, turns to the source, groans) ->
## INVESTIGATE (walks to where it was) -> CHASE (lurching run) -> SEARCH (sweeps around the last sighting) ->
## back to PATROL. Light seen from close range skips straight to CHASE.
## Catching the player (touching them) emits `caught`; the chapter director handles the blackout and checkpoint.

signal caught
signal state_changed(state: int)

enum State { PATROL, SUSPICIOUS, INVESTIGATE, CHASE, SEARCH, IDLE }

const NOISE := {&"grass": 90.0, &"worn_grass": 110.0, &"paving": 170.0, &"asphalt": 210.0, &"concrete": 190.0}
const GAIT_NOISE := {&"sneak": 0.35, &"walk": 1.0, &"run": 2.6}

@export var patrol_speed: float = 42.0
@export var investigate_speed: float = 58.0
@export var chase_speed: float = 134.0
@export var catch_radius: float = 20.0
@export var sight_radius: float = 150.0
@export var close_sense_radius: float = 64.0
## Seconds without contact before a chase turns into a search.
@export var lose_seconds: float = 3.0
@export var search_seconds: float = 7.0
## Patrol route: global positions, walked in order (looping).
@export var patrol_points: PackedVector2Array = PackedVector2Array()
@export var linger_seconds: float = 2.5
## When false he stands still (scripted appearances).
@export var active: bool = false

var state: State = State.PATROL
var awareness := 0.0
var facing := "down"
var _target := Vector2.ZERO
var _last_known := Vector2.ZERO
var _since_contact := 0.0
var _state_time := 0.0
var _patrol_index := 0
var _linger := 0.0
var _sense_timer := 0.0
var _groan_timer := 4.0
var _player: Player
var _search_points: Array[Vector2] = []
var _caught_once := false
var _stuck_time := 0.0
var _last_pos := Vector2.ZERO
var _cycles := {}

@onready var _agent: NavigationAgent2D = $NavAgent
@onready var _sprite: AnimatedSprite2D = $Sprite
@onready var _eyes: Node2D = $Eyes


func _ready() -> void:
	add_to_group("threats")
	add_to_group("creatures")
	_cycles = _sprite.sprite_frames.get_meta("cycles", {}) if _sprite.sprite_frames != null else {}
	_sprite.frame_changed.connect(_on_frame_changed)
	_agent.path_desired_distance = 10.0
	_agent.target_desired_distance = 12.0
	_agent.avoidance_enabled = false
	_target = global_position
	_last_pos = global_position
	if patrol_points.size() > 0:
		_patrol_index = _nearest_patrol_index()
		_set_target(patrol_points[_patrol_index])


func _nearest_patrol_index() -> int:
	var best := 0
	for i in patrol_points.size():
		if patrol_points[i].distance_to(global_position) < patrol_points[best].distance_to(global_position):
			best = i
	return best


func set_player(p: Player) -> void:
	if _player != null and _player.footstep.is_connected(_on_player_footstep):
		_player.footstep.disconnect(_on_player_footstep)
	_player = p
	if _player != null:
		_player.footstep.connect(_on_player_footstep)


func _exit_tree() -> void:
	set_player(null)


# --- Threat (Composure reads this) -----------------------------------------------------------------------------

func threat_to(pos: Vector2) -> float:
	if not active:
		return 0.0
	var d := global_position.distance_to(pos)
	match state:
		State.CHASE:
			return clampf(1.2 - d / 700.0, 0.4, 1.0)
		State.SUSPICIOUS, State.INVESTIGATE, State.SEARCH:
			return clampf(0.8 - d / 600.0, 0.0, 0.7)
	return clampf(0.45 - d / 900.0, 0.0, 0.4)


# --- Senses ----------------------------------------------------------------------------------------------------

func _line_of_sight(to: Vector2) -> bool:
	var space := get_world_2d().direct_space_state
	var q := PhysicsRayQueryParameters2D.create(global_position + Vector2(0, -6), to + Vector2(0, -6), 1)
	q.exclude = [get_rid()]
	return space.intersect_ray(q).is_empty()


func _sense(delta: float) -> void:
	if _player == null or not is_instance_valid(_player):
		return
	var p := _player.global_position
	var d := global_position.distance_to(p)
	if _player.concealed:
		# Seen getting in while chased up close: he knows where you are.
		if state == State.CHASE and d < 200.0 and _since_contact < 0.6:
			_last_known = p
			_since_contact = 0.0
		else:
			awareness = maxf(awareness - delta * 0.25, 0.0)
		return
	var gain := 0.0
	var lantern := _player.get_node_or_null("Lantern")
	var vis := float(lantern.call("visibility")) if lantern != null else 0.0
	var los := d < 1100.0 and _line_of_sight(p)
	if los and vis > 0.0 and d < vis:
		# Far light makes him curious (he walks over to look); close light is unmistakable.
		gain = maxf(gain, 1.6 * pow(1.0 - d / vis, 1.5) + 0.12)
	if los and d < sight_radius:
		var to := (p - global_position).normalized()
		var front := _facing_vector().dot(to) > 0.2
		if front or d < close_sense_radius:
			gain = maxf(gain, 1.4 * (1.0 - d / sight_radius) + 0.3)
	if gain > 0.0:
		awareness = minf(awareness + gain * delta * 2.0, 1.5)
		_last_known = p
		if awareness >= 1.0:
			_since_contact = 0.0
	else:
		awareness = maxf(awareness - delta * 0.12, 0.0)


func _on_player_footstep(surface: StringName, gait: StringName, at: Vector2) -> void:
	if not active or _player == null:
		return
	var radius: float = float(NOISE.get(surface, 140.0)) * float(GAIT_NOISE.get(gait, 1.0))
	var d := global_position.distance_to(at)
	if d > radius:
		return
	if state == State.CHASE:
		_last_known = at
		_since_contact = minf(_since_contact, 0.5)
		return
	awareness = minf(awareness + 0.35 * (1.0 - d / radius) + 0.1, 1.2)
	_last_known = at


func _facing_vector() -> Vector2:
	match facing:
		"right": return Vector2.RIGHT
		"left": return Vector2.LEFT
		"up": return Vector2.UP
		"down": return Vector2.DOWN
		"down_right": return Vector2(1, 1).normalized()
		"down_left": return Vector2(-1, 1).normalized()
		"up_right": return Vector2(1, -1).normalized()
		"up_left": return Vector2(-1, -1).normalized()
	return Vector2.DOWN


# --- Brain -----------------------------------------------------------------------------------------------------

func _set_state(s: State) -> void:
	if s == state:
		return
	state = s
	_state_time = 0.0
	match s:
		State.CHASE:
			AudioDirector.play_at(&"guard_shriek", global_position, 2.0)
			var comp := get_tree().get_first_node_in_group("composure")
			if comp != null:
				comp.call("shock", 0.08, 2.5)
		State.SUSPICIOUS:
			AudioDirector.play_at(&"guard_groan", global_position, -2.0, 0.85)
		State.SEARCH:
			_search_points.clear()
			for i in 4:
				var a := randf() * TAU
				_search_points.append(_last_known + Vector2(cos(a), sin(a) * 0.7) * randf_range(60.0, 160.0))
	state_changed.emit(s)


func _set_target(p: Vector2) -> void:
	_target = p
	_agent.target_position = p


func _physics_process(delta: float) -> void:
	_state_time += delta
	if not active:
		velocity = Vector2.ZERO
		_animate(delta)
		return
	_sense_timer -= delta
	if _sense_timer <= 0.0:
		_sense(0.1)
		_sense_timer = 0.1
	_since_contact += delta
	_groan_timer -= delta
	if _groan_timer <= 0.0:
		_groan_timer = randf_range(5.0, 11.0)
		if state != State.CHASE:
			AudioDirector.play_at(&"guard_groan", global_position, -6.0, randf_range(0.8, 1.05))
	var speed := 0.0
	match state:
		State.PATROL, State.IDLE:
			if awareness >= 1.0:
				_set_state(State.CHASE)
			elif awareness >= 0.35:
				_set_state(State.SUSPICIOUS)
			elif patrol_points.size() > 0:
				if _linger > 0.0:
					_linger -= delta
				elif global_position.distance_to(_target) < 14.0:
					_linger = linger_seconds * randf_range(0.6, 1.4)
					_patrol_index = (_patrol_index + 1) % patrol_points.size()
					_set_target(patrol_points[_patrol_index])
				else:
					speed = patrol_speed
		State.SUSPICIOUS:
			facing = _facing_for(_last_known - global_position)
			if awareness >= 1.0:
				_set_state(State.CHASE)
			elif _state_time > 1.6:
				_set_target(_last_known)
				_set_state(State.INVESTIGATE)
		State.INVESTIGATE:
			speed = investigate_speed
			if _last_known.distance_to(_target) > 40.0:
				_set_target(_last_known)
			if awareness >= 1.0:
				_set_state(State.CHASE)
			elif global_position.distance_to(_target) < 16.0 or _state_time > 12.0:
				_set_state(State.SEARCH)
		State.CHASE:
			speed = chase_speed
			if _player != null and not _player.concealed and _since_contact < 0.3:
				_set_target(_player.global_position)
			else:
				_set_target(_last_known)
			if _since_contact > lose_seconds:
				awareness = 0.6
				_set_state(State.SEARCH)
		State.SEARCH:
			speed = investigate_speed
			if awareness >= 1.0:
				_set_state(State.CHASE)
			elif global_position.distance_to(_target) < 16.0 or _stuck_time > 1.5:
				if _search_points.is_empty() or _state_time > search_seconds:
					awareness = 0.0
					_set_state(State.PATROL)
					if patrol_points.size() > 0:
						_patrol_index = _nearest_patrol_index()
						_set_target(patrol_points[_patrol_index])
				else:
					_set_target(_search_points.pop_back())
	_move(speed, delta)
	_check_catch()
	_animate(delta)


func _move(speed: float, delta: float) -> void:
	if speed <= 0.0:
		velocity = velocity.move_toward(Vector2.ZERO, 900.0 * delta)
		move_and_slide()
		return
	var next := _agent.get_next_path_position()
	var dir := next - global_position
	if dir.length() < 2.0:
		dir = _target - global_position
	var want := dir.normalized() * speed if dir.length() > 2.0 else Vector2.ZERO
	velocity = velocity.move_toward(want, (900.0 if state == State.CHASE else 500.0) * delta)
	move_and_slide()
	if global_position.distance_to(_last_pos) < speed * delta * 0.2:
		_stuck_time += delta
	else:
		_stuck_time = 0.0
	_last_pos = global_position


func _check_catch() -> void:
	if _player == null or _caught_once or _player.concealed and state != State.CHASE:
		return
	if global_position.distance_to(_player.global_position) < catch_radius \
			or (_player.concealed and state == State.CHASE and global_position.distance_to(_player.global_position) < 34.0
				and _since_contact < 1.0):
		_caught_once = true
		active = false
		AudioDirector.play_at(&"guard_shriek", global_position, 4.0, 0.8)
		caught.emit()


## After a checkpoint reload the guard is placed fresh; this resets him in place.
func reset_brain() -> void:
	awareness = 0.0
	_caught_once = false
	active = true
	_since_contact = 99.0
	_set_state(State.PATROL)
	if patrol_points.size() > 0:
		_patrol_index = _nearest_patrol_index()
		_set_target(patrol_points[_patrol_index])


# --- Animation -----------------------------------------------------------------------------------------------

const SECTORS := ["right", "down_right", "down", "down_left", "left", "up_left", "up", "up_right"]


func _facing_for(v: Vector2) -> String:
	if v.length() < 0.01:
		return facing
	return SECTORS[posmod(roundi(rad_to_deg(atan2(v.y, v.x)) / 45.0), 8)]


func _animate(_delta: float) -> void:
	var speed := velocity.length()
	var set_name := "idle"
	if speed > 5.0:
		facing = _facing_for(velocity)
		set_name = "run" if speed > 90.0 else "walk"
	var anim := StringName("%s_%s" % [set_name, facing])
	if _sprite.animation != anim and _sprite.sprite_frames.has_animation(anim):
		_sprite.play(anim)
	var cyc: Dictionary = _cycles.get(set_name, {})
	var ref := float(cyc.get("speed_px_s", 0.0))
	_sprite.speed_scale = clampf(speed / ref, 0.6, 1.4) if ref > 0.0 else 1.0
	_eyes.visible = facing in ["down", "down_left", "down_right", "left", "right"]


func _on_frame_changed() -> void:
	var set_name := String(_sprite.animation).get_slice("_", 0)
	var cyc: Dictionary = _cycles.get(set_name, {})
	if _sprite.frame in cyc.get("contact_frames", []):
		AudioDirector.play_at(&"guard_step", global_position, -10.0 if set_name == "walk" else -4.0,
			randf_range(0.9, 1.05))

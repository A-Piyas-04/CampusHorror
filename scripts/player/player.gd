class_name Player
extends CharacterBody2D

## The one persistent player. Movement v2 (roadmap I1, Docs/PRESENTATION.md section 4):
## sneak / walk / sprint at speeds matched to the animation strides, eased acceleration and braking,
## stamina for sprinting, and an input lock for transitions. The animator (player_animator.gd) reads
## `velocity` and `gait` and calls `emit_footstep()` on heel-strike frames.

## Emitted when the nearest interactable in range changes; `null` when none is in range.
signal interaction_target_changed(target: Interactable)
## The movement the player is asking for changed: &"idle", &"sneak", &"walk" or &"sprint".
signal movement_mode_changed(mode: StringName)
## Stamina (0..1) changed; `winded` is true from empty until it recovers to `winded_until`.
signal stamina_changed(stamina: float, winded: bool)
## A foot touched the ground (heel strike). Footstep audio listens; from J5 it is the player's noise.
signal footstep(surface: StringName, gait: StringName, at: Vector2)

@export_group("Speeds (game px/s; 32 px = 1 m)")
@export var sneak_speed: float = 32.0
@export var walk_speed: float = 62.0
@export var sprint_speed: float = 154.0
## Analog stick tilt (0..1, after the dead zone) below which the player sneaks.
@export_range(0.0, 1.0, 0.05) var sneak_tilt: float = 0.6

@export_group("Acceleration (game px/s squared)")
## Speeding up to walk speed: 0 -> walk in 0.10 s.
@export var acceleration: float = 620.0
## Speeding up beyond walk speed: walk -> sprint in 0.25 s.
@export var sprint_acceleration: float = 370.0
## Slowing down, stopping and reversing: walk -> stop in 0.08 s.
@export var braking: float = 775.0

@export_group("Stamina")
## Seconds of continuous sprinting from full.
@export var sprint_seconds: float = 6.0
## Seconds to refill from empty, after `recover_delay`.
@export var recover_seconds: float = 8.0
@export var recover_delay: float = 1.0
## Once empty, sprinting is blocked until stamina is back to this.
@export_range(0.0, 1.0, 0.05) var winded_until: float = 0.3

## False while a transition or cutscene owns the player: no movement input (the player brakes to a stop)
## and no interaction.
var input_enabled := true
var stamina := 1.0
var winded := false
## What the player is asking for this frame.
var mode: StringName = &"idle"
## The cycle the body is in: &"sneak", &"walk" or &"run". Kept while braking to a stop.
var gait: StringName = &"walk"
## Set by Main on zone entry; answers "what surface is under the feet".
var surface_map: SurfaceMap

var _since_sprint := INF
var _interaction_target: Interactable

@onready var _interaction_area: Area2D = $InteractionArea
@onready var _camera: Camera2D = $Camera


func _ready() -> void:
	# Sounds are heard from the player's feet, not from the look-ahead camera.
	($Listener as AudioListener2D).make_current()


func _physics_process(delta: float) -> void:
	var dir := Vector2.ZERO
	var want_sprint := false
	var want_sneak := false
	if input_enabled:
		dir = Input.get_vector("move_left", "move_right", "move_up", "move_down")
		want_sprint = Input.is_action_pressed("sprint")
		want_sneak = Input.is_action_pressed("sneak")
	var tilt := minf(dir.length(), 1.0)
	var new_mode: StringName
	if tilt <= 0.0:
		new_mode = &"idle"
	elif want_sneak or tilt < sneak_tilt:
		new_mode = &"sneak"
	elif want_sprint and not winded:
		new_mode = &"sprint"
	else:
		new_mode = &"walk"
	if new_mode != mode:
		mode = new_mode
		movement_mode_changed.emit(mode)
	if mode != &"idle":
		gait = &"run" if mode == &"sprint" else mode

	var target := Vector2.ZERO
	if mode != &"idle":
		target = dir.normalized() * get_mode_speed(mode)
	var speed_now := velocity.length()
	var rate := acceleration
	if target.length() < speed_now - 0.01 or target.dot(velocity) < 0.0:
		rate = braking
	elif speed_now >= walk_speed - 0.5 and target.length() > walk_speed:
		rate = sprint_acceleration
	velocity = velocity.move_toward(target, rate * delta)
	move_and_slide()

	_update_stamina(delta)
	_update_interaction_target()


func get_mode_speed(for_mode: StringName) -> float:
	match for_mode:
		&"sneak":
			return sneak_speed
		&"sprint":
			return sprint_speed
		&"walk":
			return walk_speed
	return 0.0


## Called by the animator on a heel-strike frame.
func emit_footstep() -> void:
	var surface: StringName = surface_map.surface_at(global_position) if surface_map != null else &"grass"
	footstep.emit(surface, gait, global_position)


func _update_stamina(delta: float) -> void:
	var before := stamina
	var was_winded := winded
	if mode == &"sprint" and velocity.length() > walk_speed + 0.5:
		stamina = maxf(stamina - delta / sprint_seconds, 0.0)
		_since_sprint = 0.0
	else:
		_since_sprint += delta
		if _since_sprint >= recover_delay:
			stamina = minf(stamina + delta / recover_seconds, 1.0)
	if stamina <= 0.0:
		winded = true
	elif winded and stamina >= winded_until:
		winded = false
	if stamina != before or winded != was_winded:
		stamina_changed.emit(stamina, winded)


func _unhandled_input(event: InputEvent) -> void:
	if input_enabled and event.is_action_pressed("interact") and is_instance_valid(_interaction_target):
		_interaction_target.interact(self)
		get_viewport().set_input_as_handled()


## Places the player's feet at `target_position` instantly (zone changes, spawns, loading).
func teleport(target_position: Vector2) -> void:
	global_position = target_position
	velocity = Vector2.ZERO
	# Physics interpolation is on (Docs/PRESENTATION.md): without this the player would be drawn sliding
	# from the old position to the new one over a physics tick.
	reset_physics_interpolation()
	_set_interaction_target(null)
	if _camera.has_method("snap"):
		_camera.call("snap")
	else:
		_camera.reset_smoothing()


func _update_interaction_target() -> void:
	var nearest: Interactable = null
	var nearest_distance := INF
	if input_enabled:
		for area in _interaction_area.get_overlapping_areas():
			var interactable := area as Interactable
			if interactable == null:
				continue
			var distance := global_position.distance_squared_to(interactable.global_position)
			if distance < nearest_distance:
				nearest = interactable
				nearest_distance = distance
	if nearest != _interaction_target:
		_set_interaction_target(nearest)


func _set_interaction_target(target: Interactable) -> void:
	if is_instance_valid(_interaction_target):
		_interaction_target.tree_exiting.disconnect(_on_interaction_target_tree_exiting)
	_interaction_target = target
	if target != null:
		target.tree_exiting.connect(_on_interaction_target_tree_exiting)
	interaction_target_changed.emit(target)


## A freed target (e.g. a collected pickup) would otherwise keep the prompt visible.
func _on_interaction_target_tree_exiting() -> void:
	_set_interaction_target(null)

class_name Player
extends CharacterBody2D

## Emitted when the nearest interactable in range changes; `null` when none is in range.
signal interaction_target_changed(target: Interactable)

## Walking speed in pixels per second.
@export var move_speed: float = 200.0

var _interaction_target: Interactable

@onready var _interaction_area: Area2D = $InteractionArea
@onready var _camera: Camera2D = $Camera


func _physics_process(_delta: float) -> void:
	var direction := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	velocity = direction * move_speed
	move_and_slide()
	_update_interaction_target()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact") and is_instance_valid(_interaction_target):
		_interaction_target.interact(self)
		get_viewport().set_input_as_handled()


## Places the player's feet at `target_position` instantly (zone changes, spawns).
func teleport(target_position: Vector2) -> void:
	global_position = target_position
	velocity = Vector2.ZERO
	_set_interaction_target(null)
	_camera.reset_smoothing()


func _update_interaction_target() -> void:
	var nearest: Interactable = null
	var nearest_distance := INF
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

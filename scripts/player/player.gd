class_name Player
extends CharacterBody2D

## Emitted when the nearest interactable in range changes; `null` when none is in range.
signal interaction_target_changed(target: Interactable)

## Walking speed in pixels per second.
@export var move_speed: float = 200.0

var _interaction_target: Interactable

@onready var _interaction_area: Area2D = $InteractionArea


func _physics_process(_delta: float) -> void:
	var direction := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	velocity = direction * move_speed
	move_and_slide()
	_update_interaction_target()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact") and is_instance_valid(_interaction_target):
		_interaction_target.interact(self)
		get_viewport().set_input_as_handled()


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
		_interaction_target = nearest
		interaction_target_changed.emit(nearest)

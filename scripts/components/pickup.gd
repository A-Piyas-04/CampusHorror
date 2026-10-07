class_name Pickup
extends Node2D

## Stable, globally unique ID recorded in GameState when collected. Set in the Inspector.
@export var pickup_id: String = ""
## Overrides the interaction prompt. Leave empty to keep the Interactable's default text.
@export var prompt_text: String = ""

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	if pickup_id.is_empty():
		push_error("Pickup '%s' has no pickup_id." % get_path())
		return
	if GameState.is_collected(pickup_id):
		queue_free()
		return
	if not prompt_text.is_empty():
		_interactable.prompt_text = prompt_text


func _on_interactable_interacted(_interactor: Node2D) -> void:
	if pickup_id.is_empty() or GameState.is_collected(pickup_id):
		return
	GameState.mark_collected(pickup_id)
	print("[PICKUP] Collected '%s'." % pickup_id)
	queue_free()

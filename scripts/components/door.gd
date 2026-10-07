class_name Door
extends Node2D

## Emitted when the player uses the door. Main performs the zone change.
signal travel_requested(destination_zone_id: String, destination_spawn_id: String)

## zone_id of the zone this door leads to.
@export var destination_zone_id: String = ""
## spawn_id of the marker in the destination zone where the player arrives.
@export var destination_spawn_id: String = ""
## Overrides the interaction prompt. Leave empty to keep the Interactable's default text.
@export var prompt_text: String = ""

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	if not prompt_text.is_empty():
		_interactable.prompt_text = prompt_text


func _on_interactable_interacted(_interactor: Node2D) -> void:
	travel_requested.emit(destination_zone_id, destination_spawn_id)

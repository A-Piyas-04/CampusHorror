class_name Door
extends Node2D

## Emitted when the player uses the door. Main performs the zone change.
signal travel_requested(destination_zone_id: String, destination_spawn_id: String)

## zone_id of the zone this door leads to.
@export var destination_zone_id: String = ""
## spawn_id of the marker in the destination zone where the player arrives.
@export var destination_spawn_id: String = ""
## The prompt's verb and place, e.g. "Enter" + "CDS veranda" (roadmap I7).
@export var verb: String = "Enter"
@export var place_name: String = ""
## 0 = press; above 0 = hold `interact` this long (e.g. a heavy or locked door).
@export_range(0.0, 3.0, 0.05) var hold_seconds: float = 0.0

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	_interactable.verb = verb
	_interactable.object_name = place_name
	_interactable.hold_seconds = hold_seconds


func _on_interactable_interacted(_interactor: Node2D) -> void:
	travel_requested.emit(destination_zone_id, destination_spawn_id)

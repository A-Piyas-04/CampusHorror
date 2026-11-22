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
## Locked until the player has this item ("" = not locked by an item).
@export var required_item: String = ""
## Locked until this story flag is true ("" = not locked by a flag).
@export var requires_flag: String = ""
## Shown when the door won't open.
@export var locked_message: String = "Locked."
## Shown once, the first time it is unlocked ("" = nothing).
@export var unlock_message: String = ""
## Flag recording that this door was unlocked (so it stays unlocked); defaults to "door_unlocked_<node name>".
@export var unlocked_flag: String = ""
## The brown placeholder rectangle; turn off when a real door prop stands here.
@export var show_placeholder: bool = true

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	_interactable.verb = verb
	_interactable.object_name = place_name
	_interactable.hold_seconds = hold_seconds
	($Body as CanvasItem).visible = show_placeholder
	if unlocked_flag.is_empty():
		unlocked_flag = "door_unlocked_%s" % name


func is_locked() -> bool:
	if not Game.story_active:
		return false          # Explore mode (D45): every door opens, like ZoneEdge locks outside the story
	if GameState.has_flag(unlocked_flag):
		return false
	if not required_item.is_empty() and not GameState.has_item(required_item):
		return true
	if not requires_flag.is_empty() and not GameState.has_flag(requires_flag):
		return true
	return false


func _on_interactable_interacted(_interactor: Node2D) -> void:
	var hud := get_tree().get_first_node_in_group("hud")
	if is_locked():
		AudioDirector.play_at(&"door_locked", global_position, -2.0)
		if hud != null:
			hud.call("toast", locked_message)
		return
	if (not required_item.is_empty() or not requires_flag.is_empty()) and not GameState.has_flag(unlocked_flag):
		GameState.set_flag(unlocked_flag)
		if hud != null and not unlock_message.is_empty():
			hud.call("toast", unlock_message)
	AudioDirector.play_at(&"door_open", global_position, -4.0)
	travel_requested.emit(destination_zone_id, destination_spawn_id)

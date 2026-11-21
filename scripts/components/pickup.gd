class_name Pickup
extends Node2D

## Stable, globally unique ID recorded in GameState when collected. Set in the Inspector.
@export var pickup_id: String = ""
## The prompt's verb and item name, e.g. "Pick up" + "Torch battery" (roadmap I7).
@export var verb: String = "Pick up"
@export var item_name: String = ""
## Added to GameState's inventory when picked up ("" = nothing; e.g. "cds_master_key").
@export var item_id: String = ""
## Lamp oil added to the lantern's fuel (0..1) when picked up (0 = none).
@export_range(0.0, 1.0, 0.05) var fuel: float = 0.0
## Story flag set to true when picked up ("" = none).
@export var sets_flag: String = ""
## The yellow placeholder diamond; turn off when a real prop stands here.
@export var show_placeholder: bool = true

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	if pickup_id.is_empty():
		push_error("Pickup '%s' has no pickup_id." % get_path())
		return
	if GameState.is_collected(pickup_id):
		queue_free()
		return
	_interactable.verb = verb
	_interactable.object_name = item_name
	($Body as CanvasItem).visible = show_placeholder


func _on_interactable_interacted(_interactor: Node2D) -> void:
	if pickup_id.is_empty() or GameState.is_collected(pickup_id):
		return
	GameState.mark_collected(pickup_id)
	if not item_id.is_empty():
		GameState.add_item(item_id)
	if fuel > 0.0:
		GameState.set_fuel(GameState.lantern_fuel + fuel)
	if not sets_flag.is_empty():
		GameState.set_flag(sets_flag)
	var hud := get_tree().get_first_node_in_group("hud")
	AudioDirector.play_ui(&"pickup", -4.0)
	if hud != null:
		hud.call("toast", "Picked up: %s" % (item_name if not item_name.is_empty() else pickup_id))
	print("[PICKUP] Collected '%s'." % pickup_id)
	queue_free()

class_name Examine
extends Node2D

## Something to look at or try (roadmap K4): the chained gate, a dead phone, a CCTV screen. Interact shows
## `message` as a toast (or `long_message` in the note viewer), can play a sound and set a story flag.
## `requires_flag` / `hidden_until_flag`: only usable / only present once a flag is set.

signal examined

@export var verb: String = "Examine"
@export var object_name: String = ""
@export_multiline var message: String = ""
## Opens the note viewer instead of a toast (title = object_name).
@export_multiline var long_message: String = ""
@export var sound: StringName = &""
@export var sets_flag: String = ""
@export var requires_flag: String = ""
@export var not_ready_message: String = ""
@export var hidden_until_flag: String = ""

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	_interactable.verb = verb
	_interactable.object_name = object_name
	if not hidden_until_flag.is_empty():
		_refresh()
		GameState.flag_changed.connect(func(_id: String, _v: Variant) -> void: _refresh())


func _refresh() -> void:
	var on := GameState.has_flag(hidden_until_flag)
	visible = on
	_interactable.monitorable = on


func _on_interactable_interacted(_by: Node2D) -> void:
	var hud := get_tree().get_first_node_in_group("hud")
	if not requires_flag.is_empty() and not GameState.has_flag(requires_flag):
		if hud != null and not not_ready_message.is_empty():
			hud.call("toast", not_ready_message)
		return
	if sound != &"":
		AudioDirector.play_at(sound, global_position)
	if not long_message.is_empty():
		var viewer := get_tree().get_first_node_in_group("note_viewer")
		if viewer != null:
			viewer.call("show_note", object_name, long_message)
	elif hud != null and not message.is_empty():
		hud.call("toast", message)
	if not sets_flag.is_empty():
		GameState.set_flag(sets_flag)
	examined.emit()

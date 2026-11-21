class_name Keypad
extends Node2D

## A code lock in the world (breaker panel, key box). Interact to open the keypad screen; the right code sets
## `solved_flag` and emits `solved`. Once solved it only shows `solved_message`.
## `requires_flag`: can't be used before that story flag is set (shows `not_ready_message`).

signal solved

@export var code: String = "0000"
@export var title: String = "Keypad"
@export var verb: String = "Use"
@export var solved_flag: String = ""
@export var solved_message: String = "Done."
@export var requires_flag: String = ""
@export var not_ready_message: String = ""
@export var wrong_message: String = "Wrong code."

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	_interactable.verb = verb
	_interactable.object_name = title


func is_solved() -> bool:
	return not solved_flag.is_empty() and GameState.has_flag(solved_flag)


func _on_interactable_interacted(_by: Node2D) -> void:
	var hud := get_tree().get_first_node_in_group("hud")
	if is_solved():
		if hud != null:
			hud.call("toast", solved_message)
		return
	if not requires_flag.is_empty() and not GameState.has_flag(requires_flag):
		if hud != null and not not_ready_message.is_empty():
			hud.call("toast", not_ready_message)
		return
	var ui := get_tree().get_first_node_in_group("keypad_ui") as KeypadUI
	if ui == null:
		return
	var entered: String = await ui.ask(title, code.length())
	if entered.is_empty():
		return
	if entered == code:
		AudioDirector.play_ui(&"keypad_ok")
		if not solved_flag.is_empty():
			GameState.set_flag(solved_flag)
		solved.emit()
	else:
		AudioDirector.play_ui(&"keypad_bad")
		if hud != null:
			hud.call("toast", wrong_message)

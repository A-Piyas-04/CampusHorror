class_name Interactable
extends Area2D

## Emitted when the player uses this object with the `interact` action.
signal interacted(interactor: Node2D)

## Text shown by the interaction prompt while the player is in range.
@export var prompt_text: String = "Press E to interact"


func interact(interactor: Node2D) -> void:
	interacted.emit(interactor)

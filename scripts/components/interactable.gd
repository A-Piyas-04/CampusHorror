class_name Interactable
extends Area2D

## Reusable interaction component (roadmap I7). The player's sensor finds the nearest one in range; the
## world-space prompt shows `verb` and `object_name` with the device's glyph for `interact`.

## Emitted when the player uses this object with the `interact` action (after a full hold if `hold_seconds` > 0).
signal interacted(interactor: Node2D)

## What the player does, shown large in the prompt: "Enter", "Open", "Pick up", "Read", "Use".
@export var verb: String = "Use"
## What it is or where it leads, shown under the verb: "CDS veranda". Optional.
@export var object_name: String = ""
## 0 = a press. Above 0 = the player must hold `interact` this many seconds (the prompt shows a ring filling).
@export_range(0.0, 3.0, 0.05) var hold_seconds: float = 0.0
## Where the prompt floats, relative to this Interactable, in game px (negative y = up).
@export var prompt_offset: Vector2 = Vector2(0, -56)


func interact(interactor: Node2D) -> void:
	interacted.emit(interactor)

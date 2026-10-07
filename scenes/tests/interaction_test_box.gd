extends StaticBody2D

const COLOR_OFF := Color(0.6, 0.3, 0.8, 1)
const COLOR_ON := Color(0.95, 0.9, 0.3, 1)

var _use_count := 0

@onready var _body: Polygon2D = $Body


func _ready() -> void:
	_body.color = COLOR_OFF


func _on_interactable_interacted(interactor: Node2D) -> void:
	_use_count += 1
	_body.color = COLOR_ON if _use_count % 2 == 1 else COLOR_OFF
	print("[INTERACT] %s used by %s (count %d)" % [name, interactor.name, _use_count])

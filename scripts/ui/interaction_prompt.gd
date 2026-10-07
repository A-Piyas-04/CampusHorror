extends CanvasLayer

@onready var _label: Label = $Label


func _ready() -> void:
	_label.hide()


func _on_player_interaction_target_changed(target: Interactable) -> void:
	if target == null:
		_label.hide()
		return
	_label.text = target.prompt_text
	_label.show()

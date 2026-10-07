extends CanvasModulate

## TEMPORARY Milestone F lighting proof: switches the world tint between two placeholder colours.
## Not a day/night system. Timing, transitions and gameplay effects of night are undecided.

@export var day_color: Color = Color.WHITE
@export var night_color: Color = Color(0.1, 0.11, 0.2)
@export var is_night: bool = false:
	set(value):
		is_night = value
		_apply()


func _ready() -> void:
	_apply()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("debug_toggle_night"):
		is_night = not is_night
		print("[LIGHTING] %s tint." % ("Night" if is_night else "Day"))
		get_viewport().set_input_as_handled()


func _apply() -> void:
	color = night_color if is_night else day_color

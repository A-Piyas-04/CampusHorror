extends CanvasModulate

## PROVISIONAL world tint (on `Main/DayNightTint`): switches the whole world canvas between a day and a
## night colour. It has no input handling; in debug builds `DebugTools` flips it with
## `debug_toggle_night` (F2). Replaced by the real clock and per-zone lighting profiles in roadmap J1.

@export var day_color: Color = Color.WHITE
@export var night_color: Color = Color(0.1, 0.11, 0.2)
@export var is_night: bool = false:
	set(value):
		is_night = value
		_apply()


func _ready() -> void:
	_apply()


func _apply() -> void:
	color = night_color if is_night else day_color

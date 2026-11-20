extends Node

## Developer-only keys, kept in one place so none of them reach a release build.
## Lives in `Main` as `DebugTools`; in a non-debug (exported release) build it frees itself on ready.
##   debug_toggle_night (F2): flip `Main/DayNightTint` between day and night.
##   debug_save (F6) / debug_load (F9): SaveService.save_game() / load_game() until a save UI exists (roadmap K6).
## Debug-only zones (the Milestone C–F test rooms) are gated the same way in `ZoneRegistry`.

@onready var _tint: CanvasModulate = get_node_or_null("../DayNightTint") as CanvasModulate


func _ready() -> void:
	if not OS.is_debug_build():
		queue_free()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("debug_toggle_night"):
		if _tint != null:
			_tint.set("is_night", not _tint.get("is_night"))
			print("[LIGHTING] %s tint." % ("Night" if _tint.get("is_night") else "Day"))
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("debug_save"):
		SaveService.save_game()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("debug_load"):
		SaveService.load_game()
		get_viewport().set_input_as_handled()

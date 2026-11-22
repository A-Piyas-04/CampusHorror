extends Node

## Developer-only keys, kept in one place so none of them reach a release build.
## Lives in `Main` as `DebugTools`; in a non-debug (exported release) build it frees itself on ready.
##   debug_toggle_night (F2): flip `Main/DayNightTint` between day and night.
##   debug_save (F6) / debug_load (F9): SaveService.save_game() / load_game() until a save UI exists (roadmap K6).
##   debug_next_beat (F3): jump to the next Chapter 1 beat, granting what it assumes (story mode only).
##   debug_toggle_guard (F4): switch the Night Guard off / on, to explore without being hunted.
##   debug_refill (F7): fill the lantern with oil.
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
	elif event.is_action_pressed("debug_next_beat"):
		_say(_director().debug_next_beat() if _director() != null else "Not in story mode (start from the title screen).")
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("debug_toggle_guard"):
		_say(_director().debug_toggle_guard() if _director() != null else "Not in story mode.")
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("debug_refill"):
		GameState.set_fuel(1.0)
		_say("Lantern filled")
		get_viewport().set_input_as_handled()


func _director() -> Chapter1:
	var main := get_parent() as Main
	return main.get_director() if main != null else null


## Prints the line and shows it as a HUD toast, so a debug key is visible while playing.
func _say(line: String) -> void:
	print("[DEBUG] %s" % line)
	var hud := get_tree().get_first_node_in_group("hud")
	if hud != null:
		hud.call("toast", "[debug] " + line)

extends PointLight2D

## PROVISIONAL player lantern (on `Player/Lantern`): the gameplay `lantern` action switches the light on
## and off. Replaced in roadmap J2 by the real lantern (off / low / full, fuel, flicker; see
## Docs/GAME_DESIGN.md §3). This is the player's real light, not a debug control.


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("lantern"):
		enabled = not enabled
		print("[LIGHTING] Lantern %s." % ("on" if enabled else "off"))
		get_viewport().set_input_as_handled()

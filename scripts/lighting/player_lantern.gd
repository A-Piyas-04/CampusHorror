extends PointLight2D

## TEMPORARY Milestone F lighting proof: the `lantern` action only toggles this light on/off.
## Real lantern behaviour (fuel, modes, effects on gameplay) is undecided.


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("lantern"):
		enabled = not enabled
		print("[LIGHTING] Lantern %s." % ("on" if enabled else "off"))
		get_viewport().set_input_as_handled()

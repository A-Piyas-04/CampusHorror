extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I interaction suite (I7), on the real Main.tscn: the world-space prompt (verb, name, glyph, position,
## fades), device-aware glyphs and rebinding, hold-to-interact, and the prompt during travel.

const CDS_DOOR := "Objects/Buildings/CDSExterior/TableTennis/DoorCdsMainEntry"
const FIELD := Vector2(-1000, -200)

var prompt: CanvasLayer


func _run() -> void:
	tag = "INTERACT"
	prompt = main.get_node("UI/InteractionPrompt") as CanvasLayer
	check(prompt.follow_viewport_enabled and prompt.layer >= 10,
		"the prompt is its own canvas layer that follows the world through the camera (never darkened by the night tint)")
	await _door_prompt()
	await _glyphs()
	await _hold()
	await _travel_hides()
	_all_have_verbs()


func _door_area() -> Interactable:
	return main.get_current_zone().get_node(CDS_DOOR + "/Interactable") as Interactable


func _door_prompt() -> void:
	var area := _door_area()
	await place(area.global_position + Vector2(0, 6))
	await seconds(0.3)
	var texts: Array = prompt.call("get_texts")
	var glyph: Dictionary = prompt.call("get_glyph")
	check(prompt.call("get_shown_target") == area and approx(prompt.call("get_alpha"), 1.0, 0.01) and texts == ["Enter", "CDS veranda"],
		"at the CDS door the prompt fades in with '%s' / '%s'" % texts)
	check(glyph.get("kind") == "key" and glyph.get("text") == "E", "keyboard glyph: %s" % [glyph])
	var anchor: Vector2 = prompt.call("get_anchor_world")
	check(anchor.distance_to(area.global_position + area.prompt_offset) < 0.5,
		"the prompt sits on the door's prompt point %s (got %s), moving with the world" % [area.global_position + area.prompt_offset, anchor])
	await place(area.global_position + Vector2(-200, 6))
	await seconds(0.3)
	check(prompt.call("get_shown_target") == null and prompt.call("get_alpha") == 0.0, "walking away, the prompt fades out")


func _glyphs() -> void:
	await place(FIELD)
	var pad := InputEventJoypadButton.new()
	pad.button_index = JOY_BUTTON_Y          # not bound to anything: only the device changes
	pad.pressed = true
	Input.parse_input_event(pad)
	pad = pad.duplicate()
	pad.pressed = false
	Input.parse_input_event(pad)
	await frames(2)
	var area := _door_area()
	await place(area.global_position + Vector2(0, 6))
	await seconds(0.2)
	var g: Dictionary = prompt.call("get_glyph")
	check(g.get("kind") == "pad" and g.get("layout") == "xbox" and g.get("text") == "A" and (g.get("color") as Color).g > 0.6,
		"after gamepad input the glyph is the gamepad's interact button (%s, %s %s)" % [g.get("layout"), g.get("text"), g.get("color")])
	var key := InputEventKey.new()
	key.physical_keycode = KEY_F10           # not bound to anything
	key.pressed = true
	Input.parse_input_event(key)
	key = key.duplicate()
	key.pressed = false
	Input.parse_input_event(key)
	await frames(2)
	g = prompt.call("get_glyph")
	check(g.get("kind") == "key" and g.get("text") == "E", "after keyboard input it switches straight back to the key (%s)" % g.get("text"))
	# Rebinding is read live from the Input Map.
	var saved := InputMap.action_get_events(&"interact")
	InputMap.action_erase_events(&"interact")
	var f := InputEventKey.new()
	f.physical_keycode = KEY_F
	InputMap.action_add_event(&"interact", f)
	for e in saved:
		if e is InputEventJoypadButton:
			InputMap.action_add_event(&"interact", e)
	await place(FIELD)
	await place(area.global_position + Vector2(0, 6))
	await seconds(0.2)
	var rebound: String = (prompt.call("get_glyph") as Dictionary).get("text")
	InputMap.action_erase_events(&"interact")
	for e in saved:
		InputMap.action_add_event(&"interact", e)
	check(rebound == "F", "after rebinding interact to F the prompt shows %s" % rebound)


func _press_interact(pressed: bool) -> void:
	var ev := InputEventAction.new()
	ev.action = &"interact"
	ev.pressed = pressed
	Input.parse_input_event(ev)


func _hold() -> void:
	main.change_zone("test_zone_a", "start")
	await frames(2)
	var box := main.get_current_zone().get_node("Objects/InteractionTestBox/Interactable") as Interactable
	box.hold_seconds = 0.5
	var uses := {"n": 0}
	var cb := func(_by): uses.n += 1
	box.interacted.connect(cb)
	await place(box.global_position + Vector2(0, 6))
	await seconds(0.2)
	# A tap is not enough.
	_press_interact(true)
	await seconds(0.2)
	var mid_tap: float = prompt.call("get_progress")
	_press_interact(false)
	await frames(3)
	check(uses.n == 0 and mid_tap > 0.2 and mid_tap < 0.6 and prompt.call("get_progress") == 0.0,
		"a 0.2 s tap on a 0.5 s hold fills the ring to %.2f, then resets on release; nothing is used" % mid_tap)
	# A full hold uses it exactly once, even while still held.
	var peak := {"p": 0.0}
	_press_interact(true)
	for i in 60:
		await get_tree().physics_frame
		peak.p = maxf(peak.p, prompt.call("get_progress"))
	_press_interact(false)
	await frames(3)
	check(uses.n == 1 and peak.p >= 0.95, "holding 1 s uses it exactly once (ring reached %.2f), no repeat while still held" % peak.p)
	box.interacted.disconnect(cb)
	box.hold_seconds = 0.0
	main.change_zone("main_gate_exterior", "main_gate_entry")
	await frames(2)


func _travel_hides() -> void:
	var area := _door_area()
	await place(area.global_position + Vector2(0, 6))
	await seconds(0.3)
	await press("interact")
	var shown_during := 0.0
	while main.is_transitioning():
		shown_during = maxf(shown_during, float(prompt.call("get_alpha")) if prompt.call("get_shown_target") != null else 0.0)
		await get_tree().process_frame
	check(shown_during == 0.0 and main.get_current_zone_id() == "cds_veranda", "during the door travel no prompt is shown (the player has no control)")
	main.change_zone("main_gate_exterior", "main_gate_entry")
	await frames(2)


func _all_have_verbs() -> void:
	var missing := []
	for zid in main.zone_registry.get_zone_ids():
		var z := (load(main.zone_registry.get_scene_path(zid)) as PackedScene).instantiate()
		get_tree().root.add_child(z)
		for a in z.find_children("*", "Area2D", true, false):
			if a is Interactable and (a as Interactable).verb.strip_edges().is_empty():
				missing.append("%s/%s" % [zid, z.get_path_to(a)])
		z.free()
	check(missing.is_empty(), "every interactable in every zone has a verb for its prompt (missing %s)" % [missing])

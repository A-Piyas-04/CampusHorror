extends "res://scenes/tests/feel/feel_check_base.gd"

## Shared helpers for the chapter playthrough suites (test-only): use an interactable with the real interact
## action, skip story cards, close notes, travel through doors, drive the lantern.

# --- helpers -------------------------------------------------------------------------------------------------

func zone_node(path: String) -> Node2D:
	return main.get_current_zone().get_node_or_null(path) as Node2D


func use(node: Node2D, offset := Vector2(0, 14)) -> void:
	await place(node.global_position + offset)
	await frames(4)
	await press("interact")
	await frames(4)


func card_open() -> bool:
	# Main can be freed if a chapter ends by returning to the title.
	return is_instance_valid(main) and bool(main.get_node("UI/StoryCard").call("is_open"))


func skip_card(max_presses := 14) -> void:
	for i in max_presses:
		if not card_open():
			return
		await press("interact")
		await seconds(0.3)
	var start := Time.get_ticks_msec()
	while card_open() and Time.get_ticks_msec() - start < 8000:
		await get_tree().process_frame


func close_note() -> void:
	var viewer := main.get_node("UI/NoteViewer")
	if bool(viewer.call("is_open")):
		await press("interact")
		await frames(4)


func travel_through(door_path: String) -> void:
	await use(zone_node(door_path))
	await frames(2)
	await await_travel()
	await frames(6)


func lantern() -> Node:
	return player.get_node("Lantern")


func set_lantern(target: int) -> void:
	for i in 4:
		if int(lantern().get("state")) == target:
			return
		await press("lantern")

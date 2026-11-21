extends Node
## Test-only screenshot tool for the story flow (needs a window): the title screen, then a NEW game: the intro
## card, the first frame in the dark canteen, and the canteen once the lantern is lit, all at the real in-game
## zoom and night. Uses its own save file. Args (after `--`): `--out-dir=<absolute dir>`. Quits when done.

const TEST_SAVE := "user://test_story_capture_save.json"

var _out := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out-dir="):
			_out = arg.trim_prefix("--out-dir=")
	DirAccess.make_dir_recursive_absolute(_out)
	SaveService.save_path = TEST_SAVE
	_run.call_deferred()


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_out.path_join(name + ".png"))
	print("[STORYCAP] ", name)


func _wait(s: float) -> void:
	await get_tree().create_timer(s, true, false, true).timeout


func _run() -> void:
	var menu := (load("res://scenes/core/MainMenu.tscn") as PackedScene).instantiate()
	get_tree().root.add_child(menu)
	await _wait(2.5)
	await _shot("01_title")
	menu.queue_free()
	await get_tree().process_frame
	Game.set("_start_mode", "new")
	var main := (load("res://scenes/core/Main.tscn") as PackedScene).instantiate() as Main
	get_tree().root.add_child(main)
	await _wait(4.0)
	await _shot("02_intro_card")
	var card := main.get_node("UI/StoryCard") as StoryCard
	while card.is_open():
		var ev := InputEventAction.new()
		ev.action = "interact"
		ev.pressed = true
		Input.parse_input_event(ev)
		await _wait(0.25)
		ev = InputEventAction.new()
		ev.action = "interact"
		ev.pressed = false
		Input.parse_input_event(ev)
		await _wait(0.25)
	await _wait(2.5)
	await _shot("03_wake_in_the_dark")
	GameState.set_flag("got_lantern")
	await _wait(1.5)
	await _shot("04_canteen_lantern")
	for p in [TEST_SAVE, TEST_SAVE + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))
	SaveService.save_path = SaveService.SAVE_PATH
	get_tree().quit(0)

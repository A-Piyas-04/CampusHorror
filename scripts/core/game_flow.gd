extends Node

## Autoload `Game`: how Main.tscn was started, and moving between the title screen and the game.
## Main asks `take_start_mode()` once: "new" (fresh game: intro, Chapter 1), "continue" (load the save), or ""
## (started directly, e.g. from the editor or a test: the classic instant start, no story director).

const MAIN := "res://scenes/core/Main.tscn"
const TITLE := "res://scenes/core/MainMenu.tscn"

var _start_mode := ""


func take_start_mode() -> String:
	var m := _start_mode
	_start_mode = ""
	return m


func new_game() -> void:
	_start_mode = "new"
	get_tree().paused = false
	get_tree().change_scene_to_file(MAIN)


## Starts chapter `n` fresh (chapter select): what earlier chapters grant is granted by its director.
func start_chapter(n: int) -> void:
	_start_mode = "chapter:%d" % n
	get_tree().paused = false
	get_tree().change_scene_to_file(MAIN)


func continue_game() -> void:
	_start_mode = "continue"
	get_tree().paused = false
	get_tree().change_scene_to_file(MAIN)


func quit_to_title() -> void:
	get_tree().paused = false
	AudioDirector.silence()
	get_tree().change_scene_to_file(TITLE)

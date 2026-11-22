extends Node

## Autoload `Game`: how Main.tscn was started, and moving between the title screen and the game.
## Main asks `take_start_mode()` once:
##   "explore"  - Explore mode (D45): the campus with basic mechanics, no story director. The default game.
##   "continue" - load the save (an explore save while the story is parked).
##   "new" / "chapter:N" - the parked story (Chapters 1-5), only reachable while STORY_ENABLED is true.
##   ""         - started directly (the editor, tests): the classic instant start, no story director.

const MAIN := "res://scenes/core/Main.tscn"
const TITLE := "res://scenes/core/MainMenu.tscn"
## The story (Chapters 1-5) is parked while the campus is rebuilt from the official board (D45). Its code and
## scenes are untouched; flip this to bring the chapters back to the title menu once they fit the new map.
const STORY_ENABLED := false

var _start_mode := ""
## True while a story director runs. Explore mode and the sandbox keep it false: doors ignore locks, powered lamps
## follow the time of day, sprinting never tires (D45).
var story_active := false


func take_start_mode() -> String:
	var m := _start_mode
	_start_mode = ""
	return m


## Explore the campus (D45): basic mechanics, starting at the Main Gate in daylight.
func explore() -> void:
	_start_mode = "explore"
	get_tree().paused = false
	get_tree().change_scene_to_file(MAIN)


func new_game() -> void:
	_start_mode = "new" if STORY_ENABLED else "explore"
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
	story_active = false
	AudioDirector.silence()
	get_tree().change_scene_to_file(TITLE)

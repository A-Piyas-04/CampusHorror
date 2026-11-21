class_name Readable
extends Node2D

## A note, logbook page, sign or scrawl the player can read (roadmap K4). Opens the note viewer (the world pauses),
## records the note in the journal and can set a story flag. `requires_light`: only readable while lit (lantern or a
## powered light): the "light reveals" channel (Docs/GAME_DESIGN.md section 3).

@export var note_id: String = ""
@export var title: String = ""
@export_multiline var body: String = ""
@export var verb: String = "Read"
@export var requires_light: bool = false
@export var dark_message: String = "Too dark to read. Light the lantern."
## Set to true in GameState the first time it is read ("" = none).
@export var sets_flag: String = ""

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	_interactable.verb = verb
	_interactable.object_name = title
	if note_id.is_empty():
		push_error("Readable %s has no note_id." % get_path())


func _on_interactable_interacted(_by: Node2D) -> void:
	if requires_light and not LightQuery.is_lit(get_tree(), global_position):
		var hud := get_tree().get_first_node_in_group("hud")
		if hud != null:
			hud.call("toast", dark_message)
		return
	var viewer := get_tree().get_first_node_in_group("note_viewer")
	if viewer != null:
		viewer.call("show_note", title, body)
	GameState.mark_note_read(note_id, title, body)
	if not sets_flag.is_empty():
		GameState.set_flag(sets_flag)

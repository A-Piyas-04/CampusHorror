class_name HideSpot
extends Node2D

## A place to hide (a locker, under the desk, behind the counter; Docs/GAME_DESIGN.md section 5 stealth verbs).
## Interact to get in: the player vanishes, the lantern goes out, hosts can't see or hear them. Interact (or move)
## to get out at `exit_offset`. A host that SAW the player get in (chasing, in line of sight, close) knows, and
## comes to drag them out.

signal entered
signal exited

@export var verb: String = "Hide"
@export var place_name: String = ""
## Where the player stands after getting out (local offset, game px).
@export var exit_offset: Vector2 = Vector2(0, 20)

var occupied := false
var _player: Player
var _lantern_state := 0
var _since := 0.0

@onready var _interactable: Interactable = $Interactable


func _ready() -> void:
	add_to_group("hide_spots")
	_interactable.verb = verb
	_interactable.object_name = place_name


func _on_interactable_interacted(by: Node2D) -> void:
	var player := by as Player
	if player == null or occupied:
		return
	_enter(player)


func _enter(player: Player) -> void:
	_player = player
	occupied = true
	_since = 0.0
	player.concealed = true
	player.input_enabled = false
	player.velocity = Vector2.ZERO
	var lantern := player.get_node_or_null("Lantern")
	if lantern != null:
		_lantern_state = int(lantern.get("state"))
		lantern.call("set_state", 0)
	(player.get_node("Sprite") as CanvasItem).visible = false
	(player.get_node("ContactShadow") as CanvasItem).visible = false
	_interactable.verb = "Get out"
	AudioDirector.play_at(&"door_open", global_position, -8.0, 1.3)
	entered.emit()


func leave() -> void:
	if not occupied or _player == null:
		return
	var player := _player
	occupied = false
	_player = null
	player.teleport(global_position + exit_offset)
	player.concealed = false
	player.input_enabled = true
	(player.get_node("Sprite") as CanvasItem).visible = true
	(player.get_node("ContactShadow") as CanvasItem).visible = true
	var lantern := player.get_node_or_null("Lantern")
	if lantern != null and _lantern_state != 0 and GameState.lantern_fuel > 0.0:
		lantern.call("set_state", _lantern_state)
	_interactable.verb = verb
	AudioDirector.play_at(&"door_open", global_position, -8.0, 1.1)
	exited.emit()


## Dragged out by a host (counts as being caught).
func force_out() -> void:
	leave()


func _process(delta: float) -> void:
	if occupied:
		_since += delta


func _unhandled_input(event: InputEvent) -> void:
	if not occupied or _since < 0.3:
		return
	if event.is_action_pressed("interact") or event.is_action_pressed("move_up") \
			or event.is_action_pressed("move_down") or event.is_action_pressed("move_left") \
			or event.is_action_pressed("move_right"):
		leave()
		get_viewport().set_input_as_handled()

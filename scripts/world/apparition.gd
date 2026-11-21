class_name Apparition
extends Node2D

## A one-time glimpse (foreshadowing, Docs/GAME_DESIGN.md section 2): the guard standing still far away under a
## failing lamp, before he is awake. Shown only until `done_flag` is set. It vanishes when the player comes within
## `vanish_distance`, after it has been on screen for `stare_seconds`, or the moment its lamp stutters off.

@export var done_flag: String = "apparition_gate"
@export var requires_missing_flag: String = "guard_awake"
@export var vanish_distance: float = 420.0
@export var stare_seconds: float = 2.6
@export var lamp_path: NodePath

var _seen := 0.0
var _shocked := false

@onready var _notifier: VisibleOnScreenNotifier2D = $Notifier


func _ready() -> void:
	if GameState.has_flag(done_flag) or GameState.has_flag(requires_missing_flag) or not GameState.has_flag("night"):
		queue_free()


func _process(delta: float) -> void:
	var player := get_tree().get_first_node_in_group("player") as Node2D
	if player == null:
		return
	var lamp := get_node_or_null(lamp_path) as PointLight2D
	if lamp != null and lamp.enabled and lamp.energy < 0.2 and _seen > 0.8:
		_vanish()
		return
	if _notifier.is_on_screen():
		_seen += delta
		if not _shocked and _seen > 0.5:
			_shocked = true
			var comp := get_tree().get_first_node_in_group("composure")
			if comp != null:
				comp.call("shock", 0.06, 2.0)
	if global_position.distance_to(player.global_position) < vanish_distance or _seen > stare_seconds:
		_vanish()


func _vanish() -> void:
	GameState.set_flag(done_flag)
	var t := create_tween()
	t.tween_property(self, "modulate:a", 0.0, 0.12)
	t.tween_callback(queue_free)

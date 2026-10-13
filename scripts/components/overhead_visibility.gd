class_name OverheadVisibility
extends Area2D

## Fades overhead visuals (a roof, a canopy) while the player stands on the floor they cover,
## so the player stays readable. Only the targets' modulate alpha changes: collision, light
## occluders and gameplay triggers are untouched. The area's shapes are the covered floor.
## Set collision_layer 0 and collision_mask to the Player's body layer.

## CanvasItems to fade, relative to this node.
@export var target_paths: Array[NodePath] = []
## Alpha of the targets while the player is inside.
@export_range(0.0, 1.0) var faded_alpha: float = 0.35
## Duration of a full fade; partial fades take proportionally less.
@export var fade_seconds: float = 0.25

var _targets: Array[CanvasItem] = []
var _rest_alpha: Array[float] = []
var _inside := 0
var _tween: Tween


func _ready() -> void:
	for path in target_paths:
		var item := get_node_or_null(path) as CanvasItem
		if item == null:
			push_error("OverheadVisibility %s: target %s is not a CanvasItem." % [get_path(), path])
			continue
		_targets.append(item)
		_rest_alpha.append(item.modulate.a)
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)


## True while the player is inside (the targets are faded or fading out).
func is_faded() -> bool:
	return _inside > 0


func _on_body_entered(body: Node2D) -> void:
	if body is Player:
		_inside += 1
		if _inside == 1:
			_fade(true)


func _on_body_exited(body: Node2D) -> void:
	if body is Player:
		_inside = maxi(_inside - 1, 0)
		if _inside == 0:
			_fade(false)


func _fade(faded: bool) -> void:
	if _tween != null:
		_tween.kill()
		_tween = null
	if _targets.is_empty():
		return
	_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	for i in _targets.size():
		var target := _targets[i]
		var to := _rest_alpha[i] * faded_alpha if faded else _rest_alpha[i]
		var seconds := fade_seconds * absf(target.modulate.a - to) / maxf(_rest_alpha[i] * (1.0 - faded_alpha), 0.001)
		_tween.tween_property(target, "modulate:a", to, seconds)

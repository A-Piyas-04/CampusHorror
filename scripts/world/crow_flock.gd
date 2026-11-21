class_name CrowFlock
extends Node2D

## A few crows on the ground (Docs/GAME_DESIGN.md section 5: the crows are spotters, not chasers). Walk close, or
## run anywhere near, and they burst up and away with a racket, and every host within earshot comes to look.
## Sneaking past slowly keeps them down.

const PERCHED := preload("res://scenes/props/horror/CrowPerched.tscn")
const WINGS_UP := preload("res://scenes/props/horror/CrowWingsUp.tscn")
const WINGS_DOWN := preload("res://scenes/props/horror/CrowWingsDown.tscn")

@export var count: int = 4
@export var spread: Vector2 = Vector2(70, 26)
@export var scare_radius: float = 90.0
@export var scare_radius_running: float = 230.0
## Hosts within this distance hear the flock go up.
@export var alert_radius: float = 900.0

var _crows: Array[Node2D] = []
var _flown := false
var _peck_t := 0.0
var _flap_t := 0.0
var _wings_up := true


func _ready() -> void:
	y_sort_enabled = true
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(str(get_path()))
	for i in count:
		var c := Node2D.new()
		c.name = "Crow%d" % i
		c.y_sort_enabled = true
		c.position = Vector2(rng.randf_range(-spread.x, spread.x), rng.randf_range(-spread.y, spread.y))
		for scene in [PERCHED, WINGS_UP, WINGS_DOWN]:
			var s := (scene as PackedScene).instantiate() as Node2D
			s.visible = scene == PERCHED
			c.add_child(s)
		c.scale.x = -1.0 if rng.randf() < 0.5 else 1.0
		add_child(c)
		_crows.append(c)


func _process(delta: float) -> void:
	if _flown:
		# Two-frame wing flap for every crow still in the air (frame-driven: nothing left pending if freed).
		_flap_t += delta
		if _flap_t >= 0.07:
			_flap_t = 0.0
			_wings_up = not _wings_up
			for c in _crows:
				if is_instance_valid(c):
					c.get_child(0).visible = false
					c.get_child(1).visible = _wings_up
					c.get_child(2).visible = not _wings_up
		return
	_peck_t += delta
	# Small idle hops.
	for i in _crows.size():
		var c := _crows[i]
		if fmod(_peck_t + i * 0.7, 3.1) < delta:
			c.scale.x = -c.scale.x
	var player := get_tree().get_first_node_in_group("player") as Player
	if player == null or player.concealed:
		return
	var d := global_position.distance_to(player.global_position)
	var running := player.mode == &"sprint"
	if d < scare_radius or (running and d < scare_radius_running) or (player.mode == &"walk" and d < scare_radius * 1.4):
		scatter()


func scatter() -> void:
	if _flown:
		return
	_flown = true
	AudioDirector.play_at(&"crow_flap", global_position, 2.0)
	for g in get_tree().get_nodes_in_group("creatures"):
		var guard := g as NightGuard
		if guard != null and guard.active and guard.global_position.distance_to(global_position) < alert_radius:
			guard.awareness = maxf(guard.awareness, 0.6)
			guard._last_known = global_position
	var rng := RandomNumberGenerator.new()
	for c in _crows:
		var dir := Vector2(rng.randf_range(-1.0, 1.0), rng.randf_range(-1.6, -0.6)).normalized()
		c.scale.x = -1.0 if dir.x < 0.0 else 1.0
		var t := create_tween()
		t.tween_interval(rng.randf_range(0.0, 0.25))
		t.tween_property(c, "position", c.position + dir * rng.randf_range(500.0, 800.0), 2.6).set_ease(Tween.EASE_IN)
		t.parallel().tween_property(c, "modulate:a", 0.0, 2.6).set_ease(Tween.EASE_IN)
		t.tween_callback(c.queue_free)

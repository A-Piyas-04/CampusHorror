extends Zone

## The CDS indoor games hall (Chapter 1 finale). When the power comes back (flag power_on) the floor hatch by the
## court unlocks and swings open: the closed plate is swapped for the open one, a cold green light rises from the
## shaft, the organism's glow trail leads into it, and "Climb down" becomes available (it ends the chapter).

@export var hatch_closed_path: NodePath = ^"Objects/FloorHatchClosed"
@export var hatch_open_path: NodePath = ^"Objects/FloorHatchOpen"
@export var hatch_light_path: NodePath = ^"Objects/HatchLight"
@export var hatch_glow_path: NodePath = ^"Objects/HatchGlow"
@export var climb_path: NodePath = ^"Objects/ClimbDown"

var hatch_position: Vector2:
	get:
		var n := get_node_or_null(hatch_closed_path) as Node2D
		return n.global_position if n != null else global_position


func _ready() -> void:
	super._ready()
	_set_open(GameState.has_flag("hatch_open"), true)


func open_hatch() -> void:
	GameState.set_flag("hatch_open")
	_set_open(true, false)


func _set_open(open: bool, instant: bool) -> void:
	var closed := get_node_or_null(hatch_closed_path) as CanvasItem
	var opened := get_node_or_null(hatch_open_path) as CanvasItem
	var light := get_node_or_null(hatch_light_path) as PointLight2D
	var glow := get_node_or_null(hatch_glow_path) as CanvasItem
	var climb := get_node_or_null(climb_path) as Node2D
	if closed != null:
		closed.visible = not open
	if opened != null:
		opened.visible = open
	if glow != null:
		glow.visible = open
	if climb != null:
		climb.visible = open
		var it := climb.get_node_or_null("Interactable") as Area2D
		if it != null:
			it.monitorable = open
	if light != null:
		light.enabled = open
		if open and not instant:
			var e := light.energy
			light.energy = 0.0
			create_tween().tween_property(light, "energy", e, 2.5)

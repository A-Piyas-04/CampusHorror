class_name GlowMark
extends Node2D

## Bioluminescence (Docs/GAME_DESIGN.md section 2: light HIDES): the organism's faint glow, visible only in the dark
## and washed out under a lantern or a lamp. Drawn by Main's GlowLayer (its own canvas layer, so the night tint
## doesn't swallow it); this node only describes the mark.
##
## Shapes: `spots` (soft blobs around this node), `trail_to` (a dotted trail of blobs to a point) and `writing`
## (letters scrawled in glowing growth). A GlowMark with `note_id` can also be "read" in the dark: it adds the
## writing to the journal (so nobody has to memorise a code).

@export var color: Color = Color(0.45, 1.0, 0.82)
@export_range(0.0, 2.0, 0.05) var intensity: float = 0.9
## Soft blobs: x, y = offset (game px), z = radius (game px).
@export var spots: PackedVector3Array = PackedVector3Array()
## If set (non-zero), a trail of small blobs from this node to `trail_to` (local offset, game px).
@export var trail_to: Vector2 = Vector2.ZERO
@export var trail_spacing: float = 22.0
## Glowing letters (e.g. a code scrawled on a wall).
@export var writing: String = ""
@export var writing_size: int = 26
## Where the writing is drawn relative to this node (e.g. up the wall: negative y).
@export var writing_offset: Vector2 = Vector2.ZERO
## Optional: the writing can be read (journal entry) while it is dark here.
@export var note_id: String = ""
@export var note_title: String = ""
@export_multiline var note_body: String = ""
@export var pulse_speed: float = 0.6

## 0..1, how visible right now (0 under light). Updated by the GlowLayer each frame.
var visibility := 0.0
var _seed := 0


func _ready() -> void:
	add_to_group("glow_marks")
	_seed = hash(str(get_path()))
	if not note_id.is_empty():
		var it := Interactable.new()
		it.verb = "Read"
		it.object_name = note_title if not note_title.is_empty() else "The marks"
		it.collision_layer = 4
		it.collision_mask = 0
		var shape := CollisionShape2D.new()
		var circle := CircleShape2D.new()
		circle.radius = 26.0
		shape.shape = circle
		it.add_child(shape)
		it.interacted.connect(_on_read)
		add_child(it)


func _on_read(_by: Node2D) -> void:
	if visibility < 0.25:
		var hud := get_tree().get_first_node_in_group("hud")
		if hud != null:
			hud.call("toast", "Something is scratched here. In this light you can't make it out.")
		return
	var viewer := get_tree().get_first_node_in_group("note_viewer")
	if viewer != null:
		viewer.call("show_note", note_title, note_body)
	GameState.mark_note_read(note_id, note_title, note_body)


func seed_value() -> int:
	return _seed

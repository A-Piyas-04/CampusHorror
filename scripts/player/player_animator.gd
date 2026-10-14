extends AnimatedSprite2D
## Plays the player's directional idle / walk animations from the parent Player's velocity.
## Visual only: it never changes movement, collision, input or the camera.
## Diagonals use the dominant axis; an exact diagonal keeps the current facing when it is one of its two
## directions (no flicker), otherwise it turns horizontally. The facing persists when the player stops.

## Below this speed (px/s, after move_and_slide) the player idles.
const WALK_THRESHOLD := 5.0

var facing := "down"

@onready var _body := get_parent() as CharacterBody2D


func _ready() -> void:
	play("idle_down")


func _physics_process(_delta: float) -> void:
	var v := _body.velocity
	var moving := v.length() > WALK_THRESHOLD
	if moving:
		facing = _facing_for(v)
	var anim := StringName(("walk_" if moving else "idle_") + facing)
	if animation == anim:
		return
	var turning := moving and String(animation).begins_with("walk_")
	var keep_frame := frame
	var keep_progress := frame_progress
	play(anim)
	if turning:
		set_frame_and_progress(keep_frame, keep_progress)


func _facing_for(v: Vector2) -> String:
	var horizontal := "right" if v.x > 0.0 else "left"
	var vertical := "down" if v.y > 0.0 else "up"
	if absf(absf(v.x) - absf(v.y)) <= 0.01 * v.length():
		return facing if facing == horizontal or facing == vertical else horizontal
	return horizontal if absf(v.x) > absf(v.y) else vertical

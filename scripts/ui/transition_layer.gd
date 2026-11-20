class_name TransitionLayer
extends CanvasLayer

## Full-screen fade used by Main's zone travel (roadmap I5). Drawn above all UI (layer 50), never blocks
## the mouse, unaffected by the world's night tint (CanvasModulate only tints the world canvas).

var _tween: Tween

@onready var _fade: ColorRect = $Fade


## Eases the black overlay's opacity to `alpha` (0 = clear, 1 = fully black) and returns when done.
func fade_to(alpha: float, seconds: float) -> void:
	if _tween != null:
		_tween.kill()
	if seconds <= 0.0:
		_fade.modulate.a = alpha
		return
	_tween = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_tween.tween_property(_fade, "modulate:a", alpha, seconds)
	await _tween.finished


## Current opacity of the overlay (1 = the screen is fully black).
func get_alpha() -> float:
	return _fade.modulate.a

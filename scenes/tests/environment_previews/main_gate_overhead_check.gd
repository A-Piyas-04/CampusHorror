extends Node2D
## TEMPORARY Milestone G Batch 3A check of the Main Gate overhead visibility (test-only).
## Instances scenes/world/MainGateExterior.tscn plus the real scenes/player/Player.tscn and verifies, through the
## generated OverheadVisibility areas (Tower/RoofFade, Pavilion/RoomRoofFade, Pavilion/CanopyFade):
## - Each covered area fades only its own layer (to 0.35) and restores it (1.0) when the player leaves;
##   the passage, the approach and the spawn fade nothing; no other CanvasItem in the zone changes modulate.
## - Walking across a fade boundary toggles once and the alpha moves smoothly (no per-frame jump); jittering on
##   the boundary never snaps.
## - The fade areas never block the player (a walk through the tower's fade area down the passage is free).
## The porch under the pavilion canopy is outside the playable area (road side, behind the gate leaves); it is
## reached by teleport only, to test the canopy layer.
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail).

const ZONE_SCENE := "res://scenes/world/MainGateExterior.tscn"
const PLAYER_SCENE := "res://scenes/player/Player.tscn"
const GATE := "Objects/Buildings/MainGateLandmark"
const LAYERS := ["Tower/Roof", "Pavilion/RoomRoof", "Pavilion/Canopy"]
const FADED := 0.35
const EPS := 0.01
## name -> [feet position (world), faded layers]
const CASES := [
	["spawn (campus side)", Vector2(-1390, 960), []],
	["approach from the campus, just north of the roof", Vector2(-1390, 1010), []],
	["behind the tower (centre)", Vector2(-1390, 1200), ["Tower/Roof"]],
	["behind the tower, against its back wall", Vector2(-1450, 1265), ["Tower/Roof"]],
	["behind the tower's east overhang", Vector2(-1215, 1150), ["Tower/Roof"]],
	["in the passage", Vector2(-1390, 1340), []],
	["at the gate leaves", Vector2(-1390, 1388), []],
	["behind the pavilion room", Vector2(-1690, 1240), ["Pavilion/RoomRoof"]],
	["behind the tower / pavilion junction", Vector2(-1595, 1240), ["Tower/Roof", "Pavilion/RoomRoof"]],
	["under the pavilion canopy (porch, teleport only)", Vector2(-1650, 1415), ["Pavilion/Canopy"]],
	["back at the spawn", Vector2(-1390, 960), []],
]

var _zone: Node2D
var _gate: Node2D
var _player: CharacterBody2D
var _failures := 0
var _checks := 0


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[OVERHEAD] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	_zone = (load(ZONE_SCENE) as PackedScene).instantiate() as Node2D
	add_child(_zone)
	_player = (load(PLAYER_SCENE) as PackedScene).instantiate() as CharacterBody2D
	add_child(_player)
	_gate = _zone.get_node(GATE) as Node2D
	await get_tree().physics_frame
	await get_tree().physics_frame
	await _run_checks()
	print("[OVERHEAD] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _run_checks() -> void:
	for spec: Array in CASES:
		_player.call("teleport", spec[1])
		await _settle()
		var faded: Array = spec[2]
		var states := []
		var ok := true
		for path: String in LAYERS:
			var a := _alpha(path)
			states.append("%s %.2f" % [path.get_file(), a])
			ok = ok and absf(a - (FADED if faded.has(path) else 1.0)) < EPS
		var others := _changed_others()
		_check(ok and others.is_empty(), "%s %s: faded %s (%s); other items changed %s" % [spec[0], spec[1], faded, ", ".join(states), others])
	await _check_walk_across()
	await _check_jitter()
	_check_not_blocking()


## Walk south 1 px per physics frame across the north edge of Tower/RoofFade (world y 1024.4) and back.
func _check_walk_across() -> void:
	_player.call("teleport", Vector2(-1390, 1000))
	await _settle()
	var toggles := 0
	var was := _alpha("Tower/Roof") < 1.0 - EPS
	var max_step := 0.0
	var last := _alpha("Tower/Roof")
	var y := 1000.0
	while y <= 1060.0:
		_player.global_position = Vector2(-1390, y)
		await get_tree().physics_frame
		var a := _alpha("Tower/Roof")
		max_step = maxf(max_step, absf(a - last))
		last = a
		var now := bool(_gate.get_node("Tower/RoofFade").call("is_faded"))
		toggles += 1 if now != was else 0
		was = now
		y += 1.0
	await _settle()
	var faded_after := _alpha("Tower/Roof")
	while y >= 1000.0:
		_player.global_position = Vector2(-1390, y)
		await get_tree().physics_frame
		var a := _alpha("Tower/Roof")
		max_step = maxf(max_step, absf(a - last))
		last = a
		var now := bool(_gate.get_node("Tower/RoofFade").call("is_faded"))
		toggles += 1 if now != was else 0
		was = now
		y -= 1.0
	await _settle()
	_check(toggles == 2 and absf(faded_after - FADED) < EPS and absf(_alpha("Tower/Roof") - 1.0) < EPS and max_step < 0.1,
		"walking across the roof's fade edge and back: %d state changes (expected 2), faded %.2f inside, %.2f after leaving, max alpha step per physics frame %.3f (< 0.1, no snap)"
		% [toggles, faded_after, _alpha("Tower/Roof"), max_step])


## Oscillate +-2 px around the fade edge for 40 physics frames: the alpha may drift but must never jump.
func _check_jitter() -> void:
	var edge := 1024.4
	var max_step := 0.0
	var last := _alpha("Tower/Roof")
	for i in 40:
		_player.global_position = Vector2(-1390, edge + (2.0 if i % 2 == 0 else -2.0))
		await get_tree().physics_frame
		var a := _alpha("Tower/Roof")
		max_step = maxf(max_step, absf(a - last))
		last = a
	_player.call("teleport", Vector2(-1390, 960))
	await _settle()
	_check(max_step < 0.1 and absf(_alpha("Tower/Roof") - 1.0) < EPS,
		"jittering +-2 px on the fade edge: max alpha step %.3f per physics frame (< 0.1), restored to %.2f after leaving" % [max_step, _alpha("Tower/Roof")])


func _check_not_blocking() -> void:
	_player.global_position = Vector2(-1390, 1000)
	var blocked := _player.test_move(_player.global_transform, Vector2(0, 360))
	_check(not blocked, "the fade areas never block: walking from y 1000 through the roof's fade area down the passage to y 1360 is free")


func _settle() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	await get_tree().create_timer(0.45).timeout


func _alpha(path: String) -> float:
	return (_gate.get_node(path) as CanvasItem).modulate.a


## CanvasItems in the zone (other than the three layers) whose modulate is not white.
func _changed_others() -> Array:
	var out := []
	var layers := []
	for path: String in LAYERS:
		layers.append(_gate.get_node(path))
	for node in _zone.find_children("*", "CanvasItem", true, false):
		if not layers.has(node) and (node as CanvasItem).modulate != Color.WHITE:
			out.append(String(_zone.get_path_to(node)))
	return out

extends Node
## Test-only check for the Blender-rendered player character in the real scenes/player/Player.tscn, run inside the
## real scenes/core/Main.tscn (as the current scene) and driven through the real move_* input actions:
## - the source .blend, generator record and sprite sheet exist and the record's own render checks are clean;
## - Player.tscn shows the AnimatedSprite2D character (no blue Body / FeetMarker placeholder) with the physics
##   footprint, interaction range, speed, layers and lantern unchanged;
## - the SpriteFrames has exactly the 8 directional idle / walk animations, 8 looping frames each, all textures valid;
## - the opaque feet sit on the Player origin (CharacterBody2D feet) in every frame and the figure is ~1.8 m tall;
## - real input maps to walk_<dir>, diagonals use the dominant axis / keep facing, facing persists as idle_<dir>,
##   movement speed and diagonal normalization are unchanged and the walk cycle advances;
## - Y-sort, lantern light mask and the one persistent Player across a CDS zone round trip.
## Never saves; the user's save file is only hashed before and after to prove it is untouched.
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail).

const MAIN_SCENE := "res://scenes/core/Main.tscn"
const PLAYER_SCENE := "res://scenes/player/Player.tscn"
const FRAMES_PATH := "res://scenes/player/player_character_frames.tres"
const SHEET_PATH := "res://assets/sprites/characters/player_character_sheet.png"
const BLEND_PATH := "res://assets/source/blender/characters/player_character.blend"
const RECORD_PATH := "res://assets/source/blender/characters/player_character.render.json"
const SAVE_PATH := "user://save.json"
const DIRS := ["down", "up", "left", "right"]
const DIR_VECTORS := {"down": Vector2.DOWN, "up": Vector2.UP, "left": Vector2.LEFT, "right": Vector2.RIGHT}
## Central field (Docs/CAMPUS_MAP.md), open in every direction for the short test walks.
const OPEN_SPOT := Vector2(0, -50)
const EXPECTED_CHECKS := 18

var _failures := 0
var _checks := 0


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[CHARACTER] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	_start.call_deferred()


func _start() -> void:
	var save_hash := _save_hash()
	_static_checks()
	var main := (load(MAIN_SCENE) as PackedScene).instantiate()
	get_tree().root.add_child(main)
	get_tree().current_scene = main
	await _frames(10)
	await _runtime_checks(main as Main)
	_check(_save_hash() == save_hash, "the user's save file is untouched (%s)" % ("absent" if save_hash.is_empty() else save_hash.left(16)))
	_check(_checks == EXPECTED_CHECKS, "all %d checks ran (%d)" % [EXPECTED_CHECKS, _checks])
	print("[CHARACTER] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _static_checks() -> void:
	var record = JSON.parse_string(FileAccess.get_file_as_string(RECORD_PATH)) if FileAccess.file_exists(RECORD_PATH) else null
	var sheet := load(SHEET_PATH) as Texture2D
	var record_ok := record is Dictionary
	var max_low := 0.0
	if record_ok:
		for v in (record.lowest_shoe_z_per_frame_m as Dictionary).values():
			max_low = maxf(max_low, absf(float(v)))
	_check(FileAccess.file_exists(BLEND_PATH) and record_ok and sheet != null
		and sheet.get_size() == Vector2(record.sheet_px[0], record.sheet_px[1])
		and int(record.body_vertices_without_weights) == 0 and float(record.max_cell_border_alpha) == 0.0 and max_low <= 0.002,
		"source .blend, record and sheet %s exist; record: 0 unweighted vertices, clean cell borders, shoes on z = 0 (max %.4f m)"
			% [sheet.get_size() if sheet else "missing", max_low])

	var player := (load(PLAYER_SCENE) as PackedScene).instantiate() as CharacterBody2D
	var sprite := player.get_node_or_null("Sprite") as AnimatedSprite2D
	_check(sprite != null and sprite.sprite_frames != null and sprite.sprite_frames.resource_path == FRAMES_PATH
		and not player.has_node("Body") and not player.has_node("FeetMarker") and _visible_polygons(player) == 0,
		"Player.tscn shows the AnimatedSprite2D character from %s; no blue Body / FeetMarker placeholder left" % FRAMES_PATH)
	var shape := player.get_node("Collision").shape as RectangleShape2D
	var reach := player.get_node("InteractionArea/Collision").shape as CircleShape2D
	_check(shape != null and shape.size == Vector2(28, 12) and player.get_node("Collision").position == Vector2(0, -6)
		and player.collision_layer == 2 and player.collision_mask == 1 and player.motion_mode == CharacterBody2D.MOTION_MODE_FLOATING
		and float(player.get("move_speed")) == 200.0 and reach != null and reach.radius == 24.0
		and player.get_node("InteractionArea/Collision").position == Vector2(0, -6),
		"physics unchanged: 28x12 footprint at (0, -6), layer 2 / mask 1, floating, move_speed 200, interaction radius 24")

	var frames := sprite.sprite_frames if sprite else null
	var names: Array = Array(frames.get_animation_names()) if frames else []
	names.sort()
	var want: Array = []
	for kind in ["idle", "walk"]:
		for d in DIRS:
			want.append(kind + "_" + d)
	want.sort()
	var anim_problems: Array[String] = []
	for anim: String in want:
		if frames == null or not frames.has_animation(anim):
			anim_problems.append(anim + " missing")
			continue
		var speed := 3.0 if anim.begins_with("idle") else 12.0
		if frames.get_frame_count(anim) != 8 or not frames.get_animation_loop(anim) or frames.get_animation_speed(anim) != speed:
			anim_problems.append("%s: %d frames loop %s speed %s" % [anim, frames.get_frame_count(anim), frames.get_animation_loop(anim), frames.get_animation_speed(anim)])
		for i in frames.get_frame_count(anim):
			var tex := frames.get_frame_texture(anim, i) as AtlasTexture
			if tex == null or tex.atlas == null or tex.atlas.resource_path != SHEET_PATH or tex.region.size != Vector2(128, 230):
				anim_problems.append("%s[%d] bad texture" % [anim, i])
	_check(names == want and anim_problems.is_empty(),
		"exactly the 8 animations idle/walk x down/up/left/right; 8 looping frames each (idle 3 fps, walk 12 fps), all 128x230 atlas frames valid %s" % [anim_problems])

	# Feet anchoring: the lowest opaque pixel of every frame, in Player space (origin = CharacterBody2D feet).
	var lows: Array[float] = []
	var heights: Array[float] = []
	var centres: Array[float] = []
	var sheet_img := Image.load_from_file(ProjectSettings.globalize_path(SHEET_PATH))
	if frames and anim_problems.is_empty() and sheet_img != null:
		for anim: String in want:
			for i in 8:
				var img := sheet_img.get_region(Rect2i((frames.get_frame_texture(anim, i) as AtlasTexture).region))
				var used := img.get_used_rect()
				lows.append((used.end.y + sprite.offset.y) * sprite.scale.y)
				heights.append(used.size.y * sprite.scale.y)
				if anim.ends_with("down") or anim.ends_with("up"):
					centres.append((used.get_center().x + sprite.offset.x) * sprite.scale.x)
	# Rows 0-31 are idle frames, 32-63 walk frames (want is sorted: idle_* before walk_*).
	var idle_lows := lows.slice(0, 32)
	var walk_lows := lows.slice(32)
	var ranges := {}
	for k in want.size():
		var part := lows.slice(k * 8, k * 8 + 8)
		if part:
			ranges[want[k]] = "%.1f..%.1f" % [part.min(), part.max()]
	_check(sprite != null and not sprite.centered and sprite.offset == Vector2(-64, -183) and is_equal_approx(sprite.scale.x, 1.0 / 3.0)
		and lows.size() == 64 and idle_lows.min() >= -0.5 and idle_lows.max() <= 3.0
		and walk_lows.min() >= -3.0 and walk_lows.max() <= 9.0,
		"feet anchored: offset (-64, -183), scale 1/3; lowest opaque pixel vs the Player origin, px (idle: soles on the origin; walk: a stepping foot up to ~0.35 m nearer / farther projects up to ~7 px lower / higher): %s" % [ranges])
	var idle_heights := heights.slice(0, 32)
	var c_abs := 0.0
	for c in centres:
		c_abs = maxf(c_abs, absf(c))
	_check(heights.size() == 64 and idle_heights.min() >= 40.0 and idle_heights.max() <= 48.0 and heights.max() <= 54.0 and c_abs <= 3.0,
		"figure scale: idle opaque height %.1f .. %.1f px (1.8 m at 32 px/m x cos 40 deg + feet depth ~ 44-46 px), walk up to %.1f px (stride depth); front/back views centred on the origin (max %.2f px off)"
			% [idle_heights.min(), idle_heights.max(), heights.max(), c_abs])
	_check(sprite != null and sprite.light_mask == 2 and sprite.texture_filter == CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
		and sprite.z_index == 0 and sprite.z_as_relative and player.z_index == 0
		and ((player.get_node("Lantern") as PointLight2D).range_item_cull_mask & sprite.light_mask) != 0,
		"Sprite uses the upright-sprite conventions (light_mask 2, linear+mipmaps, z 0) and is lit by the Lantern")
	player.free()


func _runtime_checks(main: Main) -> void:
	var players := get_tree().root.find_children("*", "CharacterBody2D", true, false).filter(func(n): return n is Player)
	_check(main != null and players.size() == 1 and players[0] == main.get_node("World/Player")
		and main.get_current_zone_id() == "main_gate_exterior",
		"real Main.tscn is running main_gate_exterior with exactly one Player (World/Player) (%d found)" % players.size())
	if main == null:
		return
	var player := main.get_node("World/Player") as Player
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	var world := main.get_node("World") as Node2D
	_check(world.y_sort_enabled and player.get_parent() == world and sprite.is_visible_in_tree() and sprite.animation == &"idle_down"
		and sprite.is_playing(),
		"Player is Y-sorted directly under World (origin = feet), the character is visible and starts playing idle_down")

	# Every direction through the real input actions.
	var mapping: Array[String] = []
	var speed_ok := true
	var persist_ok := true
	for d: String in DIRS:
		player.teleport(OPEN_SPOT)
		await _frames(2)
		var start := player.global_position
		Input.action_press("move_" + d)
		for i in 12:
			await get_tree().physics_frame
		var walking := String(sprite.animation)
		var v := player.velocity
		Input.action_release("move_" + d)
		await _frames(3)
		var moved := player.global_position - start
		mapping.append("%s->%s" % [d, walking])
		if walking != "walk_" + d:
			mapping.append("WRONG")
		speed_ok = speed_ok and v.is_equal_approx(DIR_VECTORS[d] * 200.0) and moved.normalized().is_equal_approx(DIR_VECTORS[d]) \
			and absf(moved.length() - 200.0 * 12.0 / 60.0) <= 200.0 / 60.0 + 0.5
		persist_ok = persist_ok and sprite.animation == StringName("idle_" + d) and player.velocity == Vector2.ZERO
	_check(not mapping.has("WRONG"), "move actions play the matching walk animation: %s" % ", ".join(mapping))
	_check(persist_ok, "after releasing, the player keeps facing that way (idle_<dir>) and stops")
	_check(speed_ok, "movement unchanged: 200 px/s along each axis (40 px in 12 physics frames, +-1 frame)")

	# Diagonals: an exact diagonal keeps the current facing if it is one of its two directions, else turns horizontal.
	player.teleport(OPEN_SPOT)
	await _hold(["move_up"], 3)
	Input.action_press("move_right")
	Input.action_press("move_down")
	for i in 6:
		await get_tree().physics_frame
	var from_up := String(sprite.animation)
	var diag_v := player.velocity
	Input.action_release("move_right")
	Input.action_release("move_down")
	await _frames(2)
	player.teleport(OPEN_SPOT)
	await _hold(["move_down"], 3)
	await _hold(["move_left", "move_down"], 6)
	var keep_down := String(sprite.animation)
	_check(from_up == "walk_right" and keep_down == "idle_down" and is_equal_approx(diag_v.length(), 200.0),
		"exact diagonal: facing up + right/down turns to walk_right; facing down + left/down keeps facing down (%s, %s); diagonal speed stays 200 (%.1f)"
			% [from_up, keep_down, diag_v.length()])
	var animator := sprite
	var dominant: Array[String] = []
	for v: Vector2 in [Vector2(200, 60), Vector2(-60, -200), Vector2(-150, 100), Vector2(30, 199)]:
		dominant.append(String(animator.call("_facing_for", v)))
	_check(dominant == ["right", "up", "left", "down"], "analog diagonals use the dominant axis: %s" % [dominant])

	# The walk cycle advances and loops; idle animates too (breathing).
	player.teleport(OPEN_SPOT)
	Input.action_press("move_left")
	var seen := {}
	for i in 50:
		await get_tree().physics_frame
		seen[sprite.frame] = true
	Input.action_release("move_left")
	await _frames(2)
	var idle_seen := {}
	for i in 200:
		await get_tree().process_frame
		idle_seen[sprite.frame] = true
	_check(seen.size() == 8 and idle_seen.size() >= 3 and sprite.animation == &"idle_left",
		"holding a move action cycles all 8 walk frames (%d seen); idle keeps animating (%d frames seen) facing left" % [seen.size(), idle_seen.size()])

	# One persistent Player through a CDS zone round trip (via Main.change_zone, the path doors use).
	var id_before := player.get_instance_id()
	main.change_zone("cds_veranda", "inside_cds_entry")
	await _frames(4)
	var in_cds := main.get_current_zone_id() == "cds_veranda" and is_instance_valid(player) and player.get_instance_id() == id_before
	main.change_zone("main_gate_exterior", "outside_cds_entrance")
	await _frames(4)
	var players_after := get_tree().root.find_children("*", "CharacterBody2D", true, false).filter(func(n): return n is Player)
	_check(in_cds and main.get_current_zone_id() == "main_gate_exterior" and players_after.size() == 1
		and players_after[0].get_instance_id() == id_before and sprite.is_visible_in_tree() and sprite.animation == &"idle_left",
		"the same Player instance (and its character sprite and facing) persists through cds_veranda and back; still exactly one Player")

	# Night tint and lantern still apply to the character.
	var tint := main.get_node("DayNightTint") as CanvasModulate
	var lantern := player.get_node("Lantern") as PointLight2D
	var lantern_before := lantern.enabled
	await _press("debug_toggle_night")
	var night: bool = tint.color == tint.get("night_color")
	await _press("lantern")
	var toggled := lantern.enabled != lantern_before
	await _press("lantern")
	await _press("debug_toggle_night")
	_check(night and toggled and lantern.enabled == lantern_before and tint.color == tint.get("day_color"),
		"night tint and lantern toggle still work with the character (restored to day / lantern %s)" % ("on" if lantern_before else "off"))


func _visible_polygons(node: Node) -> int:
	var count := 0
	for child in node.get_children():
		if child is Polygon2D and child.visible:
			count += 1
	return count


func _save_hash() -> String:
	if not FileAccess.file_exists(SAVE_PATH):
		return ""
	return FileAccess.get_sha256(SAVE_PATH)


func _hold(actions: Array, frames: int) -> void:
	for a: String in actions:
		Input.action_press(a)
	for i in frames:
		await get_tree().physics_frame
	for a: String in actions:
		Input.action_release(a)
	await _frames(2)


func _press(action: String) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	await _frames(2)
	ev = InputEventAction.new()
	ev.action = action
	ev.pressed = false
	Input.parse_input_event(ev)
	await _frames(8)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame
	await get_tree().process_frame

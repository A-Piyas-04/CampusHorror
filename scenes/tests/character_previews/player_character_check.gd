extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I (I2) check of the Blender-rendered player character in the real Player.tscn, run inside the real
## Main.tscn through the real input actions:
## - assets: the four cycle sheets (idle / walk / run / sneak, 8 facings each), the record's own render checks
##   (0 unweighted vertices, clean cell borders, shoes on z = 0) and the 32 looping animations;
## - measured cycles: every moving cycle's ground speed (metadata `cycles`) equals the Player's speed for that
##   gait, and it has exactly two heel strikes; the fps of each animation equals the measured fps;
## - feet anchoring and figure scale on all 288 frames (lowest opaque pixel vs the Player origin);
## - Player.tscn conventions (footprint, layers, interaction radius, sprite scale / offset / light mask);
## - all 8 movement directions face correctly from real input, facing persists when stopping, the facing has
##   hysteresis (no flicker at a sector edge), gaits pick run / sneak cycles, a turn keeps the cycle's phase,
##   footsteps fire only on heel-strike frames, and the one Player survives a faded trip.
## Never saves. Args (after `--`): `--quit-after-checks` quits with exit code 0 / 1.

const PLAYER_SCENE := "res://scenes/player/Player.tscn"
const FRAMES_PATH := "res://scenes/player/player_character_frames.tres"
const SHEET_PATH := "res://assets/sprites/characters/player_character_%s.png"
const BLEND_PATH := "res://assets/source/blender/characters/player_character.blend"
const RECORD_PATH := "res://assets/source/blender/characters/player_character.render.json"
const SETS := {"idle": 8, "walk": 8, "run": 8, "sneak": 12}
const FACINGS := ["down", "down_left", "left", "up_left", "up", "up_right", "right", "down_right"]
const OPEN_SPOT := Vector2(-1000, -200)
## Input actions for each 8-way facing.
const DIR_ACTIONS := {"right": ["move_right"], "down_right": ["move_right", "move_down"], "down": ["move_down"],
	"down_left": ["move_left", "move_down"], "left": ["move_left"], "up_left": ["move_left", "move_up"],
	"up": ["move_up"], "up_right": ["move_right", "move_up"]}


func _run() -> void:
	tag = "CHARACTER"
	_assets()
	_player_scene()
	await _directions()
	_hysteresis()
	await _gaits_and_phase()
	await _footstep_frames()
	await _persistence()


func _assets() -> void:
	var record = JSON.parse_string(FileAccess.get_file_as_string(RECORD_PATH)) if FileAccess.file_exists(RECORD_PATH) else null
	var ok: bool = record is Dictionary and FileAccess.file_exists(BLEND_PATH)
	var max_low := 0.0
	var sheets_ok := true
	if ok:
		for v in (record.lowest_shoe_z_per_frame_m as Dictionary).values():
			max_low = maxf(max_low, absf(float(v)))
		for s: String in SETS:
			var tex := load(SHEET_PATH % s) as Texture2D
			var px: Array = record.sheets[s].px
			sheets_ok = sheets_ok and tex != null and tex.get_size() == Vector2(px[0], px[1]) \
				and tex.get_size() == Vector2(SETS[s] * 128, 8 * 230)
	check(ok and sheets_ok and int(record.body_vertices_without_weights) == 0 and float(record.max_cell_border_alpha) == 0.0 and max_low <= 0.002,
		"source .blend, record and the 4 cycle sheets exist (8 facings x frames, 128 x 230 cells); 0 unweighted vertices, clean borders, shoes on z = 0 (max %.4f m)" % max_low)
	var frames := load(FRAMES_PATH) as SpriteFrames
	var cycles: Dictionary = frames.get_meta("cycles", {})
	var problems := []
	for s: String in SETS:
		for f: String in FACINGS:
			var anim := StringName("%s_%s" % [s, f])
			if not frames.has_animation(anim):
				problems.append("missing %s" % anim)
				continue
			var c: Dictionary = cycles.get(s, {})
			if frames.get_frame_count(anim) != SETS[s] or not frames.get_animation_loop(anim) \
					or not approx(frames.get_animation_speed(anim), float(c.get("fps", -1.0)), 0.001):
				problems.append("%s: %d frames, loop %s, %.3f fps" % [anim, frames.get_frame_count(anim), frames.get_animation_loop(anim), frames.get_animation_speed(anim)])
	check(frames.get_animation_names().size() == 32 and problems.is_empty(),
		"32 looping animations (idle / walk / run / sneak x 8 facings), each at its cycle's measured fps (problems %s)" % [problems])
	var player_proto := (load(PLAYER_SCENE) as PackedScene).instantiate() as Player
	var speeds := {"walk": player_proto.walk_speed, "run": player_proto.sprint_speed, "sneak": player_proto.sneak_speed}
	player_proto.free()
	var cyc_bad := []
	for g: String in speeds:
		var c: Dictionary = cycles.get(g, {})
		if not approx(float(c.get("speed_px_s", -1.0)), speeds[g], 0.5) or (c.get("contact_frames", []) as Array).size() != 2:
			cyc_bad.append("%s %s" % [g, c])
	check(cyc_bad.is_empty(), "each moving cycle was measured at its gait's speed (walk 62, run 154, sneak 32 px/s) with two heel strikes: %s" % [cyc_bad if not cyc_bad.is_empty() else cycles])
	# Feet anchoring and scale on every frame.
	var lows := {"idle": [], "moving": []}
	var heights := {"idle": [], "moving": []}
	for s: String in SETS:
		var img := Image.load_from_file(ProjectSettings.globalize_path(SHEET_PATH % s))
		for f: String in FACINGS:
			var anim := StringName("%s_%s" % [s, f])
			for i in SETS[s]:
				var used := img.get_region(Rect2i((frames.get_frame_texture(anim, i) as AtlasTexture).region)).get_used_rect()
				var k := "idle" if s == "idle" else "moving"
				lows[k].append((used.end.y - 183) / 3.0)
				heights[k].append(used.size.y / 3.0)
	# Limits from geometry: a diagonal facing turns the toes towards the camera (idle up to ~3.3 px); the run's
	# front foot lands ~0.6 m ahead, which projects to 0.6 m x 32 px/m x sin 40 deg = 12.3 px below the origin.
	check(lows.idle.size() == 64 and lows.idle.min() >= -0.5 and lows.idle.max() <= 3.5 and lows.moving.min() >= -4.0 and lows.moving.max() <= 13.0,
		"feet anchored on all %d frames: idle soles %.1f..%.1f px from the origin; moving cycles %.1f..%.1f px (a stepping foot is nearer / farther)" % [
		lows.idle.size() + lows.moving.size(), lows.idle.min(), lows.idle.max(), lows.moving.min(), lows.moving.max()])
	check(heights.idle.min() >= 40.0 and heights.idle.max() <= 49.0 and heights.moving.max() <= 58.0 and heights.moving.min() >= 30.0,
		"figure scale: idle %.1f..%.1f px tall (1.8 m), moving cycles %.1f..%.1f px (sneak crouches, run strides)" % [
		heights.idle.min(), heights.idle.max(), heights.moving.min(), heights.moving.max()])


func _player_scene() -> void:
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	var col := (player.get_node("Collision") as CollisionShape2D)
	var reach := (player.get_node("InteractionArea/Collision") as CollisionShape2D).shape as CircleShape2D
	check(sprite.sprite_frames.resource_path == FRAMES_PATH and not sprite.centered and sprite.offset == Vector2(-64, -183)
		and is_equal_approx(sprite.scale.x, 1.0 / 3.0) and sprite.light_mask == 2
		and (col.shape as RectangleShape2D).size == Vector2(28, 12) and col.position == Vector2(0, -6)
		and player.collision_layer == 2 and player.collision_mask == 1 and reach.radius == 24.0,
		"Player.tscn: character sprite (offset (-64, -183), scale 1/3, light mask 2); 28 x 12 footprint, layer 2 / mask 1, interaction radius 24")


func _directions() -> void:
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	var wrong := []
	var persist := []
	for f: String in DIR_ACTIONS:
		await place(OPEN_SPOT)
		await hold(DIR_ACTIONS[f], 20)
		var walking := String(sprite.animation)
		await frames(15)
		if walking != "walk_" + f:
			wrong.append("%s -> %s" % [f, walking])
		if String(sprite.animation) != "idle_" + f:
			persist.append("%s -> %s" % [f, sprite.animation])
	check(wrong.is_empty(), "all 8 input directions play the matching walk facing (wrong %s)" % [wrong])
	check(persist.is_empty(), "after stopping the player keeps facing the same way as idle_<facing> (wrong %s)" % [persist])


func _hysteresis() -> void:
	var anim_node := player.get_node("Sprite")
	anim_node.set("facing", "right")
	var near_edge: String = anim_node.call("_facing_for", Vector2.from_angle(deg_to_rad(22.5 + 5.0)))
	var past_edge: String = anim_node.call("_facing_for", Vector2.from_angle(deg_to_rad(22.5 + 15.0)))
	anim_node.set("facing", "down")
	check(near_edge == "right" and past_edge == "down_right",
		"facing hysteresis: 5 deg past the sector edge keeps 'right' (%s); 15 deg past turns 'down_right' (%s)" % [near_edge, past_edge])


func _gaits_and_phase() -> void:
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	await place(OPEN_SPOT)
	await hold(["move_right", "sprint"], 40)
	var run_anim := sprite.animation
	await place(OPEN_SPOT)
	await hold(["move_right", "sneak"], 40)
	var sneak_anim := sprite.animation
	check(run_anim == &"run_right" and sneak_anim == &"sneak_right", "sprint plays %s, sneak plays %s" % [run_anim, sneak_anim])
	# Turn right -> down while walking: sample the walk cycle's phase every frame. Normal play advances it by
	# about 0.02 per frame; a restart on a facing change would show as a jump back towards 0.
	await place(OPEN_SPOT)
	var phases := []
	var sample := func(_i): phases.append(float(sprite.frame + sprite.frame_progress) / float(sprite.sprite_frames.get_frame_count(sprite.animation)))
	await hold(["move_right"], 20, 1.0, sample)
	Input.action_press("move_right")
	await hold(["move_down"], 20, 1.0, sample)
	Input.action_release("move_right")
	await hold(["move_down"], 10, 1.0, sample)
	var worst := 0.0
	for i in range(1, phases.size()):
		worst = maxf(worst, absf(wrapf(phases[i] - phases[i - 1], -0.5, 0.5)))
	check(String(sprite.animation) == "walk_down" and worst <= 0.08,
		"turning right -> down_right -> down keeps the walk cycle's phase (largest per-frame phase change %.3f, a restart would be ~0.5)" % worst)


func _footstep_frames() -> void:
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	var cycles: Dictionary = sprite.sprite_frames.get_meta("cycles", {})
	var seen := []
	var cb := func(_s, _g, _at): seen.append([String(sprite.animation).get_slice("_", 0), sprite.frame])
	player.footstep.connect(cb)
	for actions in [["move_right"], ["move_right", "sprint"], ["move_right", "sneak"]]:
		await place(OPEN_SPOT)
		await hold(actions, 150)
	player.footstep.disconnect(cb)
	var off := seen.filter(func(e): return not (cycles.get(e[0], {}) as Dictionary).get("contact_frames", []).has(e[1]))
	check(seen.size() >= 10 and off.is_empty(), "%d footsteps, every one on a heel-strike frame of its cycle (off-frame %s)" % [seen.size(), off])


func _persistence() -> void:
	var door := main.get_current_zone().get_node("Objects/Buildings/CDSExterior/TableTennis/DoorCdsMainEntry")
	await place((door.get_node("Interactable") as Node2D).global_position + Vector2(0, 6))
	await press("interact")
	await await_travel()
	var players := get_tree().root.find_children("*", "CharacterBody2D", true, false).filter(func(n): return n is Player)
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	check(main.get_current_zone_id() == "cds_veranda" and players.size() == 1 and players[0] == player and sprite.is_playing(),
		"the same Player (and its character) survives a faded trip into cds_veranda; still exactly one Player")
	main.change_zone("main_gate_exterior", "main_gate_entry")
	await frames(2)

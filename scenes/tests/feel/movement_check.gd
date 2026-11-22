extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I movement suite (I1 + I2 + surfaces), on the real Main.tscn. Targets: Docs/PRESENTATION.md section 4.

const FIELD := Vector2(12320, 4300)          # open grass in the central field, nothing to collide with
const TOL := 1.0                             # px/s
const SURFACES_TABLE := "res://data/audio/surfaces.tres"

var _steps: Array = []


func _run() -> void:
	tag = "MOVE"
	player.footstep.connect(func(s, g, at): _steps.append([s, g, at]))
	await _speeds()
	await _ramps()
	await _analog_and_diagonal()
	await _stamina()
	await _animation_match()
	await _input_lock()
	await _surfaces()


func _speed() -> float:
	return player.velocity.length()


func _speeds() -> void:
	for spec in [[["move_right"], player.walk_speed, "walk", &"walk"], [["move_right", "sprint"], player.sprint_speed, "sprint", &"sprint"],
			[["move_right", "sneak"], player.sneak_speed, "sneak", &"sneak"]]:
		await place(FIELD)
		var r := {"top": 0.0}
		await hold(spec[0], 60, 1.0, func(_i): r.top = maxf(r.top, _speed()))
		await frames(1)
		var at_end: float = r.top
		check(approx(at_end, spec[1], TOL) and player.mode == &"idle",
			"%s: top speed %.2f px/s (want %.0f, %.2f m/s); mode returns to idle on release" % [spec[2], at_end, spec[1], spec[1] / 32.0])
	check(player.walk_speed == 62.0 and player.sneak_speed == 32.0 and player.sprint_speed == 154.0,
		"configured speeds sneak 32 / walk 62 / sprint 154 px/s (Docs/PRESENTATION.md)")


func _ramps() -> void:
	await place(FIELD)
	# `physics_frame` is emitted BEFORE that tick's physics runs, so in callback i exactly i ticks have been
	# processed since the press: tick counts below are completed ticks.
	var r := {"first": -1.0, "to_walk": -1}
	await hold(["move_right"], 30, 1.0, func(i):
		if i == 1:
			r.first = _speed()
		if r.to_walk == -1 and _speed() >= 0.95 * player.walk_speed:
			r.to_walk = i)
	var first_tick_speed: float = r.first
	var to_walk: int = r.to_walk
	var stop := -1
	for i in 30:
		await get_tree().physics_frame
		if _speed() < 1.0:
			stop = i
			break
	check(first_tick_speed > 0.0, "motion starts on the same physics tick as the input (%.1f px/s after 1 tick)" % first_tick_speed)
	check(to_walk > 0 and to_walk / 60.0 <= 0.12, "0 -> walk in %.3f s (budget 0.12 s)" % (to_walk / 60.0))
	check(stop > 0 and stop / 60.0 <= 0.10, "walk -> stop in %.3f s (budget 0.10 s)" % (stop / 60.0))
	await place(FIELD)
	var t_sprint := -1
	Input.action_press("move_right")
	await frames(20)
	Input.action_press("sprint")
	for i in 60:
		await get_tree().physics_frame
		if _speed() >= 0.95 * player.sprint_speed:
			t_sprint = i
			break
	release_all()
	check(t_sprint > 0 and t_sprint / 60.0 <= 0.30, "walk -> sprint in %.3f s (target 0.25 s)" % (t_sprint / 60.0))


func _analog_and_diagonal() -> void:
	await place(FIELD)
	var r := {"v": Vector2.ZERO, "m": &"", "s": 0.0}
	await hold(["move_right", "move_down"], 40, 1.0, func(_i): r.v = player.velocity)
	var v: Vector2 = r.v
	check(approx(v.length(), player.walk_speed, TOL) and absf(v.angle() - PI / 4.0) < 0.01,
		"diagonal is normalised: %.2f px/s at %.1f deg" % [v.length(), rad_to_deg(v.angle())])
	await place(FIELD)
	await hold(["move_right"], 40, 0.7, func(_i): r.m = player.mode; r.s = _speed())
	var m: StringName = r.m
	var s: float = r.s
	check(m == &"sneak" and approx(s, player.sneak_speed, TOL), "a 70 %% stick tilt sneaks (%s, %.1f px/s)" % [m, s])
	await place(FIELD)
	await hold(["move_right"], 40, 0.95, func(_i): r.m = player.mode; r.s = _speed())
	m = r.m
	s = r.s
	check(m == &"walk" and approx(s, player.walk_speed, TOL), "a 95 %% stick tilt walks (%s, %.1f px/s)" % [m, s])


func _stamina() -> void:
	# Stamina belongs to the story (Explore mode, D45, never tires): test it with a director's rules in force.
	Game.story_active = true
	await place(FIELD)
	player.stamina = 1.0
	player.winded = false
	var drain_start := -1
	var winded_at := -1
	Input.action_press("move_right")
	Input.action_press("sprint")
	for i in 480:
		await get_tree().physics_frame
		if drain_start == -1 and player.stamina < 1.0:
			drain_start = i
		if player.winded:
			winded_at = i
			break
	var sprint_s := (winded_at - drain_start) / 60.0
	await seconds(0.5)
	var winded_speed := _speed()
	check(winded_at > 0 and approx(sprint_s, player.sprint_seconds, 0.2) and approx(winded_speed, player.walk_speed, TOL),
		"a full sprint lasts %.2f s (want %.1f); winded, the player drops to walking (%.1f px/s)" % [sprint_s, player.sprint_seconds, winded_speed])
	Input.action_release("sprint")
	await seconds(3.5)
	var st := player.stamina
	check(not player.winded and approx(st, (3.5 + 0.5 - player.recover_delay) / player.recover_seconds, 0.04),
		"after walking 4 s stamina is %.3f (1 s delay, then 1/8 per s) and the player is no longer winded" % st)
	Input.action_press("sprint")
	await seconds(0.5)
	check(approx(_speed(), player.sprint_speed, TOL), "sprinting works again once recovered (%.1f px/s)" % _speed())
	release_all()
	player.stamina = 1.0
	Game.story_active = false
	await place(FIELD)
	var lowest := {"s": 1.0, "w": false}
	await hold(["move_right", "sprint"], 8 * 60, 1.0, func(_i):
		lowest.s = minf(lowest.s, player.stamina)
		lowest.w = lowest.w or player.winded)
	check(lowest.s >= 1.0 and not lowest.w, "Explore mode: 8 s of sprinting never tires the player (lowest stamina %.2f)" % lowest.s)


func _animation_match() -> void:
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	var cycles: Dictionary = sprite.sprite_frames.get_meta("cycles", {})
	for spec in [[["move_right"], "walk"], [["move_right", "sprint"], "run"], [["move_right", "sneak"], "sneak"]]:
		await place(FIELD)
		_steps.clear()
		# Count the animation frames that really advanced in the window: the animation runs on real time while the
		# window is counted in physics ticks, and headless physics may catch up after a slow frame, so a
		# tick-based expectation would be flaky. Two heel strikes per cycle of advanced frames is exact.
		var r := {"anim": &"", "scale": 0.0, "spd": 0.0, "advanced": 0, "counting": false}
		var on_frame := func(): if r.counting: r.advanced += 1
		sprite.frame_changed.connect(on_frame)
		var n := 240
		await hold(spec[0], n, 1.0, func(i):
			if i == 60:
				_steps.clear()
				r.counting = true
			r.anim = sprite.animation
			r.scale = sprite.speed_scale
			r.spd = _speed())
		r.counting = false
		sprite.frame_changed.disconnect(on_frame)
		var anim: StringName = r.anim
		var scale: float = r.scale
		var spd: float = r.spd
		var c: Dictionary = cycles.get(spec[1], {})
		var cycle_speed := float(c.get("speed_px_s", 0.0))
		var slide := absf(spd / maxf(cycle_speed * scale, 0.001) - 1.0)
		var expected_steps := float(r.advanced) * 2.0 / float(c.get("frames", 1))
		check(String(anim) == "%s_right" % spec[1] and slide <= 0.05,
			"%s plays %s at speed_scale %.3f: legs cover %.1f px/s vs body %.1f px/s (slide %.1f %%, limit 5 %%)" % [spec[1], anim, scale, cycle_speed * scale, spd, slide * 100.0])
		check(absf(_steps.size() - expected_steps) <= 1.0 and _steps.all(func(e): return e[1] == StringName(spec[1])),
			"%s: %d footsteps over %d animation frames (expected %.1f: 2 heel strikes per cycle), all tagged %s" % [spec[1], _steps.size(), r.advanced, expected_steps, spec[1]])


func _input_lock() -> void:
	await place(FIELD)
	player.input_enabled = false
	var start := player.global_position
	await hold(["move_right", "sprint"], 30)
	var moved := player.global_position.distance_to(start)
	player.input_enabled = true
	check(moved < 0.01 and player.mode == &"idle", "with input_enabled off the player ignores movement input (moved %.2f px)" % moved)


func _surfaces() -> void:
	var zone := main.get_current_zone()
	var map := player.surface_map
	var table := (load(SURFACES_TABLE) as SurfaceTable).by_texture_stem
	# Known spots on the campus (Map v2): the plaza's brick pavers, the spine road, the Central Field, the asphalt
	# gate road, the leaf litter under the woods.
	var known := [["the plaza pavers", Vector2(5760, 2510), &"paving"], ["the spine road", Vector2(9600, 2224), &"paving"],
		["the central field", FIELD, &"grass"], ["the gate road", Vector2(13440, 5490), &"asphalt"],
		["the woods", Vector2(4000, 3601), &"worn_grass"]]
	var bad := []
	for k in known:
		var got := map.surface_at(k[1])
		if got != k[2]:
			bad.append("%s %s: %s (want %s)" % [k[0], k[1], got, k[2]])
	check(bad.is_empty(), "surface_at is right on %d known spots: pavers, road, field, gate road, woods (bad %s)" % [known.size(), bad])
	# Agreement with an independent oracle (the topmost textured ground polygon, else the profile default) on 500
	# random points over the whole campus.
	var rng := RandomNumberGenerator.new()
	rng.seed = 20261122
	var polys: Array = []
	for n in zone.get_node("Ground").find_children("*", "Polygon2D", true, false):
		var pg := n as Polygon2D
		if pg.texture != null and table.has(pg.texture.resource_path.get_file().get_basename()):
			polys.append(pg)
	var disagree := []
	for i in 500:
		var p := Vector2(rng.randf_range(0, 15400), rng.randf_range(0, 6100))
		var want := &"grass"
		for pg: Polygon2D in polys:
			if Geometry2D.is_point_in_polygon(pg.global_transform.affine_inverse() * p, pg.polygon):
				want = table[pg.texture.resource_path.get_file().get_basename()]
		var got := map.surface_at(p)
		if got != want:
			disagree.append("%s: %s vs %s" % [p.round(), got, want])
	check(disagree.is_empty(), "surface_at agrees with an independent oracle on 500 random points (disagree %s)" % [disagree.slice(0, 4)])
	main.change_zone("cds_veranda", "inside_cds_entry")
	await frames(2)
	var vs := player.surface_map.surface_at(player.global_position)
	check(vs == &"concrete", "cds_veranda (no ground textures) uses its profile's default surface: %s" % vs)
	main.change_zone("campus", "explore_start")
	await frames(2)


## A point inside the polygon (its centroid if inside, else a vertex nudged inward).
func _inside_point(pg: Polygon2D) -> Vector2:
	var c := Vector2.ZERO
	for v in pg.polygon:
		c += v
	c /= pg.polygon.size()
	if not Geometry2D.is_point_in_polygon(c, pg.polygon):
		c = pg.polygon[0].lerp(c, 0.2)
	return pg.global_transform * c

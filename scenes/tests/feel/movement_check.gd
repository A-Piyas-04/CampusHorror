extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I movement suite (I1 + I2 + surfaces), on the real Main.tscn. Targets: Docs/PRESENTATION.md section 4.

const FIELD := Vector2(-1000, -200)          # open grass in the central field, nothing to collide with
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


func _animation_match() -> void:
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	var cycles: Dictionary = sprite.sprite_frames.get_meta("cycles", {})
	for spec in [[["move_right"], "walk"], [["move_right", "sprint"], "run"], [["move_right", "sneak"], "sneak"]]:
		await place(FIELD)
		_steps.clear()
		var r := {"anim": &"", "scale": 0.0, "spd": 0.0}
		var n := 240
		await hold(spec[0], n, 1.0, func(i):
			if i == 60:
				_steps.clear()
			r.anim = sprite.animation
			r.scale = sprite.speed_scale
			r.spd = _speed())
		var anim: StringName = r.anim
		var scale: float = r.scale
		var spd: float = r.spd
		var c: Dictionary = cycles.get(spec[1], {})
		var cycle_speed := float(c.get("speed_px_s", 0.0))
		var slide := absf(spd / maxf(cycle_speed * scale, 0.001) - 1.0)
		var expected_steps := (n - 60) / 60.0 * 2.0 * float(c.get("fps", 0.0)) * scale / float(c.get("frames", 1))
		check(String(anim) == "%s_right" % spec[1] and slide <= 0.05,
			"%s plays %s at speed_scale %.3f: legs cover %.1f px/s vs body %.1f px/s (slide %.1f %%, limit 5 %%)" % [spec[1], anim, scale, cycle_speed * scale, spd, slide * 100.0])
		check(absf(_steps.size() - expected_steps) <= 1.0 and _steps.all(func(e): return e[1] == StringName(spec[1])),
			"%s: %d footsteps in 3 s (expected %.1f from the cycle's 2 heel strikes), all tagged %s" % [spec[1], _steps.size(), expected_steps, spec[1]])


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
	var tiles := zone.get_node("Ground/Tiles") as TileMapLayer
	var worn := Vector2.INF
	for c in tiles.get_used_cells():
		if tiles.get_cell_source_id(c) == 1:
			worn = tiles.to_global(tiles.map_to_local(c))
			break
	var known := [["the west palm path", Vector2(-1390, 0), &"paving"], ["the central field", FIELD, &"grass"],
		["the road beyond the wall", Vector2(0, 1600), &"asphalt"], ["a worn-grass cell", worn, &"worn_grass"]]
	for floor_name in ["Objects/Buildings/MainGateLandmark/GatePlaza", "Objects/Buildings/CDSExterior/TableTennis/Forecourt"]:
		var pg := zone.get_node(floor_name) as Polygon2D
		known.append([floor_name.get_file() + " (polygon over tiles)", _inside_point(pg), &"paving"])
	var bad := []
	for k in known:
		var got := map.surface_at(k[1])
		if got != k[2]:
			bad.append("%s %s: %s (want %s)" % [k[0], k[1], got, k[2]])
	check(bad.is_empty(), "surface_at is right on %d known spots: path, field, road, worn patch, gate plaza, CDS forecourt (bad %s)" % [known.size(), bad])
	# Agreement with an independent oracle (validator rule + landmark floors) on 500 random points.
	var rng := RandomNumberGenerator.new()
	rng.seed = 20261121
	var floors: Array = []
	var strips: Array = []
	for n in zone.find_children("*", "Polygon2D", true, false):
		var pg := n as Polygon2D
		if pg.texture == null or not table.has(pg.texture.resource_path.get_file().get_basename()):
			continue
		(strips if zone.get_node("Ground").is_ancestor_of(pg) else floors).append(pg)
	var disagree := []
	for i in 500:
		var p := Vector2(rng.randf_range(-2390, 2990), rng.randf_range(-1790, 1940))
		var want := &""
		for pg: Polygon2D in floors:
			if Geometry2D.is_point_in_polygon(pg.global_transform.affine_inverse() * p, pg.polygon):
				want = table[pg.texture.resource_path.get_file().get_basename()]
		if want == &"":
			for pg: Polygon2D in strips:
				if Geometry2D.is_point_in_polygon(pg.global_transform.affine_inverse() * p, pg.polygon):
					want = table[pg.texture.resource_path.get_file().get_basename()]
		if want == &"":
			var src := tiles.get_cell_source_id(tiles.local_to_map(tiles.to_local(p)))
			var atlas := tiles.tile_set.get_source(src) as TileSetAtlasSource if src != -1 else null
			want = table.get(atlas.texture.resource_path.get_file().get_basename(), &"grass") if atlas else &"grass"
		var got := map.surface_at(p)
		if got != want:
			disagree.append("%s: %s vs %s" % [p.round(), got, want])
	check(disagree.is_empty(), "surface_at agrees with an independent oracle on 500 random points (disagree %s)" % [disagree.slice(0, 4)])
	main.change_zone("cds_veranda", "inside_cds_entry")
	await frames(2)
	var vs := player.surface_map.surface_at(player.global_position)
	check(vs == &"concrete", "cds_veranda (no ground textures) uses its profile's default surface: %s" % vs)
	main.change_zone("main_gate_exterior", "main_gate_entry")
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

extends "res://scenes/tests/feel/feel_check_base.gd"
## Map v2 suite (D42-D45): the `campus` zone built from data/campus/campus_layout.json, played in Explore mode on
## the real Main.tscn.
## - Wiring: every entrance in the layout is a door in the zone with its arrival spawn, every door's destination
##   spawn exists, every interior exit that leads to the campus lands on a campus spawn.
## - Reach: a 1.25 m flood fill with the player's own collision shape, from the Main Gate start, reaches every
##   entrance's arrival spot and every landmark the layout names (nothing walled off, nothing walkable outside).
## - Round trips: through every door and back out, landing where the layout says.
## - Explore basics: doors ignore locks, sprinting never tires, time of day eases and drives the lamps, the map pin
##   follows the player.

const LAYOUT := "res://data/campus/campus_layout.json"
const PX := Vector2(32.0, 20.576)
const CELL_M := 1.25

var lay: Dictionary
var zone: Zone


func _run() -> void:
	tag = "CAMPUS"
	lay = JSON.parse_string(FileAccess.get_file_as_string(LAYOUT))
	check(lay is Dictionary and lay.get("schema", 0) == 1, "the layout file loads (schema 1, %d sites)" % (lay.get("sites", []).size() if lay is Dictionary else 0))
	zone = main.get_current_zone()
	check(main.get_current_zone_id() == "campus" and Game.story_active == false and main.is_explore(),
		"the game starts in the campus, in Explore mode (no story director)")
	await _wiring()
	await _reach()
	await _round_trips()
	await _explore_basics()


func _m(v: Array) -> Vector2:
	return Vector2(float(v[0]) * PX.x, float(v[1]) * PX.y)


func _entrances() -> Array:
	var out := []
	for s in lay.sites:
		for e in s.get("entrances", []):
			if e.has("spawn"):
				out.append(e)
	return out


func _wiring() -> void:
	var doors := {}
	for d in zone.get_doors():
		doors[d.destination_zone_id] = d
	var missing := []
	for e in _entrances():
		var d: Door = doors.get(e.to)
		var spawn := zone.find_spawn_marker(e.exit_spawn)
		if d == null or d.destination_spawn_id != e.spawn or spawn == null or d.global_position.distance_to(_m(e.at)) > 1.0:
			missing.append(e.to)
	check(missing.is_empty() and doors.size() == _entrances().size(),
		"all %d layout entrances are doors at their layout spot with their arrival spawn (wrong: %s)" % [_entrances().size(), missing])
	var bad := []
	for zid in main.zone_registry.get_zone_ids():
		var path := main.zone_registry.get_scene_path(zid)
		var scene := (load(path) as PackedScene).instantiate() as Zone
		for d in scene.get_doors():
			if d.destination_zone_id == "campus" and zone.find_spawn_marker(d.destination_spawn_id) == null:
				bad.append("%s/%s -> %s" % [zid, d.name, d.destination_spawn_id])
		scene.free()
	check(bad.is_empty(), "every interior exit to the campus lands on a campus spawn (broken: %s)" % [bad])


## Flood fill over walkable cells using the player's collision shape against the world layer.
func _reach() -> void:
	var space := player.get_world_2d().direct_space_state
	var box := ((player.get_node("Collision") as CollisionShape2D).shape as RectangleShape2D).size
	var start := zone.find_spawn_marker("explore_start").global_position
	var step := Vector2(CELL_M * PX.x, CELL_M * PX.y)
	# swept queries: the player's box stretched over the whole step, so no thin wall can be hopped over
	var sweeps := {}
	for dvec in [Vector2i(1, 0), Vector2i(0, 1)]:
		var r := RectangleShape2D.new()
		r.size = box + Vector2(absf(dvec.x) * step.x, absf(dvec.y) * step.y)
		var q := PhysicsShapeQueryParameters2D.new()
		q.shape = r
		q.collision_mask = player.collision_mask
		q.exclude = [player.get_rid()]
		sweeps[dvec] = q
		sweeps[-dvec] = q
	var origin := start
	var seen := {}
	# bounded to the campus rectangle plus a margin: an escape through the wall shows up as walkable cells there
	var lo := Vector2i(((_m([-25, -12]) - origin) / step).floor())
	var hi := Vector2i(((_m([500, 312]) - origin) / step).ceil())
	var frontier: Array[Vector2i] = [Vector2i.ZERO]
	seen[Vector2i.ZERO] = true
	var t0 := Time.get_ticks_msec()
	while not frontier.is_empty():
		var c: Vector2i = frontier.pop_back()
		for dvec in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var n: Vector2i = c + dvec
			if seen.has(n) or n.x < lo.x or n.y < lo.y or n.x > hi.x or n.y > hi.y:
				continue
			var mid := origin + (Vector2(c) + Vector2(n)) * 0.5 * step
			var q: PhysicsShapeQueryParameters2D = sweeps[dvec]
			q.transform = Transform2D(0.0, mid + Vector2(0, -6))
			if space.intersect_shape(q, 1).is_empty():
				seen[n] = true
				frontier.append(n)

	var walk := 0
	for v in seen.values():
		walk += 1 if v else 0
	var reached := func(at: Vector2) -> bool:
		var c := Vector2i(((at - origin) / step).round())
		for dx in range(-1, 2):
			for dy in range(-1, 2):
				if seen.get(c + Vector2i(dx, dy), false):
					return true
		return false
	var unreached := []
	for e in _entrances():
		if not reached.call(zone.find_spawn_marker(e.exit_spawn).global_position):
			unreached.append(e.to)
	var landmarks := {"Central Field": [385, 200], "Southern Field": [260, 275], "halls courtyard": [350, 51],
		"mosque plaza": [262, 175], "the woods": [125, 175], "workshop lane": [140, 78.2], "Female Hall compound": [100, 285],
		"Medical Center bridge": [18, 48.3], "Five Fundamentals causeway": [292, 212]}
	for k in landmarks:
		if not reached.call(_m(landmarks[k])):
			unreached.append(k)
	check(unreached.is_empty(), "from the Main Gate, on foot, every entrance and landmark is reachable (%d walkable cells of %.2f m, %d ms; unreached %s)" % [walk, CELL_M, Time.get_ticks_msec() - t0, unreached])
	var outside := [[-30, 150], [500, 150], [250, -20], [250, 320]]
	var escaped := []
	for o in outside:
		if reached.call(_m(o)):
			escaped.append(o)
	var lake := [[200, 210], [300, 150], [260, 222]]
	for o in lake:
		if reached.call(_m(o)):
			escaped.append(o)
	# where an escape happens: the walkable cells outside the wall line that are closest to it
	var wall := PackedVector2Array()
	for b in lay.boundary.points:
		wall.append(_m(b))
	var leaks := []
	for c in seen:
		if seen[c]:
			var p := origin + Vector2(c) * step
			if not Geometry2D.is_point_in_polygon(p, wall):
				leaks.append(p)
	leaks.sort_custom(func(a, b): return _wall_distance(a, wall) < _wall_distance(b, wall))
	var near := leaks.slice(0, 3).map(func(p): return (p / PX).round())
	check(escaped.is_empty() and leaks.is_empty(), "nothing walkable beyond the campus wall or on the lakes (escaped %s; %d cells outside the wall, nearest %s)" % [escaped, leaks.size(), near])


func _wall_distance(p: Vector2, wall: PackedVector2Array) -> float:
	var best := INF
	for i in wall.size():
		best = minf(best, p.distance_to(Geometry2D.get_closest_point_to_segment(p, wall[i], wall[(i + 1) % wall.size()])))
	return best


func _round_trips() -> void:
	var failures := []
	for e in _entrances():
		main.change_zone("campus", e.exit_spawn)
		await frames(2)
		if not main.travel(e.to, e.spawn):
			failures.append("%s: travel refused" % e.to)
			continue
		await await_travel()
		if main.get_current_zone_id() != e.to:
			failures.append("%s: not entered" % e.to)
			continue
		var exit_door: Door = null
		for d in main.get_current_zone().get_doors():
			if d.destination_zone_id == "campus":
				exit_door = d
		if exit_door == null:
			failures.append("%s: no exit to the campus" % e.to)
			continue
		await place((exit_door.get_node("Interactable") as Node2D).global_position + Vector2(0, 6))
		await press("interact")
		await await_travel()
		var back := main.get_current_zone_id() == "campus" and player.global_position.distance_to(_m(e.at)) < 4.0 * PX.x
		if not back:
			failures.append("%s: came back to %s at %s" % [e.to, main.get_current_zone_id(), (player.global_position / PX).round()])
	check(failures.is_empty(), "in through every door and back out to the right spot on campus (%d doors; failures %s)" % [_entrances().size(), failures])
	main.change_zone("campus", "explore_start")
	await frames(2)


func _explore_basics() -> void:
	zone = main.get_current_zone()
	var locked := []
	for zid in ["academic_corridor", "me_workshop", "cds_veranda", "facility_corridor"]:
		var scene := (load(main.zone_registry.get_scene_path(zid)) as PackedScene).instantiate() as Zone
		add_child(scene)
		for d in scene.get_doors():
			if d.is_locked():
				locked.append("%s/%s" % [zid, d.name])
		scene.queue_free()
	await frames(1)
	check(locked.is_empty(), "Explore mode: no door is locked, even the story's (locked: %s)" % [locked])
	var tint := main.get_node("DayNightTint")
	var lamps := zone.get_node("Objects/Lights").get_children().filter(func(l): return l is LampLight)
	tint.call("set_phase", 1, true)
	await frames(2)
	var on_by_day := lamps.filter(func(l): return (l as LampLight).enabled).size()
	tint.call("set_phase", 4, false)
	await seconds(0.8)
	var mid := float(tint.get("darkness"))
	await seconds(2.2)
	var on_at_night := lamps.filter(func(l): return (l as LampLight).enabled).size()
	check(lamps.size() > 40 and on_by_day == 0 and on_at_night == lamps.size() and mid > 0.05 and mid < 0.95,
		"time of day eases (darkness %.2f mid-blend) and drives the lamps: %d of %d lit by day, %d at night" % [mid, on_by_day, lamps.size(), on_at_night])
	var lantern := player.get_node("Lantern")
	tint.call("set_phase", 1, true)
	lantern.call("set_state", 2)
	await seconds(0.6)
	var day_energy := (lantern as PointLight2D).energy
	tint.call("set_phase", 4, true)
	await seconds(0.6)
	var night_energy := (lantern as PointLight2D).energy
	check(day_energy < night_energy * 0.35, "the lantern is faint by day (%.2f) and full at night (%.2f)" % [day_energy, night_energy])
	tint.call("set_phase", 1, true)
	var map := main.get_node("UI/CampusMap")
	await place(_m([300, 108.1]))
	map.call("open")
	await frames(2)
	var pin: Vector2 = map.get("_last_campus_m")
	check(bool(map.call("is_open")) and get_tree().paused and pin.distance_to(Vector2(300, 108.1)) < 1.0,
		"the map opens (game paused) with the pin at the player's spot (%.1f, %.1f m)" % [pin.x, pin.y])
	map.call("close")
	await frames(2)
	check(not get_tree().paused, "closing the map resumes the game")

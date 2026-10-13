extends Node2D
## TEMPORARY Milestone G Batch 2 check for the REAL main_gate_exterior south boundary wall (test-only).
## Instances scenes/world/MainGateExterior.tscn and verifies:
## - Objects/Boundary/SouthWall is no longer a BlockoutBlock: it is a Y-sorted Node2D run of 37 RedBrickWall3m
##   modules exactly 96 px apart and 38 RedBrickVerandaPier pilasters on every join and both ends, each with
##   one ContactShadow, plus RunCollision (one smooth stop line, EastEdgeJoin under PrototypeEdgeEast) and one
##   ShadowOccluder (light mask 1).
## - Collision is continuous over x -1250..2302; a 28 x 12 player footprint walking south is stopped at the same
##   line everywhere, can't pass the gate or east joins, and slides along the wall without snagging on piers.
## - Compared with main_gate_ground_baseline_batch1b.json (pre-edit record) only records inside SouthWall
##   changed: doors, spawns, landmarks, courts, prototype edges and the 42 vegetation instances are identical.
## - The versioned main_gate_ground_baseline_batch2.json equals the current zone.
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail).

const ZONE_SCENE := "res://scenes/world/MainGateExterior.tscn"
const BATCH1B_BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch1b.json"
const BATCH2_BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch2.json"
const SNAPSHOT_SCRIPT := preload("res://scenes/tests/environment_previews/main_gate_ground_check.gd")
const WALL_SCENE := "res://scenes/props/architecture/RedBrickWall3m.tscn"
const PIER_SCENE := "res://scenes/props/architecture/RedBrickVerandaPier.tscn"
const SHADOW_SCENE := "res://scenes/props/common/ContactShadow.tscn"
const SOUTH_WALL := "./Objects/Boundary/SouthWall"
const RUN_ORIGIN := Vector2(-1250, 1400)
const MODULE := 96.0
const WALLS := 37
const PIERS := 38
const RUN_END_X := -1250.0 + 37 * 96.0
const RUN_HALF_DEPTH := 10.07891 / 2.0
const STOP_Y := 1400.0 - RUN_HALF_DEPTH
const WALL_SHADOW := Vector2(1.6, 0.28)
const PIER_SHADOW := Vector2(0.45, 0.25)
const FOOTPRINT := Vector2(28, 12)
const EAST_EDGE_X := 2250.0
const EPS := 0.001

var _zone: Node2D
var _snapper: Node
var _failures := 0
var _checks := 0


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[BOUNDARY] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	_zone = (load(ZONE_SCENE) as PackedScene).instantiate() as Node2D
	add_child(_zone)
	await get_tree().physics_frame
	await get_tree().physics_frame
	await get_tree().process_frame
	_snapper = SNAPSHOT_SCRIPT.new()
	_snapper.set("_zone", _zone)
	_run_checks()
	_snapper.free()
	print("[BOUNDARY] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _run_checks() -> void:
	_check(_zone.get("zone_id") == "main_gate_exterior" and _zone.get_node_or_null("Objects/Boundary") != null,
		"zone loads (zone_id main_gate_exterior) and has Objects/Boundary")
	var run := _node(SOUTH_WALL) as Node2D
	_check(run != null, "Objects/Boundary/SouthWall exists")
	if run == null:
		return
	_check_replaced(run)
	var walls := _instances(run, WALL_SCENE)
	var piers := _instances(run, PIER_SCENE)
	_check_modules(run, walls, piers)
	_check_internals(walls, WALL_SCENE)
	_check_internals(piers, PIER_SCENE)
	_check_shadows(walls, piers)
	_check_run_collision(run)
	_check_continuity(run)
	_check_occluder(run)
	_check_probes()
	_check_slide()
	var before := _load_json(BATCH1B_BASELINE)
	var now: Dictionary = _snapper.call("_snapshot")
	_check(not before.is_empty(), "pre-edit baseline loaded from %s" % BATCH1B_BASELINE)
	if not before.is_empty():
		_check_neighbours(before, now)
		_check_diff(before, now)
		_check_versioned(before, now)
	_check_placeholders(run)
	_check(_zone.find_children("*", "CharacterBody2D", true, false).is_empty(),
		"the zone itself contains no CharacterBody2D (the one Player belongs to Main)")


func _node(key: String) -> Node:
	return _zone.get_node_or_null(NodePath(key.trim_prefix("./")))


func _instances(run: Node, scene: String) -> Array[Node2D]:
	var out: Array[Node2D] = []
	for child in run.get_children():
		if child.scene_file_path == scene:
			out.append(child as Node2D)
	return out


func _check_replaced(run: Node2D) -> void:
	var bad := []
	for node in [run] + run.find_children("*", "", true, false):
		if node is BlockoutBlock or node.is_in_group("blockout_placeholder"):
			bad.append(String(run.get_path_to(node)))
	_check(not (run is BlockoutBlock) and run.get_class() == "Node2D" and run.scene_file_path == "" and bad.is_empty(),
		"SouthWall is a plain Node2D, not a BlockoutBlock; no BlockoutBlock / blockout_placeholder under it (%s)" % [bad.slice(0, 5)])
	var unsorted := []
	var node: Node = run
	while node != null and node != self:
		if not (node as Node2D).y_sort_enabled:
			unsorted.append(String(node.name))
		node = node.get_parent()
	_check(run.global_position.is_equal_approx(RUN_ORIGIN) and run.rotation == 0.0 and run.scale == Vector2.ONE
		and unsorted.is_empty(), "SouthWall at %s, no rotation/scale, it and every ancestor Y-sorted (unsorted %s)" % [run.global_position, unsorted])


func _check_modules(run: Node2D, walls: Array[Node2D], piers: Array[Node2D]) -> void:
	var bad_walls := []
	for i in walls.size():
		var w := walls[i]
		if w.name != "Wall%02d" % (i + 1) or not w.position.is_equal_approx(Vector2(48 + MODULE * i, 0)) \
				or w.rotation != 0.0 or w.scale != Vector2.ONE:
			bad_walls.append(String(w.name))
	var spacing_ok := true
	for i in range(1, walls.size()):
		spacing_ok = spacing_ok and absf(walls[i].position.x - walls[i - 1].position.x - MODULE) <= EPS
	_check(walls.size() == WALLS and bad_walls.is_empty() and spacing_ok,
		"%d RedBrickWall3m Wall01..Wall37 at local (48 + 96k, 0), consecutive spacing exactly 96 (bad %s)" % [walls.size(), bad_walls.slice(0, 5)])
	var bad_piers := []
	for i in piers.size():
		var p := piers[i]
		if p.name != "Pier%02d" % i or not p.position.is_equal_approx(Vector2(MODULE * i, 0)) \
				or p.rotation != 0.0 or p.scale != Vector2.ONE:
			bad_piers.append(String(p.name))
	var order_ok := walls.size() > 0 and piers.size() > 0 and piers[0].get_index() > walls[walls.size() - 1].get_index()
	_check(piers.size() == PIERS and bad_piers.is_empty() and order_ok,
		"%d RedBrickVerandaPier Pier00..Pier37 on every join and both ends (local 96k), all after the walls in tree order (bad %s)" % [piers.size(), bad_piers.slice(0, 5)])
	var first := walls[0].global_position.x - MODULE / 2.0 if walls.size() > 0 else NAN
	var last := walls[walls.size() - 1].global_position.x + MODULE / 2.0 if walls.size() > 0 else NAN
	_check(absf(first - RUN_ORIGIN.x) <= EPS and absf(last - RUN_END_X) <= EPS,
		"run spans world x %.1f..%.1f (gate PierEast face -1250 to beyond PrototypeEdgeEast)" % [first, last])


func _check_internals(nodes: Array[Node2D], scene: String) -> void:
	var reference := (load(scene) as PackedScene).instantiate()
	var ref_sprite := reference.get_node("Sprite") as Sprite2D
	var ref_shape := (reference.get_node("Body/Collision") as CollisionShape2D).shape as RectangleShape2D
	var bad := []
	for n in nodes:
		var sprite := n.get_node_or_null("Sprite") as Sprite2D
		var body := n.get_node_or_null("Body") as StaticBody2D
		var shape := n.get_node_or_null("Body/Collision") as CollisionShape2D
		var ok := sprite != null and sprite.texture == ref_sprite.texture and sprite.scale == ref_sprite.scale \
			and sprite.offset == ref_sprite.offset and sprite.light_mask == 2 and _effective_z(sprite) == 0 \
			and body != null and body.collision_layer == 1 and body.collision_mask == 0 \
			and shape != null and not shape.disabled and shape.shape is RectangleShape2D \
			and (shape.shape as RectangleShape2D).size.is_equal_approx(ref_shape.size) \
			and shape.global_position.is_equal_approx(n.global_position)
		if not ok:
			bad.append(String(n.name))
	_check(nodes.size() > 0 and bad.is_empty(), "%s instances keep the generated Sprite (light mask 2) and Body (layer 1 / mask 0, %s footprint) (bad %s)" % [scene.get_file(), ref_shape.size, bad.slice(0, 5)])
	reference.free()


func _check_shadows(walls: Array[Node2D], piers: Array[Node2D]) -> void:
	var bad := []
	for n in walls + piers:
		var expected := WALL_SHADOW if n.scene_file_path == WALL_SCENE else PIER_SHADOW
		var shadows := []
		for child in n.get_children():
			if child.name.begins_with("ContactShadow"):
				shadows.append(child)
		var ok := shadows.size() == 1
		if ok:
			var s := shadows[0] as Sprite2D
			ok = s != null and s.scene_file_path == SHADOW_SCENE and s.position == Vector2.ZERO and s.rotation == 0.0 \
				and s.scale.is_equal_approx(expected) and _effective_z(s) == -9 and s.visible \
				and s.find_children("*", "CollisionObject2D", true, false).is_empty()
		if not ok:
			bad.append(String(n.name))
	_check(walls.size() + piers.size() == WALLS + PIERS and bad.is_empty(),
		"each wall/pier has exactly one ContactShadow at its origin, z -9, wall (1.6, 0.28) / pier (0.45, 0.25), no collision (bad %s)" % [bad.slice(0, 5)])


func _check_run_collision(run: Node2D) -> void:
	var body := run.get_node_or_null("RunCollision") as StaticBody2D
	var shape := run.get_node_or_null("RunCollision/Shape") as CollisionShape2D
	var join := run.get_node_or_null("RunCollision/EastEdgeJoin") as CollisionShape2D
	var ok := body != null and body.collision_layer == 1 and body.collision_mask == 0 and shape != null and join != null \
		and body.get_child_count() == 2
	if ok:
		var r := _global_rect(shape)
		var j := _global_rect(join)
		ok = not shape.disabled and not join.disabled \
			and r.position.is_equal_approx(Vector2(RUN_ORIGIN.x, STOP_Y)) and r.end.is_equal_approx(Vector2(RUN_END_X, 1400.0 + RUN_HALF_DEPTH)) \
			and j.position.is_equal_approx(Vector2(EAST_EDGE_X, 1376)) and j.end.is_equal_approx(Vector2(2280, 1396))
		print("[BOUNDARY]      RunCollision/Shape %s, EastEdgeJoin %s" % [r, j])
	_check(ok, "RunCollision: StaticBody2D layer 1 / mask 0 with Shape x -1250..2302, y %.3f..%.3f and EastEdgeJoin x 2250..2280, y 1376..1396" % [STOP_Y, 1400.0 + RUN_HALF_DEPTH])


func _check_continuity(run: Node2D) -> void:
	var space := get_world_2d().direct_space_state
	var gaps := []
	var samples := 0
	for y in [STOP_Y + 0.05, 1400.0, 1400.0 + RUN_HALF_DEPTH - 0.05]:
		var x := RUN_ORIGIN.x + 0.5
		while x < RUN_END_X:
			samples += 1
			var query := PhysicsPointQueryParameters2D.new()
			query.position = Vector2(x, y)
			query.collision_mask = 1
			var hit := false
			for result in space.intersect_point(query, 32):
				if run.is_ancestor_of(result.collider):
					hit = true
					break
			if not hit:
				gaps.append(Vector2(x, y))
			x += 1.0
	_check(samples > 0 and gaps.is_empty(), "layer-1 collision under SouthWall continuous over x -1250..2302 at 3 depths (%d samples, gaps %s)" % [samples, gaps.slice(0, 5)])


func _check_occluder(run: Node2D) -> void:
	var occluders := run.find_children("*", "LightOccluder2D", true, false)
	var occ := run.get_node_or_null("ShadowOccluder") as LightOccluder2D
	var ok := occluders.size() == 1 and occ != null and occ.occluder_light_mask == 1 and occ.occluder != null
	if ok:
		var expected := PackedVector2Array([Vector2(RUN_ORIGIN.x, STOP_Y), Vector2(RUN_END_X, STOP_Y),
			Vector2(RUN_END_X, 1400.0 + RUN_HALF_DEPTH), Vector2(RUN_ORIGIN.x, 1400.0 + RUN_HALF_DEPTH)])
		var poly := occ.occluder.polygon
		ok = poly.size() == 4
		for i in mini(poly.size(), 4):
			ok = ok and (occ.global_transform * poly[i]).is_equal_approx(expected[i])
	_check(ok, "exactly one LightOccluder2D (ShadowOccluder) under SouthWall, light mask 1, covering the run footprint")


func _make_probe() -> CharacterBody2D:
	var probe := CharacterBody2D.new()
	probe.collision_layer = 0
	probe.collision_mask = 1
	probe.motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = FOOTPRINT
	shape.shape = rect
	shape.position = Vector2(0, -FOOTPRINT.y / 2.0)
	probe.add_child(shape)
	add_child(probe)
	return probe


func _probe_end(probe: CharacterBody2D, start: Vector2, motion: Vector2) -> Dictionary:
	probe.global_position = start
	var hit := probe.move_and_collide(motion, true)
	if hit == null:
		return {"end": start + motion, "collider": null, "normal": Vector2.ZERO}
	return {"end": start + hit.get_travel(), "collider": hit.get_collider(), "normal": hit.get_normal()}


func _check_probes() -> void:
	var probe := _make_probe()
	var run := _node(SOUTH_WALL)
	var missed := []
	var off_line := []
	var stops := []
	var x := RUN_ORIGIN.x + FOOTPRINT.x / 2.0 + 2.0
	while x <= EAST_EDGE_X - FOOTPRINT.x / 2.0 - 2.0:
		var r := _probe_end(probe, Vector2(x, 1340), Vector2(0, 120))
		if r.collider == null or not run.is_ancestor_of(r.collider):
			missed.append(x)
		elif absf(r.end.y - STOP_Y) > 0.15:
			off_line.append("%s:%.3f" % [x, r.end.y])
		stops.append(r.end.y)
		x += 24.0
	stops.sort()
	print("[BOUNDARY]      walking south: %d probes, stop y min %.3f max %.3f (pre-edit blockout stop line ~1376)" % [stops.size(), stops[0], stops[stops.size() - 1]])
	_check(missed.is_empty() and off_line.is_empty() and stops.size() > 90,
		"28 x 12 footprint walking south every 24 px over x -1234..2234 is stopped by SouthWall at y %.3f +- 0.15 everywhere (missed %s, off line %s)" % [STOP_Y, missed.slice(0, 5), off_line.slice(0, 5)])
	var gate_down := _probe_end(probe, Vector2(-1236, 1340), Vector2(0, 120))
	var gate_west := _probe_end(probe, Vector2(-1200, 1394), Vector2(-120, 0))
	_check(gate_down.collider != null and gate_down.end.y < 1400.0 and gate_west.collider != null
		and gate_west.end.x > -1250.0 + FOOTPRINT.x / 2.0 - 0.5,
		"gate join closed: south at x -1236 stops at y %.3f, west along the wall stops at x %.3f (gate PierEast face -1250)" % [gate_down.end.y, gate_west.end.x])
	var east_down := _probe_end(probe, Vector2(2236, 1340), Vector2(0, 120))
	var east_slot := _probe_end(probe, Vector2(2200, STOP_Y - 0.5), Vector2(200, 0))
	var east_mid := _probe_end(probe, Vector2(2200, 1388), Vector2(200, 0))
	_check(east_down.collider != null and east_down.end.y < 1400.0
		and east_slot.collider != null and east_slot.end.x <= EAST_EDGE_X - FOOTPRINT.x / 2.0 + 0.5
		and east_mid.collider != null and east_mid.end.x <= EAST_EDGE_X - FOOTPRINT.x / 2.0 + 0.5,
		"east end closed: south at x 2236 stops at y %.3f; walking east along the wall stops at x %.3f / %.3f (PrototypeEdgeEast face 2250)" % [east_down.end.y, east_slot.end.x, east_mid.end.x])
	probe.free()


func _check_slide() -> void:
	var probe := _make_probe()
	probe.global_position = Vector2(-600, STOP_Y - 1.0)
	var start := probe.global_position
	var max_y := start.y
	var steps := 30
	var min_dx := INF
	var max_dx := 0.0
	for i in steps:
		var x_before := probe.global_position.x
		probe.velocity = Vector2(1, 1).normalized() * 200.0
		probe.move_and_slide()
		max_y = maxf(max_y, probe.global_position.y)
		if i > 0:
			var dx := probe.global_position.x - x_before
			min_dx = minf(min_dx, dx)
			max_dx = maxf(max_dx, dx)
	var travel := probe.global_position.x - start.x
	_check(travel > 3 * MODULE and min_dx >= max_dx * 0.9 and max_y <= STOP_Y + 0.15 and probe.global_position.x < EAST_EDGE_X,
		"sliding along the wall (down + right, %d move_and_slide steps) crosses %d piers without snagging: travelled %.1f px, per-step x %.2f..%.2f, max y %.3f" % [steps, int(travel / MODULE), travel, min_dx, max_dx, max_y])
	probe.free()


func _check_neighbours(before: Dictionary, now: Dictionary) -> void:
	var prefixes := ["./Objects/Buildings/MainGateLandmark", "./Objects/Buildings/CDSExterior", "./Objects/SportsCourts",
		"./Objects/Boundary/PrototypeEdgeWest", "./Objects/Boundary/PrototypeEdgeNorth", "./Objects/Boundary/PrototypeEdgeEast",
		"./Objects/Vegetation"]
	var compared := 0
	var bad := []
	for key: String in before.nodes:
		for prefix: String in prefixes:
			if key == prefix or key.begins_with(prefix + "/"):
				compared += 1
				if not now.nodes.has(key) or not _same(before.nodes[key], now.nodes[key]):
					bad.append(key)
	_check(compared > 300 and bad.is_empty(), "%d records of the gate, CDS, courts, prototype edges and 42 vegetation instances identical to the pre-edit baseline (bad %s)" % [compared, bad.slice(0, 5)])
	var door: Dictionary = now.nodes.get("./Objects/Buildings/CDSExterior/TableTennis/DoorCdsMainEntry", {})
	var spawn_gate: Dictionary = now.nodes.get("./Objects/Buildings/MainGateLandmark/SpawnMainGateEntry", {})
	var spawn_cds: Dictionary = now.nodes.get("./Objects/Buildings/CDSExterior/TableTennis/SpawnOutsideCdsEntrance", {})
	var doors := 0
	var spawns := 0
	for key: String in now.nodes:
		doors += 1 if now.nodes[key].has("destination_zone_id") else 0
		spawns += 1 if now.nodes[key].has("spawn_id") else 0
	_check(doors == 1 and spawns == 2 and door.get("destination_zone_id") == var_to_str("cds_veranda")
		and door.get("destination_spawn_id") == var_to_str("inside_cds_entry") and _xy(door) == Vector2(1452, -200)
		and spawn_gate.get("spawn_id") == var_to_str("main_gate_entry") and _xy(spawn_gate) == Vector2(-1390, 960)
		and spawn_cds.get("spawn_id") == var_to_str("outside_cds_entrance") and _xy(spawn_cds) == Vector2(1380, -200),
		"1 door (cds_main_entry -> cds_veranda/inside_cds_entry at (1452, -200)) and 2 spawns (main_gate_entry (-1390, 960), outside_cds_entrance (1380, -200)) unchanged")


func _xy(rec: Dictionary) -> Vector2:
	var xf: Array = rec.get("xform", [])
	return Vector2(xf[4], xf[5]) if xf.size() == 6 else Vector2.INF


func _in_south_wall(key: String) -> bool:
	return key == SOUTH_WALL or key.begins_with(SOUTH_WALL + "/")


func _check_diff(before: Dictionary, now: Dictionary) -> void:
	var outside_changed := []
	var removed := []
	var added := 0
	var compared := 0
	for key: String in before.nodes:
		if _in_south_wall(key):
			if not now.nodes.has(key) or not _same(before.nodes[key], now.nodes[key]):
				removed.append(key)
			continue
		compared += 1
		if not now.nodes.has(key) or not _same(before.nodes[key], now.nodes[key]):
			outside_changed.append(key)
	for key: String in now.nodes:
		if not before.nodes.has(key):
			if _in_south_wall(key):
				added += 1
			else:
				outside_changed.append(key)
	var expected_added := (WALLS + PIERS) * 5 + 4
	_check(outside_changed.is_empty() and compared == 333 and removed.size() == 3,
		"%d records outside SouthWall identical to the pre-edit baseline; the 3 blockout SouthWall records replaced (block root now a Node2D, generated collision and occluder gone) (outside changed %s)" % [compared, outside_changed.slice(0, 5)])
	_check(added == expected_added and before.zone_id == now.zone_id and _same(before.markings, now.markings),
		"%d new records, all inside SouthWall (expected %d: 75 instances x 5 + RunCollision, Shape, EastEdgeJoin, ShadowOccluder); zone_id and %d markings unchanged" % [added, expected_added, now.markings.size()])


func _check_versioned(before: Dictionary, now: Dictionary) -> void:
	var versioned := _load_json(BATCH2_BASELINE)
	_check(not versioned.is_empty() and _same(versioned, now),
		"versioned baseline %s exists and equals the current zone (%d nodes)" % [BATCH2_BASELINE.get_file(), versioned.get("nodes", {}).size()])
	if versioned.is_empty():
		return
	var outside := []
	for key: String in before.nodes:
		if not _in_south_wall(key) and (not versioned.nodes.has(key) or not _same(before.nodes[key], versioned.nodes[key])):
			outside.append(key)
	for key: String in versioned.nodes:
		if not _in_south_wall(key) and not before.nodes.has(key):
			outside.append(key)
	_check(outside.is_empty(), "batch2 baseline differs from the batch1b baseline only inside SouthWall (outside %s)" % [outside.slice(0, 5)])


func _check_placeholders(run: Node2D) -> void:
	var tops := []
	for node in _zone.find_children("*", "", true, false):
		if node.is_in_group("blockout_placeholder") and not node.get_parent().is_in_group("blockout_placeholder"):
			tops.append(String(_zone.get_path_to(node)))
	var inside := tops.filter(func(p: String) -> bool: return p.begins_with("Objects/Boundary/SouthWall"))
	print("[BOUNDARY]      remaining placeholder roots (%d): %s" % [tops.size(), ", ".join(tops)])
	_check(inside.is_empty() and tops.size() > 0, "no placeholder left in the south boundary run (%d placeholder roots remain elsewhere: gate, CDS, courts, prototype edges, markings)" % tops.size())


func _global_rect(cs: CollisionShape2D) -> Rect2:
	var size := (cs.shape as RectangleShape2D).size
	return Rect2(cs.global_position - size / 2.0, size)


func _load_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	return data if data is Dictionary else {}


func _effective_z(item: CanvasItem) -> int:
	return _snapper.call("_effective_z", item)


func _same(a, b) -> bool:
	return _snapper.call("_same", a, b)

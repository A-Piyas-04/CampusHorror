extends Node2D
## TEMPORARY Milestone G Batch 1A check for the REAL main_gate_exterior ground (test-only).
## Instances scenes/world/MainGateExterior.tscn and verifies:
## - Ground structure: Ground (z -10, not Y-sorted) > Tiles (TileMapLayer, campus_ground), EdgeStrips, Markings.
## - Coverage: an 8 px sample lattice over the original GroundFill plus samples 0.5 px either side of every
##   original surface edge must show the material of the original blockout layout (no snapping).
## - Edge strips: production texture, repeat enabled, no UV / offset, so they stay in phase with the tiles.
## - Everything outside Ground (doors, spawns, landmarks, collisions, occluders, vegetation, Y-sort, z,
##   light masks) and the markings' global transforms equal the baseline JSON.
## Baselines: main_gate_ground_baseline.json is the historical pre-Batch-1A record (placeholder vegetation; kept
## unchanged, used by main_gate_vegetation_check.gd). main_gate_ground_baseline_batch1b.json was dumped after
## Batch 1B (only the 42 vegetation instances differ) and is the pre-Batch-2 record (main_gate_boundary_check.gd).
## main_gate_ground_baseline_batch2.json was dumped after Batch 2 (differs from batch1b only inside
## Objects/Boundary/SouthWall). main_gate_ground_baseline_batch3.json is the current fixture, dumped after Batch 3
## and verified by main_gate_landmark_check.gd to differ from batch2 only inside the MainGateLandmark gate art.
## Args (after `--`): `--dump-baseline=<res:// or absolute path>` writes the baseline and quits;
## `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail).

const ZONE_SCENE := "res://scenes/world/MainGateExterior.tscn"
const BASELINE_PATH := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch3.json"
const TILESET_PATH := "res://assets/tilesets/campus_ground.tres"
const TEXTURES := {
	"res://assets/sprites/ground/grass_ground_tile.png": "grass",
	"res://assets/sprites/ground/paved_walkway_tile.png": "walkway",
	"res://assets/sprites/ground/asphalt_road_tile.png": "asphalt",
}
const SOURCE_MATERIAL := {0: "grass", 1: "grass", 2: "walkway", 3: "asphalt"}
const CELL := 64
const EPS := 0.001

## Original blockout ground surfaces (world px), drawn in this order (later wins). Batch 1A must keep them.
const GROUND_FILL := Rect2(-2400, -1800, 5400, 3750)
const SURFACES := [
	["Sidewalk", Rect2(-2400, 1400, 5400, 60), "walkway"],
	["MainRoad", Rect2(-2400, 1460, 5400, 340), "asphalt"],
	["WestPalmPath", Rect2(-1450, -1080, 120, 2480), "walkway"],
	["NorthPath", Rect2(-1450, -1080, 2810, 120), "walkway"],
	["EastPath", Rect2(1260, -1080, 100, 1880), "walkway"],
	["SouthPath", Rect2(-1450, 720, 2810, 80), "walkway"],
]

var _zone: Node2D
var _failures := 0
var _checks := 0


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[GROUND] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	_zone = (load(ZONE_SCENE) as PackedScene).instantiate() as Node2D
	add_child(_zone)
	await get_tree().physics_frame
	await get_tree().process_frame
	var dump_path := _arg_value("--dump-baseline=")
	if dump_path != "":
		_dump_baseline(dump_path)
		get_tree().quit(0)
		return
	_run_checks()
	print("[GROUND] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _arg_value(prefix: String) -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with(prefix):
			return arg.trim_prefix(prefix)
	return ""


# --- Snapshot (baseline) -------------------------------------------------------------------------

func _snapshot() -> Dictionary:
	var nodes := {}
	_snapshot_node(_zone, ".", nodes)
	var markings := {}
	for line: Line2D in _zone.get_node("Ground").find_children("*", "Line2D", true, false):
		markings[String(line.name)] = {
			"xform": _xf(line.global_transform), "points": _pts(line.points), "width": line.width,
			"color": _col(line.default_color), "closed": line.closed, "visible": line.is_visible_in_tree(),
			"light_mask": line.light_mask, "z": _effective_z(line),
		}
	return {"zone_id": _zone.get("zone_id"), "nodes": nodes, "markings": markings}


func _snapshot_node(node: Node, path: String, out: Dictionary) -> void:
	if node.get_parent() == _zone and node.name == &"Ground":
		return
	var rec := {"class": node.get_class(), "scene": node.scene_file_path, "groups": _groups(node)}
	if node is Node2D:
		var n2 := node as Node2D
		rec["xform"] = _xf(n2.global_transform)
		rec["y_sort"] = n2.y_sort_enabled
	if node is CanvasItem:
		var ci := node as CanvasItem
		rec["z"] = _effective_z(ci)
		rec["visible"] = ci.visible
		rec["light_mask"] = ci.light_mask
	if node is CollisionObject2D:
		rec["layer"] = (node as CollisionObject2D).collision_layer
		rec["mask"] = (node as CollisionObject2D).collision_mask
	if node is CollisionShape2D:
		var cs := node as CollisionShape2D
		rec["disabled"] = cs.disabled
		rec["shape"] = _shape(cs.shape)
	if node is LightOccluder2D:
		var lo := node as LightOccluder2D
		rec["occluder_mask"] = lo.occluder_light_mask
		rec["occluder"] = _pts(lo.occluder.polygon) if lo.occluder else []
	for key in ["zone_id", "spawn_id", "destination_zone_id", "destination_spawn_id", "prompt_text",
			"pickup_id", "footprint_size", "wall_height", "casts_shadow"]:
		if key in node:
			rec[key] = var_to_str(node.get(key))
	out[path] = rec
	var internal_index := 0
	for child in node.get_children(true):
		var child_path: String
		if child.get_parent() == node and node.get_children(false).has(child):
			child_path = "%s/%s" % [path, child.name]
		else:
			child_path = "%s/~internal%d:%s" % [path, internal_index, child.get_class()]
			internal_index += 1
		_snapshot_node(child, child_path, out)


func _dump_baseline(path: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		push_error("[GROUND] can't write baseline %s: %s" % [path, error_string(FileAccess.get_open_error())])
		get_tree().quit(1)
		return
	var snap := _snapshot()
	file.store_string(JSON.stringify(snap, "\t", true, true))
	file.close()
	print("[GROUND] baseline written: %s (%d nodes outside Ground, %d markings)" % [path, snap.nodes.size(), snap.markings.size()])


# --- Checks --------------------------------------------------------------------------------------

func _run_checks() -> void:
	var baseline := _load_baseline()
	_check(not baseline.is_empty(), "baseline loaded from %s" % BASELINE_PATH)
	var ground := _zone.get_node_or_null("Ground") as Node2D
	_check(ground != null, "zone loads and has Ground")
	if ground == null or baseline.is_empty():
		return
	_check(_zone.get("zone_id") == "main_gate_exterior" and baseline.zone_id == "main_gate_exterior",
		"zone_id main_gate_exterior unchanged")
	_check_structure(ground)
	var tiles := ground.get_node_or_null("Tiles") as TileMapLayer
	var strips := _strips(ground)
	if tiles != null:
		_check_strips(strips)
		_check_coverage(tiles, strips)
	var now := _snapshot()
	_check_markings(baseline.markings, now.markings)
	_check_nodes(baseline.nodes, now.nodes)


func _load_baseline() -> Dictionary:
	if not FileAccess.file_exists(BASELINE_PATH):
		return {}
	var data = JSON.parse_string(FileAccess.get_file_as_string(BASELINE_PATH))
	return data if data is Dictionary else {}


func _check_structure(ground: Node2D) -> void:
	_check(ground.z_index == -10 and ground.z_as_relative and not ground.y_sort_enabled and ground.position == Vector2.ZERO,
		"Ground at origin, z -10, not Y-sorted (z %d, y_sort %s)" % [ground.z_index, ground.y_sort_enabled])
	var names := []
	for child in ground.get_children():
		names.append(String(child.name))
	_check(names == ["Tiles", "EdgeStrips", "Markings"], "Ground children in draw order Tiles, EdgeStrips, Markings (got %s)" % [names])
	_check(not ground.is_in_group("blockout_placeholder"), "Ground itself is not a placeholder (production tiles)")
	var markings := ground.get_node_or_null("Markings")
	_check(markings != null and markings.is_in_group("blockout_placeholder"), "Ground/Markings is in blockout_placeholder")
	var tiles := ground.get_node_or_null("Tiles") as TileMapLayer
	_check(tiles != null and tiles.tile_set != null and tiles.tile_set.resource_path == TILESET_PATH,
		"Ground/Tiles is a TileMapLayer on %s" % TILESET_PATH)
	if tiles != null:
		_check(tiles.position == Vector2.ZERO and tiles.z_index == 0 and tiles.z_as_relative and not tiles.y_sort_enabled
			and tiles.tile_set.tile_size == Vector2i(CELL, CELL),
			"Tiles at origin (grid on world multiples of 64), relative z 0, not Y-sorted")
	var leftovers := 0
	var holder := ground.get_node_or_null("EdgeStrips")
	for poly: Polygon2D in ground.find_children("*", "Polygon2D", true, false):
		if holder == null or not holder.is_ancestor_of(poly):
			leftovers += 1
	_check(leftovers == 0, "no placeholder ground Polygon2D left outside EdgeStrips (%d)" % leftovers)


func _strips(ground: Node2D) -> Array[Polygon2D]:
	var out: Array[Polygon2D] = []
	var holder := ground.get_node_or_null("EdgeStrips")
	if holder != null:
		for poly: Polygon2D in holder.find_children("*", "Polygon2D", true, false):
			out.append(poly)
	return out


func _check_strips(strips: Array[Polygon2D]) -> void:
	var boundary_values := {}
	for s in SURFACES:
		var r: Rect2 = s[1]
		for v in [r.position.x, r.end.x, r.position.y, r.end.y]:
			boundary_values[v] = true
	var bad := []
	for poly in strips:
		var tex_path := poly.texture.resource_path if poly.texture else ""
		var ok := TEXTURES.has(tex_path) and poly.texture_repeat == CanvasItem.TEXTURE_REPEAT_ENABLED \
			and poly.uv.is_empty() and poly.texture_offset == Vector2.ZERO and poly.texture_scale == Vector2.ONE \
			and poly.texture_rotation == 0.0 and poly.offset == Vector2.ZERO and poly.global_transform == Transform2D.IDENTITY \
			and poly.color == Color.WHITE and poly.self_modulate == Color.WHITE and poly.modulate == Color.WHITE \
			and poly.z_index == 0 and poly.z_as_relative and poly.light_mask == 1
		for p in poly.polygon:
			for v in [p.x, p.y]:
				if not boundary_values.has(v) and fmod(v, CELL) != 0.0:
					ok = false
		if not ok:
			bad.append(String(poly.get_path()))
	_check(strips.size() > 0 and bad.is_empty(),
		"%d edge strips: production texture, repeat on, no UV/offset/tint, vertices on original edges or the 64 px grid (bad: %s)" % [strips.size(), bad])


func _expected(p: Vector2) -> String:
	var mat := "grass" if GROUND_FILL.has_point(p) else ""
	for s in SURFACES:
		if (s[1] as Rect2).has_point(p):
			mat = s[2]
	return mat


func _actual(p: Vector2, tiles: TileMapLayer, strips: Array[Polygon2D]) -> String:
	var mat := ""
	for poly in strips:
		if Geometry2D.is_point_in_polygon(p, poly.polygon):
			mat = TEXTURES.get(poly.texture.resource_path, "?")
	if mat != "":
		return mat
	var source := tiles.get_cell_source_id(tiles.local_to_map(p))
	return SOURCE_MATERIAL.get(source, "none")


func _check_coverage(tiles: TileMapLayer, strips: Array[Polygon2D]) -> void:
	var samples := 0
	var wrong := {}
	# Quarter-pixel offset: no lattice point lies exactly on an integer surface edge (ambiguous tie).
	var y := GROUND_FILL.position.y + 4.25
	while y < GROUND_FILL.end.y:
		var x := GROUND_FILL.position.x + 4.25
		while x < GROUND_FILL.end.x:
			samples += 1
			_compare(Vector2(x, y), tiles, strips, wrong)
			x += 8.0
		y += 8.0
	_check(wrong.is_empty(), "lattice: %d samples (8 px) over GroundFill match the original layout (%d wrong, e.g. %s)" % [samples, wrong.size(), wrong.keys().slice(0, 5)])
	var edge_samples := 0
	var edge_wrong := {}
	for s in SURFACES:
		var r: Rect2 = s[1]
		for i in 25:
			var t := (i + 0.5) / 25.0
			var xs := r.position.x + r.size.x * t
			var ys := r.position.y + r.size.y * t
			for p in [Vector2(r.position.x - 0.5, ys), Vector2(r.position.x + 0.5, ys),
					Vector2(r.end.x - 0.5, ys), Vector2(r.end.x + 0.5, ys),
					Vector2(xs, r.position.y - 0.5), Vector2(xs, r.position.y + 0.5),
					Vector2(xs, r.end.y - 0.5), Vector2(xs, r.end.y + 0.5)]:
				if GROUND_FILL.has_point(p):
					edge_samples += 1
					_compare(p, tiles, strips, edge_wrong)
	_check(edge_wrong.is_empty(), "edges: %d samples 0.5 px either side of every original surface edge match (%d wrong, e.g. %s)" % [edge_samples, edge_wrong.size(), edge_wrong.keys().slice(0, 5)])
	var used := tiles.get_used_rect()
	var fill_cells := Rect2i(Vector2i((GROUND_FILL.position / CELL).floor()), Vector2i.ZERO)
	fill_cells = fill_cells.expand(Vector2i((GROUND_FILL.end / CELL).ceil()))
	var counts := {}
	var empty := 0
	for cy in range(fill_cells.position.y, fill_cells.end.y):
		for cx in range(fill_cells.position.x, fill_cells.end.x):
			var src := tiles.get_cell_source_id(Vector2i(cx, cy))
			if src == -1:
				empty += 1
			else:
				counts[src] = counts.get(src, 0) + 1
	_check(empty == 0 and used == fill_cells, "every cell touching GroundFill is filled, none outside (cells %s, used %s, empty %d); per source %s" % [fill_cells, used, empty, counts])


func _compare(p: Vector2, tiles: TileMapLayer, strips: Array[Polygon2D], wrong: Dictionary) -> void:
	var expected := _expected(p)
	var actual := _actual(p, tiles, strips)
	if expected != actual:
		wrong["%s exp %s got %s" % [p, expected, actual]] = true


func _check_markings(before: Dictionary, now: Dictionary) -> void:
	_check(before.keys().size() == 4 and _same(before, now),
		"markings %s keep global transform, points, width, colour, z (%d before, %d now)" % [before.keys(), before.size(), now.size()])


func _check_nodes(before: Dictionary, now: Dictionary) -> void:
	var missing := []
	var added := []
	var changed := []
	for key in before:
		if not now.has(key):
			missing.append(key)
		elif not _same(before[key], now[key]):
			changed.append(key)
	for key in now:
		if not before.has(key):
			added.append(key)
	_check(missing.is_empty() and added.is_empty() and changed.is_empty(),
		"%d nodes outside Ground identical to baseline (missing %s, added %s, changed %s)" % [before.size(), missing.slice(0, 5), added.slice(0, 5), changed.slice(0, 5)])
	var doors := 0
	var spawns := 0
	var bodies := 0
	var shapes := 0
	var occluders := 0
	var vegetation := 0
	for key: String in before:
		var rec: Dictionary = before[key]
		doors += 1 if rec.has("destination_zone_id") else 0
		spawns += 1 if rec.has("spawn_id") else 0
		bodies += 1 if rec.has("layer") else 0
		shapes += 1 if rec.has("shape") else 0
		occluders += 1 if rec.has("occluder") else 0
		vegetation += 1 if key.begins_with("./Objects/Vegetation/") and key.count("/") == 4 else 0
	print("[GROUND] baseline covers %d doors, %d spawns, %d collision bodies, %d shapes, %d occluders, %d vegetation instances" % [doors, spawns, bodies, shapes, occluders, vegetation])


func _same(a, b) -> bool:
	if typeof(a) in [TYPE_FLOAT, TYPE_INT] and typeof(b) in [TYPE_FLOAT, TYPE_INT]:
		return absf(float(a) - float(b)) <= EPS
	if a is Dictionary and b is Dictionary:
		if a.size() != b.size():
			return false
		for k in a:
			if not b.has(k) or not _same(a[k], b[k]):
				return false
		return true
	if a is Array and b is Array:
		if a.size() != b.size():
			return false
		for i in a.size():
			if not _same(a[i], b[i]):
				return false
		return true
	return a == b


# --- Serialisation helpers (JSON-friendly) ------------------------------------------------------

func _xf(t: Transform2D) -> Array:
	return [t.x.x, t.x.y, t.y.x, t.y.y, t.origin.x, t.origin.y]


func _pts(points: PackedVector2Array) -> Array:
	var out := []
	for p in points:
		out.append([p.x, p.y])
	return out


func _col(c: Color) -> Array:
	return [c.r, c.g, c.b, c.a]


func _groups(node: Node) -> Array:
	var out := []
	for g in node.get_groups():
		if not String(g).begins_with("_"):
			out.append(String(g))
	out.sort()
	return out


func _effective_z(item: CanvasItem) -> int:
	var z := 0
	var node: Node = item
	while node is CanvasItem:
		z += (node as CanvasItem).z_index
		if not (node as CanvasItem).z_as_relative:
			break
		node = node.get_parent()
	return z


func _shape(shape: Shape2D) -> Dictionary:
	if shape is RectangleShape2D:
		return {"rect": [(shape as RectangleShape2D).size.x, (shape as RectangleShape2D).size.y]}
	if shape is CircleShape2D:
		return {"circle": (shape as CircleShape2D).radius}
	return {"other": shape.get_class() if shape else "none"}

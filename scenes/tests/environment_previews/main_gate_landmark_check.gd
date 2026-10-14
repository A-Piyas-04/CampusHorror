extends Node2D
## TEMPORARY Milestone G Batch 3 check for the REAL Main Gate landmark (test-only).
## Instances scenes/world/MainGateExterior.tscn and verifies:
## - Objects/Buildings/MainGateLandmark keeps its root transform and SpawnMainGateEntry, and its blockout art
##   (BlockoutBlock piers, leaves, pavilion, columns, placeholder plaza and Overhead roof/arch/canopy) is gone.
## - The production gate: Tower (MainGateTower), GateLeaves (MainGateLeaves), Pavilion (MainGatePavilion) at their
##   documented positions with ContactShadows, sprites on light mask 2, collision from the generated scenes,
##   two light-mask-1 occluders, walkway-textured GatePlaza / PassageFloor on the landmark ground band (z -9).
## - Collision: the gate leaves still stop a 28 x 12 player footprint at y 1390 across the passage; the passage
##   jambs, tower piers and pavilion room are solid; the pavilion closes the corner with PrototypeEdgeWest and the
##   tower's east face meets the SouthWall run at x -1250.
## - main_gate_ground_baseline_batch3.json differs from batch2 only inside the replaced MainGateLandmark art (the
##   landmark root and the spawn are identical).
## - Batch 3A: main_gate_ground_baseline_batch3a.json equals the current zone and differs from batch3 only by the
##   overhead layer sprites / fade areas added inside Tower and Pavilion and the Pavilion root's Y-sort flag (every
##   collision shape, occluder, spawn, door and transform is identical). Since Batch 4 the comparison with the
##   current zone skips the replaced CDSExterior art (main_gate_cds_check.gd verifies it).
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail).

const ZONE_SCENE := "res://scenes/world/MainGateExterior.tscn"
const BATCH2_BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch2.json"
const BATCH3_BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch3.json"
const BATCH3A_BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch3a.json"
## Batch 3A layer nodes inside the gate parts (added to batch3), and the one record allowed to change.
const BATCH3A_ADDED := ["Tower/Roof", "Tower/RoofFade", "Tower/RoofFade/ShapeBehind", "Pavilion/Room",
	"Pavilion/RoomRoof", "Pavilion/Canopy", "Pavilion/RoomRoofFade", "Pavilion/RoomRoofFade/ShapeBehind",
	"Pavilion/CanopyFade", "Pavilion/CanopyFade/ShapePorch"]
const BATCH3A_CHANGED := {"Pavilion": ["y_sort"]}
const SNAPSHOT_SCRIPT := preload("res://scenes/tests/environment_previews/main_gate_ground_check.gd")
const SHADOW_SCENE := "res://scenes/props/common/ContactShadow.tscn"
const BLOCK_SCENE := "res://scenes/world/blockout/BlockoutBlock.tscn"
const WALKWAY := "res://assets/sprites/ground/paved_walkway_tile.png"
const MAIN_GATE := "./Objects/Buildings/MainGateLandmark"
const MAIN_GATE_SPAWN := MAIN_GATE + "/SpawnMainGateEntry"
const CDS := "./Objects/Buildings/CDSExterior"
const CDS_KEPT := ["Canteen", "TableTennis", "IndoorBasketball", "TableTennis/DoorCdsMainEntry", "TableTennis/SpawnOutsideCdsEntrance"]
const ORIGIN := Vector2(-1390, 1400)
## name -> [scene, local position, ContactShadow children]
const PARTS := {
	"Tower": ["res://scenes/props/landmarks/MainGateTower.tscn", Vector2(0, 7), ["ContactShadowWest", "ContactShadowEast"]],
	"GateLeaves": ["res://scenes/props/landmarks/MainGateLeaves.tscn", Vector2(0, -5), []],
	"Pavilion": ["res://scenes/props/landmarks/MainGatePavilion.tscn", Vector2(-172, 58), ["ContactShadowRoom", "ContactShadowPorch"]],
}
## Expected global collision rects (x, y, w, h) of the generated scenes at those positions.
const RECTS := {
	"Tower/Body/CollisionWestPier": Rect2(-1562, 1268.35, 95.84, 138.65),
	"Tower/Body/CollisionEastPier": Rect2(-1313.84, 1268.35, 63.84, 138.65),
	"GateLeaves/Body/Collision": Rect2(-1466.16, 1390, 152.32, 10),
	"Pavilion/Body/CollisionRoom": Rect2(-1750, 1260, 188, 140),
}
const FOOTPRINT := Vector2(28, 12)
const GATE_STOP_Y := 1390.0
const RECT_EPS := 0.05
## move_and_collide stops up to ~0.5 px short of a face (physics safe margin).
const STOP_EPS := 0.5

var _zone: Node2D
var _gate: Node2D
var _snapper: Node
var _failures := 0
var _checks := 0


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[LANDMARK] %s %s" % ["ok  " if ok else "FAIL", label])


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
	print("[LANDMARK] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _run_checks() -> void:
	_gate = _zone.get_node_or_null(NodePath(MAIN_GATE.trim_prefix("./"))) as Node2D
	_check(_zone.get("zone_id") == "main_gate_exterior" and _gate != null,
		"zone loads (zone_id main_gate_exterior) and has Objects/Buildings/MainGateLandmark")
	if _gate == null:
		return
	_check(_gate.global_position == ORIGIN and _gate.y_sort_enabled and _gate.z_index == 0,
		"landmark root at %s, Y-sorted, z 0" % [_gate.global_position])
	_check_spawn()
	_check_blockout_gone()
	_check_parts()
	_check_overhead_layers()
	_check_paving()
	_check_occluders()
	_check_collision_rects()
	_check_probes()
	_check_baselines()
	_check(_zone.find_children("*", "CharacterBody2D", true, false).is_empty(),
		"the zone itself contains no CharacterBody2D (the one Player belongs to Main)")


func _check_spawn() -> void:
	var spawn := _gate.get_node_or_null("SpawnMainGateEntry") as Node2D
	_check(spawn != null and spawn.get("spawn_id") == "main_gate_entry" and spawn.position == Vector2(0, -440)
		and spawn.global_position == Vector2(-1390, 960),
		"SpawnMainGateEntry unchanged: spawn_id main_gate_entry, local (0, -440), world (-1390, 960)")


func _check_blockout_gone() -> void:
	var bad := []
	for node in _gate.find_children("*", "", true, false):
		if node.is_in_group("blockout_placeholder") or node.scene_file_path == BLOCK_SCENE or node is Label:
			bad.append(String(_gate.get_path_to(node)))
	for old_name in ["PierWest", "PierEast", "SidePavilion", "PavilionColumn1", "PavilionColumn2", "PavilionColumn3", "Overhead"]:
		if _gate.has_node(old_name):
			bad.append(old_name)
	_check(bad.is_empty() and not _gate.is_in_group("blockout_placeholder"),
		"no blockout block, placeholder group, Label or old blockout node left in the landmark (%s)" % [bad])


func _check_parts() -> void:
	for part_name: String in PARTS:
		var spec: Array = PARTS[part_name]
		var part := _gate.get_node_or_null(part_name) as Node2D
		var sprite := part.get_node_or_null("Sprite") as Sprite2D if part else null
		var shadows_ok := true
		if part:
			var names := []
			for child in part.get_children():
				if child.scene_file_path == SHADOW_SCENE:
					names.append(String(child.name))
			shadows_ok = names == spec[2]
		_check(part != null and part.scene_file_path == spec[0] and part.position == spec[1] and part.z_index == 0
			and sprite != null and sprite.texture != null and sprite.light_mask == 2 and _effective_z(sprite) == 0
			and shadows_ok,
			"%s = %s at local %s, sprite light mask 2 / z 0, ContactShadows %s" % [part_name, spec[0].get_file(), spec[1], spec[2]])
	var tower := _gate.get_node_or_null("Tower") as Node2D
	var leaves := _gate.get_node_or_null("GateLeaves") as Node2D
	var pier00 := _zone.get_node_or_null("Objects/Boundary/SouthWall/Pier00") as Node2D
	_check(tower and leaves and pier00 and leaves.global_position.y < tower.global_position.y
		and pier00.global_position.y < tower.global_position.y,
		"Y-sort: the leaves (y %.0f) draw before the tower (y %.0f), which draws over the wall's Pier00 (y %.0f) at the gate join"
		% [leaves.global_position.y if leaves else NAN, tower.global_position.y if tower else NAN, pier00.global_position.y if pier00 else NAN])


## Batch 3A: separately rendered layers. name -> [texture, global sort y, effective z, fade area or ""].
const LAYERS := {
	"Tower/Roof": ["main_gate_tower__roof.png", 1407.0, 10, "Tower/RoofFade"],
	"Pavilion/Room": ["main_gate_pavilion__room.png", 1400.0, 0, ""],
	"Pavilion/RoomRoof": ["main_gate_pavilion__room_roof.png", 1400.0, 0, "Pavilion/RoomRoofFade"],
	"Pavilion/Canopy": ["main_gate_pavilion__canopy.png", 1458.0, 0, "Pavilion/CanopyFade"],
}


func _check_overhead_layers() -> void:
	var pavilion := _gate.get_node_or_null("Pavilion") as Node2D
	_check(pavilion != null and pavilion.y_sort_enabled and not (_gate.get_node("Tower") as Node2D).y_sort_enabled,
		"Pavilion root is Y-sorted (its Room sorts on the wall line, columns and canopy on the column line); Tower is not")
	for path: String in LAYERS:
		var spec: Array = LAYERS[path]
		var sprite := _gate.get_node_or_null(path) as Sprite2D
		var base := sprite.get_parent().get_node_or_null("Sprite") as Sprite2D if sprite else null
		_check(sprite != null and base != null and sprite.texture != null and sprite.texture.resource_path.get_file() == spec[0]
			and absf(sprite.global_position.y - spec[1]) < 0.01 and _effective_z(sprite) == spec[2]
			and sprite.light_mask == 2 and sprite.modulate == Color.WHITE and sprite.scale == base.scale,
			"%s: %s, sort y %.0f, z %d, light mask 2, opaque at rest" % [path, spec[0], spec[1], spec[2]])
		if spec[3] == "":
			continue
		var area := _gate.get_node_or_null(spec[3]) as Area2D
		var paths: Array = area.get("target_paths") if area else []
		_check(area != null and area.collision_layer == 0 and area.collision_mask == 2 and not area.monitorable
			and paths.size() == 1 and area.get_node_or_null(paths[0]) == sprite,
			"%s: fades only %s; layer 0 / mask 2 (player body), not monitorable, so it blocks and triggers nothing" % [spec[3], path])


func _check_paving() -> void:
	for poly_name in ["GatePlaza", "PassageFloor"]:
		var poly := _gate.get_node_or_null(poly_name) as Polygon2D
		_check(poly != null and poly.z_index == -9 and poly.texture != null and poly.texture.resource_path == WALKWAY
			and poly.texture_repeat == CanvasItem.TEXTURE_REPEAT_ENABLED and poly.texture_offset == Vector2(18, 56)
			and poly.color == Color.WHITE,
			"%s: paved_walkway_tile.png, repeat on, z -9, offset (18, 56) = world tile phase" % poly_name)


func _check_occluders() -> void:
	var count := 0
	for child in _gate.get_children():
		if child is LightOccluder2D:
			var lo := child as LightOccluder2D
			count += 1 if lo.occluder != null and lo.occluder_light_mask == 1 and lo.occluder.polygon.size() >= 4 else 0
	_check(count == 2, "%d light-mask-1 occluders over the tower piers and pavilion room (expected 2)" % count)


func _check_collision_rects() -> void:
	for path: String in RECTS:
		var cs := _gate.get_node_or_null(path) as CollisionShape2D
		var got := _global_rect(cs) if cs and cs.shape is RectangleShape2D else Rect2()
		var want: Rect2 = RECTS[path]
		var body := cs.get_parent() as StaticBody2D if cs else null
		_check(cs != null and body != null and body.collision_layer == 1 and body.collision_mask == 0
			and got.position.distance_to(want.position) < RECT_EPS and got.size.distance_to(want.size) < RECT_EPS,
			"%s: layer 1 / mask 0, global rect %s (expected %s)" % [path, got, want])


func _check_probes() -> void:
	var probe := _make_probe()
	var leaves := _gate.get_node_or_null("GateLeaves")
	var bad := []
	var x := -1466.16 + FOOTPRINT.x / 2.0 + 0.5
	var count := 0
	while x <= -1313.84 - FOOTPRINT.x / 2.0 - 0.5:
		var r := _probe_end(probe, Vector2(x, 1250), Vector2(0, 200))
		if r.collider == null or not leaves.is_ancestor_of(r.collider) or absf(r.end.y - GATE_STOP_Y) > STOP_EPS:
			bad.append("%.1f:%.3f" % [x, r.end.y])
		count += 1
		x += 12.0
	_check(bad.is_empty() and count >= 10,
		"walking south through the passage (%d probes across x -1451.7..-1328.3) stops at the leaves at y %.0f +- %.1f (bad %s)" % [count, GATE_STOP_Y, STOP_EPS, bad])
	var axis := _probe_end(probe, Vector2(-1390, 1250), Vector2(0, 200))
	_check(axis.collider != null and absf(axis.end.y - GATE_STOP_Y) < STOP_EPS,
		"on the gate axis (the pre-edit runtime walk) the stop is y %.3f (pre-edit 1389.924 runtime / 1390 geometric)" % axis.end.y)

	var west_jamb := _probe_end(probe, Vector2(-1390, 1380), Vector2(-200, 0))
	var east_jamb := _probe_end(probe, Vector2(-1390, 1380), Vector2(200, 0))
	_check(west_jamb.collider != null and absf(west_jamb.end.x - (-1466.16 + FOOTPRINT.x / 2.0)) < STOP_EPS
		and east_jamb.collider != null and absf(east_jamb.end.x - (-1313.84 - FOOTPRINT.x / 2.0)) < STOP_EPS,
		"passage jambs are solid: walking west / east inside the passage stops at x %.3f / %.3f" % [west_jamb.end.x, east_jamb.end.x])

	var stops := []
	var missed := []
	for px in [-1690.0, -1640.0, -1580.0, -1562.0, -1540.0, -1490.0, -1300.0, -1270.0, -1258.0]:
		var r := _probe_end(probe, Vector2(px, 1150), Vector2(0, 300))
		stops.append("%.0f:%.2f" % [px, r.end.y])
		if r.collider == null or r.end.y > 1270.0:
			missed.append(px)
	_check(missed.is_empty(),
		"walking south over the pavilion room and tower piers is blocked north of the wall line (x:stop y %s; missed %s)" % [stops, missed])

	var corner := _probe_end(probe, Vector2(-1660, 1255), Vector2(-100, 0))
	var corner_diag := _probe_end(probe, Vector2(-1680, 1250), Vector2(-60, 200))
	_check(corner.collider != null and corner.end.x > -1700.0 + FOOTPRINT.x / 2.0 - 0.5
		and corner_diag.collider != null and corner_diag.end.y <= 1260.15,
		"south-west corner closed: walking west at y 1255 stops at x %.3f (PrototypeEdgeWest face -1700); diagonal south-west stops at y %.3f (room face 1260)"
		% [corner.end.x, corner_diag.end.y])
	var gate_join := _probe_end(probe, Vector2(-1300, 1200), Vector2(0, 200))
	var join_west := _probe_end(probe, Vector2(-1200, 1394), Vector2(-120, 0))
	_check(gate_join.collider != null and gate_join.end.y <= 1268.5 and join_west.collider != null
		and join_west.end.x > -1250.0 + FOOTPRINT.x / 2.0 - 0.5,
		"tower / wall join closed: south at x -1300 stops at y %.3f, west along the wall stops at x %.3f (tower east face -1250)"
		% [gate_join.end.y, join_west.end.x])
	probe.free()


func _check_baselines() -> void:
	var batch2 := _load_json(BATCH2_BASELINE)
	var batch3 := _load_json(BATCH3_BASELINE)
	var batch3a := _load_json(BATCH3A_BASELINE)
	var now: Dictionary = _snapper.call("_snapshot")
	_check(not batch3a.is_empty() and _same(_without_cds_art(batch3a), _without_cds_art(now)),
		"versioned baseline %s exists and equals the current zone outside the Batch 4 CDS art (%d nodes)" % [BATCH3A_BASELINE.get_file(), batch3a.get("nodes", {}).size()])
	_check_batch3a_diff(batch3, batch3a)
	if batch2.is_empty() or batch3.is_empty():
		_check(false, "batch2 and batch3 baselines load")
		return
	var outside := []
	var removed := 0
	var added := 0
	for key: String in batch2.nodes:
		if _gate_art(key):
			removed += 0 if batch3.nodes.has(key) and _same(batch2.nodes[key], batch3.nodes[key]) else 1
		elif not batch3.nodes.has(key) or not _same(batch2.nodes[key], batch3.nodes[key]):
			outside.append(key)
	for key: String in batch3.nodes:
		if not batch2.nodes.has(key):
			if _gate_art(key):
				added += 1
			else:
				outside.append(key)
	_check(outside.is_empty() and _same(batch2.markings, batch3.markings) and batch2.zone_id == batch3.zone_id
		and removed > 0 and added > 0,
		"batch3 differs from batch2 only inside the MainGateLandmark art (%d blockout records removed or changed, %d added; outside %s); the landmark root, spawn and markings are identical"
		% [removed, added, outside.slice(0, 5)])


func _check_batch3a_diff(batch3: Dictionary, batch3a: Dictionary) -> void:
	if batch3.is_empty() or batch3a.is_empty():
		_check(false, "batch3 and batch3a baselines load")
		return
	var added := []
	var unexpected := []
	for key: String in batch3a.nodes:
		if not batch3.nodes.has(key):
			added.append(key.trim_prefix(MAIN_GATE + "/"))
	for key: String in batch3.nodes:
		var short := key.trim_prefix(MAIN_GATE + "/")
		if not batch3a.nodes.has(key):
			unexpected.append("removed " + short)
			continue
		var a: Dictionary = batch3.nodes[key]
		var b: Dictionary = batch3a.nodes[key]
		for field: String in a:
			if not b.has(field) or not _same(a[field], b[field]):
				if not (BATCH3A_CHANGED.get(short, []) as Array).has(field) or key == short:
					unexpected.append("%s.%s" % [short, field])
	added.sort()
	var want := BATCH3A_ADDED.duplicate()
	want.sort()
	_check(added == want and unexpected.is_empty() and _same(batch3.markings, batch3a.markings),
		"batch3a differs from batch3 only by the overhead layers %s and Pavilion.y_sort (unexpected %s)" % [added, unexpected.slice(0, 5)])


## Copy of a snapshot without the CDSExterior records replaced in Batch 4 (main_gate_cds_check.gd verifies those;
## the CDS root, the section nodes, the door and the spawn stay in).
func _without_cds_art(snap: Dictionary) -> Dictionary:
	var out := snap.duplicate()
	var nodes := {}
	for key: String in snap.get("nodes", {}):
		var rel := key.trim_prefix(CDS + "/")
		var art := key.begins_with(CDS + "/")
		for kept: String in CDS_KEPT:
			if rel == kept or (kept.contains("/") and rel.begins_with(kept + "/")):
				art = false
		if not art:
			nodes[key] = snap.nodes[key]
	out.nodes = nodes
	return out


func _gate_art(key: String) -> bool:
	var spawn := key == MAIN_GATE_SPAWN or key.begins_with(MAIN_GATE_SPAWN + "/")
	return key.begins_with(MAIN_GATE + "/") and not spawn


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
		return {"end": start + motion, "collider": null}
	return {"end": start + hit.get_travel(), "collider": hit.get_collider()}


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

extends Node2D
## TEMPORARY Milestone G Batch 1B check for the REAL main_gate_exterior vegetation (test-only).
## Instances scenes/world/MainGateExterior.tscn and compares it with the HISTORICAL pre-Batch-1B baseline
## (main_gate_ground_baseline.json, recorded before Batch 1A and still valid for everything except vegetation):
## - Every placeholder PalmTree / Tree instance is now a CoconutPalm / BroadleafTree with the same name,
##   parent and global transform; no placeholder vegetation is left.
## - Each replacement has one ContactShadow child with the composition-test settings.
## - Trunk collision (layer 1 / mask 0, production footprint) blocks a 28 x 12 player footprint from the
##   south and the north, and the area beside each trunk stays walkable.
## - Every other node outside Ground and the field markings are identical to the historical baseline, except
##   Objects/Boundary/SouthWall, which Batch 2 replaced (verified by main_gate_boundary_check.gd), and the
##   MainGateLandmark children Batch 3 replaced (verified by main_gate_landmark_check.gd; the landmark root
##   and SpawnMainGateEntry are still compared), and the CDSExterior children Batch 4 replaced (verified by
##   main_gate_cds_check.gd; the CDS root, section nodes, door and spawn are still compared).
## - The Batch 1B versioned baseline (main_gate_ground_baseline_batch1b.json) equals the current zone outside
##   SouthWall and the replaced gate, and differs from the historical baseline only inside the 42 vegetation
##   instances.
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail).

const ZONE_SCENE := "res://scenes/world/MainGateExterior.tscn"
const HISTORICAL_BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline.json"
const BATCH1B_BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch1b.json"
const SNAPSHOT_SCRIPT := preload("res://scenes/tests/environment_previews/main_gate_ground_check.gd")
const SHADOW_SCENE := "res://scenes/props/common/ContactShadow.tscn"
const VEGETATION := "./Objects/Vegetation"
const SOUTH_BOUNDARY := "./Objects/Boundary/SouthWall"
const MAIN_GATE := "./Objects/Buildings/MainGateLandmark"
const MAIN_GATE_SPAWN := MAIN_GATE + "/SpawnMainGateEntry"
const CDS := "./Objects/Buildings/CDSExterior"
const CDS_KEPT := ["Canteen", "TableTennis", "IndoorBasketball", "TableTennis/DoorCdsMainEntry", "TableTennis/SpawnOutsideCdsEntrance"]
## Placeholder scene -> [production scene, ContactShadow scale (from MainGateCompositionTest), expected count].
const REPLACEMENTS := {
	"res://scenes/props/PalmTree.tscn": ["res://scenes/props/vegetation/CoconutPalm.tscn", Vector2(0.6, 0.24), 27],
	"res://scenes/props/Tree.tscn": ["res://scenes/props/vegetation/BroadleafTree.tscn", Vector2(1.1, 0.4), 15],
}
const FOOTPRINT := Vector2(28, 12)
const EPS := 0.001

var _zone: Node2D
var _snapper: Node
var _failures := 0
var _checks := 0


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[VEGETATION] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	_zone = (load(ZONE_SCENE) as PackedScene).instantiate() as Node2D
	add_child(_zone)
	await get_tree().physics_frame
	await get_tree().process_frame
	_snapper = SNAPSHOT_SCRIPT.new()
	_snapper.set("_zone", _zone)
	_run_checks()
	_snapper.free()
	print("[VEGETATION] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _run_checks() -> void:
	var before := _load_json(HISTORICAL_BASELINE)
	_check(not before.is_empty(), "historical baseline loaded from %s" % HISTORICAL_BASELINE)
	if before.is_empty():
		return
	var instances := _baseline_instances(before.nodes)
	var counts := {}
	for key in instances:
		counts[instances[key]] = counts.get(instances[key], 0) + 1
	_check(counts.get("res://scenes/props/PalmTree.tscn", 0) == 27 and counts.get("res://scenes/props/Tree.tscn", 0) == 15
		and instances.size() == 42, "historical baseline records 27 PalmTree + 15 Tree instances (%s)" % [counts])
	var now: Dictionary = _snapper.call("_snapshot")
	_check_replacements(before.nodes, now.nodes, instances)
	_check_no_placeholders()
	_check_shadows(instances)
	_check_collision(instances)
	_check_unchanged(before, now, instances)
	_check_versioned_baseline(before, now, instances)


## Baseline keys of the vegetation instance roots (./Objects/Vegetation/<Group>/<Name>) -> placeholder scene.
func _baseline_instances(nodes: Dictionary) -> Dictionary:
	var out := {}
	for key: String in nodes:
		if key.begins_with(VEGETATION + "/") and key.count("/") == 4:
			out[key] = nodes[key].scene
	return out


func _in_instance(key: String, instances: Dictionary) -> bool:
	for root: String in instances:
		if key == root or key.begins_with(root + "/"):
			return true
	return false


func _in_south_boundary(key: String) -> bool:
	return key == SOUTH_BOUNDARY or key.begins_with(SOUTH_BOUNDARY + "/")


## Records replaced after Batch 1B: the Batch 2 south wall, the Batch 3 gate art (not the gate root or spawn) and
## the Batch 4 CDS art (not the CDS root, the section nodes, the door or the spawn).
func _replaced_later(key: String) -> bool:
	if _in_south_boundary(key):
		return true
	var spawn := key == MAIN_GATE_SPAWN or key.begins_with(MAIN_GATE_SPAWN + "/")
	return (key.begins_with(MAIN_GATE + "/") and not spawn) or _cds_art(key)


func _cds_art(key: String) -> bool:
	if not key.begins_with(CDS + "/"):
		return false
	var rel := key.trim_prefix(CDS + "/")
	for kept: String in CDS_KEPT:
		if rel == kept or (kept.contains("/") and rel.begins_with(kept + "/")):
			return false
	return true


func _node(key: String) -> Node:
	return _zone.get_node_or_null(NodePath(key.trim_prefix("./")))


func _check_replacements(before: Dictionary, now: Dictionary, instances: Dictionary) -> void:
	var wrong_scene := []
	var moved := []
	var bad_root := []
	var bad_body := []
	var bad_sprite := []
	var per_scene := {}
	for key: String in instances:
		var expected: String = REPLACEMENTS[instances[key]][0]
		var rec: Dictionary = now.get(key, {})
		if rec.get("scene", "") != expected:
			wrong_scene.append("%s: %s" % [key, rec.get("scene", "missing")])
			continue
		per_scene[expected] = per_scene.get(expected, 0) + 1
		if not _same(rec.xform, before[key].xform):
			moved.append(key)
		if rec["class"] != "Node2D" or rec.z != 0 or not rec.visible or rec.y_sort:
			bad_root.append(key)
		var body := _node(key + "/Body") as StaticBody2D
		var shape := _node(key + "/Body/Collision") as CollisionShape2D
		var reference := (load(expected) as PackedScene).instantiate()
		var ref_shape := reference.get_node("Body/Collision") as CollisionShape2D
		var root := _node(key) as Node2D
		if body == null or shape == null or body.collision_layer != before[key].layer or body.collision_mask != before[key].mask \
				or shape.disabled or not _same(_rect(shape.shape), _rect(ref_shape.shape)) \
				or not shape.global_position.is_equal_approx(root.global_position):
			bad_body.append(key)
		var sprite := _node(key + "/Sprite") as Sprite2D
		var ref_sprite := reference.get_node("Sprite") as Sprite2D
		if sprite == null or sprite.texture != ref_sprite.texture or sprite.light_mask != 2 or sprite.scale != ref_sprite.scale \
				or sprite.offset != ref_sprite.offset or _effective_z(sprite) != 0:
			bad_sprite.append(key)
		reference.free()
	_check(wrong_scene.is_empty() and per_scene.get("res://scenes/props/vegetation/CoconutPalm.tscn", 0) == 27
		and per_scene.get("res://scenes/props/vegetation/BroadleafTree.tscn", 0) == 15,
		"exactly 27 CoconutPalm + 15 BroadleafTree at the 42 original paths (%s; wrong %s)" % [per_scene, wrong_scene.slice(0, 5)])
	_check(moved.is_empty(), "all 42 keep their original name, parent and global transform (moved %s)" % [moved.slice(0, 5)])
	_check(bad_root.is_empty(), "instance roots are Node2D, z 0, visible, not Y-sorted themselves (bad %s)" % [bad_root.slice(0, 5)])
	_check(bad_body.is_empty(), "Body layer/mask equal the placeholder's (1/0), production footprint rectangle at the trunk origin (bad %s)" % [bad_body.slice(0, 5)])
	_check(bad_sprite.is_empty(), "Sprite = production texture, scale and offset, light mask 2, z 0 (bad %s)" % [bad_sprite.slice(0, 5)])
	var unsorted := []
	for key: String in instances:
		var node := _node(key).get_parent()
		while node != null and node != self:
			if not (node as Node2D).y_sort_enabled:
				unsorted.append(String(node.name))
			node = node.get_parent()
	_check(unsorted.is_empty(), "every ancestor up to the zone root is Y-sorted, so trunks sort with the Player (unsorted %s)" % [unsorted.slice(0, 5)])


func _check_no_placeholders() -> void:
	var vegetation := _node(VEGETATION)
	var leftovers := []
	for node in vegetation.find_children("*", "", true, false):
		if node.is_in_group("blockout_placeholder") or node.scene_file_path in REPLACEMENTS:
			leftovers.append(String(vegetation.get_path_to(node)))
	_check(leftovers.is_empty(), "no placeholder vegetation (PalmTree/Tree or blockout_placeholder) left under Objects/Vegetation (%s)" % [leftovers.slice(0, 5)])


func _check_shadows(instances: Dictionary) -> void:
	var bad := []
	for key: String in instances:
		var root := _node(key)
		var shadows := []
		for child in root.get_children():
			if child.name.begins_with("ContactShadow"):
				shadows.append(child)
		var expected_scale: Vector2 = REPLACEMENTS[instances[key]][1]
		var ok := shadows.size() == 1
		if ok:
			var s := shadows[0] as Sprite2D
			ok = s != null and s.scene_file_path == SHADOW_SCENE and s.position == Vector2.ZERO and s.rotation == 0.0 \
				and s.scale.is_equal_approx(expected_scale) and _effective_z(s) == -9 and s.visible and s.texture != null \
				and s.find_children("*", "CollisionObject2D", true, false).is_empty()
		if not ok:
			bad.append(key)
	_check(bad.is_empty(), "each of the 42 has exactly one ContactShadow child at its origin, z -9, palm scale (0.6, 0.24) / tree (1.1, 0.4), visible, no collision (bad %s)" % [bad.slice(0, 5)])


func _check_collision(instances: Dictionary) -> void:
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
	var south := []
	var north := []
	var beside := []
	for key: String in instances:
		var root := _node(key) as Node2D
		var body := _node(key + "/Body")
		var half: Vector2 = _rect((_node(key + "/Body/Collision") as CollisionShape2D).shape) / 2.0
		var trunk := root.global_position
		var from_south := _probe(probe, trunk + Vector2(0, 40), Vector2(0, -80))
		if from_south == null or from_south.get_collider() != body:
			south.append(key)
		var from_north := _probe(probe, trunk + Vector2(0, -30), Vector2(0, 80))
		if from_north == null or from_north.get_collider() != body:
			north.append(key)
		for side in [-1.0, 1.0]:
			var start := trunk + Vector2(side * (half.x + FOOTPRINT.x / 2.0 + 4.0), 40)
			var hit := _probe(probe, start, Vector2(0, -80))
			if hit != null and hit.get_collider() == body:
				beside.append("%s %s" % [key, side])
	probe.free()
	_check(south.is_empty(), "28 x 12 footprint walking north from 40 px south stops at every trunk (player in front) (missed %s)" % [south.slice(0, 5)])
	_check(north.is_empty(), "28 x 12 footprint walking south from 30 px north stops at every trunk (player behind) (missed %s)" % [north.slice(0, 5)])
	_check(beside.is_empty(), "walking past 4 px beside each trunk (under the crown) is not blocked by the trunk (blocked %s)" % [beside.slice(0, 5)])


func _probe(probe: CharacterBody2D, start: Vector2, motion: Vector2) -> KinematicCollision2D:
	probe.global_position = start
	return probe.move_and_collide(motion, true)


func _check_unchanged(before: Dictionary, now: Dictionary, instances: Dictionary) -> void:
	var missing := []
	var added := []
	var changed := []
	var compared := 0
	for key: String in before.nodes:
		if _in_instance(key, instances) or _replaced_later(key):
			continue
		compared += 1
		if not now.nodes.has(key):
			missing.append(key)
		elif not _same(before.nodes[key], now.nodes[key]):
			changed.append(key)
	for key: String in now.nodes:
		if not _in_instance(key, instances) and not _replaced_later(key) and not before.nodes.has(key):
			added.append(key)
	# 294 baseline nodes outside Ground minus 42 placeholder subtrees of 4 records (root, 2 polygons, collision)
	# minus the 3 blockout SouthWall records (block, collision, occluder) replaced in Batch 2
	# minus the 27 blockout MainGateLandmark records (all but the root and the spawn's 2) replaced in Batch 3
	# minus the 24 blockout CDSExterior records (all but the root, the 3 sections, the door and the spawn) replaced in Batch 4.
	_check(missing.is_empty() and added.is_empty() and changed.is_empty() and compared == 72 and before.nodes.size() == 294,
		"%d nodes outside Ground, the 42 vegetation instances, SouthWall and the replaced gate and CDS art identical to the historical baseline (missing %s, added %s, changed %s)" % [compared, missing.slice(0, 5), added.slice(0, 5), changed.slice(0, 5)])
	_check(before.zone_id == now.zone_id and _same(before.markings, now.markings),
		"zone_id and the %d field markings unchanged" % before.markings.size())


func _check_versioned_baseline(before: Dictionary, now: Dictionary, instances: Dictionary) -> void:
	var versioned := _load_json(BATCH1B_BASELINE)
	_check(not versioned.is_empty(), "versioned baseline loaded from %s" % BATCH1B_BASELINE)
	if versioned.is_empty():
		return
	var drift := []
	for key: String in versioned.nodes:
		if not _replaced_later(key) and (not now.nodes.has(key) or not _same(versioned.nodes[key], now.nodes[key])):
			drift.append(key)
	for key: String in now.nodes:
		if not _replaced_later(key) and not versioned.nodes.has(key):
			drift.append(key)
	_check(drift.is_empty() and _same(versioned.markings, now.markings) and versioned.zone_id == now.zone_id,
		"versioned baseline equals the current zone outside SouthWall and the replaced gate and CDS art (%d nodes; differ %s)" % [versioned.nodes.size(), drift.slice(0, 5)])
	var diff_outside := []
	for key: String in before.nodes:
		if not _in_instance(key, instances) and (not versioned.nodes.has(key) or not _same(before.nodes[key], versioned.nodes[key])):
			diff_outside.append(key)
	for key: String in versioned.nodes:
		if not _in_instance(key, instances) and not before.nodes.has(key):
			diff_outside.append(key)
	var diff_inside := 0
	for key: String in versioned.nodes:
		if _in_instance(key, instances) and (not before.nodes.has(key) or not _same(before.nodes[key], versioned.nodes[key])):
			diff_inside += 1
	_check(diff_outside.is_empty() and _same(before.markings, versioned.markings) and before.zone_id == versioned.zone_id
		and diff_inside > 0, "versioned baseline differs from the historical one only inside the 42 vegetation instances (%d records there; outside %s)" % [diff_inside, diff_outside.slice(0, 5)])


func _load_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	return data if data is Dictionary else {}


func _rect(shape: Shape2D) -> Vector2:
	return (shape as RectangleShape2D).size if shape is RectangleShape2D else Vector2(-1, -1)


func _effective_z(item: CanvasItem) -> int:
	return _snapper.call("_effective_z", item)


func _same(a, b) -> bool:
	if a is Vector2 and b is Vector2:
		return (a as Vector2).distance_to(b) <= EPS
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

extends Node2D
## TEMPORARY Milestone G Batch 4 check of the production CDS exterior in main_gate_exterior (test-only).
## Instances scenes/world/MainGateExterior.tscn plus the real scenes/player/Player.tscn and verifies, against the
## pre-edit record main_gate_ground_baseline_batch3a.json:
## - CDSExterior and its three section nodes keep their positions; the door and spawn keep paths, IDs and positions.
## - Each section's Collision body has exactly the former blockout rectangles (Mass + Veranda, 6 in total) and its
##   ShadowOccluder covers the former blockout occluders; no blockout placeholder is left under CDSExterior.
## - The real player's stop lines around the CDS (west facade, north of the canteen, east side, south of the hall)
##   equal PREEDIT_STOPS, measured with `--print-stops` on the refs/checkpoints/batch4-preedit zone.
## - The forecourt, the lawn west of the canteen and the walk from the spawn to the door stay free; the door prompt
##   appears at the door.
## - Each slice layer sorts at its section's south edge + slice bound; the canteen's NorthRoof fades only while the
##   player stands behind the canteen, with no snapping, and nothing else in the zone changes modulate.
## - Each CDS prop stays within its config's render.max_texture_px.
## Args (after `--`): `--quit-after-checks` quits with exit code 0 (pass) / 1 (fail);
## `--zone=<res path>` checks another zone scene; `--print-stops` only prints the stop lines and quits.

const ZONE_SCENE := "res://scenes/world/MainGateExterior.tscn"
const PLAYER_SCENE := "res://scenes/player/Player.tscn"
const BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch3a.json"
const BATCH4_BASELINE := "res://scenes/tests/environment_previews/main_gate_ground_baseline_batch4.json"
const CONFIGS := "res://assets/source/blender/configs/%s.json"
const CDS := "Objects/Buildings/CDSExterior"
const BASE_KEY := "./Objects/Buildings/CDSExterior"
const DOOR := "TableTennis/DoorCdsMainEntry"
const SPAWN := "TableTennis/SpawnOutsideCdsEntrance"
const PROMPT := "Press E to enter the CDS veranda"
## Ground depth: 32 px/m x sin(40 deg).
const DEPTH_PX_PER_M := 20.5692032
## section -> [prop instance, asset_id, {layer: slice bound (m north of the section's south face)}]
const SECTIONS := {
	"Canteen": ["CdsCanteen", "cds_canteen", {"Slice2": 10.139626, "NorthRoof": 19.829252}],
	"TableTennis": ["CdsTableTennis", "cds_table_tennis", {"Slice2": 13.774638}],
	"IndoorBasketball": ["CdsIndoorBasketball", "cds_indoor_basketball", {"Slice2": 11.54382, "Slice3": 22.487641}],
}
const FADE_LAYER := "Canteen/CdsCanteen/NorthRoof"
const FADE_AREA := "Canteen/CdsCanteen/NorthRoofFade"
const FADED := 0.35
## [label, start (feet, world), motion]
const STOPS := [
	["west facade, canteen y -900", Vector2(1400, -900), Vector2(120, 0)],
	["west facade, canteen y -700", Vector2(1400, -700), Vector2(120, 0)],
	["west facade, canteen y -560", Vector2(1400, -560), Vector2(120, 0)],
	["west facade, table tennis y -400", Vector2(1400, -400), Vector2(120, 0)],
	["west facade, forecourt / door y -200", Vector2(1400, -200), Vector2(120, 0)],
	["west facade, table tennis y -60", Vector2(1400, -60), Vector2(120, 0)],
	["west facade, hall y 300", Vector2(1400, 300), Vector2(120, 0)],
	["west facade, hall y 650", Vector2(1400, 650), Vector2(120, 0)],
	["north of the canteen x 1520", Vector2(1520, -1080), Vector2(0, 120)],
	["north of the canteen x 1800", Vector2(1800, -1080), Vector2(0, 120)],
	["east side, canteen y -800", Vector2(2080, -800), Vector2(-120, 0)],
	["east side, table tennis y -200", Vector2(2080, -200), Vector2(-120, 0)],
	["east side, hall y 400", Vector2(2080, 400), Vector2(-120, 0)],
	["south of the hall x 1515", Vector2(1515, 780), Vector2(0, -120)],
	["south of the hall x 1800", Vector2(1800, 780), Vector2(0, -120)],
]
const PREEDIT_STOPS := [
	Vector2(1465.625, -900), Vector2(1465.625, -700), Vector2(1465.625, -560), Vector2(1465.625, -400),
	Vector2(1465.625, -200), Vector2(1465.625, -60), Vector2(1465.625, 300), Vector2(1465.625, 650),
	Vector2(1520, -1000.3125), Vector2(1800, -1000.3125),
	Vector2(2014.375, -800), Vector2(2014.375, -200), Vector2(2014.375, 400),
	Vector2(1515, 712.03125), Vector2(1800, 712.03125),
]
## [label, start (feet, world), motion] walks that must stay free.
const FREE_WALKS := [
	["lawn between the flagpoles and the canteen facade, x 1460 from y -430 to -990", Vector2(1460, -430), Vector2(0, -560)],
	["spawn north across the forecourt to y -420", Vector2(1380, -200), Vector2(0, -220)],
	["spawn east to the door", Vector2(1380, -200), Vector2(72, 0)],
	["behind the canteen, through the NorthRoof fade area", Vector2(1740, -1150), Vector2(0, 145)],
]
## [label, feet (world), NorthRoof faded]
const FADE_CASES := [
	["at the CDS spawn", Vector2(1380, -200), false],
	["behind the canteen (centre)", Vector2(1740, -1010), true],
	["behind the canteen, against its north wall at the west end", Vector2(1500, -1002), true],
	["north of the fade area", Vector2(1740, -1150), false],
	["west of the fade area", Vector2(1440, -1050), false],
	["east of the fade area", Vector2(2040, -1050), false],
	["back at the CDS spawn", Vector2(1380, -200), false],
]
const EPS := 0.01

var _zone: Node2D
var _cds: Node2D
var _player: CharacterBody2D
var _baseline: Dictionary
var _failures := 0
var _checks := 0


func _check(ok: bool, label: String) -> void:
	_checks += 1
	_failures += 0 if ok else 1
	print("[CDS] %s %s" % ["ok  " if ok else "FAIL", label])


func _ready() -> void:
	var zone_path := _arg_value("--zone=")
	_zone = (load(zone_path if not zone_path.is_empty() else ZONE_SCENE) as PackedScene).instantiate() as Node2D
	add_child(_zone)
	_player = (load(PLAYER_SCENE) as PackedScene).instantiate() as CharacterBody2D
	add_child(_player)
	_cds = _zone.get_node(CDS) as Node2D
	await get_tree().physics_frame
	await get_tree().physics_frame
	if OS.get_cmdline_user_args().has("--print-stops"):
		for spec: Array in STOPS:
			var stop := _stop(spec[1], spec[2])
			print("[CDS] stop %s: Vector2(%.4f, %.4f)" % [spec[0], stop.x, stop.y])
		get_tree().quit(0)
		return
	_baseline = _load_json(BASELINE)
	await _run_checks()
	print("[CDS] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if OS.get_cmdline_user_args().has("--quit-after-checks"):
		get_tree().quit(0 if _failures == 0 else 1)


func _arg_value(prefix: String) -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with(prefix):
			return arg.trim_prefix(prefix)
	return ""


func _run_checks() -> void:
	_check(not _baseline.is_empty(), "pre-edit baseline loaded from %s" % BASELINE.get_file())
	if _baseline.is_empty():
		return
	_check_batch4_diff()
	_check_sections()
	_check_door_and_spawn()
	_check_collision()
	_check_occluders()
	_check_placeholders()
	_check_stops()
	_check_free_walks()
	await _check_prompt()
	_check_slices()
	_check_budget()
	await _check_fade_cases()
	await _check_fade_walk()


func _check_batch4_diff() -> void:
	var batch4 := _load_json(BATCH4_BASELINE)
	if batch4.is_empty():
		_check(false, "versioned baseline %s exists" % BATCH4_BASELINE.get_file())
		return
	var outside := []
	var changed := 0
	for key: String in _baseline.nodes:
		var same: bool = batch4.nodes.has(key) and _same(_baseline.nodes[key], batch4.nodes[key])
		if not same:
			if _cds_art(key):
				changed += 1
			else:
				outside.append(key)
	var added := 0
	for key: String in batch4.nodes:
		if not _baseline.nodes.has(key):
			if _cds_art(key):
				added += 1
			else:
				outside.append(key)
	_check(outside.is_empty() and changed > 0 and added > 0 and _same(_baseline.markings, batch4.markings) and _baseline.zone_id == batch4.zone_id,
		"%s differs from %s only inside the replaced CDS art (%d records removed or changed, %d added; CDSExterior, sections, door and spawn identical; outside %s)"
		% [BATCH4_BASELINE.get_file(), BASELINE.get_file(), changed, added, outside.slice(0, 5)])


## Records under CDSExterior replaced in Batch 4: everything except the section roots, the door and the spawn.
static func _cds_art(key: String) -> bool:
	if not key.begins_with(BASE_KEY + "/"):
		return false
	var rel := key.trim_prefix(BASE_KEY + "/")
	if SECTIONS.has(rel):
		return false
	for kept: String in [DOOR, SPAWN]:
		if rel == kept or rel.begins_with(kept + "/"):
			return false
	return true


func _same(a, b) -> bool:
	if typeof(a) in [TYPE_FLOAT, TYPE_INT] and typeof(b) in [TYPE_FLOAT, TYPE_INT]:
		return absf(float(a) - float(b)) <= 0.001
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


func _check_sections() -> void:
	var bad := []
	for path: String in [""] + SECTIONS.keys():
		var node: Node2D = _cds if path.is_empty() else _cds.get_node_or_null(path) as Node2D
		var key := BASE_KEY + ("" if path.is_empty() else "/" + path)
		var rec: Dictionary = _baseline.nodes.get(key, {})
		if node == null or rec.is_empty() or _xy(rec) != node.global_position or not node.y_sort_enabled:
			bad.append(key)
	_check(bad.is_empty(), "CDSExterior (1775, 0) and the Canteen / TableTennis / IndoorBasketball nodes keep their pre-edit positions and Y-sort (bad %s)" % [bad])


func _check_door_and_spawn() -> void:
	var door := _cds.get_node_or_null(DOOR) as Node2D
	var spawn := _cds.get_node_or_null(SPAWN) as Node2D
	var door_rec: Dictionary = _baseline.nodes.get(BASE_KEY + "/" + DOOR, {})
	var spawn_rec: Dictionary = _baseline.nodes.get(BASE_KEY + "/" + SPAWN, {})
	_check(door != null and door.get("destination_zone_id") == "cds_veranda" and door.get("destination_spawn_id") == "inside_cds_entry"
		and door.get("prompt_text") == PROMPT and door.global_position == Vector2(1452, -200) and _xy(door_rec) == door.global_position
		and door_rec.get("destination_zone_id") == var_to_str("cds_veranda") and door_rec.get("scene") == door.scene_file_path,
		"DoorCdsMainEntry unchanged: %s -> cds_veranda / inside_cds_entry at (1452, -200), prompt \"%s\"" % [DOOR, PROMPT])
	_check(spawn != null and spawn.get("spawn_id") == "outside_cds_entrance" and spawn.global_position == Vector2(1380, -200)
		and _xy(spawn_rec) == spawn.global_position and spawn_rec.get("spawn_id") == var_to_str("outside_cds_entrance"),
		"SpawnOutsideCdsEntrance unchanged: %s, outside_cds_entrance at (1380, -200)" % SPAWN)


func _check_collision() -> void:
	var before := []
	for key: String in _baseline.nodes:
		var rec: Dictionary = _baseline.nodes[key]
		if key.begins_with(BASE_KEY + "/") and key.ends_with("/~internal0:CollisionShape2D") and rec.get("shape", {}).has("rect"):
			var size := Vector2(rec.shape.rect[0], rec.shape.rect[1])
			before.append(Rect2(_xy(rec) - size / 2.0, size))
	var now := []
	var bodies_ok := true
	for section: String in SECTIONS:
		var body := _cds.get_node_or_null(section + "/Collision") as StaticBody2D
		if body == null:
			bodies_ok = false
			continue
		bodies_ok = bodies_ok and body.collision_layer == 1 and body.collision_mask == 0 and body.get_child_count() == 2
		for cs: CollisionShape2D in body.get_children():
			var size := (cs.shape as RectangleShape2D).size
			now.append(Rect2(cs.global_position - size / 2.0, size))
	var key_fn := func(a: Rect2, b: Rect2) -> bool:
		return a.position.y < b.position.y or (a.position.y == b.position.y and a.position.x < b.position.x)
	before.sort_custom(key_fn)
	now.sort_custom(key_fn)
	var same := before.size() == 6 and now.size() == 6
	for i in mini(before.size(), now.size()):
		same = same and before[i].position.is_equal_approx(now[i].position) and before[i].size.is_equal_approx(now[i].size)
	_check(bodies_ok and same, "3 Collision bodies (layer 1, mask 0, 2 shapes each) with exactly the 6 former blockout rectangles %s" % [now])


func _check_occluders() -> void:
	var bad := []
	for section: String in SECTIONS:
		var before := Rect2()
		var first := true
		for key: String in _baseline.nodes:
			var rec: Dictionary = _baseline.nodes[key]
			if key.begins_with("%s/%s/" % [BASE_KEY, section]) and rec.has("occluder"):
				for p: Array in rec.occluder:
					var g := _xy(rec) + Vector2(p[0], p[1])
					before = Rect2(g, Vector2.ZERO) if first else before.expand(g)
					first = false
		var occ := _cds.get_node_or_null(section + "/ShadowOccluder") as LightOccluder2D
		if occ == null or occ.occluder == null or occ.occluder_light_mask != 1:
			bad.append(section)
			continue
		var pts := occ.occluder.polygon
		var now := Rect2(occ.global_transform * pts[0], Vector2.ZERO)
		for p in pts:
			now = now.expand(occ.global_transform * p)
		if first or pts.size() != 4 or not now.position.is_equal_approx(before.position) or not now.size.is_equal_approx(before.size):
			bad.append("%s %s vs %s" % [section, now, before])
	_check(bad.is_empty(), "each section has one ShadowOccluder (light mask 1) covering exactly its former blockout occluders (bad %s)" % [bad])


func _check_placeholders() -> void:
	var left := []
	for node in _cds.find_children("*", "", true, false):
		if node.is_in_group("blockout_placeholder") or node is Label or node.scene_file_path.ends_with("BlockoutBlock.tscn"):
			left.append(String(_cds.get_path_to(node)))
	var props := 0
	for section: String in SECTIONS:
		var prop := _cds.get_node_or_null("%s/%s" % [section, SECTIONS[section][0]])
		props += 1 if prop != null and prop.scene_file_path == "res://scenes/props/landmarks/%s.tscn" % SECTIONS[section][0] and (prop as Node2D).position == Vector2.ZERO else 0
	_check(left.is_empty() and props == 3, "no blockout placeholder, BlockoutBlock or label left under CDSExterior; the 3 CDS props are instanced at their section origins (left %s)" % [left])


func _check_stops() -> void:
	var bad := []
	var lines := []
	for i in STOPS.size():
		var stop := _stop(STOPS[i][1], STOPS[i][2])
		lines.append("%s %s" % [STOPS[i][0].get_slice(",", 0), stop])
		if i >= PREEDIT_STOPS.size() or not stop.is_equal_approx(PREEDIT_STOPS[i]) or stop.is_equal_approx(STOPS[i][1] + STOPS[i][2]):
			bad.append("%s: %s (pre-edit %s)" % [STOPS[i][0], stop, PREEDIT_STOPS[i] if i < PREEDIT_STOPS.size() else "?"])
	print("[CDS]      stops: %s" % ", ".join(lines))
	_check(bad.is_empty() and PREEDIT_STOPS.size() == STOPS.size(),
		"the real player stops at the pre-edit lines at %d points (west facade x 1466, north of the canteen, east side, south of the hall) (bad %s)" % [STOPS.size(), bad.slice(0, 3)])


func _check_free_walks() -> void:
	var blocked := []
	for spec: Array in FREE_WALKS:
		_player.global_position = spec[1]
		if _player.test_move(_player.global_transform, spec[2]):
			blocked.append(spec[0])
	_check(blocked.is_empty(), "%d walks stay free (flagpoles, lamp, door and fade area don't block) (blocked %s)" % [FREE_WALKS.size(), blocked])


func _check_prompt() -> void:
	var interactable := _cds.get_node(DOOR).get_node("Interactable")
	_player.call("teleport", Vector2(1440, -200))
	await _settle()
	var at_door: Variant = _player.get("_interaction_target")
	_player.call("teleport", Vector2(1380, -200))
	await _settle()
	var at_spawn: Variant = _player.get("_interaction_target")
	_check(at_door == interactable and interactable.get("prompt_text") == PROMPT and at_spawn != interactable,
		"standing at the door (1440, -200) targets DoorCdsMainEntry (\"%s\"); the spawn (1380, -200) does not" % PROMPT)


func _check_slices() -> void:
	var bad := []
	var fades := []
	for section: String in SECTIONS:
		var prop := _cds.get_node("%s/%s" % [section, SECTIONS[section][0]]) as Node2D
		var south := (_cds.get_node(section) as Node2D).global_position.y
		if not prop.y_sort_enabled or absf((prop.get_node("Sprite") as Node2D).global_position.y - south) > EPS:
			bad.append("%s/Sprite" % section)
		var layers: Dictionary = SECTIONS[section][2]
		for layer: String in layers:
			var node := prop.get_node_or_null(layer) as Node2D
			var want := south - float(layers[layer]) * DEPTH_PX_PER_M
			if node == null or absf(node.global_position.y - want) > EPS:
				bad.append("%s/%s (want y %.3f)" % [section, layer, want])
		for child in prop.get_children():
			if child is OverheadVisibility:
				fades.append(String(_cds.get_path_to(child)))
	_check(bad.is_empty(), "every slice sorts at its section's south edge + slice bound x 20.569 px/m (bad %s)" % [bad])
	_check(fades == [FADE_AREA], "the only fade area under CDSExterior is %s (found %s)" % [FADE_AREA, fades])


func _check_budget() -> void:
	var lines := []
	var over := []
	var total := 0
	for section: String in SECTIONS:
		var prop := _cds.get_node("%s/%s" % [section, SECTIONS[section][0]])
		var px := 0
		for sprite: Sprite2D in prop.find_children("*", "Sprite2D", true, false):
			px += sprite.texture.get_width() * sprite.texture.get_height()
		var cfg := _load_json(CONFIGS % SECTIONS[section][1])
		var budget := int(cfg.get("render", {}).get("max_texture_px", 0))
		total += px
		lines.append("%s %d / %d" % [SECTIONS[section][1], px, budget])
		if budget <= 0 or px > budget:
			over.append(SECTIONS[section][1])
	_check(over.is_empty(), "texture pixels within each config's max_texture_px: %s; total %.2f Mpx (over %s)" % [", ".join(lines), total / 1e6, over])


func _check_fade_cases() -> void:
	for spec: Array in FADE_CASES:
		_player.call("teleport", spec[1])
		await _settle()
		var a := _alpha()
		var want := FADED if spec[2] else 1.0
		var others := _changed_others()
		_check(absf(a - want) < EPS and others.is_empty(),
			"%s %s: NorthRoof alpha %.2f (want %.2f); other items changed %s" % [spec[0], spec[1], a, want, others])


## Walk south 1 px per physics frame across the north edge of the fade area (feet y -1129.8) and back.
func _check_fade_walk() -> void:
	var area := _cds.get_node(FADE_AREA)
	_player.call("teleport", Vector2(1740, -1150))
	await _settle()
	var toggles := 0
	var was := bool(area.call("is_faded"))
	var last := _alpha()
	var max_step := 0.0
	var faded_inside := 1.0
	var y := -1150.0
	var dir := 1.0
	for leg in 2:
		for i in 40:
			_player.global_position = Vector2(1740, y)
			await get_tree().physics_frame
			var a := _alpha()
			max_step = maxf(max_step, absf(a - last))
			last = a
			var now := bool(area.call("is_faded"))
			toggles += 1 if now != was else 0
			was = now
			y += dir
		if leg == 0:
			await _settle()
			faded_inside = _alpha()
			dir = -1.0
	await _settle()
	_check(toggles == 2 and absf(faded_inside - FADED) < EPS and absf(_alpha() - 1.0) < EPS and max_step < 0.1,
		"walking across the fade edge and back: %d state changes (expected 2), %.2f inside, %.2f after leaving, max alpha step per physics frame %.3f (< 0.1, no snap)"
		% [toggles, faded_inside, _alpha(), max_step])


func _stop(start: Vector2, motion: Vector2) -> Vector2:
	_player.global_position = start
	var hit := _player.move_and_collide(motion, true)
	return start + (hit.get_travel() if hit != null else motion)


func _settle() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	await get_tree().create_timer(0.45).timeout


func _alpha() -> float:
	return (_cds.get_node(FADE_LAYER) as CanvasItem).modulate.a


## CanvasItems in the zone (other than NorthRoof) whose modulate is not white.
func _changed_others() -> Array:
	var out := []
	var layer := _cds.get_node(FADE_LAYER)
	for node in _zone.find_children("*", "CanvasItem", true, false):
		if node != layer and (node as CanvasItem).modulate != Color.WHITE:
			out.append(String(_zone.get_path_to(node)))
	return out


func _xy(rec: Dictionary) -> Vector2:
	var xf: Array = rec.get("xform", [])
	return Vector2(xf[4], xf[5]) if xf.size() == 6 else Vector2.INF


func _load_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	return data if data is Dictionary else {}

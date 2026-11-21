extends Node2D
## Phase H4: the ONE data-driven zone validator (test-only). Replaces the per-batch Main Gate check scenes.
##
## Every zone in `data/zones/zone_registry.tres` is checked with the same generic rules, plus its own small
## manifest (`manifests/<zone_id>.json`) and one baseline snapshot (`baselines/<zone_id>.json`):
##   identity     the scene's Zone root has the registry key as `zone_id`
##   graph        spawn ids are unique and non-empty; every Door leads to a registered zone and an existing spawn
##   profile      every shipping zone has a ZoneProfile with an ambience bed and camera limits that contain the
##                playable bounds plus half a 1920 x 1080 view at the profile's zoom (the view can never show
##                outside the zone); its default surface has footstep sounds
##   conventions  Docs/CONVENTIONS.md rules: collision layers/masks per node kind, occluder light mask 1,
##                prop sprites light mask 2, contact shadows z -9 without collision, Y-sorted ancestors for
##                every placed prop, the zone ground at z -10
##   snapshot     every node (transform, z, Y-sort, light mask, collision, shapes, occluders, textures, tile
##                cells, exported script values) equals the baseline
##   ground       a material lattice (8 px) over the zone ground equals the baseline: proves no surface moved
##   probes       for EVERY rectangle collision shape on layer 1: the real player footprint walking at it from
##                the south and from the north is stopped at its face (or earlier by another collider), never
##                passes through
##   reach        flood fill of where the player footprint can stand, from the zone's first spawn: nothing
##                reachable outside the manifest's playable bounds (no leaks), every spawn and door reachable
##   fades        every OverheadVisibility never blocks, fades exactly its targets and smoothly, restores on
##                exit; plus the manifest's fade cases (where each layer must / must not be faded)
##   cases        the manifest's specific walks (expected stop or free path)
##
## Args (after `--`):
##   --zone=<id>[,<id>]   only these zones (default: every registered zone that is available in this build)
##   --dump-baseline      write baselines/<zone_id>.json from the current scene (prints what changed first);
##                        do this ONLY after reviewing that a failing snapshot/ground diff is intended
##   --self-test          also mutate main_gate_exterior in memory and prove each rule catches its mutation
##   --quit-after-checks  quit with exit code 0 (all pass) / 1
##
## Run headless:  <godot> --headless --path . res://scenes/tests/zone_validation/ZoneValidator.tscn -- --quit-after-checks

const REGISTRY_PATH := "res://data/zones/zone_registry.tres"
const PLAYER_SCENE := "res://scenes/player/Player.tscn"
const DIR := "res://scenes/tests/zone_validation/"
const PROP_PREFIX := "res://scenes/props/"
const SHADOW_SCENE := "res://scenes/props/common/ContactShadow.tscn"
const BASELINE_FORMAT := 1
const EPS := 0.001
const FOOT := Vector2(28, 12)          ## player footprint, bottom edge at the feet
const STEP := 8.0                      ## reach grid and ground lattice spacing (px)
const PROBE_TOL := 1.5
const LAYER_WORLD := 1
const LAYER_PLAYER := 2
const LAYER_INTERACTABLE := 4          ## bit 3
const MAX_DETAILS := 6
const MIN_FADE_SECONDS := 0.15      ## an overhead fade must ease, never snap

var _registry: ZoneRegistry
var _player: CharacterBody2D
var _checks := 0
var _failures := 0
var _quiet := false                    ## self-test runs the rules without reporting them as checks
var _spawn_cache := {}                 ## zone_id -> Array of spawn ids


func _ready() -> void:
	_registry = load(REGISTRY_PATH) as ZoneRegistry
	var args := OS.get_cmdline_user_args()
	_player = (load(PLAYER_SCENE) as PackedScene).instantiate() as CharacterBody2D
	add_child(_player)
	await get_tree().physics_frame
	var dump := args.has("--dump-baseline")
	for zone_id in _selected_zones(args):
		await _validate_zone(zone_id, dump)
	if args.has("--self-test") and not dump:
		await _self_test()
	if dump:
		print("[ZONEVAL] baselines written; re-run without --dump-baseline to validate")
	else:
		print("[ZONEVAL] %s (%d/%d)" % ["PASS" if _failures == 0 else "FAIL", _checks - _failures, _checks])
	if args.has("--quit-after-checks") or dump:
		get_tree().quit(0 if _failures == 0 else 1)


func _selected_zones(args: PackedStringArray) -> Array[String]:
	for a in args:
		if a.begins_with("--zone="):
			var out: Array[String] = []
			out.assign(a.trim_prefix("--zone=").split(",", false))
			return out
	return _registry.get_zone_ids()


# =================================================================================================
# Reporting

func _report(zone_id: String, rule: String, failures: Array, summary: String) -> void:
	if _quiet:
		return
	_checks += 1
	var ok := failures.is_empty()
	_failures += 0 if ok else 1
	print("[ZONEVAL] %s %s %s: %s" % ["ok  " if ok else "FAIL", zone_id, rule, summary])
	for i in mini(failures.size(), MAX_DETAILS):
		print("[ZONEVAL]        - %s" % failures[i])
	if failures.size() > MAX_DETAILS:
		print("[ZONEVAL]        - ... and %d more" % (failures.size() - MAX_DETAILS))


# =================================================================================================
# Per zone

func _validate_zone(zone_id: String, dump: bool) -> void:
	var manifest := _load_json(DIR + "manifests/%s.json" % zone_id)
	if manifest.is_empty():
		_report(zone_id, "manifest", ["missing or invalid %smanifests/%s.json" % [DIR, zone_id]], "every registered zone needs a manifest")
		return
	var zone := _instantiate(zone_id)
	if zone == null:
		_report(zone_id, "identity", ["scene for '%s' does not load as a Zone" % zone_id], "zone loads")
		return
	await _settle_physics()
	if dump:
		_dump_baseline(zone_id, zone, manifest)
		await _free_zone(zone)
		return
	var stats := _stats(zone)
	print("[ZONEVAL] ---- %s (%s): %s" % [zone_id, _registry.get_scene_path(zone_id), stats])
	var t := Time.get_ticks_msec()
	_rule_identity(zone_id, zone)
	_rule_graph(zone_id, zone)
	t = _lap(t, "identity+graph")
	_rule_profile(zone_id, zone, manifest)
	_rule_conventions(zone_id, zone, manifest)
	t = _lap(t, "profile+conventions")
	_rule_snapshot(zone_id, zone, manifest)
	t = _lap(t, "snapshot")
	_rule_ground(zone_id, zone, manifest)
	t = _lap(t, "ground")
	_rule_probes(zone_id, zone)
	t = _lap(t, "probes")
	_rule_reach(zone_id, zone, manifest)
	t = _lap(t, "reach")
	_rule_cases(zone_id, zone, manifest)
	await _rule_fades(zone_id, zone, manifest)
	t = _lap(t, "cases+fades")
	await _free_zone(zone)


func _lap(t: int, what: String) -> int:
	var now := Time.get_ticks_msec()
	print("[ZONEVAL]        (%s %.1f s)" % [what, (now - t) / 1000.0])
	return now


func _instantiate(zone_id: String) -> Zone:
	var path := _registry.get_scene_path(zone_id)
	if path.is_empty() or not ResourceLoader.exists(path):
		return null
	var zone := (load(path) as PackedScene).instantiate() as Zone
	if zone == null:
		return null
	add_child(zone)
	move_child(zone, 0)
	return zone


func _free_zone(zone: Node) -> void:
	remove_child(zone)
	zone.free()
	await _settle_physics()


func _settle_physics() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	await get_tree().process_frame


func _stats(zone: Node) -> String:
	var counts := {"nodes": 0, "props": 0, "bodies": 0, "shapes": 0, "occluders": 0, "placeholders": 0}
	for n in _all_nodes(zone):
		counts.nodes += 1
		if _is_top_prop(n, zone):
			counts.props += 1
		if n is StaticBody2D:
			counts.bodies += 1
		if n is CollisionShape2D:
			counts.shapes += 1
		if n is LightOccluder2D:
			counts.occluders += 1
		if n.is_in_group("blockout_placeholder") and not (n.get_parent() != null and n.get_parent().is_in_group("blockout_placeholder")):
			counts.placeholders += 1
	return "%d nodes, %d placed props, %d static bodies, %d shapes, %d occluders, %d blockout placeholder roots" % [
		counts.nodes, counts.props, counts.bodies, counts.shapes, counts.occluders, counts.placeholders]


# =================================================================================================
# identity + graph

func _rule_identity(zone_id: String, zone: Zone) -> Array:
	var f := []
	if zone.zone_id != zone_id:
		f.append("Zone root zone_id is '%s', registry key is '%s'" % [zone.zone_id, zone_id])
	_report(zone_id, "identity", f, "Zone root zone_id = registry key '%s'" % zone_id)
	return f


func _rule_graph(zone_id: String, zone: Zone) -> Array:
	var f := []
	var ids := {}
	for marker in zone.get_spawn_markers():
		var sid: String = marker.spawn_id
		if sid.is_empty():
			f.append("spawn marker %s has an empty spawn_id" % zone.get_path_to(marker))
		elif ids.has(sid):
			f.append("duplicate spawn_id '%s'" % sid)
		ids[sid] = true
	var doors := zone.get_doors()
	for door in doors:
		var dz: String = door.destination_zone_id
		var ds: String = door.destination_spawn_id
		if not _registry.has_zone(dz):
			f.append("door %s leads to unregistered zone '%s'" % [zone.get_path_to(door), dz])
		elif not _spawn_ids_of(dz).has(ds):
			f.append("door %s leads to '%s' spawn '%s', which does not exist there" % [zone.get_path_to(door), dz, ds])
	_report(zone_id, "graph", f, "%d spawns unique; %d doors lead to registered zones and existing spawns" % [ids.size(), doors.size()])
	return f


func _spawn_ids_of(zone_id: String) -> Array:
	if _spawn_cache.has(zone_id):
		return _spawn_cache[zone_id]
	var ids := []
	var path := _registry.get_scene_path(zone_id)
	if not path.is_empty():
		var z := (load(path) as PackedScene).instantiate() as Zone
		if z != null:
			for m in z.find_children("*", "SpawnMarker", true, false):
				ids.append(String(m.spawn_id))
			z.free()
	_spawn_cache[zone_id] = ids
	return ids


# =================================================================================================
# profile (roadmap I: camera, surfaces, audio per zone)

const BASE_VIEW := Vector2(1920, 1080)
const FOOTSTEPS := "res://data/audio/footsteps.tres"


func _rule_profile(zone_id: String, zone: Zone, manifest: Dictionary) -> Array:
	var f := []
	var p := zone.profile
	var shipping := not _registry.is_debug_zone(zone_id)
	if p == null:
		if shipping:
			f.append("shipping zone has no ZoneProfile (data/zones/profiles/%s.tres)" % zone_id)
		_report(zone_id, "profile", f, "no profile (debug zone: defaults)" if f.is_empty() else "profile missing")
		return f
	var r := p.camera_limits
	if shipping and (r.size.x <= 0.0 or r.size.y <= 0.0):
		f.append("camera_limits are empty; the view could show outside the zone")
	if shipping and p.ambience == null:
		f.append("no ambience bed")
	var b: Array = manifest.get("playable_bounds", [])
	if r.size.x > 0.0 and b.size() == 4:
		# A scrolling axis must keep half a view of zone around the playable area. An axis whose limits are no
		# bigger than one view is a fixed framing (small interiors, decision D21): the whole room is in view and
		# the black around it is intended, so the playable area only has to lie inside the limits on that axis.
		var view := BASE_VIEW / p.camera_zoom
		var half := view * 0.5
		var hx := 0.0 if r.size.x <= view.x + 2.0 else half.x
		var hy := 0.0 if r.size.y <= view.y + 2.0 else half.y
		var need := Rect2(b[0], b[1], b[2], b[3]).grow_individual(hx, hy, hx, hy)
		if not r.encloses(need):
			f.append("camera_limits %s don't contain the playable bounds plus half a view at zoom %.2f (%s)" % [r, p.camera_zoom, need])
	var fset := load(FOOTSTEPS) as FootstepSet
	if fset != null and not fset.streams.has(p.default_surface):
		f.append("default_surface '%s' has no footstep sounds" % p.default_surface)
	_report(zone_id, "profile", f, "zoom %.2f, limits %s contain the playable area + half a view, ambience %s, default surface %s" % [
		p.camera_zoom, r, p.ambience.resource_path.get_file() if p.ambience else "none", p.default_surface])
	return f


# =================================================================================================
# conventions (Docs/CONVENTIONS.md)

func _rule_conventions(zone_id: String, zone: Zone, manifest: Dictionary) -> Array:
	var f := []
	var n_props := 0
	var n_shadows := 0
	var n_areas := 0
	var ground_name: String = (manifest.get("ground", {}) as Dictionary).get("node", "Ground")
	var ground := zone.get_node_or_null(ground_name) as Node2D
	if ground != null and (ground.z_index != -10 or not ground.z_as_relative or ground.y_sort_enabled):
		f.append("%s must be z -10 (relative) and not Y-sorted (z %d, y_sort %s)" % [ground_name, ground.z_index, ground.y_sort_enabled])
	for n in _all_nodes(zone):
		var p := String(zone.get_path_to(n))
		if n is StaticBody2D:
			var b := n as StaticBody2D
			if b.collision_layer != LAYER_WORLD or b.collision_mask != 0:
				f.append("%s: StaticBody2D must be layer 1 'world' / mask none (layer %d, mask %d)" % [p, b.collision_layer, b.collision_mask])
		elif (n is CharacterBody2D and not (n is NightGuard)) or n is RigidBody2D:
			f.append("%s: zones must not contain moving bodies other than creatures (%s)" % [p, n.get_class()])
		if n is Area2D:
			n_areas += 1
			var a := n as Area2D
			if n is Interactable:
				if a.collision_layer != LAYER_INTERACTABLE or a.collision_mask != 0:
					f.append("%s: Interactable must be layer 3 / mask none (layer %d, mask %d)" % [p, a.collision_layer, a.collision_mask])
				# Doors and pickups copy their verb into their Interactable in _ready (zone not in the tree here),
				# so read it from the owning Door / Pickup when there is one.
				var owner_node: Node = n.get_parent()
				var verb: String = owner_node.get("verb") if (owner_node is Door or owner_node is Pickup) else (n as Interactable).verb
				if verb.strip_edges().is_empty():
					f.append("%s: Interactable has no verb for its prompt" % p)
			elif n is OverheadVisibility:
				if a.collision_layer != 0 or a.collision_mask != LAYER_PLAYER:
					f.append("%s: OverheadVisibility must be layer none / mask 2 player (layer %d, mask %d)" % [p, a.collision_layer, a.collision_mask])
			else:
				f.append("%s: Area2D of unknown role (add its rule to the validator when triggers exist)" % p)
		# Occluders cast on light mask 1; mask 0 is a shadow deliberately switched off (BlockoutBlock casts_shadow).
		if n is LightOccluder2D and not ((n as LightOccluder2D).occluder_light_mask in [0, 1]):
			f.append("%s: LightOccluder2D must use light mask 1, or 0 when its shadow is off (got %d)" % [p, (n as LightOccluder2D).occluder_light_mask])
		if n.scene_file_path == SHADOW_SCENE:
			n_shadows += 1
			if _effective_z(n as CanvasItem) != -9:
				f.append("%s: ContactShadow effective z must be -9 (got %d)" % [p, _effective_z(n as CanvasItem)])
			if not n.find_children("*", "CollisionObject2D", true, false).is_empty():
				f.append("%s: ContactShadow must not collide" % p)
		elif _is_top_prop(n, zone):
			n_props += 1
			var a2: Node = n.get_parent()
			while a2 != null:
				if not (a2 is Node2D) or not (a2 as Node2D).y_sort_enabled:
					f.append("%s: ancestor %s is not a Y-sorted Node2D, so the prop can't sort with the player" % [p, zone.get_path_to(a2)])
					break
				if a2 == zone:
					break
				a2 = a2.get_parent()
			for s in n.find_children("*", "Node2D", true, false):
				if (s is Sprite2D or s is AnimatedSprite2D) and not _inside_shadow(s, n) and (s as CanvasItem).light_mask != 2:
					f.append("%s: prop sprite light mask must be 2 (got %d)" % [zone.get_path_to(s), (s as CanvasItem).light_mask])
	_report(zone_id, "conventions", f, "%d placed props Y-sorted with sprites on light mask 2; %d contact shadows z -9; bodies, %d areas and occluders on their layers" % [n_props, n_shadows, n_areas])
	return f


func _is_top_prop(n: Node, zone: Node) -> bool:
	if n == zone or not n.scene_file_path.begins_with(PROP_PREFIX) or n.scene_file_path == SHADOW_SCENE:
		return false
	var a := n.get_parent()
	while a != null and a != zone:
		if a.scene_file_path.begins_with(PROP_PREFIX):
			return false
		a = a.get_parent()
	return true


func _inside_shadow(node: Node, stop: Node) -> bool:
	var a := node
	while a != null and a != stop:
		if a.scene_file_path == SHADOW_SCENE:
			return true
		a = a.get_parent()
	return false


# =================================================================================================
# snapshot

func _snapshot(zone: Node) -> Dictionary:
	var nodes := {}
	_snap(zone, zone, ".", nodes)
	return nodes


func _snap(zone: Node, node: Node, path: String, out: Dictionary) -> void:
	var rec := {"class": node.get_class()}
	if not node.scene_file_path.is_empty():
		rec["scene"] = node.scene_file_path
	var groups := _groups(node)
	if not groups.is_empty():
		rec["groups"] = groups
	if node is Node2D:
		rec["xform"] = _xf((node as Node2D).global_transform)
		if (node as Node2D).y_sort_enabled:
			rec["y_sort"] = true
	if node is CanvasItem:
		var ci := node as CanvasItem
		rec["z"] = _effective_z(ci)
		rec["visible"] = ci.visible
		rec["light_mask"] = ci.light_mask
		if ci.modulate != Color.WHITE:
			rec["modulate"] = _col(ci.modulate)
		if ci.self_modulate != Color.WHITE:
			rec["self_modulate"] = _col(ci.self_modulate)
		if ci.texture_filter != CanvasItem.TEXTURE_FILTER_PARENT_NODE:
			rec["texture_filter"] = ci.texture_filter
		if ci.texture_repeat != CanvasItem.TEXTURE_REPEAT_PARENT_NODE:
			rec["texture_repeat"] = ci.texture_repeat
	if node is Sprite2D:
		var s := node as Sprite2D
		rec["texture"] = _res(s.texture)
		rec["offset"] = [s.offset.x, s.offset.y]
		rec["centered"] = s.centered
		if s.region_enabled:
			rec["region"] = [s.region_rect.position.x, s.region_rect.position.y, s.region_rect.size.x, s.region_rect.size.y]
	elif node is AnimatedSprite2D:
		var a := node as AnimatedSprite2D
		rec["frames"] = _res(a.sprite_frames)
		rec["offset"] = [a.offset.x, a.offset.y]
	elif node is Polygon2D:
		var pg := node as Polygon2D
		rec["polygon"] = _pts(pg.polygon)
		rec["color"] = _col(pg.color)
		if pg.texture != null:
			rec["texture"] = _res(pg.texture)
			rec["texture_scale"] = [pg.texture_scale.x, pg.texture_scale.y]
			rec["texture_offset"] = [pg.texture_offset.x, pg.texture_offset.y]
			rec["uv"] = pg.uv.size()
	elif node is Line2D:
		var l := node as Line2D
		rec["points"] = _pts(l.points)
		rec["width"] = l.width
		rec["line_color"] = _col(l.default_color)
		rec["closed"] = l.closed
	elif node is TileMapLayer:
		var tm := node as TileMapLayer
		rec["tile_set"] = _res(tm.tile_set)
		rec["tile_size"] = [tm.tile_set.tile_size.x, tm.tile_set.tile_size.y] if tm.tile_set else []
		var cells := tm.get_used_cells()
		cells.sort()
		var by_source := {}
		var parts := PackedStringArray()
		for c in cells:
			var src := tm.get_cell_source_id(c)
			var ac := tm.get_cell_atlas_coords(c)
			by_source[str(src)] = by_source.get(str(src), 0) + 1
			parts.append("%d,%d:%d:%d,%d" % [c.x, c.y, src, ac.x, ac.y])
		rec["cells"] = cells.size()
		rec["cells_by_source"] = by_source
		rec["cells_sha256"] = "\n".join(parts).sha256_text()
	if node is CollisionObject2D:
		rec["layer"] = (node as CollisionObject2D).collision_layer
		rec["mask"] = (node as CollisionObject2D).collision_mask
	if node is Area2D:
		rec["monitoring"] = (node as Area2D).monitoring
		rec["monitorable"] = (node as Area2D).monitorable
	if node is CollisionShape2D:
		var cs := node as CollisionShape2D
		rec["disabled"] = cs.disabled
		rec["shape"] = _shape(cs.shape)
	if node is CollisionPolygon2D:
		rec["polygon"] = _pts((node as CollisionPolygon2D).polygon)
		rec["disabled"] = (node as CollisionPolygon2D).disabled
	if node is LightOccluder2D:
		var lo := node as LightOccluder2D
		rec["occluder_mask"] = lo.occluder_light_mask
		rec["occluder"] = _pts(lo.occluder.polygon) if lo.occluder else []
	if node is Light2D:
		var li := node as Light2D
		# A LampLight animates `energy` every frame (flicker, breathing): record its authored `base_energy` instead.
		var authored_energy: float = li.get("base_energy") if li.get("base_energy") != null else li.energy
		rec["light"] = {"enabled": li.enabled, "energy": authored_energy, "color": _col(li.color), "shadows": li.shadow_enabled,
			"range_mask": li.range_item_cull_mask, "shadow_mask": li.shadow_item_cull_mask}
	var vars := _script_vars(node)
	if not vars.is_empty():
		rec["script"] = vars
	out[path] = rec
	var internal := 0
	var own := node.get_children(false)
	for child in node.get_children(true):
		var child_path: String
		if own.has(child):
			child_path = "%s/%s" % [path, child.name]
		else:
			child_path = "%s/~internal%d:%s" % [path, internal, child.get_class()]
			internal += 1
		_snap(zone, child, child_path, out)


func _script_vars(node: Node) -> Dictionary:
	var s: Script = node.get_script()
	if s == null:
		return {}
	var out := {"path": s.resource_path}
	for p in node.get_property_list():
		if (p.usage & PROPERTY_USAGE_SCRIPT_VARIABLE) and (p.usage & PROPERTY_USAGE_STORAGE):
			out[p.name] = var_to_str(node.get(p.name))
	return out


func _rule_snapshot(zone_id: String, zone: Node, _manifest: Dictionary) -> Array:
	var f := []
	var base := _load_json(_baseline_path(zone_id))
	if base.is_empty() or int(base.get("format", 0)) != BASELINE_FORMAT:
		f.append("no baseline %s (create it with --dump-baseline after reviewing the zone)" % _baseline_path(zone_id))
		_report(zone_id, "snapshot", f, "baseline missing")
		return f
	var diff := _diff_nodes(base.nodes, _snapshot(zone))
	f.append_array(diff)
	_report(zone_id, "snapshot", f, "%d nodes identical to %s" % [(base.nodes as Dictionary).size(), _baseline_path(zone_id).get_file()])
	return f


func _diff_nodes(before: Dictionary, now: Dictionary) -> Array:
	var out := []
	for key in before:
		if not now.has(key):
			out.append("removed: %s" % key)
		elif not _same(before[key], now[key]):
			var fields := []
			for k in now[key]:
				if not (before[key] as Dictionary).has(k) or not _same(before[key][k], now[key][k]):
					fields.append(k)
			for k in before[key]:
				if not (now[key] as Dictionary).has(k):
					fields.append(k)
			out.append("changed: %s %s" % [key, fields])
	for key in now:
		if not before.has(key):
			out.append("added: %s" % key)
	return out


func _baseline_path(zone_id: String) -> String:
	return DIR + "baselines/%s.json" % zone_id


func _dump_baseline(zone_id: String, zone: Node, manifest: Dictionary) -> void:
	var data := {"format": BASELINE_FORMAT, "zone_id": zone_id, "nodes": _snapshot(zone), "ground_lattice": _ground_lattice(zone, manifest)}
	var old := _load_json(_baseline_path(zone_id))
	if not old.is_empty() and int(old.get("format", 0)) == BASELINE_FORMAT:
		var diff := _diff_nodes(old.nodes, data.nodes)
		var gdiff := _diff_lattice(old.get("ground_lattice", {}), data.ground_lattice)
		print("[ZONEVAL] %s: refreshing baseline; %d node differences, %d ground samples differ:" % [zone_id, diff.size(), gdiff.size()])
		for i in mini(diff.size(), 40):
			print("[ZONEVAL]        %s" % diff[i])
		if diff.size() > 40:
			print("[ZONEVAL]        ... and %d more" % (diff.size() - 40))
	else:
		print("[ZONEVAL] %s: writing first baseline" % zone_id)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR + "baselines"))
	var file := FileAccess.open(_baseline_path(zone_id), FileAccess.WRITE)
	if file == null:
		push_error("[ZONEVAL] can't write %s: %s" % [_baseline_path(zone_id), error_string(FileAccess.get_open_error())])
		_failures += 1
		return
	file.store_string(JSON.stringify(data, "\t", true, true) + "\n")
	file.close()
	print("[ZONEVAL] %s: baseline written (%d nodes, ground lattice %d rows)" % [zone_id, (data.nodes as Dictionary).size(), (data.ground_lattice.get("rows", []) as Array).size()])


# =================================================================================================
# ground material lattice

## Material at every 8 px lattice point over the manifest's ground rect: the topmost textured Polygon2D of
## the ground node at that point, else the TileMapLayer cell's atlas texture. Materials are texture file
## stems, so re-rendering a texture at another resolution (same path) keeps the lattice identical.
func _ground_lattice(zone: Node, manifest: Dictionary) -> Dictionary:
	var g: Dictionary = manifest.get("ground", {})
	if g.is_empty():
		return {}
	var ground := zone.get_node_or_null(g.get("node", "Ground"))
	if ground == null:
		return {"error": "no ground node"}
	var r: Array = g.rect
	var rect := Rect2(r[0], r[1], r[2], r[3])
	var layers: Array[TileMapLayer] = []
	var polys := []
	for n in ground.find_children("*", "", true, false):
		if n is TileMapLayer:
			layers.append(n)
		elif n is Polygon2D and (n as Polygon2D).texture != null:
			var pg := n as Polygon2D
			var inv := pg.global_transform.affine_inverse()
			var bb := Rect2(pg.global_transform * pg.polygon[0], Vector2.ZERO)
			for v in pg.polygon:
				bb = bb.expand(pg.global_transform * v)
			polys.append([pg, inv, bb, _stem(pg.texture)])
	var legend := {}
	var codes := {}
	var rows := []
	var y := rect.position.y + STEP * 0.5 + 0.25
	while y < rect.end.y:
		var row := ""
		var x := rect.position.x + STEP * 0.5 + 0.25
		while x < rect.end.x:
			var p := Vector2(x, y)
			var mat := ""
			for e in polys:
				if (e[2] as Rect2).has_point(p) and Geometry2D.is_point_in_polygon(e[1] * p, (e[0] as Polygon2D).polygon):
					mat = e[3]
			if mat == "":
				for tm in layers:
					var c := tm.local_to_map(tm.to_local(p))
					var src := tm.get_cell_source_id(c)
					if src != -1:
						var atlas := tm.tile_set.get_source(src) as TileSetAtlasSource
						mat = _stem(atlas.texture) if atlas else "src%d" % src
			if mat == "":
				mat = "none"
			if not codes.has(mat):
				var code := char(97 + codes.size())
				codes[mat] = code
				legend[code] = mat
			row += codes[mat]
			x += STEP
		rows.append(_rle(row))
		y += STEP
	return {"rect": r, "step": STEP, "legend": legend, "rows": rows}


func _rule_ground(zone_id: String, zone: Node, manifest: Dictionary) -> Array:
	var f := []
	if (manifest.get("ground", {}) as Dictionary).is_empty():
		_report(zone_id, "ground", f, "no ground lattice in the manifest (skipped)")
		return f
	var base := _load_json(_baseline_path(zone_id))
	var now := _ground_lattice(zone, manifest)
	if base.is_empty():
		f.append("no baseline")
	else:
		f.append_array(_diff_lattice(base.get("ground_lattice", {}), now))
	var n := 0
	for row in now.get("rows", []):
		n += _rle_len(row)
	_report(zone_id, "ground", f, "%d lattice samples (%d px) of %s match the baseline" % [n, int(STEP), (now.get("legend", {}) as Dictionary).values()])
	return f


func _diff_lattice(a: Dictionary, b: Dictionary) -> Array:
	var out := []
	if a.get("rect") != b.get("rect"):
		return ["ground lattice rect changed %s -> %s" % [a.get("rect"), b.get("rect")]]
	var ra: Array = a.get("rows", [])
	var rb: Array = b.get("rows", [])
	var la: Dictionary = a.get("legend", {})
	var lb: Dictionary = b.get("legend", {})
	var r: Array = b.get("rect", [0, 0, 0, 0])
	for i in mini(ra.size(), rb.size()):
		if ra[i] == rb[i] and la == lb:
			continue
		var da := _unrle(ra[i])
		var db := _unrle(rb[i])
		for j in mini(da.length(), db.length()):
			var ma: String = la.get(da[j], "?")
			var mb: String = lb.get(db[j], "?")
			if ma != mb:
				out.append("ground at (%.0f, %.0f): %s -> %s" % [r[0] + STEP * (j + 0.5), r[1] + STEP * (i + 0.5), ma, mb])
	if ra.size() != rb.size():
		out.append("ground lattice row count %d -> %d" % [ra.size(), rb.size()])
	return out


func _rle(s: String) -> String:
	var out := ""
	var i := 0
	while i < s.length():
		var j := i
		while j < s.length() and s[j] == s[i]:
			j += 1
		out += "%s%d" % [s[i], j - i]
		i = j
	return out


func _unrle(s: String) -> String:
	var out := ""
	var i := 0
	while i < s.length():
		var ch := s[i]
		i += 1
		var num := ""
		while i < s.length() and s[i] >= "0" and s[i] <= "9":
			num += s[i]
			i += 1
		out += ch.repeat(int(num))
	return out


func _rle_len(s: String) -> int:
	return _unrle(s).length()


func _stem(res: Resource) -> String:
	return res.resource_path.get_file().get_basename() if res and not res.resource_path.is_empty() else "embedded"


# =================================================================================================
# probes: every rectangle collision shape on the world layer stops the real player footprint

func _rule_probes(zone_id: String, zone: Node) -> Array:
	var f := []
	var stopped := 0
	var shielded := 0
	var skipped := 0
	for n in _all_nodes(zone):
		if not (n is CollisionShape2D):
			continue
		var cs := n as CollisionShape2D
		var body := cs.get_parent() as CollisionObject2D
		# Every static body is meant to block (the conventions rule requires layer 1), so probe them all,
		# whatever their layer: a body knocked off the world layer must show up here as a pass-through.
		if cs.disabled or body == null or not (body is StaticBody2D):
			continue
		var rect := _global_rect(cs)
		if rect.size == Vector2.ZERO:
			skipped += 2
			continue
		var cx := rect.get_center().x
		# from the south: footprint top starts 40 px below the south face, walks north; stops when top == face.
		for spec in [[Vector2(cx, rect.end.y + FOOT.y + 40.0), Vector2(0, -80), rect.end.y + FOOT.y, "south"],
				[Vector2(cx, rect.position.y - 30.0), Vector2(0, 60), rect.position.y, "north"]]:
			var res := _probe(spec[0], spec[1])
			var stop_y: float = spec[2]
			var label := "%s from the %s" % [zone.get_path_to(cs), spec[3]]
			if res.start_blocked:
				skipped += 1
			elif not res.hit:
				f.append("%s: walked straight through (no collision)" % label)
			else:
				var past: bool = res.stop.y < stop_y - PROBE_TOL if spec[3] == "south" else res.stop.y > stop_y + PROBE_TOL
				var at: bool = absf(res.stop.y - stop_y) <= PROBE_TOL
				if past:
					f.append("%s: stopped at y %.2f, past the face (expected %.2f)" % [label, res.stop.y, stop_y])
				elif at and res.collider == body:
					stopped += 1
				else:
					shielded += 1
	_report(zone_id, "probes", f, "%d face stops at their own shape, %d stopped earlier by a neighbour, %d starts inside geometry (skipped), 0 pass-throughs allowed" % [stopped, shielded, skipped])
	return f


func _probe(from: Vector2, motion: Vector2) -> Dictionary:
	var start := Transform2D(0.0, from)
	if _player.test_move(start, Vector2.ZERO):
		return {"start_blocked": true}
	var col := KinematicCollision2D.new()
	var hit := _player.test_move(start, motion, col)
	return {"start_blocked": false, "hit": hit, "stop": from + (col.get_travel() if hit else motion), "collider": col.get_collider() if hit else null}


func _global_rect(cs: CollisionShape2D) -> Rect2:
	var rs := cs.shape as RectangleShape2D
	if rs == null:
		return Rect2()
	var t := cs.global_transform
	if absf(t.x.y) > EPS or absf(t.y.x) > EPS or t.x.x <= 0.0 or t.y.y <= 0.0:
		return Rect2()
	var size := Vector2(rs.size.x * t.x.x, rs.size.y * t.y.y)
	return Rect2(t.origin - size * 0.5, size)


# =================================================================================================
# reach: flood fill of standable feet positions

func _rule_reach(zone_id: String, zone: Zone, manifest: Dictionary) -> Array:
	var f := []
	if not manifest.has("playable_bounds"):
		_report(zone_id, "reach", ["manifest has no playable_bounds"], "flood fill")
		return ["no bounds"]
	var b: Array = manifest.playable_bounds
	var bounds := Rect2(b[0], b[1], b[2], b[3])
	var area := bounds.grow(64.0)
	var w := int(ceil(area.size.x / STEP)) + 1
	var h := int(ceil(area.size.y / STEP)) + 1
	var grid := PackedByteArray()
	grid.resize(w * h)
	var q := _foot_query()
	var space := get_world_2d().direct_space_state
	var markers := zone.get_spawn_markers()
	if markers.is_empty():
		_report(zone_id, "reach", ["zone has no spawn marker to start from"], "flood fill")
		return ["no spawn"]
	var queue := PackedInt32Array()
	for m in markers:
		var seed := _cell_of(m.global_position, area)
		if seed.x >= 0 and seed.x < w and seed.y >= 0 and seed.y < h and grid[seed.y * w + seed.x] == 0:
			if _free(space, q, _feet_of(seed, area)):
				grid[seed.y * w + seed.x] = 1
				queue.append(seed.y * w + seed.x)
		break  # flood from the first spawn only; the others must be reached
	var head := 0
	var leaks := []
	var reached := 0
	while head < queue.size():
		var idx := queue[head]
		head += 1
		reached += 1
		var cx := idx % w
		var cy := idx / w
		var feet := _feet_of(Vector2i(cx, cy), area)
		if not bounds.grow(2.0).has_point(feet) and leaks.size() < 50:
			leaks.append(feet)
		for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var nx: int = cx + d.x
			var ny: int = cy + d.y
			if nx < 0 or ny < 0 or nx >= w or ny >= h:
				continue
			var ni := ny * w + nx
			if grid[ni] != 0:
				continue
			if _free(space, q, _feet_of(Vector2i(nx, ny), area)):
				grid[ni] = 1
				queue.append(ni)
			else:
				grid[ni] = 2
	for p in leaks.slice(0, 5):
		f.append("player can stand at %s, outside the playable bounds %s (leak)" % [p, bounds])
	if leaks.size() > 5:
		f.append("... %d+ leaking positions in total" % leaks.size())
	for m in markers:
		if not _near_reached(grid, w, h, _cell_of(m.global_position, area)):
			f.append("spawn '%s' at %s is not reachable from spawn '%s'" % [m.spawn_id, m.global_position, markers[0].spawn_id])
	var doors := zone.get_doors()
	for door in doors:
		if not _door_reachable(door, grid, w, h, area):
			f.append("door %s at %s can't be reached close enough to interact" % [zone.get_path_to(door), door.global_position])
	_report(zone_id, "reach", f, "%d standable positions (%.0f m2) reached from '%s'; none outside %s; %d spawns and %d doors reachable" % [
		reached, reached * STEP * STEP / 1024.0, markers[0].spawn_id, bounds, markers.size(), doors.size()])
	return f


func _foot_query() -> PhysicsShapeQueryParameters2D:
	var shape := RectangleShape2D.new()
	shape.size = FOOT
	var q := PhysicsShapeQueryParameters2D.new()
	q.shape = shape
	q.collision_mask = LAYER_WORLD
	q.collide_with_areas = false
	q.collide_with_bodies = true
	return q


func _free(space: PhysicsDirectSpaceState2D, q: PhysicsShapeQueryParameters2D, feet: Vector2) -> bool:
	q.transform = Transform2D(0.0, feet + Vector2(0, -FOOT.y * 0.5))
	return space.intersect_shape(q, 1).is_empty()


func _cell_of(p: Vector2, area: Rect2) -> Vector2i:
	return Vector2i(roundi((p.x - area.position.x) / STEP), roundi((p.y - area.position.y) / STEP))


func _feet_of(c: Vector2i, area: Rect2) -> Vector2:
	return area.position + Vector2(c) * STEP


func _near_reached(grid: PackedByteArray, w: int, h: int, c: Vector2i) -> bool:
	for dy in range(-1, 2):
		for dx in range(-1, 2):
			var x := c.x + dx
			var y := c.y + dy
			if x >= 0 and y >= 0 and x < w and y < h and grid[y * w + x] == 1:
				return true
	return false


## The player's interaction circle (radius 24 at feet + (0, -6)) must be able to overlap the door's Interactable.
func _door_reachable(door: Node2D, grid: PackedByteArray, w: int, h: int, area: Rect2) -> bool:
	var reach := 0.0
	var centre := door.global_position
	for cs: CollisionShape2D in door.find_children("*", "CollisionShape2D", true, false):
		if cs.get_parent() is Interactable and cs.shape is CircleShape2D:
			reach = (cs.shape as CircleShape2D).radius * absf(cs.global_transform.x.x) + 24.0 - 1.0
			centre = cs.global_position
	if reach <= 0.0:
		return false
	var lo := _cell_of(centre - Vector2(reach, reach - 6.0), area)
	var hi := _cell_of(centre + Vector2(reach, reach + 6.0), area)
	for y in range(maxi(lo.y, 0), mini(hi.y, h - 1) + 1):
		for x in range(maxi(lo.x, 0), mini(hi.x, w - 1) + 1):
			if grid[y * w + x] == 1 and (_feet_of(Vector2i(x, y), area) + Vector2(0, -6)).distance_to(centre) < reach:
				return true
	return false


# =================================================================================================
# manifest cases: specific walks

func _rule_cases(zone_id: String, zone: Node, manifest: Dictionary) -> Array:
	var f := []
	var cases: Array = manifest.get("walks", [])
	for c: Dictionary in cases:
		var from := Vector2(c.from[0], c.from[1])
		var motion := Vector2(c.motion[0], c.motion[1])
		var res := _probe(from, motion)
		if res.start_blocked:
			f.append("%s: start %s is inside geometry" % [c.name, from])
			continue
		if c.expect == "free" and res.hit:
			f.append("%s: blocked at %s by %s" % [c.name, res.stop, zone.get_path_to(res.collider) if res.collider is Node else res.collider])
		elif c.expect == "stop":
			var want := Vector2(c.stop[0], c.stop[1])
			if not res.hit or res.stop.distance_to(want) > float(c.get("tol", PROBE_TOL)):
				f.append("%s: stopped at %s, expected %s" % [c.name, res.stop, want])
	_report(zone_id, "cases", f, "%d manifest walks behave as specified" % cases.size())
	return f


# =================================================================================================
# fades (OverheadVisibility)

func _rule_fades(zone_id: String, zone: Zone, manifest: Dictionary) -> Array:
	var f := []
	var areas: Array = zone.find_children("*", "OverheadVisibility", true, false)
	var home: Vector2 = zone.get_spawn_markers()[0].global_position if not zone.get_spawn_markers().is_empty() else Vector2.ZERO
	# The rules before this one run synchronously in one long frame; the frame after it has a huge delta that
	# would make any tween leap. Let frame timing settle so the smoothness measurement sees normal frames.
	await _settle_physics()
	await get_tree().create_timer(0.2).timeout
	var base_mod := _modulates(zone)
	# generic: each area fades exactly its own targets, smoothly, and restores them
	for area: OverheadVisibility in areas:
		var label := String(zone.get_path_to(area))
		if area.collision_layer != 0:
			f.append("%s collides (layer %d); fade areas must never block" % [label, area.collision_layer])
		if area.fade_seconds < MIN_FADE_SECONDS:
			f.append("%s: fade_seconds %.2f is too fast to read as a fade (minimum %.2f)" % [label, area.fade_seconds, MIN_FADE_SECONDS])
		var targets := []
		for tp in area.target_paths:
			var t := area.get_node_or_null(tp)
			if t == null:
				f.append("%s: target %s does not exist" % [label, tp])
			else:
				targets.append(t)
		var inside: Variant = _area_centre(area)
		if inside == null:
			f.append("%s: no rectangle shape to test" % label)
			continue
		_player.call("teleport", inside + Vector2(0, FOOT.y * 0.5))
		# TRANS_SINE / EASE_IN_OUT: steepest slope (pi/2) x range / duration; 25 % headroom.
		var max_rate := 1.25 * PI * 0.5 * (1.0 - area.faded_alpha) / maxf(area.fade_seconds, 0.001)
		var ratio: float = await _watch_alpha(targets, 0.45, max_rate)
		for t: CanvasItem in targets:
			if absf(t.modulate.a - area.faded_alpha) > 0.01:
				f.append("%s: target %s alpha %.2f inside, expected %.2f" % [label, zone.get_path_to(t), t.modulate.a, area.faded_alpha])
		if ratio > 1.0:
			f.append("%s: alpha changed %.1fx faster than its %.2f s ease allows in one frame (a jump, not a fade)" % [label, ratio, area.fade_seconds])
		var others := _changed_modulates(zone, base_mod, targets)
		if not others.is_empty():
			f.append("%s also changed %s" % [label, others.slice(0, 3)])
		_player.call("teleport", home)
		await _watch_alpha(targets, 0.45)
		for t: CanvasItem in targets:
			if absf(t.modulate.a - 1.0) > 0.01:
				f.append("%s: target %s not restored after leaving (alpha %.2f)" % [label, zone.get_path_to(t), t.modulate.a])
	# manifest: where each faded layer must / must not be faded
	var cases: Array = manifest.get("fade_cases", [])
	var layers: Array = manifest.get("fade_layers", [])
	for c: Dictionary in cases:
		_player.call("teleport", Vector2(c.feet[0], c.feet[1]))
		await _watch_alpha([], 0.45)
		for lp: String in layers:
			var item := zone.get_node_or_null(lp) as CanvasItem
			if item == null:
				f.append("fade layer %s does not exist" % lp)
				continue
			var want := 1.0 if not (c.faded as Array).has(lp) else 0.35
			if absf(item.modulate.a - want) > 0.01:
				f.append("'%s' %s: %s alpha %.2f, expected %.2f" % [c.name, c.feet, lp, item.modulate.a, want])
	_player.call("teleport", home)
	await _watch_alpha([], 0.45)
	_report(zone_id, "fades", f, "%d fade areas: never block, fade exactly their targets within their ease rate (never a jump) and restore; %d manifest fade cases" % [areas.size(), cases.size()])
	return f


func _area_centre(area: Area2D) -> Variant:
	for cs: CollisionShape2D in area.find_children("*", "CollisionShape2D", true, false):
		var r := _global_rect(cs)
		if r.size != Vector2.ZERO:
			return r.get_center()
	return null


## Waits `seconds` of real time, sampling `targets` every process frame (the fade tween runs on process
## frames). Returns the worst ratio of an observed alpha change to what an ease may change in that frame's
## real delta: `max_rate` (alpha per second) x delta + 0.01. A ratio > 1 is a jump. Normalising by the actual
## delta keeps this deterministic: a slow headless frame lets the tween move further, and that is allowed.
func _watch_alpha(targets: Array, seconds: float, max_rate: float = 0.0) -> float:
	var last := []
	for t: CanvasItem in targets:
		last.append(t.modulate.a)
	var worst := 0.0
	var start := Time.get_ticks_usec()
	# `process_frame` fires before that frame's tween step, so the change seen now was made with the previous
	# frame's delta. Bound it by the larger of the two adjacent deltas: correct whichever way the order falls.
	var prev_delta := get_process_delta_time()
	while (Time.get_ticks_usec() - start) / 1000000.0 < seconds:
		await get_tree().process_frame
		var delta := get_process_delta_time()
		var allowed := max_rate * maxf(delta, prev_delta) + 0.01
		prev_delta = delta
		for k in targets.size():
			var a: float = (targets[k] as CanvasItem).modulate.a
			if max_rate > 0.0:
				worst = maxf(worst, absf(a - last[k]) / allowed)
			last[k] = a
	await get_tree().physics_frame
	return worst


func _modulates(zone: Node) -> Dictionary:
	var out := {}
	for n in zone.find_children("*", "CanvasItem", true, false):
		out[n] = (n as CanvasItem).modulate
	return out


func _changed_modulates(zone: Node, before: Dictionary, except: Array) -> Array:
	var out := []
	for n in before:
		if not except.has(n) and is_instance_valid(n) and (n as CanvasItem).modulate != before[n]:
			out.append(String(zone.get_path_to(n)))
	return out


# =================================================================================================
# self-test: prove each rule catches a regression of its kind (main_gate_exterior, in memory)

func _self_test() -> void:
	const Z := "main_gate_exterior"
	var manifest := _load_json(DIR + "manifests/%s.json" % Z)
	var mutations := [
		["a palm moved 10 px", "snapshot"],
		["one ground cell repainted asphalt", "ground"],
		["a static body moved to the player layer", "conventions"],
		["a trunk's collision switched off the world layer", "probes"],
		["the south road wall removed (player escapes to the road)", "reach"],
		["a door pointed at a spawn that doesn't exist", "graph"],
		["the tower roof fade stops fading", "fades"],
		["a fade area set to 0 s (snaps)", "fades-duration"],
		["a fade area rewired to snap its roof instantly", "fades-snap"],
	]
	for m in mutations:
		var zone := _instantiate(Z)
		_mutate(m[1], zone)
		await _settle_physics()
		_quiet = true
		var caught: Array = []
		match m[1]:
			"snapshot": caught = _rule_snapshot(Z, zone, manifest)
			"ground": caught = _rule_ground(Z, zone, manifest)
			"conventions": caught = _rule_conventions(Z, zone, manifest)
			"probes": caught = _rule_probes(Z, zone)
			"reach": caught = _rule_reach(Z, zone, manifest)
			"graph": caught = _rule_graph(Z, zone)
			"fades", "fades-duration", "fades-snap": caught = await _rule_fades(Z, zone, manifest)
		_quiet = false
		_report(Z, "self-test", [] if not caught.is_empty() else ["mutation not detected"],
			"'%s' is caught by the %s rule (%d finding(s), e.g. %s)" % [m[0], m[1], caught.size(), str(caught[0]).left(110) if not caught.is_empty() else "-"])
		await _free_zone(zone)


func _first_palm(z: Node) -> Node2D:
	for n in _all_nodes(z):
		if (n as Node).scene_file_path.ends_with("CoconutPalm.tscn"):
			return n as Node2D
	return null


## Self-test stand-in for a broken fade: sets every target straight to the faded alpha.
func _snap_targets(body: Node2D, area: OverheadVisibility) -> void:
	if body is Player:
		for tp in area.target_paths:
			(area.get_node(tp) as CanvasItem).modulate.a = area.faded_alpha


func _mutate(rule: String, z: Node) -> void:
	match rule:
		"snapshot":
			_first_palm(z).position.x += 10.0
		"ground":
			var tm := z.find_children("*", "TileMapLayer", true, false)[0] as TileMapLayer
			tm.set_cell(Vector2i(0, 0), 3, Vector2i.ZERO)
		"conventions":
			(z.find_children("*", "StaticBody2D", true, false)[0] as StaticBody2D).collision_layer = LAYER_PLAYER
		"probes":
			for b: StaticBody2D in _first_palm(z).find_children("*", "StaticBody2D", true, false):
				b.collision_layer = 0
		"reach":
			var wall := z.get_node("Objects/Boundary/SouthWall")
			wall.get_parent().remove_child(wall)
			wall.free()
		"graph":
			(z as Zone).get_doors()[0].destination_spawn_id = "no_such_spawn"
		"fades":
			(z.find_children("*", "OverheadVisibility", true, false)[0] as OverheadVisibility).faded_alpha = 1.0
		"fades-duration":
			(z.find_children("*", "OverheadVisibility", true, false)[0] as OverheadVisibility).fade_seconds = 0.0
		"fades-snap":
			var area := z.find_children("*", "OverheadVisibility", true, false)[0] as OverheadVisibility
			area.body_entered.disconnect(area._on_body_entered)
			area.body_entered.connect(_snap_targets.bind(area))


# =================================================================================================
# helpers

## Every node under `root` including internal children (BlockoutBlock generates its collision and
## occluder as internal children, which find_children() would skip).
func _all_nodes(root: Node) -> Array:
	var out := [root]
	var i := 0
	while i < out.size():
		out.append_array((out[i] as Node).get_children(true))
		i += 1
	return out


func _load_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var d = JSON.parse_string(FileAccess.get_file_as_string(path))
	return d if d is Dictionary else {}


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


func _xf(t: Transform2D) -> Array:
	return [t.x.x, t.x.y, t.y.x, t.y.y, t.origin.x, t.origin.y]


func _pts(points: PackedVector2Array) -> Array:
	var out := []
	for p in points:
		out.append([p.x, p.y])
	return out


func _col(c: Color) -> Array:
	return [c.r, c.g, c.b, c.a]


func _res(r: Resource) -> String:
	if r == null:
		return ""
	return r.resource_path if not r.resource_path.is_empty() and not r.resource_path.contains("::") else "embedded:" + r.get_class()


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

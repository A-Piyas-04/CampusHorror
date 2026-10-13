extends SceneTree
## Headless check of a pipeline-generated prop scene against its render record.
## Run by assets/source/blender/build_asset.py:
##   godot --headless --path . --script res://scenes/tests/asset_previews/asset_scene_check.gd -- <scene res path> <record json abs path>

const TOLERANCE := 0.05
const OVERHEAD_SCRIPT := "res://scripts/components/overhead_visibility.gd"

var _failures: Array[String] = []


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 2:
		_fail("usage: -- <scene res path> <record json path>")
		_finish()
		return
	var scene_path: String = args[0]
	var record: Variant = JSON.parse_string(FileAccess.get_file_as_string(args[1]))
	if typeof(record) != TYPE_DICTIONARY:
		_fail("cannot read record %s" % args[1])
		_finish()
		return
	_check(scene_path, record)
	_finish()


func _check(scene_path: String, record: Dictionary) -> void:
	var packed := load(scene_path) as PackedScene
	if packed == null:
		_fail("scene did not load: %s" % scene_path)
		return
	var root := packed.instantiate() as Node2D
	if root == null:
		_fail("scene root is not a Node2D")
		return
	var godot: Dictionary = record["godot"]
	var lay: Dictionary = godot["layout"]
	_expect(root.name == godot["scene_name"], "root name %s" % root.name)
	_expect(root.get_meta("asset_id", "") == record["asset"], "root metadata asset_id")
	_expect(root.transform == Transform2D.IDENTITY, "root transform is identity")

	var sprite := root.get_node_or_null("Sprite") as Sprite2D
	if sprite == null or sprite.texture == null:
		_fail("Sprite with texture missing")
		root.free()
		return
	var image_px: Array = record["projection"]["image_px"]
	var tex_size := sprite.texture.get_size()
	_expect(tex_size == Vector2(image_px[0], image_px[1]), "texture size %s == %s" % [tex_size, image_px])
	_expect(sprite.texture.resource_path == "res://" + record["outputs"]["png"], "texture path %s" % sprite.texture.resource_path)
	_expect(not sprite.centered, "sprite not centered")
	# Texture2D.has_mipmaps() is always false with the headless dummy renderer; the image knows.
	var image := sprite.texture.get_image()
	_expect(image != null and image.has_mipmaps(), "texture imported with mipmaps (drawn at ~1/7 scale)")
	var scale_expected: float = lay["sprite_scale"]
	_expect(absf(sprite.scale.x - scale_expected) < 1e-4 and absf(sprite.scale.y - scale_expected) < 1e-4,
		"sprite scale %s == %.6f" % [sprite.scale, scale_expected])

	# Texture pixel -> root-local game px, exactly as Godot draws it.
	var to_local := func(px: Vector2) -> Vector2: return sprite.transform * (px + sprite.offset)
	var origin_px: Array = record["projection"]["origin_px"]
	var adjust: Array = godot["sprite_offset_adjust_px"]
	var origin_game: Vector2 = to_local.call(Vector2(origin_px[0], origin_px[1]))
	_expect(origin_game.distance_to(Vector2(adjust[0], adjust[1])) < TOLERANCE,
		"footprint origin pixel lands on node origin (+adjust): %s" % origin_game)

	var corners_px: Array = record["projection"]["footprint_corners_px"]
	var corners_game: Array = lay["footprint_game_px"]
	for i in corners_px.size():
		var got: Vector2 = to_local.call(Vector2(corners_px[i][0], corners_px[i][1]))
		var want := Vector2(corners_game[i][0], corners_game[i][1])
		_expect(got.distance_to(want) < TOLERANCE, "footprint corner %d %s == %s" % [i, got, want])
	var fp: Dictionary = record["footprint_m"]
	var length_game: float = to_local.call(Vector2(corners_px[1][0], corners_px[1][1])).x \
		- to_local.call(Vector2(corners_px[0][0], corners_px[0][1])).x
	var length_want: float = (fp["x_max"] - fp["x_min"]) * float(lay["game_px_per_m"])
	_expect(absf(length_game - length_want) < TOLERANCE, "footprint length %.3f game px == %.3f" % [length_game, length_want])
	_check_layers(root, record, Vector2(adjust[0], adjust[1]))

	var col: Variant = godot["collision"]
	var body := root.get_node_or_null("Body") as StaticBody2D
	if col == null:
		_expect(body == null, "no collision body when collision is disabled")
	elif body == null:
		_fail("Body (StaticBody2D) missing")
	else:
		_expect(body.collision_layer == int(col["layer"]) and body.collision_mask == int(col["mask"]),
			"collision layer %d / mask %d" % [body.collision_layer, body.collision_mask])
		var shapes: Array = col["shapes"] if col.has("shapes") \
			else [{"node": "Collision", "size": col["size"], "center": col["center"]}]
		_expect(body.get_child_count() == shapes.size(),
			"Body has %d collision shape(s), record %d" % [body.get_child_count(), shapes.size()])
		for want: Dictionary in shapes:
			var shape_node := body.get_node_or_null(NodePath(want["node"])) as CollisionShape2D
			if shape_node == null or not (shape_node.shape is RectangleShape2D):
				_fail("Body/%s with RectangleShape2D missing" % want["node"])
				continue
			var size := (shape_node.shape as RectangleShape2D).size
			_expect(size.distance_to(Vector2(want["size"][0], want["size"][1])) < TOLERANCE,
				"%s size %s" % [want["node"], size])
			_expect(shape_node.position.distance_to(Vector2(want["center"][0], want["center"][1])) < TOLERANCE,
				"%s centre %s" % [want["node"], shape_node.position])

	print("[ASSETCHECK] %s: sprite %.2f x %.2f game px, scale %.6f, origin %s, footprint %s" % [
		root.name, tex_size.x * sprite.scale.x, tex_size.y * sprite.scale.y, sprite.scale.x, origin_game,
		corners_game])
	root.free()


## Layer sprites: same canvas and pixel-to-origin mapping as Sprite, on their Y-sort point and z;
## fade areas: OverheadVisibility on the player layer only, aimed at their layer, shapes as recorded.
func _check_layers(root: Node2D, record: Dictionary, adjust: Vector2) -> void:
	var lay: Dictionary = record["godot"]["layout"]
	var layers: Array = lay.get("layers") if lay.get("layers") != null else []
	var recorded: Array = record.get("layers") if record.get("layers") != null else []
	_expect(layers.size() == recorded.size(), "%d layer(s) in the layout, %d rendered" % [layers.size(), recorded.size()])
	var image_px: Array = record["projection"]["image_px"]
	var origin_px: Array = record["projection"]["origin_px"]
	var scale_expected: float = lay["sprite_scale"]
	var any_sorted := false
	for i in mini(layers.size(), recorded.size()):
		var want: Dictionary = layers[i]
		var name: String = want["name"]
		var sprite := root.get_node_or_null(NodePath(name)) as Sprite2D
		if sprite == null or sprite.texture == null:
			_fail("layer sprite %s with texture missing" % name)
			continue
		var pos := Vector2(want["position_game_px"][0], want["position_game_px"][1])
		any_sorted = any_sorted or not is_zero_approx(pos.y)
		_expect(sprite.texture.resource_path == "res://" + String(recorded[i]["png"])
			and sprite.texture.get_size() == Vector2(image_px[0], image_px[1]),
			"layer %s texture %s, %s" % [name, sprite.texture.resource_path, sprite.texture.get_size()])
		var image := sprite.texture.get_image()
		_expect(image != null and image.has_mipmaps(), "layer %s imported with mipmaps" % name)
		_expect(not sprite.centered and absf(sprite.scale.x - scale_expected) < 1e-4 and absf(sprite.scale.y - scale_expected) < 1e-4
			and sprite.position.distance_to(pos) < TOLERANCE and sprite.z_index == int(want["z_index"])
			and sprite.light_mask == (root.get_node("Sprite") as Sprite2D).light_mask,
			"layer %s: scale %s, position %s (sort point), z %d, light mask %d" % [name, sprite.scale, sprite.position, sprite.z_index, sprite.light_mask])
		var origin_game: Vector2 = sprite.transform * (Vector2(origin_px[0], origin_px[1]) + sprite.offset)
		_expect(origin_game.distance_to(adjust) < TOLERANCE,
			"layer %s: footprint origin pixel lands on node origin (+adjust): %s" % [name, origin_game])
		var fade: Variant = want["fade"]
		var area := root.get_node_or_null(NodePath(name + "Fade")) as Area2D
		if fade == null:
			_expect(area == null, "layer %s has no fade area" % name)
			continue
		if area == null or area.get_script() == null or (area.get_script() as Script).resource_path != OVERHEAD_SCRIPT:
			_fail("%sFade (%s) missing" % [name, OVERHEAD_SCRIPT])
			continue
		var paths: Array = area.get("target_paths")
		_expect(area.collision_layer == 0 and area.collision_mask == 2 and not area.monitorable
			and paths.size() == 1 and area.get_node_or_null(paths[0]) == sprite
			and absf(float(area.get("faded_alpha")) - float(fade["alpha"])) < 1e-4
			and absf(float(area.get("fade_seconds")) - float(fade["seconds"])) < 1e-4,
			"%s: layer 0 / mask 2 (player), not monitorable, targets %s, alpha %.2f, %.2f s" % [area.name, name, area.get("faded_alpha"), area.get("fade_seconds")])
		var shapes: Array = fade["shapes"]
		_expect(area.get_child_count() == shapes.size(), "%s has %d shape(s), record %d" % [area.name, area.get_child_count(), shapes.size()])
		for s: Dictionary in shapes:
			var cs := area.get_node_or_null(NodePath(s["node"])) as CollisionShape2D
			if cs == null or not (cs.shape is RectangleShape2D):
				_fail("%s/%s with RectangleShape2D missing" % [area.name, s["node"]])
				continue
			_expect((cs.shape as RectangleShape2D).size.distance_to(Vector2(s["size"][0], s["size"][1])) < TOLERANCE
				and cs.position.distance_to(Vector2(s["center"][0], s["center"][1])) < TOLERANCE,
				"%s/%s size %s centre %s" % [area.name, s["node"], (cs.shape as RectangleShape2D).size, cs.position])
	_expect(root.y_sort_enabled == any_sorted, "root y_sort_enabled %s (a layer sorts away from the origin: %s)" % [root.y_sort_enabled, any_sorted])


func _expect(condition: bool, what: String) -> void:
	if condition:
		print("[ASSETCHECK] ok   ", what)
	else:
		_fail(what)


func _fail(what: String) -> void:
	_failures.append(what)
	printerr("[ASSETCHECK] FAIL ", what)


func _finish() -> void:
	if _failures.is_empty():
		print("[ASSETCHECK] PASS")
		quit(0)
	else:
		print("[ASSETCHECK] FAILED (%d)" % _failures.size())
		quit(1)

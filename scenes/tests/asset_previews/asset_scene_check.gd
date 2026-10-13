extends SceneTree
## Headless check of a pipeline-generated prop scene against its render record.
## Run by assets/source/blender/build_asset.py:
##   godot --headless --path . --script res://scenes/tests/asset_previews/asset_scene_check.gd -- <scene res path> <record json abs path>

const TOLERANCE := 0.05

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

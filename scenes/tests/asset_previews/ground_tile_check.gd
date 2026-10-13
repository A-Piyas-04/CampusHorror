extends SceneTree
## Headless check of a pipeline-generated ground tile: its source in the shared TileSet and its
## TileMapLayer preview, against the render record. Run by assets/source/blender/build_asset.py:
##   godot --headless --path . --script res://scenes/tests/asset_previews/ground_tile_check.gd -- \
##       <tileset res path> <record json abs path> <preview res path>

var _failures: Array[String] = []


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 3:
		_fail("usage: -- <tileset res path> <record json path> <preview res path>")
		_finish()
		return
	var record: Variant = JSON.parse_string(FileAccess.get_file_as_string(args[1]))
	if typeof(record) != TYPE_DICTIONARY:
		_fail("cannot read record %s" % args[1])
		_finish()
		return
	_check_tileset(args[0], record)
	_check_preview(args[2], args[0], record)
	_finish()


func _check_tileset(tileset_path: String, record: Dictionary) -> void:
	var tileset := load(tileset_path) as TileSet
	if tileset == null:
		_fail("TileSet did not load: %s" % tileset_path)
		return
	var godot: Dictionary = record["godot"]
	var tile_px := int(godot["tile_size_px"])
	var source_id := int(godot["source_id"])
	_expect(tileset.tile_size == Vector2i(tile_px, tile_px), "tile_size %s == %d px" % [tileset.tile_size, tile_px])
	_expect(tileset.get_physics_layers_count() == 0, "no physics layers (ground tiles have no collision)")
	_expect(tileset.get_source_count() == godot["tileset_sources"].size(),
		"TileSet has %d source(s), record %d" % [tileset.get_source_count(), godot["tileset_sources"].size()])
	if not tileset.has_source(source_id):
		_fail("TileSet has no source %d" % source_id)
		return
	var source := tileset.get_source(source_id) as TileSetAtlasSource
	if source == null or source.texture == null:
		_fail("source %d is not a TileSetAtlasSource with a texture" % source_id)
		return
	_expect(source.texture.resource_path == "res://" + record["outputs"]["png"],
		"source %d texture %s" % [source_id, source.texture.resource_path])
	_expect(source.texture.get_size() == Vector2(tile_px, tile_px),
		"texture size %s == %d px" % [source.texture.get_size(), tile_px])
	_expect(source.texture_region_size == Vector2i(tile_px, tile_px), "texture_region_size %s" % source.texture_region_size)
	_expect(source.get_tiles_count() == 1 and source.has_tile(Vector2i.ZERO), "exactly one tile at atlas (0, 0)")
	# Texture2D.has_mipmaps() is always false with the headless dummy renderer; the image knows.
	var image := source.texture.get_image()
	_expect(image != null and not image.has_mipmaps(), "texture imported without mipmaps (drawn 1:1 by the TileMapLayer)")
	if image != null:
		image.decompress()
		var min_alpha := 1.0
		for y in image.get_height():
			for x in image.get_width():
				min_alpha = minf(min_alpha, image.get_pixel(x, y).a)
		_expect(min_alpha > 0.999, "imported texture fully opaque (min alpha %.3f)" % min_alpha)
	print("[GROUNDCHECK] %s: source %d, %d x %d px tile, texture %s" % [
		record["asset"], source_id, tile_px, tile_px, source.texture.resource_path])


func _check_preview(preview_path: String, tileset_path: String, record: Dictionary) -> void:
	var packed := load(preview_path) as PackedScene
	if packed == null:
		_fail("preview did not load: %s" % preview_path)
		return
	var root := packed.instantiate()
	var layer := root.get_node_or_null("Tiles") as TileMapLayer
	if layer == null:
		_fail("preview has no Tiles (TileMapLayer)")
		root.free()
		return
	_expect(layer.tile_set != null and layer.tile_set.resource_path == tileset_path,
		"preview TileMapLayer uses %s" % tileset_path)
	_expect(layer.z_index == -10, "preview ground z_index %d == -10" % layer.z_index)
	var cells: Array = record["godot"].get("preview_cells", [])
	_expect(layer.get_used_cells().size() == cells.size(),
		"preview has %d used cells, record %d" % [layer.get_used_cells().size(), cells.size()])
	var wrong := 0
	for c: Array in cells:
		var cell := Vector2i(int(c[0]), int(c[1]))
		if layer.get_cell_source_id(cell) != int(c[2]) or layer.get_cell_atlas_coords(cell) != Vector2i.ZERO:
			wrong += 1
	_expect(wrong == 0, "every preview cell has the recorded source and atlas tile (%d wrong)" % wrong)
	root.free()


func _expect(condition: bool, what: String) -> void:
	if condition:
		print("[GROUNDCHECK] ok   ", what)
	else:
		_fail(what)


func _fail(what: String) -> void:
	_failures.append(what)
	printerr("[GROUNDCHECK] FAIL ", what)


func _finish() -> void:
	if _failures.is_empty():
		print("[GROUNDCHECK] PASS")
		quit(0)
	else:
		print("[GROUNDCHECK] FAILED (%d)" % _failures.size())
		quit(1)

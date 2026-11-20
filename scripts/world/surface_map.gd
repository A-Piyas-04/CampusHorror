class_name SurfaceMap
extends RefCounted

## Answers "what surface is under this point?" for one zone (footsteps now; noise in J5).
## Built by Main whenever a zone is entered. Rule (same as the validator's ground lattice, plus landmark
## floors): the topmost Polygon2D whose texture is a ground texture (edge strips, gate plaza, passage, CDS
## forecourt; highest effective z, then later in tree order), else the topmost TileMapLayer cell, else the
## zone profile's default surface.

const TABLE_PATH := "res://data/audio/surfaces.tres"

var _table: Dictionary = {}
var _default: StringName = &"grass"
## [{poly, inv, bbox, surface, order}], sorted so the topmost is last.
var _polys: Array = []
## [{layer, order}], topmost last.
var _layers: Array = []


static func build(zone: Node, default_surface: StringName) -> SurfaceMap:
	var map := SurfaceMap.new()
	map._default = default_surface
	var table := load(TABLE_PATH) as SurfaceTable
	if table != null:
		map._table = table.by_texture_stem
	map._collect(zone, [0])
	map._polys.sort_custom(func(a, b): return a.order < b.order)
	map._layers.sort_custom(func(a, b): return a.order < b.order)
	return map


## Depth-first, so `order` follows Godot's draw order among nodes of equal z.
func _collect(node: Node, counter: Array) -> void:
	counter[0] += 1
	var order: int = counter[0]
	if node is Polygon2D and (node as Polygon2D).texture != null:
		var pg := node as Polygon2D
		var surface: StringName = _table.get(_stem(pg.texture), &"")
		if surface != &"" and pg.polygon.size() >= 3:
			var bb := Rect2(pg.global_transform * pg.polygon[0], Vector2.ZERO)
			for v in pg.polygon:
				bb = bb.expand(pg.global_transform * v)
			_polys.append({"poly": pg.polygon, "inv": pg.global_transform.affine_inverse(), "bbox": bb,
				"surface": surface, "order": _z(pg) * 1000000 + order})
	elif node is TileMapLayer and (node as TileMapLayer).tile_set != null:
		_layers.append({"layer": node, "order": _z(node as CanvasItem) * 1000000 + order})
	for child in node.get_children():
		_collect(child, counter)


func surface_at(world_pos: Vector2) -> StringName:
	for i in range(_polys.size() - 1, -1, -1):
		var e: Dictionary = _polys[i]
		if (e.bbox as Rect2).has_point(world_pos) and Geometry2D.is_point_in_polygon(e.inv * world_pos, e.poly):
			return e.surface
	for i in range(_layers.size() - 1, -1, -1):
		var layer: TileMapLayer = _layers[i].layer
		if not is_instance_valid(layer):
			continue
		var cell := layer.local_to_map(layer.to_local(world_pos))
		var src := layer.get_cell_source_id(cell)
		if src == -1:
			continue
		var atlas := layer.tile_set.get_source(src) as TileSetAtlasSource
		if atlas != null and atlas.texture != null:
			var s: StringName = _table.get(_stem(atlas.texture), &"")
			if s != &"":
				return s
	return _default


func get_default_surface() -> StringName:
	return _default


static func _stem(tex: Texture2D) -> String:
	return tex.resource_path.get_file().get_basename() if tex != null else ""


static func _z(item: CanvasItem) -> int:
	var z := 0
	var node: Node = item
	while node is CanvasItem:
		z += (node as CanvasItem).z_index
		if not (node as CanvasItem).z_as_relative:
			break
		node = node.get_parent()
	return z

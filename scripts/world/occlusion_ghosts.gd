class_name OcclusionGhosts
extends Node

## Roadmap I6: the player is never lost behind scenery, systemically, with no hand-placed areas.
##
## When the player stands behind something (a building facade, a wall, a tree canopy, a roof), a silhouette of
## the player's CURRENT animation frame is drawn through it. Each silhouette ("ghost") is a pooled Sprite2D added
## as a child of the occluding sprite, and that sprite gets `clip_children = CLIP_CHILDREN_AND_DRAW`, so the ghost
## is clipped to the occluder's own pixels: it shows exactly where the player is hidden and nowhere else.
##
## Which items occlude: every drawable item in the zone with effective z >= 0 (prop sprites and their render
## layers, Polygon2D blockout pieces, BlockoutBlocks; not ground, not contact shadows), indexed once per zone
## (scenery is static). Each physics tick an item gets a ghost when its rectangle overlaps the player's frame
## AND it draws after the player (higher z, or the same z and a later Y-sort position). Items behind the player
## never get one, so the silhouette's rim can't show as a halo around a player standing in front of a wall.
##
## Ghosts update in physics ticks like the player, so physics interpolation moves them in step on 144 Hz screens.
## Main calls `index_zone()` after entering a zone and `release_all()` before freeing one.
## Roof fades (OverheadVisibility) are kept: they let the player see what is UNDER a roof; ghosts only guarantee
## that the player is visible.

const SILHOUETTE := preload("res://assets/shaders/player_silhouette.gdshader")
const SHADOW_SCENE := "res://scenes/props/common/ContactShadow.tscn"

## Switch the system off (for comparisons and tests); releases every ghost.
@export var enabled := true:
	set(value):
		enabled = value
		if not enabled:
			release_all()
## Safety cap on simultaneous ghosts.
@export var max_ghosts := 16

var _player: Player
var _sprite: AnimatedSprite2D
var _material: ShaderMaterial
## [{item, rect, z, sort_y}] for the current zone.
var _occluders: Array = []
## occluding item -> ghost Sprite2D attached to it.
var _attached: Dictionary = {}
## occluding item -> its clip_children before a ghost was attached.
var _clip_before: Dictionary = {}
var _pool: Array[Sprite2D] = []


func setup(player: Player) -> void:
	_player = player
	_sprite = player.get_node("Sprite") as AnimatedSprite2D
	_material = ShaderMaterial.new()
	_material.shader = SILHOUETTE


## Rebuilds the occluder index for a newly entered zone.
func index_zone(zone: Node) -> void:
	release_all()
	_occluders.clear()
	_collect(zone)


## Detaches every ghost (before a zone is freed, or when disabled).
func release_all() -> void:
	for item in _attached.keys():
		_detach(item)


func get_occluder_count() -> int:
	return _occluders.size()


## Items currently showing a ghost (for tests).
func get_attached_items() -> Array:
	return _attached.keys()


func get_ghost_for(item: CanvasItem) -> Sprite2D:
	return _attached.get(item)


func get_pool_size() -> int:
	return _pool.size() + _attached.size()


func _physics_process(_delta: float) -> void:
	if not enabled or _player == null or _sprite == null:
		return
	var tex := _sprite.sprite_frames.get_frame_texture(_sprite.animation, _sprite.frame)
	if tex == null:
		return
	var prect := _sprite.global_transform * Rect2(_sprite.offset, tex.get_size())
	var pz := _effective_z(_sprite)
	var py := _player.global_position.y
	var want := {}
	for o in _occluders:
		var item: CanvasItem = o.item
		if not is_instance_valid(item) or not (o.rect as Rect2).intersects(prect) or not item.is_visible_in_tree():
			continue
		if o.z > pz or (o.z == pz and o.sort_y > py):
			want[item] = true
			if want.size() >= max_ghosts:
				break
	for item in _attached.keys():
		if not want.has(item):
			_detach(item)
	for item in want:
		if not _attached.has(item):
			_attach(item)
	for item in _attached:
		var g: Sprite2D = _attached[item]
		g.texture = tex
		g.offset = _sprite.offset
		g.flip_h = _sprite.flip_h
		g.global_transform = _sprite.global_transform


func _attach(item: CanvasItem) -> void:
	var g: Sprite2D = _pool.pop_back() if not _pool.is_empty() else _new_ghost()
	if g.get_parent() != null:
		g.get_parent().remove_child(g)
	item.add_child(g, false, Node.INTERNAL_MODE_BACK)
	g.visible = true
	g.global_transform = _sprite.global_transform
	g.reset_physics_interpolation()
	_clip_before[item] = item.clip_children
	item.clip_children = CanvasItem.CLIP_CHILDREN_AND_DRAW
	_attached[item] = g


func _detach(item: Variant) -> void:
	var g: Sprite2D = _attached.get(item)
	_attached.erase(item)
	if is_instance_valid(item):
		(item as CanvasItem).clip_children = _clip_before.get(item, CanvasItem.CLIP_CHILDREN_DISABLED)
	_clip_before.erase(item)
	if is_instance_valid(g):
		if g.get_parent() != null:
			g.get_parent().remove_child(g)
		g.visible = false
		add_child(g)
		_pool.append(g)


func _new_ghost() -> Sprite2D:
	var g := Sprite2D.new()
	g.name = "OcclusionGhost"
	g.centered = false
	g.material = _material
	g.light_mask = _sprite.light_mask
	g.scale = Vector2.ONE
	g.visible = false
	return g


# --- Indexing --------------------------------------------------------------------------------------------

func _collect(node: Node) -> void:
	if node.scene_file_path == SHADOW_SCENE:
		return
	if node is CanvasItem and not (node is Control) and _effective_z(node as CanvasItem) >= 0:
		var rect := _world_rect(node as CanvasItem)
		if rect.size.x > 0.0 and rect.size.y > 0.0:
			_occluders.append({"item": node, "rect": rect, "z": _effective_z(node as CanvasItem), "sort_y": _sort_y(node as CanvasItem)})
	for child in node.get_children():
		_collect(child)


## World-space bounds of what the item draws (static scenery), or an empty rect if it draws nothing we know.
func _world_rect(item: CanvasItem) -> Rect2:
	if item is Sprite2D:
		var s := item as Sprite2D
		return s.global_transform * s.get_rect() if s.texture != null else Rect2()
	if item is Polygon2D:
		var p := item as Polygon2D
		if p.polygon.size() < 3:
			return Rect2()
		var r := Rect2(p.global_transform * (p.polygon[0] + p.offset), Vector2.ZERO)
		for v in p.polygon:
			r = r.expand(p.global_transform * (v + p.offset))
		return r
	if item is BlockoutBlock:
		var b := item as BlockoutBlock
		var w := b.footprint_size.x
		var d := b.footprint_size.y
		return b.global_transform * Rect2(-w / 2.0, -d - b.wall_height, w, d + b.wall_height)
	return Rect2()


## The Y the renderer sorts this item by: the global Y of the nearest ancestor-or-self whose parent Y-sorts.
func _sort_y(item: CanvasItem) -> float:
	var node: Node = item
	while node.get_parent() is Node2D and not (node.get_parent() as Node2D).y_sort_enabled:
		node = node.get_parent()
	return (node as Node2D).global_position.y if node is Node2D else INF


func _effective_z(item: CanvasItem) -> int:
	var z := 0
	var node: Node = item
	while node is CanvasItem:
		z += (node as CanvasItem).z_index
		if not (node as CanvasItem).z_as_relative:
			break
		node = node.get_parent()
	return z

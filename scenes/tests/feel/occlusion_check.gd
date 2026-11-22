extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I occlusion suite (I6), on the real Main.tscn. Headless: the logic (which occluders get a ghost, ghost
## state, clip modes, pool, zone changes, cost). Windowed (`--pixels`, no --headless): the rendering, by
## comparing screenshots with ghosts on and off.

const FIELD := Vector2(12320, 4300)
## Map v2: a palm of the halls' palm avenue stands in for the occluding sprite. Buildings are rendered art
## (author_campus_v2.py): each footprint part is its own Y-sorted layer that fades (D31) while the player is behind.
const AVENUE_PALM_AT := Vector2(11200, 938)     # (350 m, 45.6 m)
const CDS := "Objects/Buildings/Cds/Art/P0Part0"     # the CDS main block's layer sprite
const BEHIND_CDS := Vector2(11520, 2346)        # (360 m, 114 m): between the spine road and the CDS's north face

var ghosts: OcclusionGhosts
var behind_tree := Vector2.ZERO
var tree: CanvasItem


func _run() -> void:
	tag = "OCCLUSION"
	ghosts = main.get_node("OcclusionGhosts") as OcclusionGhosts
	var zone := main.get_current_zone()
	var expected := _count_drawables(zone)
	check(expected > 100 and ghosts.get_occluder_count() == expected,
		"campus: indexed %d occluders = %d counted independently (textured sprites, polygons and blockout blocks at z >= 0, not contact shadows)" % [ghosts.get_occluder_count(), expected])

	await place(FIELD)
	check(ghosts.get_attached_items().is_empty(), "in the open field nothing hides the player: no ghosts")

	var palm := _nearest_tree(zone, AVENUE_PALM_AT)
	check(palm != null, "found the palm of the halls avenue nearest %s" % AVENUE_PALM_AT)
	if palm == null:
		return
	tree = palm.get_node("Sprite") as CanvasItem
	behind_tree = palm.global_position + Vector2(0, -24)
	await place(behind_tree)
	var g := ghosts.get_ghost_for(tree)
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	check(g != null and tree.clip_children == CanvasItem.CLIP_CHILDREN_AND_DRAW and g.get_parent() == tree,
		"behind a palm (north of the trunk) its sprite carries a ghost and clips it to its own pixels")
	if g != null:
		check(g.texture == sprite.sprite_frames.get_frame_texture(sprite.animation, sprite.frame)
			and g.global_transform.is_equal_approx(sprite.global_transform) and g.light_mask == sprite.light_mask
			and (g.material as ShaderMaterial).shader.resource_path.ends_with("player_silhouette.gdshader"),
			"the ghost shows the player's current frame at the player's exact transform, lit like the player, with the silhouette shader")
	await place(palm.global_position + Vector2(0, 30))
	check(ghosts.get_ghost_for(tree) == null and tree.clip_children == CanvasItem.CLIP_CHILDREN_DISABLED,
		"in front of the same palm it gets no ghost (no halo around a visible player) and its clip mode is restored")

	# Buildings: walking behind one fades it (D31), walking out restores it.
	var cds := zone.get_node_or_null(CDS) as CanvasItem
	await place(BEHIND_CDS)
	await seconds(1.0)
	var faded := cds.modulate.a if cds != null else 1.0
	await place(FIELD)
	await seconds(1.0)
	var restored := cds.modulate.a if cds != null else 0.0
	check(cds != null and faded < 0.5 and restored > 0.99,
		"behind the CDS the building fades to %.2f, and comes back to %.2f once the player is in the open" % [faded, restored])

	# Animation: walking behind the palm, the ghost follows the frames.
	await place(behind_tree + Vector2(-60, 0))
	var textures := {}
	await hold(["move_right"], 60, 1.0, func(_i):
		var gt := ghosts.get_ghost_for(tree)
		if gt != null:
			textures[gt.texture] = true)
	check(textures.size() >= 4, "walking behind the palm, the ghost follows the walk cycle (%d distinct frames)" % textures.size())

	# Pool and clip modes over repeated hide / show cycles.
	var pool_before := ghosts.get_pool_size()
	for i in 5:
		await place(behind_tree)
		await place(FIELD)
	var clipped := 0
	for n in zone.find_children("*", "CanvasItem", true, false):
		if (n as CanvasItem).clip_children != CanvasItem.CLIP_CHILDREN_DISABLED:
			clipped += 1
	check(ghosts.get_attached_items().is_empty() and clipped == 0 and ghosts.get_pool_size() == pool_before,
		"after 5 hide / show cycles: no ghost left, no item left clipping (%d), pool stable (%d -> %d)" % [clipped, pool_before, ghosts.get_pool_size()])

	# Cost per tick with ghosts attached.
	await place(behind_tree)
	var t := Time.get_ticks_usec()
	for i in 200:
		ghosts._physics_process(0.0)
	var per_tick_ms := (Time.get_ticks_usec() - t) / 200.0 / 1000.0
	check(per_tick_ms < 0.3, "occlusion update costs %.3f ms per tick over %d occluders (budget 0.3 ms)" % [per_tick_ms, ghosts.get_occluder_count()])

	# A faded travel while ghosts are attached.
	var pool := ghosts.get_pool_size()
	check(main.travel("cds_veranda", "inside_cds_entry"), "travel to cds_veranda while a ghost is attached")
	await await_travel()
	check(main.get_current_zone_id() == "cds_veranda" and ghosts.get_pool_size() == pool and ghosts.get_occluder_count() > 0,
		"after the trip the pool is intact (%d ghosts) and the veranda is indexed (%d occluders)" % [ghosts.get_pool_size(), ghosts.get_occluder_count()])
	main.change_zone("campus", "explore_start")
	await frames(3)
	zone = main.get_current_zone()
	palm = _nearest_tree(zone, AVENUE_PALM_AT)
	tree = palm.get_node("Sprite") as CanvasItem

	ghosts.enabled = false
	await place(behind_tree)
	check(ghosts.get_attached_items().is_empty(), "with the system disabled no ghost is attached")
	ghosts.enabled = true
	await place(behind_tree)
	check(ghosts.get_ghost_for(tree) != null, "re-enabled, the ghost is back")

	if OS.get_cmdline_user_args().has("--pixels"):
		await _pixels()


func _nearest_tree(zone: Node, at: Vector2) -> Node2D:
	var best: Node2D = null
	for n in zone.get_node("Objects/Vegetation").get_children():
		if n is Node2D and (best == null or (n as Node2D).global_position.distance_to(at) < best.global_position.distance_to(at)):
			best = n
	return best


## Windowed only: renders the same view with ghosts on and off. The player's idle animation is frozen on one
## frame, so the only thing that can differ between the two renders is the ghost.
func _pixels() -> void:
	var anim_sprite := player.get_node("Sprite") as AnimatedSprite2D
	var control: Variant = await _halo_control_spot()
	check(control != null, "found a spot just in front of a tree / palm with nothing in front of the player (%s)" % [control])
	if control == null:
		return
	for spec in [["behind the avenue palm", behind_tree, true], ["just in front of a tree that overlaps the player from behind", control, false]]:
		await place(spec[1])
		await seconds(0.6)            # roof fades and any depenetration settle before comparing
		anim_sprite.pause()
		anim_sprite.set_frame_and_progress(0, 0.0)
		ghosts.enabled = true
		await frames(4)
		await RenderingServer.frame_post_draw
		var on := get_viewport().get_texture().get_image()
		ghosts.enabled = false
		await frames(4)
		await RenderingServer.frame_post_draw
		var off := get_viewport().get_texture().get_image()
		ghosts.enabled = true
		anim_sprite.play()
		var centre := Vector2i(on.get_width() / 2, on.get_height() / 2)
		var changed := 0
		for y in range(centre.y - 110, centre.y + 30):
			for x in range(centre.x - 40, centre.x + 40):
				var a := on.get_pixel(x, y)
				var b := off.get_pixel(x, y)
				if absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b) > 0.06:
					changed += 1
		if spec[2]:
			check(changed > 300, "%s: the silhouette is drawn (%d pixels around the player differ, ghosts on vs off)" % [spec[0], changed])
		else:
			check(changed == 0, "%s: ghosts on vs off render identically (%d pixels differ)" % [spec[0], changed])


## Independent count of what should be indexed (not using OcclusionGhosts' own walk).
func _count_drawables(root: Node) -> int:
	var n := 0
	var stack: Array = [root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		if node.scene_file_path == "res://scenes/props/common/ContactShadow.tscn":
			continue
		stack.append_array(node.get_children())
		var drawable: bool = (node is Sprite2D and (node as Sprite2D).texture != null) or node is Polygon2D or node is BlockoutBlock
		if not drawable:
			continue
		var z := 0
		var a: Node = node
		while a is CanvasItem:
			z += (a as CanvasItem).z_index
			if not (a as CanvasItem).z_as_relative:
				break
			a = a.get_parent()
		if z >= 0:
			n += 1
	return n


## A spot 24 px in front of a tree or palm trunk where that tree's sprite overlaps the player's frame (it is
## behind the player) and nothing in front of the player is attached: the halo case. Searched, not hand-picked,
## because many trees stand near walls or other crowns that legitimately cover the player.
func _halo_control_spot() -> Variant:
	var zone := main.get_current_zone()
	for root in zone.find_children("*", "Node2D", true, false):
		if not (root.scene_file_path.ends_with("BroadleafTree.tscn") or root.scene_file_path.ends_with("CoconutPalm.tscn")):
			continue
		var pos: Vector2 = (root as Node2D).global_position + Vector2(0, 24)   # clear of the trunk's collision
		await place(pos)
		await frames(2)
		if ghosts.get_attached_items().is_empty():
			return pos
	return null

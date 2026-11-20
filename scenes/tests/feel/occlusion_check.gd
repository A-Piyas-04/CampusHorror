extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I occlusion suite (I6), on the real Main.tscn. Headless: the logic (which occluders get a ghost, ghost
## state, clip modes, pool, zone changes, cost). Windowed (`--pixels`, no --headless): the rendering, by
## comparing screenshots with ghosts on and off.

const TOWER := "Objects/Buildings/MainGateLandmark/Tower/Sprite"
const TREE := "Objects/Vegetation/SouthTreeRow/Tree04/Sprite"
const FIELD := Vector2(-1000, -200)
const DEAD_BAND := Vector2(-1270, 1255)       # behind the gate tower's east pier (fully hidden before I6)
const BEHIND_TREE := Vector2(-200, 1296)
const FRONT_OF_TREE := Vector2(-200, 1330)
const BEHIND_WALL := Vector2(300, 1392)

var ghosts: OcclusionGhosts


func _run() -> void:
	tag = "OCCLUSION"
	ghosts = main.get_node("OcclusionGhosts") as OcclusionGhosts
	var zone := main.get_current_zone()
	var expected := _count_drawables(zone)
	check(expected > 100 and ghosts.get_occluder_count() == expected,
		"main_gate_exterior: indexed %d occluders = %d counted independently (textured sprites, polygons and blockout blocks at z >= 0, not contact shadows)" % [ghosts.get_occluder_count(), expected])

	await place(FIELD)
	check(ghosts.get_attached_items().is_empty(), "in the open field nothing hides the player: no ghosts")

	await place(DEAD_BAND)
	var tower := zone.get_node(TOWER) as CanvasItem
	var g := ghosts.get_ghost_for(tower)
	var sprite := player.get_node("Sprite") as AnimatedSprite2D
	check(g != null and tower.clip_children == CanvasItem.CLIP_CHILDREN_AND_DRAW and g.get_parent() == tower,
		"behind the gate tower (the old dead band) the tower carries a ghost and clips it to its own pixels")
	if g != null:
		check(g.texture == sprite.sprite_frames.get_frame_texture(sprite.animation, sprite.frame)
			and g.global_transform.is_equal_approx(sprite.global_transform) and g.light_mask == sprite.light_mask
			and (g.material as ShaderMaterial).shader.resource_path.ends_with("player_silhouette.gdshader"),
			"the ghost shows the player's current frame at the player's exact transform, lit like the player, with the silhouette shader")

	await place(BEHIND_TREE)
	var tree := zone.get_node(TREE) as CanvasItem
	check(ghosts.get_ghost_for(tree) != null, "behind a tree (north of the trunk) its canopy and trunk carry a ghost")
	await place(FRONT_OF_TREE)
	check(ghosts.get_ghost_for(tree) == null and tree.clip_children == CanvasItem.CLIP_CHILDREN_DISABLED,
		"in front of the same tree it gets no ghost (no halo around a visible player) and its clip mode is restored")
	await place(BEHIND_WALL)
	var wall_items := ghosts.get_attached_items().filter(func(i): return String(zone.get_path_to(i)).contains("SouthWall"))
	check(not wall_items.is_empty(), "just behind the south road wall a wall module carries a ghost (%d)" % wall_items.size())

	# Animation: walking behind the tree, the ghost follows the frames.
	await place(BEHIND_TREE + Vector2(-60, 0))
	var textures := {}
	await hold(["move_right"], 60, 1.0, func(_i):
		var gt := ghosts.get_ghost_for(tree)
		if gt != null:
			textures[gt.texture] = true)
	check(textures.size() >= 4, "walking behind the tree, the ghost follows the walk cycle (%d distinct frames)" % textures.size())

	# Pool and clip modes over repeated hide / show cycles.
	var pool_before := ghosts.get_pool_size()
	for i in 5:
		await place(DEAD_BAND)
		await place(FIELD)
	var clipped := 0
	for n in zone.find_children("*", "CanvasItem", true, false):
		if (n as CanvasItem).clip_children != CanvasItem.CLIP_CHILDREN_DISABLED:
			clipped += 1
	check(ghosts.get_attached_items().is_empty() and clipped == 0 and ghosts.get_pool_size() == pool_before,
		"after 5 hide / show cycles: no ghost left, no item left clipping (%d), pool stable (%d -> %d)" % [clipped, pool_before, ghosts.get_pool_size()])

	# Cost per tick with ghosts attached.
	await place(DEAD_BAND)
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
	main.change_zone("main_gate_exterior", "main_gate_entry")
	await frames(3)

	ghosts.enabled = false
	await place(DEAD_BAND)
	check(ghosts.get_attached_items().is_empty(), "with the system disabled no ghost is attached")
	ghosts.enabled = true
	await place(DEAD_BAND)
	check(ghosts.get_ghost_for(main.get_current_zone().get_node(TOWER)) != null, "re-enabled, the ghost is back")

	if OS.get_cmdline_user_args().has("--pixels"):
		await _pixels()


## Windowed only: renders the same view with ghosts on and off. The player's idle animation is frozen on one
## frame, so the only thing that can differ between the two renders is the ghost.
func _pixels() -> void:
	var anim_sprite := player.get_node("Sprite") as AnimatedSprite2D
	var control: Variant = await _halo_control_spot()
	check(control != null, "found a spot just in front of a tree / palm with nothing in front of the player (%s)" % [control])
	if control == null:
		return
	for spec in [["the old dead band behind the tower", DEAD_BAND, true], ["just in front of a tree that overlaps the player from behind", control, false]]:
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

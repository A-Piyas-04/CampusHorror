class_name LightQuery
extends RefCounted

## "Is this point lit?" for gameplay (reading notes, light-only writing, glow marks, creatures that hunt light).
## Any node in group "gameplay_lights" with `illuminates(world_pos) -> bool` counts: the player's lantern, powered
## lamps, emergency lights.

static func is_lit(tree: SceneTree, world_pos: Vector2) -> bool:
	for n in tree.get_nodes_in_group("gameplay_lights"):
		if n.has_method("illuminates") and bool(n.call("illuminates", world_pos)):
			return true
	return false


## 0..1: how strongly lit the point is (the strongest light).
static func light_level(tree: SceneTree, world_pos: Vector2) -> float:
	var best := 0.0
	for n in tree.get_nodes_in_group("gameplay_lights"):
		if n.has_method("light_level_at"):
			best = maxf(best, float(n.call("light_level_at", world_pos)))
	return best

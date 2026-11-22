extends "res://scenes/tests/feel/feel_check_base.gd"

## The whole campus as a walkable world (Docs/CAMPUS_BUILD.md S3/S12). Two passes, sandbox mode, never saves.
## Static: every registered zone's doors and walk-off edges lead to a registered zone and an existing spawn; an
##   edge's arrival spawn is clear of every edge strip in the zone it lands in (no instant bounce back); every
##   edge has a way back. Live: the real Main.tscn tours the campus through the edges (by walking the feet into
##   the strip) and the doors (the interact action), checking each arrival zone and spawn, that each edge
##   strip really has its own size (the shared-shape bug), and that the locked stairwell stays locked.

const SKIP := ["test_zone_a", "test_zone_b"]
## Arrival clearance around a spawn: the player's collision radius plus a margin (px).
const CLEAR := 24.0

## The live tour: node names looked up in the current zone, in order. "!Name" = a locked door (no travel).
const TOUR := [
	"EdgeToPlaza2",
	"DoorMosque", "DoorOut",
	"DoorAuditorium", "DoorAv", "DoorOut", "DoorOut",
	"DoorAdmin", "DoorOffice", "DoorOut", "DoorOut",
	"DoorCafe", "DoorOut",
	"EdgeToAcademic",
	"DoorAcademic1", "!DoorStairs", "DoorClassroom", "DoorOut", "DoorOut",
	"DoorAcademic2", "DoorOut",
	"EdgeToHalls",
	"DoorSouthHall", "DoorRoom", "DoorOut", "DoorOut",
	"DoorNorthHall", "DoorOut",
	"EdgeToPlaza", "EdgeToHalls", "EdgeToField",
]


func _run() -> void:
	tag = "CAMPUS"
	_static_pass()
	await _live_pass()


# --- static ---------------------------------------------------------------------------------------------------

func _static_pass() -> void:
	var reg: Dictionary = main.zone_registry.zones
	var info := {}  # zone_id -> {spawns: {id: pos}, edges: [[name, rect, dest_zone, dest_spawn]], doors: [...]}
	for zid in reg:
		if zid in SKIP:
			continue
		var packed := load(reg[zid]) as PackedScene
		if not check(packed != null, "%s: scene loads" % zid):
			continue
		var root := packed.instantiate()
		var z := {"spawns": {}, "edges": [], "doors": []}
		for n in _all(root):
			if n is SpawnMarker:
				z.spawns[(n as SpawnMarker).spawn_id] = _local_pos(n, root)
			elif n is ZoneEdge:
				var e := n as ZoneEdge
				var c := _local_pos(n, root)
				z.edges.append([e.name, Rect2(c - e.size / 2.0, e.size), e.destination_zone_id, e.destination_spawn_id])
			elif n is Door:
				var d := n as Door
				z.doors.append([d.name, _local_pos(n, root), d.destination_zone_id, d.destination_spawn_id,
					d.requires_flag != "" or d.required_item != ""])
		info[zid] = z
		root.free()

	var broken: Array[String] = []
	var bounce: Array[String] = []
	var one_way: Array[String] = []
	var n_edges := 0
	var n_doors := 0
	for zid in info:
		for e in info[zid].edges:
			n_edges += 1
			var dest: String = e[2]
			if not info.has(dest) or not info[dest].spawns.has(e[3]):
				broken.append("%s/%s -> %s:%s" % [zid, e[0], dest, e[3]])
				continue
			var arrive: Vector2 = info[dest].spawns[e[3]]
			for f in info[dest].edges:
				if (f[1] as Rect2).grow(CLEAR).has_point(arrive):
					bounce.append("%s/%s lands on %s:%s inside %s" % [zid, e[0], dest, e[3], f[0]])
			var back := false
			for f in info[dest].edges:
				back = back or f[2] == zid
			if not back:
				one_way.append("%s/%s" % [zid, e[0]])
		for d in info[zid].doors:
			n_doors += 1
			var dest: String = d[2]
			if not info.has(dest) or not info[dest].spawns.has(d[3]):
				broken.append("%s/%s -> %s:%s" % [zid, d[0], dest, d[3]])
				continue
			if d[4]:
				continue
			var back := false
			for f in info[dest].doors + info[dest].edges:
				back = back or f[2] == zid
			if not back:
				one_way.append("%s/%s" % [zid, d[0]])
	check(n_edges >= 12 and n_doors >= 30, "the campus has %d walk-off edges and %d doors" % [n_edges, n_doors])
	check(broken.is_empty(), "every edge and door leads to a registered zone and an existing spawn %s" % [broken])
	check(bounce.is_empty(), "no edge lands the player inside an edge strip (+%d px) %s" % [CLEAR, bounce])
	check(one_way.is_empty(), "every open transition has a way back %s" % [one_way])


func _all(n: Node) -> Array[Node]:
	var out: Array[Node] = [n]
	for c in n.get_children():
		out.append_array(_all(c))
	return out


## Position of `n` in `root`'s frame without a scene tree (zone roots sit at the origin when entered).
func _local_pos(n: Node, root: Node) -> Vector2:
	var t := Transform2D.IDENTITY
	var cur := n
	while cur != null and cur != root:
		if cur is Node2D:
			t = (cur as Node2D).transform * t
		cur = cur.get_parent()
	return t.origin


# --- live -----------------------------------------------------------------------------------------------------

func _live_pass() -> void:
	check(main.get_current_zone_id() == "main_gate_exterior", "the game starts on the field (%s)" % main.get_current_zone_id())
	var visited := {main.get_current_zone_id(): true}
	var sizes_ok := true
	for step in TOUR:
		var locked: bool = step.begins_with("!")
		var node_name: String = step.trim_prefix("!")
		var zone := main.get_current_zone()
		var node := zone.find_child(node_name, true, false)
		if not check(node != null, "%s: %s exists" % [zone.zone_id, node_name]):
			return
		var from := zone.zone_id
		var dest_zone := ""
		var dest_spawn := ""
		if node is ZoneEdge:
			var e := node as ZoneEdge
			var rect := (e.get_node("Shape") as CollisionShape2D).shape as RectangleShape2D
			sizes_ok = sizes_ok and rect.size.is_equal_approx(e.size)
			dest_zone = e.destination_zone_id
			dest_spawn = e.destination_spawn_id
			release_all()
			player.teleport(e.global_position)
			await frames(4)
		else:
			var d := node as Door
			dest_zone = d.destination_zone_id
			dest_spawn = d.destination_spawn_id
			await place((d.get_node("Interactable") as Node2D).global_position + Vector2(0, 6))
			await frames(3)
			await press("interact")
		await await_travel()
		if locked:
			check(main.get_current_zone_id() == from, "%s: %s is locked (still in %s)" % [from, node_name, main.get_current_zone_id()])
			continue
		var spawn := main.get_current_zone().find_spawn_marker(dest_spawn) if main.get_current_zone() != null else null
		var ok := main.get_current_zone_id() == dest_zone and spawn != null \
			and player.global_position.distance_to(spawn.global_position) < 2.0
		check(ok, "%s --%s--> %s:%s (now in %s at %s)" % [from, node_name, dest_zone, dest_spawn,
			main.get_current_zone_id(), player.global_position])
		await seconds(0.4)
		check(main.get_current_zone_id() == dest_zone and not main.is_transitioning(),
			"  ...and stays there (no bounce back through an edge)")
		visited[dest_zone] = true
	check(sizes_ok, "every edge strip has its own collision size (no shared shape)")
	check(visited.size() >= 16, "the tour visited %d zones: %s" % [visited.size(), visited.keys()])

@tool
class_name CampusMassing
extends Node2D

## A building part drawn as an extruded massing model straight from the campus layout (Map v2, D44): the real
## footprint (any polygon: wings, round stair towers, the turned Mosque) raised to its real height in the game's
## 40 degree projection. It stands in for a building until its rendered art exists, so the whole campus is walkable
## at true size from day one.
## - Origin = the southernmost point of the footprint (it Y-sorts like any prop); `footprint` is relative to it.
## - Camera-facing (south-ish) walls are shaded by the baked sun direction, with storey bands and window bays.
## - Collision and a light occluder come from the footprint (built at runtime, never saved).
## - A sun shadow falls to the north-east on the ground band; it fades out with the daylight.
## - Fades to `behind_alpha` while the player stands behind it (D31).

const H_PX := 24.513  ## screen px per metre of height (32 * cos 40 degrees)
const SUN_SHADOW := Vector2(12.85, -11.8)  ## ground shadow offset per metre of height (sun 55 deg up, from the SW)

@export var footprint := PackedVector2Array():
	set(v):
		footprint = v
		_rebuild()
@export var height_m := 10.0:
	set(v):
		height_m = maxf(v, 0.0)
		_rebuild()
## iut_brick, brick_red_roof, workshop_sawtooth, metal_canopy, residential, utility, plain_brick,
## highrise_construction, gate, monument, plot.
@export var style: StringName = &"iut_brick":
	set(v):
		style = v
		queue_redraw()
@export var status: StringName = &"built"
@export var storey_m := 3.4
@export var casts_shadow := true
@export var solid := true
@export var behind_alpha := 0.32
@export var label := ""

var _body: StaticBody2D
var _occluder: LightOccluder2D
var _shadow: Polygon2D
var _bbox := Rect2()
var _player: Node2D
var _alpha := 1.0


func _ready() -> void:
	_rebuild()
	if Engine.is_editor_hint():
		return
	var tint := get_tree().get_first_node_in_group("world_tint")
	if tint != null and tint.has_signal("phase_changed"):
		tint.connect("phase_changed", _on_phase)
		_on_phase(0, float(tint.get("darkness")))


func _rebuild() -> void:
	if not is_inside_tree() or footprint.size() < 3:
		queue_redraw()
		return
	_bbox = Rect2(footprint[0], Vector2.ZERO)
	for p in footprint:
		_bbox = _bbox.expand(p)
	var H := height_m * H_PX
	if not Engine.is_editor_hint():
		if solid and _body == null and style != &"plot":
			_body = StaticBody2D.new()
			_body.collision_mask = 0
			add_child(_body, false, Node.INTERNAL_MODE_FRONT)
			if style == &"metal_canopy":
				for c in [_bbox.position, Vector2(_bbox.end.x, _bbox.position.y), _bbox.end, Vector2(_bbox.position.x, _bbox.end.y)]:
					var post := CollisionShape2D.new()
					var circle := CircleShape2D.new()
					circle.radius = 6.0
					post.shape = circle
					post.position = c + (_bbox.get_center() - c).normalized() * 10.0
					_body.add_child(post)
			else:
				var poly := CollisionPolygon2D.new()
				poly.polygon = footprint
				_body.add_child(poly)
		if casts_shadow and _occluder == null and style not in [&"plot", &"metal_canopy"]:
			_occluder = LightOccluder2D.new()
			var op := OccluderPolygon2D.new()
			op.polygon = footprint
			_occluder.occluder = op
			_occluder.occluder_light_mask = 1
			add_child(_occluder, false, Node.INTERNAL_MODE_FRONT)
		if casts_shadow and _shadow == null and height_m > 0.5:
			_shadow = Polygon2D.new()
			_shadow.z_as_relative = false
			_shadow.z_index = -9
			_shadow.light_mask = 1
			_shadow.color = Color(0.05, 0.07, 0.12, 0.30)
			_shadow.polygon = Geometry2D.convex_hull(_shadow_points(H))
			add_child(_shadow, false, Node.INTERNAL_MODE_FRONT)
	queue_redraw()


func _shadow_points(_H: float) -> PackedVector2Array:
	var off := SUN_SHADOW * height_m
	var pts := PackedVector2Array()
	for p in footprint:
		pts.append(p)
		pts.append(p + off)
	return pts


func _on_phase(_phase: int, darkness: float) -> void:
	if _shadow != null:
		_shadow.modulate.a = clampf(1.0 - darkness * 1.4, 0.0, 1.0)


func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		return
	if _player == null or not is_instance_valid(_player):
		_player = get_tree().get_first_node_in_group("player") as Node2D
		if _player == null:
			return
	var H := height_m * H_PX
	var local := to_local(_player.global_position)
	var screen := Rect2(_bbox.position - Vector2(0, H), _bbox.size + Vector2(0, H)).grow(6.0)
	var behind := local.y < -2.0 and screen.has_point(local) and screen.has_point(local - Vector2(0, 40))
	var target := behind_alpha if behind else 1.0
	if absf(_alpha - target) > 0.002:
		_alpha = move_toward(_alpha, target, delta * 2.6)
		modulate.a = _alpha


# --- drawing ---------------------------------------------------------------------------------------------

func _colors() -> Dictionary:
	match style:
		&"brick_red_roof":
			return {"wall": Color(0.63, 0.31, 0.23), "roof": Color(0.56, 0.17, 0.14), "win": Color(0.12, 0.10, 0.10)}
		&"workshop_sawtooth":
			return {"wall": Color(0.60, 0.32, 0.25), "roof": Color(0.58, 0.58, 0.56), "win": Color(0.16, 0.17, 0.18)}
		&"metal_canopy":
			return {"wall": Color(0.35, 0.35, 0.36), "roof": Color(0.52, 0.16, 0.14), "win": Color(0, 0, 0)}
		&"residential":
			return {"wall": Color(0.84, 0.78, 0.68), "roof": Color(0.62, 0.60, 0.57), "win": Color(0.18, 0.2, 0.22)}
		&"utility":
			return {"wall": Color(0.66, 0.66, 0.63), "roof": Color(0.5, 0.5, 0.49), "win": Color(0.2, 0.2, 0.2)}
		&"highrise_construction":
			return {"wall": Color(0.70, 0.69, 0.66), "roof": Color(0.58, 0.57, 0.55), "win": Color(0.14, 0.14, 0.15)}
		&"plot":
			return {"wall": Color(0.75, 0.75, 0.72), "roof": Color(0.6, 0.48, 0.32), "win": Color(0, 0, 0)}
	return {"wall": Color(0.64, 0.31, 0.23), "roof": Color(0.57, 0.55, 0.52), "win": Color(0.11, 0.09, 0.09)}


func _draw() -> void:
	if footprint.size() < 3:
		return
	var c := _colors()
	var H := height_m * H_PX
	if style == &"plot":
		_draw_plot(c)
		return
	var pts := footprint
	# outward normals need a known winding: make it clockwise on screen (y down)
	if _signed_area(pts) < 0.0:
		pts = _reversed(pts)
	var up := Vector2(0, -H)
	var light := Vector2(-0.57, 0.82).normalized()  # sun from the front-left (south-west)
	if style == &"metal_canopy":
		_draw_canopy(pts, c, up)
		return
	var n := pts.size()
	# walls, back to front
	var walls := []
	for i in n:
		var a := pts[i]
		var b := pts[(i + 1) % n]
		var e := b - a
		var normal := Vector2(e.y, -e.x).normalized()
		if normal.y > 0.02:
			walls.append([a, b, normal])
	walls.sort_custom(func(w1, w2): return (w1[0].y + w1[1].y) < (w2[0].y + w2[1].y))
	for w in walls:
		var a: Vector2 = w[0]
		var b: Vector2 = w[1]
		var normal: Vector2 = w[2]
		var shade := 0.72 + 0.28 * clampf(normal.dot(light), -1.0, 1.0)
		var col: Color = (c.wall as Color) * Color(shade, shade, shade)
		draw_colored_polygon(PackedVector2Array([a, b, b + up, a + up]), col)
		_draw_wall_detail(a, b, H, c, shade)
		draw_line(a, b, col.darkened(0.45), 1.5)
	# roof
	var roof := PackedVector2Array()
	for p in pts:
		roof.append(p + up)
	draw_colored_polygon(roof, c.roof)
	if style == &"workshop_sawtooth":
		_draw_sawtooth(roof, c)
	var edge: Color = (c.roof as Color).darkened(0.35)
	for i in n:
		draw_line(roof[i], roof[(i + 1) % n], edge, 2.0)
	if style == &"highrise_construction":
		_draw_scaffold(walls, H)


func _draw_wall_detail(a: Vector2, b: Vector2, H: float, c: Dictionary, shade: float) -> void:
	var length_m := a.distance_to(b) / 32.0
	if length_m < 2.5 or H < 40.0:
		return
	var storeys := maxi(1, floori(height_m / storey_m))
	var floor_px := H / float(storeys)
	var band: Color = (c.wall as Color).darkened(0.18) * Color(shade, shade, shade)
	var win: Color = c.win
	var bays := maxi(1, floori(length_m / (2.2 if style == &"iut_brick" else 3.2)))
	var dir := (b - a) / float(bays)
	for s in storeys:
		var y0 := -floor_px * s
		if s > 0:
			draw_line(a + Vector2(0, y0), b + Vector2(0, y0), band, 1.2)
		if style in [&"utility", &"gate", &"monument"]:
			continue
		for k in bays:
			var base := a + dir * (k + 0.5)
			var w := minf(dir.length() * 0.45, 30.0)
			var top := y0 - floor_px * 0.78
			var bottom := y0 - floor_px * (0.22 if s > 0 or style != &"iut_brick" else 0.0)
			if style == &"iut_brick" and s == 0:
				# ground-floor arcade: tall arched openings, the IUT signature
				var r := w * 0.5
				draw_rect(Rect2(base.x - r, base.y + top + r, w, bottom - top - r), win)
				draw_circle(Vector2(base.x, base.y + top + r), r, win)
			elif style == &"workshop_sawtooth":
				if s == 0 and k % 2 == 0:
					draw_rect(Rect2(base.x - w * 0.6, base.y + y0 - floor_px * 0.85, w * 1.2, floor_px * 0.6), win)
			else:
				draw_rect(Rect2(base.x - w * 0.5, base.y + top, w, bottom - top), win)


func _draw_sawtooth(roof: PackedVector2Array, c: Dictionary) -> void:
	var r := Rect2(roof[0], Vector2.ZERO)
	for p in roof:
		r = r.expand(p)
	var step := 3.2 * 20.576
	var y := r.position.y + step
	var hi: Color = (c.roof as Color).lightened(0.18)
	var lo: Color = (c.roof as Color).darkened(0.25)
	while y < r.end.y - 4.0:
		draw_rect(Rect2(r.position.x + 4, y - step * 0.45, r.size.x - 8, step * 0.45), hi)
		draw_line(Vector2(r.position.x + 4, y), Vector2(r.end.x - 4, y), lo, 2.0)
		y += step


func _draw_canopy(pts: PackedVector2Array, c: Dictionary, up: Vector2) -> void:
	var r := Rect2(pts[0], Vector2.ZERO)
	for p in pts:
		r = r.expand(p)
	for corner in [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]:
		var p: Vector2 = corner + (r.get_center() - corner).normalized() * 10.0
		draw_line(p, p + up, c.wall, 3.0)
	var roof := PackedVector2Array()
	for p in pts:
		roof.append(p + up)
	draw_colored_polygon(roof, c.roof)
	draw_line(roof[2], roof[3], (c.roof as Color).darkened(0.4), 3.0)


func _draw_scaffold(walls: Array, H: float) -> void:
	var col := Color(0.55, 0.45, 0.28, 0.85)  # bamboo scaffolding, as on Dhaka building sites
	for w in walls:
		var a: Vector2 = w[0]
		var b: Vector2 = w[1]
		var n := maxi(2, int(a.distance_to(b) / 48.0))
		for k in n + 1:
			var p := a.lerp(b, float(k) / n)
			draw_line(p, p + Vector2(0, -H - 12), col, 1.4)
		var levels := int(H / 50.0)
		for l in levels + 1:
			var y := -50.0 * l
			draw_line(a + Vector2(0, y), b + Vector2(0, y), col, 1.2)


func _draw_plot(c: Dictionary) -> void:
	# a fenced, staked plot (D47): corrugated-sheet fence with a gate gap on the south side
	var r := _bbox
	var fence_h := 1.9 * H_PX
	var sheet := Color(0.62, 0.64, 0.62)
	var top := Vector2(0, -fence_h)
	var segs := [[r.position, Vector2(r.end.x, r.position.y)],
		[Vector2(r.end.x, r.position.y), r.end],
		[Vector2(r.position.x, r.end.y), Vector2(r.position.x, r.position.y)]]
	var gate := r.get_center().x
	segs.append([Vector2(r.position.x, r.end.y), Vector2(gate - 64, r.end.y)])
	segs.append([Vector2(gate + 64, r.end.y), r.end])
	for s in segs:
		var a: Vector2 = s[0]
		var b: Vector2 = s[1]
		var facing := absf(a.y - b.y) < 1.0
		var col := sheet if facing else sheet.darkened(0.2)
		draw_colored_polygon(PackedVector2Array([a, b, b + top, a + top]), col)
		draw_line(a + top, b + top, col.darkened(0.3), 1.5)
	# survey stakes at the footprint corners
	for p in footprint:
		draw_line(p, p + Vector2(0, -1.2 * H_PX), Color(0.9, 0.5, 0.15), 2.5)


static func _signed_area(p: PackedVector2Array) -> float:
	var s := 0.0
	for i in p.size():
		var a := p[i]
		var b := p[(i + 1) % p.size()]
		s += a.x * b.y - b.x * a.y
	return s * 0.5


static func _reversed(p: PackedVector2Array) -> PackedVector2Array:
	var out := PackedVector2Array()
	for i in range(p.size() - 1, -1, -1):
		out.append(p[i])
	return out

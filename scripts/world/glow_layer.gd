class_name GlowLayer
extends CanvasLayer

## Draws every GlowMark (group "glow_marks") on a canvas layer that follows the world camera but sits outside the
## world's night tint, so the organism's faint glow stays visible in the dark. Additive, soft, pulsing.
## A mark fades out where the world is lit (LightQuery: lantern, lamps): "light hides".

var _canvas: Node2D
var _dot: Texture2D
var _font: Font
var _t := 0.0


func _ready() -> void:
	layer = 1
	follow_viewport_enabled = true
	_canvas = Node2D.new()
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	mat.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED
	_canvas.material = mat
	add_child(_canvas)
	_canvas.draw.connect(_draw_marks)
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	g.add_point(0.35, Color(1, 1, 1, 0.55))
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 64
	tex.height = 64
	_dot = tex
	_font = ThemeDB.fallback_font


func _process(delta: float) -> void:
	_t += delta
	var tree := get_tree()
	for m: GlowMark in tree.get_nodes_in_group("glow_marks"):
		if not m.is_visible_in_tree():
			m.visibility = 0.0
			continue
		var lit := LightQuery.light_level(tree, m.global_position)
		var want := clampf(1.0 - lit * 3.5, 0.0, 1.0)
		m.visibility = move_toward(m.visibility, want, delta * 2.5)
	_canvas.queue_redraw()


func _draw_marks() -> void:
	for m: GlowMark in get_tree().get_nodes_in_group("glow_marks"):
		if m.visibility <= 0.01 and m.trail_to == Vector2.ZERO:
			continue
		var pulse := 0.75 + 0.25 * sin(_t * m.pulse_speed * TAU + float(m.seed_value() % 100))
		# Marks fade where they themselves are lit, blob by blob (a long trail vanishes only inside the light).
		var a := m.intensity * pulse
		var base := m.global_position
		var c := m.color
		for s in m.spots:
			var p := base + Vector2(s.x, s.y)
			_blob(p, s.z, Color(c, a * _dark(p, m.visibility)))
		if m.trail_to != Vector2.ZERO:
			var n := maxi(1, int(m.trail_to.length() / m.trail_spacing))
			for i in n + 1:
				var f := float(i) / n
				var wob := Vector2(sin(f * 17.0 + m.seed_value()) * 4.0, cos(f * 13.0) * 3.0)
				var p := base + m.trail_to * f + wob
				_blob(p, 5.0 + 2.0 * sin(f * 9.0), Color(c, a * (0.6 + 0.4 * sin(f * 5.0)) * _dark(p, 1.0)))
		if not m.writing.is_empty():
			_letters(m, base + m.writing_offset, Color(c, a * m.visibility))


## 0 where the point is lit, 1 in darkness (capped by `limit`, the mark's eased visibility for its own spots).
func _dark(p: Vector2, limit: float) -> float:
	return minf(clampf(1.0 - LightQuery.light_level(get_tree(), p) * 3.5, 0.0, 1.0), limit if limit > 0.0 else 1.0)


func _blob(p: Vector2, r: float, col: Color) -> void:
	_canvas.draw_texture_rect(_dot, Rect2(p - Vector2(r, r) * 1.6, Vector2(r, r) * 3.2), false, Color(col, col.a * 0.55))
	_canvas.draw_texture_rect(_dot, Rect2(p - Vector2(r, r), Vector2(r, r) * 2.0), false, col)


## Letters scrawled in growth: each one slightly tilted and offset, with a soft halo.
func _letters(m: GlowMark, base: Vector2, col: Color) -> void:
	var size := m.writing_size
	var w := _font.get_string_size(m.writing, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var x := -w * 0.5
	var rng := RandomNumberGenerator.new()
	rng.seed = m.seed_value()
	for i in m.writing.length():
		var ch := m.writing[i]
		var cw := _font.get_string_size(ch, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
		var p := base + Vector2(x, rng.randf_range(-3.0, 3.0))
		var rot := rng.randf_range(-0.18, 0.18)
		_canvas.draw_set_transform(p, rot, Vector2(1.0, rng.randf_range(0.9, 1.15)))
		for o in [Vector2(-1.5, 0), Vector2(1.5, 0), Vector2(0, -1.5), Vector2(0, 1.5)]:
			_canvas.draw_string(_font, o, ch, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(col, col.a * 0.3))
		_canvas.draw_string(_font, Vector2.ZERO, ch, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)
		x += cw * 1.12
	_canvas.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

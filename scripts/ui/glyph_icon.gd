class_name GlyphIcon
extends Control

## Draws one input glyph (InputGlyphs.glyph()) plus an optional hold-progress ring (roadmap I7). Vector-drawn:
## a keycap for keys, a coloured face button for gamepads (PlayStation shapes drawn as lines), so there are no
## textures or font glyphs to go missing.

var glyph: Dictionary = {"kind": "key", "text": "E"}:
	set(value):
		glyph = value
		queue_redraw()
## 0..1 fill of the hold ring (0 = hidden).
var progress: float = 0.0:
	set(value):
		progress = clampf(value, 0.0, 1.0)
		queue_redraw()
var font_size := 22


func _ready() -> void:
	custom_minimum_size = Vector2(40, 40)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _draw() -> void:
	var c := size * 0.5
	var font := ThemeDB.fallback_font
	if glyph.get("kind") == "pad":
		var r := minf(size.x, size.y) * 0.42
		var col: Color = glyph.get("color", Color.WHITE)
		var shape: String = glyph.get("shape", "")
		var text: String = glyph.get("text", "")
		if shape != "" or text.length() <= 1:
			draw_circle(c, r, Color(0.08, 0.08, 0.09, 0.95))
			draw_arc(c, r, 0.0, TAU, 40, col, 2.0, true)
		else:
			_rounded(Rect2(c - Vector2(r * 1.3, r * 0.75), Vector2(r * 2.6, r * 1.5)), Color(0.08, 0.08, 0.09, 0.95), col)
		var s := r * 0.48
		match shape:
			"cross":
				draw_line(c - Vector2(s, s), c + Vector2(s, s), col, 2.5, true)
				draw_line(c + Vector2(-s, s), c + Vector2(s, -s), col, 2.5, true)
			"circle":
				draw_arc(c, s, 0.0, TAU, 32, col, 2.5, true)
			"square":
				draw_rect(Rect2(c - Vector2(s, s), Vector2(s, s) * 2.0), col, false, 2.5)
			"triangle":
				draw_polyline(PackedVector2Array([c + Vector2(0, -s * 1.1), c + Vector2(s * 1.05, s * 0.75), c + Vector2(-s * 1.05, s * 0.75), c + Vector2(0, -s * 1.1)]), col, 2.5, true)
			_:
				_text(font, c, text, col, font_size if text.length() <= 1 else font_size - 6)
	else:
		var w := maxf(size.y * 0.8, font.get_string_size(String(glyph.get("text", "?")), HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x + 14.0)
		var rect := Rect2(c - Vector2(w, size.y * 0.8) * 0.5, Vector2(w, size.y * 0.8))
		_rounded(rect, Color(0.08, 0.08, 0.09, 0.95), Color(0.95, 0.94, 0.9))
		_text(font, c, String(glyph.get("text", "?")), Color(0.97, 0.96, 0.93), font_size)
	if progress > 0.0:
		var rr := minf(size.x, size.y) * 0.5 + 3.0
		draw_arc(c, rr, -PI / 2.0, -PI / 2.0 + TAU * progress, 48, Color(1.0, 0.86, 0.55), 3.0, true)


func _rounded(rect: Rect2, fill: Color, border: Color) -> void:
	var sb := StyleBoxFlat.new()
	sb.bg_color = fill
	sb.border_color = border
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(6)
	sb.anti_aliasing = true
	draw_style_box(sb, rect)


func _text(font: Font, centre: Vector2, text: String, col: Color, fsize: int) -> void:
	var ts := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fsize)
	draw_string(font, centre + Vector2(-ts.x * 0.5, font.get_ascent(fsize) * 0.5 - 2.0), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fsize, col)

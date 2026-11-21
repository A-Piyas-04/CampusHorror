class_name UIStyle
extends RefCounted

## One quiet, consistent look for every screen (menus, notes, HUD): dark translucent panels, off-white text, a
## warm amber accent, serif titles. No font files are shipped: titles use the system's serif (Georgia / Times New
## Roman on Windows), with Godot's default font as the fallback, so text never goes missing.

const TEXT := Color(0.94, 0.92, 0.87)
const TEXT_DIM := Color(0.68, 0.66, 0.62)
const ACCENT := Color(1.0, 0.8, 0.5)
const PANEL := Color(0.035, 0.035, 0.045, 0.86)
const PAPER := Color(0.86, 0.83, 0.74)
const INK := Color(0.16, 0.14, 0.12)

static var _serif: Font


static func serif() -> Font:
	if _serif == null:
		var f := SystemFont.new()
		f.font_names = PackedStringArray(["Georgia", "Times New Roman", "Liberation Serif", "DejaVu Serif", "serif"])
		f.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
		_serif = f
	return _serif


static func panel_style(color: Color = PANEL, radius: int = 8, margin: int = 18) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(radius)
	sb.set_content_margin_all(margin)
	sb.anti_aliasing = true
	return sb


static func label(text: String, size: int = 20, color: Color = TEXT, title: bool = false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	if title:
		l.add_theme_font_override("font", serif())
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## A flat text button: dim at rest, bright with an amber marker on hover / focus (keyboard and gamepad navigable).
static func button(text: String, size: int = 24) -> Button:
	var b := Button.new()
	b.text = text
	b.flat = true
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.focus_mode = Control.FOCUS_ALL
	b.add_theme_font_override("font", serif())
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_color_override("font_color", TEXT_DIM)
	b.add_theme_color_override("font_hover_color", TEXT)
	b.add_theme_color_override("font_focus_color", ACCENT)
	b.add_theme_color_override("font_pressed_color", ACCENT)
	var empty := StyleBoxEmpty.new()
	empty.content_margin_left = 22
	for state in ["normal", "hover", "pressed", "focus", "disabled"]:
		b.add_theme_stylebox_override(state, empty)
	b.focus_entered.connect(func(): b.text = "›  " + text)
	b.focus_exited.connect(func(): b.text = text)
	b.mouse_entered.connect(func(): b.grab_focus())
	return b


## Full-screen black ColorRect (for dimming behind menus).
static func dim(alpha: float = 0.6) -> ColorRect:
	var r := ColorRect.new()
	r.color = Color(0, 0, 0, alpha)
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.mouse_filter = Control.MOUSE_FILTER_STOP
	return r

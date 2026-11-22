shader_type canvas_item;
render_mode unshaded, blend_premul_alpha;

// Map v2 lit windows (D46): a building's `_night.png` drawn over its layer sprite, unshaded so the night tint
// (CanvasModulate) doesn't darken it, faded in by the time of day through the global `night_level`. A slow
// per-window flicker keeps the rooms alive; the building's own fade (walking behind it) applies through COLOR.

global uniform float night_level;

void fragment() {
	vec4 tex = texture(TEXTURE, UV);
	float flick = 0.94 + 0.06 * sin(TIME * 0.7 + floor(UV.x * 40.0) * 1.7 + floor(UV.y * 30.0) * 2.3);
	float a = tex.a * night_level * COLOR.a;
	COLOR = vec4(tex.rgb * a * flick, a);
}

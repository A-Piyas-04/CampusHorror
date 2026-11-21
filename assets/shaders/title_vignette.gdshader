shader_type canvas_item;

// Title screen veil: a heavy vignette, a cold tint, film grain and a darker band on the left behind the menu.
uniform float strength = 1.25;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec2 uv = SCREEN_UV;
	float d = distance(uv, vec2(0.55, 0.5));
	float v = smoothstep(0.25, 0.85, d) * strength;
	float left = smoothstep(0.55, 0.0, uv.x) * 0.55;
	float grain = (hash(uv * 900.0 + TIME * 13.0) - 0.5) * 0.06;
	COLOR = vec4(0.0, 0.01, 0.03, clamp(v * 0.85 + left, 0.0, 0.95) + grain);
}

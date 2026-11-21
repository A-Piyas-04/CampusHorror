shader_type canvas_item;

// Composure overlay (scripts/player/composure.gd): the frame closes in as fear rises.
// tension 0..1 drives the vignette, grain and the edge pulse (beat, the heartbeat); desat drains the colour.
uniform float tension : hint_range(0.0, 1.0) = 0.0;
uniform float desat : hint_range(0.0, 1.0) = 0.0;
uniform float beat : hint_range(0.0, 1.0) = 0.0;
uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec2 uv = SCREEN_UV;
	vec3 col = texture(screen_tex, uv).rgb;
	float grey = dot(col, vec3(0.299, 0.587, 0.114));
	col = mix(col, vec3(grey) * vec3(0.92, 0.97, 1.05), desat);
	vec2 d = (uv - 0.5) * vec2(1.6, 1.0);
	float r = length(d);
	float inner = mix(0.95, 0.38, tension) - beat * 0.05 * tension;
	float v = smoothstep(inner, inner + 0.55, r);
	col *= 1.0 - v * (0.55 + 0.4 * tension);
	col = mix(col, col * vec3(1.15, 0.85, 0.85), v * beat * 0.35 * tension);
	float g = (hash(uv * 800.0 + TIME * 17.0) - 0.5) * 0.08 * tension;
	COLOR = vec4(col + g, 1.0);
}

shader_type canvas_item;

// Lake water for the Central Plaza moat (Polygon2D). Dark green-teal, slow drifting ripples, soft glints that
// catch the 2D lights (lamps, the lantern), darker towards the banks via a vertex-colour or `edge` mask.
// World-space so neighbouring polygons line up; lit like any canvas item, so night makes it near-black.

uniform vec4 deep : source_color = vec4(0.10, 0.17, 0.15, 1.0);
uniform vec4 shallow : source_color = vec4(0.18, 0.27, 0.22, 1.0);
uniform vec4 glint : source_color = vec4(0.75, 0.82, 0.78, 1.0);
uniform float scale = 0.012;
uniform float speed = 0.05;

varying vec2 world;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
}

void fragment() {
	vec2 p = world * scale;
	float t = TIME * speed;
	float n = noise(p * 3.0 + vec2(t, t * 0.6)) * 0.6 + noise(p * 7.0 - vec2(t * 1.3, t * 0.4)) * 0.4;
	vec3 col = mix(deep.rgb, shallow.rgb, n * 0.7);
	// Thin ripple lines (stretched across, as the camera looks across the water).
	float r = noise(vec2(p.x * 9.0, p.y * 26.0) + vec2(t * 2.0, 0.0));
	float line = smoothstep(0.78, 0.86, r) * (1.0 - smoothstep(0.86, 0.95, r));
	col = mix(col, glint.rgb, line * 0.14);
	COLOR = vec4(col * COLOR.rgb, 1.0);
}

shader_type canvas_item;

// Map v2 road paint (D46): lane lines, edge lines, zebra crossings and speed-breaker stripes, drawn as antialiased
// Polygon2Ds over the ground (tools/zones/campus_world.py). Thermoplastic paint wears: chipped away in patches,
// thinned where the tyres run, a little grime, so no line is a clean vector stripe. Lit like the ground (lamps and
// the lantern find it at night); the colour comes from the polygon's `color`.

uniform sampler2D noise_tex : filter_linear_mipmap, repeat_enable;
uniform float wear : hint_range(0.0, 1.0) = 0.32;
uniform vec2 world_px_per_m = vec2(32.0, 20.576);

varying vec2 world_m;

void vertex() {
	world_m = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy / world_px_per_m;
}

void fragment() {
	float big = texture(noise_tex, world_m / 3.1).r;
	float fine = texture(noise_tex, world_m / 0.41).g;
	float chips = big * 0.55 + fine * 0.45;
	float keep = smoothstep(wear - 0.06, wear + 0.06, chips);
	float grime = texture(noise_tex, world_m / 1.3).b;
	vec3 c = COLOR.rgb * mix(0.72, 1.0, grime);
	COLOR = vec4(c, COLOR.a * keep);
}

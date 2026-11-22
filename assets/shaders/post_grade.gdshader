shader_type canvas_item;

// Map v2 post-processing (D46), a full-screen ColorRect on its own CanvasLayer (scripts/world/post_fx.gd):
// colour grade per time of day (lift / gamma / gain, saturation, temperature), a soft bloom from the brightest
// pixels (lamps, glints, lit windows), a gentle vignette and fine animated film grain. Cheap: 13 screen taps.

uniform sampler2D screen_tex : hint_screen_texture, filter_linear, repeat_disable;
uniform vec3 lift = vec3(0.0);
uniform vec3 gamma = vec3(1.0);
uniform vec3 gain = vec3(1.0);
uniform float saturation = 1.0;
uniform float contrast = 1.0;
uniform float bloom_strength = 0.18;
uniform float bloom_threshold = 0.72;
uniform float bloom_radius_px = 9.0;
uniform float vignette = 0.28;
uniform float grain = 0.035;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec2 px = SCREEN_PIXEL_SIZE;
	vec3 col = texture(screen_tex, SCREEN_UV).rgb;

	// bloom: the bright parts of a small disc of taps around the pixel
	vec3 glow = vec3(0.0);
	float tot = 0.0;
	for (int i = 0; i < 12; i++) {
		float a = float(i) * 0.5235988;
		float r = bloom_radius_px * (i % 2 == 0 ? 1.0 : 0.55);
		vec3 s = texture(screen_tex, SCREEN_UV + vec2(cos(a), sin(a)) * r * px).rgb;
		float l = dot(s, vec3(0.2126, 0.7152, 0.0722));
		glow += s * smoothstep(bloom_threshold, 1.0, l);
		tot += 1.0;
	}
	col += glow / tot * bloom_strength * 2.0;

	// grade
	col = pow(max(col * gain + lift * (1.0 - col), vec3(0.0)), 1.0 / max(gamma, vec3(0.01)));
	col = (col - 0.5) * contrast + 0.5;
	float lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
	col = mix(vec3(lum), col, saturation);

	// vignette and grain
	vec2 d = SCREEN_UV - 0.5;
	col *= 1.0 - vignette * smoothstep(0.25, 0.85, length(d * vec2(1.15, 1.0)));
	col += (hash(SCREEN_UV * 1000.0 + fract(TIME * 7.3)) - 0.5) * grain;
	COLOR = vec4(clamp(col, 0.0, 1.0), 1.0);
}

shader_type canvas_item;

// Map v2 water (D46): the lakes round the Mosque and the boundary canal.
// - The water surface sits below the land (0.6 m in the lakes, 0.9 m in the canal). Where the shore is just NORTH
//   of a water pixel, the masonry bank face looks at the camera and fills a band as tall as the bank projects
//   (brick with a concrete coping lip, a wet dark band and algae at the waterline, a thin foam line). Where the shore
//   is south the face looks away and the land's coping (ground_splat.gdshader) covers the edge.
// - Depth tint from the shore distance (campus_water.png, tools/zones/ground_mask.py), drifting ripples, sky
//   streaks across the view, sun glints, a contact shadow under every wall, a ripple normal map for lamps at night.
// Every value is in metres of ground (a metre is 32 px across, 20.576 px deep), so it lines up with the sprites.

uniform sampler2D water_tex : filter_linear, repeat_disable;
uniform sampler2D brick_tex : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D noise_tex : filter_linear_mipmap, repeat_enable;
uniform vec2 mask_origin_m = vec2(0.0);
uniform float mask_px_per_m = 8.0;
uniform vec2 mask_size_px = vec2(4096.0, 2048.0);
uniform vec2 world_px_per_m = vec2(32.0, 20.576);

uniform vec3 deep = vec3(0.07, 0.15, 0.12);
uniform vec3 shallow = vec3(0.16, 0.26, 0.20);
uniform vec3 sky = vec3(0.58, 0.68, 0.76);
uniform float daylight : hint_range(0.0, 1.0) = 1.0;
uniform float lake_bank_m = 0.6;
uniform float canal_bank_m = 0.9;

varying vec2 world_m;

void vertex() {
	world_m = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy / world_px_per_m;
}

void fragment() {
	vec2 muv = (world_m - mask_origin_m) * mask_px_per_m / mask_size_px;
	vec4 w = texture(water_tex, muv);
	float sd = (w.r - 0.5) * 8.0;          // metres into the water
	float dn = w.g * 2.0;                   // metres north to the shore
	float canal = step(0.5, w.a);
	float bank = mix(lake_bank_m, canal_bank_m, canal);
	float face_len = bank * 24.513 / 20.576;   // the bank's projected height, in metres of ground

	float t = TIME;
	vec2 p = world_m + vec2(0.0, -face_len);   // the surface itself sits lower: sample it shifted
	float n1 = texture(noise_tex, p / 9.0 + vec2(t * 0.010, t * 0.006)).b;
	float n2 = texture(noise_tex, p / 3.3 - vec2(t * 0.018, -t * 0.010)).g;
	float depth = smoothstep(0.0, 7.0, sd);
	vec3 col = mix(shallow, deep, depth) * (0.9 + 0.2 * n1);
	col = mix(col, col * vec3(0.9, 1.08, 0.95), canal * 0.5);   // the canal runs greener and murkier
	float streak = texture(noise_tex, vec2(p.x / 11.0 + t * 0.008, p.y / 1.4 + t * 0.025)).r;
	col = mix(col, sky * 0.6, (smoothstep(0.5, 0.85, streak) * 0.2 + 0.07) * daylight);
	// sun glitter: soft, stretched across the view, gathered in drifting patches (not a starfield)
	float patch = smoothstep(0.5, 0.8, texture(noise_tex, p / 26.0 + vec2(t * 0.004, -t * 0.002)).b);
	float g = texture(noise_tex, vec2(p.x / 1.7 - t * 0.035, p.y / 0.45 + t * 0.01)).r;
	col += vec3(1.0, 0.96, 0.86) * smoothstep(0.8, 0.93, g) * patch * 0.2 * daylight;
	// broad slow swell: the surface tilts a little towards and away from the sky
	col *= 0.93 + 0.12 * texture(noise_tex, p / 14.0 + vec2(-t * 0.006, t * 0.009)).g;
	col *= mix(0.6, 1.0, smoothstep(0.0, 1.4, sd));          // the walls shade the water beside them

	vec3 nrm = normalize(vec3((n2 - 0.5) * 0.6, (n1 - 0.5) * 0.6, 1.0));
	if (dn < face_len) {
		float v = dn / face_len;                              // 0 under the coping, 1 at the waterline
		vec2 buv = vec2(world_m.x, (1.0 - v) * bank);
		vec3 b = texture(brick_tex, buv).rgb;
		b = mix(b, vec3(dot(b, vec3(0.33))) * vec3(0.95, 0.95, 0.9), canal * 0.75);   // canal walls: rendered
		b *= mix(1.0, 0.5, smoothstep(0.55, 1.0, v));             // wet dark band
		b = mix(b, b * vec3(0.62, 0.8, 0.52), smoothstep(0.7, 1.0, v) * 0.7);   // algae at the waterline
		float lip = 1.0 - smoothstep(0.0, 0.14, v);
		b = mix(b, vec3(0.74, 0.72, 0.67), lip);                // concrete coping lip
		b *= 0.94;
		float foam = smoothstep(0.93, 0.99, v) * (0.5 + 0.5 * sin(world_m.x * 3.1 + t * 1.5));
		col = mix(b, vec3(0.8, 0.86, 0.84), foam * 0.35);
		nrm = vec3(0.0, 0.45, 0.89);                             // the face leans towards the camera
	}
	COLOR = vec4(col, 1.0);
	NORMAL_MAP = nrm * 0.5 + 0.5;
}

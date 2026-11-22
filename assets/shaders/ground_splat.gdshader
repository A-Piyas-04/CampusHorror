shader_type canvas_item;

// Map v2 ground (decision D46): the whole campus floor in one quad.
// - 8 photo materials (CC0, assets/source/textures) in two texture arrays, weighted by baked splat masks
//   (tools/zones/ground_mask.py) and mapped in METRES of ground, so the 40 degree foreshortening is automatic
//   (a metre is 32 px across and 20.576 px deep on screen, exactly like the sprites).
// - Organic layers (grass, leaves, earth, asphalt, concrete) use hex-tile stochastic sampling: no visible repeat.
//   Patterned layers (herringbone, brick road) tile regularly so their courses stay straight.
// - Height blending: grass blades and grit poke into neighbouring layers instead of a cross-fade.
// - Kerbs and brick edging where paving meets anything soft, derived from the masks themselves.
// - Baked sun shadow (falls NE like every sprite's), contact AO, a damp rim along the water, wear and dry patches,
//   drifting cloud shadows by day.
// - A blended normal map so lamps and the lantern rake across pavers and grass at night.

uniform sampler2DArray albedo_array : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray normal_array : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D splat_a : filter_linear, repeat_disable;
uniform sampler2D splat_b : filter_linear, repeat_disable;
uniform sampler2D shade_tex : filter_linear, repeat_disable;
uniform sampler2D noise_tex : filter_linear_mipmap, repeat_enable;
uniform sampler2D water_tex : filter_linear, repeat_disable;   // campus_water.png: signed distance to the shore
uniform sampler2D kerb_tex : filter_linear, repeat_disable;    // campus_kerb.png: signed distance to paving edges
uniform float water_px_per_m = 8.0;
uniform vec2 water_size_px = vec2(4096.0, 2048.0);

uniform vec2 mask_origin_m = vec2(0.0);
uniform float mask_px_per_m = 4.0;
uniform vec2 mask_size_px = vec2(2048.0, 1024.0);
uniform vec2 world_px_per_m = vec2(32.0, 20.576);

// per layer: tile size (m), colour grade, stochastic tiling (1) or regular (0), height contrast
uniform float tile_m[8];
uniform vec3 tint[8];
uniform float saturation[8];
uniform float stochastic[8];
uniform float height_gain[8];
uniform vec3 target[8];       // each layer's graded average colour (scripts/world/ground_splat.gd)
uniform float contrast[8];    // photo detail kept around that average (concrete and asphalt photos are too busy)
// IUT paving is laid brick (240 x 115 mm, the Bangladeshi standard): herringbone on the mosque plaza, 45 degree
// herringbone bond (the LGED "HBB" road) on the brick roads and paths. Concrete paths are cast in 1.2 m slabs.
uniform float brick_w = 0.118;
uniform float slab_m = 1.2;

uniform float daylight : hint_range(0.0, 1.0) = 1.0;    // sun shadows and clouds fade with the light
uniform vec2 cloud_offset = vec2(0.0);                   // metres; drifted by scripts/world/ground_splat.gd
uniform float cloud_strength : hint_range(0.0, 1.0) = 0.16;
uniform float blend_depth = 0.18;                         // height-blend softness
uniform vec3 shadow_tint = vec3(0.56, 0.62, 0.78);
// the mosque plaza's painted prayer-row grid (photo 02): white lines parallel to the Mosque's qibla wall
uniform vec4 plaza_rect = vec4(0.0);          // x0, y0, x1, y1 in metres; zero = none
uniform float plaza_grid_m = 4.8;
uniform float plaza_grid_deg = 10.5;

varying vec2 world_m;

void vertex() {
	world_m = VERTEX / world_px_per_m;
}

vec2 hash2(vec2 p) {
	vec2 r = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
	return fract(sin(r) * 43758.5453);
}

// Mikkelsen's triangle grid (Practical Real-Time Hex-Tiling, 2022), GLSL form.
void tri_grid(vec2 uv, out vec3 w, out vec2 v1, out vec2 v2, out vec2 v3) {
	uv *= 3.4641016;
	vec2 skew = vec2(uv.x - 0.57735027 * uv.y, 1.15470054 * uv.y);
	vec2 base = floor(skew);
	vec3 t = vec3(fract(skew), 0.0);
	t.z = 1.0 - t.x - t.y;
	float s = step(0.0, -t.z);
	float s2 = 2.0 * s - 1.0;
	w = vec3(-t.z * s2, s - t.y * s2, s - t.x * s2);
	v1 = base + vec2(s, s);
	v2 = base + vec2(s, 1.0 - s);
	v3 = base + vec2(1.0 - s, s);
}

mat2 rot2(float a) {
	float c = cos(a);
	float s = sin(a);
	return mat2(vec2(c, s), vec2(-s, c));
}

void sample_layer(int i, vec2 uv, vec2 dx, vec2 dy, out vec3 albedo, out vec3 nrm) {
	float layer = float(i);
	if (stochastic[i] < 0.5) {
		albedo = textureGrad(albedo_array, vec3(uv, layer), dx, dy).rgb;
		nrm = textureGrad(normal_array, vec3(uv, layer), dx, dy).rgb * 2.0 - 1.0;
		return;
	}
	vec3 w;
	vec2 v1;
	vec2 v2;
	vec2 v3;
	tri_grid(uv, w, v1, v2, v3);
	vec3 a = vec3(0.0);
	vec3 n = vec3(0.0);
	vec2 vs[3] = vec2[3](v1, v2, v3);
	float ws[3] = float[3](w.x, w.y, w.z);
	float tot = 0.0;
	for (int k = 0; k < 3; k++) {
		vec2 h = hash2(vs[k]);
		mat2 r = rot2(h.x * 6.2831853);
		vec2 suv = r * uv + h * 7.0;
		vec3 sa = textureGrad(albedo_array, vec3(suv, layer), r * dx, r * dy).rgb;
		vec3 sn = textureGrad(normal_array, vec3(suv, layer), r * dx, r * dy).rgb * 2.0 - 1.0;
		sn.xy = transpose(r) * sn.xy;
		// contrast-preserving weights: favour the sample that stands out (Mikkelsen's luminance gain)
		float lw = pow(ws[k], 6.0) * (0.6 + dot(sa, vec3(0.3333)));
		a += sa * lw;
		n += sn * lw;
		tot += lw;
	}
	albedo = a / max(tot, 1e-5);
	nrm = n / max(tot, 1e-5);
}

float h1(vec2 p) {
	return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453);
}

// Herringbone in brick-width units (bricks 2 x 1): cells on diagonal bands (x - y) mod 4 pair up, 0-1 sideways,
// 3-2 upright. Returns the position inside the brick, its size and an id for the brick.
void herring(vec2 p, out vec2 loc, out vec2 sz, out vec2 bid) {
	vec2 c = floor(p);
	float d = mod(c.x - c.y, 4.0);
	vec2 o = c;
	sz = vec2(2.0, 1.0);
	if (d >= 0.5 && d < 1.5) {
		o = c - vec2(1.0, 0.0);
	} else if (d >= 1.5 && d < 2.5) {
		o = c - vec2(0.0, 1.0);
		sz = vec2(1.0, 2.0);
	} else if (d >= 2.5) {
		sz = vec2(1.0, 2.0);
	}
	loc = p - o;
	bid = o;
}

// Laid brick: per-brick colour (a few over-burnt and pale ones), the photo kept only as grain, sand or dirt in the
// joints, a bevel that darkens and tilts each brick's edge (so lamps and the lantern catch it), a little uneven
// laying. Fades to its average where a brick gets smaller than a pixel or two.
void pavers(int i, vec2 wm, vec2 dpx, vec2 dpy, inout vec3 a, inout vec3 n) {
	mat2 R = rot2(i == 4 ? 0.7853982 : radians(plaza_grid_deg));
	vec2 p = (R * wm) / brick_w;
	vec2 fw = (abs(R * dpx) + abs(R * dpy)) / brick_w;
	float fwm = max(fw.x, fw.y);
	vec2 loc;
	vec2 sz;
	vec2 bid;
	herring(p, loc, sz, bid);
	vec2 e2 = min(loc, sz - loc);
	float e = min(e2.x, e2.y);
	float jw = 0.085;
	float joint = 1.0 - smoothstep(jw - fwm * 0.5, jw + fwm * 0.5, e);
	float bev = smoothstep(jw, jw + 0.24, e);
	float r = h1(bid);
	float r2 = h1(bid + 17.31);
	float g = clamp(dot(a, vec3(0.3333)) / max(dot(target[i], vec3(0.3333)), 1e-3), 0.6, 1.5);
	vec3 base = target[i] * (0.82 + 0.3 * r);
	if (r2 < 0.07) {
		base *= vec3(0.70, 0.62, 0.64);           // over-burnt, purple-brown
	} else if (r2 > 0.955) {
		base *= vec3(1.14, 1.08, 0.90);           // under-fired, pale
	}
	vec3 brick = base * mix(1.0, g, 0.4) * mix(0.78, 1.0, bev);
	vec3 mortar = i == 4 ? vec3(0.27, 0.24, 0.19) : vec3(0.50, 0.47, 0.41);
	vec3 col = mix(brick, mortar * mix(1.0, g, 0.3), joint);
	float far = smoothstep(0.6, 1.2, fwm);
	a = mix(col, target[i] * mix(1.0, g, 0.3) * 0.93, far);
	vec2 ed = vec2(0.0);
	if (e2.x < e2.y) {
		ed.x = loc.x < sz.x - loc.x ? -1.0 : 1.0;
	} else {
		ed.y = loc.y < sz.y - loc.y ? -1.0 : 1.0;
	}
	mat2 Ri = transpose(R);
	vec2 tilt = Ri * ((vec2(r, r2) - 0.5) * 0.14);
	vec3 pn = normalize(vec3(Ri * ed * (1.0 - bev) * (1.0 - joint) * 0.75 + tilt, 1.0));
	n = normalize(mix(normalize(n * vec3(0.35, 0.35, 1.0)), pn, 0.85 * (1.0 - far)));
}

// Cast concrete in slabs: thin dark joints, dirt gathered along them, each slab a slightly different pour.
void slabs(vec2 wm, vec2 dpx, vec2 dpy, inout vec3 a, inout vec3 n) {
	vec2 p = wm / slab_m;
	vec2 c = floor(p);
	vec2 f = fract(p);
	vec2 fw = (abs(dpx) + abs(dpy)) / slab_m;
	vec2 e2 = min(f, 1.0 - f);
	float jx = 0.009 / slab_m;
	float jl = max(1.0 - smoothstep(jx, jx + fw.x, e2.x), 1.0 - smoothstep(jx, jx + fw.y, e2.y));
	float r = h1(c);
	vec3 col = a * (0.93 + 0.12 * r);
	col *= mix(0.88, 1.0, smoothstep(0.0, 0.05, min(e2.x, e2.y)));
	a = mix(col, col * 0.5, jl);
	vec2 ed = vec2(0.0);
	if (e2.x < e2.y) {
		ed.x = f.x < 0.5 ? -1.0 : 1.0;
	} else {
		ed.y = f.y < 0.5 ? -1.0 : 1.0;
	}
	float edge = 1.0 - smoothstep(0.0, 0.025, min(e2.x, e2.y));
	n = normalize(n + vec3(ed * edge * 0.5, 0.0));
}

void fragment() {
	vec2 dpx = dFdx(world_m);
	vec2 dpy = dFdy(world_m);
	vec2 muv = (world_m - mask_origin_m) * mask_px_per_m / mask_size_px;
	vec4 wa = texture(splat_a, muv);
	vec4 wb = texture(splat_b, muv);
	vec4 sh = texture(shade_tex, muv);
	float w[8] = float[8](wa.r, wa.g, wa.b, wa.a, wb.r, wb.g, wb.b, wb.a);

	vec3 cols[8];
	vec3 nrms[8];
	float hts[8];
	float best = -10.0;
	for (int i = 0; i < 8; i++) {
		cols[i] = vec3(0.0);
		nrms[i] = vec3(0.0, 0.0, 1.0);
		hts[i] = -10.0;
		if (w[i] < 0.003) {
			continue;
		}
		vec2 uv = world_m / tile_m[i];
		vec3 a;
		vec3 n;
		sample_layer(i, uv, dpx / tile_m[i], dpy / tile_m[i], a, n);
		float lum = dot(a, vec3(0.2126, 0.7152, 0.0722));
		a = mix(vec3(lum), a, saturation[i]) * tint[i];
		a = mix(target[i], a, contrast[i]);
		if (i == 3 || i == 4) {
			pavers(i, world_m, dpx, dpy, a, n);
		} else if (i == 6) {
			slabs(world_m, dpx, dpy, a, n);
		}
		lum = dot(a, vec3(0.2126, 0.7152, 0.0722)) / max(dot(target[i], vec3(0.2126, 0.7152, 0.0722)), 1e-3) * 0.4;
		cols[i] = a;
		nrms[i] = n;
		hts[i] = w[i] + lum * height_gain[i];
		best = max(best, hts[i]);
	}
	vec3 col = vec3(0.0);
	vec3 nrm = vec3(0.0);
	float tot = 0.0;
	for (int i = 0; i < 8; i++) {
		float b = max(hts[i] - best + blend_depth, 0.0);
		col += cols[i] * b;
		nrm += nrms[i] * b;
		tot += b;
	}
	col /= max(tot, 1e-5);
	nrm = normalize(nrm / max(tot, 1e-5) + vec3(0.0, 0.0, 0.0001));

	// macro variation: large soft brightness and hue drift, dry patches in the grass
	float n1 = texture(noise_tex, world_m / 41.0).b;
	float n2 = texture(noise_tex, world_m / 9.7).g;
	float grassy = w[0] + w[1] + w[2];
	col *= 0.9 + 0.2 * mix(n1, n2, 0.35);
	float dry = smoothstep(0.55, 0.85, sh.a) * grassy;
	col = mix(col, col * vec3(1.16, 1.02, 0.66), dry * 0.55);

	// prayer-row grid on the mosque plaza's pavers
	vec2 q = rot2(radians(plaza_grid_deg)) * (world_m - plaza_rect.xy) / plaza_grid_m;
	vec2 aa = fwidth(q) * 1.2;
	if (plaza_rect.z > plaza_rect.x && world_m.x > plaza_rect.x && world_m.x < plaza_rect.z
			&& world_m.y > plaza_rect.y && world_m.y < plaza_rect.w) {
		vec2 f = abs(fract(q) - 0.5);
		float line_w = 0.06 / plaza_grid_m;
		float line = max(1.0 - smoothstep(0.5 - line_w - aa.x, 0.5 - line_w + aa.x, f.x),
			1.0 - smoothstep(0.5 - line_w - aa.y, 0.5 - line_w + aa.y, f.y));
		line = 1.0 - line;  // 1 on the lines
		col = mix(col, vec3(0.86, 0.84, 0.80), line * smoothstep(0.85, 1.0, w[3]) * 0.75);
	}

	// kerbs as stones, not lines (baked edge field, tools/zones/ground_mask.py): where paving meets soft ground a
	// 15 cm kerb stands 12 cm proud. Its top is lit; where the paving lies south its front face looks at the camera
	// (a sunlit band as tall as 12 cm projects); where the paving lies north the raised top hides a sliver of road
	// and drops a contact shadow. Joints every 0.6 m along the edge; a dark contact line on the soft side.
	float paved = w[3] + w[4] + w[5] + w[6];
	vec4 kt = texture(kerb_tex, (world_m - mask_origin_m) * water_px_per_m / water_size_px);
	float kd = kt.r - 0.5;                                    // metres, + into the paving
	vec2 kn = vec2(kt.g, kt.b) * 2.0 - 1.0;
	kn = kn / max(length(kn), 1e-4);
	vec3 kerb_nrm = vec3(0.0, 0.0, 1.0);
	float kerb_any = 0.0;
	if (kt.a < 0.5 && kd > -0.12 && kd < 0.5) {
		float aa = max(fwidth(kd), 0.01);
		float face_len = 0.12 * 24.513 / 20.576 * max(kn.y, 0.0);
		float hide_len = 0.12 * 24.513 / 20.576 * max(-kn.y, 0.0);
		float top = smoothstep(-aa, aa, kd) * (1.0 - smoothstep(0.15 - aa, 0.15 + aa, kd));
		float front = smoothstep(0.15 - aa, 0.15 + aa, kd) * (1.0 - smoothstep(0.15 + face_len - aa, 0.15 + face_len + aa, kd));
		float hidden = smoothstep(0.15 - aa, 0.15 + aa, kd) * (1.0 - smoothstep(0.15 + hide_len - aa, 0.15 + hide_len + aa, kd));
		float shadow = smoothstep(0.15 + hide_len - aa, 0.15 + hide_len + aa, kd) * (1.0 - smoothstep(0.27 + hide_len, 0.32 + hide_len, kd)) * step(0.05, -kn.y);
		float contact = (1.0 - smoothstep(-0.07, -0.02, kd)) * smoothstep(-0.12, -0.07, kd);
		vec2 tng = vec2(-kn.y, kn.x);
		float joints = smoothstep(0.46, 0.485, abs(fract(dot(world_m, tng) / 0.6) - 0.5));
		vec3 kerb_col = mix(vec3(0.46, 0.22, 0.16), vec3(0.70, 0.68, 0.63), clamp((w[5] + w[6]) * 2.4, 0.0, 1.0));
		vec3 sun = normalize(vec3(-0.57, 0.82, 0.0));
		vec3 top_col = kerb_col * (0.96 - 0.25 * (1.0 - joints));
		vec3 face_col = kerb_col * (0.72 + 0.32 * max(dot(vec3(kn, 0.0), sun), 0.0)) * (0.92 - 0.2 * (1.0 - joints));
		col = mix(col, top_col, max(top, hidden));
		col = mix(col, face_col, front);
		col *= 1.0 - shadow * 0.28 - contact * 0.3;
		kerb_any = max(max(top, hidden), front);
		kerb_nrm = normalize(mix(vec3(0.0, 0.0, 1.0), vec3(kn, 0.35), front));
	}

	// coping stones along every lake and canal edge (the land side), 35 cm wide, jointed, slightly raised
	vec4 wt = texture(water_tex, (world_m - mask_origin_m) * water_px_per_m / water_size_px);
	float land = -(wt.r - 0.5) * 8.0;                         // metres from the water, on land
	vec2 wg = vec2(dFdx(wt.r) / max(abs(dFdx(world_m.x)), 1e-5), dFdy(wt.r) / max(abs(dFdy(world_m.y)), 1e-5));
	if (land > -0.02 && land < 0.38) {
		vec2 tng2 = normalize(vec2(-wg.y, wg.x) + vec2(1e-5));
		float jj = smoothstep(0.46, 0.49, abs(fract(dot(world_m, tng2) / 0.75) - 0.5));
		vec3 cop = vec3(0.74, 0.72, 0.67) * (0.95 - 0.28 * (1.0 - jj));
		cop *= 0.9 + 0.2 * texture(noise_tex, world_m / 1.7).r;
		col = mix(col, cop, smoothstep(0.38, 0.33, land));
		col *= 1.0 - smoothstep(0.3, 0.38, land) * smoothstep(0.42, 0.38, land) * 0.35;   // its inner edge
		kerb_any = 1.0;
	}

	// damp rim along the water, contact AO, then the sun shadow (cool) and drifting clouds
	col = mix(col, col * vec3(0.66, 0.72, 0.70), sh.b * 0.7);
	col *= 1.0 - sh.g * 0.5;
	col = mix(col, col * shadow_tint, sh.r * daylight * 0.82);
	float cloud = smoothstep(0.42, 0.78, texture(noise_tex, (world_m + cloud_offset) / 95.0).a);
	col *= 1.0 - cloud * cloud_strength * daylight;

	COLOR = vec4(col, 1.0);
	nrm = normalize(mix(nrm, kerb_nrm, kerb_any));
	NORMAL_MAP = nrm * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = 1.0;
}

// Player silhouette for occlusion ghosts (roadmap I6; scripts/world/occlusion_ghosts.gd).
// Draws the player's current animation frame as a soft pale fill with a brighter inner rim. The ghost is a child
// of the occluding sprite with clip_children on, so it only ever shows on the pixels that hide the player.
// The rim is INSIDE the silhouette edge (alpha minus the neighbours' minimum), so it never spills past the shape.
shader_type canvas_item;

uniform vec4 fill_color : source_color = vec4(0.93, 0.91, 0.86, 0.30);
uniform vec4 rim_color : source_color = vec4(0.97, 0.95, 0.90, 0.85);
// Rim width in texels of the 3x supersampled character sheet (3 texels = 1 game px).
uniform float rim_texels = 3.0;

void fragment() {
	float a = texture(TEXTURE, UV).a;
	vec2 d = TEXTURE_PIXEL_SIZE * rim_texels;
	float n = min(min(texture(TEXTURE, UV + vec2(d.x, 0.0)).a, texture(TEXTURE, UV - vec2(d.x, 0.0)).a),
			min(texture(TEXTURE, UV + vec2(0.0, d.y)).a, texture(TEXTURE, UV - vec2(0.0, d.y)).a));
	float rim = clamp(a - n, 0.0, 1.0);
	vec4 c = mix(fill_color, rim_color, rim);
	COLOR = vec4(c.rgb, a * c.a);
}

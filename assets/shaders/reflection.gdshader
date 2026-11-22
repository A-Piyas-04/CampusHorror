shader_type canvas_item;

// Map v2: a building's reflection in the lake (a vertically mirrored copy of its layer sprite, clipped to the water
// polygon by tools/zones/campus_world.py). Rippled sideways, tinted towards the water, fading with the reflected
// height so only the facade near the waterline reads clearly, the way still water reflects at a low angle.

uniform vec3 water = vec3(0.10, 0.18, 0.15);
uniform float strength : hint_range(0.0, 1.0) = 0.62;
uniform float fade_px = 640.0;      // render pixels of building height over which the reflection fades out
uniform float ripple = 0.0026;

varying float height_px;

void vertex() {
	height_px = -VERTEX.y;          // the sprite's own pixels above its base line (before the mirror)
}

void fragment() {
	vec2 uv = UV;
	uv.x += sin(UV.y * 260.0 + TIME * 1.7) * ripple + sin(UV.y * 90.0 - TIME * 0.9) * ripple * 0.6;
	vec4 tex = texture(TEXTURE, uv);
	float fade = 1.0 - smoothstep(0.0, fade_px, height_px);
	vec3 col = mix(tex.rgb * 0.62, water, 0.45);
	COLOR = vec4(col, tex.a * strength * fade);
}

extends Node2D
## TEMPORARY probe: does CanvasModulate darken an `unshaded` canvas material in this renderer? Saves a PNG, quits.

func _ready() -> void:
	var cm := CanvasModulate.new()
	cm.color = Color(0.13, 0.15, 0.26)
	add_child(cm)
	for i in 2:
		var r := Polygon2D.new()
		r.polygon = PackedVector2Array([Vector2(100 + i * 300, 100), Vector2(300 + i * 300, 100), Vector2(300 + i * 300, 300), Vector2(100 + i * 300, 300)])
		r.color = Color(1, 0.8, 0.5)
		if i == 1:
			var m := ShaderMaterial.new()
			var s := Shader.new()
			s.code = "shader_type canvas_item;\nrender_mode unshaded;\nvoid fragment(){ COLOR = vec4(1.0, 0.8, 0.5, 1.0); }"
			m.shader = s
			r.material = m
		add_child(r)
	for k in 30:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var k := float(img.get_width()) / 1920.0
	var a := img.get_pixel(int(200 * k), int(200 * k))
	var b := img.get_pixel(int(500 * k), int(200 * k))
	print("[PROBE] shaded under modulate: %s   unshaded under modulate: %s" % [a, b])
	get_tree().quit()

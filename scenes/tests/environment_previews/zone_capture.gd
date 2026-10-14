extends Node
## TEMPORARY test-only screenshot tool: instances the real scenes/core/Main.tscn (gameplay camera and zoom, real
## zone loading), teleports the player, optionally switches the test night tint / lantern on, waits for fades to
## settle and saves the viewport. Needs a window (not --headless). Never saves the game.
## Args (after `--`): `--out-dir=<absolute dir>` and `--shots=<name>@<x>,<y>[,<option>...][;...]`. Quits when done.
## Shot options: `night`, `lantern`, `zone=<zone_id>` (entered at the given feet position), `zoom=<f>`,
## `face=<down|up|left|right>` (a short step that way so the player faces it, then back to the position) and
## `walk=<down|up|left|right>` (the move action is held while the shot is taken).
## Global `--zoom=<f>` sets the default camera zoom.

const MAIN_SCENE := "res://scenes/core/Main.tscn"


func _ready() -> void:
	var out_dir := _arg_value("--out-dir=")
	var shots := _arg_value("--shots=").split(";", false)
	if out_dir.is_empty() or shots.is_empty():
		push_error("[CAPTURE] need --out-dir= and --shots=")
		get_tree().quit(1)
		return
	DirAccess.make_dir_recursive_absolute(out_dir)
	var main := (load(MAIN_SCENE) as PackedScene).instantiate() as Main
	add_child(main)
	var player := main.get_node("World/Player") as CharacterBody2D
	var camera := player.get_node("Camera") as Camera2D
	var lantern := player.get_node("Lantern") as PointLight2D
	var tint := main.get_node("DayNightTint")
	var default_zoom := camera.zoom
	if not _arg_value("--zoom=").is_empty():
		default_zoom = Vector2.ONE * float(_arg_value("--zoom="))
	var lantern_default := lantern.enabled
	await _settle(1.0)
	for shot: String in shots:
		var name := shot.get_slice("@", 0)
		var parts := shot.get_slice("@", 1).split(",")
		var pos := Vector2(float(parts[0]), float(parts[1]))
		var opts := {}
		for part in parts.slice(2):
			opts[part.get_slice("=", 0)] = part.get_slice("=", 1) if part.contains("=") else "1"
		camera.zoom = Vector2.ONE * float(opts.zoom) if opts.has("zoom") else default_zoom
		tint.set("is_night", opts.has("night"))
		lantern.enabled = true if opts.has("lantern") else lantern_default
		if opts.has("zone") and opts.zone != main.get_current_zone_id():
			main.enter_zone_at_position(opts.zone, pos)
			await _settle(0.3)
		player.call("teleport", pos)
		if opts.has("face"):
			await _hold("move_" + opts.face, 4)
			player.call("teleport", pos)
		await _settle(0.8)
		if opts.has("walk"):
			Input.action_press("move_" + opts.walk)
			for i in 9:
				await get_tree().physics_frame
		await RenderingServer.frame_post_draw
		var path := out_dir.path_join(name + ".png")
		var err := get_viewport().get_texture().get_image().save_png(path)
		if opts.has("walk"):
			Input.action_release("move_" + opts.walk)
		var anim: StringName = player.get_node("Sprite").get("animation") if player.has_node("Sprite") else &"-"
		print("[CAPTURE] %s at %s zone %s anim %s %s -> %s (%s)" % [name, pos, main.get_current_zone_id(), anim, opts.keys(), path, error_string(err)])
	get_tree().quit(0)


func _hold(action: String, frames: int) -> void:
	Input.action_press(action)
	for i in frames:
		await get_tree().physics_frame
	Input.action_release(action)
	await get_tree().physics_frame


func _settle(seconds: float) -> void:
	for i in 3:
		await get_tree().physics_frame
	await get_tree().create_timer(seconds).timeout
	for i in 3:
		await get_tree().process_frame


func _arg_value(prefix: String) -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with(prefix):
			return arg.trim_prefix(prefix)
	return ""

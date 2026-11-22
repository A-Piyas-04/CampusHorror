extends Node
## Test-only screenshot tool for the whole campus at night (needs a window): starts Chapter 2 (chapter select),
## then photographs the plaza arrival, the Mosque's beacon, every campus interior and the other exteriors at the
## real in-game zoom, night tint and lantern. The guard is switched off. Uses its own save file.
## Args (after `--`): `--out-dir=<absolute dir>`. Quits when done.

const TEST_SAVE := "user://test_campus_capture_save.json"
## [shot name, zone_id, spawn_id or "", feet offset from the spawn]
const SHOTS := [
	["plaza_mosque_beacon", "central_plaza", "outside_mosque", Vector2(0, 40)],
	["plaza_admin", "central_plaza", "outside_admin", Vector2(0, 60)],
	["plaza_north_gate", "central_plaza", "plaza_from_academic", Vector2(0, 80)],
	["mosque", "mosque_prayer_hall", "mosque_from_plaza", Vector2(0, -60)],
	["admin_lobby", "admin_lobby", "lobby_from_outside", Vector2(0, -40)],
	["admin_office", "admin_office", "office_from_lobby", Vector2(40, -20)],
	["auditorium", "auditorium_hall", "auditorium_from_plaza", Vector2(100, -120)],
	["av_hall", "av_hall", "av_from_auditorium", Vector2(80, -40)],
	["cafe", "central_cafe", "cafe_from_plaza", Vector2(120, -60)],
	["academic_ext", "academic_exterior", "outside_academic_1", Vector2(0, 40)],
	["academic_corridor", "academic_corridor", "corridor_from_outside", Vector2(120, 0)],
	["classroom", "academic_classroom", "classroom_from_corridor", Vector2(80, -40)],
	["lab", "academic_lab", "lab_from_outside", Vector2(80, -30)],
	["halls_ext", "halls_exterior", "outside_south_hall", Vector2(200, 40)],
	["hall_corridor", "hall_corridor", "hallcorr_from_outside", Vector2(150, 0)],
	["dorm_room", "hall_room", "room_from_corridor", Vector2(30, -20)],
	["common_room", "hall_common", "common_from_outside", Vector2(60, -30)],
]

## Chapter 3 and 4 shots (`--chapter=3` / `--chapter=4`): their creatures are shown (switched off, still visible).
const SHOTS3 := [
	["ch3_road_students", "academic_exterior", "academic_from_plaza", Vector2(-300, -100)],
	["ch3_workshop_shutter", "academic_exterior", "academic_from_plaza", Vector2(-1127, -290)],
	["ch3_generator", "academic_exterior", "academic_from_halls", Vector2(-1450, -380)],
	["ch3_corridor_student", "academic_corridor", "corridor_from_outside", Vector2(560, -20)],
	["ch3_lab_keybox", "academic_lab", "lab_from_outside", Vector2(300, -150)],
]
const SHOTS4 := [
	["ch4_courtyard", "halls_exterior", "halls_from_academic", Vector2(0, 700)],
	["ch4_rafi", "halls_exterior", "halls_from_academic", Vector2(0, 1680)],
	["ch4_ub_stair", "halls_exterior", "outside_south_hall", Vector2(770, -10)],
	["ch4_corridor_sleeper", "hall_corridor", "hallcorr_from_outside", Vector2(500, 0)],
]
const SHOTS5 := [
	["ch5_workshop", "me_workshop", "workshop_from_outside", Vector2(300, -120)],
	["ch5_pit_lift", "me_workshop", "workshop_from_lift", Vector2(0, 10)],
	["ch5_b1_corridor", "facility_corridor", "corridor_from_lift", Vector2(300, 0)],
	["ch5_control", "facility_control", "control_from_corridor", Vector2(150, -60)],
	["ch5_lab", "facility_lab", "lab_from_corridor", Vector2(-120, -80)],
	["ch5_chamber", "facility_chamber", "chamber_from_lift", Vector2(300, -40)],
]

var _out := ""
var _chapter := 2
var main: Main


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out-dir="):
			_out = arg.trim_prefix("--out-dir=")
		elif arg.begins_with("--chapter="):
			_chapter = int(arg.trim_prefix("--chapter="))
	DirAccess.make_dir_recursive_absolute(_out)
	SaveService.save_path = TEST_SAVE
	_run.call_deferred()


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_out.path_join(name + ".png"))
	print("[CAMPUSCAP] ", name)


func _wait(s: float) -> void:
	await get_tree().create_timer(s, true, false, true).timeout


func _run() -> void:
	Game.set("_start_mode", "chapter:%d" % _chapter)
	main = (load("res://scenes/core/Main.tscn") as PackedScene).instantiate() as Main
	get_tree().root.add_child(main)
	get_tree().current_scene = main
	var player := main.get_node("World/Player") as Player
	var card := main.get_node("UI/StoryCard")
	await _wait(1.0)
	await _shot("ch%d_intro_card" % _chapter)
	while bool(card.call("is_open")):
		var ev := InputEventAction.new()
		ev.action = "interact"
		ev.pressed = true
		Input.parse_input_event(ev)
		await _wait(0.1)
		ev = InputEventAction.new()
		ev.action = "interact"
		ev.pressed = false
		Input.parse_input_event(ev)
		await _wait(0.4)
	await _wait(1.5)
	await _shot("ch%d_arrival" % _chapter)
	main.get_director().debug_toggle_guard()
	for s in {2: SHOTS, 3: SHOTS3, 4: SHOTS4, 5: SHOTS5}[_chapter]:
		var zone_id: String = s[1]
		if main.get_current_zone_id() != zone_id:
			main.change_zone(zone_id, s[2])
		else:
			var m := main.get_current_zone().find_spawn_marker(s[2])
			player.teleport(m.global_position)
		await _wait(0.2)
		player.teleport(player.global_position + s[3])
		await _wait(1.2)
		await _shot(s[0])
	for p in [TEST_SAVE, TEST_SAVE + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))
	SaveService.save_path = SaveService.SAVE_PATH
	get_tree().quit(0)

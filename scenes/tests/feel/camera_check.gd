extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I camera suite (I4), on the real Main.tscn: zoom and limits from the zone profile, the view never shows
## outside the zone's authored area, look-ahead leads movement and settles, teleports snap, shake decays.

const MANIFESTS := "res://scenes/tests/zone_validation/manifests/%s.json"
const FIELD := Vector2(12320, 4300)

var cam: Camera2D


func _run() -> void:
	tag = "CAMERA"
	cam = player.get_node("Camera") as Camera2D
	await _profile_and_limits("campus")
	await _look_ahead()
	await _snap_and_shake()
	main.change_zone("cds_veranda", "inside_cds_entry")
	await frames(3)
	await _profile_and_limits("cds_veranda")
	main.change_zone("campus", "explore_start")
	await frames(3)


func _profile_and_limits(zone_id: String) -> void:
	var profile := main.get_current_zone().profile
	var r := profile.camera_limits
	check(cam.zoom.is_equal_approx(Vector2.ONE * profile.camera_zoom) and cam.limit_left == floori(r.position.x)
		and cam.limit_top == floori(r.position.y) and cam.limit_right == ceili(r.end.x) and cam.limit_bottom == ceili(r.end.y),
		"%s: zoom %.2f and limits %s from the profile" % [zone_id, cam.zoom.x, r])
	var m: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MANIFESTS % zone_id))
	var b: Array = m.playable_bounds
	var bounds := Rect2(b[0], b[1], b[2], b[3])
	var probes := [bounds.position, Vector2(bounds.end.x, bounds.position.y), bounds.end, Vector2(bounds.position.x, bounds.end.y), bounds.get_center()]
	for marker in main.get_current_zone().get_spawn_markers():
		probes.append(marker.global_position)
	# The probes reach the zone's borders, where walk-off edges (ZoneEdge) live: switch them off so a probe tests
	# this zone's camera instead of travelling to the neighbour.
	for e in main.get_current_zone().find_children("*", "ZoneEdge", true, false):
		(e as ZoneEdge).set_deferred("monitoring", false)
	await frames(2)
	var outside := []
	for p in probes:
		await place(p)
		await frames(2)
		var view: Rect2 = cam.call("get_view_rect")
		if not r.grow(1.0).encloses(view):
			outside.append("%s -> view %s" % [p, view])
	check(outside.is_empty(), "%s: with the player at the %d corners / centre / spawns of the playable area the view stays inside the limits (no grey void) (bad %s)" % [zone_id, probes.size(), outside])


func _look_ahead() -> void:
	await place(FIELD)
	await hold(["move_right", "sprint"], 120)
	var lead := cam.offset
	check(lead.x >= 0.8 * float(cam.get("look_ahead_px")) and absf(lead.y) < 2.0,
		"sprinting right, the camera leads by %s (target up to %.0f px ahead)" % [lead.round(), float(cam.get("look_ahead_px"))])
	await hold(["move_down"], 90)
	var lead_down := cam.offset
	check(lead_down.y > 10.0 and lead_down.x < lead.x, "turning down, the lead eases round to %s" % lead_down.round())
	await seconds(3.0)
	check(cam.offset.length() < 2.0, "standing still, the lead settles back to %s" % cam.offset.round())


func _snap_and_shake() -> void:
	var target := FIELD + Vector2(400, 150)
	player.teleport(target)
	await frames(2)
	var centre := cam.get_screen_center_position()
	check(centre.distance_to(target) <= 1.0, "a teleport snaps the view onto the feet at once (centre %s, feet %s)" % [centre.round(), target])
	cam.call("shake", 0.6)
	await frames(3)
	var shaking := cam.offset.length()
	await seconds(1.0)
	check(shaking > 0.5 and cam.offset.length() < 0.5, "shake(0.6) moves the view (%.1f px) and decays to rest within 1 s (%.2f px)" % [shaking, cam.offset.length()])

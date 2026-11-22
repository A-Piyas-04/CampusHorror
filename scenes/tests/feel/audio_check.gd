extends "res://scenes/tests/feel/feel_check_base.gd"
## Phase I audio suite (I3), on the real Main.tscn. Headless runs use the Dummy audio driver, which never mixes:
## AudioDirector and the footstep player then track what they would play without creating playbacks (no leaks).
## This suite asserts that intended state and every parameter; the sound itself is checked by ear (manual check).

const FOOTSTEPS := "res://data/audio/footsteps.tres"
const SURFACES := "res://data/audio/surfaces.tres"
const EXPECTED_BUSES := ["Master", "Music", "Ambience", "UI", "World", "Footsteps"]


func _run() -> void:
	tag = "AUDIO"
	_buses()
	await _ambience_and_reverb("campus")
	_player_audio_nodes()
	_footstep_set()
	await _footsteps()
	await _travel_ducking()


func _buses() -> void:
	var names := []
	for i in AudioServer.bus_count:
		names.append(String(AudioServer.get_bus_name(i)))
	var world := AudioServer.get_bus_index(&"World")
	var has_reverb := false
	for e in AudioServer.get_bus_effect_count(world):
		has_reverb = has_reverb or AudioServer.get_bus_effect(world, e) is AudioEffectReverb
	check(names == EXPECTED_BUSES and AudioServer.get_bus_send(AudioServer.get_bus_index(&"Footsteps")) == &"World" and has_reverb,
		"bus layout %s; Footsteps -> World; World has the zone reverb" % [names])
	check(AudioDirector.can_play() == (AudioServer.get_driver_name() != "Dummy"),
		"driver '%s': AudioDirector plays sounds only with a real device (can_play %s)" % [AudioServer.get_driver_name(), AudioDirector.can_play()])


func _ambience_and_reverb(zone_id: String) -> void:
	var profile := main.get_current_zone().profile
	check(main.get_current_zone_id() == zone_id and AudioDirector.get_ambience() == profile.ambience and profile.ambience != null,
		"%s: ambience bed is the profile's %s" % [zone_id, profile.ambience.resource_path.get_file() if profile.ambience else "none"])
	var wav := profile.ambience as AudioStreamWAV
	check(wav != null and wav.loop_mode == AudioStreamWAV.LOOP_FORWARD and wav.loop_begin == 0 and wav.loop_end >= 1279999 - 1,
		"%s: the bed is imported as a forward loop over the whole file (loop %s..%s, from the WAV smpl chunk)" % [zone_id, wav.loop_begin if wav else -1, wav.loop_end if wav else -1])
	await seconds(1.3)
	var rv := AudioDirector.get_reverb()
	check(rv != null and approx(rv.room_size, profile.reverb_room_size, 0.01) and approx(rv.damping, profile.reverb_damping, 0.01) and approx(rv.wet, profile.reverb_wet, 0.01),
		"%s: World reverb eased to the profile (room %.2f, damping %.2f, wet %.2f)" % [zone_id, rv.room_size, rv.damping, rv.wet])


func _player_audio_nodes() -> void:
	var listener := player.get_node("Listener") as AudioListener2D
	var fp := player.get_node("Footsteps") as AudioStreamPlayer2D
	check(listener.is_current() and fp.bus == &"Footsteps" and fp.max_polyphony >= 2,
		"sounds are heard from the player's feet (AudioListener2D current); footsteps on the Footsteps bus, polyphony %d" % fp.max_polyphony)


func _footstep_set() -> void:
	var fset := load(FOOTSTEPS) as FootstepSet
	var table := (load(SURFACES) as SurfaceTable).by_texture_stem
	var surfaces: Array = table.values()
	surfaces.append(&"concrete")
	var bad := []
	for s in surfaces:
		var st := fset.stream_for(s) as AudioStreamRandomizer
		if st == null or st.streams_count < 3 or not fset.streams.has(s):
			bad.append(s)
			continue
		for i in st.streams_count:
			if st.get_stream(i) == null:
				bad.append("%s#%d" % [s, i])
	check(bad.is_empty(), "every surface (%s) has a randomised footstep set of real takes (bad %s)" % [surfaces, bad])


func _walk_step(at: Vector2, actions: Array) -> Dictionary:
	var fp := player.get_node("Footsteps")
	await place(at)
	var before: int = fp.steps_played
	await hold(actions, 70)
	await frames(1)
	return {"n": int(fp.steps_played) - before, "last": fp.last_step}


func _footsteps() -> void:
	var fset := load(FOOTSTEPS) as FootstepSet
	for spec in [["the plaza pavers", Vector2(5760, 2510), ["move_up"], &"paving", &"walk"],
			["the field, sprinting", Vector2(12320, 4300), ["move_right", "sprint"], &"grass", &"run"],
			["the field, sneaking", Vector2(12320, 4300), ["move_right", "sneak"], &"grass", &"sneak"]]:
		var r: Dictionary = await _walk_step(spec[1], spec[2])
		var last: Dictionary = r.last
		var want_db := float(fset.gain_db.get(spec[3], 0.0)) + float(fset.gait_gain_db.get(spec[4], 0.0))
		check(r.n >= 1 and last.get("surface") == spec[3] and last.get("gait") == spec[4] and approx(float(last.get("volume_db", 99.0)), want_db, 0.01),
			"%s: %d steps, last on %s / %s at %.1f dB (want %s / %s at %.1f dB)" % [spec[0], r.n, last.get("surface"), last.get("gait"), last.get("volume_db", 0.0), spec[3], spec[4], want_db])
	main.change_zone("cds_veranda", "inside_cds_entry")
	await frames(2)
	var rv: Dictionary = await _walk_step(Vector2(0, 0), ["move_down"])
	check(rv.n >= 1 and rv.last.get("surface") == &"concrete" and approx(float(rv.last.get("pitch_scale", 0.0)), float(fset.pitch.get(&"concrete", 1.0)), 0.001),
		"cds_veranda: steps on concrete (the profile default) at pitch %.2f" % float(rv.last.get("pitch_scale", 0.0)))
	await _ambience_and_reverb("cds_veranda")


func _travel_ducking() -> void:
	var idx := AudioServer.get_bus_index(&"Ambience")
	var base := AudioServer.get_bus_volume_db(idx)
	var lowest := base
	check(main.travel("campus", "explore_start"), "travel back to campus starts")
	while main.is_transitioning():
		lowest = minf(lowest, AudioServer.get_bus_volume_db(idx))
		await get_tree().process_frame
	await seconds(0.5)
	check(approx(lowest, base + AudioDirector.DUCK_DB, 0.5) and approx(AudioServer.get_bus_volume_db(idx), base, 0.05),
		"during the travel fade the Ambience bus dips to %.1f dB (base %.1f, duck %.0f) and comes back to %.1f dB" % [lowest, base, AudioDirector.DUCK_DB, AudioServer.get_bus_volume_db(idx)])
	await _ambience_and_reverb("campus")

extends Node

## Autoload `AudioDirector` (roadmap I3): the zone's ambience bed and acoustics.
## - Ambience: two players on the Ambience bus crossfade (CROSSFADE s) when a zone with another bed is entered.
## - Acoustics: the World bus's reverb (footsteps and world sounds) eases to the zone profile's values.
## - Ducking: during a zone travel fade the Ambience and World buses dip by DUCK_DB.
## Later home of composure audio (breathing, heartbeat; roadmap J6). Bus layout: data/audio/default_bus_layout.tres.
## Without an audio device (the Dummy driver: headless tests) nothing is actually played, because the dummy driver
## never mixes, so playbacks would never be released; the intended state is still tracked for tests.

const CROSSFADE := 1.5
const SILENT_DB := -60.0
const DUCK_DB := -10.0
const REVERB_EASE := 1.0
const DUCKED_BUSES: Array[StringName] = [&"Ambience", &"World"]

var _players: Array[AudioStreamPlayer] = []
var _active := 0
var _reverb: AudioEffectReverb
var _bus_base_db := {}
var _tweens := {}
var _intended: Array[AudioStream] = [null, null]
var _can_play := true


func _ready() -> void:
	_can_play = AudioServer.get_driver_name() != "Dummy"
	for i in 2:
		var p := AudioStreamPlayer.new()
		p.name = "Ambience%d" % i
		p.bus = &"Ambience"
		p.volume_db = SILENT_DB
		add_child(p)
		_players.append(p)
	var world := AudioServer.get_bus_index(&"World")
	if world != -1:
		for e in AudioServer.get_bus_effect_count(world):
			var fx := AudioServer.get_bus_effect(world, e)
			if fx is AudioEffectReverb:
				_reverb = fx
	for bus in DUCKED_BUSES:
		var idx := AudioServer.get_bus_index(bus)
		_bus_base_db[bus] = AudioServer.get_bus_volume_db(idx) if idx != -1 else 0.0


## Looping beds would otherwise still hold their stream and playback when the engine shuts down (reported as
## leaked AudioStreamWAV / AudioStreamPlaybackWAV instances at exit).
func _exit_tree() -> void:
	for t in _tweens.values():
		if (t as Tween).is_valid():
			(t as Tween).kill()
	_tweens.clear()
	for p in _players:
		p.stop()
		p.stream = null
	_intended = [null, null]


## Called by Main on every zone entry.
func apply_profile(profile: ZoneProfile) -> void:
	_set_ambience(profile.ambience, profile.ambience_volume_db)
	if _reverb != null:
		_tween_to(&"reverb", _reverb, {"room_size": profile.reverb_room_size, "damping": profile.reverb_damping,
			"wet": profile.reverb_wet}, REVERB_EASE)


## Dips (true) or restores (false) the Ambience and World buses over `seconds`.
func duck(on: bool, seconds: float) -> void:
	for bus in DUCKED_BUSES:
		var idx := AudioServer.get_bus_index(bus)
		if idx == -1:
			continue
		var target: float = _bus_base_db[bus] + (DUCK_DB if on else 0.0)
		var key := StringName("bus_%s" % bus)
		if _tweens.has(key) and (_tweens[key] as Tween).is_valid():
			(_tweens[key] as Tween).kill()
		var t := create_tween()
		t.tween_method(func(db: float) -> void: AudioServer.set_bus_volume_db(idx, db),
			AudioServer.get_bus_volume_db(idx), target, maxf(seconds, 0.01))
		_tweens[key] = t


## The ambience bed currently playing (or fading in), or null.
func get_ambience() -> AudioStream:
	return _intended[_active]


## False without an audio device (Dummy driver): sounds are tracked but not played.
func can_play() -> bool:
	return _can_play


func get_reverb() -> AudioEffectReverb:
	return _reverb


func _set_ambience(stream: AudioStream, volume_db: float) -> void:
	var current := _players[_active]
	if stream != null and _intended[_active] == stream:
		_fade(current, volume_db, CROSSFADE, false)
		return
	_fade(current, SILENT_DB, CROSSFADE, true)
	_intended[_active] = null
	if stream == null:
		return
	_active = 1 - _active
	var next := _players[_active]
	_intended[_active] = stream
	next.volume_db = SILENT_DB
	if _can_play:
		next.stream = _looping(stream)
		next.play()
	_fade(next, volume_db, CROSSFADE, false)


func _fade(p: AudioStreamPlayer, db: float, seconds: float, stop_after: bool) -> void:
	var key := StringName("player_%s" % p.name)
	if _tweens.has(key) and (_tweens[key] as Tween).is_valid():
		(_tweens[key] as Tween).kill()
	var t := create_tween()
	t.tween_property(p, "volume_db", db, seconds)
	if stop_after:
		t.tween_callback(p.stop)
	_tweens[key] = t


func _tween_to(key: StringName, target: Object, values: Dictionary, seconds: float) -> void:
	if _tweens.has(key) and (_tweens[key] as Tween).is_valid():
		(_tweens[key] as Tween).kill()
	var t := create_tween().set_parallel(true)
	for prop: String in values:
		t.tween_property(target, prop, values[prop], seconds)
	_tweens[key] = t


## Ambience beds must loop. Generated WAVs carry their loop in a `smpl` chunk; this is the safety net.
func _looping(stream: AudioStream) -> AudioStream:
	var wav := stream as AudioStreamWAV
	if wav != null and wav.loop_mode == AudioStreamWAV.LOOP_DISABLED:
		push_warning("[AUDIO] ambience %s has no loop points; looping the whole file." % stream.resource_path)
	return stream

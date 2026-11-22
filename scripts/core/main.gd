class_name Main
extends Node2D

## Owns the world: which zone is loaded, the one persistent Player, and moving between zones.
##
## Two ways to change zone:
## - `travel()` / `travel_to_position()` (doors, loading a save): the player's input is locked, the screen fades
##   to black while the zone loads on a worker thread, the swap happens only while the screen is fully black,
##   then it fades back in (roadmap I5; Docs/PRESENTATION.md section 5: no visible stall).
## - `change_zone()` / `enter_zone_at_position()`: instant and synchronous (game start, tests, debug).
## Every entry applies the zone's ZoneProfile: footstep surfaces, camera zoom and limits, ambience and reverb.
## The scenes of the last few visited zones stay in memory, so going back through a door is instant.
## There is deliberately no background prefetch: a worker-thread load needs the main thread for part of its
## work, so any blocking load() of the same scene meanwhile can deadlock (seen in Phase I testing).

## Emitted after every zone entry (instant or travelled), once the player is in place.
signal zone_entered(zone_id: String)
## A fading travel started / finished (finished = faded back in and the player has control again).
signal transition_started(zone_id: String)
signal transition_finished(zone_id: String)

## zone_id -> scene path for every zone (shipping and debug-only). Data, not code: edit the resource.
@export var zone_registry: ZoneRegistry = preload("res://data/zones/zone_registry.tres")

@export var start_zone_id: String = "main_gate_exterior"
@export var start_spawn_id: String = "main_gate_entry"
## Seconds for each half of a travel fade (out, then in).
@export var fade_seconds: float = 0.3
## How many recently visited zone scenes stay loaded (instant return trips).
@export var kept_zone_scenes: int = 3

var _current_zone: Zone
var _transitioning := false
## Most recently used last: [scene_path, PackedScene].
var _kept_scenes: Array = []
var _director: StoryDirector
## The chapter directors by number (D32). Continue starts the one the save is in (GameState flag `chapter`).
const CHAPTERS := {
	1: "res://scripts/story/chapter_1.gd",
	2: "res://scripts/story/chapter_2.gd",
	3: "res://scripts/story/chapter_3.gd",
}

@onready var _world: Node2D = $World
@onready var _player: Player = $World/Player
@onready var _transition: TransitionLayer = $UI/TransitionLayer
@onready var _ghosts: OcclusionGhosts = $OcclusionGhosts
@onready var _tint: CanvasModulate = $DayNightTint


func _ready() -> void:
	add_to_group("main")
	_ghosts.setup(_player)
	# How the game was started (Game autoload): "new" / "continue" run the story; "" (the editor, tests) is the
	# classic instant start in daylight with no director.
	match Game.take_start_mode():
		"new":
			_start_story(true)
		"continue":
			if SaveService.load_at_start(self):
				_start_story(false)
			else:
				_start_story(true)
		var mode:
			# "chapter:N" (chapter select, tests): a fresh start of chapter N with what earlier chapters grant.
			if String(mode).begins_with("chapter:") and has_chapter(int(String(mode).get_slice(":", 1))):
				_start_story_at(int(String(mode).get_slice(":", 1)))
			else:
				change_zone(start_zone_id, start_spawn_id)


func _start_story(new_game: bool) -> void:
	var chapter := 1 if new_game else int(GameState.get_flag("chapter", 1))
	_director = _make_director(chapter if has_chapter(chapter) else 1)
	if new_game:
		_director.begin_new()
	else:
		_director.begin_continue()


func _start_story_at(chapter: int) -> void:
	_director = _make_director(chapter)
	_director.begin_new()


func has_chapter(chapter: int) -> bool:
	return CHAPTERS.has(chapter)


## Ends the running chapter's director and begins `chapter` in this session (called by a director's end card).
func start_chapter(chapter: int) -> void:
	if _director != null:
		_director.queue_free()
	_director = _make_director(chapter)
	_director.begin_from_previous()


func _make_director(chapter: int) -> StoryDirector:
	var lantern := _player.get_node("Lantern")
	lantern.set("burns_fuel", true)
	var d := (load(CHAPTERS[chapter]) as GDScript).new() as StoryDirector
	d.name = "Chapter%d" % chapter
	add_child(d)
	d.setup(self)
	GameState.set_flag("chapter", chapter)
	return d


# --- Instant (synchronous) zone changes ---------------------------------------------------------------------

## Replaces the current zone and moves the existing player to the given spawn marker, immediately.
## Leaves the current zone untouched if the zone or spawn can't be found.
func change_zone(zone_id: String, spawn_id: String) -> void:
	var zone := _instantiate_zone(zone_id)
	if zone == null:
		return
	var marker := zone.find_spawn_marker(spawn_id)
	if marker == null:
		push_error("Zone '%s' has no spawn marker '%s'." % [zone_id, spawn_id])
		zone.free()
		return
	_enter_zone(zone)
	_player.teleport(marker.global_position)
	print("[ZONE] Entered '%s' at spawn '%s'." % [zone_id, spawn_id])
	zone_entered.emit(zone_id)


## Replaces the current zone and places the player's feet at the global `feet_position`, immediately.
func enter_zone_at_position(zone_id: String, feet_position: Vector2) -> bool:
	var zone := _instantiate_zone(zone_id)
	if zone == null:
		return false
	_enter_zone(zone)
	_player.teleport(feet_position)
	print("[ZONE] Entered '%s' at position %s." % [zone_id, feet_position])
	zone_entered.emit(zone_id)
	return true


# --- Faded travel -------------------------------------------------------------------------------------------

## Travels to `spawn_id` in `zone_id` behind a fade. Returns false (and does nothing) if a travel is already
## running or the zone is unknown. Await `transition_finished` to know when the player has control again.
func travel(zone_id: String, spawn_id: String) -> bool:
	return _start_travel(zone_id, spawn_id, Vector2.ZERO, false)


## Like `travel()`, but places the feet at a global position (loading a save).
func travel_to_position(zone_id: String, feet_position: Vector2) -> bool:
	return _start_travel(zone_id, "", feet_position, true)


func is_transitioning() -> bool:
	return _transitioning


func has_zone(zone_id: String) -> bool:
	return zone_registry.has_zone(zone_id)


func get_current_zone_id() -> String:
	return _current_zone.zone_id if _current_zone != null else ""


## The story director in story mode, or null in the sandbox (debug tools and tests ask for it).
func get_director() -> StoryDirector:
	return _director


func get_current_zone() -> Zone:
	return _current_zone


## Bakes the current zone's navigation from its colliders if it has creatures and none is baked yet (the story
## director calls this on zone entry, still behind the travel fade). Returns true if a mesh exists afterwards.
func bake_navigation() -> bool:
	if _current_zone == null:
		return false
	if _current_zone.get_node_or_null("BakedNavigation") != null:
		return true
	for c in get_tree().get_nodes_in_group("creatures"):
		if _current_zone.is_ancestor_of(c):
			var profile := _current_zone.profile if _current_zone.profile != null else ZoneProfile.new()
			var bounds := profile.camera_limits if profile.camera_limits.size.x > 0.0 else Rect2(-3000, -3000, 6000, 6000)
			NavBuilder.bake(_current_zone, bounds)
			return true
	return false


func get_player_feet_position() -> Vector2:
	return _player.global_position


func _start_travel(zone_id: String, spawn_id: String, feet: Vector2, by_position: bool) -> bool:
	if _transitioning:
		return false
	var path := zone_registry.get_scene_path(zone_id)
	if path.is_empty():
		push_error("Unknown zone_id '%s'." % zone_id)
		return false
	_transitioning = true
	_run_travel(zone_id, path, spawn_id, feet, by_position)
	return true


func _run_travel(zone_id: String, path: String, spawn_id: String, feet: Vector2, by_position: bool) -> void:
	transition_started.emit(zone_id)
	_player.input_enabled = false
	if not ResourceLoader.has_cached(path) \
			and ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
		ResourceLoader.load_threaded_request(path)
	AudioDirector.duck(true, fade_seconds)
	await _transition.fade_to(1.0, fade_seconds)
	# Fully black from here until the fade-in: any stall (finishing the load, instancing the zone) is invisible.
	var packed := await _finish_load(path)
	var zone := _instantiate_zone(zone_id, packed)
	var marker: SpawnMarker = zone.find_spawn_marker(spawn_id) if zone != null and not by_position else null
	if zone == null or (not by_position and marker == null):
		push_error("Can't travel to '%s' spawn '%s'; staying here." % [zone_id, spawn_id])
		if zone != null:
			zone.free()
	else:
		_enter_zone(zone)
		_player.teleport(feet if by_position else marker.global_position)
		print("[ZONE] Travelled to '%s' %s." % [zone_id, ("at position %s" % feet) if by_position else ("at spawn '%s'" % spawn_id)])
		zone_entered.emit(zone_id)
	# Let the new zone settle for one physics step behind the black screen before revealing it.
	await get_tree().physics_frame
	await get_tree().process_frame
	AudioDirector.duck(false, fade_seconds)
	await _transition.fade_to(0.0, fade_seconds)
	_player.input_enabled = true
	_transitioning = false
	transition_finished.emit(get_current_zone_id())


## Collects the travel's threaded load, yielding frames while it runs (never blocking); falls back to the cache or
## a plain load.
func _finish_load(path: String) -> PackedScene:
	while ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
		await get_tree().process_frame
	if ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_LOADED:
		return ResourceLoader.load_threaded_get(path) as PackedScene
	return load(path) as PackedScene


# --- Internals ----------------------------------------------------------------------------------------------

func _instantiate_zone(zone_id: String, packed: PackedScene = null) -> Zone:
	var scene_path := zone_registry.get_scene_path(zone_id)
	if scene_path.is_empty():
		push_error("Unknown zone_id '%s'." % zone_id)
		return null
	if packed == null:
		packed = load(scene_path) as PackedScene
	if packed != null:
		_keep_scene(scene_path, packed)
	var zone := packed.instantiate() as Zone if packed != null else null
	if zone == null or zone.zone_id != zone_id:
		push_error("Scene for zone_id '%s' has no Zone root with a matching zone_id." % zone_id)
		if zone != null:
			zone.free()
		return null
	return zone


func _enter_zone(zone: Zone) -> void:
	# Ghosts live on the old zone's sprites; take them back before that zone is freed.
	_ghosts.release_all()
	if _current_zone != null:
		_world.remove_child(_current_zone)
		_current_zone.queue_free()
	_current_zone = zone
	_world.add_child(zone)
	_world.move_child(zone, 0)
	for door in zone.get_doors():
		door.travel_requested.connect(_on_door_travel_requested)
	_apply_profile(zone)
	_ghosts.index_zone(zone)


## Everything the zone's profile decides (a zone without one gets the defaults).
func _apply_profile(zone: Zone) -> void:
	var profile := zone.profile if zone.profile != null else ZoneProfile.new()
	_player.surface_map = SurfaceMap.build(zone, profile.default_surface)
	var camera := _player.get_node("Camera")
	if camera.has_method("apply_profile"):
		camera.call("apply_profile", profile)
	AudioDirector.apply_profile(profile)
	# Night (story mode): the zone's own darkness; the sandbox start keeps the day tint (F2 still flips it).
	if GameState.has_flag("night"):
		_tint.set("night_color", profile.night_ambient)
		_tint.set("is_night", true)


## Keeps a reference to the zone's PackedScene (most recent last) so the resource cache holds it.
func _keep_scene(path: String, packed: PackedScene) -> void:
	for i in range(_kept_scenes.size() - 1, -1, -1):
		if _kept_scenes[i][0] == path:
			_kept_scenes.remove_at(i)
	_kept_scenes.append([path, packed])
	while _kept_scenes.size() > kept_zone_scenes:
		_kept_scenes.pop_front()


func _on_door_travel_requested(destination_zone_id: String, destination_spawn_id: String) -> void:
	travel(destination_zone_id, destination_spawn_id)

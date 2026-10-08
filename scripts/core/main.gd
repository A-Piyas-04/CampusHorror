class_name Main
extends Node2D

## Every zone a door can lead to, by zone_id. Scenes are loaded only when entered.
const ZONE_SCENES: Dictionary[String, String] = {
	"test_zone_a": "res://scenes/world/TestZoneA.tscn",
	"test_zone_b": "res://scenes/world/TestZoneB.tscn",
	"main_gate_exterior": "res://scenes/world/MainGateExterior.tscn",
	"cds_veranda": "res://scenes/world/CdsVeranda.tscn",
}

@export var start_zone_id: String = "test_zone_a"
@export var start_spawn_id: String = "start"

var _current_zone: Zone

@onready var _world: Node2D = $World
@onready var _player: Player = $World/Player


func _ready() -> void:
	change_zone(start_zone_id, start_spawn_id)


## Replaces the current zone and moves the existing player to the given spawn marker.
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


## Replaces the current zone and places the existing player's feet at the global `feet_position`.
## Used when loading a save; doors always use `change_zone()`.
func enter_zone_at_position(zone_id: String, feet_position: Vector2) -> bool:
	var zone := _instantiate_zone(zone_id)
	if zone == null:
		return false
	_enter_zone(zone)
	_player.teleport(feet_position)
	print("[ZONE] Entered '%s' at position %s." % [zone_id, feet_position])
	return true


func has_zone(zone_id: String) -> bool:
	return ZONE_SCENES.has(zone_id)


func get_current_zone_id() -> String:
	return _current_zone.zone_id if _current_zone != null else ""


func get_player_feet_position() -> Vector2:
	return _player.global_position


func _instantiate_zone(zone_id: String) -> Zone:
	if not ZONE_SCENES.has(zone_id):
		push_error("Unknown zone_id '%s'." % zone_id)
		return null
	var zone := (load(ZONE_SCENES[zone_id]) as PackedScene).instantiate() as Zone
	if zone == null or zone.zone_id != zone_id:
		push_error("Scene for zone_id '%s' has no Zone root with a matching zone_id." % zone_id)
		if zone != null:
			zone.free()
		return null
	return zone


func _enter_zone(zone: Zone) -> void:
	if _current_zone != null:
		_world.remove_child(_current_zone)
		_current_zone.queue_free()
	_current_zone = zone
	_world.add_child(zone)
	_world.move_child(zone, 0)
	for door in zone.get_doors():
		door.travel_requested.connect(_on_door_travel_requested)


func _on_door_travel_requested(destination_zone_id: String, destination_spawn_id: String) -> void:
	change_zone.call_deferred(destination_zone_id, destination_spawn_id)

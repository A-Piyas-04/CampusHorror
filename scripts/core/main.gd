extends Node2D

## Every zone a door can lead to, by zone_id. Scenes are loaded only when entered.
const ZONE_SCENES: Dictionary[String, String] = {
	"test_zone_a": "res://scenes/world/TestZoneA.tscn",
	"test_zone_b": "res://scenes/world/TestZoneB.tscn",
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
	if not ZONE_SCENES.has(zone_id):
		push_error("Unknown zone_id '%s'." % zone_id)
		return
	var zone := (load(ZONE_SCENES[zone_id]) as PackedScene).instantiate() as Zone
	if zone == null or zone.zone_id != zone_id:
		push_error("Scene for zone_id '%s' has no Zone root with a matching zone_id." % zone_id)
		if zone != null:
			zone.free()
		return
	var marker := zone.find_spawn_marker(spawn_id)
	if marker == null:
		push_error("Zone '%s' has no spawn marker '%s'." % [zone_id, spawn_id])
		zone.free()
		return

	if _current_zone != null:
		_world.remove_child(_current_zone)
		_current_zone.queue_free()
	_current_zone = zone
	_world.add_child(zone)
	_world.move_child(zone, 0)
	for door in zone.get_doors():
		door.travel_requested.connect(_on_door_travel_requested)

	_player.teleport(marker.global_position)
	print("[ZONE] Entered '%s' at spawn '%s'." % [zone_id, spawn_id])


func _on_door_travel_requested(destination_zone_id: String, destination_spawn_id: String) -> void:
	change_zone.call_deferred(destination_zone_id, destination_spawn_id)

class_name Zone
extends Node2D

## Stable, globally unique ID. Must match this zone's key in Main's ZONE_SCENES.
@export var zone_id: String = ""


func _ready() -> void:
	var seen: Dictionary[String, bool] = {}
	for marker in get_spawn_markers():
		if marker.spawn_id.is_empty() or seen.has(marker.spawn_id):
			push_error("Zone '%s': spawn_id '%s' on %s is empty or duplicated." % [zone_id, marker.spawn_id, marker.get_path()])
		seen[marker.spawn_id] = true


func get_spawn_markers() -> Array[SpawnMarker]:
	var markers: Array[SpawnMarker] = []
	for node in find_children("*", "Marker2D", true, false):
		if node is SpawnMarker:
			markers.append(node)
	return markers


func find_spawn_marker(spawn_id: String) -> SpawnMarker:
	for marker in get_spawn_markers():
		if marker.spawn_id == spawn_id:
			return marker
	return null


func get_doors() -> Array[Door]:
	var doors: Array[Door] = []
	for node in find_children("*", "Node2D", true, false):
		if node is Door:
			doors.append(node)
	return doors

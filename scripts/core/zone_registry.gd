class_name ZoneRegistry
extends Resource

## Every zone a door, a save or the start settings can lead to, by `zone_id`. Scenes load only when entered.
## Instance: `data/zones/zone_registry.tres` (edit it in the Inspector; no code change needed for a new zone).
## Each key must equal the `zone_id` exported on that scene's `Zone` root.

## Zones that ship.
@export var zones: Dictionary[String, String] = {}
## Zones that exist only in debug builds (editor runs, tests): the Milestone C–F test rooms.
## A release build reports them as unknown, so a save made in one is refused there.
@export var debug_zones: Dictionary[String, String] = {}


func has_zone(zone_id: String) -> bool:
	return zones.has(zone_id) or (OS.is_debug_build() and debug_zones.has(zone_id))


## Scene path for `zone_id`, or "" if unknown in this build.
func get_scene_path(zone_id: String) -> String:
	if zones.has(zone_id):
		return zones[zone_id]
	if OS.is_debug_build() and debug_zones.has(zone_id):
		return debug_zones[zone_id]
	return ""


## All zone IDs available in this build (shipping zones first).
func get_zone_ids() -> Array[String]:
	var ids: Array[String] = []
	ids.assign(zones.keys())
	if OS.is_debug_build():
		for id in debug_zones.keys():
			ids.append(id)
	return ids


func is_debug_zone(zone_id: String) -> bool:
	return debug_zones.has(zone_id) and not zones.has(zone_id)

extends Node

## In-memory state that must outlive zone changes. Registered as the `GameState` autoload.
## Does no file I/O; SaveService reads and restores it.

## Stable IDs of collected pickups / used-up persistent objects. Used as a set (values are always true).
var _collected_ids: Dictionary[String, bool] = {}


func mark_collected(id: String) -> void:
	if id.is_empty():
		push_error("GameState.mark_collected() called with an empty id.")
		return
	_collected_ids[id] = true


func is_collected(id: String) -> bool:
	return _collected_ids.has(id)


func get_collected_ids() -> PackedStringArray:
	return PackedStringArray(_collected_ids.keys())


## Replaces every collected ID (used when loading a save).
func restore_collected_ids(ids: PackedStringArray) -> void:
	_collected_ids.clear()
	for id in ids:
		mark_collected(id)

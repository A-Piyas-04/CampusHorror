extends Node

## In-memory state that must outlive zone changes. Registered as the `GameState` autoload.
## Nothing here is written to disk yet.

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

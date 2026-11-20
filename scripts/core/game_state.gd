extends Node
## In-memory state that must outlive zone changes. Registered as the `GameState` autoload.
## Does no file I/O; SaveService reads (`to_dict`) and restores (`from_dict`) it.
##
## v2 (Chapter 1 slice): story flags, items, lantern fuel, the current objective and read notes, on top of the
## v1 set of collected IDs.

## A story flag changed (any value: bool, int, String).
signal flag_changed(id: String, value: Variant)
## Items were added or removed.
signal inventory_changed
## The current objective text changed ("" = none).
signal objective_changed(text: String)
## Lantern fuel changed (0..1).
signal fuel_changed(fuel: float)
## A note was read for the first time (id).
signal note_read(id: String)

## Stable IDs of collected pickups / used-up persistent objects. Used as a set (values are always true).
var _collected_ids: Dictionary[String, bool] = {}
var _flags: Dictionary = {}
var _items: Dictionary = {}
var _notes: Array[String] = []
var objective: String = ""
var lantern_fuel: float = 0.6


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


# --- Flags ---------------------------------------------------------------------------------------------

func set_flag(id: String, value: Variant = true) -> void:
	if _flags.get(id) == value:
		return
	_flags[id] = value
	flag_changed.emit(id, value)


func get_flag(id: String, default: Variant = false) -> Variant:
	return _flags.get(id, default)


func has_flag(id: String) -> bool:
	return bool(_flags.get(id, false))


# --- Items ---------------------------------------------------------------------------------------------

func add_item(id: String, count: int = 1) -> void:
	_items[id] = int(_items.get(id, 0)) + count
	inventory_changed.emit()


func remove_item(id: String, count: int = 1) -> bool:
	var have := int(_items.get(id, 0))
	if have < count:
		return false
	if have == count:
		_items.erase(id)
	else:
		_items[id] = have - count
	inventory_changed.emit()
	return true


func has_item(id: String) -> bool:
	return int(_items.get(id, 0)) > 0


func item_count(id: String) -> int:
	return int(_items.get(id, 0))


func get_items() -> Dictionary:
	return _items.duplicate()


# --- Objective, notes, fuel ---------------------------------------------------------------------------------

func set_objective(text: String) -> void:
	if text == objective:
		return
	objective = text
	objective_changed.emit(text)


func mark_note_read(id: String) -> void:
	if not _notes.has(id):
		_notes.append(id)
		note_read.emit(id)


func has_read_note(id: String) -> bool:
	return _notes.has(id)


func get_read_notes() -> Array[String]:
	return _notes.duplicate()


func set_fuel(value: float) -> void:
	var v := clampf(value, 0.0, 1.0)
	if is_equal_approx(v, lantern_fuel):
		return
	lantern_fuel = v
	fuel_changed.emit(v)


# --- Whole state ----------------------------------------------------------------------------------------

## Back to a fresh game (new game).
func reset() -> void:
	_collected_ids.clear()
	_flags.clear()
	_items.clear()
	_notes.clear()
	set_objective("")
	lantern_fuel = 0.6
	fuel_changed.emit(lantern_fuel)
	inventory_changed.emit()


func to_dict() -> Dictionary:
	return {"flags": _flags.duplicate(true), "items": _items.duplicate(), "notes": Array(_notes),
		"objective": objective, "lantern_fuel": lantern_fuel}


## Restores flags, items, notes, objective and fuel (collected IDs are restored separately, v1-compatible).
func from_dict(d: Dictionary) -> void:
	_flags = (d.get("flags", {}) as Dictionary).duplicate(true)
	_items.clear()
	var items: Dictionary = d.get("items", {})
	for k in items:
		_items[String(k)] = int(items[k])
	_notes.clear()
	for n in d.get("notes", []):
		_notes.append(String(n))
	objective = String(d.get("objective", ""))
	lantern_fuel = clampf(float(d.get("lantern_fuel", 0.6)), 0.0, 1.0)
	objective_changed.emit(objective)
	fuel_changed.emit(lantern_fuel)
	inventory_changed.emit()

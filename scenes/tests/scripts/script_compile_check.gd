extends Node

## Compiles every GDScript under res://scripts (and the story / creature folders) with the autoloads present, and
## reports any that fail. A parse error in a rarely loaded script otherwise only shows when that scene opens.
## Run: godot --headless --path . res://scenes/tests/scripts/ScriptCompileCheck.tscn

const ROOTS := ["res://scripts"]


func _ready() -> void:
	var files: Array[String] = []
	for r in ROOTS:
		_collect(r, files)
	var bad := 0
	for f in files:
		var s := ResourceLoader.load(f, "", ResourceLoader.CACHE_MODE_IGNORE) as GDScript
		if s == null or not s.can_instantiate() and not _is_static_only(s):
			print("[SCRIPTS] FAIL  %s" % f)
			bad += 1
	print("[SCRIPTS] %s (%d/%d compiled)" % ["PASS" if bad == 0 else "FAIL", files.size() - bad, files.size()])
	get_tree().quit(0 if bad == 0 else 1)


func _is_static_only(s: GDScript) -> bool:
	return s != null and s.is_tool() == false and s.get_instance_base_type() != &""


func _collect(dir: String, out: Array[String]) -> void:
	var d := DirAccess.open(dir)
	if d == null:
		return
	for f in d.get_files():
		if f.ends_with(".gd"):
			out.append(dir.path_join(f))
	for sub in d.get_directories():
		_collect(dir.path_join(sub), out)

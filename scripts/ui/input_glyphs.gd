class_name InputGlyphs
extends RefCounted

## What an action's button looks like on the device the player is using (roadmap I7). Read live from the
## Input Map, so rebinding changes the prompt automatically. No textures or special fonts: glyphs are drawn by
## GlyphIcon from the dictionary returned here.
##   {kind: "key", text: "E"}
##   {kind: "pad", layout: "xbox" | "playstation" | "nintendo", button: int, text: "A", color: Color, shape: ""}
## `note_event()` (called from the prompt's _input) switches between keyboard and gamepad on real use.

enum Device { KEYBOARD, GAMEPAD }

## The device the player used last (keyboard / mouse or gamepad).
static var device: Device = Device.KEYBOARD
static var pad_index: int = 0

const XBOX := {0: ["A", Color(0.36, 0.72, 0.29)], 1: ["B", Color(0.83, 0.27, 0.24)], 2: ["X", Color(0.25, 0.5, 0.88)],
	3: ["Y", Color(0.92, 0.75, 0.2)], 4: ["View", Color.WHITE], 6: ["Menu", Color.WHITE], 7: ["LS", Color.WHITE],
	8: ["RS", Color.WHITE], 9: ["LB", Color.WHITE], 10: ["RB", Color.WHITE]}
const NINTENDO := {0: "B", 1: "A", 2: "Y", 3: "X"}
## PlayStation face buttons are shapes (drawn by GlyphIcon), with their customary colours.
const PLAYSTATION := {0: ["cross", Color(0.45, 0.6, 0.95)], 1: ["circle", Color(0.9, 0.35, 0.35)],
	2: ["square", Color(0.88, 0.5, 0.75)], 3: ["triangle", Color(0.35, 0.8, 0.65)]}


## Returns true if the device changed.
static func note_event(event: InputEvent) -> bool:
	var before := device
	if event is InputEventKey or event is InputEventMouseButton:
		device = Device.KEYBOARD
	elif event is InputEventJoypadButton:
		device = Device.GAMEPAD
		pad_index = event.device
	elif event is InputEventJoypadMotion and absf((event as InputEventJoypadMotion).axis_value) > 0.5:
		device = Device.GAMEPAD
		pad_index = event.device
	return device != before


static func glyph(action: StringName) -> Dictionary:
	var events := InputMap.action_get_events(action)
	if device == Device.GAMEPAD:
		for e in events:
			if e is InputEventJoypadButton:
				return _pad((e as InputEventJoypadButton).button_index)
	for e in events:
		if e is InputEventKey:
			var k := e as InputEventKey
			var code := k.keycode
			if k.physical_keycode != 0:
				# The label on the player's own keyboard layout for that key position (an AZERTY player sees the
				# key they actually press). The headless display server can't map layouts; use the position's name.
				var headless := DisplayServer.get_name() == "headless"
				code = k.physical_keycode if headless else DisplayServer.keyboard_get_keycode_from_physical(k.physical_keycode)
			return {"kind": "key", "text": OS.get_keycode_string(code)}
	return {"kind": "key", "text": "?"}


static func pad_layout() -> String:
	var n := Input.get_joy_name(pad_index).to_lower()
	if n.contains("ps") or n.contains("dualsense") or n.contains("dualshock") or n.contains("sony") or n.contains("playstation"):
		return "playstation"
	if n.contains("nintendo") or n.contains("switch") or n.contains("pro controller"):
		return "nintendo"
	return "xbox"


static func _pad(button: int) -> Dictionary:
	var layout := pad_layout()
	var g := {"kind": "pad", "layout": layout, "button": button, "text": "", "color": Color.WHITE, "shape": ""}
	if layout == "playstation" and PLAYSTATION.has(button):
		g.shape = PLAYSTATION[button][0]
		g.color = PLAYSTATION[button][1]
	elif layout == "nintendo" and NINTENDO.has(button):
		g.text = NINTENDO[button]
	elif XBOX.has(button):
		g.text = XBOX[button][0]
		g.color = XBOX[button][1]
	else:
		g.text = str(button)
	return g

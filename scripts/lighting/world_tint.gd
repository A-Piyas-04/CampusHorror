extends CanvasModulate

## Time of day (on `Main/DayNightTint`, group "world_tint"): the whole world canvas is tinted by one of five
## phases, and every change eases over `blend_seconds` so the light never snaps.
##   DAWN (cool, soft) -> DAY (neutral) -> GOLDEN (warm, low sun) -> DUSK (blue hour) -> NIGHT (dark blue).
## `darkness` (0 day .. 1 night) is what lights listen to: lamps switch on and the lantern gains strength as it
## rises (Explore mode, D45). In story mode Main sets `is_night` and the zone's own night colour, as before.
## `time_of_day` (T) cycles the phases in Explore mode; `debug_toggle_night` (F2) flips day / night.

signal phase_changed(phase: int, darkness: float)

enum Phase { DAWN, DAY, GOLDEN, DUSK, NIGHT }

const NAMES := ["Dawn", "Day", "Golden hour", "Dusk", "Night"]
## Tint per phase. DAY is a touch warm so daylight never looks clinical; NIGHT is replaced by `night_color`.
const COLORS := [Color(0.80, 0.80, 0.93), Color(1.0, 0.985, 0.955), Color(1.0, 0.86, 0.70),
	Color(0.50, 0.50, 0.70), Color(0.13, 0.15, 0.26)]
const DARKNESS := [0.35, 0.0, 0.12, 0.7, 1.0]

@export var day_color: Color = Color(1.0, 0.985, 0.955)
@export var night_color: Color = Color(0.13, 0.15, 0.26)
@export var blend_seconds: float = 2.5
@export var phase: Phase = Phase.DAY
## Compatibility with the story code and tests: true = NIGHT, false = DAY (applied instantly).
@export var is_night: bool = false:
	set(value):
		is_night = value
		if is_inside_tree() and not _syncing:
			set_phase(Phase.NIGHT if value else Phase.DAY, true)

var darkness := 0.0
var _tween: Tween
var _syncing := false


func _ready() -> void:
	add_to_group("world_tint")
	set_phase(Phase.NIGHT if is_night else phase, true)


func phase_name() -> String:
	return NAMES[phase]


func phase_color(p: Phase) -> Color:
	if p == Phase.NIGHT:
		return night_color
	if p == Phase.DAY:
		return day_color
	return COLORS[p]


## Moves to `p`, easing the tint and darkness unless `instant`.
func set_phase(p: Phase, instant: bool = false) -> void:
	phase = p
	_syncing = true
	is_night = p == Phase.NIGHT
	_syncing = false
	var target_color := phase_color(p)
	var target_dark: float = DARKNESS[p]
	if _tween != null and _tween.is_valid():
		_tween.kill()
	if instant or blend_seconds <= 0.0 or not is_inside_tree():
		color = target_color
		_set_darkness(target_dark)
		return
	_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_tween.tween_property(self, "color", target_color, blend_seconds)
	_tween.tween_method(_set_darkness, darkness, target_dark, blend_seconds)


func next_phase() -> Phase:
	var p := (int(phase) + 1) % NAMES.size() as Phase
	set_phase(p)
	return p


func _set_darkness(v: float) -> void:
	darkness = v
	# lit windows and signs (assets/shaders/night_windows.gdshader) come on from dusk
	RenderingServer.global_shader_parameter_set(&"night_level", smoothstep(0.3, 0.9, v))
	phase_changed.emit(phase, darkness)

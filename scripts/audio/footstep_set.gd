class_name FootstepSet
extends Resource

## Footstep sounds per surface (roadmap I3). Instance: `data/audio/footsteps.tres`.
## Each stream is usually an AudioStreamRandomizer (several takes, random pitch and volume).

## surface -> stream. Surfaces come from SurfaceMap (data/audio/surfaces.tres or a zone profile's default).
@export var streams: Dictionary[StringName, AudioStream] = {}
## surface -> base pitch (asphalt is a concrete take pitched down, for example).
@export var pitch: Dictionary[StringName, float] = {}
## surface -> gain in dB.
@export var gain_db: Dictionary[StringName, float] = {}
## gait (sneak / walk / run) -> gain in dB.
@export var gait_gain_db: Dictionary[StringName, float] = {&"sneak": -10.0, &"walk": 0.0, &"run": 3.0}
## Used when a surface has no entry.
@export var fallback_surface: StringName = &"concrete"


func stream_for(surface: StringName) -> AudioStream:
	return streams.get(surface, streams.get(fallback_surface))


func resolved(surface: StringName) -> StringName:
	return surface if streams.has(surface) else fallback_surface

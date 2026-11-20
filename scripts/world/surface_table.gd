class_name SurfaceTable
extends Resource

## Which footstep surface each ground texture is. Instance: `data/audio/surfaces.tres`.
## Keys are texture file stems (`paved_walkway_tile`), so re-rendering a texture keeps its surface.

@export var by_texture_stem: Dictionary[String, StringName] = {}

class_name NavBuilder
extends RefCounted

## Bakes a navigation mesh for a zone at entry, from its static colliders (walls, buildings, trees, furniture), so
## creatures can path around everything that blocks the player. Takes a few tens of milliseconds; Main runs it
## behind the travel fade, only for zones that have creatures in them.

static func bake(zone: Node2D, bounds: Rect2, agent_radius: float = 13.0) -> NavigationRegion2D:
	var poly := NavigationPolygon.new()
	poly.agent_radius = agent_radius
	poly.parsed_geometry_type = NavigationPolygon.PARSED_GEOMETRY_STATIC_COLLIDERS
	poly.parsed_collision_mask = 1
	poly.source_geometry_mode = NavigationPolygon.SOURCE_GEOMETRY_ROOT_NODE_CHILDREN
	poly.add_outline(PackedVector2Array([bounds.position, Vector2(bounds.end.x, bounds.position.y), bounds.end,
		Vector2(bounds.position.x, bounds.end.y)]))
	var data := NavigationMeshSourceGeometryData2D.new()
	NavigationServer2D.parse_source_geometry_data(poly, data, zone)
	NavigationServer2D.bake_from_source_geometry_data(poly, data)
	var region := NavigationRegion2D.new()
	region.name = "BakedNavigation"
	region.navigation_polygon = poly
	zone.add_child(region)
	print("[NAV] Baked %d polygon(s) for '%s'." % [poly.get_polygon_count(), zone.name])
	return region

"""CDS section: one of the three CDS masses, split into north-south slices for Y-sorting.

Sections (generators/cds_common.py SECTIONS, footprints = the blockout's): `canteen` and
`table_tennis` are the low arcaded block, `indoor_basketball` is the tall hall. The origin is
the section's south face at x = the CDSExterior node; the footprint is x X_WEST..X_EAST,
y 0..depth, so the prop sits on the existing collision rectangles without changing them.

Slices: `slice_bounds_m` cuts the section at pier centres. Slice n gets the objects
S<n>Walls, S<n>Roof, optional S<n>Items (roof dishes) and, for every slice with a neighbour to
the north, S<n>Overlap: a camera-only copy of its roof surface and coping running `overlap_m`
under the neighbour, so the join between two Y-sorted sprites shows no gap. The configs map
slices to the base Sprite and layers; render.occlusion makes every slice sprite keep only the
pixels it really shows.
"""

from generators import cds_common as cds
from pipeline.modeling import extreme_points

COLLECTION_NAME = "CdsSection"

DEFAULT_PARAMS = {
    "section": "indoor_basketball",
    "slice_bounds_m": [],        # internal slice boundaries (section-local y, at pier centres)
    "overlap_m": 0.06,           # seam strip under the northern neighbour (~4 render px of screen depth)
    "overlap_north": False,      # the last slice also runs under the next section to the north
    "dishes_m": [],              # [[x, y], ...] satellite dishes on the roof (section-local)
    "south_bays": 4,             # hall south face: blind-arch bays (not photographed; same as the west face)
    "south_end_m": 0.6,          # hall: corner pier width on the south and west faces
    "west_bays": 9,              # hall west face (photo: 9-10 tall blind arches)
    "canteen_bays": 8,           # canteen arcade (photo: 5-8 arches on the projecting wing)
    "canteen_end_m": 0.45,
    "tt_bays": 5,                # table tennis: 5 open arches, the southernmost is the entrance
    "tt_vents": 6,               # table tennis: plain wall with 6 small square vents (photo)
}


def build(collection, rng, params):
    p = params
    name = p["section"]
    if name not in cds.SECTIONS:
        raise ValueError(f"unknown CDS section {name!r}; choose from {sorted(cds.SECTIONS)}")
    sec = cds.SECTIONS[name]
    depth = sec["depth"]
    bounds = [0.0] + list(p["slice_bounds_m"]) + [depth]
    if any(b1 - b0 < 2.0 for b0, b1 in zip(bounds, bounds[1:])):
        raise ValueError(f"slice_bounds_m {p['slice_bounds_m']} must be increasing and inside 0..{depth:.3f}")
    sl = cds.Slices(bounds, sec["y0"])
    m = cds.materials()

    if sec["kind"] == "hall":
        spec, membrane = cds.HALL, m["hall_roof"]
        openings, info = _hall(sl, m, p, depth)
        south_end, north_end = spec["parapet_depth"], depth - spec["end_depth"]
    else:
        spec, membrane = cds.LOW, m["bitumen"]
        openings, info = _low_block(sl, m, p, name, depth)
        # Canteen and table tennis are one continuous roof: end walls only at the block's two ends.
        south_end = spec["end_depth"] if name == "table_tennis" else 0.0
        north_end = depth - spec["end_depth"] if name == "canteen" else depth

    for b in p["slice_bounds_m"]:
        inside = [o for o in openings if o[0] - 1e-6 < b < o[1] + 1e-6]
        if inside:
            raise ValueError(f"slice boundary {b:.3f} cuts the opening {inside[0]}; put it on a pier")

    # Roof surface and side coping, per slice, between the end walls; seam strips to the north.
    last = len(bounds) - 2
    for i in range(last + 1):
        y0, y1 = max(bounds[i], south_end), min(bounds[i + 1], north_end)
        cds.roof_band(sl.part(i, "roof"), m, y0, y1, spec, membrane)
        if i < last or p["overlap_north"]:
            b = bounds[i + 1]
            cds.roof_band(sl.part(i, "overlap"), m, b, b + p["overlap_m"], spec, membrane, lift=cds.OVERLAP_LIFT)

    for x, y in p["dishes_m"]:
        if any(abs(y - b) < 1.0 for b in p["slice_bounds_m"]):
            raise ValueError(f"dish at y {y} is within 1 m of a slice boundary")
        cds.satellite_dish(sl.part(sl.index(y), "items"), m, x, y, spec["slab_top"])

    objects, slices = sl.finish(collection, cds.mark_seam_overlap)
    return {
        "objects": objects,
        "bounds_points_m": extreme_points(objects),
        "footprint_m": [cds.X_WEST, cds.X_EAST, 0.0, depth],
        "info": dict(info, **{
            "section": name,
            "cds_frame_y0_m": round(sec["y0"], 5),
            "design_size_m": {"width_x": cds.X_EAST - cds.X_WEST, "depth_y": round(depth, 5),
                              "height_z": spec["coping_top"]},
            "heights_m": spec,
            "slice_bounds_m": [round(b, 5) for b in bounds],
            "slice_objects": slices,
            "overlap_m": p["overlap_m"],
            "materials": ["CdsBrick (procedural running bond in the CDS frame)", "CdsCoping", "CdsBitumen",
                          "CdsHallRoof", "CdsDarkRecess", "CdsWindowGlass", "CdsDish", "CdsSteel"],
            "reference": "Docs/map-reference/area1/cds-building.png, cds-building2.png; dimensions estimated, "
                         "footprint = blockout",
        }),
    }


def _hall(sl, m, p, depth):
    spec = cds.HALL
    top, wd, ed, nd = spec["wall_top"], spec["west_depth"], spec["east_depth"], spec["end_depth"]
    pd = spec["parapet_depth"]
    end = p["south_end_m"]

    # South face (the only full facade the game camera sees): blind bays across the full width.
    width = cds.X_EAST - cds.X_WEST
    pitch_s = (width - 2 * end) / p["south_bays"]
    south_open = []
    for k in range(p["south_bays"]):
        centre = cds.X_WEST + end + (k + 0.5) * pitch_s
        south_open.append(cds.blind_bay(sl, m, cds.south_frame, centre, top, wd, 0)[0])
    for a, b in cds.pier_gaps(cds.X_WEST, cds.X_EAST, south_open):
        sl.part(0, "walls").box(a, b, 0.0, wd, 0.0, top, m["brick"])
    sl.part(0, "roof").box(cds.X_WEST, cds.X_EAST, 0.0, pd, top, spec["parapet_top"], m["brick"])
    sl.part(0, "roof").box(cds.X_WEST, cds.X_EAST, 0.0, pd, spec["parapet_top"], spec["coping_top"], m["coping"])

    # West face: blind bays between the south face and the north wall, cut at pier centres.
    pitch_w = (depth - 2 * end) / p["west_bays"]
    west_open = []
    for k in range(p["west_bays"]):
        centre = end + (k + 0.5) * pitch_w
        west_open.append(cds.blind_bay(sl, m, cds.west_frame, centre, top, wd, sl.index(centre))[0])
    for a, b in cds.pier_gaps(wd, depth - nd, west_open):
        sl.box("walls", cds.X_WEST, cds.X_WEST + wd, a, b, 0.0, top, m["brick"])
    cds.parapet_sides(sl, m, pd, depth - nd, spec, top)
    sl.box("walls", cds.X_EAST - ed, cds.X_EAST, wd, depth - nd, 0.0, top, m["brick"])
    cds.end_wall(sl, m, depth - nd, depth, spec)
    return west_open, {
        "south_face": {"bays": p["south_bays"], "pitch_m": round(pitch_s, 4), "observed": False,
                       "note": "not photographed; same blind-arch bay as the west face (default)"},
        "west_face": {"bays": p["west_bays"], "pitch_m": round(pitch_w, 4)},
        "blind_bay": cds.BLIND,
    }


def _low_block(sl, m, p, name, depth):
    spec = cds.LOW
    top, wd, ed, nd = spec["wall_top"], spec["west_depth"], spec["east_depth"], spec["end_depth"]
    arch = cds.ARCADE[name]
    openings, info = [], {"arcade_arch": arch}
    if name == "canteen":
        end = p["canteen_end_m"]
        pitch = (depth - 2 * end) / p["canteen_bays"]
        for k in range(p["canteen_bays"]):
            openings.append(cds.arcade_bay(sl, m, end + (k + 0.5) * pitch, arch, top, wd))
        run_start, run_end = 0.0, depth - nd
        cds.end_wall(sl, m, depth - nd, depth, spec)
        info["arcade"] = {"bays": p["canteen_bays"], "pitch_m": round(pitch, 4)}
    else:
        # The entrance bay faces DoorCdsMainEntry (world y -200 = 200 game px north of the south face).
        entrance = 200.0 / cds.DEPTH_PX_PER_M
        pitch = (depth - entrance) / (p["tt_bays"] - 0.5)
        plain_end = entrance - pitch / 2.0
        for k in range(p["tt_bays"]):
            openings.append(cds.arcade_bay(sl, m, plain_end + (k + 0.5) * pitch, arch, top, wd, sill=k > 0))
        _vent_wall(sl, m, nd, plain_end, top, wd, p["tt_vents"])
        sl.part(sl.index(entrance), "walls").box(cds.X_VERANDA_BACK - 0.02, cds.X_VERANDA_BACK, entrance - 0.8,
                                                 entrance + 0.8, 0.15, 2.45, m["dark"])
        run_start, run_end = plain_end, depth
        cds.end_wall(sl, m, 0.0, nd, spec)
        info["arcade"] = {"bays": p["tt_bays"], "pitch_m": round(pitch, 4), "entrance_bay_centre_m": round(entrance, 4),
                          "plain_wall_m": [nd, round(plain_end, 4)], "vents": p["tt_vents"]}
    for a, b in cds.pier_gaps(run_start, run_end, openings):
        sl.box("walls", cds.X_WEST, cds.X_WEST + wd, a, b, 0.0, top, m["brick"])
    y_lo = nd if name == "table_tennis" else 0.0
    y_hi = depth - nd if name == "canteen" else depth
    sl.box("walls", cds.X_WEST + wd, cds.X_VERANDA_BACK, y_lo, y_hi, 0.0, 0.15, m["coping"])
    sl.box("walls", cds.X_VERANDA_BACK, cds.X_VERANDA_BACK + 0.3, y_lo, y_hi, 0.0, top, m["brick"])
    sl.box("walls", cds.X_EAST - ed, cds.X_EAST, y_lo, y_hi, 0.0, top, m["brick"])
    cds.parapet_sides(sl, m, y_lo, y_hi, spec, top)
    return openings, info


def _vent_wall(sl, m, y0, y1, top, wd, vents):
    """Plain west wall with small square high vents (photo: six, framed, near the top)."""
    x0, x1 = cds.X_WEST, cds.X_WEST + wd
    z0, z1, size = 2.45, 2.95, 0.5
    sl.box("walls", x0, x1, y0, y1, 0.0, z0, m["brick"])
    sl.box("walls", x0, x1, y0, y1, z1, top, m["brick"])
    pitch = (y1 - y0) / vents
    u = y0
    for k in range(vents):
        c = y0 + (k + 0.5) * pitch
        sl.box("walls", x0, x1, u, c - size / 2, z0, z1, m["brick"])
        sl.box("walls", x0 + 0.15, x1, c - size / 2, c + size / 2, z0, z1, m["dark"])
        sl.box("walls", x0, x0 + 0.04, c - size / 2 - 0.06, c - size / 2, z0 - 0.06, z1 + 0.06, m["coping"])
        sl.box("walls", x0, x0 + 0.04, c + size / 2, c + size / 2 + 0.06, z0 - 0.06, z1 + 0.06, m["coping"])
        u = c + size / 2
    sl.box("walls", x0, x1, u, y1, z0, z1, m["brick"])

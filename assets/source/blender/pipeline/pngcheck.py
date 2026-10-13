"""Minimal PNG reader and sprite checks. Plain Python standard library (no bpy, no Pillow)."""

import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"


class PngError(Exception):
    pass


def read_rgba(path):
    """Returns (width, height, header_info, rows) for an 8-bit RGBA, non-interlaced PNG.

    `rows` is a list of bytearrays (4 bytes per pixel), top row first.
    """
    raw = path.read_bytes()
    if raw[:8] != SIGNATURE:
        raise PngError("not a PNG file (bad signature)")
    pos, idat, ihdr = 8, [], None
    while pos < len(raw):
        length, ctype = struct.unpack(">I4s", raw[pos:pos + 8])
        data = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", data)
        elif ctype == b"IDAT":
            idat.append(data)
        elif ctype == b"IEND":
            break
    if ihdr is None:
        raise PngError("missing IHDR")
    width, height, bit_depth, color_type, _, _, interlace = ihdr
    info = {"bit_depth": bit_depth, "png_color_type": color_type, "interlace": interlace,
            "file_bytes": len(raw)}
    if bit_depth != 8 or color_type != 6 or interlace != 0:
        raise PngError(f"expected 8-bit RGBA non-interlaced, got bit depth {bit_depth}, "
                       f"colour type {color_type}, interlace {interlace}")

    data = zlib.decompress(b"".join(idat))
    bpp, stride = 4, width * 4
    rows, prev = [], bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        ftype = data[start]
        cur = bytearray(data[start + 1:start + 1 + stride])
        if ftype == 1:
            for i in range(bpp, stride):
                cur[i] = (cur[i] + cur[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = cur[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pred) & 0xFF
        elif ftype != 0:
            raise PngError(f"bad filter type {ftype} on row {y}")
        rows.append(cur)
        prev = cur
    return width, height, info, rows


def write_rgba(path, width, height, rows):
    """Writes 8-bit RGBA rows (bytearrays, top row first) as a PNG."""
    def chunk(ctype, data):
        return (struct.pack(">I", len(data)) + ctype + data
                + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF))
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    path.write_bytes(SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def keep_columns(path, x_from, x_to):
    """Clears every pixel outside columns [x_from, x_to) to transparent black."""
    width, height, _, rows = read_rgba(path)
    x_from, x_to = max(0, x_from), min(width, x_to)
    for r in rows:
        r[:x_from * 4] = bytes(x_from * 4)
        r[x_to * 4:] = bytes((width - x_to) * 4)
    write_rgba(path, width, height, rows)


def crop(path, x0, y0, width, height):
    """Replaces the PNG with its [x0, x0 + width) x [y0, y0 + height) region."""
    w, h, _, rows = read_rgba(path)
    if x0 < 0 or y0 < 0 or x0 + width > w or y0 + height > h:
        raise PngError(f"crop {x0},{y0} {width}x{height} outside the {w}x{h} image")
    write_rgba(path, width, height, [r[x0 * 4:(x0 + width) * 4] for r in rows[y0:y0 + height]])


def _step(a, b):
    return (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])) / 3.0


def wrap_seam_metrics(path):
    """Seamless-tile check. For each axis: the mean RGB step between neighbouring interior
    columns (rows) and the step across the wrap-around (last column -> first column).
    A visible seam is a wrap step clearly above the interior steps."""
    w, h, _, rows = read_rgba(path)
    px = [[(r[x * 4], r[x * 4 + 1], r[x * 4 + 2]) for x in range(w)] for r in rows]
    result = {}
    for axis in ("x", "y"):
        n = w if axis == "x" else h
        steps = []
        for i in range(n):
            j = (i + 1) % n
            if axis == "x":
                s = sum(_step(px[y][i], px[y][j]) for y in range(h)) / h
            else:
                s = sum(_step(px[i][x], px[j][x]) for x in range(w)) / w
            steps.append(s)
        interior = steps[:-1]
        result[axis] = {
            "interior_mean_step": round(sum(interior) / len(interior), 3),
            "interior_max_step": round(max(interior), 3),
            "wrap_step": round(steps[-1], 3),
        }
    return result


def luma_halves(path):
    """Mean luma (0-255) of the left/right and top/bottom halves: a lighting gradient across
    the tile shows up as a difference between opposite halves."""
    w, h, _, rows = read_rgba(path)

    def luma(r, x):
        return 0.2126 * r[x * 4] + 0.7152 * r[x * 4 + 1] + 0.0722 * r[x * 4 + 2]

    lum = [[luma(r, x) for x in range(w)] for r in rows]
    left = sum(sum(row[:w // 2]) for row in lum) / (h * (w // 2))
    right = sum(sum(row[w - w // 2:]) for row in lum) / (h * (w // 2))
    top = sum(sum(row) for row in lum[:h // 2]) / (w * (h // 2))
    bottom = sum(sum(row) for row in lum[h - h // 2:]) / (w * (h // 2))
    return {"left": round(left, 2), "right": round(right, 2), "top": round(top, 2), "bottom": round(bottom, 2),
            "max_half_difference": round(max(abs(left - right), abs(top - bottom)), 3)}


def border_band_diff(path_a, path_b, band):
    """Mean / max RGB difference between two same-size tiles inside a `band` px frame along all edges."""
    wa, ha, _, ra = read_rgba(path_a)
    wb, hb, _, rb = read_rgba(path_b)
    if (wa, ha) != (wb, hb):
        return {"same_size": False}
    diffs = []
    for y in range(ha):
        for x in range(wa):
            if band <= x < wa - band and band <= y < ha - band:
                continue
            i = x * 4
            diffs.append(_step(ra[y][i:i + 3], rb[y][i:i + 3]))
    return {"same_size": True, "band_px": band, "pixels": len(diffs),
            "mean_rgb_diff": round(sum(diffs) / len(diffs), 3), "max_rgb_diff": round(max(diffs), 3)}


def analyse(path):
    """Size, alpha coverage, content bbox and margins of an RGBA sprite."""
    width, height, info, rows = read_rgba(path)
    min_x, min_y, max_x, max_y = width, height, -1, -1
    opaque = partial = 0
    for y, row in enumerate(rows):
        alpha = row[3::4]
        if not any(alpha):
            continue
        for x, a in enumerate(alpha):
            if a == 0:
                continue
            if a == 255:
                opaque += 1
            else:
                partial += 1
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
        min_y = min(min_y, y)
        max_y = y
    border = max(max(rows[0][3::4]), max(rows[-1][3::4]),
                 max(r[3] for r in rows), max(r[-1] for r in rows))
    has_content = max_x >= 0
    return dict(info, **{
        "size_px": [width, height],
        "opaque_pixels": opaque,
        "partially_transparent_pixels": partial,
        "fully_transparent_pixels": width * height - opaque - partial,
        # Inclusive pixel indices, top-left origin.
        "content_bbox_px": [min_x, min_y, max_x, max_y] if has_content else None,
        "margins_px": {"left": min_x, "right": width - 1 - max_x,
                       "top": min_y, "bottom": height - 1 - max_y} if has_content else None,
        "max_alpha_on_image_border": round(border / 255.0, 4),
    })


def compare(path_a, path_b):
    """Pixel difference between two same-size RGBA PNGs (0-255 scale)."""
    wa, ha, _, ra = read_rgba(path_a)
    wb, hb, _, rb = read_rgba(path_b)
    if (wa, ha) != (wb, hb):
        return {"same_size": False, "size_a": [wa, ha], "size_b": [wb, hb]}
    n = rgb_sum = rgb_max = alpha_max = alpha_diff_px = 0
    for row_a, row_b in zip(ra, rb):
        for i in range(0, len(row_a), 4):
            da = abs(row_a[i + 3] - row_b[i + 3])
            alpha_max = max(alpha_max, da)
            if da > 2:
                alpha_diff_px += 1
            if row_a[i + 3] and row_b[i + 3]:
                d = max(abs(row_a[i] - row_b[i]), abs(row_a[i + 1] - row_b[i + 1]), abs(row_a[i + 2] - row_b[i + 2]))
                rgb_sum += d
                rgb_max = max(rgb_max, d)
                n += 1
    return {
        "same_size": True,
        "mean_rgb_diff": round(rgb_sum / n, 3) if n else None,
        "max_rgb_diff": rgb_max,
        "max_alpha_diff": alpha_max,
        "pixels_alpha_diff_over_2": alpha_diff_px,
    }

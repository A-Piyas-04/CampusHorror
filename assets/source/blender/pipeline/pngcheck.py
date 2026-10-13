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

"""Compositing helpers for layered sprites (Map v2, D46).

A layer that stands behind others in the same asset (a main block behind its wings) is rendered twice: once with
the front layers as holdouts (its exposed surfaces, with the front layers' real shadows on them) and once with the
front layers gone entirely (the surfaces they hide, lit as if open). `png_over` lays the first over the second, so
when a front layer fades over the player (D31) the wall behind it is lit brick, not the black of a face that no
light could reach. Runs inside Blender (bpy images + numpy); renders are 8-bit straight-alpha RGBA.
"""
from pathlib import Path

import bpy
import numpy as np


def _load(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.alpha_mode = "STRAIGHT"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    cs = img.colorspace_settings.name
    bpy.data.images.remove(img)
    return w, h, px.reshape(-1, 4), cs


def save_rgba(path, w, h, px, colorspace="sRGB"):
    img = bpy.data.images.new("_layer_fill", w, h, alpha=True)
    img.alpha_mode = "STRAIGHT"
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.ascontiguousarray(px, dtype=np.float32).ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def png_over(top, bottom, out):
    """out = top over bottom (straight alpha, same size). Returns the share of pixels the bottom filled in."""
    import os
    dbg = os.environ.get("LAYER_FILL_DEBUG")
    if dbg:                                                  # keep both passes for inspection
        import shutil
        shutil.copy(top, Path(dbg) / ("H_" + Path(out).name))
        shutil.copy(bottom, Path(dbg) / ("B_" + Path(out).name))
    w, h, t, cs = _load(top)
    w2, h2, b, _ = _load(bottom)
    if (w, h) != (w2, h2):
        raise RuntimeError(f"png_over: {top} is {w}x{h} but {bottom} is {w2}x{h2}")
    ta, ba = t[:, 3:4], b[:, 3:4]
    oa = ta + ba * (1.0 - ta)
    rgb = (t[:, :3] * ta + b[:, :3] * ba * (1.0 - ta)) / np.maximum(oa, 1e-6)
    rgb = np.where(ta >= 0.999, t[:, :3], rgb)              # exposed pixels stay bit-exact
    save_rgba(Path(out), w, h, np.concatenate([rgb, oa], axis=1), cs)
    return float(np.mean((ba[:, 0] > 0.5) & (ta[:, 0] < 0.5)))

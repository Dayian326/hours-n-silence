"""Chameleon color: pick one usable accent from a piece of artwork.

We quantize the picture to a handful of colors, then choose the most
saturated one that still reads on a near-black background. Very dark or
washed-out art falls back to the default accent.
"""

import colorsys
import os

from PIL import Image

DEFAULT = "#fa586a"
_cache = {}


def _usable(h, s, l):
    return s >= 0.25 and 0.22 <= l <= 0.72


def vibrant_color(image_path):
    if not image_path or not os.path.exists(image_path):
        return DEFAULT
    key = (image_path, os.path.getmtime(image_path))
    if key in _cache:
        return _cache[key]
    try:
        im = Image.open(image_path).convert("RGB")
        im.thumbnail((96, 96))
        q = im.quantize(colors=12, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()[:36]
        counts = sorted(q.getcolors(), reverse=True)   # (count, index)
        best, best_score = None, -1.0
        total = sum(c for c, _ in counts) or 1
        for count, idx in counts:
            r, g, b = pal[idx * 3: idx * 3 + 3]
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            share = count / total
            if not _usable(h, s, l):
                continue
            # saturation first, then how much of the picture it covers
            score = s * 0.7 + min(share, 0.35) * 0.3
            if score > best_score:
                best, best_score = (r, g, b), score
        if best is None:
            color = DEFAULT
        else:
            r, g, b = best
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            # nudge into a range that stays readable as button and slider color
            l = min(max(l, 0.5), 0.66)
            s = min(max(s, 0.55), 0.95)
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    except Exception:
        color = DEFAULT
    _cache[key] = color
    return color

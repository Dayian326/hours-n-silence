"""Chameleon color: pick one usable accent from a piece of artwork.

We quantize the picture to a handful of colors, then choose the most
saturated one that still reads on a near-black background. Very dark or
washed-out art falls back to the default accent.
"""

import colorsys
import os

from PIL import Image

DEFAULT = "#dc6ab0"
_cache = {}


def _usable(h, s, l):
    return s >= 0.25 and 0.22 <= l <= 0.72


def spark_colors(image_path, n=4):
    """A few lively colors from the art, for the beat sparks. Falls back to the accent."""
    if not image_path or not os.path.exists(image_path):
        return [DEFAULT]
    try:
        im = Image.open(image_path).convert("RGB")
        im.thumbnail((96, 96))
        q = im.quantize(colors=10, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()[:30]
        scored = []
        for count, idx in q.getcolors():
            r, g, b = pal[idx * 3: idx * 3 + 3]
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if l < 0.12:
                continue
            l = min(max(l, 0.5), 0.75)
            s = min(max(s, 0.45), 1.0)
            rr, gg, bb = colorsys.hls_to_rgb(h, l, s)
            scored.append((s * 0.6 + count / (96 * 96) * 0.4,
                           f"#{int(rr * 255):02x}{int(gg * 255):02x}{int(bb * 255):02x}"))
        scored.sort(reverse=True)
        colors = [c for _, c in scored[:n]]
        return colors or [DEFAULT]
    except Exception:
        return [DEFAULT]


def _hex(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def cover_palette(image_path):
    """One color per visualizer part, all drawn from the cover.

    The cover's colors are ranked by liveliness, then picked so that each
    part gets a hue at least 25 degrees away from the ones already taken.
    When a cover has fewer distinct hues than parts, the remaining parts get
    lighter or darker versions of what there is, so they still read apart.
    """
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        im = Image.open(image_path).convert("RGB")
        im.thumbnail((96, 96))
        q = im.quantize(colors=12, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()[:36]
        total = 96 * 96
        cands = []
        for count, idx in q.getcolors():
            r, g, b = pal[idx * 3: idx * 3 + 3]
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if l < 0.10 or l > 0.95:
                continue
            cands.append((s * 0.65 + min(count / total, 0.3) * 0.35, h, l, s))
        cands.sort(reverse=True)
        picked = []
        for _, h, l, s in cands:
            if all(min(abs(h - ph), 1 - abs(h - ph)) * 360 >= 25 for ph, _, _ in picked):
                picked.append((h, l, s))
            if len(picked) == 4:
                break
        if not picked:
            return None
        while len(picked) < 4:
            h, l, s = picked[len(picked) % len(picked[:1] or [(0, 0.5, 0.5)])]
            picked.append(((h + 0.5) % 1.0, l, s))     # opposite hue as a stand-in
        (h1, l1, s1), (h2, l2, s2), (h3, l3, s3), (h4, l4, s4) = picked
        return {
            "kick": _hex(h1, min(max(l1, 0.55), 0.72), min(max(s1, 0.6), 1.0)),
            "voice": _hex(h2, min(max(l2, 0.55), 0.72), min(max(s2, 0.55), 1.0)),
            "snare": _hex(h3, min(max(l3, 0.6), 0.75), min(max(s3, 0.5), 1.0)),
            "bass": _hex(h4, min(max(l4, 0.45), 0.6), min(max(s4, 0.5), 1.0)),
            "hats": _hex(h2, 0.9, min(max(s2, 0.3), 0.8)),      # a pale twinkle of the voice hue
        }
    except Exception:
        return None


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

"""Playlist covers.

iTunes keeps the art you drag onto a playlist in its artwork cache, under
"Album Artwork/Custom", one .itc2 file per playlist named after the playlist's
persistent id. The image inside is a plain PNG or JPEG with a header in front
of it, so we find the picture, copy it out, and keep a PNG in artwork_cache/.
Read-only: nothing in the iTunes folder is ever changed.
"""

import glob
import io
import os

from PIL import Image

from .cache import CACHE_DIR

CUSTOM_DIR = os.path.join(os.path.expanduser("~"), "Music", "iTunes", "Album Artwork", "Custom")
SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")

_index = None   # persistent id (16 hex chars) -> .itc2 path


def _build_index():
    global _index
    _index = {}
    for path in glob.glob(os.path.join(CUSTOM_DIR, "**", "*.itc2"), recursive=True):
        name = os.path.basename(path)
        if "-" in name:
            pid = name.split("-", 1)[1].split(".", 1)[0].upper()
            _index[pid] = path


def _largest_image(data):
    best = None
    for sig in SIGNATURES:
        start = 0
        while True:
            i = data.find(sig, start)
            if i < 0:
                break
            try:
                im = Image.open(io.BytesIO(data[i:]))
                im.load()
                if best is None or im.size[0] * im.size[1] > best.size[0] * best.size[1]:
                    best = im
            except Exception:
                pass
            start = i + 1
    return best


def persistent_hex(high, low):
    return f"{high & 0xFFFFFFFF:08X}{low & 0xFFFFFFFF:08X}"


def cover_for(pid_hex, size=600):
    """Path to the playlist's cover PNG, or "" when it has none."""
    if _index is None:
        _build_index()
    src = _index.get(pid_hex.upper())
    if not src:
        return ""
    out = os.path.join(CACHE_DIR, f"playlist_{pid_hex.upper()}.png")
    try:
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
            return out
        im = _largest_image(open(src, "rb").read())
        if im is None:
            return ""
        im = im.convert("RGB")
        im.thumbnail((size, size))
        im.save(out, "PNG", optimize=True)
        return out
    except Exception:
        return ""

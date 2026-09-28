"""Artwork cache: iTunes hands back big BMPs; we keep small PNGs on disk."""

import os

from PIL import Image

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artwork_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def artwork_path_for(db_id):
    return os.path.join(CACHE_DIR, f"{db_id}.png")


def save_artwork(src_path, dest_path, size=512):
    img = Image.open(src_path).convert("RGB")
    img.thumbnail((size, size))
    img.save(dest_path, "PNG", optimize=True)

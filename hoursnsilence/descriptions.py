"""Playlist descriptions.

iTunes' scripting hook does not hand these out. The one place iTunes can
write them is its library XML export, which exists only once "Share iTunes
Library XML with other applications" is ticked in iTunes' preferences
(Edit, Preferences, Advanced). When that file exists, this reads it and
maps each playlist's persistent id to its description. Read-only.
"""

import os
import plistlib

MUSIC_DIR = os.path.join(os.path.expanduser("~"), "Music", "iTunes")
CANDIDATES = ("iTunes Music Library.xml", "iTunes Library.xml")

_cache = {"path": None, "mtime": None, "map": {}}


def xml_path():
    for name in CANDIDATES:
        p = os.path.join(MUSIC_DIR, name)
        if os.path.exists(p):
            return p
    return None


def descriptions():
    """{persistent id (16 hex chars): description} or {} when there is no export."""
    p = xml_path()
    if p is None:
        return {}
    try:
        mtime = os.path.getmtime(p)
        if _cache["path"] == p and _cache["mtime"] == mtime:
            return _cache["map"]
        with open(p, "rb") as f:
            data = plistlib.load(f)
        out = {}
        for pl in data.get("Playlists", []):
            pid = pl.get("Playlist Persistent ID")
            desc = pl.get("Description")
            if pid and isinstance(desc, str) and desc.strip():
                out[str(pid).upper()] = desc.strip()
        _cache.update(path=p, mtime=mtime, map=out)
        return out
    except Exception:
        return {}

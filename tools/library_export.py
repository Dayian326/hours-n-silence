"""DJ step 1: export the library and every playlist's play order.

    python tools/library_export.py

Writes dj/library.json (gitignored): one record per song with the facts
iTunes keeps (genre, year, length, plays, skips, rating, date added, last
played, BPM when tagged, kind) and one record per playlist with its songs in
play order. Read-only; safe to run any time; overwrites the previous export.
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from win32com.client import CastTo, gencache  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "dj")
OUT = os.path.join(OUT_DIR, "library.json")


def track_record(t):
    rec = {"db_id": t.TrackDatabaseID, "name": t.Name, "artist": t.Artist, "album": t.Album,
           "duration": t.Duration, "kind": t.KindAsString}
    for key, attr in (("genre", "Genre"), ("year", "Year"), ("plays", "PlayedCount"), ("skips", "SkippedCount"),
                      ("rating", "Rating"), ("bpm", "BPM"), ("track_number", "TrackNumber"),
                      ("album_artist", "AlbumArtist"), ("compilation", "Compilation")):
        try:
            rec[key] = getattr(t, attr)
        except Exception:
            rec[key] = None
    for key, attr in (("date_added", "DateAdded"), ("last_played", "PlayedDate"), ("last_skipped", "SkippedDate")):
        try:
            v = getattr(t, attr)
            rec[key] = v.strftime("%Y-%m-%d %H:%M") if v and v.year > 1900 else None
        except Exception:
            rec[key] = None
    return rec


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    it = gencache.EnsureDispatch("iTunes.Application")
    t0 = time.time()
    lib = it.LibraryPlaylist.Tracks
    tracks = []
    n = lib.Count
    for i in range(1, n + 1):
        tracks.append(track_record(lib.Item(i)))
        if i % 300 == 0:
            print(f"  songs {i}/{n}", flush=True)
    playlists = []
    pls = it.LibrarySource.Playlists
    for i in range(1, pls.Count + 1):
        p = pls.Item(i)
        if p.Kind != 2 or not p.Visible:
            continue
        up = CastTo(p, "IITUserPlaylist")
        if up.SpecialKind not in (0,):
            continue
        parent = up.Parent
        order = [p.Tracks.ItemByPlayOrder(j).TrackDatabaseID for j in range(1, p.Tracks.Count + 1)]
        playlists.append({"name": p.Name, "folder": parent.Name if parent is not None else None, "songs": order})
    data = {"exported": time.strftime("%Y-%m-%d %H:%M"), "itunes": it.Version, "songs": tracks, "playlists": playlists}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    kinds = {}
    for t in tracks:
        kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
    with_bpm = sum(1 for t in tracks if t.get("bpm"))
    with_genre = sum(1 for t in tracks if t.get("genre"))
    played = sum(1 for t in tracks if (t.get("plays") or 0) > 0)
    print(f"wrote {OUT}")
    print(f"songs {len(tracks)} | playlists {len(playlists)} | {time.time() - t0:.1f}s")
    print(f"with genre {with_genre} | with BPM tag {with_bpm} | ever played {played}")
    print("kinds:", kinds)
    top = sorted(tracks, key=lambda t: -(t.get("plays") or 0))[:5]
    print("most played:", [(t["artist"], t["name"], t["plays"]) for t in top])
    return 0


if __name__ == "__main__":
    sys.exit(main())

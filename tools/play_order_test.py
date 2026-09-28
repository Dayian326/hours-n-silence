"""Positive control for "play from here", shuffle and repeat, through the worker.

    python tools/play_order_test.py

Double-clicking song N in a playlist must make iTunes continue with song
N+1, not go back to whatever it was going to play before. This starts song 8
of a playlist through the worker, presses Next in iTunes, and checks song 9
comes up. Then it flips shuffle and repeat on and off and checks iTunes
reports them. Plays audio briefly, then puts back what was playing.
Run it with iTunes open. It never changes the library.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.coinit_flags = 2
from PyQt6.QtCore import QCoreApplication
from win32com.client import CastTo, gencache

from appleview.itunes_worker import ITunesWorker

PLAYLIST = "hrs n silence pt 6"
N = 8

app = QCoreApplication([])
w = ITunesWorker()
state = {"snap": {}, "playlists": None, "tracks": None, "status": []}
w.snapshot.connect(lambda s: state.__setitem__("snap", s))
w.playlists.connect(lambda p: state.__setitem__("playlists", p))
w.playlist_tracks.connect(lambda pid, t: state.__setitem__("tracks", t))
w.status.connect(lambda s: state["status"].append(s))


def wait_until(pred, timeout, what):
    t0 = time.time()
    while time.time() - t0 < timeout:
        app.processEvents()
        if pred():
            return True
        time.sleep(0.1)
    print("TIMEOUT waiting for", what, "| last status:", state["status"][-3:], flush=True)
    return False


it = gencache.EnsureDispatch("iTunes.Application")
orig = it.CurrentTrack
orig_ids = (orig.sourceID, orig.playlistID, orig.trackID, orig.TrackDatabaseID) if orig else None
orig_pos, orig_playing = it.PlayerPosition, it.PlayerState == 1
print("was playing:", orig.Name if orig else None, "at", orig_pos, "playing:", orig_playing, flush=True)

w.start()
assert wait_until(lambda: state["playlists"] is not None, 30, "playlists")
pl = [p for p in state["playlists"] if p["name"] == PLAYLIST][0]
w.send("load_tracks", pl["db_id"])
assert wait_until(lambda: state["tracks"] is not None, 30, "tracks")
tracks = state["tracks"]
song_n, song_next = tracks[N - 1], tracks[N]
print(f"song {N}: {song_n['name']} | song {N + 1}: {song_next['name']}", flush=True)

ok = True
w.send("play_track", song_n)
if wait_until(lambda: state["snap"].get("db_id") == song_n["db_id"] and state["snap"].get("playing"), 20, "song N playing"):
    it.NextTrack()
    got = wait_until(lambda: state["snap"].get("db_id") == song_next["db_id"], 6, "song N+1 after Next")
    print("NEXT AFTER PLAY-FROM-HERE:", "ok" if got else "FAILED", "| now:", state["snap"].get("name"), flush=True)
    ok &= got
else:
    ok = False

w.send("set_shuffle", True)
got = wait_until(lambda: state["snap"].get("shuffle") is True, 5, "shuffle on")
print("SHUFFLE ON:", "ok" if got else "FAILED", flush=True); ok &= got
w.send("set_shuffle", False)
got = wait_until(lambda: state["snap"].get("shuffle") is False, 5, "shuffle off")
print("SHUFFLE OFF:", "ok" if got else "FAILED", flush=True); ok &= got
w.send("set_repeat", 2)
got = wait_until(lambda: state["snap"].get("repeat") == 2, 5, "repeat all")
print("REPEAT ALL:", "ok" if got else "FAILED", flush=True); ok &= got
w.send("set_repeat", 0)
got = wait_until(lambda: state["snap"].get("repeat") == 0, 5, "repeat off")
print("REPEAT OFF:", "ok" if got else "FAILED", flush=True); ok &= got

if orig_ids:
    CastTo(it.GetITObjectByID(*orig_ids), "IITTrack").Play()
    time.sleep(0.8)
    it.PlayerPosition = orig_pos
    if not orig_playing:
        it.Pause()
    print("restored:", it.CurrentTrack.Name, "at", it.PlayerPosition, "playing:", it.PlayerState == 1, flush=True)
else:
    it.Stop()
w.stop()
w.wait(3000)
print("RESULT:", "PASS" if ok else "FAIL", flush=True)
sys.exit(0 if ok else 1)

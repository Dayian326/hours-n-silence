"""Positive control for the queue handoff, using the worker exactly as the app does.

    python tools/queue_test.py
    python tools/queue_test.py "<song name>" <seconds>   (put that song back first)

It queues two short songs, plays the first, jumps to three seconds before its
end, and checks that the second takes over on its own, then presses Next with
an empty queue and checks iTunes moved on by itself. It plays audio for about
ten seconds and then puts back whatever was playing, at the same position.
Run it with iTunes open. It never changes the library.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
sys.coinit_flags = 2
from PyQt6.QtCore import QCoreApplication
from hoursnsilence.itunes_worker import ITunesWorker

app = QCoreApplication([])
w = ITunesWorker()
state = {"snap": {}, "queue": None, "status": [], "tracks": None}
w.snapshot.connect(lambda s: state.__setitem__("snap", s))
w.queue_changed.connect(lambda q: state.__setitem__("queue", q))
w.status.connect(lambda s: state["status"].append(s))
w.playlist_tracks.connect(lambda pid, t: state.__setitem__("tracks", t))
w.playlists.connect(lambda pls: w.send("load_tracks", [p for p in pls if p["music"]][0]["db_id"]))

def wait_until(pred, timeout, what):
    t0 = time.time()
    while time.time() - t0 < timeout:
        app.processEvents()
        if pred():
            return True
        time.sleep(0.1)
    print("TIMEOUT waiting for", what, "| last status:", state["status"][-3:], flush=True)
    return False

w.start()
assert wait_until(lambda: state["tracks"] is not None, 30, "Music tracks")
tracks = state["tracks"]
print("Music tracks loaded:", len(tracks), flush=True)

# remember what was playing so we can put it back
from win32com.client import gencache, CastTo
it = gencache.EnsureDispatch("iTunes.Application")
if len(sys.argv) > 2:
    # a previous run left the wrong song on; put the named one back first
    want = [t for t in tracks if t["name"] == sys.argv[1]][0]
    CastTo(it.GetITObjectByID(want["source_id"], want["playlist_id"], want["track_id"], want["db_id"]), "IITTrack").Play()
    time.sleep(0.8); it.PlayerPosition = int(sys.argv[2])
    print("put back:", want["name"], "at", sys.argv[2], flush=True)
orig = it.CurrentTrack
orig_pos = it.PlayerPosition
orig_playing = it.PlayerState == 1
orig_ids = (orig.sourceID, orig.playlistID, orig.trackID, orig.TrackDatabaseID) if orig else None
print("was playing:", orig.Name if orig else None, "at", orig_pos, "playing:", orig_playing, flush=True)

# pick two short songs that are not the current one
cands = [t for t in tracks if 60 < t["duration"] < 240 and t["db_id"] != (orig.TrackDatabaseID if orig else None)]
a, b = cands[0], cands[1]
print("queue:", a["artist"], "-", a["name"], "|", b["artist"], "-", b["name"], flush=True)
w.send("enqueue", a); w.send("enqueue", b)
assert wait_until(lambda: state["queue"] is not None and len(state["queue"]) == 2, 5, "queue of 2")
w.send("play_queue")
assert wait_until(lambda: state["snap"].get("db_id") == a["db_id"] and state["snap"].get("playing"), 10, "first queued song playing")
print("first queued song is playing; queue left:", len(state["queue"]), flush=True)
assert len(state["queue"]) == 1

# jump to 3 seconds before the end and watch for the handoff
w.send("seek", int(a["duration"]) - 3)
ok = wait_until(lambda: state["snap"].get("db_id") == b["db_id"] and state["snap"].get("playing"), 10, "handoff to second song")
print("HANDOFF:", "ok" if ok else "FAILED", "| now:", state["snap"].get("artist"), "-", state["snap"].get("name"), "| queue left:", len(state["queue"] or []), flush=True)

# next with an empty queue should fall through to iTunes' own next
w.send("next")
assert wait_until(lambda: state["snap"].get("db_id") not in (a["db_id"], b["db_id"]), 6, "iTunes next")
print("next with empty queue -> iTunes moved to:", state["snap"].get("name"), flush=True)

# put things back
if orig_ids:
    t = CastTo(it.GetITObjectByID(*orig_ids), "IITTrack")
    t.Play(); time.sleep(0.8)
    it.PlayerPosition = orig_pos
    if not orig_playing:
        it.Pause()
    print("restored:", it.CurrentTrack.Name, "at", it.PlayerPosition, "playing:", it.PlayerState == 1, flush=True)
w.stop(); w.wait(3000)
print("RESULT:", "PASS" if ok else "FAIL", flush=True)

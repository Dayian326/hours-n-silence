"""Positive control for the beat meter: listen for six seconds and report.

    python tools/beat_test.py

Starts a song in iTunes if nothing is playing, runs the same listener the
mini player uses, and prints how many beats it heard and the bass levels.
Puts playback back the way it was. It never changes the library.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.coinit_flags = 2
from PyQt6.QtCore import QCoreApplication
from win32com.client import gencache

from appleview.audio import LoopbackMeter

app = QCoreApplication([])
it = gencache.EnsureDispatch("iTunes.Application")
was_playing = it.PlayerState == 1
if not was_playing:
    it.Play()
print("song:", it.CurrentTrack.Name if it.CurrentTrack else None, "| was playing:", was_playing, flush=True)

levels, beats, statuses = [], [], []
m = LoopbackMeter()
m.level.connect(lambda b, a, beat: (levels.append((b, a)), beats.append(time.time()) if beat else None))
m.status.connect(lambda s: (statuses.append(s), print("status:", s, flush=True)))
m.start()
t0 = time.time()
while time.time() - t0 < 8:
    app.processEvents()
    time.sleep(0.02)
m.stop()
m.wait(4000)
if not was_playing:
    it.Pause()
n = len(levels)
if n:
    bass = [b for b, _ in levels]
    print(f"samples: {n} | bass mean {sum(bass)/n:.2f} max {max(bass):.2f} | beats: {len(beats)}", flush=True)
    if len(beats) > 1:
        gaps = [round(b - a, 2) for a, b in zip(beats, beats[1:])]
        print("beat gaps (s):", gaps[:20], flush=True)
ok = n > 50 and len(beats) >= 4
print("RESULT:", "PASS" if ok else "FAIL", flush=True)
sys.exit(0 if ok else 1)

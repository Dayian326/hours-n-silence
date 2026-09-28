"""Positive control for the listener: listen for eight seconds and report what it heard.

    python tools/beat_test.py

Starts a song in iTunes if nothing is playing, runs the same listener the
mini player uses, and prints how many kicks, snares and hi-hat hits it heard and how much voice.
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

feats, statuses = [], []
m = LoopbackMeter()
m.features.connect(lambda f: feats.append(dict(f, t=time.time())))
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
n = len(feats)
kicks = sum(1 for f in feats if f["kick"]); snares = sum(1 for f in feats if f["snare"]); hats = sum(1 for f in feats if f["hats"])
if n:
    voice = [f["voice"] for f in feats]; bass = [f["bass"] for f in feats]
    print(f"samples: {n} | kicks {kicks} | snares {snares} | hats {hats} | voice mean {sum(voice)/n:.2f} max {max(voice):.2f} | bass mean {sum(bass)/n:.2f}", flush=True)
ok = n > 50 and kicks >= 4
print("RESULT:", "PASS" if ok else "FAIL", flush=True)
sys.exit(0 if ok else 1)

"""Listens to what is coming out of the speakers and picks the song apart.

Windows can hand a program a copy of any output device's sound (a
"loopback"). Virtual devices such as Sonar's channels do not produce one,
so we try every output and keep the first that actually delivers samples,
which on a Sonar rig is the physical headset or speakers carrying the final
mix. Nothing is recorded or kept; each chunk is measured and dropped.

What we measure, each about 50 times a second:
  kick   - a hit in the low end (40-120 Hz), the beat
  bass   - how much low end is there right now (40-200 Hz), sustained
  snare  - a hit that is both a mid thump (150-400 Hz) and a burst of
           noise (2-5 kHz), the clap or snare
  voice  - center-panned energy in the voice range (200-4000 Hz): what is
           in the middle of the stereo picture and not at the sides.
           Vocals live there; so do lead melodies, so read it as
           "voice or lead"
  hats   - a hit in the top end (8-16 kHz), hi-hats and sparkle
  loud   - overall loudness against the recent average
"""

import time

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

FRAMES = 1024
MAX_RATE = 50       # features per second handed to the UI, at most


class _Onset:
    """Was this louder than lately? With a short refractory so one hit is one hit."""

    def __init__(self, ratio, floor, refractory):
        self.avg = 0.0
        self.ratio = ratio
        self.floor = floor
        self.refractory = refractory
        self.last = 0.0

    def feed(self, value, now):
        hit = value > max(self.avg * self.ratio, self.floor) and now - self.last > self.refractory
        self.avg = self.avg * 0.9 + value * 0.1
        if hit:
            self.last = now
        level = min(1.0, value / (self.avg * 2.0 + 1e-6)) if self.avg > 0 else 0.0
        return hit, level


class LoopbackMeter(QThread):
    features = pyqtSignal(dict)
    status = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            import pyaudiowpatch as pyaudio
        except Exception:
            self.status.emit("Visualizer: audio library missing")
            return
        pa = pyaudio.PyAudio()
        try:
            while not self._stop:
                device = self._pick_device(pa)
                if device is None:
                    self.status.emit("Visualizer: no output device is producing sound")
                    self._sleep(3.0)
                    continue
                self.status.emit(f"Visualizer listening on {device['name']}")
                self._listen(pa, device)
        finally:
            pa.terminate()

    def _sleep(self, seconds):
        t0 = time.time()
        while not self._stop and time.time() - t0 < seconds:
            time.sleep(0.1)

    def _pick_device(self, pa):
        """The first loopback that delivers samples within a second."""
        import pyaudiowpatch as pyaudio
        for d in pa.get_loopback_device_info_generator():
            if self._stop:
                return None
            try:
                s = pa.open(format=pyaudio.paFloat32, channels=d["maxInputChannels"],
                            rate=int(d["defaultSampleRate"]), input=True,
                            input_device_index=d["index"], frames_per_buffer=FRAMES)
                t0 = time.time()
                ok = False
                while time.time() - t0 < 1.0:
                    if s.get_read_available() >= FRAMES:
                        ok = True
                        break
                    time.sleep(0.02)
                s.close()
                if ok:
                    return d
            except Exception:
                continue
        return None

    def _listen(self, pa, d):
        import pyaudiowpatch as pyaudio
        rate = int(d["defaultSampleRate"])
        ch = d["maxInputChannels"]
        stream = pa.open(format=pyaudio.paFloat32, channels=ch, rate=rate, input=True,
                         input_device_index=d["index"], frames_per_buffer=FRAMES)
        window = np.hanning(FRAMES).astype(np.float32)
        freqs = np.fft.rfftfreq(FRAMES, 1 / rate)
        band = lambda lo, hi: (freqs >= lo) & (freqs < hi)       # noqa: E731
        b_kick, b_bass, b_snare_lo, b_snare_hi = band(40, 120), band(40, 200), band(150, 400), band(2000, 5000)
        b_voice, b_hats = band(200, 4000), band(8000, 16000)
        kick, snare, hats = _Onset(1.35, 0.02, 0.12), _Onset(1.6, 0.01, 0.10), _Onset(1.5, 0.004, 0.06)
        avg_loud = avg_bass = avg_voice = 0.0
        silent_since = None
        last_emit = 0.0
        min_gap = 1.0 / MAX_RATE
        try:
            while not self._stop:
                if stream.get_read_available() < FRAMES:
                    time.sleep(0.004)
                    continue
                raw = np.frombuffer(stream.read(FRAMES, exception_on_overflow=False), dtype=np.float32)
                frames = raw.reshape(-1, ch) if ch > 1 else raw.reshape(-1, 1)
                left = frames[:, 0]
                right = frames[:, 1] if ch > 1 else left
                mid = (left + right) * 0.5
                side = (left - right) * 0.5
                now = time.time()
                rms = float(np.sqrt(np.mean(mid ** 2)))
                spec = np.abs(np.fft.rfft(mid * window))
                side_spec = np.abs(np.fft.rfft(side * window)) if ch > 1 else spec * 0.0

                k_hit, k_lvl = kick.feed(float(spec[b_kick].mean()), now)
                s_hit, s_lvl = snare.feed(float(spec[b_snare_lo].mean()) * float(spec[b_snare_hi].mean()) ** 0.5, now)
                h_hit, h_lvl = hats.feed(float(spec[b_hats].mean()), now)

                bass_now = float(spec[b_bass].mean())
                avg_bass = avg_bass * 0.95 + bass_now * 0.05
                bass = min(1.0, bass_now / (avg_bass * 1.8 + 1e-6)) if avg_bass > 0 else 0.0

                v_mid = float(spec[b_voice].mean())
                v_side = float(side_spec[b_voice].mean())
                center = max(0.0, v_mid - v_side * 1.2)          # what sits in the middle only
                avg_voice = avg_voice * 0.95 + center * 0.05
                voice = min(1.0, center / (avg_voice * 1.6 + 1e-6)) if avg_voice > 0 else 0.0
                if rms < 1e-4:
                    voice = 0.0

                avg_loud = avg_loud * 0.95 + rms * 0.05
                loud = min(1.0, rms / (avg_loud * 1.8 + 1e-6)) if avg_loud > 0 else 0.0

                if now - last_emit >= min_gap or k_hit or s_hit:
                    last_emit = now
                    self.features.emit({
                        "kick": k_hit, "kick_level": k_lvl, "bass": bass,
                        "snare": s_hit, "snare_level": s_lvl,
                        "voice": voice, "hats": h_hit, "hats_level": h_lvl, "loud": loud,
                    })
                if rms < 1e-5:
                    silent_since = silent_since or now
                    if now - silent_since > 20:
                        return          # sound may have moved to another device; re-pick
                else:
                    silent_since = None
        finally:
            stream.close()

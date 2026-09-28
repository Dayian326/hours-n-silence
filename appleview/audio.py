"""Listens to what is coming out of the speakers and turns it into beat energy.

Windows can hand a program a copy of any output device's sound (a
"loopback"). Virtual devices such as Sonar's channels do not produce one,
so we try every output and keep the first that actually delivers samples,
which on a Sonar rig is the physical headset or speakers carrying the final
mix. Nothing is recorded or kept; each chunk is measured and dropped.
"""

import time

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

FRAMES = 1024


class LoopbackMeter(QThread):
    level = pyqtSignal(float, float, bool)   # (bass 0..1, overall 0..1, beat just hit)
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
            self.status.emit("Beat meter: audio library missing")
            return
        pa = pyaudio.PyAudio()
        try:
            while not self._stop:
                device = self._pick_device(pa)
                if device is None:
                    self.status.emit("Beat meter: no output device is producing sound")
                    self._sleep(3.0)
                    continue
                self.status.emit(f"Beat meter listening on {device['name']}")
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
        window = np.hanning(FRAMES)
        freqs = np.fft.rfftfreq(FRAMES, 1 / rate)
        bass_bins = (freqs >= 40) & (freqs < 160)
        avg_bass = 0.0
        avg_all = 0.0
        last_beat = 0.0
        silent_since = None
        try:
            while not self._stop:
                if stream.get_read_available() < FRAMES:
                    time.sleep(0.005)
                    continue
                raw = np.frombuffer(stream.read(FRAMES, exception_on_overflow=False), dtype=np.float32)
                mono = raw.reshape(-1, ch).mean(axis=1) if ch > 1 else raw
                rms = float(np.sqrt(np.mean(mono ** 2)))
                spec = np.abs(np.fft.rfft(mono * window))
                bass = float(spec[bass_bins].mean())
                # slow averages so a beat is "louder than lately", not "loud"
                avg_bass = avg_bass * 0.92 + bass * 0.08
                avg_all = avg_all * 0.95 + rms * 0.05
                now = time.time()
                beat = bass > max(avg_bass * 1.35, 0.02) and now - last_beat > 0.12
                if beat:
                    last_beat = now
                b = min(1.0, bass / (avg_bass * 2.2 + 1e-6)) if avg_bass > 0 else 0.0
                a = min(1.0, rms / (avg_all * 2.0 + 1e-6)) if avg_all > 0 else 0.0
                self.level.emit(b, a, beat)
                # device went quiet for a long while: maybe sound moved elsewhere
                if rms < 1e-5:
                    silent_since = silent_since or now
                    if now - silent_since > 20:
                        return
                else:
                    silent_since = None
        finally:
            stream.close()

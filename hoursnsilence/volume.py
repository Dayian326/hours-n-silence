"""Watches the Windows volume of every output device so the popup reacts to
the knob no matter which device it is turning (Sonar channels, the headset,
the monitor, all of them)."""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class VolumeWatcher(QObject):
    changed = pyqtSignal(int, str)   # new volume 0-100, device name

    def __init__(self, parent=None, interval_ms=100, rescan_ms=10000):
        super().__init__(parent)
        self._devices = []     # [(name, endpoint volume)]
        self._last = {}        # name -> percent
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)
        self._rescan = QTimer(self)
        self._rescan.setInterval(rescan_ms)
        self._rescan.timeout.connect(self._scan)

    def start(self):
        self._scan()
        self._timer.start()
        self._rescan.start()

    def device_names(self):
        return [n for n, _ in self._devices]

    def _scan(self):
        found = []
        try:
            from pycaw.pycaw import AudioUtilities
            for d in AudioUtilities.GetAllDevices():
                try:
                    state = getattr(d, "state", None)
                    if state is not None and int(state) != 1:      # 1 = active
                        continue
                    ev = d.EndpointVolume
                    if ev is None:
                        continue
                    ev.GetMasterVolumeLevelScalar()                # proves we can read it
                    found.append((d.FriendlyName or "device", ev))
                except Exception:
                    continue
            if not found:
                spk = AudioUtilities.GetSpeakers()
                found.append((getattr(spk, "FriendlyName", "Speakers"), spk.EndpointVolume))
        except Exception:
            pass
        self._devices = found

    def _tick(self):
        for name, ev in self._devices:
            try:
                v = round(ev.GetMasterVolumeLevelScalar() * 100)
            except Exception:
                continue
            last = self._last.get(name)
            self._last[name] = v
            if last is not None and v != last:
                self.changed.emit(v, name)

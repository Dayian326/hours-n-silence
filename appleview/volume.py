"""Watches the Windows master volume so the popup can react to the knob."""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class VolumeWatcher(QObject):
    changed = pyqtSignal(int)   # new master volume, 0-100

    def __init__(self, parent=None, interval_ms=100):
        super().__init__(parent)
        self._last = None
        self._endpoint = None
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)

    def start(self):
        try:
            from pycaw.pycaw import AudioUtilities
            self._endpoint = AudioUtilities.GetSpeakers().EndpointVolume
        except Exception:
            self._endpoint = None
        self._timer.start()

    def current(self):
        if self._endpoint is None:
            return None
        try:
            return round(self._endpoint.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            return None

    def _tick(self):
        v = self.current()
        if v is None:
            return
        if self._last is None:
            self._last = v
            return
        if v != self._last:
            self._last = v
            self.changed.emit(v)

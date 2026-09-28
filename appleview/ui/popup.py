"""The corner card that appears when the volume changes or a song starts.

It never takes focus, so typing is not interrupted. It fades out on its own.
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from .theme import BORDER, accent
from .widgets import ArtLabel

SHOW_MS = 3000
MARGIN = 18


class NowPlayingPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 104)

        card = QWidget(self)
        card.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)  # card edge = window edge
        outer.addWidget(card)

        row = QHBoxLayout(card)
        row.setContentsMargins(14, 12, 16, 12)
        row.setSpacing(14)
        self.art = ArtLabel(72, 10)
        row.addWidget(self.art)

        col = QVBoxLayout()
        col.setSpacing(3)
        self.title = QLabel("Nothing playing")
        self.title.setObjectName("title")
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("subtitle")
        self.line = QLabel("")
        self.line.setObjectName("status")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)
        self.apply_accent()
        col.addWidget(self.title)
        col.addWidget(self.subtitle)
        col.addStretch(1)
        col.addWidget(self.line)
        col.addWidget(self.bar)
        row.addLayout(col, 1)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)
        self._anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._after_anim)
        self._fading_out = False

        self._snap = {}
        self._art_path = ""

    def apply_accent(self):
        self.bar.setStyleSheet(
            f"QProgressBar {{ background: {BORDER}; border: none; border-radius: 2px; }}"
            f"QProgressBar::chunk {{ background: {accent()}; border-radius: 2px; }}"
        )

    # ---- data ----
    def update_snapshot(self, snap):
        self._snap = snap
        self.title.setText(snap.get("name") or "Nothing playing")
        artist = snap.get("artist") or ""
        album = snap.get("album") or ""
        self.subtitle.setText(f"{artist}  -  {album}" if artist and album else artist or album)
        if not snap.get("connected", True):
            self.title.setText("iTunes is not running")
            self.subtitle.setText("")

    def set_art(self, path):
        self._art_path = path
        self.art.set_art(path)

    # ---- showing ----
    def show_volume(self, percent):
        self.line.setText(f"Volume {percent}")
        self.bar.setValue(int(percent))
        self.bar.show()
        self._pop()

    def show_track(self):
        self.line.setText("Now playing" if self._snap.get("playing") else "Paused")
        self.bar.hide()
        self._pop()

    def _pop(self):
        self._place()
        self._fading_out = False
        self._anim.stop()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        else:
            self.setWindowOpacity(1.0)
        self._hide_timer.start(SHOW_MS)

    def _place(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - MARGIN, screen.bottom() - self.height() - MARGIN)

    def _fade_out(self):
        self._fading_out = True
        self._anim.stop()
        self._anim.setStartValue(self.windowOpacity())
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _after_anim(self):
        if self._fading_out:
            self.hide()
            self._fading_out = False

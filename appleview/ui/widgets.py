"""Small shared pieces: rounded artwork, icon buttons, the transport row."""

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStyle, QWidget

from .theme import ACCENT, BORDER, PANEL_2, TEXT


class ArtLabel(QLabel):
    """Album art with rounded corners. Shows a soft placeholder when empty."""

    def __init__(self, size=56, radius=8, parent=None):
        super().__init__(parent)
        self._size = size
        self._radius = radius
        self._pix = None
        self.setFixedSize(size, size)
        self.set_art("")

    def set_art(self, path):
        pix = QPixmap(path) if path else QPixmap()
        if pix.isNull():
            pix = QPixmap(self._size, self._size)
            pix.fill(QColor(PANEL_2))
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QColor(BORDER))
            p.setBrush(QColor(BORDER))
            r = self._size * 0.28
            p.drawEllipse(QRectF(self._size / 2 - r, self._size / 2 - r, 2 * r, 2 * r))
            p.setBrush(QColor(PANEL_2))
            r2 = r * 0.35
            p.drawEllipse(QRectF(self._size / 2 - r2, self._size / 2 - r2, 2 * r2, 2 * r2))
            p.end()
        else:
            pix = pix.scaled(self._size, self._size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                             Qt.TransformationMode.SmoothTransformation)
        rounded = QPixmap(self._size, self._size)
        rounded.fill(Qt.GlobalColor.transparent)
        p = QPainter(rounded)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self._size, self._size), self._radius, self._radius)
        p.setClipPath(path)
        p.drawPixmap(0, 0, pix)
        p.end()
        self._pix = rounded
        self.setPixmap(rounded)


def std_icon(widget, name):
    return widget.style().standardIcon(getattr(QStyle.StandardPixmap, name))


def tinted_icon(widget, name, color=TEXT, size=20):
    """Standard Qt media icons come out grey; recolor them for the dark theme."""
    base = std_icon(widget, name).pixmap(QSize(size, size))
    out = QPixmap(base.size())
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.drawPixmap(0, 0, base)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(out.rect(), QColor(color))
    p.end()
    return QIcon(out)


class IconButton(QPushButton):
    def __init__(self, icon_name, size=32, icon_size=18, tip="", parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._icon_size = icon_size
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.set_icon(icon_name)

    def set_icon(self, icon_name, color=TEXT):
        self._icon_name = icon_name
        self.setIcon(tinted_icon(self, icon_name, color, self._icon_size))
        self.setIconSize(QSize(self._icon_size, self._icon_size))


class Transport(QWidget):
    """Previous / play-pause / next."""

    previous = pyqtSignal()
    play_pause = pyqtSignal()
    next = pyqtSignal()

    def __init__(self, size=32, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.prev_btn = IconButton("SP_MediaSkipBackward", size, tip="Previous")
        self.play_btn = IconButton("SP_MediaPlay", size + 6, size // 2 + 4, tip="Play or pause")
        self.next_btn = IconButton("SP_MediaSkipForward", size, tip="Next")
        for b in (self.prev_btn, self.play_btn, self.next_btn):
            lay.addWidget(b)
        self.prev_btn.clicked.connect(self.previous)
        self.play_btn.clicked.connect(self.play_pause)
        self.next_btn.clicked.connect(self.next)

    def set_playing(self, playing):
        self.play_btn.set_icon("SP_MediaPause" if playing else "SP_MediaPlay", ACCENT if playing else TEXT)

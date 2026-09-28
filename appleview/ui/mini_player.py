"""The small always-on-top card shown when the main window is minimized."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .widgets import ArtLabel, IconButton, Transport


class MiniPlayer(QWidget):
    expand_requested = pyqtSignal()
    previous = pyqtSignal()
    play_pause = pyqtSignal()
    next = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(340, 100)
        self._drag = None

        card = QWidget(self)
        card.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        row = QHBoxLayout(card)
        row.setContentsMargins(12, 10, 10, 10)
        row.setSpacing(12)
        self.art = ArtLabel(76, 10)
        row.addWidget(self.art)

        col = QVBoxLayout()
        col.setSpacing(2)
        top = QHBoxLayout()
        self.title = QLabel("Nothing playing")
        self.title.setObjectName("title")
        self.expand_btn = IconButton("SP_TitleBarNormalButton", 24, 12, tip="Back to full view")
        self.expand_btn.clicked.connect(self.expand_requested)
        top.addWidget(self.title, 1)
        top.addWidget(self.expand_btn)
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("subtitle")
        self.transport = Transport(28)
        self.transport.previous.connect(self.previous)
        self.transport.play_pause.connect(self.play_pause)
        self.transport.next.connect(self.next)
        col.addLayout(top)
        col.addWidget(self.subtitle)
        col.addStretch(1)
        col.addWidget(self.transport, 0, Qt.AlignmentFlag.AlignLeft)
        row.addLayout(col, 1)

    def update_snapshot(self, snap):
        self.title.setText(snap.get("name") or "Nothing playing")
        self.subtitle.setText(snap.get("artist") or "")
        self.transport.set_playing(bool(snap.get("playing")))
        if not snap.get("connected", True):
            self.title.setText("iTunes is not running")

    def set_art(self, path):
        self.art.set_art(path)

    def place_default(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 18, screen.top() + 18)

    # ---- drag anywhere ----
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.expand_requested.emit()

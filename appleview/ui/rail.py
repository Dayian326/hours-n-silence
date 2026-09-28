"""The playlist rail on the left.

Collapsed it is a column of covers. Expanded it shows names and counts too.
Hovering a cover while collapsed shows a small flyout with the name. Recently
played playlists are pinned at the top; everything else is below, folders
grouped.
"""

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from .theme import BORDER, MUTED, PANEL_2, TEXT, accent

COLLAPSED_W = 64
EXPANDED_W = 250
COVER = 40
ROW_H = 50
_pix_cache = {}


def cover_pixmap(path, name, size=COVER, radius=10):
    """Rounded cover, or a tile with the first letter when there is no cover."""
    key = (path or name, size)
    if key in _pix_cache:
        return _pix_cache[key]
    src = QPixmap(path) if path else QPixmap()
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    p.setClipPath(clip)
    if src.isNull():
        p.fillRect(0, 0, size, size, QColor(PANEL_2))
        p.setPen(QColor(MUTED))
        f = QFont()
        f.setPointSize(max(9, size // 3))
        f.setBold(True)
        p.setFont(f)
        p.drawText(out.rect(), Qt.AlignmentFlag.AlignCenter, (name or "?").strip()[:1].upper())
    else:
        p.drawPixmap(0, 0, src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation))
    p.end()
    _pix_cache[key] = out
    return out


class Flyout(QWidget):
    """The name card that appears next to a cover while the rail is collapsed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        card = QFrame(self)
        card.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(card)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(12, 8, 12, 8)
        inner.setSpacing(1)
        self.title = QLabel()
        self.title.setObjectName("title")
        self.sub = QLabel()
        self.sub.setObjectName("subtitle")
        inner.addWidget(self.title)
        inner.addWidget(self.sub)

    def show_for(self, widget, name, sub):
        self.title.setText(name)
        self.sub.setText(sub)
        self.adjustSize()
        pos = widget.mapToGlobal(widget.rect().topRight())
        self.move(pos.x() + 10, pos.y() + (widget.height() - self.height()) // 2)
        self.show()


class RailRow(QWidget):
    clicked = pyqtSignal(object)          # playlist dict
    double_clicked = pyqtSignal(object)
    hovered = pyqtSignal(object, object)  # (row widget or None, playlist dict)

    def __init__(self, playlist, indent=0, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.indent = indent
        self.expanded = False
        self.selected = False
        self.playing = False
        self._hover = False
        self.setFixedHeight(ROW_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def set_expanded(self, on):
        self.expanded = on
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        if self.selected or self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(PANEL_2) if self.selected else QColor(255, 255, 255, 14))
            p.drawRoundedRect(QRectF(4, 2, r.width() - 8, r.height() - 4), 8, 8)
        x = 12 + (self.indent if self.expanded else 0)
        y = (r.height() - COVER) // 2
        pix = cover_pixmap(self.playlist.get("cover", ""), self.playlist["name"])
        p.drawPixmap(x, y, pix)
        if self.playing:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(accent()))
            p.drawEllipse(QRectF(x + COVER - 9, y + COVER - 9, 8, 8))
        if self.expanded:
            p.setPen(QColor(TEXT if not self.playlist.get("folder") else MUTED))
            f = p.font()
            f.setPointSize(10)
            p.setFont(f)
            fm = p.fontMetrics()
            tx = x + COVER + 12
            avail = r.width() - tx - 10
            name = fm.elidedText(self.playlist["name"], Qt.TextElideMode.ElideRight, avail)
            p.drawText(tx, y + 17, name)
            p.setPen(QColor(MUTED))
            f.setPointSize(9)
            p.setFont(f)
            count = self.playlist.get("count", 0)
            p.drawText(tx, y + 34, f"{count} songs" if not self.playlist.get("folder") else "folder")
        p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        self.hovered.emit(self, self.playlist)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        self.hovered.emit(None, self.playlist)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.playlist)

    def mouseDoubleClickEvent(self, e):
        self.double_clicked.emit(self.playlist)


class SectionLabel(QLabel):
    """Section heading. Collapsed it becomes a short divider line instead of words."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._full = text
        self._expanded = True
        self.setObjectName("heading")
        self.setContentsMargins(14, 10, 8, 4)

    def set_expanded(self, on):
        self._expanded = on
        self.setFixedHeight(26 if on else 14)
        super().setText(self._full if on else "")
        self.update()

    def paintEvent(self, e):
        if self._expanded:
            super().paintEvent(e)
            return
        p = QPainter(self)
        p.setPen(QColor(BORDER))
        y = self.height() // 2
        p.drawLine(18, y, self.width() - 18, y)
        p.end()


class PlaylistRail(QFrame):
    playlist_clicked = pyqtSignal(object)
    playlist_double_clicked = pyqtSignal(object)
    expanded_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self._expanded = False
        self._playlists = []
        self._recent_pids = []
        self._rows = []
        self._selected_id = None
        self._playing_id = None
        self._flyout = Flyout()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(12, 0, 8, 4)
        self.toggle = QPushButton("»")
        self.toggle.setObjectName("mode")
        self.toggle.setToolTip("Show playlist names")
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle.setFixedSize(COVER, 30)
        self.toggle.clicked.connect(lambda: self.set_expanded(not self._expanded))
        top.addWidget(self.toggle)
        top.addStretch(1)
        lay.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 0, 0, 0)
        self.body_lay.setSpacing(0)
        self.body_lay.addStretch(1)
        self.scroll.setWidget(self.body)
        lay.addWidget(self.scroll, 1)
        self.set_expanded(False)

    # ---- data ----
    def set_playlists(self, playlists, recent_pids):
        self._playlists = playlists
        self._recent_pids = recent_pids
        self._rebuild()

    def set_recent(self, recent_pids):
        if recent_pids != self._recent_pids:
            self._recent_pids = recent_pids
            self._rebuild()

    def set_selected(self, playlist_id):
        self._selected_id = playlist_id
        for r in self._rows:
            r.selected = r.playlist["db_id"] == playlist_id
            r.update()

    def set_playing(self, playlist_id):
        self._playing_id = playlist_id
        for r in self._rows:
            r.playing = r.playlist["db_id"] == playlist_id
            r.update()

    def _rebuild(self):
        while self.body_lay.count() > 1:
            item = self.body_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows = []
        self._sections = []
        by_pid = {p.get("pid"): p for p in self._playlists if p.get("pid")}
        recent = [by_pid[pid] for pid in self._recent_pids if pid in by_pid]
        if recent:
            self._add_section("RECENT")
            for p in recent:
                self._add_row(p)
        self._add_section("ALL PLAYLISTS")
        children = {}
        for p in self._playlists:
            if p.get("parent"):
                children.setdefault(p["parent"], []).append(p)
        for p in self._playlists:
            if p.get("parent"):
                continue
            self._add_row(p)
            if p.get("folder"):
                for c in children.get(p["db_id"], []):
                    self._add_row(c, indent=12)
        self.set_selected(self._selected_id)
        self.set_playing(self._playing_id)

    def _add_section(self, text):
        s = SectionLabel(text)
        s.set_expanded(self._expanded)
        self.body_lay.insertWidget(self.body_lay.count() - 1, s)
        self._sections.append(s)

    def _add_row(self, playlist, indent=0):
        row = RailRow(playlist, indent)
        row.set_expanded(self._expanded)
        row.clicked.connect(self.playlist_clicked)
        row.double_clicked.connect(self.playlist_double_clicked)
        row.hovered.connect(self._on_hover)
        self.body_lay.insertWidget(self.body_lay.count() - 1, row)
        self._rows.append(row)

    # ---- expand / collapse ----
    def set_expanded(self, on):
        self._expanded = on
        self.setFixedWidth(EXPANDED_W if on else COLLAPSED_W)
        self.toggle.setText("«" if on else "»")
        self.toggle.setToolTip("Hide playlist names" if on else "Show playlist names")
        for r in self._rows:
            r.set_expanded(on)
        for s in getattr(self, "_sections", []):
            s.set_expanded(on)
        self._flyout.hide()
        self.expanded_changed.emit(on)

    def is_expanded(self):
        return self._expanded

    def _on_hover(self, row, playlist):
        if row is None or self._expanded:
            self._flyout.hide()
            return
        if playlist.get("folder"):
            sub = "folder"
        else:
            sub = f'{playlist.get("count", 0)} songs'
        self._flyout.show_for(row, playlist["name"], sub)

    def hideEvent(self, e):
        self._flyout.hide()
        super().hideEvent(e)

    def sizeHint(self):
        return QSize(EXPANDED_W if self._expanded else COLLAPSED_W, 400)

"""The landing page: "<you>'s Library", a shelf for the Hours In Silence
folder, then every playlist as a cover card. Click a card to open it."""

import getpass

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget,
)

from .rail import cover_pixmap
from .theme import MUTED, TEXT

CARD_W, CARD_H = 170, 236
SHELF_W, SHELF_H = 118, 166


def owner_name():
    """Who is logged into Windows, tidied for a title."""
    try:
        name = getpass.getuser().strip()
    except Exception:
        name = ""
    if not name:
        return "Your"
    return name[:1].upper() + name[1:] + ("'" if name.endswith("s") else "'s")


class Card(QWidget):
    clicked = pyqtSignal(object)
    double_clicked = pyqtSignal(object)

    def __init__(self, playlist, cover_size, w, h, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.cover_size = cover_size
        self.setFixedSize(w, h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 26 if self._hover else 14))
        p.drawRoundedRect(QRectF(0, 0, r.width(), r.height()), 12, 12)
        pad = 10
        p.drawPixmap(pad, pad, cover_pixmap(self.playlist.get("cover", ""), self.playlist["name"], self.cover_size, 8))
        f = QFont()
        f.setPointSize(10)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(TEXT))
        fm = p.fontMetrics()
        y = pad + self.cover_size + 18
        p.drawText(pad, y, fm.elidedText(self.playlist["name"], Qt.TextElideMode.ElideRight, r.width() - 2 * pad))
        f.setBold(False)
        f.setPointSize(8)
        p.setFont(f)
        desc = self.playlist.get("description") or ""
        if desc and r.height() - y > 40:
            p.setPen(QColor("#c9c9d1"))
            lines = self._wrap(p.fontMetrics(), desc, r.width() - 2 * pad, 2)
            for i, line in enumerate(lines):
                p.drawText(pad, y + 16 + i * 13, line)
            y += 16 + 13 * len(lines) - 13
        p.setPen(QColor(MUTED))
        p.drawText(pad, r.height() - pad, f'{self.playlist.get("count", 0)} songs')
        p.end()

    @staticmethod
    def _wrap(fm, text, width, max_lines):
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if fm.horizontalAdvance(test) <= width:
                cur = test
            else:
                lines.append(cur)
                cur = w
                if len(lines) == max_lines:
                    break
        if len(lines) < max_lines and cur:
            lines.append(cur)
        if len(lines) == max_lines and len(" ".join(lines)) < len(text):
            lines[-1] = fm.elidedText(lines[-1] + " " + " ".join(words[len(" ".join(lines).split()):]),
                                      Qt.TextElideMode.ElideRight, width)
        return lines

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.playlist)

    def mouseDoubleClickEvent(self, e):
        self.double_clicked.emit(self.playlist)


class HomePage(QWidget):
    open_playlist = pyqtSignal(object)
    play_playlist = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlists = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        outer.addWidget(self.scroll)
        body = QWidget()
        self.scroll.setWidget(body)
        self.lay = QVBoxLayout(body)
        self.lay.setContentsMargins(26, 22, 26, 22)
        self.lay.setSpacing(18)

        head = QHBoxLayout()
        self.title = QLabel(f"{owner_name()} Library")
        self.title.setObjectName("bigtitle")
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("subtitle")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search playlists")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(240)
        self.search.textChanged.connect(self._rebuild)
        head.addWidget(self.title)
        head.addSpacing(12)
        head.addWidget(self.subtitle)
        head.addStretch(1)
        head.addWidget(self.search)
        self.lay.addLayout(head)

        self.sections = QVBoxLayout()
        self.sections.setSpacing(18)
        self.lay.addLayout(self.sections)
        self.lay.addStretch(1)

    def set_playlists(self, playlists):
        self._playlists = playlists
        self._rebuild()

    def _clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear(item.layout())

    def _rebuild(self):
        self._clear(self.sections)
        q = self.search.text().strip().lower()
        real = [p for p in self._playlists if not p.get("folder") and not p.get("music")]
        with_cover = sum(1 for p in real if p.get("cover"))
        self.subtitle.setText(f"{len(real)} playlists, {with_cover} with covers")
        folders = [p for p in self._playlists if p.get("folder")]
        shown_ids = set()
        for folder in folders:
            kids = [p for p in real if p.get("parent") == folder["db_id"] and (not q or q in p["name"].lower())]
            if not kids:
                continue
            shown_ids.update(p["db_id"] for p in kids)
            self._add_heading(folder["name"], f"{len(kids)} parts, played in order")
            # a wrapping shelf: as many per row as fit, never wider than the page
            shelf = QGridLayout()
            shelf.setHorizontalSpacing(12)
            shelf.setVerticalSpacing(12)
            per_row = max(3, (self.width() - 60) // (SHELF_W + 12)) if self.width() > 0 else 8
            for i, p in enumerate(kids):
                shelf.addWidget(self._card(p, 118, SHELF_W, SHELF_H), i // per_row, i % per_row)
            shelf.setColumnStretch(per_row, 1)
            self.sections.addLayout(shelf)
        rest = [p for p in real if p["db_id"] not in shown_ids and (not q or q in p["name"].lower())]
        self._add_heading("All playlists", "")
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        cols = max(3, (self.width() - 60) // (CARD_W + 14)) if self.width() > 0 else 5
        for i, p in enumerate(rest):
            grid.addWidget(self._card(p, 150, CARD_W, CARD_H), i // cols, i % cols)
        grid.setColumnStretch(cols, 1)
        self.sections.addLayout(grid)

    def _add_heading(self, text, note):
        row = QHBoxLayout()
        h = QLabel(text)
        h.setObjectName("title")
        row.addWidget(h)
        if note:
            n = QLabel(note)
            n.setObjectName("subtitle")
            row.addSpacing(8)
            row.addWidget(n)
        row.addStretch(1)
        self.sections.addLayout(row)

    def _card(self, p, cover, w, h):
        c = Card(p, cover, w, h)
        c.clicked.connect(self.open_playlist)
        c.double_clicked.connect(self.play_playlist)
        return c

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._playlists:
            self._rebuild()

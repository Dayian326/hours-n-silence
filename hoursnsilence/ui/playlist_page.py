"""The immersive playlist page: blurred cover behind, a card with the cover,
name and description on the left, the song list on the right."""

from PyQt6.QtCore import QAbstractListModel, QModelIndex, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QLabel, QLineEdit, QListView, QMenu, QPushButton,
    QStyle, QStyledItemDelegate, QVBoxLayout, QWidget,
)

from .backdrop import Backdrop
from .rail import cover_pixmap
from .theme import MUTED, TEXT, accent, fmt_time

ROW_H = 46


class TrackModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks = []
        self.rows = []          # indexes into tracks after the search filter
        self.current_db_id = None

    def set_tracks(self, tracks, query=""):
        self.beginResetModel()
        self.tracks = tracks
        self._filter(query)
        self.endResetModel()

    def set_query(self, query):
        self.beginResetModel()
        self._filter(query)
        self.endResetModel()

    def _filter(self, query):
        q = (query or "").strip().lower()
        self.rows = [
            i for i, t in enumerate(self.tracks)
            if not q or q in (t["name"] or "").lower() or q in (t["artist"] or "").lower()
            or q in (t["album"] or "").lower()
        ]

    def track_at(self, row):
        if 0 <= row < len(self.rows):
            return self.tracks[self.rows[row]]
        return None

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        t = self.track_at(index.row())
        if t is None:
            return None
        if role == Qt.ItemDataRole.UserRole:
            return t
        if role == Qt.ItemDataRole.DisplayRole:
            return t["name"]
        return None

    def set_current(self, db_id):
        if db_id == self.current_db_id:
            return
        self.current_db_id = db_id
        if self.rows:
            self.dataChanged.emit(self.index(0), self.index(len(self.rows) - 1))


class TrackDelegate(QStyledItemDelegate):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), ROW_H)

    def paint(self, painter, option, index):
        t = index.data(Qt.ItemDataRole.UserRole)
        if t is None:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if selected or hover:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 30 if selected else 14))
            painter.drawRoundedRect(r.adjusted(4, 1, -4, -1), 8, 8)
        current = t["db_id"] == self.model.current_db_id
        f = QFont(option.font)
        fm_small = painter.fontMetrics()
        # number
        painter.setPen(QColor(accent() if current else MUTED))
        painter.drawText(QRect(r.left() + 10, r.top(), 30, r.height()),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(t.get("order") or ""))
        # time
        time_text = fmt_time(t["duration"])
        time_w = fm_small.horizontalAdvance(time_text) + 8
        painter.setPen(QColor(MUTED))
        painter.drawText(QRect(r.right() - time_w - 10, r.top(), time_w, r.height()),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, time_text)
        # title and artist
        x = r.left() + 52
        avail = r.right() - time_w - 22 - x
        f.setBold(True)
        f.setPointSize(10)
        painter.setFont(f)
        painter.setPen(QColor(accent() if current else TEXT))
        name = painter.fontMetrics().elidedText(t["name"] or "", Qt.TextElideMode.ElideRight, avail)
        painter.drawText(QRect(x, r.top() + 6, avail, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        f.setBold(False)
        f.setPointSize(9)
        painter.setFont(f)
        painter.setPen(QColor(MUTED))
        sub = f'{t["artist"] or ""}  ·  {t["album"] or ""}'
        sub = painter.fontMetrics().elidedText(sub, Qt.TextElideMode.ElideRight, avail)
        painter.drawText(QRect(x, r.top() + 24, avail, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, sub)
        painter.restore()


class PlaylistPage(QWidget):
    play_playlist = pyqtSignal()
    shuffle_playlist = pyqtSignal()
    queue_all = pyqtSignal()
    play_track = pyqtSignal(object)
    enqueue_track = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlist = None
        self.backdrop = Backdrop(self)
        self.backdrop.lower()

        outer = QHBoxLayout(self)
        outer.setContentsMargins(22, 22, 22, 22)
        outer.setSpacing(20)

        # left card
        self.card = QFrame()
        self.card.setObjectName("glass")
        self.card.setFixedWidth(330)
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(18, 18, 18, 18)
        cl.setSpacing(12)
        self.cover = QLabel()
        self.cover.setFixedSize(294, 294)
        cl.addWidget(self.cover)
        self.title = QLabel("Music")
        self.title.setObjectName("bigtitle")
        self.title.setWordWrap(True)
        cl.addWidget(self.title)
        self.description = QLabel("")
        self.description.setObjectName("description")
        self.description.setWordWrap(True)
        cl.addWidget(self.description)
        self.meta = QLabel("")
        self.meta.setObjectName("subtitle")
        cl.addWidget(self.meta)
        cl.addStretch(1)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("primary")
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self.play_playlist)
        self.shuffle_btn = QPushButton("Shuffle")
        self.shuffle_btn.setObjectName("glassbtn")
        self.shuffle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.shuffle_btn.clicked.connect(self.shuffle_playlist)
        buttons.addWidget(self.play_btn, 1)
        buttons.addWidget(self.shuffle_btn, 1)
        cl.addLayout(buttons)
        self.queue_all_btn = QPushButton("Add all to queue")
        self.queue_all_btn.setObjectName("flat")
        self.queue_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.queue_all_btn.clicked.connect(self.queue_all)
        cl.addWidget(self.queue_all_btn)
        outer.addWidget(self.card)

        # right list
        self.list_panel = QFrame()
        self.list_panel.setObjectName("glass")
        ll = QVBoxLayout(self.list_panel)
        ll.setContentsMargins(10, 12, 10, 10)
        ll.setSpacing(8)
        head = QHBoxLayout()
        head.setContentsMargins(8, 0, 4, 0)
        self.songs_label = QLabel("SONGS")
        self.songs_label.setObjectName("heading")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search this playlist")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(230)
        self.search.textChanged.connect(self._on_search)
        head.addWidget(self.songs_label)
        head.addStretch(1)
        head.addWidget(self.search)
        ll.addLayout(head)
        self.model = TrackModel(self)
        self.view = QListView()
        self.view.setObjectName("tracks")
        self.view.setModel(self.model)
        self.view.setItemDelegate(TrackDelegate(self.model, self.view))
        self.view.setUniformItemSizes(True)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setMouseTracking(True)
        self.view.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.view.doubleClicked.connect(self._on_double)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._menu)
        ll.addWidget(self.view, 1)
        outer.addWidget(self.list_panel, 1)

    # ---- data ----
    def set_playlist(self, playlist, fallback_art=""):
        self._playlist = playlist
        name = playlist["name"] if playlist else "Music"
        self.title.setText(name)
        cover = (playlist or {}).get("cover") or ""
        # no cover of its own (Music, a few playlists): borrow the playing song's art
        self.cover.setPixmap(cover_pixmap(cover or fallback_art, name, 294, 12))
        self.backdrop.set_image(cover or fallback_art)
        if playlist and playlist.get("music"):
            self.description.setText("Everything in your library.")
        elif playlist and playlist.get("description"):
            self.description.setText(playlist["description"])
        else:
            self.description.setText("No description yet.")
        count = (playlist or {}).get("count", 0)
        self.meta.setText(f"{count} songs")
        self.search.clear()

    def set_fallback_art(self, path):
        if self._playlist and not self._playlist.get("cover"):
            self.backdrop.set_image(path)
            self.cover.setPixmap(cover_pixmap(path, self._playlist["name"], 294, 12))

    def set_tracks(self, tracks):
        self.model.set_tracks(tracks, self.search.text())
        self.view.scrollToTop()

    def set_current(self, db_id):
        self.model.set_current(db_id)

    def _on_search(self, text):
        self.model.set_query(text)

    def _on_double(self, index):
        t = self.model.track_at(index.row())
        if t is not None:
            self.play_track.emit(t)

    def _menu(self, pos):
        index = self.view.indexAt(pos)
        t = self.model.track_at(index.row()) if index.isValid() else None
        if t is None:
            return
        menu = QMenu(self)
        a_play = menu.addAction("Play")
        a_queue = menu.addAction("Add to queue")
        chosen = menu.exec(self.view.viewport().mapToGlobal(pos))
        if chosen == a_play:
            self.play_track.emit(t)
        elif chosen == a_queue:
            self.enqueue_track.emit(t)

    def resizeEvent(self, e):
        self.backdrop.setGeometry(self.rect())
        super().resizeEvent(e)

"""The full window: playlists on the left, songs on the right, player bar
below, and a queue panel that slides in on the right."""

import os

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QPushButton, QSplitter, QSystemTrayIcon, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .theme import ACCENT, MUTED, fmt_time
from .widgets import ArtLabel, ClickSlider, IconButton, ModeButton, Transport

REPEAT_OFF, REPEAT_ONE, REPEAT_ALL = 0, 1, 2


ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "assets", "appleview.ico")


def make_app_icon():
    # the same picture the shortcut uses, so the taskbar and the window match
    if os.path.exists(ICON_PATH):
        icon = QIcon(ICON_PATH)
        if not icon.isNull():
            return icon
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(ACCENT))
    p.drawEllipse(4, 4, 56, 56)
    p.setBrush(QColor("#0e0e10"))
    p.drawEllipse(24, 24, 16, 16)
    p.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    # commands out to the worker
    command = pyqtSignal(str, object)      # (name, arg or None)
    minimized_to_mini = pyqtSignal()
    restored = pyqtSignal()                # full window is back; mini player should go
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AppleView")
        self.setWindowIcon(make_app_icon())
        self.resize(1080, 680)
        self._playlists = []
        self._tracks = []           # tracks of the selected playlist
        self._rows = []             # indexes into _tracks after filtering
        self._selected_playlist = None
        self._snap = {}
        self._seeking = False
        self._build()

    # ---- layout ----
    def _build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(12, 12, 12, 10)
        v.setSpacing(10)

        split = QSplitter(Qt.Orientation.Horizontal)
        v.addWidget(split, 1)

        # left: playlists
        left = QWidget()
        left.setObjectName("panel")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 10, 8, 8)
        head = QLabel("PLAYLISTS")
        head.setObjectName("heading")
        lv.addWidget(head)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.itemClicked.connect(self._on_playlist_clicked)
        self.tree.itemDoubleClicked.connect(self._on_playlist_double)
        lv.addWidget(self.tree, 1)
        split.addWidget(left)

        # middle: search + tracks
        mid = QWidget()
        mid.setObjectName("panel")
        mv = QVBoxLayout(mid)
        mv.setContentsMargins(10, 10, 10, 8)
        top = QHBoxLayout()
        self.playlist_title = QLabel("Music")
        self.playlist_title.setObjectName("title")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search this playlist")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refill_table)
        self.play_all_btn = QPushButton("Play playlist")
        self.play_all_btn.setObjectName("primary")
        self.play_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_all_btn.clicked.connect(self._play_selected_playlist)
        self.queue_btn = QPushButton("Queue")
        self.queue_btn.setObjectName("flat")
        self.queue_btn.setCheckable(True)
        self.queue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.queue_btn.toggled.connect(self._toggle_queue)
        top.addWidget(self.playlist_title)
        top.addSpacing(12)
        top.addWidget(self.search, 1)
        top.addWidget(self.play_all_btn)
        top.addWidget(self.queue_btn)
        mv.addLayout(top)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Title", "Artist", "Album", "Time"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 64)
        self.table.cellDoubleClicked.connect(self._on_track_double)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._track_menu)
        mv.addWidget(self.table, 1)
        split.addWidget(mid)

        # right: queue
        self.queue_panel = QWidget()
        self.queue_panel.setObjectName("panel")
        qv = QVBoxLayout(self.queue_panel)
        qv.setContentsMargins(8, 10, 8, 8)
        qh = QHBoxLayout()
        qhead = QLabel("UP NEXT")
        qhead.setObjectName("heading")
        self.queue_play_btn = QPushButton("Play")
        self.queue_play_btn.setObjectName("flat")
        self.queue_play_btn.clicked.connect(lambda: self.command.emit("play_queue", None))
        self.queue_clear_btn = QPushButton("Clear")
        self.queue_clear_btn.setObjectName("flat")
        self.queue_clear_btn.clicked.connect(lambda: self.command.emit("clear_queue", None))
        qh.addWidget(qhead, 1)
        qh.addWidget(self.queue_play_btn)
        qh.addWidget(self.queue_clear_btn)
        qv.addLayout(qh)
        self.queue_list = QListWidget()
        self.queue_list.setToolTip("Double-click a song to remove it from the queue")
        self.queue_list.itemDoubleClicked.connect(self._on_queue_double)
        qv.addWidget(self.queue_list, 1)
        self.queue_hint = QLabel("Right-click a song and choose Add to queue.")
        self.queue_hint.setObjectName("status")
        self.queue_hint.setWordWrap(True)
        qv.addWidget(self.queue_hint)
        split.addWidget(self.queue_panel)
        self.queue_panel.hide()

        split.setSizes([230, 620, 230])
        split.setStretchFactor(1, 1)

        # bottom: player bar
        bar = QWidget()
        bar.setObjectName("panel")
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(12, 10, 12, 10)
        bh.setSpacing(14)
        self.art = ArtLabel(56, 8)
        bh.addWidget(self.art)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.now_title = QLabel("Nothing playing")
        self.now_title.setObjectName("title")
        self.now_sub = QLabel("")
        self.now_sub.setObjectName("subtitle")
        info.addWidget(self.now_title)
        info.addWidget(self.now_sub)
        info_w = QWidget()
        info_w.setLayout(info)
        info_w.setFixedWidth(260)
        bh.addWidget(info_w)

        center = QVBoxLayout()
        center.setSpacing(4)
        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.shuffle_btn = ModeButton("⇄", tip="Shuffle the current playlist")
        self.shuffle_btn.clicked.connect(self._toggle_shuffle)
        self.transport = Transport(32)
        self.transport.previous.connect(lambda: self.command.emit("previous", None))
        self.transport.play_pause.connect(lambda: self.command.emit("play_pause", None))
        self.transport.next.connect(lambda: self.command.emit("next", None))
        self.repeat_btn = ModeButton("⟳", tip="Repeat: off, all, one")
        self.repeat_btn.clicked.connect(self._cycle_repeat)
        controls.addStretch(1)
        controls.addWidget(self.shuffle_btn)
        controls.addWidget(self.transport)
        controls.addWidget(self.repeat_btn)
        controls.addStretch(1)
        center.addLayout(controls)
        seek_row = QHBoxLayout()
        self.pos_label = QLabel("0:00")
        self.pos_label.setObjectName("status")
        self.seek = ClickSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderPressed.connect(self._seek_pressed)
        self.seek.sliderReleased.connect(self._seek_released)
        self._show_remaining = True
        self.dur_label = QPushButton("-0:00")
        self.dur_label.setObjectName("time")
        self.dur_label.setToolTip("Time left. Click to show the song length instead.")
        self.dur_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dur_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dur_label.clicked.connect(self._toggle_time_mode)
        seek_row.addWidget(self.pos_label)
        seek_row.addWidget(self.seek, 1)
        seek_row.addWidget(self.dur_label)
        center.addLayout(seek_row)
        bh.addLayout(center, 1)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(6)
        self.vol_icon = IconButton("SP_MediaVolume", 26, 16, tip="iTunes volume")
        self.vol = ClickSlider(Qt.Orientation.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setFixedWidth(110)
        self.vol.valueChanged.connect(self._on_vol_changed)
        vol_row.addWidget(self.vol_icon)
        vol_row.addWidget(self.vol)
        bh.addLayout(vol_row)

        self.mini_btn = IconButton("SP_TitleBarMinButton", 28, 14, tip="Mini player")
        self.mini_btn.clicked.connect(self.showMinimized)
        bh.addWidget(self.mini_btn)
        v.addWidget(bar)

        # status line
        srow = QHBoxLayout()
        self.status = QLabel("Starting")
        self.status.setObjectName("status")
        self.start_btn = QPushButton("Start iTunes")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(lambda: self.command.emit("launch", None))
        self.start_btn.hide()
        srow.addWidget(self.status, 1)
        srow.addWidget(self.start_btn)
        v.addLayout(srow)

        # tray
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        menu = QMenu(self)
        self._tray_menu = menu
        a_show = QAction("Open AppleView", menu)
        a_show.triggered.connect(self.restore_from_mini)
        a_mini = QAction("Mini player", menu)
        a_mini.triggered.connect(self.showMinimized)
        a_quit = QAction("Quit", menu)
        a_quit.triggered.connect(self.quit_requested)
        menu.addAction(a_show)
        menu.addAction(a_mini)
        menu.addSeparator()
        menu.addAction(a_quit)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("AppleView")
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    # ---- playlists ----
    def set_playlists(self, playlists):
        self._playlists = playlists
        self.tree.clear()
        by_id = {}
        music_item = None
        for p in playlists:
            it = QTreeWidgetItem([p["name"] if p["folder"] else f'{p["name"]}   ({p["count"]})'])
            it.setData(0, Qt.ItemDataRole.UserRole, p["db_id"])
            if p["folder"]:
                it.setForeground(0, QColor(MUTED))
            by_id[p["db_id"]] = it
            if p["music"]:
                music_item = it
        for p in playlists:
            it = by_id[p["db_id"]]
            parent = by_id.get(p["parent"]) if p["parent"] else None
            if parent is not None:
                parent.addChild(it)
            else:
                self.tree.addTopLevelItem(it)
        self.tree.expandAll()
        # keep the playlist that was open (this also runs after iTunes reconnects)
        current = by_id.get(self._selected_playlist) if self._selected_playlist is not None else None
        if current is not None:
            self.tree.setCurrentItem(current)
            self.command.emit("load_tracks", self._selected_playlist)
        elif music_item is not None:
            self.tree.setCurrentItem(music_item)
            self._on_playlist_clicked(music_item, 0)

    def _playlist_of(self, item):
        pid = item.data(0, Qt.ItemDataRole.UserRole)
        for p in self._playlists:
            if p["db_id"] == pid:
                return p
        return None

    def _on_playlist_clicked(self, item, _col):
        p = self._playlist_of(item)
        if p is None or p["folder"]:
            return
        self._selected_playlist = p["db_id"]
        self.playlist_title.setText(p["name"])
        self.search.clear()
        self.command.emit("load_tracks", p["db_id"])

    def _on_playlist_double(self, item, _col):
        p = self._playlist_of(item)
        if p is not None and not p["folder"]:
            self.command.emit("play_playlist", p["db_id"])

    def _play_selected_playlist(self):
        if self._selected_playlist is not None:
            self.command.emit("play_playlist", self._selected_playlist)

    # ---- tracks ----
    def set_tracks(self, playlist_id, tracks):
        if playlist_id != self._selected_playlist:
            return
        self._tracks = tracks
        self._refill_table()

    def _refill_table(self):
        q = self.search.text().strip().lower()
        self._rows = [
            i for i, t in enumerate(self._tracks)
            if not q or q in (t["name"] or "").lower() or q in (t["artist"] or "").lower()
            or q in (t["album"] or "").lower()
        ]
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(self._rows))
        for r, i in enumerate(self._rows):
            t = self._tracks[i]
            cells = (t["name"], t["artist"], t["album"], fmt_time(t["duration"]))
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text or "")
                if c == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    item.setForeground(QColor(MUTED))
                self.table.setItem(r, c, item)
        self.table.setUpdatesEnabled(True)
        self._highlight_current()

    def _track_at_row(self, row):
        if 0 <= row < len(self._rows):
            return self._tracks[self._rows[row]]
        return None

    def _on_track_double(self, row, _col):
        t = self._track_at_row(row)
        if t is not None:
            self.command.emit("play_track", t)

    def _track_menu(self, pos):
        row = self.table.rowAt(pos.y())
        t = self._track_at_row(row)
        if t is None:
            return
        menu = QMenu(self)
        a_play = menu.addAction("Play")
        a_queue = menu.addAction("Add to queue")
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == a_play:
            self.command.emit("play_track", t)
        elif chosen == a_queue:
            self.command.emit("enqueue", t)
            if not self.queue_btn.isChecked():
                self.queue_btn.setChecked(True)

    def _highlight_current(self):
        cur = self._snap.get("db_id")
        for r, i in enumerate(self._rows):
            color = QColor(ACCENT) if self._tracks[i]["db_id"] == cur else None
            for c in range(3):
                item = self.table.item(r, c)
                if item is not None:
                    if color is not None:
                        item.setForeground(color)
                    else:
                        item.setData(Qt.ItemDataRole.ForegroundRole, None)

    # ---- queue ----
    def _toggle_queue(self, on):
        self.queue_panel.setVisible(on)

    def set_queue(self, tracks):
        self.queue_list.clear()
        for t in tracks:
            self.queue_list.addItem(QListWidgetItem(f'{t["name"]}  -  {t["artist"]}'))
        self.queue_hint.setVisible(not tracks)

    def _on_queue_double(self, item):
        self.command.emit("dequeue", self.queue_list.row(item))

    # ---- now playing ----
    def update_snapshot(self, snap):
        prev_id = self._snap.get("db_id")
        self._snap = snap
        if not snap.get("connected", True):
            self.now_title.setText("iTunes is not running")
            self.now_sub.setText("")
            self.start_btn.show()
            self.transport.set_playing(False)
            return
        self.start_btn.hide()
        self.now_title.setText(self._elide(self.now_title, snap.get("name") or "Nothing playing"))
        artist = snap.get("artist") or ""
        album = snap.get("album") or ""
        self.now_sub.setText(self._elide(self.now_sub, f"{artist}  -  {album}" if artist and album else artist or album))
        self.now_title.setToolTip(snap.get("name") or "")
        self.now_sub.setToolTip(f"{artist} - {album}")
        self.transport.set_playing(bool(snap.get("playing")))
        dur = int(snap.get("duration") or 0)
        pos = int(snap.get("position") or 0)
        if not self._seeking:
            self.seek.setRange(0, dur)
            self.seek.setValue(pos)
            self.pos_label.setText(fmt_time(pos))
            self._update_time_label(pos, dur)
        self.shuffle_btn.set_active(bool(snap.get("shuffle")))
        repeat = int(snap.get("repeat") or REPEAT_OFF)
        self.repeat_btn.setText("⟳" if repeat != REPEAT_ONE else "⟳¹")
        self.repeat_btn.set_active(repeat != REPEAT_OFF)
        vol = snap.get("volume")
        if vol is not None and not self.vol.isSliderDown():
            self.vol.blockSignals(True)
            self.vol.setValue(int(vol))
            self.vol.blockSignals(False)
        if snap.get("db_id") != prev_id:
            self._highlight_current()

    def set_art(self, path):
        self.art.set_art(path)

    @staticmethod
    def _elide(label, text):
        """Long titles get a trailing ellipsis instead of running off the edge."""
        width = max(label.width() - 4, 120)
        return label.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, width)

    def set_status(self, text):
        self.status.setText(text)

    def _seek_pressed(self):
        self._seeking = True

    def _seek_released(self):
        self._seeking = False
        self.command.emit("seek", self.seek.value())

    def _update_time_label(self, pos, dur):
        if self._show_remaining:
            self.dur_label.setText("-" + fmt_time(max(dur - pos, 0)))
        else:
            self.dur_label.setText(fmt_time(dur))

    def _toggle_time_mode(self):
        self._show_remaining = not self._show_remaining
        self.dur_label.setToolTip("Time left. Click to show the song length instead." if self._show_remaining
                                  else "Song length. Click to show the time left instead.")
        self._update_time_label(int(self._snap.get("position") or 0), int(self._snap.get("duration") or 0))

    def _toggle_shuffle(self):
        self.command.emit("set_shuffle", not bool(self._snap.get("shuffle")))

    def _cycle_repeat(self):
        current = int(self._snap.get("repeat") or REPEAT_OFF)
        nxt = {REPEAT_OFF: REPEAT_ALL, REPEAT_ALL: REPEAT_ONE, REPEAT_ONE: REPEAT_OFF}[current]
        self.command.emit("set_repeat", nxt)

    def _on_vol_changed(self, value):
        self.command.emit("volume", value)

    # ---- minimize to mini, tray ----
    def changeEvent(self, e):
        if e.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, self._go_mini)
        super().changeEvent(e)

    def _go_mini(self):
        self.hide()
        self.minimized_to_mini.emit()

    def restore_from_mini(self):
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()
        self.restored.emit()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.showMinimized()
            else:
                self.restore_from_mini()

    def closeEvent(self, e):
        # closing the window quits the app; the tray is for minimizing
        self.quit_requested.emit()
        e.accept()

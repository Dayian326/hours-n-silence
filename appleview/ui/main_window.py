"""The full window, v2: playlist rail on the left, the immersive playlist page
in the middle, the queue panel on the right, the player bar below."""

import os

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMenu, QPushButton,
    QSystemTrayIcon, QVBoxLayout, QWidget,
)

from ..state import State
from .playlist_page import PlaylistPage
from .rail import PlaylistRail
from .theme import ACCENT, fmt_time
from .widgets import ArtLabel, ClickSlider, IconButton, ModeButton, Transport

REPEAT_OFF, REPEAT_ONE, REPEAT_ALL = 0, 1, 2
ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "assets", "hours_n_silence.ico")


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
    command = pyqtSignal(str, object)      # (name, arg or None)
    minimized_to_mini = pyqtSignal()
    restored = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hours N Silence")
        self.setWindowIcon(make_app_icon())
        self.resize(1180, 740)
        self.state = State()
        self._playlists = []
        self._by_id = {}
        self._selected_playlist = None
        self._snap = {}
        self._art_path = ""
        self._seeking = False
        self._show_remaining = True
        self._build()

    # ---- layout ----
    def _build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(12, 12, 12, 10)
        v.setSpacing(10)

        middle = QHBoxLayout()
        middle.setSpacing(10)
        v.addLayout(middle, 1)

        self.rail = PlaylistRail()
        self.rail.playlist_clicked.connect(self._on_playlist_clicked)
        self.rail.playlist_double_clicked.connect(self._on_playlist_double)
        self.rail.expanded_changed.connect(self._on_rail_expanded)
        middle.addWidget(self.rail)

        self.page = PlaylistPage()
        self.page.setObjectName("panel")
        self.page.play_playlist.connect(self._play_selected_playlist)
        self.page.shuffle_playlist.connect(self._shuffle_selected_playlist)
        self.page.queue_all.connect(self._queue_all)
        self.page.play_track.connect(lambda t: self.command.emit("play_track", t))
        self.page.enqueue_track.connect(self._enqueue)
        middle.addWidget(self.page, 1)

        # queue panel
        self.queue_panel = QFrame()
        self.queue_panel.setObjectName("panel")
        self.queue_panel.setFixedWidth(240)
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
        middle.addWidget(self.queue_panel)
        self.queue_panel.hide()

        # player bar
        bar = QFrame()
        bar.setObjectName("playerbar")   # a faint accent edge around the player
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
        info_w.setFixedWidth(250)
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

        right = QHBoxLayout()
        right.setSpacing(6)
        self.vol_icon = IconButton("SP_MediaVolume", 26, 16, tip="iTunes volume")
        self.vol = ClickSlider(Qt.Orientation.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setFixedWidth(110)
        self.vol.valueChanged.connect(self._on_vol_changed)
        self.queue_btn = QPushButton("Queue")
        self.queue_btn.setObjectName("flat")
        self.queue_btn.setCheckable(True)
        self.queue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.queue_btn.toggled.connect(self.queue_panel.setVisible)
        self.mini_btn = IconButton("SP_TitleBarMinButton", 28, 14, tip="Mini player")
        self.mini_btn.clicked.connect(self.showMinimized)
        right.addWidget(self.vol_icon)
        right.addWidget(self.vol)
        right.addSpacing(8)
        right.addWidget(self.queue_btn)
        right.addWidget(self.mini_btn)
        bh.addLayout(right)
        v.addWidget(bar)

        srow = QHBoxLayout()
        self.status = QLabel("Starting")
        self.status.setObjectName("status")
        self.start_btn = QPushButton("Start iTunes")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(lambda: self.command.emit("launch", None))
        self.start_btn.hide()
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setObjectName("flat")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_requested)
        srow.addWidget(self.status, 1)
        srow.addWidget(self.settings_btn)
        srow.addWidget(self.start_btn)
        v.addLayout(srow)

        # tray
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        menu = QMenu(self)
        self._tray_menu = menu
        a_show = QAction("Open Hours N Silence", menu)
        a_show.triggered.connect(self.restore_from_mini)
        a_mini = QAction("Mini player", menu)
        a_mini.triggered.connect(self.showMinimized)
        a_settings = QAction("Settings", menu)
        a_settings.triggered.connect(self.settings_requested)
        a_quit = QAction("Quit", menu)
        a_quit.triggered.connect(self.quit_requested)
        menu.addAction(a_show)
        menu.addAction(a_mini)
        menu.addAction(a_settings)
        menu.addSeparator()
        menu.addAction(a_quit)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Hours N Silence")
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

        self.rail.set_expanded(self.state.rail_expanded)

    # ---- playlists ----
    def set_playlists(self, playlists):
        self._playlists = playlists
        self._by_id = {p["db_id"]: p for p in playlists}
        self.rail.set_playlists(playlists, self.state.recent)
        current = self._by_id.get(self._selected_playlist) if self._selected_playlist is not None else None
        if current is None:
            current = next((p for p in playlists if p.get("music")), None)
        if current is not None:
            self._open_playlist(current)

    def _open_playlist(self, p):
        self._selected_playlist = p["db_id"]
        self.rail.set_selected(p["db_id"])
        self.page.set_playlist(p, self._art_path)
        self.command.emit("load_tracks", p["db_id"])

    def _on_playlist_clicked(self, p):
        if p is None or p.get("folder"):
            return
        self._open_playlist(p)

    def _on_playlist_double(self, p):
        if p is not None and not p.get("folder"):
            self.command.emit("play_playlist", p["db_id"])

    def _play_selected_playlist(self):
        if self._selected_playlist is not None:
            self.command.emit("play_playlist", self._selected_playlist)

    def _shuffle_selected_playlist(self):
        if self._selected_playlist is not None:
            self.command.emit("shuffle_playlist", self._selected_playlist)

    def _queue_all(self):
        for t in self.page.model.tracks:
            self.command.emit("enqueue", t)
        if self.page.model.tracks and not self.queue_btn.isChecked():
            self.queue_btn.setChecked(True)

    def _on_rail_expanded(self, on):
        if self.state.rail_expanded != on:
            self.state.rail_expanded = on
            self.state.save()

    # ---- tracks ----
    def set_tracks(self, playlist_id, tracks):
        if playlist_id != self._selected_playlist:
            return
        self.page.set_tracks(tracks)
        self.page.set_current(self._snap.get("db_id"))

    def _enqueue(self, t):
        self.command.emit("enqueue", t)
        if not self.queue_btn.isChecked():
            self.queue_btn.setChecked(True)

    # ---- queue ----
    def set_queue(self, tracks):
        self.queue_list.clear()
        for t in tracks:
            self.queue_list.addItem(QListWidgetItem(f'{t["name"]}  -  {t["artist"]}'))
        self.queue_hint.setVisible(not tracks)

    def _on_queue_double(self, item):
        self.command.emit("dequeue", self.queue_list.row(item))

    # ---- now playing ----
    def update_snapshot(self, snap):
        prev = self._snap
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
        if snap.get("db_id") != prev.get("db_id"):
            self.page.set_current(snap.get("db_id"))
        pl_id = snap.get("playlist_id")
        if pl_id != prev.get("playlist_id"):
            self.rail.set_playing(pl_id)
            p = self._by_id.get(pl_id)
            if p is not None and not p.get("music") and not p.get("folder") and p.get("pid"):
                if self.state.touch_recent(p["pid"]):
                    self.rail.set_recent(self.state.recent)

    def set_art(self, path):
        self._art_path = path
        self.art.set_art(path)
        self.page.set_fallback_art(path)

    def apply_accent(self):
        """The accent changed (chameleon): repaint what draws it by hand."""
        self.transport.set_playing(bool(self._snap.get("playing")))
        self.shuffle_btn.set_active(bool(self._snap.get("shuffle")))
        self.repeat_btn.set_active(int(self._snap.get("repeat") or 0) != REPEAT_OFF)
        self.page.view.viewport().update()
        for r in self.rail._rows:
            r.update()

    @staticmethod
    def _elide(label, text):
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
        self.quit_requested.emit()
        e.accept()

"""Run with:  python -m hoursnsilence"""

import sys

# Qt and the audio library must agree on how COM is set up on the main thread.
sys.coinit_flags = 2  # noqa: E402

from PyQt6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from .audio import LoopbackMeter  # noqa: E402
from .discord_presence import DiscordPresence  # noqa: E402
from .itunes_worker import ITunesWorker  # noqa: E402
from .palette import cover_palette, spark_colors, vibrant_color  # noqa: E402
from .ui.main_window import MainWindow  # noqa: E402
from .ui.mini_player import MiniPlayer  # noqa: E402
from .ui.popup import NowPlayingPopup  # noqa: E402
from .ui.theme import accent, build_qss, set_accent  # noqa: E402
from .volume import VolumeWatcher  # noqa: E402


APP_ID = "Dayian.HoursNSilence"   # taskbar identity; the shortcut carries the same id
SINGLE_INSTANCE_NAME = "HoursNSilence-single-instance"


def _already_running():
    """If a copy is running, tell it to come back to the front and report True."""
    sock = QLocalSocket()
    sock.connectToServer(SINGLE_INSTANCE_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def _claim_taskbar_identity():
    """Without this Windows files the window under python.exe on the taskbar."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


class App:
    def __init__(self, argv, qt=None):
        _claim_taskbar_identity()
        self.qt = qt or QApplication(argv)
        self.qt.setStyle("Fusion")
        self.qt.setStyleSheet(build_qss())
        self.qt.setQuitOnLastWindowClosed(False)
        self.qt.setApplicationName("Hours N Silence")

        self.worker = ITunesWorker()
        self.window = MainWindow()
        self.mini = MiniPlayer()
        self.popup = NowPlayingPopup()
        self.volume = VolumeWatcher()
        self.meter = None            # the beat listener, only alive while the mini player shows
        self.presence = DiscordPresence()
        self.presence.status.connect(self.window.set_status)
        d = self.window.state.discord
        self.presence.configure(d.get("enabled", True), d.get("app_id", ""))

        self._art_path = ""
        self._last_track_id = None

        # worker -> ui
        self.worker.snapshot.connect(self._on_snapshot)
        self.worker.artwork.connect(self._on_artwork)
        self.worker.playlists.connect(self.window.set_playlists)
        self.worker.playlist_tracks.connect(self.window.set_tracks)
        self.worker.queue_changed.connect(self.window.set_queue)
        self.worker.status.connect(self.window.set_status)

        # ui -> worker
        self.window.command.connect(self._command)
        for sig, name in ((self.mini.previous, "previous"), (self.mini.play_pause, "play_pause"),
                          (self.mini.next, "next")):
            sig.connect(lambda _=None, n=name: self.worker.send(n))

        # window modes
        self.window.minimized_to_mini.connect(self._show_mini)
        self.window.restored.connect(self.mini.hide)
        self.mini.expand_requested.connect(self._show_full)
        self.window.quit_requested.connect(self.quit)

        # the knob
        self.volume.changed.connect(self._on_volume)

        # a second launch (taskbar click while the mini player is up) just brings us back
        QLocalServer.removeServer(SINGLE_INSTANCE_NAME)
        self._server = QLocalServer()
        self._server.newConnection.connect(self._on_second_launch)
        self._server.listen(SINGLE_INSTANCE_NAME)

        # the listener follows the mini player
        self.mini.shown.connect(self._start_meter)
        self.mini.hidden.connect(self._stop_meter)
        self.mini.set_viz(self.window.state.viz)
        self.window.settings_requested.connect(self._open_settings)
        self._settings = None

    def _command(self, name, arg):
        if arg is None:
            self.worker.send(name)
        else:
            self.worker.send(name, arg)

    def _on_snapshot(self, snap):
        self.presence.push(snap)
        self.window.update_snapshot(snap)
        self.mini.update_snapshot(snap)
        self.popup.update_snapshot(snap)
        track_id = snap.get("db_id")
        if track_id != self._last_track_id:
            self._last_track_id = track_id
            # a new song started while the full window is out of the way: say so
            if track_id is not None and not self.window.isVisible():
                self.popup.show_track()

    def _on_artwork(self, db_id, path):
        if db_id != self._last_track_id:
            return
        self._art_path = path
        self.window.set_art(path)
        self.mini.set_art(path)
        self.popup.set_art(path)
        self._chameleon(path)
        self.mini.set_cover_colors(spark_colors(path), cover_palette(path))

    def _chameleon(self, art_path):
        """The accent follows the playing song's art."""
        color = vibrant_color(art_path)
        if color == accent():
            return
        set_accent(color)
        self.qt.setStyleSheet(build_qss(color))
        self.window.apply_accent()
        self.popup.apply_accent()
        self.mini.apply_accent()

    def _on_volume(self, percent, device):
        self.popup.show_volume(percent, device)

    def _start_meter(self):
        if self.meter is not None:
            return
        self.meter = LoopbackMeter()
        self.meter.features.connect(self.mini.on_features)
        self.meter.status.connect(self.window.set_status)
        self.meter.start()

    def _open_settings(self):
        from .ui.settings_dialog import SettingsDialog
        if self._settings is not None:
            self._settings.raise_()
            self._settings.activateWindow()
            return
        dlg = SettingsDialog(self.window.state.viz, self.window.state.discord)
        dlg.changed.connect(self._on_viz_changed)
        dlg.discord_changed.connect(self._on_discord_changed)
        dlg.finished.connect(lambda _=None: setattr(self, "_settings", None))
        self._settings = dlg
        dlg.show()

    def _on_discord_changed(self, enabled, app_id):
        self.window.state.set_discord(enabled, app_id)
        self.presence.configure(enabled, app_id)

    def _on_viz_changed(self, viz):
        self.window.state.set_viz(viz)
        self.mini.set_viz(viz)

    def _stop_meter(self):
        if self.meter is None:
            return
        m = self.meter
        self.meter = None
        m.stop()
        m.wait(3000)

    def _show_mini(self):
        # first time: top-right corner; after that, wherever it was dragged to
        if not getattr(self, "_mini_placed", False):
            self.mini.place_default()
            self._mini_placed = True
        self.mini.show()

    def _on_second_launch(self):
        while self._server.hasPendingConnections():
            conn = self._server.nextPendingConnection()
            conn.disconnectFromServer()
        self._show_full()

    def _show_full(self):
        self.window.restore_from_mini()   # emits restored, which hides the mini player

    def run(self):
        from PyQt6.QtCore import Qt
        from .ui.glass import apply_glass
        from .ui.theme import set_glass
        # the frosted glass needs the window to be see-through where panels are not
        self.window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.window.show()
        how = apply_glass(self.window)
        if how == "none":
            # no glass available: go back to solid panels so nothing is see-through
            self.window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            set_glass(False)
            self.qt.setStyleSheet(build_qss())
        else:
            apply_glass(self.mini, frameless=True)
            apply_glass(self.popup, frameless=True)
        self.worker.start()
        self.volume.start()
        self.presence.start()
        code = self.qt.exec()
        self._stop_meter()
        self.presence.stop()
        self.presence.wait(3000)
        self.worker.stop()
        self.worker.wait(2000)
        return code

    def quit(self):
        self.qt.quit()


def _install_error_log():
    """PyQt kills the app silently when a slot raises. Log it instead."""
    import logging
    import os
    import traceback

    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hoursnsilence.log")
    logging.basicConfig(filename=log_path, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    def hook(exc_type, exc, tb):
        logging.error("".join(traceback.format_exception(exc_type, exc, tb)))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def main():
    _install_error_log()
    qt = QApplication(sys.argv)        # a socket needs an application object
    if _already_running():
        sys.exit(0)
    sys.exit(App(sys.argv, qt).run())


if __name__ == "__main__":
    main()

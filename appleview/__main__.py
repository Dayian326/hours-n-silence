"""Run with:  python -m appleview"""

import sys

# Qt and the audio library must agree on how COM is set up on the main thread.
sys.coinit_flags = 2  # noqa: E402

from PyQt6.QtWidgets import QApplication  # noqa: E402

from .itunes_worker import ITunesWorker  # noqa: E402
from .ui.main_window import MainWindow  # noqa: E402
from .ui.mini_player import MiniPlayer  # noqa: E402
from .ui.popup import NowPlayingPopup  # noqa: E402
from .ui.theme import QSS  # noqa: E402
from .volume import VolumeWatcher  # noqa: E402


class App:
    def __init__(self, argv):
        self.qt = QApplication(argv)
        self.qt.setStyle("Fusion")
        self.qt.setStyleSheet(QSS)
        self.qt.setQuitOnLastWindowClosed(False)
        self.qt.setApplicationName("AppleView")

        self.worker = ITunesWorker()
        self.window = MainWindow()
        self.mini = MiniPlayer()
        self.popup = NowPlayingPopup()
        self.volume = VolumeWatcher()

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
        self.mini.expand_requested.connect(self._show_full)
        self.window.quit_requested.connect(self.quit)

        # the knob
        self.volume.changed.connect(self._on_volume)

    def _command(self, name, arg):
        if arg is None:
            self.worker.send(name)
        else:
            self.worker.send(name, arg)

    def _on_snapshot(self, snap):
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

    def _on_volume(self, percent):
        self.popup.show_volume(percent)

    def _show_mini(self):
        if self.mini.pos().isNull():
            self.mini.place_default()
        self.mini.show()

    def _show_full(self):
        self.mini.hide()
        self.window.restore_from_mini()

    def run(self):
        self.window.show()
        self.worker.start()
        self.volume.start()
        code = self.qt.exec()
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

    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "appleview.log")
    logging.basicConfig(filename=log_path, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    def hook(exc_type, exc, tb):
        logging.error("".join(traceback.format_exception(exc_type, exc, tb)))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def main():
    _install_error_log()
    sys.exit(App(sys.argv).run())


if __name__ == "__main__":
    main()

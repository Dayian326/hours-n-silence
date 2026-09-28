"""Discord Rich Presence: "Listening to Hours N Silence" with the song, the
artist and album, a progress bar, and the cover.

Discord shows presence under an "application" that the owner creates once at
discord.com/developers/applications; its Application ID (not a secret, every
client shows it) goes into Settings. Covers come from Apple's public search,
which returns a picture link Discord can display. Nothing else leaves the
machine: just song title, artist, album and timing, and only while Discord
is running.
"""

import json
import threading
import time
import urllib.parse
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

APP_NAME = "Hours N Silence"
REFRESH_SECONDS = 12
RETRY_SECONDS = 30


def artwork_url(artist, name, album, cache={}):
    """A cover picture link from Apple's public search, or "" when none."""
    key = (artist, name, album)
    if key in cache:
        return cache[key]
    url = ""
    try:
        q = urllib.parse.urlencode({"term": f"{artist} {name}", "entity": "song", "limit": 3})
        with urllib.request.urlopen("https://itunes.apple.com/search?" + q, timeout=6) as r:
            results = json.load(r).get("results", [])
        best = None
        for res in results:
            if album and album.lower() in (res.get("collectionName") or "").lower():
                best = res
                break
        best = best or (results[0] if results else None)
        if best and best.get("artworkUrl100"):
            url = best["artworkUrl100"].replace("100x100", "512x512")
    except Exception:
        url = ""
    cache[key] = url
    return url


class DiscordPresence(QThread):
    status = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._snap = {}
        self._enabled = False
        self._app_id = ""
        self._stop = False
        self._dirty = True

    # ---- from the UI thread ----
    def configure(self, enabled, app_id):
        with self._lock:
            self._enabled = bool(enabled)
            self._app_id = (app_id or "").strip()
            self._dirty = True

    def push(self, snap):
        with self._lock:
            keys = ("db_id", "playing", "name", "artist", "album", "duration", "position", "connected")
            new = {k: snap.get(k) for k in keys}
            if new.get("db_id") != self._snap.get("db_id") or new.get("playing") != self._snap.get("playing"):
                self._dirty = True
            self._snap = new

    def stop(self):
        self._stop = True

    # ---- the thread ----
    def run(self):
        try:
            from pypresence import Presence
        except Exception:
            self.status.emit("Discord: presence library missing")
            return
        rpc = None
        connected_id = ""
        last_update = 0.0
        while not self._stop:
            with self._lock:
                enabled, app_id, snap, dirty = self._enabled, self._app_id, dict(self._snap), self._dirty
                self._dirty = False
            if not enabled or not app_id:
                if rpc is not None:
                    self._close(rpc)
                    rpc, connected_id = None, ""
                    self.status.emit("Discord presence off")
                self._sleep(2)
                continue
            if rpc is None or connected_id != app_id:
                if rpc is not None:
                    self._close(rpc)
                try:
                    rpc = Presence(app_id)
                    rpc.connect()
                    connected_id = app_id
                    self.status.emit("Discord presence on")
                    dirty = True
                except Exception as e:
                    rpc, connected_id = None, ""
                    self.status.emit(f"Discord not reachable ({str(e)[:40]}); retrying")
                    self._sleep(RETRY_SECONDS)
                    continue
            now = time.time()
            if dirty or now - last_update >= REFRESH_SECONDS:
                last_update = now
                try:
                    self._send(rpc, snap)
                except Exception as e:
                    self.status.emit(f"Discord update failed ({str(e)[:40]}); reconnecting")
                    self._close(rpc)
                    rpc, connected_id = None, ""
                    self._sleep(5)
                    continue
            self._sleep(1)
        if rpc is not None:
            self._close(rpc)

    def _send(self, rpc, snap):
        if not snap.get("connected", True) or not snap.get("name"):
            rpc.clear()
            return
        artist, album, name = snap.get("artist") or "", snap.get("album") or "", snap.get("name") or ""
        state = f"{artist}  -  {album}" if artist and album else artist or album or " "
        kwargs = {
            "details": name[:128],
            "state": state[:128],
            "large_text": album[:128] or APP_NAME,
            "small_text": APP_NAME,
        }
        art = artwork_url(artist, name, album)
        if art:
            kwargs["large_image"] = art
        if snap.get("playing"):
            start = time.time() - float(snap.get("position") or 0)
            kwargs["start"] = int(start)
            if snap.get("duration"):
                kwargs["end"] = int(start + float(snap["duration"]))
        else:
            kwargs["state"] = ("Paused  -  " + state)[:128]
        try:
            from pypresence import ActivityType
            rpc.update(activity_type=ActivityType.LISTENING, **kwargs)     # "Listening to"
        except Exception:
            rpc.update(**kwargs)                                            # older library: "Playing"


    @staticmethod
    def _close(rpc):
        try:
            rpc.clear()
        except Exception:
            pass
        try:
            rpc.close()
        except Exception:
            pass

    def _sleep(self, seconds):
        t0 = time.time()
        while not self._stop and time.time() - t0 < seconds:
            time.sleep(0.2)

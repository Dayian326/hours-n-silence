"""The one thread that talks to iTunes.

COM objects belong to the thread that created them, so everything iTunes
lives here. The UI only ever sees plain dicts and lists, and sends commands
back through a queue. AppleView never writes to the library: the only calls
that change anything are play, pause, next, previous, seek and volume.
"""

import os
import queue
import time

import psutil
import pythoncom
from PyQt6.QtCore import QThread, pyqtSignal
from win32com.client import CastTo, gencache

from .cache import artwork_path_for, save_artwork
from .covers import cover_for, persistent_hex

PLAYLIST_KIND_USER = 2
SPECIAL_NONE = 0          # a normal playlist
SPECIAL_FOLDER = 4
SPECIAL_MUSIC = 6

POLL_SECONDS = 0.25
# iTunes reports position in whole seconds, so this fires during the song's last
# second; any smaller and iTunes reaches the end and moves on before we do.
HANDOFF_SECONDS = 1
# iTunes' crossfade can be set up to 12 seconds; a track change with less than
# this left on the queued song counts as "it ended", not "the user changed it".
EARLY_SWITCH_SECONDS = 15
# Playing a song "from here" means starting its playlist and hopping forward,
# about 30 ms a hop. Past this many hops we play the song directly and let
# AppleView's queue carry the rest of the playlist instead.
HOP_LIMIT = 400
REPEAT_OFF, REPEAT_ONE, REPEAT_ALL = 0, 1, 2


# command names as a person would say them, for status messages
PLAIN = {
    "play_pause": "play or pause",
    "next": "skip to the next song",
    "previous": "go back a song",
    "play_track": "play that song",
    "play_playlist": "play that playlist",
    "play_queue": "play the queue",
    "seek": "jump to that spot",
    "volume": "change the volume",
    "load_tracks": "load that playlist",
    "launch": "start iTunes",
}


def itunes_is_running():
    for p in psutil.process_iter(["name"]):
        if (p.info["name"] or "").lower() == "itunes.exe":
            return True
    return False


class ITunesWorker(QThread):
    snapshot = pyqtSignal(dict)          # now-playing state, only when it changes
    artwork = pyqtSignal(int, str)       # (db_id, png path)
    playlists = pyqtSignal(list)         # [{name, db_id, folder, parent, count}]
    playlist_tracks = pyqtSignal(int, list)   # (playlist db id, [track dict])
    queue_changed = pyqtSignal(list)     # [track dict]
    status = pyqtSignal(str)             # short human-readable line

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cmds = queue.Queue()
        self._stop = False
        self._queue = []          # AppleView's own queue of track dicts
        self._queue_current = None   # db_id of the queued song now playing
        self._last_remaining = None  # seconds left on it at the last poll
        self._last = {}
        self._last_art_id = None
        self._it = None
        self._track_cache = {}    # playlist db_id -> [track dict]

    # ---- commands from the UI (thread-safe) ----
    def send(self, name, *args):
        self._cmds.put((name, args))

    def stop(self):
        self._stop = True

    # ---- thread body ----
    def run(self):
        pythoncom.CoInitialize()
        try:
            self._loop()
        except Exception as e:
            # PyQt aborts the whole app if a thread dies with an error; report instead
            self.status.emit(f"The iTunes connection stopped: {str(e)[:100]}")
            self.snapshot.emit({"connected": False})
        finally:
            self._it = None
            pythoncom.CoUninitialize()

    def _connect(self, launch=False):
        was_running = itunes_is_running()
        if not launch and not was_running:
            return False
        try:
            if not was_running:
                self.status.emit("Starting iTunes in the background")
            self._it = gencache.EnsureDispatch("iTunes.Application")
            if not was_running:
                self._tuck_itunes_away()
            self.status.emit(f"Connected to iTunes {self._it.Version}")
            return True
        except Exception as e:
            self.status.emit(f"Could not reach iTunes: {e}")
            self._it = None
            return False

    def _tuck_itunes_away(self):
        """iTunes opens its window when we start it; minimize it so AppleView is the face."""
        try:
            self._it.BrowserWindow.Minimized = True
        except Exception:
            pass

    def _loop(self):
        # AppleView is meant to be the only thing you open: start iTunes if it is closed.
        connected = self._connect(launch=True)
        if connected:
            self._safe_load_playlists()
        else:
            self.status.emit("iTunes is not running. Open it, or use Start iTunes.")
            self.snapshot.emit({"connected": False})
        while not self._stop:
            try:
                while True:
                    name, args = self._cmds.get_nowait()
                    try:
                        self._handle(name, args)
                    except Exception as e:
                        # a bad command must never take the thread down with it
                        self.status.emit(f"Could not {PLAIN.get(name, name)}: {str(e)[:100]}")
            except queue.Empty:
                pass
            if self._it is None:
                if itunes_is_running() and self._connect():
                    self._safe_load_playlists()
                else:
                    time.sleep(1.0)
                    continue
            try:
                self._poll()
            except Exception as e:
                # iTunes quit or is busy; drop the connection and retry
                self.status.emit(f"Lost iTunes: {str(e)[:80]}")
                self._it = None
                self._last = {}
                self._track_cache = {}
                self.snapshot.emit({"connected": False})
            time.sleep(POLL_SECONDS)

    # ---- iTunes reads ----
    def _poll(self):
        it = self._it
        t = it.CurrentTrack
        state = it.PlayerState
        snap = {
            "connected": True,
            "playing": state == 1,
            "volume": it.SoundVolume,
            "shuffle": False,
            "repeat": REPEAT_OFF,
            "playlist_id": None,
        }
        try:
            cp = it.CurrentPlaylist
            if cp is not None:
                snap["shuffle"] = bool(cp.Shuffle)
                snap["repeat"] = int(cp.SongRepeat)
                snap["playlist_id"] = cp.playlistID
        except Exception:
            pass
        if t is not None:
            pos = it.PlayerPosition
            snap.update({
                "db_id": t.TrackDatabaseID,
                "name": t.Name,
                "artist": t.Artist,
                "album": t.Album,
                "duration": t.Duration,
                "position": pos,
                "kind": t.KindAsString,
            })
            self._drive_queue(snap)
        else:
            snap.update({"db_id": None, "name": "", "artist": "", "album": "",
                         "duration": 0, "position": 0, "kind": ""})
        if snap != self._last:
            self._last = snap
            self.snapshot.emit(snap)
        # artwork goes out after the snapshot so the UI already knows the new track
        if t is not None and snap["db_id"] != self._last_art_id:
            self._last_art_id = snap["db_id"]
            self._emit_artwork(t)

    def _emit_artwork(self, track):
        db_id = track.TrackDatabaseID
        path = artwork_path_for(db_id)
        if not os.path.exists(path):
            try:
                art = track.Artwork
                if art.Count > 0:
                    piece = art.Item(1)
                    ext = {1: ".bmp", 2: ".jpg", 3: ".png"}.get(piece.Format, ".img")
                    tmp = path + ".src" + ext
                    try:
                        piece.SaveArtworkToFile(tmp)
                        save_artwork(tmp, path)
                    finally:
                        if os.path.exists(tmp):
                            os.remove(tmp)
                else:
                    path = ""
            except Exception:
                path = ""
        self.artwork.emit(db_id, path)

    def _track_dict(self, t, order=None):
        d = {
            "order": order,          # 1-based position in the playlist's play order
            "db_id": t.TrackDatabaseID,
            "source_id": t.sourceID,
            "playlist_id": t.playlistID,
            "track_id": t.trackID,
            "name": t.Name,
            "artist": t.Artist,
            "album": t.Album,
            "duration": t.Duration,
            "kind": t.KindAsString,
        }
        for field, attr in (("genre", "Genre"), ("plays", "PlayedCount"),
                            ("skips", "SkippedCount"), ("year", "Year")):
            try:
                d[field] = getattr(t, attr)
            except Exception:
                d[field] = None
        return d

    def _load_playlists(self):
        it = self._it
        pls = it.LibrarySource.Playlists
        out = []
        for i in range(1, pls.Count + 1):
            p = pls.Item(i)
            if p.Kind != PLAYLIST_KIND_USER or not p.Visible:
                continue
            up = CastTo(p, "IITUserPlaylist")
            special = up.SpecialKind
            if special not in (SPECIAL_NONE, SPECIAL_FOLDER, SPECIAL_MUSIC):
                continue
            parent = up.Parent
            if special == SPECIAL_NONE and self._is_video_playlist(p):
                continue
            cover = ""
            try:
                cover = cover_for(persistent_hex(*it.GetITObjectPersistentIDs(p)))
            except Exception:
                pass
            out.append({
                "name": p.Name,
                "db_id": p.playlistID,
                "folder": special == SPECIAL_FOLDER,
                "music": special == SPECIAL_MUSIC,
                "parent": parent.playlistID if parent is not None else None,
                "count": p.Tracks.Count if special != SPECIAL_FOLDER else 0,
                "cover": cover,
            })
        self.playlists.emit(out)
        self.status.emit(f"{len(out)} playlists loaded")

    @staticmethod
    def _is_video_playlist(p):
        """Home Videos and the like: a playlist whose first item is a video."""
        try:
            if p.Tracks.Count == 0:
                return False
            first = CastTo(p.Tracks.Item(1), "IITFileOrCDTrack")
            return first.VideoKind != 0
        except Exception:
            # Apple Music tracks refuse that cast; they are audio
            return False

    def _safe_load_playlists(self):
        try:
            self._load_playlists()
        except Exception as e:
            self.status.emit(f"Could not read the playlists: {str(e)[:100]}")

    def _playlist_by_id(self, playlist_id):
        # With track and database ids of 0, GetITObjectByID returns the playlist itself.
        src = self._it.LibrarySource
        obj = self._it.GetITObjectByID(src.sourceID, playlist_id, 0, 0)
        return CastTo(obj, "IITUserPlaylist")

    def _load_tracks(self, playlist_id):
        if playlist_id in self._track_cache:
            self.playlist_tracks.emit(playlist_id, self._track_cache[playlist_id])
            return
        p = self._playlist_by_id(playlist_id)
        tracks = p.Tracks
        n = tracks.Count
        out = []
        # play order is the order iTunes itself will play them in
        for i in range(1, n + 1):
            out.append(self._track_dict(tracks.ItemByPlayOrder(i), order=i))
            if i % 200 == 0:
                self.status.emit(f"Loading {p.Name}: {i}/{n}")
        self._track_cache[playlist_id] = out
        self.playlist_tracks.emit(playlist_id, out)
        self.status.emit(f"{p.Name}: {n} songs")

    # ---- iTunes commands ----
    def _track_obj(self, d):
        obj = self._it.GetITObjectByID(d["source_id"], d["playlist_id"], d["track_id"], d["db_id"])
        return CastTo(obj, "IITTrack")

    def _play_track(self, d):
        self._track_obj(d).Play()

    def _handle(self, name, args):
        if name == "launch":
            if self._it is None and self._connect(launch=True):
                self._safe_load_playlists()
            return
        if name == "load_tracks":
            if self._it is not None:
                self._load_tracks(args[0])
            return
        if name == "enqueue":
            self._queue.append(args[0])
            self.queue_changed.emit(list(self._queue))
            return
        if name == "dequeue":
            idx = args[0]
            if 0 <= idx < len(self._queue):
                self._queue.pop(idx)
            self.queue_changed.emit(list(self._queue))
            return
        if name == "clear_queue":
            self._queue.clear()
            self._queue_current = None
            self.queue_changed.emit([])
            return
        if self._it is None:
            return
        it = self._it
        try:
            if name == "play_pause":
                it.PlayPause()
            elif name == "next":
                if not self._play_next_queued():
                    it.NextTrack()
            elif name == "previous":
                it.BackTrack()
            elif name == "play_track":
                self._queue_current = None
                self._play_from_here(args[0])
            elif name == "set_shuffle":
                cp = it.CurrentPlaylist
                if cp is None:
                    self.status.emit("Start a playlist first, then shuffle it")
                else:
                    cp.Shuffle = bool(args[0])
            elif name == "set_repeat":
                cp = it.CurrentPlaylist
                if cp is None:
                    self.status.emit("Start a playlist first, then set repeat")
                else:
                    cp.SongRepeat = int(args[0])
            elif name == "play_playlist":
                self._queue_current = None
                CastTo(self._playlist_by_id(args[0]), "IITUserPlaylist").PlayFirstTrack()
            elif name == "play_queue":
                self._play_next_queued()
            elif name == "seek":
                it.PlayerPosition = int(args[0])
            elif name == "volume":
                it.SoundVolume = int(args[0])
        except Exception as e:
            self.status.emit(f"iTunes would not {PLAIN.get(name, name)}: {str(e)[:80]}")

    def _play_from_here(self, d):
        """Play a song and have iTunes continue with the songs after it.

        A plain Play() on a track makes iTunes play it once and then go back to
        whatever it was going to play next. The only way to make iTunes carry
        on from the clicked song is to start its playlist and hop forward,
        muted and paused so nothing is heard. Past HOP_LIMIT hops that takes
        too long, so we play the song directly and queue the rest ourselves.
        """
        it = self._it
        order = d.get("order")
        playlist_id = d.get("playlist_id")
        if not order or playlist_id is None:
            self._play_track(d)
            return
        pl = self._playlist_by_id(playlist_id)
        if pl.Shuffle:
            # order means nothing under shuffle; just switch iTunes to this playlist
            pl.PlayFirstTrack()
            self._play_track(d)
            return
        if order == 1:
            pl.PlayFirstTrack()
            return
        if order - 1 > HOP_LIMIT:
            self._play_track(d)
            rest = [t for t in self._track_cache.get(playlist_id, []) if (t.get("order") or 0) > order]
            self._queue = rest
            self._queue_current = d["db_id"]
            self._last_remaining = None
            self.queue_changed.emit(list(self._queue))
            self.status.emit(f"Song {order} of {len(rest) + order}: the rest of the playlist is queued in AppleView")
            return
        self.status.emit(f"Lining up song {order} of {pl.Tracks.Count}")
        volume = it.SoundVolume
        try:
            it.SoundVolume = 0
            pl.PlayFirstTrack()
            it.Pause()
            for _ in range(order - 1):
                it.NextTrack()
            it.Play()
        finally:
            it.SoundVolume = volume
        self.status.emit(f"{pl.Name}: playing from song {order}")

    # ---- AppleView's own queue ----
    def _play_next_queued(self):
        if not self._queue:
            self._queue_current = None
            return False
        d = self._queue.pop(0)
        self._queue_current = d["db_id"]
        self._play_track(d)
        self.queue_changed.emit(list(self._queue))
        return True

    def _drive_queue(self, snap):
        """Hand over to the next queued song when the current one is ending.

        Two triggers. The plain one: the song is in its last second. The
        crossfade one: with crossfade on, iTunes switches to its own next song
        several seconds early, so if the queued song was near its end and the
        track changed under us, iTunes moved on and we take over right away.
        A change that happens mid-song means the user picked something else in
        iTunes; the queue keeps its songs but stops driving.
        """
        if self._queue_current is None:
            return
        remaining = snap["duration"] - snap["position"]
        if snap["db_id"] == self._queue_current:
            self._last_remaining = remaining
            if self._queue and snap["playing"] and remaining <= HANDOFF_SECONDS:
                try:
                    self._play_next_queued()
                except Exception as e:
                    self._queue_current = None
                    self.status.emit(f"Could not play the next queued song: {str(e)[:80]}")
            return
        # the track changed away from the queued song
        near_end = self._last_remaining is not None and self._last_remaining <= EARLY_SWITCH_SECONDS
        if near_end and self._queue:
            try:
                self._play_next_queued()
            except Exception as e:
                # one bad queued song should not look like iTunes went away
                self._queue_current = None
                self.status.emit(f"Could not play the next queued song: {str(e)[:80]}")
        else:
            self._queue_current = None

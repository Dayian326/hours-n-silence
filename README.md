# AppleView

A minimalist, private music player for Windows that sits on top of old iTunes.

iTunes keeps doing everything it does today: downloads, iCloud sync, the mixed
library of downloaded files and Apple Music tracks. AppleView only reads from
iTunes and sends it play, pause, next, previous, seek and volume. It never
writes to the library.

## What it does

- **Popup card** in the bottom-right corner whenever the system volume changes
  (knob, mouse, taskbar slider all count): album art, song, artist, volume bar.
  Never takes focus, fades after three seconds. Also shows when a new song
  starts while the full window is out of the way.
- **Mini player** when you minimize: a small always-on-top card with art and
  play/pause/next/previous. Drag it anywhere. Double-click or use the corner
  button to get the full window back. The tray icon does the same.
- **Library browser**: playlists on the left (folders grouped), songs on the
  right, search box, double-click to play, Play playlist button.
- **Queue**: right-click a song, Add to queue. AppleView plays queued songs in
  order and takes over the moment iTunes would move on (including when
  crossfade starts the next song early). Next with a non-empty queue plays the
  next queued song. Picking a different song in iTunes mid-song stops the
  queue from driving; the songs stay listed.
- **Dark theme** throughout.

Media keys keep working exactly as before: iTunes handles them and AppleView
updates to match.

## Requirements

- Windows 11, iTunes from Apple's desktop installer (tested on 12.13.10.3).
- Do NOT install the Apple Music, Apple TV, or Apple Devices apps from the
  Microsoft Store. They lock iTunes down to podcasts and audiobooks.
- Python 3.12+

```
pip install -r requirements.txt
```

## Run

With iTunes open (AppleView will not start it on its own; there is a Start
iTunes button if it is closed):

```
python -m appleview
```

Closing the window quits. Minimizing goes to the mini player.

## Day-one test

```
python probe.py
```

Prints the iTunes version, the current track, whether artwork came through,
and your playlists. Confirms the scripting hook works.

## Known rough edges

- **Queue is AppleView's, not iTunes'.** iTunes' scripting hook refuses to add
  songs to playlists on this library (every call style returns "parameter is
  incorrect", most likely because Sync Library is on), so the queue cannot be
  an iTunes playlist. Consequences: the queue is gone when AppleView closes,
  and the handoff between queued songs is a cut, not a crossfade.
- **Quitting iTunes while AppleView runs** shows iTunes' "an application is
  using iTunes" prompt. Close AppleView first.
- **The stock Windows volume slider** still appears bottom-center. AppleView's
  card is bottom-right so they do not overlap.
- Playlists load their songs on first click (about a second for the biggest).

## Layout

- `appleview/itunes_worker.py` - the one thread that talks to iTunes
- `appleview/volume.py` - watches the Windows master volume
- `appleview/cache.py` - artwork cache (`artwork_cache/`, gitignored)
- `appleview/ui/` - main window, mini player, popup, theme, shared widgets
- `probe.py` - connection test, safe to run any time
- `tools/shot.py` - screenshot helper used while testing the UI

# AppleView

A minimalist, private music player for Windows that sits on top of old iTunes.

iTunes keeps doing everything it does today: downloads, iCloud sync, the mixed
library of downloaded files and Apple Music tracks. AppleView only reads from
iTunes and sends it play, pause, next, previous, seek and volume. It never
writes to the library.

## What it does

v2 look: a playlist rail on the left (covers only, or covers with names
when you expand it with the button at the top; hover a cover while it is
collapsed to see the name), recently played playlists pinned at the top of
the rail, and an immersive playlist page: the cover blurred across the whole
page, a card with the cover, name, description and Play / Shuffle, the songs
on the right. The accent color follows the art of whatever is playing.

- **Popup card** in the bottom-right corner whenever the system volume changes
  (knob, mouse, taskbar slider all count): album art, song, artist, volume bar.
  Never takes focus, fades after three seconds. Also shows when a new song
  starts while the full window is out of the way.
- **Mini player** when you minimize: a small always-on-top card with art and
  play/pause/next/previous. Drag it anywhere. Double-click or use the corner
  button to get the full window back. The tray icon does the same.
- **Library browser**: playlists on the left (folders grouped), songs on the
  right in iTunes' play order, search box, Play playlist button.
  Double-click a song and iTunes carries on with the songs after it, the way
  it does when you click in iTunes itself. (iTunes' scripting hook can only
  do that by starting the playlist and hopping forward, muted, about 30 ms a
  hop; past song 400 AppleView plays the song directly and queues the rest.)
- **Shuffle and repeat** buttons in the player bar. They set iTunes' own
  shuffle and repeat for the playlist that is playing.
- **Seek bar**: click anywhere to jump there. The right-hand time is time
  left; click it to see the song length instead.
- **Playlist covers**: the art you dragged onto playlists in iTunes is read
  from iTunes' artwork cache (never written) and kept as PNGs in
  `artwork_cache/`. Playlists without a cover borrow the playing song's art.
- **Descriptions**: shown when available. iTunes does not expose them to
  scripts yet, so the card says "No description yet" for now.
- **Remembers**: recently played playlists and whether the rail is expanded,
  in `appleview_state.json` (gitignored).
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

```
python -m appleview
```

If iTunes is closed, AppleView starts it in the background and minimizes its
window, so AppleView is the only thing you open. iTunes stays running when
you close AppleView. Closing the window quits AppleView; minimizing goes to
the mini player.

## Pin it to the taskbar

Once:

```
python tools/make_shortcut.py
```

That draws the icon (`assets/appleview.ico`) and puts an AppleView shortcut
in the Start Menu and on the Desktop. Open AppleView from either, right-click
its taskbar icon, Pin to taskbar. Safe to run again any time.

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
- `appleview/covers.py` - playlist covers out of iTunes' artwork cache
- `appleview/palette.py` - the chameleon: one accent color from a piece of art
- `appleview/state.py` - recents and rail state between runs
- `appleview/ui/` - main window, rail, playlist page, backdrop, mini player,
  popup, theme, shared widgets
- `assets/appleview.ico` - the icon, drawn by `tools/make_shortcut.py`
- `probe.py` - connection test, safe to run any time
- `tools/make_shortcut.py` - icon plus Start Menu and Desktop shortcuts
- `tools/queue_test.py` - proves the queue handoff against a running iTunes
- `tools/shot.py` - screenshot helper used while testing the UI

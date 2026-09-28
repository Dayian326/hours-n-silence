# AppleView

A minimalist, private music player for Windows that sits on top of old iTunes.

iTunes keeps doing everything it does today: downloads, iCloud sync, the mixed
library of downloaded files and Apple Music tracks. AppleView only reads from
iTunes and sends it commands through its built-in scripting hook (COM), so
nothing in the library is touched.

## What it does (planned)

- Popup card in the corner when the system volume changes: album art, song,
  artist, play/pause/next. Fades after a few seconds.
- Mini player when minimized: small always-on-top card with art and controls.
- Library browser: playlists and tracks straight from iTunes, search,
  double-click to play.
- Queue: AppleView manages its own queue playlist inside iTunes (iTunes'
  scripting hook has no Up Next call).
- Dark theme, inspired by Sidra's look.

## Requirements

- Windows 11, iTunes desktop installer (not the Microsoft Store apps).
- Do NOT install the Apple Music, Apple TV, or Apple Devices apps from the
  Microsoft Store. They lock iTunes down to podcasts and audiobooks.
- Python 3.12+

```
pip install -r requirements.txt
```

## Day-one test

With iTunes open and a song playing:

```
python probe.py
```

Prints the iTunes version, the current track, whether artwork came through,
and your playlists. Confirms the scripting hook works for both downloaded
files and Apple Music tracks before anything else gets built.

## Layout

- `probe.py` - connection test, safe to run any time
- `appleview/` - the app (coming)

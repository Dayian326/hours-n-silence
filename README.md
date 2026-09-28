# Hours N Silence

A private, modern front end for old iTunes on Windows. iTunes keeps doing
what it does (playing, downloads, iCloud sync, the mixed library of
downloaded files and Apple Music tracks). Hours N Silence gives it a new
face: black glass, your playlist covers, a mini player with a live
visualizer, and a volume popup that iTunes never had.

It never writes to the library. The only things it ever tells iTunes are
play, pause, next, previous, jump to a spot, shuffle, repeat, and volume.

## How it works

- **iTunes plays, this displays and controls.** Old iTunes ships with a
  scripting interface that Apple built for other programs to use. Hours N
  Silence reads the library and playlists through it and sends playback
  commands back. The new Apple Music app for Windows has no such interface,
  which is why this is built on old iTunes.
- **Nothing locked is touched.** Apple Music tracks stay inside Apple's
  player. No converting, no ripping, no playing them anywhere else.
- **The sound is measured after it leaves.** Windows offers a live copy of
  whatever is coming out of an output device. The visualizer reads that copy
  about fifty times a second, measures it, and drops it. Nothing is recorded.
- **Windows draws the glass.** The frosted panels are Windows' own blur
  behind the window, with dark translucent panes on top.
- **Covers come from iTunes' own cache** on disk, read only.

## What it does

- **Playlist rail** on the left: covers only, or covers with names when
  expanded. Hover a cover while collapsed to see its name. Recently played
  playlists pin at the top; everything else sits below, folders grouped.
- **Immersive playlist page**: the cover blurred across the page, a card with
  the cover, name, description and song count, Play, Shuffle and Add all to
  queue, and the songs on the right in iTunes' play order, with search.
- **Double-click a song** and iTunes carries on with the songs after it, the
  way it does when you click inside iTunes itself.
- **Chameleon accent**: buttons, sliders and highlights take their color from
  the art of whatever is playing.
- **Black glass and a dark title bar**, regardless of the Windows accent
  setting. If Windows cannot blur, the panels fall back to solid dark.
- **Player bar**: shuffle, repeat, previous, play, next, a seek bar that
  jumps where you click, time left (click for the song length), volume, a
  queue panel, and a mini player button.
- **Queue**: right-click a song, Add to queue. Queued songs play in order and
  take over the moment iTunes would move on, crossfade included.
- **Mini player** when you minimize: a small always-on-top glass card with
  art and controls. Drag it anywhere; double-click to get the full window
  back. The tray icon does the same.
- **Visualizer** in the mini player. Each part of the sound has its own look
  and color:

  | Part | What it is | Look |
  |---|---|---|
  | Kick / beat | a hit in the low end, 40 to 120 Hz | big sparks from the art's edge, flying right |
  | Bass | how much low end is there right now | the card's edge glows, thicker with more bass |
  | Snare / clap | a mid thump plus a burst of noise | quick streaks dropping in from the top |
  | Voice / lead | center-panned energy in the voice range | soft motes rising along the text |
  | Hi-hats / sparkle | a hit in the top end, 8 to 16 kHz | tiny twinkles, gone in a blink |

  By default every part is colored from the playing song's cover, with the
  hues kept apart so they read as different things. Settings (the button in
  the status line, or the tray menu) switches to your own colors, turns parts
  on or off, and sets how much of it there is. Voice is "what sits in the
  middle of the stereo picture", which is where vocals live but lead melodies
  too, so read it as voice or lead.
- **Volume popup** bottom-right whenever any output device's volume changes:
  art, song, artist, the level, and which device moved. Never takes focus,
  fades after three seconds. Also shows when a new song starts while the
  full window is out of the way.
- **Playlist covers** are the art you dragged onto playlists in iTunes.
  Playlists without one borrow the playing song's art.
- **Descriptions** appear once iTunes' XML export is on (Edit, Preferences,
  Advanced, "Share iTunes Library XML with other applications").

Media keys keep working: iTunes handles them and Hours N Silence updates.

## Cost

Measured with `python tools/resource_check.py` while playing with the mini
player and visualizer up: about 1 percent of the CPU, 157 MB of memory, no
GPU work of its own. The listener runs only while the mini player shows.

## Requirements

- Windows 11, iTunes from Apple's desktop installer (tested on 12.13.10.3).
- Do NOT install the Apple Music, Apple TV, or Apple Devices apps from the
  Microsoft Store. They lock iTunes down to podcasts and audiobooks.
- Python 3.12 or newer.

```
pip install -r requirements.txt
```

## Run

```
python -m hoursnsilence
```

If iTunes is
closed, Hours N Silence starts it in the background and minimizes its
window. iTunes stays running when you close Hours N Silence. Closing the
window quits; minimizing goes to the mini player.

## Pin it to the taskbar

Once:

```
python tools/make_shortcut.py
```

That draws the icon and puts a Hours N Silence shortcut in the Start Menu
and on the Desktop. Open it from either, right-click its taskbar icon, Pin
to taskbar. Safe to run again any time.

## Tests

All of them run against a live iTunes and put playback back the way it was.

- `python probe.py` - can we talk to iTunes at all
- `python tools/play_order_test.py` - double-click a song, the next one follows
- `python tools/queue_test.py` - the queue hands over between songs
- `python tools/beat_test.py` - the listener hears kicks, snares, hats, voice
- `python tools/resource_check.py` - CPU, memory and GPU of the running app

## Known rough edges

- The queue is Hours N Silence's, not iTunes'. iTunes refuses playlist edits
  from scripts on a synced library, so the queue cannot be an iTunes
  playlist: it is gone when the app closes, and the handoff between queued
  songs is a cut, not a crossfade.
- Quitting iTunes while Hours N Silence runs shows iTunes' "an application
  is using iTunes" prompt. Close Hours N Silence first.
- The stock Windows volume slider still appears bottom-center. The card is
  bottom-right so they do not overlap.
- Virtual audio devices (Sonar channels and the like) do not offer a
  loopback, so the visualizer listens on the physical output carrying the
  final mix.

## Layout

- `hoursnsilence/itunes_worker.py` - the one thread that talks to iTunes
- `hoursnsilence/audio.py` - the listener: kick, bass, snare, voice, hats
- `hoursnsilence/volume.py` - watches every output device's volume
- `hoursnsilence/covers.py` - playlist covers out of iTunes' artwork cache
- `hoursnsilence/descriptions.py` - playlist descriptions from the XML export
- `hoursnsilence/palette.py` - colors from art: the accent and the visualizer palette
- `hoursnsilence/state.py` - recents, rail state and settings between runs
- `hoursnsilence/ui/` - main window, rail, playlist page, backdrop, mini player,
  sparks, popup, settings, theme, glass, shared widgets
- `assets/hours_n_silence.ico` - the icon, drawn by `tools/make_shortcut.py`
- `tools/` - shortcut maker, tests, resource check, screenshot helper

---

Dayian Nadeem, Pandaminds Corporation. September 28, 2026.

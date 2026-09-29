# Hours N Silence AI DJ

Not a talking DJ. A set builder: you say a mood and a length, it plans the
songs, in an order with a shape, out of your own library, and hands the set
to the queue.

## What to steal from the big players

- Apple's Smart Mix and Autoplay: never jump lanes cold. Stay in the current
  genre lane, drift slowly, cross lanes only through a song that belongs to
  both.
- Spotify's DJ: play in segments with a shape. A set has an arc ("focus for
  40 minutes, then rise into hype"), not a shuffle.
- Spotify's daylist: mood is tied to the moment. "Study" and "type something
  out" are moods with a duration, not genres.

## What is ours

The skrt series is the owner's own catalogue: `skrt N` playlists are his
albums, and the `skrt N.1`, `N.2` ... playlists are mixtapes that each tell
a story in order. Some songs are trimmed in iTunes (a start and stop time
on the track) and spliced: in skrt 4, "Calling For You" plays as its first
111 seconds, another song sits between, then the same song returns from
182 seconds to the end as the 21 Savage half. Passionfruit starts at 60
seconds. Forty songs in the library carry trims like that. Those trims are
the owner marking where a song's good part begins and ends, and the splices
are how he builds a transition. The vibe cards and the set builder must read
the trims (exported as start/finish) and learn the splice moves, not just
the song order.

The taste model is the owner's own playlists. Hours In Silence parts 1 to 8
are songs sequenced by hand, on purpose. The builder learns what sits next
to what, how long a vibe lasts before it moves, and how the owner crosses
from R&B to rap. Nobody else has that data.

## How it works

1. **Library export** (`tools/library_export.py`, done): every song with its
   iTunes facts (genre, year, length, plays, skips, rating, date added, BPM
   when tagged) plus every playlist with its play order. This is the raw
   material and the taste data. Written to `dj/library.json`, gitignored.
2. **Vibe cards**, one per song, built once and cached: energy 1 to 10,
   lane (R&B, rap, pop, mixed), tempo, mood tags, and a "bridge" flag for
   short crossover tracks. Sources: the iTunes facts, the owner's playlist
   placements, the model's own knowledge of the song, and Apple's public
   30-second preview for measured tempo and energy on Apple Music tracks.
   Downloaded files can be measured in full.
3. **Song shape** from the web, where available: timed lyrics (free, no key)
   give where the chorus is, where the outro starts, where a beat switch
   sits. Lets the builder pair a fade-out with a soft intro and know when
   to cut.
4. **Set builder**: mood plus length in, an arc out (lanes, energy curve,
   how it ends). Picks songs, crosses lanes through bridge tracks, ends on
   purpose. The set is shown before it plays; drop or swap, then it goes to
   the queue.
5. **It learns**: skips during a set count against that placement; songs
   left to ride are reinforced; new playlists feed the taste model.

## Rules

- Cheap work local (ranking, filtering), real reasoning on the API, once per
  set. The vibe cards are a one-time pass.
- Never touches the library. The set goes to Hours N Silence's own queue.
- Everything the builder decides is visible before it plays.

## Status

- Step 1 done (2026-09-28): `python tools/library_export.py` writes
  `dj/library.json`: every song's facts and every playlist's play order.
- Next: step 2, vibe cards. One-time pass over the library on the API,
  cached, so it is a few dollars once and free after.
- Then steps 3 to 5 in order.

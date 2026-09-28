"""Day-one test: can we talk to iTunes, and what does it give us?

Run with iTunes open and a song playing. Safe to run any time; it changes
nothing in the library. Artwork is saved next to this file as
probe_artwork.<ext> and overwritten on each run.
"""

import os
import sys

import win32com.client

# Playlist and track names can contain characters the Windows console can't
# print by default. Force UTF-8 so a name never crashes the probe, able to read emojis as well.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    try:
        itunes = win32com.client.Dispatch("iTunes.Application")
    except Exception as e:
        print("Could not reach iTunes:", e)
        print("Is iTunes installed from Apple's desktop installer and open?")
        return 1

    print("iTunes version:", itunes.Version)
    state = {0: "stopped", 1: "playing"}.get(itunes.PlayerState, itunes.PlayerState)
    print("Player state:", state)
    print("Volume:", itunes.SoundVolume)

    track = itunes.CurrentTrack
    if track is None:
        print("No current track. Start a song in iTunes and run again.")
    else:
        print()
        print("Now playing")
        print("  Name:   ", track.Name)
        print("  Artist: ", track.Artist)
        print("  Album:  ", track.Album)
        print("  Kind:   ", track.KindAsString)
        print("  Length: ", track.Time)
        pos = itunes.PlayerPosition
        print("  Position:", f"{pos // 60}:{pos % 60:02d}")

        art = track.Artwork
        count = art.Count
        print("  Artwork pieces:", count)
        if count > 0:
            piece = art.Item(1)
            ext = {1: ".bmp", 2: ".jpg", 3: ".png"}.get(piece.Format, ".img")
            out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_artwork" + ext)
            piece.SaveArtworkToFile(out)
            print("  Artwork saved to:", out)
        else:
            print("  No artwork exposed for this track.")

    print()
    lib = itunes.LibraryPlaylist
    print("Library tracks:", lib.Tracks.Count)

    playlists = itunes.LibrarySource.Playlists
    print("Playlists:", playlists.Count)
    for i in range(1, playlists.Count + 1):
        p = playlists.Item(i)
        print(f"  {p.Name}  ({p.Tracks.Count} tracks)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

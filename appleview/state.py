"""Small things AppleView remembers between runs: recently played playlists,
whether the sidebar is expanded. Lives in appleview_state.json next to the
code, gitignored."""

import json
import os

STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "appleview_state.json")
RECENT_MAX = 6


class State:
    def __init__(self):
        self.recent = []            # playlist persistent ids, newest first
        self.rail_expanded = False
        self.load()

    def load(self):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            self.recent = [str(x) for x in data.get("recent", [])][:RECENT_MAX]
            self.rail_expanded = bool(data.get("rail_expanded", False))
        except Exception:
            pass

    def save(self):
        try:
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump({"recent": self.recent, "rail_expanded": self.rail_expanded}, f, indent=2)
        except Exception:
            pass

    def touch_recent(self, pid):
        """Move a playlist to the front of the recents. Returns True if the list changed."""
        if not pid:
            return False
        if self.recent and self.recent[0] == pid:
            return False
        self.recent = [pid] + [p for p in self.recent if p != pid]
        self.recent = self.recent[:RECENT_MAX]
        self.save()
        return True

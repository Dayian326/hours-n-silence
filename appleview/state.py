"""Small things Hours N Silence remembers between runs: recently played
playlists, whether the sidebar is expanded, the visualizer's colors. Lives
in appleview_state.json next to the code, gitignored."""

import copy
import json
import os

from .ui.sparks import DEFAULT_VIZ

STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "appleview_state.json")
RECENT_MAX = 6


class State:
    def __init__(self):
        self.recent = []            # playlist persistent ids, newest first
        self.rail_expanded = False
        self.viz = copy.deepcopy(DEFAULT_VIZ)
        self.load()

    def load(self):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            self.recent = [str(x) for x in data.get("recent", [])][:RECENT_MAX]
            self.rail_expanded = bool(data.get("rail_expanded", False))
            saved = data.get("viz") or {}
            viz = copy.deepcopy(DEFAULT_VIZ)
            viz["enabled"] = bool(saved.get("enabled", viz["enabled"]))
            viz["intensity"] = float(saved.get("intensity", viz["intensity"]))
            viz["kick_from_cover"] = bool(saved.get("kick_from_cover", viz["kick_from_cover"]))
            for key, el in viz["elements"].items():
                s = (saved.get("elements") or {}).get(key) or {}
                el["on"] = bool(s.get("on", el["on"]))
                if isinstance(s.get("color"), str) and s["color"].startswith("#"):
                    el["color"] = s["color"]
            self.viz = viz
        except Exception:
            pass

    def save(self):
        try:
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump({"recent": self.recent, "rail_expanded": self.rail_expanded, "viz": self.viz}, f, indent=2)
        except Exception:
            pass

    def set_viz(self, viz):
        self.viz = copy.deepcopy(viz)
        self.save()

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

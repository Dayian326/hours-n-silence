"""The visualizer layer behind the mini player's text.

Each thing the listener picks out of the song has its own look and color:
  kick   bursts of big sparks from the artwork's edge, flying right
  bass   the card's edge glows, thicker the more low end there is
  snare  quick streaks that drop in from the top
  voice  soft motes that rise slowly along the text
  hats   tiny twinkles anywhere, gone in a blink
Colors and on/off come from settings. Everything is capped so it stays cheap.
"""

import math
import random

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

FPS = 45
MAX_SPARKS = 320

DEFAULT_VIZ = {
    "enabled": True,
    "intensity": 1.0,
    "kick_from_cover": True,      # kick sparks borrow the cover's colors instead of one color
    "elements": {
        "kick":  {"on": True, "color": "#4da3ff", "label": "Kick / beat"},
        "bass":  {"on": True, "color": "#8a5cff", "label": "Bass (edge glow)"},
        "snare": {"on": True, "color": "#ffb347", "label": "Snare / clap"},
        "voice": {"on": True, "color": "#ff5c7a", "label": "Voice / lead"},
        "hats":  {"on": True, "color": "#ffffff", "label": "Hi-hats / sparkle"},
    },
}


class SparkLayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.viz = DEFAULT_VIZ
        self.cover_colors = ["#4da3ff"]
        self._sparks = []
        self._bass = 0.0
        self._glow = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / FPS))
        self._timer.timeout.connect(self._step)

    # ---- configuration ----
    def set_settings(self, viz):
        self.viz = viz

    def set_cover_colors(self, colors):
        self.cover_colors = colors or ["#4da3ff"]

    def _color(self, element):
        return self.viz["elements"][element]["color"]

    def _on(self, element):
        return self.viz.get("enabled", True) and self.viz["elements"][element]["on"]

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()
        self._sparks.clear()
        self._glow = 0.0
        self.update()

    # ---- from the listener ----
    def on_features(self, f):
        if not self.viz.get("enabled", True):
            return
        k = self.viz.get("intensity", 1.0)
        self._bass = f.get("bass", 0.0) if self._on("bass") else 0.0
        if f.get("kick") and self._on("kick"):
            self._glow = 1.0
            colors = self.cover_colors if self.viz.get("kick_from_cover", True) else [self._color("kick")]
            self._spawn_kick(int((6 + 14 * f.get("kick_level", 0.5)) * k), colors)
        if f.get("snare") and self._on("snare"):
            self._spawn_snare(int((4 + 6 * f.get("snare_level", 0.5)) * k), self._color("snare"))
        if self._on("voice"):
            v = f.get("voice", 0.0)
            if v > 0.45 and random.random() < v * 0.6 * k:
                self._spawn_voice(1 + int(v * 2 * k), self._color("voice"))
        if f.get("hats") and self._on("hats"):
            self._spawn_hats(int((2 + 4 * f.get("hats_level", 0.5)) * k), self._color("hats"))
        if len(self._sparks) > MAX_SPARKS:
            del self._sparks[:len(self._sparks) - MAX_SPARKS]

    def _add(self, **s):
        self._sparks.append(s)

    def _spawn_kick(self, n, colors):
        h = self.height()
        for _ in range(n):
            angle = random.uniform(-0.9, 0.9)
            speed = random.uniform(2.5, 6.5) * (0.7 + self._bass)
            self._add(x=92 + random.uniform(-6, 6), y=random.uniform(12, h - 12),
                      vx=math.cos(angle) * speed, vy=math.sin(angle) * speed * 0.5, g=0.01, drag=0.975,
                      life=1.0, decay=random.uniform(0.008, 0.02), size=random.uniform(2.5, 6.0),
                      color=random.choice(colors), kind="kick")

    def _spawn_snare(self, n, color):
        w = self.width()
        for _ in range(n):
            self._add(x=random.uniform(100, w - 20), y=random.uniform(-4, 8),
                      vx=random.uniform(0.5, 2.0), vy=random.uniform(3.0, 6.0), g=0.05, drag=0.98,
                      life=1.0, decay=random.uniform(0.03, 0.05), size=random.uniform(1.5, 3.0),
                      color=color, kind="snare")

    def _spawn_voice(self, n, color):
        w, h = self.width(), self.height()
        for _ in range(n):
            self._add(x=random.uniform(110, w - 24), y=h + random.uniform(0, 6),
                      vx=random.uniform(-0.3, 0.3), vy=random.uniform(-1.4, -0.6), g=0.0, drag=1.0,
                      life=1.0, decay=random.uniform(0.006, 0.012), size=random.uniform(5.0, 9.0),
                      color=color, kind="voice")

    def _spawn_hats(self, n, color):
        w, h = self.width(), self.height()
        for _ in range(n):
            self._add(x=random.uniform(96, w - 8), y=random.uniform(6, h - 6),
                      vx=0.0, vy=0.0, g=0.0, drag=1.0,
                      life=1.0, decay=random.uniform(0.08, 0.16), size=random.uniform(1.0, 2.2),
                      color=color, kind="hats")

    def _step(self):
        alive = []
        w = self.width()
        for s in self._sparks:
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            s["vy"] += s["g"]
            s["vx"] *= s["drag"]
            s["life"] -= s["decay"]
            if s["life"] > 0 and s["x"] < w + 10 and s["y"] > -12:
                alive.append(s)
        self._sparks = alive
        self._glow *= 0.86
        self.update()

    def paintEvent(self, _e):
        edge_level = max(self._glow, self._bass * 0.7 if self._on("bass") else 0.0)
        if not self._sparks and edge_level < 0.03:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        if edge_level >= 0.03:
            c = QColor(self._color("bass") if self._on("bass") else self._color("kick"))
            c.setAlphaF(min(0.6, edge_level * 0.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(c, 1.5 + 2.5 * edge_level))
            p.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 11, 11)
            p.setPen(Qt.PenStyle.NoPen)
        for s in self._sparks:
            c = QColor(s["color"])
            r = s["size"] * (0.6 + 0.4 * s["life"])
            reach = r * (1.6 if s["kind"] == "voice" else 2.2)
            grad = QRadialGradient(s["x"], s["y"], reach)
            c.setAlphaF((0.55 if s["kind"] == "voice" else 0.95) * s["life"])
            grad.setColorAt(0.0, c)
            c2 = QColor(c)
            c2.setAlphaF(0.0)
            grad.setColorAt(1.0, c2)
            p.setBrush(grad)
            p.drawEllipse(QRectF(s["x"] - reach, s["y"] - reach, reach * 2, reach * 2))
        p.end()

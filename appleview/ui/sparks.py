"""Beat sparks: little glowing particles in the cover's colors that burst on
every beat and drift across the mini player, plus a soft pulse of the edge."""

import math
import random

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

FPS = 45


class SparkLayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.colors = ["#dc6ab0"]
        self.edge_color = "#dc6ab0"
        self._sparks = []       # dicts: x, y, vx, vy, life, size, color
        self._bass = 0.0
        self._glow = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / FPS))
        self._timer.timeout.connect(self._step)

    def set_colors(self, colors, edge):
        self.colors = colors or ["#dc6ab0"]
        self.edge_color = edge or self.colors[0]

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()
        self._sparks.clear()
        self._glow = 0.0
        self.update()

    # ---- from the meter ----
    def on_level(self, bass, overall, beat):
        self._bass = bass
        if beat:
            self._glow = 1.0
            self._burst(int(6 + 14 * bass))
        elif bass > 0.6 and random.random() < bass * 0.3:
            self._burst(1)

    def _burst(self, n):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        # sparks leave the artwork's right edge and fly across the rest of the card
        ox = 92
        for _ in range(n):
            angle = random.uniform(-0.9, 0.9)
            speed = random.uniform(2.5, 6.5) * (0.7 + self._bass)
            self._sparks.append({
                "x": ox + random.uniform(-6, 6), "y": random.uniform(12, h - 12),
                "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed * 0.5,
                "life": 1.0, "decay": random.uniform(0.008, 0.02),
                "size": random.uniform(2.5, 6.0), "color": random.choice(self.colors),
            })
        if len(self._sparks) > 220:
            del self._sparks[:len(self._sparks) - 220]

    def _step(self):
        alive = []
        for s in self._sparks:
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            s["vy"] += 0.01
            s["vx"] *= 0.975
            if s["x"] > self.width() + 10:
                s["life"] = 0
            s["life"] -= s["decay"]
            if s["life"] > 0:
                alive.append(s)
        self._sparks = alive
        self._glow *= 0.86
        self.update()

    def paintEvent(self, _e):
        if not self._sparks and self._glow < 0.02:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        # edge pulse
        if self._glow > 0.02:
            c = QColor(self.edge_color)
            c.setAlphaF(min(0.55, self._glow * 0.55))
            pen_rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(c, 2))
            p.drawRoundedRect(pen_rect, 11, 11)
            p.setPen(Qt.PenStyle.NoPen)
        for s in self._sparks:
            c = QColor(s["color"])
            r = s["size"] * (0.6 + 0.4 * s["life"])
            grad = QRadialGradient(s["x"], s["y"], r * 2.2)
            c.setAlphaF(0.95 * s["life"])
            grad.setColorAt(0.0, c)
            c2 = QColor(c)
            c2.setAlphaF(0.0)
            grad.setColorAt(1.0, c2)
            p.setBrush(grad)
            p.drawEllipse(QRectF(s["x"] - r * 2.2, s["y"] - r * 2.2, r * 4.4, r * 4.4))
        p.end()

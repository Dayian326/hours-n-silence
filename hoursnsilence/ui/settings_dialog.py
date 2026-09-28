"""Settings: the visualizer's colors, what is on, and how much of it."""

import copy

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QColorDialog, QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QSlider,
    QVBoxLayout,
)

from .sparks import DEFAULT_VIZ


class ColorButton(QPushButton):
    changed = pyqtSignal(str)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_color(color)
        self.clicked.connect(self._pick)

    def set_color(self, color):
        self.color = color
        self.setStyleSheet(f"QPushButton {{ background: {color}; border: 1px solid rgba(255,255,255,60); border-radius: 6px; }}")

    def _pick(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Pick a color")
        if c.isValid():
            self.set_color(c.name())
            self.changed.emit(c.name())


class SettingsDialog(QDialog):
    changed = pyqtSignal(dict)      # the whole viz settings, live as you change them

    def __init__(self, viz, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hours N Silence settings")
        self.setModal(False)
        self.viz = copy.deepcopy(viz)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        head = QLabel("VISUALIZER")
        head.setObjectName("heading")
        root.addWidget(head)
        self.enabled = QCheckBox("Show the visualizer in the mini player")
        self.enabled.setChecked(bool(self.viz.get("enabled", True)))
        self.enabled.toggled.connect(self._push)
        root.addWidget(self.enabled)

        source = QLabel("COLORS")
        source.setObjectName("heading")
        root.addWidget(source)
        self.from_cover = QRadioButton("From the cover art: every part gets its own color from the art")
        self.custom = QRadioButton("My colors, chosen below")
        (self.from_cover if self.viz.get("palette_mode", "cover") == "cover" else self.custom).setChecked(True)
        self.from_cover.toggled.connect(self._push)
        root.addWidget(self.from_cover)
        root.addWidget(self.custom)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self.rows = {}
        for i, (key, el) in enumerate(self.viz["elements"].items()):
            on = QCheckBox(el["label"])
            on.setChecked(bool(el["on"]))
            on.toggled.connect(self._push)
            btn = ColorButton(el["color"])
            btn.changed.connect(self._push)
            grid.addWidget(on, i, 0)
            grid.addWidget(btn, i, 1)
            self.rows[key] = (on, btn)
        root.addLayout(grid)

        self.cover = QCheckBox("Kick sparks use the cover's colors instead of one color")
        self.cover.setChecked(bool(self.viz.get("kick_from_cover", True)))
        self.cover.toggled.connect(self._push)
        root.addWidget(self.cover)

        row = QHBoxLayout()
        lab = QLabel("How much")
        lab.setObjectName("subtitle")
        self.intensity = QSlider(Qt.Orientation.Horizontal)
        self.intensity.setRange(20, 200)
        self.intensity.setValue(int(float(self.viz.get("intensity", 1.0)) * 100))
        self.intensity.valueChanged.connect(self._push)
        row.addWidget(lab)
        row.addWidget(self.intensity, 1)
        root.addLayout(row)

        buttons = QHBoxLayout()
        reset = QPushButton("Reset colors")
        reset.setObjectName("flat")
        reset.clicked.connect(self._reset)
        close = QPushButton("Done")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        buttons.addWidget(close)
        root.addLayout(buttons)
        # grey out the color pickers while the cover is in charge
        custom = self.custom.isChecked()
        for _, btn in self.rows.values():
            btn.setEnabled(custom)
        self.cover.setEnabled(custom)

    def _reset(self):
        for key, (on, btn) in self.rows.items():
            btn.set_color(DEFAULT_VIZ["elements"][key]["color"])
        self._push()

    def _push(self, *_):
        self.viz["enabled"] = self.enabled.isChecked()
        self.viz["palette_mode"] = "cover" if self.from_cover.isChecked() else "custom"
        custom = self.viz["palette_mode"] == "custom"
        for _, btn in self.rows.values():
            btn.setEnabled(custom)
        self.cover.setEnabled(custom)
        self.viz["kick_from_cover"] = self.cover.isChecked()
        self.viz["intensity"] = self.intensity.value() / 100.0
        for key, (on, btn) in self.rows.items():
            self.viz["elements"][key]["on"] = on.isChecked()
            self.viz["elements"][key]["color"] = btn.color
        self.changed.emit(copy.deepcopy(self.viz))

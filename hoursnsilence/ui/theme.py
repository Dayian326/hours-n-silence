"""Dark glass theme.

The rules for glass that stays readable, per the usual guidance: panel fill
is white at 8 to 16 percent over the blurred desktop, one 1 px white edge at
12 to 18 percent, a faint highlight along the top, and text always light.
The accent follows the playing song's art (the chameleon), so the stylesheet
is built from a function, not fixed. The default accent is a pink pulled
from the Her Loss cover's backdrop hue.
"""

BG = "#0e0e10"
PANEL = "#17171b"
PANEL_2 = "#1f1f24"
BORDER = "#2a2a31"
TEXT = "#f2f2f5"
MUTED = "#a3a3ad"
ACCENT = "#dc6ab0"

_current = {"accent": ACCENT, "glass": True}


def accent():
    return _current["accent"]


def set_accent(color):
    _current["accent"] = color or ACCENT


def set_glass(on):
    _current["glass"] = bool(on)


def darker(hex_color, factor=0.8):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def _glass_fill(alpha, highlight=10):
    """Black glass: a dark tinted pane with only a whisper of light along the top edge."""
    return (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 rgba(255, 255, 255, {highlight}), "
            f"stop:0.06 rgba(0, 0, 0, {alpha}), "
            f"stop:1 rgba(0, 0, 0, {alpha}))")


def build_qss(accent_color=None):
    a = accent_color or _current["accent"]
    a_dim = darker(a)
    glass = _current["glass"]
    root_bg = "transparent" if glass else BG
    panel_bg = _glass_fill(120) if glass else PANEL
    card_bg = _glass_fill(150) if glass else PANEL
    edge = "rgba(255, 255, 255, 30)"
    edge_soft = "rgba(255, 255, 255, 20)"
    return f"""
* {{
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QWidget#root {{ background: {root_bg}; }}
QWidget#panel, QFrame#panel {{ background: {panel_bg}; border: 1px solid {edge_soft}; border-radius: 14px; }}
QWidget#card, QFrame#card {{ background: {card_bg}; border: 1px solid {edge}; border-radius: 12px; }}
QFrame#glass {{ background: {_glass_fill(130)}; border: 1px solid {edge}; border-radius: 16px; }}
QFrame#playerbar {{ background: {_glass_fill(140)}; border: 1px solid {rgba(a, 80)}; border-radius: 14px; }}

QLineEdit {{
    background: rgba(255, 255, 255, 16); border: 1px solid {edge_soft}; border-radius: 8px;
    padding: 6px 10px; selection-background-color: {a};
}}
QLineEdit:focus {{ border-color: {rgba(a, 160)}; }}

QListWidget, QTableWidget, QTreeWidget {{
    background: transparent; border: none; outline: none; border-radius: 10px;
}}
QListView#tracks, QListView#tracks::viewport {{ background: transparent; border: none; outline: none; }}
QListView#tracks::item {{ background: transparent; border: none; }}
QTreeWidget::item, QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: rgba(255,255,255,30); color: {TEXT}; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: rgba(255,255,255,16); }}
QHeaderView::section {{
    background: transparent; color: {MUTED}; border: none; padding: 6px 8px;
    border-bottom: 1px solid {edge_soft}; font-weight: 600;
}}

QPushButton {{
    background: transparent; border: none; border-radius: 16px; padding: 6px;
    color: {TEXT};
}}
QPushButton:hover {{ background: rgba(255,255,255,22); }}
QPushButton:pressed {{ background: rgba(255,255,255,36); }}
QPushButton#primary {{ background: {a}; color: white; padding: 9px 14px; border-radius: 8px; font-weight: 600; }}
QPushButton#primary:hover {{ background: {a_dim}; }}
QPushButton#glassbtn {{ background: rgba(255,255,255,26); border: 1px solid {edge}; padding: 9px 14px; border-radius: 8px; font-weight: 600; }}
QPushButton#glassbtn:hover {{ background: rgba(255,255,255,44); }}
QPushButton#flat {{ color: {MUTED}; padding: 4px 8px; border-radius: 6px; }}
QPushButton#flat:hover {{ color: {TEXT}; background: rgba(255,255,255,22); }}
QPushButton#mode {{ color: {MUTED}; padding: 2px 8px; border-radius: 6px; font-size: 16px; }}
QPushButton#mode:hover {{ color: {TEXT}; background: rgba(255,255,255,22); }}
QPushButton#mode[active="true"] {{ color: {a}; }}
QPushButton#time {{ color: {MUTED}; font-size: 12px; padding: 2px 4px; border-radius: 4px; }}
QPushButton#time:hover {{ color: {TEXT}; }}

QSlider::groove:horizontal {{ height: 4px; background: rgba(255,255,255,50); border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {a}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: {TEXT};
}}
QSlider::handle:horizontal:hover {{ background: white; }}

QLabel#title {{ font-size: 14px; font-weight: 600; }}
QLabel#bigtitle {{ font-size: 24px; font-weight: 700; }}
QLabel#description {{ color: #d6d6dd; font-size: 13px; }}
QLabel#subtitle {{ color: {MUTED}; }}
QLabel#status {{ color: {MUTED}; font-size: 12px; }}
QLabel#signature {{ color: rgba(163, 163, 173, 150); font-size: 11px; }}
QLabel#heading {{ color: {MUTED}; font-size: 12px; font-weight: 600; letter-spacing: 1px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,60); border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}

QMenu {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
QMenu::item:selected {{ background: {BORDER}; }}
QSplitter::handle {{ background: transparent; width: 8px; }}
QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""


QSS = build_qss()


def fmt_time(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 60}:{seconds % 60:02d}"

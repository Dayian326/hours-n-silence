"""Dark theme. Palette borrowed in spirit from Sidra: near-black panels,
soft grey text, one warm accent. The accent follows the playing song's art
(the chameleon), so the stylesheet is built from a function, not fixed."""

BG = "#0e0e10"
PANEL = "#17171b"
PANEL_2 = "#1f1f24"
BORDER = "#2a2a31"
TEXT = "#ececef"
MUTED = "#8b8b95"
ACCENT = "#fa586a"

_current = {"accent": ACCENT}


def accent():
    return _current["accent"]


def set_accent(color):
    _current["accent"] = color or ACCENT


def darker(hex_color, factor=0.8):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def build_qss(accent_color=None):
    a = accent_color or _current["accent"]
    a_dim = darker(a)
    return f"""
* {{
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget#panel, QFrame#panel {{ background: {PANEL}; border-radius: 10px; }}
QWidget#card, QFrame#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px; }}
QFrame#glass {{ background: rgba(23, 23, 27, 190); border: 1px solid rgba(255, 255, 255, 22); border-radius: 16px; }}

QLineEdit {{
    background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 6px 10px; selection-background-color: {a};
}}
QLineEdit:focus {{ border-color: {a_dim}; }}

QListWidget, QTableWidget, QTreeWidget {{
    background: {PANEL}; border: none; outline: none; border-radius: 10px;
    alternate-background-color: {PANEL};
}}
QListView#tracks, QListView#tracks::viewport {{ background: transparent; border: none; outline: none; }}
QListView#tracks::item {{ background: transparent; border: none; }}
QTreeWidget::item, QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: {PANEL_2}; color: {TEXT}; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {PANEL_2}; }}
QHeaderView::section {{
    background: {PANEL}; color: {MUTED}; border: none; padding: 6px 8px;
    border-bottom: 1px solid {BORDER}; font-weight: 600;
}}

QPushButton {{
    background: transparent; border: none; border-radius: 16px; padding: 6px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {PANEL_2}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton#primary {{ background: {a}; color: white; padding: 9px 14px; border-radius: 8px; font-weight: 600; }}
QPushButton#primary:hover {{ background: {a_dim}; }}
QPushButton#glassbtn {{ background: rgba(255,255,255,20); border: 1px solid rgba(255,255,255,30); padding: 9px 14px; border-radius: 8px; font-weight: 600; }}
QPushButton#glassbtn:hover {{ background: rgba(255,255,255,34); }}
QPushButton#flat {{ color: {MUTED}; padding: 4px 8px; border-radius: 6px; }}
QPushButton#flat:hover {{ color: {TEXT}; background: {PANEL_2}; }}
QPushButton#mode {{ color: {MUTED}; padding: 2px 8px; border-radius: 6px; font-size: 16px; }}
QPushButton#mode:hover {{ color: {TEXT}; background: {PANEL_2}; }}
QPushButton#mode[active="true"] {{ color: {a}; }}
QPushButton#time {{ color: {MUTED}; font-size: 12px; padding: 2px 4px; border-radius: 4px; }}
QPushButton#time:hover {{ color: {TEXT}; }}

QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {a}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: {TEXT};
}}
QSlider::handle:horizontal:hover {{ background: white; }}

QLabel#title {{ font-size: 14px; font-weight: 600; }}
QLabel#bigtitle {{ font-size: 24px; font-weight: 700; }}
QLabel#description {{ color: #c9c9d1; font-size: 13px; }}
QLabel#subtitle {{ color: {MUTED}; }}
QLabel#status {{ color: {MUTED}; font-size: 12px; }}
QLabel#heading {{ color: {MUTED}; font-size: 12px; font-weight: 600; letter-spacing: 1px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}

QMenu {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
QMenu::item:selected {{ background: {BORDER}; }}
QSplitter::handle {{ background: {BG}; width: 8px; }}
QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""


QSS = build_qss()


def fmt_time(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 60}:{seconds % 60:02d}"

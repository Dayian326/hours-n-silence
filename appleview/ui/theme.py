"""Dark theme. Palette borrowed in spirit from Sidra: near-black panels,
soft grey text, one warm accent."""

BG = "#0e0e10"
PANEL = "#17171b"
PANEL_2 = "#1f1f24"
BORDER = "#2a2a31"
TEXT = "#ececef"
MUTED = "#8b8b95"
ACCENT = "#fa586a"
ACCENT_DIM = "#c9414f"

QSS = f"""
* {{
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget#panel {{ background: {PANEL}; border-radius: 10px; }}
QWidget#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px; }}

QLineEdit {{
    background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 6px 10px; selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border-color: {ACCENT_DIM}; }}

QListWidget, QTableWidget, QTreeWidget {{
    background: {PANEL}; border: none; outline: none; border-radius: 10px;
    alternate-background-color: {PANEL};
}}
QTreeWidget::item, QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: {PANEL_2}; color: {TEXT}; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {PANEL_2}; }}
QTreeWidget::branch {{ background: {PANEL}; }}
QTableWidget {{ gridline-color: transparent; }}
QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid {BG}; }}
QTableWidget::item:selected {{ background: {PANEL_2}; color: {TEXT}; }}
QHeaderView::section {{
    background: {PANEL}; color: {MUTED}; border: none; padding: 6px 8px;
    border-bottom: 1px solid {BORDER}; font-weight: 600;
}}
QTableCornerButton::section {{ background: {PANEL}; border: none; }}

QPushButton {{
    background: transparent; border: none; border-radius: 16px; padding: 6px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {PANEL_2}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton#primary {{ background: {ACCENT}; color: white; padding: 6px 14px; border-radius: 8px; }}
QPushButton#primary:hover {{ background: {ACCENT_DIM}; }}
QPushButton#flat {{ color: {MUTED}; padding: 4px 8px; border-radius: 6px; }}
QPushButton#flat:hover {{ color: {TEXT}; background: {PANEL_2}; }}
QPushButton#mode {{ color: {MUTED}; padding: 2px 8px; border-radius: 6px; font-size: 16px; }}
QPushButton#mode:hover {{ color: {TEXT}; background: {PANEL_2}; }}
QPushButton#mode[active="true"] {{ color: {ACCENT}; }}
QPushButton#time {{ color: {MUTED}; font-size: 12px; padding: 2px 4px; border-radius: 4px; }}
QPushButton#time:hover {{ color: {TEXT}; }}

QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: {TEXT};
}}
QSlider::handle:horizontal:hover {{ background: white; }}

QLabel#title {{ font-size: 14px; font-weight: 600; }}
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


def fmt_time(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 60}:{seconds % 60:02d}"

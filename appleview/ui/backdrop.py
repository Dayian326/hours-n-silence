"""The blurred cover that fills the playlist page behind the panels."""

import os

from PIL import Image, ImageFilter
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

from ..cache import CACHE_DIR

_BLUR_DIR = os.path.join(CACHE_DIR, "blur")
os.makedirs(_BLUR_DIR, exist_ok=True)


def blurred_path(image_path):
    """A small, heavily blurred copy of the image, cached on disk. "" if it can't be made."""
    if not image_path or not os.path.exists(image_path):
        return ""
    key = os.path.splitext(os.path.basename(image_path))[0]
    out = os.path.join(_BLUR_DIR, f"{key}.png")
    try:
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(image_path):
            return out
        im = Image.open(image_path).convert("RGB")
        im.thumbnail((160, 160))
        im = im.filter(ImageFilter.GaussianBlur(22))
        im.save(out, "PNG")
        return out
    except Exception:
        return ""


class Backdrop(QWidget):
    """Sits behind everything in the page; the page keeps it sized to itself."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pix = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_image(self, image_path):
        p = blurred_path(image_path)
        pix = QPixmap(p) if p else QPixmap()
        self._pix = None if pix.isNull() else pix
        self.update()

    def paintEvent(self, _e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = self.rect()
        painter.fillRect(r, QColor("#17171b"))
        if self._pix is not None:
            # overscan a little so the blur's soft edges never show
            scaled = self._pix.scaled(int(r.width() * 1.15), int(r.height() * 1.15),
                                      Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
            painter.setOpacity(0.85)
            painter.drawPixmap(r.center().x() - scaled.width() // 2, r.center().y() - scaled.height() // 2, scaled)
            painter.setOpacity(1.0)
        grad = QLinearGradient(0, 0, r.width(), 0)
        grad.setColorAt(0.0, QColor(14, 14, 16, 70))
        grad.setColorAt(1.0, QColor(14, 14, 16, 150))
        painter.fillRect(r, grad)
        painter.end()

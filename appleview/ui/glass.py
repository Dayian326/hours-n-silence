"""Frosted glass and a dark title bar, straight from Windows.

Windows 11 can blur whatever is behind a window (the same effect its own
menus and flyouts use). We ask for it per window with two calls into the
desktop window manager. Older builds fall back to the acrylic blur that
Windows 10 exposed. If neither works the window just stays dark and flat.
"""

import ctypes
from ctypes import wintypes

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_TRANSIENTWINDOW = 3          # acrylic
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19


class _MARGINS(ctypes.Structure):
    _fields_ = [("left", ctypes.c_int), ("right", ctypes.c_int), ("top", ctypes.c_int), ("bottom", ctypes.c_int)]


class _ACCENT_POLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class _WCA_DATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]


def _hwnd(widget):
    return wintypes.HWND(int(widget.winId()))


DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def _colorref(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return ctypes.c_uint((b << 16) | (g << 8) | r)


def dark_title_bar(widget, caption="#17171b", text="#ececef"):
    """Dark title bar even when Windows is set to color title bars with its accent."""
    try:
        dwm = ctypes.windll.dwmapi
        value = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(_hwnd(widget), DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
        for attr, color in ((DWMWA_CAPTION_COLOR, caption), (DWMWA_TEXT_COLOR, text)):
            c = _colorref(color)
            dwm.DwmSetWindowAttribute(_hwnd(widget), attr, ctypes.byref(c), ctypes.sizeof(c))
    except Exception:
        pass


def _dwm_acrylic(widget):
    dwm = ctypes.windll.dwmapi
    margins = _MARGINS(-1, -1, -1, -1)
    if dwm.DwmExtendFrameIntoClientArea(_hwnd(widget), ctypes.byref(margins)) != 0:
        return False
    kind = ctypes.c_int(DWMSBT_TRANSIENTWINDOW)
    return dwm.DwmSetWindowAttribute(_hwnd(widget), DWMWA_SYSTEMBACKDROP_TYPE,
                                     ctypes.byref(kind), ctypes.sizeof(kind)) == 0


def _legacy_acrylic(widget, tint):
    r, g, b, a = tint
    policy = _ACCENT_POLICY(ACCENT_ENABLE_ACRYLICBLURBEHIND, 2, (a << 24) | (b << 16) | (g << 8) | r, 0)
    data = _WCA_DATA(WCA_ACCENT_POLICY, ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p), ctypes.sizeof(policy))
    fn = ctypes.windll.user32.SetWindowCompositionAttribute
    fn.argtypes = [wintypes.HWND, ctypes.POINTER(_WCA_DATA)]
    return bool(fn(_hwnd(widget), ctypes.byref(data)))


def apply_glass(widget, tint=(23, 23, 27, 200)):
    """Frost the area behind this top-level window. Returns which method took."""
    dark_title_bar(widget)
    try:
        if _dwm_acrylic(widget):
            return "dwm"
    except Exception:
        pass
    try:
        if _legacy_acrylic(widget, tint):
            return "legacy"
    except Exception:
        pass
    return "none"

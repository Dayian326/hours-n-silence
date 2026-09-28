"""Frosted glass, rounded corners and a dark title bar, straight from Windows.

Windows can blur whatever is behind a window (the same effect its own menus
and flyouts use). We ask for the older acrylic blur first because it lets us
choose how dark the tint is; the newer Windows 11 backdrop is the fallback
(its tint is fixed and quite heavy). Windows 11 also rounds the corners of
frameless windows for us, so the blur is clipped to the card shape.
"""

import ctypes
from ctypes import wintypes

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_TRANSIENTWINDOW = 3          # acrylic
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19

# tint over the blur: dark, but see-through enough that the desktop reads
GLASS_TINT = (8, 8, 10, 0xB4)     # black glass: mostly dark, the desktop only ghosts through


class _MARGINS(ctypes.Structure):
    _fields_ = [("left", ctypes.c_int), ("right", ctypes.c_int), ("top", ctypes.c_int), ("bottom", ctypes.c_int)]


class _ACCENT_POLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class _WCA_DATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]


def _hwnd(widget):
    return wintypes.HWND(int(widget.winId()))


def _set_attr(widget, attr, value):
    ctypes.windll.dwmapi.DwmSetWindowAttribute(_hwnd(widget), attr, ctypes.byref(value), ctypes.sizeof(value))


def _colorref(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return ctypes.c_uint((b << 16) | (g << 8) | r)


def dark_title_bar(widget, caption="#151518", text="#ececef"):
    """Dark title bar even when Windows is set to color title bars with its accent."""
    try:
        _set_attr(widget, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.c_int(1))
        _set_attr(widget, DWMWA_CAPTION_COLOR, _colorref(caption))
        _set_attr(widget, DWMWA_TEXT_COLOR, _colorref(text))
    except Exception:
        pass


def round_corners(widget):
    try:
        _set_attr(widget, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.c_int(DWMWCP_ROUND))
    except Exception:
        pass


def _legacy_acrylic(widget, tint):
    r, g, b, a = tint
    policy = _ACCENT_POLICY(ACCENT_ENABLE_ACRYLICBLURBEHIND, 2, (a << 24) | (b << 16) | (g << 8) | r, 0)
    data = _WCA_DATA(WCA_ACCENT_POLICY, ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p), ctypes.sizeof(policy))
    fn = ctypes.windll.user32.SetWindowCompositionAttribute
    fn.argtypes = [wintypes.HWND, ctypes.POINTER(_WCA_DATA)]
    return bool(fn(_hwnd(widget), ctypes.byref(data)))


def _dwm_acrylic(widget):
    dwm = ctypes.windll.dwmapi
    margins = _MARGINS(-1, -1, -1, -1)
    if dwm.DwmExtendFrameIntoClientArea(_hwnd(widget), ctypes.byref(margins)) != 0:
        return False
    return dwm.DwmSetWindowAttribute(_hwnd(widget), DWMWA_SYSTEMBACKDROP_TYPE,
                                     ctypes.byref(ctypes.c_int(DWMSBT_TRANSIENTWINDOW)),
                                     ctypes.sizeof(ctypes.c_int)) == 0


def apply_glass(widget, tint=GLASS_TINT, frameless=False):
    """Frost the area behind this top-level window. Returns which method took."""
    if frameless:
        round_corners(widget)
    else:
        dark_title_bar(widget)
    try:
        if _legacy_acrylic(widget, tint):
            return "acrylic"
    except Exception:
        pass
    try:
        if _dwm_acrylic(widget):
            return "dwm"
    except Exception:
        pass
    return "none"

"""Screenshot helper for checking the UI without eyes on the monitor.

    python tools/shot.py out.png            whole primary screen
    python tools/shot.py out.png AppleView  just the window with that title
"""

import sys

from PIL import ImageGrab


def main():
    out = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None
    bbox = None
    if title:
        import win32gui
        found = []

        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == title:
                found.append(hwnd)
        win32gui.EnumWindows(cb, None)
        if not found:
            print("no window titled", title)
            return 1
        left, top, right, bottom = win32gui.GetWindowRect(found[0])
        bbox = (left, top, right, bottom)
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    img.save(out)
    print("saved", out, img.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())

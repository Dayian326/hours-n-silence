"""Make AppleView something you can pin to the taskbar.

    python tools/make_shortcut.py

Draws the icon file (assets/appleview.ico), then creates an AppleView shortcut
in the Start Menu and on the Desktop. The shortcut runs the app without a
console window and carries the same taskbar identity the app claims for
itself, which is what lets Windows pin it properly.

After running this once: open AppleView from the Start Menu or Desktop,
right-click its taskbar icon, Pin to taskbar. Safe to run again any time.
"""

import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
ICON = os.path.join(ASSETS, "appleview.ico")
APP_ID = "Dayian.AppleView"
ACCENT = (250, 88, 106, 255)
DARK = (14, 14, 16, 255)


def draw_icon():
    os.makedirs(ASSETS, exist_ok=True)
    frames = []
    for size in (256, 128, 64, 48, 32, 16):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        pad = max(1, size // 16)
        d.ellipse((pad, pad, size - pad, size - pad), fill=ACCENT)
        hole = size // 4
        c = size / 2
        d.ellipse((c - hole / 2, c - hole / 2, c + hole / 2, c + hole / 2), fill=DARK)
        frames.append(img)
    frames[0].save(ICON, format="ICO", sizes=[f.size for f in frames], append_images=frames[1:])
    return ICON


def make_shortcut(folder):
    import pythoncom
    from win32com.propsys import propsys, pscon
    from win32com.shell import shell

    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    path = os.path.join(folder, "AppleView.lnk")

    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER,
                                      shell.IID_IShellLink)
    link.SetPath(pythonw)
    link.SetArguments("-m appleview")
    link.SetWorkingDirectory(ROOT)
    link.SetIconLocation(ICON, 0)
    link.SetDescription("AppleView music player")

    store = link.QueryInterface(propsys.IID_IPropertyStore)
    store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(APP_ID))
    store.Commit()

    link.QueryInterface(pythoncom.IID_IPersistFile).Save(path, 0)
    return path


def main():
    print("icon:", draw_icon())
    start_menu = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs")
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    for folder in (start_menu, desktop):
        if os.path.isdir(folder):
            print("shortcut:", make_shortcut(folder))
    print("Now open AppleView from the Start Menu, right-click its taskbar icon, Pin to taskbar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

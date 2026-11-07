"""Run with python -m image_swiper."""
import tkinter as tk
from . import app_icon
from .app import ImageOrganizer

def main():
    import sys
    if '--version' in sys.argv:
        from .version import __version__
        print(__version__)
        return
    if sys.platform == 'win32':
        # Render at the display's real resolution instead of a blurry bitmap stretch.
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    # The icon is embedded in the package, so the build ships no loose icon file.
    root._app_icons = [tk.PhotoImage(data=data) for data in app_icon.WINDOW]
    root.iconphoto(True, *root._app_icons)
    ImageOrganizer(root)
    root.mainloop()

if __name__ == "__main__":
    main()

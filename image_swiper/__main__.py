"""Run with python -m image_swiper."""
import tkinter as tk
from pathlib import Path
from .app import ImageOrganizer

def main():
    import sys
    if '--version' in sys.argv:
        from .version import __version__
        print(__version__)
        return
    root = tk.Tk()
    # __file__ also resolves inside PyInstaller's bundled resources.
    icon_path = Path(__file__).resolve().parent.parent / 'docs' / 'assets' / 'image-swiper-icon-v2.png'
    root._app_icon = tk.PhotoImage(file=str(icon_path))
    root.iconphoto(True, root._app_icon)
    ImageOrganizer(root)
    root.mainloop()

if __name__ == "__main__":
    main()

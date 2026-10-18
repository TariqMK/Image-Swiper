"""Run with python -m image_swiper."""
import tkinter as tk
from .app import ImageOrganizer

def main():
    import sys
    if '--version' in sys.argv:
        from .version import __version__
        print(__version__)
        return
    root = tk.Tk()
    ImageOrganizer(root)
    root.mainloop()

if __name__ == "__main__":
    main()

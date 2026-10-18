"""Run with python -m image_swiper."""
import tkinter as tk
from .app import ImageOrganizer

def main():
    root = tk.Tk()
    ImageOrganizer(root)
    root.mainloop()

if __name__ == "__main__":
    main()

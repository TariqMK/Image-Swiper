"""Takes the README screenshots from the real app, filled with generated sample photos.

Writes:
  assets/screenshots/review.png        A folder part-way through review, with one deletion
  assets/screenshots/on-this-day.png   On This Day, showing today's date in earlier years

Sample photos are drawn by this script into a temporary folder; the app's cache and recent
folders also go there, so your own files and settings are never read or changed. Nothing
is deleted: the deleted frame on the contact strip is set directly. The window is drawn at
2x (1120 x 720 px layout, saved as 2240 x 1440 px).

Run from the repository root on Windows, with the app's dependencies installed and the
window free to appear on screen for a few seconds:
  python assets/make_screenshots.py --version v3.0.2
--version is the release tag shown in the toolbar; it defaults to the newest local git tag.
"""

import argparse
import ctypes
import math
import random
import subprocess
import sys
import tempfile
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path

import piexif
from PIL import Image, ImageDraw, ImageFilter, ImageGrab

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'screenshots'
SCALE = 2.0             # Layout pixels to screenshot pixels.
WINDOW = (1120, 720)    # Layout size of the window's content.


# ---- Sample photos ----------------------------------------------------------------------

def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def ridge(rng, width, base, roughness, steps=9):
    """A mountain ridge line by midpoint displacement."""
    points = [base + rng.uniform(-roughness, roughness), base + rng.uniform(-roughness, roughness)]
    spread = roughness
    for _ in range(steps):
        spread *= 0.55
        nxt = []
        for a, b in zip(points, points[1:]):
            nxt += [a, (a + b) / 2 + rng.uniform(-spread, spread)]
        points = nxt + [points[-1]]
    step = width / (len(points) - 1)
    return [(i * step, y) for i, y in enumerate(points)]


SCENES = [
    # sky top, sky horizon, sun colour, land near colour, has water
    ((24, 44, 92), (246, 160, 102), (255, 226, 170), (28, 30, 44), True),
    ((60, 122, 196), (178, 214, 238), (255, 252, 236), (38, 74, 56), False),
    ((18, 22, 48), (120, 74, 128), (250, 206, 214), (22, 20, 36), True),
    ((96, 150, 204), (232, 222, 196), (255, 246, 214), (86, 98, 62), False),
    ((34, 58, 96), (240, 120, 76), (255, 204, 128), (40, 26, 34), False),
    ((140, 180, 214), (230, 236, 240), (255, 255, 255), (60, 88, 104), True),
    ((44, 90, 140), (156, 206, 222), (255, 250, 230), (24, 66, 70), True),
    ((64, 40, 86), (236, 150, 120), (255, 220, 170), (40, 30, 52), False),
]


def scene(seed, size, palette):
    rng = random.Random(seed)
    w, h = size
    top, horizon, sun, near, water = palette
    image = Image.new('RGB', size)
    draw = ImageDraw.Draw(image)
    horizon_y = h * rng.uniform(0.55, 0.68)
    for y in range(h):
        draw.line([(0, y), (w, y)], fill=lerp(top, horizon, min(1, y / horizon_y) ** 1.4))

    glow = Image.new('L', size, 0)
    sx, sy, r = w * rng.uniform(0.25, 0.75), horizon_y * rng.uniform(0.45, 0.85), h * 0.06
    ImageDraw.Draw(glow).ellipse([sx - r * 3, sy - r * 3, sx + r * 3, sy + r * 3], fill=110)
    glow = glow.filter(ImageFilter.GaussianBlur(r * 1.6))
    image = Image.composite(Image.new('RGB', size, sun), image, glow)
    draw = ImageDraw.Draw(image)
    draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=sun)

    layers = 4
    for i in range(layers):
        depth = i / (layers - 1)
        colour = lerp(lerp(horizon, top, 0.35), near, 0.35 + 0.65 * depth)
        base = horizon_y - h * 0.16 * (1 - depth) + (h * 0.05 if water else h * 0.12) * depth
        line = ridge(rng, w, base, h * (0.10 - 0.05 * depth))
        draw.polygon(line + [(w, h), (0, h)], fill=colour)

    if water:
        water_top = round(horizon_y + h * 0.10)
        band = image.crop((0, water_top - (h - water_top), w, water_top)).transpose(
            Image.Transpose.FLIP_TOP_BOTTOM)
        tint = Image.new('RGB', band.size, lerp(top, near, 0.5))
        reflection = Image.blend(band, tint, 0.45).filter(ImageFilter.GaussianBlur(3))
        image.paste(reflection, (0, water_top))
        # A few soft glints under the sun.
        glints = Image.new('L', size, 0)
        draw = ImageDraw.Draw(glints)
        for _ in range(28):
            y = rng.uniform(water_top + h * 0.02, h)
            x = sx + rng.gauss(0, w * 0.06) * (1 + (y - water_top) / h)
            length = rng.uniform(w * 0.01, w * 0.05)
            draw.line([(x - length, y), (x + length, y)], fill=120, width=max(2, h // 400))
        glints = glints.filter(ImageFilter.GaussianBlur(2))
        image = Image.composite(Image.new('RGB', size, lerp(sun, horizon, 0.3)), image, glints)

    grain = Image.effect_noise(size, 10).convert('RGB')
    return Image.blend(image, grain, 0.04)


def make_samples(folder: Path) -> None:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rng = random.Random(7)
    files = []
    # Ten photos from the last two years, two of them portrait.
    for i in range(10):
        taken = today - timedelta(days=rng.randint(20, 700), minutes=rng.randint(420, 1100))
        files.append((f'IMG_{4210 + i * 3}.jpg', taken, (2400, 1600) if i not in (3, 7) else (1600, 2400)))
    # Four photos from today's date in earlier years, for On This Day.
    for years in (2, 5, 8, 11):
        taken = today.replace(year=today.year - years) + timedelta(hours=rng.randint(9, 18),
                                                                   minutes=rng.randint(0, 59))
        files.append((f'DSC_{1000 + years * 37}.jpg', taken, (2400, 1600)))
    for n, (name, taken, size) in enumerate(files):
        picture = scene(n * 11 + 3, size, SCENES[n % len(SCENES)])
        stamp = taken.strftime('%Y:%m:%d %H:%M:%S').encode()
        exif = piexif.dump({'0th': {piexif.ImageIFD.Make: b'Sample', piexif.ImageIFD.Model: b'Camera'},
                            'Exif': {piexif.ExifIFD.DateTimeOriginal: stamp}})
        picture.save(folder / name, quality=95, subsampling=0, exif=exif)


# ---- Driving the app --------------------------------------------------------------------

def newest_tag() -> str | None:
    result = subprocess.run(['git', 'tag', '--sort=-v:refname'], cwd=ROOT,
                            capture_output=True, text=True)
    tags = result.stdout.split()
    return tags[0] if tags else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', default=newest_tag(),
                        help='Release tag to show in the toolbar, for example v3.0.2.')
    args = parser.parse_args()
    if not args.version:
        sys.exit('No release tag found. Pass --version, for example --version v3.0.2.')
    if sys.platform != 'win32':
        sys.exit('This script captures the window with Windows APIs; run it on Windows.')

    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    sys.path.insert(0, str(ROOT))
    # Show the release version, not the development one, in this process only.
    import image_swiper.version
    image_swiper.version.__version__ = args.version.lstrip('v')
    import image_swiper.app as app_module
    from image_swiper import app_icon, paths, theme

    work = Path(tempfile.mkdtemp(prefix='image-swiper-shots-'))
    samples = work / 'Holiday photos'
    samples.mkdir()
    make_samples(samples)
    app_module.runtime_paths = lambda: paths.runtime_paths(work / 'app')
    (work / 'app').mkdir()

    original_init = theme.Theme.__init__

    def fixed_scale(self, root):
        original_init(self, root)
        self.scale = SCALE
    theme.Theme.__init__ = fixed_scale

    root = tk.Tk()
    root._icons = [tk.PhotoImage(data=data) for data in app_icon.WINDOW]
    root.iconphoto(True, *root._icons)
    app = app_module.ImageOrganizer(root)
    width, height = (round(v * SCALE) for v in WINDOW)
    root.geometry(f'{width}x{height}+40+40')
    root.attributes('-topmost', True)
    OUT.mkdir(parents=True, exist_ok=True)

    def capture(name):
        # The real temporary path would show your user name; show a neutral one instead.
        app.path_label.config(text=' D:\\Pictures\\Holiday photos')
        root.update()
        x, y = root.winfo_rootx(), root.winfo_rooty()
        shot = ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height()),
                              all_screens=True)
        shot.save(OUT / f'{name}.png', optimize=True)
        print(f'Wrote assets/screenshots/{name}.png ({shot.width} x {shot.height} px)')

    def when_scanned(then):
        if app._scanning or not app.images:
            root.after(100, lambda: when_scanned(then))
        else:
            root.after(1200, then)

    def review():
        # Seven photos in: one deleted, the rest kept. Set directly so nothing is deleted.
        app.current_index = 6
        app.deleted_indices = {3}
        app.processed_count, app.deleted_count, app.space_saved_mb = 6, 1, 2.4
        app.show_current_image()
        root.after(1200, lambda: (capture('review'), on_this_day()))

    def on_this_day():
        app.processed_count, app.deleted_count, app.space_saved_mb = 0, 0, 0
        app.this_day_var.set(True)
        app.toggle_this_day()
        def second_photo():
            app.current_index = 1
            app.show_current_image()
            root.after(1200, lambda: (capture('on-this-day'), app.close()))
        when_scanned(second_photo)

    root.after(500, lambda: (app.open_review_folder(str(samples)), when_scanned(review)))
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())

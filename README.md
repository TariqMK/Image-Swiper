# Image Swiper

A desktop app for Windows, Apple Silicon macOS and Linux for reviewing photos and videos one at a time, keeping the
ones you want and sending unwanted files to the Recycle Bin. Built with Python,
Tkinter, Pillow and SQLite.

## Features

- Photo previews, with optional HEIC/HEIF and RAW decoding.
- Video thumbnails through FFmpeg; centre-click opens the default video player.
- Keyboard and canvas navigation, deletion and single-item undo.
- Natural filename sorting, date sorting and random order.
- Optional recursive folder scanning.
- **On This Day:** matches month and day across all years, sorted chronologically.
  Use the date arrows to review another day. The current year is included too.
- File dates, sizes and session review statistics.
- SQLite metadata caching and a tool to clean orphaned video thumbnails.

## Installation

Requires Python 3.10 or later with Tkinter. Windows supports delete and in-app undo;
macOS and Linux use native Trash with manual restoration through the file manager.
Linux source installations may need their distribution's Tkinter package.

## Release builds

The **Build release** GitHub Actions workflow runs manually only. Its form asks
for **draft/public** and **major/minor/patch** before building Windows x64,
Apple Silicon macOS (ARM64 only), and Linux x64 packages. Version allocation
includes existing drafts and tags. The GUI shows the tagged build's version
in muted text beside the title. See [release instructions](docs/releases.md)
for versioning, downloads, platform requirements and failure behavior.

## Running from source

From the project folder, create an environment and install the application:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[formats]"
.venv\Scripts\python.exe -m image_swiper
```

The `formats` extra installs `pillow-heif` and `rawpy`. For basic image support,
install with `pip install -e .` instead. Core dependencies include Pillow, piexif,
winshell and pywin32.

For video thumbnails and creation dates, install FFmpeg and ffprobe separately
and put both on `PATH`. Without them, videos use a placeholder preview and fall
back to file modification dates; playback still uses the default player.

The existing `Image_Swiper.bat` uses the existing `venv/` environment. The original
`python Image_Swiper.py` command also remains available.

## Usage

1. Set **Subdirectories** before selecting a folder; changing this toggle affects
   the next scan.
2. Click **Select Folder** and choose your media folder.
3. Browse normally, select **Sort by Date** or **Random**, or enable **On This Day**.
4. Review files with the controls below.

| Control | Action |
| --- | --- |
| `Q` / DELETE | Send the current file to the Recycle Bin or system Trash |
| `W` | Keep the current file and advance |
| Right arrow / right edge of preview | Next existing file |
| Left arrow / left edge of preview | Previous existing file |
| Backspace / UNDO | Windows: restore the most recent deletion, when available |
| Centre of video preview | Open video in the default player |
| Folder path | Open the containing folder in Explorer |
| Clean | Find orphaned thumbnails and request confirmation before removing them |

Keeping a file advances the viewer; it does not move or tag the original.
Windows deletion uses the Recycle Bin; macOS/Linux use native Trash and require
manual restoration through the system file manager. On Windows the app keeps one undo record, and the end-of-review
screen disables the undo button; files can also be restored through Windows.
The reported saved space is the size sent to the Recycle Bin, not necessarily
reclaimed disk space. Statistics count review actions rather than unique files.

## Screenshots

Place public README screenshots in `docs/screenshots/`, for example
`docs/screenshots/image-swiper.png`. PNG, JPG, JPEG and WebP files directly in
that folder are allowed through `.gitignore`.

Once the file exists, embed it with:

```markdown
![Image Swiper interface](docs/screenshots/image-swiper.png)
```

## Project structure

```text
Image Swiper/
|-- .github/workflows/release.yml # Manual release builds
|-- image_swiper/
|   |-- __main__.py       # Application entry point
|   |-- app.py            # Review state and action coordination
|   |-- ui.py             # Tkinter layout and bindings
|   |-- library.py        # Scanning, filtering and sorting
|   |-- media.py          # Decoding, previews and rendering
|   |-- metadata.py       # Dates and formatting
|   |-- cache.py          # SQLite cache and thumbnail cleanup
|   |-- recycle_bin.py    # Windows deletion and restoration
|   |-- version.py        # Version displayed in the GUI
|   `-- paths.py          # Private runtime paths and legacy migration
|-- data/                 # Private generated cache and thumbnails (ignored)
|-- Meta/                 # Private historical context (ignored)
|-- docs/
|   |-- architecture.md
|   `-- screenshots/      # Public documentation screenshots
|-- tests/
|-- scripts/              # Version allocation and packaging
|-- Image_Swiper.py       # Compatibility launcher
|-- Image_Swiper.bat      # Windows launcher using venv/
|-- pyproject.toml
`-- README.md
```

See [architecture notes](docs/architecture.md) for the module boundaries.
The source code is the authority for current behavior; historical context notes
may describe features or fixes that are absent from the current implementation.

## Private data and Git

Source runs store generated files beside the package in:

- `data/OnThisDay_cache.db`: media paths, dates, sizes, modification timestamps,
  video flags and thumbnail paths.
- `data/thumbnails/`: generated video previews.

At startup, existing caches and thumbnail folders are migrated from the project
root or `Meta/` into `data/`, with the root taking priority. Cached thumbnail
paths are updated. The historical context log stays in `Meta/Context.txt`.
Close other app instances before migration.

Packaged builds use private per-user application storage instead of writing inside
the executable bundle; see [release instructions](docs/releases.md#downloads).

Git ignores `data/`, `Meta/`, `private/`, `personal/`, legacy caches, databases,
common media formats, logs, local settings, credentials and Python environments.
Put other personal files in `private/` or `personal/`. Documentation screenshots
are an explicit public exception. Ignore rules do not remove already tracked
files or erase Git history.

## Metadata and supported media

Photo dates use EXIF `DateTimeOriginal` when readable. Video dates use ffprobe's
`creation_time`. Both fall back to file modification time. Cached dates are reused
while modification timestamps remain unchanged. Video timezone offsets are
stripped rather than converted to local time.

The scanner recognises JPEG, PNG, GIF, BMP, WebP, TIFF, HEIC/HEIF, common RAW
extensions (CR2, CR3, NEF, ARW, DNG, ORF, RAW), ICO, JFIF and PNM-family images.
SVG files are discovered, but the app has no SVG renderer, so they may fail to load.
RAW and HEIC decoding depends on the optional libraries and the individual file.

Video extensions include MP4, MOV, AVI, MKV, WMV, FLV, WebM, M4V, MPG, MPEG, 3GP,
M2TS, MTS, TS, VOB and OGV. Playback compatibility depends on the external player.

## Limitations and troubleshooting

- Folder scans and scan-time metadata extraction run in a cancellable background
  worker. Closing the window cancels the scan and stops running media tools.
  Display-time image decoding still runs on the UI thread, so large RAW files can
  temporarily delay interaction while their preview loads.
- There is no active date picker, rotation, favourites, duplicate detection,
  batch review or saved review position.
- Sorting and navigation retain their existing behavior; the refactor did not
  implement historical proposals for a unified folder-based sort.
- If RAW or HEIC decoding fails, check that the `formats` extra is installed.
- If video previews fail, check `ffmpeg -version` and `ffprobe -version`.
- If dates look wrong, check the source metadata and modification dates.
- To rebuild the cache, close the app and remove `data/OnThisDay_cache.db`.
  Previews can also be regenerated by removing `data/thumbnails/`.

## Validation

```powershell
python -B -m unittest discover -s tests -v
```

Storage tests use synthetic temporary files to check legacy migration,
thumbnail-path updates, repeat runs, existing destinations and active-cache
sidecars. They do not open personal media or exercise the GUI.

## License

Free to use and modify. No warranty provided.

Last updated: 18 October 2026.

# Development and maintenance

The source code defines current behavior. See [architecture](architecture.md)
for module responsibilities and [releases](releases.md) for release automation.

## Run from source

Requires Python 3.10 or later with Tkinter. Release tooling and tests use Python
3.12 in CI. Install optional image-format support with the `formats` extra.

Windows:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[formats]"
.venv\Scripts\python.exe -m image_swiper
```

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[formats]'
.venv/bin/python -m image_swiper
```

Linux may require the distribution's Tkinter package. The existing Windows batch
launcher uses `venv/`, while the examples above create `.venv/`.
`python Image_Swiper.py` remains a compatibility entry point.

## Documentation screenshots

Public README screenshots belong in `docs/screenshots/`. PNG, JPG, JPEG and WebP
files directly in that folder have explicit Git ignore exceptions. Other private
media remains ignored. Use relative image links from README.md; encode spaces
in filenames as `%20`.

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

See [architecture notes](architecture.md) for the module boundaries.
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

Windows builds use `cache/` beside the executable; macOS/Linux builds use
private per-user application storage; see [release instructions](releases.md#downloads).

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


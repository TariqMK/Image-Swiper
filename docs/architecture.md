# Architecture

Source code defines current behavior. Historical notes in private `Meta/Context.txt`
may describe features absent from the current application.

`app.ImageOrganizer` owns review state and coordinates actions. Focused mixins
preserve shared state while separating the original class into modules:

- `ui.py`: widgets, keyboard bindings and opening external applications.
- `library.py`: scanning, filtering and sorting.
- `media.py`: image decoding, video thumbnails and canvas rendering.
- `metadata.py`: date extraction, matching and size formatting.
- `cache.py`: SQLite schema, metadata cache and thumbnail cleanup.
- `date_cache.py`: one connection per scan and short batched metadata writes.
- `recent_folders.py`: atomic private storage of the three most recently opened folders.
- `recycle_bin.py`: Windows delete/restore and native Trash support elsewhere.
- `paths.py`: private runtime storage and legacy cache migration.

Run `python -m image_swiper` or the original launcher. `scanning.py` traverses
folders and extracts scan metadata in a daemon worker. `library.py` snapshots scan
options and polls a result queue on the Tk thread. Cancellation events and scan
generation IDs prevent obsolete results from updating the interface. Closing
cancels pending work, kills managed media subprocesses and destroys the window
without joining the worker. `processes.py` keeps those media tools console-free
on Windows and tracks their lifetime. Preview decoding still runs on the UI thread.

Date scans never generate video thumbnails. The scan snapshot owns a `DateCache`
session in its worker thread; UI calls use separate short sessions. Pending rows
are readable immediately and flush at 100 entries or after roughly one second
when another row is stored. No write transaction remains open during metadata
extraction. Session exit flushes completed rows even after cancellation/errors.
Immediate process termination can discard an unflushed batch, which is safe to
rescan. Viewing a video generates its preview and registers the thumbnail path
for cleanup tracking; unchanged cached dates retain existing thumbnail records.

## Private data

Runtime files live in ignored `data/` beside the package. On first launch, legacy
cache files and thumbnails move there from the project root or `Meta/`, with the
root taking priority. Cached thumbnail paths are updated. The context log remains
in ignored `Meta/`; it is not copied into public documentation.

Git ignores runtime storage, databases, common media formats, local configuration,
logs and virtual environments. Store other personal files in ignored `private/`
or `personal/`. Do not force-add private files. Ignore rules cannot remove data
already committed to an existing repository.

Frozen Windows builds use `cache/` beside the executable. macOS/Linux builds
use per-user application storage instead of writing inside the bundle. `version.py` is stamped alongside `pyproject.toml` on the release tag;
the UI renders that version in muted header text. See [releases](releases.md)
for the manual build workflow and platform-specific behavior.

The Recent folders dropdown stores full paths in `recent_folders.json` beside
the runtime database, inside private `data/` storage. Source runs therefore ignore
the history through the existing `/data/` rule. Windows bundles use ignored
`cache/` beside the executable; macOS/Linux use per-user storage.
History is deduplicated and capped at three entries. Missing drives are checked
only when selected, and malformed history is ignored without blocking startup.
Selecting a recent folder uses the same reset and cancellable scan as Select Folder.

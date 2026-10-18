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
- `recycle_bin.py`: Windows delete/restore and native Trash support elsewhere.
- `paths.py`: private runtime storage and legacy cache migration.

Run `python -m image_swiper` or the original launcher. Scanning remains synchronous;
the refactor preserves existing sorting and review behavior.

## Private data

Runtime files live in ignored `data/` beside the package. On first launch, legacy
cache files and thumbnails move there from the project root or `Meta/`, with the
root taking priority. Cached thumbnail paths are updated. The context log remains
in ignored `Meta/`; it is not copied into public documentation.

Git ignores runtime storage, databases, common media formats, local configuration,
logs and virtual environments. Store other personal files in ignored `private/`
or `personal/`. Do not force-add private files. Ignore rules cannot remove data
already committed to an existing repository.

Frozen release builds use per-user application storage instead of writing inside
the bundle. `version.py` is stamped alongside `pyproject.toml` on the release tag;
the UI renders that version in muted header text. See [releases](releases.md)
for the manual build workflow and platform-specific behavior.

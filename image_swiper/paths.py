"""Private runtime storage, independent of the current working directory."""
from contextlib import closing
from pathlib import Path
import os
import shutil
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def runtime_paths(project_root=None):
    if project_root is not None:
        root = Path(project_root)
    elif getattr(sys, 'frozen', False):
        # Bundles may be read-only or extracted into temporary directories.
        if sys.platform == 'win32':
            root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'ImageSwiper'
        elif sys.platform == 'darwin':
            root = Path.home() / 'Library' / 'Application Support' / 'ImageSwiper'
        else:
            root = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'image-swiper'
        root.mkdir(parents=True, exist_ok=True)
    else:
        root = PROJECT_ROOT
    data = root / 'data'
    data.mkdir(exist_ok=True)
    database = data / 'OnThisDay_cache.db'
    thumbnails = data / 'thumbnails'
    for legacy in (root, root / 'Meta'):
        old_database = legacy / 'OnThisDay_cache.db'
        old_thumbnails = legacy / 'OnThisDay_thumbnails'
        if not database.exists() and old_database.exists():
            if any(Path(str(old_database) + suffix).exists() for suffix in ('-wal', '-shm', '-journal')):
                raise RuntimeError('Close other Image Swiper instances before migrating the cache.')
            shutil.move(str(old_database), str(database))
        if not thumbnails.exists() and old_thumbnails.exists():
            shutil.move(str(old_thumbnails), str(thumbnails))
    thumbnails.mkdir(exist_ok=True)
    if database.exists():
        with closing(sqlite3.connect(database)) as connection, connection:
            columns = {row[1] for row in connection.execute('PRAGMA table_info(image_cache)')}
            if 'thumbnail_path' in columns:
                records = connection.execute('SELECT filepath, thumbnail_path FROM image_cache WHERE thumbnail_path IS NOT NULL').fetchall()
                for filepath, previous in records:
                    candidate = thumbnails / Path(previous).name
                    if candidate.exists() and str(candidate) != previous:
                        connection.execute('UPDATE image_cache SET thumbnail_path = ? WHERE filepath = ?', (str(candidate), filepath))
    return database, thumbnails

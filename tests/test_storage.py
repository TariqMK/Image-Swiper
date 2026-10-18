from contextlib import closing
"""Exercise storage migration using synthetic files, never personal media."""
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from image_swiper.paths import runtime_paths


class StorageTests(unittest.TestCase):
    def test_frozen_build_storage_location(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', str(base / 'ImageSwiper.exe')), patch('pathlib.Path.home', return_value=base), patch.dict(
                'os.environ', {'LOCALAPPDATA': str(base), 'XDG_DATA_HOME': str(base)}
            ):
                database, thumbnails = runtime_paths()
            if sys.platform == 'win32':
                expected = base / 'cache'
            elif sys.platform == 'darwin':
                expected = base / 'Library' / 'Application Support' / 'ImageSwiper' / 'data'
            else:
                expected = base / 'image-swiper' / 'data'
            # Windows temp paths may use an 8.3 alias (RUNNER~1), while the
            # executable path is resolved to its long form (runneradmin).
            self.assertEqual(database.parent.resolve(), expected.resolve())
            self.assertEqual(thumbnails.resolve(), (expected / 'thumbnails').resolve())

    def test_legacy_cache_and_thumbnail_paths_migrate_and_repeat_safely(self):
        for location in ('', 'Meta'):
            with self.subTest(location=location), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                legacy = root / location
                legacy.mkdir(exist_ok=True)
                old_thumbnails = legacy / 'OnThisDay_thumbnails'
                old_thumbnails.mkdir()
                thumbnail = old_thumbnails / 'example.jpg'
                thumbnail.write_bytes(b'synthetic preview')
                with closing(sqlite3.connect(legacy / 'OnThisDay_cache.db')) as connection, connection:
                    connection.execute('CREATE TABLE image_cache (filepath TEXT PRIMARY KEY, thumbnail_path TEXT)')
                    connection.execute('INSERT INTO image_cache VALUES (?, ?)', ('synthetic.mp4', str(thumbnail)))
                database, thumbnails = runtime_paths(root)
                self.assertEqual((thumbnails / thumbnail.name).read_bytes(), b'synthetic preview')
                with closing(sqlite3.connect(database)) as connection, connection:
                    self.assertEqual(connection.execute('SELECT thumbnail_path FROM image_cache').fetchone()[0],
                                     str(thumbnails / thumbnail.name))
                self.assertEqual(runtime_paths(root), (database, thumbnails))

    def test_active_database_is_not_moved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / 'OnThisDay_cache.db'
            database.touch()
            Path(str(database) + '-wal').touch()
            with self.assertRaises(RuntimeError):
                runtime_paths(root)
            self.assertTrue(database.exists())

    def test_existing_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database, thumbnails = runtime_paths(root)
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute('CREATE TABLE marker (value TEXT)')
                connection.execute("INSERT INTO marker VALUES ('existing')")
            (root / 'OnThisDay_cache.db').write_bytes(b'legacy')
            runtime_paths(root)
            with closing(sqlite3.connect(database)) as connection, connection:
                self.assertEqual(connection.execute('SELECT value FROM marker').fetchone()[0], 'existing')
            self.assertEqual((root / 'OnThisDay_cache.db').read_bytes(), b'legacy')


if __name__ == '__main__':
    unittest.main()

"""Cold/warm scans, deferred previews and bounded batch transactions."""
from datetime import datetime
from pathlib import Path
import sqlite3
import tempfile
from threading import Event
import unittest
from unittest.mock import Mock

from image_swiper.cache import CacheMixin
from image_swiper.date_cache import DateCache


class CacheHarness(CacheMixin):
    pass


class DateCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.app = CacheHarness()
        self.app.db_path = self.root / 'cache.db'
        self.app.video_extensions = {'.mp4'}
        self.app._scan_cancel = Event()
        self.app.get_video_date = Mock(return_value=datetime(2020, 10, 18))
        self.app.extract_image_date = Mock(return_value=datetime(2021, 10, 18))
        self.app.generate_video_thumbnail = Mock(side_effect=AssertionError('scan generated a preview'))
        self.app.init_database()

    def file(self, name):
        path = self.root / name
        path.write_bytes(b'synthetic')
        return path

    def test_cold_and_warm_video_scan_never_generates_previews(self):
        video = self.file('example.mp4')
        with DateCache(self.app.db_path) as session:
            self.app._date_cache_session = session
            self.assertEqual(self.app.get_cached_date(video), datetime(2020, 10, 18))
            # An entry pending in memory must already count as cached.
            self.app.get_cached_date(video)
        with DateCache(self.app.db_path) as session:
            self.app._date_cache_session = session
            self.app.get_cached_date(video)
        self.app.get_video_date.assert_called_once_with(video)
        self.app.generate_video_thumbnail.assert_not_called()

    def test_writes_are_batched_and_partial_batch_is_flushed(self):
        trace = []
        with DateCache(self.app.db_path) as session:
            session.connection.set_trace_callback(trace.append)
            for number in range(250):
                session.store(str(number), datetime(2020, 1, 1), 10, 1.0, False)
            self.assertEqual(sum(command == 'COMMIT' for command in trace), 2)
            self.assertEqual(len(session.pending), 50)
        self.assertEqual(sum(command == 'COMMIT' for command in trace), 3)
        with DateCache(self.app.db_path) as session:
            self.assertEqual(session.connection.execute('SELECT COUNT(*) FROM image_cache').fetchone()[0], 250)

    def test_cancellation_preserves_completed_partial_batch(self):
        video = self.file('complete.mp4')
        with DateCache(self.app.db_path) as session:
            self.app._date_cache_session = session
            self.app.get_cached_date(video)
            self.app._scan_cancel.set()
            self.assertIsNone(self.app.get_cached_date(self.root / 'not-started.mp4'))
        with DateCache(self.app.db_path) as session:
            self.assertIsNotNone(session.lookup(video))
            self.assertIsNone(session.lookup(self.root / 'not-started.mp4'))

    def test_metadata_extraction_does_not_hold_write_lock(self):
        with DateCache(self.app.db_path) as session:
            session.store('pending', datetime(2020, 1, 1), 10, 1.0, False)
            self.assertFalse(session.connection.in_transaction)
            with DateCache(self.app.db_path, batch_size=1) as other:
                other.store('other', datetime(2020, 1, 1), 10, 1.0, False)

    def test_failed_scan_flushes_completed_records(self):
        with self.assertRaises(RuntimeError):
            with DateCache(self.app.db_path) as session:
                session.store('complete', datetime(2020, 1, 1), 10, 1.0, False)
                raise RuntimeError('synthetic scan failure')
        with DateCache(self.app.db_path) as session:
            self.assertIsNotNone(session.lookup('complete'))

    def test_displayed_preview_is_registered_without_rereading_date(self):
        video = self.file('example.mp4')
        self.app.get_cached_date(video)
        preview = self.file('preview.jpg')
        self.app.record_thumbnail(video, preview)
        self.app.get_cached_date(video)
        with DateCache(self.app.db_path) as session:
            row = session.connection.execute('SELECT thumbnail_path FROM image_cache WHERE filepath = ?', (str(video),)).fetchone()
            self.assertEqual(row[0], str(preview))
        self.app.get_video_date.assert_called_once()

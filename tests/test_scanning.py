"""Scanning cancellation, filter correctness and stale UI messages."""
from datetime import datetime
from pathlib import Path
from queue import Queue
import tempfile
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from image_swiper.scanning import scan_library
from image_swiper.library import LibraryMixin


class ScanningTests(unittest.TestCase):
    def test_scan_returns_control_while_metadata_is_still_running(self):
        started = Event()
        release = Event()
        finished = Event()
        def blocked_metadata(path):
            started.set()
            release.wait(timeout=3)
            finished.set()
            return datetime(2020, 10, 18)
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / 'example.jpg').touch()
            window = SimpleNamespace(
                _closing=False, _scan_cancel=None, _scan_generation=0,
                _scan_messages=Queue(), delete_btn=Mock(), undo_btn=Mock(),
                canvas=Mock(), counter_label=Mock(), include_subdirs=True,
                image_extensions={'.jpg'}, video_extensions=set(), sort_by_date=False,
                on_this_day_mode=True, viewing_date=datetime(2026, 10, 18),
                random_mode=False, get_cached_date=blocked_metadata,
                natural_sort_key=lambda path: path.name,
            )
            try:
                LibraryMixin.load_images(window, temporary)
                self.assertTrue(started.wait(timeout=2))
                self.assertFalse(finished.is_set())
                # Simulate Close while a metadata tool is blocked.
                window._closing = True
                window._scan_cancel.set()
            finally:
                release.set()
                self.assertTrue(finished.wait(timeout=2))

    def options(self, cancel, get_date):
        return dict(cancel=cancel, extensions={'.jpg'}, include_subdirs=True,
                    get_date=get_date, sort_key=lambda path: path.name,
                    sort_by_date=False, on_this_day=True,
                    reference_date=datetime(2026, 10, 18), random_mode=False,
                    progress=Mock())

    def test_cancellation_stops_before_next_metadata_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('a.jpg', 'b.jpg', 'c.jpg'):
                (root / name).touch()
            cancel = Event()
            def date(path):
                cancel.set()
                return datetime(2020, 10, 18)
            get_date = Mock(side_effect=date)
            result = scan_library(root, **self.options(cancel, get_date))
            self.assertEqual(result, [])
            get_date.assert_called_once()

    def test_filter_dates_and_mixed_case_extensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dates = {'a.JPG': datetime(2022, 10, 18), 'b.jpg': datetime(2020, 10, 18),
                     'c.jpg': datetime(2021, 10, 19)}
            for name in dates:
                (root / name).touch()
            result = scan_library(root, **self.options(Event(), lambda path: dates[path.name]))
            self.assertEqual([path.name for path in result], ['b.jpg', 'a.JPG'])

    def test_nonrecursive_scan_excludes_subfolders(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'subfolder').mkdir()
            (root / 'subfolder' / 'hidden.jpg').touch()
            (root / 'visible.jpg').touch()
            options = self.options(Event(), Mock())
            options.update(include_subdirs=False, on_this_day=False)
            result = scan_library(root, **options)
            self.assertEqual([path.name for path in result], ['visible.jpg'])
            options['get_date'].assert_not_called()

    def test_closed_window_never_receives_worker_updates(self):
        window = SimpleNamespace(_closing=True, root=Mock(), counter_label=Mock())
        LibraryMixin.poll_scan(window)
        window.root.after.assert_not_called()
        window.counter_label.config.assert_not_called()

    def test_results_from_superseded_scan_are_ignored(self):
        messages = Queue()
        messages.put((1, 'done', ['old.jpg']))
        window = SimpleNamespace(_closing=False, _scan_generation=2,
                                 _scan_messages=messages, root=Mock(), images=[], poll_scan=Mock())
        LibraryMixin.poll_scan(window)
        self.assertEqual(window.images, [])
        window.root.after.assert_called_once()

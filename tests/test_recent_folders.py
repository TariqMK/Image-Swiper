"""Folder history uses synthetic paths and stays bounded across restarts."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from image_swiper.recent_folders import RecentFolders
from image_swiper.library import LibraryMixin


class RecentFolderTests(unittest.TestCase):
    def test_three_latest_are_persisted_and_reopening_moves_to_front(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            history = RecentFolders(root / 'data' / 'recent_folders.json')
            for name in ('a', 'b', 'c', 'd'):
                history.remember(root / name)
            self.assertEqual([Path(folder).name for folder in history.folders], ['d', 'c', 'b'])
            history = RecentFolders(history.path)
            history.remember(root / 'c')
            self.assertEqual([Path(folder).name for folder in RecentFolders(history.path).folders], ['c', 'd', 'b'])

    def test_missing_corrupt_or_invalid_history_is_safe(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'recent_folders.json'
            self.assertEqual(RecentFolders(path).folders, [])
            for content in ('broken', '{}', '[null, 42, "", "\\u0000"]'):
                path.write_text(content, encoding='utf-8')
                self.assertEqual(RecentFolders(path).folders, [])

    def test_unavailable_folder_does_not_replace_active_scan(self):
        window = SimpleNamespace(load_images=Mock())
        with patch('image_swiper.library.Path.is_dir', return_value=False), patch('image_swiper.library.messagebox.showwarning') as warning:
            LibraryMixin.open_review_folder(window, 'unavailable-folder')
        warning.assert_called_once()
        window.load_images.assert_not_called()

    def test_dropdown_opens_saved_folder_without_a_picker(self):
        window = SimpleNamespace(recent_folder_var=Mock(), recent_folders=SimpleNamespace(folders=['saved']),
                                 open_review_folder=Mock())
        window.recent_folder_var.get.return_value = 'saved'
        LibraryMixin.select_recent_folder(window)
        window.open_review_folder.assert_called_once_with('saved')

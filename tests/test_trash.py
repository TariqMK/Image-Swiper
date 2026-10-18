"""Verify trash routing without deleting any files."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class TrashTests(unittest.TestCase):
    def load_backend(self, platform, modules):
        spec = importlib.util.spec_from_file_location('trash_test_backend', Path(__file__).resolve().parents[1] / 'image_swiper' / 'recycle_bin.py')
        backend = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'platform', platform), patch.dict(sys.modules, modules):
            spec.loader.exec_module(backend)
        return backend

    def test_windows_keeps_recycle_bin_restore(self):
        shell = SimpleNamespace(delete_file=Mock(), undelete=Mock())
        backend = self.load_backend('win32', {'winshell': shell})
        backend.delete_file('synthetic.jpg')
        backend.restore_file('synthetic.jpg')
        shell.delete_file.assert_called_once_with('synthetic.jpg', no_confirm=True, allow_undo=True)
        shell.undelete.assert_called_once_with('synthetic.jpg')
        self.assertTrue(backend.CAN_RESTORE)

    def test_macos_and_linux_use_trash_without_windows_import(self):
        for platform in ('darwin', 'linux'):
            with self.subTest(platform=platform):
                trash = Mock()
                backend = self.load_backend(platform, {'send2trash': SimpleNamespace(send2trash=trash), 'winshell': None})
                backend.delete_file('synthetic.jpg')
                trash.assert_called_once_with('synthetic.jpg')
                self.assertFalse(backend.CAN_RESTORE)
                with self.assertRaises(NotImplementedError):
                    backend.restore_file('synthetic.jpg')

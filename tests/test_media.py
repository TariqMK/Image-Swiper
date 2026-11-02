"""Shown images must not hold their files open, or Windows refuses to delete them."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from image_swiper.media import MediaMixin, open_detached


class OpenDetachedTests(unittest.TestCase):
    def test_multi_frame_file_can_be_deleted_while_shown(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'animated.gif'
            frames = [Image.new('RGB', (8, 8), colour) for colour in ('red', 'blue')]
            frames[0].save(path, save_all=True, append_images=frames[1:])

            shown = open_detached(path)
            path.unlink()  # PermissionError on Windows if the file is still open

            self.assertFalse(path.exists())
            self.assertEqual(shown.size, (8, 8))


# Runs in a fresh interpreter, which gets a new hash() seed like a new launch.
FIND_PREVIEW = '''
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from image_swiper.media import MediaMixin
folder = Path(sys.argv[1])
window = SimpleNamespace(ffmpeg_available=True, thumbnails_dir=folder)
window.video_thumbnail_path = lambda path: MediaMixin.video_thumbnail_path(window, path)
with patch('image_swiper.media.run_background', side_effect=AssertionError('regenerated')):
    print(MediaMixin.generate_video_thumbnail(window, folder / 'clip.mp4'))
'''


class VideoPreviewNameTests(unittest.TestCase):
    def test_existing_preview_is_reused_after_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            window = SimpleNamespace(ffmpeg_available=True, thumbnails_dir=folder)
            window.video_thumbnail_path = lambda path: MediaMixin.video_thumbnail_path(window, path)
            with patch('image_swiper.media.run_background') as ffmpeg:
                ffmpeg.side_effect = lambda command, **_: Image.new('RGB', (4, 4)).save(command[-1])
                first = MediaMixin.generate_video_thumbnail(window, folder / 'clip.mp4')

            project = Path(__file__).resolve().parents[1]
            after_restart = subprocess.run([sys.executable, '-c', FIND_PREVIEW, temporary],
                                           cwd=project, check=True, capture_output=True, text=True)
            # The last line is the result; optional-format warnings may precede it.
            self.assertEqual(after_restart.stdout.strip().splitlines()[-1], str(first))


class VideoPreviewQueueTests(unittest.TestCase):
    def window(self, folder, video):
        return SimpleNamespace(
            _closing=False, _preview_file=video, _preview_failed=set(),
            _preview_thread=SimpleNamespace(is_alive=lambda: False),
            current_file=lambda: video, is_video_file=lambda path: True,
            video_thumbnail_path=lambda path: folder / f'{path.stem}.jpg',
            show_current_image=Mock(), request_video_preview=Mock(), root=Mock())

    def test_failed_preview_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            window = self.window(folder, folder / 'broken.mp4')
            MediaMixin.poll_video_preview(window)
            self.assertIn(folder / 'broken.mp4', window._preview_failed)
            window.show_current_image.assert_called_once()  # shows "Preview unavailable"
            window.request_video_preview.assert_not_called()

    def test_preview_starts_for_the_video_you_moved_to(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            window = self.window(folder, folder / 'skipped.mp4')
            window.current_file = lambda: folder / 'current.mp4'
            MediaMixin.poll_video_preview(window)
            window.request_video_preview.assert_called_once_with(folder / 'current.mp4')
            window.show_current_image.assert_not_called()

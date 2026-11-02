"""Shown images must not hold their files open, or Windows refuses to delete them."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
with patch('image_swiper.media.run_background', side_effect=AssertionError('regenerated')):
    print(MediaMixin.generate_video_thumbnail(window, folder / 'clip.mp4'))
'''


class VideoPreviewNameTests(unittest.TestCase):
    def test_existing_preview_is_reused_after_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            window = SimpleNamespace(ffmpeg_available=True, thumbnails_dir=folder)
            with patch('image_swiper.media.run_background') as ffmpeg:
                ffmpeg.side_effect = lambda command, **_: Image.new('RGB', (4, 4)).save(command[-1])
                first = MediaMixin.generate_video_thumbnail(window, folder / 'clip.mp4')

            project = Path(__file__).resolve().parents[1]
            after_restart = subprocess.run([sys.executable, '-c', FIND_PREVIEW, temporary],
                                           cwd=project, check=True, capture_output=True, text=True)
            self.assertEqual(after_restart.stdout.strip(), str(first))

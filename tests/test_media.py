"""Shown images must not hold their files open, or Windows refuses to delete them."""
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from image_swiper.media import open_detached


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

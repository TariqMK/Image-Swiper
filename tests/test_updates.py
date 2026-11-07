"""The manual update check compares versions correctly and only opens this project's pages."""
import io
import json
import unittest
from unittest.mock import patch

from image_swiper import updates


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake(payload):
    return FakeResponse(json.dumps(payload).encode())


class VersionTests(unittest.TestCase):
    def test_newer_versions_compare_numerically(self):
        self.assertTrue(updates.is_newer('1.10.0', '1.9.9'))
        self.assertTrue(updates.is_newer('v2.0.0', '1.0.0'))
        self.assertFalse(updates.is_newer('1.0.0', '1.0.0'))
        self.assertFalse(updates.is_newer('1.0.0', '1.0.1'))

    def test_unparseable_versions_never_report_an_update(self):
        self.assertFalse(updates.is_newer('latest', '1.0.0'))
        self.assertFalse(updates.is_newer('1.2.0', 'dev'))


class FetchTests(unittest.TestCase):
    def test_reads_tag_and_release_page(self):
        page = f'{updates.RELEASES_PAGE}/tag/v1.4.0'
        with patch('image_swiper.updates.urllib.request.urlopen',
                   return_value=fake({'tag_name': 'v1.4.0', 'html_url': page})) as urlopen:
            self.assertEqual(updates.fetch_latest_release(), ('v1.4.0', page))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, updates.LATEST_RELEASE_API)
        self.assertIsNone(request.data)

    def test_foreign_release_url_falls_back_to_project_releases(self):
        with patch('image_swiper.updates.urllib.request.urlopen',
                   return_value=fake({'tag_name': 'v1.4.0', 'html_url': 'https://example.com/x'})):
            self.assertEqual(updates.fetch_latest_release()[1], updates.RELEASES_PAGE)

    def test_bad_tag_is_an_error(self):
        with patch('image_swiper.updates.urllib.request.urlopen',
                   return_value=fake({'tag_name': 'nightly'})):
            with self.assertRaises(ValueError):
                updates.fetch_latest_release()


if __name__ == '__main__':
    unittest.main()

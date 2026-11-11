"""The manual update check compares versions correctly, explains failures and only opens this project's pages."""
import io
import json
import socket
import unittest
import urllib.error
from unittest.mock import patch

from image_swiper import updates

URLOPEN = 'image_swiper.updates.urllib.request.urlopen'


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake(payload):
    return FakeResponse(json.dumps(payload).encode())


def http_error(code):
    return urllib.error.HTTPError(updates.LATEST_RELEASE_API, code, 'error', {}, None)


class VersionTests(unittest.TestCase):
    def test_newer_versions_compare_numerically(self):
        self.assertTrue(updates.is_newer('0.10.0', '0.9.0'))
        self.assertTrue(updates.is_newer('1.10.0', '1.9.9'))
        self.assertTrue(updates.is_newer('v2.0.0', '1.0.0'))
        self.assertFalse(updates.is_newer('1.0.0', '1.0.0'))
        self.assertFalse(updates.is_newer('1.0.0', '1.0.1'))

    def test_unparseable_versions_never_report_an_update(self):
        self.assertFalse(updates.is_newer('latest', '1.0.0'))
        self.assertFalse(updates.is_newer('1.2.0', 'dev'))
        self.assertIsNone(updates.parse_version('0.0.0-dev'))

    def test_classify(self):
        self.assertEqual(updates.classify('v2.5.0', '2.4.0'), 'newer')
        self.assertEqual(updates.classify('v2.4.0', '2.4.0'), 'current')
        self.assertEqual(updates.classify('v2.4.0', '2.5.0'), 'current')
        self.assertEqual(updates.classify('v2.5.0', '0.0.0-dev'), 'dev')

    def test_result_text(self):
        self.assertEqual(updates.result_text('newer', 'v2.5.0', '2.4.0'),
                         ('Image Swiper v2.5.0 is available.',
                          'You have v2.4.0. Open the release page to download the new version.'))
        self.assertEqual(updates.result_text('current', 'v2.4.0', '2.4.0'),
                         ('Image Swiper is up to date.', 'v2.4.0 is the latest release.'))
        self.assertEqual(updates.result_text('dev', 'v2.5.0', '0.0.0-dev'),
                         ('This is a development build.',
                          'You are running v0.0.0-dev. The latest release is v2.5.0.'))


class FetchTests(unittest.TestCase):
    def test_reads_tag_release_page_and_notes(self):
        page = f'{updates.RELEASES_PAGE}/tag/v1.4.0'
        with patch(URLOPEN, return_value=fake({'tag_name': 'v1.4.0', 'html_url': page,
                                               'body': ' Notes \n'})) as urlopen:
            self.assertEqual(updates.fetch_latest_release(), ('v1.4.0', page, 'Notes'))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, updates.LATEST_RELEASE_API)
        self.assertIsNone(request.data)
        self.assertTrue(request.get_header('User-agent').startswith('Image-Swiper/'))

    def test_missing_foreign_or_http_release_url_falls_back_to_project_releases(self):
        for url in (None, 'https://example.com/x', f'http://github.com/{updates.REPOSITORY}/releases/tag/v1'):
            with patch(URLOPEN, return_value=fake({'tag_name': 'v1.4.0', 'html_url': url})):
                self.assertEqual(updates.fetch_latest_release()[1], updates.RELEASES_PAGE)

    def assertMessage(self, side_effect, message):
        with patch(URLOPEN, side_effect=side_effect):
            with self.assertRaises(updates.UpdateError) as caught:
                updates.fetch_latest_release()
        self.assertEqual(str(caught.exception), message)

    def test_error_messages(self):
        self.assertMessage(http_error(404), 'No Image Swiper releases are published yet.')
        for code in (403, 429):
            self.assertMessage(http_error(code), 'GitHub limits how often it can be checked. Try again in an hour.')
        self.assertMessage(http_error(500), 'GitHub answered with error 500. Try again later.')
        self.assertMessage(urllib.error.URLError('no route'),
                           "Can't reach GitHub: no route. Check the internet connection.")
        self.assertMessage(socket.timeout('timed out'),
                           "Can't reach GitHub: timed out. Check the internet connection.")

    def test_unreadable_answers(self):
        unreadable = "GitHub sent an answer Image Swiper can't read. Try again later."
        with patch(URLOPEN, return_value=FakeResponse(b'not json')):
            with self.assertRaises(updates.UpdateError) as caught:
                updates.fetch_latest_release()
        self.assertEqual(str(caught.exception), unreadable)
        for payload in ({'tag_name': 'nightly'}, {'tag_name': 'v1.2.3-beta'}, []):
            with patch(URLOPEN, return_value=fake(payload)):
                with self.assertRaises(updates.UpdateError) as caught:
                    updates.fetch_latest_release()
            self.assertEqual(str(caught.exception), unreadable)


if __name__ == '__main__':
    unittest.main()

"""Release numbering must reserve drafts and historical tags too."""
from contextlib import chdir
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.release_version import list_pages, main, next_version


class ReleaseVersionTests(unittest.TestCase):
    def test_release_listing_reads_beyond_the_first_page(self):
        first = [{'tag_name': f'v1.0.{i}'} for i in range(100)]
        last = [{'tag_name': 'v2.0.0', 'draft': True}]
        with patch.dict(os.environ, {'GITHUB_REPOSITORY': 'example/repo', 'GH_TOKEN': 'test-token'}), patch(
            'scripts.release_version.urlopen', side_effect=[
                io.BytesIO(json.dumps(first).encode()), io.BytesIO(json.dumps(last).encode())
            ]
        ) as request:
            releases = list(list_pages('releases'))
        self.assertEqual(len(releases), 101)
        self.assertTrue(releases[-1]['draft'])
        self.assertIn('page=2', request.call_args.args[0].full_url)

    def test_bump_resets_lower_components(self):
        self.assertEqual(next_version('1.2.3', [], 'major'), '2.0.0')
        self.assertEqual(next_version('1.2.3', [], 'minor'), '1.3.0')
        self.assertEqual(next_version('1.2.3', [], 'patch'), '1.2.4')

    def test_drafts_tags_and_prereleases_reserve_versions(self):
        self.assertEqual(next_version('1.0.0', ['v1.2.8', 'v2.0.0', 'v2.1.0-rc.1', 'unrelated'], 'patch'), '2.1.1')

    def test_numeric_order_and_source_baseline(self):
        self.assertEqual(next_version('1.0.0', ['v1.9.9', 'v1.10.0'], 'minor'), '1.11.0')
        self.assertEqual(next_version('5.0.0', ['v1.0.0'], 'patch'), '5.0.1')

    def test_prepare_stamps_both_versions_and_outputs(self):
        with tempfile.TemporaryDirectory() as temporary, chdir(temporary):
            Path('image_swiper').mkdir()
            Path('pyproject.toml').write_text('[project]\nversion = "1.0.0"\n', encoding='utf-8')
            output = str(Path('output').resolve())
            with patch.dict(os.environ, {'GITHUB_OUTPUT': output}), patch('sys.argv', ['release_version.py', 'minor']), patch(
                'scripts.release_version.list_pages', side_effect=[
                    [{'tag_name': 'v1.4.2', 'draft': True}], [{'name': 'v1.5.0'}]
                ]
            ):
                main()
            self.assertIn('version = "1.6.0"', Path('pyproject.toml').read_text())
            self.assertIn('__version__ = "1.6.0"', Path('image_swiper/version.py').read_text())
            self.assertEqual(Path(output).read_text(), 'version=1.6.0\ntag=v1.6.0\n')

    def test_invalid_bump_is_rejected(self):
        with self.assertRaises(ValueError):
            next_version('1.0.0', [], 'invalid')


if __name__ == '__main__':
    unittest.main()

"""Manual update check: asks GitHub for the latest release tag, only when the user clicks.

The request goes to api.github.com, sends no user data, and nothing is downloaded.
A newer version is offered as a link to its release page in the browser.
"""

import json
import re
import urllib.request
import webbrowser
from threading import Thread
from tkinter import messagebox

from .version import __version__

REPOSITORY = 'TariqMK/Image-Swiper'
LATEST_RELEASE_API = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
RELEASES_PAGE = f'https://github.com/{REPOSITORY}/releases'
TIMEOUT_SECONDS = 10
VERSION = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)')


def parse_version(text):
    """Return (major, minor, patch) from '1.2.3' or 'v1.2.3', or None."""
    match = VERSION.match(str(text).strip())
    return tuple(map(int, match.groups())) if match else None


def is_newer(latest, current):
    latest_v, current_v = parse_version(latest), parse_version(current)
    return latest_v is not None and current_v is not None and latest_v > current_v


def fetch_latest_release(timeout=TIMEOUT_SECONDS):
    """Return (tag, release page URL) for the latest published release."""
    request = urllib.request.Request(LATEST_RELEASE_API, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'Image-Swiper',
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.load(response)
    tag = data.get('tag_name')
    if not parse_version(tag):
        raise ValueError(f'Unexpected release tag: {tag!r}')
    url = data.get('html_url') or ''
    # Only ever open this project's own release pages.
    if not url.startswith(RELEASES_PAGE + '/'):
        url = RELEASES_PAGE
    return tag, url


class UpdatesMixin:
    def check_for_updates(self):
        if getattr(self, '_update_thread', None) is not None and self._update_thread.is_alive():
            return
        self._update_result = None

        def work():
            try:
                self._update_result = ('ok', *fetch_latest_release())
            except Exception as error:  # Network, TLS, JSON or tag errors all mean "could not check".
                self._update_result = ('error', str(error))

        self._update_thread = Thread(target=work, name='update-check', daemon=True)
        self._update_thread.start()
        self.root.after(100, self.poll_update_check)

    def poll_update_check(self):
        if self._closing:
            return
        if self._update_thread.is_alive():
            self.root.after(100, self.poll_update_check)
            return
        result = self._update_result
        if result[0] == 'error':
            messagebox.showwarning('Check for Updates',
                                   'Could not check for updates. Check your internet connection and try again.',
                                   parent=self.root)
            return
        _, tag, url = result
        latest = tag.lstrip('v')
        if is_newer(latest, __version__):
            if messagebox.askyesno('Update Available',
                                   f'Image Swiper {latest} is available. You have {__version__}.\n\n'
                                   'Open the release page to download it?', parent=self.root):
                webbrowser.open(url)
        else:
            messagebox.showinfo('Check for Updates',
                                f'You have the latest version ({__version__}).', parent=self.root)

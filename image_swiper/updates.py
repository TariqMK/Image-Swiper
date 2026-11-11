"""Manual update check: asks GitHub for the latest release, only when the user clicks the version.

The request goes to api.github.com, sends no user data, and nothing is downloaded
or stored. A newer version is offered as a link to its release page in the browser.
"""

import json
import re
import socket
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from threading import Thread

from .version import __version__
from .widgets import FlatButton

APP_NAME = 'Image Swiper'
REPOSITORY = 'TariqMK/Image-Swiper'
LATEST_RELEASE_API = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
RELEASES_PAGE = f'https://github.com/{REPOSITORY}/releases'
TIMEOUT_SECONDS = 10
VERSION = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')
DIALOG_TITLE = 'Check for updates'


class UpdateError(Exception):
    """A failed check, with a message written for the user."""


def parse_version(text):
    """Return (major, minor, patch) from '1.2.3' or 'v1.2.3', or None for anything else."""
    match = VERSION.match(str(text).strip())
    return tuple(map(int, match.groups())) if match else None


def is_newer(latest, current):
    latest_v, current_v = parse_version(latest), parse_version(current)
    return latest_v is not None and current_v is not None and latest_v > current_v


def display_version(text):
    return 'v' + str(text).strip().lstrip('v')


def classify(latest, current):
    """'newer', 'current' or 'dev' (the running version is not a release number)."""
    if parse_version(current) is None:
        return 'dev'
    return 'newer' if is_newer(latest, current) else 'current'


def fetch_latest_release(timeout=TIMEOUT_SECONDS):
    """Return (tag, release page URL, release notes) for the latest published release.

    Raises UpdateError with a message for the user when the check fails.
    """
    request = urllib.request.Request(LATEST_RELEASE_API, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': f'Image-Swiper/{__version__}',
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise UpdateError(f'No {APP_NAME} releases are published yet.') from error
        if error.code in (403, 429):
            raise UpdateError('GitHub limits how often it can be checked. Try again in an hour.') from error
        raise UpdateError(f'GitHub answered with error {error.code}. Try again later.') from error
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as error:
        reason = getattr(error, 'reason', None) or error
        raise UpdateError(f"Can't reach GitHub: {reason}. Check the internet connection.") from error
    except ValueError as error:  # JSON that can't be read
        raise UpdateError(f"GitHub sent an answer {APP_NAME} can't read. Try again later.") from error
    tag = data.get('tag_name') if isinstance(data, dict) else None
    if not parse_version(tag):
        raise UpdateError(f"GitHub sent an answer {APP_NAME} can't read. Try again later.")
    url = data.get('html_url') or ''
    # Only ever open this project's own release pages, over https.
    if not url.startswith(RELEASES_PAGE + '/'):
        url = RELEASES_PAGE
    notes = data.get('body') if isinstance(data.get('body'), str) else ''
    return tag, url, notes.strip()


def result_text(kind, latest, current):
    """Headline and detail for a successful check."""
    latest, current = display_version(latest), display_version(current)
    if kind == 'newer':
        return (f'{APP_NAME} {latest} is available.',
                f'You have {current}. Open the release page to download the new version.')
    if kind == 'dev':
        return ('This is a development build.',
                f'You are running {current}. The latest release is {latest}.')
    return f'{APP_NAME} is up to date.', f'{current} is the latest release.'


class UpdatesMixin:
    def check_for_updates(self):
        if getattr(self, '_update_thread', None) is not None and self._update_thread.is_alive():
            return
        self._update_result = None
        self.version_btn.set_checking(True)

        def work():
            try:
                self._update_result = ('ok', *fetch_latest_release())
            except UpdateError as error:
                self._update_result = ('error', str(error))
            except Exception:  # Anything unexpected still gets a readable message.
                self._update_result = ('error', f"GitHub sent an answer {APP_NAME} can't read. Try again later.")

        self._update_thread = Thread(target=work, name='update-check', daemon=True)
        self._update_thread.start()
        self.root.after(100, self.poll_update_check)

    def poll_update_check(self):
        if self._closing:
            return
        if self._update_thread.is_alive():
            self.root.after(100, self.poll_update_check)
            return
        self.version_btn.set_checking(False)
        result = self._update_result
        if result[0] == 'error':
            self.show_update_dialog("Couldn't check for updates.", result[1])
            return
        _, tag, url, notes = result
        kind = classify(tag, __version__)
        headline, detail = result_text(kind, tag, __version__)
        if kind == 'newer':
            self.version_btn.mark_update(display_version(tag))
        open_page = (lambda: webbrowser.open(url)) if kind in ('newer', 'dev') else None
        self.show_update_dialog(headline, detail, notes=notes if open_page else '', open_page=open_page)

    def show_update_dialog(self, headline, detail, notes='', open_page=None):
        t = self.theme
        dialog = tk.Toplevel(self.root, bg=t.bar)
        dialog.title(DIALOG_TITLE)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        body = tk.Frame(dialog, bg=t.bar)
        body.pack(fill=tk.BOTH, expand=True, padx=t.px(24), pady=(t.px(20), t.px(16)))
        wrap = t.px(380)
        tk.Label(body, text=headline, bg=t.bar, fg=t.text, font=t.font(15, semibold=True),
                 justify=tk.LEFT, anchor='w', wraplength=wrap).pack(fill=tk.X)
        tk.Label(body, text=detail, bg=t.bar, fg=t.text_secondary, font=t.font(13),
                 justify=tk.LEFT, anchor='w', wraplength=wrap).pack(fill=tk.X, pady=(t.px(6), 0))

        if notes:
            notes_box = tk.Text(body, bg=t.control, fg=t.text_secondary, font=t.font(12),
                                height=10, width=1, wrap=tk.WORD, bd=0, highlightthickness=0,
                                padx=t.px(10), pady=t.px(8))
            notes_box.insert('1.0', notes)
            notes_box.configure(state=tk.DISABLED)
            toggle = tk.Label(body, text='▸ Release notes', bg=t.bar, fg=t.text_secondary,
                              font=t.font(12), cursor='hand2', anchor='w', takefocus=1,
                              highlightthickness=1, highlightbackground=t.bar, highlightcolor=t.accent)

            def flip(event=None):
                if notes_box.winfo_ismapped():
                    notes_box.pack_forget()
                    toggle.configure(text='▸ Release notes')
                else:
                    notes_box.pack(fill=tk.BOTH, expand=True, pady=(t.px(6), 0), after=toggle)
                    toggle.configure(text='▾ Release notes')
            toggle.bind('<Button-1>', flip)
            toggle.bind('<Return>', flip)
            toggle.bind('<space>', flip)
            toggle.pack(fill=tk.X, pady=(t.px(12), 0))

        buttons = tk.Frame(dialog, bg=t.bar)
        buttons.pack(fill=tk.X, padx=t.px(24), pady=(0, t.px(20)))

        def close(event=None):
            dialog.destroy()

        def open_and_close(event=None):
            open_page()
            close()

        if open_page:
            FlatButton(buttons, t, 'Open release page', open_and_close, variant='primary',
                       height=32).pack(side=tk.RIGHT)
            FlatButton(buttons, t, 'Close', close, height=32).pack(side=tk.RIGHT, padx=(0, t.px(8)))
            dialog.bind('<Return>', open_and_close)
        else:
            FlatButton(buttons, t, 'Close', close, variant='primary', height=32).pack(side=tk.RIGHT)
            dialog.bind('<Return>', close)
        dialog.bind('<Escape>', close)

        dialog.update_idletasks()
        width = max(dialog.winfo_reqwidth(), wrap + t.px(48))
        dialog.minsize(width, 1)  # height follows the content, so the release notes can expand
        x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_rooty() + t.px(80)
        dialog.geometry(f'+{max(0, x)}+{max(0, y)}')
        self.style_title_bar(dialog)
        dialog.grab_set()
        dialog.focus_set()

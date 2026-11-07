"""Ui operations for the desktop application."""

import tkinter as tk
from tkinter import messagebox
import os
import subprocess
import sys
from datetime import datetime
import base64
import io
from PIL import Image, ImageTk
from . import app_icon, icons
from .recycle_bin import CAN_RESTORE
from .version import __version__
from .widgets import FlatButton, Segmented, Switch

MOD = 'Command' if sys.platform == 'darwin' else 'Control'
MOD_LABEL = '⌘' if sys.platform == 'darwin' else 'Ctrl '
FILE_MANAGER = {'win32': 'Explorer', 'darwin': 'Finder'}.get(sys.platform, 'file manager')
TRASH = 'Recycle Bin' if sys.platform == 'win32' else 'Trash'
ORDERS = [('name', 'Name'), ('date', 'Date'), ('shuffle', 'Shuffle')]


def shorten(text, limit):
    """Trim the middle of long paths and names so both ends stay readable."""
    if len(text) <= limit:
        return text
    keep = (limit - 1) // 2
    return f'{text[:keep]}…{text[-keep:]}'


class UiMixin:
    def setup_ui(self):
        t = self.theme
        self.root.configure(bg=t.window)
        self.root.minsize(t.px(980), t.px(640))
        self._ui_images = {}
        self._source_img = None
        self._render_cache = None
        self._render_after = None
        self._nav_zone = None
        self._canvas_message = None

        self.build_toolbar()
        tk.Frame(self.root, bg=t.hairline, height=1).pack(fill=tk.X, side=tk.TOP)
        self.build_decision_bar()
        tk.Frame(self.root, bg=t.hairline, height=1).pack(fill=tk.X, side=tk.BOTTOM)
        self.build_strip()
        self.build_viewer()
        if sys.platform == 'darwin':
            self.build_menubar()
        self.show_welcome()

    def _image(self, key, factory):
        if key not in self._ui_images:
            self._ui_images[key] = ImageTk.PhotoImage(factory())
        return self._ui_images[key]

    def _separator(self, parent):
        t = self.theme
        tk.Frame(parent, bg=t.hairline, width=1, height=t.px(20)).pack(side=tk.LEFT, padx=t.px(16))

    # Toolbar: brand, folder, order, filters

    def build_toolbar(self):
        t = self.theme
        bar = tk.Frame(self.root, bg=t.bar, height=t.px(56))
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)
        inner = tk.Frame(bar, bg=t.bar)
        inner.pack(fill=tk.BOTH, expand=True, padx=t.px(16))

        try:
            mark = self._image('mark', lambda: Image.open(
                io.BytesIO(base64.b64decode(app_icon.TOOLBAR))).convert('RGBA').resize(
                (t.px(22), t.px(22)), Image.Resampling.LANCZOS))
            tk.Label(inner, image=mark, bg=t.bar).pack(side=tk.LEFT, padx=(0, t.px(10)))
        except OSError:
            pass
        tk.Label(inner, text='Image Swiper', bg=t.bar, fg=t.text,
                 font=t.font(14, semibold=True)).pack(side=tk.LEFT)
        tk.Label(inner, text=__version__, bg=t.bar, fg=t.text_muted,
                 font=t.font(11, 'mono')).pack(side=tk.LEFT, padx=(t.px(8), 0), pady=(t.px(2), 0))

        self._separator(inner)
        FlatButton(inner, t, 'Open Folder…', self.select_folder, icon='folder').pack(side=tk.LEFT)
        self.recent_btn = FlatButton(inner, t, command=self.show_recent_menu, icon='chevron-down')
        self.recent_btn.pack(side=tk.LEFT, padx=(t.px(4), 0))

        self._separator(inner)
        self.order_var = tk.StringVar(value='name')
        self.order_control = Segmented(inner, t, ORDERS, 'name', self.set_order)
        self.order_control.pack(side=tk.LEFT)

        self.subdirs_var = tk.BooleanVar(value=True)
        self.subdirs_switch = Switch(inner, t, 'Subfolders', self.subdirs_var, self.toggle_subdirs)
        self.subdirs_switch.pack(side=tk.LEFT, padx=(t.px(20), 0))

        self.this_day_var = tk.BooleanVar(value=False)
        self.this_day_switch = Switch(inner, t, 'On This Day', self.this_day_var, self.toggle_this_day)
        self.this_day_switch.pack(side=tk.LEFT, padx=(t.px(20), 0))

        # Day stepper, shown only while On This Day is on.
        self.date_nav_frame = tk.Frame(inner, bg=t.bar)
        self.prev_day_btn = FlatButton(self.date_nav_frame, t, command=self.previous_day,
                                       variant='ghost', icon='chevron-left', height=28)
        self.prev_day_btn.pack(side=tk.LEFT)
        self.viewing_date_label = tk.Label(self.date_nav_frame, text='', bg=t.bar, fg=t.text,
                                           font=t.font(13), width=6)
        self.viewing_date_label.pack(side=tk.LEFT)
        self.next_day_btn = FlatButton(self.date_nav_frame, t, command=self.next_day,
                                       variant='ghost', icon='chevron-right', height=28)
        self.next_day_btn.pack(side=tk.LEFT)

        self.more_btn = FlatButton(inner, t, command=self.show_more_menu, variant='ghost', icon='more')
        self.more_btn.pack(side=tk.RIGHT)

    def _menu(self):
        t = self.theme
        return tk.Menu(self.root, tearoff=0, bg=t.control, fg=t.text, activebackground=t.control_active,
                       activeforeground=t.text, disabledforeground=t.text_disabled, bd=0,
                       font=t.font(13))

    def _post_menu(self, menu, widget):
        try:
            menu.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height() + self.theme.px(4))
        finally:
            menu.grab_release()

    def fill_recent_menu(self, menu):
        menu.delete(0, tk.END)
        for folder in self.recent_folders.folders:
            menu.add_command(label=shorten(folder, 64),
                             command=lambda f=folder: self.select_recent_folder(f))
        if not self.recent_folders.folders:
            menu.add_command(label='No recent folders', state=tk.DISABLED)
        menu.add_separator()
        menu.add_command(label='Choose Folder…', command=self.select_folder)

    def show_recent_menu(self):
        menu = self._menu()
        self.fill_recent_menu(menu)
        self._post_menu(menu, self.recent_btn)

    def show_more_menu(self):
        menu = self._menu()
        menu.add_command(label=f'Show in {FILE_MANAGER}', command=self.open_folder,
                         state=tk.NORMAL if self.current_file() else tk.DISABLED)
        menu.add_separator()
        menu.add_command(label='Clear Thumbnail Cache…', command=self.clean_thumbnails)
        self._post_menu(menu, self.more_btn)

    def build_menubar(self):
        """macOS keeps every command in the menu bar, as people expect there."""
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Open Folder…', accelerator='Command-O', command=self.select_folder)
        recent = tk.Menu(file_menu, tearoff=0, postcommand=lambda: self.fill_recent_menu(recent))
        file_menu.add_cascade(label='Open Recent', menu=recent)
        file_menu.add_separator()
        file_menu.add_command(label=f'Show in {FILE_MANAGER}', command=self.open_folder)
        file_menu.add_command(label='Clear Thumbnail Cache…', command=self.clean_thumbnails)
        menubar.add_cascade(label='File', menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label='Undo Delete', accelerator='Command-Z', command=self.undo_delete)
        edit_menu.add_separator()
        edit_menu.add_command(label='Delete', accelerator='Q', command=self.delete_image)
        edit_menu.add_command(label='Keep', accelerator='W', command=self.keep_image)
        menubar.add_cascade(label='Edit', menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        for value, label in ORDERS:
            view_menu.add_radiobutton(label=f'Order by {label}' if value != 'shuffle' else 'Shuffle',
                                      variable=self.order_var, value=value,
                                      command=lambda v=value: self.set_order(v))
        view_menu.add_separator()
        view_menu.add_checkbutton(label='Include Subfolders', variable=self.subdirs_var,
                                  command=self.toggle_subdirs)
        view_menu.add_checkbutton(label='On This Day', variable=self.this_day_var,
                                  command=self.toggle_this_day)
        view_menu.add_command(label='Previous Day', command=self.previous_day)
        view_menu.add_command(label='Next Day', command=self.next_day)
        menubar.add_cascade(label='View', menu=view_menu)
        self.root.config(menu=menubar)

    # Viewer and contact strip

    def build_viewer(self):
        self.canvas = tk.Canvas(self.root, bg=self.theme.window, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<Motion>', self.on_canvas_motion)
        self.canvas.bind('<Leave>', lambda e: self.set_nav_zone(None))
        self.canvas.bind('<Configure>', lambda e: self.schedule_render())

    def build_strip(self):
        t = self.theme
        row = tk.Frame(self.root, bg=t.window)
        row.pack(fill=tk.X, side=tk.BOTTOM, padx=t.px(24), pady=(0, t.px(12)))
        self.stats_label = tk.Label(row, text='', bg=t.window, fg=t.text_muted, font=t.font(12, 'mono'))
        self.stats_label.pack(side=tk.RIGHT)
        self.counter_label = tk.Label(row, text='', bg=t.window, fg=t.text_secondary,
                                      font=t.font(12, 'mono'))
        self.counter_label.pack(side=tk.RIGHT, padx=(t.px(16), t.px(16)))
        self.strip = tk.Canvas(row, bg=t.window, height=t.px(20), highlightthickness=0, bd=0)
        self.strip.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.strip.bind('<Configure>', lambda e: self.render_strip())
        self.strip.bind('<Button-1>', self.on_strip_click)

    def strip_pitch(self):
        return self.strip.winfo_width() / len(self.images) if self.images else 0

    def render_strip(self):
        """Draw one frame per file, like a contact sheet: reviewed, deleted, current, upcoming."""
        t = self.theme
        s = self.strip
        s.delete('all')
        n = len(self.images)
        width, height = s.winfo_width(), s.winfo_height()
        if not n or width < 2:
            s.configure(cursor='')
            return
        s.configure(cursor='hand2')
        pitch = width / n
        bar_h = t.px(8)
        top = (height - bar_h) // 2
        current = min(self.current_index, n)

        def color(i):
            if i in self.deleted_indices:
                return t.danger
            return t.strip_reviewed if i < current else t.strip_upcoming

        if pitch >= t.px(3):
            gap = t.px(1) if pitch < t.px(8) else t.px(2)
            for i in range(n):
                x0 = round(i * pitch)
                x1 = max(x0 + 1, round((i + 1) * pitch) - gap)
                s.create_rectangle(x0, top, x1, top + bar_h, fill=color(i), width=0)
            if current < n:
                x0 = round(current * pitch)
                s.create_rectangle(x0, 0, max(x0 + t.px(2), round((current + 1) * pitch) - gap), height,
                                   fill=t.accent, width=0)
        else:
            # Too many files for separate frames: a progress bar with deletion marks.
            s.create_rectangle(0, top, width, top + bar_h, fill=t.strip_upcoming, width=0)
            s.create_rectangle(0, top, round(current * pitch), top + bar_h, fill=t.strip_reviewed, width=0)
            for x in sorted({round(i * pitch) for i in self.deleted_indices}):
                s.create_rectangle(x, top, x + 1, top + bar_h, fill=t.danger, width=0)
            if current < n:
                x0 = round(current * pitch)
                s.create_rectangle(x0, 0, x0 + t.px(2), height, fill=t.accent, width=0)

    def on_strip_click(self, event):
        if not self.images or self._scanning:
            return
        index = min(len(self.images) - 1, max(0, int(event.x / self.strip_pitch())))
        self.current_index = index
        self.set_review_enabled(True)
        self.show_current_image()

    def schedule_render(self):
        if self._render_after is not None:
            self.root.after_cancel(self._render_after)
        self._render_after = self.root.after(60, self.render_canvas)

    def render_canvas(self):
        self._render_after = None
        t = self.theme
        c = self.canvas
        c.delete('all')
        width, height = c.winfo_width(), c.winfo_height()
        if width < 2 or height < 2:
            return
        if self._source_img is None:
            self.draw_canvas_message(width, height)
        else:
            pad = t.px(24)
            img = self._source_img
            scale = min((width - pad * 2) / img.width, (height - pad * 2) / img.height, 1)
            size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
            if self._render_cache is None or self._render_cache[0] is not img or self._render_cache[1] != size:
                self._render_cache = (img, size, ImageTk.PhotoImage(img.resize(size, Image.Resampling.LANCZOS)))
            self.photo = self._render_cache[2]
            c.create_image(width // 2, height // 2, image=self.photo)
            if self.current_file_is_video:
                badge = self._image('play', lambda: self._badge('play', 64, 26))
                c.create_image(width // 2, height // 2, image=badge)
        self.draw_nav()

    def _badge(self, name, diameter, glyph):
        t = self.theme
        size, inner = t.px(diameter), t.px(glyph)
        img = icons.circle(size, (17, 18, 19, 170))
        mark = icons.icon(name, inner, '#ffffff')
        offset = t.px(2) if name == 'play' else 0
        img.alpha_composite(mark, ((size - inner) // 2 + offset, (size - inner) // 2))
        return img

    def draw_canvas_message(self, width, height):
        if not self._canvas_message:
            return
        t = self.theme
        c = self.canvas
        title, body, action, glyph_name = self._canvas_message
        cx, cy = width // 2, height // 2 - t.px(32)
        glyph = self._image(f'message-{glyph_name}',
                            lambda: icons.icon(glyph_name, t.px(40), t.text_muted, stroke=1.5))
        c.create_image(cx, cy - t.px(56), image=glyph)
        c.create_text(cx, cy, text=title, fill=t.text, font=t.font(20, 'display', semibold=True))
        c.create_text(cx, cy + t.px(32), text=body, fill=t.text_secondary, font=t.font(13),
                      width=t.px(420), justify=tk.CENTER, anchor='n')
        if action:
            if not hasattr(self, 'empty_open_btn'):
                self.empty_open_btn = FlatButton(c, t, 'Open Folder…', self.select_folder, variant='primary',
                                                 icon='folder', key=f'{MOD_LABEL}O', height=40, bg=t.window)
            c.create_window(cx, cy + t.px(104), window=self.empty_open_btn)

    def set_canvas_message(self, title, body='', action=False, glyph='image'):
        self._source_img = None
        self._canvas_message = (title, body, action, glyph)
        self.render_canvas()

    def show_welcome(self):
        self.set_canvas_message('Open a folder to start',
                                'Photos and videos appear one at a time. Keep what you want and '
                                f'delete the rest. Deleted files go to the {TRASH}.', action=True)

    def draw_nav(self):
        c = self.canvas
        c.delete('nav')
        if not self._nav_zone or self._source_img is None:
            return
        t = self.theme
        name = 'chevron-left' if self._nav_zone == 'left' else 'chevron-right'
        badge = self._image(name, lambda: self._badge(name, 40, 20))
        margin = t.px(44)
        x = margin if self._nav_zone == 'left' else c.winfo_width() - margin
        c.create_image(x, c.winfo_height() // 2, image=badge, tags='nav')

    def nav_zone_at(self, x):
        zone = self.canvas.winfo_width() // 5  # left and right 20% are navigation zones
        if x < zone and self.current_index > 0:
            return 'left'
        if x > self.canvas.winfo_width() - zone and self.current_index < len(self.images) - 1:
            return 'right'
        return None

    def set_nav_zone(self, zone):
        if zone != self._nav_zone:
            self._nav_zone = zone
            self.draw_nav()

    def on_canvas_motion(self, event):
        showing = self._source_img is not None or self.current_file_is_video
        zone = self.nav_zone_at(event.x) if showing and self.current_file() else None
        self.set_nav_zone(zone)
        clickable = zone or (self.current_file_is_video and self.current_file())
        self.canvas.configure(cursor='hand2' if clickable else '')

    # Caption and decisions

    def build_decision_bar(self):
        t = self.theme
        bar = tk.Frame(self.root, bg=t.bar, height=t.px(80))
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        inner = tk.Frame(bar, bg=t.bar)
        inner.pack(fill=tk.BOTH, expand=True, padx=t.px(24))

        caption = tk.Frame(inner, bg=t.bar)
        caption.pack(side=tk.LEFT, fill=tk.Y, pady=t.px(16))
        line1 = tk.Frame(caption, bg=t.bar)
        line1.pack(side=tk.TOP, anchor='w')
        self.date_label = tk.Label(line1, text='', bg=t.bar, fg=t.text,
                                   font=t.font(17, 'display', semibold=True), padx=0, pady=0)
        self.date_label.pack(side=tk.LEFT)
        self.years_label = tk.Label(line1, text='', bg=t.bar, fg=t.accent, font=t.font(13), padx=0, pady=0)
        self.years_label.pack(side=tk.LEFT, padx=(t.px(10), 0), pady=(t.px(3), 0))

        line2 = tk.Frame(caption, bg=t.bar)
        line2.pack(side=tk.TOP, anchor='w', pady=(t.px(4), 0))
        self.meta_label = tk.Label(line2, text='', bg=t.bar, fg=t.text_muted, font=t.font(12, 'mono'),
                                   padx=0, pady=0)
        self.meta_label.pack(side=tk.LEFT)
        folder = self._image('folder-small', lambda: icons.icon('folder', t.px(14), t.text_secondary))
        self.path_label = tk.Label(line2, text='', image=folder, compound=tk.LEFT, bg=t.bar,
                                   fg=t.text_secondary, font=t.font(12), padx=0, pady=0, cursor='hand2')
        self.path_label.bind('<Button-1>', self.open_folder)
        self.path_label.bind('<Enter>', lambda e: self.path_label.configure(fg=t.text))
        self.path_label.bind('<Leave>', lambda e: self.path_label.configure(fg=t.text_secondary))

        buttons = tk.Frame(inner, bg=t.bar)
        buttons.pack(side=tk.RIGHT)
        self.keep_btn = FlatButton(buttons, t, 'Keep', self.keep_image, variant='primary',
                                   icon='check', key='W', height=40)
        self.keep_btn.pack(side=tk.RIGHT)
        self.delete_btn = FlatButton(buttons, t, 'Delete', self.delete_image, variant='danger',
                                     icon='trash', key='Q', height=40)
        self.delete_btn.pack(side=tk.RIGHT, padx=(0, t.px(8)))
        self.undo_btn = FlatButton(buttons, t, 'Undo', self.undo_delete, variant='ghost',
                                   icon='undo', key=f'{MOD_LABEL}Z', height=40)
        if CAN_RESTORE:
            self.undo_btn.pack(side=tk.RIGHT, padx=(0, t.px(16)))
        self.undo_btn.set_enabled(False)
        self.set_review_enabled(False)

    def set_review_enabled(self, enabled):
        self.delete_btn.set_enabled(enabled)
        self.keep_btn.set_enabled(enabled)

    def update_caption(self, file_path, file_date, file_size):
        t = self.theme
        if file_date:
            years_ago = datetime.now().year - file_date.year
            self.date_label.config(text=f'{file_date.day} {file_date:%B %Y}', fg=t.text)
            self.years_label.config(text=f"{years_ago} year{'s' if years_ago != 1 else ''} ago"
                                    if years_ago > 0 else 'This year')
        else:
            self.date_label.config(text='Undated', fg=t.text_secondary)
            self.years_label.config(text='')
        kind = 'Video' if self.current_file_is_video else 'Photo'
        self.meta_label.config(text=f'{shorten(file_path.name, 40)}  ·  '
                                    f'{self.format_file_size(file_size)}  ·  {kind}')
        self.path_label.config(text=f' {shorten(str(file_path.parent), 56)}')
        if not self.path_label.winfo_ismapped():
            self.path_label.pack(side=tk.LEFT, padx=(t.px(16), 0))

    def clear_caption(self):
        for label in (self.date_label, self.years_label, self.meta_label):
            label.config(text='')
        self.path_label.pack_forget()

    def update_stats(self):
        n = len(self.images)
        self.counter_label.config(text=f'{min(self.current_index + 1, n):,} / {n:,}' if n else '')
        freed = self.space_saved_mb
        freed_text = f'{freed / 1024:,.2f} GB' if freed >= 1024 else f'{freed:,.1f} MB'
        self.stats_label.config(text=f'{self.deleted_count:,} deleted  ·  {freed_text} freed' if n else '')
        self.render_strip()

    def style_title_bar(self):
        """Match the Windows title bar to the toolbar instead of the default white."""
        if sys.platform != 'win32':
            return
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            dark = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
            r, g, b = (int(self.theme.bar[i:i + 2], 16) for i in (1, 3, 5))
            caption = ctypes.c_int(b << 16 | g << 8 | r)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))
        except Exception:
            pass

    def bind_keys(self):
        self.root.bind('<Left>', lambda e: self.previous_image())
        self.root.bind('<Right>', lambda e: self.next_image())
        self.root.bind('q', lambda e: self.delete_image())
        self.root.bind('Q', lambda e: self.delete_image())
        self.root.bind('w', lambda e: self.keep_image())
        self.root.bind('W', lambda e: self.keep_image())
        self.root.bind('<BackSpace>', lambda e: self.undo_delete())
        self.root.bind(f'<{MOD}-z>', lambda e: self.undo_delete())
        self.root.bind(f'<{MOD}-o>', lambda e: self.select_folder())

    def current_file(self):
        if self.images and self.current_index < len(self.images):
            return self.images[self.current_index]
        return None

    def on_canvas_click(self, event):
        if not self.current_file():
            return

        zone = self.nav_zone_at(event.x)
        if zone == 'left':
            self.previous_image()
            return
        if zone == 'right':
            self.next_image()
            return

        # Centre click opens videos in the default player.
        if self.current_file_is_video:
            file_path = self.current_file()
            try:
                if sys.platform == 'win32':
                    os.startfile(str(file_path))
                elif sys.platform == 'darwin':
                    subprocess.run(['open', str(file_path)])
                else:
                    subprocess.run(['xdg-open', str(file_path)])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open video: {str(e)}")


    def open_folder(self, event=None):
        """Open the folder containing the current file in file explorer"""
        if self.current_file():
            folder_path = self.current_file().parent
            try:
                if sys.platform == 'win32':
                    os.startfile(str(folder_path))
                elif sys.platform == 'darwin':
                    subprocess.run(['open', str(folder_path)])
                else:
                    subprocess.run(['xdg-open', str(folder_path)])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {str(e)}")


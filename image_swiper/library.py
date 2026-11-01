"""Library operations for the desktop application."""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
from copy import copy
from queue import Empty
from threading import Event, Thread
from .scanning import scan_library
from .date_cache import DateCache

class LibraryMixin:
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder with images and videos")
        if folder:
            self.open_review_folder(folder)

    def select_recent_folder(self, folder):
        if folder in self.recent_folders.folders:
            self.open_review_folder(folder)

    def open_review_folder(self, folder):
        if not Path(folder).is_dir():
            messagebox.showwarning('Folder unavailable',
                                   'This folder is unavailable. Connect its drive or choose another folder.')
            return
        try:
            self.recent_folders.remember(folder)
        except OSError:
            messagebox.showwarning('Could not save recent folders',
                                   'You can open this folder, but its location could not be saved for next time.')
        self.processed_count = 0
        self.deleted_count = 0
        self.space_saved_mb = 0
        self.load_images(folder)


    def toggle_subdirs(self):
        self.include_subdirs = self.subdirs_var.get()
        self.subdirs_switch.redraw()


    def natural_sort_key(self, path):
        """Generate sort key for natural/numeric sorting of filenames"""
        import re
        filename = path.name.lower()
        # Split filename into text and number parts for natural sorting
        result = [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', filename)]
        # DEBUG - print first 5 files
        if not hasattr(self, '_debug_count'):
            self._debug_count = 0
        if self._debug_count < 5:
            print(f"natural_sort_key({path.name}) = {result}")
            self._debug_count += 1
        return result


    def set_order(self, order):
        """Order files by name, by date taken, or shuffled."""
        self.order_var.set(order)
        self.order_control.set_value(order)
        self.sort_by_date = order == 'date'
        self.random_mode = order == 'shuffle'
        if getattr(self, 'current_folder', None):
            self.load_images(self.current_folder)


    def toggle_this_day(self):
        self.on_this_day_mode = self.this_day_var.get()
        self.this_day_switch.redraw()
        
        if self.on_this_day_mode:
            # Show the day stepper beside the switch
            self.date_nav_frame.pack(side=tk.LEFT, padx=(self.theme.px(8), 0))
            # Reset to today
            self.viewing_date = datetime.now()
            self.update_viewing_date_label()
        else:
            self.date_nav_frame.pack_forget()
        
        if hasattr(self, 'current_folder') and self.current_folder:
            self.load_images(self.current_folder)


    def previous_day(self):
        """Navigate to previous day for On This Day"""
        from datetime import timedelta
        self.viewing_date = self.viewing_date - timedelta(days=1)
        self.update_viewing_date_label()
        if hasattr(self, 'current_folder') and self.current_folder:
            self.load_images(self.current_folder)


    def next_day(self):
        """Navigate to next day for On This Day"""
        from datetime import timedelta
        self.viewing_date = self.viewing_date + timedelta(days=1)
        self.update_viewing_date_label()
        if hasattr(self, 'current_folder') and self.current_folder:
            self.load_images(self.current_folder)


    def update_viewing_date_label(self):
        """Update the label showing which day we're viewing"""
        self.viewing_date_label.config(text=f"{self.viewing_date.day} {self.viewing_date:%b}")


    def load_images(self, folder):
        if self._closing:
            return
        if self._scan_cancel is not None:
            self._scan_cancel.set()
        self.current_folder = folder
        self.images = []
        self.current_index = 0
        self.deleted_indices = set()
        self.last_deleted_index = None
        self.set_review_enabled(False)
        self.undo_btn.set_enabled(False)
        self.clear_caption()
        self.update_stats()
        self.set_canvas_message(f'Scanning {Path(folder).name or folder}', 'Finding photos and videos…')
        self._scan_cancel = Event()
        self._scanning = True
        self._scan_generation += 1
        generation = self._scan_generation
        cancel = self._scan_cancel
        # Metadata/cache methods use a snapshot, never live UI state.
        worker = copy(self)
        options = dict(
            include_subdirs=self.include_subdirs,
            extensions=self.image_extensions | self.video_extensions,
            sort_by_date=self.sort_by_date,
            on_this_day=self.on_this_day_mode,
            reference_date=self.viewing_date,
            random_mode=self.random_mode,
        )
        def work():
            try:
                with DateCache(worker.db_path) as cache:
                    worker._date_cache_session = cache
                    images = scan_library(folder, cancel=cancel,
                        get_date=worker.get_cached_date, sort_key=worker.natural_sort_key,
                        progress=lambda text: self._scan_messages.put((generation, 'progress', text)),
                        **options)
                if not cancel.is_set():
                    self._scan_messages.put((generation, 'done', images))
            except Exception as exc:
                if not cancel.is_set():
                    self._scan_messages.put((generation, 'error', str(exc)))
        Thread(target=work, name='media-scan', daemon=True).start()

    def poll_scan(self):
        if self._closing:
            return
        # Drain only a bounded number of messages to keep event handling responsive.
        for _ in range(100):
            if self._closing:
                return
            try:
                generation, kind, value = self._scan_messages.get_nowait()
            except Empty:
                break
            if generation != self._scan_generation:
                continue
            if kind == 'progress':
                title = self._canvas_message[0] if self._canvas_message else 'Scanning'
                self.set_canvas_message(title, value)
            elif kind == 'error':
                self._scanning = False
                self.set_canvas_message('Scan failed', value, action=True)
            elif kind == 'done':
                self._scanning = False
                self.images = value
                if not self.images:
                    self.update_stats()
                    self.show_empty_folder()
                else:
                    self.current_index = 0
                    self.set_review_enabled(True)
                    self.show_current_image()
                    if self._closing:
                        return
        if not self._closing:
            self._scan_after = self.root.after(50, self.poll_scan)

    def show_empty_folder(self):
        if self.on_this_day_mode:
            day = f"{self.viewing_date.day} {self.viewing_date:%B}"
            self.set_canvas_message(f'Nothing from {day}',
                                    'No photos or videos from this day in any year. '
                                    'Try another day with the arrows beside On This Day.')
        else:
            hint = 'Choose another folder.' if self.include_subdirs else                 'Turn on Subfolders to look inside folders within this one, or choose another folder.'
            self.set_canvas_message('No photos or videos here', hint, action=True)

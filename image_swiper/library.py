"""Library operations for the desktop application."""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import random

class LibraryMixin:
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder with images and videos")
        if folder:
            self.processed_count = 0
            self.deleted_count = 0
            self.space_saved_mb = 0
            self.stats_label.config(text="Ready to organize")
            self.load_images(folder)


    def toggle_subdirs(self):
        self.include_subdirs = self.subdirs_var.get()


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


    def toggle_sort_by_date(self):
        self.sort_by_date = self.sort_by_date_var.get()
        # Just re-sort existing images, don't re-scan
        if self.images:
            if self.sort_by_date:
                file_date_pairs = []
                for file in self.images:
                    file_date = self.get_cached_date(file)
                    # Strip timezone for comparison
                    if file_date and file_date.tzinfo is not None:
                        file_date = file_date.replace(tzinfo=None)
                    file_date_pairs.append((file, file_date if file_date else datetime.min))
                # Sort by date, then by natural filename
                file_date_pairs.sort(key=lambda x: (x[1], self.natural_sort_key(x[0])))
                self.images = [file for file, _ in file_date_pairs]
            else:
                # Sort by natural filename order
                self.images.sort(key=self.natural_sort_key)
            
            self.current_index = 0
            self.show_current_image()


    def toggle_this_day(self):
        self.on_this_day_mode = self.this_day_var.get()
        
        if self.on_this_day_mode:
            # Show navigation arrows and date label
            self.date_nav_frame.pack(side=tk.LEFT, padx=5)
            self.viewing_date_label.pack(side=tk.LEFT, padx=25)
            # Reset to today
            self.viewing_date = datetime.now()
            self.update_viewing_date_label()
        else:
            # Hide navigation arrows and date label
            self.date_nav_frame.pack_forget()
            self.viewing_date_label.pack_forget()
        
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
        date_str = self.viewing_date.strftime('%B %d, %Y')
        self.viewing_date_label.config(text=f"Viewing memories from {date_str}")


    def load_images(self, folder):
        self.current_folder = folder
        self.images = []
        path = Path(folder)
        
        if self.on_this_day_mode or self.specific_date_mode:
            self.counter_label.config(text="Scanning files...")
            self.root.update()
        
        all_extensions = self.image_extensions | self.video_extensions
        
        if self.include_subdirs:
            for ext in all_extensions:
                self.images.extend(path.rglob(f'*{ext}'))
                self.images.extend(path.rglob(f'*{ext.upper()}'))
        else:
            for ext in all_extensions:
                self.images.extend(path.glob(f'*{ext}'))
                self.images.extend(path.glob(f'*{ext.upper()}'))
        
        self.images = sorted(list(set(self.images)), key=self.natural_sort_key)
        
        # Sort by date taken if toggled, otherwise keep filename sort
        if self.sort_by_date:
            file_date_pairs = []
            for file in self.images:
                file_date = self.get_cached_date(file)
                # Strip timezone for comparison
                if file_date and file_date.tzinfo is not None:
                    file_date = file_date.replace(tzinfo=None)
                file_date_pairs.append((file, file_date if file_date else datetime.min))
            # Sort by date, then by natural filename
            file_date_pairs.sort(key=lambda x: (x[1], self.natural_sort_key(x[0])))
            self.images = [file for file, _ in file_date_pairs]
        
        if self.on_this_day_mode:
            total_files = len(self.images)
            filtered_files = []
            for i, file in enumerate(self.images):
                if i % 100 == 0:
                    self.counter_label.config(text=f"Scanning {i}/{total_files}...")
                    self.root.update()
                
                file_date = self.get_cached_date(file)
                if self.matches_this_day(file_date):
                    if file_date and file_date.tzinfo is not None:
                        file_date = file_date.replace(tzinfo=None)
                    filtered_files.append((file, file_date))
            
            filtered_files.sort(key=lambda x: (x[1], self.natural_sort_key(x[0])))
            self.images = [file for file, date in filtered_files]
            
            # DEBUG: Print filtered files to see order after On This Day sorting
            print("\nDEBUG - Files after 'On This Day' filtering (all):")
            for i, f in enumerate(self.images):
                print(f"  {i+1}. {f.name}")
            
            if not self.images:
                date_str = self.viewing_date.strftime('%B %d')
                messagebox.showinfo("No Memories", f"No photos or videos found from {date_str} in previous years.")
                self.counter_label.config(text="No files loaded")
                return
        
        # Apply sort by date if toggled
        if self.sort_by_date and self.images:
            file_date_pairs = []
            for file in self.images:
                file_date = self.get_cached_date(file)
                # Strip timezone for comparison
                if file_date and file_date.tzinfo is not None:
                    file_date = file_date.replace(tzinfo=None)
                file_date_pairs.append((file, file_date if file_date else datetime.min))
            # Sort by date, then by natural filename
            file_date_pairs.sort(key=lambda x: (x[1], self.natural_sort_key(x[0])))
            self.images = [file for file, _ in file_date_pairs]
        
        if not self.images:
            messagebox.showinfo("No Files", "No images or videos found in the selected folder.")
            return
        
        if self.random_mode and not self.on_this_day_mode:
            random.shuffle(self.images)
            
        self.current_index = 0
        self.show_current_image()
        self.delete_btn.config(state=tk.NORMAL, bg=self.accent_danger)
        self.undo_btn.config(state=tk.DISABLED, bg='#4a4a4a')


    def toggle_random_mode(self):
        self.random_mode = self.random_var.get()
        if self.images:
            if self.random_mode:
                random.shuffle(self.images)
            else:
                self.images = sorted(self.images)
            self.current_index = 0
            self.show_current_image()



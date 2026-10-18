"""Application state and review actions."""

import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import sqlite3
from .paths import runtime_paths
from .recycle_bin import CAN_RESTORE, delete_file, restore_file
from .ui import UiMixin
from .media import MediaMixin
from .metadata import MetadataMixin
from .cache import CacheMixin
from .library import LibraryMixin
from .version import __version__

class ImageOrganizer(UiMixin, MediaMixin, MetadataMixin, CacheMixin, LibraryMixin):
    def __init__(self, root):
        self.root = root
        self.root.title(f"Memory Organizer v{__version__}")
        self.root.geometry("1100x800")
        
        # Modern color scheme - dark elegant theme
        self.bg_primary = '#0f0f0f'
        self.bg_secondary = '#1a1a1a'
        self.bg_card = '#252525'
        self.accent_primary = '#6366f1'  # Indigo
        self.accent_success = '#10b981'  # Emerald
        self.accent_danger = '#ef4444'   # Red
        self.accent_warning = '#f59e0b'  # Amber
        self.accent_info = '#3b82f6'     # Blue
        self.text_primary = '#f8fafc'
        self.text_secondary = '#94a3b8'
        self.text_muted = '#64748b'
        
        self.root.configure(bg=self.bg_primary)
        
        self.images = []
        self.current_index = 0
        self.photo = None
        self.random_mode = False
        self.include_subdirs = True
        self.sort_by_date = False
        self.on_this_day_mode = False
        self.specific_date_mode = False
        self.target_date = None
        self.viewing_date = datetime.now()  # Track which day we're viewing for "On This Day"
        self.last_deleted = None
        self.last_deleted_size = 0
        self.processed_count = 0
        self.deleted_count = 0
        self.space_saved_mb = 0
        self.current_file_is_video = False
        
        # Database setup
        self.db_path, self.thumbnails_dir = runtime_paths()
        self.thumbnails_dir.mkdir(exist_ok=True)
        self.init_database()
        
        # Check for ffmpeg
        self.ffmpeg_available = self.check_ffmpeg()
        if not self.ffmpeg_available:
            print("WARNING: ffmpeg not found. Video thumbnails will not be generated.")
        
        # Supported formats
        self.image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', 
            '.ico', '.heic', '.heif', '.jfif', '.ppm', '.pgm', '.pbm', '.pnm',
            '.svg', '.raw', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf'
        }
        
        self.video_extensions = {
            '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v',
            '.mpg', '.mpeg', '.3gp', '.m2ts', '.mts', '.ts', '.vob', '.ogv'
        }
        
        self.setup_ui()
        self.bind_keys()


    def delete_image(self):
        if not self.images or self.current_index >= len(self.images):
            return
            
        file_path = self.images[self.current_index]
        
        try:
            file_size_bytes = file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            delete_file(file_path)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM image_cache WHERE filepath = ?', (str(file_path),))
            conn.commit()
            conn.close()
            
            self.last_deleted = file_path
            self.last_deleted_size = file_size_mb
            if CAN_RESTORE:
                self.undo_btn.config(state=tk.NORMAL, bg=self.accent_warning)
            self.deleted_count += 1
            self.processed_count += 1
            self.space_saved_mb += file_size_mb
            self.current_index += 1
            self.show_current_image()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete file: {str(e)}")


    def undo_delete(self):
        if not CAN_RESTORE:
            return
        if not self.last_deleted:
            return
        
        try:
            restore_file(self.last_deleted)
            
            is_video = self.is_video_file(self.last_deleted)
            
            if is_video:
                file_date = self.get_video_date(self.last_deleted)
                thumbnail_path = self.generate_video_thumbnail(self.last_deleted)
            else:
                file_date = self.extract_image_date(self.last_deleted)
                thumbnail_path = None
            
            file_size = self.last_deleted.stat().st_size
            current_mtime = self.last_deleted.stat().st_mtime
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO image_cache (filepath, date_taken, file_size, last_modified, is_video, thumbnail_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(self.last_deleted), file_date.isoformat() if file_date else None, file_size, current_mtime,
                  1 if is_video else 0, str(thumbnail_path) if thumbnail_path else None))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Undo", f"Restored: {self.last_deleted.name}")
            self.last_deleted = None
            self.undo_btn.config(state=tk.DISABLED, bg='#4a4a4a')
            self.deleted_count -= 1
            self.processed_count -= 1
            self.space_saved_mb -= self.last_deleted_size
            self.last_deleted_size = 0
            self.show_current_image()
        except Exception as e:
            messagebox.showerror("Error", f"Could not restore file: {str(e)}\nRestore manually from Recycle Bin.")


    def keep_image(self):
        """Navigate to next image (used by arrow keys and W key for consistency)"""
        if not self.images or self.current_index >= len(self.images):
            return
            
        self.processed_count += 1
        self.current_index += 1
        self.show_current_image()


    def previous_image(self):
        if not self.images:
            return
        original_index = self.current_index
        while self.current_index > 0:
            self.current_index -= 1
            if self.images[self.current_index].exists():
                self.show_current_image()
                return
        self.current_index = original_index


    def next_image(self):
        if not self.images:
            return
        self.processed_count += 1
        original_index = self.current_index
        while self.current_index < len(self.images) - 1:
            self.current_index += 1
            if self.images[self.current_index].exists():
                self.show_current_image()
                return
        self.current_index = original_index



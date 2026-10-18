"""Cache operations for the desktop application."""

from pathlib import Path
from datetime import datetime
from tkinter import messagebox
import sqlite3
from contextlib import closing

class CacheMixin:
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS image_cache (
                filepath TEXT PRIMARY KEY,
                date_taken TEXT,
                file_size INTEGER,
                last_modified REAL,
                is_video INTEGER,
                thumbnail_path TEXT
            )
        ''')

        try:
            cursor.execute("SELECT is_video FROM image_cache LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE image_cache ADD COLUMN is_video INTEGER DEFAULT 0")

        try:
            cursor.execute("SELECT thumbnail_path FROM image_cache LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE image_cache ADD COLUMN thumbnail_path TEXT")

        conn.commit()
        conn.close()


    def get_cached_date(self, file_path):
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT date_taken, last_modified FROM image_cache WHERE filepath = ?', (str(file_path),))
            result = cursor.fetchone()

            current_mtime = file_path.stat().st_mtime

            if result and result[1] == current_mtime:
                if result[0]:
                    return datetime.fromisoformat(result[0])
                return None

            is_video = file_path.suffix.lower() in self.video_extensions

            if is_video:
                file_date = self.get_video_date(file_path)
                thumbnail_path = self.generate_video_thumbnail(file_path)
            else:
                file_date = self.extract_image_date(file_path)
                thumbnail_path = None

            if getattr(self, "_scan_cancel", None) is not None and self._scan_cancel.is_set():
                return None
            file_size = file_path.stat().st_size

            cursor.execute('''
                INSERT OR REPLACE INTO image_cache (filepath, date_taken, file_size, last_modified, is_video, thumbnail_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(file_path), file_date.isoformat() if file_date else None, file_size, current_mtime,
                  1 if is_video else 0, str(thumbnail_path) if thumbnail_path else None))

            conn.commit()

            return file_date


    def clean_thumbnails(self):
        if not self.thumbnails_dir.exists():
            messagebox.showinfo("Clean Thumbnails", "No thumbnails folder found.")
            return

        try:
            thumbnail_files = list(self.thumbnails_dir.glob('*.jpg'))

            if not thumbnail_files:
                messagebox.showinfo("Clean Thumbnails", "No thumbnails to clean.")
                return

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT filepath, thumbnail_path FROM image_cache WHERE is_video = 1')
            video_records = cursor.fetchall()
            conn.close()

            orphaned = []
            for thumb_file in thumbnail_files:
                is_orphaned = True
                for video_path, thumb_path in video_records:
                    if thumb_path and Path(thumb_path) == thumb_file:
                        if Path(video_path).exists():
                            is_orphaned = False
                            break

                if is_orphaned:
                    orphaned.append(thumb_file)

            if not orphaned:
                messagebox.showinfo("Clean Thumbnails", "No orphaned thumbnails found. All clean!")
                return

            size_mb = sum(f.stat().st_size for f in orphaned) / (1024 * 1024)
            if messagebox.askyesno("Clean Thumbnails",
                                  f"Found {len(orphaned)} orphaned thumbnail(s) ({size_mb:.1f} MB).\n\nDelete them?"):
                for thumb_file in orphaned:
                    thumb_file.unlink()

                messagebox.showinfo("Clean Thumbnails",
                                   f"Deleted {len(orphaned)} orphaned thumbnail(s), freed {size_mb:.1f} MB.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not clean thumbnails: {str(e)}")



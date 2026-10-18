"""Cache operations for the desktop application."""

from pathlib import Path
from datetime import datetime
from tkinter import messagebox
import sqlite3
from contextlib import closing
from .date_cache import DateCache

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
        session = getattr(self, '_date_cache_session', None)
        if session is not None:
            return self._read_cached_date(file_path, session)
        with DateCache(self.db_path, batch_size=1) as session:
            return self._read_cached_date(file_path, session)

    def _read_cached_date(self, file_path, session):
        cancel = getattr(self, '_scan_cancel', None)
        if cancel is not None and cancel.is_set():
            return None
        stat = file_path.stat()
        result = session.lookup(file_path)
        if result and result[1] == stat.st_mtime:
            return datetime.fromisoformat(result[0]) if result[0] else None
        is_video = file_path.suffix.lower() in self.video_extensions
        # Date scans never decode or generate video previews.
        date = self.get_video_date(file_path) if is_video else self.extract_image_date(file_path)
        if cancel is not None and cancel.is_set():
            return None
        session.store(file_path, date, stat.st_size, stat.st_mtime, is_video)
        return date

    def record_thumbnail(self, file_path, thumbnail):
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.execute('UPDATE image_cache SET thumbnail_path = ? WHERE filepath = ?',
                               (str(thumbnail), str(file_path)))


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



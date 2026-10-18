"""One connection per scan, with short batched write transactions."""
import sqlite3
from time import monotonic


class DateCache:
    def __init__(self, path, batch_size=100, flush_interval=1.0):
        self.connection = sqlite3.connect(path)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pending = {}
        self.last_flush = monotonic()

    def __enter__(self):
        return self

    def lookup(self, path):
        key = str(path)
        if key in self.pending:
            row = self.pending[key]
            return row[1], row[3]
        return self.connection.execute(
            'SELECT date_taken, last_modified FROM image_cache WHERE filepath = ?', (key,)
        ).fetchone()

    def store(self, path, date, size, mtime, is_video):
        self.pending[str(path)] = (str(path), date.isoformat() if date else None,
                                   size, mtime, int(is_video), None)
        if len(self.pending) >= self.batch_size or monotonic() - self.last_flush >= self.flush_interval:
            self.flush()

    def flush(self):
        if not self.pending:
            return
        # Metadata extraction happens outside a transaction: slow probes do not
        # hold the SQLite write lock and block another scan or a UI operation.
        with self.connection:
            self.connection.executemany('''
                INSERT OR REPLACE INTO image_cache
                    (filepath, date_taken, file_size, last_modified, is_video, thumbnail_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', self.pending.values())
        self.pending.clear()
        self.last_flush = monotonic()

    def __exit__(self, *exception):
        try:
            # Also preserve completed metadata when cancelled or interrupted.
            self.flush()
        finally:
            self.connection.close()

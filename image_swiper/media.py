"""Media operations for the desktop application."""

from tkinter import messagebox
from PIL import Image
from .processes import run_background
from datetime import datetime
from hashlib import sha1
from threading import Thread
from uuid import uuid4

# Register HEIC decoding when the optional package is installed.
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception as exc:
    print(f'WARNING: HEIC support not available: {exc}')


def open_detached(path):
    """Decode an image fully into memory and close its file.

    Pillow keeps multi-frame files (GIF, TIFF, phone MPO JPEGs) open after
    load(), and Windows refuses to delete a file that is still open.
    """
    with Image.open(path) as source:
        return source.copy()

class MediaMixin:
    def check_ffmpeg(self):
        try:
            run_background(['ffmpeg', '-version'], check=True)
            return True
        except:
            return False


    def video_thumbnail_path(self, video_path):
        # hash() changes every launch, so derive a name that stays stable.
        return self.thumbnails_dir / f"{sha1(str(video_path).encode('utf-8')).hexdigest()}.jpg"


    def generate_video_thumbnail(self, video_path):
        if not self.ffmpeg_available:
            return None
        
        thumb_path = self.video_thumbnail_path(video_path)
        if thumb_path.exists():
            return thumb_path

        # Publish only complete previews, including when a scan is interrupted.
        work_path = thumb_path.with_name(f'.{thumb_path.stem}.{uuid4().hex}.jpg')
        try:
            run_background(
                ['ffmpeg', '-ss', '00:00:01', '-i', str(video_path),
                 '-vframes', '1', '-q:v', '2', str(work_path)],
                timeout=10, check=True
            )
            
            if work_path.exists():
                work_path.replace(thumb_path)
                return thumb_path
        except:
            pass
        finally:
            try:
                work_path.unlink(missing_ok=True)
            except OSError:
                pass
        
        return None


    def request_video_preview(self, video_path):
        """Make a missing preview off the UI thread so clicks stay responsive.

        One FFmpeg runs at a time; skipping quickly past videos only previews
        the one you stop on.
        """
        if self._preview_thread is not None and self._preview_thread.is_alive():
            return
        self._preview_file = video_path
        self._preview_thread = Thread(target=self.generate_video_thumbnail, args=(video_path,),
                                      name='video-preview', daemon=True)
        self._preview_thread.start()
        self.root.after(50, self.poll_video_preview)


    def poll_video_preview(self):
        if self._closing:
            return
        if self._preview_thread.is_alive():
            self.root.after(50, self.poll_video_preview)
            return
        finished, self._preview_file = self._preview_file, None
        if not self.video_thumbnail_path(finished).exists():
            self._preview_failed.add(finished)
        current = self.current_file()
        if current is None or not self.is_video_file(current):
            return
        if current == finished or self.video_thumbnail_path(current).exists():
            self.show_current_image()
        elif current not in self._preview_failed:
            self.request_video_preview(current)


    def wait_for_video_preview(self, video_path):
        """Let FFmpeg release a video before it is deleted."""
        if self._preview_file == video_path and self._preview_thread.is_alive():
            self._preview_thread.join(timeout=15)


    def is_video_file(self, file_path):
        return file_path.suffix.lower() in self.video_extensions


    def show_current_image(self):
        if not self.images or self.current_index >= len(self.images):
            self.show_review_complete()
            return
            
        file_path = self.images[self.current_index]
        
        try:
            if not file_path.exists():
                if self.current_index < len(self.images) - 1:
                    self.current_index += 1
                    self.show_current_image()
                elif self.current_index > 0:
                    self.current_index -= 1
                    self.show_current_image()
                return
            
            self.current_file_is_video = self.is_video_file(file_path)
            thumb_path = None

            preview_coming = False
            if self.current_file_is_video:
                thumb_path = self.video_thumbnail_path(file_path)
                if not thumb_path.exists():
                    thumb_path = None
                    if self.ffmpeg_available and file_path not in self._preview_failed:
                        self.request_video_preview(file_path)
                        preview_coming = True
                img = open_detached(thumb_path) if thumb_path else None
            else:
                # Handle different image formats
                if file_path.suffix.lower() == '.cr3':
                    try:
                        import rawpy
                        with rawpy.imread(str(file_path)) as raw:
                            img = Image.fromarray(raw.postprocess())
                    except ImportError:
                        raise Exception("CR3 support requires 'rawpy'. Install with: pip install rawpy")
                    except Exception as cr3_error:
                        try:
                            img = open_detached(file_path)
                        except:
                            raise cr3_error
                elif file_path.suffix.lower() in ['.heic', '.heif']:
                    try:
                        import pillow_heif
                        heif_file = pillow_heif.read_heif(str(file_path))
                        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
                    except Exception as heic_error:
                        try:
                            img = open_detached(file_path)
                        except:
                            raise heic_error
                elif file_path.suffix.lower() in ['.raw', '.cr2', '.nef', '.arw', '.dng', '.orf']:
                    try:
                        import rawpy
                        with rawpy.imread(str(file_path)) as raw:
                            img = Image.fromarray(raw.postprocess())
                    except ImportError:
                        raise Exception("RAW file support requires 'rawpy'. Install with: pip install rawpy")
                    except Exception as raw_error:
                        try:
                            img = open_detached(file_path)
                        except:
                            raise raw_error
                else:
                    img = open_detached(file_path)
            
            if img is None:
                self.set_canvas_message('Loading preview' if preview_coming else 'Preview unavailable',
                                        'Click to open this video in your default player.')
            else:
                self._source_img = img
                self._canvas_message = None
                self.render_canvas()
            
            file_date = self.get_cached_date(file_path)
            if self.current_file_is_video and thumb_path:
                self.record_thumbnail(file_path, thumb_path)
            self.update_caption(file_path, file_date, file_path.stat().st_size)
            self.update_stats()
            
        except Exception as e:
            error_msg = f"Could not load file: {file_path.name}\n\nError: {str(e)}\n\nSkip to next file?"
            if file_path.suffix.lower() in ['.heic', '.heif']:
                error_msg = f"HEIC Error: {str(e)}\nTry: pip install pillow-heif\n\nSkip?"
            
            if messagebox.askyesno("Error Loading File", error_msg):
                if self.current_index < len(self.images) - 1:
                    self.current_index += 1
                    self.show_current_image()
                else:
                    self.current_index = len(self.images)
                    self.show_current_image()


    def show_review_complete(self):
        self.current_index = len(self.images)
        self.current_file_is_video = False
        self.set_review_enabled(False)
        self.clear_caption()
        self.update_stats()
        freed = self.space_saved_mb
        freed_text = f'{freed / 1024:,.2f} GB' if freed >= 1024 else f'{freed:,.1f} MB'
        self.set_canvas_message('Folder reviewed',
                                f'{self.processed_count:,} reviewed  ·  {self.deleted_count:,} deleted  ·  '
                                f'{freed_text} freed', action=True, glyph='check')

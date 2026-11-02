"""Media operations for the desktop application."""

from tkinter import messagebox
from PIL import Image
from .processes import run_background
from datetime import datetime
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


    def generate_video_thumbnail(self, video_path):
        if not self.ffmpeg_available:
            return None
        
        thumb_name = f"{hash(str(video_path))}.jpg"
        thumb_path = self.thumbnails_dir / thumb_name
        
        if thumb_path.exists():
            return thumb_path

        # Publish only complete previews, including when a scan is interrupted.
        work_path = thumb_path.with_name(f'.{thumb_path.stem}.{uuid4().hex}.jpg')
        try:
            run_background(
                ['ffmpeg', '-i', str(video_path), '-ss', '00:00:01', 
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

            if self.current_file_is_video:
                thumb_path = self.generate_video_thumbnail(file_path)
                img = open_detached(thumb_path) if thumb_path and thumb_path.exists() else None
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
                self.set_canvas_message('Preview unavailable',
                                        'Click to open this video in your default player.')
            else:
                self._source_img = img
                self._canvas_message = None
                self.render_canvas()
            
            file_date = self.get_cached_date(file_path)
            if self.current_file_is_video and thumb_path and thumb_path.exists():
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

"""Media operations for the desktop application."""

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import subprocess
from datetime import datetime

# Register HEIC decoding when the optional package is installed.
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception as exc:
    print(f'WARNING: HEIC support not available: {exc}')

class MediaMixin:
    def check_ffmpeg(self):
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
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
        
        try:
            subprocess.run(
                ['ffmpeg', '-i', str(video_path), '-ss', '00:00:01', 
                 '-vframes', '1', '-q:v', '2', str(thumb_path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True
            )
            
            if thumb_path.exists():
                return thumb_path
        except:
            pass
        
        return None


    def is_video_file(self, file_path):
        return file_path.suffix.lower() in self.video_extensions


    def create_play_overlay(self, img):
        draw = ImageDraw.Draw(img, 'RGBA')
        width, height = img.size
        
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 120))
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        
        center_x, center_y = width // 2, height // 2
        triangle_size = min(width, height) // 6
        
        draw = ImageDraw.Draw(img)
        points = [(center_x - triangle_size//2, center_y - triangle_size),
                 (center_x - triangle_size//2, center_y + triangle_size),
                 (center_x + triangle_size, center_y)]
        draw.polygon(points, fill=(255, 255, 255, 220))
        
        text = "Click to play"
        text_x = center_x - len(text) * 4
        text_y = center_y + triangle_size + 30
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 250))
        
        return img.convert('RGB')


    def show_current_image(self):
        if not self.images or self.current_index >= len(self.images):
            messagebox.showinfo("Done!", "All files have been reviewed!")
            self.delete_btn.config(state=tk.DISABLED, bg='#4a4a4a')
            self.undo_btn.config(state=tk.DISABLED, bg='#4a4a4a')
            self.counter_label.config(text="All done!")
            self.stats_label.config(text="Review complete")
            self.canvas.delete("all")
            self.path_label.config(text="")
            self.filename_label.config(text="")
            self.date_label.config(text="")
            self.media_type_label.config(text="")
            self.filesize_label.config(text="")
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
            
            if self.current_file_is_video:
                thumb_path = self.generate_video_thumbnail(file_path)
                if thumb_path and thumb_path.exists():
                    img = Image.open(thumb_path)
                    img = self.create_play_overlay(img)
                else:
                    img = Image.new('RGB', (800, 600), color=self.bg_secondary)
                    draw = ImageDraw.Draw(img)
                    text = "Video Preview Unavailable\nClick to play"
                    draw.text((400, 300), text, fill='white', anchor='mm')
                
                self.media_type_label.config(text="🎬 VIDEO")
            else:
                # Handle different image formats
                if file_path.suffix.lower() == '.cr3':
                    try:
                        import rawpy
                        raw = rawpy.imread(str(file_path))
                        img = Image.fromarray(raw.postprocess())
                    except ImportError:
                        raise Exception("CR3 support requires 'rawpy'. Install with: pip install rawpy")
                    except Exception as cr3_error:
                        try:
                            img = Image.open(file_path)
                        except:
                            raise cr3_error
                elif file_path.suffix.lower() in ['.heic', '.heif']:
                    try:
                        import pillow_heif
                        heif_file = pillow_heif.read_heif(str(file_path))
                        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
                    except Exception as heic_error:
                        try:
                            img = Image.open(file_path)
                        except:
                            raise heic_error
                elif file_path.suffix.lower() in ['.raw', '.cr2', '.nef', '.arw', '.dng', '.orf']:
                    try:
                        import rawpy
                        raw = rawpy.imread(str(file_path))
                        img = Image.fromarray(raw.postprocess())
                    except ImportError:
                        raise Exception("RAW file support requires 'rawpy'. Install with: pip install rawpy")
                    except Exception as raw_error:
                        try:
                            img = Image.open(file_path)
                        except:
                            raise raw_error
                else:
                    img = Image.open(file_path)
                
                self.media_type_label.config(text="📷 PHOTO")
            
            self.root.update()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            img_width, img_height = img.size
            scale = min(canvas_width / img_width, canvas_height / img_height, 1)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(img)
            
            self.canvas.delete("all")
            x = canvas_width // 2
            y = canvas_height // 2
            self.canvas.create_image(x, y, image=self.photo, anchor=tk.CENTER)
            
            # Overlay navigation arrows — left and right thirds of the canvas.
            # Semi-transparent rounded backing drawn first, arrow glyph on top.
            arrow_y = canvas_height // 2
            arrow_size = 28
            pad = 10
            
            # Left arrow
            self.canvas.create_oval(
                pad, arrow_y - arrow_size,
                pad + arrow_size * 2, arrow_y + arrow_size,
                fill='#1a1a1a', outline='', stipple='gray50', tags='nav_arrow'
            )
            self.canvas.create_text(
                pad + arrow_size, arrow_y,
                text='‹', font=('Arial', 36, 'bold'),
                fill='#ffffff', tags='nav_arrow'
            )
            
            # Right arrow
            self.canvas.create_oval(
                canvas_width - pad - arrow_size * 2, arrow_y - arrow_size,
                canvas_width - pad, arrow_y + arrow_size,
                fill='#1a1a1a', outline='', stipple='gray50', tags='nav_arrow'
            )
            self.canvas.create_text(
                canvas_width - pad - arrow_size, arrow_y,
                text='›', font=('Arial', 36, 'bold'),
                fill='#ffffff', tags='nav_arrow'
            )
            
            self.counter_label.config(text=f"File {self.current_index + 1} of {len(self.images)}")
            
            file_date = self.get_cached_date(file_path)
            if file_date:
                years_ago = datetime.now().year - file_date.year
                date_text = file_date.strftime('%B %d, %Y')
                if years_ago > 0:
                    date_text += f" • {years_ago} year{'s' if years_ago != 1 else ''} ago"
                self.date_label.config(text=f"📅 {date_text}")
            else:
                self.date_label.config(text="")
            
            self.path_label.config(text=str(file_path.parent))
            self.filename_label.config(text=file_path.name)
            
            file_size = file_path.stat().st_size
            self.filesize_label.config(text=f"• {self.format_file_size(file_size)}")
            
            self.stats_label.config(text=f"Processed: {self.processed_count} • Deleted: {self.deleted_count} • Saved: {self.space_saved_mb:.1f} MB")
            
        except Exception as e:
            error_msg = f"Could not load file: {file_path.name}\n\nError: {str(e)}\n\nSkip to next file?"
            if file_path.suffix.lower() in ['.heic', '.heif']:
                error_msg = f"HEIC Error: {str(e)}\nTry: pip install pillow-heif\n\nSkip?"
            
            if messagebox.askyesno("Error Loading File", error_msg):
                if self.current_index < len(self.images) - 1:
                    self.current_index += 1
                    self.show_current_image()
                else:
                    messagebox.showinfo("Done!", "No more files to display.")



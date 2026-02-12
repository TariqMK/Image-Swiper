"""
Image & Video Organizer - "On This Day" Feature

REQUIRED PACKAGES:
Install all dependencies with pip before running this script:

    pip install pillow piexif pillow-heif winshell tkcalendar

Package details:
- pillow: Image processing and display
- piexif: EXIF metadata extraction from photos
- pillow-heif: HEIC/HEIF image format support (iPhone photos)
- winshell: Windows recycle bin operations (delete/undo)
- tkcalendar: Calendar widget for date picker

OPTIONAL (for video support):
- ffmpeg: Must be installed and added to system PATH for video thumbnails
  Download from: https://ffmpeg.org/download.html
  Or install via chocolatey: choco install ffmpeg

FEATURES:
- Browse photos/videos one-by-one with keep/delete options
- "On This Day" - view photos from this date in previous years
- Date picker - view photos from a specific date
- Video support with click-to-play in VLC
- SQLite caching for fast scanning
- Thumbnail cleanup for videos
- Undo last deletion
- Stats tracking (files processed, deleted, space saved)
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import os
from pathlib import Path
import winshell
import random
from datetime import datetime
import piexif
import sqlite3
import subprocess
import sys

# Register HEIC support
heic_support = False
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    heic_support = True
    print("HEIC support enabled")
except Exception as e:
    print(f"WARNING: HEIC support not available: {e}")

class ImageOrganizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Memory Organizer")
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
        script_dir = Path(__file__).parent
        self.db_path = script_dir / "OnThisDay_cache.db"
        self.thumbnails_dir = script_dir / "OnThisDay_thumbnails"
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
            '.svg', '.raw', '.cr2', '.nef', '.arw', '.dng', '.orf'
        }
        
        self.video_extensions = {
            '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v',
            '.mpg', '.mpeg', '.3gp', '.m2ts', '.mts', '.ts', '.vob', '.ogv'
        }
        
        self.setup_ui()
        self.bind_keys()
    
    def check_ffmpeg(self):
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except:
            return False
    
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
    
    def get_video_date(self, video_path):
        if not self.ffmpeg_available:
            return datetime.fromtimestamp(video_path.stat().st_mtime)
        
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                 '-show_entries', 'format_tags=creation_time', str(video_path)],
                capture_output=True, text=True, timeout=5
            )
            
            import json
            data = json.loads(result.stdout)
            
            if 'format' in data and 'tags' in data['format']:
                creation_time = data['format']['tags'].get('creation_time')
                if creation_time:
                    dt = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                    return dt.replace(tzinfo=None)
        except:
            pass
        
        return datetime.fromtimestamp(video_path.stat().st_mtime)
    
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
    
    def get_cached_date(self, file_path):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT date_taken, last_modified FROM image_cache WHERE filepath = ?', (str(file_path),))
        result = cursor.fetchone()
        
        current_mtime = file_path.stat().st_mtime
        
        if result and result[1] == current_mtime:
            conn.close()
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
        
        file_size = file_path.stat().st_size
        
        cursor.execute('''
            INSERT OR REPLACE INTO image_cache (filepath, date_taken, file_size, last_modified, is_video, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(file_path), file_date.isoformat() if file_date else None, file_size, current_mtime,
              1 if is_video else 0, str(thumbnail_path) if thumbnail_path else None))
        
        conn.commit()
        conn.close()
        
        return file_date
    
    def extract_image_date(self, img_path):
        try:
            exif_data = piexif.load(str(img_path))
            if piexif.ExifIFD.DateTimeOriginal in exif_data['Exif']:
                date_str = exif_data['Exif'][piexif.ExifIFD.DateTimeOriginal].decode()
                return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except:
            pass
        
        try:
            return datetime.fromtimestamp(img_path.stat().st_mtime)
        except:
            return None
    
    def matches_this_day(self, file_date, reference_date=None):
        if file_date is None:
            return False
        if reference_date is None:
            reference_date = self.viewing_date  # Use the currently selected viewing date
        return file_date.month == reference_date.month and file_date.day == reference_date.day
    
    def matches_specific_date(self, file_date, target_date):
        if file_date is None or target_date is None:
            return False
        if file_date.tzinfo is not None:
            file_date = file_date.replace(tzinfo=None)
        file_date_only = datetime(file_date.year, file_date.month, file_date.day)
        target_date_only = datetime(target_date.year, target_date.month, target_date.day)
        return file_date_only == target_date_only
    
    def format_file_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def is_video_file(self, file_path):
        return file_path.suffix.lower() in self.video_extensions
    
    def create_modern_button(self, parent, text, command, bg_color, width=140, height=50):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg=self.text_primary,
            font=('Segoe UI', 11, 'bold'),
            bd=0,
            activebackground=bg_color,
            activeforeground=self.text_primary,
            cursor='hand2',
            relief=tk.FLAT,
            width=width//8,
            height=height//25
        )
        
        # Hover effect
        def on_enter(e):
            btn['bg'] = self.lighten_color(bg_color)
        def on_leave(e):
            btn['bg'] = bg_color
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def lighten_color(self, hex_color):
        # Simple color lightening
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, r + 20)
        g = min(255, g + 20)
        b = min(255, b + 20)
        return f'#{r:02x}{g:02x}{b:02x}'
        
    def setup_ui(self):
        # Header bar
        header = tk.Frame(self.root, bg=self.bg_secondary, height=70)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        
        # Title
        title_frame = tk.Frame(header, bg=self.bg_secondary)
        title_frame.pack(side=tk.LEFT, padx=25, pady=15)
        
        tk.Label(
            title_frame,
            text="📸 Memory Organizer",
            bg=self.bg_secondary,
            fg=self.text_primary,
            font=('Segoe UI', 18, 'bold')
        ).pack(side=tk.LEFT)
        
        # Action buttons in header
        btn_frame = tk.Frame(header, bg=self.bg_secondary)
        btn_frame.pack(side=tk.RIGHT, padx=20)
        
        self.create_modern_button(btn_frame, "📁 Select Folder", self.select_folder, 
                                 self.accent_primary, 130, 40).pack(side=tk.LEFT, padx=5)
        self.create_modern_button(btn_frame, "🧹 Clean", self.clean_thumbnails, 
                                 self.accent_warning, 100, 40).pack(side=tk.LEFT, padx=5)
        
        # Control panel
        control_panel = tk.Frame(self.root, bg=self.bg_card, height=80)
        control_panel.pack(fill=tk.X, padx=15, pady=(10, 0))
        control_panel.pack_propagate(False)
        
        # Left side - filters
        filter_frame = tk.Frame(control_panel, bg=self.bg_card)
        filter_frame.pack(side=tk.LEFT, padx=20, pady=15)
        
        self.random_var = tk.BooleanVar(value=False)
        self.create_checkbox(filter_frame, "🎲 Random", self.random_var, 
                           self.toggle_random_mode).pack(side=tk.LEFT, padx=8)
        
        self.subdirs_var = tk.BooleanVar(value=True)
        self.create_checkbox(filter_frame, "📂 Subdirectories", self.subdirs_var, 
                           self.toggle_subdirs).pack(side=tk.LEFT, padx=8)
        
        self.this_day_var = tk.BooleanVar(value=False)
        self.create_checkbox(filter_frame, "📅 On This Day", self.this_day_var, 
                           self.toggle_this_day, self.accent_primary).pack(side=tk.LEFT, padx=8)
        
        # Date navigation arrows (initially hidden)
        self.date_nav_frame = tk.Frame(filter_frame, bg=self.bg_card)
        self.date_nav_frame.pack(side=tk.LEFT, padx=5)
        
        self.prev_day_btn = tk.Button(
            self.date_nav_frame,
            text="←",
            command=self.previous_day,
            bg=self.bg_secondary,
            fg=self.text_primary,
            font=('Segoe UI', 11, 'bold'),
            bd=0,
            cursor='hand2',
            width=3,
            height=1
        )
        self.prev_day_btn.pack(side=tk.LEFT, padx=2)
        
        self.next_day_btn = tk.Button(
            self.date_nav_frame,
            text="→",
            command=self.next_day,
            bg=self.bg_secondary,
            fg=self.text_primary,
            font=('Segoe UI', 11, 'bold'),
            bd=0,
            cursor='hand2',
            width=3,
            height=1
        )
        self.next_day_btn.pack(side=tk.LEFT, padx=2)
        
        self.date_nav_frame.pack_forget()  # Hide initially
        
        # Right side - counter and stats
        stats_frame = tk.Frame(control_panel, bg=self.bg_card)
        stats_frame.pack(side=tk.RIGHT, padx=20, pady=15)
        
        self.counter_label = tk.Label(
            stats_frame,
            text="No files loaded",
            bg=self.bg_card,
            fg=self.text_primary,
            font=('Segoe UI', 11, 'bold')
        )
        self.counter_label.pack(side=tk.TOP)
        
        self.stats_label = tk.Label(
            stats_frame,
            text="Ready to organize",
            bg=self.bg_card,
            fg=self.text_secondary,
            font=('Segoe UI', 9)
        )
        self.stats_label.pack(side=tk.TOP, pady=(3, 0))
        
        # Viewing date label (shown when On This Day is active)
        self.viewing_date_label = tk.Label(
            control_panel,
            text="",
            bg=self.bg_card,
            fg=self.text_muted,
            font=('Segoe UI', 8, 'italic')
        )
        self.viewing_date_label.pack(side=tk.LEFT, padx=25)
        self.viewing_date_label.pack_forget()  # Hide initially
        
        # Main content area
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Image viewer card
        viewer_card = tk.Frame(content, bg=self.bg_card, bd=0, highlightthickness=1, 
                              highlightbackground=self.bg_secondary)
        viewer_card.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for image
        self.canvas = tk.Canvas(
            viewer_card,
            bg=self.bg_secondary,
            highlightthickness=0,
            cursor='hand2'
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        
        # Info panel
        info_panel = tk.Frame(self.root, bg=self.bg_card, height=120)
        info_panel.pack(fill=tk.X, padx=15, pady=(0, 10))
        info_panel.pack_propagate(False)
        
        # Center container for all info
        center_container = tk.Frame(info_panel, bg=self.bg_card)
        center_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Date and type
        top_info = tk.Frame(center_container, bg=self.bg_card)
        top_info.pack(pady=(0, 5))
        
        self.date_label = tk.Label(
            top_info,
            text="",
            bg=self.bg_card,
            fg=self.accent_primary,
            font=('Segoe UI', 12, 'bold')
        )
        self.date_label.pack(side=tk.LEFT, padx=10)
        
        self.media_type_label = tk.Label(
            top_info,
            text="",
            bg=self.bg_card,
            fg=self.accent_info,
            font=('Segoe UI', 9)
        )
        self.media_type_label.pack(side=tk.LEFT, padx=10)
        
        # File info
        file_info = tk.Frame(center_container, bg=self.bg_card)
        file_info.pack(pady=(0, 5))
        
        self.filename_label = tk.Label(
            file_info,
            text="",
            bg=self.bg_card,
            fg=self.text_primary,
            font=('Segoe UI', 10)
        )
        self.filename_label.pack(side=tk.LEFT, padx=10)
        
        self.filesize_label = tk.Label(
            file_info,
            text="",
            bg=self.bg_card,
            fg=self.text_secondary,
            font=('Segoe UI', 9)
        )
        self.filesize_label.pack(side=tk.LEFT, padx=10)
        
        # Path - make it clickable (centered)
        path_container = tk.Frame(center_container, bg=self.bg_card)
        path_container.pack()
        
        self.path_label = tk.Label(
            path_container,
            text="",
            bg=self.bg_card,
            fg=self.accent_info,
            font=('Segoe UI', 8, 'underline'),
            cursor='hand2'
        )
        self.path_label.pack()
        self.path_label.bind('<Button-1>', self.open_folder)
        
        # Action buttons footer
        footer = tk.Frame(self.root, bg=self.bg_primary, height=100)
        footer.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=(0, 15))
        footer.pack_propagate(False)
        
        button_container = tk.Frame(footer, bg=self.bg_primary)
        button_container.pack(expand=True)
        
        # Delete button - larger, more prominent
        delete_frame = tk.Frame(button_container, bg=self.accent_danger, bd=0, 
                               relief=tk.FLAT, highlightthickness=2, 
                               highlightbackground='#7f1d1d')
        delete_frame.pack(side=tk.LEFT, padx=15)
        
        self.delete_btn = tk.Button(
            delete_frame,
            text="✕  DELETE",
            command=self.delete_image,
            bg=self.accent_danger,
            fg=self.text_primary,
            font=('Segoe UI', 13, 'bold'),
            bd=0,
            activebackground='#dc2626',
            activeforeground=self.text_primary,
            cursor='hand2',
            relief=tk.FLAT,
            padx=35,
            pady=18,
            state=tk.DISABLED
        )
        self.delete_btn.pack(padx=3, pady=3)
        
        # Undo button - medium prominence
        undo_frame = tk.Frame(button_container, bg=self.accent_warning, bd=0,
                             relief=tk.FLAT, highlightthickness=2,
                             highlightbackground='#78350f')
        undo_frame.pack(side=tk.LEFT, padx=15)
        
        self.undo_btn = tk.Button(
            undo_frame,
            text="↶  UNDO",
            command=self.undo_delete,
            bg=self.accent_warning,
            fg=self.text_primary,
            font=('Segoe UI', 13, 'bold'),
            bd=0,
            activebackground='#f59e0b',
            activeforeground=self.text_primary,
            cursor='hand2',
            relief=tk.FLAT,
            padx=35,
            pady=18,
            state=tk.DISABLED
        )
        self.undo_btn.pack(padx=3, pady=3)
        
        # Add hover effects
        def delete_enter(e):
            if self.delete_btn['state'] != tk.DISABLED:
                delete_frame.config(highlightbackground='#991b1b')
                self.delete_btn.config(bg='#dc2626')
        def delete_leave(e):
            delete_frame.config(highlightbackground='#7f1d1d')
            self.delete_btn.config(bg=self.accent_danger)
        
        def undo_enter(e):
            if self.undo_btn['state'] != tk.DISABLED:
                undo_frame.config(highlightbackground='#92400e')
                self.undo_btn.config(bg='#d97706')
        def undo_leave(e):
            undo_frame.config(highlightbackground='#78350f')
            self.undo_btn.config(bg=self.accent_warning)
        
        delete_frame.bind("<Enter>", delete_enter)
        delete_frame.bind("<Leave>", delete_leave)
        self.delete_btn.bind("<Enter>", delete_enter)
        self.delete_btn.bind("<Leave>", delete_leave)
        
        undo_frame.bind("<Enter>", undo_enter)
        undo_frame.bind("<Leave>", undo_leave)
        self.undo_btn.bind("<Enter>", undo_enter)
        self.undo_btn.bind("<Leave>", undo_leave)
        
        # Keyboard hints
        hints = tk.Label(
            footer,
            text="← Previous  |  → Next  |  Q Delete  |  ⌫ Undo  |  Click video to play  |  Click path to open folder",
            bg=self.bg_primary,
            fg=self.text_muted,
            font=('Segoe UI', 8)
        )
        hints.pack(side=tk.BOTTOM, pady=(10, 0))
    
    def create_checkbox(self, parent, text, variable, command, accent=None):
        if accent is None:
            accent = self.text_secondary
        
        cb = tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            command=command,
            bg=self.bg_card,
            fg=self.text_primary,
            selectcolor=self.bg_secondary,
            activebackground=self.bg_card,
            activeforeground=self.text_primary,
            font=('Segoe UI', 9),
            cursor='hand2',
            bd=0,
            highlightthickness=0
        )
        return cb
        
    def bind_keys(self):
        self.root.bind('<Left>', lambda e: self.previous_image())
        self.root.bind('<Right>', lambda e: self.next_image())
        self.root.bind('q', lambda e: self.delete_image())
        self.root.bind('Q', lambda e: self.delete_image())
        self.root.bind('w', lambda e: self.keep_image())
        self.root.bind('W', lambda e: self.keep_image())
        self.root.bind('<BackSpace>', lambda e: self.undo_delete())
    
    def on_canvas_click(self, event):
        if self.current_file_is_video and self.images and self.current_index < len(self.images):
            file_path = self.images[self.current_index]
            try:
                if sys.platform == 'win32':
                    os.startfile(str(file_path))
                elif sys.platform == 'darwin':
                    subprocess.run(['open', str(file_path)])
                else:
                    subprocess.run(['xdg-open', str(file_path)])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open video: {str(e)}")
    
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
    
    def open_folder(self, event=None):
        """Open the folder containing the current file in file explorer"""
        if self.images and self.current_index < len(self.images):
            folder_path = self.images[self.current_index].parent
            try:
                if sys.platform == 'win32':
                    os.startfile(str(folder_path))
                elif sys.platform == 'darwin':
                    subprocess.run(['open', str(folder_path)])
                else:
                    subprocess.run(['xdg-open', str(folder_path)])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {str(e)}")
            
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
        
        self.images = sorted(list(set(self.images)))
        
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
            
            filtered_files.sort(key=lambda x: x[1] if x[1] else datetime.min)
            self.images = [file for file, date in filtered_files]
            
            if not self.images:
                date_str = self.viewing_date.strftime('%B %d')
                messagebox.showinfo("No Memories", f"No photos or videos found from {date_str} in previous years.")
                self.counter_label.config(text="No files loaded")
                return
        
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
                if file_path.suffix.lower() in ['.heic', '.heif']:
                    try:
                        import pillow_heif
                        heif_file = pillow_heif.read_heif(str(file_path))
                        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
                    except Exception as heic_error:
                        try:
                            img = Image.open(file_path)
                        except:
                            raise heic_error
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
            
    def delete_image(self):
        if not self.images or self.current_index >= len(self.images):
            return
            
        file_path = self.images[self.current_index]
        
        try:
            file_size_bytes = file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            winshell.delete_file(str(file_path), no_confirm=True, allow_undo=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM image_cache WHERE filepath = ?', (str(file_path),))
            conn.commit()
            conn.close()
            
            self.last_deleted = file_path
            self.last_deleted_size = file_size_mb
            self.undo_btn.config(state=tk.NORMAL, bg=self.accent_warning)
            self.deleted_count += 1
            self.processed_count += 1
            self.space_saved_mb += file_size_mb
            self.current_index += 1
            self.show_current_image()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete file: {str(e)}")
    
    def undo_delete(self):
        if not self.last_deleted:
            return
        
        try:
            winshell.undelete(str(self.last_deleted))
            
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

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageOrganizer(root)
    root.mainloop()

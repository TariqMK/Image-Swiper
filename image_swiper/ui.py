"""Ui operations for the desktop application."""

import tkinter as tk
from tkinter import messagebox
import os
import subprocess
import sys
from .version import __version__

class UiMixin:
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
        
        tk.Label(
            title_frame,
            text=f"v{__version__}",
            bg=self.bg_secondary,
            fg=self.text_muted,
            font=('Segoe UI', 10)
        ).pack(side=tk.LEFT, padx=(12, 0))

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
        
        self.sort_by_date_var = tk.BooleanVar(value=False)
        self.create_checkbox(filter_frame, "📅 Sort by Date", self.sort_by_date_var,
                           self.toggle_sort_by_date).pack(side=tk.LEFT, padx=8)
        
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
        if not self.images:
            return
        
        canvas_width = self.canvas.winfo_width()
        zone = canvas_width // 5  # left and right 20% are navigation zones
        
        if event.x < zone:
            self.previous_image()
            return
        if event.x > canvas_width - zone:
            self.next_image()
            return
        
        # Centre click — open video as before
        if self.current_file_is_video and self.current_index < len(self.images):
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



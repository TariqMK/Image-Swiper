"""Metadata operations for the desktop application."""

from datetime import datetime
import subprocess
import piexif

class MetadataMixin:
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



# Image Swiper

Review your photos and videos one at a time, revisit memories from the same day
across the years, and clear out the files you no longer want.

![Image Swiper interface](docs/screenshots/Screenshot%2001.png)

## Download and open

Download a build from [Releases](https://github.com/TariqMK/Image-Swiper/releases)
for your computer:

| Platform | Download | Open after extracting |
| --- | --- | --- |
| Windows (64-bit) | `windows-x64.zip` | `ImageSwiper/ImageSwiper.exe` |
| macOS (Apple Silicon) | `macos-arm64.zip` | `ImageSwiper.app` |
| Linux (64-bit) | `linux-x64.tar.gz` | `ImageSwiper/ImageSwiper` |

Keep the extracted application and its accompanying files together. Release builds
include Python, so you do not need to install Python separately. Intel Macs are
not supported. Linux requires a graphical desktop; builds target Ubuntu 22.04 or
newer compatible systems. Downloads are unsigned, and macOS builds are not
notarized, so your system may show an application security prompt.

For video thumbnails and original video dates, install
[FFmpeg](https://ffmpeg.org/download.html) with `ffprobe` and make both available
on your system's `PATH`. Without them, you can still open videos in your default
player, but previews may be unavailable and dates use file modification times.

## Start reviewing

1. Choose whether to include **Subdirectories**, then click **Select Folder**.
2. Browse in filename order, select **Sort by Date**, or enable **Random**.
3. Keep the photos and videos you want; delete unwanted ones with **DELETE** or `Q`.
4. Enable **On This Day** to see memories from the same month and day across all
   years. Use the date arrows to explore another day.

The current year is included in On This Day. Scanning runs in the background,
with progress shown in the window. On Windows, background video tools run without
flashing terminal windows. You can close the app during a scan to cancel it.

The application name is **Image Swiper**, with its build version shown beside the
title in muted text and in the window title.

## Controls

| Control | Action |
| --- | --- |
| `Q` or DELETE | Send the current file to the Recycle Bin or Trash |
| `W` or Right arrow | Keep and move forward |
| Left arrow | Go back to the previous available file |
| Left/right edge of the preview | Browse backward/forward |
| Backspace or UNDO | Windows: restore the most recent deletion, when available |
| Centre of a video preview | Open it in your default player |
| Folder path | Open the containing folder |
| Clean | Remove unused video previews after confirmation |

Keeping a file leaves it where it is. Image Swiper does not move it or add tags.

## Deleted files and undo

On **Windows**, deleted files go to the Recycle Bin. Image Swiper supports undoing
the most recent deletion while UNDO is available. The completion screen disables
that button; you can still restore files through the Recycle Bin.

On **macOS and Linux**, files go to the system Trash. Restore them through your
file manager; in-app undo is unavailable on these platforms.

The space-saved figure shows the size of files sent to the Recycle Bin or Trash.
Disk space may not be reclaimed until you empty it. Review statistics count actions,
so revisiting a file may count it more than once.

## Photo and video support

Image Swiper previews common image formats, including JPEG, PNG, GIF, BMP, WebP
and TIFF, plus HEIC/HEIF and camera RAW formats such as CR2, CR3, NEF, ARW and DNG.
Some files may depend on their camera or encoding. Large RAW previews can take
longer to open.

Video formats include MP4, MOV, AVI, MKV and others. Playback opens in your default
player rather than inside Image Swiper.

Photo dates come from the original capture metadata when available. Video dates
come from creation metadata when readable. Otherwise, file modification dates are
used, which can affect which memories appear in On This Day.

## Your data

Image Swiper stores a local metadata cache and generated video previews to speed
up repeat scans. Packaged apps keep these in your user account's application-data
folder. Your original photos and videos stay in the folder you selected until you
choose to delete them. Saved scan progress is kept if you close the app; a small
unfinished batch may need to be scanned again next time.

## Troubleshooting

- **No video preview:** check that FFmpeg and ffprobe are installed and available
  on `PATH`. Videos can still be opened in your default player.
- **Unexpected On This Day results:** check the file's capture date. Files without
  readable capture metadata use their modification date.
- **Slow first scan:** new files need their dates read. Video previews are generated
  only when you view a video, so unrelated videos do not slow down the date scan
  with thumbnail generation. Repeat scans reuse cached dates. You can close the
  window during a scan.
- **Large RAW image takes time to appear:** preview decoding can briefly delay
  interaction while the image opens.

Reviews do not resume automatically after restarting. Rotation, favourites,
duplicate detection and batch deletion are not currently available.

## For contributors

See [development and maintenance](docs/development.md) for running from source,
private-file handling and tests, [architecture](docs/architecture.md) for the code
layout, and [release instructions](docs/releases.md) for manual GitHub builds.

## License

Free to use and modify. No warranty provided.

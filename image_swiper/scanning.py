"""Cancellable library scanning without Tk calls."""
from datetime import datetime
import os
from pathlib import Path
import random


def scan_library(folder, *, cancel, extensions, include_subdirs, get_date,
                 sort_key, sort_by_date, on_this_day, reference_date,
                 random_mode, progress):
    images = []
    # One filesystem traversal rather than two walks per supported extension.
    for directory, subdirs, filenames in os.walk(folder):
        if cancel.is_set():
            return []
        if not include_subdirs:
            subdirs.clear()
        for name in filenames:
            if cancel.is_set():
                return []
            path = Path(directory) / name
            if path.suffix.lower() in extensions:
                images.append(path)
        progress(f"Finding files... {len(images)} found")
    if cancel.is_set():
        return []
    images.sort(key=sort_key)
    if sort_by_date or on_this_day:
        dated = []
        for i, path in enumerate(images):
            if cancel.is_set():
                return []
            if i % 10 == 0:
                progress(f"Scanning {i}/{len(images)}...")
            date = get_date(path)
            if cancel.is_set():
                return []
            if date is not None:
                date = date.replace(tzinfo=None)
            if on_this_day and (date is None or (date.month, date.day) != (reference_date.month, reference_date.day)):
                continue
            dated.append((path, date or datetime.min))
        dated.sort(key=lambda item: (item[1], sort_key(item[0])))
        images = [path for path, _ in dated]
    if random_mode and not on_this_day:
        random.shuffle(images)
    return images

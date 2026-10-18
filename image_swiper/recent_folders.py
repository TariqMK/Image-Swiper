"""Private, persistent history of the three most recently opened folders."""
import json
import os
from pathlib import Path
import tempfile


class RecentFolders:
    def __init__(self, path):
        self.path = Path(path)
        self.folders = []
        try:
            values = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(values, list):
                seen = set()
                for value in values:
                    if not isinstance(value, str) or not value.strip() or '\0' in value:
                        continue
                    normalized = os.path.abspath(os.path.expanduser(value))
                    key = os.path.normcase(normalized)
                    if key not in seen:
                        self.folders.append(normalized)
                        seen.add(key)
                    if len(self.folders) == 3:
                        break
        except (OSError, ValueError):
            pass

    def remember(self, folder):
        normalized = os.path.abspath(os.path.expanduser(str(folder)))
        key = os.path.normcase(normalized)
        self.folders = [normalized] + [value for value in self.folders if os.path.normcase(value) != key]
        self.folders = self.folders[:3]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='recent-folders-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(self.folders, stream, indent=2, ensure_ascii=False)
                stream.write('\n')
            temporary.replace(self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

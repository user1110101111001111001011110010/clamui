"""Path navigation and Tab completion, without shell evaluation."""
import os
from pathlib import Path


def complete_path(value: str) -> tuple[str, list[str]]:
    expanded = os.path.expanduser(value or "./")
    base, prefix = os.path.split(expanded)
    parent = Path(base or ".")
    candidates = []
    with os.scandir(parent) as entries:
        for entry in entries:
            if entry.name.startswith(prefix):
                candidate = str(parent / entry.name)
                if entry.is_dir(follow_symlinks=False):
                    candidate += "/"
                candidates.append(candidate)
    candidates.sort()
    if not candidates:
        return value, []
    common = os.path.commonprefix(candidates)
    return (candidates[0] if len(candidates) == 1 else common), candidates


class FileBrowser:
    def __init__(self):
        self.directory = Path.home()
        self.entries = []
        self.show_hidden = False

    def open(self, directory):
        directory = Path(directory).expanduser().absolute()
        entries = []
        with os.scandir(directory) as iterator:
            for entry in iterator:
                if not self.show_hidden and entry.name.startswith("."):
                    continue
                # A symlink is visible but deliberately not selectable.
                if entry.is_symlink():
                    kind = "link"
                elif entry.is_dir(follow_symlinks=False):
                    kind = "dir"
                elif entry.is_file(follow_symlinks=False):
                    kind = "file"
                else:
                    continue
                entries.append((entry.name, Path(entry.path), kind))
        self.directory = directory
        self.entries = sorted(entries, key=lambda item: (item[2] != "dir", item[0].casefold()))

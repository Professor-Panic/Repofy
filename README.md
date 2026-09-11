# Repofy

Repofy is a Python project for building a terminal user interface around repository workflows. The current implementation provides a Textual file-picker modal with directory navigation and a small set of safe filesystem commands.

## Current Status

Implemented:

- `FilePickerModal` for browsing files and directories inside a selected root
- Case-insensitive file filtering
- Directory navigation with parent-directory support
- `pwd`, `ls`, `cd`, `mkdir`, and `rmdir` commands
- Protection against navigating outside the picker root

The `Brancher.py`, `Merger.py`, `Sprinter.py`, `Stager.py`, and `Ui.py` modules are currently placeholders for future functionality. There is not yet a standalone application entry point.

## Requirements

- Python 3.10 or newer
- [Textual](https://textual.textualize.io/)

Install the dependency with:

```bash
python -m pip install textual
```

## Usage

`FilePickerModal` can be opened from a Textual application and returns the selected file path when a file is chosen:

```python
from pathlib import Path

from textual.app import App

from File_picker import FilePickerModal


class RepofyApp(App):
    def open_picker(self) -> None:
        self.push_screen(FilePickerModal(Path.cwd()), self.file_selected)

    def file_selected(self, path: Path | None) -> None:
        if path is not None:
            print(f"Selected: {path}")


if __name__ == "__main__":
    RepofyApp().run()
```

Inside the picker:

- Type in the filter field to narrow the visible entries.
- Select a directory to enter it.
- Select a file to close the picker and return its path.
- Use `Escape` to cancel.
- Enter commands in the command field:

```text
pwd
ls
cd <directory>
mkdir <directory>
rmdir <directory>
```

All file operations are restricted to the picker root, and `.git` is hidden from the file list.

## Project Layout

| File | Purpose |
| --- | --- |
| `File_picker.py` | Textual file-picker modal |
| `Brancher.py` | Reserved for branch workflow features |
| `Merger.py` | Reserved for merge workflow features |
| `Sprinter.py` | Reserved for sprint workflow features |
| `Stager.py` | Reserved for staging workflow features |
| `Ui.py` | Reserved for the application UI |

## Development

Compile-check the Python files with:

```bash
python -m compileall .
```

The project does not currently include automated tests or a packaging configuration.
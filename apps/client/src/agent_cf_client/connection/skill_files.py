"""Read directory names on this PC for the operator's Markdown file chooser."""

import os
from pathlib import Path


def list_skill_files(path: str | None) -> dict:
    try:
        directory = Path(path).expanduser() if path else Path.home()
        if not directory.is_absolute():
            raise ValueError("Cần đường dẫn thư mục tuyệt đối")
        directory = directory.resolve(strict=True)
        if directory.is_file():
            directory = directory.parent
        entries = []
        truncated = False
        with os.scandir(directory) as children:
            for child in children:
                if child.is_symlink():
                    continue
                is_dir = child.is_dir(follow_symlinks=False)
                if is_dir or (child.is_file(follow_symlinks=False) and Path(child.name).suffix.lower() == ".md"):
                    if len(entries) >= 500:
                        truncated = True
                        break
                    entries.append({"name": child.name, "path": str(directory / child.name), "is_dir": is_dir})
        entries.sort(key=lambda item: (not item["is_dir"], item["name"].lower()))
        roots = [f"{letter}:\\" for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{letter}:\\").is_dir()] if os.name == "nt" else ["/"]
        return {"path": str(directory), "parent": str(directory.parent), "roots": roots, "entries": entries, "truncated": truncated}
    except (OSError, ValueError) as exc:
        return {"error": f"Không mở được thư mục trên PC: {exc}"}

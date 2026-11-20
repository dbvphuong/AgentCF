"""Portable validation of paths owned by a selected PC, without reading its disk."""

from pathlib import PurePosixPath, PureWindowsPath


def validate_absolute_path(value: str) -> str:
    if not value or any(c in value for c in ("\0", "\r", "\n")):
        raise ValueError("Đường dẫn tuyệt đối không hợp lệ")
    if not (PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()):
        raise ValueError("Cần đường dẫn tuyệt đối trên PC thực thi")
    return value


def validate_skill_source(instructions: str, source_path: str | None, source_runner_id: str | None) -> None:
    if source_path:
        validate_absolute_path(source_path)
        if PureWindowsPath(source_path).suffix.lower() != ".md":
            raise ValueError("Đường dẫn Skill phải trỏ tới file .md chính")
        if not source_runner_id:
            raise ValueError("Skill local cần chọn PC sở hữu file")
    elif source_runner_id:
        raise ValueError("Chọn PC cho Skill cần kèm đường dẫn SKILL.md")
    elif not instructions.strip():
        raise ValueError("Cần hướng dẫn hoặc đường dẫn tuyệt đối tới SKILL.md")

"""Workspace isolation and path traversal defense (CLI-002)."""

import os
from pathlib import Path
import re


def _sanitize_id(identifier: str) -> str:
    """Sanitize identifier to prevent directory traversal or unsafe path chars."""
    if not identifier or ".." in identifier or "/" in identifier or "\\" in identifier or "\0" in identifier:
        raise ValueError(f"Unsafe path component: {identifier!r}")
    # Allow alphanumeric, dashes, underscores, dots (if not ..)
    if not re.match(r"^[a-zA-Z0-9_.-]+$", identifier):
        raise ValueError(f"Invalid path characters in identifier: {identifier!r}")
    return identifier


class WorkspaceManager:
    def __init__(self, base_dir: Path | str | None = None) -> None:
        if base_dir is None:
            base_dir = Path("runtime/client/workspaces").resolve()
        self.base_dir = Path(base_dir).resolve()

    def create_attempt_workspace(self, run_id: str, attempt_id: str) -> Path:
        safe_run_id = _sanitize_id(run_id)
        safe_attempt_id = _sanitize_id(attempt_id)

        workspace_path = (self.base_dir / safe_run_id / safe_attempt_id).resolve()
        # Verify strictly inside base_dir
        if not str(workspace_path).startswith(str(self.base_dir)):
            raise ValueError(f"Workspace path escape detected: {workspace_path}")

        workspace_path.mkdir(parents=True, exist_ok=True)
        (workspace_path / "artifacts").mkdir(exist_ok=True)
        (workspace_path / "logs").mkdir(exist_ok=True)
        (workspace_path / "input").mkdir(exist_ok=True)
        return workspace_path

    def resolve_safe_path(self, workspace_path: Path, relative_path: str) -> Path:
        """Resolve a path within workspace_path and verify no path traversal."""
        resolved_ws = workspace_path.resolve()
        target = (resolved_ws / relative_path).resolve()
        if not str(target).startswith(str(resolved_ws)):
            raise ValueError(f"Path traversal detected: {relative_path!r} escapes {workspace_path}")
        return target

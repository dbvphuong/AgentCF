"""Durable execution journaling before spawn (CLI-001, CLI-002)."""

from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import time
from typing import Any, Literal


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


JournalState = Literal["planned", "running", "completed", "failed", "cancelled"]


class ExecutionJournal:
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self.journal_file = workspace_path / "execution_journal.json"

    def record_planned(
        self,
        attempt_id: str,
        run_id: str,
        task_run_id: str,
        generation: int,
        launch_id: str,
        command_argv: list[str],
    ) -> dict[str, Any]:
        data = {
            "attempt_id": attempt_id,
            "run_id": run_id,
            "task_run_id": task_run_id,
            "generation": generation,
            "launch_id": launch_id,
            "command_argv": command_argv,
            "state": "planned",
            "planned_at": _now_iso(),
            "started_at": None,
            "ended_at": None,
            "exit_code": None,
            "error": None,
        }
        self._write_atomic(data)
        return data

    def record_started(self, pid: int) -> dict[str, Any]:
        data = self.read()
        data["state"] = "running"
        data["pid"] = pid
        data["started_at"] = _now_iso()
        self._write_atomic(data)
        return data

    def record_completed(self, exit_code: int) -> dict[str, Any]:
        data = self.read()
        data["state"] = "completed" if exit_code == 0 else "failed"
        data["exit_code"] = exit_code
        data["ended_at"] = _now_iso()
        self._write_atomic(data)
        return data

    def record_failed(self, error: str, exit_code: int | None = None) -> dict[str, Any]:
        data = self.read()
        data["state"] = "failed"
        data["exit_code"] = exit_code
        data["error"] = error
        data["ended_at"] = _now_iso()
        self._write_atomic(data)
        return data

    def record_cancelled(self, reason: str = "cancelled") -> dict[str, Any]:
        data = self.read()
        data["state"] = "cancelled"
        data["error"] = reason
        data["ended_at"] = _now_iso()
        self._write_atomic(data)
        return data

    def read(self) -> dict[str, Any]:
        if not self.journal_file.exists():
            raise FileNotFoundError(f"Journal not found at {self.journal_file}")
        return json.loads(self.journal_file.read_text(encoding="utf-8"))

    def exists(self) -> bool:
        return self.journal_file.exists()

    def _write_atomic(self, data: dict[str, Any]) -> None:
        temp_file = self.journal_file.with_name(f"{self.journal_file.stem}_{secrets.token_hex(4)}.tmp")
        temp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        # On Windows, os.replace can intermittently raise PermissionError if the target
        # was read/written immediately beforehand. Retry with small backoff.
        for attempt in range(5):
            try:
                temp_file.replace(self.journal_file)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05)

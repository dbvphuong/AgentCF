"""Codex CLI runtime adapter (RTM-005, RTM-009, RTM-011, RTM-012)."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any

from agent_cf_client.execution.process_manager import ProcessManager, ProcessResult
from agent_cf_client.runtime.base import BaseRuntimeAdapter, RuntimeExecutionResult

CODEX_REASONING_EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max"})


def _parse_version_key(folder_name: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", folder_name)
    return tuple(int(part) for part in parts) if parts else (0,)


def _find_ide_codex_executable() -> str | None:
    extensions_dir = Path.home() / ".vscode" / "extensions"
    if not extensions_dir.is_dir():
        return None
    candidates: list[tuple[tuple[int, ...], Path]] = []
    for entry in extensions_dir.iterdir():
        if not entry.is_dir() or not entry.name.startswith("openai.chatgpt-"):
            continue
        binary = entry / "bin" / "windows-x86_64" / "codex.exe"
        if binary.is_file():
            candidates.append((_parse_version_key(entry.name), binary))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return str(candidates[0][1])


class CodexAdapter(BaseRuntimeAdapter):
    """Adapter executing Codex CLI non-interactively via JSONL output and session resume."""

    def __init__(
        self,
        executable_path: str | None = None,
        process_manager: ProcessManager | None = None,
    ) -> None:
        self._configured_executable = executable_path
        self.pm = process_manager or ProcessManager()

    @property
    def adapter_id(self) -> str:
        return "codex"

    @property
    def _executable(self) -> str | None:
        if self._configured_executable:
            return self._configured_executable
        if sys.platform == "win32":
            native = shutil.which("codex.exe")
            if native:
                return native
            ide_binary = _find_ide_codex_executable()
            if ide_binary:
                return ide_binary
            wrapper = shutil.which("codex.cmd")
            if wrapper:
                return wrapper
            return shutil.which("codex")
        return shutil.which("codex")

    def is_available(self) -> bool:
        return bool(self._executable)

    def build_command(
        self,
        prompt: str,
        cwd: Path,
        model: str | None = None,
        session_id: str | None = None,
        output_file: Path | None = None,
        reasoning_effort: str | None = None,
        sandbox: str = "read-only",
        **kwargs: Any,
    ) -> list[str]:
        if reasoning_effort is not None and reasoning_effort not in CODEX_REASONING_EFFORTS:
            raise ValueError(
                f"Mức suy luận '{reasoning_effort}' không hợp lệ cho Codex CLI; "
                f"chỉ hỗ trợ: {', '.join(sorted(CODEX_REASONING_EFFORTS))}."
            )

        exe = self._executable or "codex"
        command: list[str] = [exe, "exec"]
        if session_id:
            command.append("resume")
        command.extend(["--json", "--skip-git-repo-check"])
        if not session_id:
            command.extend(["-C", str(cwd), "-s", sandbox])
        if model:
            command.extend(["-m", model])
        if reasoning_effort is not None:
            command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
        if output_file is not None:
            command.extend(["--output-last-message", str(output_file)])
        if session_id:
            command.append(session_id)
        command.append(prompt)
        return command

    def parse_output(
        self,
        result: ProcessResult,
        output_file: Path | None = None,
        session_id: str | None = None,
    ) -> RuntimeExecutionResult:
        if result.timed_out:
            return RuntimeExecutionResult(
                success=False,
                exit_code=result.exit_code if result.exit_code is not None else -1,
                session_id=session_id,
                error_code="timeout",
                error_message=f"Codex CLI timed out after {result.duration_seconds:.1f}s",
                duration_seconds=result.duration_seconds,
            )
        if result.cancelled:
            return RuntimeExecutionResult(
                success=False,
                exit_code=result.exit_code if result.exit_code is not None else -1,
                session_id=session_id,
                error_code="cancelled",
                error_message="Codex CLI execution was cancelled",
                duration_seconds=result.duration_seconds,
            )

        thread_id = session_id
        messages: list[str] = []
        turn_failed_msg: str | None = None
        turn_completed = False

        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            if event_type == "thread.started" and event.get("thread_id"):
                thread_id = str(event["thread_id"])
            elif event_type == "item.completed":
                item = event.get("item")
                if isinstance(item, dict) and item.get("type") == "agent_message":
                    text = item.get("text")
                    if isinstance(text, str):
                        messages.append(text)
            elif event_type == "turn.completed":
                turn_completed = True
            elif event_type in {"turn.failed", "error"}:
                err_obj = event.get("error")
                if isinstance(err_obj, dict) and err_obj.get("message"):
                    turn_failed_msg = str(err_obj["message"])
                elif event.get("message"):
                    turn_failed_msg = str(event["message"])
                else:
                    turn_failed_msg = "Codex turn failed"

        artifact_paths: list[Path] = []
        file_text = ""
        if output_file is not None and output_file.is_file() and output_file.stat().st_size > 0:
            file_text = output_file.read_text(encoding="utf-8", errors="replace")
            artifact_paths.append(output_file)

        output_text = file_text if file_text.strip() else (messages[-1] if messages else "")
        combined_diag = "\n".join(part for part in (result.stderr, turn_failed_msg or "", result.stdout) if part)
        lowered_diag = combined_diag.lower()

        error_code: str | None = None
        if "insufficient_quota" in lowered_diag or "exceeded your current quota" in lowered_diag:
            error_code = "quota_exceeded"
        elif "model_not_found" in lowered_diag or "does not exist or you do not have access" in lowered_diag:
            error_code = "model_not_found"

        exit_code = result.exit_code if result.exit_code is not None else -1
        if exit_code != 0 or turn_failed_msg is not None:
            return RuntimeExecutionResult(
                success=False,
                exit_code=exit_code,
                output_text=output_text,
                session_id=thread_id,
                error_code=error_code or "non_zero_exit",
                error_message=turn_failed_msg or result.stderr.strip() or f"Codex CLI exited with code {exit_code}",
                artifact_paths=artifact_paths,
                duration_seconds=result.duration_seconds,
            )

        if not output_text.strip() and not artifact_paths and not turn_completed:
            return RuntimeExecutionResult(
                success=False,
                exit_code=exit_code,
                output_text="",
                session_id=thread_id,
                error_code="empty_output",
                error_message="Codex CLI exited with code 0 but returned empty output",
                duration_seconds=result.duration_seconds,
            )

        return RuntimeExecutionResult(
            success=True,
            exit_code=exit_code,
            output_text=output_text,
            session_id=thread_id,
            artifact_paths=artifact_paths,
            duration_seconds=result.duration_seconds,
        )

    def execute_skill(
        self,
        prompt: str,
        cwd: Path,
        model: str | None = None,
        session_id: str | None = None,
        output_file: Path | None = None,
        timeout_seconds: float = 300.0,
        log_dir: Path | None = None,
        on_started: Any | None = None,
        reasoning_effort: str | None = None,
        sandbox: str = "read-only",
        **kwargs: Any,
    ) -> RuntimeExecutionResult:
        resolved_cwd = Path(cwd)
        logs = Path(log_dir) if log_dir is not None else (resolved_cwd / "logs")
        logs.mkdir(parents=True, exist_ok=True)
        stdout_path = logs / "codex.stdout.jsonl"
        stderr_path = logs / "codex.stderr.log"

        command = self.build_command(
            prompt=prompt,
            cwd=resolved_cwd,
            model=model,
            session_id=session_id,
            output_file=output_file,
            reasoning_effort=reasoning_effort,
            sandbox=sandbox,
            **kwargs,
        )
        proc_result = self.pm.run_process(
            argv=command,
            cwd=resolved_cwd,
            timeout_seconds=timeout_seconds,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            on_started=on_started,
        )
        return self.parse_output(proc_result, output_file=output_file, session_id=session_id)

    def execute_local_skill(
        self,
        prompt: str,
        cwd: Path,
        model: str | None = None,
        session_id: str | None = None,
        timeout_seconds: float = 300.0,
        log_dir: Path | None = None,
        on_started: Any | None = None,
        reasoning_effort: str | None = None,
        **kwargs: Any,
    ) -> RuntimeExecutionResult:
        resolved_cwd = Path(cwd)
        logs = Path(log_dir) if log_dir is not None else (resolved_cwd / "logs")
        logs.mkdir(parents=True, exist_ok=True)
        last_message_file = logs / "codex.last-message.txt"
        return self.execute_skill(
            prompt=prompt,
            cwd=resolved_cwd,
            model=model,
            session_id=session_id,
            output_file=last_message_file,
            timeout_seconds=timeout_seconds,
            log_dir=logs,
            on_started=on_started,
            reasoning_effort=reasoning_effort,
            sandbox="workspace-write",
            **kwargs,
        )

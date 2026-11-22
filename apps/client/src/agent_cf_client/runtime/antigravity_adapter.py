"""Antigravity CLI runtime adapter with strict model policy and DB trajectory fallback (RTM-006, RTM-010)."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sqlite3
import sys
from typing import Any

from agent_cf_client.execution.process_manager import ProcessManager, ProcessResult
from agent_cf_client.runtime.base import BaseRuntimeAdapter, RuntimeExecutionResult

ANTIGRAVITY_REASONING_EFFORTS = frozenset({"low", "medium", "high"})

ANTIGRAVITY_MODEL_MAP: dict[str, str] = {
    "claude-sonnet-4.6-thinking": "Claude Sonnet 4.6 (Thinking)",
    "claude-opus-4.6-thinking": "Claude Opus 4.6 (Thinking)",
    "gpt-oss-120b-medium": "GPT-OSS 120B (Medium)",
    "gemini-3.8-flash-high": "gemini-3.8-flash-high",
    "gemini-4-carbon": "gemini-4-carbon",
    "gemini-4-argon": "gemini-4-argon",
    "gemini-4-hydrogen": "gemini-4-hydrogen",
}


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, offset
        shift += 7
    raise ValueError("Truncated protobuf varint")


def _iter_proto_fields(data: bytes):
    offset = 0
    length = len(data)
    while offset < length:
        tag, offset = _read_varint(data, offset)
        field_num = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            val, offset = _read_varint(data, offset)
            yield field_num, wire_type, val
        elif wire_type == 1:
            if offset + 8 > length:
                break
            yield field_num, wire_type, data[offset : offset + 8]
            offset += 8
        elif wire_type == 2:
            size, offset = _read_varint(data, offset)
            if offset + size > length:
                break
            yield field_num, wire_type, data[offset : offset + size]
            offset += size
        elif wire_type == 5:
            if offset + 4 > length:
                break
            yield field_num, wire_type, data[offset : offset + 4]
            offset += 4
        else:
            break


def extract_assistant_text_from_step_payload(payload: bytes) -> str | None:
    """Decode assistant response text from an Antigravity SQLite step_payload protobuf blob."""
    if not payload:
        return None
    try:
        for field_num, wire_type, raw in _iter_proto_fields(payload):
            if field_num == 20 and wire_type == 2 and isinstance(raw, bytes):
                for sub_num, sub_wire, sub_raw in _iter_proto_fields(raw):
                    if sub_num == 1 and sub_wire == 2 and isinstance(sub_raw, bytes):
                        text = sub_raw.decode("utf-8", errors="replace").strip()
                        if text:
                            return text
    except ValueError:
        return None
    return None


_NOISY_CLI_LOG_SUBSTRINGS = (
    "You are not logged into Antigravity",
    "skipping empty or temp file",
    "Failed to resolve GeminiDir",
    "while reconciling: conversation ",
)


def _extract_cli_error_detail(
    log_text: str,
    stderr: str,
    stdout: str,
    log_file: Path | None = None,
) -> str | None:
    """Return the most actionable CLI error line from stderr, stdout, or log file."""
    if stderr and stderr.strip():
        return stderr.strip()[-500:]
    error_lines = [
        line.strip()
        for line in log_text.splitlines()
        if re.match(r"^E\d{4}\s", line.strip())
        and not any(noise in line for noise in _NOISY_CLI_LOG_SUBSTRINGS)
    ]
    if error_lines:
        return error_lines[-1][-500:]
    if stdout and stdout.strip():
        return stdout.strip()[-400:]
    if log_file is not None and log_file.is_file():
        return f"Chi tiết tại log CLI: {log_file}"
    return None


class AntigravityAdapter(BaseRuntimeAdapter):
    """Adapter executing Antigravity CLI (`agy`) with strict model checks and SQLite recovery."""

    def __init__(
        self,
        executable_path: str | None = None,
        process_manager: ProcessManager | None = None,
        conversations_dir: Path | None = None,
    ) -> None:
        self._configured_executable = executable_path
        self.pm = process_manager or ProcessManager()
        self.conversations_dir = (
            Path(conversations_dir)
            if conversations_dir is not None
            else (Path.home() / ".gemini" / "antigravity" / "conversations")
        )

    @property
    def adapter_id(self) -> str:
        return "antigravity"

    @property
    def _executable(self) -> str | None:
        if self._configured_executable:
            return self._configured_executable
        if sys.platform == "win32":
            for candidate_name in ("agy.exe", "agy.cmd", "agy"):
                found = shutil.which(candidate_name)
                if found:
                    return found
            for local_bin in (
                Path.home() / ".gemini" / "bin" / "agy.exe",
                Path.home() / ".antigravity" / "bin" / "agy.exe",
            ):
                if local_bin.is_file():
                    return str(local_bin)
            return None
        found = shutil.which("agy")
        if found:
            return found
        local_bin = Path.home() / ".gemini" / "bin" / "agy"
        return str(local_bin) if local_bin.is_file() else None

    def is_available(self) -> bool:
        return bool(self._executable)

    def map_model(self, model_id: str) -> str:
        """Map canonical Agent CF model ID to Antigravity CLI label/flag without guessing."""
        return ANTIGRAVITY_MODEL_MAP.get(model_id, model_id)

    def build_command(
        self,
        prompt: str,
        cwd: Path | None = None,
        model: str | None = None,
        session_id: str | None = None,
        timeout_seconds: float | None = None,
        log_file: Path | None = None,
        reasoning_effort: str | None = None,
        add_dirs: list[Path] | None = None,
        dangerously_skip_permissions: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        if reasoning_effort is not None and reasoning_effort not in ANTIGRAVITY_REASONING_EFFORTS:
            raise ValueError(
                f"Mức suy luận '{reasoning_effort}' không hợp lệ cho Antigravity CLI; "
                f"chỉ hỗ trợ: {', '.join(sorted(ANTIGRAVITY_REASONING_EFFORTS))}."
            )

        exe = self._executable or ("agy.exe" if sys.platform == "win32" else "agy")
        command: list[str] = [exe]
        if session_id:
            command.append(f"--conversation={session_id}")
        if model:
            command.extend(["--model", self.map_model(model)])
        if reasoning_effort is not None:
            command.extend(["--effort", reasoning_effort])
        if timeout_seconds is not None:
            command.extend(["--print-timeout", f"{max(1, int(round(timeout_seconds)))}s"])
        if log_file is not None:
            command.extend(["--log-file", str(log_file)])
        if add_dirs:
            for directory in add_dirs:
                command.extend(["--add-dir", str(directory)])
        if dangerously_skip_permissions:
            command.append("--dangerously-skip-permissions")
        command.extend(["-p", prompt])
        return command

    def get_latest_response_from_db(self, conv_id: str) -> str | None:
        """Read latest assistant text from Antigravity's local SQLite conversation DB."""
        if not conv_id:
            return None
        db_file = self.conversations_dir / f"{conv_id}.db"
        if not db_file.is_file():
            return None
        try:
            conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
            try:
                rows = conn.execute(
                    "SELECT step_payload FROM steps WHERE step_type = 15 ORDER BY idx DESC"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error:
            return None

        for (payload,) in rows:
            if isinstance(payload, (bytes, bytearray)):
                text = extract_assistant_text_from_step_payload(bytes(payload))
                if text:
                    return text
        return None

    def parse_output(
        self,
        result: ProcessResult,
        log_file: Path | None = None,
        requested_model: str | None = None,
        session_id: str | None = None,
    ) -> RuntimeExecutionResult:
        if result.timed_out:
            return RuntimeExecutionResult(
                success=False,
                exit_code=result.exit_code if result.exit_code is not None else -1,
                session_id=session_id,
                error_code="timeout",
                error_message=f"Antigravity CLI timed out after {result.duration_seconds:.1f}s",
                duration_seconds=result.duration_seconds,
            )
        if result.cancelled:
            return RuntimeExecutionResult(
                success=False,
                exit_code=result.exit_code if result.exit_code is not None else -1,
                session_id=session_id,
                error_code="cancelled",
                error_message="Antigravity CLI execution was cancelled",
                duration_seconds=result.duration_seconds,
            )

        log_text = ""
        if log_file is not None and log_file.is_file():
            log_text = log_file.read_text(encoding="utf-8", errors="replace")

        combined_diag = "\n".join(part for part in (log_text, result.stdout, result.stderr) if part)
        # Note: `Propagating selected model override` is logged on normal `--model` runs too;
        # only actual resolution failures indicate an unsupported/fallback model.
        fallback_markers = (
            "Failed to resolve model flag",
            "is not recognized as a known model",
        )
        matched_line = next(
            (
                line.strip()
                for line in combined_diag.splitlines()
                if any(marker in line for marker in fallback_markers)
            ),
            None,
        )
        if matched_line is not None:
            return RuntimeExecutionResult(
                success=False,
                exit_code=result.exit_code if result.exit_code is not None else 1,
                session_id=session_id,
                error_code="unsupported_model",
                error_message=(
                    f"Requested model '{requested_model or 'unknown'}' is unsupported; "
                    f"silent model substitution disallowed ({matched_line})"
                ),
                duration_seconds=result.duration_seconds,
            )

        conv_id = session_id
        match = re.search(r"agy\s+--conversation=([A-Za-z0-9._-]+)", result.stdout)
        if not match:
            match = re.search(r"conversation=([A-Za-z0-9._-]+)", combined_diag)
        if match:
            conv_id = match.group(1)

        cleaned_lines = [
            line
            for line in result.stdout.splitlines()
            if not re.match(r"^\s*agy\s+--conversation=[A-Za-z0-9._-]+\s*$", line)
        ]
        output_text = "\n".join(cleaned_lines).strip()

        if not output_text and conv_id:
            recovered = self.get_latest_response_from_db(conv_id)
            if recovered:
                output_text = recovered

        exit_code = result.exit_code if result.exit_code is not None else -1
        if exit_code != 0:
            detail = _extract_cli_error_detail(log_text, result.stderr, result.stdout, log_file)
            msg = f"Antigravity CLI exited with code {exit_code}"
            if detail:
                msg = f"{msg}: {detail}"
            return RuntimeExecutionResult(
                success=False,
                exit_code=exit_code,
                output_text=output_text,
                session_id=conv_id,
                error_code="non_zero_exit",
                error_message=msg,
                duration_seconds=result.duration_seconds,
            )

        if not output_text:
            detail = _extract_cli_error_detail(log_text, result.stderr, "", log_file)
            msg = "Antigravity CLI exited with code 0 but returned empty output"
            if detail:
                msg = f"{msg} ({detail})"
            return RuntimeExecutionResult(
                success=False,
                exit_code=exit_code,
                output_text="",
                session_id=conv_id,
                error_code="empty_output",
                error_message=msg,
                duration_seconds=result.duration_seconds,
            )

        return RuntimeExecutionResult(
            success=True,
            exit_code=exit_code,
            output_text=output_text,
            session_id=conv_id,
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
        **kwargs: Any,
    ) -> RuntimeExecutionResult:
        resolved_cwd = Path(cwd).resolve()
        logs = Path(log_dir) if log_dir is not None else (resolved_cwd / "logs")
        logs.mkdir(parents=True, exist_ok=True)
        stdout_path = logs / "antigravity.stdout.log"
        stderr_path = logs / "antigravity.stderr.log"
        cli_log_path = logs / "antigravity.cli.log"

        command = self.build_command(
            prompt=prompt,
            cwd=resolved_cwd,
            model=model,
            session_id=session_id,
            timeout_seconds=timeout_seconds,
            log_file=cli_log_path,
            reasoning_effort=reasoning_effort,
            add_dirs=kwargs.get("add_dirs"),
            dangerously_skip_permissions=kwargs.get("dangerously_skip_permissions", False),
        )
        proc_result = self.pm.run_process(
            argv=command,
            cwd=resolved_cwd,
            timeout_seconds=timeout_seconds,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            on_started=on_started,
        )
        parsed = self.parse_output(
            proc_result,
            log_file=cli_log_path,
            requested_model=model,
            session_id=session_id,
        )
        if parsed.success and output_file is not None and not output_file.exists():
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(parsed.output_text, encoding="utf-8")
            parsed.artifact_paths.append(output_file)
        return parsed

    def execute_local_skill(
        self,
        prompt: str,
        cwd: Path,
        model: str | None = None,
        timeout_seconds: float = 300.0,
        log_dir: Path | None = None,
        on_started: Any | None = None,
        session_id: str | None = None,
        reasoning_effort: str | None = None,
        **kwargs: Any,
    ) -> RuntimeExecutionResult:
        resolved_cwd = Path(cwd).resolve()
        return self.execute_skill(
            prompt=prompt,
            cwd=resolved_cwd,
            model=model,
            session_id=session_id,
            timeout_seconds=timeout_seconds,
            log_dir=log_dir,
            on_started=on_started,
            reasoning_effort=reasoning_effort,
            add_dirs=[resolved_cwd],
            dangerously_skip_permissions=True,
            **kwargs,
        )

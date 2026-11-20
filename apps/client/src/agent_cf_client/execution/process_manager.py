"""Process tree management, execution timeout, and Windows taskkill termination (CLI-002)."""

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False
    duration_seconds: float = 0.0


def kill_process_tree(pid: int) -> None:
    """Safely terminate a process and all its child processes without killing other processes."""
    if pid <= 0:
        return
    if sys.platform == "win32":
        try:
            extra_kwargs: dict[str, Any] = {}
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            # /F = forcefully terminate, /T = terminate process tree, /PID = target PID
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
                **extra_kwargs,
            )
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(pid), 15)  # SIGTERM
            time.sleep(0.5)
            os.killpg(os.getpgid(pid), 9)  # SIGKILL
        except Exception:
            pass


class ProcessManager:
    def __init__(self) -> None:
        pass

    def run_process(
        self,
        argv: list[str],
        cwd: Path,
        timeout_seconds: float | None = None,
        env: dict[str, str] | None = None,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
        cancel_event: threading.Event | None = None,
        on_started: Any | None = None,
    ) -> ProcessResult:
        """Run a process tree with timeout, cancellation, and stdout/stderr spooling."""
        if not argv:
            raise ValueError("Empty argv command")

        start_time = time.monotonic()
        process_env = dict(os.environ)
        process_env.setdefault("PYTHONIOENCODING", "utf-8")
        process_env.setdefault("PYTHONUTF8", "1")
        if env:
            process_env.update(env)

        stdout_file = None
        stderr_file = None
        if stdout_path:
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_file = open(stdout_path, "w", encoding="utf-8", errors="replace")
        if stderr_path:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            stderr_file = open(stderr_path, "w", encoding="utf-8", errors="replace")

        try:
            extra_kwargs: dict[str, Any] = {}
            if sys.platform == "win32":
                if hasattr(subprocess, "CREATE_NO_WINDOW"):
                    extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                extra_kwargs["startupinfo"] = startupinfo

            proc = subprocess.Popen(
                argv,
                cwd=str(cwd),
                env=process_env,
                stdout=stdout_file or subprocess.PIPE,
                stderr=stderr_file or subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                **extra_kwargs,
            )
        except Exception as exc:
            if stdout_file:
                stdout_file.close()
            if stderr_file:
                stderr_file.close()
            return ProcessResult(
                exit_code=-1,
                stdout="",
                stderr=f"Spawn failure: {exc}",
                duration_seconds=time.monotonic() - start_time,
            )

        if on_started:
            on_started(proc.pid)

        timed_out = False
        cancelled = False

        while proc.poll() is None:
            now = time.monotonic()
            elapsed = now - start_time

            if timeout_seconds is not None and elapsed > timeout_seconds:
                timed_out = True
                kill_process_tree(proc.pid)
                break

            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                kill_process_tree(proc.pid)
                break

            time.sleep(0.1)

        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            kill_process_tree(proc.pid)

        duration = time.monotonic() - start_time

        stdout_text = ""
        stderr_text = ""

        if stdout_file:
            stdout_file.close()
            if stdout_path and stdout_path.exists():
                stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        elif proc.stdout:
            stdout_text = proc.stdout.read()

        if stderr_file:
            stderr_file.close()
            if stderr_path and stderr_path.exists():
                stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        elif proc.stderr:
            stderr_text = proc.stderr.read()

        return ProcessResult(
            exit_code=proc.returncode,
            stdout=stdout_text,
            stderr=stderr_text,
            timed_out=timed_out,
            cancelled=cancelled,
            duration_seconds=duration,
        )

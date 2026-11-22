"""Base runtime adapter abstractions and execution result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RuntimeExecutionResult:
    """Normalized execution result returned by local runtime adapters."""

    success: bool
    exit_code: int | None
    output_text: str = ""
    session_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    artifact_paths: list[Path] = field(default_factory=list)
    duration_seconds: float = 0.0


class BaseRuntimeAdapter(ABC):
    """Contract for local CLI/runtime adapters (Codex, Antigravity)."""

    @property
    @abstractmethod
    def adapter_id(self) -> str:
        """Canonical adapter identifier ('codex' or 'antigravity')."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the underlying CLI executable can be resolved."""

    @abstractmethod
    def execute_skill(
        self,
        prompt: str,
        cwd: Path,
        model: str | None = None,
        session_id: str | None = None,
        output_file: Path | None = None,
        timeout_seconds: float = 300.0,
        **kwargs: Any,
    ) -> RuntimeExecutionResult:
        """Execute a Skill invocation and return normalized output/session metadata."""

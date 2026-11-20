"""Desktop tray controller and Windows user session management (CLI-003)."""

import ctypes
from dataclasses import dataclass
import sys
import threading
from typing import Any, Callable


@dataclass
class DesktopState:
    status: str = "disconnected"  # disconnected, connecting, idle, running, disabled, stopping, error
    current_run_id: str | None = None
    current_task: str | None = None
    last_error: str | None = None


class DesktopController:
    """Manages the desktop runner state, tray status representation, and controlled shutdown."""

    def __init__(self, on_status_change: Callable[[DesktopState], None] | None = None) -> None:
        self.state = DesktopState()
        self.shutdown_event = threading.Event()
        self.on_status_change = on_status_change
        self._lock = threading.Lock()

    def set_status(
        self,
        status: str,
        current_run_id: str | None = None,
        current_task: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self.state.status = status
            self.state.current_run_id = current_run_id
            self.state.current_task = current_task
            self.state.last_error = error
        if self.on_status_change:
            self.on_status_change(self.state)

    def get_status(self) -> DesktopState:
        with self._lock:
            return DesktopState(
                status=self.state.status,
                current_run_id=self.state.current_run_id,
                current_task=self.state.current_task,
                last_error=self.state.last_error,
            )

    def request_shutdown(self) -> None:
        """Trigger controlled graceful shutdown."""
        self.shutdown_event.set()
        self.set_status("stopping")

    def is_shutdown_requested(self) -> bool:
        return self.shutdown_event.is_set()

    def is_windows_session_locked(self) -> bool:
        """Check if Windows desktop session is locked (Windows only)."""
        if sys.platform != "win32":
            return False
        try:
            # OpenInputDesktop checks whether current desktop is interactive/active
            user32 = ctypes.windll.user32
            h_desktop = user32.OpenInputDesktop(0, False, 0x0001)  # DESKTOP_READOBJECTS
            if h_desktop == 0:
                # Unable to open input desktop, typically locked or switched to UAC/secure desktop
                return True
            user32.CloseDesktop(h_desktop)
            return False
        except Exception:
            return False

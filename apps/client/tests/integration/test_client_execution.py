"""Integration tests for CLI-001, CLI-002, PC-001, and CLI-003."""

import os
from pathlib import Path
import sys
import threading
import time
import pytest
from fastapi.testclient import TestClient

from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.desktop.tray import DesktopController
from agent_cf_client.execution.journal import ExecutionJournal
from agent_cf_client.execution.process_manager import ProcessManager, kill_process_tree
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.runners.repository import AuthenticationError, RunnerRepository


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "runners_test.sqlite3")
    database.migrate()
    # Bootstrap workspace
    projects = ProjectRepository(database)
    projects.create_workspace(workspace_id="ws-local", name="Local Workspace")
    return database


@pytest.fixture
def client_app(db, tmp_path):
    settings = ServerSettings(database_path=db.path, temporal_enabled=False)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# PC-001 & CLI-001: Pairing, Authentication, Sessions, Heartbeats & Revocation
# =============================================================================

def test_pc001_cli001_pairing_and_session_lifecycle(client_app):
    # 1. Operator creates pairing code
    code_res = client_app.post(
        "/v1/pairing-codes",
        json={"workspace_id": "ws-local", "name": "Worker PC Alpha", "expires_in_seconds": 300},
    )
    assert code_res.status_code == 201
    pairing_code = code_res.json()["pairing_code"]

    # 2. Runner pairs using code
    pair_res = client_app.post(
        "/v1/runners/pair",
        json={"pairing_code": pairing_code, "client_version": "0.1.0", "machine_fingerprint": "pc-fp-123"},
    )
    assert pair_res.status_code == 201
    data = pair_res.json()
    runner_id = data["runner_id"]
    runner_token = data["runner_token"]
    assert runner_id.startswith("pc-")
    assert len(runner_token) == 64

    # 3. One-time code cannot be reused
    reuse_res = client_app.post(
        "/v1/runners/pair",
        json={"pairing_code": pairing_code},
    )
    assert reuse_res.status_code == 401

    # 4. Start runner session with token
    headers = {"Authorization": f"Bearer {runner_token}"}
    sess_res = client_app.post(
        f"/v1/runners/{runner_id}/sessions",
        json={"client_version": "0.1.0", "capabilities": ["codex", "python"]},
        headers=headers,
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["session_id"]
    assert session_id.startswith("sess-")

    # 5. Heartbeat updates metrics
    hb_res = client_app.post(
        f"/v1/runners/{runner_id}/heartbeat",
        json={"session_id": session_id, "cpu_percent": 12.5, "ram_percent": 45.0},
        headers=headers,
    )
    assert hb_res.status_code == 200
    assert hb_res.json()["stop_requested"] is False

    # Check runner in operator PC list
    runner_info = client_app.get(f"/v1/runners/{runner_id}").json()
    assert runner_info["status"] == "online"
    assert runner_info["cpu_percent"] == 12.5

    # 6. Session deduplication: opening a new session invalidates old session
    sess_res2 = client_app.post(
        f"/v1/runners/{runner_id}/sessions",
        json={"client_version": "0.1.0", "capabilities": ["codex"]},
        headers=headers,
    )
    assert sess_res2.status_code == 201
    new_session_id = sess_res2.json()["session_id"]
    assert new_session_id != session_id

    # Old session heartbeat is rejected (403 SessionInvalid)
    stale_hb = client_app.post(
        f"/v1/runners/{runner_id}/heartbeat",
        json={"session_id": session_id},
        headers=headers,
    )
    assert stale_hb.status_code == 403

    # 7. Disabling runner: heartbeat signals stop_requested = True
    client_app.post(f"/v1/runners/{runner_id}/disable")
    new_hb = client_app.post(
        f"/v1/runners/{runner_id}/heartbeat",
        json={"session_id": new_session_id},
        headers=headers,
    )
    assert new_hb.status_code == 200
    assert new_hb.json()["stop_requested"] is True

    # 8. Revoking runner credential
    client_app.post(f"/v1/runners/{runner_id}/revoke")
    revoked_hb = client_app.post(
        f"/v1/runners/{runner_id}/heartbeat",
        json={"session_id": new_session_id},
        headers=headers,
    )
    assert revoked_hb.status_code == 401


# =============================================================================
# CLI-002: Process Tree, Workspace Isolation, Timeout, Cancellation, UTF-8
# =============================================================================

def test_cli002_workspace_isolation_and_path_traversal_defense(tmp_path):
    mgr = WorkspaceManager(base_dir=tmp_path / "workspaces")

    # Safe workspace creation
    ws = mgr.create_attempt_workspace(run_id="run-101", attempt_id="att-1")
    assert ws.exists()
    assert (ws / "artifacts").exists()
    assert (ws / "logs").exists()

    # Rejects path traversal attempts
    with pytest.raises(ValueError, match="Unsafe path component"):
        mgr.create_attempt_workspace(run_id="../escape", attempt_id="att-1")

    with pytest.raises(ValueError, match="Unsafe path component"):
        mgr.create_attempt_workspace(run_id="run-1", attempt_id="..\\escape")

    # Rejects path escape during resolve
    with pytest.raises(ValueError, match="Path traversal detected"):
        mgr.resolve_safe_path(ws, "../../sensitive.txt")


def test_cli002_process_execution_utf8_vietnamese(tmp_path):
    pm = ProcessManager()
    output_file = tmp_path / "output.txt"

    # Command printing Vietnamese UTF-8 topic
    topic = "3.Thật tệ khi làm mẹ đơn thân — Cốt truyện & Nhân vật"
    code = f'import sys; print("{topic}"); sys.stdout.flush()'
    argv = [sys.executable, "-c", code]

    res = pm.run_process(argv, cwd=tmp_path, stdout_path=output_file)
    assert res.exit_code == 0
    assert not res.timed_out
    assert not res.cancelled
    assert topic in res.stdout
    assert output_file.read_text(encoding="utf-8").strip() == topic


def test_cli002_process_timeout_and_tree_kill(tmp_path):
    pm = ProcessManager()

    # Process that sleeps longer than timeout
    code = "import time; time.sleep(10)"
    argv = [sys.executable, "-c", code]

    res = pm.run_process(argv, cwd=tmp_path, timeout_seconds=0.5)
    assert res.timed_out is True
    assert res.duration_seconds < 3.0


def test_cli002_process_cancellation(tmp_path):
    pm = ProcessManager()
    cancel_event = threading.Event()

    # Cancel after 0.3s
    timer = threading.Timer(0.3, cancel_event.set)
    timer.start()

    code = "import time; time.sleep(10)"
    argv = [sys.executable, "-c", code]

    res = pm.run_process(argv, cwd=tmp_path, cancel_event=cancel_event)
    timer.cancel()
    assert res.cancelled is True


def test_cli002_execution_journaling(tmp_path):
    ws = tmp_path / "run_ws"
    ws.mkdir()
    journal = ExecutionJournal(ws)

    # 1. Planned
    planned = journal.record_planned(
        attempt_id="att-1",
        run_id="run-1",
        task_run_id="task-1",
        generation=1,
        launch_id="launch-1",
        command_argv=["python", "script.py"],
    )
    assert planned["state"] == "planned"

    # 2. Started
    started = journal.record_started(pid=12345)
    assert started["state"] == "running"
    assert started["pid"] == 12345

    # 3. Completed
    completed = journal.record_completed(exit_code=0)
    assert completed["state"] == "completed"

    # Reload from disk
    saved = journal.read()
    assert saved["state"] == "completed"
    assert saved["attempt_id"] == "att-1"


# =============================================================================
# CLI-003: Desktop Controller & Controlled Shutdown
# =============================================================================

def test_cli003_desktop_controller_lifecycle():
    state_changes = []
    ctrl = DesktopController(on_status_change=lambda s: state_changes.append(s.status))

    ctrl.set_status("connecting")
    ctrl.set_status("idle")
    ctrl.set_status("running", current_run_id="run-123", current_task="task-story")

    status = ctrl.get_status()
    assert status.status == "running"
    assert status.current_run_id == "run-123"

    # Controlled shutdown
    ctrl.request_shutdown()
    assert ctrl.is_shutdown_requested()
    assert ctrl.get_status().status == "stopping"
    assert "stopping" in state_changes

    # Session lock method returns a boolean without raising
    is_locked = ctrl.is_windows_session_locked()
    assert isinstance(is_locked, bool)

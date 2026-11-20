"""Integration tests for Scheduling, PC Selection, and Real-Data Overview (PROC-004, OVW-001)."""

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.agents.repository import AgentRepository
from agent_cf_server.infrastructure.overview.repository import OverviewRepository
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.processes.schedule_repository import ScheduleRepository
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.runners.repository import RunnerRepository
from agent_cf_server.infrastructure.runs.repository import RunRepository
from agent_cf_server.infrastructure.settings.repository import SettingsRepository


@pytest.fixture
def env(tmp_path):
    db_path = tmp_path / "test_proc004_ovw001.sqlite3"
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    settings = ServerSettings(
        database_path=db_path,
        artifacts_dir=artifacts_dir,
        temporal_enabled=False,
    )
    app = create_app(settings)
    database = Database(db_path)
    database.migrate()

    projects = ProjectRepository(database)
    projects.create_workspace(workspace_id="ws-main", name="Main Workspace")
    projects.create_project(project_id="proj-alpha", workspace_id="ws-main", name="Alpha Project")
    projects.create_project(project_id="proj-beta", workspace_id="ws-main", name="Beta Project (No Targets)")

    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-p1", project_id="proj-alpha", name="Process Alpha")

    # Publish Version 1
    def1 = {
        "definition_format_version": "1",
        "interpreter_version": "dag-v1",
        "tasks": [{"id": "t1", "task_key": "step1", "runtime": {"adapter": "codex", "model_id": "test"}}],
        "dependencies": [],
    }
    processes.store_published(
        workspace_id="ws-main",
        project_id="proj-alpha",
        process_id="proc-p1",
        version_id="ver-p1-v1",
        version_number=1,
        definition=def1,
        snapshot_sha256="1" * 64,
    )

    client = TestClient(app)
    return {
        "database": database,
        "settings": settings,
        "client": client,
        "processes": processes,
        "projects": projects,
        "run_repo": RunRepository(database),
        "schedule_repo": ScheduleRepository(database),
        "overview_repo": OverviewRepository(database),
        "agent_repo": AgentRepository(database),
        "settings_repo": SettingsRepository(database),
    }


def pair_and_activate_runner(env, name="PC-Dedicated-1"):
    client = env["client"]
    resp = client.post(
        "/v1/pairing-codes",
        json={"workspace_id": "ws-main", "name": name, "expires_in_seconds": 300},
    )
    assert resp.status_code == 201
    code = resp.json()["pairing_code"]

    resp = client.post("/v1/runners/pair", json={"pairing_code": code, "client_version": "0.1.0"})
    assert resp.status_code == 201
    runner_id = resp.json()["runner_id"]
    runner_token = resp.json()["runner_token"]

    resp = client.post(
        f"/v1/runners/{runner_id}/sessions",
        json={"client_version": "0.1.0", "capabilities": ["codex", "antigravity"]},
        headers={"Authorization": f"Bearer {runner_token}"},
    )
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]
    return {"runner_id": runner_id, "token": runner_token, "session_id": session_id}


# =============================================================================
# PROC-004: Scheduling & PC Selection
# =============================================================================

def test_save_schedule_does_not_start_and_does_not_run(env):
    """Save không Start, Save không Run: Creating a schedule leaves it inactive with no runs."""
    client = env["client"]
    payload = {
        "name": "Daily Morning News",
        "process_version_id": "ver-p1-v1",
        "cadence": "daily",
        "input": {"topic": "AI news"},
    }
    resp = client.post(
        "/v1/processes/proc-p1/schedules?project_id=proj-alpha",
        json=payload,
        headers={"Idempotency-Key": "sched-save-1"},
    )
    assert resp.status_code == 201
    sched = resp.json()
    assert sched["name"] == "Daily Morning News"
    assert sched["is_active"] is False  # Save không Start!
    assert sched["next_run_at"] is None
    assert sched["last_run_at"] is None

    # Verify no runs created
    runs_resp = client.get("/v1/runs?project_id=proj-alpha")
    assert len(runs_resp.json()["items"]) == 0


def test_start_schedule_does_not_run_immediately(env):
    """Start không Run ngay: Starting schedule sets is_active=True and next_run_at, but does not run immediately."""
    client = env["client"]
    sched_resp = client.post(
        "/v1/processes/proc-p1/schedules?project_id=proj-alpha",
        json={"name": "Hourly Check", "process_version_id": "ver-p1-v1", "cadence": "hourly"},
        headers={"Idempotency-Key": "sched-start-1"},
    )
    sched_id = sched_resp.json()["id"]

    # Start schedule
    start_resp = client.post(
        f"/v1/schedules/{sched_id}/start",
        headers={"Idempotency-Key": "start-key-1"},
    )
    assert start_resp.status_code == 200
    started_sched = start_resp.json()
    assert started_sched["is_active"] is True
    assert started_sched["next_run_at"] is not None
    assert started_sched["last_run_at"] is None  # No run occurred yet!

    # Verify no runs were spawned
    runs = client.get("/v1/runs?project_id=proj-alpha").json()["items"]
    assert len(runs) == 0


def test_stop_schedule_does_not_cancel_active_runs(env):
    """Stop không Cancel: Stopping a schedule deactivates future ticks, but does not cancel active runs."""
    client = env["client"]
    runner = pair_and_activate_runner(env)

    sched_resp = client.post(
        "/v1/processes/proc-p1/schedules?project_id=proj-alpha",
        json={"name": "Stop Test", "process_version_id": "ver-p1-v1", "cadence": "daily"},
        headers={"Idempotency-Key": "sched-stop-1"},
    )
    sched_id = sched_resp.json()["id"]
    client.post(f"/v1/schedules/{sched_id}/start", headers={"Idempotency-Key": "start-stop-1"})

    # Trigger a run via schedule
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    trig_resp = client.post(
        f"/v1/schedules/{sched_id}/trigger",
        json={"scheduled_for": now_utc},
        headers={"Idempotency-Key": "trig-1"},
    )
    assert trig_resp.status_code == 200
    run_id = trig_resp.json()["run_id"]

    # Claim task so run becomes running
    run_info = client.get(f"/v1/runs/{run_id}").json()
    task_id = run_info["task_runs"][0]["id"]
    claim_resp = client.post(
        f"/v1/task-runs/{task_id}/claim",
        json={"session_id": runner["session_id"], "lease_seconds": 60},
        headers={"Idempotency-Key": "claim-active", "Authorization": f"Bearer {runner['token']}"},
    )
    assert claim_resp.status_code == 201

    # Now STOP the schedule
    stop_resp = client.post(f"/v1/schedules/{sched_id}/stop", headers={"Idempotency-Key": "stop-key-1"})
    assert stop_resp.status_code == 200
    assert stop_resp.json()["is_active"] is False

    # The active run MUST still be running (NOT cancelled)!
    run_after_stop = client.get(f"/v1/runs/{run_id}").json()
    assert run_after_stop["status"] in ("queued", "running")
    assert run_after_stop["status"] != "cancelled"


def test_cancel_run_does_not_stop_schedule(env):
    """Cancel không Stop: Cancelling an individual run leaves the schedule active for future ticks."""
    client = env["client"]
    sched_resp = client.post(
        "/v1/processes/proc-p1/schedules?project_id=proj-alpha",
        json={"name": "Cancel Run Test", "process_version_id": "ver-p1-v1", "cadence": "daily"},
        headers={"Idempotency-Key": "sched-cancel-1"},
    )
    sched_id = sched_resp.json()["id"]
    client.post(f"/v1/schedules/{sched_id}/start", headers={"Idempotency-Key": "start-cancel-1"})

    # Trigger run
    time_tick = "2026-11-16T12:00:00Z"
    trig_resp = client.post(
        f"/v1/schedules/{sched_id}/trigger",
        json={"scheduled_for": time_tick},
        headers={"Idempotency-Key": "trig-cancel-1"},
    )
    run_id = trig_resp.json()["run_id"]

    # Cancel the run
    cancel_resp = client.post(
        f"/v1/runs/{run_id}/cancel",
        json={"reason": "Operator abort"},
        headers={"Idempotency-Key": "cancel-run-1"},
    )
    assert cancel_resp.status_code == 202

    # Schedule must STILL be active
    sched_after = client.get(f"/v1/schedules/{sched_id}").json()
    assert sched_after["is_active"] is True


def test_pinned_version_immutable_when_new_version_published(env):
    """Version được ghim: Publishing a new ProcessVersion does NOT change existing schedule's pinned version."""
    client = env["client"]
    sched_resp = client.post(
        "/v1/processes/proc-p1/schedules?project_id=proj-alpha",
        json={"name": "Pinned Test", "process_version_id": "ver-p1-v1", "cadence": "daily"},
        headers={"Idempotency-Key": "sched-pin-1"},
    )
    sched_id = sched_resp.json()["id"]
    assert sched_resp.json()["process_version_id"] == "ver-p1-v1"

    # Now publish Version 2 of proc-p1
    def2 = {
        "definition_format_version": "1",
        "interpreter_version": "dag-v1",
        "tasks": [{"id": "t1_v2", "task_key": "step1_v2", "runtime": {"adapter": "codex", "model_id": "v2"}}],
        "dependencies": [],
    }
    env["processes"].store_published(
        workspace_id="ws-main",
        project_id="proj-alpha",
        process_id="proc-p1",
        version_id="ver-p1-v2",
        version_number=2,
        definition=def2,
        snapshot_sha256="2" * 64,
    )

    # Schedule pinned version MUST remain ver-p1-v1
    sched_now = client.get(f"/v1/schedules/{sched_id}").json()
    assert sched_now["process_version_id"] == "ver-p1-v1"


def test_schedule_deduplication_by_scheduled_for(env):
    """Khóa lịch trùng: Triggering twice for the exact same scheduled_for timestamp is rejected."""
    client = env["client"]
    sched_resp = client.post(
        "/v1/processes/proc-p1/schedules?project_id=proj-alpha",
        json={"name": "Dedup Test", "process_version_id": "ver-p1-v1", "cadence": "hourly"},
        headers={"Idempotency-Key": "sched-dedup-1"},
    )
    sched_id = sched_resp.json()["id"]
    scheduled_time = "2026-11-16T15:00:00Z"

    # First trigger succeeds
    t1 = client.post(
        f"/v1/schedules/{sched_id}/trigger",
        json={"scheduled_for": scheduled_time},
        headers={"Idempotency-Key": "trig-key-first"},
    )
    assert t1.status_code == 200

    # Second trigger with same scheduled_for -> 409 Conflict (duplicate tick)
    t2 = client.post(
        f"/v1/schedules/{sched_id}/trigger",
        json={"scheduled_for": scheduled_time},
        headers={"Idempotency-Key": "trig-key-second"},
    )
    assert t2.status_code == 409
    assert "duplicate_schedule_tick" in t2.json()["detail"]


def test_schedule_busy_skips_when_previous_run_active(env):
    """Lịch đến hạn khi lượt cũ chưa xong: Previous run still in progress causes tick to skip without duplicate run."""
    client = env["client"]
    runner = pair_and_activate_runner(env, name="PC-Busy-1")

    sched_resp = client.post(
        "/v1/processes/proc-p1/schedules?project_id=proj-alpha",
        json={"name": "Busy Test", "process_version_id": "ver-p1-v1", "cadence": "hourly"},
        headers={"Idempotency-Key": "sched-busy-1"},
    )
    sched_id = sched_resp.json()["id"]

    # First trigger
    t1 = client.post(
        f"/v1/schedules/{sched_id}/trigger",
        json={"scheduled_for": "2026-11-16T10:00:00Z"},
        headers={"Idempotency-Key": "trig-busy-1"},
    )
    assert t1.status_code == 200
    run_id = t1.json()["run_id"]

    # Second trigger arrives at 11:00, but first run is still queued/running!
    t2 = client.post(
        f"/v1/schedules/{sched_id}/trigger",
        json={"scheduled_for": "2026-11-16T11:00:00Z"},
        headers={"Idempotency-Key": "trig-busy-2"},
    )
    assert t2.status_code == 409
    assert "schedule_busy" in t2.json()["detail"]

    # Check schedule_ticks in DB
    with env["database"].connect() as conn:
        ticks = conn.execute("SELECT * FROM schedule_ticks WHERE schedule_id=?", (sched_id,)).fetchall()
        assert len(ticks) == 2
        statuses = [tk["status"] for tk in ticks]
        assert "triggered" in statuses
        assert "skipped_busy" in statuses


def test_schedule_pc_selection_policy_offline_disabled(env):
    """PC offline / disabled: Pinned runner prevents execution and rejects dispatch."""
    client = env["client"]
    runner = pair_and_activate_runner(env, name="PC-Pinned-Offline")
    runner_id = runner["runner_id"]

    # End runner session (make it offline)
    with env["database"].transaction() as conn:
        conn.execute("UPDATE runner_sessions SET status='expired' WHERE runner_id=?", (runner_id,))

    # Create schedule with this runner pinned
    sched_resp = client.post(
        "/v1/processes/proc-p1/schedules?project_id=proj-alpha",
        json={
            "name": "Offline PC Test",
            "process_version_id": "ver-p1-v1",
            "cadence": "daily",
            "default_runner_id": runner_id,
        },
        headers={"Idempotency-Key": "sched-offline-pc"},
    )
    sched_id = sched_resp.json()["id"]

    # Triggering when pinned runner is offline must raise 409 ConflictError (runner_offline)
    trig_resp = client.post(
        f"/v1/schedules/{sched_id}/trigger",
        json={"scheduled_for": "2026-11-16T18:00:00Z"},
        headers={"Idempotency-Key": "trig-offline-1"},
    )
    assert trig_resp.status_code == 409
    assert "runner_offline" in trig_resp.json()["detail"]


# =============================================================================
# OVW-001: Overview from Real Data
# =============================================================================

def test_overview_unresolved_errors_and_acknowledgment(env):
    """OVW-001: Overview displays failed runs in unresolved errors. Acknowledgment clears error without mutating run status."""
    client = env["client"]
    runner = pair_and_activate_runner(env, name="PC-OVW-1")

    # Create a run and fail it
    run_resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-p1-v1", "input": {"topic": "Failed Run Test"}},
        headers={"Idempotency-Key": "run-fail-ovw"},
    )
    run_id = run_resp.json()["id"]
    task_id = run_resp.json()["task_runs"][0]["id"]

    claim = client.post(
        f"/v1/task-runs/{task_id}/claim",
        json={"session_id": runner["session_id"], "lease_seconds": 60},
        headers={"Idempotency-Key": "claim-fail-ovw", "Authorization": f"Bearer {runner['token']}"},
    )
    client.post(
        f"/v1/attempts/{claim.json()['attempt_id']}/complete",
        json={"outcome": "failed", "error": {"code": "FATAL_CRASH", "message": "Disk out of space"}},
        headers={"X-Execution-Token": claim.json()["execution_token"], "Idempotency-Key": "comp-fail-ovw"},
    )

    # 1. Check Overview: unresolved error must appear
    ovw1 = client.get("/v1/overview/summary").json()
    err_runs = [e["run_id"] for e in ovw1["unresolved_errors"]]
    assert run_id in err_runs
    err_item = next(e for e in ovw1["unresolved_errors"] if e["run_id"] == run_id)
    assert err_item["error"]["code"] == "FATAL_CRASH"
    assert err_item["topic"] == "Failed Run Test"

    # 2. Acknowledge error via POST /v1/runs/{id}/acknowledge-error
    ack_resp = client.post(
        f"/v1/runs/{run_id}/acknowledge-error",
        json={"notes": "Cleared disk and reviewed logs"},
        headers={"Idempotency-Key": "ack-key-1"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"

    # 3. Check Overview again: error is now resolved/cleared from unresolved list
    ovw2 = client.get("/v1/overview/summary").json()
    err_runs_after = [e["run_id"] for e in ovw2["unresolved_errors"]]
    assert run_id not in err_runs_after

    # 4. Crucial rule: process_runs.status MUST STILL BE 'failed'! (không đổi status Run)
    run_still_failed = client.get(f"/v1/runs/{run_id}").json()
    assert run_still_failed["status"] == "failed"


def test_overview_project_progress_with_and_without_targets(env):
    """OVW-001: Project with targets shows counts; project with no targets shows null / dash, not 0/0 or fake On track."""
    client = env["client"]

    # Set real target on proj-alpha
    env["overview_repo"].set_project_target(
        project_id="proj-alpha",
        name="Q4 Videos",
        period="monthly",
        target_count=20,
        completed_count=8,
        status="in_progress",
    )

    # Fetch overview summary
    ovw = client.get("/v1/overview/summary").json()
    projects_by_id = {p["project_id"]: p for p in ovw["projects_progress"]}

    # proj-alpha has target
    alpha = projects_by_id["proj-alpha"]
    assert alpha["has_targets"] is True
    assert alpha["targets"][0]["completed_count"] == 8
    assert alpha["targets"][0]["target_count"] == 20

    # proj-beta has NO target -> targets is None, has_targets is False
    beta = projects_by_id["proj-beta"]
    assert beta["has_targets"] is False
    assert beta["targets"] is None  # Front-end renders "—"


def test_overview_agent_token_usage_ranked_and_no_fabricated_data(env):
    """OVW-001: Agent token usage comes from real tracking. Agents with no usage show explicit None / 'Chưa có dữ liệu'."""
    client = env["client"]

    # Seed provider, model, and roles
    env["settings_repo"].create_provider("prov-openai", "OpenAI", "openai", "https://api.openai.com/v1")
    env["settings_repo"].create_model("gpt-5.6-sol", "prov-openai", "GPT-5.6", "gpt-5.6-sol")
    env["settings_repo"].create_role("role-writer", "Story Writer", "Writes narrative arcs")
    env["settings_repo"].create_role("role-reviewer", "Reviewer", "Reviews narrative output")

    # Register two agents
    env["agent_repo"].create_agent(
        agent_id="agent-writer-1",
        name="Writer Bot",
        role_id="role-writer",
        model_id="gpt-5.6-sol",
    )
    env["agent_repo"].create_agent(
        agent_id="agent-idle-2",
        name="Idle Bot",
        role_id="role-reviewer",
        model_id="gpt-5.6-sol",
    )

    # Record real token usage ONLY for agent-writer-1 (dummy run_id/task_run_id)
    # First create a dummy run for foreign key
    dummy_run = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-p1-v1", "input": {"test": 1}},
        headers={"Idempotency-Key": "run-dummy-tokens"},
    ).json()
    t_id = dummy_run["task_runs"][0]["id"]

    env["overview_repo"].record_agent_token_usage(
        agent_id="agent-writer-1",
        run_id=dummy_run["id"],
        task_run_id=t_id,
        prompt_tokens=4200,
        completion_tokens=850,
    )

    ovw = client.get("/v1/overview/summary").json()
    agents = {a["agent_id"]: a for a in ovw["agents_token_usage"]}

    # agent-writer-1 has real data
    writer = agents["agent-writer-1"]
    assert writer["has_usage"] is True
    assert writer["total_tokens"] == 5050
    assert writer["prompt_tokens"] == 4200
    assert writer["completion_tokens"] == 850

    # agent-idle-2 has NO token data -> total_tokens is None, has_usage is False (no fake numbers)
    idle = agents["agent-idle-2"]
    assert idle["has_usage"] is False
    assert idle["total_tokens"] is None

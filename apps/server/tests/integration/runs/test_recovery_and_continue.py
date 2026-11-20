"""Integration tests for Recovery after Interruption and Safe Human Continue (REL-001, REL-003)."""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.runners.repository import RunnerRepository
from agent_cf_server.infrastructure.runs.repository import RunRepository


@pytest.fixture
def test_env(tmp_path):
    db_path = tmp_path / "test_recovery_continue.sqlite3"
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
    projects.create_workspace(workspace_id="ws-1", name="Workspace 1")
    projects.create_project(project_id="proj-1", workspace_id="ws-1", name="Project 1")
    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-1", project_id="proj-1", name="Multi Step Pipeline")

    # Define a 5-step sequential pipeline: n1 -> n2 -> n3 -> n4 -> n5
    definition_5_nodes = {
        "definition_format_version": "1",
        "interpreter_version": "dag-v1",
        "tasks": [
            {"id": "node-1", "task_key": "step1", "runtime": {"adapter": "codex", "model_id": "test"}},
            {"id": "node-2", "task_key": "step2", "runtime": {"adapter": "codex", "model_id": "test"}},
            {"id": "node-3", "task_key": "step3", "runtime": {"adapter": "codex", "model_id": "test"}},
            {"id": "node-4", "task_key": "step4", "runtime": {"adapter": "codex", "model_id": "test"}},
            {"id": "node-5", "task_key": "step5", "runtime": {"adapter": "codex", "model_id": "test"}},
        ],
        "dependencies": [
            {"source_task_id": "node-1", "target_task_id": "node-2"},
            {"source_task_id": "node-2", "target_task_id": "node-3"},
            {"source_task_id": "node-3", "target_task_id": "node-4"},
            {"source_task_id": "node-4", "target_task_id": "node-5"},
        ],
    }
    processes.store_published(
        workspace_id="ws-1",
        project_id="proj-1",
        process_id="proc-1",
        version_id="ver-seq-5",
        version_number=1,
        definition=definition_5_nodes,
        snapshot_sha256="a" * 64,
    )

    client = TestClient(app)
    return {
        "db_path": db_path,
        "database": database,
        "settings": settings,
        "client": client,
        "artifacts_dir": artifacts_dir,
    }


def pair_and_start_runner(test_env, name="PC-Local-1"):
    client = test_env["client"]
    resp = client.post(
        "/v1/pairing-codes",
        json={"workspace_id": "ws-1", "name": name, "expires_in_seconds": 300},
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

    return {
        "runner_id": runner_id,
        "runner_token": runner_token,
        "session_id": session_id,
    }


# =============================================================================
# REL-001: Reconcile After Interruption & Late Result Protection
# =============================================================================

def test_expired_lease_rejects_late_complete_attempt(test_env):
    """REL-001: An attempt whose lease has expired is rejected with 409 ConflictError (stale_execution)."""
    client = test_env["client"]
    runner = pair_and_start_runner(test_env)

    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-seq-5", "input": {"test": 1}},
        headers={"Idempotency-Key": "run-expired-lease"},
    )
    assert resp.status_code == 202
    run_id = resp.json()["id"]
    task_run_id = resp.json()["task_runs"][0]["id"]

    # Claim task with short lease
    claim_resp = client.post(
        f"/v1/task-runs/{task_run_id}/claim",
        json={"session_id": runner["session_id"], "lease_seconds": 10},
        headers={"Idempotency-Key": "claim-1", "Authorization": f"Bearer {runner['runner_token']}"},
    )
    assert claim_resp.status_code == 201
    attempt_id = claim_resp.json()["attempt_id"]
    token = claim_resp.json()["execution_token"]

    # Manually expire the attempt lease in DB
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    with test_env["database"].transaction() as conn:
        conn.execute("UPDATE execution_grants SET expires_at=? WHERE attempt_id=?", (past_time, attempt_id))

    # Late completion must be rejected
    complete_resp = client.post(
        f"/v1/attempts/{attempt_id}/complete",
        json={"outcome": "succeeded", "output": {"result": "too late"}},
        headers={"X-Execution-Token": token, "Idempotency-Key": "comp-expired"},
    )
    assert complete_resp.status_code == 409
    assert "stale_execution" in complete_resp.json()["detail"]


def test_revoked_grant_rejects_complete_attempt(test_env):
    """REL-001: An attempt whose grant was revoked is rejected with 409 ConflictError (stale_execution)."""
    client = test_env["client"]
    runner = pair_and_start_runner(test_env)

    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-seq-5", "input": {"test": 1}},
        headers={"Idempotency-Key": "run-revoked-grant"},
    )
    run_id = resp.json()["id"]
    task_run_id = resp.json()["task_runs"][0]["id"]

    claim_resp = client.post(
        f"/v1/task-runs/{task_run_id}/claim",
        json={"session_id": runner["session_id"], "lease_seconds": 60},
        headers={"Idempotency-Key": "claim-2", "Authorization": f"Bearer {runner['runner_token']}"},
    )
    attempt_id = claim_resp.json()["attempt_id"]
    token = claim_resp.json()["execution_token"]

    # Revoke grant in DB
    past_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with test_env["database"].transaction() as conn:
        conn.execute("UPDATE execution_grants SET revoked_at=? WHERE attempt_id=?", (past_time, attempt_id))

    complete_resp = client.post(
        f"/v1/attempts/{attempt_id}/complete",
        json={"outcome": "succeeded", "output": {"result": "revoked"}},
        headers={"X-Execution-Token": token, "Idempotency-Key": "comp-revoked"},
    )
    assert complete_resp.status_code == 409
    assert "stale_execution" in complete_resp.json()["detail"]


def test_terminal_state_protection_and_post_mortem_observation(test_env):
    """REL-001: Terminal states cannot be overwritten. Observations can be recorded post-mortem."""
    client = test_env["client"]
    runner = pair_and_start_runner(test_env)

    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-seq-5", "input": {"test": 1}},
        headers={"Idempotency-Key": "run-obs"},
    )
    task_run_id = resp.json()["task_runs"][0]["id"]

    claim_resp = client.post(
        f"/v1/task-runs/{task_run_id}/claim",
        json={"session_id": runner["session_id"], "lease_seconds": 60},
        headers={"Idempotency-Key": "claim-3", "Authorization": f"Bearer {runner['runner_token']}"},
    )
    attempt_id = claim_resp.json()["attempt_id"]
    token = claim_resp.json()["execution_token"]

    # Complete the attempt as failed
    comp_resp = client.post(
        f"/v1/attempts/{attempt_id}/complete",
        json={"outcome": "failed", "error": {"code": "ERR_TEST", "message": "simulated failure"}},
        headers={"X-Execution-Token": token, "Idempotency-Key": "comp-fail"},
    )
    assert comp_resp.status_code == 200

    # Try to overwrite with "succeeded" -> rejected (terminal)
    comp_retry = client.post(
        f"/v1/attempts/{attempt_id}/complete",
        json={"outcome": "succeeded", "output": {"done": True}},
        headers={"X-Execution-Token": token, "Idempotency-Key": "comp-overwrite"},
    )
    assert comp_retry.status_code == 409

    # Record post-mortem observation via POST /v1/attempts/{id}/observations
    obs_resp = client.post(
        f"/v1/attempts/{attempt_id}/observations",
        json={
            "session_id": runner["session_id"],
            "observation_type": "post_mortem_evidence",
            "data": {"exit_code": 1, "stderr": "process crash info"},
        },
        headers={"Idempotency-Key": "obs-1", "Authorization": f"Bearer {runner['runner_token']}"},
    )
    assert obs_resp.status_code == 202
    assert obs_resp.json()["status"] == "accepted"

    # Idempotent observation call
    obs_retry = client.post(
        f"/v1/attempts/{attempt_id}/observations",
        json={
            "session_id": runner["session_id"],
            "observation_type": "post_mortem_evidence",
            "data": {"exit_code": 1, "stderr": "process crash info"},
        },
        headers={"Idempotency-Key": "obs-1", "Authorization": f"Bearer {runner['runner_token']}"},
    )
    assert obs_retry.status_code == 202
    assert obs_retry.json()["status"] == "accepted"


def test_server_restart_preserves_consistent_state(test_env):
    """REL-001: Simulating server restart reloads state from SQLite and maintains durability."""
    client = test_env["client"]
    runner = pair_and_start_runner(test_env)

    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-seq-5", "input": {"test": 1}},
        headers={"Idempotency-Key": "run-restart"},
    )
    run_id = resp.json()["id"]
    task_run_id = resp.json()["task_runs"][0]["id"]

    claim_resp = client.post(
        f"/v1/task-runs/{task_run_id}/claim",
        json={"session_id": runner["session_id"], "lease_seconds": 60},
        headers={"Idempotency-Key": "claim-rst", "Authorization": f"Bearer {runner['runner_token']}"},
    )
    attempt_id = claim_resp.json()["attempt_id"]
    token = claim_resp.json()["execution_token"]

    client.post(
        f"/v1/attempts/{attempt_id}/complete",
        json={"outcome": "succeeded", "output": {"step": 1, "data": "completed before restart"}},
        headers={"X-Execution-Token": token, "Idempotency-Key": "comp-rst"},
    )

    # Simulate restart by instantiating a completely new app/client pointing to the same SQLite db
    new_app = create_app(test_env["settings"])
    new_client = TestClient(new_app)

    # Verify run state persisted across restart
    get_resp = new_client.get(f"/v1/runs/{run_id}")
    assert get_resp.status_code == 200
    run_state = get_resp.json()
    assert run_state["status"] == "running"
    task_map = {t["task_id"]: t for t in run_state["task_runs"]}
    assert task_map["node-1"]["status"] == "succeeded"
    assert task_map["node-2"]["status"] == "queued"


# =============================================================================
# REL-003: Safe Human Continue
# =============================================================================

def test_safe_human_continue_scenario_3_of_5_complete(test_env):
    """
    REL-003 Scenario:
    - 5-node pipeline (node-1 -> node-2 -> node-3 -> node-4 -> node-5).
    - Nodes 1, 2, 3 complete successfully.
    - Node 4 pauses for human review/input (waiting_for_input).
    - Outputs and artifacts from nodes 1, 2, 3 are preserved.
    - Human operator calls POST /v1/runs/{run_id}/continue with approval/input.
    - Node 4 advances, node 5 runs to completion.
    - Prior nodes 1, 2, 3 are NOT re-executed.
    - Run completes as succeeded.
    """
    client = test_env["client"]
    runner = pair_and_start_runner(test_env)

    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-seq-5", "input": {"topic": "Continue Test"}},
        headers={"Idempotency-Key": "run-cont-1"},
    )
    assert resp.status_code == 202
    run_id = resp.json()["id"]

    # Execute Node 1 -> Node 2 -> Node 3 sequentially
    node_outputs = {}
    for node_idx, task_id in enumerate(["node-1", "node-2", "node-3"], start=1):
        run_data = client.get(f"/v1/runs/{run_id}").json()
        task_info = next(t for t in run_data["task_runs"] if t["task_id"] == task_id)
        assert task_info["status"] == "queued"

        claim = client.post(
            f"/v1/task-runs/{task_info['id']}/claim",
            json={"session_id": runner["session_id"], "lease_seconds": 60},
            headers={"Idempotency-Key": f"claim-node-{node_idx}", "Authorization": f"Bearer {runner['runner_token']}"},
        )
        assert claim.status_code == 201
        att_id = claim.json()["attempt_id"]
        tok = claim.json()["execution_token"]

        out = {"step": node_idx, "summary": f"Completed node {node_idx}"}
        node_outputs[task_id] = out

        comp = client.post(
            f"/v1/attempts/{att_id}/complete",
            json={"outcome": "succeeded", "output": out},
            headers={"X-Execution-Token": tok, "Idempotency-Key": f"comp-node-{node_idx}"},
        )
        assert comp.status_code == 200

    # At this point, node-1, node-2, node-3 are succeeded; node-4 is queued
    run_data = client.get(f"/v1/runs/{run_id}").json()
    task_map = {t["task_id"]: t for t in run_data["task_runs"]}
    assert task_map["node-1"]["status"] == "succeeded"
    assert task_map["node-2"]["status"] == "succeeded"
    assert task_map["node-3"]["status"] == "succeeded"
    assert task_map["node-4"]["status"] == "queued"
    assert task_map["node-5"]["status"] == "pending"

    # Simulate node-4 waiting for human input
    run_repo = RunRepository(test_env["database"])
    run_repo.set_task_waiting_for_input(
        task_run_id=task_map["node-4"]["id"],
        waiting_for="human_approval",
        reason="Awaiting editorial approval for Step 4",
    )

    # Verify run displays waiting state
    run_data_waiting = client.get(f"/v1/runs/{run_id}").json()
    assert run_data_waiting["attention_reason"] == "Awaiting editorial approval for Step 4"
    t4 = next(t for t in run_data_waiting["task_runs"] if t["task_id"] == "node-4")
    assert t4["waiting_for"] == "human_approval"

    # Now operator calls POST /v1/runs/{run_id}/continue
    continue_resp = client.post(
        f"/v1/runs/{run_id}/continue",
        json={
            "task_id": "node-4",
            "decision": "proceed",
            "feedback": "Approved by Chief Editor",
            "input": {"editor_notes": "All looks good"},
        },
        headers={"Idempotency-Key": "cont-key-1"},
    )
    assert continue_resp.status_code == 200
    continued_run = continue_resp.json()
    assert continued_run["status"] == "running"

    # Verify nodes 1, 2, 3 outputs are STILL PRESERVED and untouched
    task_map_after = {t["task_id"]: t for t in continued_run["task_runs"]}
    assert task_map_after["node-1"]["status"] == "succeeded"
    assert task_map_after["node-1"]["output"] == node_outputs["node-1"]
    assert task_map_after["node-2"]["status"] == "succeeded"
    assert task_map_after["node-2"]["output"] == node_outputs["node-2"]
    assert task_map_after["node-3"]["status"] == "succeeded"
    assert task_map_after["node-3"]["output"] == node_outputs["node-3"]

    # Verify human_decisions record was created in database
    with test_env["database"].connect() as conn:
        decision_row = conn.execute("SELECT * FROM human_decisions WHERE run_id=?", (run_id,)).fetchone()
        assert decision_row is not None
        assert decision_row["decision"] == "proceed"
        assert decision_row["feedback"] == "Approved by Chief Editor"

    # Node-4 was approved/succeeded, which allowed Node-5 to become queued!
    assert task_map_after["node-4"]["status"] == "succeeded"
    assert task_map_after["node-5"]["status"] == "queued"

    # Now execute Node 5 to complete the run
    claim_5 = client.post(
        f"/v1/task-runs/{task_map_after['node-5']['id']}/claim",
        json={"session_id": runner["session_id"], "lease_seconds": 60},
        headers={"Idempotency-Key": "claim-node-5", "Authorization": f"Bearer {runner['runner_token']}"},
    )
    assert claim_5.status_code == 201
    comp_5 = client.post(
        f"/v1/attempts/{claim_5.json()['attempt_id']}/complete",
        json={"outcome": "succeeded", "output": {"final": "all 5 nodes completed"}},
        headers={"X-Execution-Token": claim_5.json()["execution_token"], "Idempotency-Key": "comp-node-5"},
    )
    assert comp_5.status_code == 200

    # Entire run is now succeeded
    final_run = client.get(f"/v1/runs/{run_id}").json()
    assert final_run["status"] == "succeeded"


def test_idempotent_continue_call(test_env):
    """REL-003: Repeated Continue calls with same Idempotency-Key return identical response without duplicate side effects."""
    client = test_env["client"]
    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-seq-5", "input": {"topic": "Idempotent Continue"}},
        headers={"Idempotency-Key": "run-cont-idem"},
    )
    run_id = resp.json()["id"]
    t1 = resp.json()["task_runs"][0]

    run_repo = RunRepository(test_env["database"])
    run_repo.set_task_waiting_for_input(
        task_run_id=t1["id"],
        waiting_for="human_review",
        reason="Needs manual verification",
    )

    payload = {"task_id": "node-1", "decision": "proceed", "feedback": "First try"}
    headers = {"Idempotency-Key": "same-continue-key"}

    resp1 = client.post(f"/v1/runs/{run_id}/continue", json=payload, headers=headers)
    assert resp1.status_code == 200

    resp2 = client.post(f"/v1/runs/{run_id}/continue", json=payload, headers=headers)
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]

    # Verify only ONE human_decisions record was written
    with test_env["database"].connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM human_decisions WHERE run_id=?", (run_id,)).fetchone()[0]
        assert count == 1


def test_continue_on_terminal_run_rejected(test_env):
    """REL-003: Calling Continue on a terminal run (cancelled/succeeded/failed) returns 409 Conflict."""
    client = test_env["client"]
    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-seq-5", "input": {"test": 1}},
        headers={"Idempotency-Key": "run-term-cancel"},
    )
    run_id = resp.json()["id"]

    # Cancel the run
    cancel_resp = client.post(
        f"/v1/runs/{run_id}/cancel",
        json={"reason": "Operator abort"},
        headers={"Idempotency-Key": "cancel-key"},
    )
    assert cancel_resp.status_code == 202

    # Attempt to continue cancelled run -> 409 Conflict
    cont_resp = client.post(
        f"/v1/runs/{run_id}/continue",
        json={"decision": "proceed"},
        headers={"Idempotency-Key": "cont-cancelled"},
    )
    assert cont_resp.status_code == 409
    assert "run_terminal" in cont_resp.json()["detail"]

"""Integration tests for Run Execution, Claiming CAS, Artifacts, and Worker (RUN-002 to RUN-006)."""

import hashlib
import json
from pathlib import Path
import secrets
import pytest
from fastapi.testclient import TestClient
import httpx

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.runners.repository import RunnerRepository
from agent_cf_server.infrastructure.runs.repository import IdempotencyConflict, RunRepository

from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.execution.journal import ExecutionJournal
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.runtime.base import BaseRuntimeAdapter, RuntimeExecutionResult


@pytest.fixture
def test_env(tmp_path):
    db_path = tmp_path / "test_runs.sqlite3"
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
    processes.create_process(process_id="proc-1", project_id="proj-1", name="Story Generation")

    # Publish ProcessVersion with 2 tasks: task-1 (root) -> task-2 (dependent)
    definition = {
        "definition_format_version": "1",
        "interpreter_version": "dag-v1",
        "tasks": [
            {
                "id": "task-outline",
                "task_key": "outline",
                "runtime": {"adapter": "codex", "model_id": "gpt-5.6-sol"},
            },
            {
                "id": "task-content",
                "task_key": "content",
                "runtime": {"adapter": "codex", "model_id": "gpt-5.6-sol"},
            },
        ],
        "dependencies": [
            {"source_task_id": "task-outline", "target_task_id": "task-content"}
        ],
    }
    processes.store_published(
        workspace_id="ws-1",
        project_id="proj-1",
        process_id="proc-1",
        version_id="ver-story-v1",
        version_number=1,
        definition=definition,
        snapshot_sha256="c" * 64,
    )

    client = TestClient(app)
    return {
        "database": database,
        "settings": settings,
        "client": client,
        "artifacts_dir": artifacts_dir,
    }


def pair_and_start_runner(test_env, name="PC-Local-1"):
    client = test_env["client"]
    # 1. Create pairing code
    resp = client.post(
        "/v1/pairing-codes",
        json={"workspace_id": "ws-1", "name": name, "expires_in_seconds": 300},
    )
    assert resp.status_code == 201
    code = resp.json()["pairing_code"]

    # 2. Pair
    resp = client.post("/v1/runners/pair", json={"pairing_code": code, "client_version": "0.1.0"})
    assert resp.status_code == 201
    runner_id = resp.json()["runner_id"]
    runner_token = resp.json()["runner_token"]

    # 3. Start session
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


def test_run_creation_idempotency_and_initial_queuing(test_env):
    client = test_env["client"]
    key = "idem-run-1"
    payload = {
        "process_version_id": "ver-story-v1",
        "input": {"topic": "Thật tệ khi làm mẹ đơn thân"},
    }

    # 1. First creation
    resp1 = client.post("/v1/runs", json=payload, headers={"Idempotency-Key": key})
    assert resp1.status_code == 202
    run1 = resp1.json()
    assert run1["status"] == "queued"
    assert run1["input"]["topic"] == "Thật tệ khi làm mẹ đơn thân"
    assert len(run1["task_runs"]) == 2

    # Root task (outline) must be queued, dependent task (content) must be pending
    tasks_by_id = {t["task_id"]: t for t in run1["task_runs"]}
    assert tasks_by_id["task-outline"]["status"] == "queued"
    assert tasks_by_id["task-content"]["status"] == "pending"

    # 2. Same idempotency key + same payload -> returns identical run
    resp2 = client.post("/v1/runs", json=payload, headers={"Idempotency-Key": key})
    assert resp2.status_code == 202
    assert resp2.json()["id"] == run1["id"]

    # 3. Same idempotency key + different payload -> 409 conflict
    resp3 = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-story-v1", "input": {"topic": "Khác"}},
        headers={"Idempotency-Key": key},
    )
    assert resp3.status_code == 409


def test_work_polling_and_claim_cas_prevents_duplicate_assignment(test_env):
    client = test_env["client"]
    runner1 = pair_and_start_runner(test_env, "PC-1")
    runner2 = pair_and_start_runner(test_env, "PC-2")

    # Create run
    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-story-v1", "input": {"topic": "Thử nghiệm"}},
        headers={"Idempotency-Key": "run-test-claim"},
    )
    run_id = resp.json()["id"]
    task_runs = resp.json()["task_runs"]
    outline_task = [t for t in task_runs if t["task_id"] == "task-outline"][0]

    # Both runners poll work
    work1 = client.get(
        f"/v1/runners/{runner1['runner_id']}/work",
        params={"session_id": runner1["session_id"]},
        headers={"Authorization": f"Bearer {runner1['runner_token']}"},
    ).json()["items"]
    assert len(work1) == 1
    assert work1[0]["task_run_id"] == outline_task["id"]

    # Runner 1 claims
    claim_resp1 = client.post(
        f"/v1/task-runs/{outline_task['id']}/claim",
        json={"session_id": runner1["session_id"], "lease_seconds": 60},
        headers={
            "Authorization": f"Bearer {runner1['runner_token']}",
            "Idempotency-Key": "claim-key-1",
        },
    )
    assert claim_resp1.status_code == 201
    assignment1 = claim_resp1.json()
    assert assignment1["task_run_id"] == outline_task["id"]
    assert assignment1["generation"] == 1
    assert "execution_token" in assignment1

    # Runner 2 tries to claim same task -> 409 Conflict
    claim_resp2 = client.post(
        f"/v1/task-runs/{outline_task['id']}/claim",
        json={"session_id": runner2["session_id"], "lease_seconds": 60},
        headers={
            "Authorization": f"Bearer {runner2['runner_token']}",
            "Idempotency-Key": "claim-key-2",
        },
    )
    assert claim_resp2.status_code == 409

    # Runner 1 re-sends same claim with same key -> gets identical assignment
    claim_retry = client.post(
        f"/v1/task-runs/{outline_task['id']}/claim",
        json={"session_id": runner1["session_id"], "lease_seconds": 60},
        headers={
            "Authorization": f"Bearer {runner1['runner_token']}",
            "Idempotency-Key": "claim-key-1",
        },
    )
    assert claim_retry.status_code == 201
    assert claim_retry.json()["attempt_id"] == assignment1["attempt_id"]


def test_artifact_registration_upload_and_safe_download(test_env):
    client = test_env["client"]
    runner = pair_and_start_runner(test_env, "PC-Artifact")

    # Create run and claim outline
    run = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-story-v1", "input": {"topic": "Artifact test"}},
        headers={"Idempotency-Key": "run-art-1"},
    ).json()
    task_id = [t for t in run["task_runs"] if t["task_id"] == "task-outline"][0]["id"]
    assign = client.post(
        f"/v1/task-runs/{task_id}/claim",
        json={"session_id": runner["session_id"]},
        headers={
            "Authorization": f"Bearer {runner['runner_token']}",
            "Idempotency-Key": "claim-art-1",
        },
    ).json()

    attempt_id = assign["attempt_id"]
    token = assign["execution_token"]

    # 1. Register artifact
    content = "Nội dung dàn ý: 5 Part đầy đủ tiếng Việt UTF-8".encode("utf-8")
    sha256 = hashlib.sha256(content).hexdigest()
    reg_resp = client.post(
        f"/v1/attempts/{attempt_id}/artifacts",
        json={
            "logical_name": "cot truyen.txt",
            "media_type": "text/plain; charset=utf-8",
            "size_bytes": len(content),
            "sha256": sha256,
        },
        headers={
            "Authorization": f"Bearer {runner['runner_token']}",
            "X-Execution-Token": token,
            "Idempotency-Key": "reg-art-1",
        },
    )
    assert reg_resp.status_code == 201
    artifact_id = reg_resp.json()["id"]

    # 2. Upload content
    up_resp = client.put(
        f"/v1/artifacts/{artifact_id}/content",
        content=content,
        headers={
            "Authorization": f"Bearer {runner['runner_token']}",
            "X-Execution-Token": token,
        },
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["availability"] == "available"

    # 3. Download content
    dl_resp = client.get(f"/v1/artifacts/{artifact_id}/content")
    assert dl_resp.status_code == 200
    assert dl_resp.content == content
    assert dl_resp.text == "Nội dung dàn ý: 5 Part đầy đủ tiếng Việt UTF-8"


def test_dag_progression_and_run_completion(test_env):
    client = test_env["client"]
    runner = pair_and_start_runner(test_env, "PC-DAG")

    run = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-story-v1", "input": {"topic": "DAG test"}},
        headers={"Idempotency-Key": "run-dag-1"},
    ).json()
    run_id = run["id"]
    outline_id = [t for t in run["task_runs"] if t["task_id"] == "task-outline"][0]["id"]
    content_id = [t for t in run["task_runs"] if t["task_id"] == "task-content"][0]["id"]

    # Claim & complete Task 1 (outline)
    assign1 = client.post(
        f"/v1/task-runs/{outline_id}/claim",
        json={"session_id": runner["session_id"]},
        headers={"Authorization": f"Bearer {runner['runner_token']}", "Idempotency-Key": "claim-t1"},
    ).json()

    comp1 = client.post(
        f"/v1/attempts/{assign1['attempt_id']}/complete",
        json={
            "outcome": "succeeded",
            "process_stopped": True,
            "exit_code": 0,
            "output": {"summary": "Outline done"},
        },
        headers={
            "X-Execution-Token": assign1["execution_token"],
            "Idempotency-Key": "comp-t1",
        },
    )
    assert comp1.status_code == 200

    # Verify Task 2 (content) automatically transitioned from pending to queued!
    run_after_t1 = client.get(f"/v1/runs/{run_id}").json()
    t2 = [t for t in run_after_t1["task_runs"] if t["task_id"] == "task-content"][0]
    assert t2["status"] == "queued"

    # Claim & complete Task 2
    assign2 = client.post(
        f"/v1/task-runs/{content_id}/claim",
        json={"session_id": runner["session_id"]},
        headers={"Authorization": f"Bearer {runner['runner_token']}", "Idempotency-Key": "claim-t2"},
    ).json()

    comp2 = client.post(
        f"/v1/attempts/{assign2['attempt_id']}/complete",
        json={
            "outcome": "succeeded",
            "process_stopped": True,
            "exit_code": 0,
            "output": {"article": "Full article done"},
        },
        headers={
            "X-Execution-Token": assign2["execution_token"],
            "Idempotency-Key": "comp-t2",
        },
    )
    assert comp2.status_code == 200

    # Entire ProcessRun must now be succeeded!
    final_run = client.get(f"/v1/runs/{run_id}").json()
    assert final_run["status"] == "succeeded"
    assert final_run["ended_at"] is not None
    assert "task-outline" in final_run["output"]
    assert "task-content" in final_run["output"]


def test_run_cancellation_lifecycle(test_env):
    client = test_env["client"]
    run = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-story-v1", "input": {"topic": "Cancel test"}},
        headers={"Idempotency-Key": "run-cancel-1"},
    ).json()
    run_id = run["id"]

    # Cancel run
    cancel_resp = client.post(
        f"/v1/runs/{run_id}/cancel",
        json={"reason": "Operator requested stop"},
        headers={"Idempotency-Key": "cancel-key-1"},
    )
    assert cancel_resp.status_code == 202
    cancelled_run = cancel_resp.json()
    assert cancelled_run["status"] == "cancelled"
    assert all(t["status"] == "cancelled" for t in cancelled_run["task_runs"])


class MockSkill0CodexAdapter(BaseRuntimeAdapter):
    @property
    def adapter_id(self) -> str:
        return "codex"

    def is_available(self) -> bool:
        return True

    def execute_skill(
        self,
        prompt: str,
        cwd: Path,
        model: str | None = None,
        session_id: str | None = None,
        output_file: Path | None = None,
        timeout_seconds: float = 60.0,
    ) -> RuntimeExecutionResult:
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                f"DÀN Ý CỐT TRUYỆN: {prompt}\n\n"
                "Part 1: Khởi đầu khó khăn của người mẹ đơn thân\n"
                "Part 2: Biến cố việc làm\n"
                "Part 3: Điểm tựa gia đình\n"
                "Part 4: Vượt khó vươn lên\n"
                "Part 5: Thành quả và tương lai",
                encoding="utf-8",
            )
        return RuntimeExecutionResult(
            success=True,
            exit_code=0,
            output_text="Hoàn thành tạo dàn ý 5 Part theo Skill 0",
            session_id="thread-mock-123",
            duration_seconds=1.5,
        )


def test_run006_end_to_end_skill0_execution(test_env, tmp_path, monkeypatch):
    """End-to-end test simulating Skill 0 run through Web/API -> Server -> Worker -> Output."""
    client = test_env["client"]
    runner_data = pair_and_start_runner(test_env, "PC-Skill0")

    # Client-side components
    creds_path = tmp_path / "runner_creds.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_data["runner_id"],
        runner_token=runner_data["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_data["session_id"]

    ws_mgr = WorkspaceManager(tmp_path / "workspace_runs")
    mock_adapter = MockSkill0CodexAdapter()

    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=ws_mgr,
        codex_adapter=mock_adapter,
    )

    # 1. Web/Operator creates Run
    topic = "Thật tệ khi làm mẹ đơn thân"
    create_resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-story-v1", "input": {"topic": topic}},
        headers={"Idempotency-Key": "run-skill0-e2e"},
    )
    assert create_resp.status_code == 202
    run_id = create_resp.json()["id"]

    # Mock httpx in TaskExecutionWorker to talk to testclient
    orig_send = httpx.Client.send
    def mock_httpx_send(self_client, request, **kwargs):
        if isinstance(self_client, TestClient):
            return orig_send(self_client, request, **kwargs)
        method = request.method
        url = request.url.raw_path.decode("utf-8")
        headers = dict(request.headers)
        content = request.content
        resp = client.request(method, url, headers=headers, content=content)
        return httpx.Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
            request=request,
        )

    # Patch httpx.Client.send
    monkeypatch.setattr(httpx.Client, "send", mock_httpx_send)

    # 2. Worker executes Task 1 (outline)
    exec_res1 = worker.poll_and_execute_once()
    assert exec_res1 is not None
    assert exec_res1["outcome"] == "succeeded"
    assert len(exec_res1["artifact_ids"]) == 1

    # 3. Worker executes Task 2 (content)
    exec_res2 = worker.poll_and_execute_once()
    assert exec_res2 is not None
    assert exec_res2["outcome"] == "succeeded"

    # 4. Verify Server state: Run succeeded, artifact accessible, events complete
    run_data = client.get(f"/v1/runs/{run_id}").json()
    assert run_data["status"] == "succeeded"
    assert len(run_data["artifacts"]) >= 1

    art = next((a for a in run_data["artifacts"] if a["logical_name"] == "cot truyen.txt"), None)
    assert art is not None

    # Download artifact and check UTF-8 Vietnamese content
    art_content_resp = client.get(f"/v1/artifacts/{art['id']}/content")
    assert art_content_resp.status_code == 200
    assert "DÀN Ý CỐT TRUYỆN: Thật tệ khi làm mẹ đơn thân" in art_content_resp.text
    assert "Part 1: Khởi đầu khó khăn của người mẹ đơn thân" in art_content_resp.text

    # Verify event audit trail
    events = client.get(f"/v1/runs/{run_id}/events").json()["items"]
    event_types = [e["event_type"] for e in events]
    assert "run_created" in event_types
    assert "task_claimed" in event_types
    assert "task_completed" in event_types
    assert "run_succeeded" in event_types

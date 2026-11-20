"""Integration tests for Robot catalog, versioning, immutability, pinned runner, worker execution, and real statistics (ROB-001)."""

import hashlib
import json
from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient
import httpx

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.robots.repository import RobotRepository
from agent_cf_server.infrastructure.runners.repository import RunnerRepository
from agent_cf_server.infrastructure.runs.repository import ConflictError, RunRepository
from agent_cf_server.infrastructure.settings.repository import InUseError, ResourceConflictError

from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager


@pytest.fixture
def robot_env(tmp_path):
    db_path = tmp_path / "test_robots.sqlite3"
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

    client = TestClient(app)
    return {
        "database": database,
        "settings": settings,
        "client": client,
        "artifacts_dir": artifacts_dir,
        "tmp_path": tmp_path,
    }


def pair_runner(robot_env, runner_name="PC-Pinned"):
    client = robot_env["client"]
    resp = client.post(
        "/v1/pairing-codes",
        json={"workspace_id": "ws-1", "name": runner_name, "expires_in_seconds": 300},
    )
    assert resp.status_code == 201
    code = resp.json()["pairing_code"]

    resp = client.post("/v1/runners/pair", json={"pairing_code": code, "client_version": "0.1.0"})
    assert resp.status_code == 201
    runner_id = resp.json()["runner_id"]
    runner_token = resp.json()["runner_token"]

    resp = client.post(
        f"/v1/runners/{runner_id}/sessions",
        headers={"Authorization": f"Bearer {runner_token}"},
        json={"client_version": "0.1.0"},
    )
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]

    return {
        "runner_id": runner_id,
        "runner_token": runner_token,
        "session_id": session_id,
    }


def test_robot_crud_versioning_and_immutability(robot_env):
    database = robot_env["database"]
    repo = RobotRepository(database)

    # 1. Create robot
    robot = repo.create_robot(name="Media Processor", description="Automated video audio converter")
    assert robot["name"] == "Media Processor"
    assert robot["status"] == "active"
    robot_id = robot["id"]

    # 2. Create draft version v1
    v1 = repo.create_draft_version(
        robot_id=robot_id,
        entrypoint="python ffmpeg_worker.py",
        contract_version="1.0.0",
        input_schema={"type": "object", "properties": {"video_path": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"audio_path": {"type": "string"}}},
    )
    assert v1["version_number"] == 1
    assert v1["status"] == "draft"
    v1_id = v1["id"]

    # 3. Only 1 draft version allowed per robot
    with pytest.raises(ResourceConflictError):
        repo.create_draft_version(robot_id=robot_id, entrypoint="python v2.py")

    # 4. Publish version v1
    published_v1 = repo.publish_version(v1_id)
    assert published_v1["status"] == "published"
    assert published_v1["bundle_sha256"] is not None
    assert published_v1["published_at"] is not None

    # Parent robot auto-sets active_version_id on first published version
    robot_updated = repo.get_robot(robot_id)
    assert robot_updated["active_version_id"] == v1_id

    # 5. Database triggers enforce immutability of published versions
    with database.transaction() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="published_robot_version_immutable"):
            conn.execute("UPDATE robot_versions SET entrypoint = 'malicious.py' WHERE id = ?", (v1_id,))

    with database.transaction() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="published_robot_version_immutable"):
            conn.execute("DELETE FROM robot_versions WHERE id = ?", (v1_id,))

    # 6. Delete robot with published version is protected
    with pytest.raises(InUseError, match="phiên bản v1 được phát hành"):
        repo.delete_robot(robot_id)

    # 7. Archive and Restore
    archived = repo.archive_robot(robot_id)
    assert archived["status"] == "archived"
    restored = repo.restore_robot(robot_id)
    assert restored["status"] == "active"

    # 8. Unused robot with only draft version can be deleted cleanly
    r_temp = repo.create_robot(name="Temp Robot")
    repo.create_draft_version(robot_id=r_temp["id"], entrypoint="python test.py")
    repo.delete_robot(r_temp["id"])
    with pytest.raises(Exception):
        repo.get_robot(r_temp["id"])


def test_robot_api_endpoints(robot_env):
    client = robot_env["client"]

    # 1. Create robot via API
    resp = client.post("/v1/robots", json={"name": "Crawler Bot", "description": "Web scraper"})
    assert resp.status_code == 201
    bot = resp.json()
    bot_id = bot["id"]

    # 2. List robots
    resp = client.get("/v1/robots")
    assert resp.status_code == 200
    assert any(r["id"] == bot_id for r in resp.json())

    # 3. Create draft version
    resp = client.post(
        f"/v1/robots/{bot_id}/versions",
        json={"entrypoint": "python crawler.py", "contract_version": "1.0.0"},
    )
    assert resp.status_code == 201
    ver_id = resp.json()["id"]

    # 4. Publish version
    resp = client.post(f"/v1/robots/{bot_id}/versions/{ver_id}/publish", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    # 5. Check statistics endpoint: new version with 0 runs displays success_rate=null
    resp = client.get(f"/v1/robots/{bot_id}/statistics")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["robot_id"] == bot_id
    assert stats["overall"]["total_runs"] == 0
    assert stats["overall"]["success_rate"] is None
    assert stats["versions"][0]["success_rate"] is None


def test_robot_node_pinned_runner_enforcement(robot_env):
    database = robot_env["database"]
    client = robot_env["client"]

    runner_pinned = pair_runner(robot_env, "PC-Dedicated")
    runner_other = pair_runner(robot_env, "PC-Other")

    # Set up Robot and published version
    robots = RobotRepository(database)
    robot = robots.create_robot(name="Dedicated OCR")
    ver = robots.create_draft_version(robot["id"], entrypoint="python ocr.py")
    robots.publish_version(ver["id"])

    # Create Process with task pinned to runner_pinned["runner_id"]
    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-ocr", project_id="proj-1", name="OCR Flow")

    task_def = {
        "id": "task-ocr-1",
        "task_key": "ocr",
        "name": "OCR Node",
        "kind": "robot",
        "robot_version_id": ver["id"],
        "runner_id": runner_pinned["runner_id"],  # PINNED RUNNER!
        "entrypoint": "python ocr.py",
        "contract_version": "1.0.0",
        "execution_timeout_seconds": 30,
        "queue_timeout_seconds": 60,
        "required_artifacts": [],
        "input_mapping": [],
        "input_schema": {},
        "output_schema": {},
        "agent": {"id": "ag-1", "name": "OCR Agent", "role": "Worker"},
    }
    process_def = {
        "definition_format_version": "1",
        "interpreter_version": "dag-v1",
        "tasks": [task_def],
        "dependencies": [],
    }
    processes.store_published(
        workspace_id="ws-1",
        project_id="proj-1",
        process_id="proc-ocr",
        version_id="ver-ocr-v1",
        version_number=1,
        definition=process_def,
        snapshot_sha256="d" * 64,
    )

    # Start run
    runs_repo = RunRepository(database)
    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-ocr-v1", "input": {"image_path": "scan.png"}},
        headers={"Idempotency-Key": "req-ocr-1"},
    )
    assert resp.status_code == 202
    run_info = resp.json()
    task_run_id = run_info["task_runs"][0]["id"]

    # 1. Runner Other polls work: task must NOT be visible because it is pinned to Runner Dedicated!
    work_other = runs_repo.list_work(runner_other["runner_id"], runner_other["session_id"])
    assert not any(w["task_run_id"] == task_run_id for w in work_other)

    # 2. Runner Other tries to claim the task: must be rejected with ConflictError!
    with pytest.raises(ConflictError, match="pinned to runner"):
        runs_repo.claim_task_run(
            task_run_id=task_run_id,
            runner_id=runner_other["runner_id"],
            session_id=runner_other["session_id"],
            request_key="claim-other-fail",
            request_sha256="f" * 64,
        )

    # 3. Runner Dedicated polls work: task IS visible!
    work_pinned = runs_repo.list_work(runner_pinned["runner_id"], runner_pinned["session_id"])
    assert any(w["task_run_id"] == task_run_id for w in work_pinned)

    # 4. Runner Dedicated claims the task: succeeds!
    assignment = runs_repo.claim_task_run(
        task_run_id=task_run_id,
        runner_id=runner_pinned["runner_id"],
        session_id=runner_pinned["session_id"],
        request_key="claim-pinned-ok",
        request_sha256="0" * 64,
    )
    assert assignment["task_run_id"] == task_run_id
    assert assignment["runner_id"] == runner_pinned["runner_id"]


def test_robot_worker_execution_and_statistics(robot_env, monkeypatch):
    database = robot_env["database"]
    client = robot_env["client"]
    tmp_path = robot_env["tmp_path"]

    runner_info = pair_runner(robot_env, "PC-Robot-Exec")

    # Set up Robot
    robots = RobotRepository(database)
    robot = robots.create_robot(name="Script Runner Bot")
    # Entrypoint creates an output artifact in artifacts/output.txt and outputs JSON
    script_code = (
        "import os, json\n"
        "os.makedirs('artifacts', exist_ok=True)\n"
        "with open('artifacts/robot_result.txt', 'w', encoding='utf-8') as f:\n"
        "    f.write('Robot Execution Success Content')\n"
        "with open('output.json', 'w', encoding='utf-8') as f:\n"
        "    json.dump({'status': 'ok', 'score': 98}, f)\n"
    )
    script_file = tmp_path / "robot_task.py"
    script_file.write_text(script_code, encoding="utf-8")

    ver = robots.create_draft_version(robot["id"], entrypoint=f"python {script_file.as_posix()}")
    robots.publish_version(ver["id"])
    ver_id = ver["id"]

    # Set up Process
    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-rob-test", project_id="proj-1", name="Robot Run Process")
    task_def = {
        "id": "task-rob-node-1",
        "task_key": "robot_step",
        "name": "Robot Step",
        "kind": "robot",
        "robot_version_id": ver_id,
        "runner_id": runner_info["runner_id"],
        "entrypoint": f"python {script_file.as_posix()}",
        "contract_version": "1.0.0",
        "execution_timeout_seconds": 20,
        "queue_timeout_seconds": 60,
        "required_artifacts": [],
        "input_mapping": [],
        "input_schema": {},
        "output_schema": {},
        "agent": {"id": "ag-1", "name": "Bot Agent", "role": "Executor"},
    }
    processes.store_published(
        workspace_id="ws-1",
        project_id="proj-1",
        process_id="proc-rob-test",
        version_id="ver-rob-p1",
        version_number=1,
        definition={
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "tasks": [task_def],
            "dependencies": [],
        },
        snapshot_sha256="1" * 64,
    )

    # Start run 1
    runs_repo = RunRepository(database)
    resp1 = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-rob-p1", "input": {"seed": 42}},
        headers={"Idempotency-Key": "run-rob-1"},
    )
    assert resp1.status_code == 202
    run_1 = resp1.json()

    # Set up client worker
    creds_path = tmp_path / "credentials.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_info["runner_id"],
        runner_token=runner_info["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_info["session_id"]
    workspace_mgr = WorkspaceManager(tmp_path / "workspaces")

    # Wire httpx.Client calls to TestClient
    orig_send = httpx.Client.send

    def mock_httpx_send(self_client, request, **kwargs):
        if isinstance(self_client, TestClient):
            return orig_send(self_client, request, **kwargs)
        method = request.method
        url_path = request.url.raw_path.decode("utf-8")
        headers = dict(request.headers)
        content = request.content
        resp = client.request(method, url_path, headers=headers, content=content)
        return httpx.Response(
            status_code=resp.status_code,
            headers=resp.headers,
            content=resp.content,
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "send", mock_httpx_send)

    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=workspace_mgr,
    )

    # Execute run 1 via worker
    exec_res_1 = worker.poll_and_execute_once()
    assert exec_res_1 is not None
    assert exec_res_1["outcome"] == "succeeded"
    assert len(exec_res_1["artifact_ids"]) == 1

    # Verify run 1 settled to succeeded
    run_1_data = runs_repo.get(run_1["id"])
    assert run_1_data["status"] == "succeeded"

    # Verify uploaded artifact content
    art_id = exec_res_1["artifact_ids"][0]
    art_content_resp = client.get(f"/v1/artifacts/{art_id}/content")
    assert art_content_resp.status_code == 200
    assert art_content_resp.text == "Robot Execution Success Content"

    # Verify statistics after 1 successful run: 100.0%
    stats_1 = robots.get_robot_statistics(robot["id"])
    assert stats_1["overall"]["total_runs"] == 1
    assert stats_1["overall"]["succeeded_runs"] == 1
    assert stats_1["overall"]["failed_runs"] == 0
    assert stats_1["overall"]["success_rate"] == 100.0

    # Start run 2: failure test
    # Create failing script
    fail_script = tmp_path / "failing_robot.py"
    fail_script.write_text("import sys; sys.stderr.write('fatal crash'); sys.exit(2)", encoding="utf-8")

    task_def_fail = dict(task_def)
    task_def_fail["entrypoint"] = f"python {fail_script.as_posix()}"
    processes.store_published(
        workspace_id="ws-1",
        project_id="proj-1",
        process_id="proc-rob-test",
        version_id="ver-rob-p2",
        version_number=2,
        definition={
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "tasks": [task_def_fail],
            "dependencies": [],
        },
        snapshot_sha256="3" * 64,
    )

    resp2 = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-rob-p2", "input": {"seed": 43}},
        headers={"Idempotency-Key": "run-rob-2"},
    )
    assert resp2.status_code == 202
    run_2 = resp2.json()

    # Worker executes failing run 2
    exec_res_2 = worker.poll_and_execute_once()
    assert exec_res_2 is not None
    assert exec_res_2["outcome"] == "failed"

    # Verify statistics after 1 success and 1 fail: exactly 50.0%
    stats_2 = robots.get_robot_statistics(robot["id"])
    assert stats_2["overall"]["total_runs"] == 2
    assert stats_2["overall"]["succeeded_runs"] == 1
    assert stats_2["overall"]["failed_runs"] == 1
    assert stats_2["overall"]["success_rate"] == 50.0
    # Version 1 stats
    v1_stat = next(v for v in stats_2["versions"] if v["robot_version_id"] == ver_id)
    assert v1_stat["total_runs"] == 2
    assert v1_stat["success_rate"] == 50.0

"""Comprehensive End-to-End integration tests for dynamic heterogeneous Processes:
Agent + Robot + Review pipelines, dynamic Skill configuration, cascading failure,
timeout, recovery reconciliation, human continue, and permission enforcement (Instruction 14).
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
import time
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
import httpx

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.agents.repository import AgentRepository
from agent_cf_server.infrastructure.audit.repository import AuditRepository
from agent_cf_server.infrastructure.overview.repository import OverviewRepository
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.robots.repository import RobotRepository
from agent_cf_server.infrastructure.runners.repository import (
    AuthenticationError as RunnerAuthError,
    RunnerRepository,
    SessionInvalidError,
)
from agent_cf_server.infrastructure.runs.repository import (
    AuthenticationError as RunAuthError,
    ConflictError,
    RunRepository,
)
from agent_cf_server.infrastructure.settings.repository import SettingsRepository
from agent_cf_server.infrastructure.skills.repository import SkillRepository

from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.runtime.base import BaseRuntimeAdapter, RuntimeExecutionResult


class MockDynamicPipelineAdapter(BaseRuntimeAdapter):
    """Mock adapter supporting both Agent creation and Review stages."""

    def __init__(self, adapter_id: str = "antigravity", fail_task_keys: list[str] | None = None) -> None:
        self._adapter_id = adapter_id
        self.fail_task_keys = fail_task_keys or []
        self.executed_calls: list[dict] = []

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

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
        skill_name: str | None = None,
        **kwargs,
    ) -> RuntimeExecutionResult:
        self.executed_calls.append({
            "prompt": prompt,
            "cwd": str(cwd),
            "model": model,
            "output_file": str(output_file) if output_file else None,
            "skill_name": skill_name,
        })

        out_name = output_file.name if output_file else ""
        prompt_str = str(prompt)

        # Check simulated failure
        for k in self.fail_task_keys:
            if k == "*" or k in prompt_str.lower() or k in out_name.lower():
                return RuntimeExecutionResult(
                    success=False,
                    exit_code=1,
                    output_text="Simulated adapter failure",
                    error_message="Runtime adapter failed on task execution",
                )

        if "review" in out_name.lower() or "review" in prompt_str.lower():
            text = (
                "BÁO CÁO REVIEW TỰ ĐỘNG CHO PIPELINE:\n"
                "- Kiểm tra tiêu chí chất lượng: ĐẠT\n"
                "- Thuật ngữ nghiệp vụ: Hợp lệ\n"
                "- Kết quả tổng hợp: Phê duyệt (Approved)\n"
            )
        elif "cot truyen" in out_name.lower() or "analysis" in prompt_str.lower() or "outline" in prompt_str.lower():
            text = (
                "PHÂN TÍCH VÀ CỐT TRUYỆN MỤC TIÊU:\n"
                "Chủ đề: Hệ thống tự động hóa nội dung đa kênh\n"
                "Bước 1: Thu thập thông tin và cấu hình tham số\n"
                "Bước 2: Xử lý dữ liệu định dạng qua robot chuyên dụng\n"
                "Bước 3: Đánh giá chất lượng và xuất bản\n"
            )
        else:
            text = f"Kết quả thực thi Agent với skill '{skill_name or 'generic'}': {prompt_str[:80]}"

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(text, encoding="utf-8")

        return RuntimeExecutionResult(success=True, exit_code=0, output_text=text)


@pytest.fixture
def e2e_env(tmp_path):
    db_path = tmp_path / "e2e_agentcf.sqlite3"
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
    projects.create_workspace(workspace_id="ws-e2e", name="E2E Enterprise Workspace")
    projects.create_project(project_id="proj-e2e", workspace_id="ws-e2e", name="Automated Media Corp")

    client = TestClient(app)
    return {
        "database": database,
        "settings": settings,
        "client": client,
        "artifacts_dir": artifacts_dir,
        "tmp_path": tmp_path,
    }


def pair_runner(e2e_env, name="PC-Worker-Alpha", workspace_id="ws-e2e"):
    client = e2e_env["client"]
    resp = client.post(
        "/v1/pairing-codes",
        json={"workspace_id": workspace_id, "name": name, "expires_in_seconds": 300},
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
        json={"client_version": "0.1.0", "capabilities": ["antigravity", "codex", "python"]},
    )
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]
    return {
        "runner_id": runner_id,
        "runner_token": runner_token,
        "session_id": session_id,
    }


def patch_worker_httpx(monkeypatch, client):
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

    monkeypatch.setattr(httpx.Client, "send", mock_httpx_send)


# =============================================================================
# 1. End-to-End Heterogeneous Dynamic DAG (Agent -> Robot -> Review)
# =============================================================================

def test_e2e_heterogeneous_dag_agent_robot_review(e2e_env, tmp_path, monkeypatch):
    """Verify execution of a heterogeneous 3-task DAG:
    1. Agent Node (Antigravity): produces analysis outline artifact.
    2. Robot Node (Python script): reads upstream artifact, transforms data, writes report artifact and JSON.
    3. Review Agent Node (Codex): reviews pipeline output and finalizes run.
    """
    database = e2e_env["database"]
    client = e2e_env["client"]
    runner_data = pair_runner(e2e_env, "PC-Hetero-Exec")

    # 1. Create a Robot and publish its version
    robots = RobotRepository(database)
    robot = robots.create_robot(name="Data Processing Robot", description="Automated data transformer")
    script_content = (
        "import os, json\n"
        "os.makedirs('artifacts', exist_ok=True)\n"
        "# Read input.json if available\n"
        "input_val = {}\n"
        "if os.path.exists('input.json'):\n"
        "    with open('input.json', 'r', encoding='utf-8') as f:\n"
        "        input_val = json.load(f)\n"
        "# Generate robot report artifact\n"
        "with open('artifacts/robot_report.txt', 'w', encoding='utf-8') as f:\n"
        "    f.write('Robot Processed Report: Transformed 100 records successfully')\n"
        "with open('output.json', 'w', encoding='utf-8') as f:\n"
        "    json.dump({'records_processed': 100, 'quality_score': 99, 'input_received': input_val}, f)\n"
    )
    script_path = tmp_path / "robot_proc.py"
    script_path.write_text(script_content, encoding="utf-8")

    r_ver = robots.create_draft_version(robot["id"], entrypoint=f"python {script_path.as_posix()}")
    robots.publish_version(r_ver["id"])

    # 2. Build and publish dynamic Process DAG: task-agent-1 -> task-robot-2 -> task-review-3
    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-hetero", project_id="proj-e2e", name="Multi-Agent-Robot Pipeline")

    tasks_def = [
        {
            "id": "task-agent-1",
            "task_key": "outline",
            "name": "Market Researcher Agent",
            "kind": "agent",
            "runtime": {"adapter": "antigravity", "model_id": "gemini-3.1-pro"},
        },
        {
            "id": "task-robot-2",
            "task_key": "data_transform",
            "name": "Automated Transformer Robot",
            "kind": "robot",
            "robot_version_id": r_ver["id"],
            "runner_id": runner_data["runner_id"],
            "entrypoint": f"python {script_path.as_posix()}",
            "contract_version": "1.0.0",
            "execution_timeout_seconds": 25,
            "queue_timeout_seconds": 60,
            "required_artifacts": [],
            "input_mapping": [],
            "input_schema": {},
            "output_schema": {},
        },
        {
            "id": "task-review-3",
            "task_key": "review_validation",
            "name": "Quality Reviewer Agent",
            "kind": "agent",
            "runtime": {"adapter": "codex", "model_id": "gpt-5.6-sol"},
        },
    ]
    deps_def = [
        {"source_task_id": "task-agent-1", "target_task_id": "task-robot-2"},
        {"source_task_id": "task-robot-2", "target_task_id": "task-review-3"},
    ]

    processes.store_published(
        workspace_id="ws-e2e",
        project_id="proj-e2e",
        process_id="proc-hetero",
        version_id="ver-hetero-v1",
        version_number=1,
        definition={
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "tasks": tasks_def,
            "dependencies": deps_def,
        },
        snapshot_sha256=hashlib.sha256(b"proc-hetero").hexdigest(),
    )

    # 3. Start ProcessRun
    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-hetero-v1", "input": {"project_goal": "Publish AI Report"}},
        headers={"Idempotency-Key": "run-e2e-hetero-1"},
    )
    assert resp.status_code == 202
    run_id = resp.json()["id"]

    # 4. Set up Worker with mock adapters
    creds_path = tmp_path / "worker_creds.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_data["runner_id"],
        runner_token=runner_data["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_data["session_id"]
    ws_mgr = WorkspaceManager(tmp_path / "ws_hetero")

    mock_agy = MockDynamicPipelineAdapter("antigravity")
    mock_codex = MockDynamicPipelineAdapter("codex")

    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=ws_mgr,
        codex_adapter=mock_codex,
        antigravity_adapter=mock_agy,
    )
    patch_worker_httpx(monkeypatch, client)

    # 5. Execute Step 1: Agent Task (Antigravity)
    step1 = worker.poll_and_execute_once()
    assert step1 is not None
    assert step1["outcome"] == "succeeded"
    assert len(step1["artifact_ids"]) >= 1

    # Verify Task 2 is now queued
    run_state = client.get(f"/v1/runs/{run_id}").json()
    t2_state = next(t for t in run_state["task_runs"] if t["task_id"] == "task-robot-2")
    assert t2_state["status"] == "queued"

    # 6. Execute Step 2: Robot Task
    step2 = worker.poll_and_execute_once()
    assert step2 is not None
    assert step2["outcome"] == "succeeded"
    assert len(step2["artifact_ids"]) >= 1

    # Verify Task 2 output saved on server
    run_state = client.get(f"/v1/runs/{run_id}").json()
    t2_state = next(t for t in run_state["task_runs"] if t["task_id"] == "task-robot-2")
    assert t2_state["output"]["records_processed"] == 100
    assert t2_state["status"] == "succeeded"

    # Verify Task 3 is now queued
    run_state = client.get(f"/v1/runs/{run_id}").json()
    t3_state = next(t for t in run_state["task_runs"] if t["task_id"] == "task-review-3")
    assert t3_state["status"] == "queued"

    # 7. Execute Step 3: Review Agent Task
    step3 = worker.poll_and_execute_once()
    assert step3 is not None
    assert step3["outcome"] == "succeeded"

    # 8. Verify terminal Run state
    final_run = client.get(f"/v1/runs/{run_id}").json()
    assert final_run["status"] == "succeeded"
    assert final_run["ended_at"] is not None
    for tr in final_run["task_runs"]:
        assert tr["status"] == "succeeded"

    # Verify audit trail contains complete end-to-end chain
    audit_repo = AuditRepository(database)
    events = audit_repo.get_run_audit_trail(run_id)
    event_types = [e["event_type"] for e in events]
    assert "run_created" in event_types
    assert "task_claimed" in event_types
    assert "task_completed" in event_types
    assert "run_succeeded" in event_types


# =============================================================================
# 2. Dynamic Skill Addition via Configuration & Execution
# =============================================================================

def test_e2e_dynamically_configured_skill_execution(e2e_env, tmp_path, monkeypatch):
    """Verify adding a new Skill purely via configuration/SkillRepository,
    binding it to an Agent, and executing in a new dynamic Process without code changes.
    """
    database = e2e_env["database"]
    client = e2e_env["client"]
    runner_data = pair_runner(e2e_env, "PC-Dynamic-Skill")

    # 1. Dynamically configure Provider, Model, and Role in Settings
    settings_repo = SettingsRepository(database)
    provider = settings_repo.create_provider(
        provider_id="prov-google",
        name="Google AI",
        api_format="google",
        base_url="https://generativelanguage.googleapis.com",
    )
    model = settings_repo.create_model(
        model_id="gemini-3.1-pro",
        provider_id=provider["id"],
        name="Gemini 3.1 Pro",
        model_identifier="gemini-3.1-pro",
    )
    role = settings_repo.create_role(
        role_id="role-analyst",
        name="SEO Analyst",
        description="Search engine optimization role",
    )

    # 2. Dynamically configure Tool and Skill
    skills_repo = SkillRepository(database)
    tool = skills_repo.create_tool(
        tool_id="tool-scraper",
        name="web_scraping_engine",
        description="Scrapes targeted competitive URLs",
        tool_type="api",
    )
    skill = skills_repo.create_skill(
        skill_id="skill-seo",
        name="SEO Keyword Optimization",
        description="Analyzes ranking keywords and applies dynamic metadata",
    )
    s_ver = skills_repo.create_draft_version(
        version_id="ver-seo-skill-1",
        skill_id=skill["id"],
        instructions="# SEO Optimization Guidelines\nEnsure keyword density between 1-3%.",
        output_standards="# Output Schema\nProduce seo_report.txt with primary and secondary keywords.",
        tool_ids=[tool["id"]],
    )
    skills_repo.publish_version(s_ver["id"])

    # 3. Dynamically configure Agent with allowed tools and assigned skill
    agents_repo = AgentRepository(database)
    agent = agents_repo.create_agent(
        agent_id="agent-seo",
        name="SEO Specialist Agent",
        role_id=role["id"],
        model_id=model["id"],
        instructions="Focus on long-tail keywords in Vietnamese e-commerce.",
        skill_ids=[skill["id"]],
        allowed_tool_ids=[tool["id"]],
    )
    assert agent["status"] == "active"

    # 3. Create Process with this dynamically configured Skill
    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-seo", project_id="proj-e2e", name="SEO Pipeline")
    processes.store_published(
        workspace_id="ws-e2e",
        project_id="proj-e2e",
        process_id="proc-seo",
        version_id="ver-seo-v1",
        version_number=1,
        definition={
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "tasks": [
                {
                    "id": "task-seo-node",
                    "task_key": "seo_step",
                    "name": "SEO Task",
                    "kind": "agent",
                    "skill_id": skill["id"],
                    "agent": {"id": agent["id"], "name": agent["name"]},
                    "runtime": {"adapter": "antigravity", "model_id": "gemini-3.1-pro"},
                }
            ],
            "dependencies": [],
        },
        snapshot_sha256=hashlib.sha256(b"proc-seo").hexdigest(),
    )

    # 4. Start Run
    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-seo-v1", "input": {"keyword_target": "mua nha ha noi"}},
        headers={"Idempotency-Key": "run-dynamic-skill-1"},
    )
    assert resp.status_code == 202
    run_id = resp.json()["id"]

    # 5. Worker executes with mock adapter
    creds_path = tmp_path / "creds_seo.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_data["runner_id"],
        runner_token=runner_data["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_data["session_id"]
    ws_mgr = WorkspaceManager(tmp_path / "ws_seo")

    mock_agy = MockDynamicPipelineAdapter("antigravity")
    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=ws_mgr,
        antigravity_adapter=mock_agy,
    )
    patch_worker_httpx(monkeypatch, client)

    res = worker.poll_and_execute_once()
    assert res is not None
    assert res["outcome"] == "succeeded"

    final_run = client.get(f"/v1/runs/{run_id}").json()
    assert final_run["status"] == "succeeded"


# =============================================================================
# 3. Cascading Failure & Overview Alert Box
# =============================================================================

def test_e2e_upstream_failure_cascade_and_overview_alert(e2e_env, tmp_path, monkeypatch):
    """Verify that when an upstream task fails:
    1. Direct and indirect downstream tasks are immediately skipped.
    2. ProcessRun terminates with status 'failed'.
    3. The failed run creates an unhandled red alert on Overview.
    4. Acknowledging the error clears the alert without modifying run history.
    """
    database = e2e_env["database"]
    client = e2e_env["client"]
    runner_data = pair_runner(e2e_env, "PC-Fail-Cascade")

    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-fail-demo", project_id="proj-e2e", name="Failure Cascade Process")

    # Task 1 (fails) -> Task 2 (dependent, should be skipped) -> Task 3 (should be skipped)
    tasks_def = [
        {
            "id": "t-fail-1",
            "task_key": "step_fail",
            "name": "Failing Step",
            "kind": "agent",
            "runtime": {"adapter": "antigravity", "model_id": "gemini-3.1-pro"},
        },
        {
            "id": "t-downstream-2",
            "task_key": "step_downstream_2",
            "name": "Dependent Step 2",
            "kind": "agent",
            "runtime": {"adapter": "antigravity", "model_id": "gemini-3.1-pro"},
        },
        {
            "id": "t-downstream-3",
            "task_key": "step_downstream_3",
            "name": "Dependent Step 3",
            "kind": "agent",
            "runtime": {"adapter": "antigravity", "model_id": "gemini-3.1-pro"},
        },
    ]
    deps_def = [
        {"source_task_id": "t-fail-1", "target_task_id": "t-downstream-2"},
        {"source_task_id": "t-downstream-2", "target_task_id": "t-downstream-3"},
    ]
    processes.store_published(
        workspace_id="ws-e2e",
        project_id="proj-e2e",
        process_id="proc-fail-demo",
        version_id="ver-fail-v1",
        version_number=1,
        definition={
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "tasks": tasks_def,
            "dependencies": deps_def,
        },
        snapshot_sha256=hashlib.sha256(b"proc-fail").hexdigest(),
    )

    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-fail-v1", "input": {"test": "cascade"}},
        headers={"Idempotency-Key": "run-fail-cascade-1"},
    )
    assert resp.status_code == 202
    run_id = resp.json()["id"]

    creds_path = tmp_path / "creds_fail.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_data["runner_id"],
        runner_token=runner_data["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_data["session_id"]
    ws_mgr = WorkspaceManager(tmp_path / "ws_fail")

    # Configured to fail
    mock_agy = MockDynamicPipelineAdapter("antigravity", fail_task_keys=["*"])
    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=ws_mgr,
        antigravity_adapter=mock_agy,
    )
    patch_worker_httpx(monkeypatch, client)

    # Step 1 executes and fails
    res1 = worker.poll_and_execute_once()
    assert res1 is not None
    assert res1["outcome"] == "failed"

    # Verify run state: t-fail-1 is 'failed', downstream are 'skipped', run is 'failed'
    run_data = client.get(f"/v1/runs/{run_id}").json()
    assert run_data["status"] == "failed"
    task_map = {t["task_id"]: t["status"] for t in run_data["task_runs"]}
    assert task_map["t-fail-1"] == "failed"
    assert task_map["t-downstream-2"] == "skipped"
    assert task_map["t-downstream-3"] == "skipped"

    # Verify Overview unhandled errors shows this run
    ovw_repo = OverviewRepository(database)
    summary = ovw_repo.get_overview_summary()
    assert any(e["run_id"] == run_id for e in summary["unresolved_errors"])

    # Operator acknowledges the error
    ack_res = ovw_repo.acknowledge_error(run_id=run_id, acknowledged_by="admin_op")
    assert ack_res["status"] == "acknowledged"

    # Error is no longer in unhandled alerts
    summary_after = ovw_repo.get_overview_summary()
    assert not any(e["run_id"] == run_id for e in summary_after["unresolved_errors"])

    # But run status remains 'failed' (history integrity preserved)
    run_data_after = client.get(f"/v1/runs/{run_id}").json()
    assert run_data_after["status"] == "failed"


# =============================================================================
# 4. Task Timeout & Context Error Recording
# =============================================================================

def test_e2e_robot_task_timeout_and_error_context(e2e_env, tmp_path, monkeypatch):
    """Verify robot task exceeding execution_timeout_seconds is terminated,
    attempt marked failed with code 'timeout', and run marked failed.
    """
    database = e2e_env["database"]
    client = e2e_env["client"]
    runner_data = pair_runner(e2e_env, "PC-Timeout-Exec")

    robots = RobotRepository(database)
    robot = robots.create_robot(name="Hanging Robot")
    # Script that sleeps for 10 seconds
    hanging_script = (
        "import time\n"
        "time.sleep(10)\n"
    )
    script_file = tmp_path / "hanging.py"
    script_file.write_text(hanging_script, encoding="utf-8")

    ver = robots.create_draft_version(robot["id"], entrypoint=f"python {script_file.as_posix()}")
    robots.publish_version(ver["id"])

    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-timeout", project_id="proj-e2e", name="Timeout Process")
    processes.store_published(
        workspace_id="ws-e2e",
        project_id="proj-e2e",
        process_id="proc-timeout",
        version_id="ver-to-v1",
        version_number=1,
        definition={
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "tasks": [
                {
                    "id": "t-hang",
                    "task_key": "hanging_step",
                    "kind": "robot",
                    "robot_version_id": ver["id"],
                    "entrypoint": f"python {script_file.as_posix()}",
                    "contract_version": "1.0.0",
                    "execution_timeout_seconds": 1,  # Short timeout of 1 second!
                    "queue_timeout_seconds": 30,
                    "required_artifacts": [],
                    "input_mapping": [],
                    "input_schema": {},
                    "output_schema": {},
                }
            ],
            "dependencies": [],
        },
        snapshot_sha256=hashlib.sha256(b"proc-to").hexdigest(),
    )

    resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-to-v1", "input": {}},
        headers={"Idempotency-Key": "run-to-1"},
    )
    assert resp.status_code == 202
    run_id = resp.json()["id"]

    creds_path = tmp_path / "creds_to.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_data["runner_id"],
        runner_token=runner_data["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_data["session_id"]
    ws_mgr = WorkspaceManager(tmp_path / "ws_to")

    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=ws_mgr,
    )
    patch_worker_httpx(monkeypatch, client)

    res = worker.poll_and_execute_once()
    assert res is not None
    assert res["outcome"] == "failed"

    run_data = client.get(f"/v1/runs/{run_id}").json()
    assert run_data["status"] == "failed"
    task_err = run_data["task_runs"][0]["error"]
    assert task_err["code"] == "timeout"
    assert "timed out after 1" in task_err["message"]


# =============================================================================
# 5. Stale Lease Reconciliation & Reclaiming
# =============================================================================

def test_e2e_reconciliation_of_interrupted_attempt(e2e_env):
    """Verify that when a runner claims a task and then crashes/stops sending heartbeats:
    1. Stale attempt lease expires.
    2. Reconciliation detects stale claim and sets run to 'reconciling'.
    """
    database = e2e_env["database"]
    runner_repo = RunnerRepository(database)
    run_repo = RunRepository(database)

    runner_data = pair_runner(e2e_env, "PC-Crash-Test")

    # Single-task process
    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-reconcile", project_id="proj-e2e", name="Reconciliation Process")
    processes.store_published(
        workspace_id="ws-e2e",
        project_id="proj-e2e",
        process_id="proc-reconcile",
        version_id="ver-rec-v1",
        version_number=1,
        definition={
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "tasks": [
                {
                    "id": "t-rec-1",
                    "task_key": "step_rec",
                    "kind": "agent",
                    "runtime": {"adapter": "antigravity", "model_id": "gemini-3.1-pro"},
                }
            ],
            "dependencies": [],
        },
        snapshot_sha256=hashlib.sha256(b"proc-rec").hexdigest(),
    )

    created = run_repo.create_from_version(
        version_id="ver-rec-v1",
        principal_id="user-rec",
        request_key="req-rec-run",
        request_sha256="sha-rec-run",
    )
    run_id = created["run_id"]

    work = run_repo.list_work(runner_data["runner_id"], runner_data["session_id"])
    assert len(work) == 1
    task_run_id = work[0]["task_run_id"]

    # Claim task with short lease of 1 second
    claimed = run_repo.claim_task_run(
        task_run_id=task_run_id,
        runner_id=runner_data["runner_id"],
        session_id=runner_data["session_id"],
        request_key="req-rec-claim",
        request_sha256="sha-rec-claim",
        lease_seconds=1,
    )
    attempt_id = claimed["attempt_id"]

    # Expire the lease in database
    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
    with database.transaction() as conn:
        conn.execute("UPDATE execution_grants SET expires_at=? WHERE attempt_id=?", (past, attempt_id))

    # Runner attempts to complete with expired lease -> rejected with ConflictError
    with pytest.raises(ConflictError, match="stale_execution: lease has expired"):
        run_repo.complete_attempt(
            attempt_id=attempt_id,
            execution_token=claimed["execution_token"],
            outcome="succeeded",
            process_stopped=True,
            exit_code=0,
            output={"res": "ok"},
            error=None,
            artifact_ids=[],
            process_evidence=None,
            request_key="req-rec-complete",
            request_sha256="sha-rec-complete",
        )

    # Reconcile marks run as reconciling
    run_state = run_repo.get(run_id)
    rec_res = run_repo.mark_reconciling(
        run_id=run_id,
        expected_revision=run_state["revision"],
        command_id="cmd-rec-1",
        request_sha256="sha-cmd-rec-1",
        reason="Runner heartbeat lost during attempt",
    )
    assert rec_res["run_id"] == run_id

    run_state_after = run_repo.get(run_id)
    assert run_state_after["status"] == "reconciling"


# =============================================================================
# 6. Human-in-the-Loop Continue
# =============================================================================

def test_e2e_human_intervention_wait_and_continue(e2e_env):
    """Verify human continue flow (REL-003):
    1. Run pauses and waits for user.
    2. Operator issues continue_run with feedback.
    3. Target task run restarts while completed upstream tasks are preserved.
    """
    database = e2e_env["database"]
    runner_repo = RunnerRepository(database)
    run_repo = RunRepository(database)
    client = e2e_env["client"]
    runner_data = pair_runner(e2e_env, "PC-Human-Loop")

    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-human", project_id="proj-e2e", name="Human Review Process")
    processes.store_published(
        workspace_id="ws-e2e",
        project_id="proj-e2e",
        process_id="proc-human",
        version_id="ver-human-v1",
        version_number=1,
        definition={
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "tasks": [
                {
                    "id": "t-human-1",
                    "task_key": "step_human",
                    "kind": "agent",
                    "runtime": {"adapter": "antigravity", "model_id": "gemini-3.1-pro"},
                }
            ],
            "dependencies": [],
        },
        snapshot_sha256=hashlib.sha256(b"proc-human").hexdigest(),
    )

    created = run_repo.create_from_version(
        version_id="ver-human-v1",
        principal_id="user-op",
        request_key="req-human-run",
        request_sha256="sha-human-run",
    )
    run_id = created["run_id"]

    # Mark task as waiting for human input
    run_info = run_repo.get(run_id)
    t_id = run_info["task_runs"][0]["id"]
    run_repo.set_task_waiting_for_input(
        task_run_id=t_id,
        waiting_for="human_approval",
        reason="Waiting for human review",
    )

    # Continue run with approved decision via API
    cont_resp = client.post(
        f"/v1/runs/{run_id}/continue",
        json={
            "task_id": "t-human-1",
            "decision": "approved",
            "feedback": "Verified content, proceed to production output",
            "input": {"editor": "supervisor_mary"},
        },
        headers={"Idempotency-Key": "req-human-cont-1"},
    )
    assert cont_resp.status_code == 200
    continued = cont_resp.json()
    assert continued["status"] == "running"

    # Audit trail verifies human decision is recorded
    audit_repo = AuditRepository(database)
    events = audit_repo.get_run_audit_trail(run_id)
    cont_event = next(e for e in events if e["event_type"] == "run_continued")
    assert cont_event["actor_id"] == "operator"
    assert cont_event["data"]["decision"] == "approved"

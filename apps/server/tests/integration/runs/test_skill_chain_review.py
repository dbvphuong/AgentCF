"""Integration tests for Review Criteria, Agent Decision Loop, Checkpoints, and Skill 0->1->2 Pipeline (AGN-001, AGN-002, RUN-007)."""

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

from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.runtime.base import BaseRuntimeAdapter, RuntimeExecutionResult
from agent_cf_client.runtime.review_search import ReviewSearchCapability


@pytest.fixture
def skill_chain_env(tmp_path):
    db_path = tmp_path / "skill_chain.sqlite3"
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
    from agent_cf_server.infrastructure.skills.repository import SkillRepository
    for skill_id in ("0.tao_cot_truyen", "1.tao_noi_dung", "2.review_noi_dung"):
        SkillRepository(database).create_skill(skill_id, skill_id, is_global=True)

    projects = ProjectRepository(database)
    projects.create_workspace(workspace_id="ws-chain", name="Chain Workspace")
    projects.create_project(project_id="proj-chain", workspace_id="ws-chain", name="Story Pipeline")
    processes = ProcessRepository(database)
    processes.create_process(process_id="proc-chain", project_id="proj-chain", name="Skill 0-1-2 Pipeline")

    # Publish Process DAG: Task 0 (outline) -> Task 1 (content) -> Task 2 (review)
    definition = {
        "definition_format_version": "1",
        "interpreter_version": "dag-v1",
        "tasks": [
            {
                "id": "task-0-outline",
                "task_key": "outline",
                "skill_id": "0.tao_cot_truyen",
                "runtime": {"adapter": "codex", "model_id": "gpt-5.6-sol"},
            },
            {
                "id": "task-1-content",
                "task_key": "content",
                "skill_id": "1.tao_noi_dung",
                "max_revisions": 2,
                "review_criteria": {
                    "min_words": 15,
                    "require_pov_ban": True,
                    "max_line_length": 500,
                    "required_keywords": ["Bạn"],
                },
                "runtime": {"adapter": "codex", "model_id": "gpt-5.6-sol"},
            },
            {
                "id": "task-2-review",
                "task_key": "review",
                "skill_id": "2.review_noi_dung",
                "search_query": "tiếng lóng bất động sản củ tỏi",
                "runtime": {"adapter": "codex", "model_id": "gpt-5.6-sol"},
            },
        ],
        "dependencies": [
            {"source_task_id": "task-0-outline", "target_task_id": "task-1-content"},
            {"source_task_id": "task-1-content", "target_task_id": "task-2-review"},
        ],
    }
    processes.store_published(
        workspace_id="ws-chain",
        project_id="proj-chain",
        process_id="proc-chain",
        version_id="ver-chain-v1",
        version_number=1,
        definition=definition,
        snapshot_sha256="a" * 64,
    )

    client = TestClient(app)
    return {
        "database": database,
        "settings": settings,
        "client": client,
        "artifacts_dir": artifacts_dir,
    }


def pair_runner(test_env, name="PC-Chain-1"):
    client = test_env["client"]
    resp = client.post(
        "/v1/pairing-codes",
        json={"workspace_id": "ws-chain", "name": name, "expires_in_seconds": 300},
    )
    assert resp.status_code == 201
    code = resp.json()["pairing_code"]

    resp = client.post("/v1/runners/pair", json={"pairing_code": code, "client_version": "0.1.0"})
    assert resp.status_code == 201
    runner_id = resp.json()["runner_id"]
    runner_token = resp.json()["runner_token"]

    resp = client.post(
        f"/v1/runners/{runner_id}/sessions",
        json={"client_version": "0.1.0"},
        headers={"Authorization": f"Bearer {runner_token}"},
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


# --- AGN-001 & AGN-002: Review Criteria Evaluation & Decision Deduplication ---

def test_agn001_agn002_review_criteria_and_deduplication(skill_chain_env):
    client = skill_chain_env["client"]

    # 1. Content Evaluation: All criteria met -> approved
    valid_content = "Bạn đang đứng trước một ngã rẽ cuộc đời. Bạn phải trả giá 500 củ để tiếp tục."
    resp = client.post(
        "/v1/evaluate-content",
        json={
            "content": valid_content,
            "criteria": {
                "min_words": 10,
                "require_pov_ban": True,
                "required_keywords": ["Bạn", "củ"],
                "max_line_length": 500,
            },
            "revision_round": 1,
            "max_revisions": 2,
        },
    )
    assert resp.status_code == 200
    res = resp.json()
    assert res["decision"] == "approved"
    assert res["score"] >= 9.0
    assert len(res["violations"]) == 0

    # 2. Content Evaluation: Criteria failed on round 1 -> revision_requested
    bad_content = "Tôi đang đứng trước ngã rẽ cuộc đời. Tôi không biết phải làm sao."
    resp = client.post(
        "/v1/evaluate-content",
        json={
            "content": bad_content,
            "criteria": {
                "min_words": 10,
                "require_pov_ban": True,
                "required_keywords": ["Bạn"],
            },
            "revision_round": 1,
            "max_revisions": 2,
        },
    )
    assert resp.status_code == 200
    res = resp.json()
    assert res["decision"] == "revision_requested"
    assert any("missing_pov_ban" in v for v in res["violations"])
    assert "Yêu cầu chỉnh sửa vòng 1" in res["feedback"]

    # 3. Content Evaluation: Criteria failed on round 2 (max_revisions reached) -> escalated
    resp = client.post(
        "/v1/evaluate-content",
        json={
            "content": bad_content,
            "criteria": {
                "min_words": 10,
                "require_pov_ban": True,
            },
            "revision_round": 2,
            "max_revisions": 2,
        },
    )
    assert resp.status_code == 200
    res = resp.json()
    assert res["decision"] == "escalated"
    assert "Vượt quá số lần sửa tối đa" in res["feedback"]

    # 4. Decision Recording & Deduplication (idempotency key)
    runner = pair_runner(skill_chain_env, "PC-Reviewer")
    run = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-chain-v1", "input": {"topic": "Review Test"}},
        headers={"Idempotency-Key": "run-rev-test"},
    ).json()
    task_run_id = run["task_runs"][0]["id"]
    assign = client.post(
        f"/v1/task-runs/{task_run_id}/claim",
        json={"session_id": runner["session_id"]},
        headers={"Authorization": f"Bearer {runner['runner_token']}", "Idempotency-Key": "claim-rev"},
    ).json()
    attempt_id = assign["attempt_id"]

    dec_key = "decision-unique-test-key-1"
    rev_payload = {
        "attempt_id": attempt_id,
        "reviewer_agent_id": "agent-critic-1",
        "revision_round": 1,
        "decision": "revision_requested",
        "score": 6.5,
        "feedback": "Cần thêm từ lóng và ngôi Bạn",
        "violations": ["missing_pov_ban"],
        "decision_key": dec_key,
    }
    rec_resp = client.post(
        f"/v1/task-runs/{task_run_id}/reviews",
        json=rev_payload,
        headers={"Authorization": f"Bearer {runner['runner_token']}"},
    )
    assert rec_resp.status_code == 201
    recorded = rec_resp.json()
    assert recorded["decision"] == "revision_requested"
    assert recorded["decision_key"] == dec_key

    # Re-sending with same decision_key returns existing decision (deduplication)
    dup_resp = client.post(
        f"/v1/task-runs/{task_run_id}/reviews",
        json=rev_payload,
        headers={"Authorization": f"Bearer {runner['runner_token']}"},
    )
    assert dup_resp.status_code == 201
    assert dup_resp.json()["id"] == recorded["id"]

    # List decisions for task run
    list_resp = client.get(
        f"/v1/task-runs/{task_run_id}/reviews",
        headers={"Authorization": f"Bearer {runner['runner_token']}"},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["id"] == recorded["id"]


# --- RUN-007: Skill 0 -> 1 -> 2 Sequential Execution Pipeline ---

class MockStoryChainAdapter(BaseRuntimeAdapter):
    """Simulates realistic Story Chain execution across Skill 0, Skill 1, and Skill 2."""
    def __init__(self, fail_skill1_rounds: int = 0, permanent_fail_skill1: bool = False):
        self.call_count = 0
        self.fail_skill1_rounds = fail_skill1_rounds
        self.permanent_fail_skill1 = permanent_fail_skill1
        self.skill1_round = 0

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
        self.call_count += 1
        prompt_str = str(prompt)

        # Detect which skill is executing based on prompt context / output file name
        out_name = output_file.name if output_file else ""

        if "cot truyen" in out_name or "DÀN Ý" not in prompt_str:
            # Skill 0: Tạo cốt truyện
            text = (
                "DÀN Ý CỐT TRUYỆN: Mẹ đơn thân khởi nghiệp\n"
                "Part 1: Biến cố chia tay và số tiền nợ 200 củ\n"
                "Part 2: Những ngày đầu bán hàng livestream chật vật\n"
                "Part 3: Cú ngã khi bị đối tác quỵt cọc 50 củ\n"
                "Part 4: Nỗ lực không ngừng và sự đồng lòng của hai mẹ con\n"
                "Part 5: Thành quả chạm mốc doanh thu 1 tỏi đầu tiên\n"
            )
            if output_file:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(text, encoding="utf-8")
            return RuntimeExecutionResult(success=True, exit_code=0, output_text=text)

        elif "noi dung_round" in out_name or "noi dung" in out_name:
            # Skill 1: Tạo nội dung
            self.skill1_round += 1
            if self.permanent_fail_skill1 or (self.skill1_round <= self.fail_skill1_rounds):
                # Generates content that violates criteria (missing "Bạn" POV)
                text = (
                    "Tôi bắt đầu câu chuyện này khi mọi thứ sụp đổ quanh tôi. "
                    "Tôi không còn một đồng xu dính túi và ôm đứa con nhỏ khóc trong đêm mưa lạnh lẽo."
                )
            else:
                # Generates approved content with "Bạn" and required word count
                text = (
                    "================================================================================\n"
                    "TIÊU ĐỀ: BÀI HỌC KHỞI NGHIỆP CỦA NGƯỜI MẸ ĐƠN THÂN\n"
                    "Chủ đề: Khởi nghiệp\n"
                    "================================================================================\n\n"
                    "--------------------------------------------------------------------------------\n"
                    "PART 1: GÁNH NẶNG NỢ NẦN\n"
                    "--------------------------------------------------------------------------------\n\n"
                    "Bạn tưởng rằng cuộc sống sẽ buông tha bạn khi bạn rơi xuống đáy sâu nhất của tuyệt vọng sao? "
                    "Không đâu. Khi người đàn ông ấy dứt áo ra đi để lại cho bạn một khoản nợ 200 củ, bạn chỉ có đúng hai lựa chọn: "
                    "buông xuôi để con bạn chịu khổ, hoặc đứng dậy cắn răng mà chiến đấu từng ngày một trên thương trường khốc liệt này.\n"
                )
            if output_file:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(text, encoding="utf-8")
            return RuntimeExecutionResult(success=True, exit_code=0, output_text=text)

        else:
            # Fallback
            text = f"Default execution output: {prompt[:50]}"
            if output_file:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(text, encoding="utf-8")
            return RuntimeExecutionResult(success=True, exit_code=0, output_text=text)


def test_run007_full_skill_chain_happy_path(skill_chain_env, tmp_path, monkeypatch):
    """Full Skill 0 -> 1 -> 2 pipeline: All 3 tasks succeed, artifacts passed and preserved."""
    client = skill_chain_env["client"]
    runner_data = pair_runner(skill_chain_env, "PC-Happy-Chain")

    creds_path = tmp_path / "creds.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_data["runner_id"],
        runner_token=runner_data["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_data["session_id"]

    ws_mgr = WorkspaceManager(tmp_path / "ws_chain_happy")
    adapter = MockStoryChainAdapter(fail_skill1_rounds=0)
    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=ws_mgr,
        codex_adapter=adapter,
    )
    patch_worker_httpx(monkeypatch, client)

    # 1. Create Run
    create_resp = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-chain-v1", "input": {"topic": "Mẹ đơn thân khởi nghiệp"}},
        headers={"Idempotency-Key": "run-chain-happy-1"},
    )
    assert create_resp.status_code == 202
    run_id = create_resp.json()["id"]

    # 2. Worker executes Task 0 (Outline)
    res0 = worker.poll_and_execute_once()
    assert res0 is not None
    assert res0["outcome"] == "succeeded"
    assert len(res0["artifact_ids"]) == 1

    # 3. Worker executes Task 1 (Content)
    res1 = worker.poll_and_execute_once()
    assert res1 is not None
    assert res1["outcome"] == "succeeded"
    # Produces round checkpoint + final noi dung.txt
    assert len(res1["artifact_ids"]) >= 2

    # 4. Worker executes Task 2 (Review)
    res2 = worker.poll_and_execute_once()
    assert res2 is not None
    assert res2["outcome"] == "succeeded"
    # Produces noi dung_reviewed.txt and audit_report.md
    assert len(res2["artifact_ids"]) == 2

    # 5. Verify Run is fully succeeded
    run_data = client.get(f"/v1/runs/{run_id}").json()
    assert run_data["status"] == "succeeded"

    # Verify all tasks succeeded
    task_runs = run_data["task_runs"]
    assert len(task_runs) == 3
    assert all(t["status"] == "succeeded" for t in task_runs)

    # Verify artifacts preserved on server
    artifacts = run_data["artifacts"]
    artifact_names = [a["logical_name"] for a in artifacts]
    assert "cot truyen.txt" in artifact_names
    assert "noi dung.txt" in artifact_names
    assert "noi dung_reviewed.txt" in artifact_names
    assert "audit_report.md" in artifact_names

    # Check reviewed content has zero clutter (no PART 1:, no ====) and <= 500 chars
    rev_art = next(a for a in artifacts if a["logical_name"] == "noi dung_reviewed.txt")
    rev_content = client.get(f"/v1/artifacts/{rev_art['id']}/content").text
    assert "====" not in rev_content
    assert "PART 1:" not in rev_content
    assert all(len(line) <= 500 for line in rev_content.splitlines())

    # Check audit report content
    audit_art = next(a for a in artifacts if a["logical_name"] == "audit_report.md")
    audit_content = client.get(f"/v1/artifacts/{audit_art['id']}/content").text
    assert "BÁO CÁO NGHIỆM THU NỘI DUNG" in audit_content
    assert "Chuẩn giọng đọc ElevenLabs" in audit_content
    assert "Bằng chứng Tra cứu Search" in audit_content


def test_run007_skill1_revision_requested_and_checkpoint_preservation(skill_chain_env, tmp_path, monkeypatch):
    """Skill 1 fails round 1, gets feedback, passes round 2: Checkpoints preserved."""
    client = skill_chain_env["client"]
    runner_data = pair_runner(skill_chain_env, "PC-Revision-Chain")

    creds_path = tmp_path / "creds_rev.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_data["runner_id"],
        runner_token=runner_data["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_data["session_id"]

    ws_mgr = WorkspaceManager(tmp_path / "ws_chain_rev")
    # Fails round 1, passes round 2
    adapter = MockStoryChainAdapter(fail_skill1_rounds=1)
    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=ws_mgr,
        codex_adapter=adapter,
    )
    patch_worker_httpx(monkeypatch, client)

    # 1. Create Run
    run_id = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-chain-v1", "input": {"topic": "Mẹ đơn thân vượt khó"}},
        headers={"Idempotency-Key": "run-chain-rev-1"},
    ).json()["id"]

    # 2. Execute Task 0
    worker.poll_and_execute_once()

    # 3. Execute Task 1 (will undergo Round 1 -> revision_requested -> Round 2 -> approved)
    res1 = worker.poll_and_execute_once()
    assert res1 is not None
    assert res1["outcome"] == "succeeded"

    # 4. Verify decisions on server for Task 1
    content_task_id = res1["task_run_id"]
    decisions = client.get(f"/v1/task-runs/{content_task_id}/reviews").json()
    assert len(decisions) == 2
    assert decisions[0]["decision"] == "revision_requested"
    assert decisions[0]["revision_round"] == 1
    assert decisions[1]["decision"] == "approved"
    assert decisions[1]["revision_round"] == 2

    # 5. Verify Checkpoint artifacts: round 1 checkpoint, round 2 checkpoint, and final noi dung.txt
    run_data = client.get(f"/v1/runs/{run_id}").json()
    art_names = [a["logical_name"] for a in run_data["artifacts"]]
    assert "noi dung_round_1.txt" in art_names
    assert "noi dung_round_2.txt" in art_names
    assert "noi dung.txt" in art_names


def test_run007_skill1_exceeds_max_revisions_escalates_and_blocks_downstream(skill_chain_env, tmp_path, monkeypatch):
    """Skill 1 fails round 1 and round 2: Exceeds max_revisions -> escalated -> downstream skipped."""
    client = skill_chain_env["client"]
    runner_data = pair_runner(skill_chain_env, "PC-Escalate-Chain")

    creds_path = tmp_path / "creds_esc.json"
    session_mgr = ClientSessionManager(credentials_path=creds_path)
    session_mgr.save_credentials(
        runner_id=runner_data["runner_id"],
        runner_token=runner_data["runner_token"],
        server_url="http://testserver",
    )
    session_mgr.current_session_id = runner_data["session_id"]

    ws_mgr = WorkspaceManager(tmp_path / "ws_chain_esc")
    # Always fails criteria
    adapter = MockStoryChainAdapter(permanent_fail_skill1=True)
    worker = TaskExecutionWorker(
        session_manager=session_mgr,
        workspace_manager=ws_mgr,
        codex_adapter=adapter,
    )
    patch_worker_httpx(monkeypatch, client)

    # 1. Create Run
    run_id = client.post(
        "/v1/runs",
        json={"process_version_id": "ver-chain-v1", "input": {"topic": "Mẹ đơn thân thất bại"}},
        headers={"Idempotency-Key": "run-chain-esc-1"},
    ).json()["id"]

    # 2. Execute Task 0 (Outline succeeds)
    res0 = worker.poll_and_execute_once()
    assert res0["outcome"] == "succeeded"

    # 3. Execute Task 1 (fails both round 1 and round 2 -> escalated -> failed)
    res1 = worker.poll_and_execute_once()
    assert res1 is not None
    assert res1["outcome"] == "failed"

    # 4. Check decisions on server
    content_task_id = res1["task_run_id"]
    decisions = client.get(f"/v1/task-runs/{content_task_id}/reviews").json()
    assert len(decisions) == 2
    assert decisions[0]["decision"] == "revision_requested"
    assert decisions[1]["decision"] == "escalated"

    # 5. Verify failure isolation on server:
    run_data = client.get(f"/v1/runs/{run_id}").json()
    assert run_data["status"] == "failed"

    task_runs = run_data["task_runs"]
    t0 = next(t for t in task_runs if t["task_id"] == "task-0-outline")
    t1 = next(t for t in task_runs if t["task_id"] == "task-1-content")
    t2 = next(t for t in task_runs if t["task_id"] == "task-2-review")

    assert t0["status"] == "succeeded"
    assert t1["status"] == "failed"
    # Task 2 MUST BE SKIPPED (Downstream blocked)!
    assert t2["status"] == "skipped"

    # Upstream Task 0 artifact preserved!
    art_names = [a["logical_name"] for a in run_data["artifacts"]]
    assert "cot truyen.txt" in art_names

    # Polling again yields no more work (Skill 2 was skipped, cannot be claimed)
    next_work = worker.poll_and_execute_once()
    assert next_work is None

"""Integration tests for Agent templates, LLM gateway, multi-turn orchestration, and conditional routing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.agents.llm_gateway import LLMGateway
from agent_cf_server.infrastructure.agents.orchestrator import AgentOrchestrator
from agent_cf_server.infrastructure.overview.repository import OverviewRepository
from agent_cf_server.infrastructure.runs.repository import RunRepository


def _create_app_with_mock_llm(tmp_path: Path, handler):
    settings = ServerSettings(
        database_path=tmp_path / "test.db",
        artifacts_dir=tmp_path / "artifacts",
        client_installer_path=tmp_path / "installer.exe",
    )
    app = create_app(settings)
    transport = httpx.MockTransport(handler)
    gateway = LLMGateway(transport=transport)
    orchestrator = AgentOrchestrator(gateway=gateway)
    return app, orchestrator


def _seed_common(client: TestClient, tmp_path: Path, api_format: str = "openai"):
    # Create provider + model + role
    p = client.post(
        "/v1/settings/providers",
        json={
            "id": "prov-1",
            "name": "Test Provider",
            "api_format": api_format,
            "base_url": "https://llm.local/v1" if api_format == "openai" else "https://llm.local",
            "api_key": "sk-test-123",
        },
    )
    assert p.status_code == 201
    m = client.post(
        "/v1/settings/models",
        json={
            "id": "mod-1",
            "provider_id": "prov-1",
            "name": "Brain Model",
            "model_identifier": "gpt-brain",
        },
    )
    assert m.status_code == 201
    r = client.post(
        "/v1/settings/roles",
        json={"id": "role-1", "name": "Điều phối viên", "description": "Điều phối"},
    )
    assert r.status_code == 201

    # Workspace, Runner, Agent, Skill
    db = client.app.state.database
    with db.transaction() as conn:
        conn.execute("INSERT INTO workspaces (id, name) VALUES ('ws-1', 'Default')")
        conn.execute(
            "INSERT INTO runners (id, workspace_id, status) VALUES ('run-pc-1', 'ws-1', 'online')"
        )
        conn.execute(
            "INSERT INTO runner_sessions (id, runner_id, status, created_at, capabilities_json) "
            "VALUES ('sess-1', 'run-pc-1', 'active', '2026-11-23T00:00:00Z', '[\"codex\", \"antigravity\"]')"
        )

    ag = client.post(
        "/v1/agents",
        json={
            "id": "agent-1",
            "name": "Nhân viên A",
            "role_id": "role-1",
            "model_id": "mod-1",
            "template_id": "tpl-multi-part-writer",
            "instructions": "Tự gõ tiếp tục khi hỏi Part. Báo lỗi dễ hiểu nếu hỏng.",
            "allow_reply": True,
            "allow_retry": True,
            "allow_need_human": True,
            "max_turns": 8,
        },
    )
    assert ag.status_code == 201

    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# Skill test\n", encoding="utf-8")
    work_dir = tmp_path / "project_root"
    work_dir.mkdir(exist_ok=True)

    proj = client.post(
        "/v1/projects",
        json={
            "workspace_id": "ws-1",
            "name": "YouTube Test",
            "description": "Test",
            "pm_agent_id": "agent-1",
            "working_directory": str(work_dir),
        },
    )
    assert proj.status_code == 201
    project_id = proj.json()["id"]

    sk = client.post(
        "/v1/skills",
        json={
            "id": "sk-1",
            "name": "Skill Viết",
            "description": "Test",
            "project_ids": [project_id],
            "source_runner_id": "run-pc-1",
            "source_path": str(skill_file),
        },
    )
    assert sk.status_code == 201
    return project_id, work_dir


def test_agent_templates_crud_and_default_switching(tmp_path: Path):
    app = create_app(
        ServerSettings(
            database_path=tmp_path / "tpl.db",
            artifacts_dir=tmp_path / "artifacts",
            client_installer_path=tmp_path / "installer.exe",
        )
    )
    with TestClient(app) as client:
        res = client.get("/v1/agent-templates")
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 3
        assert sum(1 for t in items if t["is_default"]) == 1

        # Create custom template & set as default
        created = client.post(
            "/v1/agent-templates",
            json={
                "name": "Mẫu tùy chỉnh của tôi",
                "description": "Mô tả ngắn",
                "prompt_text": "Luôn kiểm tra kỹ lỗi.",
                "allow_reply": True,
                "allow_retry": False,
                "allow_need_human": True,
                "max_turns": 6,
                "is_default": True,
            },
        )
        assert created.status_code == 201
        tpl_id = created.json()["id"]
        assert created.json()["is_default"] is True
        assert created.json()["allow_retry"] is False

        # Cannot delete default template directly
        del_default = client.delete(f"/v1/agent-templates/{tpl_id}")
        assert del_default.status_code == 409

        # Update template
        upd = client.patch(
            f"/v1/agent-templates/{tpl_id}",
            json={"max_turns": 12, "description": "Đã sửa"},
        )
        assert upd.status_code == 200
        assert upd.json()["max_turns"] == 12

        # Switch default back and delete custom template
        sw = client.post("/v1/agent-templates/tpl-default-orchestrator/default")
        assert sw.status_code == 200
        assert sw.json()["is_default"] is True

        deleted = client.delete(f"/v1/agent-templates/{tpl_id}")
        assert deleted.status_code == 204


def test_llm_gateway_formats_openai_anthropic_google():
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append((str(request.url), dict(request.headers)))
        if str(request.url).endswith("/messages"):
            return httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": '```json\n{"action":"done","summary_vi":"Xong"}\n```'}],
                    "usage": {"input_tokens": 11, "output_tokens": 7},
                },
            )
        if ":generateContent" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": [{"text": '{"action":"reply","reply_message":"1"}'}]}}],
                    "usageMetadata": {"promptTokenCount": 15, "candidatesTokenCount": 5, "totalTokenCount": 20},
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"action":"fail","error_analysis":"Hết quota"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16},
            },
        )

    gw = LLMGateway(transport=httpx.MockTransport(handler))
    r1 = gw.complete_json(
        provider={"api_format": "openai", "base_url": "https://api.openai.com/v1", "api_key": "k1"},
        model={"model_identifier": "gpt-4o-mini"},
        system_prompt="sys",
        user_prompt="usr",
    )
    assert r1.parsed_json["action"] == "fail"
    assert r1.total_tokens == 16

    r2 = gw.complete_json(
        provider={"api_format": "anthropic", "base_url": "https://api.anthropic.com", "api_key": "k2"},
        model={"model_identifier": "claude-sonnet"},
        system_prompt="sys",
        user_prompt="usr",
    )
    assert r2.parsed_json["action"] == "done"
    assert r2.total_tokens == 18

    r3 = gw.complete_json(
        provider={"api_format": "google", "base_url": "https://generativelanguage.googleapis.com", "api_key": "k3"},
        model={"model_identifier": "gemini-2.5-flash"},
        system_prompt="sys",
        user_prompt="usr",
    )
    assert r3.parsed_json["action"] == "reply"
    assert r3.total_tokens == 20
    assert len(seen_requests) == 3


def test_multi_turn_orchestration_need_human_and_conditional_routing(tmp_path: Path):
    llm_responses = [
        # Turn 1: CLI asks question, no files yet -> reply
        {
            "action": "reply",
            "reply_message": "Tiếp tục viết Part 2",
            "summary_vi": "CLI đã xong Part 1 và hỏi tiếp tục.",
        },
        # Turn 2: CLI asks creative option -> need_human
        {
            "action": "need_human",
            "question_for_user": "Bạn muốn kết thúc buồn hay kết thúc có hậu?",
            "suggested_options": ["Kết thúc buồn", "Kết thúc có hậu"],
            "summary_vi": "CLI đang chờ bạn chọn hướng kết thúc.",
        },
        # Turn 3 (after human Continue): CLI finishes and creates file -> done with route="dat_chuan"
        {
            "action": "done",
            "route": "dat_chuan",
            "summary_vi": "Đã viết xong toàn bộ bài và lưu file.",
        },
    ]

    def llm_handler(request: httpx.Request) -> httpx.Response:
        payload = llm_responses.pop(0)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
            },
        )

    app, orchestrator = _create_app_with_mock_llm(tmp_path, llm_handler)
    with TestClient(app) as client:
        # Inject mock orchestrator into repository
        app.state.runs_repo.orchestrator = orchestrator
        project_id, _ = _seed_common(client, tmp_path)

        # Create Process with 3 nodes: t-write -> t-pass (route="dat_chuan"), t-write -> t-fix (route="viet_lai")
        proc = client.post(
            f"/v1/projects/{project_id}/processes",
            json={"name": "Luồng Rẽ Nhánh", "description": "Test"},
        )
        assert proc.status_code == 201
        process_id = proc.json()["id"]

        cfg = client.get(f"/v1/processes/{process_id}/configuration").json()
        definition = {
            "definition_format_version": "1",
            "interpreter_version": "dag-v1",
            "session_mode": "shared_per_tool",
            "tasks": [
                {
                    "id": "t-write",
                    "task_key": "write",
                    "name": "Viết bài",
                    "kind": "agent",
                    "agent_id": "agent-1",
                    "skill_id": "sk-1",
                    "runner_id": "run-pc-1",
                    "runtime": {"adapter": "antigravity", "model_id": "gemini-4-hydrogen"},
                    "orchestration_enabled": True,
                },
                {
                    "id": "t-pass",
                    "task_key": "pass_step",
                    "name": "Làm Voice",
                    "kind": "agent",
                    "agent_id": "agent-1",
                    "skill_id": "sk-1",
                    "runner_id": "run-pc-1",
                    "runtime": {"adapter": "antigravity", "model_id": "gemini-4-hydrogen"},
                },
                {
                    "id": "t-fix",
                    "task_key": "fix_step",
                    "name": "Viết lại",
                    "kind": "agent",
                    "agent_id": "agent-1",
                    "skill_id": "sk-1",
                    "runner_id": "run-pc-1",
                    "runtime": {"adapter": "antigravity", "model_id": "gemini-4-hydrogen"},
                },
            ],
            "dependencies": [
                {
                    "source_task_id": "t-write",
                    "target_task_id": "t-pass",
                    "condition_type": "route",
                    "route_key": "dat_chuan",
                    "condition_label": "Đạt chuẩn",
                },
                {
                    "source_task_id": "t-write",
                    "target_task_id": "t-fix",
                    "condition_type": "route",
                    "route_key": "viet_lai",
                    "condition_label": "Cần viết lại",
                },
            ],
        }
        saved = client.put(
            f"/v1/processes/{process_id}/configuration",
            json={"definition": definition, "expected_token": cfg["configuration_token"]},
        )
        assert saved.status_code == 200

        # Launch run
        run_res = client.post(
            f"/v1/processes/{process_id}/runs",
            json={"input": {"topic": "Kể chuyện"}},
            headers={"Idempotency-Key": f"run-{uuid4().hex}"},
        )
        assert run_res.status_code == 202
        run_id = run_res.json()["id"]

        # Claim t-write
        runner_headers = {"Authorization": "Bearer tok-runner-1"}
        work = client.get(
            "/v1/runners/run-pc-1/work",
            params={"session_id": "sess-1"},
            headers=runner_headers,
        ).json()["items"]
        assert len(work) == 1
        claim_res = client.post(
            f"/v1/task-runs/{work[0]['task_run_id']}/claim",
            json={"session_id": "sess-1", "lease_seconds": 120},
            headers={**runner_headers, "Idempotency-Key": f"c1-{uuid4().hex}"},
        )
        assert claim_res.status_code == 201, claim_res.text
        claim1 = claim_res.json()

        # Turn 1 -> reply
        t1 = client.post(
            f"/v1/attempts/{claim1['attempt_id']}/turn",
            json={
                "turn_number": 1,
                "output_text": "Đã xong Part 1. Bạn muốn viết tiếp Part 2 không?",
                "session_id": "agy-conv-99",
                "exit_code": 0,
                "local_files": [],
            },
            headers={"X-Execution-Token": claim1["execution_token"]},
        )
        assert t1.status_code == 200
        assert t1.json()["action"] == "reply"
        assert t1.json()["reply_message"] == "Tiếp tục viết Part 2"

        # Turn 2 -> need_human
        t2 = client.post(
            f"/v1/attempts/{claim1['attempt_id']}/turn",
            json={
                "turn_number": 2,
                "output_text": "Bạn chọn kết thúc buồn hay kết thúc có hậu?",
                "session_id": "agy-conv-99",
                "exit_code": 0,
                "local_files": [],
            },
            headers={"X-Execution-Token": claim1["execution_token"]},
        )
        assert t2.status_code == 200
        assert t2.json()["action"] == "need_human"

        # Verify Run is paused with suggested options
        run_detail = client.get(f"/v1/runs/{run_id}").json()
        assert run_detail["attention_reason"] == "Bạn muốn kết thúc buồn hay kết thúc có hậu?"
        tr_write = next(t for t in run_detail["task_runs"] if t["task_id"] == "t-write")
        assert tr_write["waiting_for"] == "human_input"
        assert tr_write["waiting_context"]["suggested_options"] == ["Kết thúc buồn", "Kết thúc có hậu"]

        # Human replies via Continue
        cont = client.post(
            f"/v1/runs/{run_id}/continue",
            json={"decision": "continue", "feedback": "Kết thúc có hậu"},
            headers={"Idempotency-Key": f"cont-{uuid4().hex}"},
        )
        assert cont.status_code == 200
        assert cont.json()["attention_reason"] is None

        # Client claims t-write again and receives resume_session_id + human_reply
        claim2 = client.post(
            f"/v1/task-runs/{tr_write['id']}/claim",
            json={"session_id": "sess-1", "lease_seconds": 120},
            headers={**runner_headers, "Idempotency-Key": f"c2-{uuid4().hex}"},
        ).json()
        assert claim2["waiting_context"]["resume_session_id"] == "agy-conv-99"
        assert claim2["waiting_context"]["human_reply"] == "Kết thúc có hậu"

        # Turn 3 -> done with route="dat_chuan"
        t3 = client.post(
            f"/v1/attempts/{claim2['attempt_id']}/turn",
            json={
                "turn_number": 3,
                "output_text": "Đã hoàn tất ghi truyện ra file.",
                "session_id": "agy-conv-99",
                "exit_code": 0,
                "local_files": [{"path": "D:/story.txt", "size_bytes": 4096}],
            },
            headers={"X-Execution-Token": claim2["execution_token"]},
        )
        assert t3.status_code == 200
        assert t3.json()["action"] == "done"
        assert t3.json()["route"] == "dat_chuan"

        # Complete t-write -> t-pass becomes queued, t-fix becomes skipped!
        comp1 = client.post(
            f"/v1/attempts/{claim2['attempt_id']}/complete",
            json={
                "session_id": "sess-1",
                "generation": claim2["generation"],
                "outcome": "succeeded",
                "exit_code": 0,
                "output": {"route": "dat_chuan", "agent_summary": t3.json()["summary_vi"]},
            },
            headers={
                "X-Execution-Token": claim2["execution_token"],
                "Idempotency-Key": f"comp1-{uuid4().hex}",
            },
        )
        assert comp1.status_code == 200

        mid_run = client.get(f"/v1/runs/{run_id}").json()
        by_id = {t["task_id"]: t["status"] for t in mid_run["task_runs"]}
        assert by_id["t-write"] == "succeeded"
        assert by_id["t-pass"] == "queued"
        assert by_id["t-fix"] == "skipped"

        # Complete t-pass -> entire Run succeeds despite t-fix skipped by branching
        tr_pass = next(t for t in mid_run["task_runs"] if t["task_id"] == "t-pass")
        claim_pass = client.post(
            f"/v1/task-runs/{tr_pass['id']}/claim",
            json={"session_id": "sess-1", "lease_seconds": 60},
            headers={**runner_headers, "Idempotency-Key": f"cp-{uuid4().hex}"},
        ).json()
        client.post(
            f"/v1/attempts/{claim_pass['attempt_id']}/complete",
            json={
                "session_id": "sess-1",
                "generation": claim_pass["generation"],
                "outcome": "succeeded",
                "exit_code": 0,
                "output": {"ok": True},
            },
            headers={
                "X-Execution-Token": claim_pass["execution_token"],
                "Idempotency-Key": f"comp2-{uuid4().hex}",
            },
        )

        final_run = client.get(f"/v1/runs/{run_id}").json()
        assert final_run["status"] == "succeeded"
        assert len(final_run["turn_decisions"]) == 3

        # Overview token tracking must record 3 * 130 = 390 tokens for agent-1
        ov = OverviewRepository(app.state.database).get_overview_summary()
        ag_usage = next(a for a in ov["agents_token_usage"] if a["agent_id"] == "agent-1")
        assert ag_usage["total_tokens"] == 390

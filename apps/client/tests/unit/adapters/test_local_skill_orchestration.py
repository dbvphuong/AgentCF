"""Unit/integration tests for client multi-turn Agent API orchestration loop."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.runtime.base import BaseRuntimeAdapter, RuntimeExecutionResult


class _MultiTurnFakeAdapter(BaseRuntimeAdapter):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    @property
    def adapter_id(self) -> str:
        return "antigravity"

    def is_available(self) -> bool:
        return True

    def execute_skill(self, prompt: str, cwd: Path, **kwargs) -> RuntimeExecutionResult:
        return self.execute_local_skill(prompt=prompt, cwd=cwd, **kwargs)

    def execute_local_skill(self, prompt: str, cwd: Path, **kwargs) -> RuntimeExecutionResult:
        self.calls.append({"prompt": prompt, "session_id": kwargs.get("session_id")})
        turn = len(self.calls)
        if turn == 1:
            return RuntimeExecutionResult(
                success=True,
                exit_code=0,
                output_text="Đã xong Part 1. Bạn muốn viết tiếp Part 2 không?",
                session_id="conv-agy-1",
            )
        # Turn 2 creates output file
        topic_dir = cwd / "ChuDe1"
        (topic_dir / "part2.txt").write_text("Nội dung Part 2", encoding="utf-8")
        return RuntimeExecutionResult(
            success=True,
            exit_code=0,
            output_text="Đã hoàn tất toàn bộ và lưu vào part2.txt.",
            session_id="conv-agy-1",
        )


def test_task_worker_multi_turn_reply_then_done(tmp_path: Path, monkeypatch):
    work_dir = tmp_path / "project"
    topic_dir = work_dir / "ChuDe1"
    topic_dir.mkdir(parents=True)
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("# Skill\n", encoding="utf-8")

    ws_mgr = WorkspaceManager(tmp_path / "workspaces")
    sess_mgr = ClientSessionManager(tmp_path / "creds.json")
    sess_mgr.save_credentials(
        runner_id="pc-1",
        runner_token="tok-1",
        server_url="http://server.local",
    )
    sess_mgr.current_session_id = "sess-1"

    adapter = _MultiTurnFakeAdapter()
    worker = TaskExecutionWorker(
        session_manager=sess_mgr,
        workspace_manager=ws_mgr,
        antigravity_adapter=adapter,
    )

    turn_requests: list[dict] = []
    complete_requests: list[dict] = []

    def fake_renew(self, *args, **kwargs):
        return None

    def fake_evaluate_turn(self, server_url, creds, execution_token, attempt_id, payload):
        turn_requests.append(payload)
        if payload["turn_number"] == 1:
            return {
                "action": "reply",
                "reply_message": "Tiếp tục viết Part 2",
                "summary_vi": "Đang hỏi viết tiếp Part 2",
            }
        return {
            "action": "done",
            "route": "dat_chuan",
            "summary_vi": "Hoàn tất đủ 2 part",
        }

    def fake_complete(self, server_url, creds, execution_token, attempt_id, task_run_id, generation, outcome, exit_code, output_payload, error_payload, artifact_ids, launch_id, pid, journal):
        complete_requests.append({"outcome": outcome, "output": output_payload, "error": error_payload})
        return {"outcome": outcome, "output": output_payload}

    monkeypatch.setattr(TaskExecutionWorker, "_renew_lease", fake_renew)
    monkeypatch.setattr(TaskExecutionWorker, "_evaluate_turn_on_server", fake_evaluate_turn)
    monkeypatch.setattr(TaskExecutionWorker, "_complete_attempt_on_server", fake_complete)

    assignment = {
        "run_id": "run-1",
        "task_run_id": "tr-1",
        "attempt_id": "att-1",
        "generation": 1,
        "execution_token": "exec-tok",
        "session_mode": "shared_per_tool",
        "task": {
            "id": "t-1",
            "name": "Viết bài",
            "kind": "agent",
            "runner_id": "pc-1",
            "working_directory": str(work_dir),
            "runtime": {"adapter": "antigravity", "model_id": "gemini-4-hydrogen"},
            "agent_snapshot": {"id": "agent-1", "name": "Nhân viên"},
            "skill_snapshot": {"source_runner_id": "pc-1", "source_path": str(skill_path)},
            "orchestration_enabled": True,
        },
        "input": {"topic_directory": str(topic_dir)},
    }

    res = worker.execute_assignment(assignment)
    assert res["outcome"] == "succeeded"
    assert len(adapter.calls) == 2
    assert adapter.calls[1]["session_id"] == "conv-agy-1"
    assert adapter.calls[1]["prompt"] == "Tiếp tục viết Part 2"
    assert len(turn_requests) == 2
    assert complete_requests[0]["output"]["route"] == "dat_chuan"
    assert complete_requests[0]["output"]["agent_summary"] == "Hoàn tất đủ 2 part"
    assert len(complete_requests[0]["output"]["local_files"]) == 1

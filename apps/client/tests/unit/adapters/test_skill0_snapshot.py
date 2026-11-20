"""Regression checks for the real Skill 0 Project execution path."""

import sys

import pytest

from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.runtime.base import RuntimeExecutionResult
from agent_cf_client.runtime.codex_adapter import CodexAdapter


@pytest.mark.parametrize("success", [True, False])
def test_skill0_reads_published_snapshot_and_honors_timeout(tmp_path, monkeypatch, success):
    class Session:
        current_session_id = "session"

        def get_credentials(self):
            return {"server_url": "http://127.0.0.1:8000", "runner_token": "test-token"}

    instructions = "# Skill 0\nDàn ý nguyên văn: nhân vật, điểm tương tác, PART 1–5."

    class Adapter:
        def execute_skill(self, **kwargs):
            request = (kwargs["cwd"] / "skill0-request.md").read_text(encoding="utf-8")
            assert instructions in request
            assert "Biên kịch tiếng Việt" in request
            assert "Chủ đề kiểm chứng" in request
            assert "Tiêu chí đã publish" in request
            assert "# Node task\ndone" in request
            assert "skill0-request.md" in kwargs["prompt"]
            assert kwargs["model"] == "test-model"
            assert kwargs["timeout_seconds"] == 600
            if success:
                kwargs["output_file"].write_text("DÀN Ý CỐT TRUYỆN\nPART 1–5", encoding="utf-8")
            return RuntimeExecutionResult(
                success=success, exit_code=0 if success else 1,
                output_text="DÀN Ý CỐT TRUYỆN\nPART 1–5" if success else "",
                error_code=None if success else "runtime_error",
            )

    worker = TaskExecutionWorker(Session(), WorkspaceManager(tmp_path), codex_adapter=Adapter())
    uploads = []
    monkeypatch.setattr(worker, "upload_artifact", lambda **kw: uploads.append(kw) or "artifact-1")
    monkeypatch.setattr(worker, "_complete_attempt_on_server", lambda **kw: kw)
    result = worker.execute_assignment({
        "run_id": "run-1", "task_run_id": "task-1", "attempt_id": "attempt-1",
        "execution_token": "test-execution", "generation": 1,
        "input": {"topic": "Chủ đề kiểm chứng"},
        "task": {
            "kind": "agent", "name": "Tạo cốt truyện", "task_key": "outline",
            "execution_timeout_seconds": 600,
            "instructions": "done",
            "runtime": {"adapter": "codex", "model_id": "test-model"},
            "agent_snapshot": {"instructions": "Biên kịch tiếng Việt"},
            "skill_snapshot": {"instructions": instructions, "output_standards": "Tiêu chí đã publish"},
        },
    })
    assert result["outcome"] == ("succeeded" if success else "failed")
    assert result["artifact_ids"] == (["artifact-1"] if success else [])
    assert len(uploads) == int(success)


def test_codex_large_reply_does_not_block_on_pipe_buffers(tmp_path):
    class LocalCodex(CodexAdapter):
        def build_command(self, **kwargs):
            code = (
                "import json; "
                "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'a'*262144}})); "
                "print(json.dumps({'type':'turn.completed'}))"
            )
            return [sys.executable, "-c", code]

    result = LocalCodex().execute_skill(prompt="test", cwd=tmp_path, timeout_seconds=5)
    assert result.success
    assert len(result.output_text) == 262144
    assert (tmp_path / "logs/codex.stdout.jsonl").stat().st_size > 262144

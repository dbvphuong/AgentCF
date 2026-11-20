import pytest
from pathlib import Path
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.runtime.base import RuntimeExecutionResult


class DummySession:
    current_session_id = "session"

    def get_credentials(self):
        return {"runner_id": "pc-1", "server_url": "http://127.0.0.1:8000", "runner_token": "test"}


class SpyAdapter:
    def __init__(self, adapter_id: str):
        self.adapter_id = adapter_id
        self.calls: list[dict] = []
        self.next_session_id = f"{adapter_id}-session-1"

    def execute_local_skill(self, **kwargs):
        self.calls.append(kwargs)
        if "on_started" in kwargs and kwargs["on_started"]:
            kwargs["on_started"](999)
        (kwargs["cwd"] / f"{self.adapter_id}_output_{len(self.calls)}.txt").write_text(f"ok_{len(self.calls)}", encoding="utf-8")
        return RuntimeExecutionResult(
            success=True,
            exit_code=0,
            session_id=self.next_session_id,
            output_text=f"done {len(self.calls)}",
        )


def make_task(tmp_path: Path, adapter: str, session_mode: str = "shared_per_tool") -> dict:
    source_skill = tmp_path / "skill.md"
    source_skill.write_text("# Skill", encoding="utf-8")
    work_dir = tmp_path / "project"
    work_dir.mkdir(exist_ok=True)
    return {
        "id": f"task_{adapter}",
        "session_mode": session_mode,
        "runner_id": "pc-1",
        "working_directory": str(work_dir),
        "runtime": {"adapter": adapter, "model_id": "gpt-5"},
        "skill_snapshot": {
            "source_runner_id": "pc-1",
            "source_path": str(source_skill),
        },
    }


def test_shared_session_mode_shares_per_tool(tmp_path, monkeypatch):
    codex_adapter = SpyAdapter("codex")
    agy_adapter = SpyAdapter("antigravity")

    worker = TaskExecutionWorker(
        DummySession(),
        WorkspaceManager(tmp_path / "logs"),
        codex_adapter=codex_adapter,
        antigravity_adapter=agy_adapter,
    )
    monkeypatch.setattr(worker, "_complete_attempt_on_server", lambda **kw: kw)

    run_id = "run-001"

    # Node 1: Codex (shared)
    task1 = make_task(tmp_path, "codex", session_mode="shared_per_tool")
    worker.execute_assignment({
        "run_id": run_id, "task_run_id": "t1", "attempt_id": "att1", "generation": 1,
        "execution_token": "tok", "task": task1, "input": {},
    })
    assert len(codex_adapter.calls) == 1
    assert codex_adapter.calls[0]["session_id"] is None

    # Node 2: Antigravity (shared)
    task2 = make_task(tmp_path, "antigravity", session_mode="shared_per_tool")
    worker.execute_assignment({
        "run_id": run_id, "task_run_id": "t2", "attempt_id": "att2", "generation": 1,
        "execution_token": "tok", "task": task2, "input": {},
    })
    assert len(agy_adapter.calls) == 1
    assert agy_adapter.calls[0]["session_id"] is None

    # Node 3: Codex (shares session with Node 1)
    task3 = make_task(tmp_path, "codex", session_mode="shared_per_tool")
    worker.execute_assignment({
        "run_id": run_id, "task_run_id": "t3", "attempt_id": "att3", "generation": 1,
        "execution_token": "tok", "task": task3, "input": {},
    })
    assert len(codex_adapter.calls) == 2
    assert codex_adapter.calls[1]["session_id"] == "codex-session-1"

    # Node 4: Antigravity (shares session with Node 2)
    task4 = make_task(tmp_path, "antigravity", session_mode="shared_per_tool")
    worker.execute_assignment({
        "run_id": run_id, "task_run_id": "t4", "attempt_id": "att4", "generation": 1,
        "execution_token": "tok", "task": task4, "input": {},
    })
    assert len(agy_adapter.calls) == 2
    assert agy_adapter.calls[1]["session_id"] == "antigravity-session-1"


def test_isolated_session_mode_runs_fresh_session(tmp_path, monkeypatch):
    codex_adapter = SpyAdapter("codex")

    worker = TaskExecutionWorker(
        DummySession(),
        WorkspaceManager(tmp_path / "logs"),
        codex_adapter=codex_adapter,
    )
    monkeypatch.setattr(worker, "_complete_attempt_on_server", lambda **kw: kw)

    run_id = "run-002"

    # Node 1: Codex isolated
    task1 = make_task(tmp_path, "codex", session_mode="isolated")
    worker.execute_assignment({
        "run_id": run_id, "task_run_id": "t1", "attempt_id": "att1", "generation": 1,
        "execution_token": "tok", "task": task1, "input": {},
    })
    assert len(codex_adapter.calls) == 1
    assert codex_adapter.calls[0]["session_id"] is None

    # Node 2: Codex isolated (does NOT reuse session)
    task2 = make_task(tmp_path, "codex", session_mode="isolated")
    worker.execute_assignment({
        "run_id": run_id, "task_run_id": "t2", "attempt_id": "att2", "generation": 1,
        "execution_token": "tok", "task": task2, "input": {},
    })
    assert len(codex_adapter.calls) == 2
    assert codex_adapter.calls[1]["session_id"] is None


def test_codex_adapter_build_command_with_session():
    from agent_cf_client.runtime.codex_adapter import CodexAdapter
    adapter = CodexAdapter()
    cmd = adapter.build_command(
        prompt="Tiếp tục làm bước 2",
        cwd=Path("E:/TestDir"),
        model="gpt-5",
        session_id="thr-abc-123",
        output_file=Path("E:/TestDir/last.txt"),
    )
    assert "resume" in cmd
    assert "--json" in cmd
    assert "thr-abc-123" in cmd
    assert "Tiếp tục làm bước 2" in cmd
    assert "--output-last-message" in cmd

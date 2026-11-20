"""Local file Skills keep their workflow and binary/text outputs on the PC."""

import json
from pathlib import Path

import pytest

from agent_cf_client.execution.local_skill import execute_local_skill
from agent_cf_client.runtime.base import RuntimeExecutionResult
from agent_cf_client.runtime.codex_adapter import CodexAdapter


def test_topic_context_keeps_project_cwd_and_outputs_in_existing_topic(setup_local):
    source, work, logs, task = setup_local
    topic = work / "Chủ đề 2"
    topic.mkdir()
    untouched = work / "Other topic.txt"
    untouched.write_text("keep")
    seen=[]
    class Adapter:
        def execute_local_skill(self, **kwargs):
            assert kwargs['cwd']==work.resolve()
            prompt=kwargs['prompt']
            assert prompt == f"Gọi skill {source}\ncho chủ đề {topic.resolve()}"
            assert not (logs/'local-skill-request.md').exists()
            seen.append(prompt)
            (topic/'result.txt').write_text('Output from Skill')
            return RuntimeExecutionResult(success=True,exit_code=0)
    result,metadata=execute_local_skill(adapter=Adapter(),task=task,input_data={'topic_directory':str(topic)},runner_id='pc-1',log_dir=logs,on_started=lambda _:None)
    assert result.success and metadata['topic_directory']==str(topic.resolve())
    assert [Path(f['path']).name for f in metadata['local_files']]==['result.txt']
    assert untouched.read_text()=='keep'
    assert len(seen[0].splitlines()) == 2


def test_missing_topic_never_spawns_or_creates_directory(setup_local):
    source,work,logs,task=setup_local
    missing=work/'missing'
    with pytest.raises(ValueError,match='chủ đề'):
        execute_local_skill(adapter=object(),task=task,input_data={'topic_directory':str(missing)},runner_id='pc-1',log_dir=logs,on_started=lambda _:None)
    assert not missing.exists()


@pytest.fixture(params=["SKILL.md", "main.md"])
def setup_local(tmp_path, request):
    source = tmp_path / "skill" / request.param
    source.parent.mkdir()
    source.write_text("# Một Skill có tên bất kỳ\nTạo file ảnh và sửa tài liệu.", encoding="utf-8")
    work = tmp_path / "thư mục làm việc"
    work.mkdir()
    (work / "existing.txt").write_text("Bản cũ", encoding="utf-8")
    logs = tmp_path / "control"
    logs.mkdir()
    task = {
        "name": "review content - tên không quyết định hành vi", "runner_id": "pc-1",
        "skill_snapshot": {"source_path": str(source), "source_runner_id": "pc-1"},
        "working_directory": str(work), "runtime": {"adapter": "codex", "model_id": "exact-model"},
        "execution_timeout_seconds": 123,
        "instructions": "",
    }
    return source, work, logs, task


def test_only_user_entered_notes_extend_the_two_line_prompt(setup_local):
    source, work, logs, task = setup_local
    topic = work / "Chủ đề 2"
    topic.mkdir()
    task["instructions"] = "Giữ giọng văn gần gũi."
    task["agent_snapshot"] = {"instructions": "Agent rules must not be injected"}
    task["skill_snapshot"].update(instructions="Cached Skill rules", output_standards="Cached standards")
    class Adapter:
        def execute_local_skill(self, **kwargs):
            assert kwargs["prompt"] == (
                f"Gọi skill {source}\ncho chủ đề {topic.resolve()}\n"
                "Giữ giọng văn gần gũi.\nTuy nhiên viết 200–300 từ thôi nhé."
            )
            assert not (logs / "local-skill-request.md").exists()
            (topic / "result.txt").write_text("Real output", encoding="utf-8")
            return RuntimeExecutionResult(success=True, exit_code=0)
    result, _ = execute_local_skill(adapter=Adapter(), task=task,
        input_data={"topic_directory":str(topic), "request":"Tuy nhiên viết 200–300 từ thôi nhé."},
        runner_id="pc-1", log_dir=logs, on_started=lambda _:None)
    assert result.success


@pytest.mark.parametrize("mode", ["files", "chat_only", "source_modified", "runtime_failed"])
def test_files_are_created_by_runtime_and_never_uploaded_or_replaced_by_chat(setup_local, mode):
    source, work, logs, task = setup_local
    original = source.read_bytes()

    class Adapter:
        def execute_local_skill(self, **kwargs):
            assert kwargs["cwd"] == work
            assert kwargs["model"] == "exact-model"
            assert kwargs["timeout_seconds"] == 123
            assert kwargs["prompt"] == f"Gọi skill {source}\ncho chủ đề Chủ đề"
            assert not (logs / "local-skill-request.md").exists()
            kwargs["on_started"](1234)
            if mode in {"files", "source_modified"}:
                (work / "ảnh.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\xff")
                (work / "existing.txt").write_text("Nội dung mới", encoding="utf-8")
            if mode == "source_modified":
                source.write_text("Changed by runtime", encoding="utf-8")
            return RuntimeExecutionResult(
                success=mode != "runtime_failed", exit_code=1 if mode == "runtime_failed" else 0,
                output_text="Chat response must not be turned into an output file",
                error_code="runtime_error" if mode == "runtime_failed" else None,
            )

    started = []
    result, metadata = execute_local_skill(
        adapter=Adapter(), task=task, input_data={"topic": "Chủ đề"}, runner_id="pc-1",
        log_dir=logs, on_started=started.append,
    )
    assert started == [1234]
    assert result.success == (mode == "files")
    assert not (work / "cot truyen.txt").exists()
    if mode == "files":
        assert {Path(f["path"]).name for f in metadata["local_files"]} == {"ảnh.png", "existing.txt"}
        assert source.read_bytes() == original
    if mode == "chat_only":
        assert result.error_code == "local_output_missing"
    if mode == "source_modified":
        assert result.error_code == "skill_source_modified"


@pytest.mark.parametrize("bad", ["wrong_pc", "relative_skill", "missing_skill", "relative_directory", "missing_directory", "unsupported_adapter"])
def test_invalid_local_configuration_never_spawns(setup_local, bad):
    source, work, logs, task = setup_local
    if bad == "wrong_pc": task["skill_snapshot"]["source_runner_id"] = "pc-other"
    if bad == "relative_skill": task["skill_snapshot"]["source_path"] = "skill/SKILL.md"
    if bad == "missing_skill": source.unlink()
    if bad == "relative_directory": task["working_directory"] = "relative"
    if bad == "missing_directory": task["working_directory"] = str(work / "missing")
    class Adapter:
        pass
    with pytest.raises(ValueError):
        execute_local_skill(adapter=Adapter(), task=task, input_data={}, runner_id="pc-1", log_dir=logs, on_started=lambda pid: None)


def test_codex_local_command_allows_file_tools_and_keeps_response_in_control_logs(tmp_path):
    from agent_cf_client.execution.process_manager import ProcessResult

    class PM:
        def run_process(self, argv, **kwargs):
            assert argv[argv.index("-s") + 1] == "workspace-write"
            assert argv.index("-s") > argv.index("exec")
            assert argv[argv.index("-C") + 1] == str(tmp_path)
            assert Path(argv[argv.index("--output-last-message") + 1]).parent == tmp_path / "control"
            kwargs["on_started"](99)
            return ProcessResult(exit_code=0, stdout=json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Files created"}}), stderr="")

    pids = []
    result = CodexAdapter(process_manager=PM()).execute_local_skill(
        prompt="Use original Skill", cwd=tmp_path, model="exact-model", timeout_seconds=10,
        log_dir=tmp_path / "control", on_started=pids.append,
    )
    assert result.success and pids == [99]


@pytest.mark.parametrize("adapter_name", ["codex", "antigravity"])
def test_worker_local_mode_precedes_skill_name_and_does_not_upload(setup_local, monkeypatch, adapter_name):
    from agent_cf_client.execution.task_worker import TaskExecutionWorker
    from agent_cf_client.execution.workspace import WorkspaceManager

    source, work, logs, task = setup_local
    task["runtime"]["adapter"] = adapter_name
    class Session:
        current_session_id = "session"
        def get_credentials(self):
            return {"runner_id": "pc-1", "server_url": "http://127.0.0.1:8000", "runner_token": "test"}
    class Adapter:
        def execute_local_skill(self, **kwargs):
            kwargs["on_started"](123)
            (kwargs["cwd"] / "actual.bin").write_bytes(b"\0\xff")
            return RuntimeExecutionResult(success=True, exit_code=0, output_text="Saved actual.bin")
    worker = TaskExecutionWorker(Session(), WorkspaceManager(logs), **{f"{adapter_name}_adapter": Adapter()})
    monkeypatch.setattr(worker, "upload_artifact", lambda **kw: pytest.fail("Local output must not require an upload"))
    monkeypatch.setattr(worker, "_complete_attempt_on_server", lambda **kw: kw)
    result = worker.execute_assignment({
        "run_id": "run", "attempt_id": "attempt", "task_run_id": "task", "generation": 1,
        "execution_token": "test", "task": task, "input": {"action": "Create binary"},
    })
    assert result["outcome"] == "succeeded" and result["pid"] == 123
    assert result["artifact_ids"] == []
    assert result["output_payload"]["local_files"][0]["path"] == str(work / "actual.bin")


def test_demo_local_mode_does_not_reset_cli_permissions(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("local_demo", Path("apps/client/scripts/skill0_test_project.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    command = module.TestCodexAdapter().build_command(prompt="Use local Skill", cwd=tmp_path, sandbox="workspace-write")
    assert "--ignore-user-config" not in command
    assert command[command.index("-s") + 1] == "workspace-write"

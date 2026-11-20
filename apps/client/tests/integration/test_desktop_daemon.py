import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.desktop.daemon import ClientDaemon
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.runtime.base import RuntimeExecutionResult
from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.runs.repository import RunRepository


@pytest.mark.parametrize("topic_mode", [False, True])
def test_general_desktop_client_executes_non_demo_process_and_drains_session(tmp_path, monkeypatch, topic_mode):
    app = create_app(ServerSettings(database_path=tmp_path/"db.sqlite3", temporal_enabled=False))
    with TestClient(app) as api:
        db = app.state.database
        ProjectRepository(db).create_workspace(workspace_id="ws", name="Workspace")
        code = api.post("/v1/pairing-codes", json={"workspace_id": "ws", "name": "General PC"}).json()["pairing_code"]
        paired = api.post("/v1/runners/pair", json={"pairing_code": code}).json()
        manager = ClientSessionManager(tmp_path/"creds.json")
        manager.save_credentials(paired["runner_id"], paired["runner_token"], "http://testserver")
        source = tmp_path/"Skill/main.md"
        source.parent.mkdir()
        source.write_text("Custom fixture Skill, not a demo name", encoding="utf-8")
        work = tmp_path/"output"
        work.mkdir()
        topic = work/"Chủ đề 2"
        topic.mkdir()
        projects = ProjectRepository(db)
        projects.create_project(project_id="any-project", workspace_id="ws", name="Non-demo Project")
        processes = ProcessRepository(db)
        processes.create_process(process_id="any-process", project_id="any-project", name="Unrelated Process")
        node={"id": "node", "task_key": "custom", "name": "Custom Skill", "kind": "agent", "runner_id": paired["runner_id"], "runtime": {"adapter": "codex", "model_id": "fixture"}, "working_directory": str(work), "skill_snapshot": {"source_path": str(source), "source_runner_id": paired["runner_id"]}}
        nodes=[node, {**node,"id":"next","task_key":"next"}] if topic_mode else [node]
        edges=[{"source_task_id":"node","target_task_id":"next"}] if topic_mode else []
        processes.store_published(workspace_id="ws", project_id="any-project", process_id="any-process", version_id="version", version_number=1,
            definition={"definition_format_version": "1", "interpreter_version": "dag-v1", "dependencies": edges, "tasks": nodes}, snapshot_sha256="a"*64)
        runs = RunRepository(db)
        run = runs.create_from_version(version_id="version", principal_id="operator", request_key="test", request_sha256="b"*64, run_input={"topic_directory":str(topic)} if topic_mode else {})["run_id"]
        original_client = httpx.Client
        def transport(request):
            response = api.request(request.method, str(request.url), content=request.content, headers=request.headers)
            return httpx.Response(response.status_code, content=response.content, headers=response.headers)
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(transport), **kwargs))
        class FixtureAdapter:
            def is_available(self): return True
            def execute_local_skill(self, **kwargs):
                target=topic if topic_mode else work
                if topic_mode:
                    assert kwargs['cwd']==work
                    assert kwargs['prompt'] == f"Gọi skill {source}\ncho chủ đề {topic}"
                    if (topic/'result.txt').exists():
                        assert (topic/'result.txt').read_text()=="Real local fixture output"
                        (topic/'next.txt').write_text("Read previous step output",encoding='utf-8')
                (target/"result.txt").write_text("Real local fixture output", encoding="utf-8")
                return RuntimeExecutionResult(success=True, exit_code=0)
        events = []
        def worker_factory(manager, workspace, process_manager):
            return TaskExecutionWorker(manager, workspace, process_manager=process_manager, codex_adapter=FixtureAdapter(), antigravity_adapter=FixtureAdapter())
        daemon = ClientDaemon(manager, tmp_path/"client", events.append, worker_factory=worker_factory)
        monkeypatch.setattr(daemon.desktop, "is_windows_session_locked", lambda: False)
        daemon.start()
        deadline = time.monotonic()+8
        while time.monotonic()<deadline and runs.get(run)["status"] != "succeeded":
            time.sleep(.05)
        daemon.shutdown()
        daemon.thread.join(timeout=5)
        assert not daemon.thread.is_alive()
        assert runs.get(run)["status"] == "succeeded", events
        assert ((topic if topic_mode else work)/"result.txt").read_text() == "Real local fixture output"
        if topic_mode:
            assert (topic/'next.txt').read_text()=="Read previous step output"
            assert all(t['output']['topic_directory']==str(topic) for t in runs.get(run)['task_runs'])
        assert api.get(f"/v1/runners/{paired['runner_id']}").json()["status"] == "offline"
        with db.connect() as conn:
            assert conn.execute("SELECT COUNT(*) FROM attempts WHERE run_id=?", (run,)).fetchone()[0] == (2 if topic_mode else 1)

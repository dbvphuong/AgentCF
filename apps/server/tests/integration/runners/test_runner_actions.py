import pytest
from fastapi.testclient import TestClient

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.runs.repository import RunRepository


@pytest.fixture
def env(tmp_path):
    db = Database(tmp_path / "pc.sqlite3")
    db.migrate()
    ProjectRepository(db).create_workspace(workspace_id="ws", name="Workspace")
    with TestClient(create_app(ServerSettings(database_path=db.path, temporal_enabled=False))) as client:
        yield client, db


def pair(client):
    code = client.post("/v1/pairing-codes", json={"workspace_id": "ws", "name": "PC test"}).json()["pairing_code"]
    response = client.post("/v1/runners/pair", json={"pairing_code": code})
    assert response.status_code == 201
    data = response.json()
    return data["runner_id"], {"Authorization": "Bearer " + data["runner_token"]}


def test_rename_preserves_connection_and_validates_payload(env):
    client, db = env
    runner, auth = pair(client)
    url = "/v1/runners/" + runner
    updated = client.patch(url, json={"name": "  New name  "})
    assert updated.status_code == 200
    assert updated.json()["name"] == "New name"
    assert updated.json()["id"] == runner
    assert updated.json()["workspace_id"] == "ws"
    assert client.post(url + "/sessions", json={"client_version": "test"}, headers=auth).status_code == 201
    for payload in ({"name": "   "}, {"name": "a" * 129}, {"name": "x", "workspace_id": "other"}):
        assert client.patch(url, json=payload).status_code == 422
    assert client.patch("/v1/runners/missing", json={"name": "x"}).status_code == 404
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='runner_renamed'").fetchone()[0] == 1


def test_delete_revokes_credentials_hides_pc_and_cannot_restore(env):
    client, db = env
    runner, auth = pair(client)
    url = "/v1/runners/" + runner
    client.post(url + "/sessions", json={"client_version": "test"}, headers=auth).raise_for_status()
    assert client.delete(url).status_code == 204
    assert client.delete(url).status_code == 204
    assert client.get("/v1/runners").json() == []
    assert client.get(url).json()["deleted_at"]
    assert client.post(url + "/sessions", json={"client_version": "test"}, headers=auth).status_code == 401
    assert client.post(url + "/enable").status_code == 404
    assert client.patch(url, json={"name": "x"}).status_code == 404
    assert client.delete("/v1/runners/missing").status_code == 404
    with db.connect() as conn:
        assert conn.execute("SELECT status FROM runner_sessions WHERE runner_id=?", (runner,)).fetchone()[0] == "revoked"
        assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='runner_removed'").fetchone()[0] == 1
    assert pair(client)[0] != runner


def test_delete_blocks_unfinished_pinned_run_preserves_history_and_stops_schedule(env):
    client, db = env
    runner, auth = pair(client)
    ProjectRepository(db).create_project(project_id="project", workspace_id="ws", name="Project")
    processes = ProcessRepository(db)
    processes.create_process(process_id="process", project_id="project", name="Process")
    processes.store_published(
        workspace_id="ws", project_id="project", process_id="process", version_id="version", version_number=1,
        definition={"definition_format_version": "1", "interpreter_version": "dag-v1", "dependencies": [],
                    "tasks": [{"id": "node", "task_key": "node", "runner_id": runner, "runtime": {"model_id": "fixture"}}]},
        snapshot_sha256="a" * 64,
    )
    runs = RunRepository(db)
    run_id = runs.create_from_version(version_id="version", principal_id="operator", request_key="first", request_sha256="b" * 64)["run_id"]
    url = "/v1/runners/" + runner
    blocked = client.delete(url)
    assert blocked.status_code == 409
    message = blocked.json()["detail"]
    for text in ("PC test", "Project", "Process", "giờ Việt Nam", "Runs"):
        assert text in message
    assert runner not in message and run_id not in message
    assert client.get(url).json()["deleted_at"] is None
    with db.transaction() as conn:
        conn.execute("UPDATE task_runs SET status='skipped' WHERE run_id=?", (run_id,))
        conn.execute("UPDATE process_runs SET status='cancelled',ended_at='2026-11-18T00:00:00Z' WHERE id=?", (run_id,))
        conn.execute("INSERT INTO schedules(id,project_id,process_id,process_version_id,name,cadence,is_active,default_runner_id,next_run_at,created_at,updated_at) VALUES ('schedule','project','process','version','Schedule','daily',1,?,'2026-11-19T00:00:00Z','2026-11-18T00:00:00Z','2026-11-18T00:00:00Z')", (runner,))
    before = runs.get(run_id)
    assert client.delete(url).status_code == 204
    assert runs.get(run_id) == before
    with db.connect() as conn:
        schedule = conn.execute("SELECT is_active,next_run_at FROM schedules").fetchone()
        assert tuple(schedule) == (0, None)
    with pytest.raises(ValueError, match="PC"):
        runs.create_from_version(version_id="version", principal_id="operator", request_key="next", request_sha256="c" * 64)

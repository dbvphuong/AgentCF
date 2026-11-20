"""Regression checks for the UI's persisted Project and editor operations."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(ServerSettings(database_path=tmp_path / "web.sqlite3", artifacts_dir=tmp_path / "artifacts", temporal_enabled=False))
    with TestClient(app) as c:
        assert c.post("/v1/settings/providers", json={"id": "p", "name": "Local", "api_format": "custom", "base_url": "http://localhost"}).status_code == 201
        c.post("/v1/settings/models", json={"id": "m", "provider_id": "p", "name": "Exact model", "model_identifier": "exact-model"})
        c.post("/v1/settings/ai-tool-models", json={"id": "cli-test", "tool_id": "codex", "name": "CLI test model", "model_identifier": "exact-model"}).raise_for_status()
        c.post("/v1/settings/roles", json={"id": "r", "name": "Writer"})
        c.post("/v1/skills", json={"id": "s", "name": "Any configured skill", "is_global": True})
        c.post("/v1/skills/s/versions", json={"id": "sv", "instructions": "Use the supplied input."})
        c.post("/v1/skills/s/versions/sv/publish", json={})
        assert c.post("/v1/agents", json={"id": "a", "name": "PM", "role_id": "r", "model_id": "m", "skill_ids": ["s"]}).status_code == 201
        yield c


def setup_project(c):
    workspace = c.post("/v1/workspaces", json={"name": "Company"}).json()
    project = c.post("/v1/projects", json={"workspace_id": workspace["id"], "name": "Project", "pm_agent_id": "a"}).json()
    process = c.post(f"/v1/projects/{project['id']}/processes", json={"name": "Process"}).json()
    return project, process


def definition():
    return {"definition_format_version": "1", "interpreter_version": "dag-v1", "tasks": [
        {"id": "first", "task_key": "first", "name": "First", "kind": "agent", "agent_id": "a", "skill_id": "s", "runtime": {"adapter": "codex", "model_id": "exact-model"}},
        {"id": "second", "task_key": "second", "name": "Second", "kind": "agent", "agent_id": "a", "skill_id": "s", "runtime": {"adapter": "codex", "model_id": "exact-model"}},
    ], "dependencies": [{"source_task_id": "first", "target_task_id": "second"}]}


def test_persist_team_target_and_restart(client):
    project, process = setup_project(client)
    pid = project["id"]
    assert project["team"][0]["id"] == "a"
    assert client.put(f"/v1/projects/{pid}/team", json={"agent_ids": []}).status_code == 422
    target = {"name": "Approved deliverables", "period": "monthly", "target_count": 10, "completed_count": 3, "starts_on": "2026-11-01", "ends_on": "2026-11-30", "acceptance_criteria": "Human approval"}
    result = client.post(f"/v1/projects/{pid}/targets", json=target)
    assert result.status_code == 201, result.text
    assert result.json()["targets"][0]["completed_count"] == 3
    assert client.post(f"/v1/projects/{pid}/targets", json={**target, "ends_on": "2026-10-01"}).status_code == 422
    assert client.get(f"/v1/projects/{pid}").json()["processes"][0]["id"] == process["id"]
    with TestClient(create_app(ServerSettings(database_path=client.app.state.database.path, temporal_enabled=False))) as reopened:
        assert reopened.get(f"/v1/projects/{pid}").json()["targets"][0]["completed_count"] == 3


def test_publish_is_immutable_cas_and_runs_pin_version(client):
    project, process = setup_project(client)
    path = f"/v1/processes/{process['id']}"
    version = process["versions"][0]
    vpath = f"{path}/versions/{version['id']}"
    saved = client.put(vpath, json={"revision": 1, "definition": definition()})
    assert saved.status_code == 200, saved.text
    assert client.put(vpath, json={"revision": 1, "definition": definition()}).status_code == 422
    assert client.post(vpath + "/validate", json={"revision": 2}).json() == {"valid": True}
    published = client.post(vpath + "/publish", json={"revision": 2})
    assert published.status_code == 200, published.text
    snapshot = published.json()["versions"][0]
    assert snapshot["definition"]["tasks"][0]["skill_snapshot"]["instructions"] == "Use the supplied input."
    assert client.put(vpath, json={"revision": 2, "definition": definition()}).status_code == 422
    new = client.post(path + "/draft").json()["versions"][0]
    assert new["id"] != version["id"] and new["version_number"] == 2
    assert client.get(path).json()["versions"][1] == snapshot
    run = client.post("/v1/runs", json={"process_version_id": version["id"], "input": {"arbitrary": "input"}}, headers={"Idempotency-Key": "ui-run"})
    assert run.status_code == 202, run.text
    assert run.json()["process_version_id"] == version["id"]
    assert client.post(f"/v1/projects/{project['id']}/archive").status_code == 422
    assert client.get(f"/v1/projects/{project['id']}").json()["targets"] == []


@pytest.mark.parametrize("bad", ["cycle", "missing", "duplicate", "model", "team", "mapping"])
def test_reject_invalid_graph(client, bad):
    _, process = setup_project(client)
    graph = deepcopy(definition())
    if bad == "cycle": graph["dependencies"].append({"source_task_id": "second", "target_task_id": "first"})
    if bad == "missing": graph["dependencies"][0]["source_task_id"] = "missing"
    if bad == "duplicate": graph["tasks"][1]["task_key"] = "first"
    if bad == "model": graph["tasks"][0]["runtime"]["model_id"] = "silently-changed-model"
    if bad == "team": graph["tasks"][0]["agent_id"] = "foreign-agent"
    if bad == "mapping": graph["tasks"][0]["input_mapping"] = [{"target": "result", "source": "task_output", "task_id": "second", "pointer": ""}]
    path = f"/v1/processes/{process['id']}/versions/{process['versions'][0]['id']}"
    assert client.put(path, json={"revision": 1, "definition": graph}).status_code == 200
    response = client.post(path + "/publish", json={"revision": 2})
    assert response.status_code == 422, response.text
    assert client.get(f"/v1/processes/{process['id']}").json()["versions"][0]["status"] == "draft"


def test_archive_restore_keeps_schedule_stopped(client):
    project, process = setup_project(client)
    path = f"/v1/processes/{process['id']}"
    vid = process["versions"][0]["id"]
    client.put(f"{path}/versions/{vid}", json={"revision": 1, "definition": definition()})
    client.post(f"{path}/versions/{vid}/publish", json={"revision": 2})
    schedule = client.post(path + f"/schedules?project_id={project['id']}", json={"name": "Daily", "process_version_id": vid}, headers={"Idempotency-Key": "schedule"}).json()
    client.post(f"/v1/schedules/{schedule['id']}/start", headers={"Idempotency-Key": "start"})
    assert client.post(f"/v1/projects/{project['id']}/archive").status_code == 200
    assert client.get(f"/v1/schedules/{schedule['id']}").json()["is_active"] is False
    assert client.post(f"/v1/projects/{project['id']}/restore").status_code == 200
    assert client.get(f"/v1/schedules/{schedule['id']}").json()["is_active"] is False


def test_pairing_expiry_is_rfc3339(client):
    from datetime import datetime
    workspace = client.post("/v1/workspaces", json={"name": "Pairing"}).json()
    code = client.post("/v1/pairing-codes", json={"workspace_id": workspace["id"], "name": "PC", "expires_in_seconds": 600}).json()
    expiry = datetime.fromisoformat(code["expires_at"].replace("Z", "+00:00"))
    assert expiry.tzinfo is not None


def test_local_skill_path_is_persisted_and_published_on_its_own_pc(client):
    project, process = setup_project(client)
    code = client.post("/v1/pairing-codes", json={"workspace_id": project["workspace_id"], "name": "Local PC"}).json()
    paired = client.post("/v1/runners/pair", json={"pairing_code": code["pairing_code"]}).json()
    runner = paired["runner_id"]
    source = "E:\\PC Skills\\Một Skill\\SKILL.md"
    created = client.post("/v1/skills/s/versions", json={
        "id": "local-v2", "source_path": source, "source_runner_id": runner,
    })
    assert created.status_code == 201, created.text
    assert created.json()["source_path"] == source
    assert client.post("/v1/skills/s/versions/local-v2/publish", json={}).status_code == 200
    assert client.patch("/v1/skills/s/versions/local-v2", json={"source_path": "C:\\changed\\SKILL.md", "source_runner_id": runner}).status_code == 409
    graph = definition()
    for task in graph["tasks"]:
        task.update(runner_id=runner, working_directory="E:\\PC output")
    path = f"/v1/processes/{process['id']}/versions/{process['versions'][0]['id']}"
    graph["tasks"][0]["working_directory"] = "relative"
    assert client.put(path, json={"revision": 1, "definition": graph}).status_code == 200
    assert client.post(path + "/validate", json={"revision": 2}).status_code == 422
    graph["tasks"][0]["working_directory"] = "E:\\PC output"
    graph["tasks"][0]["runner_id"] = "wrong-pc"
    assert client.put(path, json={"revision": 2, "definition": graph}).status_code == 200
    assert client.post(path + "/publish", json={"revision": 3}).status_code in {404, 422}
    graph["tasks"][0]["runner_id"] = runner
    assert client.put(path, json={"revision": 3, "definition": graph}).status_code == 200
    published = client.post(path + "/publish", json={"revision": 4})
    assert published.status_code == 200, published.text
    node = published.json()["versions"][0]["definition"]["tasks"][0]
    assert node["skill_snapshot"]["source_path"] == source
    assert node["skill_snapshot"]["source_runner_id"] == runner
    assert node["working_directory"] == "E:\\PC output"


@pytest.mark.parametrize("source", ["SKILL.md", "relative/SKILL.md", "C:SKILL.md", "E:\\skills\\other.txt"])
def test_reject_invalid_skill_file_reference(client, source):
    response = client.post("/v1/skills/s/versions", json={"id": "bad-local", "source_path": source, "source_runner_id": "pc"})
    assert response.status_code == 422


def test_provider_connection_never_returns_response_body_or_secret(client, monkeypatch):
    import httpx
    from agent_cf_server.api import settings
    original = httpx.Client
    observed = []

    def handle(request):
        observed.append(request)
        return httpx.Response(401, json={"error": "sensitive-provider-response"})

    def mock_client(**kwargs):
        return original(transport=httpx.MockTransport(handle), **kwargs)

    client.patch("/v1/settings/providers/p", json={"api_key": "do-not-render-this-key"})
    monkeypatch.setattr(settings.httpx, "Client", mock_client)
    response = client.post("/v1/settings/providers/p/test")
    assert response.status_code == 200
    assert response.json() == {"reachable": True, "ok": False, "http_status": 401}
    assert observed[0].headers["Authorization"] == "Bearer do-not-render-this-key"
    assert "sensitive-provider-response" not in response.text
    assert "do-not-render-this-key" not in response.text


def test_run_list_filters_counts_and_cursor(client):
    project, process = setup_project(client)
    vid = process["versions"][0]["id"]
    path = f"/v1/processes/{process['id']}/versions/{vid}"
    client.put(path, json={"revision": 1, "definition": definition()})
    client.post(path + "/publish", json={"revision": 2})
    for i in range(3):
        client.post("/v1/runs", json={"process_version_id": vid}, headers={"Idempotency-Key": f"run-list-{i}"})
    page = client.get("/v1/runs", params={"project_id": project["id"], "limit": 2}).json()
    assert page["total"] == 3 and len(page["items"]) == 2 and page["next_cursor"]
    second = client.get("/v1/runs", params={"project_id": project["id"], "cursor": page["next_cursor"], "limit": 2}).json()
    assert len(second["items"]) == 1 and second["total"] == 3
    assert second["items"][0]["id"] not in {r["id"] for r in page["items"]}
    match = client.get("/v1/runs", params={"search": page["items"][0]["id"]}).json()
    assert match["total"] == 1
    assert client.get("/v1/runs?started_from=2099-01-01T00:00:00Z").json()["total"] == 0
    assert client.get("/v1/runs?started_from=2026-01-01T00:00:00").status_code == 422


def test_skill_draft_updates_only_before_publish(client):
    client.post("/v1/skills/s/versions", json={"id": "second-draft", "instructions": "Before"})
    path = "/v1/skills/s/versions/second-draft"
    assert client.patch(path, json={"instructions": "After", "tool_ids": []}).json()["instructions"] == "After"
    assert client.post(path + "/publish").status_code == 200
    assert client.patch(path, json={"instructions": "Overwrite"}).status_code == 409
    assert client.get(path).json()["instructions"] == "After"


def test_delete_unused_drafts_and_published_versions(client):
    project, process = setup_project(client)
    assert client.delete(f"/v1/projects/{project['id']}").json() == {"deleted": True}
    assert client.get(f"/v1/processes/{process['id']}").status_code == 404
    project, process = setup_project(client)
    vid = process["versions"][0]["id"]
    path = f"/v1/processes/{process['id']}/versions/{vid}"
    client.put(path, json={"revision": 1, "definition": definition()})
    client.post(path + "/publish", json={"revision": 2})
    assert client.delete(f"/v1/projects/{project['id']}").json() == {"deleted": True}
    assert client.get(path).status_code == 404


def test_draft_for_existing_process_without_versions(client):
    project, _ = setup_project(client)
    with client.app.state.database.transaction() as conn:
        conn.execute("INSERT INTO processes(id,project_id,name) VALUES ('no-version',?,'Existing process')", (project["id"],))
    result = client.post("/v1/processes/no-version/draft")
    assert result.status_code == 200
    assert result.json()["versions"][0]["definition"]["tasks"] == []

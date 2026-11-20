"""Cloning copies configuration, never execution history or active schedules."""
from copy import deepcopy
import json
import sqlite3

import pytest

from test_project_web import client, setup_project, definition  # shared isolated catalog fixture


def rich_project(client):
    project, process = setup_project(client)
    pid, procid = project["id"], process["id"]
    client.patch(f"/v1/projects/{pid}", json={"name": "Video production", "description": "Create and review videos", "workspace_id": project["workspace_id"], "pm_agent_id": "a"})
    client.post("/v1/agents", json={"id": "second-agent", "name": "Reviewer", "role_id": "r", "model_id": "m", "skill_ids": ["s"]})
    graph = definition()
    graph["tasks"][1]["agent_id"] = "second-agent"
    graph["layout"] = {"first": {"x": 50, "y": 60}, "second": {"x": 400, "y": 60}}
    vid = process["versions"][0]["id"]
    path = f"/v1/processes/{procid}/versions/{vid}"
    assert client.put(path, json={"revision": 1, "definition": graph}).status_code == 200
    assert client.post(path + "/publish", json={"revision": 2}).status_code == 200
    draft = client.post(f"/v1/processes/{procid}/draft").json()["versions"][0]
    next_graph = deepcopy(graph)
    next_graph["tasks"][0]["name"] = "Changed only in draft"
    client.put(f"/v1/processes/{procid}/versions/{draft['id']}", json={"revision": draft["revision"], "definition": next_graph})
    client.post(f"/v1/projects/{pid}/targets", json={"name": "November", "period": "monthly", "target_count": 12, "completed_count": 5, "starts_on": "2026-11-01", "ends_on": "2026-11-30", "acceptance_criteria": "PM approval"})
    schedule = client.post(f"/v1/processes/{procid}/schedules?project_id={pid}", json={"name": "Daily", "process_version_id": vid, "input": {"prompt": "Scheduled input"}}, headers={"Idempotency-Key": "schedule"}).json()
    client.post(f"/v1/schedules/{schedule['id']}/start", headers={"Idempotency-Key": "start"})
    run = client.post("/v1/runs", json={"process_version_id": vid, "input": {"secret_business_result": "Source only"}}, headers={"Idempotency-Key": "source-run"}).json()
    extra = client.post(f"/v1/projects/{pid}/processes", json={"name": "Archived configuration"}).json()
    client.post(f"/v1/processes/{extra['id']}/archive")
    return client.get(f"/v1/projects/{pid}").json(), client.get(f"/v1/processes/{procid}").json(), schedule, run


def test_clone_all_configuration_with_new_ids_and_stopped_schedules(client):
    source, process, schedule, run = rich_project(client)
    response = client.post(f"/v1/projects/{source['id']}/clone", json={"name": "Video production copy"}, headers={"Idempotency-Key": "clone-1"})
    assert response.status_code == 201, response.text
    copied = response.json()
    assert copied["id"] != source["id"]
    for key in ("workspace_id", "description", "pm_agent_id", "status", "team"):
        assert copied[key] == source[key]
    assert copied["targets"][0]["id"] != source["targets"][0]["id"]
    for key in ("name", "period", "target_count", "completed_count", "status", "starts_on", "ends_on", "acceptance_criteria"):
        assert copied["targets"][0][key] == source["targets"][0][key]
    assert len(copied["processes"]) == 2
    assert {p["id"] for p in copied["processes"]}.isdisjoint(p["id"] for p in source["processes"])
    assert {p["name"]: p["status"] for p in copied["processes"]} == {p["name"]: p["status"] for p in source["processes"]}
    copied_process = next(p for p in copied["processes"] if p["name"] == process["name"])
    versions = client.get(f"/v1/processes/{copied_process['id']}").json()["versions"]
    assert len(versions) == 2
    for old, new in zip(process["versions"], versions):
        assert old["id"] != new["id"]
        for key in ("definition", "status", "revision", "version_number", "snapshot_sha256", "published_at"):
            assert new[key] == old[key]
    published = next(v for v in versions if v["status"] == "published")
    db = client.app.state.database
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks WHERE process_version_id=?", (published["id"],)).fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM dependencies WHERE process_version_id=?", (published["id"],)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM process_runs WHERE project_id=?", (copied["id"],)).fetchone()[0] == 0
        audit = conn.execute("SELECT data_json FROM audit_events WHERE resource_id=? AND event_type='project_cloned'", (copied["id"],)).fetchone()
        assert json.loads(audit[0])["source_project_id"] == source["id"]
    with pytest.raises(sqlite3.IntegrityError, match="published_version_immutable"):
        with db.transaction() as conn:
            conn.execute("UPDATE process_versions SET revision=99 WHERE id=?", (published["id"],))
    copied_schedule = client.get(f"/v1/processes/{copied_process['id']}/schedules").json()["items"][0]
    assert copied_schedule["id"] != schedule["id"]
    assert copied_schedule["process_version_id"] == published["id"]
    assert copied_schedule["is_active"] is False
    assert copied_schedule["run_input"] == {"prompt": "Scheduled input"}
    assert all(copied_schedule[key] is None for key in ("next_run_at", "last_run_at", "last_run_id"))
    assert client.get(f"/v1/schedules/{schedule['id']}").json()["is_active"] is True
    assert client.get(f"/v1/projects/{source['id']}").json() == source
    assert client.get(f"/v1/runs/{run['id']}").json()["status"] == "queued"
    client.patch(f"/v1/projects/{copied['id']}", json={"name": "Independent", "description": "Changed", "workspace_id": copied["workspace_id"], "pm_agent_id": "a"})
    assert client.get(f"/v1/projects/{source['id']}").json()["name"] == source["name"]


def test_clone_retry_is_deduplicated_and_changed_name_conflicts(client):
    source, _ = setup_project(client)
    path = f"/v1/projects/{source['id']}/clone"
    headers = {"Idempotency-Key": "same-clone"}
    first = client.post(path, json={"name": "Copy"}, headers=headers)
    repeated = client.post(path, json={"name": "Copy"}, headers=headers)
    assert repeated.json()["id"] == first.json()["id"]
    assert client.post(path, json={"name": "Another copy"}, headers=headers).status_code == 409
    assert len(client.get("/v1/projects").json()) == 2
    assert client.post(path, json={"name": "   "}).status_code == 422
    assert client.post("/v1/projects/missing/clone", json={"name": "Copy"}).status_code == 404


def test_clone_rolls_back_if_a_child_fails(client, monkeypatch):
    source, _ = setup_project(client)
    from agent_cf_server.infrastructure.projects.management import ProjectManagement
    def fail(*args):
        raise ValueError("Cannot copy this version")
    monkeypatch.setattr(ProjectManagement, "_clone_versions", fail)
    result = client.post(f"/v1/projects/{source['id']}/clone", json={"name": "Broken copy"})
    assert result.status_code == 422
    assert [p["id"] for p in client.get("/v1/projects").json()] == [source["id"]]


def test_clone_inactive_project_preserves_status(client):
    source, _ = setup_project(client)
    client.post(f"/v1/projects/{source['id']}/archive")
    result = client.post(f"/v1/projects/{source['id']}/clone", json={"name": "Inactive copy"})
    assert result.status_code == 201
    assert result.json()["status"] == "archived"

"""Aggregate deletion removes owned history and preserves other Projects/catalog/PC files."""

import sqlite3

import pytest

from test_project_web import client, setup_project, definition
from agent_cf_server.infrastructure.runs.artifact_cleanup import cleanup_artifacts


def published(client):
    project, process = setup_project(client)
    vid = process["versions"][0]["id"]
    path = f"/v1/processes/{process['id']}/versions/{vid}"
    client.put(path, json={"revision": 1, "definition": definition()}).raise_for_status()
    client.post(path + "/publish", json={"revision": 2}).raise_for_status()
    return project, process, vid


def history(client, state="succeeded"):
    project, process, vid = published(client)
    run = client.post("/v1/runs", json={"process_version_id": vid}, headers={"Idempotency-Key": project["id"]}).json()
    schedule = client.post(f"/v1/processes/{process['id']}/schedules?project_id={project['id']}", json={"name":"Daily", "process_version_id":vid}, headers={"Idempotency-Key":project["id"]}).json()
    db = client.app.state.database
    rid, tid = run["id"], run["task_runs"][0]["id"]
    aid = "attempt-" + rid
    at = "2026-11-19T00:00:00Z"
    with db.transaction() as c:
        c.execute("INSERT INTO runners(id,workspace_id,status) VALUES (?,?,'offline')", (rid,project["workspace_id"]))
        c.execute("INSERT INTO runner_sessions(id,runner_id,status,created_at) VALUES (?,?,'expired',?)", (rid,rid,at))
        c.execute("INSERT INTO attempts(id,task_run_id,run_id,runner_id,session_id,generation,status,claimed_at,ended_at,execution_deadline_at) VALUES (?,?,?,?,?,1,?,?,?,?)", (aid,tid,rid,rid,rid,state,at,at,at))
        c.execute("INSERT INTO execution_grants(attempt_id,task_run_id,runner_id,session_id,generation,token_hash,expires_at) VALUES (?,?,?,?,1,?,?)", (aid,tid,rid,rid,rid,at))
        c.execute("UPDATE task_runs SET status=? WHERE run_id=?", (state,rid))
        c.execute("UPDATE process_runs SET status=?,ended_at=? WHERE id=?", (state,at,rid))
        c.execute("INSERT INTO artifacts VALUES (?,?, 'output','text/plain',4,?,'available',?,?)", (rid,aid,"f"*64,aid+"/output.txt",at))
        c.execute("INSERT INTO engine_inbox VALUES (?,?,'hash','{}',?)", (rid,rid,at))
        c.execute("INSERT INTO review_decisions(id,task_run_id,attempt_id,reviewer_agent_id,decision,decision_key) VALUES (?,?,?,'a','approved',?)", (rid,tid,aid,rid))
        c.execute("INSERT INTO human_decisions(id,run_id,task_run_id,decision,decision_key,decided_by) VALUES (?,?,?,'approved',?,'operator')", (rid,rid,tid,rid))
        c.execute("INSERT INTO agent_token_usage(id,agent_id,run_id,task_run_id,recorded_at) VALUES (?,'a',?,?,?)", (rid,rid,tid,at))
        c.execute("INSERT INTO run_error_acknowledgments VALUES (?,'operator','seen',?)", (rid,at))
        c.execute("INSERT INTO schedule_ticks VALUES (?,?,?,?,'triggered',?)", (rid,schedule["id"],at,rid,at))
    file = db.path.parent / "artifacts" / aid / "output.txt"
    file.parent.mkdir(parents=True)
    file.write_text("test")
    return project, process, rid, file


@pytest.mark.parametrize("state", ["succeeded", "failed", "cancelled"])
def test_delete_full_history_keeps_other_project_catalog_and_pc_files(client, tmp_path, state):
    project, process, run, file = history(client, state)
    other, other_process, other_run, other_file = history(client)
    pc_file = tmp_path / "pc-output.txt"
    pc_file.write_text("keep")
    response = client.delete(f"/v1/projects/{project['id']}")
    assert response.status_code == 200, response.text
    assert response.json() == {"deleted":True}
    for url in (f"/v1/projects/{project['id']}", f"/v1/processes/{process['id']}", f"/v1/runs/{run}"):
        assert client.get(url).status_code == 404
    assert client.get(f"/v1/runs/{other_run}").status_code == 200
    assert client.get("/v1/skills/s").status_code == 200
    assert client.get("/v1/agents/a").status_code == 200
    assert not file.exists() and other_file.exists() and pc_file.read_text() == "keep"
    with client.app.state.database.connect() as c:
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        for table in ("process_runs","task_runs","attempts","artifacts","engine_inbox","engine_outbox","review_decisions","human_decisions","schedule_ticks","agent_token_usage","run_error_acknowledgments"):
            assert c.execute(f"SELECT count(*) FROM {table}").fetchone()[0] >= 1
        assert c.execute("SELECT count(*) FROM artifact_cleanup").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM audit_events WHERE event_type='project_deleted' AND resource_id=?", (project["id"],)).fetchone()[0] == 1


def test_project_delete_rolls_back_history_and_keeps_files_on_error(client):
    project, _, run, file = history(client)
    with client.app.state.database.transaction() as c:
        c.execute("CREATE TRIGGER reject_project_delete BEFORE DELETE ON projects BEGIN SELECT RAISE(ABORT,'fixture'); END")
    assert client.delete(f"/v1/projects/{project['id']}").status_code == 409
    assert file.exists()
    assert client.get(f"/v1/runs/{run}").status_code == 200
    with client.app.state.database.connect() as c:
        assert c.execute("SELECT count(*) FROM artifact_cleanup").fetchone()[0] == 0
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            c.execute("DELETE FROM run_events")


@pytest.mark.parametrize("status", ["queued", "running", "reconciling", "cancelling"])
def test_unfinished_run_blocks_delete_then_completed_run_can_be_deleted(client, status):
    project, _, vid = published(client)
    run = client.post("/v1/runs", json={"process_version_id":vid}, headers={"Idempotency-Key":"pending"}).json()
    with client.app.state.database.transaction() as c:
        c.execute("UPDATE process_runs SET status=? WHERE id=?", (status, run["id"]))
    rejected = client.delete(f"/v1/projects/{project['id']}")
    assert rejected.status_code == 422 and "Run" in rejected.json()["detail"]
    with client.app.state.database.transaction() as c:
        c.execute("UPDATE task_runs SET status='cancelled' WHERE run_id=?", (run["id"],))
        c.execute("UPDATE process_runs SET status='cancelled',ended_at='2026-11-19T00:00:00Z' WHERE id=?", (run["id"],))
    assert client.delete(f"/v1/projects/{project['id']}").json() == {"deleted":True}


def test_deleting_one_process_preserves_project_and_sibling_history(client):
    project, process, run, file = history(client)
    sibling = client.post(f"/v1/projects/{project['id']}/processes", json={"name":"Sibling"}).json()
    assert client.delete(f"/v1/processes/{process['id']}").json() == {"deleted": True}
    assert client.get(f"/v1/projects/{project['id']}").status_code == 200
    assert client.get(f"/v1/processes/{sibling['id']}").status_code == 200
    assert client.get(f"/v1/runs/{run}").status_code == 404
    assert not file.exists()


def test_shared_catalog_cannot_delete_until_last_process_removed(client):
    first, _ = setup_project(client)
    second, proc, _ = published(client)
    assert client.delete(f"/v1/projects/{first['id']}").status_code == 200
    for kind, id in (("skills","s"),("agents","a")):
        blocked = client.delete(f"/v1/{kind}/{id}")
        assert blocked.status_code == 409, blocked.text
        assert proc["name"] in blocked.json()["detail"]
    assert client.delete(f"/v1/projects/{second['id']}").status_code == 200
    assert client.delete("/v1/skills/s").status_code == 204
    assert client.delete("/v1/agents/a").status_code == 204


def test_draft_references_also_block_catalog_deletion(client):
    project, process = setup_project(client)
    vid=process["versions"][0]["id"]
    client.put(f"/v1/processes/{process['id']}/versions/{vid}",json={"revision":1,"definition":definition()}).raise_for_status()
    assert client.delete("/v1/skills/s").status_code == 409
    assert client.delete("/v1/agents/a").status_code == 409


def test_catalog_membership_and_snapshot_alone_do_not_block_agent_deletion(client):
    project, _ = setup_project(client)
    client.post("/v1/agents/a/snapshot").raise_for_status()
    assert client.delete("/v1/agents/a").status_code == 204
    remaining = client.get(f"/v1/projects/{project['id']}").json()
    assert remaining["pm_agent_id"] is None and remaining["team"] == []


def test_server_object_cleanup_failure_is_retried_without_touching_external_file(client, monkeypatch, tmp_path):
    project, _, _, file = history(client)
    from pathlib import Path
    original = Path.unlink
    def blocked(path, *args, **kwargs):
        if path == file:
            raise PermissionError("fixture locked")
        return original(path, *args, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(Path,"unlink",blocked)
        assert client.delete(f"/v1/projects/{project['id']}").status_code == 200
    assert file.exists()
    cleanup_artifacts(client.app.state.database,file.parents[1])
    assert not file.exists()
    outside=tmp_path / "outside.txt"
    outside.write_text("keep")
    with client.app.state.database.transaction() as c:
        c.execute("INSERT INTO artifact_cleanup(storage_key) VALUES (?)", (str(outside),))
    cleanup_artifacts(client.app.state.database,file.parents[1])
    assert outside.read_text() == "keep"

"""Project-specific Skill visibility is enforced beyond the dropdown."""

import pytest

from test_project_web import client, setup_project, definition


def test_scope_crud_filter_and_validation(client):
    first, _ = setup_project(client)
    second, _ = setup_project(client)
    a, b = first["id"], second["id"]
    assert client.post("/v1/skills", json={"id": "missing", "name": "Missing scope"}).status_code == 422
    assert client.post("/v1/skills", json={"id": "mixed", "name": "Mixed", "is_global": True, "project_ids": [a]}).status_code == 422
    assert client.post("/v1/skills", json={"id": "unknown", "name": "Unknown", "project_ids": ["no-project"]}).status_code == 422
    assert client.get("/v1/skills/unknown").status_code == 404
    created = client.post("/v1/skills", json={"id": "private", "name": "Private", "project_ids": [a, b, a]})
    assert created.status_code == 201, created.text
    assert set(created.json()["project_ids"]) == {a, b}
    assert created.json()["is_global"] is False
    assert {p["name"] for p in created.json()["projects"]} == {first["name"]}
    assert "private" in {s["id"] for s in client.get("/v1/skills", params={"project_id": b}).json()}
    changed = client.patch("/v1/skills/private", json={"project_ids": [a]})
    assert changed.status_code == 200 and changed.json()["project_ids"] == [a]
    assert "private" not in {s["id"] for s in client.get("/v1/skills", params={"project_id": b}).json()}
    assert "s" in {s["id"] for s in client.get("/v1/skills", params={"project_id": b}).json()}
    assert client.patch("/v1/skills/private", json={"project_ids": []}).status_code == 422
    assert client.get("/v1/skills/private").json()["project_ids"] == [a]
    globalized = client.patch("/v1/skills/private", json={"is_global": True, "project_ids": []})
    assert globalized.status_code == 200 and globalized.json()["is_global"] is True
    assert "private" in {s["id"] for s in client.get("/v1/skills", params={"project_id": b}).json()}


def test_publish_and_new_run_check_current_scope_without_changing_history(client):
    first, process = setup_project(client)
    second, _ = setup_project(client)
    a, b = first["id"], second["id"]
    path = f"/v1/processes/{process['id']}/versions/{process['versions'][0]['id']}"
    assert client.put(path, json={"revision": 1, "definition": definition()}).status_code == 200
    assert client.patch("/v1/skills/s", json={"is_global": False, "project_ids": [b]}).status_code == 200
    assert client.post(path + "/publish", json={"revision": 2}).status_code == 422
    assert client.patch("/v1/skills/s", json={"project_ids": [a, b]}).status_code == 200
    published = client.post(path + "/publish", json={"revision": 2}).json()["versions"][0]
    payload = {"process_version_id": published["id"], "input": {}}
    run = client.post("/v1/runs", json=payload, headers={"Idempotency-Key": "scope-allowed"})
    assert run.status_code == 202
    assert client.patch("/v1/skills/s", json={"project_ids": [b]}).status_code == 200
    rejected = client.post("/v1/runs", json=payload, headers={"Idempotency-Key": "scope-blocked"})
    assert rejected.status_code == 422
    assert client.get(f"/v1/runs/{run.json()['id']}").json() == run.json()
    assert client.get(path).json() == published


@pytest.mark.parametrize("shared", [False, True])
def test_delete_project_detaches_scope_without_deleting_or_globalizing_skill(client, shared):
    project, process = setup_project(client)
    other, _ = setup_project(client)
    project_ids = [project["id"], other["id"]] if shared else [project["id"]]
    assert client.patch("/v1/skills/s", json={"is_global": False, "project_ids": project_ids}).status_code == 200
    before = client.get("/v1/skills/s/versions/sv").json()
    response = client.delete(f"/v1/projects/{project['id']}")
    assert response.status_code == 200, response.text
    assert response.json() == {"deleted": True}
    assert client.get(f"/v1/projects/{project['id']}").status_code == 404
    assert client.get(f"/v1/processes/{process['id']}").status_code == 404
    skill = client.get("/v1/skills/s").json()
    assert skill["is_global"] is False
    assert skill["project_ids"] == ([other["id"]] if shared else [])
    assert client.get("/v1/skills/s/versions/sv").json() == before
    available = {s["id"] for s in client.get("/v1/skills", params={"project_id": other["id"]}).json()}
    assert ("s" in available) is shared
    # A Skill left without a Project can be assigned again explicitly.
    assert client.patch("/v1/skills/s", json={"project_ids": [other["id"]]}).status_code == 200


def test_delete_published_project_preserves_skill_but_removes_membership(client):
    project, process = setup_project(client)
    assert client.patch("/v1/skills/s", json={"is_global": False, "project_ids": [project["id"]]}).status_code == 200
    path = f"/v1/processes/{process['id']}/versions/{process['versions'][0]['id']}"
    assert client.put(path, json={"revision": 1, "definition": definition()}).status_code == 200
    assert client.post(path + "/publish", json={"revision": 2}).status_code == 200
    response = client.delete(f"/v1/projects/{project['id']}")
    assert response.status_code == 200, response.text
    assert response.json() == {"deleted": True}
    assert client.get("/v1/skills/s").json()["project_ids"] == []


def test_clone_reuses_skill_and_adds_clone_membership(client):
    project, _ = setup_project(client)
    assert client.patch("/v1/skills/s", json={"is_global": False, "project_ids": [project["id"]]}).status_code == 200
    cloned = client.post(f"/v1/projects/{project['id']}/clone", json={"name": "Clone"}, headers={"Idempotency-Key": "scope-clone"})
    assert cloned.status_code == 201, cloned.text
    scope = client.get("/v1/skills/s").json()
    assert set(scope["project_ids"]) == {project["id"], cloned.json()["id"]}
    assert len(client.get("/v1/skills").json()) == 1

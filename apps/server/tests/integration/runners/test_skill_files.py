import httpx
import pytest

from test_runner_actions import env, pair
from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.connection.skill_files import list_skill_files
from agent_cf_server.infrastructure.runners.file_browser import FileBrowser


def test_metadata_file_is_saved_atomically_and_published_versions_stay_unchanged(env):
    client, db = env
    runner, _ = pair(client)
    payload = {"id": "s", "name": "Skill", "is_global": True,
               "source_path": "E:\\Skills\\Tiếng Việt\\main.md", "source_runner_id": runner}
    created = client.post("/v1/skills", json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["source_path"] == payload["source_path"]
    versions = client.get("/v1/skills/s/versions").json()
    assert len(versions) == 1 and versions[0]["status"] == "draft"
    version = versions[0]["id"]
    client.post(f"/v1/skills/s/versions/{version}/publish", json={}).raise_for_status()
    original = client.get(f"/v1/skills/s/versions/{version}").json()
    updated = client.patch("/v1/skills/s", json={"source_path": "E:\\Skills\\second.MD", "source_runner_id": runner})
    assert updated.status_code == 200
    assert updated.json()["source_path"].endswith("second.MD")
    assert client.get(f"/v1/skills/s/versions/{version}").json() == original
    assert len(client.get("/v1/skills/s/versions").json()) == 2
    client.patch("/v1/skills/s", json={"description": "Metadata only"}).raise_for_status()
    assert client.get("/v1/skills/s").json()["source_path"].endswith("second.MD")
    # Invalid source must roll back the metadata update too.
    assert client.patch("/v1/skills/s", json={"name": "Wrong", "source_path": "relative.md", "source_runner_id": runner}).status_code == 422
    assert client.get("/v1/skills/s").json()["name"] == "Skill"
    for bad in ({"source_runner_id": "missing"}, {"source_path": "E:\\skill.txt"}, {"source_runner_id": None}):
        assert client.post("/v1/skills", json={**payload, "id": "invalid", "name": "Invalid", **bad}).status_code == 422
        assert client.get("/v1/skills/invalid").status_code == 404


def test_file_chooser_round_trip_uses_client_disk_and_requires_own_session(env, tmp_path, monkeypatch):
    client, _ = env
    runner, auth = pair(client)
    other, other_auth = pair(client)
    session = client.post(f"/v1/runners/{runner}/sessions", json={"client_version": "test"}, headers=auth).json()["id"]
    directory = tmp_path / "Skill có ref"
    directory.mkdir()
    (directory / "main.md").write_text("Read refs/data.txt", encoding="utf-8")
    (directory / "refs").mkdir()
    (directory / "secret.txt").write_text("Not returned", encoding="utf-8")
    endpoint = f"/v1/runners/{runner}/skill-files"
    pending = client.post(endpoint, json={"path": str(directory)})
    assert pending.status_code == 201
    request_id = pending.json()["id"]
    body = {"session_id": session, "result": {"error": "Test error"}}
    assert client.post(f"{endpoint}/{request_id}/result", json=body).status_code == 401
    assert client.post(f"{endpoint}/{request_id}/result", json=body, headers=other_auth).status_code == 401
    assert client.get(f"/v1/runners/{other}/skill-files/{request_id}").status_code == 404
    assert client.post(f"{endpoint}/{request_id}/result", json={**body, "session_id": "wrong"}, headers=auth).status_code == 403
    manager = ClientSessionManager(tmp_path / "credentials.json")
    manager.save_credentials(runner, auth["Authorization"][7:], "http://testserver")
    manager.current_session_id = session
    original_client = httpx.Client

    def transport(request):
        response = client.request(request.method, str(request.url), content=request.content, headers=request.headers)
        return httpx.Response(response.status_code, content=response.content, headers=response.headers)

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(transport), **kwargs))
    manager.send_heartbeat()
    result = client.get(f"{endpoint}/{request_id}").json()
    assert result["status"] == "completed"
    assert {e["name"] for e in result["result"]["entries"]} == {"refs", "main.md"}
    assert all("content" not in e for e in result["result"]["entries"])
    assert client.post(endpoint, json={"path": "relative"}).status_code == 422


def test_directory_listing_errors_and_markdown_only(tmp_path):
    (tmp_path / "main.MD").write_text("# Skill", encoding="utf-8")
    (tmp_path / "other.bin").write_bytes(b"binary")
    listing = list_skill_files(str(tmp_path / "main.MD"))
    assert listing["path"] == str(tmp_path.resolve())
    assert [e["name"] for e in listing["entries"]] == ["main.MD"]
    assert "error" in list_skill_files(str(tmp_path / "missing"))
    assert "error" in list_skill_files("relative")


def test_browse_requests_expire_and_are_bounded(monkeypatch):
    clock = [0]
    monkeypatch.setattr("agent_cf_server.infrastructure.runners.file_browser.monotonic", lambda: clock[0])
    browser = FileBrowser()
    first = browser.create("pc", None)
    for _ in range(127):
        browser.create("pc", None)
    with pytest.raises(ValueError):
        browser.create("pc", None)
    assert len(browser.pending("pc")) == 8
    clock[0] = 61
    with pytest.raises(KeyError):
        browser.get("pc", first["id"])
    assert browser.pending("pc") == []
    browser.create("pc", None)

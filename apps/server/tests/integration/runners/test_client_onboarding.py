import time

from test_runner_actions import env


def test_pairing_requires_confirmation_session_and_actual_heartbeat(env):
    client, db = env
    code = client.post("/v1/pairing-codes", json={"workspace_id": "ws", "name": "Web name"}).json()
    assert len(code["pairing_code"]) == 64
    state_url = "/v1/pairing-codes/" + code["id"]
    assert client.get(state_url).json()["status"] == "pending"
    preview = client.post("/v1/pairing-codes/inspect", json={"pairing_code": code["pairing_code"]})
    assert preview.status_code == 200
    assert preview.json()["workspace_name"] == "Workspace"
    assert "runner_token" not in preview.text and "pairing_code" not in preview.text
    paired = client.post("/v1/runners/pair", json={"pairing_code": code["pairing_code"], "name": "Confirmed PC"}).json()
    from datetime import datetime
    assert datetime.fromisoformat(paired["runner"]["credential_expires_at"].replace("Z", "+00:00"))
    rid = paired["runner_id"]
    auth = {"Authorization": "Bearer " + paired["runner_token"]}
    assert client.get(f"/v1/runners/{rid}").json()["display_status"] == "offline"
    assert client.get(state_url).json()["status"] == "paired"
    session = client.post(f"/v1/runners/{rid}/sessions", json={"client_version": "0.2.0", "os_name": "Windows test"}, headers=auth).json()["id"]
    assert client.get(state_url).json()["status"] == "paired"
    assert client.get(f"/v1/runners/{rid}").json()["display_status"] == "offline"
    client.post(f"/v1/runners/{rid}/heartbeat", json={"session_id": session}, headers=auth).raise_for_status()
    status = client.get(state_url).json()
    assert status["status"] == "connected" and status["name"] == "Confirmed PC"
    assert client.get(f"/v1/runners/{rid}").json()["display_status"] == "online"
    assert client.get(f"/v1/runners/{rid}").json()["os_name"] == "Windows test"
    assert client.post("/v1/pairing-codes/inspect", json={"pairing_code": code["pairing_code"]}).status_code == 401
    assert client.post("/v1/runners/pair", json={"pairing_code": code["pairing_code"]}).status_code == 401
    assert client.delete(f"/v1/runners/{rid}/sessions/{session}").status_code == 401
    assert client.delete(f"/v1/runners/{rid}/sessions/{session}", headers=auth).status_code == 204
    assert client.get(f"/v1/runners/{rid}").json()["display_status"] == "offline"
    client.delete(f"/v1/runners/{rid}").raise_for_status()
    assert client.get(state_url).json()["status"] == "removed"


def test_expired_pairing_is_visible_and_cannot_be_consumed(env):
    client, db = env
    code = client.post("/v1/pairing-codes", json={"workspace_id": "ws", "name": "Expired PC"}).json()
    with db.transaction() as conn:
        conn.execute("UPDATE runner_pairing_codes SET expires_at='2000-01-01T00:00:00Z' WHERE id=?", (code["id"],))
    assert client.get("/v1/pairing-codes/"+code["id"]).json()["status"] == "expired"
    assert client.post("/v1/pairing-codes/inspect", json={"pairing_code": code["pairing_code"]}).status_code == 401
    assert client.post("/v1/runners/pair", json={"pairing_code": code["pairing_code"]}).status_code == 401
    assert client.get("/v1/pairing-codes/missing").status_code == 404


def test_installer_download_is_fixed_configured_path(tmp_path):
    from fastapi.testclient import TestClient
    from agent_cf_server.bootstrap.server import create_app
    from agent_cf_server.bootstrap.config import ServerSettings
    artifact = tmp_path / "installer.exe"
    with TestClient(create_app(ServerSettings(database_path=tmp_path/"db.sqlite3", temporal_enabled=False, client_installer_path=artifact))) as client:
        assert not client.get("/v1/client/desktop").json()["installer_available"]
        assert client.get("/v1/client/windows-installer").status_code == 503
        artifact.write_bytes(b"MZ installer fixture")
        assert client.get("/v1/client/desktop").json()["installer_available"]
        response = client.get("/v1/client/windows-installer?path=C:/secret.txt")
        assert response.status_code == 200 and response.content == artifact.read_bytes()
        assert "CF" in response.headers["content-disposition"]

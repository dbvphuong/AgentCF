from fastapi.testclient import TestClient

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app


def test_startup_migrates_and_health_has_only_safe_metadata(tmp_path):
    app = create_app(ServerSettings(database_path=tmp_path / "health.sqlite3", temporal_enabled=False))
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["database"]["schema_version"] >= 1
        assert response.json()["temporal"] == {"configured": False}
        assert str(tmp_path) not in response.text
        assert client.get("/readyz").json() == {"status": "ok", "temporal": "disabled"}
        assert client.post("/v1/processes", json={}).status_code == 404
        assert client.post("/v1/runs", json={}).status_code == 422


def test_missing_temporal_is_not_reported_ready(tmp_path, monkeypatch):
    async def unavailable(settings):
        raise ConnectionError("sensitive connection details")

    monkeypatch.setattr("agent_cf_server.api.health.temporal_is_ready", unavailable)
    app = create_app(ServerSettings(database_path=tmp_path / "health.sqlite3"))
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable", "component": "temporal"}


def test_restart_reads_existing_migrated_database(tmp_path):
    settings = ServerSettings(database_path=tmp_path / "restart.sqlite3", temporal_enabled=False)
    for _ in range(2):
        with TestClient(create_app(settings)) as client:
            assert client.get("/healthz").status_code == 200

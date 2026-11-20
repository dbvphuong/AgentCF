import pytest
from pydantic import ValidationError

from agent_cf_server.bootstrap.config import ServerSettings, load_settings


def test_environment_is_validated(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_CF_SERVER_PORT", "8123")
    monkeypatch.setenv("AGENT_CF_SERVER_DATABASE_PATH", str(tmp_path / "business.sqlite3"))
    monkeypatch.setenv("AGENT_CF_SERVER_TEMPORAL_ENABLED", "false")
    settings = load_settings()
    assert settings.port == 8123
    assert settings.database_path == tmp_path / "business.sqlite3"
    assert settings.temporal_enabled is False


def test_default_database_path_is_absolute():
    assert ServerSettings().database_path.is_absolute()


@pytest.mark.parametrize("values", [
    {"host": "0.0.0.0"}, {"port": 0}, {"request_timeout_seconds": 0},
    {"temporal_address": "https://localhost:7233"},
    {"temporal_address": "host:bad"}, {"unknown_option": True},
    {"temporal_address": "example.com:7233"},
])
def test_invalid_configuration_fails_before_start(values):
    with pytest.raises(ValidationError):
        ServerSettings(**values)

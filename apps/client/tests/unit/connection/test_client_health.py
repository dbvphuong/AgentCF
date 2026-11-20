import json

import httpx
import pytest

from agent_cf_client.cli import main
from agent_cf_client.config import ClientConfig
from agent_cf_client.connection.health import HealthCheckError, ServerHealth, check_server, parse_health


HEALTH = {"status": "ok", "database": {"schema_version": 2}, "temporal": {"configured": True}}


def test_default_config_and_environment():
    assert ClientConfig.from_environment({}) == ClientConfig()
    assert ClientConfig.from_environment({"AGENT_CF_CLIENT_SERVER_URL": "https://example.org", "AGENT_CF_CLIENT_TIMEOUT_SECONDS": "2.5"}).timeout_seconds == 2.5


@pytest.mark.parametrize("url", ["ftp://localhost", "http://example.org", "http://user:password@localhost", "http://localhost/path", "http://localhost?token=secret", "http://localhost:99999", "file:///tmp/server", "http://localhost/#secret"])
def test_config_rejects_unsafe_server_origins(url):
    with pytest.raises(ValueError):
        ClientConfig(server_url=url)


@pytest.mark.parametrize("timeout", [0, -1, 61, float("inf"), float("nan")])
def test_config_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        ClientConfig(timeout_seconds=timeout)


def test_environment_rejects_non_numeric_timeout():
    with pytest.raises(ValueError, match="must be a number"):
        ClientConfig.from_environment({"AGENT_CF_CLIENT_TIMEOUT_SECONDS": "forever"})


def test_check_server_requests_safe_health_only():
    def handle(request):
        assert str(request.url) == "http://127.0.0.1:8000/healthz"
        assert request.method == "GET"
        assert "authorization" not in request.headers
        return httpx.Response(200, json=HEALTH)

    assert check_server(ClientConfig(), transport=httpx.MockTransport(handle)) == ServerHealth(2, True)


def test_does_not_treat_temporal_configuration_as_connectivity():
    assert parse_health({**HEALTH, "temporal": {"configured": False}}) == ServerHealth(2, False)


@pytest.mark.parametrize("payload", [None, {}, {**HEALTH, "status": "failed"}, {**HEALTH, "database": {"schema_version": True}}, {**HEALTH, "database": {"schema_version": 0}}, {**HEALTH, "temporal": {"configured": "true"}}])
def test_rejects_invalid_health_contract(payload):
    with pytest.raises(HealthCheckError, match="invalid health response"):
        parse_health(payload)


def test_rejects_non_json_http_error_and_oversized_response():
    responses = [httpx.Response(503, text="private detail"), httpx.Response(200, text="not json"), httpx.Response(200, text="x" * 16385)]
    for response in responses:
        with pytest.raises(HealthCheckError) as error:
            check_server(ClientConfig(), transport=httpx.MockTransport(lambda _: response))
        assert "private detail" not in str(error.value)


def test_connection_error_is_safe():
    def fail(request):
        raise httpx.ConnectError("private detail", request=request)

    with pytest.raises(HealthCheckError, match="Unable to connect") as error:
        check_server(ClientConfig(), transport=httpx.MockTransport(fail))
    assert "private detail" not in str(error.value)


def test_oversized_stream_is_stopped_before_reading_entire_body():
    class Body(httpx.SyncByteStream):
        chunks_read = 0

        def __iter__(self):
            for _ in range(1000):
                self.chunks_read += 1
                yield b"x" * 4096

    body = Body()
    with pytest.raises(HealthCheckError, match="oversized"):
        check_server(ClientConfig(), transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=body)))
    assert body.chunks_read == 5


def test_cli_reports_safe_json_and_error(monkeypatch, capsys):
    monkeypatch.setattr("agent_cf_client.cli.check_server", lambda _: ServerHealth(2, True))
    assert main(["check"]) == 0
    assert json.loads(capsys.readouterr().out) == HEALTH

    def fail(_):
        raise HealthCheckError("Unable to connect")

    monkeypatch.setattr("agent_cf_client.cli.check_server", fail)
    assert main(["check"]) == 1
    assert "Unable to connect" in capsys.readouterr().err


def test_cli_flags_override_invalid_environment(monkeypatch):
    monkeypatch.setenv("AGENT_CF_CLIENT_SERVER_URL", "invalid")
    monkeypatch.setenv("AGENT_CF_CLIENT_TIMEOUT_SECONDS", "invalid")

    def check(config):
        assert config == ClientConfig(server_url="http://localhost:8081", timeout_seconds=2)
        return ServerHealth(2, True)

    monkeypatch.setattr("agent_cf_client.cli.check_server", check)
    assert main(["check", "--server-url", "http://localhost:8081", "--timeout", "2"]) == 0

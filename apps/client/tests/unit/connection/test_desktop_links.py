import sys
import pytest

from agent_cf_client.desktop.links import parse_connection_link, connection_link
from agent_cf_client.connection.client_session import ClientSessionManager


def test_link_is_data_only_and_uses_validated_server_origin():
    value = connection_link("http://127.0.0.1:5173", "a" * 64)
    parsed = parse_connection_link(value)
    assert parsed.server_url == "http://127.0.0.1:5173" and parsed.pairing_code == "a" * 64
    for bad in ("https://example.com", "agentcf://run/#command=cmd", "agentcf://connect/?server=foo", value+"&cmd=cmd.exe", value+"&code=bbb", value.replace('127.0.0.1','192.168.1.2'), value.replace("a"*64,"bad-code")):
        with pytest.raises(ValueError):
            parse_connection_link(bad)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI")
def test_desktop_credentials_are_protected_for_current_windows_user(tmp_path):
    path = tmp_path / "credentials.dpapi"
    manager = ClientSessionManager(path, protect_credentials=True)
    manager.save_credentials("pc-1", "a-private-runner-token", "http://127.0.0.1:8000")
    assert b"a-private-runner-token" not in path.read_bytes()
    assert path.read_bytes().startswith(b"AGENTCF-DPAPI\0")
    assert manager.get_credentials()["runner_token"] == "a-private-runner-token"


def test_pairing_error_detail_is_extracted_from_server_response(tmp_path, monkeypatch):
    path = tmp_path / "credentials.dpapi"
    manager = ClientSessionManager(path, protect_credentials=False)
    import httpx
    def mock_post(*args, **kwargs):
        return httpx.Response(409, json={"detail": "PC còn tác vụ đang thực thi; dừng hoặc chờ hoàn tất trước khi đổi kết nối."}, request=httpx.Request("POST", "http://test"))
    monkeypatch.setattr(httpx.Client, "post", mock_post)
    with pytest.raises(ConnectionError) as exc_info:
        manager.pair("http://127.0.0.1:8000", "code-123")
    assert str(exc_info.value) == "PC còn tác vụ đang thực thi; dừng hoặc chờ hoàn tất trước khi đổi kết nối."

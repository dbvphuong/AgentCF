"""Strict, data-only application links. No commands or executable paths from Web."""

from dataclasses import dataclass
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from agent_cf_client.config import ClientConfig


@dataclass(frozen=True)
class ConnectionLink:
    server_url: str
    pairing_code: str


def parse_connection_link(value: str) -> ConnectionLink:
    if len(value) > 8192 or any(c in value for c in ('\0', '\r', '\n')):
        raise ValueError("Liên kết CF Client không hợp lệ")
    url = urlsplit(value)
    if url.scheme != "agentcf" or url.netloc != "connect" or url.path not in ("", "/") or url.query:
        raise ValueError("Chỉ hỗ trợ liên kết agentcf://connect")
    data = parse_qs(url.fragment, strict_parsing=True)
    if set(data) != {"server", "code"} or any(len(v) != 1 for v in data.values()):
        raise ValueError("Liên kết kết nối thiếu hoặc thừa thông tin")
    server = ClientConfig(server_url=data["server"][0]).server_url.rstrip("/")
    code = data["code"][0]
    if not re.fullmatch(r"[a-fA-F0-9]{32}|[a-fA-F0-9]{64}", code):
        raise ValueError("Mã ghép nối không hợp lệ")
    return ConnectionLink(server, code)


def connection_link(server_url: str, pairing_code: str) -> str:
    value = "agentcf://connect/#" + urlencode({"server": server_url, "code": pairing_code})
    parse_connection_link(value)
    return value

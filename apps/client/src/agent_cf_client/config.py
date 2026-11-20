"""Environment configuration for the Client connection check."""

from dataclasses import dataclass
import ipaddress
import math
import os
from typing import Mapping
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ClientConfig:
    server_url: str = "http://127.0.0.1:8000"
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        try:
            url = urlsplit(self.server_url)
            if not url.hostname or url.scheme not in {"http", "https"}:
                raise ValueError
            if url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
                raise ValueError
            if url.port is not None and not 1 <= url.port <= 65535:
                raise ValueError
            if url.scheme == "http" and url.hostname != "localhost":
                if not ipaddress.ip_address(url.hostname).is_loopback:
                    raise ValueError
        except ValueError:
            raise ValueError("Server URL must be an HTTP(S) origin without credentials; HTTP is local only.") from None
        if not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 60:
            raise ValueError("Client timeout must be greater than 0 and at most 60 seconds.")

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "ClientConfig":
        env = os.environ if environment is None else environment
        try:
            timeout = float(env.get("AGENT_CF_CLIENT_TIMEOUT_SECONDS", "5"))
        except ValueError:
            raise ValueError("AGENT_CF_CLIENT_TIMEOUT_SECONDS must be a number.") from None
        return cls(
            server_url=env.get("AGENT_CF_CLIENT_SERVER_URL", "http://127.0.0.1:8000"),
            timeout_seconds=timeout,
        )

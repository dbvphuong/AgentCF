"""Validated local configuration. Environment files are not loaded implicitly."""

import ipaddress
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    database_path: Path = Path("runtime/server/agent_cf.sqlite3")
    database_busy_timeout_ms: int = Field(default=5000, ge=1, le=60000)
    artifacts_dir: Path = Path("runtime/server/artifacts")
    client_installer_path: Path = Path("runtime/client-build/CF Client Setup.exe")
    temporal_enabled: bool = True
    temporal_address: str = "127.0.0.1:7233"
    temporal_namespace: str = Field(default="default", min_length=1)
    temporal_task_queue: str = Field(default="agent-cf-process-v1", min_length=1)
    request_timeout_seconds: float = Field(default=5, gt=0, le=60)

    @field_validator("host")
    @classmethod
    def local_bind_only(cls, value: str) -> str:
        if value != "localhost" and not ipaddress.ip_address(value).is_loopback:
            raise ValueError("foundation HTTP server must bind to loopback")
        return value

    @field_validator("database_path")
    @classmethod
    def resolve_database_path(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("artifacts_dir", "client_installer_path")
    @classmethod
    def resolve_artifacts_dir(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("temporal_address")
    @classmethod
    def valid_temporal_address(cls, value: str) -> str:
        # An SDK target is host:port, not a URL or credential-bearing URI.
        host, separator, port = value.rpartition(":")
        if not separator or not host or "/" in host or "@" in host:
            raise ValueError("Temporal address must be host:port")
        try:
            valid_port = 1 <= int(port) <= 65535
        except ValueError:
            valid_port = False
        if not valid_port:
            raise ValueError("Temporal port must be between 1 and 65535")
        if host != "localhost":
            try:
                local = ipaddress.ip_address(host.strip("[]")).is_loopback
            except ValueError:
                local = False
            if not local:
                raise ValueError("foundation Temporal connection must use loopback")
        return value


def load_settings() -> ServerSettings:
    fields = ServerSettings.model_fields
    values = {
        name: os.environ[f"AGENT_CF_SERVER_{name.upper()}"]
        for name in fields
        if f"AGENT_CF_SERVER_{name.upper()}" in os.environ
    }
    return ServerSettings.model_validate(values)

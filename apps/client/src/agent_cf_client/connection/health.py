"""Safe foundation connectivity check; it grants no Runner execution rights."""

from dataclasses import dataclass
import json

import httpx

from agent_cf_client.config import ClientConfig


class HealthCheckError(Exception):
    """The Server could not supply a valid healthy response."""


@dataclass(frozen=True)
class ServerHealth:
    schema_version: int
    temporal_configured: bool


def parse_health(value: object) -> ServerHealth:
    if not isinstance(value, dict) or value.get("status") != "ok":
        raise HealthCheckError("Server returned an invalid health response.")
    database = value.get("database")
    temporal = value.get("temporal")
    if not isinstance(database, dict) or not isinstance(temporal, dict):
        raise HealthCheckError("Server returned an invalid health response.")
    version = database.get("schema_version")
    configured = temporal.get("configured")
    if type(version) is not int or version < 1 or type(configured) is not bool:
        raise HealthCheckError("Server returned an invalid health response.")
    return ServerHealth(schema_version=version, temporal_configured=configured)


def check_server(config: ClientConfig, *, transport: httpx.BaseTransport | None = None) -> ServerHealth:
    try:
        with httpx.Client(timeout=config.timeout_seconds, transport=transport, trust_env=False) as client:
            with client.stream("GET", f"{config.server_url.rstrip('/')}/healthz", headers={"Accept": "application/json"}) as response:
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_bytes(chunk_size=4096):
                    if len(content) + len(chunk) > 16384:
                        raise HealthCheckError("Server returned an oversized health response.")
                    content.extend(chunk)
                try:
                    payload = json.loads(content)
                except ValueError:
                    raise HealthCheckError("Server returned an invalid health response.") from None
    except httpx.HTTPStatusError as exc:
        raise HealthCheckError(f"Server health check returned HTTP {exc.response.status_code}.") from None
    except httpx.RequestError:
        raise HealthCheckError("Unable to connect to Server or the request timed out.") from None
    return parse_health(payload)

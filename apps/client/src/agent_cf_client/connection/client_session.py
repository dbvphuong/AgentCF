"""Authenticated Runner connection, pairing, and heartbeat session (CLI-001, PC-001)."""

import json
from pathlib import Path
from typing import Any
import httpx


class ClientSessionManager:
    def __init__(self, credentials_path: Path | None = None, timeout_seconds: float = 10.0, protect_credentials: bool = False) -> None:
        self.protect_credentials = protect_credentials
        if credentials_path is None:
            credentials_path = Path.home() / ".agent_cf" / "runner_credentials.json"
        self.credentials_path = Path(credentials_path)
        self.timeout_seconds = timeout_seconds
        self.current_session_id: str | None = None

    def pair(
        self,
        server_url: str,
        pairing_code: str,
        machine_fingerprint: str | None = None,
        client_version: str = "0.1.0",
        name: str | None = None,
        device_id: str | None = None,
        device_key: str | None = None,
    ) -> dict[str, Any]:
        """Exchange one-time pairing code for runner credentials."""
        url = server_url.rstrip("/") + "/v1/runners/pair"
        payload = {
            "pairing_code": pairing_code,
            "machine_fingerprint": machine_fingerprint,
            "client_version": client_version,
        }
        if name is not None:
            payload["name"] = name
        if device_id or device_key:
            payload.update(device_id=device_id, device_key=device_key)
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 201:
                detail = None
                try:
                    body = resp.json()
                    if isinstance(body, dict):
                        detail = body.get("detail")
                except Exception:
                    pass
                raise ConnectionError(detail or f"Pairing failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            runner_id = data["runner_id"]
            runner_token = data["runner_token"]
            self.save_credentials(runner_id=runner_id, runner_token=runner_token, server_url=server_url)
            return data

    def start_session(
        self,
        capabilities: list[str] | None = None,
        client_version: str = "0.1.0",
        machine_fingerprint: str | None = None,
        os_name: str | None = None,
        device_id: str | None = None,
        device_key: str | None = None,
    ) -> dict[str, Any]:
        """Open a new active execution session with Server."""
        creds = self.get_credentials()
        if not creds:
            raise ValueError("No runner credentials found. Pair runner first.")

        server_url = creds["server_url"].rstrip("/")
        runner_id = creds["runner_id"]
        runner_token = creds["runner_token"]

        url = f"{server_url}/v1/runners/{runner_id}/sessions"
        headers = {"Authorization": f"Bearer {runner_token}"}
        payload = {
            "client_version": client_version,
            "machine_fingerprint": machine_fingerprint,
            "capabilities": capabilities or [],
        }
        if os_name:
            payload["os_name"] = os_name
        if device_id or device_key:
            payload.update(device_id=device_id,device_key=device_key)

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 201:
                raise ConnectionError(f"Session start failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            self.current_session_id = data["session_id"]
            return data

    def send_heartbeat(
        self,
        cpu_percent: float | None = None,
        ram_percent: float | None = None,
        running_attempts: list[str] | None = None,
        memory_total_bytes: int | None = None,
        memory_used_bytes: int | None = None,
    ) -> dict[str, Any]:
        """Send periodic heartbeat to Server."""
        creds = self.get_credentials()
        if not creds or not self.current_session_id:
            raise ValueError("No active runner session")

        server_url = creds["server_url"].rstrip("/")
        runner_id = creds["runner_id"]
        runner_token = creds["runner_token"]

        url = f"{server_url}/v1/runners/{runner_id}/heartbeat"
        headers = {"Authorization": f"Bearer {runner_token}"}
        payload = {
            "session_id": self.current_session_id,
            "cpu_percent": cpu_percent,
            "ram_percent": ram_percent,
            "running_attempts": running_attempts or [],
            "memory_total_bytes": memory_total_bytes,
            "memory_used_bytes": memory_used_bytes,
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise ConnectionError(f"Heartbeat failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            from agent_cf_client.connection.skill_files import list_skill_files
            for item in data.get("skill_file_requests", []):
                result = list_skill_files(item.get("path"))
                completed = client.post(
                    f"{server_url}/v1/runners/{runner_id}/skill-files/{item['id']}/result",
                    json={"session_id": self.current_session_id, "result": result}, headers=headers,
                )
                # A browser may close or its request may expire during a slow filesystem read.
                if completed.status_code != 404:
                    completed.raise_for_status()
            return data

    def close_session(self):
        creds = self.get_credentials()
        if creds and self.current_session_id:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.delete(f"{creds['server_url'].rstrip('/')}/v1/runners/{creds['runner_id']}/sessions/{self.current_session_id}", headers={"Authorization": f"Bearer {creds['runner_token']}"})
                response.raise_for_status()
        self.current_session_id = None

    def get_credentials(self) -> dict[str, str] | None:
        if not self.credentials_path.exists():
            return None
        try:
            raw = self.credentials_path.read_bytes()
            if self.protect_credentials and not raw.startswith(b"AGENTCF-DPAPI\0"):
                return None
            if raw.startswith(b"AGENTCF-DPAPI\0"):
                from agent_cf_client.connection.credentials import protect
                raw = protect(raw[len(b"AGENTCF-DPAPI\0"):], decrypt=True)
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict) or any(not isinstance(data.get(key), str) or not data[key] for key in ("server_url", "runner_id", "runner_token")):
                return None
            return data
        except Exception:
            return None

    def save_credentials(self, runner_id: str, runner_token: str, server_url: str) -> None:
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "runner_id": runner_id,
            "runner_token": runner_token,
            "server_url": server_url,
        }
        temp_file = self.credentials_path.with_suffix(".tmp")
        raw = json.dumps(data, indent=2).encode("utf-8")
        if self.protect_credentials:
            from agent_cf_client.connection.credentials import protect
            raw = b"AGENTCF-DPAPI\0" + protect(raw)
        temp_file.write_bytes(raw)
        temp_file.replace(self.credentials_path)

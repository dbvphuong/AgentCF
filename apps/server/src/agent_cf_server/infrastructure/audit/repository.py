"""Audit trail persistence, structured query, and sensitive data redaction (REL-002, REQ-AUDIT-01)."""

from datetime import datetime, timezone
import json
import re
from typing import Any
from uuid import uuid4

from agent_cf_server.infrastructure.persistence.database import Database

# Sensitive dictionary keys to redact
SENSITIVE_KEY_SUBSTRINGS = (
    "secret",
    "token",
    "password",
    "api_key",
    "apikey",
    "credential",
    "authorization",
    "private_key",
    "ciphertext",
)

# Regex patterns matching token headers or credentials embedded in text strings
TOKEN_REGEXES = [
    re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.~+/]+=*)", re.IGNORECASE),
    re.compile(r"(sk-[a-zA-Z0-9_\-]{20,})"),
    re.compile(r"(rt_[a-f0-9]{32,})", re.IGNORECASE),
]


def redact_secrets(val: Any) -> Any:
    """Recursively mask secrets, tokens, credentials, and api keys from dictionaries, lists, and strings."""
    if isinstance(val, dict):
        redacted = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            if any(sub in k_lower for sub in SENSITIVE_KEY_SUBSTRINGS):
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = redact_secrets(v)
        return redacted
    elif isinstance(val, (list, tuple)):
        return [redact_secrets(item) for item in val]
    elif isinstance(val, str):
        cleaned = val
        for rgx in TOKEN_REGEXES:
            cleaned = rgx.sub(lambda m: m.group(0).split()[0] + " ***REDACTED***" if " " in m.group(0) else "***REDACTED***", cleaned)
        return cleaned
    return val


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AuditRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def record_event(
        self,
        *,
        actor_id: str,
        event_type: str,
        resource_id: str,
        data: dict[str, Any] | None = None,
        run_id: str | None = None,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        """Record an immutable audit event with automatic secret redaction."""
        event_id = str(uuid4())
        at = recorded_at or _now_iso()
        safe_data = redact_secrets(data or {})
        data_json = json.dumps(safe_data, ensure_ascii=False)

        with self.database.transaction() as conn:
            conn.execute(
                "INSERT INTO audit_events(id, run_id, actor_id, event_type, resource_id, data_json, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event_id, run_id, actor_id, event_type, resource_id, data_json, at),
            )

        return {
            "id": event_id,
            "run_id": run_id,
            "actor_id": actor_id,
            "event_type": event_type,
            "resource_id": resource_id,
            "data": safe_data,
            "recorded_at": at,
        }

    def list_events(
        self,
        *,
        run_id: str | None = None,
        actor_id: str | None = None,
        resource_id: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        cursor_time: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query audit log with filtering and pagination."""
        clauses = []
        params: list[Any] = []

        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if actor_id is not None:
            clauses.append("actor_id = ?")
            params.append(actor_id)
        if resource_id is not None:
            clauses.append("resource_id = ?")
            params.append(resource_id)
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)
        if cursor_time is not None:
            clauses.append("recorded_at > ?")
            params.append(cursor_time)

        query = "SELECT * FROM audit_events"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY recorded_at ASC LIMIT ?"
        params.append(limit)

        with self.database.connect(read_only=True) as conn:
            rows = conn.execute(query, params).fetchall()

        results = []
        for r in rows:
            item = dict(r)
            raw_data = json.loads(item.pop("data_json"))
            item["data"] = redact_secrets(raw_data)
            results.append(item)
        return results

    def get_run_audit_trail(self, run_id: str) -> list[dict[str, Any]]:
        """Return the complete chronological audit trail for a ProcessRun."""
        return self.list_events(run_id=run_id, limit=500)

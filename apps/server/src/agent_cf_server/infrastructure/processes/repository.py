"""Store already-validated immutable ProcessVersion snapshots.

This repository is a persistence boundary, not the publish validator or HTTP API.
The caller supplies the snapshot fingerprint after validation/canonicalization.
"""

from datetime import datetime, timezone
import json

from agent_cf_server.infrastructure.persistence.database import Database


def encode_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


class ProcessRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_process(self, *, process_id: str, project_id: str, name: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO processes(id,project_id,name) VALUES (?,?,?)",
                (process_id, project_id, name),
            )

    def store_published(
        self,
        *,
        workspace_id: str,
        project_id: str,
        process_id: str,
        version_id: str,
        version_number: int,
        definition: dict,
        snapshot_sha256: str,
    ) -> None:
        """Persist a validated snapshot and normalized Task identities atomically."""
        if not definition.get("tasks"):
            raise ValueError("A ProcessVersion needs at least one Task")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self.database.transaction() as connection:
            owner = connection.execute(
                "SELECT p.project_id,j.workspace_id FROM processes p "
                "JOIN projects j ON j.id=p.project_id WHERE p.id=?", (process_id,)
            ).fetchone()
            if owner is None:
                raise ValueError("An existing Process and Project are required")
            if owner["project_id"] != project_id or owner["workspace_id"] != workspace_id:
                raise ValueError("Process ownership does not match the Project and Workspace")
            connection.execute(
                "INSERT INTO process_versions(id,process_id,version_number,status,definition_format_version,"
                "interpreter_version,definition_json) VALUES (?,?,?,'draft',?,?,?)",
                (version_id, process_id, version_number, definition["definition_format_version"],
                 definition["interpreter_version"], encode_json(definition)),
            )
            connection.executemany(
                "INSERT INTO tasks(process_version_id,id,task_key,definition_json) VALUES (?,?,?,?)",
                [(version_id, task["id"], task["task_key"], encode_json(task)) for task in definition["tasks"]],
            )
            connection.executemany(
                "INSERT INTO dependencies(process_version_id,source_task_id,target_task_id) VALUES (?,?,?)",
                [(version_id, edge["source_task_id"], edge["target_task_id"]) for edge in definition["dependencies"]],
            )
            connection.execute(
                "UPDATE process_versions SET status='published',snapshot_sha256=?,published_at=? WHERE id=?",
                (snapshot_sha256, now, version_id),
            )

    def get_version(self, version_id: str) -> dict:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM process_versions WHERE id=?", (version_id,)).fetchone()
            if row is None:
                raise KeyError(version_id)
            result = dict(row)
            result["definition"] = json.loads(result.pop("definition_json"))
            return result

"""Persistence and lifecycle for Robots and Robot Versions (ROB-001)."""

from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from typing import Any
from uuid import uuid4

from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.settings.repository import (
    InUseError,
    ResourceConflictError,
    ResourceNotFoundError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


def compute_robot_bundle_hash(
    entrypoint: str,
    contract_version: str,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> str:
    """Compute canonical sha256 of robot version content."""
    hasher = hashlib.sha256()
    payload = {
        "entrypoint": entrypoint.strip(),
        "contract_version": contract_version.strip(),
        "input_schema": input_schema or {},
        "output_schema": output_schema or {},
    }
    hasher.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return hasher.hexdigest()


class RobotRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    # -------------------------------------------------------------------------
    # Robots Catalog
    # -------------------------------------------------------------------------

    def create_robot(
        self,
        name: str,
        description: str = "",
        robot_id: str | None = None,
        active_version_id: str | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        rid = robot_id or str(uuid4())
        name = name.strip()
        if not name:
            raise ValueError("Robot name must not be empty")

        with self.database.transaction() as conn:
            try:
                conn.execute(
                    "INSERT INTO robots (id, name, description, active_version_id, status, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (rid, name, description, active_version_id, status, _now_iso(), _now_iso()),
                )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Robot conflict: {exc}") from exc
        return self.get_robot(rid)

    def get_robot(self, robot_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM robots WHERE id = ?", (robot_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Robot not found: {robot_id}")
            result = dict(row)

            # Attach active version details if present
            if result.get("active_version_id"):
                v_row = conn.execute(
                    "SELECT * FROM robot_versions WHERE id = ?",
                    (result["active_version_id"],),
                ).fetchone()
                if v_row:
                    v_dict = dict(v_row)
                    try:
                        v_dict["input_schema"] = json.loads(v_dict.pop("input_schema_json"))
                    except Exception:
                        v_dict["input_schema"] = {}
                    try:
                        v_dict["output_schema"] = json.loads(v_dict.pop("output_schema_json"))
                    except Exception:
                        v_dict["output_schema"] = {}
                    result["active_version"] = v_dict
                else:
                    result["active_version"] = None
            else:
                result["active_version"] = None

            return result

    def list_robots(self, status: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            query = "SELECT * FROM robots"
            params: list[Any] = []
            if status is not None:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY name ASC"
            results = []
            for row in conn.execute(query, params).fetchall():
                item = dict(row)
                if item.get("active_version_id"):
                    v_row = conn.execute(
                        "SELECT version_number, status, entrypoint FROM robot_versions WHERE id = ?",
                        (item["active_version_id"],),
                    ).fetchone()
                    item["active_version"] = dict(v_row) if v_row else None
                else:
                    item["active_version"] = None
                results.append(item)
            return results

    def update_robot(
        self,
        robot_id: str,
        name: str | None = None,
        description: str | None = None,
        active_version_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM robots WHERE id = ?", (robot_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Robot not found: {robot_id}")

            updates: list[str] = []
            params: list[Any] = []
            if name is not None:
                cleaned_name = name.strip()
                if not cleaned_name:
                    raise ValueError("Robot name must not be empty")
                updates.append("name = ?")
                params.append(cleaned_name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if active_version_id is not None:
                if active_version_id != "":
                    # Verify active version belongs to this robot and is published
                    v_row = conn.execute(
                        "SELECT id, status FROM robot_versions WHERE id = ? AND robot_id = ?",
                        (active_version_id, robot_id),
                    ).fetchone()
                    if not v_row:
                        raise ResourceNotFoundError(f"Robot version {active_version_id} not found for this robot")
                    if v_row["status"] != "published":
                        raise ResourceConflictError("Only published versions can be set as active version")
                    updates.append("active_version_id = ?")
                    params.append(active_version_id)
                else:
                    updates.append("active_version_id = NULL")
            if status is not None:
                if status not in ("active", "archived"):
                    raise ValueError(f"Invalid robot status: {status}")
                updates.append("status = ?")
                params.append(status)

            if not updates:
                return self.get_robot(robot_id)

            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(robot_id)

            try:
                conn.execute(f"UPDATE robots SET {', '.join(updates)} WHERE id = ?", params)
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Robot update conflict: {exc}") from exc

        return self.get_robot(robot_id)

    def archive_robot(self, robot_id: str) -> dict[str, Any]:
        return self.update_robot(robot_id, status="archived")

    def restore_robot(self, robot_id: str) -> dict[str, Any]:
        return self.update_robot(robot_id, status="active")

    def delete_robot(self, robot_id: str) -> None:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT id,name FROM robots WHERE id = ?", (robot_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Robot not found: {robot_id}")

            # Check if any task in process_versions references any version of this robot
            ref_task = conn.execute(
                "SELECT COALESCE(json_extract(t.definition_json,'$.name'),t.task_key) AS task_name, "
                "p.name AS process_name,pr.name AS project_name,v.version_number FROM tasks t "
                "JOIN process_versions v ON v.id=t.process_version_id JOIN processes p ON p.id=v.process_id "
                "JOIN projects pr ON pr.id=p.project_id "
                "JOIN robot_versions rv ON json_extract(t.definition_json, '$.robot_version_id') = rv.id "
                "WHERE rv.robot_id = ? LIMIT 1",
                (robot_id,),
            ).fetchone()
            if ref_task:
                raise InUseError(
                    f'Không thể xóa Robot “{existing["name"]}” vì đang được bước “{ref_task["task_name"]}” '
                    f'trong Process “{ref_task["process_name"]}” v{ref_task["version_number"]}, Project “{ref_task["project_name"]}” tham chiếu. '
                    "Kiểm tra Process liên quan. Tham chiếu trong phiên bản đã phát hành được giữ bất biến; sửa cấu hình mới không gỡ liên kết cũ."
                )

            # Check if any published version exists (which is immutable by trigger)
            pub_version = conn.execute(
                "SELECT version_number FROM robot_versions WHERE robot_id = ? AND status = 'published' ORDER BY version_number LIMIT 1",
                (robot_id,),
            ).fetchone()
            if pub_version:
                raise InUseError(
                    f'Không thể xóa Robot “{existing["name"]}” vì đã có phiên bản v{pub_version["version_number"]} được phát hành. '
                    "Phiên bản đã phát hành được giữ bất biến để bảo vệ lịch sử; hiện chưa hỗ trợ xóa Robot trong trường hợp này."
                )

            # Safe to delete draft versions and robot
            conn.execute("DELETE FROM robot_versions WHERE robot_id = ?", (robot_id,))
            conn.execute("DELETE FROM robots WHERE id = ?", (robot_id,))

    # -------------------------------------------------------------------------
    # Robot Versions
    # -------------------------------------------------------------------------

    def create_draft_version(
        self,
        robot_id: str,
        entrypoint: str,
        version_id: str | None = None,
        contract_version: str = "1.0.0",
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        ready_to_use: bool = False,
    ) -> dict[str, Any]:
        vid = version_id or str(uuid4())
        entrypoint = entrypoint.strip()
        if not entrypoint:
            raise ValueError("Entrypoint must not be empty")

        input_schema_json = json.dumps(input_schema or {})
        output_schema_json = json.dumps(output_schema or {})

        with self.database.transaction() as conn:
            robot = conn.execute("SELECT id FROM robots WHERE id = ?", (robot_id,)).fetchone()
            if not robot:
                raise ResourceNotFoundError(f"Robot not found: {robot_id}")

            # Calculate next version number
            last_v = conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) FROM robot_versions WHERE robot_id = ?",
                (robot_id,),
            ).fetchone()[0]
            next_version_num = last_v + 1

            try:
                conn.execute(
                    "INSERT INTO robot_versions (id, robot_id, version_number, status, contract_version, entrypoint, "
                    "input_schema_json, output_schema_json, bundle_sha256, created_at, published_at) "
                    "VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, NULL, ?, NULL)",
                    (
                        vid,
                        robot_id,
                        next_version_num,
                        contract_version,
                        entrypoint,
                        input_schema_json,
                        output_schema_json,
                        _now_iso(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Draft version conflict: {exc}") from exc

            if ready_to_use:
                digest = compute_robot_bundle_hash(entrypoint, contract_version, input_schema or {}, output_schema or {})
                conn.execute("UPDATE robot_versions SET status='published',bundle_sha256=?,published_at=? WHERE id=?", (digest, _now_iso(), vid))

        return self.get_version(vid)

    def get_version(self, version_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM robot_versions WHERE id = ?", (version_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Robot version not found: {version_id}")
            result = dict(row)
            try:
                result["input_schema"] = json.loads(result.pop("input_schema_json"))
            except Exception:
                result["input_schema"] = {}
            try:
                result["output_schema"] = json.loads(result.pop("output_schema_json"))
            except Exception:
                result["output_schema"] = {}
            return result

    def list_versions(self, robot_id: str) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            rows = conn.execute(
                "SELECT * FROM robot_versions WHERE robot_id = ? ORDER BY version_number DESC",
                (robot_id,),
            ).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["input_schema"] = json.loads(item.pop("input_schema_json"))
                except Exception:
                    item["input_schema"] = {}
                try:
                    item["output_schema"] = json.loads(item.pop("output_schema_json"))
                except Exception:
                    item["output_schema"] = {}
                results.append(item)
            return results

    def publish_version(self, version_id: str, bundle_sha256: str | None = None) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM robot_versions WHERE id = ?", (version_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Robot version not found: {version_id}")
            if existing["status"] == "published":
                return self.get_version(version_id)

            if not bundle_sha256:
                input_schema = json.loads(existing["input_schema_json"])
                output_schema = json.loads(existing["output_schema_json"])
                bundle_sha256 = compute_robot_bundle_hash(
                    entrypoint=existing["entrypoint"],
                    contract_version=existing["contract_version"],
                    input_schema=input_schema,
                    output_schema=output_schema,
                )

            published_at = _now_iso()
            conn.execute(
                "UPDATE robot_versions SET status = 'published', bundle_sha256 = ?, published_at = ? WHERE id = ?",
                (bundle_sha256, published_at, version_id),
            )

            # If parent robot has no active_version_id, set it now
            robot = conn.execute("SELECT active_version_id FROM robots WHERE id = ?", (existing["robot_id"],)).fetchone()
            if robot and not robot["active_version_id"]:
                conn.execute(
                    "UPDATE robots SET active_version_id = ?, updated_at = ? WHERE id = ?",
                    (version_id, published_at, existing["robot_id"]),
                )

        return self.get_version(version_id)

    # -------------------------------------------------------------------------
    # Statistics per RobotVersion from Real Execution Data
    # -------------------------------------------------------------------------

    def get_robot_statistics(self, robot_id: str) -> dict[str, Any]:
        """Aggregate success rate and execution counts per RobotVersion from real runs."""
        with self.database.connect(read_only=True) as conn:
            robot = conn.execute("SELECT id, name, active_version_id FROM robots WHERE id = ?", (robot_id,)).fetchone()
            if not robot:
                raise ResourceNotFoundError(f"Robot not found: {robot_id}")

            versions = conn.execute(
                "SELECT id, version_number, status, contract_version, entrypoint, published_at "
                "FROM robot_versions WHERE robot_id = ? ORDER BY version_number DESC",
                (robot_id,),
            ).fetchall()

            version_stats: list[dict[str, Any]] = []
            overall_total = 0
            overall_succeeded = 0
            overall_failed = 0
            overall_cancelled = 0

            for v in versions:
                vid = v["id"]
                # Query actual task runs that executed this robot version
                rows = conn.execute(
                    "SELECT tr.status, tr.error_json "
                    "FROM task_runs tr "
                    "JOIN tasks t ON t.process_version_id = tr.process_version_id AND t.id = tr.task_id "
                    "WHERE json_extract(t.definition_json, '$.robot_version_id') = ? "
                    "AND tr.status IN ('succeeded', 'failed', 'cancelled')",
                    (vid,),
                ).fetchall()

                total = len(rows)
                succeeded = sum(1 for r in rows if r["status"] == "succeeded")
                failed = sum(1 for r in rows if r["status"] == "failed")
                cancelled = sum(1 for r in rows if r["status"] == "cancelled")

                # Success rate: succeeded / (succeeded + failed); None if no completed runs (not 0%)
                if (succeeded + failed) > 0:
                    success_rate = round((succeeded / (succeeded + failed)) * 100, 1)
                else:
                    success_rate = None

                overall_total += total
                overall_succeeded += succeeded
                overall_failed += failed
                overall_cancelled += cancelled

                version_stats.append({
                    "robot_version_id": vid,
                    "version_number": v["version_number"],
                    "status": v["status"],
                    "entrypoint": v["entrypoint"],
                    "published_at": v["published_at"],
                    "total_runs": total,
                    "succeeded_runs": succeeded,
                    "failed_runs": failed,
                    "cancelled_runs": cancelled,
                    "success_rate": success_rate,
                })

            if (overall_succeeded + overall_failed) > 0:
                overall_success_rate = round((overall_succeeded / (overall_succeeded + overall_failed)) * 100, 1)
            else:
                overall_success_rate = None

            return {
                "robot_id": robot_id,
                "name": robot["name"],
                "active_version_id": robot["active_version_id"],
                "overall": {
                    "total_runs": overall_total,
                    "succeeded_runs": overall_succeeded,
                    "failed_runs": overall_failed,
                    "cancelled_runs": overall_cancelled,
                    "success_rate": overall_success_rate,
                },
                "versions": version_stats,
            }

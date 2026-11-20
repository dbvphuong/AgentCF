"""Persistence and lifecycle for Runners, Pairing Codes, and Sessions (PC-001, CLI-001)."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
import sqlite3
from typing import Any
from uuid import uuid4

from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.deletion_feedback import RUN_CONTEXT, reference_list, run_label
from agent_cf_server.infrastructure.settings.repository import (
    ResourceConflictError,
    ResourceNotFoundError,
)


class AuthenticationError(Exception):
    """Runner authentication failed or credential expired."""


class SessionInvalidError(Exception):
    """Runner session is not active or has been revoked."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_dt().strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RunnerRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    # -------------------------------------------------------------------------
    # Pairing Codes
    # -------------------------------------------------------------------------

    def create_pairing_code(
        self,
        workspace_id: str,
        name: str,
        expires_in_seconds: int = 300,
        target_runner_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        raw_code = secrets.token_hex(32)
        pairing_id = str(uuid4())
        code_hash = _hash_token(raw_code)
        expires_at = (_now_dt() + timedelta(seconds=expires_in_seconds)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        now = _now_iso()

        with self.database.transaction() as conn:
            ws = conn.execute("SELECT id FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
            if not ws:
                raise ResourceNotFoundError(f"Workspace not found: {workspace_id}")
            if target_runner_id:
                target = conn.execute("SELECT * FROM runners WHERE id=? AND workspace_id=? AND deleted_at IS NULL", (target_runner_id,workspace_id)).fetchone()
                if not target:
                    raise ResourceNotFoundError("PC cần kết nối lại không thuộc Workspace hoặc đã bị xóa")
                name = target["name"]
            conn.execute(
                "INSERT INTO runner_pairing_codes (id,code_hash, workspace_id, name, expires_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pairing_id,code_hash, workspace_id, name, expires_at, now),
            )
            conn.execute("UPDATE runner_pairing_codes SET target_runner_id=? WHERE code_hash=?", (target_runner_id,code_hash))
        return raw_code, {
            "id": pairing_id,
            "code_hash": code_hash,
            "workspace_id": workspace_id,
            "name": name,
            "expires_at": expires_at,
        }

    def exchange_pairing_code(
        self,
        raw_code: str,
        machine_fingerprint: str | None = None,
        client_version: str | None = None,
        name: str | None = None,
        device_id: str | None = None,
        device_key: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        code_hash = _hash_token(raw_code)
        now = _now_iso()
        if bool(device_id) != bool(device_key):
            raise ValueError("Định danh máy cần đủ ID và bằng chứng Client")

        with self.database.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM runner_pairing_codes WHERE code_hash = ? AND used_at IS NULL",
                (code_hash,),
            ).fetchone()
            if not row:
                raise AuthenticationError("Invalid or already used pairing code")
            if row["expires_at"] < now:
                raise AuthenticationError("Pairing code has expired")
            if not device_id and not row["target_runner_id"] and client_version in ("0.2.0", "0.3.0"):
                raise ResourceConflictError("Cập nhật CF Client hoặc bấm Kết nối trên dòng PC có sẵn để tránh tạo PC trùng.")
            existing = None
            if device_id:
                existing = conn.execute("SELECT * FROM runners WHERE workspace_id=? AND device_id=? AND deleted_at IS NULL", (row["workspace_id"],device_id)).fetchone()
            if row["target_runner_id"]:
                target = conn.execute("SELECT * FROM runners WHERE id=? AND workspace_id=? AND deleted_at IS NULL", (row["target_runner_id"],row["workspace_id"])).fetchone()
                if not target:
                    raise ResourceConflictError("PC cần kết nối lại đã bị xóa")
                if (target["device_id"] and target["device_id"] != device_id) or (existing and existing["id"] != target["id"]):
                    raise ResourceConflictError("Máy này đã thuộc PC khác; chọn đúng PC để kết nối lại")
                existing = target
            elif existing:
                if not existing["device_key_hash"] or not secrets.compare_digest(existing["device_key_hash"], _hash_token(device_key)) or existing["status"] == "disabled":
                    raise ResourceConflictError("Máy đã có trong danh sách. Bấm Kết nối tại dòng PC đó để cấp lại kết nối.")
            if existing:
                self._require_no_active_execution(conn, existing["id"])

            # Mark code as used
            conn.execute("UPDATE runner_pairing_codes SET used_at = ? WHERE code_hash = ?", (now, code_hash))

            runner_id = existing["id"] if existing else f"pc-{secrets.token_hex(6)}"
            raw_token = secrets.token_hex(32)  # 256-bit token
            token_hash = _hash_token(raw_token)
            expires_at = (_now_dt() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            if existing:
                conn.execute("UPDATE runner_sessions SET status='revoked' WHERE runner_id=? AND status='active'", (runner_id,))
                conn.execute("UPDATE runners SET status='offline',credential_hash=?,credential_expires_at=?,client_version=?,device_id=COALESCE(?,device_id),device_key_hash=COALESCE(?,device_key_hash),machine_fingerprint=COALESCE(?,machine_fingerprint) WHERE id=?", (token_hash,expires_at,client_version,device_id,_hash_token(device_key) if device_key else None,machine_fingerprint,runner_id))
            else:
                conn.execute(
                    "INSERT INTO runners(id,workspace_id,name,status,credential_hash,credential_expires_at,machine_fingerprint,client_version,last_seen_at,device_id,device_key_hash) VALUES (?,?,?,'online',?,?,?,?,?,?,?)",
                    (runner_id,row["workspace_id"],name.strip() if name else row["name"],token_hash,expires_at,machine_fingerprint,client_version,now,device_id,_hash_token(device_key) if device_key else None),
                )
            conn.execute("INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator',?,?,'{}',?)", (str(uuid4()),'runner_reconnected' if existing else 'runner_paired',runner_id,now))
            conn.execute("UPDATE runner_pairing_codes SET runner_id=? WHERE code_hash=?", (runner_id,code_hash))

        runner = self.get_runner(runner_id)
        return raw_token, runner

    def inspect_pairing_code(self, raw_code: str) -> dict:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT c.name,c.expires_at,c.target_runner_id,w.name workspace_name FROM runner_pairing_codes c JOIN workspaces w ON w.id=c.workspace_id WHERE c.code_hash=? AND c.used_at IS NULL AND c.expires_at>?", (_hash_token(raw_code),_now_iso())).fetchone()
            if not row:
                raise AuthenticationError("Mã ghép nối không hợp lệ, đã dùng hoặc hết hạn")
            return dict(row)

    def pairing_state(self, pairing_id: str) -> dict:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM runner_pairing_codes WHERE id=?", (pairing_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError("Không tìm thấy phiên ghép nối")
            result = {"id": pairing_id, "name": row["name"], "expires_at": row["expires_at"], "status": "pending"}
            if row["runner_id"]:
                runner = conn.execute("SELECT * FROM runners WHERE id=?", (row["runner_id"],)).fetchone()
                if runner["deleted_at"]:
                    result["status"] = "removed"
                else:
                    fresh = (_now_dt()-timedelta(seconds=45)).isoformat().replace('+00:00','Z')
                    session = conn.execute("SELECT 1 FROM runner_sessions WHERE runner_id=? AND status='active' AND last_heartbeat_at>? AND last_heartbeat_at>created_at", (row["runner_id"], fresh)).fetchone()
                    result.update(status="connected" if session and runner["status"] != "disabled" else "paired", runner_id=runner["id"], name=runner["name"])
            elif row["expires_at"] <= _now_iso():
                result["status"] = "expired"
            return result

    # -------------------------------------------------------------------------
    # Authentication & Runner Management
    # -------------------------------------------------------------------------

    def authenticate_runner(self, runner_id: str, raw_token: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM runners WHERE id = ?", (runner_id,)).fetchone()
            if not row or row["deleted_at"]:
                raise AuthenticationError(f"Runner not found: {runner_id}")
            token_hash = _hash_token(raw_token)
            if row["credential_hash"] != token_hash:
                raise AuthenticationError("Invalid runner credential")
            if row["credential_expires_at"] and row["credential_expires_at"] <= _now_iso():
                raise AuthenticationError("Runner credential has expired or been revoked")
            return dict(row)

    def get_runner(self, runner_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM runners WHERE id = ?", (runner_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Runner not found: {runner_id}")
            res = dict(row)
            res.pop("credential_hash", None)
            res.pop("device_key_hash", None)
            self._add_activity(conn, res)
            return res

    @staticmethod
    def _add_activity(conn, item: dict[str, Any]) -> None:
        item["current_tasks"] = [dict(row) for row in conn.execute(
            "SELECT a.run_id,a.task_run_id,a.status,t.task_key,"
            "json_extract(t.definition_json,'$.name') AS node_name,"
            "json_extract(t.definition_json,'$.agent_id') AS agent_id,p.name AS process_name "
            "FROM attempts a JOIN task_runs tr ON tr.id=a.task_run_id "
            "JOIN tasks t ON t.process_version_id=tr.process_version_id AND t.id=tr.task_id "
            "JOIN process_runs r ON r.id=a.run_id JOIN processes p ON p.id=r.process_id "
            "WHERE a.runner_id=? AND a.status IN ('claimed','running','reconciling')", (item["id"],))]
        # Presentation freshness never changes execution grants or reassigns work.
        if item["status"] == "online":
            try:
                session = conn.execute("SELECT last_heartbeat_at,created_at FROM runner_sessions WHERE runner_id=? AND status='active'", (item["id"],)).fetchone()
                if not session or not session["last_heartbeat_at"] or session["last_heartbeat_at"] <= session["created_at"]:
                    item["display_status"] = "offline"
                    return
                last_seen = datetime.fromisoformat(session["last_heartbeat_at"].replace("Z", "+00:00"))
                item["display_status"] = "offline" if _now_dt() - last_seen > timedelta(seconds=90) else "busy" if item["current_tasks"] else "online"
            except ValueError:
                item["display_status"] = "offline"
        else:
            item["display_status"] = item["status"]

    def list_runners(self, workspace_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            query = "SELECT * FROM runners"
            clauses = ["deleted_at IS NULL"]
            params = []
            if workspace_id is not None:
                clauses.append("workspace_id = ?")
                params.append(workspace_id)
            if status is not None:
                clauses.append("status = ?")
                params.append(status)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY name ASC"
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item.pop("credential_hash", None)
                item.pop("device_key_hash", None)
                self._add_activity(conn, item)
                results.append(item)
            return results

    def disable_runner(self, runner_id: str) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM runners WHERE id = ?", (runner_id,)).fetchone()
            if not existing or existing["deleted_at"]:
                raise ResourceNotFoundError(f"Runner not found: {runner_id}")
            conn.execute("UPDATE runners SET status = 'disabled' WHERE id = ?", (runner_id,))
        return self.get_runner(runner_id)

    def enable_runner(self, runner_id: str) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM runners WHERE id = ?", (runner_id,)).fetchone()
            if not existing or existing["deleted_at"]:
                raise ResourceNotFoundError(f"Runner not found: {runner_id}")
            conn.execute("UPDATE runners SET status = 'online' WHERE id = ?", (runner_id,))
        return self.get_runner(runner_id)

    def rename_runner(self, runner_id: str, name: str) -> dict[str, Any]:
        name = name.strip()
        if not name or len(name) > 128:
            raise ValueError("Tên PC phải có từ 1 đến 128 ký tự")
        with self.database.transaction() as conn:
            row = conn.execute("SELECT name,deleted_at FROM runners WHERE id=?", (runner_id,)).fetchone()
            if not row or row["deleted_at"]:
                raise ResourceNotFoundError("Không tìm thấy PC")
            if row["name"] != name:
                conn.execute("UPDATE runners SET name=? WHERE id=?", (name, runner_id))
                conn.execute(
                    "INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator','runner_renamed',?,?,?)",
                    (str(uuid4()), runner_id, json.dumps({"old_name": row["name"], "name": name}), _now_iso()),
                )
        return self.get_runner(runner_id)

    def remove_runner(self, runner_id: str) -> None:
        with self.database.transaction() as conn:
            row = conn.execute("SELECT name,deleted_at FROM runners WHERE id=?", (runner_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError("Không tìm thấy PC")
            if row["deleted_at"]:
                return
            related_runs = conn.execute(
                RUN_CONTEXT + "WHERE r.status NOT IN ('succeeded','failed','cancelled') AND ("
                "EXISTS (SELECT 1 FROM attempts a WHERE a.run_id=r.id AND a.runner_id=?) OR "
                "EXISTS (SELECT 1 FROM task_runs tr JOIN tasks t "
                "ON t.process_version_id=tr.process_version_id AND t.id=tr.task_id "
                "WHERE tr.run_id=r.id AND json_extract(t.definition_json,'$.runner_id')=?)) ORDER BY r.created_at,r.id",
                (runner_id, runner_id),
            ).fetchall()
            if related_runs:
                raise ResourceConflictError(
                    f'Không thể xóa PC “{row["name"]}” vì còn liên quan đến lượt chạy chưa kết thúc: '
                    + reference_list(run_label(r) for r in related_runs)
                    + ". Vào Runs để dừng các lượt chạy này và chờ kết thúc trước khi xóa PC."
                )
            now = _now_iso()
            conn.execute("UPDATE runners SET deleted_at=?,status='disabled',credential_expires_at=? WHERE id=?", (now, now, runner_id))
            conn.execute("UPDATE runner_sessions SET status='revoked' WHERE runner_id=?", (runner_id,))
            conn.execute(
                "UPDATE schedules SET is_active=0,next_run_at=NULL,updated_at=? WHERE default_runner_id=? OR process_version_id IN "
                "(SELECT process_version_id FROM tasks WHERE json_extract(definition_json,'$.runner_id')=?)",
                (now, runner_id, runner_id),
            )
            conn.execute(
                "INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator','runner_removed',?,'{}',?)",
                (str(uuid4()), runner_id, now),
            )

    def revoke_runner(self, runner_id: str) -> None:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM runners WHERE id = ?", (runner_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Runner not found: {runner_id}")
            now = _now_iso()
            conn.execute(
                "UPDATE runners SET status = 'disabled', credential_expires_at = ? WHERE id = ?",
                (now, runner_id),
            )
            conn.execute(
                "UPDATE runner_sessions SET status = 'revoked' WHERE runner_id = ?",
                (runner_id,),
            )

    # -------------------------------------------------------------------------
    # Sessions & Heartbeats
    # -------------------------------------------------------------------------

    def create_session(
        self,
        runner_id: str,
        client_version: str,
        machine_fingerprint: str | None = None,
        capabilities: list[str] | None = None,
        os_name: str | None = None,
        device_id: str | None = None,
        device_key: str | None = None,
    ) -> dict[str, Any]:
        capabilities = capabilities or []
        session_id = f"sess-{secrets.token_hex(8)}"
        now = _now_iso()

        with self.database.transaction() as conn:
            runner = conn.execute("SELECT * FROM runners WHERE id = ?", (runner_id,)).fetchone()
            if not runner or runner["deleted_at"]:
                raise ResourceNotFoundError(f"Runner not found: {runner_id}")
            if runner["status"] == "disabled":
                raise AuthenticationError(f"Cannot start session: Runner {runner_id} is disabled")
            if bool(device_id) != bool(device_key):
                raise ResourceConflictError("Thiếu định danh máy hoặc bằng chứng Client")
            if device_id:
                other = conn.execute("SELECT id FROM runners WHERE workspace_id=? AND device_id=? AND id!=? AND deleted_at IS NULL", (runner["workspace_id"],device_id,runner_id)).fetchone()
                if other or (runner["device_id"] and runner["device_id"] != device_id):
                    raise ResourceConflictError("Định danh máy đã thuộc PC khác; kết nối đúng dòng PC có sẵn.")
                conn.execute("UPDATE runners SET device_id=?,device_key_hash=? WHERE id=?", (device_id,_hash_token(device_key),runner_id))

            # Revoke prior active sessions
            conn.execute(
                "UPDATE runner_sessions SET status = 'revoked' WHERE runner_id = ? AND status = 'active'",
                (runner_id,),
            )

            conn.execute(
                "INSERT INTO runner_sessions (id, runner_id, status, created_at, last_heartbeat_at, capabilities_json) "
                "VALUES (?, ?, 'active', ?, ?, ?)",
                (session_id, runner_id, now, now, json.dumps(capabilities)),
            )

            conn.execute(
                "UPDATE runners SET status = 'online', client_version = ?, machine_fingerprint = COALESCE(?,machine_fingerprint), last_seen_at = ?,cpu_percent=NULL,ram_percent=NULL,memory_total_bytes=NULL,memory_used_bytes=NULL WHERE id = ?",
                (client_version, machine_fingerprint, now, runner_id),
            )
            if os_name:
                conn.execute("UPDATE runners SET os_name=? WHERE id=?", (os_name,runner_id))

        return {
            "session_id": session_id,
            "id": session_id,
            "runner_id": runner_id,
            "status": "active",
            "created_at": now,
            "capabilities": capabilities,
        }

    def require_active_session(self, runner_id: str, session_id: str) -> None:
        with self.database.connect(read_only=True) as conn:
            session = conn.execute(
                "SELECT rs.id FROM runner_sessions rs JOIN runners r ON r.id=rs.runner_id "
                "WHERE rs.id=? AND rs.runner_id=? AND rs.status='active' "
                "AND r.deleted_at IS NULL AND r.status!='disabled'", (session_id, runner_id),
            ).fetchone()
            if not session:
                raise SessionInvalidError("PC cần phiên Client đang hoạt động")

    def close_session(self, runner_id: str, session_id: str):
        with self.database.transaction() as conn:
            session = conn.execute("SELECT status FROM runner_sessions WHERE runner_id=? AND id=?", (runner_id,session_id)).fetchone()
            if not session:
                raise ResourceNotFoundError("Không tìm thấy phiên Client")
            if session["status"] != "active":
                return
            if conn.execute("SELECT 1 FROM attempts WHERE runner_id=? AND session_id=? AND status IN ('running','claimed','reconciling') LIMIT 1", (runner_id,session_id)).fetchone():
                raise ResourceConflictError("Còn việc đang thực thi hoặc chờ đối soát")
            conn.execute("UPDATE runner_sessions SET status='expired' WHERE id=?", (session_id,))
            conn.execute("UPDATE runners SET status='offline' WHERE id=? AND status!='disabled'", (runner_id,))

    @staticmethod
    def _require_idle(conn, runner_id):
        attempt = conn.execute("SELECT 1 FROM attempts WHERE runner_id=? AND status IN ('claimed','running','reconciling') LIMIT 1", (runner_id,)).fetchone()
        pending = conn.execute("SELECT 1 FROM process_runs r JOIN tasks t ON t.process_version_id=r.process_version_id WHERE json_extract(t.definition_json,'$.runner_id')=? AND r.status NOT IN ('succeeded','failed','cancelled') LIMIT 1", (runner_id,)).fetchone()
        if attempt or pending:
            raise ResourceConflictError("PC còn Run chưa kết thúc; dừng Run và chờ kết thúc trước khi hủy kết nối.")

    @staticmethod
    def _require_no_active_execution(conn, runner_id):
        attempt = conn.execute("SELECT 1 FROM attempts WHERE runner_id=? AND status IN ('claimed','running','reconciling') LIMIT 1", (runner_id,)).fetchone()
        if attempt:
            raise ResourceConflictError("PC còn tác vụ đang thực thi; dừng hoặc chờ hoàn tất trước khi đổi kết nối.")

    def disconnect_runner(self, runner_id):
        with self.database.transaction() as conn:
            runner = conn.execute("SELECT id FROM runners WHERE id=? AND deleted_at IS NULL", (runner_id,)).fetchone()
            if not runner:
                raise ResourceNotFoundError("Không tìm thấy PC")
            self._require_idle(conn, runner_id)
            conn.execute("UPDATE runner_sessions SET status='revoked' WHERE runner_id=? AND status='active'", (runner_id,))
            conn.execute("UPDATE runners SET status='offline',credential_expires_at=? WHERE id=?", (_now_iso(),runner_id))
            conn.execute("INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator','runner_disconnected',?,'{}',?)", (str(uuid4()),runner_id,_now_iso()))

    def heartbeat(
        self,
        runner_id: str,
        session_id: str,
        cpu_percent: float | None = None,
        ram_percent: float | None = None,
        running_attempts: list[str] | None = None,
        memory_total_bytes: int | None = None,
        memory_used_bytes: int | None = None,
    ) -> dict[str, Any]:
        now = _now_iso()
        with self.database.transaction() as conn:
            runner = conn.execute("SELECT * FROM runners WHERE id = ?", (runner_id,)).fetchone()
            if not runner:
                raise ResourceNotFoundError(f"Runner not found: {runner_id}")

            session = conn.execute(
                "SELECT * FROM runner_sessions WHERE id = ? AND runner_id = ?",
                (session_id, runner_id),
            ).fetchone()
            if not session:
                raise SessionInvalidError(f"Session not found: {session_id}")
            if session["status"] != "active":
                raise SessionInvalidError(f"Session {session_id} is not active ({session['status']})")

            conn.execute(
                "UPDATE runner_sessions SET last_heartbeat_at = ? WHERE id = ?",
                (now, session_id),
            )

            updates = ["last_seen_at = ?"]
            if runner["status"] != "disabled":
                updates.append("status = 'online'")
            params: list[Any] = [now]
            if cpu_percent is not None:
                updates.append("cpu_percent = ?")
                params.append(cpu_percent)
            if ram_percent is not None:
                updates.append("ram_percent = ?")
                params.append(ram_percent)
            if memory_total_bytes is not None:
                updates.extend(["memory_total_bytes=?", "memory_used_bytes=?"])
                params.extend([memory_total_bytes,memory_used_bytes])
            params.append(runner_id)

            conn.execute(f"UPDATE runners SET {', '.join(updates)} WHERE id = ?", params)

        return {
            "status": "ok",
            "runner_id": runner_id,
            "session_id": session_id,
            "server_time": now,
            "stop_requested": runner["status"] == "disabled",
            "stop_attempt_ids": self.stop_attempt_ids(runner_id, session_id, running_attempts or []),
        }

    def stop_attempt_ids(self, runner_id, session_id, attempts):
        if not attempts:
            return []
        with self.database.connect(read_only=True) as conn:
            rows = conn.execute("SELECT a.id,a.status,r.status run_status,g.expires_at,a.execution_deadline_at FROM attempts a JOIN process_runs r ON r.id=a.run_id LEFT JOIN execution_grants g ON g.attempt_id=a.id WHERE a.runner_id=? AND a.session_id=?", (runner_id,session_id))
            now = _now_iso()
            return [r["id"] for r in rows if r["id"] in attempts and (r["run_status"] in ('cancelling','cancelled','failed') or r["status"] not in ('running','claimed') or not r["expires_at"] or r["expires_at"] <= now or r["execution_deadline_at"] <= now)]

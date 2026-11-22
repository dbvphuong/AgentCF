"""Durable run creation, receipts, work claims, attempt completion, and safe artifact storage (RUN-002, RUN-003)."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any
from uuid import uuid4

from agent_cf_server.infrastructure.audit.repository import redact_secrets
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.skills.access import require_project_skill


def encode_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _build_run_failure_error(connection: Any, run_id: str, all_tasks: list[Any]) -> dict[str, Any]:
    """Summarize concrete task failure code/message for run-level failure records."""
    task_names: dict[str, str] = {}
    pv_row = connection.execute(
        "SELECT pv.definition_json FROM process_runs pr "
        "JOIN process_versions pv ON pv.id = pr.process_version_id WHERE pr.id=?",
        (run_id,),
    ).fetchone()
    if pv_row and pv_row["definition_json"]:
        try:
            for tdef in json.loads(pv_row["definition_json"]).get("tasks", []):
                if isinstance(tdef, dict) and tdef.get("id"):
                    task_names[tdef["id"]] = tdef.get("name") or tdef["id"]
        except Exception:
            pass

    failed_details: list[dict[str, Any]] = []
    for task in all_tasks:
        if task["status"] not in ("failed", "cancelled"):
            continue
        code = None
        msg = ""
        if task["error_json"]:
            try:
                parsed = json.loads(task["error_json"])
                if isinstance(parsed, dict):
                    code = parsed.get("code")
                    msg = str(parsed.get("message") or "").strip()
            except Exception:
                msg = str(task["error_json"]).strip()
        failed_details.append({
            "task_id": task["task_id"],
            "task_name": task_names.get(task["task_id"], task["task_id"]),
            "code": code,
            "message": msg or f"Trạng thái {task['status']}",
        })

    if not failed_details:
        return {"message": "One or more tasks failed"}

    first = failed_details[0]
    code_prefix = f"[{first['code']}] " if first.get("code") else ""
    summary = f'Bước "{first["task_name"]}" thất bại: {code_prefix}{first["message"]}'
    if len(failed_details) > 1:
        summary += f" (+{len(failed_details) - 1} bước khác)"
    payload: dict[str, Any] = {"message": summary, "failed_tasks": failed_details}
    if first.get("code"):
        payload["code"] = first["code"]
    return redact_secrets(payload)


class IdempotencyConflict(ValueError):
    pass


class RevisionConflict(ValueError):
    pass


class ConflictError(ValueError):
    pass


class AuthenticationError(ValueError):
    pass


class RunRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def run_context(self, version_id):
        from agent_cf_server.domain.processes.topic import topic_configuration
        with self.database.connect(read_only=True) as c:
            version = c.execute("SELECT v.definition_json,p.name process_name,j.name project_name FROM process_versions v JOIN processes p ON p.id=v.process_id JOIN projects j ON j.id=p.project_id WHERE v.id=? AND v.status='published' AND p.status='active' AND j.status='active'", (version_id,)).fetchone()
            if not version:
                raise ValueError("Chọn phiên bản Process đã publish và đang hoạt động.")
            result = {"process_name": version["process_name"], "project_name": version["project_name"]}
            try:
                result.update(topic_configuration(json.loads(version["definition_json"]).get("tasks", [])), topic_supported=True)
            except ValueError as exc:
                result.update(topic_supported=False, reason=str(exc))
            return result

    def create_from_version(
        self,
        *,
        version_id: str | None = None,
        principal_id: str,
        request_key: str,
        request_sha256: str,
        run_input: dict | None = None,
        default_runner_id: str | None = None,
        queue_timeout_seconds: int = 86400,
        process_id: str | None = None,
    ) -> dict:
        if run_input is None:
            run_input = {}
        if queue_timeout_seconds <= 0:
            raise ValueError("queue_timeout_seconds must be positive")
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")
        deadline = (now + timedelta(seconds=queue_timeout_seconds)).isoformat().replace("+00:00", "Z")
        with self.database.transaction() as connection:
            receipt_resource = process_id or version_id
            receipt_operation = 'create_process_run' if process_id else 'create_run'
            receipt = connection.execute(
                "SELECT request_sha256,response_json FROM receipts "
                "WHERE principal_id=? AND operation=? AND resource_id=? AND request_key=?",
                (principal_id, receipt_operation, receipt_resource, request_key),
            ).fetchone()
            if receipt:
                if receipt["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("idempotency_conflict")
                return json.loads(receipt["response_json"])
            if process_id:
                from agent_cf_server.infrastructure.projects.management import ProjectManagement
                version_id = ProjectManagement(self.database).freeze_configuration(connection, process_id)
            version = connection.execute(
                "SELECT v.*,p.project_id,j.workspace_id FROM process_versions v "
                "JOIN processes p ON p.id=v.process_id JOIN projects j ON j.id=p.project_id "
                "WHERE v.id=? AND v.status='published' AND p.status='active' AND j.status='active'",
                (version_id,),
            ).fetchone()
            if version is None:
                raise ValueError("Active published ProcessVersion required")
            from agent_cf_server.domain.processes.topic import normalize_topic_input
            run_input = normalize_topic_input(run_input, json.loads(version["definition_json"]).get("tasks", []))
            for task in json.loads(version["definition_json"]).get("tasks", []):
                tool_model_id = task.get("runtime", {}).get("tool_model_id")
                if tool_model_id:
                    tool_model = connection.execute("SELECT status FROM ai_tool_models WHERE id=?", (tool_model_id,)).fetchone()
                    if not tool_model or tool_model["status"] != "active":
                        raise ValueError("Model thực thi đã tắt sử dụng; chọn model khác và publish phiên bản mới")
                if task.get("skill_id"):
                    require_project_skill(connection, task["skill_id"], version["project_id"])
                if task.get("runner_id"):
                    runner = connection.execute("SELECT deleted_at FROM runners WHERE id=?", (task["runner_id"],)).fetchone()
                    if runner and runner["deleted_at"]:
                        raise ValueError("PC được gán cho Process đã bị xóa; chọn PC khác và publish phiên bản mới")
            run_id = str(uuid4())
            connection.execute(
                "INSERT INTO process_runs(id,workspace_id,project_id,process_id,process_version_id,"
                "snapshot_sha256,status,input_json,created_at,queue_deadline_at) "
                "VALUES (?,?,?,?,?,?,'queued',?,?,?)",
                (run_id, version["workspace_id"], version["project_id"], version["process_id"], version_id,
                 version["snapshot_sha256"], encode_json(run_input), at, deadline),
            )
            tasks = connection.execute("SELECT id FROM tasks WHERE process_version_id=? ORDER BY id", (version_id,)).fetchall()
            if not tasks:
                raise ValueError("Published ProcessVersion has no Tasks")

            # Root tasks with no incoming dependencies start as 'queued'
            dep_targets = {
                r["target_task_id"]
                for r in connection.execute(
                    "SELECT target_task_id FROM dependencies WHERE process_version_id=?", (version_id,)
                ).fetchall()
            }

            for task in tasks:
                is_root = task["id"] not in dep_targets
                status = "queued" if is_root else "pending"
                queued_at = at if is_root else None
                queue_deadline = deadline if is_root else None
                connection.execute(
                    "INSERT INTO task_runs(id,run_id,process_version_id,task_id,status,queued_at,queue_deadline_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (str(uuid4()), run_id, version_id, task["id"], status, queued_at, queue_deadline),
                )

            event_id = str(uuid4())
            connection.execute(
                "INSERT INTO run_events(id,run_id,sequence,event_type,data_json,recorded_at) VALUES (?,?,1,'run_created','{}',?)",
                (event_id, run_id, at),
            )
            connection.execute(
                "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) "
                "VALUES (?,?,?,'run_created',?,'{}',?)",
                (str(uuid4()), run_id, principal_id, run_id, at),
            )
            connection.execute(
                "INSERT INTO engine_outbox(command_id,run_id,sequence,command_type,payload_json,created_at) "
                "VALUES (?,?,1,'start_run',?,?)",
                (str(uuid4()), run_id, encode_json({"run_id": run_id, "revision": 1}), at),
            )
            response = {"run_id": run_id, "revision": 1}
            connection.execute(
                "INSERT INTO receipts(principal_id,operation,resource_id,request_key,request_sha256,response_json,created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (principal_id, receipt_operation, receipt_resource, request_key, request_sha256, encode_json(response), at),
            )
            return response

    def _get_with_connection(self, connection, run_id: str) -> dict:
        row = connection.execute("SELECT * FROM process_runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        result = dict(row)
        for name in ("input", "output", "error"):
            value = result.pop(name + "_json")
            result[name] = json.loads(value) if value is not None else None

        task_runs = []
        for task in connection.execute(
            "SELECT tr.*, t.task_key FROM task_runs tr "
            "LEFT JOIN tasks t ON t.process_version_id=tr.process_version_id AND t.id=tr.task_id "
            "WHERE tr.run_id=? ORDER BY tr.task_id", (run_id,)
        ).fetchall():
            tr_dict = dict(task)
            for name in ("input", "output", "error"):
                val = tr_dict.pop(name + "_json", None)
                tr_dict[name] = json.loads(val) if val is not None else None
            task_runs.append(tr_dict)
        result["task_runs"] = task_runs

        artifacts = []
        for art in connection.execute(
            "SELECT a.* FROM artifacts a JOIN attempts att ON att.id=a.attempt_id WHERE att.run_id=?", (run_id,)
        ).fetchall():
            artifacts.append(dict(art))
        result["artifacts"] = artifacts
        return result

    def get(self, run_id: str) -> dict:
        with self.database.connect() as connection:
            return self._get_with_connection(connection, run_id)

    def list_runs(
        self,
        *,
        workspace_id: str | None = None,
        project_id: str | None = None,
        process_id: str | None = None,
        status_filter: list[str] | None = None,
        cursor: str | None = None,
        limit: int = 50,
        search: str | None = None,
        started_from: str | None = None,
        started_to: str | None = None,
    ) -> tuple[list[dict], str | None]:
        with self.database.connect() as connection:
            clauses = ["1=1"]
            params: list[Any] = []
            if workspace_id:
                clauses.append("pr.workspace_id=?")
                params.append(workspace_id)
            if project_id:
                clauses.append("pr.project_id=?")
                params.append(project_id)
            if process_id:
                clauses.append("pr.process_id=?")
                params.append(process_id)
            if status_filter:
                placeholders = ",".join("?" for _ in status_filter)
                clauses.append(f"pr.status IN ({placeholders})")
                params.extend(status_filter)
            if search:
                clauses.append("instr(lower(pr.id),lower(?)) > 0")
                params.append(search)
            if started_from:
                clauses.append("COALESCE(pr.started_at,pr.created_at) >= ?")
                params.append(started_from)
            if started_to:
                clauses.append("COALESCE(pr.started_at,pr.created_at) < ?")
                params.append(started_to)
            if cursor:
                parts = cursor.split("|", 1)
                if len(parts) == 2:
                    clauses.append("(pr.created_at, pr.id) < (?, ?)")
                    params.extend(parts)

            where = " AND ".join(clauses)
            sql = f"SELECT pr.*, p.name as process_name FROM process_runs pr JOIN processes p ON p.id=pr.process_id WHERE {where} ORDER BY pr.created_at DESC, pr.id DESC LIMIT ?"
            params.append(limit + 1)
            rows = connection.execute(sql, params).fetchall()

            items = []
            for r in rows:
                item = dict(r)
                for name in ("input", "output", "error"):
                    val = item.pop(name + "_json")
                    item[name] = json.loads(val) if val is not None else None
                # Add compact task runs summary
                task_rows = connection.execute(
                    "SELECT id, task_id, status, generation FROM task_runs WHERE run_id=? ORDER BY task_id",
                    (item["id"],),
                ).fetchall()
                item["task_runs"] = [dict(t) for t in task_rows]
                items.append(item)

            next_cursor = None
            if len(items) > limit:
                items = items[:limit]
                last = items[-1]
                next_cursor = f"{last['created_at']}|{last['id']}"
            return items, next_cursor

    def count_runs(self, *, project_id=None, process_id=None, status_filter=None, search=None, started_from=None, started_to=None) -> int:
        clauses, params = [], []
        for column, value in (("project_id", project_id), ("process_id", process_id)):
            if value:
                clauses.append(f"{column}=?")
                params.append(value)
        if status_filter:
            clauses.append("status IN (" + ",".join("?" for _ in status_filter) + ")")
            params.extend(status_filter)
        if search:
            clauses.append("instr(lower(id),lower(?)) > 0")
            params.append(search)
        if started_from:
            clauses.append("COALESCE(started_at,created_at) >= ?")
            params.append(started_from)
        if started_to:
            clauses.append("COALESCE(started_at,created_at) < ?")
            params.append(started_to)
        with self.database.connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM process_runs" + (" WHERE " + " AND ".join(clauses) if clauses else ""), params).fetchone()[0]

    def get_run_events(
        self,
        run_id: str,
        cursor: int | None = None,
        limit: int = 50,
    ) -> tuple[list[dict], int | None]:
        with self.database.connect() as connection:
            if cursor:
                rows = connection.execute(
                    "SELECT * FROM run_events WHERE run_id=? AND sequence > ? ORDER BY sequence ASC LIMIT ?",
                    (run_id, cursor, limit + 1),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM run_events WHERE run_id=? ORDER BY sequence ASC LIMIT ?",
                    (run_id, limit + 1),
                ).fetchall()
            items = []
            for r in rows:
                item = dict(r)
                item["data"] = json.loads(item.pop("data_json"))
                items.append(item)
            next_cursor = None
            if len(items) > limit:
                items = items[:limit]
                next_cursor = items[-1]["sequence"]
            return items, next_cursor

    def cancel_run(
        self,
        *,
        run_id: str,
        principal_id: str,
        request_key: str,
        request_sha256: str,
        reason: str = "Operator cancelled",
    ) -> dict:
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")
        with self.database.transaction() as connection:
            receipt = connection.execute(
                "SELECT request_sha256, response_json FROM receipts "
                "WHERE principal_id=? AND operation='cancel_run' AND resource_id=? AND request_key=?",
                (principal_id, run_id, request_key),
            ).fetchone()
            if receipt:
                if receipt["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("idempotency_conflict")
                return json.loads(receipt["response_json"])

            run = connection.execute("SELECT * FROM process_runs WHERE id=?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(run_id)
            if run["status"] in ("succeeded", "failed", "cancelled"):
                raise ConflictError("run_terminal")
            if run["status"] == "cancelling":
                return self.get(run_id)

            # Cancel pending/queued task runs
            connection.execute(
                "UPDATE task_runs SET status='cancelled' WHERE run_id=? AND status IN ('pending', 'queued')",
                (run_id,),
            )
            # Check if there are active running/reconciling task runs
            active_tasks = connection.execute(
                "SELECT COUNT(*) FROM task_runs WHERE run_id=? AND status IN ('running', 'reconciling')",
                (run_id,),
            ).fetchone()[0]

            new_status = "cancelling" if active_tasks > 0 else "cancelled"
            ended_at = at if new_status == "cancelled" else None

            connection.execute(
                "UPDATE process_runs SET status=?, attention_reason=?, ended_at=?, revision=revision+1 WHERE id=?",
                (new_status, reason, ended_at, run_id),
            )
            seq = connection.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?", (run_id,)).fetchone()[0]
            connection.execute(
                "INSERT INTO run_events(id,run_id,sequence,event_type,data_json,recorded_at) VALUES (?,?,?,'run_cancelled',?,?)",
                (str(uuid4()), run_id, seq, encode_json({"reason": reason, "status": new_status}), at),
            )
            connection.execute(
                "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,?,?,?,?,?,?)",
                (str(uuid4()), run_id, principal_id, "run_cancelled", run_id, encode_json({"reason": reason}), at),
            )
            res = self._get_with_connection(connection, run_id)
            connection.execute(
                "INSERT INTO receipts(principal_id,operation,resource_id,request_key,request_sha256,response_json,created_at) VALUES (?,'cancel_run',?,?,?,?,?)",
                (principal_id, run_id, request_key, request_sha256, encode_json(res), at),
            )
            return res

    def list_work(self, runner_id: str, session_id: str) -> list[dict]:
        with self.database.connect() as connection:
            session = connection.execute(
                "SELECT rs.*, r.workspace_id, r.status as runner_status FROM runner_sessions rs "
                "JOIN runners r ON r.id=rs.runner_id "
                "WHERE rs.id=? AND rs.runner_id=? AND rs.status='active'",
                (session_id, runner_id),
            ).fetchone()
            if session is None or session["runner_status"] == "disabled":
                return []

            rows = connection.execute(
                "SELECT tr.id as task_run_id, tr.run_id, tr.process_version_id, tr.task_id, t.definition_json as task_def_json "
                "FROM task_runs tr "
                "JOIN process_runs pr ON pr.id=tr.run_id "
                "JOIN tasks t ON t.process_version_id=tr.process_version_id AND t.id=tr.task_id "
                "WHERE tr.status='queued' AND pr.status IN ('queued', 'running') AND pr.workspace_id=? "
                "ORDER BY tr.queued_at ASC, tr.id ASC",
                (session["workspace_id"],),
            ).fetchall()
            eligible = []
            for r in rows:
                try:
                    task_def = json.loads(r["task_def_json"])
                    assigned_runner = task_def.get("runner_id")
                    if assigned_runner is not None and assigned_runner != runner_id:
                        continue
                    capabilities = json.loads(session["capabilities_json"])
                    if "desktop-client-v1" in capabilities:
                        required = "python" if task_def.get("kind") == "robot" else task_def.get("runtime", {}).get("adapter")
                        if required not in capabilities:
                            continue
                except Exception:
                    pass
                eligible.append({
                    "task_run_id": r["task_run_id"],
                    "run_id": r["run_id"],
                    "process_version_id": r["process_version_id"],
                    "task_id": r["task_id"],
                })
            return eligible

    def claim_task_run(
        self,
        *,
        task_run_id: str,
        runner_id: str,
        session_id: str,
        request_key: str,
        request_sha256: str,
        lease_seconds: int = 60,
    ) -> dict:
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")
        expires_at = (now + timedelta(seconds=lease_seconds)).isoformat().replace("+00:00", "Z")
        execution_deadline_at = (now + timedelta(seconds=1800)).isoformat().replace("+00:00", "Z")

        with self.database.transaction() as connection:
            receipt = connection.execute(
                "SELECT request_sha256, response_json FROM receipts "
                "WHERE principal_id=? AND operation='claim_task' AND resource_id=? AND request_key=?",
                (runner_id, task_run_id, request_key),
            ).fetchone()
            if receipt:
                if receipt["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("idempotency_conflict")
                return json.loads(receipt["response_json"])

            session = connection.execute(
                "SELECT rs.*, r.workspace_id, r.status as runner_status FROM runner_sessions rs "
                "JOIN runners r ON r.id=rs.runner_id "
                "WHERE rs.id=? AND rs.runner_id=? AND rs.status='active'",
                (session_id, runner_id),
            ).fetchone()
            if session is None:
                raise AuthenticationError("Active runner session required")
            if session["runner_status"] == "disabled":
                raise AuthenticationError("Runner is disabled")

            tr = connection.execute(
                "SELECT tr.*, pr.workspace_id, pr.status as run_status, pr.snapshot_sha256, "
                "pr.input_json as run_input_json, t.definition_json as task_def_json "
                "FROM task_runs tr "
                "JOIN process_runs pr ON pr.id=tr.run_id "
                "JOIN tasks t ON t.process_version_id=tr.process_version_id AND t.id=tr.task_id "
                "WHERE tr.id=?",
                (task_run_id,),
            ).fetchone()
            if tr is None:
                raise KeyError(task_run_id)
            if tr["workspace_id"] != session["workspace_id"]:
                raise AuthenticationError("Runner workspace mismatch")
            if tr["status"] != "queued":
                raise ConflictError("task_not_claimable")
            if tr["run_status"] not in ("queued", "running"):
                raise ConflictError("run_not_dispatchable")

            task_def = json.loads(tr["task_def_json"])
            assigned_runner = task_def.get("runner_id")
            if assigned_runner is not None and assigned_runner != runner_id:
                raise ConflictError(f"Task is pinned to runner '{assigned_runner}', not '{runner_id}'")
            capabilities = json.loads(session["capabilities_json"])
            if "desktop-client-v1" in capabilities:
                required = "python" if task_def.get("kind") == "robot" else task_def.get("runtime", {}).get("adapter")
                if required not in capabilities:
                    raise ConflictError("Công cụ AI chưa sẵn sàng trên PC này")

            attempt_id = str(uuid4())
            generation = tr["generation"] + 1
            execution_token = secrets.token_hex(32)
            token_hash = hashlib.sha256(execution_token.encode("utf-8")).hexdigest()

            connection.execute(
                "INSERT INTO attempts(id,task_run_id,run_id,runner_id,session_id,generation,status,claimed_at,execution_deadline_at) "
                "VALUES (?,?,?,?,?,?,'running',?,?)",
                (attempt_id, task_run_id, tr["run_id"], runner_id, session_id, generation, at, execution_deadline_at),
            )
            connection.execute(
                "INSERT INTO execution_grants(attempt_id,task_run_id,runner_id,session_id,generation,token_hash,expires_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (attempt_id, task_run_id, runner_id, session_id, generation, token_hash, expires_at),
            )
            updated = connection.execute(
                "UPDATE task_runs SET status='running', generation=? WHERE id=? AND status='queued'",
                (generation, task_run_id),
            )
            if updated.rowcount != 1:
                raise ConflictError("claim_race_lost")

            if tr["run_status"] == "queued":
                connection.execute(
                    "UPDATE process_runs SET status='running', started_at=COALESCE(started_at, ?), revision=revision+1 WHERE id=?",
                    (at, tr["run_id"]),
                )

            seq = connection.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?", (tr["run_id"],)).fetchone()[0]
            connection.execute(
                "INSERT INTO run_events(id,run_id,sequence,event_type,task_run_id,attempt_id,data_json,recorded_at) "
                "VALUES (?,?,?,'task_claimed',?,?,?,?)",
                (str(uuid4()), tr["run_id"], seq, task_run_id, attempt_id, encode_json({"runner_id": runner_id, "generation": generation}), at),
            )
            connection.execute(
                "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid4()), tr["run_id"], runner_id, "task_claimed", task_run_id, encode_json({"attempt_id": attempt_id}), at),
            )

            task_def = json.loads(tr["task_def_json"])
            run_input = json.loads(tr["run_input_json"])
            input_data = json.loads(tr["input_json"]) if tr["input_json"] else run_input
            if run_input.get("topic_directory"):
                input_data = {**input_data, **{k:run_input[k] for k in ("topic_directory", "topic", "request") if k in run_input}}

            existing_artifacts = connection.execute(
                "SELECT a.id, a.logical_name, a.media_type, a.size_bytes, a.sha256 "
                "FROM artifacts a "
                "JOIN attempts att ON att.id=a.attempt_id "
                "WHERE att.run_id=? AND a.availability='available'",
                (tr["run_id"],),
            ).fetchall()

            pv_row = connection.execute(
                "SELECT definition_json FROM process_versions WHERE id=?",
                (tr["process_version_id"],),
            ).fetchone()
            proc_def = json.loads(pv_row["definition_json"]) if pv_row and pv_row["definition_json"] else {}
            session_mode = proc_def.get("session_mode") or task_def.get("session_mode", "shared_per_tool")
            tool_adapter = task_def.get("runtime", {}).get("adapter")
            tool_session_id = None

            if session_mode == "shared_per_tool" and tool_adapter:
                prior_runs = connection.execute(
                    "SELECT tr.output_json, t.definition_json "
                    "FROM task_runs tr "
                    "JOIN tasks t ON t.process_version_id=tr.process_version_id AND t.id=tr.task_id "
                    "WHERE tr.run_id=? AND tr.status='succeeded' AND tr.output_json IS NOT NULL "
                    "ORDER BY tr.queued_at ASC, tr.id ASC",
                    (tr["run_id"],),
                ).fetchall()
                for pr_row in prior_runs:
                    try:
                        t_def = json.loads(pr_row["definition_json"])
                        if t_def.get("runtime", {}).get("adapter") == tool_adapter:
                            out_meta = json.loads(pr_row["output_json"])
                            if out_meta.get("session_id"):
                                tool_session_id = out_meta["session_id"]
                    except Exception:
                        pass

            assignment = {
                "run_id": tr["run_id"],
                "task_run_id": task_run_id,
                "attempt_id": attempt_id,
                "runner_id": runner_id,
                "session_id": session_id,
                "generation": generation,
                "execution_token": execution_token,
                "server_time": at,
                "expires_at": expires_at,
                "execution_deadline_at": execution_deadline_at,
                "snapshot_sha256": tr["snapshot_sha256"],
                "task": task_def,
                "input": input_data,
                "run_artifacts": [dict(a) for a in existing_artifacts],
                "renew_interval_seconds": 15,
                "session_mode": session_mode,
                "tool_session_id": tool_session_id,
            }
            connection.execute(
                "INSERT INTO receipts(principal_id,operation,resource_id,request_key,request_sha256,response_json,created_at) "
                "VALUES (?,'claim_task',?,?,?,?,?)",
                (runner_id, task_run_id, request_key, request_sha256, encode_json(assignment), at),
            )
            return assignment

    def complete_attempt(
        self,
        *,
        attempt_id: str,
        execution_token: str,
        outcome: str,
        process_stopped: bool,
        exit_code: int,
        output: dict | None,
        error: dict | None,
        artifact_ids: list[str] | None,
        process_evidence: dict | None,
        request_key: str,
        request_sha256: str,
    ) -> dict:
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")
        token_hash = hashlib.sha256(execution_token.encode("utf-8")).hexdigest()

        with self.database.transaction() as connection:
            receipt = connection.execute(
                "SELECT request_sha256, response_json FROM receipts "
                "WHERE operation='complete_attempt' AND resource_id=? AND request_key=?",
                (attempt_id, request_key),
            ).fetchone()
            if receipt:
                if receipt["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("idempotency_conflict")
                return json.loads(receipt["response_json"])

            grant = connection.execute(
                "SELECT g.*, a.run_id, a.task_run_id, a.status as attempt_status, tr.process_version_id, tr.task_id "
                "FROM execution_grants g "
                "JOIN attempts a ON a.id=g.attempt_id "
                "JOIN task_runs tr ON tr.id=a.task_run_id "
                "WHERE g.attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if grant is None:
                raise KeyError(attempt_id)
            if grant["token_hash"] != token_hash:
                raise AuthenticationError("Invalid execution token")
            if grant["attempt_status"] not in ("claimed", "running"):
                raise ConflictError("attempt_already_settled")
            if grant["revoked_at"] is not None:
                raise ConflictError("stale_execution: grant has been revoked")
            if grant["expires_at"] < at:
                raise ConflictError("stale_execution: lease has expired")

            connection.execute(
                "UPDATE execution_grants SET revoked_at=? WHERE attempt_id=?",
                (at, attempt_id),
            )
            connection.execute(
                "UPDATE attempts SET status=?, ended_at=?, output_json=?, error_json=?, launch_evidence_json=? WHERE id=?",
                (outcome, at, encode_json(output) if output is not None else None,
                 encode_json(error) if error is not None else None,
                 encode_json(process_evidence) if process_evidence is not None else None,
                 attempt_id),
            )
            connection.execute(
                "UPDATE task_runs SET status=?, output_json=?, error_json=? WHERE id=?",
                (outcome, encode_json(output) if output is not None else None,
                 encode_json(error) if error is not None else None,
                 grant["task_run_id"]),
            )

            seq = connection.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?", (grant["run_id"],)).fetchone()[0]
            event_type = "task_completed" if outcome == "succeeded" else "task_failed"
            event_data: dict[str, Any] = {
                "exit_code": exit_code,
                "outcome": outcome,
                "artifacts": artifact_ids or [],
            }
            audit_data: dict[str, Any] = {
                "attempt_id": attempt_id,
                "exit_code": exit_code,
                "outcome": outcome,
            }
            if outcome != "succeeded" and error is not None:
                redacted_error = redact_secrets(error)
                event_data["error"] = redacted_error
                audit_data["error"] = redacted_error
            connection.execute(
                "INSERT INTO run_events(id,run_id,sequence,event_type,task_run_id,attempt_id,data_json,recorded_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (str(uuid4()), grant["run_id"], seq, event_type, grant["task_run_id"], attempt_id,
                 encode_json(event_data), at),
            )
            connection.execute(
                "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid4()), grant["run_id"], grant["runner_id"], event_type, grant["task_run_id"],
                 encode_json(redact_secrets(audit_data)), at),
            )

            if outcome == "succeeded":
                pending_tasks = connection.execute(
                    "SELECT tr.id, tr.task_id, tr.process_version_id FROM task_runs tr "
                    "WHERE tr.run_id=? AND tr.status='pending'",
                    (grant["run_id"],),
                ).fetchall()
                for pt in pending_tasks:
                    deps = connection.execute(
                        "SELECT source_task_id FROM dependencies WHERE process_version_id=? AND target_task_id=?",
                        (pt["process_version_id"], pt["task_id"]),
                    ).fetchall()
                    if deps:
                        source_ids = [d["source_task_id"] for d in deps]
                        placeholders = ",".join("?" for _ in source_ids)
                        succeeded_count = connection.execute(
                            f"SELECT COUNT(*) FROM task_runs WHERE run_id=? AND task_id IN ({placeholders}) AND status='succeeded'",
                            [grant["run_id"]] + source_ids,
                        ).fetchone()[0]
                        if succeeded_count == len(source_ids):
                            connection.execute(
                                "UPDATE task_runs SET status='queued', queued_at=? WHERE id=?",
                                (at, pt["id"]),
                            )
            elif outcome in ("failed", "cancelled"):
                connection.execute(
                    "UPDATE task_runs SET status='skipped' WHERE run_id=? AND status='pending'",
                    (grant["run_id"],),
                )

            all_tasks = connection.execute(
                "SELECT task_id, status, output_json, error_json FROM task_runs WHERE run_id=?",
                (grant["run_id"],),
            ).fetchall()
            all_terminal = all(t["status"] in ("succeeded", "failed", "skipped", "cancelled") for t in all_tasks)
            if all_terminal:
                all_succeeded = all(t["status"] == "succeeded" for t in all_tasks)
                if all_succeeded:
                    agg_output = {}
                    for t in all_tasks:
                        if t["output_json"]:
                            try:
                                agg_output[t["task_id"]] = json.loads(t["output_json"])
                            except Exception:
                                pass
                    connection.execute(
                        "UPDATE process_runs SET status='succeeded', ended_at=?, output_json=?, revision=revision+1 WHERE id=?",
                        (at, encode_json(agg_output), grant["run_id"]),
                    )
                    seq = connection.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?", (grant["run_id"],)).fetchone()[0]
                    connection.execute(
                        "INSERT INTO run_events(id,run_id,sequence,event_type,data_json,recorded_at) VALUES (?,?,?,'run_succeeded','{}',?)",
                        (str(uuid4()), grant["run_id"], seq, at),
                    )
                    connection.execute(
                        "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) "
                        "VALUES (?,?,'engine','run_succeeded',?,'{}',?)",
                        (str(uuid4()), grant["run_id"], grant["run_id"], at),
                    )
                else:
                    err_msg = _build_run_failure_error(connection, grant["run_id"], all_tasks)
                    connection.execute(
                        "UPDATE process_runs SET status='failed', ended_at=?, error_json=?, revision=revision+1 WHERE id=?",
                        (at, encode_json(err_msg), grant["run_id"]),
                    )
                    seq = connection.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?", (grant["run_id"],)).fetchone()[0]
                    connection.execute(
                        "INSERT INTO run_events(id,run_id,sequence,event_type,data_json,recorded_at) VALUES (?,?,?,'run_failed',?,?)",
                        (str(uuid4()), grant["run_id"], seq, encode_json(err_msg), at),
                    )
                    connection.execute(
                        "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) "
                        "VALUES (?,?,'engine','run_failed',?,?,?)",
                        (str(uuid4()), grant["run_id"], grant["run_id"], encode_json(redact_secrets(err_msg)), at),
                    )

            receipt_resp = {"receipt": "complete_attempt_ok", "attempt_id": attempt_id, "recorded_at": at}
            connection.execute(
                "INSERT INTO receipts(principal_id,operation,resource_id,request_key,request_sha256,response_json,created_at) "
                "VALUES (?,'complete_attempt',?,?,?,?,?)",
                (grant["runner_id"], attempt_id, request_key, request_sha256, encode_json(receipt_resp), at),
            )
            return receipt_resp

    def register_artifact(
        self,
        *,
        attempt_id: str,
        execution_token: str,
        logical_name: str,
        media_type: str,
        size_bytes: int,
        sha256: str,
        request_key: str,
        request_sha256: str,
    ) -> dict:
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")
        token_hash = hashlib.sha256(execution_token.encode("utf-8")).hexdigest()

        with self.database.transaction() as connection:
            receipt = connection.execute(
                "SELECT request_sha256, response_json FROM receipts "
                "WHERE operation='register_artifact' AND resource_id=? AND request_key=?",
                (attempt_id, request_key),
            ).fetchone()
            if receipt:
                if receipt["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("idempotency_conflict")
                return json.loads(receipt["response_json"])

            grant = connection.execute(
                "SELECT g.*, a.status as attempt_status FROM execution_grants g "
                "JOIN attempts a ON a.id=g.attempt_id "
                "WHERE g.attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if grant is None:
                raise KeyError(attempt_id)
            if grant["token_hash"] != token_hash:
                raise AuthenticationError("Invalid execution token")
            if grant["attempt_status"] not in ("claimed", "running"):
                raise ConflictError("attempt_already_settled")
            if grant["revoked_at"] is not None:
                raise ConflictError("stale_execution: grant has been revoked")
            if grant["expires_at"] < at:
                raise ConflictError("stale_execution: lease has expired")

            existing = connection.execute(
                "SELECT * FROM artifacts WHERE attempt_id=? AND logical_name=?",
                (attempt_id, logical_name),
            ).fetchone()
            if existing:
                return dict(existing)

            artifact_id = str(uuid4())
            storage_key = f"{attempt_id}/{logical_name}"
            connection.execute(
                "INSERT INTO artifacts(id,attempt_id,logical_name,media_type,size_bytes,sha256,availability,storage_key,created_at) "
                "VALUES (?,?,?,?,?,?,'uploading',?,?)",
                (artifact_id, attempt_id, logical_name, media_type, size_bytes, sha256, storage_key, at),
            )
            artifact_ref = {
                "id": artifact_id,
                "attempt_id": attempt_id,
                "logical_name": logical_name,
                "media_type": media_type,
                "size_bytes": size_bytes,
                "sha256": sha256,
                "availability": "uploading",
                "storage_key": storage_key,
                "created_at": at,
            }
            connection.execute(
                "INSERT INTO receipts(principal_id,operation,resource_id,request_key,request_sha256,response_json,created_at) "
                "VALUES (?,'register_artifact',?,?,?,?,?)",
                (grant["runner_id"], attempt_id, request_key, request_sha256, encode_json(artifact_ref), at),
            )
            return artifact_ref

    def save_artifact_content(
        self,
        *,
        artifact_id: str,
        execution_token: str,
        content: bytes,
        storage_dir: Path,
    ) -> dict:
        token_hash = hashlib.sha256(execution_token.encode("utf-8")).hexdigest()
        with self.database.transaction() as connection:
            art = connection.execute(
                "SELECT a.*, g.token_hash FROM artifacts a "
                "JOIN execution_grants g ON g.attempt_id=a.attempt_id "
                "WHERE a.id=?",
                (artifact_id,),
            ).fetchone()
            if art is None:
                raise KeyError(artifact_id)
            if art["token_hash"] != token_hash:
                raise AuthenticationError("Invalid execution token")

            if len(content) != art["size_bytes"]:
                raise ValueError(f"Content length mismatch: expected {art['size_bytes']}, got {len(content)}")
            content_hash = hashlib.sha256(content).hexdigest()
            if content_hash != art["sha256"]:
                raise ValueError(f"Content sha256 mismatch: expected {art['sha256']}, got {content_hash}")

            target_path = storage_dir / art["storage_key"]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(content)

            connection.execute(
                "UPDATE artifacts SET availability='available' WHERE id=?",
                (artifact_id,),
            )
            row = connection.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
            return dict(row)

    def get_artifact(self, artifact_id: str, storage_dir: Path) -> tuple[dict, bytes]:
        with self.database.connect() as connection:
            art = connection.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
            if art is None:
                raise KeyError(artifact_id)
            art_dict = dict(art)
            if art_dict["availability"] != "available":
                raise ValueError("Artifact not available yet")
            target_path = (storage_dir / art_dict["storage_key"]).resolve()
            if not str(target_path).startswith(str(storage_dir.resolve())):
                raise ValueError("Illegal storage path traversal")
            if not target_path.exists():
                raise FileNotFoundError(f"Artifact file not found: {art_dict['storage_key']}")
            return art_dict, target_path.read_bytes()

    def mark_reconciling(
        self, *, run_id: str, expected_revision: int, command_id: str, request_sha256: str, reason: str
    ) -> dict:
        """CAS + inbox + audit/outbox in one transaction; never grants execution."""
        at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self.database.transaction() as connection:
            prior = connection.execute("SELECT * FROM engine_inbox WHERE command_id=?", (command_id,)).fetchone()
            if prior:
                if prior["run_id"] != run_id or prior["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("idempotency_conflict")
                return json.loads(prior["response_json"])
            updated = connection.execute(
                "UPDATE process_runs SET status='reconciling',attention_reason=?,revision=revision+1 "
                "WHERE id=? AND revision=? AND status IN ('running','reconciling')",
                (reason, run_id, expected_revision),
            )
            if updated.rowcount != 1:
                raise RevisionConflict("revision_conflict")
            revision = expected_revision + 1
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?", (run_id,)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO run_events(id,run_id,sequence,event_type,data_json,recorded_at) VALUES (?,?,?,'state_changed',?,?)",
                (str(uuid4()), run_id, sequence, encode_json({"status": "reconciling", "reason": reason}), at),
            )
            connection.execute(
                "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) "
                "VALUES (?,?,'engine','reconciling',?,?,?)",
                (str(uuid4()), run_id, run_id, encode_json({"reason": reason}), at),
            )
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM engine_outbox WHERE run_id=?", (run_id,)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO engine_outbox(command_id,run_id,sequence,command_type,payload_json,created_at) "
                "VALUES (?,?,?,'state_changed',?,?)",
                (str(uuid4()), run_id, sequence, encode_json({"revision": revision}), at),
            )
            response = {"run_id": run_id, "revision": revision}
            connection.execute(
                "INSERT INTO engine_inbox(command_id,run_id,request_sha256,response_json,applied_at) VALUES (?,?,?,?,?)",
                (command_id, run_id, request_sha256, encode_json(response), at),
            )
            return response

    def record_attempt_observation(
        self,
        *,
        attempt_id: str,
        runner_id: str,
        session_id: str,
        observation_type: str,
        data: dict,
        request_key: str,
        request_sha256: str,
    ) -> dict:
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")

        with self.database.transaction() as connection:
            receipt = connection.execute(
                "SELECT request_sha256, response_json FROM receipts "
                "WHERE operation='record_attempt_observation' AND resource_id=? AND request_key=?",
                (attempt_id, request_key),
            ).fetchone()
            if receipt:
                if receipt["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("idempotency_conflict")
                return json.loads(receipt["response_json"])

            session = connection.execute(
                "SELECT rs.*, r.status as runner_status FROM runner_sessions rs "
                "JOIN runners r ON r.id=rs.runner_id "
                "WHERE rs.id=? AND rs.runner_id=? AND rs.status='active'",
                (session_id, runner_id),
            ).fetchone()
            if session is None or session["runner_status"] == "disabled":
                raise AuthenticationError("Active runner session required")

            attempt = connection.execute(
                "SELECT * FROM attempts WHERE id=?",
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise KeyError(attempt_id)
            if attempt["runner_id"] != runner_id:
                raise AuthenticationError("Runner does not own this attempt")

            safe_data = redact_secrets(data)
            seq = connection.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?",
                (attempt["run_id"],),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO run_events(id,run_id,sequence,event_type,task_run_id,attempt_id,data_json,recorded_at) "
                "VALUES (?,?,?,'attempt_observation',?,?,?,?)",
                (str(uuid4()), attempt["run_id"], seq, attempt["task_run_id"], attempt_id,
                 encode_json({"observation_type": observation_type, "data": safe_data, "recorded_by": runner_id}), at),
            )
            connection.execute(
                "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid4()), attempt["run_id"], runner_id, "attempt_observation", attempt_id,
                 encode_json({"observation_type": observation_type, "data": safe_data}), at),
            )

            res = {
                "attempt_id": attempt_id,
                "status": "accepted",
                "observation_type": observation_type,
                "recorded_at": at,
            }
            connection.execute(
                "INSERT INTO receipts(principal_id,operation,resource_id,request_key,request_sha256,response_json,created_at) "
                "VALUES (?,'record_attempt_observation',?,?,?,?,?)",
                (runner_id, attempt_id, request_key, request_sha256, encode_json(res), at),
            )
            return res

    def set_task_waiting_for_input(
        self,
        *,
        task_run_id: str,
        waiting_for: str = "human_input",
        reason: str = "waiting_for_input",
    ) -> None:
        at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self.database.transaction() as connection:
            tr = connection.execute("SELECT * FROM task_runs WHERE id=?", (task_run_id,)).fetchone()
            if not tr:
                raise KeyError(task_run_id)
            connection.execute(
                "UPDATE task_runs SET waiting_for=?, attention_reason=? WHERE id=?",
                (waiting_for, reason, task_run_id),
            )
            connection.execute(
                "UPDATE process_runs SET attention_reason=?, revision=revision+1 WHERE id=?",
                (reason, tr["run_id"]),
            )
            seq = connection.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?", (tr["run_id"],)).fetchone()[0]
            connection.execute(
                "INSERT INTO run_events(id,run_id,sequence,event_type,task_run_id,data_json,recorded_at) "
                "VALUES (?,?,?,'task_waiting_for_input',?,?,?)",
                (str(uuid4()), tr["run_id"], seq, task_run_id, encode_json({"waiting_for": waiting_for, "reason": reason}), at),
            )

    def continue_run(
        self,
        *,
        run_id: str,
        principal_id: str,
        decision: str = "proceed",
        task_id: str | None = None,
        feedback: str = "",
        input_data: dict | None = None,
        request_key: str,
        request_sha256: str,
    ) -> dict:
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")

        with self.database.transaction() as connection:
            receipt = connection.execute(
                "SELECT request_sha256, response_json FROM receipts "
                "WHERE operation='continue_run' AND resource_id=? AND request_key=?",
                (run_id, request_key),
            ).fetchone()
            if receipt:
                if receipt["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("idempotency_conflict")
                return json.loads(receipt["response_json"])

            run = connection.execute("SELECT * FROM process_runs WHERE id=?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(run_id)

            if run["status"] in ("succeeded", "failed", "cancelled"):
                raise ConflictError("run_terminal: Cannot continue a terminal run")

            # Look for waiting task
            if task_id:
                target_tr = connection.execute(
                    "SELECT * FROM task_runs WHERE run_id=? AND task_id=?",
                    (run_id, task_id),
                ).fetchone()
            else:
                target_tr = connection.execute(
                    "SELECT * FROM task_runs WHERE run_id=? AND (waiting_for IS NOT NULL OR attention_reason IS NOT NULL) ORDER BY id ASC",
                    (run_id,),
                ).fetchone()

            if target_tr is None:
                if not run["attention_reason"]:
                    raise ConflictError("run_not_waiting: Run is not waiting for input")
                target_tr = connection.execute(
                    "SELECT * FROM task_runs WHERE run_id=? AND status IN ('running', 'pending', 'queued') ORDER BY id ASC",
                    (run_id,),
                ).fetchone()

            decision_id = str(uuid4())
            connection.execute(
                "INSERT INTO human_decisions (id, run_id, task_run_id, decision, feedback, input_json, decision_key, decided_by, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (decision_id, run_id, target_tr["id"] if target_tr else None, decision, feedback,
                 encode_json(input_data) if input_data is not None else None, request_key, principal_id, at),
            )

            if decision in ("proceed", "approved", "continue"):
                if target_tr:
                    new_input = input_data if input_data is not None else (json.loads(target_tr["input_json"]) if target_tr["input_json"] else None)
                    if target_tr["waiting_for"] == "human_approval" or target_tr["status"] == "running":
                        connection.execute(
                            "UPDATE task_runs SET status='succeeded', waiting_for=NULL, attention_reason=NULL, output_json=? WHERE id=?",
                            (encode_json({"decision": decision, "feedback": feedback, "human_input": input_data}), target_tr["id"]),
                        )
                        # Queue eligible downstream tasks
                        pending_tasks = connection.execute(
                            "SELECT tr.id, tr.task_id, tr.process_version_id FROM task_runs tr "
                            "WHERE tr.run_id=? AND tr.status='pending'",
                            (run_id,),
                        ).fetchall()
                        for pt in pending_tasks:
                            deps = connection.execute(
                                "SELECT source_task_id FROM dependencies WHERE process_version_id=? AND target_task_id=?",
                                (pt["process_version_id"], pt["task_id"]),
                            ).fetchall()
                            if deps:
                                source_ids = [d["source_task_id"] for d in deps]
                                placeholders = ",".join("?" for _ in source_ids)
                                succ_count = connection.execute(
                                    f"SELECT COUNT(*) FROM task_runs WHERE run_id=? AND task_id IN ({placeholders}) AND status='succeeded'",
                                    [run_id] + source_ids,
                                ).fetchone()[0]
                                if succ_count == len(source_ids):
                                    connection.execute(
                                        "UPDATE task_runs SET status='queued', queued_at=? WHERE id=?",
                                        (at, pt["id"]),
                                    )
                    else:
                        connection.execute(
                            "UPDATE task_runs SET status='queued', waiting_for=NULL, attention_reason=NULL, input_json=?, queued_at=? WHERE id=?",
                            (encode_json(new_input) if new_input is not None else None, at, target_tr["id"]),
                        )

                connection.execute(
                    "UPDATE process_runs SET status='running', attention_reason=NULL, revision=revision+1 WHERE id=?",
                    (run_id,),
                )

                seq = connection.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM run_events WHERE run_id=?", (run_id,)).fetchone()[0]
                connection.execute(
                    "INSERT INTO run_events(id,run_id,sequence,event_type,task_run_id,data_json,recorded_at) "
                    "VALUES (?,?,?,'run_continued',?,?,?)",
                    (str(uuid4()), run_id, seq, target_tr["id"] if target_tr else None,
                     encode_json({"decision": decision, "feedback": feedback, "task_id": target_tr["task_id"] if target_tr else None}), at),
                )
                connection.execute(
                    "INSERT INTO audit_events(id,run_id,actor_id,event_type,resource_id,data_json,recorded_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (str(uuid4()), run_id, principal_id, "run_continued", run_id,
                     encode_json({"decision": decision, "task_id": target_tr["task_id"] if target_tr else None}), at),
                )

            res = self._get_with_connection(connection, run_id)
            connection.execute(
                "INSERT INTO receipts(principal_id,operation,resource_id,request_key,request_sha256,response_json,created_at) "
                "VALUES (?,'continue_run',?,?,?,?,?)",
                (principal_id, run_id, request_key, request_sha256, encode_json(res), at),
            )
            return res

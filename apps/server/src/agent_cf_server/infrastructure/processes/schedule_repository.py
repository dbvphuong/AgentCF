"""Schedule storage and execution management (PROC-004).

Rules enforced:
- Save không Start: Saving/creating schedule does not activate it (is_active = 0).
- Start không Run ngay: Activating schedule sets is_active = 1 and calculates next_run_at, does not immediately trigger run.
- Stop không Cancel: Deactivating schedule sets is_active = 0, does not cancel active runs.
- Cancel không Stop: Cancelling a run does not alter schedule status.
- Version được ghim: ProcessVersion ID remains pinned to the published version selected at creation time.
- Deduplication: Unique constraint on (schedule_id, scheduled_for) prevents duplicate execution ticks.
- PC Selection: Validates Runner online status if pinned PC is specified.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import json
from uuid import uuid4
from typing import Any

from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.runs.repository import ConflictError, IdempotencyConflict, RunRepository


def encode_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def compute_next_run(cadence: str, from_dt: datetime) -> datetime:
    if cadence == "hourly":
        return from_dt + timedelta(hours=1)
    elif cadence == "daily":
        return from_dt + timedelta(days=1)
    elif cadence == "weekly":
        return from_dt + timedelta(weeks=1)
    else:  # manual or cron default fallback
        return from_dt + timedelta(days=1)


class ScheduleRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_schedule(
        self,
        *,
        schedule_id: str | None = None,
        project_id: str,
        process_id: str,
        process_version_id: str | None = None,
        follow_current_configuration: bool = False,
        name: str,
        cadence: str = "daily",
        cron_expression: str | None = None,
        timezone_str: str = "Asia/Ho_Chi_Minh",
        default_runner_id: str | None = None,
        run_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not name or not name.strip():
            raise ValueError("Schedule name cannot be empty")
        if cadence not in ("manual", "hourly", "daily", "weekly", "cron"):
            raise ValueError(f"Invalid cadence: {cadence}")

        sid = schedule_id or f"sched-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")

        with self.database.transaction() as conn:
            # Validate project and process exist
            proc = conn.execute(
                "SELECT * FROM processes WHERE id=? AND project_id=?", (process_id, project_id)
            ).fetchone()
            if proc is None:
                raise ValueError("Process not found for project")

            if follow_current_configuration:
                from agent_cf_server.infrastructure.projects.management import ProjectManagement
                process_version_id = ProjectManagement(self.database).freeze_configuration(conn, process_id)
            # Legacy callers may explicitly pin an existing immutable snapshot.
            ver = conn.execute(
                "SELECT * FROM process_versions WHERE id=? AND process_id=?", (process_version_id, process_id)
            ).fetchone()
            if ver is None:
                raise ValueError(f"ProcessVersion {process_version_id} not found")
            if ver["status"] != "published":
                raise ValueError("Schedule must pin a published ProcessVersion, drafts are not permitted")

            # Validate runner if specified
            if default_runner_id:
                runner = conn.execute("SELECT * FROM runners WHERE id=?", (default_runner_id,)).fetchone()
                if runner is None:
                    raise ValueError(f"Runner {default_runner_id} not found")

            # Save không Start: is_active is 0
            conn.execute(
                "INSERT INTO schedules(id, project_id, process_id, process_version_id, name, cadence, cron_expression, "
                "timezone, is_active, default_runner_id, run_input_json, next_run_at, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, NULL, ?, ?)",
                (sid, project_id, process_id, process_version_id, name.strip(), cadence, cron_expression,
                 timezone_str, default_runner_id, encode_json(run_input or {}), at, at),
            )
            conn.execute("UPDATE schedules SET follow_current_configuration=? WHERE id=?", (int(follow_current_configuration), sid))

        return self.get_schedule(sid)

    def get_schedule(self, schedule_id: str) -> dict[str, Any]:
        with self.database.connect() as conn:
            row = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
            if row is None:
                raise KeyError(schedule_id)
            d = dict(row)
            d["is_active"] = bool(d["is_active"])
            d["run_input"] = json.loads(d["run_input_json"]) if d["run_input_json"] else {}
            return d

    def list_schedules(self, *, process_id: str | None = None, project_id: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
            query = "SELECT * FROM schedules WHERE 1=1"
            params = []
            if process_id:
                query += " AND process_id=?"
                params.append(process_id)
            if project_id:
                query += " AND project_id=?"
                params.append(project_id)
            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["is_active"] = bool(d["is_active"])
                d["run_input"] = json.loads(d["run_input_json"]) if d["run_input_json"] else {}
                results.append(d)
            return results

    def start_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Start schedule: sets is_active = 1 and calculates next_run_at (Start không Run ngay)."""
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")
        with self.database.transaction() as conn:
            sched = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
            if sched is None:
                raise KeyError(schedule_id)

            next_run_dt = compute_next_run(sched["cadence"], now)
            next_run_at = next_run_dt.isoformat().replace("+00:00", "Z")

            conn.execute(
                "UPDATE schedules SET is_active=1, next_run_at=?, updated_at=? WHERE id=?",
                (next_run_at, at, schedule_id),
            )
        return self.get_schedule(schedule_id)

    def stop_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Stop schedule: sets is_active = 0 (Stop không Cancel)."""
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")
        with self.database.transaction() as conn:
            sched = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
            if sched is None:
                raise KeyError(schedule_id)

            conn.execute(
                "UPDATE schedules SET is_active=0, next_run_at=NULL, updated_at=? WHERE id=?",
                (at, schedule_id),
            )
        return self.get_schedule(schedule_id)

    def trigger_schedule(
        self,
        *,
        schedule_id: str,
        scheduled_for: str,
        run_repo: RunRepository,
        principal_id: str = "scheduler",
    ) -> dict[str, Any]:
        """Trigger a schedule tick at scheduled_for (UTC timestamp). Enforces deduplication and PC checks."""
        now = datetime.now(timezone.utc)
        at = now.isoformat().replace("+00:00", "Z")

        with self.database.transaction() as conn:
            sched = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
            if sched is None:
                raise KeyError(schedule_id)

            # Deduplication key: (schedule_id, scheduled_for)
            existing_tick = conn.execute(
                "SELECT * FROM schedule_ticks WHERE schedule_id=? AND scheduled_for=?",
                (schedule_id, scheduled_for),
            ).fetchone()
            if existing_tick is not None:
                raise IdempotencyConflict("duplicate_schedule_tick: Schedule tick already exists for this time")

            # Runner Policy: check pinned runner status if specified
            if sched["default_runner_id"]:
                runner = conn.execute("SELECT * FROM runners WHERE id=?", (sched["default_runner_id"],)).fetchone()
                if runner is None or runner["status"] == "disabled":
                    raise ConflictError("runner_disabled_or_unavailable: Pinned runner is disabled or not found")
                active_session = conn.execute(
                    "SELECT * FROM runner_sessions WHERE runner_id=? AND status='active'",
                    (sched["default_runner_id"],),
                ).fetchone()
                if active_session is None:
                    raise ConflictError("runner_offline: Pinned runner has no active session and cannot dispatch")

            # Busy check: previous run is still active
            is_busy = False
            last_run_id = None
            if sched["last_run_id"]:
                last_run = conn.execute("SELECT status FROM process_runs WHERE id=?", (sched["last_run_id"],)).fetchone()
                if last_run and last_run["status"] in ("queued", "running", "reconciling"):
                    is_busy = True
                    last_run_id = sched["last_run_id"]

        if is_busy:
            with self.database.transaction() as conn:
                tick_id = f"tick-{uuid4().hex[:12]}"
                conn.execute(
                    "INSERT INTO schedule_ticks(id, schedule_id, scheduled_for, run_id, status, created_at) "
                    "VALUES (?, ?, ?, ?, 'skipped_busy', ?)",
                    (tick_id, schedule_id, scheduled_for, last_run_id, at),
                )
            raise ConflictError("schedule_busy: Previous run is still in progress, skipping overlapping execution")

        # Now create run using pinned process_version_id
        idem_key = f"schedule-{schedule_id}-{scheduled_for}"
        input_data = json.loads(sched["run_input_json"]) if sched["run_input_json"] else {}
        raw_body = json.dumps(input_data, sort_keys=True)
        request_sha256 = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        created_run = run_repo.create_from_version(
            version_id=None if sched["follow_current_configuration"] else sched["process_version_id"],
            process_id=sched["process_id"] if sched["follow_current_configuration"] else None,
            run_input=input_data,
            principal_id=principal_id,
            request_key=idem_key,
            request_sha256=request_sha256,
            default_runner_id=sched["default_runner_id"],
        )
        run_id = created_run["run_id"]

        with self.database.transaction() as conn:
            tick_id = f"tick-{uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO schedule_ticks(id, schedule_id, scheduled_for, run_id, status, created_at) "
                "VALUES (?, ?, ?, ?, 'triggered', ?)",
                (tick_id, schedule_id, scheduled_for, run_id, at),
            )
            next_run_dt = compute_next_run(sched["cadence"], now)
            next_run_at = next_run_dt.isoformat().replace("+00:00", "Z")
            conn.execute(
                "UPDATE schedules SET last_run_at=?, last_run_id=?, next_run_at=?, updated_at=? WHERE id=?",
                (at, run_id, next_run_at, at, schedule_id),
            )

        return {
            "tick_id": tick_id,
            "schedule_id": schedule_id,
            "scheduled_for": scheduled_for,
            "run_id": run_id,
            "status": "triggered",
        }

"""Overview aggregation and error acknowledgment repository (OVW-001).

Rules enforced:
- Real data only: Project progress, targets, and Agent tokens come strictly from DB.
- No fabricated numbers: Missing usage or targets are explicitly null / "—", never 0/0 or fake "On track".
- Error acknowledgment preserves terminal state: Acknowledging an error records an entry in
  run_error_acknowledgments without mutating process_runs.status (status remains 'failed').
- Agents ranked by token usage descending.
"""

from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4
from typing import Any

from agent_cf_server.infrastructure.persistence.database import Database


class OverviewRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_overview_summary(self) -> dict[str, Any]:
        local_now = datetime.now(timezone(timedelta(hours=7)))
        today = local_now.date().isoformat()
        month_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_bounds = tuple(value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") for value in (month_start, month_end))
        with self.database.connect() as conn:
            # 1. Unresolved Errors (failed runs not acknowledged)
            error_rows = conn.execute(
                "SELECT pr.id, pr.project_id, pr.process_id, pr.process_version_id, pr.error_json, "
                "pr.input_json, pr.ended_at, pr.created_at, p.name as process_name, j.name as project_name, "
                "(SELECT error_json FROM task_runs WHERE run_id=pr.id AND error_json IS NOT NULL LIMIT 1) as task_error_json "
                "FROM process_runs pr "
                "LEFT JOIN processes p ON p.id=pr.process_id "
                "LEFT JOIN projects j ON j.id=pr.project_id "
                "WHERE pr.status='failed' AND pr.id NOT IN (SELECT run_id FROM run_error_acknowledgments) "
                "ORDER BY pr.ended_at DESC, pr.created_at DESC LIMIT 50"
            ).fetchall()

            unresolved_errors = []
            for r in error_rows:
                task_err = json.loads(r["task_error_json"]) if r["task_error_json"] else None
                run_err = json.loads(r["error_json"]) if r["error_json"] else None
                err_data = task_err if task_err else run_err
                inp_data = json.loads(r["input_json"]) if r["input_json"] else {}
                topic = inp_data.get("topic") or inp_data.get("prompt") or None
                unresolved_errors.append({
                    "run_id": r["id"],
                    "project_id": r["project_id"],
                    "project_name": r["project_name"] or r["project_id"],
                    "process_id": r["process_id"],
                    "process_name": r["process_name"] or r["process_id"],
                    "process_version_id": r["process_version_id"],
                    "error": err_data,
                    "topic": topic,
                    "occurred_at": r["ended_at"] or r["created_at"],
                })

            # 2. Projects Progress
            project_rows = conn.execute("SELECT id, name FROM projects WHERE status='active' ORDER BY name ASC").fetchall()
            projects_progress = []
            for proj in project_rows:
                pid = proj["id"]
                # Targets
                targets = conn.execute(
                    "SELECT name, period, target_count, completed_count, status FROM project_targets WHERE project_id=? "
                    "AND (starts_on IS NULL OR starts_on<=?) AND (ends_on IS NULL OR ends_on>=?) "
                    "ORDER BY CASE period WHEN 'monthly' THEN 0 WHEN 'weekly' THEN 1 ELSE 2 END,created_at DESC",
                    (pid, today, today),
                ).fetchall()

                # Runs stats
                run_stats = conn.execute(
                    "SELECT "
                    "COUNT(*) as total, "
                    "SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) as succeeded, "
                    "SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed, "
                    "SUM(CASE WHEN status IN ('queued', 'running', 'reconciling') THEN 1 ELSE 0 END) as running "
                    "FROM process_runs WHERE project_id=?",
                    (pid,),
                ).fetchone()

                targets_list = [dict(t) for t in targets]
                projects_progress.append({
                    "project_id": pid,
                    "name": proj["name"],
                    "targets": targets_list if targets_list else None,
                    "has_targets": len(targets_list) > 0,
                    "total_runs": run_stats["total"] or 0,
                    "succeeded_runs": run_stats["succeeded"] or 0,
                    "failed_runs": run_stats["failed"] or 0,
                    "running_runs": run_stats["running"] or 0,
                })

            # 3. Agents Token Usage
            # Query all agents and join with token usage if available
            agent_rows = conn.execute(
                "SELECT a.id, a.name, a.role_id, a.model_id, "
                "COALESCE(u.total, NULL) as total_tokens, "
                "COALESCE(u.prompt, NULL) as prompt_tokens, "
                "COALESCE(u.completion, NULL) as completion_tokens "
                "FROM agents a "
                "LEFT JOIN ("
                "   SELECT agent_id, SUM(total_tokens) as total, SUM(prompt_tokens) as prompt, SUM(completion_tokens) as completion "
                "   FROM agent_token_usage WHERE recorded_at >= ? AND recorded_at < ? GROUP BY agent_id"
                ") u ON u.agent_id=a.id "
                "ORDER BY total_tokens DESC, a.name ASC",
                month_bounds,
            ).fetchall()

            agents_token_usage = []
            for ag in agent_rows:
                has_usage = ag["total_tokens"] is not None
                agents_token_usage.append({
                    "agent_id": ag["id"],
                    "name": ag["name"],
                    "role_id": ag["role_id"],
                    "model_id": ag["model_id"],
                    "has_usage": has_usage,
                    "total_tokens": ag["total_tokens"] if has_usage else None,
                    "prompt_tokens": ag["prompt_tokens"] if has_usage else None,
                    "completion_tokens": ag["completion_tokens"] if has_usage else None,
                })

            return {
                "unresolved_errors": unresolved_errors,
                "projects_progress": projects_progress,
                "agents_token_usage": agents_token_usage,
                "summary_stats": {
                    "unresolved_error_count": len(unresolved_errors),
                    "active_projects_count": len(projects_progress),
                    "active_agents_count": len(agents_token_usage),
                },
            }

    def acknowledge_error(self, run_id: str, acknowledged_by: str = "operator", notes: str = "") -> dict[str, Any]:
        """Acknowledge an error for a failed run. Does NOT alter run status."""
        at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self.database.transaction() as conn:
            run = conn.execute("SELECT id, status FROM process_runs WHERE id=?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(run_id)

            conn.execute(
                "INSERT INTO run_error_acknowledgments(run_id, acknowledged_by, notes, acknowledged_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET acknowledged_by=excluded.acknowledged_by, "
                "notes=excluded.notes, acknowledged_at=excluded.acknowledged_at",
                (run_id, acknowledged_by, notes, at),
            )

        return {
            "run_id": run_id,
            "status": "acknowledged",
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": at,
        }

    def record_agent_token_usage(
        self,
        *,
        agent_id: str,
        run_id: str,
        task_run_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        total = prompt_tokens + completion_tokens
        uid = f"tok-{uuid4().hex[:12]}"
        with self.database.transaction() as conn:
            conn.execute(
                "INSERT INTO agent_token_usage(id, agent_id, run_id, task_run_id, prompt_tokens, completion_tokens, total_tokens, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, agent_id, run_id, task_run_id, prompt_tokens, completion_tokens, total, at),
            )

    def set_project_target(
        self,
        *,
        project_id: str,
        name: str,
        period: str = "monthly",
        target_count: int = 10,
        completed_count: int = 0,
        status: str = "in_progress",
    ) -> dict[str, Any]:
        at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        tid = f"tgt-{uuid4().hex[:12]}"
        with self.database.transaction() as conn:
            conn.execute(
                "INSERT INTO project_targets(id, project_id, name, period, target_count, completed_count, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tid, project_id, name, period, target_count, completed_count, status, at, at),
            )
        return {
            "id": tid,
            "project_id": project_id,
            "name": name,
            "period": period,
            "target_count": target_count,
            "completed_count": completed_count,
            "status": status,
        }

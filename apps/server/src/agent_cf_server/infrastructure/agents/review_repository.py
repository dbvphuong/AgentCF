"""Persistence and evaluation logic for Agent Review decisions (AGN-001, AGN-002)."""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any
from uuid import uuid4

from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.settings.repository import ResourceNotFoundError


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


class ReviewRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def evaluate_content(
        self,
        content: str,
        criteria: dict[str, Any],
        revision_round: int = 1,
        max_revisions: int = 2,
    ) -> dict[str, Any]:
        """Evaluate actual output text against criteria, returning structured decision."""
        violations: list[str] = []
        words = len(content.split())

        # 1. Word count
        min_words = criteria.get("min_words")
        if min_words is not None and words < min_words:
            violations.append(f"word_count_insufficient: Found {words} words, required >= {min_words}")

        max_words = criteria.get("max_words")
        if max_words is not None and words > max_words:
            violations.append(f"word_count_excessive: Found {words} words, required <= {max_words}")

        # 2. POV Check (Require "Bạn")
        if criteria.get("require_pov_ban"):
            if "Bạn" not in content and "bạn" not in content:
                violations.append("missing_pov_ban: Content must use 2nd-person POV ('Bạn')")

        # 3. Line length for TTS
        max_line_len = criteria.get("max_line_length")
        if max_line_len is not None:
            lines = [l for l in content.splitlines() if l.strip()]
            too_long = [l for l in lines if len(l) > max_line_len]
            if too_long:
                violations.append(f"line_too_long: {len(too_long)} lines exceed max length {max_line_len}")

        # 4. Anti-clutter for TTS (no markdown dividers or raw headers)
        if criteria.get("anti_clutter"):
            clutter_markers = ["====", "----", "PART 1:", "PART 2:", "TIÊU ĐỀ:"]
            found = [m for m in clutter_markers if m in content]
            if found:
                violations.append(f"clutter_detected: Found raw headers/dividers prohibited for TTS: {', '.join(found)}")

        # 5. Required keywords or hooks
        required_keywords = criteria.get("required_keywords", [])
        if required_keywords:
            missing = [kw for kw in required_keywords if kw.lower() not in content.lower()]
            if missing:
                violations.append(f"missing_required_keywords: {', '.join(missing)}")

        # Decision calculation
        if not violations:
            decision = "approved"
            score = 9.5
            feedback = "Nội dung đạt đầy đủ tiêu chuẩn chất lượng và định dạng."
        else:
            if revision_round < max_revisions:
                decision = "revision_requested"
                score = max(1.0, 8.0 - len(violations) * 1.5)
                feedback = f"Yêu cầu chỉnh sửa vòng {revision_round}: " + "; ".join(violations)
            else:
                decision = "escalated"
                score = max(1.0, 5.0 - len(violations) * 1.5)
                feedback = f"Vượt quá số lần sửa tối đa ({max_revisions}). Báo người vận hành can thiệp: " + "; ".join(violations)

        return {
            "decision": decision,
            "score": round(score, 1),
            "feedback": feedback,
            "violations": violations,
            "revision_round": revision_round,
            "max_revisions": max_revisions,
            "word_count": words,
        }

    def record_decision(
        self,
        task_run_id: str,
        attempt_id: str,
        reviewer_agent_id: str,
        revision_round: int,
        decision: str,
        score: float | None = None,
        feedback: str = "",
        violations: list[str] | None = None,
        decision_key: str | None = None,
    ) -> dict[str, Any]:
        """Record review decision with deduplication/idempotency support."""
        d_key = decision_key or f"dec-{task_run_id}-round-{revision_round}"
        violations = violations or []
        v_json = json.dumps(violations)
        now = _now_iso()

        with self.database.transaction() as conn:
            # Check existing decision with same decision_key (idempotency deduplication)
            existing = conn.execute(
                "SELECT * FROM review_decisions WHERE decision_key = ?",
                (d_key,),
            ).fetchone()
            if existing:
                res = dict(existing)
                res["violations"] = json.loads(res.pop("violations_json"))
                return res

            # Verify task_run and attempt exist
            tr = conn.execute("SELECT id FROM task_runs WHERE id = ?", (task_run_id,)).fetchone()
            if not tr:
                raise ResourceNotFoundError(f"Task run not found: {task_run_id}")

            att = conn.execute("SELECT id FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
            if not att:
                raise ResourceNotFoundError(f"Attempt not found: {attempt_id}")

            decision_id = str(uuid4())
            conn.execute(
                "INSERT INTO review_decisions (id, task_run_id, attempt_id, reviewer_agent_id, revision_round, "
                "decision, score, feedback, violations_json, decision_key, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    decision_id,
                    task_run_id,
                    attempt_id,
                    reviewer_agent_id,
                    revision_round,
                    decision,
                    score,
                    feedback,
                    v_json,
                    d_key,
                    now,
                ),
            )

        return self.get_decision(decision_id)

    def get_decision(self, decision_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM review_decisions WHERE id = ?", (decision_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Review decision not found: {decision_id}")
            res = dict(row)
            res["violations"] = json.loads(res.pop("violations_json"))
            return res

    def list_decisions_for_task_run(self, task_run_id: str) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            rows = conn.execute(
                "SELECT * FROM review_decisions WHERE task_run_id = ? ORDER BY revision_round ASC, created_at ASC",
                (task_run_id,),
            ).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["violations"] = json.loads(item.pop("violations_json"))
                results.append(item)
            return results

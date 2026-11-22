"""Persistence and lifecycle for Agents and Agent Snapshots (AGN-003)."""

from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from typing import Any

from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.settings.repository import (
    InUseError,
    ResourceConflictError,
    ResourceNotFoundError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


class AgentRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def _validate_agent_tool_permissions(
        self, conn: sqlite3.Connection, skill_ids: list[str], allowed_tool_ids: set[str]
    ) -> None:
        """Enforce domain rule: Agent cannot be assigned a Skill requiring Tools not in Allowed Tools."""
        for skill_id in skill_ids:
            # Check latest published (or latest draft) version's tools
            tools = conn.execute(
                "SELECT t.id, t.name FROM tools t "
                "JOIN skill_version_tools svt ON t.id = svt.tool_id "
                "JOIN skill_versions sv ON svt.skill_version_id = sv.id "
                "WHERE sv.skill_id = ? ORDER BY sv.version_number DESC",
                (skill_id,),
            ).fetchall()
            for tool in tools:
                if tool["id"] not in allowed_tool_ids:
                    raise ResourceConflictError(
                        f"Skill '{skill_id}' requires tool '{tool['name']}' ({tool['id']}) which is not in Agent's allowed tools"
                    )

    def create_agent(
        self,
        agent_id: str,
        name: str,
        role_id: str,
        model_id: str,
        instructions: str = "",
        skill_ids: list[str] | None = None,
        allowed_tool_ids: list[str] | None = None,
        status: str = "active",
        template_id: str | None = None,
        allow_reply: bool = True,
        allow_retry: bool = True,
        allow_need_human: bool = True,
        max_turns: int = 10,
    ) -> dict[str, Any]:
        skill_ids = skill_ids or []
        allowed_tool_ids = allowed_tool_ids or []
        allowed_tools_set = set(allowed_tool_ids)

        with self.database.transaction() as conn:
            # Validate role exists
            role = conn.execute("SELECT id, status FROM roles WHERE id = ?", (role_id,)).fetchone()
            if not role:
                raise ResourceNotFoundError(f"Role not found: {role_id}")
            if role["status"] != "active":
                raise ResourceConflictError(f"Cannot assign inactive/archived role: {role_id}")

            # Validate model exists
            model = conn.execute("SELECT id, status FROM models WHERE id = ?", (model_id,)).fetchone()
            if not model:
                raise ResourceNotFoundError(f"Model not found: {model_id}")
            if model["status"] != "active":
                raise ResourceConflictError(f"Cannot assign disabled model: {model_id}")

            # Validate skills exist
            for sid in skill_ids:
                s = conn.execute("SELECT id, status FROM skills WHERE id = ?", (sid,)).fetchone()
                if not s:
                    raise ResourceNotFoundError(f"Skill not found: {sid}")
                if s["status"] != "active":
                    raise ResourceConflictError(f"Cannot assign inactive/archived skill: {sid}")

            # Validate tools exist
            for tid in allowed_tool_ids:
                t = conn.execute("SELECT id, status FROM tools WHERE id = ?", (tid,)).fetchone()
                if not t:
                    raise ResourceNotFoundError(f"Tool not found: {tid}")

            # Enforce skill tools <= allowed tools
            self._validate_agent_tool_permissions(conn, skill_ids, allowed_tools_set)

            try:
                conn.execute(
                    "INSERT INTO agents (id, name, role_id, model_id, instructions, status, template_id, allow_reply, allow_retry, allow_need_human, max_turns, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        agent_id,
                        name,
                        role_id,
                        model_id,
                        instructions,
                        status,
                        template_id,
                        int(bool(allow_reply)),
                        int(bool(allow_retry)),
                        int(bool(allow_need_human)),
                        int(max_turns),
                        _now_iso(),
                        _now_iso(),
                    ),
                )
                for sid in skill_ids:
                    conn.execute("INSERT INTO agent_skills (agent_id, skill_id) VALUES (?, ?)", (agent_id, sid))
                for tid in allowed_tool_ids:
                    conn.execute("INSERT INTO agent_allowed_tools (agent_id, tool_id) VALUES (?, ?)", (agent_id, tid))
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Agent conflict: {exc}") from exc

        return self.get_agent(agent_id)

    def _derived_skills(self, conn: sqlite3.Connection, agent_id: str) -> list[sqlite3.Row]:
        query = """
            SELECT DISTINCT s.* FROM skills s
            WHERE s.id IN (
                SELECT json_extract(node.value, '$.skill_id')
                FROM processes p
                JOIN process_versions v ON v.process_id = p.id
                JOIN json_each(v.definition_json, '$.tasks') node
                WHERE v.version_number = (
                    SELECT MAX(latest.version_number)
                    FROM process_versions latest
                    WHERE latest.process_id = p.id
                )
                AND json_extract(node.value, '$.agent_id') = ?
                AND json_extract(node.value, '$.kind') = 'agent'
                AND json_extract(node.value, '$.skill_id') IS NOT NULL
                UNION
                SELECT skill_id FROM agent_skills WHERE agent_id = ?
            )
            ORDER BY s.name ASC
        """
        return conn.execute(query, (agent_id, agent_id)).fetchall()

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute(
                "SELECT a.*, r.name AS role_name, m.name AS model_name, m.model_identifier "
                "FROM agents a "
                "JOIN roles r ON a.role_id = r.id "
                "JOIN models m ON a.model_id = m.id "
                "WHERE a.id = ?",
                (agent_id,),
            ).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Agent not found: {agent_id}")
            result = dict(row)

            # Get skills (derived from process node assignments and legacy catalog)
            skills = self._derived_skills(conn, agent_id)
            result["skills"] = [dict(s) for s in skills]
            result["skill_ids"] = [s["id"] for s in skills]

            # Get allowed tools
            tools = conn.execute(
                "SELECT t.* FROM tools t JOIN agent_allowed_tools aat ON t.id = aat.tool_id WHERE aat.agent_id = ? ORDER BY t.name ASC",
                (agent_id,),
            ).fetchall()
            result["allowed_tools"] = [dict(t) for t in tools]
            result["allowed_tool_ids"] = [t["id"] for t in tools]
            for flag in ("allow_reply", "allow_retry", "allow_need_human"):
                if flag in result:
                    result[flag] = bool(result[flag])
            return result

    def list_agents(self, status: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            query = (
                "SELECT a.*, r.name AS role_name, m.name AS model_name, m.model_identifier "
                "FROM agents a "
                "JOIN roles r ON a.role_id = r.id "
                "JOIN models m ON a.model_id = m.id"
            )
            params: list[Any] = []
            if status is not None:
                query += " WHERE a.status = ?"
                params.append(status)
            query += " ORDER BY a.name ASC"
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                skills = self._derived_skills(conn, item["id"])
                item["skills"] = [dict(s) for s in skills]
                item["skill_ids"] = [s["id"] for s in skills]
                item["allowed_tool_ids"] = [
                    r["tool_id"] for r in conn.execute("SELECT tool_id FROM agent_allowed_tools WHERE agent_id = ?", (item["id"],)).fetchall()
                ]
                for flag in ("allow_reply", "allow_retry", "allow_need_human"):
                    if flag in item:
                        item[flag] = bool(item[flag])
                results.append(item)
            return results

    def update_agent(
        self,
        agent_id: str,
        name: str | None = None,
        role_id: str | None = None,
        model_id: str | None = None,
        instructions: str | None = None,
        skill_ids: list[str] | None = None,
        allowed_tool_ids: list[str] | None = None,
        status: str | None = None,
        template_id: str | None = None,
        allow_reply: bool | None = None,
        allow_retry: bool | None = None,
        allow_need_human: bool | None = None,
        max_turns: int | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Agent not found: {agent_id}")

            current_skill_ids = [r["skill_id"] for r in conn.execute("SELECT skill_id FROM agent_skills WHERE agent_id = ?", (agent_id,)).fetchall()]
            current_tool_ids = [r["tool_id"] for r in conn.execute("SELECT tool_id FROM agent_allowed_tools WHERE agent_id = ?", (agent_id,)).fetchall()]

            effective_skills = skill_ids if skill_ids is not None else current_skill_ids
            effective_tools = allowed_tool_ids if allowed_tool_ids is not None else current_tool_ids

            if role_id is not None:
                role = conn.execute("SELECT id, status FROM roles WHERE id = ?", (role_id,)).fetchone()
                if not role:
                    raise ResourceNotFoundError(f"Role not found: {role_id}")
                if role["status"] != "active":
                    raise ResourceConflictError(f"Cannot assign inactive role: {role_id}")

            if model_id is not None:
                model = conn.execute("SELECT id, status FROM models WHERE id = ?", (model_id,)).fetchone()
                if not model:
                    raise ResourceNotFoundError(f"Model not found: {model_id}")
                if model["status"] != "active":
                    raise ResourceConflictError(f"Cannot assign disabled model: {model_id}")

            # Enforce tool permission
            self._validate_agent_tool_permissions(conn, effective_skills, set(effective_tools))

            updates: list[str] = []
            params: list[Any] = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if role_id is not None:
                updates.append("role_id = ?")
                params.append(role_id)
            if model_id is not None:
                updates.append("model_id = ?")
                params.append(model_id)
            if instructions is not None:
                updates.append("instructions = ?")
                params.append(instructions)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if template_id is not None:
                updates.append("template_id = ?")
                params.append(template_id or None)
            if allow_reply is not None:
                updates.append("allow_reply = ?")
                params.append(int(bool(allow_reply)))
            if allow_retry is not None:
                updates.append("allow_retry = ?")
                params.append(int(bool(allow_retry)))
            if allow_need_human is not None:
                updates.append("allow_need_human = ?")
                params.append(int(bool(allow_need_human)))
            if max_turns is not None:
                updates.append("max_turns = ?")
                params.append(int(max_turns))

            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(agent_id)

            try:
                conn.execute(f"UPDATE agents SET {', '.join(updates)} WHERE id = ?", params)
                if skill_ids is not None:
                    conn.execute("DELETE FROM agent_skills WHERE agent_id = ?", (agent_id,))
                    for sid in skill_ids:
                        conn.execute("INSERT INTO agent_skills (agent_id, skill_id) VALUES (?, ?)", (agent_id, sid))
                if allowed_tool_ids is not None:
                    conn.execute("DELETE FROM agent_allowed_tools WHERE agent_id = ?", (agent_id,))
                    for tid in allowed_tool_ids:
                        conn.execute("INSERT INTO agent_allowed_tools (agent_id, tool_id) VALUES (?, ?)", (agent_id, tid))
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Agent update conflict: {exc}") from exc

        return self.get_agent(agent_id)

    def archive_agent(self, agent_id: str) -> dict[str, Any]:
        return self.update_agent(agent_id, status="archived")

    def restore_agent(self, agent_id: str) -> dict[str, Any]:
        return self.update_agent(agent_id, status="active")

    def delete_agent(self, agent_id: str) -> None:
        from agent_cf_server.infrastructure.projects.references import process_using
        with self.database.transaction() as conn:
            agent = conn.execute("SELECT name FROM agents WHERE id=?", (agent_id,)).fetchone()
            if not agent:
                raise ResourceNotFoundError(f"Agent not found: {agent_id}")
            used = process_using(conn, "agent", agent_id)
            if used:
                raise InUseError(
                    f'Agent “{agent["name"]}” đang được sử dụng trong Process “{used["name"]}” '
                    f'thuộc Project “{used["project_name"]}”, bước “{used["task_name"]}” ({used["source"]}). '
                    "Gỡ tham chiếu Agent thực hiện/duyệt khỏi Process; nếu thuộc snapshot của Run chưa kết thúc, dừng Run và chờ kết thúc trước khi xóa."
                )
            try:
                conn.execute("UPDATE projects SET pm_agent_id=NULL WHERE pm_agent_id=?", (agent_id,))
                conn.execute("DELETE FROM project_team WHERE agent_id=?", (agent_id,))
                conn.execute("DELETE FROM agent_snapshots WHERE agent_id=?", (agent_id,))
                conn.execute("DELETE FROM agent_skills WHERE agent_id = ?", (agent_id,))
                conn.execute("DELETE FROM agent_allowed_tools WHERE agent_id = ?", (agent_id,))
                cursor = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
                if cursor.rowcount == 0:
                    raise ResourceNotFoundError(f"Agent not found: {agent_id}")
            except sqlite3.IntegrityError as exc:
                raise InUseError(f'Không thể xóa Agent “{agent["name"]}” vì còn dữ liệu liên kết được bảo vệ. Tải lại Agent và kiểm tra các Process liên quan trước khi thử lại.') from exc

    def create_agent_snapshot(self, agent_id: str) -> dict[str, Any]:
        """Capture immutable execution snapshot of the agent's current configuration."""
        agent = self.get_agent(agent_id)
        snapshot_data = {
            "agent_id": agent["id"],
            "name": agent["name"],
            "role": {"id": agent["role_id"], "name": agent["role_name"]},
            "model": {"id": agent["model_id"], "name": agent["model_name"], "model_identifier": agent["model_identifier"]},
            "instructions": agent["instructions"],
            "template_id": agent.get("template_id"),
            "allow_reply": agent.get("allow_reply", True),
            "allow_retry": agent.get("allow_retry", True),
            "allow_need_human": agent.get("allow_need_human", True),
            "max_turns": agent.get("max_turns", 10),
            "skills": [
                {"id": s["id"], "name": s["name"]} for s in agent.get("skills", [])
            ],
            "allowed_tools": [
                {"id": t["id"], "name": t["name"], "tool_type": t["tool_type"]} for t in agent.get("allowed_tools", [])
            ],
        }
        canonical_json = json.dumps(snapshot_data, sort_keys=True)
        sha = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        snapshot_id = f"snap-{agent_id}-{sha[:16]}"

        with self.database.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO agent_snapshots (id, agent_id, snapshot_sha256, snapshot_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (snapshot_id, agent_id, sha, canonical_json, _now_iso()),
            )
        return {
            "snapshot_id": snapshot_id,
            "agent_id": agent_id,
            "snapshot_sha256": sha,
            "snapshot": snapshot_data,
        }

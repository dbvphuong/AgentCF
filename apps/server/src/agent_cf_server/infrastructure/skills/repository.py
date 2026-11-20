"""Persistence and lifecycle for Skills, Skill Versions, and Tools (SKL-001, SKL-002)."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any
from uuid import uuid4

from agent_cf_server.domain.skills.local_source import validate_skill_source
from agent_cf_server.domain.skills.project_scope import validate_scope

from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.deletion_feedback import reference_list
from agent_cf_server.infrastructure.settings.repository import (
    InUseError,
    ResourceConflictError,
    ResourceNotFoundError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


def compute_skill_bundle_hash(instructions: str, output_standards: str, tool_ids: list[str], source_path=None, source_runner_id=None) -> str:
    """Compute canonical sha256 of skill definition content and bound tool IDs."""
    hasher = hashlib.sha256()
    payload = {
        "instructions": instructions.strip(),
        "output_standards": output_standards.strip(),
        "tools": sorted(tool_ids),
    }
    if source_path:
        payload.update(source_path=source_path, source_runner_id=source_runner_id)
    hasher.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return hasher.hexdigest()


def compute_directory_bundle_hash(directory: Path) -> str:
    """Compute sha256 hash of all files in a skill directory."""
    hasher = hashlib.sha256()
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            rel_path = file_path.relative_to(directory).as_posix()
            hasher.update(rel_path.encode("utf-8"))
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()


class SkillRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _scope(conn, skill):
        result = dict(skill)
        source = conn.execute(
            "SELECT v.source_path,v.source_runner_id,v.status,v.version_number,"
            "(SELECT MAX(p.version_number) FROM skill_versions p WHERE p.skill_id=v.skill_id AND p.status='published') published_version_number "
            "FROM skill_versions v WHERE v.skill_id=? ORDER BY v.version_number DESC LIMIT 1",
            (result["id"],),
        ).fetchone()
        result.update(source_path=source["source_path"] if source else None,
                      source_runner_id=source["source_runner_id"] if source else None)
        result.update(
            published_version_number=source["published_version_number"] if source else None,
            latest_version_number=source["version_number"] if source else None,
            latest_version_status=source["status"] if source else None,
        )
        result["is_global"] = bool(result["is_global"])
        result["projects"] = [dict(row) for row in conn.execute(
            "SELECT p.id,p.name FROM projects p JOIN skill_projects sp ON sp.project_id=p.id WHERE sp.skill_id=? ORDER BY p.name,p.id",
            (result["id"],),
        )]
        result["project_ids"] = [p["id"] for p in result["projects"]]
        return result

    @staticmethod
    def _set_scope(conn, skill_id, is_global, project_ids):
        project_ids = sorted(set(project_ids))
        validate_scope(is_global, project_ids)
        for pid in project_ids:
            if not conn.execute("SELECT 1 FROM projects WHERE id=?", (pid,)).fetchone():
                raise ValueError("Project được chọn không tồn tại")
        conn.execute("DELETE FROM skill_projects WHERE skill_id=?", (skill_id,))
        conn.execute("UPDATE skills SET is_global=? WHERE id=?", (int(is_global), skill_id))
        conn.executemany("INSERT INTO skill_projects VALUES (?,?)", [(skill_id, pid) for pid in project_ids])
        conn.execute(
            "INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator','skill_scope_changed',?,?,?)",
            (str(uuid4()), skill_id, json.dumps({"is_global": is_global, "project_ids": project_ids}), _now_iso()),
        )

    # -------------------------------------------------------------------------
    # Tools
    # -------------------------------------------------------------------------

    def create_tool(
        self,
        tool_id: str,
        name: str,
        description: str = "",
        tool_type: str = "internal",
        configuration: dict[str, Any] | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        config_json = json.dumps(configuration or {})
        with self.database.transaction() as conn:
            try:
                conn.execute(
                    "INSERT INTO tools (id, name, description, tool_type, configuration_json, status, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (tool_id, name, description, tool_type, config_json, status, _now_iso(), _now_iso()),
                )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Tool conflict: {exc}") from exc
        return self.get_tool(tool_id)

    def get_tool(self, tool_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Tool not found: {tool_id}")
            result = dict(row)
            try:
                result["configuration"] = json.loads(result.pop("configuration_json"))
            except Exception:
                result["configuration"] = {}
            return result

    def list_tools(self, status: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            query = "SELECT * FROM tools"
            params: list[Any] = []
            if status is not None:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY name ASC"
            results = []
            for row in conn.execute(query, params).fetchall():
                item = dict(row)
                try:
                    item["configuration"] = json.loads(item.pop("configuration_json"))
                except Exception:
                    item["configuration"] = {}
                results.append(item)
            return results

    def update_tool(
        self,
        tool_id: str,
        name: str | None = None,
        description: str | None = None,
        tool_type: str | None = None,
        configuration: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Tool not found: {tool_id}")
            updates: list[str] = []
            params: list[Any] = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if tool_type is not None:
                updates.append("tool_type = ?")
                params.append(tool_type)
            if configuration is not None:
                updates.append("configuration_json = ?")
                params.append(json.dumps(configuration))
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if not updates:
                return self.get_tool(tool_id)
            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(tool_id)
            try:
                conn.execute(f"UPDATE tools SET {', '.join(updates)} WHERE id = ?", params)
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Tool update conflict: {exc}") from exc
        return self.get_tool(tool_id)

    def archive_tool(self, tool_id: str) -> dict[str, Any]:
        return self.update_tool(tool_id, status="archived")

    def restore_tool(self, tool_id: str) -> dict[str, Any]:
        return self.update_tool(tool_id, status="active")

    def delete_tool(self, tool_id: str) -> None:
        with self.database.transaction() as conn:
            try:
                cursor = conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
                if cursor.rowcount == 0:
                    raise ResourceNotFoundError(f"Tool not found: {tool_id}")
            except sqlite3.IntegrityError as exc:
                tool = conn.execute("SELECT name FROM tools WHERE id=?", (tool_id,)).fetchone()
                skills = conn.execute(
                    "SELECT s.name,v.version_number FROM skill_version_tools st "
                    "JOIN skill_versions v ON v.id=st.skill_version_id JOIN skills s ON s.id=v.skill_id "
                    "WHERE st.tool_id=? ORDER BY s.name,v.version_number", (tool_id,),
                ).fetchall()
                agents = conn.execute(
                    "SELECT a.name FROM agent_allowed_tools at JOIN agents a ON a.id=at.agent_id "
                    "WHERE at.tool_id=? ORDER BY a.name", (tool_id,),
                ).fetchall()
                names = reference_list(
                    [f'Skill “{r["name"]}” v{r["version_number"]}' for r in skills]
                    + [f'Agent “{r["name"]}”' for r in agents]
                )
                raise InUseError(
                    f'Không thể xóa Tool “{tool["name"]}” vì còn liên kết: {names}. '
                    "Gỡ Tool khỏi Allowed tools của Agent và các phiên bản Skill liên quan trước khi xóa. "
                    "Phiên bản Skill đã phát hành được giữ bất biến; sửa phiên bản mới không gỡ liên kết trong phiên bản cũ."
                ) from exc

    # -------------------------------------------------------------------------
    # Skills
    # -------------------------------------------------------------------------

    def create_skill(
        self,
        skill_id: str,
        name: str,
        description: str = "",
        status: str = "active",
        is_global: bool = True,
        project_ids: list[str] | None = None,
        source_path: str | None = None,
        source_runner_id: str | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            try:
                conn.execute(
                    "INSERT INTO skills (id, name, description, status, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (skill_id, name, description, status, _now_iso(), _now_iso()),
                )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Skill conflict: {exc}") from exc
            self._set_scope(conn, skill_id, is_global, project_ids or [])
            if source_path or source_runner_id:
                self._save_source(conn, skill_id, source_path, source_runner_id)
        return self.get_skill(skill_id)

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Skill not found: {skill_id}")
            return self._scope(conn, row)

    def list_skills(self, status: str | None = None, project_id: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            query = "SELECT * FROM skills"
            params: list[Any] = []
            if status is not None:
                query += " WHERE status = ?"
                params.append(status)
            if project_id is not None:
                query += (" AND " if status is not None else " WHERE ") + "(is_global=1 OR EXISTS(SELECT 1 FROM skill_projects sp WHERE sp.skill_id=skills.id AND sp.project_id=?))"
                params.append(project_id)
            query += " ORDER BY name ASC"
            return [self._scope(conn, r) for r in conn.execute(query, params).fetchall()]

    def update_skill(
        self,
        skill_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        is_global: bool | None = None,
        project_ids: list[str] | None = None,
        source_path: str | None = None,
        source_runner_id: str | None = None,
        update_source: bool = False,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Skill not found: {skill_id}")
            if update_source:
                self._save_source(conn, skill_id, source_path, source_runner_id)
            if is_global is not None or project_ids is not None:
                current_ids = [r[0] for r in conn.execute("SELECT project_id FROM skill_projects WHERE skill_id=?", (skill_id,))]
                self._set_scope(conn, skill_id, bool(existing["is_global"]) if is_global is None else is_global,
                                current_ids if project_ids is None else project_ids)
            updates: list[str] = []
            params: list[Any] = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if not updates and is_global is None and project_ids is None and not update_source:
                return self.get_skill(skill_id)
            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(skill_id)
            try:
                conn.execute(f"UPDATE skills SET {', '.join(updates)} WHERE id = ?", params)
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Skill update conflict: {exc}") from exc
        return self.get_skill(skill_id)

    @staticmethod
    def _save_source(conn, skill_id, source_path, source_runner_id):
        previous = conn.execute("SELECT * FROM skill_versions WHERE skill_id=? ORDER BY version_number DESC LIMIT 1", (skill_id,)).fetchone()
        if previous and (previous["source_path"], previous["source_runner_id"]) == (source_path, source_runner_id):
            return
        if not previous and not source_path and not source_runner_id:
            return
        instructions = previous["instructions"] if previous else ""
        validate_skill_source(instructions, source_path, source_runner_id)
        if source_runner_id:
            runner = conn.execute("SELECT status,deleted_at FROM runners WHERE id=?", (source_runner_id,)).fetchone()
            if not runner or runner["deleted_at"] or runner["status"] == "disabled":
                raise ValueError("PC sở hữu file Skill không khả dụng")
        if previous and previous["status"] == "draft":
            conn.execute("UPDATE skill_versions SET source_path=?,source_runner_id=? WHERE id=?", (source_path, source_runner_id, previous["id"]))
            return
        version_id = str(uuid4())
        conn.execute("INSERT INTO skill_versions(id,skill_id,version_number,status,instructions,output_standards,created_at,source_path,source_runner_id) VALUES (?,?,?,'draft',?,?,?,?,?)",
                     (version_id, skill_id, previous["version_number"] + 1 if previous else 1, instructions,
                      previous["output_standards"] if previous else "", _now_iso(), source_path, source_runner_id))
        if previous:
            conn.execute("INSERT INTO skill_version_tools(skill_version_id,tool_id) SELECT ?,tool_id FROM skill_version_tools WHERE skill_version_id=?", (version_id, previous["id"]))

    def archive_skill(self, skill_id: str) -> dict[str, Any]:
        return self.update_skill(skill_id, status="archived")

    def restore_skill(self, skill_id: str) -> dict[str, Any]:
        return self.update_skill(skill_id, status="active")

    def delete_skill(self, skill_id: str) -> None:
        from agent_cf_server.infrastructure.projects.references import process_using
        from agent_cf_server.infrastructure.persistence.deletion import delete_rows
        with self.database.transaction() as conn:
            skill = conn.execute("SELECT name FROM skills WHERE id=?", (skill_id,)).fetchone()
            if not skill:
                raise ResourceNotFoundError(f"Skill not found: {skill_id}")
            used = process_using(conn, "skill", skill_id)
            if used:
                raise InUseError(
                    f'Skill “{skill["name"]}” đang được sử dụng trong Process “{used["name"]}” '
                    f'thuộc Project “{used["project_name"]}”, bước “{used["task_name"]}” ({used["source"]}). '
                    "Gỡ tham chiếu khỏi Process; nếu thuộc snapshot của Run chưa kết thúc, dừng Run và chờ kết thúc trước khi xóa."
                )
            try:
                conn.execute("DELETE FROM agent_skills WHERE skill_id=?", (skill_id,))
                delete_rows(conn, "skill_version_tools", "skill_version_id IN (SELECT id FROM skill_versions WHERE skill_id=?)", (skill_id,))
                delete_rows(conn, "skill_versions", "skill_id=?", (skill_id,))
                cursor = conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
                if cursor.rowcount == 0:
                    raise ResourceNotFoundError(f"Skill not found: {skill_id}")
            except sqlite3.IntegrityError as exc:
                raise InUseError(f'Không thể xóa Skill “{skill["name"]}” vì còn dữ liệu liên kết được bảo vệ. Tải lại Skill và kiểm tra các Process liên quan trước khi thử lại.') from exc

    # -------------------------------------------------------------------------
    # Skill Versions
    # -------------------------------------------------------------------------

    def create_draft_version(
        self,
        version_id: str,
        skill_id: str,
        instructions: str,
        output_standards: str = "",
        tool_ids: list[str] | None = None,
        source_path: str | None = None,
        source_runner_id: str | None = None,
    ) -> dict[str, Any]:
        validate_skill_source(instructions, source_path, source_runner_id)
        tool_ids = tool_ids or []
        with self.database.transaction() as conn:
            # Check skill exists
            skill = conn.execute("SELECT id FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if not skill:
                raise ResourceNotFoundError(f"Skill not found: {skill_id}")

            # Check tools exist
            for tid in tool_ids:
                tool = conn.execute("SELECT id FROM tools WHERE id = ?", (tid,)).fetchone()
                if not tool:
                    raise ResourceNotFoundError(f"Tool not found: {tid}")

            # Next version number
            last = conn.execute(
                "SELECT MAX(version_number) FROM skill_versions WHERE skill_id = ?", (skill_id,)
            ).fetchone()[0]
            next_version = (last or 0) + 1

            try:
                conn.execute(
                    "INSERT INTO skill_versions (id, skill_id, version_number, status, instructions, output_standards, created_at, source_path, source_runner_id) "
                    "VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?)",
                    (version_id, skill_id, next_version, instructions, output_standards, _now_iso(), source_path, source_runner_id),
                )
                for tid in tool_ids:
                    conn.execute(
                        "INSERT INTO skill_version_tools (skill_version_id, tool_id) VALUES (?, ?)",
                        (version_id, tid),
                    )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Draft version conflict: {exc}") from exc
        return self.get_version(version_id)

    def get_version(self, version_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM skill_versions WHERE id = ?", (version_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Skill version not found: {version_id}")
            result = dict(row)
            tools = conn.execute(
                "SELECT t.* FROM tools t JOIN skill_version_tools svt ON t.id = svt.tool_id WHERE svt.skill_version_id = ?",
                (version_id,),
            ).fetchall()
            result["tools"] = [dict(t) for t in tools]
            result["tool_ids"] = [t["id"] for t in tools]
            return result

    def update_draft_version(self, version_id: str, instructions: str, output_standards: str, tool_ids: list[str], source_path=None, source_runner_id=None) -> dict[str, Any]:
        validate_skill_source(instructions, source_path, source_runner_id)
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT status FROM skill_versions WHERE id=?", (version_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError("Skill version not found")
            if existing["status"] != "draft":
                raise ResourceConflictError("Published Skill versions are immutable")
            for tid in set(tool_ids):
                tool = conn.execute("SELECT status FROM tools WHERE id=?", (tid,)).fetchone()
                if not tool or tool["status"] != "active":
                    raise ResourceConflictError("Tool must exist and be active")
            conn.execute("UPDATE skill_versions SET instructions=?,output_standards=?,source_path=?,source_runner_id=? WHERE id=?", (instructions, output_standards, source_path, source_runner_id, version_id))
            conn.execute("DELETE FROM skill_version_tools WHERE skill_version_id=?", (version_id,))
            conn.executemany("INSERT INTO skill_version_tools VALUES (?,?)", [(version_id, tid) for tid in set(tool_ids)])
        return self.get_version(version_id)

    def list_versions(self, skill_id: str) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            rows = conn.execute(
                "SELECT * FROM skill_versions WHERE skill_id = ? ORDER BY version_number DESC",
                (skill_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def publish_version(self, version_id: str, bundle_sha256: str | None = None) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM skill_versions WHERE id = ?", (version_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Skill version not found: {version_id}")
            if existing["status"] == "published":
                return self.get_version(version_id)

            tool_rows = conn.execute(
                "SELECT tool_id FROM skill_version_tools WHERE skill_version_id = ? ORDER BY tool_id ASC",
                (version_id,),
            ).fetchall()
            tool_ids = [r["tool_id"] for r in tool_rows]

            if not bundle_sha256:
                bundle_sha256 = compute_skill_bundle_hash(
                    existing["instructions"], existing["output_standards"], tool_ids,
                    existing["source_path"], existing["source_runner_id"],
                )

            published_at = _now_iso()
            conn.execute(
                "UPDATE skill_versions SET status = 'published', bundle_sha256 = ?, published_at = ? WHERE id = ?",
                (bundle_sha256, published_at, version_id),
            )
        return self.get_version(version_id)

    def delete_draft_version(self, version_id: str) -> None:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM skill_versions WHERE id = ?", (version_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Skill version not found: {version_id}")
            if existing["status"] == "published":
                skill = conn.execute("SELECT name FROM skills WHERE id=?", (existing["skill_id"],)).fetchone()
                raise ResourceConflictError(
                    f'Không thể xóa phiên bản v{existing["version_number"]} của Skill “{skill["name"]}” vì đã phát hành và được giữ bất biến. '
                    "Có thể sửa Skill để tạo phiên bản mới; phiên bản đã phát hành vẫn được giữ."
                )
            conn.execute("DELETE FROM skill_version_tools WHERE skill_version_id = ?", (version_id,))
            conn.execute("DELETE FROM skill_versions WHERE id = ?", (version_id,))


# -----------------------------------------------------------------------------
# Dynamic Skill Loader
# -----------------------------------------------------------------------------

def parse_skill_markdown(content: str) -> tuple[str, str, str]:
    """Parse SKILL.md content, extracting name, description/instructions, and output standards."""
    name = ""
    description = ""
    # Simple frontmatter parser if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            body = parts[2]
            for line in fm.splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"').strip("'")
            return name or "Untitled Skill", body.strip(), ""

    # Header-based fallback
    lines = content.splitlines()
    for line in lines:
        if line.startswith("# "):
            name = line[2:].strip()
            break
    instructions = content.strip()
    return name or "Untitled Skill", instructions, ""


def sync_skills_from_directory(directory: Path, repository: SkillRepository, *, is_global=True, project_ids=None) -> list[dict[str, Any]]:
    """Scan a directory for skill folders and sync them into the repository."""
    if not directory.exists() or not directory.is_dir():
        return []

    synced = []
    for item in sorted(directory.iterdir()):
        if not item.is_dir():
            continue
        skill_file = item / "SKILL.md"
        if not skill_file.exists():
            continue

        raw_content = skill_file.read_text(encoding="utf-8")
        parsed_name, instructions, output_standards = parse_skill_markdown(raw_content)

        # Normalize skill ID from folder name
        skill_id = item.name.lower().replace(" ", "-")
        skill_name = parsed_name or item.name

        # Create or update skill
        try:
            skill = repository.get_skill(skill_id)
        except ResourceNotFoundError:
            skill = repository.create_skill(
                skill_id=skill_id,
                name=skill_name,
                is_global=is_global,
                project_ids=project_ids,
                description=f"Loaded dynamically from {item.name}",
            )

        # Check existing versions
        versions = repository.list_versions(skill_id)
        bundle_hash = compute_directory_bundle_hash(item)

        # Check if already published with same hash
        published_matching = [v for v in versions if v["status"] == "published" and v.get("bundle_sha256") == bundle_hash]
        if published_matching:
            synced.append(published_matching[0])
            continue

        # Check if there is an existing draft
        drafts = [v for v in versions if v["status"] == "draft"]
        if drafts:
            draft_id = drafts[0]["id"]
            # Publish the draft
            published = repository.publish_version(draft_id, bundle_sha256=bundle_hash)
            synced.append(published)
        else:
            version_id = f"{skill_id}-v{len(versions) + 1}"
            draft = repository.create_draft_version(
                version_id=version_id,
                skill_id=skill_id,
                instructions=instructions,
                output_standards=output_standards,
            )
            published = repository.publish_version(draft["id"], bundle_sha256=bundle_hash)
            synced.append(published)

    return synced

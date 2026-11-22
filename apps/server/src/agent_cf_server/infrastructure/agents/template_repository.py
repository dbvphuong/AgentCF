"""Persistence and lifecycle for Agent orchestration prompt templates."""

from datetime import datetime, timezone
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


def _row_to_template(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["allow_reply"] = bool(item["allow_reply"])
    item["allow_retry"] = bool(item["allow_retry"])
    item["allow_need_human"] = bool(item["allow_need_human"])
    item["is_default"] = bool(item["is_default"])
    return item


class AgentTemplateRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_templates(self) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            rows = conn.execute(
                "SELECT * FROM agent_templates ORDER BY is_default DESC, name ASC"
            ).fetchall()
            return [_row_to_template(r) for r in rows]

    def get_template(self, template_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute(
                "SELECT * FROM agent_templates WHERE id = ?",
                (template_id,),
            ).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Không tìm thấy mẫu điều phối: {template_id}")
            return _row_to_template(row)

    def get_default_template(self) -> dict[str, Any] | None:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute(
                "SELECT * FROM agent_templates ORDER BY is_default DESC, created_at ASC LIMIT 1"
            ).fetchone()
            return _row_to_template(row) if row else None

    def create_template(
        self,
        *,
        template_id: str | None = None,
        name: str,
        description: str = "",
        prompt_text: str,
        allow_reply: bool = True,
        allow_retry: bool = True,
        allow_need_human: bool = True,
        max_turns: int = 10,
        is_default: bool = False,
    ) -> dict[str, Any]:
        tid = (template_id or f"tpl-{uuid4().hex[:12]}").strip()
        clean_name = name.strip()
        clean_prompt = prompt_text.strip()
        if not clean_name:
            raise ValueError("Tên mẫu điều phối không được để trống.")
        if not clean_prompt:
            raise ValueError("Nội dung prompt điều phối không được để trống.")
        now = _now_iso()

        with self.database.transaction() as conn:
            if is_default:
                conn.execute("UPDATE agent_templates SET is_default = 0 WHERE is_default = 1")
            else:
                has_default = conn.execute(
                    "SELECT 1 FROM agent_templates WHERE is_default = 1 LIMIT 1"
                ).fetchone()
                if not has_default:
                    is_default = True
            try:
                conn.execute(
                    "INSERT INTO agent_templates "
                    "(id, name, description, prompt_text, allow_reply, allow_retry, allow_need_human, max_turns, is_default, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        tid,
                        clean_name,
                        description.strip(),
                        clean_prompt,
                        int(bool(allow_reply)),
                        int(bool(allow_retry)),
                        int(bool(allow_need_human)),
                        int(max_turns),
                        int(bool(is_default)),
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Tên mẫu điều phối “{clean_name}” đã tồn tại.") from exc
        return self.get_template(tid)

    def update_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        prompt_text: str | None = None,
        allow_reply: bool | None = None,
        allow_retry: bool | None = None,
        allow_need_human: bool | None = None,
        max_turns: int | None = None,
        is_default: bool | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute(
                "SELECT * FROM agent_templates WHERE id = ?",
                (template_id,),
            ).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Không tìm thấy mẫu điều phối: {template_id}")

            updates: list[str] = []
            params: list[Any] = []
            if name is not None:
                clean_name = name.strip()
                if not clean_name:
                    raise ValueError("Tên mẫu điều phối không được để trống.")
                updates.append("name = ?")
                params.append(clean_name)
            if description is not None:
                updates.append("description = ?")
                params.append(description.strip())
            if prompt_text is not None:
                clean_prompt = prompt_text.strip()
                if not clean_prompt:
                    raise ValueError("Nội dung prompt điều phối không được để trống.")
                updates.append("prompt_text = ?")
                params.append(clean_prompt)
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
            if is_default is True:
                conn.execute(
                    "UPDATE agent_templates SET is_default = 0 WHERE is_default = 1 AND id <> ?",
                    (template_id,),
                )
                updates.append("is_default = 1")
            elif is_default is False and existing["is_default"]:
                raise ResourceConflictError("Phải có ít nhất một mẫu mặc định. Hãy đặt mẫu khác làm mặc định trước.")

            if not updates:
                return _row_to_template(existing)

            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(template_id)
            try:
                conn.execute(f"UPDATE agent_templates SET {', '.join(updates)} WHERE id = ?", params)
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError("Tên mẫu điều phối bị trùng hoặc dữ liệu không hợp lệ.") from exc
        return self.get_template(template_id)

    def set_default(self, template_id: str) -> dict[str, Any]:
        return self.update_template(template_id, is_default=True)

    def delete_template(self, template_id: str) -> None:
        with self.database.transaction() as conn:
            row = conn.execute(
                "SELECT id, name, is_default FROM agent_templates WHERE id = ?",
                (template_id,),
            ).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Không tìm thấy mẫu điều phối: {template_id}")
            total = conn.execute("SELECT COUNT(*) FROM agent_templates").fetchone()[0]
            if total <= 1:
                raise InUseError("Không thể xóa mẫu cuối cùng. Hệ thống cần ít nhất 1 mẫu điều phối.")
            if row["is_default"]:
                raise InUseError(
                    f'Không thể xóa mẫu mặc định “{row["name"]}”. Hãy đặt mẫu khác làm mặc định trước khi xóa.'
                )
            conn.execute("DELETE FROM agent_templates WHERE id = ?", (template_id,))

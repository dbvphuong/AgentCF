"""Persistence for Providers, Models, Roles, and General Settings (SET-002)."""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any

from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.deletion_feedback import reference_list


class ResourceConflictError(Exception):
    """The requested operation violates uniqueness or referential integrity."""


class ResourceNotFoundError(Exception):
    """The requested resource was not found."""


class InUseError(Exception):
    """The resource is currently referenced by other entities and cannot be deleted."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


def _mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    # -------------------------------------------------------------------------
    # Providers
    # -------------------------------------------------------------------------

    def create_provider(
        self,
        provider_id: str,
        name: str,
        api_format: str,
        base_url: str,
        api_key: str | None = None,
        request_timeout_seconds: int = 60,
        status: str = "active",
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            try:
                conn.execute(
                    "INSERT INTO providers (id, name, api_format, base_url, api_key_ciphertext, request_timeout_seconds, status, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (provider_id, name, api_format, base_url, api_key, request_timeout_seconds, status, _now_iso(), _now_iso()),
                )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Provider conflict: {exc}") from exc
        return self.get_provider(provider_id)

    def get_provider(self, provider_id: str, include_secret: bool = False) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Provider not found: {provider_id}")
            result = dict(row)
            key = result.pop("api_key_ciphertext", None)
            result["api_key_masked"] = _mask_api_key(key)
            if include_secret:
                result["api_key"] = key
                result["api_key_ciphertext"] = key
            return result

    def list_providers(self, status: str | None = None, include_secret: bool = True) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            query = "SELECT * FROM providers"
            params: list[Any] = []
            if status is not None:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY name ASC"
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                key = item.pop("api_key_ciphertext", None)
                item["api_key_masked"] = _mask_api_key(key)
                if include_secret:
                    item["api_key"] = key
                results.append(item)
            return results

    def update_provider(
        self,
        provider_id: str,
        name: str | None = None,
        api_format: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        request_timeout_seconds: int | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Provider not found: {provider_id}")
            updates: list[str] = []
            params: list[Any] = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if api_format is not None:
                updates.append("api_format = ?")
                params.append(api_format)
            if base_url is not None:
                updates.append("base_url = ?")
                params.append(base_url)
            if api_key is not None:
                updates.append("api_key_ciphertext = ?")
                params.append(api_key)
            if request_timeout_seconds is not None:
                updates.append("request_timeout_seconds = ?")
                params.append(request_timeout_seconds)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if not updates:
                return self.get_provider(provider_id)
            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(provider_id)
            try:
                conn.execute(f"UPDATE providers SET {', '.join(updates)} WHERE id = ?", params)
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Provider update conflict: {exc}") from exc
        return self.get_provider(provider_id)

    def delete_provider(self, provider_id: str) -> None:
        with self.database.transaction() as conn:
            try:
                cursor = conn.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
                if cursor.rowcount == 0:
                    raise ResourceNotFoundError(f"Provider not found: {provider_id}")
            except sqlite3.IntegrityError as exc:
                provider = conn.execute("SELECT name FROM providers WHERE id=?", (provider_id,)).fetchone()
                models = conn.execute("SELECT name FROM models WHERE provider_id=? ORDER BY name,id", (provider_id,)).fetchall()
                names = reference_list(f'“{row["name"]}”' for row in models)
                raise InUseError(
                    f'Không thể xóa Provider “{provider["name"]}” vì còn Model API liên kết: {names}. '
                    "Vào Settings → Providers & Models API → Models API để xóa các model này trước."
                ) from exc

    # -------------------------------------------------------------------------
    # Models
    # -------------------------------------------------------------------------

    def create_model(
        self,
        model_id: str,
        provider_id: str,
        name: str,
        model_identifier: str,
        max_output_tokens: int | None = None,
        temperature: float = 0.7,
        status: str = "active",
        runtime_adapter: str | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            try:
                conn.execute(
                    "INSERT INTO models (id, provider_id, name, model_identifier, max_output_tokens, temperature, status, created_at, updated_at,runtime_adapter) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (model_id, provider_id, name, model_identifier, max_output_tokens, temperature, status, _now_iso(), _now_iso(),runtime_adapter),
                )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Model conflict or invalid provider: {exc}") from exc
        return self.get_model(model_id)

    def get_model(self, model_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Model not found: {model_id}")
            return dict(row)

    def list_models(self, provider_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            query = "SELECT m.*, p.name AS provider_name FROM models m JOIN providers p ON m.provider_id = p.id"
            clauses: list[str] = []
            params: list[Any] = []
            if provider_id is not None:
                clauses.append("m.provider_id = ?")
                params.append(provider_id)
            if status is not None:
                clauses.append("m.status = ?")
                params.append(status)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY m.name ASC"
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def update_model(
        self,
        model_id: str,
        name: str | None = None,
        model_identifier: str | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        status: str | None = None,
        runtime_adapter: str | None = None,
        update_runtime: bool = False,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Model not found: {model_id}")
            updates: list[str] = []
            params: list[Any] = []
            if update_runtime:
                updates.append("runtime_adapter = ?")
                params.append(runtime_adapter)
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if model_identifier is not None:
                updates.append("model_identifier = ?")
                params.append(model_identifier)
            if max_output_tokens is not None:
                updates.append("max_output_tokens = ?")
                params.append(max_output_tokens)
            if temperature is not None:
                updates.append("temperature = ?")
                params.append(temperature)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if not updates:
                return self.get_model(model_id)
            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(model_id)
            try:
                conn.execute(f"UPDATE models SET {', '.join(updates)} WHERE id = ?", params)
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Model update conflict: {exc}") from exc
        return self.get_model(model_id)

    def delete_model(self, model_id: str) -> None:
        with self.database.transaction() as conn:
            try:
                cursor = conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
                if cursor.rowcount == 0:
                    raise ResourceNotFoundError(f"Model not found: {model_id}")
            except sqlite3.IntegrityError as exc:
                model = conn.execute("SELECT name FROM models WHERE id=?", (model_id,)).fetchone()
                agents = conn.execute("SELECT name FROM agents WHERE model_id=? ORDER BY name,id", (model_id,)).fetchall()
                names = reference_list(f'“{row["name"]}”' for row in agents)
                raise InUseError(
                    f'Không thể xóa Model API “{model["name"]}” vì đang được Agent sử dụng: {names}. '
                    "Vào Agent điều phối để đổi model cho các Agent này trước khi xóa."
                ) from exc

    # -------------------------------------------------------------------------
    # Roles
    # -------------------------------------------------------------------------

    def create_role(self, role_id: str, name: str, description: str = "", status: str = "active") -> dict[str, Any]:
        with self.database.transaction() as conn:
            try:
                conn.execute(
                    "INSERT INTO roles (id, name, description, status, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (role_id, name, description, status, _now_iso(), _now_iso()),
                )
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Role conflict: {exc}") from exc
        return self.get_role(role_id)

    def get_role(self, role_id: str) -> dict[str, Any]:
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError(f"Role not found: {role_id}")
            return dict(row)

    def list_roles(self, status: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect(read_only=True) as conn:
            query = "SELECT * FROM roles"
            params: list[Any] = []
            if status is not None:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY name ASC"
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def update_role(
        self,
        role_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as conn:
            existing = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
            if not existing:
                raise ResourceNotFoundError(f"Role not found: {role_id}")
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
            if not updates:
                return self.get_role(role_id)
            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(role_id)
            try:
                conn.execute(f"UPDATE roles SET {', '.join(updates)} WHERE id = ?", params)
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError(f"Role update conflict: {exc}") from exc
        return self.get_role(role_id)

    def archive_role(self, role_id: str) -> dict[str, Any]:
        return self.update_role(role_id, status="archived")

    def restore_role(self, role_id: str) -> dict[str, Any]:
        return self.update_role(role_id, status="active")

    def delete_role(self, role_id: str) -> None:
        with self.database.transaction() as conn:
            try:
                cursor = conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
                if cursor.rowcount == 0:
                    raise ResourceNotFoundError(f"Role not found: {role_id}")
            except sqlite3.IntegrityError as exc:
                role = conn.execute("SELECT name FROM roles WHERE id=?", (role_id,)).fetchone()
                agents = conn.execute("SELECT name FROM agents WHERE role_id=? ORDER BY name,id", (role_id,)).fetchall()
                names = reference_list(f'“{row["name"]}”' for row in agents)
                raise InUseError(
                    f'Không thể xóa Role “{role["name"]}” vì đang được Agent sử dụng: {names}. '
                    "Vào Agent điều phối để đổi Role cho các Agent này trước khi xóa."
                ) from exc

    # -------------------------------------------------------------------------
    # General Settings
    # -------------------------------------------------------------------------

    DEFAULT_GENERAL_SETTINGS: dict[str, Any] = {
        "default_task_timeout_seconds": 1800,
        "default_logs_lines": 100,
        "default_timezone": "Asia/Ho_Chi_Minh",
    }

    def get_general_settings(self) -> dict[str, Any]:
        result = dict(self.DEFAULT_GENERAL_SETTINGS)
        with self.database.connect(read_only=True) as conn:
            rows = conn.execute("SELECT key, value_json FROM general_settings").fetchall()
            for row in rows:
                key = row["key"]
                try:
                    result[key] = json.loads(row["value_json"])
                except Exception:
                    pass
        return result

    def update_general_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        now = _now_iso()
        with self.database.transaction() as conn:
            for key, val in updates.items():
                conn.execute(
                    "INSERT INTO general_settings (key, value_json, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at",
                    (key, json.dumps(val), now),
                )
        return self.get_general_settings()

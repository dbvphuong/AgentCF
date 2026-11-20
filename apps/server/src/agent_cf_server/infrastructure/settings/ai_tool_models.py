"""Editable CLI model preferences. Never reuse the API provider/model catalog."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from uuid import uuid4

from agent_cf_server.infrastructure.settings.repository import ResourceConflictError, ResourceNotFoundError, InUseError
from agent_cf_server.infrastructure.deletion_feedback import reference_list

DEFAULT_AI_TOOL_MODELS: list[dict[str, str]] = [
    # Codex CLI models (GPT-6 series & GPT-5 series)
    {"id": "cli-codex-61-sol", "tool_id": "codex", "name": "GPT-6.1 Sol", "model_identifier": "gpt-6.1-sol", "status": "active"},
    {"id": "cli-codex-61-terra", "tool_id": "codex", "name": "GPT-6.1 Terra", "model_identifier": "gpt-6.1-terra", "status": "active"},
    {"id": "cli-codex-6-astra", "tool_id": "codex", "name": "GPT-6 Astra", "model_identifier": "gpt-6-astra", "status": "active"},
    {"id": "cli-codex-6-sol", "tool_id": "codex", "name": "GPT-6 Sol", "model_identifier": "gpt-6-sol", "status": "active"},
    {"id": "cli-codex-6-luna", "tool_id": "codex", "name": "GPT-6 Luna", "model_identifier": "gpt-6-luna", "status": "active"},
    {"id": "cli-codex-sol", "tool_id": "codex", "name": "GPT-5.6 Sol", "model_identifier": "gpt-5.6-sol", "status": "active"},
    {"id": "cli-codex-terra", "tool_id": "codex", "name": "GPT-5.6 Terra", "model_identifier": "gpt-5.6-terra", "status": "active"},
    {"id": "cli-codex-luna", "tool_id": "codex", "name": "GPT-5.6 Luna", "model_identifier": "gpt-5.6-luna", "status": "active"},
    {"id": "cli-codex-55", "tool_id": "codex", "name": "GPT-5.5", "model_identifier": "gpt-5.5", "status": "active"},
    {"id": "cli-codex-54", "tool_id": "codex", "name": "GPT-5.4", "model_identifier": "gpt-5.4", "status": "active"},
    {"id": "cli-codex-54m", "tool_id": "codex", "name": "GPT-5.4-Mini", "model_identifier": "gpt-5.4-mini", "status": "active"},
    {"id": "cli-codex-52", "tool_id": "codex", "name": "GPT-5.2", "model_identifier": "gpt-5.2", "status": "active"},
    {"id": "cli-codex-reserve", "tool_id": "codex", "name": "GPT-Reserve", "model_identifier": "gpt-reserve", "status": "active"},

    # Antigravity models
    {"id": "cli-agy-sonnet", "tool_id": "antigravity", "name": "Claude Sonnet 4.6 (Thinking)", "model_identifier": "claude-sonnet-4.6-thinking", "status": "active"},
    {"id": "cli-agy-opus", "tool_id": "antigravity", "name": "Claude Opus 4.6 (Thinking)", "model_identifier": "claude-opus-4.6-thinking", "status": "active"},
    {"id": "cli-agy-gpt-oss", "tool_id": "antigravity", "name": "GPT-OSS 120B (Medium)", "model_identifier": "gpt-oss-120b-medium", "status": "active"},
    {"id": "cli-agy-gemini-flash", "tool_id": "antigravity", "name": "Gemini 3.8 Flash High", "model_identifier": "gemini-3.8-flash-high", "status": "active"},
    {"id": "cli-agy-gemini-carbon", "tool_id": "antigravity", "name": "Gemini 4 Carbon", "model_identifier": "gemini-4-carbon", "status": "active"},
    {"id": "cli-agy-gemini-argon", "tool_id": "antigravity", "name": "Gemini 4 Argon", "model_identifier": "gemini-4-argon", "status": "active"},
    {"id": "cli-agy-gemini-hydrogen", "tool_id": "antigravity", "name": "Gemini 4 Hydrogen", "model_identifier": "gemini-4-hydrogen", "status": "active"},
]


class AiToolModelRepository:
    def __init__(self, database):
        self.database = database

    def list(self, tool_id=None, status=None):
        clauses, params = [], []
        for name, value in (("tool_id", tool_id), ("status", status)):
            if value is not None:
                clauses.append(f"{name}=?")
                params.append(value)
        query = "SELECT * FROM ai_tool_models" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY tool_id,name,id"
        with self.database.connect(read_only=True) as conn:
            return [dict(row) for row in conn.execute(query, params)]

    def get(self, model_id):
        with self.database.connect(read_only=True) as conn:
            row = conn.execute("SELECT * FROM ai_tool_models WHERE id=?", (model_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError("Không tìm thấy Model thực thi")
            return dict(row)

    def save(self, model_id, payload, create=False):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self.database.transaction() as conn:
            try:
                if create:
                    conn.execute("INSERT INTO ai_tool_models(id,tool_id,name,model_identifier,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                        (model_id, payload["tool_id"], payload["name"], payload["model_identifier"], payload.get("status", "active"), now, now))
                else:
                    existing = conn.execute("SELECT * FROM ai_tool_models WHERE id=?", (model_id,)).fetchone()
                    if not existing:
                        raise ResourceNotFoundError("Không tìm thấy Model thực thi")
                    if "tool_id" in payload and payload["tool_id"] != existing["tool_id"]:
                        raise ResourceConflictError("Không chuyển Model sang công cụ khác; hãy tạo Model mới trong công cụ đó")
                    # A model belongs to one tool permanently; create another record for another tool.
                    updates = {key: value for key, value in payload.items() if key in ("name", "model_identifier", "status")}
                    if not updates:
                        return dict(existing)
                    updates["updated_at"] = now
                    conn.execute("UPDATE ai_tool_models SET " + ",".join(f"{key}=?" for key in updates) + " WHERE id=?", [*updates.values(), model_id])
            except sqlite3.IntegrityError as exc:
                raise ResourceConflictError("Model ID đã tồn tại trong công cụ này hoặc cấu hình không hợp lệ") from exc
            conn.execute("INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator',?,?,?,?)",
                (str(uuid4()), "ai_tool_model_created" if create else "ai_tool_model_updated", model_id, json.dumps(payload), now))
        return self.get(model_id)

    def delete(self, model_id):
        with self.database.transaction() as conn:
            row = conn.execute("SELECT * FROM ai_tool_models WHERE id=?", (model_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError("Không tìm thấy Model thực thi")
            references = conn.execute(
                "SELECT DISTINCT p.name AS process_name,pr.name AS project_name,v.version_number "
                "FROM process_versions v JOIN processes p ON p.id=v.process_id "
                "JOIN projects pr ON pr.id=p.project_id,json_each(v.definition_json,'$.tasks') task "
                "WHERE json_extract(task.value,'$.runtime.tool_model_id')=? ORDER BY pr.name,p.name,v.version_number",
                (model_id,),
            ).fetchall()
            if references:
                names = reference_list(f'Process “{ref["process_name"]}” v{ref["version_number"]} trong Project “{ref["project_name"]}”' for ref in references)
                raise InUseError(
                    f'Không thể xóa Model thực thi “{row["name"]}” vì đang được tham chiếu trong: {names}. '
                    "Có thể tắt sử dụng model trong Settings → Công cụ AI trên PC để giữ lịch sử."
                )
            conn.execute("DELETE FROM ai_tool_models WHERE id=?", (model_id,))
            conn.execute("INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator','ai_tool_model_deleted',?,'{}',?)",
                (str(uuid4()), model_id, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")))

    def configure_tool_models(self, tool_id: str, active_model_ids: list[str]) -> list[dict]:
        """Atomically set active models for a tool; unticked models are disabled."""
        if tool_id not in ("codex", "antigravity"):
            raise ResourceConflictError("Công cụ AI không hợp lệ; chỉ hỗ trợ 'codex' hoặc 'antigravity'")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        active_set = set(active_model_ids)
        with self.database.transaction() as conn:
            rows = conn.execute("SELECT id, status FROM ai_tool_models WHERE tool_id=?", (tool_id,)).fetchall()
            for row in rows:
                mid = row["id"]
                new_status = "active" if mid in active_set else "disabled"
                if new_status != row["status"]:
                    conn.execute("UPDATE ai_tool_models SET status=?, updated_at=? WHERE id=?", (new_status, now, mid))
            conn.execute(
                "INSERT INTO audit_events(id, actor_id, event_type, resource_id, data_json, recorded_at) "
                "VALUES (?, 'operator', 'ai_tool_models_configured', ?, ?, ?)",
                (str(uuid4()), tool_id, json.dumps({"tool_id": tool_id, "active_count": len(active_set)}), now),
            )
        return self.list(tool_id=tool_id)

    def _discover_codex_models(self) -> list[dict[str, str]]:
        """Dynamically discover models from local Codex cache."""
        discovered = []
        cache_path = Path.home() / ".codex" / "models_cache.json"
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                for item in data.get("models", []):
                    slug = item.get("slug")
                    name = item.get("display_name") or slug
                    if slug:
                        discovered.append({
                            "id": f"cli-codex-{slug.replace('.', '')}",
                            "tool_id": "codex",
                            "name": name,
                            "model_identifier": slug,
                            "status": "active",
                        })
            except Exception:
                pass
        return discovered

    def sync_defaults(self) -> dict:
        """Sync comprehensive and newly discovered models into the database."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        added = []
        with self.database.transaction() as conn:
            existing = {
                (row["tool_id"], row["model_identifier"]): row["id"]
                for row in conn.execute("SELECT id, tool_id, model_identifier FROM ai_tool_models").fetchall()
            }
            models_to_sync = list(DEFAULT_AI_TOOL_MODELS)
            for m in self._discover_codex_models():
                if not any(item["tool_id"] == "codex" and item["model_identifier"] == m["model_identifier"] for item in models_to_sync):
                    models_to_sync.append(m)

            for item in models_to_sync:
                key = (item["tool_id"], item["model_identifier"])
                if key not in existing:
                    new_id = item.get("id") or f"cli-{item['tool_id']}-{uuid4().hex[:8]}"
                    conn.execute(
                        "INSERT INTO ai_tool_models(id, tool_id, name, model_identifier, status, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (new_id, item["tool_id"], item["name"], item["model_identifier"], item.get("status", "active"), now, now),
                    )
                    existing[key] = new_id
                    added.append(item["name"])
            if added:
                conn.execute(
                    "INSERT INTO audit_events(id, actor_id, event_type, resource_id, data_json, recorded_at) "
                    "VALUES (?, 'operator', 'ai_tool_models_synced', 'catalog', ?, ?)",
                    (str(uuid4()), json.dumps({"added_models": added}), now),
                )
        return {"added_count": len(added), "added": added, "total": len(existing)}

    def check_tools(self) -> dict:
        """Check local availability and version of Codex and Antigravity CLI tools on the PC."""
        result = {}
        # 1. Codex
        codex_cmd = shutil.which("codex.cmd") or shutil.which("codex")
        if codex_cmd:
            try:
                ver_res = subprocess.run([codex_cmd, "--version"], capture_output=True, text=True, timeout=5)
                ver_str = ver_res.stdout.strip() if ver_res.returncode == 0 else ""
                discovered = self._discover_codex_models()
                models_list = [m["name"] for m in discovered] if discovered else [m["name"] for m in DEFAULT_AI_TOOL_MODELS if m["tool_id"] == "codex"]

                result["codex"] = {
                    "installed": True,
                    "version": ver_str or "codex-cli",
                    "status": "ready",
                    "executable": codex_cmd,
                    "models_count": len(models_list),
                    "recommended_models": models_list,
                }
            except Exception as e:
                result["codex"] = {"installed": True, "version": "", "status": "error", "error": str(e)}
        else:
            result["codex"] = {"installed": False, "version": "", "status": "not_installed"}

        # 2. Antigravity
        agy_cmd = shutil.which("agy.exe") or shutil.which("agy")
        if agy_cmd:
            try:
                ver_res = subprocess.run([agy_cmd, "--version"], capture_output=True, text=True, timeout=5)
                ver_str = ver_res.stdout.strip() if ver_res.returncode == 0 else ""
                agy_models = [m["name"] for m in DEFAULT_AI_TOOL_MODELS if m["tool_id"] == "antigravity"]

                result["antigravity"] = {
                    "installed": True,
                    "version": ver_str or "antigravity",
                    "status": "ready",
                    "executable": agy_cmd,
                    "models_count": len(agy_models),
                    "recommended_models": agy_models,
                }
            except Exception as e:
                result["antigravity"] = {"installed": True, "version": "", "status": "error", "error": str(e)}
        else:
            result["antigravity"] = {"installed": False, "version": "", "status": "not_installed"}

        return result

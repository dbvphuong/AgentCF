"""Editable CLI model preferences. Never reuse the API provider/model catalog."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

from agent_cf_server.infrastructure.settings.repository import ResourceConflictError, ResourceNotFoundError, InUseError
from agent_cf_server.infrastructure.deletion_feedback import reference_list

DEFAULT_AI_TOOL_MODELS: list[dict[str, str]] = [
    # Codex CLI models (fallback when ~/.codex/models_cache.json is unavailable)
    {"id": "cli-codex-62-sol", "tool_id": "codex", "name": "GPT-6.2-Sol", "model_identifier": "gpt-6.2-sol", "status": "active"},
    {"id": "cli-codex-62-astra", "tool_id": "codex", "name": "GPT-6.2-Astra", "model_identifier": "gpt-6.2-astra", "status": "active"},
    {"id": "cli-codex-61-sol", "tool_id": "codex", "name": "GPT-6.1-Sol", "model_identifier": "gpt-6.1-sol", "status": "active"},
    {"id": "cli-codex-61-terra", "tool_id": "codex", "name": "GPT-6.1 Terra", "model_identifier": "gpt-6.1-terra", "status": "active"},
    {"id": "cli-codex-6-astra", "tool_id": "codex", "name": "GPT-6-Astra", "model_identifier": "gpt-6-astra", "status": "active"},
    {"id": "cli-codex-6-sol", "tool_id": "codex", "name": "GPT-6-Sol", "model_identifier": "gpt-6-sol", "status": "active"},
    {"id": "cli-codex-6-luna", "tool_id": "codex", "name": "GPT-6-Luna", "model_identifier": "gpt-6-luna", "status": "active"},
    {"id": "cli-codex-sol", "tool_id": "codex", "name": "GPT-5.6-Sol", "model_identifier": "gpt-5.6-sol", "status": "active"},
    {"id": "cli-codex-terra", "tool_id": "codex", "name": "GPT-5.6-Terra", "model_identifier": "gpt-5.6-terra", "status": "active"},
    {"id": "cli-codex-luna", "tool_id": "codex", "name": "GPT-5.6-Luna", "model_identifier": "gpt-5.6-luna", "status": "active"},

    # Antigravity models (fallback when `agy models` is unavailable)
    {"id": "cli-agy-gemini-4-neon-high", "tool_id": "antigravity", "name": "Gemini 4 Neon (High)", "model_identifier": "gemini-4-neon-high", "status": "active"},
    {"id": "cli-agy-gemini-4-neon-xhigh", "tool_id": "antigravity", "name": "Gemini 4 Neon (XHigh)", "model_identifier": "gemini-4-neon-xhigh", "status": "active"},
    {"id": "cli-agy-gemini-4-neon-medium", "tool_id": "antigravity", "name": "Gemini 4 Neon (Medium)", "model_identifier": "gemini-4-neon-medium", "status": "active"},
    {"id": "cli-agy-gemini-4-neon-low", "tool_id": "antigravity", "name": "Gemini 4 Neon (Low)", "model_identifier": "gemini-4-neon-low", "status": "active"},
    {"id": "cli-agy-gemini-4-argon-high", "tool_id": "antigravity", "name": "Gemini 4 Argon (High)", "model_identifier": "gemini-4-argon-high", "status": "active"},
    {"id": "cli-agy-gemini-4-argon-medium", "tool_id": "antigravity", "name": "Gemini 4 Argon (Medium)", "model_identifier": "gemini-4-argon-medium", "status": "active"},
    {"id": "cli-agy-gemini-4-argon-low", "tool_id": "antigravity", "name": "Gemini 4 Argon (Low)", "model_identifier": "gemini-4-argon-low", "status": "active"},
    {"id": "cli-agy-gemini-4-hydrogen-high", "tool_id": "antigravity", "name": "Gemini 4 Hydrogen (High)", "model_identifier": "gemini-4-hydrogen-high", "status": "active"},
    {"id": "cli-agy-gemini-4-hydrogen-xhigh", "tool_id": "antigravity", "name": "Gemini 4 Hydrogen (XHigh)", "model_identifier": "gemini-4-hydrogen-xhigh", "status": "active"},
    {"id": "cli-agy-gemini-4-hydrogen-medium", "tool_id": "antigravity", "name": "Gemini 4 Hydrogen (Medium)", "model_identifier": "gemini-4-hydrogen-medium", "status": "active"},
    {"id": "cli-agy-gemini-4-hydrogen-low", "tool_id": "antigravity", "name": "Gemini 4 Hydrogen (Low)", "model_identifier": "gemini-4-hydrogen-low", "status": "active"},
    {"id": "cli-agy-orchestrator-neon", "tool_id": "antigravity", "name": "Orchestrator (Neon)", "model_identifier": "gemini-pro-orchestrator-neon", "status": "active"},
    {"id": "cli-agy-orchestrator-argon", "tool_id": "antigravity", "name": "Orchestrator (Argon)", "model_identifier": "gemini-pro-orchestrator-g1-pro", "status": "active"},
    {"id": "cli-agy-gemini-flash", "tool_id": "antigravity", "name": "Gemini 3.8 Flash (High)", "model_identifier": "gemini-3.8-flash-high", "status": "active"},
    {"id": "cli-agy-gemini-flash-medium", "tool_id": "antigravity", "name": "Gemini 3.8 Flash (Medium)", "model_identifier": "gemini-3.8-flash-medium", "status": "active"},
    {"id": "cli-agy-gemini-flash-low", "tool_id": "antigravity", "name": "Gemini 3.8 Flash (Low)", "model_identifier": "gemini-3.8-flash-low", "status": "active"},
    {"id": "cli-agy-opus-55-high", "tool_id": "antigravity", "name": "Claude Opus 5.5 (High)", "model_identifier": "claude-opus-5-5-high", "status": "active"},
    {"id": "cli-agy-opus-55-medium", "tool_id": "antigravity", "name": "Claude Opus 5.5 (Medium)", "model_identifier": "claude-opus-5-5-medium", "status": "active"},
    {"id": "cli-agy-opus-55-low", "tool_id": "antigravity", "name": "Claude Opus 5.5 (Low)", "model_identifier": "claude-opus-5-5-low", "status": "active"},
    {"id": "cli-agy-sonnet-55-high", "tool_id": "antigravity", "name": "Claude Sonnet 5.5 (High)", "model_identifier": "claude-sonnet-5-5-high", "status": "active"},
    {"id": "cli-agy-sonnet-55-medium", "tool_id": "antigravity", "name": "Claude Sonnet 5.5 (Medium)", "model_identifier": "claude-sonnet-5-5-medium", "status": "active"},
    {"id": "cli-agy-sonnet-55-low", "tool_id": "antigravity", "name": "Claude Sonnet 5.5 (Low)", "model_identifier": "claude-sonnet-5-5-low", "status": "active"},
    {"id": "cli-agy-gpt-oss", "tool_id": "antigravity", "name": "GPT-OSS 120B (Medium)", "model_identifier": "gpt-oss-120b-medium", "status": "active"},
]

_CANONICAL_MODEL_IDS: dict[tuple[str, str], str] = {
    (item["tool_id"], item["model_identifier"]): item["id"]
    for item in DEFAULT_AI_TOOL_MODELS
}


def _parse_version_key(folder_name: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", folder_name)
    return tuple(int(part) for part in parts) if parts else (0,)


def _slug_to_record_id(tool_id: str, identifier: str) -> str:
    canonical = _CANONICAL_MODEL_IDS.get((tool_id, identifier))
    if canonical:
        return canonical
    prefix = "codex" if tool_id == "codex" else "agy"
    slug = re.sub(r"[^a-z0-9]+", "-", identifier.lower()).strip("-") or "custom"
    return f"cli-{prefix}-{slug}"


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

    def _find_codex_executable(self) -> str | None:
        """Locate Codex CLI binary (PATH or VS Code/Codex extension binary on Windows)."""
        if sys.platform == "win32":
            native = shutil.which("codex.exe")
            if native:
                return native
            extensions_dir = Path.home() / ".vscode" / "extensions"
            if extensions_dir.is_dir():
                candidates: list[tuple[tuple[int, ...], Path]] = []
                for entry in extensions_dir.iterdir():
                    if not entry.is_dir() or not entry.name.startswith("openai.chatgpt-"):
                        continue
                    binary = entry / "bin" / "windows-x86_64" / "codex.exe"
                    if binary.is_file():
                        candidates.append((_parse_version_key(entry.name), binary))
                if candidates:
                    candidates.sort(key=lambda item: item[0], reverse=True)
                    return str(candidates[0][1])
            return shutil.which("codex.cmd") or shutil.which("codex")
        return shutil.which("codex")

    def _find_agy_executable(self) -> str | None:
        """Locate Antigravity CLI binary (PATH, ~/.gemini/bin, or ~/.antigravity/bin)."""
        if sys.platform == "win32":
            for candidate_name in ("agy.exe", "agy.cmd", "agy"):
                found = shutil.which(candidate_name)
                if found:
                    return found
            for local_bin in (
                Path.home() / ".gemini" / "bin" / "agy.exe",
                Path.home() / ".antigravity" / "bin" / "agy.exe",
            ):
                if local_bin.is_file():
                    return str(local_bin)
            return None
        found = shutil.which("agy")
        if found:
            return found
        local_bin = Path.home() / ".gemini" / "bin" / "agy"
        return str(local_bin) if local_bin.is_file() else None

    def _discover_codex_models(self) -> list[dict[str, str]]:
        """Dynamically discover user-visible models from local Codex cache."""
        discovered: list[dict[str, str]] = []
        seen_identifiers: set[str] = set()
        cache_path = Path.home() / ".codex" / "models_cache.json"
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                for item in data.get("models", []):
                    if item.get("visibility") == "hide":
                        continue
                    slug = (item.get("slug") or "").strip()
                    name = (item.get("display_name") or slug).strip()
                    if slug and slug not in seen_identifiers:
                        seen_identifiers.add(slug)
                        discovered.append({
                            "id": _slug_to_record_id("codex", slug),
                            "tool_id": "codex",
                            "name": name,
                            "model_identifier": slug,
                            "status": "active",
                        })
            except Exception:
                pass
        return discovered

    def _discover_antigravity_models(self) -> list[dict[str, str]]:
        """Dynamically discover available models from local `agy models` CLI."""
        agy_cmd = self._find_agy_executable()
        if not agy_cmd:
            return []
        try:
            res = subprocess.run(
                [agy_cmd, "models"],
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            return []
        if res.returncode != 0:
            return []

        discovered: list[dict[str, str]] = []
        seen_identifiers: set[str] = set()
        for raw_line in res.stdout.splitlines():
            if "\t" not in raw_line:
                continue
            identifier, name = (part.strip() for part in raw_line.split("\t", 1))
            if not identifier or not name or not re.fullmatch(r"[A-Za-z0-9._-]+", identifier):
                continue
            if identifier in seen_identifiers:
                continue
            seen_identifiers.add(identifier)
            discovered.append({
                "id": _slug_to_record_id("antigravity", identifier),
                "tool_id": "antigravity",
                "name": name,
                "model_identifier": identifier,
                "status": "active",
            })
        return discovered

    def sync_defaults(self) -> dict:
        """Sync models with live local PC discovery (`models_cache.json` and `agy models`)."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        codex_live = self._discover_codex_models()
        agy_live = self._discover_antigravity_models()
        live_by_tool = {
            "codex": (codex_live, len(codex_live) > 0),
            "antigravity": (agy_live, len(agy_live) > 0),
        }

        added: list[str] = []
        updated: list[str] = []
        removed: list[str] = []
        disabled: list[str] = []

        with self.database.transaction() as conn:
            used_ids = {row["id"] for row in conn.execute("SELECT id FROM ai_tool_models").fetchall()}

            for tool_id in ("codex", "antigravity"):
                discovered, from_live = live_by_tool[tool_id]
                target_models = (
                    discovered
                    if from_live
                    else [item for item in DEFAULT_AI_TOOL_MODELS if item["tool_id"] == tool_id]
                )
                existing_rows = {
                    row["model_identifier"]: dict(row)
                    for row in conn.execute("SELECT * FROM ai_tool_models WHERE tool_id=?", (tool_id,)).fetchall()
                }

                for item in target_models:
                    identifier = item["model_identifier"]
                    if identifier not in existing_rows:
                        new_id = item.get("id") or _slug_to_record_id(tool_id, identifier)
                        if new_id in used_ids:
                            new_id = f"{new_id}-{uuid4().hex[:6]}"
                        used_ids.add(new_id)
                        conn.execute(
                            "INSERT INTO ai_tool_models(id, tool_id, name, model_identifier, status, created_at, updated_at) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (new_id, tool_id, item["name"], identifier, item.get("status", "active"), now, now),
                        )
                        added.append(item["name"])
                    else:
                        row = existing_rows[identifier]
                        if row["name"] != item["name"]:
                            conn.execute(
                                "UPDATE ai_tool_models SET name=?, updated_at=? WHERE id=?",
                                (item["name"], now, row["id"]),
                            )
                            updated.append(item["name"])

                if from_live:
                    live_identifiers = {item["model_identifier"] for item in target_models}
                    for identifier, row in existing_rows.items():
                        if identifier in live_identifiers:
                            continue
                        referenced = conn.execute(
                            "SELECT 1 FROM process_versions v, json_each(v.definition_json, '$.tasks') task "
                            "WHERE json_extract(task.value, '$.runtime.tool_model_id')=? LIMIT 1",
                            (row["id"],),
                        ).fetchone()
                        if referenced:
                            if row["status"] != "disabled":
                                conn.execute(
                                    "UPDATE ai_tool_models SET status='disabled', updated_at=? WHERE id=?",
                                    (now, row["id"]),
                                )
                                disabled.append(row["name"])
                        else:
                            conn.execute("DELETE FROM ai_tool_models WHERE id=?", (row["id"],))
                            removed.append(row["name"])

            total = conn.execute("SELECT COUNT(*) FROM ai_tool_models").fetchone()[0]
            if added or updated or removed or disabled:
                conn.execute(
                    "INSERT INTO audit_events(id, actor_id, event_type, resource_id, data_json, recorded_at) "
                    "VALUES (?, 'operator', 'ai_tool_models_synced', 'catalog', ?, ?)",
                    (
                        str(uuid4()),
                        json.dumps({
                            "added_models": added,
                            "updated_models": updated,
                            "removed_models": removed,
                            "disabled_models": disabled,
                        }),
                        now,
                    ),
                )
        return {
            "added_count": len(added),
            "added": added,
            "updated_count": len(updated),
            "updated": updated,
            "removed_count": len(removed),
            "removed": removed,
            "disabled_count": len(disabled),
            "disabled": disabled,
            "sources": {
                "codex": "local_cache" if codex_live else "default",
                "antigravity": "cli" if agy_live else "default",
            },
            "total": total,
        }

    def check_tools(self) -> dict:
        """Check local availability and version of Codex and Antigravity CLI tools on the PC."""
        result = {}
        # 1. Codex
        codex_cmd = self._find_codex_executable()
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
        agy_cmd = self._find_agy_executable()
        if agy_cmd:
            try:
                ver_res = subprocess.run([agy_cmd, "--version"], capture_output=True, text=True, timeout=5)
                ver_str = ver_res.stdout.strip() if ver_res.returncode == 0 else ""
                db_agy_models = self.list(tool_id="antigravity", status="active")
                agy_models = (
                    [m["name"] for m in db_agy_models]
                    if db_agy_models
                    else [m["name"] for m in DEFAULT_AI_TOOL_MODELS if m["tool_id"] == "antigravity"]
                )

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

"""Project management and transactional draft publication for the Web editor."""

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4

from agent_cf_server.domain.processes.graph import validate_graph
from agent_cf_server.domain.skills.local_source import validate_absolute_path
from agent_cf_server.infrastructure.skills.access import require_project_skill
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.projects.deletion import delete_process_history
from agent_cf_server.infrastructure.runs.artifact_cleanup import cleanup_artifacts
from agent_cf_server.infrastructure.deletion_feedback import RUN_CONTEXT, reference_list, run_label


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class CloneConflictError(ValueError):
    """A clone retry reused its key with different input."""


class ConfigurationConflictError(ValueError):
    """Current configuration changed after the editor loaded."""


class ProjectManagement:
    def __init__(self, database: Database, artifacts_dir=None):
        self.database = database
        self.artifacts_dir = artifacts_dir

    @staticmethod
    def required(conn, table, rid):
        # Table names are internal constants, never request input.
        row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
        if row is None:
            raise KeyError(rid)
        return dict(row)

    def workspaces(self):
        with self.database.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM workspaces ORDER BY name")]

    def list_projects(self):
        with self.database.connect() as conn:
            projects = [dict(r) for r in conn.execute(
                "SELECT p.*,a.name pm_name FROM projects p LEFT JOIN agents a ON a.id=p.pm_agent_id ORDER BY p.name")]
            for p in projects:
                p["team"] = [dict(r) for r in conn.execute(
                    "SELECT a.id,a.name,a.status FROM agents a WHERE a.id IN ("
                    "SELECT pm_agent_id FROM projects WHERE id=? UNION "
                    "SELECT json_extract(node.value,'$.agent_id') FROM processes pr "
                    "JOIN json_each(COALESCE(pr.configuration_json,(SELECT definition_json FROM process_versions v WHERE v.process_id=pr.id ORDER BY version_number DESC LIMIT 1)),'$.tasks') node "
                    "WHERE pr.project_id=?) "
                    "ORDER BY a.name", (p["id"], p["id"]))]
                p["targets"] = [dict(r) for r in conn.execute(
                    "SELECT * FROM project_targets WHERE project_id=? ORDER BY starts_on DESC", (p["id"],))]
                p["processes"] = [dict(r) for r in conn.execute(
                    "SELECT * FROM processes WHERE project_id=? ORDER BY name", (p["id"],))]
            return projects

    def save_project(self, payload, project_id=None):
        with self.database.transaction() as conn:
            pm = self.required(conn, "agents", payload["pm_agent_id"])
            if pm["status"] != "active":
                raise ValueError("PM phải là Agent active")
            working_directory = payload.get("working_directory")
            if working_directory:
                working_directory = validate_absolute_path(working_directory.strip())
            if project_id:
                self.required(conn, "projects", project_id)
                conn.execute("UPDATE projects SET name=?,description=?,pm_agent_id=? WHERE id=?",
                             (payload["name"], payload["description"], pm["id"], project_id))
                if working_directory is not None:
                    conn.execute("UPDATE projects SET working_directory=? WHERE id=?", (working_directory, project_id))
            else:
                project_id = str(uuid4())
                self.required(conn, "workspaces", payload["workspace_id"])
                conn.execute("INSERT INTO projects(id,workspace_id,name,description,pm_agent_id) VALUES (?,?,?,?,?)",
                             (project_id, payload["workspace_id"], payload["name"], payload["description"], pm["id"]))
                conn.execute("UPDATE projects SET working_directory=? WHERE id=?", (working_directory or "", project_id))
        return self.get_project(project_id)

    def get_project(self, project_id):
        with self.database.connect() as conn:
            result = self.required(conn, "projects", project_id)
            result["team"] = [dict(r) for r in conn.execute(
                "SELECT a.id,a.name,a.status FROM agents a WHERE a.id IN ("
                "SELECT pm_agent_id FROM projects WHERE id=? UNION "
                "SELECT json_extract(node.value,'$.agent_id') FROM processes p "
                "JOIN json_each(COALESCE(p.configuration_json,(SELECT definition_json FROM process_versions v WHERE v.process_id=p.id ORDER BY version_number DESC LIMIT 1)),'$.tasks') node "
                "WHERE p.project_id=?) "
                "ORDER BY a.name", (project_id, project_id))]
            result["targets"] = [dict(r) for r in conn.execute("SELECT * FROM project_targets WHERE project_id=? ORDER BY starts_on DESC", (project_id,))]
            result["processes"] = [dict(r) for r in conn.execute("SELECT * FROM processes WHERE project_id=? ORDER BY name", (project_id,))]
            return result

    def clone_project(self, source_id: str, name: str, request_key: str | None = None):
        name = name.strip()
        if not name or len(name) > 128:
            raise ValueError("Tên Project phải có từ 1 đến 128 ký tự")
        fingerprint = sha256(encode({"name": name}).encode("utf-8")).hexdigest()
        with self.database.transaction() as conn:
            receipt = None
            if request_key:
                receipt = conn.execute(
                    "SELECT request_sha256,response_json FROM receipts WHERE principal_id='operator' "
                    "AND operation='clone_project' AND resource_id=? AND request_key=?",
                    (source_id, request_key),
                ).fetchone()
            if receipt:
                if receipt["request_sha256"] != fingerprint:
                    raise CloneConflictError("Khóa yêu cầu nhân bản đã được dùng với tên khác")
                clone_id = json.loads(receipt["response_json"])["project_id"]
            else:
                source = self.required(conn, "projects", source_id)
                clone_id = str(uuid4())
                at = now()
                conn.execute(
                    "INSERT INTO projects(id,workspace_id,name,status,description,pm_agent_id) VALUES (?,?,?,?,?,?)",
                    (clone_id, source["workspace_id"], name, source["status"], source["description"], source["pm_agent_id"]),
                )
                conn.execute("UPDATE projects SET working_directory=? WHERE id=?", (source["working_directory"], clone_id))
                conn.execute(
                    "INSERT INTO skill_projects(skill_id,project_id) SELECT skill_id,? FROM skill_projects WHERE project_id=?",
                    (clone_id, source_id),
                )
                for target in conn.execute("SELECT * FROM project_targets WHERE project_id=?", (source_id,)).fetchall():
                    conn.execute(
                        "INSERT INTO project_targets(id,project_id,name,period,target_count,completed_count,status,"
                        "created_at,updated_at,starts_on,ends_on,acceptance_criteria) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (str(uuid4()), clone_id, target["name"], target["period"], target["target_count"],
                         target["completed_count"], target["status"], at, at, target["starts_on"],
                         target["ends_on"], target["acceptance_criteria"]),
                    )
                process_ids: dict[str, str] = {}
                version_ids: dict[str, str] = {}
                for process in conn.execute("SELECT * FROM processes WHERE project_id=? ORDER BY id", (source_id,)).fetchall():
                    copied_id = str(uuid4())
                    process_ids[process["id"]] = copied_id
                    conn.execute(
                        "INSERT INTO processes(id,project_id,name,status,description) VALUES (?,?,?,?,?)",
                        (copied_id, clone_id, process["name"], process["status"], process["description"]),
                    )
                    self._clone_versions(conn, process["id"], copied_id, version_ids)
                    conn.execute("UPDATE processes SET configuration_json=?,configuration_revision=? WHERE id=?", (process["configuration_json"],process["configuration_revision"],copied_id))
                for schedule in conn.execute("SELECT * FROM schedules WHERE project_id=?", (source_id,)).fetchall():
                    if schedule["process_id"] not in process_ids or schedule["process_version_id"] not in version_ids:
                        raise ValueError("Lịch của Project gốc có tham chiếu Process/version không hợp lệ")
                    conn.execute(
                        "INSERT INTO schedules(id,project_id,process_id,process_version_id,name,cadence,cron_expression,"
                        "timezone,is_active,default_runner_id,run_input_json,next_run_at,last_run_at,last_run_id,created_at,updated_at,follow_current_configuration) "
                        "VALUES (?,?,?,?,?,?,?,?,0,?,?,NULL,NULL,NULL,?,?,?)",
                        (str(uuid4()), clone_id, process_ids[schedule["process_id"]], version_ids[schedule["process_version_id"]],
                         schedule["name"], schedule["cadence"], schedule["cron_expression"], schedule["timezone"],
                         schedule["default_runner_id"], schedule["run_input_json"], at, at, schedule["follow_current_configuration"]),
                    )
                conn.execute(
                    "INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) "
                    "VALUES (?,'operator','project_cloned',?,?,?)",
                    (str(uuid4()), clone_id, encode({"source_project_id": source_id}), at),
                )
                if request_key:
                    conn.execute(
                        "INSERT INTO receipts(principal_id,operation,resource_id,request_key,request_sha256,response_json,created_at) "
                        "VALUES ('operator','clone_project',?,?,?,?,?)",
                        (source_id, request_key, fingerprint, encode({"project_id": clone_id}), at),
                    )
        return self.get_project(clone_id)

    @staticmethod
    def _clone_versions(conn, source_process_id, copied_process_id, version_ids):
        for version in conn.execute("SELECT * FROM process_versions WHERE process_id=? ORDER BY CASE status WHEN 'published' THEN 0 ELSE 1 END,version_number", (source_process_id,)).fetchall():
            copied_id = str(uuid4())
            version_ids[version["id"]] = copied_id
            # Insert children while draft, then freeze the copied published snapshot.
            # The source and its immutability triggers are never changed.
            conn.execute(
                "INSERT INTO process_versions(id,process_id,version_number,revision,status,definition_format_version,"
                "interpreter_version,definition_json) VALUES (?,?,?,?,'draft',?,?,?)",
                (copied_id, copied_process_id, version["version_number"], version["revision"],
                 version["definition_format_version"], version["interpreter_version"], version["definition_json"]),
            )
            conn.execute(
                "INSERT INTO tasks(process_version_id,id,task_key,definition_json) "
                "SELECT ?,id,task_key,definition_json FROM tasks WHERE process_version_id=?",
                (copied_id, version["id"]),
            )
            conn.execute(
                "INSERT INTO dependencies(process_version_id,source_task_id,target_task_id) "
                "SELECT ?,source_task_id,target_task_id FROM dependencies WHERE process_version_id=?",
                (copied_id, version["id"]),
            )
            if version["status"] == "published":
                conn.execute(
                    "UPDATE process_versions SET status='published',snapshot_sha256=?,published_at=? WHERE id=?",
                    (version["snapshot_sha256"], version["published_at"], copied_id),
                )

    def save_team(self, project_id, ids):
        # Retain an explicit error for older clients; membership is no longer editable.
        with self.database.connect() as conn:
            self.required(conn, "projects", project_id)
        raise ValueError("Team được tổng hợp tự động từ PM và Agent trong node Process; không chỉnh thành viên thủ công.")

    def save_target(self, project_id, payload, target_id=None):
        if payload["ends_on"] < payload["starts_on"]:
            raise ValueError("Ngày kết thúc phải sau ngày bắt đầu")
        if payload["completed_count"] > payload["target_count"]:
            raise ValueError("Số kết quả được duyệt không được vượt mục tiêu")
        with self.database.transaction() as conn:
            self.required(conn, "projects", project_id)
            if target_id:
                old = self.required(conn, "project_targets", target_id)
                if old["project_id"] != project_id:
                    raise KeyError(target_id)
                conn.execute("UPDATE project_targets SET name=?,period=?,target_count=?,completed_count=?,starts_on=?,ends_on=?,acceptance_criteria=?,updated_at=? WHERE id=?",
                             (*[payload[k] for k in ("name", "period", "target_count", "completed_count", "starts_on", "ends_on", "acceptance_criteria")], now(), target_id))
            else:
                target_id = str(uuid4())
                conn.execute("INSERT INTO project_targets(id,project_id,name,period,target_count,completed_count,starts_on,ends_on,acceptance_criteria,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                             (target_id, project_id, *[payload[k] for k in ("name", "period", "target_count", "completed_count", "starts_on", "ends_on", "acceptance_criteria")], now(), now()))
        return self.get_project(project_id)

    def save_process(self, project_id, payload, process_id=None):
        with self.database.transaction() as conn:
            if self.required(conn, "projects", project_id)["status"] != "active":
                raise ValueError("Project đã archived")
            if process_id:
                old = self.required(conn, "processes", process_id)
                if old["project_id"] != project_id:
                    raise KeyError(process_id)
                conn.execute("UPDATE processes SET name=?,description=? WHERE id=?", (payload["name"], payload["description"], process_id))
            else:
                process_id = str(uuid4())
                conn.execute("INSERT INTO processes(id,project_id,name,description) VALUES (?,?,?,?)", (process_id, project_id, payload["name"], payload["description"]))
                self._new_draft(conn, process_id, {"definition_format_version": "1", "interpreter_version": "dag-v1", "tasks": [], "dependencies": []})
        return self.get_process(process_id)

    def get_process(self, process_id):
        with self.database.connect() as conn:
            result = self.required(conn, "processes", process_id)
            result["versions"] = []
            for row in conn.execute("SELECT * FROM process_versions WHERE process_id=? ORDER BY version_number DESC", (process_id,)):
                v = dict(row)
                v["definition"] = json.loads(v.pop("definition_json"))
                result["versions"].append(v)
            return result

    def _new_draft(self, conn, process_id, definition):
        number = conn.execute("SELECT COALESCE(MAX(version_number),0)+1 FROM process_versions WHERE process_id=?", (process_id,)).fetchone()[0]
        vid = str(uuid4())
        conn.execute("INSERT INTO process_versions(id,process_id,version_number,status,definition_format_version,interpreter_version,definition_json) VALUES (?,?,?,'draft','1','dag-v1',?)", (vid, process_id, number, encode(definition)))
        return vid

    def draft(self, process_id):
        with self.database.transaction() as conn:
            proc = self.required(conn, "processes", process_id)
            if proc["status"] != "active":
                raise ValueError("Process đã archived")
            draft = conn.execute("SELECT id FROM process_versions WHERE process_id=? AND status='draft'", (process_id,)).fetchone()
            if not draft:
                latest = conn.execute("SELECT definition_json FROM process_versions WHERE process_id=? ORDER BY version_number DESC LIMIT 1", (process_id,)).fetchone()
                definition = json.loads(latest[0]) if latest else {"definition_format_version": "1", "interpreter_version": "dag-v1", "tasks": [], "dependencies": []}
                self._new_draft(conn, process_id, definition)
        return self.get_process(process_id)

    def save_draft(self, process_id, version_id, definition, revision):
        # Incomplete drafts are allowed; publication performs full validation.
        if not isinstance(definition.get("tasks"), list) or not isinstance(definition.get("dependencies"), list):
            raise ValueError("Draft phải có tasks và dependencies")
        with self.database.transaction() as conn:
            v = self.required(conn, "process_versions", version_id)
            if v["process_id"] != process_id:
                raise KeyError(version_id)
            if v["status"] != "draft" or v["revision"] != revision:
                raise ValueError("Draft đã thay đổi; tải lại trước khi lưu")
            conn.execute("UPDATE process_versions SET definition_json=?,revision=revision+1 WHERE id=?", (encode(definition), version_id))
        return self.get_process(process_id)

    def _snapshot(self, conn, process_id, definition, current_skills=False):
        snapshot = deepcopy(definition)
        validate_graph(snapshot)
        proc = self.required(conn, "processes", process_id)
        project = self.required(conn, "projects", proc["project_id"])
        if proc["status"] != "active" or project["status"] != "active":
            raise ValueError("Project/Process phải active")
        session_mode = definition.get("session_mode") or "shared_per_tool"
        snapshot["session_mode"] = session_mode
        for task in snapshot["tasks"]:
            task.setdefault("session_mode", session_mode)
            tid = task["id"]
            aid = task.get("agent_id")
            if not aid or not conn.execute("SELECT 1 FROM agents WHERE id=?", (aid,)).fetchone():
                raise ValueError(f"Node {tid}: Agent điều phối không tồn tại")
            agent = self.required(conn, "agents", aid)
            model = self.required(conn, "models", agent["model_id"])
            provider = self.required(conn, "providers", model["provider_id"])
            role = self.required(conn, "roles", agent["role_id"])
            if any(row["status"] != "active" for row in (agent, model, provider, role)):
                raise ValueError(f"Node {tid}: Agent/model/provider/role không active")
            task["agent_snapshot"] = {
                "id": agent["id"],
                "name": agent["name"],
                "role_id": agent["role_id"],
                "instructions": agent["instructions"],
                "model_id": agent["model_id"],
                "template_id": agent.get("template_id"),
                "allow_reply": bool(agent.get("allow_reply", 1)),
                "allow_retry": bool(agent.get("allow_retry", 1)),
                "allow_need_human": bool(agent.get("allow_need_human", 1)),
                "max_turns": int(agent.get("max_turns") or 10),
            }
            if task["kind"] == "agent":
                runtime = task.get("runtime", {})
                if runtime.get("adapter") not in ("codex", "antigravity") or not runtime.get("model_id"):
                    raise ValueError(f"Node {tid}: cần runtime và Model ID chính xác")
                if runtime.get("tool_model_id"):
                    selected_model = self.required(conn, "ai_tool_models", runtime["tool_model_id"])
                else:
                    # Existing graphs may contain only an exact CLI identifier. Resolve within
                    # that tool's catalog, never via the orchestration Agent's API model.
                    selected_model = conn.execute("SELECT * FROM ai_tool_models WHERE tool_id=? AND model_identifier=?", (runtime["adapter"], runtime["model_id"])).fetchone()
                    if not selected_model:
                        raise ValueError(f"Node {tid}: chọn Model thực thi trong Settings → Công cụ AI trên PC")
                if selected_model["status"] != "active":
                    raise ValueError(f"Node {tid}: Model thực thi đã tắt sử dụng")
                if current_skills:
                    runtime["model_id"] = selected_model["model_identifier"]
                if runtime["model_id"] != selected_model["model_identifier"]:
                    raise ValueError(f"Node {tid}: Model ID phải khớp model đã chọn")
                if selected_model["tool_id"] != runtime["adapter"]:
                    raise ValueError(f"Node {tid}: Model không thuộc Công cụ AI thực thi đã chọn")
                runtime.pop("catalog_model_id", None)
                runtime["tool_model_id"] = selected_model["id"]
                task["tool_model_snapshot"] = {key: selected_model[key] for key in ("id", "tool_id", "name", "model_identifier")}
                sid = task.get("skill_id")
                if not sid:
                    raise ValueError(f"Node {tid}: thiếu Skill")
                if self.required(conn, "skills", sid)["status"] != "active":
                    raise ValueError(f"Node {tid}: Skill đã archived")
                require_project_skill(conn, sid, proc["project_id"])
                skill = conn.execute("SELECT * FROM skill_versions WHERE skill_id=? " + ("" if current_skills else "AND status='published' ") + "ORDER BY version_number DESC LIMIT 1", (sid,)).fetchone()
                if not skill:
                    raise ValueError(f"Node {tid}: Skill chưa cấu hình file hoặc hướng dẫn" if current_skills else f"Node {tid}: Skill chưa có version published")
                if skill["source_path"]:
                    if current_skills and not project["working_directory"]:
                        raise ValueError("Thiếu thư mục Project trên PC. Mở Sửa Project để đặt thư mục bạn thường mở trong Codex/Antigravity.")
                    if not task.get("runner_id"):
                        task["runner_id"] = skill["source_runner_id"]
                    if current_skills or not task.get("working_directory"):
                        task["working_directory"] = project["working_directory"]
                    runner = self.required(conn, "runners", task.get("runner_id", ""))
                    if runner["deleted_at"]:
                        raise ValueError(f"Node {tid}: PC chứa Skill đã bị xóa kết nối. Sửa Skill để chọn PC đang kết nối, lưu rồi chạy lại Process.")
                    if runner["id"] != skill["source_runner_id"] or runner["workspace_id"] != project["workspace_id"] or runner["status"] == "disabled":
                        raise ValueError(f"Node {tid}: PC phải khớp PC sở hữu file Skill và Workspace")
                    validate_absolute_path(task.get("working_directory", ""))
                allowed = {r[0] for r in conn.execute("SELECT tool_id FROM agent_allowed_tools WHERE agent_id=?", (aid,))}
                required = {r[0] for r in conn.execute("SELECT tool_id FROM skill_version_tools WHERE skill_version_id=?", (skill["id"],))}
                if not required <= allowed:
                    raise ValueError(f"Node {tid}: Skill vượt quyền Tool của Agent")
                for tool_id in required:
                    if self.required(conn, "tools", tool_id)["status"] != "active":
                        raise ValueError(f"Node {tid}: Tool đã archived")
                task["skill_snapshot"] = dict(skill)
                task["allowed_tool_ids"] = sorted(required)
            else:
                robot = self.required(conn, "robot_versions", task.get("robot_version_id", ""))
                if robot["status"] != "published" or self.required(conn, "robots", robot["robot_id"])["status"] != "active":
                    raise ValueError(f"Node {tid}: RobotVersion phải published và Robot active")
                runner = self.required(conn, "runners", task.get("runner_id", ""))
                if runner["workspace_id"] != project["workspace_id"] or runner["status"] == "disabled":
                    raise ValueError(f"Node {tid}: PC không hợp lệ")
                for key in ("entrypoint", "contract_version", "bundle_sha256"):
                    task[key] = robot[key]
            task.setdefault("execution_timeout_seconds", 300)
        return snapshot

    def _current_configuration(self, conn, process_id):
        proc = self.required(conn, "processes", process_id)
        if proc["configuration_json"] is not None:
            return proc, json.loads(proc["configuration_json"]), f"saved:{proc['configuration_revision']}"
        latest = conn.execute("SELECT * FROM process_versions WHERE process_id=? ORDER BY version_number DESC LIMIT 1", (process_id,)).fetchone()
        definition = json.loads(latest["definition_json"]) if latest else {"definition_format_version":"1","interpreter_version":"dag-v1","tasks":[],"dependencies":[],"session_mode":"shared_per_tool"}
        if "session_mode" not in definition:
            definition["session_mode"] = "shared_per_tool"
        token = f"legacy:{latest['id']}:{latest['revision']}" if latest else "empty"
        return proc, definition, token

    def get_configuration(self, process_id):
        with self.database.connect(read_only=True) as conn:
            proc, definition, token = self._current_configuration(conn, process_id)
            return {"id":process_id,"name":proc["name"],"definition":definition,"configuration_token":token}

    def save_configuration(self, process_id, definition, expected_token):
        with self.database.transaction() as conn:
            _, _, token = self._current_configuration(conn, process_id)
            if token != expected_token:
                raise ConfigurationConflictError("Cấu hình đã được thay đổi ở nơi khác. Tải lại trước khi lưu.")
            self._snapshot(conn, process_id, definition, current_skills=True)
            conn.execute("UPDATE processes SET configuration_json=?,configuration_revision=configuration_revision+1 WHERE id=?", (encode(definition),process_id))
            conn.execute("INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator','process_configuration_saved',?,'{}',?)", (str(uuid4()),process_id,now()))
        return self.get_configuration(process_id)

    def configuration_context(self, process_id):
        from agent_cf_server.domain.processes.topic import topic_configuration
        with self.database.connect(read_only=True) as conn:
            proc, definition, _ = self._current_configuration(conn, process_id)
            snapshot = self._snapshot(conn, process_id, definition, current_skills=True)
            result = {"process_name":proc["name"],"project_name":self.required(conn,"projects",proc["project_id"])["name"]}
            try:
                result.update(topic_configuration(snapshot["tasks"]),topic_supported=True)
            except ValueError as exc:
                result.update(topic_supported=False,reason=str(exc))
            return result

    def freeze_configuration(self, conn, process_id):
        _, definition, _ = self._current_configuration(conn, process_id)
        snapshot = self._snapshot(conn, process_id, definition, current_skills=True)
        row = conn.execute("SELECT id FROM process_versions WHERE process_id=? AND status='draft'", (process_id,)).fetchone()
        vid = row[0] if row else self._new_draft(conn,process_id,snapshot)
        # An old editable row can be consumed only after full validation. Existing
        # published snapshots and their Runs are never updated.
        conn.execute("DELETE FROM dependencies WHERE process_version_id=?", (vid,))
        conn.execute("DELETE FROM tasks WHERE process_version_id=?", (vid,))
        conn.executemany("INSERT INTO tasks VALUES (?,?,?,?)", [(vid,t["id"],t["task_key"],encode(t)) for t in snapshot["tasks"]])
        conn.executemany("INSERT INTO dependencies VALUES (?,?,?)", [(vid,e["source_task_id"],e["target_task_id"]) for e in snapshot["dependencies"]])
        data = encode(snapshot)
        conn.execute("UPDATE process_versions SET definition_json=?,snapshot_sha256=?,published_at=?,status='published',revision=revision+1 WHERE id=?", (data,sha256(data.encode()).hexdigest(),now(),vid))
        return vid

    def publish(self, process_id, version_id, revision, validate_only=False):
        with self.database.transaction() as conn:
            version = self.required(conn, "process_versions", version_id)
            if version["process_id"] != process_id:
                raise KeyError(version_id)
            if version["status"] != "draft" or version["revision"] != revision:
                raise ValueError("Version không phải draft hiện tại; tải lại trước khi publish")
            snapshot = self._snapshot(conn, process_id, json.loads(version["definition_json"]))
            if validate_only:
                return {"valid": True}
            conn.executemany("INSERT INTO tasks VALUES (?,?,?,?)", [(version_id, t["id"], t["task_key"], encode(t)) for t in snapshot["tasks"]])
            conn.executemany("INSERT INTO dependencies VALUES (?,?,?)", [(version_id, e["source_task_id"], e["target_task_id"]) for e in snapshot["dependencies"]])
            data = encode(snapshot)
            conn.execute("UPDATE process_versions SET definition_json=?,snapshot_sha256=?,published_at=?,status='published' WHERE id=?", (data, sha256(data.encode()).hexdigest(), now(), version_id))
            conn.execute("INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator','version_published',?,'{}',?)", (str(uuid4()), version_id, now()))
        return self.get_process(process_id)

    def lifecycle(self, kind, rid, archived):
        table = {"project": "projects", "process": "processes"}[kind]
        with self.database.transaction() as conn:
            record = self.required(conn, table, rid)
            column = "project_id" if kind == "project" else "process_id"
            if archived:
                active = conn.execute(f"SELECT 1 FROM process_runs WHERE {column}=? AND status NOT IN ('succeeded','failed','cancelled')", (rid,)).fetchone()
                if active:
                    raise ValueError("Còn Run chưa kết thúc; không thể Archive")
                conn.execute(f"UPDATE schedules SET is_active=0,next_run_at=NULL WHERE {column}=?", (rid,))
            elif kind == "process" and self.required(conn, "projects", record["project_id"])["status"] != "active":
                raise ValueError("Restore Project trước")
            conn.execute(f"UPDATE {table} SET status=? WHERE id=?", ("archived" if archived else "active", rid))
        return {"status": "archived" if archived else "active"}

    def delete(self, kind, rid):
        table = {"project": "projects", "process": "processes"}[kind]
        column = "project_id" if kind == "project" else "process_id"
        with self.database.transaction() as conn:
            record = self.required(conn, table, rid)
            resource = "Project" if kind == "project" else "Process"
            runs = conn.execute(
                RUN_CONTEXT + f"WHERE r.{column}=? AND r.status NOT IN ('succeeded','failed','cancelled') ORDER BY r.created_at,r.id",
                (rid,),
            ).fetchall()
            if runs:
                raise ValueError(
                    f'Không thể xóa {resource} “{record["name"]}” vì còn Run chưa kết thúc: '
                    + reference_list(run_label(r) for r in runs)
                    + ". Vào Runs để dừng các lượt chạy này và chờ kết thúc trước khi xóa."
                )
            unsettled = conn.execute(
                "SELECT pc.name AS runner_name,r.created_at,r.status,p.name AS process_name,pr.name AS project_name "
                "FROM attempts a JOIN runners pc ON pc.id=a.runner_id JOIN process_runs r ON r.id=a.run_id "
                "JOIN processes p ON p.id=r.process_id JOIN projects pr ON pr.id=r.project_id "
                f"WHERE r.{column}=? AND a.status NOT IN ('succeeded','failed','cancelled') ORDER BY r.created_at,r.id",
                (rid,),
            ).fetchall()
            if unsettled:
                raise ValueError(
                    f'Không thể xóa {resource} “{record["name"]}” vì PC chưa xác nhận công việc đã dừng: '
                    + reference_list(f'PC “{r["runner_name"]}”: {run_label(r)}' for r in unsettled)
                    + ". Kiểm tra kết nối Client trên các PC này và chờ xác nhận đã dừng trước khi xóa."
                )
            delete_process_history(conn, column, rid)
            if kind == "project":
                # Remove membership only: keep the Skill and never widen its scope to Global.
                conn.execute("DELETE FROM skill_projects WHERE project_id=?", (rid,))
                conn.execute("DELETE FROM project_targets WHERE project_id=?", (rid,))
                conn.execute("DELETE FROM project_team WHERE project_id=?", (rid,))
                conn.execute("DELETE FROM projects WHERE id=?", (rid,))
            conn.execute("INSERT INTO audit_events(id,actor_id,event_type,resource_id,data_json,recorded_at) VALUES (?,'operator',?,?,'{}',?)", (str(uuid4()), f"{kind}_deleted", rid, now()))
        if self.artifacts_dir is not None:
            cleanup_artifacts(self.database, self.artifacts_dir)
        return {"deleted": True}

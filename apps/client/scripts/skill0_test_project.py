"""Prepare and serve one local Skill 0 test Project through the public HTTP API.

This deliberately scoped runner handles published versions of its configured Process.
It is not the general Client daemon or a Temporal worker.
"""

import argparse
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time
from uuid import uuid4

import httpx

from agent_cf_client.config import ClientConfig
from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.runtime.codex_adapter import CodexAdapter


ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "runtime" / "skill0-test-project"
MANIFEST = STATE / "project.json"
CREDENTIALS = STATE / "credentials.json"
DEFAULT_TOPIC = "Thật tệ khi làm mẹ đơn thân"


class TestCodexAdapter(CodexAdapter):
    """Pin demo effort while preserving installed tool config for local Skills."""

    def build_command(self, **kwargs):
        command = super().build_command(**kwargs)
        command[1:1] = ["-c", 'model_reasoning_effort="low"']
        # CLI 0.147.0 ignores writable sandbox selection with --ignore-user-config.
        # Local Skills also need the user's installed tool configuration.
        if kwargs.get("sandbox", "read-only") == "read-only":
            command.insert(command.index("exec") + 1, "--ignore-user-config")
        return command


@contextmanager
def runner_lock():
    """A second launcher must not replace the active PC session."""
    import msvcrt

    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "runner.lock").open("a+b") as lock:
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("Skill 0 test PC is already running. Use the existing runner.") from None
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def save(data, *, new_run=False):
    STATE.mkdir(parents=True, exist_ok=True)
    if MANIFEST.exists() and not new_run:
        current = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if current.get("last_run_id"):
            data["last_run_id"] = current["last_run_id"]
    temporary = MANIFEST.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(MANIFEST)


def api(server_url, method, path, payload=None):
    response = httpx.request(
        method, server_url + path, json=payload, timeout=15,
        headers={"Idempotency-Key": str(uuid4())},
    )
    response.raise_for_status()
    return response.json()


def setup(server_url, model, skill_path=None, working_directory=None):
    ClientConfig(server_url=server_url)
    source = Path(skill_path or ROOT / "tests/.agents/skills/0.tao_cot_truyen/SKILL.md")
    working = Path(working_directory or ROOT / "tests")
    if not source.is_absolute() or not source.is_file() or not working.is_absolute() or not working.is_dir():
        raise ValueError("Skill file and working directory must be existing absolute PC paths.")
    state = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {
        "server_url": server_url, "model": model, "prefix": "skill0-test-" + uuid4().hex[:8],
    }
    if state["server_url"] != server_url or state["model"] != model:
        raise ValueError("Existing test Project uses a different Server/model; keep its configuration.")
    if state.get("execution_mode") != "local_file":
        # Preserve earlier demonstrations and their history; create new versions/configuration.
        state["legacy_demo"] = {k: state[k] for k in ("process_id", "process_version_id", "skill_version_id") if k in state}
        for key in ("process_id", "process_version_id", "skill_version_id", "skill_published"):
            state.pop(key, None)
        state["execution_mode"] = "local_file"
        state["source_path"] = str(source)
        state["working_directory"] = str(working)
    if state["source_path"] != str(source) or state["working_directory"] != str(working):
        raise ValueError("Existing local demo paths differ; edit its Skill/Process draft on the Web.")
    save(state)

    def create(key, path, payload):
        if key not in state:
            result = api(server_url, "POST", path, payload)
            state[key] = result["id"]
            save(state)
        return state[key]

    prefix = state["prefix"]
    workspace = create("workspace_id", "/v1/workspaces", {"name": "Test Skill 0 - Codex CLI"})
    manager = ClientSessionManager(credentials_path=CREDENTIALS)
    if "runner_id" not in state:
        pairing = api(server_url, "POST", "/v1/pairing-codes", {
            "workspace_id": workspace, "name": "PC Local - Test Skill 0 Codex", "expires_in_seconds": 300,
        })
        paired = manager.pair(server_url, pairing["pairing_code"])
        state["runner_id"] = paired["runner_id"]
        save(state)
    provider = create("provider_id", "/v1/settings/providers", {
        "id": prefix + "-provider", "name": "Codex CLI local (test Skill 0)",
        "api_format": "custom", "base_url": "http://127.0.0.1",
    })
    model_id = create("model_id", "/v1/settings/models", {
        "id": prefix + "-model", "provider_id": provider,
        "name": model + " (Codex CLI)", "model_identifier": model,
    })
    role = create("role_id", "/v1/settings/roles", {
        "id": prefix + "-writer", "name": "Biên kịch - test Skill 0",
        "description": "Tạo dàn ý cốt truyện bằng Skill 0 trên Codex CLI local.",
    })
    skill = create("skill_id", "/v1/skills", {
        "is_global": True,
        "id": prefix + "-skill0", "name": "0.tao_cot_truyen (test Codex CLI)",
        "description": "Bản nguyên văn từ tests/.agents/skills/0.tao_cot_truyen/SKILL.md.",
    })
    if not state.get("local_skill_ready"):
        api(server_url, "PATCH", f"/v1/skills/{skill}", {
            "description": "File Skill gốc trên PC: " + str(source) + ". Output giữ tại thư mục làm việc của Process.",
        })
        state["local_skill_ready"] = True
        save(state)
    skill_version = create("skill_version_id", f"/v1/skills/{skill}/versions", {
        "id": prefix + "-local-" + uuid4().hex[:8], "instructions": "",
        "source_path": str(source), "source_runner_id": state["runner_id"],
        "output_standards": "Thực thi file Skill gốc; output thật nằm trên PC theo quy ước của Skill.",
    })
    if not state.get("skill_published"):
        api(server_url, "POST", f"/v1/skills/{skill}/versions/{skill_version}/publish", {})
        state["skill_published"] = True
        state["skill_source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        save(state)
    agent = create("agent_id", "/v1/agents", {
        "id": prefix + "-agent", "name": "Biên kịch Codex - Skill 0 Test",
        "role_id": role, "model_id": model_id, "skill_ids": [skill], "allowed_tool_ids": [],
        "instructions": "Đọc file Skill gốc, giữ nguyên quy trình và tài nguyên của Skill. "
        "Dùng tool tạo/sửa file thực tế trong thư mục làm việc. Không chỉ trả nội dung trong chat. "
        "Giữ file có sẵn không liên quan; không sửa file Skill nguồn.",
    })
    if not state.get("local_agent_ready"):
        api(server_url, "PATCH", f"/v1/agents/{agent}", {
            "instructions": "Đọc file Skill gốc và giữ nguyên quy trình. Dùng tool tạo/sửa output thật trong thư mục làm việc. "
            "Giữ file có sẵn không liên quan, không sửa Skill nguồn. Chỉ chạy Skill được giao; báo trạng thái và đường dẫn thật.",
        })
        state["local_agent_ready"] = True
        save(state)
    project = create("project_id", "/v1/projects", {
        "name": "TEST - Tạo cốt truyện Skill 0 bằng Codex CLI", "workspace_id": workspace,
        "pm_agent_id": agent,
        "description": "Project chạy thử thật Skill 0. Process đã publish, PC riêng, Codex CLI "
        + model + ". Input: {\"topic\":\"Tên chủ đề\"}. Output gốc trên PC: " + str(working),
    })
    if not state.get("local_project_ready"):
        api(server_url, "PATCH", f"/v1/projects/{project}", {
            "name": "TEST - Tạo cốt truyện Skill 0 bằng Codex CLI", "workspace_id": workspace,
            "pm_agent_id": agent, "description": "Web điều khiển Codex thực thi Skill gốc. Output thật tại: " + str(working),
        })
        state["local_project_ready"] = True
        save(state)
    process_id = create("process_id", f"/v1/projects/{project}/processes", {
        "name": "Skill 0 - Thực thi trên PC", "description": "Codex đọc Skill gốc và dùng tool tạo file tại thư mục làm việc trên PC.",
    })
    if "process_version_id" not in state:
        process = api(server_url, "GET", f"/v1/processes/{process_id}")
        version = next(v for v in process["versions"] if v["status"] == "draft")
        definition = {
            "definition_format_version": "1", "interpreter_version": "dag-v1",
            "tasks": [{
                "id": "outline", "task_key": "skill0_outline", "name": "Skill 0 - Tạo cốt truyện",
                "kind": "agent", "agent_id": agent, "skill_id": skill,
                "runner_id": state["runner_id"], "runtime": {"adapter": "codex", "model_id": model},
                "working_directory": str(working),
                "execution_timeout_seconds": 600,
                "input_schema": {"type": "object", "properties": {"topic": {"type": "string"}}},
                "output_schema": {"type": "object"}, "input_mapping": [],
            }], "dependencies": [],
        }
        saved = api(server_url, "PUT", f"/v1/processes/{process_id}/versions/{version['id']}", {
            "revision": version["revision"], "definition": definition,
        })
        draft = next(v for v in saved["versions"] if v["id"] == version["id"])
        api(server_url, "POST", f"/v1/processes/{process_id}/versions/{version['id']}/publish", {
            "revision": draft["revision"],
        })
        state["process_version_id"] = version["id"]
        save(state)
    legacy_process = state.get("legacy_demo", {}).get("process_id")
    if legacy_process and not state.get("legacy_archived"):
        api(server_url, "POST", f"/v1/processes/{legacy_process}/archive", {})
        state["legacy_archived"] = True
        save(state)
    return state


def serve(state):
    manager = ClientSessionManager(credentials_path=CREDENTIALS)
    creds = manager.get_credentials()
    if not creds or creds["runner_id"] != state["runner_id"]:
        raise ValueError("Test runner credentials missing or mismatched.")
    worker = TaskExecutionWorker(
        manager, WorkspaceManager(STATE / "workspaces"), codex_adapter=TestCodexAdapter(),
    )
    if not worker.codex_adapter.is_available():
        raise ValueError("Codex CLI is not available on PATH.")
    manager.start_session(capabilities=["codex"])
    print("Skill 0 test runner ready. Press Ctrl+C to stop after the current task.", flush=True)
    with ThreadPoolExecutor(max_workers=1) as executor:
        current = None
        assignment = None
        while True:
            running = [assignment["attempt_id"]] if current and not current.done() else []
            heartbeat = manager.send_heartbeat(running_attempts=running)
            if heartbeat.get("stop_requested"):
                print("PC disabled; stopping after current task.", flush=True)
                return
            if current and current.done():
                # Never retry a failed/uncertain execution automatically.
                result = current.result()
                print(json.dumps(result, ensure_ascii=False), flush=True)
                current = None
                assignment = None
            if current is None:
                work = []
                process = api(state["server_url"], "GET", f"/v1/processes/{state['process_id']}")
                versions = {v["id"] for v in process["versions"] if v["status"] == "published"}
                for item in worker.poll_work():
                    if item["process_version_id"] in versions:
                        work.append(item)
                if work:
                    # The bounded demo task finishes before this execution grant expires.
                    assignment = worker.claim_task(work[0]["task_run_id"], lease_seconds=900)
                    print("Executing run " + assignment["run_id"], flush=True)
                    current = executor.submit(worker.execute_assignment, assignment)
            time.sleep(3)


def main():
    # Corporate proxies must not intercept the local Server or PC connection.
    existing_no_proxy = os.environ.get("NO_PROXY", os.environ.get("no_proxy", ""))
    os.environ["NO_PROXY"] = existing_no_proxy + ",127.0.0.1,localhost,::1"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "serve", "run"])
    parser.add_argument("--server-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--skill-path", default=str(ROOT / "tests/.agents/skills/0.tao_cot_truyen/SKILL.md"))
    parser.add_argument("--working-directory", default=str(ROOT / "tests"))
    args = parser.parse_args()
    state = setup(args.server_url, args.model, args.skill_path, args.working_directory)
    print("Project: " + state["project_id"], flush=True)
    if args.command == "serve":
        with runner_lock():
            serve(state)
    elif args.command == "run":
        result = api(state["server_url"], "POST", "/v1/runs", {
            "process_version_id": state["process_version_id"], "input": {"topic": args.topic},
        })
        state["last_run_id"] = result["id"]
        save(state, new_run=True)
        print("Run: " + result["id"], flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Test runner stopped.")
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        print("Skill 0 test error: " + str(exc))
        raise SystemExit(1) from None

"""Bounded local-runtime checks; no credentials or raw runtime logs are exported."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests/fixtures/runtime-probe"
FIRST_PROMPT = (
    "Use the runtime-probe Skill in this workspace. Input word: orchid. "
    "Follow the Skill exactly. Do not edit files or delegate."
)
RESUME_PROMPT = (
    "Using the same Skill, recall the input word from the previous turn. "
    "Output only the recall response defined by the Skill. Do not edit files or delegate."
)


def run_command(command: list[str], timeout: float) -> dict:
    try:
        result = subprocess.run(
            command, cwd=FIXTURE, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "timeout_seconds": timeout}
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def summarize_turn(result: dict, expected: str, *, jsonl: bool) -> dict:
    if result.get("status") == "timeout":
        return result
    stdout = result["stdout"]
    events = []
    if jsonl:
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                events.append(event)
        replies = [
            event["item"].get("text", "").strip()
            for event in events
            if event.get("type") == "item.completed"
            and event.get("item", {}).get("type") == "agent_message"
        ]
        reply = replies[-1] if replies else ""
    else:
        reply = stdout.strip()
    completed = not jsonl or any(event.get("type") == "turn.completed" for event in events)
    failed = any(event.get("type") in {"error", "turn.failed"} for event in events)
    passed = result["exit_code"] == 0 and completed and not failed and reply == expected
    return {
        "status": "passed" if passed else "not_verified",
        "exit_code": result["exit_code"],
        "expected_reply_matched": reply == expected,
        "stdout_empty": not stdout.strip(),
        "stderr_empty": not result["stderr"].strip(),
        "turn_completed": completed,
        "thread_id": next(
            (event.get("thread_id") for event in events if event.get("type") == "thread.started"),
            None,
        ),
    }


class CodexRpc:
    def __init__(self, executable: str, timeout: float):
        self.timeout = timeout
        self.sequence = 0
        self.messages = queue.Queue()
        self.process = subprocess.Popen(
            [executable, "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1,
        )
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.process.stdout:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                self.messages.put(value)

    def send(self, value: dict):
        self.process.stdin.write(json.dumps(value) + "\n")
        self.process.stdin.flush()

    def call(self, method: str, params: dict):
        self.sequence += 1
        ident = self.sequence
        self.send({"id": ident, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                value = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if value.get("id") != ident:
                continue
            if "error" in value:
                raise RuntimeError(f"{method}: RPC error {value['error'].get('code')}")
            return value["result"]
        raise TimeoutError(f"{method}: timeout")

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        self.process.stdin.close()
        self.process.stdout.close()


def inspect_codex(executable: str, timeout: float) -> dict:
    rpc = CodexRpc(executable, timeout)
    try:
        rpc.call("initialize", {
            "clientInfo": {"name": "agent_cf_probe", "version": "0.1.0"},
            "capabilities": {"experimentalApi": True},
        })
        rpc.send({"method": "initialized", "params": {}})
        models = []
        cursor = None
        seen_cursors = set()
        for _ in range(100):
            params = {"includeHidden": True}
            if cursor:
                params["cursor"] = cursor
            result = rpc.call("model/list", params)
            for model in result.get("data", []):
                models.append({
                    "id": model["model"], "label": model["displayName"],
                    "hidden": model.get("hidden", False),
                    "is_default": model.get("isDefault", False),
                    "reasoning_efforts": [
                        effort["reasoningEffort"]
                        for effort in model.get("supportedReasoningEfforts", [])
                    ],
                    "access": "not_verified",
                })
            cursor = result.get("nextCursor")
            if not cursor:
                break
            if cursor in seen_cursors:
                raise RuntimeError("model/list: repeated pagination cursor")
            seen_cursors.add(cursor)
        else:
            raise RuntimeError("model/list: pagination limit reached")
        skills = rpc.call("skills/list", {"cwds": [str(FIXTURE)], "forceReload": True})
        probe = [
            {"name": skill["name"], "enabled": skill.get("enabled")}
            for row in skills.get("data", [])
            for skill in row.get("skills", [])
            if skill.get("name") == "runtime-probe"
        ]
        return {"models": models, "fixture_skills": probe}
    finally:
        rpc.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", choices=["codex", "antigravity"])
    parser.add_argument("--smoke", action="store_true", help="Send a small real inference request")
    parser.add_argument("--model", help="Exact verified runtime model ID; never a guessed UI label")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error("--timeout must be between 1 and 120 seconds")
    executable = shutil.which("codex.cmd" if args.runtime == "codex" else "agy.exe")
    if not executable:
        print(json.dumps({"runtime": args.runtime, "status": "not_installed"}))
        return 1
    version = run_command([executable, "--version"], args.timeout)
    report = {"runtime": args.runtime, "transport": "stdio_pipes", "version": version.get("stdout", "").strip()}
    try:
        if args.runtime == "codex":
            report.update(inspect_codex(executable, args.timeout))
        else:
            models = run_command([executable, "models"], args.timeout)
            report["model_discovery"] = {
                "status": "timeout" if models.get("status") == "timeout" else "manual_inspection_required",
                "exit_code": models.get("exit_code"),
                "stdout_empty": not models.get("stdout", "").strip(),
                "stderr_empty": not models.get("stderr", "").strip(),
            }
        if args.smoke:
            if args.runtime == "codex":
                if not args.model:
                    parser.error("Codex smoke check requires an explicit --model from model/list")
                base = [executable, "-a", "never", "-s", "read-only", "exec"]
                turn = run_command(base + ["--json", "-m", args.model, "-C", str(FIXTURE), FIRST_PROMPT], args.timeout)
                first = summarize_turn(turn, "SKILL_OK|orchid|cobalt-lantern-42", jsonl=True)
                report["skill_turn"] = first
                if first["status"] == "passed" and first["thread_id"]:
                    turn = run_command(base + ["resume", "--json", "-m", args.model, first["thread_id"], RESUME_PROMPT], args.timeout)
                    report["resume_turn"] = summarize_turn(turn, "RESUME_OK|orchid|cobalt-lantern-42", jsonl=True)
                else:
                    report["resume_turn"] = {"status": "not_run"}
            else:
                command = [executable, "--sandbox", "--print-timeout", f"{int(args.timeout)}s"]
                if args.model:
                    command += ["--model", args.model]
                turn = run_command(command + ["-p", FIRST_PROMPT], args.timeout)
                report["skill_turn"] = summarize_turn(turn, "SKILL_OK|orchid|cobalt-lantern-42", jsonl=False)
                report["resume_turn"] = {"status": "not_run", "reason": "This pipe probe captured no conversation ID; CMD/PTY validation is recorded separately; never resume the user's latest session"}
    except (OSError, TimeoutError, RuntimeError) as error:
        report["status"] = "error"
        report["error_type"] = type(error).__name__
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if args.smoke:
        return 0 if all(report[key]["status"] == "passed" for key in ("skill_turn", "resume_turn")) else 1
    if args.runtime == "antigravity":
        return 1  # Text output still needs a verified model parser/mapping.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

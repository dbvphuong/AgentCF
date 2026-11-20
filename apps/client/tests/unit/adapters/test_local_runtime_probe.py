import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "scripts/probe_local_runtime.py"
SPEC = importlib.util.spec_from_file_location("local_runtime_probe", SCRIPT)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
EXPECTED = "SKILL_OK|orchid|cobalt-lantern-42"


def event_result(*, completed=True, failed=False, exit_code=0):
    events = [
        {"type": "thread.started", "thread_id": "fixture-thread"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": EXPECTED}},
    ]
    if completed:
        events.append({"type": "turn.completed"})
    if failed:
        events.append({"type": "turn.failed"})
    return {"exit_code": exit_code, "stdout": "\n".join(map(json.dumps, events)), "stderr": ""}


def test_completed_turn_preserves_exact_session_id():
    result = probe.summarize_turn(event_result(), EXPECTED, jsonl=True)
    assert result["status"] == "passed"
    assert result["thread_id"] == "fixture-thread"


@pytest.mark.parametrize("options", [{"completed": False}, {"failed": True}, {"exit_code": 1}])
def test_matching_text_does_not_override_failed_or_incomplete_turn(options):
    assert probe.summarize_turn(event_result(**options), EXPECTED, jsonl=True)["status"] == "not_verified"


def test_zero_exit_with_empty_antigravity_output_is_not_success():
    result = probe.summarize_turn({"exit_code": 0, "stdout": "", "stderr": ""}, EXPECTED, jsonl=False)
    assert result["status"] == "not_verified"
    assert result["stdout_empty"] is True


def test_different_reply_is_not_a_skill_success():
    assert probe.summarize_turn(event_result(), "different", jsonl=True)["status"] == "not_verified"


def test_non_event_lines_do_not_break_protocol_parsing():
    result = event_result()
    result["stdout"] = 'not-json\n[]\n' + result["stdout"]
    assert probe.summarize_turn(result, EXPECTED, jsonl=True)["status"] == "passed"


def test_subprocess_timeout_is_reported_without_partial_output(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="partial private log")

    monkeypatch.setattr(probe.subprocess, "run", timeout)
    result = probe.run_command(["fixture"], 2)
    assert result == {"status": "timeout", "timeout_seconds": 2}


def test_raw_logs_are_not_exported_in_summary():
    result = event_result()
    result["stderr"] = "private runtime diagnostics"
    summary = probe.summarize_turn(result, EXPECTED, jsonl=True)
    assert "private runtime diagnostics" not in json.dumps(summary)

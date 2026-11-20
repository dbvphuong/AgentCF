"""Integration tests for Codex Adapter (RTM-005), Antigravity Adapter (RTM-006), and Review Search (RTM-007)."""

import json
from pathlib import Path
import sys
import pytest

from agent_cf_client.execution.process_manager import ProcessManager, ProcessResult
from agent_cf_client.runtime.antigravity_adapter import AntigravityAdapter
from agent_cf_client.runtime.codex_adapter import CodexAdapter
from agent_cf_client.runtime.review_search import (
    ReviewSearchCapability,
    SearchCapabilityMissingError,
)


# =============================================================================
# RTM-005: Codex Adapter
# =============================================================================

def test_rtm005_codex_command_generation(tmp_path):
    adapter = CodexAdapter(executable_path="codex.cmd")

    # 1. New session command with output-last-message
    out_file = tmp_path / "cot_truyen.txt"
    cmd = adapter.build_command(
        prompt="Tạo cốt truyện cho chủ đề: Thật tệ khi làm mẹ đơn thân",
        cwd=tmp_path,
        model="gpt-5.6-sol",
        output_file=out_file,
    )
    assert "exec" in cmd
    assert "--json" in cmd
    assert "-m" in cmd and "gpt-5.6-sol" in cmd
    assert "--output-last-message" in cmd and str(out_file) in cmd
    assert "Tạo cốt truyện" in cmd[-1]

    # 2. Resume session command
    resume_cmd = adapter.build_command(
        prompt="Tiếp tục phần 2",
        cwd=tmp_path,
        session_id="thread_xyz123",
        model="gpt-5.6-sol",
    )
    assert "resume" in resume_cmd
    assert "thread_xyz123" in resume_cmd
    assert "Tiếp tục phần 2" in resume_cmd


def test_rtm005_codex_output_parsing_success(tmp_path):
    adapter = CodexAdapter()
    out_file = tmp_path / "result.txt"
    out_file.write_text("Cốt truyện hoàn chỉnh: 5 Part", encoding="utf-8")

    jsonl_output = "\n".join([
        json.dumps({"type": "thread.started", "thread_id": "thread-987"}),
        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Dàn ý chi tiết"}}),
        json.dumps({"type": "turn.completed"}),
    ])

    proc_res = ProcessResult(exit_code=0, stdout=jsonl_output, stderr="", duration_seconds=1.2)
    parsed = adapter.parse_output(proc_res, output_file=out_file)

    assert parsed.success is True
    assert parsed.session_id == "thread-987"
    assert parsed.output_text == "Cốt truyện hoàn chỉnh: 5 Part"
    assert len(parsed.artifact_paths) == 1
    assert parsed.artifact_paths[0] == out_file


def test_rtm005_codex_quota_and_model_error_detection():
    adapter = CodexAdapter()

    # Quota exceeded error simulation
    res_quota = ProcessResult(
        exit_code=1,
        stdout="",
        stderr="Error: insufficient_quota. You exceeded your current quota, please check your plan.",
    )
    parsed_quota = adapter.parse_output(res_quota)
    assert parsed_quota.success is False
    assert parsed_quota.error_code == "quota_exceeded"

    # Model not found error simulation
    res_mod = ProcessResult(
        exit_code=1,
        stdout="",
        stderr="Error: model_not_found. The model gpt-6.1-sol does not exist or you do not have access.",
    )
    parsed_mod = adapter.parse_output(res_mod)
    assert parsed_mod.success is False
    assert parsed_mod.error_code == "model_not_found"

    # Exit 0 but empty output -> MUST NOT report success!
    res_empty = ProcessResult(exit_code=0, stdout="", stderr="")
    parsed_empty = adapter.parse_output(res_empty)
    assert parsed_empty.success is False
    assert parsed_empty.error_code == "empty_output"


def test_rtm005_codex_skill_snapshot_verification_with_fixture(tmp_path):
    """Test using the actual fixture without modifying skill files."""
    fixture_dir = Path("tests/fixtures/runtime-probe").resolve()
    skill_file = fixture_dir / ".agents" / "skills" / "runtime-probe" / "SKILL.md"
    if not skill_file.exists():
        pytest.skip("tests/fixtures/runtime-probe not present in workspace")

    # Read unmodified skill
    content = skill_file.read_text(encoding="utf-8")
    assert "runtime-probe" in content

    # Mock runner that simulates reading the skill and generating the expected marker
    class MockProcessManager:
        def run_process(self, argv, cwd, **kwargs):
            events = [
                json.dumps({"type": "thread.started", "thread_id": "thr-fixture-1"}),
                json.dumps({
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "SKILL_OK|orchid|cobalt-lantern-42"},
                }),
                json.dumps({"type": "turn.completed"}),
            ]
            return ProcessResult(exit_code=0, stdout="\n".join(events), stderr="")

    adapter = CodexAdapter(process_manager=MockProcessManager())
    res = adapter.execute_skill(
        prompt="Use the runtime-probe Skill in this workspace. Input word: orchid.",
        cwd=fixture_dir,
        model="gpt-5.6-sol",
    )
    assert res.success is True
    assert res.session_id == "thr-fixture-1"
    assert "SKILL_OK|orchid|cobalt-lantern-42" in res.output_text


# =============================================================================
# RTM-006: Antigravity Adapter & Model Mapping
# =============================================================================

def test_rtm006_antigravity_model_mapping_and_command(tmp_path):
    adapter = AntigravityAdapter(executable_path="agy.exe")

    # 1. Model mapping
    assert adapter.map_model("gemini-3.8-flash-high") == "gemini-3.8-flash-high"
    assert adapter.map_model("claude-sonnet-4.6-thinking") == "Claude Sonnet 4.6 (Thinking)"

    # 2. Command with mapped model and timeout
    cmd = adapter.build_command(
        prompt="Viết kịch bản video YouTube",
        model="gemini-3.8-flash-high",
        timeout_seconds=45.0,
    )
    assert "--model" in cmd
    assert "gemini-3.8-flash-high" in cmd
    assert "--print-timeout" in cmd and "45s" in cmd
    assert "-p" in cmd

    # 3. Resume with conversation ID
    resume_cmd = adapter.build_command(
        prompt="Tiếp tục",
        session_id="conv-agy-456",
    )
    assert "--conversation=conv-agy-456" in resume_cmd


def test_rtm006_antigravity_output_parsing_and_empty_check(tmp_path):
    adapter = AntigravityAdapter()

    # Success with conversation id in output
    raw_output = (
        "Chào bạn, tôi đã tạo xong kịch bản.\n"
        "agy --conversation=conv-succ-789\n"
    )
    proc_res = ProcessResult(exit_code=0, stdout=raw_output, stderr="", duration_seconds=2.0)
    parsed = adapter.parse_output(proc_res)

    assert parsed.success is True
    assert parsed.session_id == "conv-succ-789"
    assert "Chào bạn, tôi đã tạo xong kịch bản" in parsed.output_text

    # Exit 0 with empty stdout (pipe limitation) and no db -> must reject success
    empty_res = ProcessResult(exit_code=0, stdout="", stderr="")
    parsed_empty = adapter.parse_output(empty_res)
    assert parsed_empty.success is False
    assert parsed_empty.error_code == "empty_output"


def test_rtm006_antigravity_protobuf_and_db_extraction(tmp_path):
    """Test extracting output text and session continuity from SQLite conversation DB."""
    from agent_cf_client.runtime.antigravity_adapter import (
        extract_assistant_text_from_step_payload,
    )
    import sqlite3

    # 1. Protobuf payload decoding test
    text = "Kịch bản chi tiết 5 phần cho YouTube"
    text_bytes = text.encode("utf-8")
    sub1 = b"\x0a" + bytes([len(text_bytes)]) + text_bytes
    f20 = bytes([0xa2, 0x01]) + bytes([len(sub1)]) + sub1
    extracted = extract_assistant_text_from_step_payload(f20)
    assert extracted == text

    # 2. SQLite database extraction test
    conv_dir = tmp_path / "conversations"
    conv_dir.mkdir(parents=True)
    conv_id = "conv-test-abc-123"
    db_file = conv_dir / f"{conv_id}.db"

    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_type INTEGER, status INTEGER, step_payload BLOB)"
    )
    conn.execute(
        "INSERT INTO steps (idx, step_type, status, step_payload) VALUES (?, ?, ?, ?)",
        (1, 15, 3, f20),
    )
    conn.commit()
    conn.close()

    adapter = AntigravityAdapter(conversations_dir=conv_dir)
    db_text = adapter.get_latest_response_from_db(conv_id)
    assert db_text == text

    # 3. ProcessResult with empty stdout but log pointing to conversation -> recovers text
    log_file = tmp_path / "test.log"
    log_file.write_text(f"Print mode: conversation={conv_id}, sending message\n", encoding="utf-8")

    empty_stdout_res = ProcessResult(exit_code=0, stdout="", stderr="", duration_seconds=1.5)
    parsed = adapter.parse_output(empty_stdout_res, log_file=log_file)
    assert parsed.success is True
    assert parsed.session_id == conv_id
    assert parsed.output_text == text


def test_rtm006_antigravity_unsupported_model_fallback_rejection(tmp_path):
    """Strict model policy: Never silently swap or allow runtime to substitute another model."""
    adapter = AntigravityAdapter()

    log_file = tmp_path / "fallback.log"
    log_file.write_text(
        "I1116 10:00:00.000000 1234 resolver.go:62] Resolving model Gemini 3.8 Flash High\n"
        "W1116 10:00:00.000000 1234 model_config_manager.go:54] Failed to resolve model flag Gemini 3.8 Flash High: "
        "model Gemini 3.8 Flash High is not recognized as a known model or custom model in settings\n"
        "I1116 10:00:00.000000 1234 model_config_manager.go:157] Propagating selected model override to backend: label=\"Claude Sonnet 4.6 (Thinking)\"\n",
        encoding="utf-8",
    )

    proc_res = ProcessResult(exit_code=0, stdout="Claude output", stderr="", duration_seconds=1.0)
    parsed = adapter.parse_output(
        proc_res,
        log_file=log_file,
        requested_model="gemini-3.8-flash-high",
    )

    assert parsed.success is False
    assert parsed.error_code == "unsupported_model"
    assert "silent model substitution disallowed" in parsed.error_message


# =============================================================================
# RTM-007: Review Search Capability
# =============================================================================

def test_rtm007_review_search_capability():
    search = ReviewSearchCapability()
    codex_adapter = CodexAdapter()
    agy_adapter = AntigravityAdapter()

    # 1. Antigravity supports search natively
    assert search.supports_search(agy_adapter) is True

    # 2. Codex without injected provider lacks search -> raises SearchCapabilityMissingError
    assert search.supports_search(codex_adapter) is False
    with pytest.raises(SearchCapabilityMissingError, match="lacks web search capability"):
        search.search("Kiểm tra nhân vật lịch sử", codex_adapter)

    # 3. Search with Antigravity produces verified result with evidence
    result = search.search("Đối chiếu tình tiết single mom", agy_adapter)
    assert result.verified is True
    assert "Single mom" in result.query or "single mom" in result.query
    assert len(result.sources) >= 1
    assert "https://internal.review.search" in result.sources[0].url

    # 4. Search with custom search provider for Codex
    def custom_provider(query, max_results):
        return [
            {"title": "Bài báo đối chiếu", "url": "https://news.vn/article", "snippet": "Tư liệu thực tế"}
        ]

    search_custom = ReviewSearchCapability(search_provider=custom_provider)
    assert search_custom.supports_search(codex_adapter) is True
    custom_res = search_custom.search("Đối chiếu thực tế", codex_adapter)
    assert custom_res.verified is True
    assert custom_res.sources[0].url == "https://news.vn/article"

    # 5. Audit trail records search queries
    audit = search_custom.get_audit_trail()
    assert len(audit) == 1
    assert audit[0]["query"] == "Đối chiếu thực tế"

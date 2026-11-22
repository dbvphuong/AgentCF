import assert from "node:assert/strict";
import test from "node:test";

import { formatRunEventsToLogItems } from "../../src/features/runs/formatRunLog.ts";

test("formatRunEventsToLogItems formats agent_decision actions clearly", () => {
  const run = {
    id: "run-1",
    workspace_id: "ws-1",
    project_id: "proj-1",
    process_id: "proc-1",
    process_version_id: "pv-1",
    snapshot_sha256: "a".repeat(64),
    revision: 1,
    status: "running",
    input: { topic: "Kể chuyện" },
    created_at: "2026-11-23T00:00:00Z",
    queue_deadline_at: "2026-11-24T00:00:00Z",
    task_runs: [
      { id: "tr-1", run_id: "run-1", process_version_id: "pv-1", task_id: "t-1", status: "running", generation: 1 },
    ],
  };

  const events = [
    {
      id: "ev-1",
      run_id: "run-1",
      sequence: 1,
      task_run_id: "tr-1",
      event_type: "agent_decision",
      recorded_at: "2026-11-23T00:01:00Z",
      data: {
        turn_number: 1,
        agent_name: "Nhân viên A",
        action: "reply",
        reply_message: "Tiếp tục viết Part 2",
        summary_vi: "CLI hỏi viết tiếp Part 2",
      },
    },
    {
      id: "ev-2",
      run_id: "run-1",
      sequence: 2,
      task_run_id: "tr-1",
      event_type: "agent_decision",
      recorded_at: "2026-11-23T00:02:00Z",
      data: {
        turn_number: 2,
        agent_name: "Nhân viên A",
        action: "done",
        route: "dat_chuan",
        summary_vi: "Đã hoàn thành",
      },
    },
    {
      id: "ev-3",
      run_id: "run-1",
      sequence: 3,
      task_run_id: "tr-1",
      event_type: "agent_decision",
      recorded_at: "2026-11-23T00:03:00Z",
      data: {
        turn_number: 3,
        agent_name: "Nhân viên A",
        action: "fail",
        error_analysis: "Thiếu API key cho ElevenLabs",
      },
    },
  ];

  const items = formatRunEventsToLogItems({ run, events, process: null, runners: [], skills: [] });
  assert.equal(items.length, 3);
  assert.equal(items[0].level, "INFO");
  assert.match(items[0].message, /Tự trả lời tiếp.*Tiếp tục viết Part 2/);
  assert.equal(items[1].level, "SUCCESS");
  assert.match(items[1].message, /Duyệt hoàn thành.*dat_chuan/);
  assert.equal(items[2].level, "ERROR");
  assert.match(items[2].message, /Thiếu API key cho ElevenLabs/);
});

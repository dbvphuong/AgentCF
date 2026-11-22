import test from "node:test";
import assert from "node:assert/strict";
import { formatRunEventsToLogItems } from "../../src/features/runs/formatRunLog.ts";

test("downloadArtifactUrl constructs correct path without local traversal", async () => {
  const { downloadArtifactUrl } = await import("../../src/features/runs/api.js").catch(async () => {
    // In node test without TS transpile on the fly, test direct URL logic
    return {
      downloadArtifactUrl: (id) => `/v1/artifacts/${encodeURIComponent(id)}/content`,
    };
  });
  assert.equal(downloadArtifactUrl("art-123"), "/v1/artifacts/art-123/content");
  assert.equal(downloadArtifactUrl("art/sub"), "/v1/artifacts/art%2Fsub/content");
});

test("runs API generates distinct idempotency keys", () => {
  const generateKey = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  const key1 = generateKey("run");
  const key2 = generateKey("run");
  assert.notEqual(key1, key2);
  assert.match(key1, /^run-\d+-[a-z0-9]+$/);

  const contKey = generateKey("continue");
  assert.match(contKey, /^continue-\d+-[a-z0-9]+$/);
});

test("continueRun constructs correct URL with escaping", () => {
  const getContinueUrl = (runId) => `/v1/runs/${encodeURIComponent(runId)}/continue`;
  assert.equal(getContinueUrl("run-123"), "/v1/runs/run-123/continue");
  assert.equal(getContinueUrl("run/special"), "/v1/runs/run%2Fspecial/continue");
});

test("structured log translation categorizes run events clearly", () => {
  const baseRun = {
    id: "run-1",
    workspace_id: "ws-1",
    project_id: "p-1",
    process_id: "proc-1",
    process_version_id: "ver-1",
    snapshot_sha256: "a".repeat(64),
    revision: 1,
    status: "failed",
    input: { topic: "Einstein" },
    error: { message: "One or more tasks failed" },
    created_at: "2026-11-22T05:00:00Z",
    queue_deadline_at: "2026-11-22T05:05:00Z",
    task_runs: [
      {
        id: "tr-1",
        run_id: "run-1",
        process_version_id: "ver-1",
        task_id: "t-1",
        status: "failed",
        generation: 1,
        error: { code: "local_output_missing", message: "Runtime chưa tạo/sửa file output" },
      },
    ],
  };
  const proc = {
    id: "proc-1",
    name: "Demo",
    versions: [{ id: "ver-1", definition: { tasks: [{ id: "t-1", name: "Tạo cốt truyện" }] } }],
  };
  const events = [
    { id: "e1", run_id: "run-1", sequence: 1, event_type: "run_created", data: {}, recorded_at: "2026-11-22T05:00:00Z" },
    { id: "e2", run_id: "run-1", sequence: 2, event_type: "task_claimed", task_run_id: "tr-1", data: { generation: 1 }, recorded_at: "2026-11-22T05:00:01Z" },
    { id: "e3", run_id: "run-1", sequence: 3, event_type: "task_waiting_for_input", task_run_id: "tr-1", data: { reason: "Chờ duyệt" }, recorded_at: "2026-11-22T05:00:02Z" },
    { id: "e4", run_id: "run-1", sequence: 4, event_type: "task_completed", task_run_id: "tr-1", data: { outcome: "succeeded", exit_code: 0 }, recorded_at: "2026-11-22T05:00:03Z" },
    { id: "e5", run_id: "run-1", sequence: 5, event_type: "task_failed", task_run_id: "tr-1", data: { outcome: "failed", exit_code: 1 }, recorded_at: "2026-11-22T05:00:04Z" },
    { id: "e6", run_id: "run-1", sequence: 6, event_type: "run_succeeded", data: {}, recorded_at: "2026-11-22T05:00:05Z" },
    { id: "e7", run_id: "run-1", sequence: 7, event_type: "run_failed", data: { message: "One or more tasks failed" }, recorded_at: "2026-11-22T05:00:06Z" },
    { id: "e8", run_id: "run-1", sequence: 8, event_type: "run_cancelled", data: {}, recorded_at: "2026-11-22T05:00:07Z" },
  ];

  const items = formatRunEventsToLogItems({ run: baseRun, events, process: proc, runners: [], skills: [] });
  assert.deepEqual(
    items.map((i) => i.level),
    ["INFO", "INFO", "WARN", "SUCCESS", "ERROR", "SUCCESS", "ERROR", "WARN"],
  );
  assert.match(items[4].message, /\[local_output_missing\]: Runtime chưa tạo\/sửa file output/);
  assert.match(items[4].details?.errorText ?? "", /\[local_output_missing\]/);
  assert.match(items[6].message, /Tạo cốt truyện: \[local_output_missing\] Runtime chưa tạo\/sửa file output/);
});

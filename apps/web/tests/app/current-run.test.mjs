import test from "node:test";
import assert from "node:assert/strict";
import { createProcessRun } from "../../src/features/runs/api.ts";

test("current Process launch sends topic input without a version and reports validation errors", async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options });
    return Response.json({ id: "run" });
  };
  try {
    const input = { topic_directory: "E:\\Project\\Topic 2", request: "" };
    assert.equal((await createProcessRun("process/one", input)).id, "run");
    assert.equal(calls[0].url, "/v1/processes/process%2Fone/runs");
    assert.deepEqual(JSON.parse(calls[0].body), { input });
    assert.ok(calls[0].headers["Idempotency-Key"]);
    globalThis.fetch = async () => Response.json({ detail: "PC chưa kết nối" }, { status: 422 });
    await assert.rejects(createProcessRun("p", input), /PC chưa kết nối/);
  } finally {
    globalThis.fetch = original;
  }
});

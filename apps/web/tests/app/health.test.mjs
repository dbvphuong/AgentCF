import test from "node:test";
import assert from "node:assert/strict";
import { fetchHealth, parseHealth } from "../../src/app/health.ts";

const health = { status: "ok", database: { schema_version: 1 }, temporal: { configured: true } };

test("accepts a valid health response without treating configured as connected", () => {
  assert.deepEqual(parseHealth(health), health);
  assert.equal(parseHealth({ ...health, temporal: { configured: false } }).temporal.configured, false);
});

test("rejects missing or untrusted health data", () => {
  for (const value of [null, {}, { ...health, status: "failed" }, { ...health, database: { schema_version: 0 } }, { ...health, database: { schema_version: 1.2 } }, { ...health, temporal: { configured: "true" } }]) {
    assert.throws(() => parseHealth(value), /không hợp lệ/);
  }
});

test("requests only safe health data through the same origin", async () => {
  const request = async (url, options) => {
    assert.equal(url, "/healthz");
    assert.equal(options.cache, "no-store");
    assert.equal(options.headers.Accept, "application/json");
    return Response.json(health);
  };
  assert.deepEqual(await fetchHealth(request), health);
});

test("does not report connected for HTTP failure, invalid JSON or malformed JSON", async () => {
  await assert.rejects(fetchHealth(async () => new Response("unavailable", { status: 503 })), /HTTP 503/);
  await assert.rejects(fetchHealth(async () => new Response("<html>")), /không hợp lệ/);
  await assert.rejects(fetchHealth(async () => Response.json({ status: "ok" })), /không hợp lệ/);
});

test("stops oversized health streams", async () => {
  let cancelled = false;
  const body = new ReadableStream({
    pull(controller) { controller.enqueue(new Uint8Array(4096)); },
    cancel() { cancelled = true; },
  });
  await assert.rejects(fetchHealth(async () => new Response(body)), /không hợp lệ/);
  assert.equal(cancelled, true);
});

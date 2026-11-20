import test from "node:test";
import assert from "node:assert/strict";
import { request, dateTime, resource } from "../../src/shared/api.ts";

test("UI requests escape resource IDs and preserve JSON and mutation keys", async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return Response.json({ id: "saved" });
  };
  try {
    const path = resource("/v1/projects", "a/b?c");
    assert.equal(path, "/v1/projects/a%2Fb%3Fc");
    assert.deepEqual(await request(path, "POST", { name: "Dự án" }), {
      id: "saved",
    });
    await request(path, "POST", {});
    assert.equal(JSON.parse(calls[0].options.body).name, "Dự án");
    assert.notEqual(
      calls[0].options.headers["Idempotency-Key"],
      calls[1].options.headers["Idempotency-Key"],
    );
    assert.equal(calls[0].options.cache, "no-store");
  } finally {
    globalThis.fetch = original;
  }
});

test("UI propagates server validation errors and handles a 204 response", async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () =>
      Response.json({ detail: "Draft đã thay đổi" }, { status: 422 });
    await assert.rejects(request("/v1/processes/x"), /Draft đã thay đổi/);
    globalThis.fetch = async () => new Response(null, { status: 204 });
    assert.equal(await request("/v1/skills/x", "DELETE"), undefined);
  } finally {
    globalThis.fetch = original;
  }
});

test("UI dates use Vietnam time and clearly handle missing or malformed telemetry", () => {
  assert.equal(dateTime(null), "—");
  assert.equal(dateTime("invalid"), "—");
  assert.match(dateTime("2026-11-17T00:00:00Z"), /07:00:00/);
});

test("delete errors preserve named blockers and explain network, permission and server failures", async () => {
  const original = globalThis.fetch;
  try {
    const message = 'Không thể xóa Provider “Local” vì còn Model API liên kết: “Model viết bài”.';
    globalThis.fetch = async () => Response.json({ detail: message }, { status: 409 });
    await assert.rejects(request('/v1/settings/providers/p', 'DELETE'), error => error.message === message);
    globalThis.fetch = async () => new Response('upstream unavailable', { status: 502 });
    await assert.rejects(request('/v1/robots/r', 'DELETE'), /Server chưa xử lý được yêu cầu xóa/);
    globalThis.fetch = async () => Response.json({ error: 'private-internal-diagnostic' }, { status: 403 });
    await assert.rejects(request('/v1/skills/s', 'DELETE'), error => error.message === 'Bạn không có quyền xóa mục này.');
    globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
    await assert.rejects(request('/v1/agents/a', 'DELETE'), /Kiểm tra kết nối tới Server/);
    globalThis.fetch = async () => { throw new DOMException('Aborted', 'AbortError'); };
    await assert.rejects(request('/v1/robots/r', 'DELETE'), error => error.name === 'AbortError');
  } finally {
    globalThis.fetch = original;
  }
});

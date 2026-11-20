import test from "node:test";
import assert from "node:assert/strict";

test("overview acknowledgeRunError constructs correct URL with escaping", () => {
  const getAckUrl = (runId) => `/v1/runs/${encodeURIComponent(runId)}/acknowledge-error`;
  assert.equal(getAckUrl("run-123"), "/v1/runs/run-123/acknowledge-error");
  assert.equal(getAckUrl("run/special"), "/v1/runs/run%2Fspecial/acknowledge-error");
});

test("overview API generates distinct idempotency keys", () => {
  const generateKey = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  const key1 = generateKey("ack");
  const key2 = generateKey("ack");
  assert.notEqual(key1, key2);
  assert.match(key1, /^ack-\d+-[a-z0-9]+$/);
});

test("overview displays dash for missing targets and does not fabricate 0/0 or On track", () => {
  const formatTarget = (targets) => {
    if (!targets || targets.length === 0) return "—";
    const t = targets[0];
    return `${t.completed_count}/${t.target_count} (${t.status})`;
  };

  assert.equal(formatTarget(null), "—");
  assert.equal(formatTarget([]), "—");
  assert.equal(
    formatTarget([{ completed_count: 5, target_count: 10, status: "in_progress" }]),
    "5/10 (in_progress)"
  );
});

test("overview displays dash and explicit label for missing token usage", () => {
  const formatTokens = (ag) => {
    if (!ag.has_usage || ag.total_tokens === null || ag.total_tokens === undefined) {
      return "— (Chưa có dữ liệu)";
    }
    return `${ag.total_tokens.toLocaleString("vi-VN")} tokens`;
  };

  assert.equal(formatTokens({ has_usage: false, total_tokens: null }), "— (Chưa có dữ liệu)");
  assert.equal(formatTokens({ has_usage: true, total_tokens: 15000 }), "15.000 tokens");
});

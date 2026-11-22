import test from "node:test";
import assert from "node:assert/strict";
import {
  extractEmbeddedModelLevel,
  resolveTaskModelInfo,
  shouldShowReasoningEffort,
} from "../../src/features/projects/processes/modelLevel.ts";

test("extractEmbeddedModelLevel detects level encoded in Antigravity model identifiers and names", () => {
  assert.equal(extractEmbeddedModelLevel({ model_identifier: "gemini-4-hydrogen-xhigh", name: "Gemini 4 Hydrogen (XHigh)" }), "xhigh");
  assert.equal(extractEmbeddedModelLevel({ model_identifier: "gemini-4-argon-high", name: "Gemini 4 Argon (High)" }), "high");
  assert.equal(extractEmbeddedModelLevel({ model_identifier: "gpt-oss-120b-medium", name: "GPT-OSS 120B (Medium)" }), "medium");
  assert.equal(extractEmbeddedModelLevel({ model_identifier: "claude-opus-5-5-low", name: "Claude Opus 5.5 (Low)" }), "low");
  assert.equal(extractEmbeddedModelLevel({ model_identifier: "custom-model", name: "Custom (High)" }), "high");

  assert.equal(extractEmbeddedModelLevel({ model_identifier: "gemini-pro-orchestrator-neon", name: "Orchestrator (Neon)" }), null);
  assert.equal(extractEmbeddedModelLevel({ model_identifier: "gpt-6.2-sol", name: "GPT-6.2-Sol" }), null);
  assert.equal(extractEmbeddedModelLevel({ model_identifier: "agy-exact", name: "Agy model" }), null);
  assert.equal(extractEmbeddedModelLevel(null), null);
});

test("shouldShowReasoningEffort hides redundant level selector when Antigravity model already includes level", () => {
  assert.equal(shouldShowReasoningEffort("codex", null), true);
  assert.equal(shouldShowReasoningEffort("codex", { tool_id: "codex", model_identifier: "gpt-6.2-sol", name: "GPT-6.2-Sol" }), true);

  assert.equal(shouldShowReasoningEffort("antigravity", null), false);
  assert.equal(shouldShowReasoningEffort("antigravity", { tool_id: "antigravity", model_identifier: "gemini-4-hydrogen-xhigh", name: "Gemini 4 Hydrogen (XHigh)" }), false);
  assert.equal(shouldShowReasoningEffort("antigravity", { tool_id: "antigravity", model_identifier: "gemini-4-argon-high", name: "Gemini 4 Argon (High)" }), false);

  assert.equal(shouldShowReasoningEffort("antigravity", { tool_id: "antigravity", model_identifier: "gemini-pro-orchestrator-neon", name: "Orchestrator (Neon)" }), true);
  assert.equal(shouldShowReasoningEffort("antigravity", { tool_id: "antigravity", model_identifier: "agy-exact", name: "Agy model" }), true);
});

test("resolveTaskModelInfo avoids redundant card pill for embedded-level models and labels Inspector clearly", () => {
  const models = [
    { id: "m-agy-xhigh", tool_id: "antigravity", name: "Gemini 4 Hydrogen (XHigh)", model_identifier: "gemini-4-hydrogen-xhigh" },
    { id: "m-agy-orch", tool_id: "antigravity", name: "Orchestrator (Neon)", model_identifier: "gemini-pro-orchestrator-neon" },
    { id: "m-codex", tool_id: "codex", name: "GPT-6.2-Sol", model_identifier: "gpt-6.2-sol" },
  ];

  const agyEmbedded = resolveTaskModelInfo({ kind: "agent", runtime: { adapter: "antigravity", tool_model_id: "m-agy-xhigh", model_id: "gemini-4-hydrogen-xhigh" } }, models);
  assert.equal(agyEmbedded.showCardPill, false);
  assert.equal(agyEmbedded.effortRaw, "xhigh");
  assert.equal(agyEmbedded.inspectorLevelLabel, "Extra High (theo model)");

  const agyOrch = resolveTaskModelInfo({ kind: "agent", runtime: { adapter: "antigravity", tool_model_id: "m-agy-orch", model_id: "gemini-pro-orchestrator-neon", reasoning_effort: "high" } }, models);
  assert.equal(agyOrch.showCardPill, true);
  assert.equal(agyOrch.levelLabel, "High");
  assert.equal(agyOrch.inspectorLevelLabel, "High");

  const codexDefault = resolveTaskModelInfo({ kind: "agent", runtime: { adapter: "codex", tool_model_id: "m-codex", model_id: "gpt-6.2-sol" } }, models);
  assert.equal(codexDefault.showCardPill, true);
  assert.equal(codexDefault.levelLabel, "Mặc định");
  assert.equal(codexDefault.inspectorLevelLabel, "Mặc định");

  assert.equal(resolveTaskModelInfo({ kind: "robot" }, models), null);
});

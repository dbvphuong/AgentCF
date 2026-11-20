-- CLI model preferences are independent of API providers/models used by orchestration Agents.
CREATE TABLE ai_tool_models (
    id TEXT PRIMARY KEY,
    tool_id TEXT NOT NULL CHECK(tool_id IN ('codex','antigravity')),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    model_identifier TEXT NOT NULL CHECK(length(trim(model_identifier)) > 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','disabled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(tool_id, model_identifier)
) STRICT;

-- Small, editable defaults from the locally verified adapters, not an entitlement claim.
INSERT INTO ai_tool_models VALUES
('cli-codex-sol','codex','GPT-5.6-Sol','gpt-5.6-sol','active',strftime('%Y-%m-%dT%H:%M:%fZ','now'),strftime('%Y-%m-%dT%H:%M:%fZ','now')),
('cli-agy-sonnet','antigravity','Claude Sonnet 4.6 (Thinking)','claude-sonnet-4.6-thinking','active',strftime('%Y-%m-%dT%H:%M:%fZ','now'),strftime('%Y-%m-%dT%H:%M:%fZ','now'));

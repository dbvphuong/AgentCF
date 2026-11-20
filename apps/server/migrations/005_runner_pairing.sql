CREATE TABLE runner_pairing_codes (
    code_hash TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

ALTER TABLE runners ADD COLUMN name TEXT NOT NULL DEFAULT 'Runner PC';
ALTER TABLE runners ADD COLUMN machine_fingerprint TEXT;
ALTER TABLE runners ADD COLUMN client_version TEXT;
ALTER TABLE runners ADD COLUMN last_seen_at TEXT;
ALTER TABLE runners ADD COLUMN cpu_percent REAL;
ALTER TABLE runners ADD COLUMN ram_percent REAL;

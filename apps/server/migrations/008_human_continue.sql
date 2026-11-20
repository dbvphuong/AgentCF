ALTER TABLE task_runs ADD COLUMN waiting_for TEXT;

ALTER TABLE task_runs ADD COLUMN attention_reason TEXT;

CREATE TABLE human_decisions (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES process_runs(id),
    task_run_id TEXT REFERENCES task_runs(id),
    decision TEXT NOT NULL CHECK(decision IN ('proceed', 'approved', 'rejected', 'retry', 'continue')),
    feedback TEXT NOT NULL DEFAULT '',
    input_json TEXT CHECK(input_json IS NULL OR json_valid(input_json)),
    decision_key TEXT NOT NULL UNIQUE CHECK(length(trim(decision_key)) > 0),
    decided_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE INDEX idx_human_decisions_run ON human_decisions(run_id);

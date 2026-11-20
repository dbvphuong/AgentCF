CREATE TABLE review_decisions (
    id TEXT PRIMARY KEY,
    task_run_id TEXT NOT NULL REFERENCES task_runs(id),
    attempt_id TEXT NOT NULL REFERENCES attempts(id),
    reviewer_agent_id TEXT NOT NULL,
    revision_round INTEGER NOT NULL DEFAULT 1 CHECK(revision_round > 0),
    decision TEXT NOT NULL CHECK(decision IN ('approved', 'revision_requested', 'escalated')),
    score REAL CHECK(score IS NULL OR (score >= 0.0 AND score <= 10.0)),
    feedback TEXT NOT NULL DEFAULT '',
    violations_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(violations_json)),
    decision_key TEXT NOT NULL UNIQUE CHECK(length(trim(decision_key)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE INDEX idx_review_decisions_task ON review_decisions(task_run_id);

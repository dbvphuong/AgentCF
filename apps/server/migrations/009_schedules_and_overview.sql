-- Migration 009: Schedules (PROC-004) and Overview & Real Tracking (OVW-001)

CREATE TABLE schedules (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    process_id TEXT NOT NULL REFERENCES processes(id),
    process_version_id TEXT NOT NULL REFERENCES process_versions(id),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    cadence TEXT NOT NULL CHECK(cadence IN ('manual', 'hourly', 'daily', 'weekly', 'cron')),
    cron_expression TEXT,
    timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
    is_active INTEGER NOT NULL DEFAULT 0 CHECK(is_active IN (0, 1)),
    default_runner_id TEXT REFERENCES runners(id),
    run_input_json TEXT CHECK(run_input_json IS NULL OR json_valid(run_input_json)),
    next_run_at TEXT,
    last_run_at TEXT,
    last_run_id TEXT REFERENCES process_runs(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;

CREATE TABLE schedule_ticks (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL REFERENCES schedules(id),
    scheduled_for TEXT NOT NULL,
    run_id TEXT REFERENCES process_runs(id),
    status TEXT NOT NULL CHECK(status IN ('triggered', 'skipped_busy', 'failed')),
    created_at TEXT NOT NULL,
    UNIQUE(schedule_id, scheduled_for)
) STRICT;

CREATE TABLE project_targets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    period TEXT NOT NULL CHECK(period IN ('weekly', 'monthly', 'quarterly')),
    target_count INTEGER NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK(status IN ('in_progress', 'completed', 'behind', 'on_track')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;

CREATE TABLE run_error_acknowledgments (
    run_id TEXT PRIMARY KEY REFERENCES process_runs(id),
    acknowledged_by TEXT NOT NULL,
    notes TEXT,
    acknowledged_at TEXT NOT NULL
) STRICT;

CREATE TABLE agent_token_usage (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES process_runs(id),
    task_run_id TEXT NOT NULL REFERENCES task_runs(id),
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    recorded_at TEXT NOT NULL
) STRICT;

CREATE TABLE runners (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    status TEXT NOT NULL CHECK(status IN ('pending', 'online', 'offline', 'disabled')),
    credential_hash TEXT,
    credential_expires_at TEXT,
    UNIQUE(id, workspace_id)
) STRICT;

CREATE TABLE runner_sessions (
    id TEXT PRIMARY KEY,
    runner_id TEXT NOT NULL REFERENCES runners(id),
    status TEXT NOT NULL CHECK(status IN ('active', 'revoked', 'expired')),
    created_at TEXT NOT NULL,
    last_heartbeat_at TEXT,
    capabilities_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(capabilities_json)),
    UNIQUE(id, runner_id)
) STRICT;

CREATE UNIQUE INDEX one_active_session_per_runner ON runner_sessions(runner_id) WHERE status = 'active';

CREATE TABLE process_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    process_id TEXT NOT NULL,
    process_version_id TEXT NOT NULL,
    snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256) = 64 AND snapshot_sha256 NOT GLOB '*[^a-f0-9]*'),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'reconciling', 'cancelling', 'succeeded', 'failed', 'cancelled')),
    input_json TEXT NOT NULL CHECK(json_valid(input_json)),
    output_json TEXT CHECK(output_json IS NULL OR json_valid(output_json)),
    error_json TEXT CHECK(error_json IS NULL OR json_valid(error_json)),
    attention_reason TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    queue_deadline_at TEXT NOT NULL,
    schedule_id TEXT,
    scheduled_for TEXT,
    FOREIGN KEY(project_id, workspace_id) REFERENCES projects(id, workspace_id),
    FOREIGN KEY(process_id, project_id) REFERENCES processes(id, project_id),
    FOREIGN KEY(process_version_id, process_id) REFERENCES process_versions(id, process_id),
    UNIQUE(id, process_version_id),
    CHECK((schedule_id IS NULL) = (scheduled_for IS NULL)),
    CHECK((status IN ('succeeded', 'failed', 'cancelled')) = (ended_at IS NOT NULL))
) STRICT;

CREATE UNIQUE INDEX one_run_per_schedule_tick ON process_runs(schedule_id, scheduled_for)
WHERE schedule_id IS NOT NULL;

CREATE TABLE task_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    process_version_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'queued', 'running', 'reconciling', 'succeeded', 'failed', 'skipped', 'cancelled')),
    input_json TEXT CHECK(input_json IS NULL OR json_valid(input_json)),
    output_json TEXT CHECK(output_json IS NULL OR json_valid(output_json)),
    error_json TEXT CHECK(error_json IS NULL OR json_valid(error_json)),
    generation INTEGER NOT NULL DEFAULT 0 CHECK(generation >= 0),
    FOREIGN KEY(run_id, process_version_id) REFERENCES process_runs(id, process_version_id),
    FOREIGN KEY(process_version_id, task_id) REFERENCES tasks(process_version_id, id),
    UNIQUE(run_id, task_id),
    UNIQUE(id, run_id)
) STRICT;

CREATE TABLE attempts (
    id TEXT PRIMARY KEY,
    task_run_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    runner_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation > 0),
    status TEXT NOT NULL CHECK(status IN ('claimed', 'running', 'reconciling', 'succeeded', 'failed', 'cancelled')),
    claimed_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    execution_deadline_at TEXT NOT NULL,
    stop_reason TEXT CHECK(stop_reason IN ('cancel_requested', 'timeout', 'credential_revoked', 'lease_expired')),
    launch_evidence_json TEXT CHECK(launch_evidence_json IS NULL OR json_valid(launch_evidence_json)),
    output_json TEXT CHECK(output_json IS NULL OR json_valid(output_json)),
    error_json TEXT CHECK(error_json IS NULL OR json_valid(error_json)),
    FOREIGN KEY(task_run_id, run_id) REFERENCES task_runs(id, run_id),
    FOREIGN KEY(session_id, runner_id) REFERENCES runner_sessions(id, runner_id),
    UNIQUE(task_run_id, generation),
    UNIQUE(id, run_id),
    UNIQUE(id, task_run_id, runner_id, session_id, generation),
    CHECK((status IN ('succeeded', 'failed', 'cancelled')) = (ended_at IS NOT NULL))
) STRICT;

CREATE UNIQUE INDEX one_unsettled_attempt ON attempts(task_run_id)
WHERE status IN ('claimed', 'running', 'reconciling');

CREATE TABLE execution_grants (
    attempt_id TEXT PRIMARY KEY,
    task_run_id TEXT NOT NULL,
    runner_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK(generation > 0),
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY(attempt_id, task_run_id, runner_id, session_id, generation)
        REFERENCES attempts(id, task_run_id, runner_id, session_id, generation)
) STRICT;

CREATE UNIQUE INDEX one_unrevoked_grant ON execution_grants(task_run_id) WHERE revoked_at IS NULL;

CREATE TABLE receipts (
    principal_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    request_key TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    response_json TEXT NOT NULL CHECK(json_valid(response_json)),
    created_at TEXT NOT NULL,
    PRIMARY KEY(principal_id, operation, resource_id, request_key)
) STRICT;

CREATE TABLE engine_inbox (
    command_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES process_runs(id),
    request_sha256 TEXT NOT NULL,
    response_json TEXT NOT NULL CHECK(json_valid(response_json)),
    applied_at TEXT NOT NULL
) STRICT;

CREATE TABLE run_events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES process_runs(id),
    sequence INTEGER NOT NULL CHECK(sequence > 0),
    event_type TEXT NOT NULL,
    task_run_id TEXT,
    attempt_id TEXT,
    data_json TEXT NOT NULL CHECK(json_valid(data_json)),
    occurred_at TEXT,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(task_run_id, run_id) REFERENCES task_runs(id, run_id),
    FOREIGN KEY(attempt_id, run_id) REFERENCES attempts(id, run_id),
    UNIQUE(run_id, sequence)
) STRICT;

CREATE TABLE audit_events (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES process_runs(id),
    actor_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    data_json TEXT NOT NULL CHECK(json_valid(data_json)),
    recorded_at TEXT NOT NULL
) STRICT;

CREATE TABLE engine_outbox (
    command_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES process_runs(id),
    sequence INTEGER NOT NULL CHECK(sequence > 0),
    command_type TEXT NOT NULL,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    created_at TEXT NOT NULL,
    delivered_at TEXT,
    delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK(delivery_attempts >= 0),
    UNIQUE(run_id, sequence)
) STRICT;

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL REFERENCES attempts(id),
    logical_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
    sha256 TEXT NOT NULL CHECK(length(sha256) = 64 AND sha256 NOT GLOB '*[^a-f0-9]*'),
    availability TEXT NOT NULL CHECK(availability IN ('uploading', 'available')),
    storage_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    UNIQUE(attempt_id, logical_name)
) STRICT;

CREATE TRIGGER run_uses_published_snapshot BEFORE INSERT ON process_runs
WHEN NOT EXISTS(SELECT 1 FROM process_versions
    WHERE id = NEW.process_version_id AND status = 'published' AND snapshot_sha256 = NEW.snapshot_sha256)
BEGIN
    SELECT RAISE(ABORT, 'published_snapshot_required');
END;

CREATE TRIGGER immutable_run_identity BEFORE UPDATE ON process_runs
WHEN NEW.process_version_id <> OLD.process_version_id OR NEW.snapshot_sha256 <> OLD.snapshot_sha256
    OR NEW.process_id <> OLD.process_id OR NEW.project_id <> OLD.project_id
    OR NEW.workspace_id <> OLD.workspace_id OR NEW.input_json <> OLD.input_json
BEGIN
    SELECT RAISE(ABORT, 'run_identity_immutable');
END;

CREATE TRIGGER terminal_run_immutable BEFORE UPDATE ON process_runs
WHEN OLD.status IN ('succeeded', 'failed', 'cancelled')
BEGIN
    SELECT RAISE(ABORT, 'terminal_run_immutable');
END;

CREATE TRIGGER immutable_task_run_identity BEFORE UPDATE ON task_runs
WHEN NEW.run_id <> OLD.run_id OR NEW.process_version_id <> OLD.process_version_id OR NEW.task_id <> OLD.task_id
BEGIN
    SELECT RAISE(ABORT, 'task_run_identity_immutable');
END;

CREATE TRIGGER immutable_attempt_identity BEFORE UPDATE ON attempts
WHEN NEW.run_id <> OLD.run_id OR NEW.task_run_id <> OLD.task_run_id OR NEW.runner_id <> OLD.runner_id
    OR NEW.session_id <> OLD.session_id OR NEW.generation <> OLD.generation
BEGIN
    SELECT RAISE(ABORT, 'attempt_identity_immutable');
END;

CREATE TRIGGER attempt_runner_workspace BEFORE INSERT ON attempts
WHEN NOT EXISTS(SELECT 1 FROM process_runs p JOIN runners r ON r.workspace_id = p.workspace_id
    WHERE p.id = NEW.run_id AND r.id = NEW.runner_id)
BEGIN
    SELECT RAISE(ABORT, 'runner_workspace_mismatch');
END;

CREATE TRIGGER terminal_task_run_immutable BEFORE UPDATE ON task_runs
WHEN OLD.status IN ('succeeded', 'failed', 'skipped', 'cancelled')
BEGIN
    SELECT RAISE(ABORT, 'terminal_task_run_immutable');
END;

CREATE TRIGGER terminal_attempt_immutable BEFORE UPDATE ON attempts
WHEN OLD.status IN ('succeeded', 'failed', 'cancelled')
BEGIN
    SELECT RAISE(ABORT, 'terminal_attempt_immutable');
END;

CREATE TRIGGER append_only_run_event_update BEFORE UPDATE ON run_events
BEGIN
    SELECT RAISE(ABORT, 'event_immutable');
END;

CREATE TRIGGER append_only_run_event_delete BEFORE DELETE ON run_events
BEGIN
    SELECT RAISE(ABORT, 'event_immutable');
END;

CREATE TRIGGER append_only_audit_update BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_immutable');
END;

CREATE TRIGGER append_only_audit_delete BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_immutable');
END;

CREATE TRIGGER finalized_artifact_immutable BEFORE UPDATE ON artifacts
WHEN OLD.availability = 'available'
BEGIN
    SELECT RAISE(ABORT, 'artifact_immutable');
END;

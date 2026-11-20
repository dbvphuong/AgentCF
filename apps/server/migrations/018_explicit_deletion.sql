-- Explicit aggregate deletion may remove owned history; ordinary mutations remain immutable.

DROP TRIGGER immutable_published_version_delete;
CREATE TRIGGER immutable_published_version_delete BEFORE DELETE ON process_versions
WHEN (OLD.status = 'published') AND NOT cf_delete_allowed('process_versions', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

DROP TRIGGER immutable_published_task_delete;
CREATE TRIGGER immutable_published_task_delete BEFORE DELETE ON tasks
WHEN ((SELECT status FROM process_versions WHERE id=OLD.process_version_id)='published') AND NOT cf_delete_allowed('tasks', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

DROP TRIGGER immutable_published_dependency_delete;
CREATE TRIGGER immutable_published_dependency_delete BEFORE DELETE ON dependencies
WHEN ((SELECT status FROM process_versions WHERE id=OLD.process_version_id)='published') AND NOT cf_delete_allowed('dependencies', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

DROP TRIGGER immutable_run_delete;
CREATE TRIGGER immutable_run_delete BEFORE DELETE ON process_runs
WHEN (1) AND NOT cf_delete_allowed('process_runs', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'run_history_immutable');
END;

DROP TRIGGER immutable_task_run_delete;
CREATE TRIGGER immutable_task_run_delete BEFORE DELETE ON task_runs
WHEN (1) AND NOT cf_delete_allowed('task_runs', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'task_run_history_immutable');
END;

DROP TRIGGER immutable_attempt_delete;
CREATE TRIGGER immutable_attempt_delete BEFORE DELETE ON attempts
WHEN (1) AND NOT cf_delete_allowed('attempts', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'attempt_history_immutable');
END;

DROP TRIGGER append_only_run_event_delete;
CREATE TRIGGER append_only_run_event_delete BEFORE DELETE ON run_events
WHEN (1) AND NOT cf_delete_allowed('run_events', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'event_immutable');
END;

DROP TRIGGER append_only_audit_delete;
CREATE TRIGGER append_only_audit_delete BEFORE DELETE ON audit_events
WHEN (1) AND NOT cf_delete_allowed('audit_events', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'audit_immutable');
END;

DROP TRIGGER finalized_artifact_delete;
CREATE TRIGGER finalized_artifact_delete BEFORE DELETE ON artifacts
WHEN (OLD.availability='available') AND NOT cf_delete_allowed('artifacts', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'artifact_immutable');
END;

DROP TRIGGER immutable_receipt_delete;
CREATE TRIGGER immutable_receipt_delete BEFORE DELETE ON receipts
WHEN (1) AND NOT cf_delete_allowed('receipts', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'receipt_immutable');
END;

DROP TRIGGER immutable_inbox_delete;
CREATE TRIGGER immutable_inbox_delete BEFORE DELETE ON engine_inbox
WHEN (1) AND NOT cf_delete_allowed('engine_inbox', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'inbox_immutable');
END;

DROP TRIGGER immutable_published_skill_version_delete;
CREATE TRIGGER immutable_published_skill_version_delete BEFORE DELETE ON skill_versions
WHEN (OLD.status='published') AND NOT cf_delete_allowed('skill_versions', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'published_skill_version_immutable');
END;

DROP TRIGGER immutable_published_skill_tool_delete;
CREATE TRIGGER immutable_published_skill_tool_delete BEFORE DELETE ON skill_version_tools
WHEN ((SELECT status FROM skill_versions WHERE id=OLD.skill_version_id)='published') AND NOT cf_delete_allowed('skill_version_tools', OLD.rowid)
BEGIN
    SELECT RAISE(ABORT, 'published_skill_version_immutable');
END;

CREATE TABLE artifact_cleanup (
    storage_key TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;

